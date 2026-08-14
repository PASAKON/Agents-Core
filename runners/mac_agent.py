"""Mac-side drain agent for the secretary's relay queue (task-776fbf7e).

The Telegram secretary (SomPong) runs on Contabo. Every C-level session the CEO
actually works with runs on this Mac. The secretary can act on Contabo directly,
but anything aimed at the Mac lands in a queue that needs draining here.

Direction matters: **the Mac dials out**. Contabo cannot reach it — SSH is
closed there, verified `Connection refused` — and that asymmetry is the security
design, not a gap to fix. A compromised Contabo can put rows in a queue; it
cannot make this machine do anything the dispatch table below does not already
allow.

Queue contract (owned by runners/relay_mcp_server.py on Contabo — consume it,
do not redesign it here):

    relay_queue(id, kind, target_role, payload TEXT/JSON, status,
                created_at, done_at, result)
    kind: 'relay' | 'spawn' | 'read' | 'terminals' | 'history' | 'terminal_open'
                                 status: 'pending' | 'done' | 'failed'

`relay` delivers by MAILBOX LETTER (state/inbox/<role>-<sid>/, via
lib.mailbox) and reports done only once the letter file exists on disk —
never by typing the body into a pane (GH #70). Same contract as Contabo's
relay_to_session (task-18241f1d).

Run:  python -m runners.mac_agent          (loop)
      python -m runners.mac_agent --once   (single tick, for testing)
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import mailbox  # noqa: E402
from lib.logger import get_logger  # noqa: E402
from tools.org_inspector import (  # noqa: E402
    detect_host,
    history_index,
    history_read,
    list_sessions,
)
from tools.send_to_cxo import (  # noqa: E402
    Identity,
    _active_session_id,
    attempt_wake,
    authorize,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SSH_HOST = os.environ.get("MAC_AGENT_SSH_HOST", "mooniex-vps")
REMOTE_DB = os.environ.get(
    "MAC_AGENT_REMOTE_DB", "/home/secretary/runtime/relay_queue.db"
)
REMOTE_SQLITE_USER = os.environ.get("MAC_AGENT_REMOTE_USER", "secretary")
POLL_SECONDS = int(os.environ.get("MAC_AGENT_POLL_SECONDS", "30"))
SSH_TIMEOUT = int(os.environ.get("MAC_AGENT_SSH_TIMEOUT", "20"))
MAX_BATCH = int(os.environ.get("MAC_AGENT_MAX_BATCH", "10"))

# The attribution marker the Contabo side stamps onto every relayed order. An
# entry without it is refused rather than repaired: this marker is the only
# thing telling a human reading a transcript that an order came from the bot
# and not from the CEO's own hands. Silently adding it here would destroy the
# exact signal it exists to carry.
RELAY_PREFIX = "[CEO via SomPong]"

# The secretary's own mailbox identity — SAME values as Contabo's
# runners/relay_mcp_server.py (task-18241f1d), so a letter looks identical
# whichever host relayed it. Two attributions, both non-optional: the body
# prefix above for the human reading the pane, the structured from below for
# the machine. Sender is always the secretary itself — never a C-level role
# (impersonation) and never the CEO (the CEO did not write this letter;
# their secretary did, on their behalf).
SECRETARY_FROM_ROLE = "secretary"
SECRETARY_FROM_SESSION_ID = "sompong"
# Label the wake marker carries: the pane reads "[New message from SomPong]"
# — the secretary's own name, not a C-level's (same rule).
SECRETARY_WAKE_LABEL = "SomPong"

C_LEVEL_ROLES = ("cto", "cfo", "cmo", "cgo")

# Cap on a `read` capture. A pane holds thousands of lines and every one of them
# is paid for twice — across the wire, then into the model reading it back.
MAX_READ_LINES = int(os.environ.get("MAC_AGENT_MAX_READ_LINES", "200"))

# Cap on one entry's `result` TEXT. The Contabo side reads this column back to
# the secretary, so it has to carry whole JSON payloads (a 50-row `terminals`
# snapshot is ~15 KB), not just one-line acks. It was previously hard-coded at
# 500 chars, which silently destroyed every payload longer than an ack — and
# also most of a `read` pane tail. Env-overridable for tighter boxes.
MAX_RESULT_CHARS = int(os.environ.get("MAC_AGENT_MAX_RESULT_CHARS", "20000"))

# Row cap for `terminals`. Dozens of .title files on the Mac make a long list;
# 50 newest-first rows is what fits a phone screen and the queue row. When
# rows fall off the end the result must SAY so — silent truncation would have
# the secretary tell the CEO a session does not exist when it simply dropped.
MAX_TERMINAL_ROWS = int(os.environ.get("MAC_AGENT_MAX_TERMINAL_ROWS", "50"))

# Enumerated `history` modes — an unknown mode fails the entry, exactly like
# an unknown kind. Dispatch here is a list, not a shell.
HISTORY_MODES = ("index", "read")


def _tmux_bin() -> str:
    """Absolute path to tmux.

    launchd hands a process a bare PATH (/usr/bin:/bin:/usr/sbin:/sbin) — it
    does NOT inherit the login shell's. Homebrew installs tmux in
    /opt/homebrew/bin, so a plain "tmux" resolves to nothing under launchd and
    every lookup fails. The dangerous part is what that looked like: sessions
    that plainly existed were reported as "no live cto session on this Mac" —
    a confident wrong answer rather than a missing-tool error.
    """
    override = os.environ.get("MAC_AGENT_TMUX_BIN")
    if override:
        return override
    for candidate in ("/opt/homebrew/bin/tmux", "/usr/local/bin/tmux", "/usr/bin/tmux"):
        if Path(candidate).exists():
            return candidate
    return "tmux"  # last resort; surfaces as a real error rather than a silent miss

_LOGGER = None


def _log():
    global _LOGGER
    if _LOGGER is None:
        _LOGGER = get_logger("mac_agent")
    return _LOGGER


# ---------------------------------------------------------------------------
# Transport — outbound SSH only.
#
# sqlite3 runs on the far end as the owning user (`sudo -u`), because the queue
# file is mode 600 under /home/secretary. Each call is a single statement:
# SQLite makes one statement atomic, so a concurrent writer on the Contabo side
# cannot hand back a half-written row, and we never hold a transaction open
# across the network.
# ---------------------------------------------------------------------------

def _ssh_sqlite(sql: str) -> tuple[bool, str]:
    """Run one SQL statement on the remote queue. Returns (ok, output).

    Never raises. An unreachable VPS is expected (the Mac changes networks, the
    box reboots); crashing here would have launchd restart the agent in a tight
    loop, which is worse than waiting for the next tick.
    """
    remote = (
        f"sudo -u {shlex.quote(REMOTE_SQLITE_USER)} "
        f"sqlite3 {shlex.quote(REMOTE_DB)} {shlex.quote(sql)}"
    )
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={SSH_TIMEOUT}",
             SSH_HOST, remote],
            capture_output=True, text=True, timeout=SSH_TIMEOUT + 15,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"ssh failed: {e}"
    if r.returncode != 0:
        return False, (r.stderr or "").strip()[:400]
    return True, r.stdout


def fetch_pending() -> list[dict]:
    """Pending rows, oldest first. Returns [] on failure — and logs it, because
    the caller cannot tell "nothing to do" from "could not ask"."""
    sql = (
        "SELECT id, kind, target_role, payload FROM relay_queue "
        f"WHERE status = 'pending' ORDER BY id LIMIT {MAX_BATCH};"
    )
    ok, out = _ssh_sqlite(sql)
    if not ok:
        _log().warning("queue unreachable: %s", out)
        return []
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 3)
        if len(parts) != 4:
            _log().warning("skipping malformed queue row: %r", line[:120])
            continue
        rid, kind, role, payload = parts
        try:
            rows.append({
                "id": int(rid), "kind": kind, "target_role": role,
                "payload": json.loads(payload) if payload else {},
            })
        except (ValueError, json.JSONDecodeError) as e:
            _log().warning("skipping unparseable row id=%s: %s", rid, e)
    return rows


def mark(entry_id: int, status: str, result: str) -> bool:
    """Close a queue entry. Every entry ends 'done' or 'failed' WITH a reason —
    one left pending forever is invisible work nobody will chase."""
    safe = result.replace("'", "''")[:MAX_RESULT_CHARS]
    sql = (
        f"UPDATE relay_queue SET status = '{status}', "
        f"done_at = datetime('now'), result = '{safe}' WHERE id = {int(entry_id)};"
    )
    ok, out = _ssh_sqlite(sql)
    if not ok:
        _log().error("could not mark entry %s as %s: %s", entry_id, status, out)
    return ok


# ---------------------------------------------------------------------------
# Executor — the security core.
#
# The queue is written by a bot that reads Telegram. Treat every field as
# hostile even though the Telegram side is allowlisted: that allowlist is one
# config edit away from being wrong, and this is the second wall.
#
# No queue content is ever concatenated into a shell string. Each kind maps to
# a fixed local call with typed arguments.
# ---------------------------------------------------------------------------

def _valid_role(role) -> bool:
    return isinstance(role, str) and role.lower() in C_LEVEL_ROLES


def find_session_for_role(role: str) -> str | None:
    """First live tmux session named <role>-<something>.

    READ path only (task-02d0e863): reading an arbitrary pane of the role
    is a harmless, read-only act, so "whichever cto-* pane" is an
    acceptable answer there. Sending is not harmless — do_relay addresses
    the PRIMARY session via the <role>-active pointer instead (see
    _live_session), because first-match on this Mac picks whichever of
    the several live cto-* sessions tmux happens to list first. The
    asymmetry is deliberate; do not "simplify" them back together.
    """
    try:
        r = subprocess.run([_tmux_bin(), "ls", "-F", "#{session_name}"],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    prefix = role.lower() + "-"
    for name in r.stdout.split():
        if name.lower().startswith(prefix):
            return name
    return None


def _live_session(name: str) -> bool:
    """Is tmux session `name` live right now?

    Uses the absolute-path _tmux_bin(), not tools/tmux_session.py's plain
    "tmux": this agent runs under launchd, whose bare PATH does not carry
    Homebrew, and a liveness check that cannot find tmux must not turn
    into "no live session" — the confident-wrong-answer failure
    _tmux_bin() itself documents.
    """
    try:
        r = subprocess.run([_tmux_bin(), "has-session", "-t", name],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def _resolve_pointer_session(role: str) -> tuple[str | None, str | None]:
    """Resolve the PRIMARY <role> session — the one state/locks/<role>-active
    names (same resolution tools/send_to_cxo.py uses for its own sends, with
    the .winid fallback) — never "the first tmux session whose name starts
    with <role>-". This Mac runs several cto-* sessions at once and
    first-match is whichever tmux lists first, so a CEO order could land in
    a session the CEO was not talking to (task-02d0e863 D1a).

    Returns (session_id, None) on success, or (None, reason) on failure.
    Includes the race cross-check: if the pointer moved between the two
    reads, neither id is trustworthy — fail rather than guess. Shared by
    do_relay and do_terminal_open (task-2a135187 D3) — one resolution, not
    two copies that could drift.
    """
    session_id = _active_session_id(role)
    if not session_id:
        return None, (f"no active {role} session on this Mac "
                       f"(state/locks/{role}-active absent or empty)")
    expected = f"{role}-{session_id}"
    if not _live_session(expected):
        return None, (f"{role}-active names {expected} but that tmux session "
                       f"is not live -- pointer and tmux disagree; refusing "
                       f"to guess which session the CEO means")
    if _active_session_id(role) != session_id:
        return None, (f"{role}-active moved mid-relay (was {session_id}); "
                       f"refusing to guess which session the CEO means")
    return session_id, None


def do_relay(role: str, payload: dict) -> tuple[bool, str]:
    if not _valid_role(role):
        return False, f"unknown role {role!r}"
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return False, "empty or non-string message"
    if RELAY_PREFIX not in message:
        return False, f"missing {RELAY_PREFIX} attribution; refusing to deliver"
    role = role.lower()

    # Mirrors Contabo's relay_to_session: address the PRIMARY <role>
    # session via the same pointer resolution + race cross-check
    # _resolve_pointer_session documents, never "the first tmux session
    # whose name starts with <role>-".
    session_id, err = _resolve_pointer_session(role)
    if err:
        return False, err
    expected = f"{role}-{session_id}"

    # Authorization: the secretary is not a C-level, so the C-level
    # identity chain is the wrong gate. authorize() carries an explicit
    # secretary CEO-proxy entry (tools/send_to_cxo.py) — SomPong is never
    # dressed up as a C-level to pass it; impersonation is the one thing
    # that guard exists to prevent. A PermissionError propagates to
    # tick()'s catch and fails the entry with its reason.
    authorize(
        Identity("secretary", SECRETARY_FROM_ROLE, SECRETARY_FROM_SESSION_ID),
        role, session_id, spawning=False,
    )

    # Delivery IS a letter on disk, in the recipient's mailbox. The body
    # never travels by keystroke: tmux send-keys' Enter can be swallowed
    # (GH #70), leaving the order unsubmitted in the recipient's composer
    # while the queue entry said done — SomPong telling the CEO "ส่งแล้วครับ"
    # for a message nobody received. Mirrors Contabo exactly
    # (task-18241f1d), same mailbox, same secretary identity.
    try:
        letter_path = mailbox.send(
            role, session_id, message,
            SECRETARY_FROM_ROLE, SECRETARY_FROM_SESSION_ID,
        )
        letter_on_disk = letter_path.is_file()
    except Exception as e:
        return False, f"mailbox write failed: {e}"
    if not letter_on_disk:
        # The write "succeeded" but there is nothing on disk — report the
        # effect, not the act. Never "delivered".
        return False, f"letter not on disk after write: {letter_path}"
    # Best-effort wake only: types the short content-free marker via the
    # org's ONE wake implementation (tools/send_to_cxo.py), never the
    # body. attempt_wake swallows every failure internally; this
    # caller-side wrap is the other half of the same rule — even a wake
    # that somehow raises can never turn a written letter into a failed
    # entry, because the letter is drained on the recipient's next prompt
    # either way.
    try:
        attempt_wake(role, session_id, SECRETARY_WAKE_LABEL)
    except Exception as e:
        _log().warning("wake failed for %s (letter already on disk): %s",
                       expected, e)
    return True, f"delivered to {expected}: letter {letter_path}"


def do_spawn(role: str, payload: dict) -> tuple[bool, str]:
    if not _valid_role(role):
        return False, f"unknown role {role!r}"
    role = role.lower()
    script = ROOT / "scripts" / ("spawn-cto.sh" if role == "cto" else "spawn-cxo.sh")
    if not script.exists():
        return False, f"missing {script.name}"
    cmd = [str(script)] if role == "cto" else [str(script), "--role", role]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"spawn failed: {e}"
    if r.returncode != 0:
        return False, f"spawn exit {r.returncode}: {(r.stderr or '').strip()[:200]}"
    return True, f"spawned {role} on mac"


def do_read(role: str, payload: dict) -> tuple[bool, str]:
    """Capture the tail of a Mac C-level pane and hand it back as the entry's
    result, so read_session(host="mac") on Contabo can return it.

    Read-only: nothing is typed into the session. What comes back is a pane
    snapshot, not a reply — the Contabo side labels it that way, and must keep
    doing so.
    """
    if not _valid_role(role):
        return False, f"unknown role {role!r}"
    lines = payload.get("lines", 40)
    if not isinstance(lines, int) or lines < 1:
        return False, "lines must be a positive integer"
    lines = min(lines, MAX_READ_LINES)

    target = find_session_for_role(role)
    if not target:
        return False, f"no live {role} session on this Mac"

    try:
        r = subprocess.run([_tmux_bin(), "capture-pane", "-p", "-t", target],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"capture failed: {e}"
    if r.returncode != 0:
        return False, f"capture exit {r.returncode}"

    kept = r.stdout.splitlines()
    while kept and not kept[-1].strip():
        kept.pop()
    return True, f"[{target}] " + "\n".join(kept[-lines:])


def do_terminals(role: str, payload: dict) -> tuple[bool, str]:
    """kind=terminals — read-only snapshot of THIS Mac's C-level sessions.

    `role` is ignored: the question is host-wide ("what is open on the Mac"),
    not per-role. Payload {"include_closed": bool}. Result is JSON for the
    Contabo side to render, rows capped at MAX_TERMINAL_ROWS, newest first,
    with dropped rows said out loud.
    """
    include_closed = payload.get("include_closed", False)
    if not isinstance(include_closed, bool):
        return False, "include_closed must be a boolean"
    rows = list_sessions(include_closed=include_closed)
    kept = rows[:MAX_TERMINAL_ROWS]
    dropped = len(rows) - len(kept)
    out = {
        "host": detect_host(),
        "total_sessions": len(rows),
        "returned": len(kept),
        "dropped": dropped,
        "sessions": kept,
    }
    if dropped:
        out["note"] = f"{dropped} older session(s) not returned (row cap " \
                      f"{MAX_TERMINAL_ROWS}) — ask with a narrower filter"
    return True, json.dumps(out, ensure_ascii=False)


def do_history(role: str, payload: dict) -> tuple[bool, str]:
    """kind=history — index what saved history exists, or read one file's
    tail. Read-only (tools/org_inspector.py enforces the allowlists).

      mode=index → {"session_id": str|None}
      mode=read  → {"path": str, "tail_lines": int}

    An unknown mode fails the entry, same contract as an unknown kind. A
    history_read refusal (outside ALLOWED_HISTORY_ROOTS, bad extension, …)
    also fails the entry — the Contabo side must see a rejection as a
    rejection, never as success-with-a-body.
    """
    mode = payload.get("mode")
    if mode not in HISTORY_MODES:
        return False, f"unknown mode {mode!r}. Known: {', '.join(HISTORY_MODES)}"
    if mode == "index":
        sid = payload.get("session_id")
        if sid is not None and not isinstance(sid, str):
            return False, "session_id must be a string when given"
        return True, json.dumps(history_index(sid), ensure_ascii=False)

    path = payload.get("path")
    if not isinstance(path, str) or not path.strip():
        return False, "path is required for mode=read"
    tail_lines = payload.get("tail_lines", 80)
    if isinstance(tail_lines, bool) or not isinstance(tail_lines, int) or tail_lines < 1:
        return False, "tail_lines must be a positive integer"
    out = history_read(path, tail_lines=tail_lines)
    if out.get("status") == "rejected":
        return False, f"read rejected: {out.get('reason')}"
    return True, json.dumps(out, ensure_ascii=False)


def do_terminal_open(role: str, payload: dict) -> tuple[bool, str]:
    """kind=terminal_open -- reattach an iTerm window on this Mac to an
    already-running C-level tmux session, via scripts/terminal-open.sh
    (task-2a135187 D3). Mac-only and spawns nothing (see that script's own
    header) -- this never starts a new session, only opens a window onto
    one that already exists.

    payload: {"session_id": str | None}. When session_id is omitted,
    resolve the <role>-active pointer via the SAME primary-session
    resolution do_relay uses (_resolve_pointer_session), including its
    race guard -- a pointer that disagrees with tmux is refused, never
    guessed. When session_id IS given, it names an explicit session
    directly: checked live, never redirected to the primary.
    """
    if not _valid_role(role):
        return False, f"unknown role {role!r}"
    role = role.lower()
    session_id = payload.get("session_id")
    if session_id is not None and not isinstance(session_id, str):
        return False, "session_id must be a string when given"

    if session_id:
        target = f"{role}-{session_id}"
        if not _live_session(target):
            return False, f"no live tmux session named {target}"
    else:
        session_id, err = _resolve_pointer_session(role)
        if err:
            return False, err
        target = f"{role}-{session_id}"

    script = ROOT / "scripts" / "terminal-open.sh"
    if not script.exists():
        return False, f"missing {script.name}"
    try:
        r = subprocess.run(["bash", str(script), target],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"terminal-open failed: {e}"
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()[:300]
        return False, f"terminal-open exit {r.returncode}: {detail}"
    return True, f"opened iTerm window -> {target}"


# Explicit dispatch table. An unknown kind is a failure, never a fallback
# execution — that is the whole difference between an enumerated action list
# and a remote shell.
HANDLERS = {
    "relay": do_relay,
    "spawn": do_spawn,
    "read": do_read,
    "terminals": do_terminals,
    "history": do_history,
    "terminal_open": do_terminal_open,
}


def process(entry: dict) -> tuple[bool, str]:
    handler = HANDLERS.get(entry.get("kind"))
    if handler is None:
        return False, f"unknown kind {entry.get('kind')!r}"
    payload = entry.get("payload")
    if not isinstance(payload, dict):
        return False, "payload is not an object"
    return handler(entry.get("target_role", ""), payload)


def tick() -> int:
    """One drain pass. Returns how many entries were closed."""
    closed = 0
    for entry in fetch_pending():
        try:
            ok, detail = process(entry)
        except Exception as e:  # one bad entry must never kill the loop
            ok, detail = False, f"handler raised: {e}"
        mark(entry["id"], "done" if ok else "failed", detail)
        _log().info("entry %s (%s/%s) -> %s: %s", entry["id"], entry.get("kind"),
                    entry.get("target_role"), "done" if ok else "failed", detail)
        closed += 1
    return closed


def main() -> None:
    once = "--once" in sys.argv
    # attempt_wake (tools/send_to_cxo.py) types the wake marker with a bare
    # "tmux"; under launchd that resolves to nothing on the bare PATH, and
    # the wake would be silently skipped every tick. _tmux_bin() knows
    # where tmux really lives — put its directory on OUR path so the nudge
    # can fire. Delivery never depends on this (a failed wake cannot fail
    # an entry); it just keeps the wake working in the launchd deployment.
    bin_path = Path(_tmux_bin())
    if bin_path.is_absolute() and bin_path.parent.is_dir():
        current = os.environ.get("PATH", "")
        if str(bin_path.parent) not in current.split(":"):
            os.environ["PATH"] = f"{bin_path.parent}:{current}"
    _log().info("mac_agent starting (host=%s db=%s poll=%ss once=%s)",
                SSH_HOST, REMOTE_DB, POLL_SECONDS, once)
    while True:
        try:
            tick()
        except Exception as e:
            # Sleeping through a bad tick beats launchd restarting us forever.
            _log().error("tick failed: %s", e)
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()

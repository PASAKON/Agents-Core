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
    kind: 'relay' | 'spawn'      status: 'pending' | 'done' | 'failed'

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

from lib.logger import get_logger  # noqa: E402

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

C_LEVEL_ROLES = ("cto", "cfo", "cmo", "cgo")

# Cap on a `read` capture. A pane holds thousands of lines and every one of them
# is paid for twice — across the wire, then into the model reading it back.
MAX_READ_LINES = int(os.environ.get("MAC_AGENT_MAX_READ_LINES", "200"))

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
    safe = result.replace("'", "''")[:500]
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
    """First live tmux session named <role>-<something>."""
    try:
        r = subprocess.run(["tmux", "ls", "-F", "#{session_name}"],
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


def do_relay(role: str, payload: dict) -> tuple[bool, str]:
    if not _valid_role(role):
        return False, f"unknown role {role!r}"
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return False, "empty or non-string message"
    if RELAY_PREFIX not in message:
        return False, f"missing {RELAY_PREFIX} attribution; refusing to deliver"

    target = find_session_for_role(role)
    if not target:
        return False, f"no live {role} session on this Mac"

    try:
        # Fixed argv. `message` is ONE argument — never part of a command
        # string — so shell metacharacters in it are inert text.
        subprocess.run(
            ["tmux", "send-keys", "-t", target, message, "Enter"],
            check=True, capture_output=True, text=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"tmux send failed: {e}"
    return True, f"delivered to {target}"


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
        r = subprocess.run(["tmux", "capture-pane", "-p", "-t", target],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"capture failed: {e}"
    if r.returncode != 0:
        return False, f"capture exit {r.returncode}"

    kept = r.stdout.splitlines()
    while kept and not kept[-1].strip():
        kept.pop()
    return True, f"[{target}] " + "\n".join(kept[-lines:])


# Explicit dispatch table. An unknown kind is a failure, never a fallback
# execution — that is the whole difference between an enumerated action list
# and a remote shell.
HANDLERS = {"relay": do_relay, "spawn": do_spawn, "read": do_read}


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

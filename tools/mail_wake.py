"""Wake the session that waits on a mailbox letter, the moment a card ends.

The Console writes a Run Inbox result letter into `state/inbox/<box>/` when a card
ends (`<box>` = the card's `requester.session`, the mailbox name `<role>-<id>`:
cto-fresh, project_head-b2ff34d1, cmo-e785343f, dev-task-8669cf28) but never woke
the pane, so an idle session saw the CEO's answer only with the CEO's next chat
prompt (Q-20261029-2106-b3b3, Q-20261029-2021-4e31, Q-20261029-2038-68c3). The
Console now calls this once per box:

    python -m tools.mail_wake <box> [--label RUN-INBOX]

It wakes the box only when `state/inbox/<box>/` holds at least one unread `*.json`
letter, read no-follow (`lib.mailbox._BoxView`: this runs as root over boxes other
users can write, so a symlinked box or letter must never be followed).

  * `project_head-<sid>` while Claude is spent: not the pane, see "Claude is spent"
    below. Reason "claude spent: ran AGY brain".
  * `<role>-<sid>` with role a C-level or `project_head`: `send_to_cxo.attempt_wake`,
    at once. No debounce, because the session is waiting on that answer. Needs the
    venv's python (lib.config reads policies/agents.yaml) but not ORG_DB_URL.
  * `<role>-task-<8 hex>` (a worker): the tmux session `wd-<8 hex>`, which
    `tools/delegate.py` names with `tmux_session.session_name_for` and
    `tools/send_to_worker.py` wakes through the same `agent_transport.attempt_wake`.
    Derived from the box name, so no hub lookup: a task on another backend has no
    such session and is simply not woken.
  * Anything else: no wake.

Best effort, like `attempt_wake`: one JSON line {"box", "woke", "reason"}, exit 0
even when nothing could be woken, exit 2 only for a usage error (a missing box or a
name that is not one path segment). Never raises.

Claude is spent (CEO 4 Nov 2026, Q-20261104-0251-39de: "คงเดิม (Opus) ทำแค่ AGY ทำต่อ")
------------------------------------------------------------------------------------
A Project Head on the AGY brain (host flag ORG_PH_AGY_BRAIN, scripts/cxo-claude.sh) is a
Haiku shell in tmux whose brain is `tools/ph_brain.py turn` on AGY. The shell needs
Claude to take a turn, so once Claude Pro is spent a letter to the PH (a worker report,
an owner relay, a card answer) wakes nobody and the AGY worker chain stops. Both wakes
that reach a PH call `handle_ph(sid)` before they type into its pane: this module's
`_wake` (the Console, owner_relay, escalation_watch, portfolio_watch) and
`tools/send_to_cto._attempt_wake` (a worker's report). C-level boxes are unchanged.

`handle_ph` returns None when it does not apply and the caller wakes the pane as before:
Claude not spent (`lib.claude_quota.claude_spent`, kill switch
`state/claude_out_fallback.off`), the host not on the AGY brain, no live PH record
(cxo-claude.sh renames `.project` and `.spawned_by` to `.parked` when the session ends),
or not POSIX. Otherwise it starts a detached runner (setsid; the caller returns at once),
`python -m tools.mail_wake project_head-<sid> --run-fallback`, with its output in
`state/ph-brain/fallback-<sid>.log`, and answers {"woke": True, "reason": REASON}.

The runner makes up to MAX_TURNS passes while letters keep arriving. A pass, under a
flock on `state/ph-brain/fallback-<sid>.lock` (one run per PH; a second runner exits and
the holder's next pass takes the new letter):
  1. drains the PH's unread letters no-follow (`mailbox._drain_envelope`: they move to
     `read/` and stay 7 days, so the full text survives the 4000-character cut);
  2. runs `tools/ph_brain.py turn --ph --project --lane --owner --message=<letters>`
     through `scripts/hub/org-python.sh`, as roles/ph_shell.md rule 2 does;
  3. runs the commands of the brain's reply that roles/ph_shell.md rule 4 allows, and
     only those: `ph_brain.py delegate|status` and `session_charter set`. The PH's own id
     is forced into `--ph`, nothing goes through a shell, and a command-looking line that
     is not on that list, or has a shell operator, is written to the log and not run.
If the brain does not answer, the letters go back into the box as one letter, so the
Claude shell still sees them when Claude is back.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import claude_quota, mailbox, org_flags  # noqa: E402
from lib.roles import (PH_ROLE, c_level_roles, ph_lane_refusal,  # noqa: E402
                       ph_project_refusal)
from tools import live_sessions  # noqa: E402

try:
    import fcntl
except ImportError:          # Windows: no flock and no setsid; the caller wakes the pane
    fcntl = None

DEFAULT_LABEL = "RUN-INBOX"
# One path segment: the same rule the hub puts on requester.session.
BOX_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
# `<worker role>-<task id>`; the role is whatever WORKER_ROLE holds ("dev" by default).
WORKER_BOX_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*-(task-[0-9a-f]{8})")

ROOT = mailbox.ROOT          # the hub checkout: the PH's letters, locks and brain live here
LOCKS_DIR = ROOT / "state" / "locks"
FALLBACK_DIR = ROOT / "state" / "ph-brain"

FALLBACK_REASON = "claude spent: ran AGY brain"
MESSAGE_MAX = 4000           # characters of letters handed to one brain turn
MAX_TURNS = 3                # passes of one runner while letters keep arriving
MAX_COMMANDS = 5             # plan commands run per turn
TURN_TIMEOUT_S = 1200        # ph_brain tries up to 4 models of 240 s each
COMMAND_TIMEOUT_S = 600
MAX_STATEMENT_LINES = 200

PH_SID_RE = re.compile(r"[0-9a-f]{8}")
OWNER_SID_RE = re.compile(r"[0-9a-f]{8}|fresh")      # the same rule as tools/owner_relay.py
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _result(box: str, woke: bool, reason: str) -> dict:
    return {"box": box, "woke": woke, "reason": reason}


def _has_unread(box_path: Path) -> bool:
    with mailbox._BoxView(box_path) as view:
        return view.ok and next(view.letters(), None) is not None


def wake(box: str, label: str = DEFAULT_LABEL) -> dict:
    """Wake `box`'s session if it has an unread letter. Never raises."""
    try:
        return _wake(box, label)
    except Exception as e:  # best effort: a broken wake must never fail the Console's call
        return _result(box, False, f"error: {type(e).__name__}")


def _wake(box: str, label: str) -> dict:
    if not BOX_RE.fullmatch(box):
        return _result(box, False, "invalid box name")
    box_path = mailbox.INBOX_ROOT / box
    if box_path.is_symlink():
        return _result(box, False, "box is a symlink, refused")
    if not _has_unread(box_path):
        return _result(box, False, "no unread letter")

    role, _, sid = box.partition("-")
    if sid and role == PH_ROLE and (fallback := handle_ph(sid)) is not None:
        return _result(box, fallback["woke"], fallback["reason"])
    if sid and (role in c_level_roles() or role == PH_ROLE):
        from tools import send_to_cxo  # lazy: a refusal above never pays for the import

        woke = send_to_cxo.attempt_wake(role, sid, label)
    elif (m := WORKER_BOX_RE.fullmatch(box)):
        from tools import agent_transport, tmux_session

        woke = agent_transport.attempt_wake(
            tmux_session.session_name_for(m.group(1)), label, "mail_wake")
    else:
        return _result(box, False, "not a session box")
    return _result(box, bool(woke), "woke" if woke else "no live session reached")


# ============================================================================
# Claude is spent: a Project Head's letters go to its AGY brain (module docstring)
# ============================================================================

def _log(msg: str) -> None:
    """One line to the runner's stdout, which `_spawn_runner` points at the PH's fallback log."""
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S%z')}] {msg}", flush=True)


def _ph_record(sid: str) -> dict | None:
    """{project, lane, owner} of a live Project Head from its lock records, else None.
    The `.spawned_by` reads "cxo:<lane>:<owner sid>"; the owner is the C-level box
    `<lane>-<owner sid>`, as in tools/owner_relay.py."""
    project = live_sessions.read_lock(LOCKS_DIR / f"{PH_ROLE}-{sid}.project")
    parts = live_sessions.read_lock(LOCKS_DIR / f"{PH_ROLE}-{sid}.spawned_by").split(":")
    if (ph_project_refusal(project) or len(parts) != 3 or parts[0] != "cxo"
            or ph_lane_refusal(parts[1]) or not OWNER_SID_RE.fullmatch(parts[2])):
        return None
    return {"project": project, "lane": parts[1], "owner": f"{parts[1]}-{parts[2]}"}


def _spawn_runner(sid: str) -> None:
    """Start the runner detached (setsid), its output appended to the PH's fallback log."""
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(FALLBACK_DIR / f"fallback-{sid}.log", os.O_WRONLY | os.O_CREAT | os.O_APPEND | _NOFOLLOW, 0o600)
    try:
        subprocess.Popen([sys.executable, "-m", "tools.mail_wake", f"{PH_ROLE}-{sid}", "--run-fallback"],
                         cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=fd, stderr=fd,
                         start_new_session=True, close_fds=True)
    finally:
        os.close(fd)


def handle_ph(sid: str) -> dict | None:
    """The fallback for a wake aimed at Project Head `sid`. None: it does not apply, wake the
    pane as before. Otherwise {"woke": True, "reason": FALLBACK_REASON} and the pane is left
    alone. Never raises: a broken fallback must cost the caller nothing it had."""
    try:
        if (fcntl is None or not PH_SID_RE.fullmatch(sid or "") or not claude_quota.claude_spent()
                or not org_flags.on("ORG_PH_AGY_BRAIN") or _ph_record(sid) is None):
            return None
        _spawn_runner(sid)
        return {"woke": True, "reason": FALLBACK_REASON}
    except Exception:
        return None


def _py(*args: str) -> list[str]:
    """`bash scripts/hub/org-python.sh <args>`: the venv python with the task ledger reachable."""
    return ["bash", "scripts/hub/org-python.sh", *args]


def _run_cmd(argv: list[str], *, env: dict | None = None, timeout: int) -> tuple[int, str]:
    """(exit code, stdout) of one command in the hub checkout; stderr goes to the log. The
    only place the runner starts a process, so a test replaces it."""
    try:
        proc = subprocess.run(argv, cwd=str(ROOT), env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, ""
    except OSError as e:
        _log(f"cannot start {argv[:3]}: {type(e).__name__}")
        return 127, ""
    if proc.stderr.strip():
        _log(f"stderr: {proc.stderr.strip()[:2000]}")
    return proc.returncode, proc.stdout


@contextlib.contextmanager
def _flock(sid: str):
    """Yield True holding the PH's run lock, or False when another runner holds it."""
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    fd = os.open(FALLBACK_DIR / f"fallback-{sid}.lock", os.O_RDWR | os.O_CREAT | _NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        yield True
    finally:
        os.close(fd)            # closing the descriptor releases the lock


def format_letters(letters: list[dict], sid: str) -> str:
    """The letters as one message for the brain, cut at MESSAGE_MAX characters."""
    blocks = []
    for lt in letters:
        frm = lt.get("from") if isinstance(lt.get("from"), dict) else {}
        head = " ".join(f"[{lt.get('id', '?')}] {str(lt.get('kind') or 'message').upper()} from "
                        f"{frm.get('role', '?')} {frm.get('session_id', '?')} · {lt.get('sent_at', '')}".split())
        blocks.append(f"{head}\n{lt.get('body', '')}")
    text = "\n\n".join(blocks)
    if len(text) <= MESSAGE_MAX:
        return text
    note = f"\n…[cut at {MESSAGE_MAX} chars; the full letters are in state/inbox/{PH_ROLE}-{sid}/read/]"
    return text[:MESSAGE_MAX - len(note)] + note


def brain_argv(sid: str, rec: dict, message: str) -> list[str]:
    # `--message=` and not `--message <text>`: a letter that starts with "-" is not an option.
    return _py("tools/ph_brain.py", "turn", "--ph", sid, "--project", rec["project"],
               "--lane", rec["lane"], "--owner", rec["owner"], f"--message={message}")


# --- the commands roles/ph_shell.md rule 4 allows ---------------------------------------
_LEAD_RE = re.compile(r"^(?:\s|>|\*|`|-(?=\s)|\$(?=\s)|\d+[.)](?=\s))*")      # bullet, prompt, fence
_START_RE = re.compile(
    r"(?:bash\s+\S*org-python\.sh\s+|\S*python3?\s+)?"
    r"(?:tools/ph_brain\.py\s+(?P<sub>delegate|status)|-m\s+tools\.session_charter\s+(?P<charter>set))(?=[\s;&|<>()]|$)")
_VAR_RE = re.compile(r"\$(?:\{(CXO_SESSION_ID|ORG_PH_PROJECT|ORG_PH_LANE)\}|(CXO_SESSION_ID|ORG_PH_PROJECT|ORG_PH_LANE)\b)")
_OPERATORS = set("();<>|&")


def _unclosed(stmt: str) -> bool:
    try:
        shlex.split(stmt)
    except ValueError:
        return True
    return False


def _statements(reply: str) -> list[str]:
    """Each line of the reply that starts an allowed command, with the lines it continues
    onto (a trailing backslash, or a quote still open) joined to it."""
    lines, out, i = reply.splitlines(), [], 0
    while i < len(lines):
        first = _LEAD_RE.sub("", lines[i]).rstrip().rstrip("`")
        i += 1
        if not _START_RE.match(first):
            continue
        stmt, used = first, 1
        while i < len(lines) and used < MAX_STATEMENT_LINES and (stmt.endswith("\\") or _unclosed(stmt)):
            stmt = (stmt[:-1].rstrip() + " " if stmt.endswith("\\") else stmt + "\n") + lines[i].rstrip()
            i, used = i + 1, used + 1
        out.append(stmt.rstrip().rstrip("`"))
    return out


def plan_commands(reply: str, sid: str, rec: dict) -> tuple[list[list[str]], list[str]]:
    """(argv lists to run through org-python.sh, reasons a command-looking line was not run).
    Only `tools/ph_brain.py delegate|status` and `-m tools.session_charter set`; `--ph` is
    this PH's id or is added; $CXO_SESSION_ID, $ORG_PH_PROJECT and $ORG_PH_LANE are filled in
    as the PH shell's environment would; a shell operator outside quotes refuses the line."""
    values = {"CXO_SESSION_ID": sid, "ORG_PH_PROJECT": rec["project"], "ORG_PH_LANE": rec["lane"]}
    run, skipped = [], []
    for stmt in _statements(reply or ""):
        m = _START_RE.match(stmt)
        label = " ".join(stmt.split())[:100]
        try:
            lex = shlex.shlex(stmt[m.end():], posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            tokens = [_VAR_RE.sub(lambda v: values[v.group(1) or v.group(2)], t) for t in lex]
        except ValueError as e:
            skipped.append(f"{label}: {e}")
            continue
        if any(set(t) <= _OPERATORS for t in tokens):
            skipped.append(f"{label}: shell operator")
            continue
        if m.group("charter"):
            argv = ["-m", "tools.session_charter", "set", *tokens]
        else:
            own = [t.split("=", 1)[1] if t.startswith("--ph=") else tokens[k + 1]
                   for k, t in enumerate(tokens) if t.startswith("--ph=") or (t == "--ph" and k + 1 < len(tokens))]
            if any(v != sid for v in own):
                skipped.append(f"{label}: --ph is not this PH ({sid})")
                continue
            argv = ["tools/ph_brain.py", m.group("sub"), *tokens, *([] if own else ["--ph", sid])]
        if len(run) >= MAX_COMMANDS:
            skipped.append(f"{label}: over {MAX_COMMANDS} commands in one turn")
            continue
        run.append(argv)
    return run, skipped


def _run_plan(sid: str, rec: dict, reply: str) -> None:
    run, skipped = plan_commands(reply, sid, rec)
    for why in skipped:
        _log(f"plan command not run: {why}")
    # The PH shell's own identity, so session_charter and the delegate's owner are the PH's.
    env = {**os.environ, "CXO_ROLE": PH_ROLE, "CXO_SESSION_ID": sid,
           "ORG_PH_PROJECT": rec["project"], "ORG_PH_LANE": rec["lane"]}
    env.pop("CTO_SESSION_ID", None)
    for argv in run:
        rc, out = _run_cmd(_py(*argv), env=env, timeout=COMMAND_TIMEOUT_S)
        _log(f"plan command rc={rc}: {shlex.join(argv)[:300]}\n{out.strip()[:2000]}")


def _requeue(sid: str, message: str) -> None:
    """The brain did not answer: give the letters back to the box as one letter."""
    mailbox.send(PH_ROLE, sid, "[claude-out fallback: the AGY brain did not answer these; "
                 "shown again]\n" + message, "hub", "claude-out")


def _fallback_pass(sid: str) -> str:
    """One locked pass: drain, one brain turn, the allowed plan commands.
    Returns busy | no-record | idle | failed | ok."""
    rec = _ph_record(sid)
    if rec is None:
        _log(f"PH {sid} has no live project record; nothing run")
        return "no-record"
    with _flock(sid) as got:
        if not got:
            _log(f"another runner holds PH {sid}; its next pass takes the new letters")
            return "busy"
        # No-follow, and read/ keeps a copy: this runs as root over a box other users can write.
        letters = mailbox._drain_envelope(PH_ROLE, sid, None)
        if not letters:
            return "idle"
        message = format_letters(letters, sid)
        _log(f"PH {sid}: {len(letters)} letter(s), {len(message)} chars; Claude is spent, AGY brain turn")
        rc, reply = _run_cmd(brain_argv(sid, rec, message), timeout=TURN_TIMEOUT_S)
        if rc != 0:
            _log(f"brain turn failed rc={rc}; letters put back in the box")
            _requeue(sid, message)
            return "failed"
        _log(f"brain reply:\n{reply.strip()}")
        _run_plan(sid, rec, reply)
        return "ok"


def run_fallback(sid: str) -> str:
    """The detached runner: passes while letters keep arriving. Each pass takes the lock and
    releases it before the next, so a letter that came in while a turn ran is not stranded."""
    if fcntl is None or not PH_SID_RE.fullmatch(sid or ""):
        raise ValueError(f"cannot run the fallback for PH {sid!r} here")
    turns = 0
    for _ in range(MAX_TURNS):
        outcome = _fallback_pass(sid)
        if outcome != "ok":
            return "ok" if outcome == "idle" and turns else outcome    # worked, then nothing was left
        turns += 1
    return "capped"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m tools.mail_wake", description=__doc__.split("\n")[0])
    p.add_argument("box", help="mailbox name <role>-<id>, as in the card's requester.session")
    p.add_argument("--label", default=DEFAULT_LABEL,
                   help=f"who the wake says it is from (default {DEFAULT_LABEL})")
    p.add_argument("--run-fallback", action="store_true",
                   help="internal: the detached runner handle_ph starts for box project_head-<sid>")
    args = p.parse_args(argv)
    if args.run_fallback:
        role, _, sid = args.box.partition("-")
        try:
            if role != PH_ROLE:
                raise ValueError(f"--run-fallback needs a {PH_ROLE}-<sid> box, not {args.box!r}")
            _log(f"run PH {sid}: {run_fallback(sid)}")
        except Exception as e:      # the log is the only place this runner can report to
            _log(f"run PH {sid}: error {type(e).__name__}: {e}")
            return 1
        return 0
    print(json.dumps(wake(args.box, args.label)))
    return 0 if BOX_RE.fullmatch(args.box) else 2


if __name__ == "__main__":
    sys.exit(main())

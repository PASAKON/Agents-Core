"""CTO (or any owning C-level) -> DEV mailbox: queue a message into the
DEV's inbox, then attempt a best-effort wake.

Task task-2f04a8ca (CEO directive 2026-08-14, "ยกเลิกการส่งแบบที่ต้องใช้
Keyboard ถาวรได้เลย ... ทุกๆ ตำแหน่งในองกรณ์เลย" -- extend the mailbox+wake
pattern `tools/send_to_cxo.py` already proved twice tonight (task-de2cdc15,
task-cf325742) to every worker role's kickoff + mid-task channel, not just
C-level cross-talk). `send()` used to resolve `task["tmux_session"]` and
type into it, falling back to an iTerm AppleScript search that matched a
tab by title substring -- `full_id[:6]` when the full id didn't match
(GH #65: two tasks sharing that 6-char prefix collide, and a message can
land in the WRONG DEV's tab while reporting success to the sender). That
whole tab-matching code path is deleted here, not kept as a fallback --
mirrors `send_to_cxo.py`'s "a fallback that can silently misdeliver is
worse than no fallback" (GH #69's lesson). `send()` now writes the
message into the recipient's `lib.mailbox` box, keyed by (task["role"],
task["id"]) -- the exact, already-unique DB row id, never a name/prefix
match against anything typed into a terminal. Two tasks sharing a 6-char
prefix now resolve to two structurally distinct boxes; GH #65's whole bug
class is gone by construction, not patched.

GH #65 was never actually in the DB-prefix convenience lookup below (the
`task_id LIKE '<prefix>%'` query that lets a human type a short id on the
CLI) -- that's a separate, pre-existing DB-row resolution step that always
terminates in one canonical `task["id"]`, which is what the mailbox key
uses. GH #65 was specifically about the iTerm tab-title fallback, which no
longer exists.

Usage:
    python -m tools.send_to_worker <task_id_or_prefix> "<message>"
    python -m tools.send_to_worker task-161dbcf7 "status check please"

Sender label: resolved from the calling process's env the same way
`send_to_cxo._resolve_sender_role()` does (`CXO_ROLE` -> that C-level's
display name, else "CEO") rather than the old hardcoded "[CTO]:" --
`tasks.owner_role` already lets a CFO/CMO/CGO own a DEV task directly, so
a CFO-delegated kickoff now correctly reads "[CFO]:" instead of lying
"[CTO]:" like it used to.

**Correction (CTO iter-2 review, measured not inferred)**: an earlier
draft of this docstring claimed kickoff depends on the wake pressing
Enter into a composer that `runners/worker_init.py`'s `os.execvpe` had
merely "pre-loaded" with the prompt. That was wrong, and the CTO measured
it directly rather than trusting the inference: a `claude` process
spawned with a positional prompt argv **auto-submits it** -- the composer
is never left waiting for a keypress. Consequence: **DEV kickoff never
depended on the wake/typing step at all** -- a spawned DEV starts working
from argv alone, `_auto_kickoff` (`tools/delegate.py`, not in this
file's touches) is a mid-task nudge layered on top of an already-running
turn, not the thing that starts the first one.

The reachability gap that *is* real sits one caller over: `_send_ping`
in `runners/watchdog.py`, which sends a silent DEV a "status check" at
`PING_AFTER_S` (10 min). Unlike kickoff, that ping has no argv to fall
back on -- if `_attempt_wake()` below can't reach the DEV's pane, the
letter queues (delivery, by this file's own definition, has already
happened) but nothing prompts the DEV to read it before its next turn,
which may be much later or never for an otherwise-idle task. The wake
below reaches a pane only via `task["tmux_session"]`, set by
`tools/delegate.py` exclusively when the owning project's
`spawn_backend: tmux` (`tools/tmux_session.session_name_for()`) --
`config/projects.yaml` now sets that for every default-worker project
except `mooniex-claudesign` (task-2f04a8ca, same iteration; that project
keeps the pre-existing `web_designer`-only tmux/passive-mirror path
documented in `runners/worker_init.py` unchanged, so it stays on
`spawn_backend: iterm`). Before that config change every project spawned
DEVs on the plain iTerm backend and this wake always silently no-op'd.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib import mailbox
from lib.config import display_for, host as get_host
from tools import agent_transport
from tools.agent_transport import (
    _resolve_sender_role,
    _wake_tmux_send,
    current_identity,
)

# Same value as tools.delegate.REMOTE_SSH_TIMEOUT_S -- kept as its own
# constant rather than imported so this module has no import-time
# dependency on tools.delegate (a higher-level orchestration module that
# already imports THIS one, lazily, inside _auto_kickoff).
_REMOTE_SSH_TIMEOUT_S = 30


def _ps_quote(value: str) -> str:
    """Quote `value` as a single PowerShell double-quoted string literal.

    Mirrors tools.delegate._ps_quote exactly (same reason: ssh joins argv
    into ONE command string the remote shell re-parses with its own
    quoting rules, not Python's) -- duplicated rather than imported, see
    the _REMOTE_SSH_TIMEOUT_S note above.
    """
    escaped = value.replace("`", "``").replace('"', '`"').replace("$", "`$")
    return f'"{escaped}"'


def _send_remote(task: dict, message: str, *, from_role: str, from_sid: str,
                 label: str) -> str:
    """Deliver `message` to a non-mac host's DEV via its MAILBOX.md.

    GH #150 (task task-e40fc5a1): a `tmux_session` only ever exists for a
    Mac-spawned DEV -- send()'s old mailbox+tmux-wake path silently no-op'd
    the wake for a remote task while still returning "queued", which read
    as delivered when nothing had reached the box at all. Contract fixed by
    the CEO brief (shared with the paired multi-host task, not renegotiable
    here):

        path:   <worktree root>\\MAILBOX.md   (created on first append)
        format: append-only, one line per message:
                <ISO-8601 UTC> | <from_role>-<from_sid> | <message>
        worker: reads it before every tool call; "STOP" means halt + push
                BLOCKER (roles/_worker_remote.md, the paired task's file --
                not touched here).

    `task["worktree"]` already holds the full remote path once a spawn has
    landed (tools.delegate._spawn_remote writes it verbatim on success) --
    no separate path-derivation helper exists or is needed.

    Written over `ssh <alias> powershell -Command <script>` with the line
    body piped in on stdin (`[Console]::In.ReadToEnd()` on the far side),
    NOT interpolated into the command string -- the remote shell must never
    get a chance to re-parse Thai/quote-bearing message text as script
    (same lesson the tmux load-buffer fix drew the same day this task was
    filed). Confirms delivery by reading the file's own last line back and
    comparing it to what was sent; raises (never returns "queued") on any
    mismatch, ssh failure, or missing worktree -- "delivered" here is a
    verified claim, not an attempt.
    """
    tid = task["id"]
    role = task["role"]
    host_name = task["host"]
    worktree = task.get("worktree")
    if not worktree:
        raise RuntimeError(
            f"remote worktree not present yet for {tid} on {host_name} "
            f"-- retry after spawn"
        )
    host_cfg = get_host(host_name)
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        raise RuntimeError(f"host {host_name!r} has no ssh alias configured")
    if host_cfg.get("os") != "windows":
        raise NotImplementedError(
            f"remote mailbox delivery not wired for os={host_cfg.get('os')!r} "
            f"(only windows/winbox today)"
        )

    mailbox_path = f"{worktree}\\MAILBOX.md"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    clean_message = " ".join(message.splitlines())
    line = f"{ts} | {from_role}-{from_sid} | {clean_message}"

    script = (
        # Confirmed live on winbox (task-e40fc5a1): the raw bytes arriving
        # over ssh's stdin pipe are already correct UTF-8, and
        # InputEncoding decodes them fine -- the mangled-Thai failure was
        # entirely on the way OUT. PowerShell 5.1's default console output
        # codepage (not UTF-8) is what Write-Output/Get-Content's pipeline
        # output gets re-encoded through when stdout is a redirected ssh
        # pipe, silently turning every Thai byte sequence into "?" on its
        # way back to the hub -- this must be set before ANY output below,
        # including ERR_NO_WORKTREE.
        "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false ; "
        f"if (-not (Test-Path {_ps_quote(worktree)})) "
        f"{{ Write-Output 'ERR_NO_WORKTREE'; exit 2 }} ; "
        "[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false ; "
        "$line = [Console]::In.ReadToEnd() ; "
        f"Add-Content -LiteralPath {_ps_quote(mailbox_path)} -Value $line -Encoding UTF8 ; "
        f"Get-Content -LiteralPath {_ps_quote(mailbox_path)} -Tail 1 -Encoding UTF8"
    )
    cmd = ["ssh", ssh_alias, "powershell", "-NoProfile", "-Command", script]

    try:
        r = subprocess.run(
            cmd, input=line, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=_REMOTE_SSH_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"ssh to {host_name} failed: {e}") from e

    out_lines = [ln for ln in (r.stdout or "").splitlines() if ln.strip()]
    if r.returncode == 2 or (out_lines and out_lines[0] == "ERR_NO_WORKTREE"):
        raise RuntimeError(
            f"remote worktree not present yet for {tid} on {host_name} "
            f"-- retry after spawn"
        )
    if r.returncode != 0:
        detail = (r.stderr or r.stdout or "").strip()[:500]
        raise RuntimeError(f"MAILBOX write to {host_name} failed: {detail}")

    readback = out_lines[-1].strip() if out_lines else ""
    if readback != line.strip():
        raise RuntimeError(
            f"MAILBOX write to {host_name} could not be verified -- wrote "
            f"{line!r}, read back {readback!r}"
        )

    return f"delivered to {display_for(role)} ({tid}) on {host_name}: [{label}] : {message}"


def _attempt_wake(tmux_sess: str | None, label: str) -> None:
    """Best-effort attention nudge for the just-delivered letter's DEV.

    Mirrors `send_to_cxo._attempt_wake()`'s isolation guarantee exactly:
    nothing here may raise or change `send()`'s return value. Unlike
    `send_to_cxo`, the target tmux session name is read straight off the
    task row (`task["tmux_session"]`, set by `tools/delegate.py` only for
    `spawn_backend: tmux` projects) rather than derived from
    `session_name.lock_basename()` -- DEV tmux sessions are not named
    `<role>-<task_id>` the way C-level sessions are. As of task-2f04a8ca
    (see module docstring) most projects in `config/projects.yaml` set
    `spawn_backend: tmux`, so this fires for real on those; it stays a
    no-op only for a project still left on `spawn_backend: iterm`
    (currently just `mooniex-claudesign`, to keep its unrelated
    `web_designer` passive-mirror path undisturbed).

    Delegates the actual wrap/log/never-raise nudge to
    `tools.agent_transport.attempt_wake()` (task task-eb0d9863) --
    `send_fn=_wake_tmux_send` is this module's own imported reference,
    resolved in THIS module's globals, so a test that monkeypatches
    `tools.send_to_worker._wake_tmux_send` is still honored.
    """
    agent_transport.attempt_wake(tmux_sess, label, "send_to_worker", send_fn=_wake_tmux_send)


def send(task_id: str, message: str) -> str:
    """Queue `message` into the DEV's mailbox, then attempt a wake.

    Contract: queued/delivered or raised, never "probably" (GH #60's
    contract on this function, kept across the transport swap). Raises
    `ValueError` when `task_id` (or its prefix) matches no row -- the one
    failure mode that still makes sense once "delivered" no longer depends
    on any terminal existing. A mailbox write failure (disk full, permission
    denied) raises whatever `lib.mailbox.send()` raises; there is no
    fallback transport to catch it and retry.

    GH #150 (task task-e40fc5a1): for a task whose `host` is not mac/None,
    `tmux_session` is never set (that column only exists for Mac-spawned
    DEVs), so the mailbox+tmux path below would silently no-op the wake
    while still returning "queued" -- delivered a message to nowhere,
    successfully. Such a task is instead handed to `_send_remote()`, which
    writes into the DEV's MAILBOX.md over ssh and returns "delivered ..."
    only once it has read the line back and confirmed it matches. It raises
    (never returns) on any ssh failure, missing worktree, or verification
    mismatch -- "queued" must never be the return value for a remote task.

    Used by `tools/delegate.py`'s `_auto_kickoff` for the mandatory kickoff
    ping (IRON-RULES §29) and for mid-task review messages. `_auto_kickoff`
    already wraps this call in try/except and warns rather than propagating
    (untouched here -- not in this task's touches), so a raise surfaces
    loudly without blocking the spawn.
    """
    db.init()
    task = db.get_task(task_id)
    if not task:
        from lib.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE id LIKE ? LIMIT 1",
                (f"{task_id}%",),
            ).fetchone()
        if not row:
            raise ValueError(f"no task matching {task_id}")
        task = db.get_task(row[0])

    tid = task["id"]
    role = task["role"]
    sender_identity = current_identity()
    label = _resolve_sender_role()
    from_role = sender_identity.role.lower()
    from_sid = sender_identity.session_id or "ceo"

    host_name = task.get("host") or "mac"
    if host_name != "mac":
        return _send_remote(task, message, from_role=from_role,
                            from_sid=from_sid, label=label)

    mailbox.send(role, tid, message, from_role, from_sid)
    _attempt_wake(task.get("tmux_session"), label)
    return f"queued to {display_for(role)} ({tid}): [{label}] : {message}"


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_worker <task_id_or_prefix> "<message>"',
              file=sys.stderr)
        return 1
    needle, message = sys.argv[1], sys.argv[2]
    try:
        result = send(needle, message)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

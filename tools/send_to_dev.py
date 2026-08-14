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
    python -m tools.send_to_dev <task_id_or_prefix> "<message>"
    python -m tools.send_to_dev task-161dbcf7 "status check please"

Sender label: resolved from the calling process's env the same way
`send_to_cxo._resolve_sender_role()` does (`CXO_ROLE` -> that C-level's
display name, else "CEO") rather than the old hardcoded "[CTO]:" --
`tasks.owner_role` already lets a CFO/CMO/CGO own a DEV task directly, so
a CFO-delegated kickoff now correctly reads "[CFO]:" instead of lying
"[CTO]:" like it used to.

**Correction (CTO iter-2 review, measured not inferred)**: an earlier
draft of this docstring claimed kickoff depends on the wake pressing
Enter into a composer that `runners/dev_init.py`'s `os.execvpe` had
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
documented in `runners/dev_init.py` unchanged, so it stays on
`spawn_backend: iterm`). Before that config change every project spawned
DEVs on the plain iTerm backend and this wake always silently no-op'd.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib import mailbox
from lib import notify
from lib.config import display_for
from tools import tmux_session
from tools.send_to_cxo import (
    current_identity,
    _resolve_sender_role,
    _wake_tmux_send,
    _WAKE_MARKER_TEMPLATE,
)


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
    """
    if not tmux_sess:
        return
    try:
        if not tmux_session.has_session(tmux_sess):
            try:
                notify.info(f"[send_to_dev] wake skipped (no live session): {tmux_sess}")
            except Exception:
                pass
            return
        try:
            notify.info(f"[send_to_dev] wake attempted: {tmux_sess}")
        except Exception:
            pass
        marker = _WAKE_MARKER_TEMPLATE.format(label=label)
        _wake_tmux_send(tmux_sess, marker)
        try:
            notify.info(f"[send_to_dev] wake succeeded: {tmux_sess}")
        except Exception:
            pass
    except Exception as e:
        try:
            notify.info(f"[send_to_dev] wake failed: {tmux_sess}: {e}")
        except Exception:
            pass


def send(task_id: str, message: str) -> str:
    """Queue `message` into the DEV's mailbox, then attempt a wake.

    Contract: queued or raised, never "probably" (GH #60's contract on this
    function, kept across the transport swap). Raises `ValueError` when
    `task_id` (or its prefix) matches no row -- the one failure mode that
    still makes sense once "delivered" no longer depends on any terminal
    existing. A mailbox write failure (disk full, permission denied) raises
    whatever `lib.mailbox.send()` raises; there is no fallback transport to
    catch it and retry.

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

    mailbox.send(role, tid, message, from_role, from_sid)
    _attempt_wake(task.get("tmux_session"), label)
    return f"queued to {display_for(role)} ({tid}): [{label}] : {message}"


def main() -> int:
    if len(sys.argv) < 3:
        print('usage: python -m tools.send_to_dev <task_id_or_prefix> "<message>"',
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

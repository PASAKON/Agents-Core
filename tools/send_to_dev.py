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

**Known gap, reported per this task's brief rather than worked around**:
the wake nudge below is tmux-only, exactly mirroring
`send_to_cxo._wake_tmux_send()` -- it types into `task["tmux_session"]`
if that tmux session is live. `task["tmux_session"]` is only ever set by
`tools/delegate.py` when the owning project's `spawn_backend: tmux`
(`tools/tmux_session.session_name_for()`). As of this task, ZERO entries
in `config/projects.yaml` set `spawn_backend: tmux` -- every project spawns
DEVs on the plain iTerm backend (`runners/dev_init.py` execs `claude`
straight into a new iTerm tab, no tmux). That means, for every DEV spawn
in the org today, `task.get("tmux_session")` is `None` and the wake below
always silently no-ops -- the mailbox letter queues correctly (delivery,
by this file's own definition, has already happened), but nothing then
drains it, because nothing ever fires the DEV's `UserPromptSubmit` hook.
See this task's submitted report for the live-spawn proof and the
consequence: **this migration, exactly as specified, leaves iTerm-backend
DEV kickoffs with no working wake path** -- not a wording/signal problem,
a reachability one. Fixing it needs either `spawn_backend: tmux` rolled
out org-wide (`config/projects.yaml`, out of my touches) or a non-tmux
wake mechanism for DEV tabs (also out of scope: re-adding iTerm typing
here is exactly what this task exists to remove). Flagged, not silently
worked around.
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
    `<role>-<task_id>` the way C-level sessions are (see module docstring:
    this is `None` for every project today, so this is a no-op in practice
    until a project opts into the tmux backend).
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

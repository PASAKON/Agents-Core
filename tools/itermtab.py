"""iTerm tab lifecycle helpers.

Spawn is owned by tools/delegate.py:_spawn_iterm_tab. This module owns the
close side: when a task reaches `done` (post-merge) git_ops.merge_task
calls close_tab(task_id) so the DEV tab disappears and the desktop stays
clean. Tabs for tasks that are still pending / in_progress / review /
blocked stay open.

Tab title set by delegate is `<RoleDisplay> (<full task_id>)`. We match
the full task_id substring, with a 6-char fallback for tabs spawned
before the full-id title change.

## Safety: which tabs we will close

close_tab only closes a tab whose title contains the requested `task_id`
substring AND that task_id starts with `task-`. Tabs we deliberately
never close:
  - CTO Chat / CTO Log / Dev Logs (spawn-cto.sh side tabs — no task_id).
  - User-opened terminals (shells without a task_id in title).
  - Tabs from a hypothetical interactive `spawn Web Designer` REPL whose
    title does not carry a task_id.

A tab is therefore only closeable when it was spawned by the delegate
path (`tools/delegate.py:_spawn_iterm_tab`) or by `tools/resume_dev.py:
_spawn_resume_tab`. Both set the title `<Role> (task-<id>)`.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LOCKS = _ROOT / "state" / "locks"


def close_tab(task_id: str) -> bool:
    """Close the iTerm tab whose title contains the given task id.

    Returns True if any tab was closed. Safe to call when no matching
    tab exists (returns False).
    """
    if not task_id or not task_id.startswith("task-"):
        # Refuse to operate on inputs that don't look like a real task id.
        # Protects against accidental empty/garbage matches reaching
        # iTerm and closing the wrong tab.
        return False
    fallback = task_id[:6]
    script = f'''
tell application "iTerm"
  set closedAny to false
  repeat with w in windows
    set tabsList to tabs of w
    repeat with t in tabsList
      tell t
        if name of current session contains "{task_id}" then
          close t
          set closedAny to true
        end if
      end tell
    end repeat
  end repeat
  if not closedAny then
    repeat with w in windows
      set tabsList to tabs of w
      repeat with t in tabsList
        tell t
          if name of current session contains "{fallback}" then
            close t
            set closedAny to true
          end if
        end tell
      end repeat
    end repeat
  end if
  if closedAny then
    return "1"
  else
    return "0"
  end if
end tell
'''
    r = subprocess.run(["osascript", "-e", script],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "1"


def close_session(role: str, session_id: str) -> bool:
    """Close the iTerm tab owned by role+session_id.

    Enforces four gates: lock file exists, winid is live in iTerm, caller
    env ($CXO_ROLE/$CXO_SESSION_ID) matches, no in-progress task for session.
    Refusals are appended to state/locks/close-refusals.log as JSON lines.
    """
    lock_path = _LOCKS / f"{role}-{session_id}.winid"
    refusals_log = _LOCKS / "close-refusals.log"

    def _refuse(reason: str) -> bool:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "role": role,
            "session_id": session_id,
            "reason": reason,
        }
        try:
            _LOCKS.mkdir(parents=True, exist_ok=True)
            with refusals_log.open("a") as fh:
                fh.write(json.dumps(entry) + "\n")
        except OSError:
            pass
        return False

    # Gate 1: lock file must exist
    if not lock_path.exists():
        return _refuse("lock file missing")

    winid = lock_path.read_text().strip()
    if not winid.isdigit():
        return _refuse(f"lock file malformed: {winid!r}")

    # Gate 2: winid must be in iTerm's live window list
    r = subprocess.run(
        ["osascript", "-e", 'tell application "iTerm2" to return id of windows'],
        capture_output=True, text=True,
    )
    live = "," + r.stdout.strip().replace(" ", "") + ","
    if f",{winid}," not in live:
        return _refuse(f"winid {winid} not in live windows")

    # Gate 3: caller env must match owner
    if os.environ.get("CXO_ROLE") != role or os.environ.get("CXO_SESSION_ID") != session_id:
        return _refuse("caller env mismatch")

    # Gate 4: no in-progress task bound to this session_id
    # TODO(Phase 2): extend once c_level_sessions.active_task_id column exists.
    # Uses tasks table session_id column in state/tasks.db (via lib/db path).
    try:
        import sqlite3
        db_path = _ROOT / "state" / "tasks.db"
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id FROM tasks WHERE session_id=? AND status='in_progress' LIMIT 1",
                (session_id,),
            ).fetchone()
            conn.close()
            if row:
                return _refuse(f"in-progress task {row['id']} bound to session")
    except Exception:
        pass

    # All gates passed — close the window
    script = f"""
tell application "iTerm2"
  repeat with w in windows
    if id of w is {winid} then
      close w
      return "1"
    end if
  end repeat
  return "0"
end tell
"""
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip() == "1":
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        return True
    return _refuse("iTerm close failed or window not found")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("usage: python -m tools.itermtab <task_id>")
        sys.exit(1)
    ok = close_tab(sys.argv[1])
    print(f"closed: {ok}")

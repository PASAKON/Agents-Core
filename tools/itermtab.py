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
    # Both title surfaces are checked (sticky tab name + session badge,
    # same as delegate's spawn matcher) — the session badge flickers to
    # the running process name, which made session-name-only closes miss.
    #
    # C-level tabs carry a live work summary in the title (IRON-RULES §32,
    # scripts/tab-title.sh). If a summary ever mentions a task, a naive
    # task-id match would close the C-level chat itself — so any tab whose
    # title carries a C-level prefix is excluded from closing.
    guard = ('and not (nm contains "CTO ") and not (nm contains "CMO ") '
             'and not (nm contains "CGO ") and not (nm contains "CFO ") '
             'and not (tn contains "CTO ") and not (tn contains "CMO ") '
             'and not (tn contains "CGO ") and not (tn contains "CFO ")')
    script = f'''
tell application "iTerm"
  set closedAny to false
  repeat with w in windows
    set tabsList to tabs of w
    repeat with t in tabsList
      set nm to ""
      try
        set nm to name of current session of t
      end try
      set tn to ""
      try
        set tn to name of t
      end try
      if ((nm contains "{task_id}") or (tn contains "{task_id}")) {guard} then
        close t
        set closedAny to true
      end if
    end repeat
  end repeat
  if not closedAny then
    repeat with w in windows
      set tabsList to tabs of w
      repeat with t in tabsList
        set nm to ""
        try
          set nm to name of current session of t
        end try
        set tn to ""
        try
          set tn to name of t
        end try
        if ((nm contains "{fallback}") or (tn contains "{fallback}")) {guard} then
          close t
          set closedAny to true
        end if
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

    # Gate 4: no in-progress task bound to this session via c_level_sessions
    try:
        import sys as _sys
        _sys.path.insert(0, str(_ROOT))
        from lib.db import db_conn
        with db_conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM c_level_sessions "
                "WHERE role = ? AND session_id = ? AND active_task_id IS NOT NULL "
                "AND active_task_id IN (SELECT id FROM tasks WHERE status = 'in_progress')",
                (role, session_id),
            ).fetchone()
        if row is not None:
            return _refuse("session has in-progress task")
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

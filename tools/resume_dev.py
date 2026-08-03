"""Open a new iTerm tab and resume a DEV that was paused by a
rate-limit. Soft-resumes via `claude --resume <session_id>` if the
hook captured a session id, otherwise hard-resumes through
runners.dev_init (the DEV reads TASK.md + git status and continues).

Usage:
    python -m tools.resume_dev <task_id>
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import display_for
from tools.delegate import _owner_window_id

ROOT = Path(__file__).resolve().parent.parent


def _spawn_resume_tab(role: str, task_id: str,
                      owner_cto: str | None = None,
                      owner_role: str | None = None) -> None:
    display = display_for(role)
    tab_title = f"{display} ({task_id}) [RESUMED]"
    cmd = (
        f"printf '\\\\033]1;{tab_title}\\\\007' && "
        f"cd '{ROOT}' && source .venv/bin/activate && "
        f"python -m runners.dev_resume {role} {task_id}"
    )
    # Route back into the owning C-level's window (CTO/CFO/CMO/CGO, per
    # owner_role) instead of always assuming CTO — same fix as
    # tools.delegate._build_spawn_applescript. Falls back to a generic
    # "CTO" match only when owner_role is unknown (legacy rows).
    owner_display = display_for(owner_role) if owner_role else "CTO"
    owner_winid = _owner_window_id(owner_cto, owner_role)
    script = f'''
tell application "iTerm"
  set targetWin to missing value
  if "{owner_winid or ''}" is not "" then
    try
      set targetWin to (first window whose id is ({owner_winid or 0}))
    end try
  end if
  if targetWin is missing value then
  repeat with w in windows
    repeat with t in tabs of w
      try
        set tabName to name of current session of t
        -- "<DISPLAY> Chat #"/"<DISPLAY> #" only: a bare "{owner_display}"
        -- would also match ephemeral cross-talk tabs titled
        -- "CFO <- CTO: ...".
        if (tabName contains "{owner_display} Chat #") or (tabName contains "{owner_display} #") then
          set targetWin to w
          exit repeat
        end if
      end try
    end repeat
    if targetWin is not missing value then exit repeat
  end repeat
  end if
  if targetWin is missing value then
    if (count of windows) = 0 then
      set targetWin to (create window with default profile)
      tell current session of current tab of targetWin
        write text "{cmd}"
      end tell
      return
    else
      set targetWin to current window
    end if
  end if
  tell targetWin
    set newTab to (create tab with default profile)
    tell current session of newTab
      write text "{cmd}"
    end tell
  end tell
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def resume(task_id: str) -> str:
    db.init()
    task = db.get_task(task_id)
    if not task:
        return f"ERROR: task {task_id} not found"
    if task["status"] == "done":
        return f"ERROR: task {task_id} already done; nothing to resume"
    role = task["role"]
    owner_cto = task.get("owner_cto")
    owner_role = task.get("owner_role") or "cto"
    _spawn_resume_tab(role, task_id, owner_cto, owner_role)
    mode = "soft" if task.get("session_id") else "hard"
    return f"OK: resume tab opened for {task_id} (mode={mode})"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m tools.resume_dev <task_id>", file=sys.stderr)
        return 1
    print(resume(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

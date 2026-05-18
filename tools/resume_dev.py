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

ROOT = Path(__file__).resolve().parent.parent

ROLE_DISPLAY = {
    "developer": "Developer",
    "tester": "Tester",
    "web_designer": "Web Designer",
    "devops_engineer": "DevOps Engineer",
    "security_engineer": "Security Engineer",
    "data_analyst": "Data Analytics",
    "prompt_engineer": "Prompt Engineer",
}


def _spawn_resume_tab(role: str, task_id: str) -> None:
    display = ROLE_DISPLAY.get(role, role)
    tab_title = f"{display} ({task_id}) [RESUMED]"
    cmd = (
        f"printf '\\\\033]0;{tab_title}\\\\007' && "
        f"cd '{ROOT}' && source .venv/bin/activate && "
        f"python -m runners.dev_resume {role} {task_id}"
    )
    script = f'''
tell application "iTerm"
  activate
  if (count of windows) = 0 then
    set newWin to (create window with default profile)
    tell current session of current tab of newWin
      write text "{cmd}"
    end tell
  else
    tell current window
      set newTab to (create tab with default profile)
      tell current session of newTab
        write text "{cmd}"
      end tell
    end tell
  end if
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
    _spawn_resume_tab(role, task_id)
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

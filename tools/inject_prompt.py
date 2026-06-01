"""Helper: write task description to TASK.md in worktree, then send a short
pointer prompt to the DEV's iTerm tab so the DEV's claude TUI reads it.

Usage:
    python -m tools.inject_prompt <task_id_substring>

Workflow:
  1. Load task from DB by id (or prefix-match).
  2. Write task description + instructions to <worktree>/TASK.md.
  3. Send short prompt via iTerm `write text` to the tab whose session
     name contains the task id (no Accessibility permission needed).

iTerm `write text` appends Enter → claude TUI submits the prompt.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db


def _build_task_md(task) -> str:
    return (
        f"# Task {task['id']}\n\n"
        f"Project: {task['project']}\n"
        f"Role: {task['role']}\n"
        f"Branch: {task.get('branch')}\n\n"
        "## Description\n\n"
        f"{task['description']}\n\n"
        "---\n\n"
        "## DEV Workflow\n\n"
        "1. Implement per description above. Edit / create files in this worktree only.\n"
        "2. Commit incrementally with descriptive messages.\n"
        "3. Run tests if patterns exist.\n"
        "4. When done, call `mcp__org__submit_report` with: files changed, tests run, blockers.\n"
        "5. Without `submit_report` the task stays in_progress forever — CTO can't see your work.\n"
    )


def _write_task_md(worktree: str, body: str) -> Path:
    wt = Path(worktree)
    wt.mkdir(parents=True, exist_ok=True)
    p = wt / "TASK.md"
    p.write_text(body, encoding="utf-8")
    return p


def _send_pointer(tab_substring: str, task_md_path: Path) -> None:
    pointer = (
        f"Read {task_md_path} and execute the task described inside. "
        "After completing, call mcp__org__submit_report."
    )
    pointer_escaped = pointer.replace('\\', '\\\\').replace('"', '\\"')
    # `newline NO` suppresses iTerm's default trailing LF. Then we
    # append CR (ASCII 13) which claude TUI interprets as Enter/submit.
    script = f'''
tell application "iTerm"
  tell current window
    repeat with t in tabs
      tell t
        if name of current session contains "{tab_substring}" then
          select t
          tell current session
            write text "{pointer_escaped}" newline NO
            write text (ASCII character 13) newline NO
          end tell
        end if
      end tell
    end repeat
  end tell
end tell
'''
    subprocess.run(["osascript", "-e", script], check=True)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m tools.inject_prompt <task_id_or_prefix>", file=sys.stderr)
        return 1
    needle = sys.argv[1]

    db.init()
    task = db.get_task(needle)
    if not task:
        from lib.db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT id FROM tasks WHERE id LIKE ? LIMIT 1",
                (f"{needle}%",),
            ).fetchone()
        if not row:
            print(f"no task matching {needle}", file=sys.stderr)
            return 2
        task = db.get_task(row[0])

    worktree = task.get("worktree")
    if not worktree:
        print(f"task {task['id']} has no worktree", file=sys.stderr)
        return 3

    md_path = _write_task_md(worktree, _build_task_md(task))
    short = task["id"][:10]
    _send_pointer(short, md_path)
    print(f"wrote {md_path} + sent pointer to tab matching {short}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""DEV resume launcher — re-attaches to a previous DEV session after a
rate-limit interruption.

Invoked from tools/resume_dev.py inside an iTerm tab. Mirrors dev_init
but execs `claude --resume <session_id>` instead of spawning fresh, so
the DEV continues exactly where it left off with full chat history.

Usage:
    python -m runners.dev_resume <role> <task_id>

Falls back to a hard resume (delegating to runners.dev_init) if the
task has no session_id recorded yet.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import get_project, role as get_role
from runners.dev_init import _write_dev_settings  # type: ignore

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m runners.dev_resume <role> <task_id>",
              file=sys.stderr)
        sys.exit(1)
    role = sys.argv[1]
    task_id = sys.argv[2]

    db.init()
    task = db.get_task(task_id)
    if not task:
        print(f"task {task_id} not found", file=sys.stderr)
        sys.exit(2)

    session_id = task.get("session_id")
    if not session_id:
        print(f"no session_id on {task_id} - falling back to hard resume "
              "via dev_init", file=sys.stderr)
        os.execvp("python", ["python", "-m", "runners.dev_init", role, task_id])
        return

    worktree = task.get("worktree")
    if not worktree or not Path(worktree).exists():
        db.update_status(task_id, "failed",
                         report="worktree missing on resume", actor=role)
        print(f"worktree missing for task {task_id}", file=sys.stderr)
        sys.exit(4)

    db.update_status(task_id, "in_progress", actor=role,
                     assigned_agent=role)

    project = get_project(task["project"])
    role_doc = (ROOT / "roles" / f"{role}.md").read_text()
    try:
        model = get_role(role).get("model") or "claude-opus-4-8[1m]"
    except ValueError:
        model = "claude-opus-4-8[1m]"

    env = os.environ.copy()
    env["DEV_TASK_ID"] = task_id
    env["DEV_ROLE"] = role

    _write_dev_settings(worktree)

    allowed = (
        "mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search "
        "mcp__org__submit_report mcp__org__dev_message "
        "mcp__org__file_blocker_issue "
        "Read Write Edit Bash Glob Grep"
    ).split()

    resume_nudge = (
        f"[RESUMED after rate-limit cooldown] Task {task_id} on project "
        f"{project['name']}. Branch {task['branch']}. Before doing anything "
        "else: run `git status` + `git diff` to see what was already done, "
        "skim TASK.md, then continue. Submit report when finished."
    )

    os.chdir(worktree)
    os.execvpe(
        "claude",
        [
            "claude",
            "-n", f"{role}:{task_id}",
            "--resume", session_id,
            "--model", model,
            "--effort", "max",
            "--permission-mode", "auto",
            "--append-system-prompt", role_doc,
            "--mcp-config", str(ROOT / "config" / "dev.mcp.json"),
            "--strict-mcp-config",
            "--allowed-tools", *allowed,
            resume_nudge,
        ],
        env,
    )


if __name__ == "__main__":
    main()

"""DEV launcher — claims a task, then execs Claude Code CLI in the worktree.

Invoked from inside an iTerm tab spawned by tools/delegate.py:
    python -m runners.dev_init <role> <task_id>

After exec the tab becomes a normal Claude Code TUI scoped to the DEV's
worktree, with the task description already injected as the first prompt
and an MCP `submit_report` tool wired so the DEV can hand work back.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import display_for, get_project, role as get_role

ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = ROOT / "scripts" / "hook-log-dev-reply.py"


def _write_dev_settings(worktree: str) -> None:
    """Drop .claude/settings.local.json into the worktree so claude wires
    the Stop hook that relays DEV replies into cto.log."""
    settings_dir = Path(worktree) / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "permissionMode": "auto",
        "hooks": {
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"python3 {HOOK_SCRIPT}",
                        }
                    ]
                }
            ]
        },
    }
    (settings_dir / "settings.local.json").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )


def _build_prompt(task, project, worktree) -> str:
    return f"""# Task {task['id']}

Project: {project['name']} ({project['key']})
Stack: {', '.join(project.get('stack', []))}
Repo path (your worktree, work ONLY here): {worktree}
Branch: {task['branch']}
Default branch (do NOT touch): {project['default_branch']}

## Description

{task['description']}

---

## Instructions

1. Read your role doc (already in your system prompt).
2. Read relevant wiki pages (use mcp__org__wiki_read).
3. Inspect the codebase you've been given (your cwd is the worktree).
4. Implement the task incrementally with commits inside your worktree.
5. Run tests if patterns exist.
6. When done, call `mcp__org__submit_report` with your final report
   (files changed, tests run, blockers). This is how the CTO learns
   you finished — without it the task stays in_progress forever.

Begin.
"""


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m runners.dev_init <role> <task_id>", file=sys.stderr)
        sys.exit(1)
    role = sys.argv[1]
    task_id = sys.argv[2]

    db.init()
    task = db.get_task(task_id)
    if not task:
        print(f"task {task_id} not found", file=sys.stderr)
        sys.exit(2)
    if not db.claim_task(task_id, agent=role):
        print(f"could not claim task {task_id}", file=sys.stderr)
        sys.exit(3)

    worktree = task.get("worktree")
    if not worktree or not Path(worktree).exists():
        db.update_status(task_id, "failed", report="worktree missing", actor=role)
        print(f"worktree missing for task {task_id}", file=sys.stderr)
        sys.exit(4)

    project = get_project(task["project"])
    role_doc = (ROOT / "roles" / f"{role}.md").read_text()
    prompt = _build_prompt(task, project, worktree)
    try:
        model = get_role(role).get("model") or "claude-sonnet-4-6"
    except ValueError:
        # role file exists in roles/ but not registered in policies/agents.yaml
        # fall back to worker-tier default
        model = "claude-sonnet-4-6"

    env = os.environ.copy()
    env["DEV_TASK_ID"] = task_id
    env["DEV_ROLE"] = role

    _write_dev_settings(worktree)

    task_md = Path(worktree) / "TASK.md"
    task_md.write_text(prompt, encoding="utf-8")

    allowed = (
        "mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search "
        "mcp__org__submit_report mcp__org__dev_message "
        "mcp__org__file_blocker_issue "
        "Read Write Edit Bash Glob Grep"
    ).split()

    os.chdir(worktree)
    os.execvpe(
        "claude",
        [
            "claude",
            "-n", f"{display_for(role)} ({task_id})",
            "--model", model,
            "--permission-mode", "auto",
            "--append-system-prompt", role_doc,
            "--mcp-config", str(ROOT / "config" / "dev.mcp.json"),
            "--strict-mcp-config",
            "--allowed-tools", *allowed,
            prompt,
        ],
        env,
    )


if __name__ == "__main__":
    main()

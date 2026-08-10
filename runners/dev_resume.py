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
from lib.config import get_project, role as get_role, dev_provider_overrides
from runners.dev_init import (  # type: ignore
    _write_dev_settings,
    _symlink_knowledge,
    dev_tool_grants,
)

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
    # Same composition as dev_init: shared conventions first, then the role
    # doc. Resuming used to load the role doc alone, so a resumed DEV silently
    # lost every Hard Rule — including "never git push" and the ask-before-you-
    # spend rule.
    role_doc = (
        (ROOT / "roles" / "_dev_shared.md").read_text()
        + "\n\n"
        + (ROOT / "roles" / f"{role}.md").read_text()
    )
    try:
        model = get_role(role).get("model") or "claude-opus-5"
    except ValueError:
        model = "claude-opus-5"

    env = os.environ.copy()
    env["DEV_TASK_ID"] = task_id
    env["DEV_ROLE"] = role

    _write_dev_settings(worktree)
    _symlink_knowledge(worktree, role)

    # Shared with dev_init so a resumed DEV keeps exactly the tools it was
    # spawned with. This list used to be a hand-copied duplicate and had
    # already drifted (no request_human_handoff, no Skill for web_designer).
    allowed, chrome_args = dev_tool_grants(role)

    resume_nudge = (
        f"[RESUMED after rate-limit cooldown] Task {task_id} on project "
        f"{project['name']}. Branch {task['branch']}. Before doing anything "
        "else: run `git status` + `git diff` to see what was already done, "
        "skim TASK.md, then continue. Submit report when finished."
    )

    # DEV model provider override (flag-gated) — mirror dev_init so a
    # resumed worker DEV keeps the same model/endpoint it was spawned on.
    _ov = dev_provider_overrides(role)
    effort_args = ["--effort", "max"]
    if _ov:
        model = _ov["model"]
        env.update(_ov["env"])
        if _ov["effort"] is None:
            effort_args = []

    os.chdir(worktree)
    os.execvpe(
        "claude",
        [
            "claude",
            "-n", f"{role}:{task_id}",
            "--resume", session_id,
            "--model", model,
            *effort_args,
            "--permission-mode", "auto",
            "--append-system-prompt", role_doc,
            "--mcp-config", str(ROOT / "config" / "dev.mcp.json"),
            "--strict-mcp-config",
            *chrome_args,
            "--allowed-tools", *allowed,
            resume_nudge,
        ],
        env,
    )


if __name__ == "__main__":
    main()

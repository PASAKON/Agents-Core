"""DEV resume launcher — re-attaches to a previous DEV session after a
rate-limit interruption.

Invoked from tools/resume_worker.py inside an iTerm tab. Mirrors worker_init
but execs `claude --resume <session_id>` instead of spawning fresh, so
the DEV continues exactly where it left off with full chat history.

Usage:
    python -m runners.worker_resume <role> <task_id>

Falls back to a hard resume (delegating to runners.worker_init) if the
task has no session_id recorded yet.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import get_project, role as get_role, worker_provider_overrides, worker_session_name
from runners.worker_init import (  # type: ignore
    _write_dev_settings,
    _symlink_knowledge,
    clean_title,
    current_host,
    worker_claude_argv,
    worker_tool_grants,
)

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: python -m runners.worker_resume <role> <task_id>",
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
              "via worker_init", file=sys.stderr)
        os.execvp("python", ["python", "-m", "runners.worker_init", role, task_id])
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
    # Same composition as worker_init: shared conventions first, then the role
    # doc. Resuming used to load the role doc alone, so a resumed DEV silently
    # lost every Hard Rule — including "never git push" and the ask-before-you-
    # spend rule.
    role_doc = (
        (ROOT / "roles" / "_worker_shared.md").read_text()
        + "\n\n"
        + (ROOT / "roles" / f"{role}.md").read_text()
    )
    try:
        model = get_role(role).get("model") or "claude-opus-5-5"
    except ValueError:
        model = "claude-opus-5-5"

    env = os.environ.copy()
    # Mirror worker_init: an update prompt is a startup interrupt that no
    # --permission-mode or --allowed-tools setting can reach, and it would
    # block a resumed worker nobody is watching (IRON-RULES §45).
    env["DISABLE_AUTOUPDATER"] = "1"
    env["WORKER_TASK_ID"] = task_id
    env["WORKER_ROLE"] = role

    _write_dev_settings(worktree)
    _symlink_knowledge(worktree, role)

    # Shared with worker_init so a resumed DEV keeps exactly the tools it was
    # spawned with. This list used to be a hand-copied duplicate and had
    # already drifted (no request_human_handoff, no Skill for web_designer).
    allowed, chrome_args = worker_tool_grants(role)

    resume_nudge = (
        f"[RESUMED after rate-limit cooldown] Task {task_id} on project "
        f"{project['name']}. Branch {task['branch']}. Before doing anything "
        "else: run `git status` + `git diff` to see what was already done, "
        "skim TASK.md, then continue. Submit report when finished."
    )

    # DEV model provider override (flag-gated) — mirror worker_init so a
    # resumed worker DEV keeps the same model/endpoint it was spawned on.
    _ov = worker_provider_overrides(role, task.get("model_hint"))
    effort_args = ["--effort", "max"]
    if _ov:
        model = _ov["model"]
        env.update(_ov["env"])
        if _ov["effort"] is None:
            effort_args = []

    host_name = current_host()
    session_name = worker_session_name(host_name, role, task_id, clean_title(task.get("title")))

    os.chdir(worktree)
    os.execvpe(
        "claude",
        # Positional `prompt` FIRST, --allowed-tools LAST -- see the full
        # note at worker_claude_argv / the matching site in
        # runners/worker_init.py. That flag is variadic and eats any argv
        # element that follows it.
        worker_claude_argv(
            prompt=resume_nudge,
            session_name=session_name,
            model=model,
            effort_args=effort_args,
            role_doc=role_doc,
            mcp_config=ROOT / "config" / "worker.mcp.json",
            chrome_args=chrome_args,
            allowed=allowed,
            host_name=host_name,
            extra_flags=["--resume", session_id],
        ),
        env,
    )


if __name__ == "__main__":
    main()

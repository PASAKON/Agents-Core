"""CTO delegates to DEV: spawns subprocess running runners.dev module.

Each DEV runs as separate process so logs/stdout don't collide
and one DEV crashing doesn't kill the CTO loop.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from lib import db
from lib.config import get_project, role as get_role
from lib.notify import info, success, error
from tools.worktree import create_worktree

ROOT = Path(__file__).resolve().parent.parent


async def delegate_task(task_id: str) -> dict:
    """Spawn DEV subprocess for a task. Returns final task row."""
    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")

    role_name = task["role"]
    project_key = task["project"]

    # validate role allowed on this project
    proj = get_project(project_key)
    if role_name not in proj["agents_allowed"]:
        raise PermissionError(f"role {role_name} not allowed on project {project_key}")

    # create worktree if not already set
    if not task.get("worktree"):
        wt_info = create_worktree(project_key, role_name, task_id)
        db.update_status(task_id, "pending",
                         worktree=wt_info["worktree"],
                         branch=wt_info["branch"],
                         actor="cto")
        info(f"worktree ready: {wt_info['worktree']}")

    info(f"delegate task={task_id} role={role_name} project={project_key}")

    # spawn DEV subprocess
    cmd = [sys.executable, "-m", "runners.dev", role_name, task_id]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(ROOT),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode

    if rc != 0:
        error(f"DEV exited with code {rc} task={task_id}\n{stderr.decode()[:500]}")
        db.update_status(task_id, "failed",
                         report=f"DEV crashed (rc={rc}). stderr:\n{stderr.decode()[:2000]}",
                         actor="cto")
    else:
        success(f"DEV done task={task_id}")

    return db.get_task(task_id)


async def delegate_parallel(task_ids: list[str], max_concurrent: int = 3) -> list[dict]:
    """Delegate multiple tasks with concurrency cap."""
    sem = asyncio.Semaphore(max_concurrent)

    async def _run(tid):
        async with sem:
            return await delegate_task(tid)

    return await asyncio.gather(*[_run(t) for t in task_ids])

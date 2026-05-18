"""Git operations restricted to CTO. Merge worktree branch → default, then push."""
from __future__ import annotations

import subprocess
from pathlib import Path

from lib import db
from lib.config import get_project, is_c_level
from lib.notify import info, success, error
from tools.worktree import branch_name, remove_worktree


class GitOpsError(Exception):
    pass


def _run(cmd: list[str], cwd: str | Path) -> str:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise GitOpsError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def merge_task(task_id: str, *, role: str = "cto", strategy: str = "no-ff",
               push: bool | None = None, cleanup: bool = True) -> dict:
    """Merge agent branch into project default branch. CTO only."""
    if not is_c_level(role):
        raise PermissionError(f"only C-level can merge. got: {role}")

    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")
    if task["status"] != "review" and task["status"] != "done":
        raise GitOpsError(f"task {task_id} not in review/done state (got {task['status']})")

    proj = get_project(task["project"])
    repo = Path(proj["path"])
    base = proj["default_branch"]
    branch = task["branch"] or branch_name(task["role"], task_id)

    info(f"merging {branch} → {base} on {proj['key']}")

    # ensure we are on default branch
    _run(["git", "checkout", base], cwd=repo)
    try:
        _run(["git", "pull", "--ff-only", "origin", base], cwd=repo)
    except GitOpsError:
        pass  # offline or no remote

    merge_args = ["git", "merge", "--no-ff" if strategy == "no-ff" else "--ff",
                  "-m", f"Merge {branch} (task {task_id})", branch]
    _run(merge_args, cwd=repo)

    result = {"merged": True, "branch": branch, "base": base, "project": proj["key"]}

    do_push = push if push is not None else proj.get("auto_push", False)
    if do_push:
        try:
            out = _run(["git", "push", "origin", base], cwd=repo)
            result["pushed"] = True
            result["push_output"] = out[:300]
            success(f"pushed {base} on {proj['key']}")
        except GitOpsError as e:
            result["pushed"] = False
            result["push_error"] = str(e)[:500]
            error(f"push failed: {e}")

    if cleanup:
        try:
            remove_worktree(task["project"], task["role"], task_id, delete_branch=True)
            result["cleaned"] = True
        except Exception as e:
            result["cleaned"] = False
            result["cleanup_error"] = str(e)[:300]

    db.update_status(task_id, "done", actor="cto",
                     report=(task.get("report") or "") + f"\n\n## Merge\n{result}")
    return result

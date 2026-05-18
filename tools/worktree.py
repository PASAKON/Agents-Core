"""Git worktree per task. Each DEV works in own isolated dir on dedicated branch."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from lib.config import get_project

ROOT = Path(__file__).resolve().parent.parent
WORKTREE_DIR = ROOT / "worktrees"


class GitError(Exception):
    pass


def _run(cmd: list[str], cwd: str | Path | None = None) -> str:
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise GitError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def worktree_path(project_key: str, role: str, task_id: str) -> Path:
    safe = project_key.replace("/", "_").replace(" ", "_")
    return WORKTREE_DIR / f"{safe}__{role}__{task_id}"


def branch_name(role: str, task_id: str) -> str:
    return f"agent/{role}-{task_id}"


def create_worktree(project_key: str, role: str, task_id: str) -> dict:
    """Create isolated worktree on new branch from default branch."""
    proj = get_project(project_key)
    repo = Path(proj["path"])
    base = proj["default_branch"]
    branch = branch_name(role, task_id)
    wt = worktree_path(project_key, role, task_id)

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    # ensure base branch exists locally + fetch if remote tracked
    try:
        _run(["git", "fetch", "origin", base], cwd=repo)
    except GitError:
        pass

    # remove stale worktree if any
    if wt.exists():
        try:
            _run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo)
        except GitError:
            shutil.rmtree(wt, ignore_errors=True)

    # delete stale branch if exists
    try:
        _run(["git", "branch", "-D", branch], cwd=repo)
    except GitError:
        pass

    _run(["git", "worktree", "add", "-b", branch, str(wt), base], cwd=repo)

    return {
        "project": project_key,
        "task_id": task_id,
        "role": role,
        "branch": branch,
        "worktree": str(wt),
        "base": base,
        "repo": str(repo),
    }


def commit_worktree(worktree: str, message: str, author: str | None = None) -> dict:
    wt = Path(worktree)
    _run(["git", "add", "-A"], cwd=wt)
    status = _run(["git", "status", "--porcelain"], cwd=wt)
    if not status:
        return {"committed": False, "reason": "no changes"}
    env_msg = message
    args = ["git"]
    if author:
        args += ["-c", f"user.name={author}", "-c", f"user.email={author}@agents.local"]
    args += ["commit", "-m", env_msg]
    _run(args, cwd=wt)
    sha = _run(["git", "rev-parse", "HEAD"], cwd=wt)
    return {"committed": True, "sha": sha[:12], "message": env_msg}


def diff_summary(worktree: str, base: str) -> str:
    wt = Path(worktree)
    return _run(["git", "diff", "--stat", f"{base}...HEAD"], cwd=wt)


def diff_full(worktree: str, base: str, max_lines: int = 2000) -> str:
    wt = Path(worktree)
    out = _run(["git", "diff", f"{base}...HEAD"], cwd=wt)
    lines = out.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines)-max_lines} more lines truncated)"
    return out


def remove_worktree(project_key: str, role: str, task_id: str, *, delete_branch: bool = False) -> str:
    proj = get_project(project_key)
    repo = Path(proj["path"])
    wt = worktree_path(project_key, role, task_id)
    branch = branch_name(role, task_id)
    try:
        _run(["git", "worktree", "remove", "--force", str(wt)], cwd=repo)
    except GitError as e:
        if wt.exists():
            shutil.rmtree(wt, ignore_errors=True)
    if delete_branch:
        try:
            _run(["git", "branch", "-D", branch], cwd=repo)
        except GitError:
            pass
    return f"removed worktree {wt}"


def list_worktrees(project_key: str) -> list[str]:
    proj = get_project(project_key)
    out = _run(["git", "worktree", "list", "--porcelain"], cwd=proj["path"])
    return out.splitlines()

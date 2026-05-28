"""revert_task(task_id) — revert a previously merged task."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from lib import db
from lib.config import get_project
from lib.notify import info, success, error, warn
from tools.git_ops import _run, _run_shell, GitOpsError

RVR_DEPTH_LIMIT = int(os.environ.get("RVR_DEPTH_LIMIT", "20"))


def _find_merge_sha(task: dict, repo: Path) -> str | None:
    """Find merge SHA from task.review JSON, task.report text, or git log."""
    # 1. review field (JSON written by merge_task)
    review_str = task.get("review") or ""
    try:
        rev = json.loads(review_str)
        if sha := rev.get("merge_sha"):
            return sha
    except (json.JSONDecodeError, AttributeError):
        pass

    # 2. regex search in report / delegate_log
    for field in ("report", "delegate_log"):
        text = task.get(field) or ""
        m = re.search(r'"merge_sha"\s*:\s*"([0-9a-f]{7,40})"', text)
        if m:
            return m.group(1)

    # 3. git log --grep
    r = subprocess.run(
        ["git", "log", f"--grep=task {task['id']}", "--merges", "-n", "1", "--pretty=%H"],
        cwd=str(repo), capture_output=True, text=True,
    )
    return r.stdout.strip() or None


def _commits_ahead(repo: Path, sha: str) -> int:
    """Commits between merge_sha and HEAD (how far back the merge is)."""
    r = subprocess.run(
        ["git", "rev-list", "--count", f"{sha}..HEAD"],
        cwd=str(repo), capture_output=True, text=True,
    )
    try:
        return int(r.stdout.strip())
    except (ValueError, AttributeError):
        return 9999


def revert_task(task_id: str, *, force: bool = False) -> dict:
    """
    Steps:
      1. Load task row. Require status in {'merged', 'done'}.
      2. Find merge SHA from task.review, task.report, or git log.
      3. Refuse if merge SHA is >RVR_DEPTH_LIMIT commits behind HEAD
         (bypass with force=True).
      4. fetch → checkout default_branch → pull → revert -m 1 → push.
      5. Fire auto_deploy if project has it enabled and not requires_ceo_ack.
      6. UPDATE status='reverted'.
      7. Record task_reverted event.
      8. Return result dict.
    """
    task = db.get_task(task_id)
    if not task:
        return {"reverted": False, "reason": f"task not found: {task_id}"}
    if task["status"] not in ("merged", "done"):
        return {"reverted": False, "reason": "task not in mergeable state"}

    proj = get_project(task["project"])
    repo = Path(proj["path"])
    base = proj["default_branch"]

    merge_sha = _find_merge_sha(task, repo)
    if not merge_sha:
        return {"reverted": False, "reason": "merge_sha not found"}

    depth = _commits_ahead(repo, merge_sha)
    if depth > RVR_DEPTH_LIMIT and not force:
        return {
            "reverted": False,
            "reason": (
                f"merge_sha is {depth} commits behind HEAD "
                f"(limit {RVR_DEPTH_LIMIT}). Use force=True to override."
            ),
        }

    try:
        _run(["git", "fetch", "origin"], cwd=repo)
        _run(["git", "checkout", base], cwd=repo)
        _run(["git", "pull", "--ff-only"], cwd=repo)
        _run(["git", "revert", "-m", "1", merge_sha, "--no-edit"], cwd=repo)
        _run(["git", "push", "origin", base], cwd=repo)
    except GitOpsError as e:
        return {"reverted": False, "reason": str(e)[:500]}

    revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    deploy_result: dict = {}
    auto_deploy = proj.get("auto_deploy") or {}
    if auto_deploy.get("enabled") and not auto_deploy.get("requires_ceo_ack"):
        cmd = auto_deploy.get("command", "")
        if cmd:
            rc, out = _run_shell(cmd, cwd=repo)
            deploy_result = {"command": cmd, "exit_code": rc, "output": out[:500]}
            if rc == 0:
                success(f"auto_deploy succeeded for {task_id}")
            else:
                warn(f"auto_deploy failed (rc={rc}) for {task_id}")

    db.update_status(task_id, "reverted", actor="cto")

    with db.get_conn() as conn:
        db.log_event(conn, task_id, "cto", "task_reverted", {
            "merge_sha": merge_sha,
            "revert_sha": revert_sha,
            "deploy_result": deploy_result,
        })

    info(f"reverted {task_id}: {merge_sha[:8]} → {revert_sha[:8]}")
    return {
        "reverted": True,
        "merge_sha": merge_sha,
        "revert_sha": revert_sha,
        "pushed": True,
        "deploy": deploy_result,
    }

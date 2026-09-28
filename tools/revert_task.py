"""revert_task(task_id) — revert a previously merged task."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from lib import db
from lib.config import get_project, self_host
from lib.notify import info, success, error, warn
from tools.git_ops import (
    _run, _run_shell, GitOpsError,
    _repo_path_for_host, _create_temp_worktree, _remove_temp_worktree,
    _ff_runtime_checkout, _push_base,
)

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


def _commits_ahead(repo: Path, sha: str, upto: str = "HEAD") -> int:
    """Commits between merge_sha and `upto` (how far back the merge is).

    `upto` defaults to HEAD (original behavior, no-origin projects). A
    project with an origin remote passes `origin/<base>` instead, so the
    depth check is measured against the freshly-fetched remote tip rather
    than this host's possibly-stale local HEAD (Org Mesh W0.2 — the same
    "Mac diverged main" staleness the merge path fixes).
    """
    r = subprocess.run(
        ["git", "rev-list", "--count", f"{sha}..{upto}"],
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
      3. Refuse if merge SHA is >RVR_DEPTH_LIMIT commits behind (bypass
         with force=True).
      4. Revert + push. Host-aware (Org Mesh W0.2): a project with an
         origin remote reverts in a throwaway detached worktree of
         origin/<base>, pushes, then best-effort fast-forwards the runtime
         checkout in place. No origin: the original local-checkout path
         (fetch → checkout base → pull → revert -m 1 → push) unchanged.
      5. Fire auto_deploy if project has it enabled, not requires_ceo_ack,
         and (on the origin path) the runtime checkout actually advanced.
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
    base = proj["default_branch"]
    host = self_host()
    repo = Path(_repo_path_for_host(proj, host))
    has_origin = bool(proj.get("remote"))

    merge_sha = _find_merge_sha(task, repo)
    if not merge_sha:
        return {"reverted": False, "reason": "merge_sha not found"}

    if has_origin:
        try:
            _run(["git", "fetch", "origin", base], cwd=repo)
        except GitOpsError as e:
            return {"reverted": False, "reason": str(e)[:500]}
        depth = _commits_ahead(repo, merge_sha, upto=f"origin/{base}")
    else:
        depth = _commits_ahead(repo, merge_sha)

    if depth > RVR_DEPTH_LIMIT and not force:
        return {
            "reverted": False,
            "reason": (
                f"merge_sha is {depth} commits behind HEAD "
                f"(limit {RVR_DEPTH_LIMIT}). Use force=True to override."
            ),
        }

    if not has_origin:
        return _revert_local(task_id, task, proj, repo, base, merge_sha, host)

    return _revert_via_temp_worktree(task_id, task, proj, repo, base, merge_sha, host)


def _revert_local(task_id: str, task: dict, proj: dict, repo: Path, base: str,
                  merge_sha: str, host: str) -> dict:
    """Original revert path: no origin remote, revert directly in `repo`.

    Unchanged from before Org Mesh W0.2 (task brief item 6, byte-for-byte)
    except for the additive host/runtime_updated/runtime_reason result
    fields every revert_task caller can now rely on regardless of path.
    """
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
        "host": host,
        "runtime_updated": True,
        "runtime_reason": None,
    }


def _revert_via_temp_worktree(task_id: str, task: dict, proj: dict, repo: Path,
                              base: str, merge_sha: str, host: str) -> dict:
    """Org Mesh W0.2: revert in a throwaway detached worktree of
    origin/<base>, push, then best-effort fast-forward the runtime checkout
    in place. Mirrors tools.git_ops's merge path."""
    tmp_dir = _create_temp_worktree(repo, f"origin/{base}", prefix=f"revertwt-{task_id}-")
    try:
        try:
            _run(["git", "revert", "-m", "1", merge_sha, "--no-edit"], cwd=tmp_dir)
        except GitOpsError as e:
            try:
                _run(["git", "revert", "--abort"], cwd=tmp_dir)
            except GitOpsError:
                pass
            return {"reverted": False, "reason": str(e)[:500]}

        revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=tmp_dir)
        push_result = _push_base(tmp_dir, base, revert_sha)
    finally:
        _remove_temp_worktree(repo, tmp_dir)

    if not push_result.get("pushed"):
        return {"reverted": False,
               "reason": push_result.get("push_error", "revert push failed"),
               "merge_sha": merge_sha, "revert_sha": revert_sha, "host": host}

    ff_result = _ff_runtime_checkout(repo, base)
    if not ff_result["runtime_updated"]:
        warn(f"runtime checkout on {host} not fast-forwarded for {proj['key']}: "
             f"{ff_result.get('runtime_reason')}")

    deploy_result: dict = {}
    auto_deploy = proj.get("auto_deploy") or {}
    if auto_deploy.get("enabled") and not auto_deploy.get("requires_ceo_ack"):
        if not ff_result["runtime_updated"]:
            deploy_result = {"deployed": False,
                             "reason": "runtime_updated=false, skipping deploy"}
        else:
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
        "on_origin": push_result.get("on_origin", False),
        "deploy": deploy_result,
        "host": host,
        "runtime_updated": ff_result["runtime_updated"],
        "runtime_reason": ff_result["runtime_reason"],
    }

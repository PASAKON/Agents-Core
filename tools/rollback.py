"""Revert a merged task. CTO-only.

Reads the merge SHA from tasks.review JSON (written by tools.git_ops.merge_task),
reverts it on the project's default branch and pushes, then flips task status
to cancelled.

Host-aware (Org Mesh W0.2, docs/design/org-mesh.md C5): a project with an
origin remote reverts in a throwaway detached worktree of origin/<base>,
then best-effort fast-forwards the runtime checkout in place. `auto_push`
now controls only whether a WORKER may push its own branch directly — a
rollback on an origin project always pushes (unless push=False is passed
explicitly). A project with no origin remote keeps the original
local-checkout path, still gated by `auto_push`.

Usage:
    python -m tools.rollback <task_id>
    python -m tools.rollback <task_id> --no-push
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.config import get_project, self_host
from lib.notify import info, success, error, warn
from tools.git_ops import (
    _repo_path_for_host, _create_temp_worktree, _remove_temp_worktree,
    _ff_runtime_checkout, _push_base, GitOpsError,
)


class RollbackError(Exception):
    pass


def _run(cmd: list[str], cwd: str | Path) -> str:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise RollbackError(f"{' '.join(cmd)}\n{r.stderr.strip()}")
    return r.stdout.strip()


def rollback(task_id: str, *, push: bool | None = None) -> dict:
    task = db.get_task(task_id)
    if not task:
        raise RollbackError(f"task not found: {task_id}")
    if task["status"] != "done":
        raise RollbackError(
            f"task {task_id} status={task['status']} — only 'done' tasks can be rolled back"
        )

    try:
        review = json.loads(task.get("review") or "{}")
    except json.JSONDecodeError:
        review = {}
    merge_sha = review.get("merge_sha")
    if not merge_sha:
        raise RollbackError(
            f"task {task_id} has no merge_sha in review. Manual revert required."
        )

    proj = get_project(task["project"])
    base = proj["default_branch"]
    host = self_host()
    repo = Path(_repo_path_for_host(proj, host))
    has_origin = bool(proj.get("remote"))

    if not has_origin:
        return _rollback_local(task_id, task, proj, repo, base, merge_sha,
                               review, push, host)

    return _rollback_via_temp_worktree(task_id, task, proj, repo, base,
                                       merge_sha, review, push, host)


def _rollback_local(task_id: str, task: dict, proj: dict, repo: Path, base: str,
                    merge_sha: str, review: dict, push: bool | None,
                    host: str) -> dict:
    """Original rollback path: no origin remote, revert directly in `repo`."""
    info(f"reverting {merge_sha[:10]} on {proj['key']}/{base}")
    _run(["git", "checkout", base], cwd=repo)
    try:
        _run(["git", "pull", "--ff-only", "origin", base], cwd=repo)
    except RollbackError:
        pass
    _run(["git", "revert", "--no-edit", "-m", "1", merge_sha], cwd=repo)
    revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    result = {"rolled_back": True, "task_id": task_id, "reverted_sha": merge_sha,
              "revert_sha": revert_sha, "host": host, "runtime_updated": True,
              "runtime_reason": None}

    do_push = push if push is not None else proj.get("auto_push", False)
    if do_push:
        try:
            _run(["git", "push", "origin", base], cwd=repo)
            result["pushed"] = True
            success(f"pushed revert {revert_sha[:10]} on {proj['key']}")
        except RollbackError as e:
            result["pushed"] = False
            result["push_error"] = str(e)[:300]
            error(f"push failed: {e}")
    else:
        result["pushed"] = False

    new_review = {**review, "rolled_back": True, "revert_sha": revert_sha}
    db.update_status(
        task_id, "cancelled", actor="cto",
        review=json.dumps(new_review),
        report=(task.get("report") or "") + f"\n\n## Rolled Back\n{result}",
    )
    return result


def _rollback_via_temp_worktree(task_id: str, task: dict, proj: dict, repo: Path,
                                base: str, merge_sha: str, review: dict,
                                push: bool | None, host: str) -> dict:
    """Org Mesh W0.2: revert in a throwaway detached worktree of
    origin/<base>, push, then best-effort fast-forward the runtime checkout
    in place. Mirrors tools.git_ops's merge path."""
    try:
        tmp_dir = _create_temp_worktree(repo, f"origin/{base}", prefix=f"rollbackwt-{task_id}-")
    except GitOpsError as e:
        raise RollbackError(f"could not create temp worktree: {e}") from e
    try:
        try:
            _run(["git", "revert", "--no-edit", "-m", "1", merge_sha], cwd=tmp_dir)
        except RollbackError as e:
            try:
                _run(["git", "revert", "--abort"], cwd=tmp_dir)
            except RollbackError:
                pass
            raise RollbackError(f"revert failed: {e}") from e
        revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=tmp_dir)

        do_push = push if push is not None else True
        if do_push:
            try:
                push_result = _push_base(tmp_dir, base, revert_sha)
            except GitOpsError as e:
                push_result = {"pushed": False, "push_error": str(e)[:300]}
        else:
            push_result = {"pushed": False}
    finally:
        _remove_temp_worktree(repo, tmp_dir)

    if push_result.get("pushed"):
        ff_result = _ff_runtime_checkout(repo, base)
    else:
        ff_result = {"runtime_updated": False, "runtime_reason": "not pushed"}
    if push_result.get("pushed") and not ff_result["runtime_updated"]:
        warn(f"runtime checkout on {host} not fast-forwarded for {proj['key']}: "
             f"{ff_result.get('runtime_reason')}")

    result = {"rolled_back": True, "task_id": task_id, "reverted_sha": merge_sha,
              "revert_sha": revert_sha, "host": host}
    result.update(push_result)
    result.update(ff_result)
    if push_result.get("pushed"):
        success(f"pushed revert {revert_sha[:10]} on {proj['key']}")
    elif "push_error" in push_result:
        error(f"push failed: {push_result['push_error']}")

    new_review = {**review, "rolled_back": True, "revert_sha": revert_sha}
    db.update_status(
        task_id, "cancelled", actor="cto",
        review=json.dumps(new_review),
        report=(task.get("report") or "") + f"\n\n## Rolled Back\n{result}",
    )
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Revert a merged task")
    ap.add_argument("task_id")
    ap.add_argument("--no-push", action="store_true",
                    help="skip git push even if project has auto_push")
    args = ap.parse_args()

    db.init()
    try:
        out = rollback(args.task_id, push=False if args.no_push else None)
    except RollbackError as e:
        error(str(e))
        return 1
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

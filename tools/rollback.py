"""Revert a merged task. CTO-only.

Reads the merge SHA from tasks.review JSON (written by tools.git_ops.merge_task),
runs `git revert <sha>` on the project's default branch, pushes if the project
has auto_push, and flips task status to cancelled.

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
from lib.config import get_project
from lib.notify import info, success, error


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
    repo = Path(proj["path"])
    base = proj["default_branch"]

    info(f"reverting {merge_sha[:10]} on {proj['key']}/{base}")
    _run(["git", "checkout", base], cwd=repo)
    try:
        _run(["git", "pull", "--ff-only", "origin", base], cwd=repo)
    except RollbackError:
        pass
    _run(["git", "revert", "--no-edit", "-m", "1", merge_sha], cwd=repo)
    revert_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    result = {"rolled_back": True, "task_id": task_id, "reverted_sha": merge_sha,
              "revert_sha": revert_sha}

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

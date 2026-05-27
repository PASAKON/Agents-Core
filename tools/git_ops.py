"""Git operations restricted to CTO. Merge worktree branch → default, then push."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib import db
from lib.config import get_project, is_c_level
from lib.notify import info, success, error, warn
from tools.itermtab import close_tab
from tools.worktree import branch_name, remove_worktree


class GitOpsError(Exception):
    pass


def _run(cmd: list[str], cwd: str | Path) -> str:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.returncode != 0:
        raise GitOpsError(f"{' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def _run_shell(cmd: str, cwd: str | Path) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=str(cwd), shell=True,
                       capture_output=True, text=True)
    return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()


def _conflict_files(repo: Path) -> list[str]:
    try:
        out = _run(["git", "diff", "--name-only", "--diff-filter=U"], cwd=repo)
        return [line for line in out.splitlines() if line.strip()]
    except GitOpsError:
        return []


def _is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    """True if `ancestor` is an ancestor of (or equal to) `descendant`.

    Used to detect a no-op merge: if the task branch is already contained in
    base, `git merge` reports "Already up to date" and creates no commit.
    """
    r = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=str(repo), capture_output=True, text=True,
    )
    # exit 0 = is ancestor; 1 = not; other = bad ref / error (treat as "not"
    # so the subsequent merge surfaces the real failure).
    return r.returncode == 0


def merge_task(task_id: str, *, role: str = "cto", strategy: str = "no-ff",
               push: bool | None = None, cleanup: bool = True,
               gate_tests: bool = False) -> dict:
    """Merge agent branch into project default branch. CTO only.

    With gate_tests=True (or proj.gate_tests=true), run proj.test_command
    in the worktree before merging — failure reopens the task with output.

    On merge conflict: abort, set status=conflict, file a gh issue with
    the conflict files so the human can resolve.
    """
    if not is_c_level(role):
        raise PermissionError(f"only C-level can merge. got: {role}")

    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"task not found: {task_id}")
    if task["status"] not in ("review", "done"):
        raise GitOpsError(f"task {task_id} not in review/done state (got {task['status']})")

    proj = get_project(task["project"])
    repo = Path(proj["path"])
    base = proj["default_branch"]
    branch = task["branch"] or branch_name(task["role"], task_id)
    worktree = task.get("worktree")

    gate = gate_tests or bool(proj.get("gate_tests"))
    test_cmd = proj.get("test_command")
    if gate and test_cmd and worktree:
        info(f"gate_tests: running `{test_cmd}` in {worktree}")
        rc, out = _run_shell(test_cmd, cwd=worktree)
        if rc != 0:
            tail = "\n".join(out.splitlines()[-60:])
            warn(f"gate_tests FAILED ({rc}) — reopening task")
            db.update_status(
                task_id, "pending",
                description=(task["description"] +
                             f"\n\n## CTO Test Gate FAILED (iter {task['iteration']+1})\n"
                             f"`{test_cmd}` exit={rc}\n\n```\n{tail}\n```"),
                iteration=task["iteration"] + 1,
                assigned_agent=None,
                actor="cto",
            )
            return {"merged": False, "gate_tests": "failed",
                    "exit_code": rc, "tail": tail[:1000]}
        success(f"gate_tests passed ({test_cmd})")

    info(f"merging {branch} → {base} on {proj['key']}")
    _run(["git", "checkout", base], cwd=repo)
    try:
        _run(["git", "pull", "--ff-only", "origin", base], cwd=repo)
    except GitOpsError:
        pass

    # Capture pre-merge HEAD so we can verify the merge actually advances base.
    pre_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)

    # Guard: if the branch is already contained in base, `git merge` is a silent
    # no-op ("Already up to date", exit 0). Without this guard the no-op was
    # reported as merged=true (line below hardcoded it) AND triggered destructive
    # cleanup (delete branch + worktree) while nothing landed — losing the work.
    # An ancestor branch means it carries no new commits (stale/empty/wrong ref).
    if _is_ancestor(repo, branch, "HEAD"):
        msg = (f"branch {branch} is already an ancestor of {base} at "
               f"{pre_sha[:8]} — nothing to merge (empty/stale branch ref?). "
               f"Refusing to report success; branch + worktree preserved for retry.")
        error(f"merge no-op on {task_id}: {msg}")
        db.update_status(
            task_id, "review", actor="cto",
            review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
        )
        return {"merged": False, "no_op": True, "reason": msg,
                "branch": branch, "base": base, "project": proj["key"]}

    merge_args = ["git", "merge", "--no-ff" if strategy == "no-ff" else "--ff",
                  "-m", f"Merge {branch} (task {task_id})", branch]
    try:
        _run(merge_args, cwd=repo)
    except GitOpsError as merge_err:
        conflicts = _conflict_files(repo)
        try:
            _run(["git", "merge", "--abort"], cwd=repo)
        except GitOpsError:
            pass
        body = (
            f"Merge of `{branch}` into `{base}` for task `{task_id}` "
            f"failed with conflicts.\n\n"
            f"**Conflicting files** ({len(conflicts)}):\n" +
            "\n".join(f"- `{f}`" for f in conflicts) +
            f"\n\n**Worktree**: `{worktree}`\n"
            f"**Error**:\n```\n{str(merge_err)[:1500]}\n```\n\n"
            "Resolve manually, then re-run merge_task."
        )
        issue_url = ""
        try:
            from tools.gh_issue import create_issue
            issue_url = create_issue(
                proj["key"],
                f"merge conflict: {branch} → {base}",
                body,
                labels=["merge-conflict", "agent"],
            )
        except Exception as e:
            warn(f"gh issue creation failed: {e}")
        db.update_status(
            task_id, "conflict", actor="cto",
            review=json.dumps({"conflicts": conflicts, "issue": issue_url,
                               "error": str(merge_err)[:1000]}),
        )
        error(f"merge conflict on {task_id}: {len(conflicts)} files. issue: {issue_url or '(none)'}")
        return {"merged": False, "conflict": True, "files": conflicts,
                "issue": issue_url}

    # Verify the merge actually advanced base. A no-ff merge of a branch with
    # new commits always creates a new commit; if HEAD is unchanged the merge
    # silently did nothing — fail loudly instead of reporting success + cleaning.
    merge_sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)
    if merge_sha == pre_sha:
        msg = (f"merge of {branch} did not advance {base} (HEAD still "
               f"{pre_sha[:8]}). Aborting without cleanup; branch preserved.")
        error(f"merge no-op on {task_id}: {msg}")
        db.update_status(
            task_id, "review", actor="cto",
            review=json.dumps({"merge_error": msg, "branch": branch, "base": base}),
        )
        return {"merged": False, "no_op": True, "reason": msg,
                "branch": branch, "base": base, "project": proj["key"]}

    result = {"merged": True, "branch": branch, "base": base, "project": proj["key"],
              "merge_sha": merge_sha}

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

    db.update_status(
        task_id, "done", actor="cto",
        report=(task.get("report") or "") + f"\n\n## Merge\n{result}",
        review=json.dumps({"merge_sha": merge_sha, "branch": branch,
                           "base": base}),
    )

    try:
        result["tab_closed"] = close_tab(task_id)
    except Exception as e:
        result["tab_closed"] = False
        result["tab_close_error"] = str(e)[:300]

    return result

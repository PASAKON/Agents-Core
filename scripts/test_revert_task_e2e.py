"""End-to-end proof that `git revert -m 1 <merge_sha> --no-edit` (the real git
call revert_task makes) actually undoes a merge_task-style merge correctly.

scripts/test_revert_task.py already covers revert_task()'s Python control flow
(status transitions, depth-limit gating, auto_deploy) with every git call
mocked — that proves the function calls git in the right order, not that the
underlying git operation restores the repo correctly. This test builds a real
temp git repo, does a real `--no-ff` merge (matching git_ops.merge_task's
strategy), then really reverts it, and asserts:

  1. The revert restores the base file content exactly (the feature's change
     is gone from the working tree).
  2. The revert is itself a new commit, not a history rewrite (HEAD advances
     forward, main's prior commits are untouched) — safe to push, unlike
     reset --hard.
  3. A second, independent merge after the revert applies cleanly (the
     revert of merge 1 did not corrupt the tree for merge 2).

Run via:   python scripts/test_revert_task_e2e.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}\n{r.stderr}")
    return r.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "r"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "t@test")
        _git(repo, "config", "user.name", "test")
        (repo / "app.txt").write_text("base\n")
        _git(repo, "add", "app.txt")
        _git(repo, "commit", "-q", "-m", "C0 base")
        pre_merge_sha = _git(repo, "rev-parse", "HEAD")

        # --- merge_task-style merge: feature branch, --no-ff ---
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "app.txt").write_text("base\nfeature line\n")
        _git(repo, "add", "app.txt")
        _git(repo, "commit", "-q", "-m", "C1 feature change")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "--no-ff", "-m", "Merge feature (task t1)", "feature")
        merge_sha = _git(repo, "rev-parse", "HEAD")
        _mark((repo / "app.txt").read_text() == "base\nfeature line\n",
              "sanity: merge landed the feature change")

        # --- the actual revert_task git call ---
        _git(repo, "revert", "-m", "1", merge_sha, "--no-edit")
        revert_sha = _git(repo, "rev-parse", "HEAD")

        # --- 1: working tree restored to pre-merge content ---
        restored = (repo / "app.txt").read_text()
        _mark(restored == "base\n",
              f"revert restores base file content exactly (got {restored!r})")

        # --- 2: revert is a forward commit, base history untouched ---
        _mark(revert_sha != merge_sha, "revert produced a new commit (not a no-op)")
        log = _git(repo, "log", "--oneline")
        _mark("C0 base" in log and "Merge feature" in log,
              "prior history (base commit + merge commit) still present in log — "
              "this is a forward revert commit, not a destructive rewrite")
        _mark(_git(repo, "merge-base", "--is-ancestor", pre_merge_sha, revert_sha) == "",
              "pre-merge base commit is still an ancestor of HEAD after revert")

        # --- 3: a second, independent merge after the revert is unaffected ---
        _git(repo, "checkout", "-q", "-b", "feature2")
        (repo / "other.txt").write_text("unrelated\n")
        _git(repo, "add", "other.txt")
        _git(repo, "commit", "-q", "-m", "C2 unrelated feature")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "--no-ff", "-m", "Merge feature2 (task t2)", "feature2")
        _mark((repo / "other.txt").read_text() == "unrelated\n",
              "a second, independent merge after the revert applies cleanly "
              "(the revert of merge 1 did not corrupt the tree for merge 2)")
        _mark((repo / "app.txt").read_text() == "base\n",
              "app.txt still shows the reverted (pre-feature) state after the "
              "second unrelated merge — revert held")

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

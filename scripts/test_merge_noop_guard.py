"""Regression test for the merge_task no-op guard (git_ops._is_ancestor).

Reproduces the task-e8ed0d81 bug (2026-05-27): when the task branch is already
an ancestor of base, `git merge --no-ff` is a silent no-op ("Already up to
date") — git creates no commit and writes no reflog entry. The old code
hardcoded merged=true and ran destructive cleanup (delete branch + worktree)
anyway, losing the work.

This builds real temp git repos and asserts:
  1. _is_ancestor() detects a stale/empty branch (ancestor of base)  -> True
  2. _is_ancestor() lets a branch with new commits merge             -> False
  3. End-to-end: `git merge --no-ff <ancestor>` does NOT advance HEAD
     (the exact no-op the post-merge guard `merge_sha == pre_sha` catches)
  4. End-to-end: `git merge --no-ff <feature>` DOES advance HEAD

Run via:   python scripts/test_merge_noop_guard.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.git_ops import _is_ancestor  # noqa: E402

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


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@test")
    _git(repo, "config", "user.name", "test")
    (repo / "f.txt").write_text("base\n")
    _git(repo, "add", "f.txt")
    _git(repo, "commit", "-q", "-m", "C0 base")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "r"
        repo.mkdir()
        _init_repo(repo)
        c0 = _git(repo, "rev-parse", "HEAD")

        # Stale branch: points at C0, no new commits (the bug condition).
        _git(repo, "branch", "stale", c0)

        # Feature branch: a real new commit on top of C0.
        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "f.txt").write_text("base\nfeature\n")
        _git(repo, "add", "f.txt")
        _git(repo, "commit", "-q", "-m", "C1 feature")
        _git(repo, "checkout", "-q", "main")

        # --- 1 & 2: _is_ancestor discriminates stale vs feature ---
        _mark(_is_ancestor(repo, "stale", "HEAD") is True,
              "_is_ancestor: stale branch (ancestor of base) detected -> no-op guard fires")
        _mark(_is_ancestor(repo, "feature", "HEAD") is False,
              "_is_ancestor: feature branch (new commits) allowed to merge")

        # --- 3: real no-op merge does not advance HEAD ---
        pre = _git(repo, "rev-parse", "HEAD")
        out = _git(repo, "merge", "--no-ff", "-m", "merge stale", "stale")
        post = _git(repo, "rev-parse", "HEAD")
        _mark(post == pre,
              f"merge --no-ff <ancestor> is a no-op (HEAD unchanged) — git said: {out!r}")

        # --- 4: real merge of new commits advances HEAD ---
        pre2 = _git(repo, "rev-parse", "HEAD")
        _git(repo, "merge", "--no-ff", "-m", "merge feature", "feature")
        post2 = _git(repo, "rev-parse", "HEAD")
        _mark(post2 != pre2, "merge --no-ff <feature> advances HEAD (real merge)")

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

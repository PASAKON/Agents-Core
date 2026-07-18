"""Regression test for the merge_task touches gate (git_ops._touches_violation).

Reproduces the shape of the task-98a3442c incident (2026-07-18, GH issue #29):
a branch declared touches=[one file] but actually changed 15 files (stale
worktree base + git-add-A picked up unrelated deletions/replacements). That
incident was only caught because a human happened to run `git diff --stat`
by hand before merging. This test proves the gate now catches it structurally.

Builds a real temp git repo and asserts:
  1. A branch that only changes declared-touches files -> no violation
  2. A branch that changes a file under a declared directory prefix -> covered
  3. A branch that changes a file matching a declared glob -> covered
  4. A branch that changes a file outside every declaration -> flagged
     (the actual incident shape: 1 declared file + 1 stray file)

Run via:   python scripts/test_touches_gate.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.git_ops import _touches_violation  # noqa: E402

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
    (repo / "README.md").write_text("base\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "C0 base")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "r"
        repo.mkdir()
        _init_repo(repo)

        # --- 1: exact-file declaration, branch touches exactly that file ---
        _git(repo, "checkout", "-q", "-b", "clean-branch")
        Path(repo / "output/content").mkdir(parents=True)
        (repo / "output/content/pilot.md").write_text("v1\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "C1 declared file only")
        extra = _touches_violation(str(repo), "main", ["output/content/pilot.md"])
        _mark(extra == [], f"exact-file match: no violation (got {extra})")
        _git(repo, "checkout", "-q", "main")

        # --- 2: directory-prefix declaration ---
        _git(repo, "checkout", "-q", "-b", "dir-branch")
        Path(repo / "knowledge/content-knowledge").mkdir(parents=True)
        (repo / "knowledge/content-knowledge/facts.json").write_text("{}\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "C1 file under declared dir")
        extra = _touches_violation(str(repo), "main", ["knowledge/content-knowledge/"])
        _mark(extra == [], f"dir-prefix match: no violation (got {extra})")
        _git(repo, "checkout", "-q", "main")

        # --- 3: glob declaration ---
        _git(repo, "checkout", "-q", "-b", "glob-branch")
        Path(repo / "output/posters").mkdir(parents=True)
        (repo / "output/posters/fed-warsh.html").write_text("<html>\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "C1 file matching glob")
        extra = _touches_violation(str(repo), "main", ["output/posters/*.html"])
        _mark(extra == [], f"glob match: no violation (got {extra})")
        _git(repo, "checkout", "-q", "main")

        # --- 4: the actual incident shape — declared 1 file, touched 2 ---
        _git(repo, "checkout", "-q", "-b", "incident-branch")
        (repo / "output/content/pilot.md").parent.mkdir(parents=True, exist_ok=True)
        (repo / "output/content/pilot.md").write_text("v1\n")
        (repo / "README.md").write_text("silently deleted/replaced\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "C1 declared file + stray unrelated file")
        extra = _touches_violation(str(repo), "main", ["output/content/pilot.md"])
        _mark(extra == ["README.md"],
              f"stray file outside declaration flagged (got {extra})")
        _git(repo, "checkout", "-q", "main")

    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Sparse worktrees (ADR 0030, task-bfa778ab) — tools/worktree.py create_worktree.

Builds a throwaway git repo in tmp_path with a docs/reports/big.bin (stands
in for the media that made a real Agents-Core worktree 867 MB, 738 of it
docs/) and a tracked src/a.py. Verifies: a role NOT in `full_checkout_roles`
gets a sparse worktree that excludes docs/reports/; a role IN
`full_checkout_roles` gets today's unchanged full checkout; the main
checkout's own sparse-checkout state is never touched; `commit_worktree`
still commits a changed file from a sparse worktree; and a merge of that
branch into a full (non-sparse) checkout keeps docs/reports intact.

Run via:  pytest tests/test_worktree_sparse.py
(not in pytest.ini's default `testpaths` [scripts, lib] — run explicitly,
same convention as tests/test_decide.py.)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.worktree as worktree_mod  # noqa: E402


def _git(cmd: list[str], cwd: Path) -> str:
    r = subprocess.run(["git", *cmd], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {cmd} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def _init_origin_repo(tmp_path: Path) -> Path:
    """A bare-ish 'origin' repo with docs/reports/big.bin + src/a.py on main,
    matching create_worktree's `origin/<base>` start-point path."""
    repo = tmp_path / "origin"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("print('hi')\n")
    (repo / "docs" / "reports").mkdir(parents=True)
    (repo / "docs" / "reports" / "big.bin").write_bytes(b"\0" * (2 * 1024 * 1024))
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


def _make_clone_with_origin(tmp_path: Path, origin: Path) -> Path:
    """The repo `create_worktree` treats as the project's own checkout —
    cloned from `origin` so `origin/<base>` resolves (mirrors production:
    `git fetch origin <base>` + `git rev-parse --verify origin/<base>`)."""
    repo = tmp_path / "repo"
    _git(["clone", str(origin), str(repo)], tmp_path)
    return repo


@pytest.fixture()
def policy_file(tmp_path):
    """A minimal storage-policy.yaml, isolated from the real repo's config
    so this test never depends on (or breaks from) future policy edits."""
    p = tmp_path / "storage-policy.yaml"
    p.write_text(
        "gauge:\n"
        "  orange: 5\n"
        "sparse_worktree:\n"
        "  exclude: [\"docs/reports/**\"]\n"
        "  full_checkout_roles: [\"video_editor\"]\n"
    )
    return p


@pytest.fixture()
def wired(tmp_path, policy_file, monkeypatch):
    """Point worktree.py at the throwaway repo + policy + a scratch
    WORKTREE_DIR (never the real ~/Projects/Agents/worktrees)."""
    origin = _init_origin_repo(tmp_path)
    repo = _make_clone_with_origin(tmp_path, origin)
    wt_dir = tmp_path / "worktrees"

    monkeypatch.setattr(worktree_mod, "STORAGE_POLICY", policy_file)
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", wt_dir)
    monkeypatch.setattr(
        worktree_mod, "get_project",
        lambda key: {"path": str(repo), "default_branch": "main"},
    )
    return {"origin": origin, "repo": repo, "wt_dir": wt_dir}


# ---------------------------------------------------------------------------
# Sparse role excludes docs/reports; full role includes it.
# ---------------------------------------------------------------------------

def test_sparse_role_excludes_configured_globs(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t1")
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert not (wt / "docs" / "reports").exists()
    assert not (wt / "docs" / "reports" / "big.bin").exists()


def test_full_checkout_role_includes_everything(wired):
    info = worktree_mod.create_worktree("testproj", "video_editor", "t2")
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert (wt / "docs" / "reports" / "big.bin").exists()


# ---------------------------------------------------------------------------
# Main checkout's own sparse-checkout state is never touched.
# ---------------------------------------------------------------------------

def test_main_checkout_stays_non_sparse(wired):
    repo = wired["repo"]
    before = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=str(repo),
        capture_output=True, text=True,
    )

    worktree_mod.create_worktree("testproj", "developer", "t3")

    after = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=str(repo),
        capture_output=True, text=True,
    )
    assert after.returncode == before.returncode
    assert after.stdout == before.stdout
    # core.sparseCheckout must stay unset in the main checkout's own scope
    # (i.e. never fall back to the shared/common config).
    cfg = subprocess.run(
        ["git", "config", "--get", "core.sparseCheckout"], cwd=str(repo),
        capture_output=True, text=True,
    )
    assert cfg.returncode != 0, f"core.sparseCheckout leaked into main checkout: {cfg.stdout!r}"
    assert (repo / "docs" / "reports" / "big.bin").exists(), \
        "main checkout must keep its own full working tree"


# ---------------------------------------------------------------------------
# commit_worktree still commits a changed file from a sparse worktree.
# ---------------------------------------------------------------------------

def test_commit_worktree_from_sparse_worktree(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t4")
    wt = Path(info["worktree"])

    (wt / "src" / "a.py").write_text("print('changed')\n")
    result = worktree_mod.commit_worktree(str(wt), "test: sparse commit")

    assert result["committed"] is True
    assert "sha" in result


# ---------------------------------------------------------------------------
# Merging a sparse branch into a full (non-sparse) checkout keeps
# docs/reports intact — files outside the sparse set are not deleted.
# ---------------------------------------------------------------------------

def test_merge_of_sparse_branch_keeps_excluded_files_intact(wired):
    repo = wired["repo"]

    info = worktree_mod.create_worktree("testproj", "developer", "t5")
    wt = Path(info["worktree"])
    branch = info["branch"]

    (wt / "NEW_FROM_SPARSE.md").write_text("added from a sparse worktree\n")
    commit = worktree_mod.commit_worktree(str(wt), "test: add file from sparse worktree")
    assert commit["committed"] is True

    # merge_task merges in the MAIN repo checkout (tools/git_ops.py:199,266,321
    # — repo = Path(proj["path"]); `git checkout <base>` and `git merge` both
    # run with cwd=repo), which is always a full, non-sparse checkout. `repo`
    # here stands in for that — it was never sparsified (see test above).
    _git(["checkout", "-b", "scratch"], repo)
    _git(["merge", "--no-ff", branch, "-m", "merge sparse branch"], repo)

    assert (repo / "docs" / "reports" / "big.bin").exists(), \
        "docs/reports must survive a merge of a branch built in a sparse worktree"
    assert (repo / "NEW_FROM_SPARSE.md").exists()

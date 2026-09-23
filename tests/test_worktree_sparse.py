"""Sparse worktrees (ADR 0030, task-bfa778ab) — tools/worktree.py create_worktree.

iter1 rewrite: a directory-level exclude ("docs/reports/**") broke `git add
-A` for any NEW file under that directory (git refuses anything outside the
sparse-checkout definition, exit 1) — 304 browser_operator tasks/30d write
new files under docs/reports, so nearly every one of those commits would
have failed. Fixed by excluding only EXISTING tracked files above
`min_bytes` with a `media_guard.extensions` extension, by EXACT PATH —
every directory (including docs/reports itself) stays inside the sparse
definition, so a brand-new file there is always addable.

Builds a throwaway git repo in tmp_path with: a small tracked src/a.py, a
large tracked docs/reports/big_video.mp4, a small tracked
docs/reports/small_icon.png, and three large tracked files exercising the
sparse-checkout pattern escaping this needs — a leading `!`, a `[` inside
the name, and a Thai filename with a space.

Run via:  pytest tests/test_worktree_sparse.py
(collected by the default `pytest` run — pytest.ini `testpaths` now
includes `tests` alongside `scripts lib`.)

Note (task-2b1b03e7, ADR 0030 §8 scope map): `create_worktree`'s `sparse`
param stays a plain bool here — the scope→bool resolution
(`_scope_applies("sparse_worktree", owner_cto)`, "all" | list | missing)
lives entirely in tools/delegate.py and is covered there
(tests/test_delegate_disk_floor.py's `sparse` assertions). Nothing in this
file changed behaviourally; only the "storage pilot" wording below was
updated to match the current scope-map terminology.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.worktree as worktree_mod  # noqa: E402

LARGE = b"\0" * (2 * 1024 * 1024)   # 2 MiB, well above the 256 KiB min_bytes
SMALL = b"\x89PNG\r\n\x1a\n" + b"\0" * 64  # a few dozen bytes, below min_bytes

BANG_FILE = "!weird.mp4"                    # leading '!' — line-start negation char
BRACKET_FILE = "docs/reports/clip[1].mp4"   # '[' — glob metacharacter
THAI_FILE = "docs/reports/แผนที่ ใหม่.mp4"      # Thai + internal space


def _git(cmd: list[str], cwd: Path) -> str:
    r = subprocess.run(["git", *cmd], cwd=str(cwd), capture_output=True, text=True)
    assert r.returncode == 0, f"git {cmd} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def _write(repo: Path, rel: str, data: bytes) -> None:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _init_origin_repo(tmp_path: Path) -> Path:
    """A bare-ish 'origin' repo, matching create_worktree's `origin/<base>`
    start-point path."""
    repo = tmp_path / "origin"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "t@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)

    _write(repo, "src/a.py", b"print('hi')\n")
    _write(repo, "docs/reports/big_video.mp4", LARGE)
    _write(repo, "docs/reports/small_icon.png", SMALL)
    _write(repo, BANG_FILE, LARGE)
    _write(repo, BRACKET_FILE, LARGE)
    _write(repo, THAI_FILE, LARGE)

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
        "media_guard:\n"
        "  extensions: [mp4, png]\n"
        "sparse_worktree:\n"
        "  min_bytes: 262144\n"
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
# Sparse role excludes only the large tracked media, by exact path; small
# files and text stay on disk. Covers the leading-'!', '[', and Thai+space
# escaping cases.
# ---------------------------------------------------------------------------

def test_sparse_role_excludes_only_large_tracked_media(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t1", sparse=True)
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert (wt / "docs" / "reports" / "small_icon.png").exists(), \
        "a small tracked png must stay on disk"

    assert not (wt / "docs" / "reports" / "big_video.mp4").exists(), \
        "a large tracked mp4 must be absent from disk"
    assert not (wt / BANG_FILE).exists(), "leading '!' path must still be excluded"
    assert not (wt / BRACKET_FILE).exists(), "'[' in path must still be excluded"
    assert not (wt / THAI_FILE).exists(), "Thai filename with a space must still be excluded"

    # the directories themselves must NOT be excluded (that was the bug) —
    # only the exact large files inside them.
    assert (wt / "docs" / "reports").is_dir()


def test_full_checkout_role_includes_everything(wired):
    info = worktree_mod.create_worktree("testproj", "video_editor", "t2", sparse=True)
    wt = Path(info["worktree"])

    assert (wt / "src" / "a.py").exists()
    assert (wt / "docs" / "reports" / "big_video.mp4").exists()
    assert (wt / BANG_FILE).exists()
    assert (wt / BRACKET_FILE).exists()
    assert (wt / THAI_FILE).exists()


# ---------------------------------------------------------------------------
# The actual regression: a NEW file under a directory that also holds
# excluded large media must still be addable and committable.
# ---------------------------------------------------------------------------

def test_new_files_under_docs_reports_are_addable_and_committable(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t3", sparse=True)
    wt = Path(info["worktree"])

    (wt / "docs" / "reports" / "NEW_REPORT.md").write_text("a new report\n")
    (wt / "docs" / "reports" / "new_screenshot.png").write_bytes(SMALL)

    r = subprocess.run(["git", "add", "-A"], cwd=str(wt), capture_output=True, text=True)
    assert r.returncode == 0, f"git add -A failed:\n{r.stdout}\n{r.stderr}"

    status = subprocess.run(["git", "status", "--porcelain"], cwd=str(wt),
                            capture_output=True, text=True).stdout
    assert "NEW_REPORT.md" in status
    assert "new_screenshot.png" in status

    result = worktree_mod.commit_worktree(str(wt), "test: add new report + screenshot")
    assert result["committed"] is True


# ---------------------------------------------------------------------------
# Main checkout's own sparse-checkout state is never touched.
# ---------------------------------------------------------------------------

def test_main_checkout_stays_non_sparse(wired):
    repo = wired["repo"]
    before = subprocess.run(
        ["git", "sparse-checkout", "list"], cwd=str(repo),
        capture_output=True, text=True,
    )

    worktree_mod.create_worktree("testproj", "developer", "t4", sparse=True)

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
    assert (repo / "docs" / "reports" / "big_video.mp4").exists(), \
        "main checkout must keep its own full working tree"


# ---------------------------------------------------------------------------
# commit_worktree still commits a changed tracked file from a sparse worktree.
# ---------------------------------------------------------------------------

def test_commit_worktree_from_sparse_worktree(wired):
    info = worktree_mod.create_worktree("testproj", "developer", "t5", sparse=True)
    wt = Path(info["worktree"])

    (wt / "src" / "a.py").write_text("print('changed')\n")
    result = worktree_mod.commit_worktree(str(wt), "test: sparse commit")

    assert result["committed"] is True
    assert "sha" in result


# ---------------------------------------------------------------------------
# Merging a sparse branch into a full (non-sparse) checkout keeps the large
# excluded media intact — files outside the sparse set are not deleted.
# ---------------------------------------------------------------------------

def test_merge_of_sparse_branch_keeps_large_media_intact(wired):
    repo = wired["repo"]

    info = worktree_mod.create_worktree("testproj", "developer", "t6", sparse=True)
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

    assert (repo / "docs" / "reports" / "big_video.mp4").exists(), \
        "large tracked media must survive a merge of a branch built in a sparse worktree"
    assert (repo / BANG_FILE).exists()
    assert (repo / BRACKET_FILE).exists()
    assert (repo / THAI_FILE).exists()
    assert (repo / "NEW_FROM_SPARSE.md").exists()


def test_default_is_full_checkout_when_sparse_not_requested(wired):
    """sparse defaults to False: a task outside the `sparse_worktree` scope
    (another session's work, CEO 2026-09-23) gets today's full checkout."""
    info = worktree_mod.create_worktree("testproj", "developer", "t9")
    wt = Path(info["worktree"])
    assert (wt / "docs" / "reports" / "big_video.mp4").exists()
    assert (wt / THAI_FILE).exists()

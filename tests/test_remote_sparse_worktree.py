"""Sparse worktrees for REMOTE workers (ADR 0030 on Contabo and winbox).

Before this, only tools/worktree.create_worktree (a local spawn) was sparse:
scripts/spawn-worker-remote.sh and windows/spawn-worker.ps1 ran a plain
`git worktree add`, so every Contabo worktree of Agents-Core was a ~0.9 GB
full checkout (ALL_Rules_DiskHygiene field note 2026-09-28: 0 of 22 sparse).
Now the dispatching host computes the exclude list (tools/worktree.
sparse_patterns) and hands the launcher a file; no file = full checkout.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.delegate as delegate  # noqa: E402
import tools.worktree as worktree  # noqa: E402

SCRIPT = ROOT / "scripts" / "spawn-worker-remote.sh"
POLICY = {
    "media_guard": {"extensions": ["mp4", "png"]},
    "sparse_worktree": {"min_bytes": 1000, "full_checkout_roles": ["video_editor"],
                        "keep_paths": [".claude/skills/*"]},
}


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@pytest.fixture()
def media_repo(tmp_path):
    """A repo with two large media files (one under a Thai name with a
    space), one large kept-path media file and a small text file."""
    src = tmp_path / "src"
    (src / "docs" / "r").mkdir(parents=True)
    (src / "a b").mkdir()
    (src / ".claude" / "skills" / "x").mkdir(parents=True)
    (src / "docs" / "r" / "big.mp4").write_bytes(os.urandom(5000))
    (src / "a b" / "ภาพ ใหญ่.png").write_bytes(os.urandom(5000))
    (src / ".claude" / "skills" / "x" / "tpl.png").write_bytes(os.urandom(5000))
    (src / "small.txt").write_text("hi\n")
    _git("init", "-q", "-b", "main", cwd=src)
    _git("add", "-A", cwd=src)
    _git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init", cwd=src)
    return src


@pytest.fixture()
def policy(monkeypatch):
    monkeypatch.setattr(worktree, "_load_storage_policy", lambda: POLICY)


def test_sparse_patterns_lists_large_media_by_exact_path(media_repo, policy):
    pats = worktree.sparse_patterns(media_repo, "main", "developer")
    assert pats[0] == "/*"
    assert sorted(pats[1:]) == ["!/a b/ภาพ ใหญ่.png", "!/docs/r/big.mp4"]


def test_sparse_patterns_empty_for_a_full_checkout_role(media_repo, policy):
    assert worktree.sparse_patterns(media_repo, "main", "video_editor") == []


def test_remote_sparse_file_written_from_the_local_clone(media_repo, policy, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "project_path_for_host", lambda p, h: str(media_repo))
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(delegate, "ROOT", tmp_path)
    task = {"id": "task-sp01", "project": "p", "owner_cto": None}
    path = delegate._remote_sparse_file(task, "developer", "main")
    assert path is not None and path.read_text(encoding="utf-8").splitlines()[0] == "/*"
    assert "!/docs/r/big.mp4" in path.read_text(encoding="utf-8")


def test_remote_sparse_file_none_without_a_local_clone(policy, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "project_path_for_host", lambda p, h: str(tmp_path / "nope"))
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    task = {"id": "task-sp02", "project": "p", "owner_cto": None}
    assert delegate._remote_sparse_file(task, "developer", "main") is None


def _run_launcher(tmp_path, media_repo, sparse_file: Path | None):
    """Run the real launcher from a throwaway agents_root with no roles/ dir:
    it creates the worktree, then stops at SPAWN_REFUSED=missing-role-docs,
    before tmux or claude are ever needed."""
    agents_root = tmp_path / "agents"
    launch = agents_root / ".launch"
    launch.mkdir(parents=True)
    shutil.copy(SCRIPT, launch / "spawn-worker-remote.sh")
    args = ["bash", str(launch / "spawn-worker-remote.sh"),
            "--task", "task-sp03", "--project", "proj", "--role", "developer",
            "--branch", "agent/developer-task-sp03", "--base", "main",
            "--repo-url", f"file://{media_repo}", "--repo-path", str(tmp_path / "clone"),
            "--worktree-root", str(tmp_path / "wts"), "--claude-args", "",
            "--model", "m", "--effort", "high", "--session-name", "s"]
    if sparse_file is not None:
        args += ["--sparse-file", str(sparse_file)]
    r = subprocess.run(args, input="prompt", capture_output=True, text=True, timeout=60)
    wt = tmp_path / "wts" / "proj__developer__task-sp03"
    return r, wt


def _files(wt: Path) -> list[str]:
    return sorted(str(p.relative_to(wt)) for p in wt.rglob("*")
                  if p.is_file() and ".git" not in p.parts and p.name != "TASK.md")


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_launcher_builds_a_sparse_worktree_from_the_file(tmp_path, media_repo, policy):
    sparse = tmp_path / "sparse.txt"
    sparse.write_text("\n".join(worktree.sparse_patterns(media_repo, "main", "developer")) + "\n",
                      encoding="utf-8")
    r, wt = _run_launcher(tmp_path, media_repo, sparse)
    assert "SPAWN_REFUSED=missing-role-docs" in r.stdout, r.stdout + r.stderr
    assert _files(wt) == [".claude/skills/x/tpl.png", "small.txt"]
    status = subprocess.run(["git", "-C", str(wt), "status", "--porcelain"],
                            capture_output=True, text=True).stdout
    assert [ln for ln in status.splitlines() if not ln.startswith("??")] == []
    assert not sparse.exists(), "the launcher deletes the list after use"
    # a NEW file under a directory that held an excluded file stays addable
    (wt / "docs" / "r").mkdir(parents=True, exist_ok=True)
    (wt / "docs" / "r" / "REPORT.md").write_text("x\n")
    subprocess.run(["git", "-C", str(wt), "add", "docs/r/REPORT.md"], check=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_launcher_without_a_file_checks_out_everything(tmp_path, media_repo):
    r, wt = _run_launcher(tmp_path, media_repo, None)
    assert "SPAWN_REFUSED=missing-role-docs" in r.stdout, r.stdout + r.stderr
    assert _files(wt) == [".claude/skills/x/tpl.png", "a b/ภาพ ใหญ่.png",
                          "docs/r/big.mp4", "small.txt"]


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_launcher_with_a_missing_file_checks_out_everything(tmp_path, media_repo):
    r, wt = _run_launcher(tmp_path, media_repo, tmp_path / "never-copied.txt")
    assert "SPAWN_REFUSED=missing-role-docs" in r.stdout, r.stdout + r.stderr
    assert "docs/r/big.mp4" in _files(wt)


def test_launcher_sets_gc_big_pack_threshold(tmp_path, media_repo):
    _run_launcher(tmp_path, media_repo, None)
    out = subprocess.run(["git", "-C", str(tmp_path / "clone"), "config", "gc.bigPackThreshold"],
                         capture_output=True, text=True).stdout.strip()
    assert out == "1g"


def test_windows_launcher_reads_and_deletes_the_sparse_file():
    ps1 = (ROOT / "windows" / "spawn-worker.ps1").read_text(encoding="utf-8")
    assert "[string]$SparseFile = ''" in ps1
    assert "sparse-checkout init --no-cone" in ps1
    assert "Remove-Item -Force -LiteralPath $SparseFile" in ps1
    assert "gc.bigPackThreshold 1g" in ps1

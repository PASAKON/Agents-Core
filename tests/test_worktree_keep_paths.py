"""sparse_worktree.keep_paths (ADR 0030, CTO 3d312dd6 review 2026-09-23):
large tracked media under a kept path stays on disk in a sparse worktree;
large media elsewhere is still excluded."""
from __future__ import annotations

import subprocess
from pathlib import Path

import tools.worktree as worktree_mod


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_keep_paths_keep_large_media_on_disk(tmp_path, monkeypatch):
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "config", "user.email", "t@t")
    _git(origin, "config", "user.name", "t")
    big = b"0" * 400_000
    for rel in ("knowledge/ref/big.png", "docs/reports/big.png", ".claude/skills/x/template/big.mp4"):
        p = origin / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(big)
    (origin / "src.py").write_text("x = 1\n")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "init")
    repo = tmp_path / "repo"
    subprocess.run(["git", "clone", "-q", str(origin), str(repo)], check=True, capture_output=True)

    policy = tmp_path / "storage-policy.yaml"
    policy.write_text(
        "media_guard:\n  extensions: [png, mp4]\n"
        "sparse_worktree:\n  min_bytes: 262144\n  full_checkout_roles: []\n"
        "  keep_paths: [\".claude/skills/*\", \"knowledge/*\"]\n")
    monkeypatch.setattr(worktree_mod, "STORAGE_POLICY", policy)
    monkeypatch.setattr(worktree_mod, "WORKTREE_DIR", tmp_path / "worktrees")
    monkeypatch.setattr(worktree_mod, "get_project",
                        lambda key: {"path": str(repo), "default_branch": "main"})

    wt = Path(worktree_mod.create_worktree("p", "developer", "task-keep0001", sparse=True)["worktree"])

    assert (wt / "knowledge/ref/big.png").exists()
    assert (wt / ".claude/skills/x/template/big.mp4").exists()
    assert not (wt / "docs/reports/big.png").exists()
    assert (wt / "src.py").exists()

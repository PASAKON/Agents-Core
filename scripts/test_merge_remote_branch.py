"""tools.git_ops._resolve_merge_ref + _touches_violation(ref=...) — merging a
branch a REMOTE worker pushed (only `origin/<branch>` exists on the hub).

Born 2026-09-18: the first E2E winbox worker (task-95803168) pushed its branch
from the box and merge_task failed with `not something we can merge` because
it merged the local branch name. Real temp repos, no mocks.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.git_ops import GitOpsError, _resolve_merge_ref, _touches_violation

BR = "agent/developer-task-rmt"


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", *args],
        cwd=str(cwd), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def repos(tmp_path):
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    seed = tmp_path / "seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    (seed / "README.md").write_text("seed\n")
    _git(seed, "add", "README.md"); _git(seed, "commit", "-qm", "seed")
    _git(seed, "push", "-q", "origin", "HEAD:main")
    hub = tmp_path / "hub"
    _git(tmp_path, "clone", "-q", str(origin), str(hub))
    # "winbox": a separate clone pushes the worker branch; hub never sees it locally.
    box = tmp_path / "box"
    _git(tmp_path, "clone", "-q", str(origin), str(box))
    _git(box, "checkout", "-qb", BR)
    (box / "docs").mkdir(); (box / "docs" / "x.md").write_text("remote work\n")
    (box / "REPORT.md").write_text("# REPORT task-rmt\n")
    _git(box, "add", "-A"); _git(box, "commit", "-qm", "remote: work")
    _git(box, "push", "-q", "origin", BR)
    return hub


def test_prefers_local_branch_when_it_exists(repos):
    hub = repos
    _git(hub, "checkout", "-qb", BR)
    _git(hub, "checkout", "-q", "main")
    assert _resolve_merge_ref(hub, BR) == BR


def test_falls_back_to_origin_ref_after_fetch(repos):
    hub = repos
    assert _git(hub, "branch", "--list", BR) == ""  # no local branch
    assert _resolve_merge_ref(hub, BR) == f"origin/{BR}"
    _git(hub, "rev-parse", "--verify", f"refs/remotes/origin/{BR}")  # fetched


def test_raises_when_branch_exists_nowhere(repos):
    with pytest.raises(GitOpsError, match="neither locally nor on origin"):
        _resolve_merge_ref(repos, "agent/developer-task-ghost")


def test_origin_ref_actually_merges(repos):
    hub = repos
    ref = _resolve_merge_ref(hub, BR)
    _git(hub, "merge", "--no-ff", "-qm", "merge", ref)
    assert (hub / "docs" / "x.md").read_text() == "remote work\n"


def test_touches_violation_against_a_fetched_ref(repos):
    hub = repos
    ref = _resolve_merge_ref(hub, BR)
    assert _touches_violation(str(hub), "main", ["docs/", "REPORT.md"], ref=ref) == []
    assert _touches_violation(str(hub), "main", ["docs/"], ref=ref) == ["REPORT.md"]


def test_drop_channel_files_removes_only_what_the_merge_added(repos):
    from tools.git_ops import _drop_channel_files
    hub = repos
    pre = _git(hub, "rev-parse", "HEAD")
    ref = _resolve_merge_ref(hub, BR)
    _git(hub, "merge", "--no-ff", "-qm", "merge", ref)
    assert (hub / "REPORT.md").exists()
    assert _drop_channel_files(hub, pre) == ["REPORT.md"]
    assert not (hub / "REPORT.md").exists()
    assert (hub / "docs" / "x.md").exists()          # real content untouched
    assert _git(hub, "status", "--porcelain") == ""   # removal is committed
    assert "drop worker channel file" in _git(hub, "log", "-1", "--format=%s")


def test_drop_channel_files_keeps_a_preexisting_one(repos):
    from tools.git_ops import _drop_channel_files
    hub = repos
    (hub / "BLOCKER.md").write_text("pre-existing on main\n")
    _git(hub, "add", "BLOCKER.md"); _git(hub, "commit", "-qm", "base has BLOCKER.md")
    pre = _git(hub, "rev-parse", "HEAD")
    _git(hub, "merge", "--no-ff", "-qm", "merge", _resolve_merge_ref(hub, BR))
    assert _drop_channel_files(hub, pre) == ["REPORT.md"]
    assert (hub / "BLOCKER.md").exists()

"""lib.org_tools_registry._h_review_diff — host-aware diff (Org Mesh W0.2,
task-ae3f22e3 round 2).

review_diff must work from a worker's PUBLISHED branch alone -- a Contabo
or winbox worker's `worktree` path only exists on that worker's own host,
never on the hub. Diffs from this host's runtime checkout
(`_repo_path_for_host`) using `_resolve_merge_ref` (local branch ref when
present, `origin/<branch>` fallback otherwise) -- never the task's own
`worktree` directory.

Uses the root conftest.py `fake_projects` fixture (bare origin + a clone
standing in for the runtime checkout, wired into lib.config's project
registry) -- never the real repo, origin, or tasks.db (ADR 0021).

Run via:  pytest tests/test_review_diff_origin.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
from lib.org_tools_registry import _h_review_diff  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@x", *args],
        cwd=str(cwd), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _make_task(*, worktree: str, branch: str) -> str:
    tid = db_mod.create_task(project="test-project", role="developer",
                             title="review_diff origin test", description="d")
    db_mod.update_status(tid, "review", actor="test", worktree=worktree, branch=branch)
    return tid


def test_review_diff_branch_only_on_origin(fake_projects, temp_db, tmp_path):
    """A remote worker (winbox/Contabo) pushed its branch straight to
    origin; it never exists in this host's runtime clone, and the task's
    `worktree` field names a path meaningless on this host. review_diff
    must still produce the diff from the published branch alone."""
    origin = fake_projects["origin"]
    branch = "agent/developer-remote-task"

    remote_worker = tmp_path / "remote-worker-clone"
    _git(tmp_path, "clone", "-q", str(origin), str(remote_worker))
    _git(remote_worker, "checkout", "-q", "-b", branch)
    (remote_worker / "feature.txt").write_text("hello from a remote worker\n")
    _git(remote_worker, "add", "-A")
    _git(remote_worker, "commit", "-q", "-m", "feature: feature.txt")
    _git(remote_worker, "push", "-q", "origin", branch)

    tid = _make_task(worktree="/nonexistent/worktree/not/on/this/host", branch=branch)

    stat = _h_review_diff(task_id=tid)
    assert "feature.txt" in stat

    full = _h_review_diff(task_id=tid, full=True)
    assert "hello from a remote worker" in full


def test_review_diff_no_remote_project_diffs_local_branch(fake_projects, temp_db):
    """A project with no origin remote diffs the local branch directly --
    the pre-W0.2 behaviour, still exercised through the new host-aware
    code path (no fetch, base_ref == base)."""
    runtime = fake_projects["runtime"]
    del fake_projects["proj"]["remote"]

    branch = "agent/developer-local-task"
    _git(runtime, "checkout", "-q", "-b", branch)
    (runtime / "local.txt").write_text("no remote here\n")
    _git(runtime, "add", "-A")
    _git(runtime, "commit", "-q", "-m", "feature: local.txt")
    _git(runtime, "checkout", "-q", "main")

    tid = _make_task(worktree=str(runtime), branch=branch)

    stat = _h_review_diff(task_id=tid)
    assert "local.txt" in stat

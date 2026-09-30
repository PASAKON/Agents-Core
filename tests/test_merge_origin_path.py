"""tools.git_ops / tools.revert_task — host-aware merge via temp worktree
(Org Mesh W0.2, docs/design/org-mesh.md C5, task-ae3f22e3).

Root causes this closes:
  - a Mac live checkout diverged ~150 commits from origin, stranding merges
    that were still keyed off the local checkout's own HEAD
  - a weekly cron dirtying a tracked state file on Contabo caused
    `base_dirty` refusals even though the incoming branch never touched
    that file
  - `proj["path"]` is a Mac-only path, breaking merges run from any other
    host

Fix: on a project with an origin remote, the merge itself happens in a
throwaway detached worktree of `origin/<base>` — never in the host's live
runtime checkout — then pushes, then best-effort fast-forwards the runtime
checkout with `git merge --ff-only`, letting git itself decide whether a
dirty/diverged checkout can advance instead of special-casing each case.

Uses the root conftest.py `fake_projects` fixture (bare origin + a clone
standing in for the runtime checkout, wired into lib.config's project
registry) — never the real repo, origin, or tasks.db (ADR 0021).

Run via:  pytest tests/test_merge_origin_path.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
from tools import git_ops  # noqa: E402
from tools import revert_task as revert_mod  # noqa: E402


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


def _make_task(*, touches: list[str] | None = None) -> str:
    tid = db_mod.create_task(project="test-project", role="developer",
                             title="origin-path merge test", description="d",
                             touches=touches)
    db_mod.update_status(tid, "review", actor="test")
    return tid


def _make_branch(runtime: Path, tid: str, filename: str, content: str) -> str:
    """Local branch on top of runtime's current `main`, like a Mac worker's
    own worktree would leave one (branch exists locally in the hub clone)."""
    branch = f"agent/developer-{tid}"
    _git(runtime, "checkout", "-q", "-b", branch)
    (runtime / filename).write_text(content)
    _git(runtime, "add", "-A")
    _git(runtime, "commit", "-q", "-m", f"feature: {filename}")
    _git(runtime, "checkout", "-q", "main")
    return branch


def _origin_main_sha(origin: Path, tmp_path: Path, tag: str) -> str:
    peek = tmp_path / f"peek-{tag}"
    _git(tmp_path, "clone", "-q", str(origin), str(peek))
    return _git(peek, "rev-parse", "main")


# --------------------------------------------------------------- merge: clean


def test_merge_clean_runtime_pushes_and_fast_forwards(fake_projects, temp_db):
    runtime = fake_projects["runtime"]
    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert result["runtime_updated"] is True
    assert result["runtime_reason"] is None
    assert result["host"] in fake_projects["proj"]["paths"]
    merge_sha = result["merge_sha"]
    assert _git(runtime, "rev-parse", "HEAD") == merge_sha  # runtime ff'd in place
    assert (runtime / "feature.txt").exists()
    assert db_mod.get_task(tid)["status"] == "done"


# ------------------------------------------------- merge: unrelated dirty file


def test_merge_unrelated_dirty_file_still_fast_forwards(fake_projects, temp_db):
    runtime = fake_projects["runtime"]
    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")

    # a concurrent session's uncommitted edit the branch never touches
    (runtime / "README.md").write_text("dirty local edit\n")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is True
    assert result["runtime_reason"] is None
    assert (runtime / "feature.txt").exists()  # merge landed
    # the unrelated dirty file survived the fast-forward, untouched
    assert (runtime / "README.md").read_text() == "dirty local edit\n"
    assert "README.md" in _git(runtime, "status", "--porcelain")


# ------------------------------------------- merge: incoming touches dirty file


def test_merge_incoming_collides_with_dirty_file_skips_ff(fake_projects, temp_db):
    runtime = fake_projects["runtime"]
    tid = _make_task()
    _make_branch(runtime, tid, "README.md", "branch version\n")

    # runtime has its OWN uncommitted edit to the same file the branch changes
    (runtime / "README.md").write_text("local uncommitted edit\n")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is False
    assert result["runtime_reason"]  # git's own refusal reason, non-empty
    # git refused cleanly -- local uncommitted edit is untouched
    assert (runtime / "README.md").read_text() == "local uncommitted edit\n"


# ------------------------------------------------------- merge: diverged runtime


def test_merge_diverged_runtime_skips_ff_local_commit_untouched(fake_projects, temp_db):
    runtime = fake_projects["runtime"]
    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")

    # runtime's local main has a commit origin never saw -- a real divergence,
    # not just a dirty working tree.
    (runtime / "local-only.txt").write_text("never pushed\n")
    _git(runtime, "add", "local-only.txt")
    _git(runtime, "commit", "-q", "-m", "local-only commit, never pushed")
    local_sha = _git(runtime, "rev-parse", "HEAD")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is False
    assert result["runtime_reason"]
    # runtime's local commit is exactly where it was -- nothing rewritten
    assert _git(runtime, "rev-parse", "HEAD") == local_sha
    assert (runtime / "local-only.txt").exists()


# --------------------------------------- merge: origin moves between fetch/push


def test_merge_origin_moves_between_fetch_and_push_retries_and_lands_both(
    fake_projects, temp_db, monkeypatch, tmp_path
):
    runtime = fake_projects["runtime"]
    origin = fake_projects["origin"]
    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")

    real_create = git_ops._create_temp_worktree

    def wrapped_create(repo, ref, *, prefix):
        wt = real_create(repo, ref, prefix=prefix)
        # a rival pushes to origin right after our temp worktree was cut
        # from the old origin/<base> tip -- the race merge_task's push
        # retry (fetch + merge --no-edit + retry) exists to handle.
        rival = tmp_path / "rival"
        _git(tmp_path, "clone", "-q", str(origin), str(rival))
        (rival / "rival.txt").write_text("rival work\n")
        _git(rival, "add", "rival.txt")
        _git(rival, "commit", "-q", "-m", "rival concurrent commit")
        _git(rival, "push", "-q", "origin", "main")
        return wt

    monkeypatch.setattr(git_ops, "_create_temp_worktree", wrapped_create)

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["pushed"] is True
    assert result["on_origin"] is True
    assert result.get("integrated") is True
    final_sha = _origin_main_sha(origin, tmp_path, "after")
    log = _git(runtime, "log", final_sha, "--format=%H")
    assert final_sha in log
    # both changes landed on origin -- fetch and inspect the tree at the tip
    _git(runtime, "fetch", "-q", "origin", "main")
    tree = _git(runtime, "ls-tree", "-r", "--name-only", "origin/main")
    assert "rival.txt" in tree
    assert "feature.txt" in tree


# -------------------------------------------------------------- merge: conflict


def test_merge_conflict_nothing_pushed(fake_projects, temp_db, monkeypatch, tmp_path):
    runtime = fake_projects["runtime"]
    origin = fake_projects["origin"]
    tid = _make_task()
    _make_branch(runtime, tid, "README.md", "branch version\n")

    # a rival lands a conflicting change to the same file on origin first
    rival = tmp_path / "rival-conflict"
    _git(tmp_path, "clone", "-q", str(origin), str(rival))
    (rival / "README.md").write_text("rival conflicting version\n")
    _git(rival, "add", "README.md")
    _git(rival, "commit", "-q", "-m", "rival conflicting commit")
    _git(rival, "push", "-q", "origin", "main")
    origin_before = _origin_main_sha(origin, tmp_path, "before-conflict")

    monkeypatch.setattr("tools.gh_issue.create_issue", lambda *a, **k: "http://fake/issue/1")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is False
    assert result["conflict"] is True
    assert "README.md" in result["files"]
    assert result["issue"] == "http://fake/issue/1"
    assert db_mod.get_task(tid)["status"] == "conflict"
    assert _origin_main_sha(origin, tmp_path, "after-conflict") == origin_before


# ----------------------------------------------------- merge: touches violation


def test_merge_touches_violation_refused_before_any_push(fake_projects, temp_db, tmp_path):
    runtime = fake_projects["runtime"]
    origin = fake_projects["origin"]
    tid = _make_task(touches=["docs/"])
    _make_branch(runtime, tid, "feature.txt", "hello\n")
    origin_before = _origin_main_sha(origin, tmp_path, "before-touches")

    # merge_task needs a truthy "worktree" on the task row to run the
    # touches gate at all. Point it at a path that does NOT exist, like a
    # remote (winbox/Contabo) worker's worktree on another box -- exercises
    # the "diff the fetched ref inside the hub clone" branch, which is the
    # one the origin/<base> base_ref fix actually applies to.
    db_mod.update_status(tid, "review", actor="test",
                         worktree=str(runtime / "nonexistent-remote-worktree"))

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is False
    assert result["touches_violation"] is True
    assert "feature.txt" in result["extra_files"]
    assert _origin_main_sha(origin, tmp_path, "after-touches") == origin_before


# --------------------------------------------------------- merge: no-origin path


def test_merge_no_origin_project_keeps_old_local_path(fake_projects, temp_db):
    """proj has no `remote` key -- has_origin False, old in-place merge path."""
    runtime = fake_projects["runtime"]
    proj = fake_projects["proj"]
    del proj["remote"]  # fake_projects' projects() lambda closes over this dict

    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")
    # old path merges the LOCAL branch directly into runtime's own checkout
    _git(runtime, "checkout", "-q", "main")

    result = git_ops.merge_task(tid, cleanup=False)

    assert result["merged"] is True
    assert result["runtime_updated"] is True
    assert result["runtime_reason"] is None
    assert (runtime / "feature.txt").exists()
    assert _git(runtime, "status", "--porcelain") == ""


# --------------------------------------------------------------- revert: shared


def _land_merge(fake_projects, temp_db) -> tuple[str, str]:
    """Merge a clean branch via the origin path, return (task_id, merge_sha)."""
    runtime = fake_projects["runtime"]
    tid = _make_task()
    _make_branch(runtime, tid, "feature.txt", "hello\n")
    result = git_ops.merge_task(tid, cleanup=False)
    assert result["merged"] and result["pushed"]
    return tid, result["merge_sha"]


# ------------------------------------------------------------- revert: clean


def test_revert_clean_runtime_fast_forwards(fake_projects, temp_db):
    tid, merge_sha = _land_merge(fake_projects, temp_db)
    runtime = fake_projects["runtime"]

    result = revert_mod.revert_task(tid)

    assert result["reverted"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is True
    assert result["runtime_reason"] is None
    assert not (runtime / "feature.txt").exists()  # revert landed on runtime
    assert db_mod.get_task(tid)["status"] == "reverted"


# ---------------------------------------------------------- revert: diverged


def test_revert_diverged_runtime_skips_ff(fake_projects, temp_db):
    tid, merge_sha = _land_merge(fake_projects, temp_db)
    runtime = fake_projects["runtime"]

    (runtime / "local-only.txt").write_text("never pushed\n")
    _git(runtime, "add", "local-only.txt")
    _git(runtime, "commit", "-q", "-m", "local-only, never pushed")
    local_sha = _git(runtime, "rev-parse", "HEAD")

    result = revert_mod.revert_task(tid)

    assert result["reverted"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is False
    assert result["runtime_reason"]
    assert _git(runtime, "rev-parse", "HEAD") == local_sha
    assert (runtime / "local-only.txt").exists()


# ------------------------------------------------------------- rollback: origin


def test_rollback_origin_path_pushes_and_fast_forwards(fake_projects, temp_db):
    from tools import rollback as rollback_mod

    tid, merge_sha = _land_merge(fake_projects, temp_db)
    runtime = fake_projects["runtime"]

    result = rollback_mod.rollback(tid)

    assert result["rolled_back"] is True
    assert result["pushed"] is True
    assert result["runtime_updated"] is True
    assert result["runtime_reason"] is None
    assert not (runtime / "feature.txt").exists()  # revert landed on runtime
    assert db_mod.get_task(tid)["status"] == "cancelled"

"""GH #158 part 1: reopen_task must put the CTO's feedback in the worker's TASK.md.

The worker re-reads TASK.md on a reopen, not the DB. Order matters: newest
instruction first, "supersedes everything below" (task-cda4f469 acted on stale
rules read top-down). A removed worktree must not be recreated.
"""
from lib import db
from lib.org_tools_registry import _h_reopen_task
from tools.inject_prompt import _build_task_md, _write_task_md


def _task(tmp_path, monkeypatch, worktree):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()
    tid = db.create_task(project="testproj", role="dev", title="T", description="initial brief", owner_cto=None)
    db.update_status(tid, "done", worktree=str(worktree), iteration=1, force=True)
    return tid


def test_reopen_rewrites_taskmd_feedback_first(tmp_path, monkeypatch):
    wt = tmp_path / "wt"
    wt.mkdir()
    tid = _task(tmp_path, monkeypatch, wt)
    _write_task_md(str(wt), _build_task_md(db.get_task(tid)))

    _h_reopen_task(task_id=tid, feedback="Please add more tests.")

    md = (wt / "TASK.md").read_text(encoding="utf-8")
    assert "Please add more tests." in md
    assert "supersedes everything below" in md
    assert "initial brief" in md
    assert md.index("Please add more tests.") < md.index("initial brief")   # newest first
    assert db.get_task(tid)["iteration"] == 2


def test_reopen_does_not_recreate_a_removed_worktree(tmp_path, monkeypatch):
    gone = tmp_path / "removed-by-merge_task"
    tid = _task(tmp_path, monkeypatch, gone)
    _h_reopen_task(task_id=tid, feedback="x")
    assert not gone.exists()

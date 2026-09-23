"""GH #158 part 3: reopen_task + delegate_task on a worker that is still running.

Before the fix the row sat pending/unassigned, the spawn claimed nothing
(tmux.create no-ops on an existing session; the iTerm path reuses the tab and
skips the kickoff), and _verify_claimed marked the live worker `failed` 25 s
later. Measured 3x in 7 days: task-a63759d5, task-adbc6f43, task-ad534f86.

Every test enters through the production door -- `_h_reopen_task` then
`delegate_task` -- not through the helper, so a delegate_task that stops
calling _resume_live_worker fails here.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.send_to_worker as send_to_worker  # noqa: E402
from lib.org_tools_registry import _h_reopen_task  # noqa: E402


@pytest.fixture()
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(delegate, "_scope_owners", lambda feature: [])
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    monkeypatch.setattr(delegate, "get_project", lambda key: {
        "path": "/tmp/does-not-matter", "default_branch": "main",
        "agents_allowed": ["developer"], "spawn_backend": "iterm",
        "web_ui": "off",
    })
    db_mod.init()

    rec = {"spawned": [], "sent": [], "background": []}

    def fake_spawn(role, task_id, **kw):
        rec["spawned"].append(task_id)
        return "spawned"

    def fake_send(task_id, message):
        rec["sent"].append((task_id, message))
        return f"queued to developer ({task_id})"

    def fake_background(coro):
        rec["background"].append(coro.__name__)
        coro.close()

    monkeypatch.setattr(delegate, "_spawn_iterm_tab", fake_spawn)
    monkeypatch.setattr(send_to_worker, "send", fake_send)
    monkeypatch.setattr(delegate, "_spawn_background", fake_background)
    rec["worktree"] = tmp_path / "wt"
    rec["worktree"].mkdir()
    return rec


def _done_task(env, *, pid, tmux_session=None) -> str:
    tid = db_mod.create_task(project="test-project", role="developer",
                             title="reopen test", description="initial brief",
                             owner_cto="owner")
    db_mod.update_status(tid, "done", worktree=str(env["worktree"]),
                         assigned_agent="developer", pid=pid,
                         tmux_session=tmux_session, iteration=1, force=True)
    return tid


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def test_reopen_on_live_worker_restores_claim_and_does_not_spawn(env):
    tid = _done_task(env, pid=os.getpid())
    _h_reopen_task(task_id=tid, feedback="Please add more tests.")
    assert db_mod.get_task(tid)["status"] == "pending"

    asyncio.run(delegate.delegate_task(tid))

    t = db_mod.get_task(tid)
    assert t["status"] == "in_progress"
    assert t["assigned_agent"] == "developer"
    assert env["spawned"] == []                      # no second worker
    assert "_verify_claimed" not in env["background"]  # nothing can mark it failed
    assert len(env["sent"]) == 1
    sent_tid, msg = env["sent"][0]
    assert sent_tid == tid
    assert "reopened" in msg and "TASK.md" in msg and "iteration 2" in msg
    assert "claim restored" in t["delegate_log"]


def test_reopen_on_dead_worker_spawns_as_before(env):
    tid = _done_task(env, pid=_dead_pid())
    _h_reopen_task(task_id=tid, feedback="x")

    asyncio.run(delegate.delegate_task(tid))

    assert env["spawned"] == [tid]
    assert "_verify_claimed" in env["background"]
    assert db_mod.get_task(tid)["status"] == "pending"   # the new worker claims


def test_live_pid_without_its_tmux_session_is_not_trusted(env, monkeypatch):
    """A recycled pid: something is alive under that number, but the worker's
    tmux session is gone. Must spawn, not hand the task to a stranger."""
    monkeypatch.setattr(delegate.tmux, "has_session", lambda name: False)
    tid = _done_task(env, pid=os.getpid(), tmux_session="dev-gone")
    _h_reopen_task(task_id=tid, feedback="x")

    asyncio.run(delegate.delegate_task(tid))

    assert env["sent"] == []
    assert env["spawned"] == [tid]


def test_live_pid_with_its_tmux_session_is_resumed(env, monkeypatch):
    monkeypatch.setattr(delegate.tmux, "has_session", lambda name: name == "dev-live")
    tid = _done_task(env, pid=os.getpid(), tmux_session="dev-live")
    _h_reopen_task(task_id=tid, feedback="x")

    asyncio.run(delegate.delegate_task(tid))

    assert env["spawned"] == []
    assert db_mod.get_task(tid)["status"] == "in_progress"


def test_mailbox_failure_keeps_the_claim_and_says_so(env, monkeypatch):
    def boom(task_id, message):
        raise OSError("disk full")
    monkeypatch.setattr(send_to_worker, "send", boom)
    tid = _done_task(env, pid=os.getpid())
    _h_reopen_task(task_id=tid, feedback="x")

    asyncio.run(delegate.delegate_task(tid))

    t = db_mod.get_task(tid)
    assert t["status"] == "in_progress"
    assert env["spawned"] == []
    assert "FAILED" in t["delegate_log"] and "disk full" in t["delegate_log"]

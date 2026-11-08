"""Tests for the 7 Agent Audit Hardening & Efficiency Upgrades:
1. Hub DB Queue Sync (`tools/host_queue.py`)
2. Multi-Slot Non-Blocking `host_queue.drain()` (no Head-of-Line blocking)
3. Watchdog Auto-Self-Heal (1-Retry with Git checkpoint + spillover on dead PID)
4. Windows Cross-Platform File Lock (`msvcrt` fallback in `tools/mail_wake.py`)
5. Real-Time Cross-Host Quota Cooldown Sharing (`tools/ph_brain.py`)
6. Smart Worker Timeout (`FAST_DEAD_STALL_AFTER_S = 10 min` for dead code workers vs `30 min` for renders)
7. Post-Merge `Work/<task-id>/tmp/` Cleanup (`tools/git_ops.py`)
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from runners import watchdog
from tools import delegate, host_queue, mail_wake, ph_brain


@pytest.fixture
def mem_locks_db(monkeypatch, tmp_path):
    db_file = tmp_path / "hub_locks.db"

    @contextmanager
    def _conn():
        with sqlite3.connect(db_file) as c:
            c.row_factory = sqlite3.Row
            yield c

    with _conn() as c:
        c.execute("CREATE TABLE locks (key TEXT PRIMARY KEY, owner TEXT, expires_at TEXT)")
    monkeypatch.setattr(host_queue.db, "get_conn", _conn)
    from lib import db as lib_db
    monkeypatch.setattr(lib_db, "get_conn", _conn)
    return _conn


def test_host_queue_multi_slot_drain_skips_head_of_line_blocker(monkeypatch, tmp_path):
    """When task-1 is blocked (still pending after delegate_task), `host_queue.drain()`
    spawns task-2 and task-3 in the SAME pass instead of stalling them for 10-15 minutes."""
    qpath = tmp_path / "queue.jsonl"
    monkeypatch.setattr(host_queue, "QUEUE_PATH", qpath)

    tasks = {
        "task-1": {"id": "task-1", "status": "pending", "owner_cto": "cto-1", "host": "winbox"},
        "task-2": {"id": "task-2", "status": "pending", "owner_cto": "cto-1", "host": "mac"},
        "task-3": {"id": "task-3", "status": "pending", "owner_cto": "cto-1", "host": "contabo"},
    }
    monkeypatch.setattr(host_queue.db, "get_task", lambda tid: tasks.get(tid))

    async def fake_delegate(tid, host=None):
        if tid == "task-1":
            # Still blocked on winbox
            return {"id": tid, "status": "pending", "host": host}
        tasks[tid]["status"] = "in_progress"
        return {"id": tid, "status": "in_progress", "host": host}

    monkeypatch.setattr(delegate, "delegate_task", fake_delegate)

    host_queue.enqueue("task-1", "cto-1", host="winbox")
    host_queue.enqueue("task-2", "cto-1", host="mac")
    host_queue.enqueue("task-3", "cto-1", host="contabo")

    asyncio.run(host_queue.drain())

    remaining = host_queue.load()
    assert [e["task_id"] for e in remaining] == ["task-1"]
    assert tasks["task-2"]["status"] == "in_progress"
    assert tasks["task-3"]["status"] == "in_progress"


def test_host_queue_hub_db_sync(monkeypatch, tmp_path, mem_locks_db):
    """When `ORG_HUB_QUEUE_SYNC=1`, `host_queue` mirrors entries to the Hub DB `locks`
    table so Contabo 24/7 can drain tasks queued from a sleeping Mac."""
    qpath = tmp_path / "queue.jsonl"
    monkeypatch.setattr(host_queue, "QUEUE_PATH", qpath)
    monkeypatch.setattr(host_queue, "_DEFAULT_QUEUE_PATH", qpath)
    monkeypatch.setenv("ORG_HUB_QUEUE_SYNC", "1")

    host_queue.enqueue("task-hub1", "cto-mac", host="contabo")
    hub_items = host_queue._hub_entries()
    assert len(hub_items) == 1
    assert hub_items[0]["task_id"] == "task-hub1"

    host_queue.remove("task-hub1")
    assert host_queue._hub_entries() == []


def test_watchdog_auto_self_heal_dead_worker_once(monkeypatch):
    """When a worker dies (`pid_alive=False`), `_auto_heal_stalled_workers` checkpoints
    its worktree, resets status to `pending`, re-delegates once, and notifies the owner."""
    monkeypatch.setenv("ORG_WATCHDOG_AUTO_HEAL", "1")

    task_row = {
        "id": "task-dead01",
        "project": "mooniex-agents",
        "role": "developer",
        "status": "stalled",
        "host": "contabo",
        "branch": "agent/developer-task-dead01",
        "worktree": "/tmp/fake-wt",
        "description": "Build module",
        "owner_cto": "cto-main",
        "owner_role": "cto",
        "review": json.dumps({"watchdog": "stalled", "pid_alive": False}),
    }
    monkeypatch.setattr(watchdog.db, "get_task", lambda tid: task_row)

    updates: list[tuple] = []

    def fake_update_status(tid, status, **kw):
        task_row["status"] = status
        task_row.update(kw)
        updates.append((tid, status, kw))

    monkeypatch.setattr(watchdog.db, "update_status", fake_update_status)

    from tools import relocate_task as relocate_mod
    monkeypatch.setattr(
        relocate_mod,
        "checkpoint_source_worktree",
        lambda t, dst: {"checkpointed": True, "branch": t.get("branch")},
    )

    delegated: list[tuple] = []

    async def fake_delegate(tid, host=None):
        delegated.append((tid, host))
        return {"id": tid, "status": "in_progress", "host": "mac"}

    monkeypatch.setattr(watchdog.delegate, "delegate_task", fake_delegate)

    notified: list[tuple] = []
    monkeypatch.setattr(
        watchdog.send_to_cto,
        "send",
        lambda tid, msg, **kw: notified.append((tid, msg)),
    )

    stalled_list = [{"task": "task-dead01", "pid_alive": False, "silent_s": 650}]
    healed = watchdog._auto_heal_stalled_workers(stalled_list)
    assert len(healed) == 1
    assert healed[0] == {"task": "task-dead01", "from_host": "contabo", "to_host": "mac"}
    assert "origin/agent/developer-task-dead01" in task_row["description"]
    assert len(notified) == 1
    assert "auto-healed (1/1)" in notified[0][1]

    # Second call on the same task must NOT heal again (1-retry cap)
    healed_again = watchdog._auto_heal_stalled_workers(stalled_list)
    assert healed_again == []


def test_windows_msvcrt_lock_fallback_in_mail_wake(monkeypatch, tmp_path):
    """When `fcntl` is None (Windows / winbox) and `msvcrt` is available, `_agy_flock`
    and `_flock` acquire and release locks cleanly without raising ValueError."""
    locked_fds: list[int] = []
    fake_msvcrt = SimpleNamespace(
        LK_NBLCK=2,
        locking=lambda fd, mode, nbytes: locked_fds.append(fd),
    )
    monkeypatch.setattr(mail_wake, "fcntl", None)
    monkeypatch.setattr(mail_wake, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(mail_wake, "AGY_SESSIONS_DIR", tmp_path)

    with mail_wake._agy_flock("cto-winbox01") as got:
        assert got is True
    assert len(locked_fds) == 1


def test_cross_host_shared_quota_cooldown(monkeypatch, mem_locks_db):
    """When one host records a quota cooldown on `claude-opus-5-5-medium`,
    `select_model_chain(..., check_shared_cooldown=True)` immediately places
    `gemini-4-argon-high` first across all hosts."""
    ok = ph_brain.record_shared_model_cooldown("claude-opus-5-5-medium", ttl_s=1800)
    assert ok is True
    cooled = ph_brain.get_shared_cooldown_models()
    assert "claude-opus-5-5-medium" in cooled

    chain = ph_brain.select_model_chain(
        "claude-opus-5-5-medium",
        check_shared_cooldown=True,
    )
    assert chain[0] == "gemini-4-argon-high"
    assert "claude-opus-5-5-medium" in chain  # kept at tail as last-resort fallback


def test_smart_stall_timeout_fast_code_vs_long_render(monkeypatch):
    """With `ORG_SMART_STALL_TIMEOUT=1`, a dead code worker triggers at 10 minutes
    (600s) while a live worker or a video/render/browser job keeps 30 minutes (1800s)."""
    monkeypatch.setenv("ORG_SMART_STALL_TIMEOUT", "1")
    code_task = {"id": "task-c1", "role": "developer", "project": "mooniex-agents", "description": "Fix unit test"}
    video_task = {"id": "task-v1", "role": "video_editor", "project": "CnDrama", "description": "Cut EP05"}

    assert watchdog._stall_threshold_seconds(code_task, pid_alive=False) == 600.0
    assert watchdog._stall_threshold_seconds(code_task, pid_alive=True) == 1800.0
    assert watchdog._stall_threshold_seconds(video_task, pid_alive=False) == 1800.0

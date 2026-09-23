"""tools/disk_queue.py — FIFO queue for ADR 0030 disk-floor-refused tasks
(task-dbe47b9b), plus its wiring into tools/delegate.py's refusal path,
runners/watchdog.py's drain, and tools/gc_stale_tasks.py's 30-minute
stale-pending reaper.

Every module-level test passes its own `path=tmp_path/...` — never the real
state/disk_queue.jsonl. Every integration test (delegate/watchdog/gc)
monkeypatches `disk_queue.QUEUE_PATH` to a tmp_path file for the same
reason, plus `db_mod.DB_PATH` for a temp tasks.db (test_delegate_disk_floor
.py's own `temp_db` fixture, mirrored here), free space
(`delegate._free_gb`/`_disk_orange_floor_gb`), `delegate.delegate_task`
(never a real spawn), and `send_to_cto.send` (never a real mailbox write —
though conftest's `_isolate_org_root` would make one harmless anyway).

Run via:  pytest tests/test_disk_queue.py
(collected by the default `pytest` run — pytest.ini testpaths includes
`tests` alongside `scripts lib`.)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402
import tools.disk_queue as disk_queue  # noqa: E402
import tools.gc_stale_tasks as gc_stale_tasks  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402


# ---------------------------------------------------------------------------
# Pure module tests — disk_queue.py itself, each with its own tmp file.
# ---------------------------------------------------------------------------

def test_enqueue_fifo_order(tmp_path):
    p = tmp_path / "disk_queue.jsonl"
    disk_queue.enqueue("task-11111111", "cto-a", path=p)
    disk_queue.enqueue("task-22222222", "cto-b", path=p)
    disk_queue.enqueue("task-33333333", "cto-c", path=p)

    ids = [e["task_id"] for e in disk_queue.all_entries(path=p)]
    assert ids == ["task-11111111", "task-22222222", "task-33333333"]
    assert disk_queue.peek(path=p)["task_id"] == "task-11111111"


def test_enqueue_returns_ahead_count(tmp_path):
    p = tmp_path / "disk_queue.jsonl"
    assert disk_queue.enqueue("task-11111111", "cto-a", path=p) == 0
    assert disk_queue.enqueue("task-22222222", "cto-a", path=p) == 1
    assert disk_queue.enqueue("task-33333333", "cto-a", path=p) == 2


def test_enqueue_is_idempotent(tmp_path):
    """Re-refusing an already-queued task (a caller retrying by hand before
    the watchdog ever pops it) must not duplicate the entry or move it."""
    p = tmp_path / "disk_queue.jsonl"
    disk_queue.enqueue("task-aaaa1111", "cto-a", path=p)
    disk_queue.enqueue("task-bbbb2222", "cto-a", path=p)
    pos = disk_queue.enqueue("task-aaaa1111", "cto-a", path=p)

    assert pos == 0
    assert len(disk_queue.all_entries(path=p)) == 2


def test_pop_drops_entry_wherever_it_sits(tmp_path):
    """A task cancelled/closed while queued is dropped from the queue —
    even from the middle, not just the FIFO head."""
    p = tmp_path / "disk_queue.jsonl"
    for i in range(3):
        disk_queue.enqueue(f"task-{i:08d}", "cto-a", path=p)

    disk_queue.pop("task-00000001", path=p)

    ids = [e["task_id"] for e in disk_queue.all_entries(path=p)]
    assert ids == ["task-00000000", "task-00000002"]


def test_pop_missing_task_is_noop(tmp_path):
    p = tmp_path / "disk_queue.jsonl"
    disk_queue.enqueue("task-00000000", "cto-a", path=p)
    disk_queue.pop("task-ffffffff", path=p)
    assert len(disk_queue.all_entries(path=p)) == 1


def test_is_queued_and_position(tmp_path):
    p = tmp_path / "disk_queue.jsonl"
    assert disk_queue.is_queued("task-00000000", path=p) is False
    disk_queue.enqueue("task-00000000", "cto-a", path=p)
    assert disk_queue.is_queued("task-00000000", path=p) is True
    assert disk_queue.position("task-00000000", path=p) == 0
    assert disk_queue.position("task-nope0000", path=p) is None


def test_peek_empty_queue_is_none(tmp_path):
    assert disk_queue.peek(path=tmp_path / "disk_queue.jsonl") is None


def test_entry_fields(tmp_path):
    p = tmp_path / "disk_queue.jsonl"
    disk_queue.enqueue("task-00000000", "cto-xyz", path=p)
    entry = disk_queue.all_entries(path=p)[0]
    assert entry["task_id"] == "task-00000000"
    assert entry["owner_cto"] == "cto-xyz"
    assert entry.get("queued_at")


# ---------------------------------------------------------------------------
# delegate.py integration — the refusal path enqueues + notifies.
# ---------------------------------------------------------------------------

@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(delegate, "_scope_owners", lambda feature: ["test-owner"])
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "disk_queue.jsonl")
    db_mod.init()
    return db_mod


def _new_task(owner: str = "test-owner", role: str = "developer") -> str:
    return db_mod.create_task(
        project="mooniex-agents", role=role,
        title="disk queue test", description="d", owner_cto=owner,
    )


def test_refusal_enqueues_and_notifies_owner(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 4.0)
    sent = []
    monkeypatch.setattr(delegate.send_to_cto, "send",
                        lambda *a, **k: sent.append((a, k)) or True)

    tid = _new_task()
    result = asyncio.run(delegate.delegate_task(tid))

    assert result["status"] == "pending"
    assert "queued for disk (0 ahead)" in result["delegate_log"]
    assert disk_queue.is_queued(tid, path=disk_queue.QUEUE_PATH)
    assert len(sent) == 1
    assert sent[0][0][0] == tid  # from_id == task_id


def test_second_refusal_shows_one_ahead(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 4.0)
    monkeypatch.setattr(delegate.send_to_cto, "send", lambda *a, **k: True)

    tid1 = _new_task()
    tid2 = _new_task()
    asyncio.run(delegate.delegate_task(tid1))
    result2 = asyncio.run(delegate.delegate_task(tid2))

    assert "queued for disk (1 ahead)" in result2["delegate_log"]


# ---------------------------------------------------------------------------
# runners/watchdog.py `_drain_disk_queue` — threshold, one-per-tick, dropped.
# ---------------------------------------------------------------------------

@pytest.fixture()
def drain_env(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "disk_queue.jsonl")
    monkeypatch.setattr(delegate, "_disk_orange_floor_gb", lambda: 5.0)
    monkeypatch.setattr(watchdog.send_to_cto, "send", lambda *a, **k: True)
    db_mod.init()
    return db_mod


def test_drain_below_threshold_spawns_nothing(drain_env, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 5.5)  # < 5+1
    tid = drain_env.create_task(project="mooniex-agents", role="developer",
                                title="q", description="d", owner_cto="a")
    disk_queue.enqueue(tid, "a")

    calls = []
    async def fake_delegate_task(task_id, **kw):
        calls.append(task_id)
    monkeypatch.setattr(delegate, "delegate_task", fake_delegate_task)

    result = watchdog._drain_disk_queue()

    assert result is None
    assert calls == []
    assert disk_queue.is_queued(tid)  # still queued, untouched


def test_drain_at_threshold_spawns_oldest(drain_env, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 6.0)  # == 5+1
    tid1 = drain_env.create_task(project="mooniex-agents", role="developer",
                                 title="q1", description="d", owner_cto="a")
    tid2 = drain_env.create_task(project="mooniex-agents", role="developer",
                                 title="q2", description="d", owner_cto="a")
    disk_queue.enqueue(tid1, "a")
    disk_queue.enqueue(tid2, "a")

    calls = []
    async def fake_delegate_task(task_id, **kw):
        calls.append(task_id)
    monkeypatch.setattr(delegate, "delegate_task", fake_delegate_task)

    result = watchdog._drain_disk_queue()

    assert result["task"] == tid1
    assert calls == [tid1]  # never several at once
    assert not disk_queue.is_queued(tid1)
    assert disk_queue.is_queued(tid2)  # left for next tick


def test_drain_skips_cancelled_head_and_spawns_next(drain_env, monkeypatch):
    """A task cancelled/closed while it waited is dropped from the queue,
    and the drain still spawns the next-oldest live one in the SAME tick —
    only the actual delegate_task call counts toward the one-per-tick cap."""
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 10.0)
    tid1 = drain_env.create_task(project="mooniex-agents", role="developer",
                                 title="q1", description="d", owner_cto="a")
    tid2 = drain_env.create_task(project="mooniex-agents", role="developer",
                                 title="q2", description="d", owner_cto="a")
    disk_queue.enqueue(tid1, "a")
    disk_queue.enqueue(tid2, "a")
    drain_env.update_status(tid1, "cancelled", actor="test")

    calls = []
    async def fake_delegate_task(task_id, **kw):
        calls.append(task_id)
    monkeypatch.setattr(delegate, "delegate_task", fake_delegate_task)

    result = watchdog._drain_disk_queue()

    assert calls == [tid2]
    assert result["task"] == tid2
    assert not disk_queue.is_queued(tid1)  # dropped, not spawned
    assert not disk_queue.is_queued(tid2)  # popped to spawn


def test_drain_empty_queue_is_noop(drain_env, monkeypatch):
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 100.0)
    calls = []
    async def fake_delegate_task(task_id, **kw):
        calls.append(task_id)
    monkeypatch.setattr(delegate, "delegate_task", fake_delegate_task)

    assert watchdog._drain_disk_queue() is None
    assert calls == []


# ---------------------------------------------------------------------------
# tools/gc_stale_tasks.py — a queued task is exempt from the 30-min reaper.
# ---------------------------------------------------------------------------

@pytest.fixture()
def gc_env(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "disk_queue.jsonl")
    db_mod.init()
    return db_mod


def _backdate(db_path: Path, task_id: str, minutes: float) -> None:
    import sqlite3
    from datetime import datetime, timedelta, timezone
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE tasks SET created_at=?, updated_at=? WHERE id=?",
                (ts, ts, task_id))
    conn.commit()
    conn.close()


def test_queued_stale_pending_task_is_exempt_from_gc(gc_env, tmp_path):
    tid = gc_env.create_task(project="mooniex-agents", role="developer",
                             title="q", description="d", owner_cto="a")
    _backdate(tmp_path / "tasks.db", tid, 45)  # > STALE_PENDING_MINUTES (30)
    disk_queue.enqueue(tid, "a")

    cancelled = gc_stale_tasks.gc_stale_tasks()

    assert all(c["task_id"] != tid for c in cancelled)
    assert gc_env.get_task(tid)["status"] == "pending"


def test_non_queued_stale_pending_task_is_still_cancelled(gc_env, tmp_path):
    """Control: the exemption is specific to queued tasks — an ordinary
    stale pending task must still be reaped exactly as before."""
    tid = gc_env.create_task(project="mooniex-agents", role="developer",
                             title="q", description="d", owner_cto="a")
    _backdate(tmp_path / "tasks.db", tid, 45)

    cancelled = gc_stale_tasks.gc_stale_tasks()

    assert any(c["task_id"] == tid for c in cancelled)
    assert gc_env.get_task(tid)["status"] == "cancelled"

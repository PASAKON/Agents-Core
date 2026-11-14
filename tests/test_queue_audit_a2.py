"""A2 regression proofs: intentionally fail until the audited defects are fixed.

Only scratch SQLite/files and monkeypatched delegates; no network or live state.
"""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from lib import db
from tools import budget_queue, disk_queue, host_queue


@pytest.fixture
def locks(tmp_path, monkeypatch):
    path = tmp_path / "locks.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE locks (key TEXT PRIMARY KEY, owner TEXT, expires_at TEXT)")
    @contextmanager
    def connect(**kwargs):
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    monkeypatch.setattr(db, "get_conn", connect)
    return connect


def test_A2_001_concurrent_acquire_two_winners(locks, monkeypatch):
    # Pause A after its SELECT has returned empty; let B commit, then resume A.
    # SQLite's deferred transaction and PG READ COMMITTED both permit this schedule.
    entered = False
    winners = []
    @contextmanager
    def interleaved(**kwargs):
        with locks() as conn:
            class Proxy:
                def execute(self, sql, args):
                    nonlocal entered
                    cur = conn.execute(sql, args)
                    if sql.startswith("SELECT") and not entered:
                        result = cur.fetchone()
                        entered = True
                        winners.append(db.acquire_lock("resource", "B"))
                        class Result:
                            def fetchone(self):
                                return result
                        return Result()
                    return cur
            yield Proxy()
    monkeypatch.setattr(db, "get_conn", interleaved)
    winners.append(db.acquire_lock("resource", "A"))
    assert sum(winners) == 1


def test_A2_002_project_like_wildcard_releases_other_project(locks):
    db.acquire_lock("proj:alphaXbeta:path:x", "task")
    db.release_task_locks("task", "alpha_beta")
    with locks() as conn:
        assert conn.execute("SELECT count(*) FROM locks").fetchone()[0] == 1


def test_A2_003_path_exception_leaks_partial_locks(locks, monkeypatch):
    original = db.acquire_lock
    def acquire(key, **kwargs):
        if key.endswith(":b"):
            raise OSError("connection lost")
        return original(key, **kwargs)
    monkeypatch.setattr(db, "acquire_lock", acquire)
    with pytest.raises(OSError):
        db.lock_paths("task", "project", ["a", "b"])
    with locks() as conn:
        assert conn.execute("SELECT count(*) FROM locks").fetchone()[0] == 0


def test_A2_004_disk_concurrent_enqueue_loses_entry(tmp_path, monkeypatch):
    path = tmp_path / "queue"
    save = disk_queue._save
    entered = False
    def interleaved(entries, path=None):
        nonlocal entered
        if not entered:
            entered = True
            disk_queue.enqueue("B", "owner", path=path)
        save(entries, path)
    monkeypatch.setattr(disk_queue, "_save", interleaved)
    disk_queue.enqueue("A", "owner", path=path)
    assert {e["task_id"] for e in disk_queue.all_entries(path=path)} == {"A", "B"}


def test_A2_005_disk_crash_truncates_queue(tmp_path, monkeypatch):
    from pathlib import Path
    path = tmp_path / "queue"
    disk_queue.enqueue("A", "owner", path=path)
    original = Path.write_text
    def crash(self, text, **kwargs):
        if self == path:
            with self.open("w"):
                pass
            raise OSError("crash after truncate")
        return original(self, text, **kwargs)
    monkeypatch.setattr(Path, "write_text", crash)
    with pytest.raises(OSError):
        disk_queue.enqueue("B", "owner", path=path)
    assert disk_queue.is_queued("A", path=path)


def test_A2_006_host_lookup_error_loses_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "host.jsonl")
    host_queue.enqueue("A", "owner")
    def unavailable(tid):
        raise OSError("hub unavailable")
    monkeypatch.setattr(db, "get_task", unavailable)
    with pytest.raises(OSError):
        asyncio.run(host_queue.drain())
    assert [e["task_id"] for e in host_queue.load()] == ["A"]


def test_A2_007_host_crash_before_delegate_loses_entry(tmp_path, monkeypatch):
    from tools import delegate
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "host.jsonl")
    monkeypatch.setattr(db, "get_task", lambda tid: {"status": "pending"})
    class ProcessDeath(BaseException):
        pass
    async def crash(*args, **kwargs):
        raise ProcessDeath()
    monkeypatch.setattr(delegate, "delegate_task", crash)
    host_queue.enqueue("A", "owner")
    with pytest.raises(ProcessDeath):
        asyncio.run(host_queue.drain())
    assert [e["task_id"] for e in host_queue.load()] == ["A"]


def test_A2_008_gc_cancels_host_waiter(tmp_path, monkeypatch):
    from tools import gc_stale_tasks as gc
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "host.jsonl")
    monkeypatch.setattr(budget_queue, "QUEUE_PATH", tmp_path / "budget.jsonl")
    host_queue.enqueue("A", "owner")
    task = dict(id="A", project="p", assigned_agent=None, pid=None,
                created_at="2000-01-01T00:00:00+00:00")
    monkeypatch.setattr(db, "list_tasks", lambda status, **kw: [task] if status == "pending" else [])
    monkeypatch.setattr(gc, "is_local_row", lambda t: True)
    monkeypatch.setattr(gc, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(gc, "_reclaim_worktree", lambda *a, **kw: None)
    monkeypatch.setattr(gc, "release_terminal_task_locks", lambda **kw: [])
    assert gc.gc_stale_tasks(dry_run=True) == []


def test_A2_009_quota_reset_skips_budget_drain(monkeypatch):
    from tools import quota_reset, delegate
    monkeypatch.setattr(host_queue, "drain", lambda: None)
    monkeypatch.setattr(budget_queue, "all_entries", lambda: [{"task_id": "A"}])
    monkeypatch.setattr(budget_queue, "ready", lambda entry: True)
    monkeypatch.setattr(budget_queue, "pop", lambda tid: None)
    monkeypatch.setattr(db, "get_task", lambda tid: {"status": "pending"})
    calls = []
    async def spawn(tid, **kwargs):
        calls.append(tid)
        return {"status": "in_progress"}
    monkeypatch.setattr(delegate, "delegate_task", spawn)
    quota_reset.drain_waiting()
    assert calls == ["A"]


def test_A2_010_clock_skew_steals_live_lease(locks, monkeypatch):
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return instant
    monkeypatch.setattr(db, "datetime", Clock)
    assert db.acquire_lock("resource", "A", 600)
    # No elapsed real time: a second client's wall clock is eleven minutes fast.
    instant += timedelta(minutes=11)
    assert not db.acquire_lock("resource", "B", 600)


def test_owner_guard_and_expiry_control(locks):
    assert db.acquire_lock("resource", "A")
    db.release_lock("resource", "B")
    assert not db.acquire_lock("resource", "B")
    db.release_lock("resource", "A")
    assert db.acquire_lock("resource", "B")


def test_A2_011_disk_delegate_error_loses_entry(monkeypatch):
    from runners import watchdog
    from tools import delegate
    disk_queue.enqueue("A", "owner")
    monkeypatch.setattr(db, "get_task", lambda tid: {"status": "pending"})
    monkeypatch.setattr(delegate, "_free_gb", lambda: 100)
    monkeypatch.setattr(delegate, "_disk_orange_floor_gb", lambda: 5)
    monkeypatch.setattr(watchdog, "error", lambda message: None)
    async def fail(*args, **kwargs):
        raise OSError("spawn failed")
    monkeypatch.setattr(delegate, "delegate_task", fail)
    watchdog._drain_disk_queue()
    assert disk_queue.is_queued("A")


def test_A2_012_console_read_error_forgets_live_holder(tmp_path):
    import json
    from pathlib import Path
    import shutil
    import subprocess
    source = Path("/opt/MoonieXHQ/Projects/MoonieX/Console/src/relay/locks.js")
    if not source.exists() or not shutil.which("node"):
        pytest.skip("Console checkout and Node required")
    # Execute the actual module with only config import stubbed: no Console
    # startup, env/config loading, HTTP, or default state path is reached.
    code = source.read_text().replace(
        "import { config } from '../config.js';", "const config = {};")
    code += "\n" + "const file = " + json.dumps(str(tmp_path / "locks.json")) + ";\n"
    code += """
const key = 'home:mac:9224', now = 1000000;
acquireLock({key, owner: 'A'}, {file, now});
const read = fs.readFileSync;
fs.readFileSync = () => { throw new Error('temporary read failure'); };
let granted = false;
try { granted = acquireLock({key, owner: 'B'}, {file, now}).ok; }
catch { /* refusing acquisition is safe */ }
fs.readFileSync = read;
console.log(JSON.stringify({granted, owner: listLocks({file, now})[0]?.owner}));
"""
    result = subprocess.run(["node", "--input-type=module"], input=code,
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout) == {"granted": False, "owner": "A"}

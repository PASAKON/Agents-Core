"""Queue tests use temporary SQLite or an explicitly configured scratch PG schema."""
import asyncio
from contextlib import contextmanager
import json
import multiprocessing
import os
from pathlib import Path
import uuid

import pytest

from lib import db, db_pg, org_queue
from tools import host_queue, budget_queue, disk_queue, queue_migrate


@pytest.fixture(params=["sqlite", "pg"])
def storage(request, monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setenv("ORG_QUEUE_HUB", "1")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "queue.db")
    for module in (host_queue, budget_queue, disk_queue):
        monkeypatch.setattr(module, "QUEUE_PATH", tmp_path / (module.__name__ + ".jsonl"))
    monkeypatch.setattr(budget_queue.usage_budget, "load_gate_rows", lambda: {})
    if request.param == "sqlite":
        db.init()
        yield request.param
        return
    url = os.environ.get("LEASE_PG_URL")
    if not url:
        pytest.skip("LEASE_PG_URL not set (scratch PG only)")
    schema = "queue_test_" + uuid.uuid4().hex
    admin = db_pg.connect(url)
    admin.execute(f'CREATE SCHEMA "{schema}"')
    admin.commit()
    @contextmanager
    def connect(**kwargs):
        conn = db_pg.connect(url)
        try:
            conn.execute(f'SET search_path TO "{schema}"')
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    monkeypatch.setattr(db, "get_conn", connect)
    try:
        with connect() as conn:
            db.init_schema(conn, is_pg=True)
        yield request.param
    finally:
        admin.execute(f'DROP SCHEMA "{schema}" CASCADE')
        admin.commit()
        admin.close()


@pytest.mark.parametrize("module,name", [(host_queue, "host"), (budget_queue, "budget"), (disk_queue, "disk")])
def test_fifo_duplicate_remove(storage, monkeypatch, module, name):
    module.QUEUE_PATH.write_bytes(b'{"task_id":"legacy-only"}\n')
    before = module.QUEUE_PATH.read_bytes()
    monkeypatch.setattr(db, "now_iso", lambda: "2026-01-02T00:00:00+00:00")
    module.enqueue("z", "owner")
    module.enqueue("a", "owner")
    monkeypatch.setattr(db, "now_iso", lambda: "2026-01-01T00:00:00+00:00")
    module.enqueue("old", "owner")
    assert module.enqueue("z", "changed") == 2
    rows = org_queue.load(name)
    assert [e["task_id"] for e in rows] == ["old", "a", "z"]
    assert rows[-1]["owner_cto"] == "owner"
    (module.remove if name == "host" else module.pop)("a")
    assert [e["task_id"] for e in org_queue.load(name)] == ["old", "z"]
    assert module.QUEUE_PATH.read_bytes() == before


def test_flag_off_legacy_bytes(storage, monkeypatch):
    monkeypatch.delenv("ORG_QUEUE_HUB")
    monkeypatch.setattr(db, "now_iso", lambda: "fixed")
    for module in (host_queue, budget_queue, disk_queue):
        module.enqueue("a", "owner")
        before = module.QUEUE_PATH.read_bytes()
        module.enqueue("a", "owner")
        assert module.QUEUE_PATH.read_bytes() == before
    assert org_queue.load("host") == org_queue.load("budget") == org_queue.load("disk") == []


def test_migrate_twice(storage, tmp_path, capsys):
    paths = {q: tmp_path / f"{q}.jsonl" for q in ("host", "budget", "disk")}
    for path in paths.values():
        path.write_text(''.join(json.dumps(dict(task_id=str(i), queued_at=str(i), extra="preserved")) + '\n' for i in range(3)))
    before = {q: p.read_bytes() for q, p in paths.items()}
    assert all(c["added"] == 3 for c in queue_migrate.migrate(paths=paths).values())
    assert org_queue.load("host") == []
    first = queue_migrate.migrate(apply=True, paths=paths)
    second = queue_migrate.migrate(apply=True, paths=paths)
    assert all(c["total"] == 3 and c["added"] == 3 for c in first.values())
    assert all(c["total"] == 3 and c["added"] == 0 for c in second.values())
    assert before == {q: p.read_bytes() for q, p in paths.items()}
    assert "disk: source=3 added=0 total=3" in capsys.readouterr().out


def test_conflicting_migration_rolls_back(storage, tmp_path):
    org_queue.enqueue("host", dict(task_id="z", queued_at="old"))
    path = tmp_path / "source.jsonl"
    path.write_text('{"task_id":"a"}\n{"task_id":"z","queued_at":"new"}\n')
    with pytest.raises(ValueError, match="conflicting hub"):
        queue_migrate.migrate(apply=True, paths={"host": path})
    assert [e["task_id"] for e in org_queue.load("host")] == ["z"]


def _writer(path, prefix, start, queue):
    os.environ.pop("ORG_DB_URL", None)
    os.environ["ORG_QUEUE_HUB"] = "1"
    db.DB_PATH = Path(path)
    module = {"host": host_queue, "budget": budget_queue, "disk": disk_queue}[queue]
    budget_queue.usage_budget.load_gate_rows = lambda: {}
    start.wait(10)
    for i in range(60):
        module.enqueue(f"{prefix}-{i}", "owner")
        module.enqueue(f"shared-{i}", "owner")


@pytest.mark.parametrize("queue", ["host", "budget", "disk"])
def test_two_processes(storage, queue):
    if storage != "sqlite":
        pytest.skip("process test uses SQLite")
    ctx = multiprocessing.get_context("spawn")
    start = ctx.Event()
    workers = [ctx.Process(target=_writer, args=(str(db.DB_PATH), str(i), start, queue)) for i in range(2)]
    for worker in workers:
        worker.start()
    start.set()
    for worker in workers:
        worker.join(30)
        assert worker.exitcode == 0
    assert len(org_queue.load(queue)) == 180


def test_budget_requeue(storage, monkeypatch):
    monkeypatch.setattr(db, "now_iso", lambda: "2026-01-01")
    budget_queue.enqueue("a", "owner", tier="low")
    budget_queue.enqueue("b", "owner")
    monkeypatch.setattr(db, "now_iso", lambda: "2026-01-02")
    budget_queue.requeue("a", "owner", tier="normal")
    assert budget_queue.is_queued("a")
    assert not disk_queue.is_queued("a")
    assert [e["task_id"] for e in budget_queue.all_entries()] == ["b", "a"]
    assert budget_queue.all_entries()[-1]["tier"] == "normal"


def test_host_drain_restores_on_error(storage, monkeypatch):
    from tools import delegate
    host_queue.enqueue("a", "owner", host="mac")
    before = host_queue.load()
    monkeypatch.setattr(db, "get_task", lambda tid: {"status": "pending"})
    async def fail(*args, **kwargs):
        raise RuntimeError("spawn failed")
    monkeypatch.setattr(delegate, "delegate_task", fail)
    with pytest.raises(RuntimeError, match="spawn failed"):
        asyncio.run(host_queue.drain())
    assert host_queue.load() == before


def test_dry_run_before_schema(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "empty.db")
    path = tmp_path / "queue.jsonl"
    path.write_text('{"task_id":"a"}\n')
    assert queue_migrate.migrate(paths={"disk": path})["disk"]["added"] == 1
    with db.get_conn() as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='org_queue'").fetchone() is None


def test_hub_failure_never_writes_jsonl(storage, monkeypatch):
    def unavailable(**kwargs):
        raise db.HubUnavailable("test outage")
    monkeypatch.setattr(db, "get_conn", unavailable)
    for module in (host_queue, budget_queue, disk_queue):
        with pytest.raises(db.HubUnavailable):
            module.enqueue("a", "owner")
        assert not module.QUEUE_PATH.exists()


@pytest.mark.parametrize("contents", ['not json\n', '{"owner_cto":"owner"}\n',
                                       '{"task_id":"a","x":1}\n{"task_id":"a","x":2}\n'])
def test_invalid_migration_preserves_source(storage, tmp_path, contents):
    path = tmp_path / "invalid.jsonl"
    path.write_text(contents)
    with pytest.raises(ValueError):
        queue_migrate.migrate(apply=True, paths={"disk": path})
    assert path.read_text() == contents
    assert disk_queue.all_entries() == []


def test_host_drain(storage, monkeypatch):
    from tools import delegate
    host_queue.enqueue("a", "owner", host="mac")
    host_queue.enqueue("b", "owner")
    monkeypatch.setattr(db, "get_task", lambda tid: {"status": "pending"})
    calls = []
    async def spawn(tid, **kwargs):
        calls.append(tid)
        return {"status": "in_progress"}
    monkeypatch.setattr(delegate, "delegate_task", spawn)
    asyncio.run(host_queue.drain(max_spawns=1))
    assert calls == ["a"]
    assert [e["task_id"] for e in host_queue.load()] == ["b"]
    assert not host_queue.QUEUE_PATH.exists()

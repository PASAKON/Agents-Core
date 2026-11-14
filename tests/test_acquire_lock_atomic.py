"""Atomic grants; LEASE_PG_URL opts into a disposable Postgres test database."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import multiprocessing
import os
import threading
import uuid

import pytest

from lib import db, db_pg


@pytest.fixture
def sqlite_locks(tmp_path, monkeypatch):
    monkeypatch.delenv("ORG_DB_URL", raising=False)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "locks.db")
    with db.get_conn() as conn:
        conn.execute("CREATE TABLE locks (key TEXT PRIMARY KEY, "
                     "owner TEXT NOT NULL, expires_at TEXT NOT NULL)")


@pytest.mark.parametrize("owner,expiry,granted", [
    (None, None, True),
    ("other", "2000-01-01T00:00:00+00:00", True),
    ("other", "2030-01-01T00:00:00+00:00", True),
    ("self", "2030-01-01T00:00:01+00:00", True),
    ("other", "2099-01-01T00:00:00+00:00", False),
])
def test_semantics(sqlite_locks, monkeypatch, owner, expiry, granted):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2030, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(db, "datetime", Clock)
    if owner is not None:
        with db.get_conn() as conn:
            conn.execute("INSERT INTO locks VALUES (?,?,?)", ("key", owner, expiry))
    assert db.acquire_lock("key", "self", ttl_seconds=600) is granted
    with db.get_conn() as conn:
        row = conn.execute("SELECT owner,expires_at FROM locks WHERE key=?", ("key",)).fetchone()
    assert tuple(row) == (("self", "2030-01-01T00:10:00+00:00")
                          if granted else (owner, expiry))


@pytest.mark.parametrize("expired", [False, True])
def test_sqlite_race(sqlite_locks, expired):
    for round_number in range(10):
        key = f"race-{round_number}"
        if expired:
            with db.get_conn() as conn:
                conn.execute("INSERT INTO locks VALUES (?,?,?)",
                             (key, "old", "2000-01-01T00:00:00+00:00"))
        barrier = threading.Barrier(8)

        def compete(index):
            barrier.wait(timeout=10)
            return db.acquire_lock(key, f"owner-{index}")

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(compete, range(8)))
        assert results.count(True) == 1
        with db.get_conn() as conn:
            row = conn.execute("SELECT owner FROM locks WHERE key=?", (key,)).fetchone()
        assert row["owner"] == f"owner-{results.index(True)}"


@pytest.mark.parametrize("affected", [0, 1])
def test_grant_is_one_statement_and_pg_translation(monkeypatch, affected):
    statements = []

    class RawCursor:
        rowcount = affected

        def execute(self, sql, params):
            statements.append((sql, params))

    class RawConnection:
        def cursor(self):
            return RawCursor()

    @contextmanager
    def connection():
        yield db_pg.Connection(RawConnection())

    monkeypatch.setattr(db, "get_conn", connection)
    assert db.acquire_lock("key", "owner") is (affected == 1)
    assert len(statements) == 1
    sql, params = statements[0]
    assert sql == (
        "INSERT INTO locks (key,owner,expires_at) VALUES (%s,%s,%s) "
        "ON CONFLICT(key) DO UPDATE SET owner=excluded.owner, "
        "expires_at=excluded.expires_at "
        "WHERE locks.expires_at <= %s OR locks.owner = excluded.owner"
    )
    assert len(params) == 4
    assert params[:2] == ("key", "owner")


def _pg_compete(url, schema, barrier, results, index):
    # Spawned workers use only the explicit test URL, never ORG_DB_URL.
    @contextmanager
    def connection():
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

    db.get_conn = connection
    for round_number in range(10):
        barrier.wait(timeout=30)
        granted = db.acquire_lock(f"race-{round_number}", f"owner-{index}")
        results.put((round_number, granted))


@pytest.mark.skipif(not os.environ.get("LEASE_PG_URL"), reason="LEASE_PG_URL not set")
def test_pg_two_process_race():
    url = os.environ["LEASE_PG_URL"]
    schema = "lock_test_" + uuid.uuid4().hex
    conn = db_pg.connect(url)
    ctx = multiprocessing.get_context("spawn")
    results = ctx.Queue()
    barrier = ctx.Barrier(2)
    workers = []
    try:
        conn.execute(f'CREATE SCHEMA "{schema}"')
        conn.execute(f'SET search_path TO "{schema}"')
        conn.execute("CREATE TABLE locks (key TEXT PRIMARY KEY, "
                     "owner TEXT NOT NULL, expires_at TEXT NOT NULL)")
        # Exercise both a missing row and takeover of an expired row.
        for n in range(5, 10):
            conn.execute("INSERT INTO locks VALUES (?,?,?)",
                         (f"race-{n}", "old", "2000-01-01T00:00:00+00:00"))
        conn.commit()
        for index in range(2):
            worker = ctx.Process(target=_pg_compete,
                                 args=(url, schema, barrier, results, index))
            worker.start()
            workers.append(worker)
        outcomes = [results.get(timeout=45) for _ in range(20)]
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        for n in range(10):
            assert sorted(granted for round_number, granted in outcomes
                          if round_number == n) == [False, True]
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
            worker.join(timeout=10)
        results.close()
        conn.rollback()
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.commit()
        conn.close()

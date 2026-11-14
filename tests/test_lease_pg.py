"""Opt-in PostgreSQL engine checks; never reads ORG_DB_URL.

LEASE_PG_URL must name a disposable local PostgreSQL database. Each test uses
its own randomly named schema and drops only that schema on completion.
"""
from contextlib import contextmanager
import multiprocessing
import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from lib import db_pg
from lib.lease import Identity, PgStore, Registry, Service

URL = os.environ.get("LEASE_PG_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="LEASE_PG_URL not set (scratch PostgreSQL only)")


@contextmanager
def connection(url, schema):
    conn = db_pg.connect(url)
    try:
        assert schema.startswith("lease_test_") and schema.replace("_", "").isalnum()
        conn.execute(f'SET search_path TO "{schema}"')
        conn.commit()
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def registry():
    # Reviewed test-only policy, no production registry edits.
    class TestRegistry:
        def resolve(self, name):
            return name, dict(kind="mutex", capacity=1, heartbeat_s=5, max_hold_s=30,
                              queue_cap=100, paid=False, on_hub_down="fail_closed",
                              needs_ceo_card=False, policy_version=1)
    return TestRegistry()


def service(url, schema, **kwargs):
    return Service(PgStore(lambda: connection(url, schema)), registry(), deliver=lambda e: True, **kwargs)


@pytest.fixture
def pg():
    # An accidentally inherited hub URL must not be usable by this harness.
    parsed = urlsplit(URL)
    assert parsed.hostname in {None, "localhost", "127.0.0.1", "::1"}, "scratch local database required"
    schema = "lease_test_" + uuid4().hex
    conn = db_pg.connect(URL)
    try:
        conn.execute(f'CREATE SCHEMA "{schema}"')
        conn.execute(f'SET search_path TO "{schema}"')
        ddl = db_pg.PG_SCHEMA.split("CREATE TABLE IF NOT EXISTS orders")[0]
        conn.executescript(ddl)
        conn.executescript(ddl)  # migration is idempotent
        conn.commit()
        yield URL, schema
    finally:
        conn.rollback()
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        conn.commit()
        conn.close()


def _contender(url, schema, owner, barrier, result):
    try:
        s = service(url, schema)
        barrier.wait(timeout=15)
        r = s.acquire("r", Identity(owner), purpose="concurrency", idempotency_key=owner)
        result.put((owner, r.state, r.token))
    except Exception as exc:
        result.put((owner, "error", type(exc).__name__))


def test_two_processes_exactly_one_winner(pg):
    url, schema = pg
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    output = ctx.Queue()
    processes = [ctx.Process(target=_contender, args=(url, schema, owner, barrier, output)) for owner in ("a", "b")]
    try:
        for p in processes:
            p.start()
        results = [output.get(timeout=30) for _ in processes]
        for p in processes:
            p.join(timeout=10)
            assert p.exitcode == 0
        assert sorted(r[1] for r in results) == ["granted", "waiting"], results
        with connection(url, schema) as conn:
            assert conn.execute("SELECT count(*) AS n FROM lease_events WHERE kind='grant'").fetchone()["n"] == 1
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)


def test_confirmed_dead_holder_freed(pg):
    dead = set()
    s = service(*pg, observer=lambda owner, evidence: False if owner in dead else None)
    a = s.acquire("r", Identity("a"), purpose="dead holder")
    b = s.acquire("r", Identity("b"), purpose="waiter")
    dead.add("a")
    s.tick()
    assert s.status(b.request_id, Identity("b")).state == "granted"
    assert not s.valid("r", a.request_id, a.token, Identity("a"))


def test_release_wakes_next_after_commit_and_retries_outbox(pg):
    s = service(*pg)
    a = s.acquire("r", Identity("a"), purpose="holder")
    b = s.acquire("r", Identity("b"), purpose="waiter")
    wakes = []
    def deliver(e):
        # Separate connection proves that both claim and wake committed already.
        assert service(*pg).status(b.request_id, Identity("b")).state == "granted"
        wakes.append(e["request_id"])
        return len(wakes) > 1
    s.deliver = deliver
    assert s.release(a.grants, Identity("a"))
    assert wakes == [b.request_id]
    s.tick()
    assert wakes == [b.request_id, b.request_id]
    s.tick()
    assert wakes == [b.request_id, b.request_id]


def test_expiry_and_fencing_reject_stale_token(pg):
    s = service(*pg)
    a = s.acquire("r", Identity("a"), purpose="holder")
    b = s.acquire("r", Identity("b"), purpose="waiter")
    with connection(*pg) as conn:
        conn.execute("UPDATE leases SET holders=jsonb_set(holders, ARRAY[?, 'expires_at'], to_jsonb(now()-interval '1 second')) WHERE name='r'", (a.request_id,))
    # Validity refuses expired authority even before reap or the next writer.
    assert not s.valid("r", a.request_id, a.token, Identity("a"))
    s.tick()
    new = s.status(b.request_id, Identity("b"))
    assert new.token > a.token
    assert not s.renew("r", a.request_id, a.token, Identity("a"))
    assert not s.release(a.grants, Identity("a"))
    assert not s.renew("r", b.request_id, a.token, Identity("b"))
    assert s.valid("r", b.request_id, new.token, Identity("b"))

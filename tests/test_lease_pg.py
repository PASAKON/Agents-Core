"""Opt-in scratch PostgreSQL tests. Never reads ORG_DB_URL.

LEASE_PG_URL must name a disposable test database. Each test creates/drops only
its own random schema; child processes use that same explicit schema and URL.
"""
import multiprocessing
import os
from pathlib import Path
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db_pg  # noqa: E402
from lib.lease import Actor, PostgresStore, Service, lease  # noqa: E402

pytestmark = pytest.mark.skipif(not os.environ.get("LEASE_PG_URL"), reason="LEASE_PG_URL not set (scratch PG only)")


def connection(url, schema):
    conn = db_pg.connect(url)
    # schema is generated internally, not supplied by CLI/SQL clients.
    conn.execute(f'SET search_path TO "{schema}"')
    conn.commit()
    return conn


@pytest.fixture
def pg():
    url = os.environ["LEASE_PG_URL"]
    schema = "lease_test_" + uuid.uuid4().hex
    conn = db_pg.connect(url)
    conn.execute(f'CREATE SCHEMA "{schema}"')
    conn.execute(f'SET search_path TO "{schema}"')
    ddl = db_pg.PG_SCHEMA.split("CREATE TABLE IF NOT EXISTS orders")[0]
    conn.executescript(ddl)
    conn.executescript(ddl)  # schema creation is idempotent
    conn.commit()
    conn.close()
    service = Service(PostgresStore(lambda: connection(url, schema)))
    service.configure("r")
    try:
        yield service, url, schema
    finally:
        conn = db_pg.connect(url)
        conn.execute(f'DROP SCHEMA "{schema}" CASCADE')
        conn.commit()
        conn.close()


def contender(url, schema, owner, barrier, output):
    service = Service(PostgresStore(lambda: connection(url, schema)))
    try:
        barrier.wait(timeout=15)
        result = service.acquire("r", Actor(owner), idempotency_key=owner)
        output.put((result.state, result.token))
    except Exception as exc:
        output.put(("error", type(exc).__name__))


def test_two_processes_exactly_one_winner(pg):
    service, url, schema = pg
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    output = ctx.Queue()
    workers = [ctx.Process(target=contender, args=(url, schema, o, barrier, output)) for o in ("a", "b")]
    try:
        for process in workers:
            process.start()
        results = [output.get(timeout=25) for _ in workers]
        assert sorted(r[0] for r in results) == ["granted", "waiting"], results
    finally:
        for process in workers:
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)


def test_dead_holder_freed(pg):
    service, _, _ = pg
    a = service.acquire("r", Actor("a"))
    b = service.acquire("r", Actor("b"))
    service.liveness = lambda owner: False if owner == "a" else None
    service.tick()
    assert not service.valid(a.request_id, Actor("a"), a.token)
    assert service.status(b.request_id, Actor("b")).state == "granted"


def test_release_wakes_next_and_outbox_survives_restart(pg):
    service, url, schema = pg
    a = service.acquire("r", Actor("a"))
    b = service.acquire("r", Actor("b"))
    assert service.release(a.request_id, Actor("a"), a.token)
    wakes = []
    restarted = Service(PostgresStore(lambda: connection(url, schema)), deliver=lambda owner, event: wakes.append((owner, event["request_id"])))
    restarted.deliver_outbox()
    restarted.deliver_outbox()
    assert len(wakes) == 1 and wakes[0][0] == "b"
    assert restarted.status(b.request_id, Actor("b")).state == "granted"


def test_fencing_rejects_stale_token(pg):
    service, _, _ = pg
    a = service.acquire("r", Actor("a"))
    b = service.acquire("r", Actor("b"))
    assert service.renew(a.request_id, Actor("a"), a.token)
    assert service.release(a.request_id, Actor("a"), a.token)
    new = service.status(b.request_id, Actor("b"))
    assert new.token > a.token
    assert not service.valid(a.request_id, Actor("a"), a.token)
    assert not service.renew(a.request_id, Actor("a"), a.token)
    assert not service.release(b.request_id, Actor("a"), new.token)
    assert not service.release(b.request_id, Actor("b"), a.token)


def test_group_abort_does_not_consume_rate_credit(pg):
    service, _, _ = pg
    service.configure("rate", kind="rate", capacity=1)
    with pytest.raises(OSError):
        service.acquire(["rate", "r"], Actor("a"), fail_at="rate")
    assert service.acquire(["r", "rate"], Actor("b")).state == "granted"


def test_rate_release_not_refunded_and_cooling(pg):
    service, _, _ = pg
    service.configure("rate", kind="rate", capacity=1)
    a = service.acquire("rate", Actor("a"))
    assert service.release(a.request_id, Actor("a"), a.token)
    b = service.acquire("rate", Actor("b"))
    assert b.state == "waiting"
    assert service.administer("reset", Actor("provider", "CTO"), name="rate", reason="verified")
    assert service.status(b.request_id, Actor("b")).state == "granted"


def test_context_manager_heartbeat_and_exception_release(pg):
    service, _, _ = pg
    with lease("r", purpose="work", wait_s=1, service=service, actor=Actor("a")) as l:
        assert isinstance(l.token, int) and l.token > 0
        l.assert_valid()
    with pytest.raises(RuntimeError):
        with lease("r", purpose="fail", wait_s=1, service=service, actor=Actor("b")) as l2:
            assert l2.token > l.token
            raise RuntimeError("boom")
    with lease("r", purpose="after", wait_s=1, service=service, actor=Actor("c")) as l3:
        assert l3.token > l2.token

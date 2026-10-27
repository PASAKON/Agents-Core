"""org_coo's CEO-order mirror against a REAL Postgres: deploy/coo-gate/org_coo_role.sql is applied
and lib/portfolio's order_take / order_close then run AS org_coo (tests/test_coo_gate.py only reads the
file as text).

Self-skips unless ORG_TEST_DB_URL is set to a LOCAL database (CI sets it against a postgres:16 service;
see tests/test_db_backend_pg.py for local setup) and psql is on PATH. The test creates the role org_coo
and changes grants on that database, so it refuses any other host (ADR 0021: never a production
database). Every test drops the portfolio tables first and last.

Run:  ORG_TEST_DB_URL=postgresql://postgres:postgres@localhost:5432/org_test \
      .venv/bin/python -m pytest tests/test_coo_orders_pg.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "deploy" / "coo-gate" / "org_coo_role.sql"
URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
PORTFOLIO = ("projects", "project_events", "milestones", "ceo_gos",
             "resource_locks", "post_ledger", "session_heartbeats", "orders")
COO = "COO#abcd1234"                 # tools.agent_transport.Identity("cxo", "coo", "abcd1234").label()


def _local(url: str) -> bool:
    parts = urlparse(url)
    host = parts.hostname or (parse_qs(parts.query).get("host") or [""])[0]
    return host in ("", "localhost", "127.0.0.1", "::1") or host.startswith("/")


pytestmark = pytest.mark.skipif(
    not URL or not shutil.which("psql") or not _local(URL),
    reason="needs ORG_TEST_DB_URL on a local Postgres 16 and psql on PATH")


def _apply_role_file() -> subprocess.CompletedProcess:
    env = {**os.environ, "ORG_COO_VERIFIER": ""}          # --grants-only: no password change
    return subprocess.run(["psql", "-X", "-v", "ON_ERROR_STOP=1", URL, "-f", str(SQL)],
                          env=env, capture_output=True, text=True, timeout=120)


class Hub:
    """One superuser connection that switches between the hub owner and org_coo, as the proof does."""

    def __init__(self, conn):
        self.conn = conn

    def owner(self, sql, params=()):
        self.conn.rollback()
        self.conn.execute("RESET ROLE")
        cur = self.conn.execute(sql, params)
        rows = cur.fetchall() if sql.lstrip().upper().startswith("SELECT") else None
        self.conn.commit()
        return rows

    def coo(self):
        """A clean transaction as org_coo; returns the connection for lib.portfolio's `conn=`."""
        self.conn.rollback()
        self.conn.execute("RESET ROLE")
        self.conn.execute("SET ROLE org_coo")
        self.conn.commit()
        assert self.conn.execute("SELECT current_user").fetchone()[0] == "org_coo"
        self.conn.commit()
        return self.conn


@pytest.fixture
def hub(monkeypatch):
    import lib.db as db_mod
    import lib.db_pg as db_pg
    monkeypatch.setenv("ORG_DB_URL", URL)
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_CHARTER_GATE", "ORG_PORTFOLIO_ENFORCE"):
        monkeypatch.delenv(var, raising=False)

    def drop():
        conn = db_pg.connect(URL, timeout=10)
        try:
            for table in reversed(PORTFOLIO):
                conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
            conn.execute("DROP FUNCTION IF EXISTS project_events_append_only() CASCADE")
            conn.commit()
        finally:
            conn.close()

    db_pg.evict(URL)
    drop()
    db_mod.init()
    db_pg.evict(URL)                                       # no prepared statement survives the DROP
    made = subprocess.run(
        ["psql", "-X", "-v", "ON_ERROR_STOP=1", URL, "-c",
         "DO $do$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_coo') "
         "THEN CREATE ROLE org_coo LOGIN; END IF; END $do$"],
        capture_output=True, text=True, timeout=60)
    assert made.returncode == 0, made.stderr[-1500:]
    admin = db_pg.connect(URL, timeout=10)
    ran = _apply_role_file()
    assert ran.returncode == 0, ran.stderr[-1500:]
    assert "row guards are in place and verified" in ran.stdout
    yield Hub(admin)
    admin.rollback()
    admin.close()
    db_pg.evict(URL)
    drop()


def test_the_role_file_applies_twice_and_its_own_proof_passes(hub):
    again = _apply_role_file()
    assert again.returncode == 0, again.stderr[-1500:]


def test_order_take_then_order_close_as_org_coo_closes_a_co_row_without_an_event(hub):
    from lib import portfolio as pf
    conn = hub.coo()
    assert pf.order_take("words", "sompong:7", actor="sompong", order_id=pf.ceo_order_hub_id(7), conn=conn) == "CO-7"
    conn.commit()
    conn = hub.coo()
    pf.order_close("CO-7", "done: shipped", actor=COO, conn=conn)
    conn.commit()
    row = hub.owner("SELECT taken_by, channel, project_id, closed_at IS NOT NULL, outcome FROM orders WHERE id = 'CO-7'")
    assert tuple(row[0]) == ("sompong", "sompong:7", None, True, "done: shipped")
    assert hub.owner("SELECT count(*) FROM project_events")[0][0] == 0


def test_closing_a_co_order_a_ph_linked_to_a_project_writes_the_close_event(hub):
    from lib import portfolio as pf
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    conn = hub.coo()
    pf.order_take("words", "sompong:8", actor="sompong", order_id="CO-8", conn=conn)
    conn.commit()
    hub.owner("UPDATE orders SET project_id = 'coo-pg' WHERE id = 'CO-8'")            # order_link, by a PH
    conn = hub.coo()
    pf.order_close("CO-8", "done: shipped", actor=COO, conn=conn)
    conn.commit()
    (event,) = hub.owner("SELECT project_id, kind, actor, body FROM project_events")
    assert (event["project_id"], event["kind"], event["actor"]) == ("coo-pg", "order", COO)
    assert dict(event["body"]) == {"op": "close", "id": "CO-8", "outcome": "done: shipped"}


def _take(**over):
    def run(conn):
        from lib import portfolio as pf
        args = {"words": "w", "channel": "sompong:9", "actor": "sompong", "order_id": "CO-9", **over}
        pf.order_take(args.pop("words"), args.pop("channel"), conn=conn, **args)
    return run


def _sql(sql):
    return lambda conn: conn.execute(sql)


def _insert_order(oid, **cols):
    names = ", ".join(["id", "words", "channel", "taken_by", "taken_at", *cols])
    values = ", ".join([f"'{oid}'", "'w'", f"'sompong:{oid[3:]}'", "'sompong'", "now()", *cols.values()])
    return _sql(f"INSERT INTO orders ({names}) VALUES ({values})")


GUARD = "org_coo may only"
DENIED = "permission denied"
FORBIDDEN = [
    ("an O- id (order_take without an order_id)", _take(order_id=None), GUARD),
    ("an id that only starts like CO-", _insert_order("CO-9x"), GUARD),
    ("a taken_by other than sompong", _take(actor="ceo"), GUARD),
    ("a chat channel", _take(channel="chat:cto-abc"), GUARD),
    ("a channel that is not the id's", _take(channel="sompong:1"), GUARD),
    ("a due date", _take(due_at=datetime(2026, 11, 1, tzinfo=timezone.utc), due_set_by="ceo"), GUARD),
    ("a project on insert", _insert_order("CO-10", project_id="'coo-pg'"), GUARD),
    ("a DELETE", _sql("DELETE FROM orders"), DENIED),
    ("reading project_events back", _sql("SELECT * FROM project_events"), DENIED),
    ("reading projects", _sql("SELECT * FROM projects"), DENIED),
    ("a project_events row of another kind", _sql(
        "INSERT INTO project_events (project_id, at, kind, actor, body) VALUES "
        f"('coo-pg', now(), 'stage', '{COO}', '{{\"op\":\"close\",\"id\":\"CO-20\"}}'::jsonb)"), GUARD),
    ("a close event under another actor", _sql(
        "INSERT INTO project_events (project_id, at, kind, actor, body) VALUES "
        "('coo-pg', now(), 'order', 'CTO#abcd1234', '{\"op\":\"close\",\"id\":\"CO-20\"}'::jsonb)"), GUARD),
    ("a close event whose actor ends in a newline", _sql(
        "INSERT INTO project_events (project_id, at, kind, actor, body) VALUES "
        f"('coo-pg', now(), 'order', E'{COO}\\n', '{{\"op\":\"close\",\"id\":\"CO-20\"}}'::jsonb)"), GUARD),
    ("a close event for an order that is still open", _sql(
        "INSERT INTO project_events (project_id, at, kind, actor, body) VALUES "
        f"('coo-pg', now(), 'order', '{COO}', '{{\"op\":\"close\",\"id\":\"CO-21\"}}'::jsonb)"), GUARD),
]


@pytest.mark.parametrize("what,run,message", FORBIDDEN, ids=[f[0] for f in FORBIDDEN])
def test_org_coo_cannot(hub, what, run, message):
    import psycopg
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome) VALUES "
              "('CO-20', 'w', 'sompong:20', 'sompong', now(), 'coo-pg', now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id) VALUES "
              "('CO-21', 'w', 'sompong:21', 'sompong', now(), 'coo-pg')")
    conn = hub.coo()
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.InsufficientPrivilege), match=message):
        run(conn)


@pytest.mark.parametrize("sql,message", [
    ("UPDATE orders SET outcome = 'changed' WHERE id = 'CO-20'", GUARD),                  # a closed CO row
    ("UPDATE orders SET words = 'changed' WHERE id = 'CO-21'", DENIED),                   # no column grant
    ("UPDATE orders SET outcome = 'x' WHERE id = 'CO-21'", GUARD),                        # closed_at left NULL
    ("UPDATE orders SET closed_at = now() WHERE id = 'O-20261027-0000-ab12'", GUARD),    # not a CO row
])
def test_org_coo_cannot_update(hub, sql, message):
    import psycopg
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, closed_at, outcome) VALUES "
              "('CO-20', 'w', 'sompong:20', 'sompong', now(), now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              "('CO-21', 'w', 'sompong:21', 'sompong', now())")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              "('O-20261027-0000-ab12', 'w', 'chat:cto-abc', 'ceo', now())")
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.InsufficientPrivilege), match=message):
        hub.coo().execute(sql)


def test_the_words_of_an_order_stay_fixed_even_with_a_column_grant(hub):
    """The trigger, not the grant, holds the other columns: grant UPDATE (words) and the close is still refused."""
    import psycopg
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              "('CO-30', 'w', 'sompong:30', 'sompong', now())")
    hub.owner("GRANT UPDATE (words) ON orders TO org_coo")
    with pytest.raises(psycopg.errors.RaiseException, match=GUARD):
        hub.coo().execute("UPDATE orders SET words = 'changed', closed_at = now(), outcome = 'x' WHERE id = 'CO-30'")


def test_a_wrong_actor_leaves_the_order_open(hub):
    """order_close updates the order, then the event is refused: one transaction, so the order is not closed."""
    import psycopg
    from lib import portfolio as pf
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id) VALUES "
              "('CO-31', 'w', 'sompong:31', 'sompong', now(), 'coo-pg')")
    with pytest.raises(psycopg.errors.RaiseException, match=GUARD):
        pf.order_close("CO-31", "done: x", actor="CTO#abcd1234", conn=hub.coo())
    assert hub.owner("SELECT closed_at IS NULL FROM orders WHERE id = 'CO-31'")[0][0] is True


@pytest.mark.parametrize("project_id", [None, "coo-pg"])
def test_org_coo_creates_a_coo_task_with_the_columns_create_task_writes(hub, project_id):
    # lib/db.create_task INSERTs project_id since ProjectTrack P1; org_coo's grant lacked it (27 Oct,
    # SomPong: permission denied for table tasks). Same column list as lib/db.py create_task.
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo') ON CONFLICT DO NOTHING")
    conn = hub.coo()
    pid = "NULL" if project_id is None else f"'{project_id}'"
    conn.execute(
        "INSERT INTO tasks (id,project,role,status,title,description,parent_task,depends_on,touches,owner_cto,"
        "owner_role,host,dispatcher_host,runner,created_at,updated_at,project_id) VALUES "
        "('task-coopg001','mooniex-agents','researcher','pending','t','d',NULL,'[]','[]','coo-x','coo',"
        f"'contabo',NULL,NULL,'2026-10-27T05:00:00Z','2026-10-27T05:00:00Z',{pid})")
    conn.commit()
    row = hub.owner("SELECT owner_role, status, project_id FROM tasks WHERE id = 'task-coopg001'")
    assert tuple(row[0]) == ("coo", "pending", project_id)

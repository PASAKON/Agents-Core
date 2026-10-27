"""org_coo's order guards against a REAL Postgres: deploy/coo-gate/org_coo_role.sql is applied
and lib/portfolio's order_take / order_close then run AS org_coo (tests/test_coo_gate.py only reads the
file as text). Two kinds of order: the CEO-order mirror CO-<n> (taken_by sompong) and the COO's own
O-YYYYMMDD-HHMM-<4hex> order (taken_by COO#<8 hex>, channel coo:<n>). The O- takes are plain INSERTs of
the columns order_take writes, so they do not depend on which channels lib/portfolio accepts.

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


def _insert_o(oid, *, channel="'coo:1'", taken_by=f"'{COO}'", **cols):
    """The COO's own O- order as order_take INSERTs it, run as org_coo. Every value is a raw SQL literal."""
    names = ", ".join(["id", "words", "channel", "taken_by", "taken_at", *cols])
    values = ", ".join([f"'{oid}'", "'w'", channel, taken_by, "now()", *cols.values()])
    return _sql(f"INSERT INTO orders ({names}) VALUES ({values})")


def _close_event(oid, actor=COO):
    return _sql("INSERT INTO project_events (project_id, at, kind, actor, body) VALUES "
                f"('coo-pg', now(), 'order', '{actor}', '{{\"op\":\"close\",\"id\":\"{oid}\"}}'::jsonb)")


GUARD = "org_coo may only"
DENIED = "permission denied"
FORBIDDEN = [
    ("an O- id taken as sompong (order_take without an order_id)", _take(order_id=None), GUARD),
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
    # The COO's own O- orders. Each case is valid but for the one thing it names, and has its own id.
    ("an O- id of the wrong shape (a short date)", _insert_o("O-2026102-0900-aa02"), GUARD),
    ("an O- id with an upper-case hex tail", _insert_o("O-20261027-0900-AA03"), GUARD),
    ("an O- id with a taken_by of sompong", _insert_o("O-20261027-0900-aa04", taken_by="'sompong'"), GUARD),
    ("an O- id with a taken_by of a C-level", _insert_o("O-20261027-0900-aa05", taken_by="'cto-fresh'"), GUARD),
    ("an O- id with a taken_by of 7 hex digits", _insert_o("O-20261027-0900-aa06", taken_by="'COO#abcd123'"), GUARD),
    ("an O- id with an upper-case COO label", _insert_o("O-20261027-0900-aa07", taken_by="'COO#ABCD1234'"), GUARD),
    ("an O- id whose taken_by ends in a newline", _insert_o("O-20261027-0900-aa08", taken_by=f"E'{COO}\\n'"), GUARD),
    ("an O- id on the channel sompong:1", _insert_o("O-20261027-0900-aa09", channel="'sompong:1'"), GUARD),
    ("an O- id on a chat channel", _insert_o("O-20261027-0900-aa0a", channel="'chat:cto-abc'"), GUARD),
    ("an O- id on a channel with 7 digits", _insert_o("O-20261027-0900-aa0b", channel="'coo:1234567'"), GUARD),
    ("an O- id on a channel with no number", _insert_o("O-20261027-0900-aa0c", channel="'coo:'"), GUARD),
    ("an O- id with a project", _insert_o("O-20261027-0900-aa0d", project_id="'coo-pg'"), GUARD),
    ("an O- id with a due date and no due_set_by", _insert_o("O-20261027-0900-aa0e", due_at="now()"), GUARD),
    ("an O- id with a due date set by a C-level", _insert_o(
        "O-20261027-0900-aa0f", due_at="now()", due_set_by="'clevel'"), GUARD),
    ("an O- id with due_set_by ceo and no due date", _insert_o("O-20261027-0900-ab00", due_set_by="'ceo'"), GUARD),
    ("a close event for an O- order of a C-level", _close_event("O-20261027-0900-ee20"), GUARD),
    ("a close event for an O- order of the COO that is still open", _close_event("O-20261027-0900-ee21"), GUARD),
    ("a close event for an O- id of the wrong shape", _close_event("O-2026102-0900-ee23"), GUARD),
    ("a close event for an O- order under another actor", _close_event("O-20261027-0900-ee22", actor="CTO#abcd1234"), GUARD),
]


@pytest.mark.parametrize("what,run,message", FORBIDDEN, ids=[f[0] for f in FORBIDDEN])
def test_org_coo_cannot(hub, what, run, message):
    import psycopg
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome) VALUES "
              "('CO-20', 'w', 'sompong:20', 'sompong', now(), 'coo-pg', now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id) VALUES "
              "('CO-21', 'w', 'sompong:21', 'sompong', now(), 'coo-pg')")
    # O- orders for the close-event cases: a C-level's (closed), the COO's closed one (the other
    # cases' actor is what refuses it) and the COO's still open, all linked to the project.
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome) VALUES "
              "('O-20261027-0900-ee20', 'w', 'chat:cto-abc', 'cto-fresh', now(), 'coo-pg', now(), 'done: x'), "
              f"('O-20261027-0900-ee22', 'w', 'coo:22', '{COO}', now(), 'coo-pg', now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id) VALUES "
              f"('O-20261027-0900-ee21', 'w', 'coo:21', '{COO}', now(), 'coo-pg')")
    conn = hub.coo()
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.InsufficientPrivilege), match=message):
        run(conn)


@pytest.mark.parametrize("sql,message", [
    ("UPDATE orders SET outcome = 'changed' WHERE id = 'CO-20'", GUARD),                  # a closed CO row
    ("UPDATE orders SET words = 'changed' WHERE id = 'CO-21'", DENIED),                   # no column grant
    ("UPDATE orders SET outcome = 'x' WHERE id = 'CO-21'", GUARD),                        # closed_at left NULL
    ("UPDATE orders SET closed_at = now() WHERE id = 'O-20261027-0000-ab12'", GUARD),    # not a CO row
    # the COO's own O- rows: a closed one, words (no column grant), closed_at left NULL, a C-level's
    ("UPDATE orders SET outcome = 'changed' WHERE id = 'O-20261027-0900-cc03'", GUARD),
    ("UPDATE orders SET words = 'changed' WHERE id = 'O-20261027-0900-cc01'", DENIED),
    ("UPDATE orders SET outcome = 'x' WHERE id = 'O-20261027-0900-cc02'", GUARD),
    ("UPDATE orders SET closed_at = now(), outcome = 'x' WHERE id = 'O-20261027-0900-cc04'", GUARD),
])
def test_org_coo_cannot_update(hub, sql, message):
    import psycopg
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, closed_at, outcome) VALUES "
              "('CO-20', 'w', 'sompong:20', 'sompong', now(), now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              "('CO-21', 'w', 'sompong:21', 'sompong', now())")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              "('O-20261027-0000-ab12', 'w', 'chat:cto-abc', 'ceo', now())")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, closed_at, outcome) VALUES "
              f"('O-20261027-0900-cc03', 'w', 'coo:3', '{COO}', now(), now(), 'done: x')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              f"('O-20261027-0900-cc01', 'w', 'coo:1', '{COO}', now()), "
              f"('O-20261027-0900-cc02', 'w', 'coo:2', '{COO}', now()), "
              "('O-20261027-0900-cc04', 'w', 'chat:cto-abc', 'cto-fresh', now())")
    with pytest.raises((psycopg.errors.RaiseException, psycopg.errors.InsufficientPrivilege), match=message):
        hub.coo().execute(sql)


@pytest.mark.parametrize("oid,channel,taken_by", [
    ("CO-30", "sompong:30", "sompong"),
    ("O-20261027-0900-cc30", "coo:30", COO),
], ids=["a CO- order", "an O- order of the COO"])
def test_the_words_of_an_order_stay_fixed_even_with_a_column_grant(hub, oid, channel, taken_by):
    """The trigger, not the grant, holds the other columns: grant UPDATE (words) and the close is still refused."""
    import psycopg
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              f"('{oid}', 'w', '{channel}', '{taken_by}', now())")
    hub.owner("GRANT UPDATE (words) ON orders TO org_coo")
    with pytest.raises(psycopg.errors.RaiseException, match=GUARD):
        hub.coo().execute(f"UPDATE orders SET words = 'changed', closed_at = now(), outcome = 'x' WHERE id = '{oid}'")
    assert hub.owner(f"SELECT words, closed_at IS NULL FROM orders WHERE id = '{oid}'")[0][0] == "w"


@pytest.mark.parametrize("oid,due", [
    ("O-20261027-0900-aa11", None),
    ("O-20261027-0900-aa12", "2026-11-01T00:00:00Z"),
], ids=["no due date", "a due date the CEO set"])
def test_org_coo_takes_an_o_order_of_its_own_with_and_without_a_due_date(hub, oid, due):
    cols = {} if due is None else {"due_at": f"'{due}'", "due_set_by": "'ceo'"}
    conn = hub.coo()
    _insert_o(oid, **cols)(conn)
    conn.commit()
    row = hub.owner("SELECT taken_by, channel, project_id, due_at IS NOT NULL, due_set_by, closed_at IS NULL "
                    f"FROM orders WHERE id = '{oid}'")
    assert tuple(row[0]) == (COO, "coo:1", None, due is not None, None if due is None else "ceo", True)


def test_org_coo_closes_an_open_o_order_it_took(hub):
    oid = "O-20261027-0900-aa13"
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              f"('{oid}', 'w', 'coo:13', '{COO}', now())")
    conn = hub.coo()
    conn.execute(f"UPDATE orders SET closed_at = now(), outcome = 'done: shipped' WHERE id = '{oid}'")
    conn.commit()
    row = hub.owner(f"SELECT words, channel, taken_by, closed_at IS NOT NULL, outcome FROM orders WHERE id = '{oid}'")
    assert tuple(row[0]) == ("w", "coo:13", COO, True, "done: shipped")


def test_order_close_as_org_coo_closes_its_o_order_without_an_event_while_no_project_is_linked(hub):
    from lib import portfolio as pf
    oid = "O-20261027-0900-aa14"
    conn = hub.coo()
    _insert_o(oid)(conn)
    conn.commit()
    pf.order_close(oid, "done: shipped", actor=COO, conn=hub.coo())
    hub.conn.commit()
    row = hub.owner(f"SELECT closed_at IS NOT NULL, outcome FROM orders WHERE id = '{oid}'")
    assert tuple(row[0]) == (True, "done: shipped")
    assert hub.owner("SELECT count(*) FROM project_events")[0][0] == 0


def test_closing_an_o_order_of_the_coo_a_ph_linked_to_a_project_writes_the_close_event(hub):
    from lib import portfolio as pf
    oid = "O-20261027-0900-aa15"
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    conn = hub.coo()
    _insert_o(oid)(conn)
    conn.commit()
    hub.owner(f"UPDATE orders SET project_id = 'coo-pg' WHERE id = '{oid}'")             # order_link, by a PH
    pf.order_close(oid, "done: shipped", actor=COO, conn=hub.coo())
    hub.conn.commit()
    (event,) = hub.owner("SELECT project_id, kind, actor, body FROM project_events")
    assert (event["project_id"], event["kind"], event["actor"]) == ("coo-pg", "order", COO)
    assert dict(event["body"]) == {"op": "close", "id": oid, "outcome": "done: shipped"}


def test_org_coo_writes_the_close_event_of_a_closed_o_order_of_its_own(hub):
    oid = "O-20261027-0900-aa16"
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-pg', 'coo-pg', 'coo')")
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome) VALUES "
              f"('{oid}', 'w', 'coo:16', '{COO}', now(), 'coo-pg', now(), 'done: x')")
    conn = hub.coo()
    _close_event(oid)(conn)
    conn.commit()
    (event,) = hub.owner("SELECT kind, actor, body FROM project_events")
    assert (event["kind"], event["actor"], dict(event["body"])) == ("order", COO, {"op": "close", "id": oid})


def test_order_close_as_org_coo_refuses_the_o_order_of_a_c_level_and_leaves_it_open(hub):
    import psycopg
    from lib import portfolio as pf
    oid = "O-20261027-0900-aa17"
    hub.owner("INSERT INTO orders (id, words, channel, taken_by, taken_at) VALUES "
              f"('{oid}', 'w', 'chat:cto-abc', 'cto-fresh', now())")
    with pytest.raises(psycopg.errors.RaiseException, match=GUARD):
        pf.order_close(oid, "done: x", actor=COO, conn=hub.coo())
    assert hub.owner(f"SELECT closed_at IS NULL FROM orders WHERE id = '{oid}'")[0][0] is True


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
    tid = "task-coopg00" + ("1" if project_id is None else "2")
    conn.execute(
        "INSERT INTO tasks (id,project,role,status,title,description,parent_task,depends_on,touches,owner_cto,"
        "owner_role,host,dispatcher_host,runner,created_at,updated_at,project_id) VALUES "
        f"('{tid}','mooniex-agents','researcher','pending','t','d',NULL,'[]','[]','coo-x','coo',"
        f"'contabo',NULL,NULL,'2026-10-27T05:00:00Z','2026-10-27T05:00:00Z',{pid})")
    conn.commit()
    row = hub.owner(f"SELECT owner_role, status, project_id FROM tasks WHERE id = '{tid}'")
    assert tuple(row[0]) == ("coo", "pending", project_id)


def test_the_gate_path_opens_and_closes_a_coo_o_order_as_org_coo_with_its_event(hub):
    # PH review, P6: lib/portfolio as the gate calls it (no order_id, channel coo:<n>, actor COO#<sid>).
    from datetime import datetime, timezone
    from lib import portfolio as pf
    hub.owner("INSERT INTO projects (id, name, lane) VALUES ('coo-gate-pg', 'coo-gate-pg', 'coo')")
    due = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
    conn = hub.coo()
    oid = pf.order_take("words", "coo:3", actor=COO, due_at=due, due_set_by="ceo", conn=conn)
    conn.commit()
    assert oid.startswith("O-")
    hub.owner(f"UPDATE orders SET project_id = 'coo-gate-pg' WHERE id = '{oid}'")      # order_link, by a C-level
    conn = hub.coo()
    pf.order_close(oid, "done: relayed", actor=COO, conn=conn)
    conn.commit()
    row = hub.owner(f"SELECT taken_by, channel, due_set_by, closed_at IS NOT NULL, outcome FROM orders WHERE id = '{oid}'")
    assert tuple(row[0]) == (COO, "coo:3", "ceo", True, "done: relayed")
    (event,) = hub.owner("SELECT kind, actor, body FROM project_events")
    assert (event["kind"], event["actor"], dict(event["body"])) == (
        "order", COO, {"op": "close", "id": oid, "outcome": "done: relayed"})

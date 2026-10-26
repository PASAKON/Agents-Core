"""Org restructure P3-A: the portfolio tables (docs/plans/org-restructure-p3-plan.md).

The first block needs no database. The rest runs lib.db.init() against a LOCAL
Postgres and self-skips unless ORG_TEST_DB_URL is set (CI sets it against a
postgres:16 service container; see tests/test_db_backend_pg.py for local setup).
ADR 0021: never a production database; every test drops these tables first."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402

ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
needs_pg = pytest.mark.skipif(not ORG_TEST_DB_URL, reason="ORG_TEST_DB_URL not set (local Postgres 16)")

PORTFOLIO = ("projects", "project_events", "milestones", "ceo_gos",
             "resource_locks", "post_ledger", "session_heartbeats", "orders")


def test_every_portfolio_table_is_in_pg_schema_and_not_in_sqlite():
    created = {db_mod._PG_CREATE_RE.match(s).group(1)
               for s in db_pg._split_statements(db_pg.PG_SCHEMA)}
    assert set(PORTFOLIO) <= created
    for t in PORTFOLIO:
        assert f"CREATE TABLE IF NOT EXISTS {t} " not in db_mod.SCHEMA


def test_guards_are_single_statements_that_never_return_new():
    assert len(db_pg.PORTFOLIO_GUARDS) == 3
    fn, row, trunc = db_pg.PORTFOLIO_GUARDS
    assert "RAISE EXCEPTION" in fn and "RETURN NEW" not in fn.upper()
    assert "BEFORE UPDATE OR DELETE ON project_events" in row
    assert "BEFORE TRUNCATE ON project_events" in trunc
    for name, stmt in zip(db_pg.PORTFOLIO_TRIGGER_NAMES, (row, trunc)):
        assert name in stmt


def test_no_portfolio_column_is_named_like_a_secret():
    import re
    body = db_pg.PG_SCHEMA[db_pg.PG_SCHEMA.index("CREATE TABLE IF NOT EXISTS projects"):]
    assert not re.search(r"\b\w*(password|secret|token|api_key|cookie)\w*\s+TEXT", body, re.I)


# --- against Postgres --------------------------------------------------------

def _drop(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for t in reversed(PORTFOLIO):
            conn.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
        conn.execute("DROP FUNCTION IF EXISTS project_events_append_only() CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def pg(monkeypatch):
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    for v in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE", "ORG_CHARTER_GATE"):
        monkeypatch.delenv(v, raising=False)
    _drop(ORG_TEST_DB_URL)
    db_mod.init()
    conn = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
    yield conn
    conn.rollback()
    conn.close()
    _drop(ORG_TEST_DB_URL)


def _fails(conn, sql, params=()):
    with pytest.raises(Exception) as ei:
        conn.execute(sql, params)
    conn.rollback()
    return str(ei.value)


def _project(conn, pid="p1", **kw):
    conn.execute("INSERT INTO projects (id, name, lane) VALUES (?, ?, ?)", (pid, "P", "cto"))
    conn.commit()


@needs_pg
def test_init_creates_tables_and_trigger_and_is_idempotent(pg):
    have = {r[0] for r in pg.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = current_schema()").fetchall()}
    assert set(PORTFOLIO) <= have
    assert db_mod._pg_schema_current(pg)
    db_mod.init()
    db_mod.init()
    for name in db_pg.PORTFOLIO_TRIGGER_NAMES:
        n = pg.execute("SELECT count(*) FROM pg_trigger WHERE tgname = ?", (name,)).fetchone()[0]
        assert n == 1, name


@needs_pg
def test_schema_is_not_current_without_the_trigger(pg):
    pg.execute("DROP TRIGGER project_events_append_only ON project_events")
    pg.commit()
    assert not db_mod._pg_schema_current(pg)
    db_mod.init()
    assert db_mod._pg_schema_current(pg)


@needs_pg
@pytest.mark.parametrize("name", ["project_events_append_only", "project_events_no_truncate"])
def test_a_disabled_trigger_is_not_current_and_init_reenables_it(pg, name):
    pg.execute(f"ALTER TABLE project_events DISABLE TRIGGER {name}")
    pg.commit()
    assert not db_mod._pg_schema_current(pg)
    db_mod.init()
    assert db_mod._pg_schema_current(pg)
    assert pg.execute("SELECT tgenabled FROM pg_trigger WHERE tgname = ?", (name,)).fetchone()[0] == "O"


@needs_pg
def test_a_same_named_trigger_on_another_table_does_not_count(pg):
    pg.execute("DROP TRIGGER project_events_no_truncate ON project_events")
    pg.execute("CREATE TRIGGER project_events_no_truncate BEFORE TRUNCATE ON milestones"
               " FOR EACH STATEMENT EXECUTE FUNCTION project_events_append_only()")
    pg.commit()
    assert not db_mod._pg_schema_current(pg)


@needs_pg
def test_truncate_is_refused(pg):
    _project(pg)
    pg.execute("INSERT INTO project_events (project_id, kind, actor) VALUES ('p1', 'opened', 'ph')")
    pg.commit()
    assert "append-only" in _fails(pg, "TRUNCATE project_events")
    assert "append-only" in _fails(pg, "TRUNCATE projects CASCADE")
    assert pg.execute("SELECT count(*) FROM project_events").fetchone()[0] == 1


@needs_pg
def test_project_events_is_append_only(pg):
    _project(pg)
    pg.execute("INSERT INTO project_events (project_id, kind, actor) VALUES ('p1', 'opened', 'ph')")
    pg.commit()
    assert "append-only" in _fails(pg, "UPDATE project_events SET actor = 'x'")
    assert "append-only" in _fails(pg, "DELETE FROM project_events")
    assert pg.execute("SELECT count(*) FROM project_events").fetchone()[0] == 1


@needs_pg
def test_checks_refuse_bad_rows(pg):
    _project(pg)
    _fails(pg, "INSERT INTO projects (id, name, lane, stage) VALUES ('p2', 'P', 'cto', 'doing')")
    _fails(pg, "INSERT INTO projects (id, name, lane, blocker_on) VALUES ('p2', 'P', 'cto', 'bob')")
    _fails(pg, "INSERT INTO project_events (project_id, kind, actor) VALUES ('p1', 'chat', 'ph')")
    _fails(pg, "INSERT INTO project_events (project_id, kind, actor) VALUES ('nope', 'opened', 'ph')")
    # a milestone is done only with evidence
    _fails(pg, "INSERT INTO milestones (project_id, n, title, done_at) VALUES ('p1', 1, 't', now())")
    _fails(pg, "INSERT INTO milestones (project_id, n, title, done_at, evidence)"
               " VALUES ('p1', 1, 't', now(), '  ')")
    pg.execute("INSERT INTO milestones (project_id, n, title, done_at, evidence)"
               " VALUES ('p1', 1, 't', now(), 'sha 3b6c6bf7')")
    pg.execute("INSERT INTO milestones (project_id, n, title) VALUES ('p1', 2, 'open')")
    pg.commit()
    # a CEO GO names where he said it
    _fails(pg, "INSERT INTO ceo_gos (id, words, source, action, given_at)"
               " VALUES ('g1', 'go', 'sompong', 'spend', now())")
    for i, src in enumerate(("run:Q-20261014-0326-8968", "run:RUN-20261014-0219-f576", "chat:cto-c34459eb")):
        pg.execute("INSERT INTO ceo_gos (id, words, source, action, given_at) VALUES (?, 'go', ?, 'x', now())",
                   (f"g{i}", src))
    pg.commit()
    pg.execute("INSERT INTO post_ledger (platform, account, url, posted_at) VALUES ('fb', 'mimi', 'u1', now())")
    pg.commit()
    _fails(pg, "INSERT INTO post_ledger (platform, account, url, posted_at) VALUES ('fb', 'mimi', 'u1', now())")


@needs_pg
def test_resource_lock_is_one_holder_per_resource(pg):
    pg.execute("INSERT INTO resource_locks (resource, holder_session, until_at)"
               " VALUES ('browser:winbox-1', 'project_head-7cf528f0', now() + interval '1 hour')")
    pg.commit()
    _fails(pg, "INSERT INTO resource_locks (resource, holder_session, until_at)"
               " VALUES ('browser:winbox-1', 'project_head-6c487e37', now() + interval '1 hour')")

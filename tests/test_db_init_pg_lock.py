"""lib.db.init_schema() on Postgres: the advisory lock that makes concurrent
inits take turns, and the fast path that skips the DDL on a current schema
(task-1b8ef857: two inits at the same moment deadlocked on the hub and a
worker's org MCP server died at startup).

These run without a database. The same behaviour against a real Postgres is
in tests/test_db_backend_pg.py (needs ORG_TEST_DB_URL)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.db_pg as db_pg  # noqa: E402


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class _Catalog:
    """Answers _pg_schema_current's catalog reads from a fixed set of
    relation names, (table, column) pairs and trigger names."""

    def __init__(self, relations, columns, triggers=db_pg.PORTFOLIO_TRIGGER_NAMES,
                 kinds=db_pg.PROJECT_EVENT_KINDS):
        self.kinds = kinds
        self.relations = set(relations)
        self.columns = set(columns)
        self.triggers = set(triggers)
        self.queries: list[str] = []

    def execute(self, sql, params=()):
        self.queries.append(sql)
        if "pg_get_constraintdef" in sql:
            return _Rows([("CHECK (kind IN (" + ", ".join(map(repr, self.kinds)) + "))",)])
        if "pg_trigger" in sql:
            return _Rows([(name,) for name in self.triggers])
        asked = set(params[0])
        if "pg_class" in sql:
            return _Rows([(name,) for name in self.relations & asked])
        return _Rows([pair for pair in self.columns if pair[0] in asked])


def _complete_catalog():
    relations = set()
    for script in (db_pg.PG_SCHEMA, db_mod.JOIN_TOKENS_SCHEMA,
                   db_mod.NODE_SECRETS_SCHEMA):
        relations |= {n.lower() for n in re.findall(r"(?i)IF NOT EXISTS\s+(\w+)", script)}
    columns = {("tasks", c) for c, _ in db_mod._MIGRATION_COLUMNS}
    columns |= {("c_level_sessions", c) for c, _ in db_mod._C_LEVEL_SESSION_MIGRATION}
    columns |= {("hosts", c) for c, _ in db_mod._HOSTS_MIGRATION + db_mod._HOSTS_JOIN_MIGRATION}
    columns |= {("letters", c) for c, _ in db_mod._LETTERS_MIGRATION}
    columns |= {("live_sessions", c) for c, _ in db_mod._LIVE_SESSIONS_MIGRATION}
    columns |= {("projects", c) for c, _ in db_mod._PROJECTS_MIGRATION}
    columns |= {("milestones", c) for c, _ in db_mod._MILESTONES_MIGRATION}
    return relations, columns


def test_a_complete_schema_is_current():
    assert db_mod._pg_schema_current(_Catalog(*_complete_catalog())) is True


def test_every_pg_schema_statement_matches_scan():
    for stmt in db_pg._split_statements(db_pg.PG_SCHEMA):
        assert db_mod._PG_CREATE_RE.match(stmt), stmt


def test_sqlite_existing_projects_gets_tier_once():
    conn = db_mod.sqlite_connect(":memory:")
    try:
        conn.execute("CREATE TABLE projects (id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO projects VALUES ('p')")
        db_mod._create_and_migrate(conn, is_pg=False)
        db_mod._create_and_migrate(conn, is_pg=False)
        assert conn.execute("SELECT tier FROM projects").fetchone()[0] == "normal"
    finally:
        conn.close()


def test_missing_project_tier_is_not_current():
    relations, columns = _complete_catalog()
    columns.remove(("projects", "tier"))
    assert not db_mod._pg_schema_current(_Catalog(relations, columns))


@pytest.mark.parametrize("missing", db_pg.PROJECT_EVENT_KINDS)
def test_missing_event_kind_is_not_current(missing):
    kinds = tuple(k for k in db_pg.PROJECT_EVENT_KINDS if k != missing)
    assert not db_mod._pg_schema_current(_Catalog(*_complete_catalog(), kinds=kinds))


def test_constraint_migration_only_when_needed():
    class Hub(_Recorder):
        def __init__(self):
            super().__init__()
            self.current = False
            self.tier = False

        def execute(self, sql, params=()):
            out = super().execute(sql, params)
            if "pg_get_constraintdef" in sql:
                return _Rows([(db_pg.PROJECT_EVENT_KIND_CHECK,)]) if self.current else _Rows([])
            if "ADD CONSTRAINT project_events_kind_check" in sql:
                self.current = True
            if "PRAGMA table_info(projects)" in sql:
                return _Rows([{"name": c} for c in (["id"] + [c for c, _ in db_mod._PROJECTS_MIGRATION]
                                                    if self.tier else ["id"])])
            if "ALTER TABLE projects ADD" in sql:
                self.tier = True
            return out

    conn = Hub()
    db_mod._create_and_migrate(conn, is_pg=True)
    ddl = [s for s in conn.sql if s.startswith("ALTER TABLE project")]
    expected = db_pg._split_statements(
        (ROOT / "docs/design/projecttrack-p1-ddl.sql").read_text())
    assert set(ddl) == {" ".join(s.split()) for s in expected if s.startswith("ALTER TABLE project")}
    conn.sql.clear()
    db_mod._create_and_migrate(conn, is_pg=True)
    assert not [s for s in conn.sql if s.startswith("ALTER TABLE project")]


@pytest.mark.parametrize("missing", ["tasks", "idx_letters_to_host_status", "node_secrets"])
def test_a_missing_table_or_index_is_not_current(missing):
    relations, columns = _complete_catalog()
    assert missing in relations
    relations.discard(missing)
    assert db_mod._pg_schema_current(_Catalog(relations, columns)) is False


def test_a_missing_portfolio_trigger_is_not_current():
    assert db_mod._pg_schema_current(_Catalog(*_complete_catalog(), triggers=())) is False


def test_a_missing_live_sessions_verified_column_is_not_current():
    relations, columns = _complete_catalog()
    columns.discard(("live_sessions", "verified"))
    assert db_mod._pg_schema_current(_Catalog(relations, columns)) is False


def test_a_missing_live_sessions_bridge_id_column_is_not_current():
    """OrgMesh P8d: a hub without live_sessions.bridge_id runs the DDL, which adds it."""
    relations, columns = _complete_catalog()
    assert ("live_sessions", "bridge_id") in columns
    columns.discard(("live_sessions", "bridge_id"))
    assert db_mod._pg_schema_current(_Catalog(relations, columns)) is False


def test_a_missing_migration_column_is_not_current():
    relations, columns = _complete_catalog()
    columns.discard(("letters", "from_host"))
    assert db_mod._pg_schema_current(_Catalog(relations, columns)) is False


def test_the_dropped_claudesign_column_still_there_is_not_current():
    relations, columns = _complete_catalog()
    columns.add(("tasks", "claudesign_project_id"))
    assert db_mod._pg_schema_current(_Catalog(relations, columns)) is False


def test_a_statement_it_cannot_read_runs_the_ddl(monkeypatch):
    """A new kind of statement in a schema script (a view, a trigger) is never
    skipped: the check answers False before it reads the catalog."""
    monkeypatch.setattr(db_pg, "PG_SCHEMA",
                        db_pg.PG_SCHEMA + "\nCREATE OR REPLACE VIEW open_tasks AS SELECT 1;\n")
    catalog = _Catalog(*_complete_catalog())
    assert db_mod._pg_schema_current(catalog) is False
    assert catalog.queries == []


class _Recorder:
    """Records what init_schema sends instead of sending it."""

    def __init__(self):
        self.sql: list[str] = []
        self.params: list[tuple] = []

    def execute(self, sql, params=()):
        self.sql.append(" ".join(sql.split()))
        self.params.append(tuple(params))
        return _Rows([])

    def executescript(self, script):
        self.sql.append("SCRIPT")


class _PgRecorder(_Recorder, db_pg.Connection):
    def __init__(self):
        _Recorder.__init__(self)
        db_pg.Connection.__init__(self, None)


def _ddl(sql):
    return [s for s in sql if s == "SCRIPT" or s.split()[0] in ("CREATE", "ALTER", "DROP")]


def test_on_postgres_the_lock_comes_first_and_a_current_schema_skips_the_ddl(monkeypatch):
    monkeypatch.setattr(db_mod, "_pg_schema_current", lambda conn: True)
    conn = _PgRecorder()
    db_mod.init_schema(conn, is_pg=True)
    assert conn.sql[0].startswith("SELECT pg_advisory_xact_lock(")
    assert conn.params[0] == (db_mod._PG_INIT_LOCK_KEY,)
    assert _ddl(conn.sql) == []
    assert conn.sql[-1].startswith("UPDATE tasks")


def test_on_postgres_a_missing_piece_runs_the_ddl_under_the_lock(monkeypatch):
    monkeypatch.setattr(db_mod, "_pg_schema_current", lambda conn: False)
    conn = _PgRecorder()
    db_mod.init_schema(conn, is_pg=True)
    assert conn.sql[0].startswith("SELECT pg_advisory_xact_lock(")
    assert "SCRIPT" in conn.sql
    assert conn.sql[-1].startswith("UPDATE tasks")


class _LiveSessionsHas(_PgRecorder):
    """A hub whose live_sessions has exactly `cols`; every other table reads as empty."""

    def __init__(self, cols):
        super().__init__()
        self.cols = cols

    def execute(self, sql, params=()):
        out = super().execute(sql, params)
        if "PRAGMA table_info(live_sessions)" in sql:
            return _Rows([{"name": c} for c in self.cols])
        if "PRAGMA table_info" in sql:
            return _Rows([])
        return out


def _live_alters(conn):
    return [s for s in conn.sql if s.startswith("ALTER TABLE live_sessions")]


def test_the_migration_adds_bridge_id_to_a_live_sessions_table_that_lacks_it():
    """P8d: additive, nullable TEXT, and only when the column is missing (init runs on every start)."""
    assert ("bridge_id", "TEXT") in db_mod._LIVE_SESSIONS_MIGRATION
    old = _LiveSessionsHas({"host", "uuid", "verified"})
    db_mod._create_and_migrate(old, is_pg=True)
    assert _live_alters(old) == ["ALTER TABLE live_sessions ADD COLUMN bridge_id TEXT"]
    current = _LiveSessionsHas({"host", "uuid", "verified", "bridge_id"})
    db_mod._create_and_migrate(current, is_pg=True)
    assert _live_alters(current) == []
    fresh = _LiveSessionsHas(set())
    db_mod._create_and_migrate(fresh, is_pg=True)
    assert _live_alters(fresh) == ["ALTER TABLE live_sessions ADD COLUMN verified BOOLEAN",
                                   "ALTER TABLE live_sessions ADD COLUMN bridge_id TEXT"]


def test_a_connection_that_is_not_postgres_keeps_the_plain_path(monkeypatch):
    """The read-only snapshot that stands in for a down hub is SQLite
    underneath, though init() passes is_pg=True: no advisory lock, no
    catalog read, the DDL runs as before."""
    def no_catalog(conn):
        raise AssertionError("the catalog must not be read off Postgres")
    monkeypatch.setattr(db_mod, "_pg_schema_current", no_catalog)
    conn = _Recorder()
    db_mod.init_schema(conn, is_pg=True)
    assert not [s for s in conn.sql if "pg_advisory" in s]
    assert conn.sql[0] == "SCRIPT"


def test_the_lock_key_is_a_postgres_bigint():
    assert 0 < db_mod._PG_INIT_LOCK_KEY < 2 ** 63

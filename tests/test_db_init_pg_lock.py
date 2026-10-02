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


class _Catalog:
    """Answers _pg_schema_current's two catalog reads from a fixed set of
    relation names and (table, column) pairs."""

    def __init__(self, relations, columns):
        self.relations = set(relations)
        self.columns = set(columns)
        self.queries: list[str] = []

    def execute(self, sql, params=()):
        self.queries.append(sql)
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
    return relations, columns


def test_a_complete_schema_is_current():
    assert db_mod._pg_schema_current(_Catalog(*_complete_catalog())) is True


@pytest.mark.parametrize("missing", ["tasks", "idx_letters_to_host_status", "node_secrets"])
def test_a_missing_table_or_index_is_not_current(missing):
    relations, columns = _complete_catalog()
    assert missing in relations
    relations.discard(missing)
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

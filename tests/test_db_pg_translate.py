"""Pure unit tests for lib.db_pg._translate -- no DB, no psycopg connection
required (task brief gap 2). Covers the SQLite -> Postgres SQL rewriting
that lib.db.get_conn()'s Postgres backend relies on: `?` -> `%s`
placeholders (quote-aware, so a literal `?` inside a string survives),
`%` escaping (only when real params are supplied -- psycopg parses the
whole query text for `%s`/`%(name)s` placeholders whenever params are
passed, so any other literal `%` must be doubled or it's misread),
`INSERT OR REPLACE` -> `ON CONFLICT ... DO UPDATE`, and PRAGMA handling.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db_pg  # noqa: E402


# ---------------------------------------------------------------------------
# `?` -> `%s` placeholder translation
# ---------------------------------------------------------------------------

def test_plain_question_mark_params_translated():
    sql = "SELECT * FROM tasks WHERE id=? AND role=?"
    assert db_pg._translate(sql) == "SELECT * FROM tasks WHERE id=%s AND role=%s"


def test_literal_question_mark_inside_quoted_string_survives():
    sql = "SELECT * FROM tasks WHERE note = 'what?' AND id=?"
    assert (
        db_pg._translate(sql)
        == "SELECT * FROM tasks WHERE note = 'what?' AND id=%s"
    )


def test_question_mark_after_escaped_quote_still_translated():
    # 'it''s ok' is a single string literal (SQL's doubled-quote escape) --
    # the scan must not treat the first '' as the string's end and start
    # translating `?` too early.
    sql = "UPDATE tasks SET note='it''s ok' WHERE id=?"
    assert db_pg._translate(sql) == "UPDATE tasks SET note='it''s ok' WHERE id=%s"


# ---------------------------------------------------------------------------
# `%` escaping -- only when has_params=True
# ---------------------------------------------------------------------------

def test_percent_untouched_when_no_params():
    sql = "SELECT report FROM tasks WHERE report LIKE 'a%'"
    assert db_pg._translate(sql) == sql
    assert db_pg._translate(sql, has_params=False) == sql


def test_percent_escaped_to_double_when_params_present():
    sql = "SELECT report FROM tasks WHERE report LIKE 'a%'"
    assert (
        db_pg._translate(sql, has_params=True)
        == "SELECT report FROM tasks WHERE report LIKE 'a%%'"
    )


def test_percent_escaping_does_not_touch_inserted_placeholders():
    # The %s inserted for `?` must never itself become %%s.
    sql = "SELECT * FROM tasks WHERE id=? AND report LIKE 'a%'"
    assert (
        db_pg._translate(sql, has_params=True)
        == "SELECT * FROM tasks WHERE id=%s AND report LIKE 'a%%'"
    )


# ---------------------------------------------------------------------------
# INSERT OR REPLACE -> upsert
# ---------------------------------------------------------------------------

def test_insert_or_replace_on_mapped_table_becomes_upsert():
    sql = "INSERT OR REPLACE INTO locks (key,owner,expires_at) VALUES (?,?,?)"
    got = db_pg._translate(sql, has_params=True)
    assert got == (
        "INSERT INTO locks (key,owner,expires_at) VALUES (%s,%s,%s) "
        "ON CONFLICT (key) DO UPDATE SET owner = EXCLUDED.owner, "
        "expires_at = EXCLUDED.expires_at"
    )


def test_insert_or_replace_on_unmapped_table_raises():
    sql = "INSERT OR REPLACE INTO widgets (id,name) VALUES (?,?)"
    with pytest.raises(ValueError, match="widgets"):
        db_pg._translate(sql, has_params=True)


def test_plain_insert_is_not_touched_by_upsert_rewrite():
    sql = "INSERT INTO tasks (id,project) VALUES (?,?)"
    assert db_pg._translate(sql) == "INSERT INTO tasks (id,project) VALUES (%s,%s)"


# ---------------------------------------------------------------------------
# PRAGMA handling
# ---------------------------------------------------------------------------

def test_pragma_table_info_translated_to_information_schema():
    sql = "PRAGMA table_info(tasks)"
    assert db_pg._translate(sql) == (
        "SELECT column_name AS name FROM information_schema.columns "
        "WHERE table_name = 'tasks' ORDER BY ordinal_position"
    )


@pytest.mark.parametrize("sql", [
    "PRAGMA journal_mode=WAL;",
    "PRAGMA foreign_keys=ON;",
    "  PRAGMA journal_mode=WAL;  ",
])
def test_other_pragmas_are_skipped(sql):
    assert db_pg._translate(sql) is None


# ---------------------------------------------------------------------------
# Org Mesh W2.1 -- lib.db's hosts/letters SQL, offline sanity (task brief:
# "the SQL you add must pass lib.db_pg's offline _translate"). Neither
# statement is an `INSERT OR REPLACE` (upsert_host writes its own
# `ON CONFLICT ... DO UPDATE SET col=excluded.col`, valid Postgres syntax
# unchanged), so both should pass through _rewrite_insert_or_replace as a
# no-op and only get `?` -> `%s` placeholder translation.
# ---------------------------------------------------------------------------

def test_upsert_host_on_conflict_sql_translates_placeholders_only():
    sql = (
        "INSERT INTO hosts (host,os,max_workers,updated_at) VALUES (?,?,?,?) "
        "ON CONFLICT(host) DO UPDATE SET os=excluded.os, "
        "max_workers=excluded.max_workers, updated_at=excluded.updated_at"
    )
    assert db_pg._translate(sql, has_params=True) == (
        "INSERT INTO hosts (host,os,max_workers,updated_at) VALUES (%s,%s,%s,%s) "
        "ON CONFLICT(host) DO UPDATE SET os=excluded.os, "
        "max_workers=excluded.max_workers, updated_at=excluded.updated_at"
    )


def test_create_letter_returning_id_sql_translates_placeholders_only():
    sql = (
        "INSERT INTO letters "
        "(to_host,to_role,to_session,from_role,from_session,body,status,created_at,attempts) "
        "VALUES (?,?,?,?,?,?,?,?,?) RETURNING id"
    )
    got = db_pg._translate(sql, has_params=True)
    assert got.count("%s") == 9
    assert got.rstrip().endswith("RETURNING id")


def test_record_letter_attempt_returning_sql_translates_placeholders_only():
    sql = (
        "UPDATE letters SET attempts = attempts + 1, last_error = ? "
        "WHERE id = ? RETURNING attempts"
    )
    assert db_pg._translate(sql, has_params=True) == (
        "UPDATE letters SET attempts = attempts + 1, last_error = %s "
        "WHERE id = %s RETURNING attempts"
    )


# ---------------------------------------------------------------------------
# _split_statements -- W1.9 F1: a `;` in a `--` comment cut a CREATE TABLE in
# half and Postgres got "only id's AUTOINCREMENT ..." as a statement.
# ---------------------------------------------------------------------------

SQL_VERBS = ("CREATE", "ALTER", "INSERT", "UPDATE", "DROP", "DO")


def test_every_statement_of_pg_schema_starts_with_a_sql_verb():
    """The only script lib.db sends through the Postgres executescript is PG_SCHEMA
    (init_schema; the ADD COLUMN migrations and the backfill go through execute(), and
    SNAPSHOT_META_SCHEMA goes to a sqlite3 connection). A stray fragment fails here
    without a Postgres."""
    stmts = db_pg._split_statements(db_pg.PG_SCHEMA)
    assert len(stmts) > 10
    bad = [s.splitlines()[0] for s in stmts if s.split(None, 1)[0].upper() not in SQL_VERBS]
    assert bad == []


def test_no_split_statement_of_pg_schema_carries_comment_prose():
    for s in db_pg._split_statements(db_pg.PG_SCHEMA):
        assert not any(ln.lstrip().startswith("--") for ln in s.splitlines()), s


def test_semicolon_inside_a_comment_line_makes_no_stray_statement():
    script = (
        "CREATE TABLE a (x INTEGER);\n"
        "-- Column shapes are identical; only id's AUTOINCREMENT -> IDENTITY changes,\n"
        "CREATE TABLE b (\n"
        "    -- a note; with a semicolon inside the column list\n"
        "    y INTEGER\n"
        ");\n"
    )
    assert db_pg._split_statements(script) == [
        "CREATE TABLE a (x INTEGER)",
        "CREATE TABLE b (\n    y INTEGER\n)",
    ]


def test_split_keeps_a_double_dash_that_is_not_a_full_line_comment():
    """Only full-line comments are dropped; `--` inside a statement line stays."""
    assert db_pg._split_statements("SELECT 1 -- one\n;\nSELECT 2;") == ["SELECT 1 -- one", "SELECT 2"]

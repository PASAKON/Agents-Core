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

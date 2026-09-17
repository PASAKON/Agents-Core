"""Tests for the charter gate (task-a63759d5, IRON-RULES §35).

lib.db.create_task() refuses to create a task for a CTO/CXO session with no
charter row set — /session-open alone can't enforce this since that skill
never writes to the DB. tools/session_charter.py is the write side.

Run via:  pytest tests/test_session_charter.py
(not in pytest.ini's default `testpaths` — run explicitly, same convention
as tests/test_multihost.py.)
"""
from __future__ import annotations

import pytest

from lib import db as db_mod
from tools import session_charter


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    monkeypatch.delenv("CTO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("CXO_ROLE", raising=False)
    monkeypatch.delenv("ORG_CHARTER_GATE", raising=False)


def _create(**overrides):
    kwargs = dict(project="test-proj", role="developer", title="t", description="d")
    kwargs.update(overrides)
    return db_mod.create_task(**kwargs)


def test_create_task_passes_with_charter(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest1")
    db_mod.register_cxo_session("cto", "ctotest1")
    session_charter.set_charter("fix the leaderboard dedup bug end to end")
    tid = _create()
    assert tid.startswith("task-")


def test_create_task_fails_when_charter_empty(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest2")
    db_mod.register_cxo_session("cto", "ctotest2")  # registered, charter stays NULL
    with pytest.raises(RuntimeError, match="has no charter set"):
        _create()


def test_create_task_fails_when_session_not_registered(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctoghost")  # no register_cxo_session call
    with pytest.raises(RuntimeError, match="has no charter set"):
        _create()


def test_create_task_owner_cto_none_passes_with_warning(monkeypatch, capsys):
    # No CTO_SESSION_ID / CXO_SESSION_ID at all -- unchanged legacy path.
    tid = _create()
    assert tid.startswith("task-")
    assert "WARNING: creating ownerless task" in capsys.readouterr().err


def test_org_charter_gate_off_passes_with_warning(monkeypatch, capsys):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest3")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    # No registration at all -- escape hatch must still let it through.
    tid = _create()
    assert tid.startswith("task-")
    assert "ORG_CHARTER_GATE=off" in capsys.readouterr().err


def test_create_task_passes_with_charter_cxo_env(monkeypatch):
    monkeypatch.setenv("CXO_SESSION_ID", "cfotest1")
    monkeypatch.setenv("CXO_ROLE", "cfo")
    db_mod.register_cxo_session("cfo", "cfotest1")
    session_charter.set_charter("close out the Q3 invoice reconciliation")
    tid = _create()
    assert tid.startswith("task-")


_PRE_MIGRATION_DDL = """
CREATE TABLE c_level_sessions (
    role             TEXT NOT NULL,
    session_id       TEXT NOT NULL,
    active_task_id   TEXT,
    spawned_at       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'open',
    closed_at        TEXT,
    note             TEXT,
    resume_uuid      TEXT,
    PRIMARY KEY (role, session_id)
)
"""


def _downgrade_to_pre_charter_schema(session_id: str) -> None:
    """Recreate c_level_sessions WITHOUT the host/charter columns and insert
    one registered session — the state of a box that pulled the code but
    never ran db.init() (Contabo, 2026-09-17)."""
    with db_mod.get_conn() as conn:
        conn.execute("DROP TABLE IF EXISTS c_level_sessions")
        conn.execute(_PRE_MIGRATION_DDL)
        conn.execute(
            "INSERT INTO c_level_sessions (role, session_id, spawned_at) VALUES (?,?,?)",
            ("cto", session_id, "2026-09-17T00:00:00+00:00"),
        )


def test_gate_on_pre_migration_db_names_the_fix(monkeypatch):
    # The gate must still fail closed, but tell the operator to run db.init()
    # instead of surfacing a bare `no such column: charter`.
    monkeypatch.setenv("CTO_SESSION_ID", "ctoold1")
    _downgrade_to_pre_charter_schema("ctoold1")
    with pytest.raises(RuntimeError) as ei:
        _create()
    msg = str(ei.value)
    assert "db.init()" in msg
    assert "session_charter set" in msg
    assert "no such column" in msg  # the underlying cause stays visible


def test_cli_migrates_before_touching_charter(monkeypatch, capsys):
    # tools.session_charter's entry point runs db.init() first, so `get` on a
    # pre-migration DB adds the column and reports the (empty) charter rather
    # than crashing on the missing column.
    monkeypatch.setenv("CTO_SESSION_ID", "ctoold2")
    _downgrade_to_pre_charter_schema("ctoold2")
    rc = session_charter.main(["get"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "(empty)" in out
    with db_mod.get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(c_level_sessions)")}
    assert "charter" in cols and "host" in cols


def test_set_charter_rejects_empty_and_short(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest4")
    db_mod.register_cxo_session("cto", "ctotest4")
    with pytest.raises(ValueError):
        session_charter.set_charter("")
    with pytest.raises(ValueError):
        session_charter.set_charter("   ")
    with pytest.raises(ValueError):
        session_charter.set_charter("short")


def test_set_charter_writes_and_get_roundtrips(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest5")
    db_mod.register_cxo_session("cto", "ctotest5")
    session_charter.set_charter("fix the flaky deploy pipeline end to end")
    assert session_charter.get_charter() == "fix the flaky deploy pipeline end to end"


def test_set_charter_refuses_unregistered_session_no_silent_insert(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctoghost2")  # never spawned
    with pytest.raises(RuntimeError, match="not registered"):
        session_charter.set_charter("this session was never spawned properly")
    with db_mod.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM c_level_sessions WHERE session_id=?", ("ctoghost2",)
        ).fetchone()
    assert row is None  # set() must never silently INSERT a session row


def test_clear_charter_empties_it_and_regate(monkeypatch):
    monkeypatch.setenv("CTO_SESSION_ID", "ctotest6")
    db_mod.register_cxo_session("cto", "ctotest6")
    session_charter.set_charter("close out the multihost rollout")
    session_charter.clear_charter()
    assert session_charter.get_charter() is None
    with pytest.raises(RuntimeError, match="has no charter set"):
        _create()


def test_get_and_clear_require_a_session_id(monkeypatch):
    with pytest.raises(RuntimeError, match="no session id in env"):
        session_charter.get_charter()
    with pytest.raises(RuntimeError, match="no session id in env"):
        session_charter.clear_charter()

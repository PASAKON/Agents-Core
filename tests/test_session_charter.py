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

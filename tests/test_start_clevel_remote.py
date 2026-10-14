import asyncio
import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from tools import start_clevel_remote as m


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CXO_SESSION_ID", "abcdef01")
    monkeypatch.setattr(m, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(m.roles, "c_level_roles", lambda: ("cto", "cmo", "coo"))
    monkeypatch.setattr(m.config, "live_c_level_roles", lambda: ("cto", "cmo", "coo"))
    monkeypatch.setattr(m.config, "self_host", lambda: "mac")
    monkeypatch.setattr(m.config, "hosts", lambda: {
        "mac": {"mesh_ssh": "a@mac"}, "contabo": {"mesh_ssh": "a@contabo"},
        "winbox": {"mesh_ssh": None}})
    monkeypatch.setattr(m.mesh, "enabled", lambda: True)
    dispatch = Mock(return_value={"ok": True, "result": {"session_id": "12345678"}})
    monkeypatch.setattr(m.mesh, "dispatch", dispatch)
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (task_id, actor, kind, payload, ts)")

    @contextmanager
    def get_conn():
        yield conn

    monkeypatch.setattr(m.db, "get_conn", get_conn)
    yield dispatch, conn
    conn.close()


@pytest.mark.parametrize("guard", ["caller", "role", "singleton", "unknown", "closed", "self", "resume", "disabled"])
def test_guards_before_dispatch(setup, monkeypatch, guard):
    dispatch, conn = setup
    host, role, sid = "contabo", "cto", ""
    if guard == "caller":
        monkeypatch.setenv("CXO_ROLE", "developer")
    elif guard == "role":
        role = "developer"
    elif guard == "singleton":
        role = "coo"
    elif guard == "unknown":
        host = "missing"
    elif guard == "closed":
        host = "winbox"
    elif guard == "self":
        host = "mac"
    elif guard == "resume":
        sid = "ABCDEF01"
    else:
        monkeypatch.setattr(m.mesh, "enabled", lambda: False)
    assert not json.loads(m.start_clevel_remote(host, role, sid))["ok"]
    dispatch.assert_not_called()
    assert not m.STATE.exists()
    row = conn.execute("SELECT actor, kind, payload FROM events").fetchone()
    assert row[:2] == ("start_clevel_remote", "mesh_start")
    assert json.loads(row[2])["ok"] is False


def test_allowed_audit_and_resume(setup):
    dispatch, conn = setup
    assert json.loads(m.start_clevel_remote("contabo", "cto", "abcdef01")) == dispatch.return_value
    dispatch.assert_called_once_with("contabo", "start_clevel", "cto", "--resume", "abcdef01")
    payload = json.loads(conn.execute("SELECT payload FROM events").fetchone()[0])
    assert payload == {"host": "contabo", "role": "cto", "resumed_from": "abcdef01",
                       "caller_role": "cto", "caller_session": "abcdef01", "ok": True,
                       "outcome": "allowed"}


def test_pair_window(setup, monkeypatch):
    dispatch, _ = setup
    clock = Mock(return_value=10000)
    monkeypatch.setattr(m.time, "time", clock)
    assert json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]
    clock.return_value += 599
    assert not json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]
    assert dispatch.call_count == 1
    clock.return_value += 1
    assert json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]
    assert dispatch.call_count == 2


def test_hour_window(setup, monkeypatch):
    dispatch, _ = setup
    monkeypatch.setattr(m.time, "time", lambda: 10000)
    m.STATE.write_text(json.dumps([{"host": "other", "role": "cto", "at": 6401}] * 6))
    assert not json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]
    dispatch.assert_not_called()
    monkeypatch.setattr(m.time, "time", lambda: 10001)
    assert json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]


@pytest.mark.parametrize("text", ["broken", "{}", '[{"at": "bad"}]'])
def test_corrupt_state_is_empty(setup, text):
    m.STATE.write_text(text)
    assert json.loads(m.start_clevel_remote("contabo", "cto"))["ok"]
    assert len(json.loads(m.STATE.read_text())) == 1


@pytest.mark.parametrize("age", [0, 60])
def test_busy_lock_refuses(setup, monkeypatch, age):
    dispatch, _ = setup
    monkeypatch.setattr(m.time, "time", lambda: 10000)
    lock = m.STATE.with_suffix(".lock")
    lock.touch()
    os.utime(lock, (10000 - age, 10000 - age))
    assert json.loads(m.start_clevel_remote("contabo", "cto")) == {
        "ok": False, "error": "rate limit state busy"}
    dispatch.assert_not_called()
    assert lock.exists()


def test_old_lock_taken_over(setup, monkeypatch):
    dispatch, _ = setup
    monkeypatch.setattr(m.time, "time", lambda: 10000)
    lock = m.STATE.with_suffix(".lock")
    lock.touch()
    os.utime(lock, (9939, 9939))
    assert json.loads(m.start_clevel_remote("contabo", "cto")) == dispatch.return_value
    dispatch.assert_called_once_with("contabo", "start_clevel", "cto")
    assert len(json.loads(m.STATE.read_text())) == 1
    assert not lock.exists()


def test_audit_failure_does_not_hide_result(setup, monkeypatch):
    dispatch, _ = setup
    monkeypatch.setattr(m.db, "log_event", Mock(side_effect=RuntimeError("hub offline")))
    assert json.loads(m.start_clevel_remote("contabo", "cto")) == dispatch.return_value


@pytest.mark.parametrize("redactor_available", [True, False])
def test_unreachable_audited_without_stderr(setup, monkeypatch, redactor_available):
    dispatch, conn = setup
    detail = "ssh failed: https://user:password@example.com " + "stderr " * 100
    expected = detail.replace("user:password", "***")
    if not redactor_available:
        monkeypatch.setitem(sys.modules, "tools.node_dispatch", None)
        expected = detail
    dispatch.side_effect = m.mesh.MeshUnreachable(detail)
    assert json.loads(m.start_clevel_remote("contabo", "cto")) == {
        "ok": False, "error": "unreachable", "detail": expected[:200]}
    payload = conn.execute("SELECT payload FROM events").fetchone()[0]
    assert json.loads(payload)["outcome"] == "MeshUnreachable"
    assert "stderr" not in payload and "password" not in payload
    assert "detail" not in json.loads(payload)


def test_registry_and_mcp(setup, monkeypatch):
    from lib import org_tools_registry as reg
    from runners import cto_mcp_server as srv

    async def inline_thread(fn, *args):
        return fn(*args)

    # Exercise the wiring without a thread-pool socket wakeup in the sandbox.
    monkeypatch.setattr(reg.asyncio, "to_thread", inline_thread)

    async def check():
        specs = await srv.mcp.list_tools()
        spec = next(s for s in specs if s.name == "start_clevel_remote")
        assert set(spec.inputSchema["properties"]) == {"host", "role", "resume_session_id"}
        assert set(spec.inputSchema["required"]) == {"host", "role"}
        assert spec.inputSchema["properties"]["resume_session_id"]["default"] == ""
        fake = Mock(return_value='{"ok": true}')
        monkeypatch.setattr(m, "start_clevel_remote", fake)
        assert await reg.dispatch("start_clevel_remote", host="contabo", role="cto") == '{"ok": true}'
        assert await srv.start_clevel_remote("contabo", "cto", "abcdef01") == '{"ok": true}'
        fake.assert_called_with("contabo", "cto", "abcdef01")

    asyncio.run(check())

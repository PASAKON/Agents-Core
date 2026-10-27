"""COO CEO-only email and read-only quota tools; no live hub calls."""
import asyncio
from datetime import datetime, timedelta, timezone
import inspect
import json
import sys
import types

import pytest

from runners import coo_mcp_server as server
from tools import email_ceo


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(email_ceo, "_post", lambda *a, **kw: pytest.fail("unexpected hub call"))


def test_email_identity_and_cli(monkeypatch, capsys):
    monkeypatch.setenv("CXO_SESSION_ID", " coo-test1234 ")
    seen = {}

    def send(arguments):
        seen.update(arguments)
        return {"id": "mail-1"}

    monkeypatch.setattr(email_ceo, "mcp_send", send)
    args = dict(kind="done", title="Finished", role="cto", session="other", dry_run=True)
    assert server._cli(["email_ceo", json.dumps(args)]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "id": "mail-1"}
    assert seen == {**args, "role": "coo", "session": "coo-test1234"}


@pytest.mark.parametrize("sid", [None, "", "  "])
def test_email_requires_cxo_session(monkeypatch, sid):
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    if sid is not None:
        monkeypatch.setenv("CXO_SESSION_ID", sid)
    monkeypatch.setenv("COO_SESSION_ID", "legacy-fallback")
    monkeypatch.setattr(email_ceo, "mcp_send", lambda a: pytest.fail("missing session sent"))
    out = server.email_ceo(kind="done", session="caller-session")
    assert out["ok"] is False
    assert "CXO_SESSION_ID" in out["error"]


@pytest.mark.parametrize("error", [email_ceo.Refused, email_ceo.HubError, ValueError])
def test_email_errors(monkeypatch, error):
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test1234")

    def fail(arguments):
        raise error("test refusal")

    monkeypatch.setattr(email_ceo, "mcp_send", fail)
    assert server.email_ceo(kind="done") == {"ok": False, "error": "test refusal"}


@pytest.mark.parametrize("age,stale", [(0, False), (7200, False), (7201, True)])
def test_quota_filtered_and_stale(tmp_path, monkeypatch, capsys, age, stale):
    now = datetime(2026, 10, 26, tzinfo=timezone.utc)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now

    monkeypatch.setattr(server, "datetime", Clock)
    path = tmp_path / "snapshot.json"
    monkeypatch.setattr(server, "QUOTA_PATH", path)
    bucket = dict(weekly_remaining=0.5, daily_remaining=0.8, weekly_resets_at=None,
                  daily_resets_at=None, limit_hit=True, limit_until="later", error="limited")
    ts = (now - timedelta(seconds=age)).isoformat()
    path.write_text(json.dumps({"ts": ts, "buckets": {
        "claude": {**bucket, "source": "/private/source", "provider": "claude"}}}))
    assert server._cli(["quota"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"ok": True, "ts": ts, "buckets": {"claude": bucket},
                   **({"stale": True} if stale else {})}


@pytest.mark.parametrize("contents,cause", [(None, "FileNotFoundError"),
                                           ("{", "JSONDecodeError"),
                                           ('{"ts": "bad"}', "ValueError"),
                                           ('{}', "KeyError")])
def test_quota_bad_file(tmp_path, monkeypatch, contents, cause):
    path = tmp_path / "snapshot.json"
    monkeypatch.setattr(server, "QUOTA_PATH", path)
    if contents is not None:
        path.write_text(contents)
    out = server.quota()
    assert out["ok"] is False
    assert cause in out["error"]


def test_quota_unreadable(monkeypatch):
    class Unreadable:
        def read_text(self, **kwargs):
            raise PermissionError("permission denied")

    monkeypatch.setattr(server, "QUOTA_PATH", Unreadable())
    assert server.quota() == {"ok": False, "error": "quota snapshot: PermissionError: permission denied"}


def test_mcp_registration_and_fields(monkeypatch):
    registered = {}

    class MCP:
        def __init__(self, name):
            pass

        def tool(self, name):
            def register(fn):
                registered[name] = fn
                return fn
            return register

        def run(self):
            pass

    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", types.SimpleNamespace(FastMCP=MCP))
    server._serve()
    assert {"email_ceo", "quota"} <= set(server.TOOL_NAMES)
    assert set(registered) == set(server.TOOL_NAMES)
    assert set(inspect.signature(registered["email_ceo"]).parameters) == {
        "kind", *email_ceo.FIELDS, "dry_run"}
    # Exercise argument forwarding without starting an executor in the test sandbox.
    async def to_thread(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", to_thread)
    monkeypatch.setattr(server, "email_ceo", lambda **a: {"ok": True, **a})
    out = json.loads(asyncio.run(registered["email_ceo"](kind="done", title="Finished")))
    assert out["ok"] and out["kind"] == "done"
    monkeypatch.setattr(server, "quota", lambda: {"ok": True, "buckets": {}})
    assert json.loads(registered["quota"]()) == {"ok": True, "buckets": {}}


def test_field_note_sends_the_gate_op_with_this_session(monkeypatch):
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test1234")
    sent = {}
    monkeypatch.setattr(server, "call", lambda op, **fields: sent.update(op=op, **fields) or {"ok": True})
    assert server.field_note("ALL_Rules_Approvals", "WRONG", "one line") == {"ok": True}
    assert sent == {"op": "field_note", "session_id": "coo-test1234", "skill": "ALL_Rules_Approvals",
                    "tag": "WRONG", "text": "one line"}


def test_field_note_needs_a_session(monkeypatch):
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("COO_SESSION_ID", raising=False)
    monkeypatch.setattr(server, "call", lambda *a, **k: pytest.fail("sent without a session"))
    out = server.field_note("ALL_Rules_Approvals", "WRONG", "x")
    assert out["ok"] is False and "CXO_SESSION_ID" in out["error"]


def test_field_note_is_a_cli_and_an_mcp_tool(monkeypatch, capsys):
    assert "field_note" in server.TOOL_NAMES and server.TOOL_NAMES[-1] == "respawn_clevel"
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test1234")
    monkeypatch.setattr(server, "call", lambda op, **fields: {"ok": True, "op": op, "tag": fields["tag"]})
    args = {"skill": "ALL_Rules_Approvals", "tag": "COSTLY", "text": "t"}
    assert server._cli(["field_note", json.dumps(args)]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "op": "field_note", "tag": "COSTLY"}

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
    assert {"field_note", "respawn_clevel"} <= set(server.TOOL_NAMES)
    monkeypatch.setenv("CXO_SESSION_ID", "coo-test1234")
    monkeypatch.setattr(server, "call", lambda op, **fields: {"ok": True, "op": op, "tag": fields["tag"]})
    args = {"skill": "ALL_Rules_Approvals", "tag": "COSTLY", "text": "t"}
    assert server._cli(["field_note", json.dumps(args)]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "op": "field_note", "tag": "COSTLY"}


def test_order_tools_send_the_gate_op_with_this_session(monkeypatch):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    sent = []
    monkeypatch.setattr(server, "call", lambda op, **fields: sent.append({"op": op, **fields}) or {"ok": True})
    assert server.order_open(7, "ship it", "2026-10-30T17:00:00+07:00") == {"ok": True}
    assert server.order_open(8, "no date") == {"ok": True}
    assert server.order_open(9, "empty date", "") == {"ok": True}      # "" means no date, not a bad one
    assert server.order_close("O-20261027-1403-ab12", "done") == {"ok": True}
    assert sent == [
        {"op": "order_open", "session_id": "c0de0001", "n": 7, "words": "ship it", "due_at": "2026-10-30T17:00:00+07:00"},
        {"op": "order_open", "session_id": "c0de0001", "n": 8, "words": "no date", "due_at": None},
        {"op": "order_open", "session_id": "c0de0001", "n": 9, "words": "empty date", "due_at": None},
        {"op": "order_close", "session_id": "c0de0001", "order_id": "O-20261027-1403-ab12", "outcome": "done"},
    ]


def test_order_tools_need_a_session(monkeypatch):
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("COO_SESSION_ID", raising=False)
    monkeypatch.setattr(server, "call", lambda *a, **k: pytest.fail("sent without a session"))
    for out in (server.order_open(7, "x"), server.order_close("O-20261027-1403-ab12", "x")):
        assert out["ok"] is False and "CXO_SESSION_ID" in out["error"]


def test_order_tools_are_cli_entries_and_mcp_tools(monkeypatch, capsys):
    assert {"order_open", "order_close"} <= set(server.TOOL_NAMES)
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    monkeypatch.setattr(server, "call", lambda op, **fields: {"ok": True, "op": op, "n": fields.get("n")})
    assert server._cli(["order_open", json.dumps({"n": 3, "words": "w"})]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "op": "order_open", "n": 3}
    assert server._cli(["order_close", json.dumps({"order_id": "O-20261027-1403-ab12", "outcome": "o"})]) == 0
    assert json.loads(capsys.readouterr().out)["op"] == "order_close"


# --------------------------------------------------------------------------- portfolio (the Project Monitor read)

PORTFOLIO_LINES = ["Alpha film · cmo · 50% · working · record the voice · 2026-10-28T12:00:00Z",
                   "Beta loop · cgo · 0% (รอบที่ 1) · stalled · — · 2026-10-27T12:00:00Z"]


def test_portfolio_sends_the_gate_op_with_this_session(monkeypatch):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    sent = []
    monkeypatch.setattr(server, "call", lambda op, **fields: sent.append({"op": op, **fields}) or {"ok": True})
    assert server.portfolio() == {"ok": True}
    assert sent == [{"op": "portfolio", "session_id": "c0de0001"}]       # nothing else can be asked for


def test_portfolio_needs_a_session(monkeypatch):
    monkeypatch.delenv("CXO_SESSION_ID", raising=False)
    monkeypatch.delenv("COO_SESSION_ID", raising=False)
    monkeypatch.setattr(server, "call", lambda *a, **k: pytest.fail("sent without a session"))
    out = server.portfolio()
    assert out["ok"] is False and "CXO_SESSION_ID" in out["error"]


def test_portfolio_is_a_tool_and_the_session_may_call_it():
    assert "portfolio" in server.TOOL_NAMES
    assert server.TOOL_NAMES.count("portfolio") == 1


def test_portfolio_cli_prints_one_line_per_project(monkeypatch, capsys):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    monkeypatch.setattr(server, "call", lambda op, **f: {"ok": True, "op": op, "payload": {"v": 2}, "text": PORTFOLIO_LINES})
    assert server._cli(["portfolio"]) == 0
    assert capsys.readouterr().out == "\n".join(PORTFOLIO_LINES) + "\n"           # lines, not JSON


def test_portfolio_cli_json_prints_the_whole_answer(monkeypatch, capsys):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    monkeypatch.setattr(server, "call", lambda op, **f: {"ok": True, "payload": {"v": 2}, "text": PORTFOLIO_LINES})
    assert server._cli(["portfolio", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"ok": True, "payload": {"v": 2}, "text": PORTFOLIO_LINES}


def test_portfolio_cli_with_no_projects_prints_nothing(monkeypatch, capsys):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    monkeypatch.setattr(server, "call", lambda op, **f: {"ok": True, "payload": {"v": 2, "projects": []}, "text": []})
    assert server._cli(["portfolio"]) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("flags", [[], ["--json"]])
def test_portfolio_cli_failure_prints_the_error_and_exits_1(monkeypatch, capsys, flags):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    err = {"ok": False, "error": "the portfolio could not be read from the hub (OperationalError)"}
    monkeypatch.setattr(server, "call", lambda op, **f: err)
    assert server._cli(["portfolio", *flags]) == 1
    assert json.loads(capsys.readouterr().out) == err


def test_portfolio_cli_when_the_gate_is_not_running(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("CXO_SESSION_ID", "c0de0001")
    monkeypatch.setattr(server, "SOCKET_PATH", str(tmp_path / "missing.sock"))
    assert server._cli(["portfolio"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and "COO gate is not running" in out["error"]


def test_portfolio_mcp_tool_answers_with_the_lines_or_the_payload(monkeypatch):
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
    assert set(inspect.signature(registered["portfolio"]).parameters) == {"raw"}
    answer = {"ok": True, "payload": {"v": 2}, "text": PORTFOLIO_LINES}
    monkeypatch.setattr(server, "portfolio", lambda: answer)
    assert registered["portfolio"]() == "\n".join(PORTFOLIO_LINES)
    assert json.loads(registered["portfolio"](raw=True)) == answer
    failed = {"ok": False, "error": "nope"}
    monkeypatch.setattr(server, "portfolio", lambda: failed)
    assert json.loads(registered["portfolio"]()) == failed
    empty = {"ok": True, "payload": {"v": 2, "projects": []}, "text": []}
    monkeypatch.setattr(server, "portfolio", lambda: empty)
    assert json.loads(registered["portfolio"]()) == empty              # no lines: the payload, not an empty string

"""Console brief.js (0416f5b) parity; vectors evaluated with Node, no Console import."""
import hashlib
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from tools import ask_run


@pytest.mark.parametrize("body, digest", [
    ({"command": "printf hello"}, "2189aff6492b39e6aa62f939b98cbc0cfaa1392da9df3a5ef73a7b0b369119d3"),
    ({"command": "printf hello", "what": "Update", "does": "", "impact": "Safe"},
     "8ef875b112ce291cb4eb4ca742cee4a0fc150a0e6225ffefa68eab584f5a719f"),
    ({"command": 'printf "ไทย😀"\n', "what": "ดูงาน", "does": "Read \\ files", "impact": "<ok>/"},
     "bf5b724b5f3a8d03c89f22c263c1241c5025810ede6ff24487a61d46c30fe089"),
])
def test_console_hash_vectors(body, digest):
    assert hashlib.sha256(ask_run.command_canonical(body).encode()).hexdigest() == digest


def command(**extra):
    return ask_run.mcp_ask(dict(host="contabo", command="printf hello", why="Read status",
                               session="cto-test", role="cto", dry_run=True, **extra), env={})["payload"]


def test_brief_trim_and_hash():
    body = command(what="  " + "😀" * 41 + "  ", does="Read", impact="Safe", expected="x" * 500)
    assert body["what"] == "😀" * 39 + "…"
    assert body["expected"] == "x" * 89 + "…"
    assert body["sha256"] == hashlib.sha256(ask_run.command_canonical(body).encode()).hexdigest()
    assert body["requester"]["lane"] == "cto"


@pytest.mark.parametrize("value", ["x" * 100 + "\u200b", "x" * 100 + "\u202e", "x" * 100 + "\ue000",
                                   "x" * 100 + " token=" + "q7" * 12])
def test_brief_checks_before_truncation(value):
    with pytest.raises(ask_run.Refused):
        command(what=value)


def test_detail_checks_before_truncation():
    for value in ("x" * 100 + "\u200b", "x" * 100 + " token=" + "q7" * 12):
        with pytest.raises(ask_run.Refused):
            command(what="Read", expected=value)
    with pytest.raises(ask_run.Refused):
        command(expected="x" * 100)


def test_question_brief():
    ns = ask_run._mcp_question_namespace(dict(question="Which colour?", options=["Blue", "Green"],
        why="x" * 1200, what="Choose colour", session="cto-test", role="cto", host="contabo"))
    body = ask_run.prepare_question(ns, env={})
    assert body["why"] == "x" * 89 + "…"
    assert body["what"] == "Choose colour"
    assert body["requester"]["lane"] == "cto"


@pytest.mark.parametrize("rows, expected", [
    ([{"name": "MoonieXConsole", "lane": "cto"}], {"lane": "cto", "project": "MoonieXConsole"}),
    ([], {}), ([{"name": "bad name", "lane": "cto"}], {}),
])
def test_ph_metadata(monkeypatch, rows, expected):
    from lib import portfolio
    @contextmanager
    def tx():
        def execute(sql, params):
            assert params == ("project_head-12345678", "12345678")
            return SimpleNamespace(fetchall=lambda: rows)
        yield SimpleNamespace(execute=execute)
    monkeypatch.setattr(portfolio, "_tx", tx)
    assert ask_run.resolve_requester("project_head-12345678", "project_head", None, env={}) == {
        "session": "project_head-12345678", "role": "project_head", **expected}


def test_ph_lookup_failure(monkeypatch):
    from lib import portfolio
    def fail():
        raise RuntimeError("offline")
    monkeypatch.setattr(portfolio, "_tx", fail)
    assert ask_run._requester_project("project_head-test") == {}


@pytest.mark.parametrize("role", ["cto", "cmo", "coo", "cfo", "cgo"])
def test_all_clevel_lanes(role):
    assert ask_run.resolve_requester(role + "-test", role, None, env={})["lane"] == role


def test_cli_and_mcp_command_parity():
    ns = ask_run._parser().parse_args(["create", "--host", "contabo", "--command", "printf hello",
        "--why", "Read status", "--what", "Read", "--does", "Check", "--impact", "Safe",
        "--session", "cto-test", "--role", "cto", "--dry-run"])
    assert ask_run.prepare_ask(ns, [], env={}) == command(what="Read", does="Check", impact="Safe")


def test_group_inherits_brief_and_item_can_override():
    result = ask_run.mcp_ask_ceo(dict(questions=[dict(question="Which colour?", why="x" * 100,
        options=["Blue", "Green"], impact="Local")], what="Choose", impact="Shared",
        session="cto-test", role="cto", host="contabo", dry_run=True), env={})
    item = result["payload"]["questions"][0]
    assert item["what"] == "Choose"
    assert item["impact"] == "Local"
    assert item["why"] == "x" * 89 + "…"


def test_empty_brief_preserves_plain_command_hash():
    body = command(what="   ", does="", impact=None)
    assert not any(k in body for k in ask_run.BRIEF_LIMITS)
    assert body["sha256"] == "2189aff6492b39e6aa62f939b98cbc0cfaa1392da9df3a5ef73a7b0b369119d3"

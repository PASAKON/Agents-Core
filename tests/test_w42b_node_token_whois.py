"""Caller identity checks: no live tailscaled, hub, secret or network required."""
import contextlib
import io
import json
import subprocess
from types import SimpleNamespace
import urllib.error

import pytest

from tools import node_token, node_token_api as api


@pytest.fixture(autouse=True)
def no_drill(monkeypatch):
    monkeypatch.delenv("DRILL_HUB_ENV", raising=False)


def whois_result(monkeypatch, body, rc=0):
    calls = []

    def run(argv, **kw):
        calls.append((argv, kw))
        return SimpleNamespace(returncode=rc, stdout=body, stderr=b"private diagnostic")

    monkeypatch.setattr(api.subprocess, "run", run)
    return calls


def handler(monkeypatch, host="node-a", source="100.64.0.2", row=None):
    seen = []
    if row is None:
        row = {"status": "online", "pubkey": "fake-recipient", "approved_at": "yes"}

    class Conn:
        def execute(self, query, args):
            seen.append((query, args))
            return SimpleNamespace(fetchone=lambda: row)

    @contextlib.contextmanager
    def hub():
        yield Conn()

    monkeypatch.setattr(api, "_hub", hub)

    def seal(recipient, payload):
        seen.append("sealed")
        return b"synthetic sealed answer"

    server = SimpleNamespace(tokens={node_token.DEFAULT_NAME: "synthetic"}, sealer=seal,
                             host_limiter=api.RateLimiter(1, 60))
    return SimpleNamespace(path=f"/v1/token?host={host}", client_address=(source, 1234),
                           server=server), seen


@pytest.mark.parametrize("name", ["node-a", "node-a.tail123.ts.net."])
def test_match_grants_and_uses_bounded_subprocess(monkeypatch, name):
    calls = whois_result(monkeypatch, json.dumps({"Node": {"Name": name}}))
    h, seen = handler(monkeypatch)
    assert api._route_token(h)[0] == 200
    assert seen[-1] == "sealed"
    argv, kw = calls[0]
    assert argv == ["tailscale", "whois", "--json", "100.64.0.2"]
    assert 0 < kw["timeout"] <= 5 and kw["capture_output"] is True
    assert kw["env"] == api.AGE_ENV and not kw.get("shell", False)


def test_mismatch_precedes_row_lookup_and_does_not_charge_host(monkeypatch):
    whois_result(monkeypatch, '{"Node":{"Name":"node-b.tail123.ts.net."}}')
    h, seen = handler(monkeypatch)
    for _ in range(3):
        with pytest.raises(api._Refuse) as exc:
            api._route_token(h)
        assert (exc.value.status, exc.value.code) == (403, "node_mismatch")
    assert seen == []
    whois_result(monkeypatch, '{"Node":{"Name":"node-a.tail123.ts.net."}}')
    assert api._route_token(h)[0] == 200


@pytest.mark.parametrize("failure", [FileNotFoundError("private"), PermissionError("private"),
                                     subprocess.TimeoutExpired("tailscale", 3)])
def test_whois_unavailable_and_timeout_fail_closed(monkeypatch, failure, caplog):
    def run(*args, **kw):
        raise failure
    monkeypatch.setattr(api.subprocess, "run", run)
    h, seen = handler(monkeypatch)
    with pytest.raises(api._Refuse) as exc:
        api._route_token(h)
    assert (exc.value.status, exc.value.code) == (403, "whois_unavailable")
    assert seen == [] and "private" not in caplog.text


@pytest.mark.parametrize("body,rc", [
    (b"garbage", 0), (b"{}", 0), (b"[]", 0), (b"null", 0),
    (b'{"Node":null}', 0), (b'{"Node":{"Name":123}}', 0),
    (b'{"Node":{"Name":""}}', 0),
    (b'{"Node":{"Name":"node-a.."}}', 0),
    (b'{"Node":{"Name":"node-a.bad name"}}', 0), (b"\xff", 0),
    (b'{"Node":{"Name":"node-a"}}', 1),
])
def test_bad_whois_output_fails_closed(monkeypatch, body, rc):
    whois_result(monkeypatch, body, rc)
    h, seen = handler(monkeypatch)
    with pytest.raises(api._Refuse) as exc:
        api._route_token(h)
    assert (exc.value.status, exc.value.code) == (403, "whois_unavailable")
    assert seen == []


def test_drill_bridge_allowed_only_with_existing_flag(monkeypatch):
    whois_result(monkeypatch, b"no tailnet peer", 1)
    h, seen = handler(monkeypatch, "drill-20261010-120000", "172.17.0.2")
    with pytest.raises(api._Refuse) as exc:
        api._route_token(h)
    assert exc.value.code == "whois_unavailable" and seen == []
    monkeypatch.setenv("DRILL_HUB_ENV", "1")
    assert api._route_token(h)[0] == 200


@pytest.mark.parametrize("host,source", [("node-a", "172.17.0.2"),
    ("drill-other", "172.17.0.2"), ("drill-20261010-120000", "172.18.0.2"),
    ("drill-20261010-120000", "100.64.0.2"), ("drill-20261010-120000", "127.0.0.1")])
def test_drill_flag_does_not_allow_other_hosts_or_sources(monkeypatch, host, source):
    monkeypatch.setenv("DRILL_HUB_ENV", "1")
    whois_result(monkeypatch, b"unavailable", 1)
    h, seen = handler(monkeypatch, host, source)
    with pytest.raises(api._Refuse) as exc:
        api._route_token(h)
    assert exc.value.code == "whois_unavailable" and seen == []


@pytest.mark.parametrize("code,exit_code", [("node_mismatch", 6), ("whois_unavailable", 7)])
def test_client_maps_new_refusals_without_retry(code, exit_code):
    calls = []

    def open_request(*args, **kw):
        calls.append(1)
        raise urllib.error.HTTPError("http://unused", 403, "refused", {},
                                     io.BytesIO(json.dumps({"error": code}).encode()))

    with pytest.raises(node_token.TokenError) as exc:
        node_token.fetch_ciphertext("http://100.64.0.1:792/v1/token", "node-a",
                                    node_token.DEFAULT_NAME, "0" * 32,
                                    opener=SimpleNamespace(open=open_request))
    assert exc.value.code == exit_code and calls == [1]


@pytest.mark.parametrize("body,expected", [
    (b'{"Node":{"Name":"node-a.tail123.ts.net."}}', 200),
    (b'{"Node":{"Name":"node-b.tail123.ts.net."}}', 403),
    (b'garbage', 403),
])
def test_http_identity_response(monkeypatch, body, expected):
    whois_result(monkeypatch, body)
    h, seen = handler(monkeypatch)
    request = api._Handler.__new__(api._Handler)
    request.path, request.client_address, request.server = h.path, h.client_address, h.server
    request.command = "GET"
    request.server.source_limiter = api.RateLimiter(30, 60)
    replies = []
    request._send = lambda *args: replies.append(args)
    request._handle()
    status, answer, content_type, _ = replies[0]
    assert status == expected and content_type == "application/json"
    if expected == 403:
        assert json.loads(answer)["error"] in ("node_mismatch", "whois_unavailable")
        assert seen == []
    else:
        assert "sealed" in seen


def test_drill_exception_still_refuses_left_rows(monkeypatch):
    monkeypatch.setenv("DRILL_HUB_ENV", "1")
    whois_result(monkeypatch, b'unavailable', 1)
    h, seen = handler(monkeypatch, "drill-20261010-120000", "172.17.0.2",
                      row={"status": "left", "approved_at": "yes", "pubkey": "fake"})
    status, body, _, _ = api._route_token(h)
    assert status == 403 and json.loads(body) == {"error": "left"}
    assert "sealed" not in seen


@pytest.mark.parametrize("flag", ["0", "true"])
def test_bridge_requires_exact_flag_even_if_whois_would_match(monkeypatch, flag):
    monkeypatch.setenv("DRILL_HUB_ENV", flag)
    calls = whois_result(monkeypatch, b'{"Node":{"Name":"drill-20261010-120000"}}')
    h, seen = handler(monkeypatch, "drill-20261010-120000", "172.17.0.2")
    with pytest.raises(api._Refuse) as exc:
        api._route_token(h)
    assert (exc.value.status, exc.value.code) == (403, "whois_unavailable")
    assert seen == [] and calls == []

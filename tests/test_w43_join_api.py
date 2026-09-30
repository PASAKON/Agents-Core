"""Org Mesh W4.3: tools/join_api.py -- the hub's public join endpoint.

A real ThreadingHTTPServer on an ephemeral 127.0.0.1 port, driven with http.client, against a
throwaway ledger: SQLite in tmp_path by default, and also the Postgres named by ORG_TEST_DB_URL
when it is set (same convention as tests/test_w41_hq_join.py; the pg param skips otherwise).
Nothing here calls Infisical, Tailscale, GitHub or ssh: the sealed-ready state is written with
plain SQL and the Tailscale minter is a lambda.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w43_join_api.py
"""
from __future__ import annotations

import http.client
import json
import logging
import os
import socket
import threading
from datetime import datetime, timedelta, timezone

import pytest

from lib import db
from lib import db_pg
from tools import hq_join, join_api

# The example recipient from the age README: a real bech32 checksum.
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "A" * 43 + " org-node:node-a"
CIPHER = "-----BEGIN AGE ENCRYPTED FILE-----\nc3ludGhldGljLWNpcGhlcnRleHQ=\n-----END AGE ENCRYPTED FILE-----\n"
TS_KEY = "tskey-auth-kSyntheticKey123-abcdefghijklmnop"
REFUSED = (403, b'{"error":"refused"}')
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
_PG_TABLES = ("locks", "events", "tasks", "c_level_sessions", "hosts", "letters", "join_tokens",
              "node_secrets")


def _drop_pg(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _PG_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(params=["sqlite", "pg"], autouse=True)
def hub(request, monkeypatch, tmp_path):
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    if request.param == "pg":
        if not ORG_TEST_DB_URL:
            pytest.skip("ORG_TEST_DB_URL not set -- pg param runs only against a throwaway org_test")
        monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
        _drop_pg(ORG_TEST_DB_URL)
        db.init()
        yield request.param
        _drop_pg(ORG_TEST_DB_URL)
    else:
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
        db.init()
        yield request.param


class Api:
    """One running server and a tiny client for it."""

    def __init__(self, **kw):
        self.server = join_api.make_server(0, **kw)
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            r = conn.getresponse()
            return r.status, r.read(), {k.lower(): v for k, v in r.getheaders()}
        finally:
            conn.close()

    def post(self, route, obj, headers=None):
        data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        status, body, _ = self.request("POST", join_api.PREFIX + route, data, h)
        return status, body

    def raw(self, data: bytes) -> int:
        """Send bytes as they are; return the status of the first response line."""
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as s:
            s.sendall(data)
            try:
                s.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            buf = b""
            while b"\r\n" not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
        return int(buf.split(b" ", 2)[1])


@pytest.fixture
def start(caplog):
    """start(**server kwargs) -> Api. Logging is captured at DEBUG for the whole test."""
    caplog.set_level(logging.DEBUG)
    made = []

    def _start(**kw):
        api = Api(**kw)
        made.append(api)
        return api

    yield _start
    for api in made:
        api.close()


@pytest.fixture
def api(start):
    return start()


def _accept_body(token, host="node-a", **over):
    body = {"token": token, "host": host, "os": "linux", "hq_root": "/opt/MoonieXHQ",
            "pubkey": PUB, "deploy_pubkey": DEPLOY}
    body.update(over)
    return body


def _join(api, host="node-a"):
    """mint + accept through the endpoint; returns the token."""
    token = hq_join.mint(host)["token"]
    status, _ = api.post("accept", _accept_body(token, host))
    assert status == 200
    return token


def _ready(host="node-a", ciphertext=CIPHER):
    """What W4.2 provision leaves behind, written directly: a sealed secret and identity_ready."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.get_conn() as conn:
        conn.execute("INSERT INTO node_secrets (host, ciphertext, infisical_client_secret_id, created_at) "
                     "VALUES (?, ?, ?, ?)", (host, ciphertext, "secret-id-1", now))
        conn.execute("UPDATE hosts SET status = ? WHERE host = ?", (hq_join.STATUS_READY, host))


def _set_used_at(token, when: datetime):
    with db.get_conn() as conn:
        conn.execute("UPDATE join_tokens SET used_at = ? WHERE token_hash = ?",
                     (when.astimezone(timezone.utc).isoformat(timespec="seconds"),
                      hq_join.hash_token(token)))


# ---------------------------------------------------------------- scripts

def test_join_sh_and_ps1_are_served_as_text_with_the_hub_filled_in(api):
    for name in ("join.sh", "join.ps1"):
        status, body, headers = api.request("GET", f"/org-join/{name}", headers={"Host": f"127.0.0.1:{api.port}"})
        assert status == 200
        assert headers["content-type"].startswith("text/plain")
        text = body.decode("ascii")
        assert "@@ORG_JOIN_HUB@@" not in text
        assert f"http://127.0.0.1:{api.port}/org-join" in text
        assert headers["cache-control"] == "no-store"


def test_a_configured_public_url_wins_over_the_host_header(start):
    api = start(public_url="https://hub.example.test")
    _, body, _ = api.request("GET", "/org-join/join.sh", headers={"Host": "evil.example"})
    text = body.decode("ascii")
    assert 'HUB_DEFAULT="https://hub.example.test/org-join"' in text
    assert "evil.example" not in text


def test_a_hostile_host_header_leaves_no_hub_so_the_script_asks_for_one(api):
    conn = http.client.HTTPConnection("127.0.0.1", api.port, timeout=10)
    try:
        conn.putrequest("GET", "/org-join/join.sh", skip_host=True)
        conn.putheader("Host", 'x"; echo PWNED_BY_HOST_HEADER; echo "')
        conn.endheaders()
        r = conn.getresponse()
        text = r.read().decode("ascii")
    finally:
        conn.close()
    assert r.status == 200
    assert 'HUB_DEFAULT=""' in text
    assert "PWNED_BY_HOST_HEADER" not in text


def test_the_served_script_is_the_file_and_nothing_else(api):
    _, body, _ = api.request("GET", "/org-join/join.sh", headers={"Host": "h.example:1"})
    src = (join_api.SCRIPTS_DIR / "join.sh").read_bytes().replace(
        join_api.HUB_PLACEHOLDER, b"http://h.example:1/org-join")
    assert body == src


# ---------------------------------------------------------------- accept

def test_accept_registers_the_host_and_returns_only_host_and_status(api):
    token = hq_join.mint("node-a")["token"]
    status, body = api.post("accept", _accept_body(token))
    assert status == 200
    assert json.loads(body) == {"host": "node-a", "status": "pending_identity"}
    row = db.get_host("node-a")
    assert row["status"] == "pending_identity" and row["pubkey"] == PUB
    assert row["deploy_pubkey"].startswith("ssh-ed25519 AAAA")


def test_accept_without_a_deploy_key_still_joins(api):
    token = hq_join.mint("node-a")["token"]
    body = _accept_body(token)
    del body["deploy_pubkey"]
    assert api.post("accept", body)[0] == 200


def test_the_tailscale_key_comes_back_only_when_a_minter_is_wired(start):
    calls = []

    def minter(host):
        calls.append(host)
        return TS_KEY

    api = start(minter=minter)
    token = hq_join.mint("node-a")["token"]
    status, body = api.post("accept", _accept_body(token))
    assert status == 200
    assert json.loads(body) == {"host": "node-a", "status": "pending_identity", "tailscale_authkey": TS_KEY}
    assert calls == ["node-a"]


def test_a_minter_that_fails_or_returns_junk_gives_a_join_without_a_key(start, caplog):
    def boom(host):
        raise RuntimeError("secret-detail-from-tailscale")

    api = start(minter=boom)
    token = hq_join.mint("node-a")["token"]
    status, body = api.post("accept", _accept_body(token))
    assert status == 200 and "tailscale_authkey" not in json.loads(body)
    assert "RuntimeError" in caplog.text
    assert "secret-detail-from-tailscale" not in caplog.text

    api2 = start(minter=lambda host: "has a space and \n newline")
    token2 = hq_join.mint("node-b")["token"]
    status, body = api2.post("accept", _accept_body(token2, "node-b"))
    assert status == 200 and "tailscale_authkey" not in json.loads(body)


def test_every_token_refusal_is_the_same_403(api):
    good_a = hq_join.mint("node-a")["token"]
    other = hq_join.mint("node-b")["token"]
    unknown = "hqj_" + "A" * 43
    expired = hq_join.mint("node-c")["token"]
    with db.get_conn() as conn:
        conn.execute("UPDATE join_tokens SET expires_at = ? WHERE token_hash = ?",
                     ("2000-01-01T00:00:00+00:00", hq_join.hash_token(expired)))
    used = _join(api, "node-d")

    answers = {
        "unknown": api.post("accept", _accept_body(unknown)),
        "wrong shape": api.post("accept", _accept_body("hqj_short")),
        "other host's token": api.post("accept", _accept_body(other, "node-a")),
        "expired": api.post("accept", _accept_body(expired, "node-c")),
        "already used": api.post("accept", _accept_body(used, "node-d")),
    }
    assert set(answers.values()) == {REFUSED}, answers
    # a refused call consumed nothing: the good tokens still work
    assert api.post("accept", _accept_body(good_a))[0] == 200
    assert api.post("accept", _accept_body(other, "node-b"))[0] == 200


def test_a_bad_argument_is_a_400_and_does_not_cost_the_token(api):
    token = hq_join.mint("node-a")["token"]
    status, body = api.post("accept", _accept_body(token, pubkey="age1notakey"))
    assert status == 400
    msg = json.loads(body)
    assert msg["error"] == "bad_arg" and token not in body.decode()
    assert api.post("accept", _accept_body(token, os="plan9"))[0] == 400
    assert api.post("accept", _accept_body(token, hq_root="relative/path"))[0] == 400
    assert api.post("accept", _accept_body(token, deploy_pubkey="ssh-rsa AAAA"))[0] == 400
    assert api.post("accept", _accept_body(token))[0] == 200   # still usable


def test_missing_or_mistyped_fields_are_a_400(api):
    token = hq_join.mint("node-a")["token"]
    for field in ("token", "host", "os", "hq_root", "pubkey"):
        body = _accept_body(token)
        del body[field]
        assert api.post("accept", body)[0] == 400, field
    assert api.post("accept", _accept_body(token, host=["node-a"]))[0] == 400
    mistyped = _accept_body(token)
    mistyped["token"] = 12345
    assert api.post("accept", mistyped)[0] == 400


def test_a_name_taken_between_mint_and_accept_is_a_409_and_the_token_survives(api):
    first = hq_join.mint("node-a")["token"]
    second = hq_join.mint("node-a")["token"]     # mint only checks the name is free at that moment
    assert api.post("accept", _accept_body(first))[0] == 200
    status, body = api.post("accept", _accept_body(second))
    assert (status, json.loads(body)) == (409, {"error": "host_in_use"})
    with db.get_conn() as conn:   # the refusal rolled the consume back
        row = conn.execute("SELECT used_at FROM join_tokens WHERE token_hash = ?",
                           (hq_join.hash_token(second),)).fetchone()
    assert row["used_at"] is None


# ---------------------------------------------------------------- sealed

def _sealed(api, host, token):
    return api.post("sealed", {"host": host, "token": token})


def test_sealed_is_pending_until_the_host_is_provisioned_then_ready(api):
    token = _join(api)
    status, body = _sealed(api, "node-a", token)
    assert (status, json.loads(body)) == (202, {"status": "pending"})
    _ready()
    status, body = _sealed(api, "node-a", token)
    assert status == 200
    assert json.loads(body) == {"status": "ready", "ciphertext": CIPHER}
    # polling again is fine, and it is the same answer
    assert _sealed(api, "node-a", token) == (status, body)


def test_every_sealed_refusal_is_the_same_403(api):
    token = _join(api, "node-a")
    _ready("node-a")
    other = _join(api, "node-b")          # a real token, a real host, but not node-a's
    _ready("node-b")
    minted_only = hq_join.mint("node-c")["token"]   # never accepted: used_at is NULL
    late = _join(api, "node-d")
    _ready("node-d")
    _set_used_at(late, datetime.now(timezone.utc) - timedelta(hours=24, seconds=5))
    left = _join(api, "node-e")
    _ready("node-e")
    with db.get_conn() as conn:
        conn.execute("UPDATE hosts SET status = ? WHERE host = ?", (hq_join.STATUS_LEFT, "node-e"))
    revoked = _join(api, "node-f")
    _ready("node-f")
    with db.get_conn() as conn:
        conn.execute("UPDATE node_secrets SET revoked_at = ? WHERE host = ?",
                     ("2026-01-01T00:00:00+00:00", "node-f"))

    assert _sealed(api, "node-a", token)[0] == 200  # the control: the good call works
    answers = {
        "wrong token": _sealed(api, "node-a", "hqj_" + "B" * 43),
        "other host's token": _sealed(api, "node-a", other),
        "unconsumed token": _sealed(api, "node-c", minted_only),
        "older than 24 h": _sealed(api, "node-d", late),
        "host left": _sealed(api, "node-e", left),
        "secret revoked": _sealed(api, "node-f", revoked),
        "unknown host": _sealed(api, "node-zz", token),
        "bad token shape": _sealed(api, "node-a", "nope"),
        "bad host shape": _sealed(api, "NODE_A!", token),
        "token not a string": api.post("sealed", {"host": "node-a", "token": 7}),
        "no fields": api.post("sealed", {}),
    }
    assert set(answers.values()) == {REFUSED}, answers


def test_the_24_hour_window_is_exact(api):
    token = _join(api)
    _ready()
    _set_used_at(token, datetime.now(timezone.utc) - timedelta(hours=23, minutes=59))
    assert _sealed(api, "node-a", token)[0] == 200
    _set_used_at(token, datetime.now(timezone.utc) - timedelta(hours=24, minutes=1))
    assert _sealed(api, "node-a", token) == REFUSED


# ---------------------------------------------------------------- request hygiene

def test_a_body_over_8kb_is_a_413_and_the_server_carries_on(api):
    big = json.dumps({"token": "x" * (join_api.MAX_BODY + 1)}).encode()
    status, body = api.post("accept", big)
    assert status == 413 and json.loads(body) == {"error": "too_large"}
    assert api.post("sealed", {"host": "node-a", "token": "hqj_" + "A" * 43}) == REFUSED


def test_a_body_of_exactly_the_cap_is_read_not_refused_as_large(api):
    pad = join_api.MAX_BODY - len(json.dumps({"token": ""}))
    body = json.dumps({"token": "x" * pad}).encode()
    assert len(body) == join_api.MAX_BODY
    assert api.post("accept", body)[0] == 400   # read, then refused for what it lacks


def test_only_json_with_a_length_is_accepted(api):
    assert api.request("POST", "/org-join/accept", b"a=b", {"Content-Type": "application/x-www-form-urlencoded"})[0] == 415
    assert api.request("POST", "/org-join/accept", b"{}", {})[0] == 415
    assert api.post("accept", b"not json")[0] == 400
    assert api.post("accept", b"[1, 2]")[0] == 400
    assert api.post("accept", b"\xff\xfe")[0] == 400
    assert api.raw(b"POST /org-join/accept HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n\r\n") == 411
    assert api.raw(b"POST /org-join/accept HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                   b"Transfer-Encoding: chunked\r\n\r\n0\r\n\r\n") == 411
    assert api.raw(b"POST /org-join/accept HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                   b"Content-Length: -5\r\n\r\n") == 400


def test_a_short_body_is_a_400_not_a_hang(api):
    status = api.raw(b"POST /org-join/accept HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
                     b"Content-Length: 50\r\n\r\n{\"a\":1}")  # 7 of 50 bytes, then the write side closes
    assert status in (400, 408)


def test_unknown_paths_methods_and_directories_are_404(api):
    for method, path in [("GET", "/"), ("GET", "/org-join"), ("GET", "/org-join/"),
                         ("GET", "/org-join/join.sh/"), ("GET", "/org-join/join.py"),
                         ("GET", "/org-join/../etc/passwd"), ("GET", "/org-join/%2e%2e/etc/passwd"),
                         ("GET", "/org-join/accept"), ("GET", "/org-join/sealed"),
                         ("POST", "/org-join/join.sh"), ("POST", "/org-join/other"),
                         ("PUT", "/org-join/accept"), ("DELETE", "/org-join/join.sh"),
                         ("PATCH", "/org-join/sealed"), ("HEAD", "/org-join/join.sh"),
                         ("GET", "/deploy/join/join.sh"), ("GET", "/tools/join_api.py"), ("GET", "/.env")]:
        status, body, _ = api.request(method, path)
        assert status == 404, (method, path, status)
        if method != "HEAD":
            assert json.loads(body) == {"error": "not_found"}


def test_no_cors_headers_and_no_server_banner(api):
    for method, path, body, hdrs in [("GET", "/org-join/join.sh", None, {"Origin": "https://evil.example"}),
                                     ("OPTIONS", "/org-join/accept", None, {"Origin": "https://evil.example"}),
                                     ("POST", "/org-join/sealed", b"{}", {"Origin": "https://evil.example",
                                                                        "Content-Type": "application/json"})]:
        status, _, headers = api.request(method, path, body, hdrs)
        assert not [h for h in headers if h.startswith("access-control-")], (method, headers)
        assert headers["server"] == "org-join"
        assert headers["x-content-type-options"] == "nosniff"


def test_a_malformed_request_line_gets_a_json_400(api):
    assert api.raw(b"GARBAGE\r\n\r\n") == 400


# ---------------------------------------------------------------- rate limit

def test_the_rate_limit_answers_429_after_the_quota(start):
    api = start(limiter=join_api.RateLimiter(limit=3, window_s=60))
    statuses = [api.request("GET", "/nothing")[0] for _ in range(5)]
    assert statuses == [404, 404, 404, 429, 429]
    status, body, headers = api.request("GET", "/org-join/join.sh")
    assert status == 429 and headers["retry-after"] == "60"
    assert json.loads(body) == {"error": "rate_limited"}


def test_the_rate_limit_counts_every_route_together(start):
    api = start(limiter=join_api.RateLimiter(limit=2, window_s=60))
    assert api.request("GET", "/org-join/join.sh")[0] == 200
    assert api.post("sealed", {})[0] == 403
    assert api.post("accept", {})[0] == 429


def test_behind_the_proxy_each_caller_has_its_own_bucket(start):
    api = start(limiter=join_api.RateLimiter(limit=1, window_s=60), trust_forwarded=True)
    a = {"X-Forwarded-For": "203.0.113.7"}
    b = {"X-Forwarded-For": "198.51.100.9"}
    assert api.request("GET", "/x", headers=a)[0] == 404
    assert api.request("GET", "/x", headers=a)[0] == 429
    assert api.request("GET", "/x", headers=b)[0] == 404
    # a caller cannot pick its own bucket by prepending: only the proxy's last entry counts
    spoof = {"X-Forwarded-For": "1.2.3.4, 203.0.113.7"}
    assert api.request("GET", "/x", headers=spoof)[0] == 429
    # junk falls back to the peer address, not a fresh bucket per junk value
    j1, j2 = {"X-Forwarded-For": "not-an-ip"}, {"X-Forwarded-For": "also-not"}
    assert api.request("GET", "/x", headers=j1)[0] == 404
    assert api.request("GET", "/x", headers=j2)[0] == 429


def test_without_trust_the_forwarded_header_is_ignored(start):
    api = start(limiter=join_api.RateLimiter(limit=1, window_s=60))
    assert api.request("GET", "/x", headers={"X-Forwarded-For": "203.0.113.7"})[0] == 404
    assert api.request("GET", "/x", headers={"X-Forwarded-For": "198.51.100.9"})[0] == 429


def test_the_limiter_forgets_after_the_window():
    now = [0.0]
    lim = join_api.RateLimiter(limit=2, window_s=10, clock=lambda: now[0])
    assert [lim.allow("k") for _ in range(3)] == [True, True, False]
    now[0] = 10.0
    assert lim.allow("k") is True


def test_the_limiter_table_does_not_grow_without_bound():
    now = [0.0]
    lim = join_api.RateLimiter(limit=5, window_s=10, clock=lambda: now[0])
    for i in range(5000):
        lim.allow(f"ip{i}")
    now[0] = 100.0
    lim.allow("fresh")
    assert len(lim._hits) < 100


# ---------------------------------------------------------------- logs

def test_logs_name_method_path_status_and_host_and_nothing_secret(start, caplog):
    api = start(minter=lambda host: TS_KEY)
    token = hq_join.mint("node-a")["token"]
    stray = hq_join.mint("node-b")["token"]
    assert api.post("accept", _accept_body(token))[0] == 200
    assert api.post("accept", _accept_body("hqj_" + "Z" * 43))[0] == 403
    assert api.post("accept", _accept_body(stray, "node-a"))[0] == 403
    assert _sealed(api, "node-a", token)[0] == 202
    _ready()
    assert _sealed(api, "node-a", token)[0] == 200
    assert _sealed(api, "node-a", stray) == REFUSED
    api.request("GET", f"/org-join/{token}")           # a token in a URL path
    api.request("GET", "/org-join/join.sh")

    text = caplog.text
    for secret in (token, stray, CIPHER, CIPHER.splitlines()[1], TS_KEY, PUB, DEPLOY.split()[1],
                   "hqj_" + "Z" * 43):
        assert secret not in text, secret[:12]
    lines = [r.getMessage() for r in caplog.records if r.name == "join_api"]
    assert "POST /org-join/accept 200 host=node-a" in lines
    assert "POST /org-join/accept 403 host=node-a" in lines
    assert "POST /org-join/sealed 202 host=node-a" in lines
    assert "POST /org-join/sealed 200 host=node-a" in lines
    assert "GET /org-join/join.sh 200 host=-" in lines
    assert "GET - 404 host=-" in lines   # the unknown path is not echoed


def test_a_hostile_host_value_is_not_logged(start, caplog):
    api = start()
    token = hq_join.mint("node-a")["token"]
    api.post("accept", _accept_body(token, host="evil\nINFO forged line"))
    assert "forged line" not in caplog.text


def test_an_internal_error_is_a_500_with_a_class_name_only(start, caplog, monkeypatch):
    api = start()
    token = hq_join.mint("node-a")["token"]

    def explode(*a, **kw):
        raise ValueError("row values: " + token)

    monkeypatch.setattr(hq_join, "accept", explode)
    status, body = api.post("accept", _accept_body(token))
    assert status == 500 and json.loads(body) == {"error": "internal"}
    assert token not in caplog.text and token not in body.decode()
    assert "ValueError" in caplog.text


# ---------------------------------------------------------------- start-up

def test_the_server_binds_loopback_only(api):
    assert api.server.server_address[0] == "127.0.0.1"


def test_a_public_url_must_be_an_origin_with_no_path():
    for bad in ("https://hub.example/org-join", "ftp://hub", "https://hub example", "hub.example"):
        with pytest.raises(ValueError):
            join_api.JoinServer(0, public_url=bad)


def test_a_database_that_is_not_ready_stops_the_start_with_a_class_name_only(monkeypatch, capsys):
    def not_ready():
        raise RuntimeError("row values: org secrets")

    monkeypatch.setattr(join_api, "_preflight", not_ready)
    assert join_api.main(["--port", "0"]) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "org secrets" not in err

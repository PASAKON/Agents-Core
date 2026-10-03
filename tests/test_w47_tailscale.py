"""Org Mesh W4, CEO gate G3 part 2: lib/tailscale_api.py, and its two uses.

  * tools/join_api.py hands each approved node a one-use tag:org-node pre-auth key, with the
    `ready` answer of /sealed (never at accept: the key is released after the CEO's approval);
  * `hq_join leave --live` removes that node's device from the tailnet.

Every test talks to FakeTailscale, a real HTTP server on an ephemeral 127.0.0.1 port. Nothing here
reaches the live Tailscale API, Infisical, GitHub or any node. The credentials are synthetic and
the tests look for them in everything a caller could see: exception text, log records, stdout and
stderr, the join answer.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w47_tailscale.py
"""
from __future__ import annotations

import http.client
import json
import logging
import socket
import threading
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from lib import db, tailscale_api
from lib.tailscale_api import TailscaleClient, TailscaleError
from tools import hq_join, join_api

CLIENT_ID = "ts-client-id-SYNTHETIC"
CLIENT_SECRET = "ts-client-secret-SYNTHETIC-0123456789"
MINT_KEY = "tskey-auth-kSyntheticMint1CNTRL-abcdefghijklmnopqrstuvwxyz"
PUB = "age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p"
DEPLOY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA" + "A" * 43 + " org-node:node-a"
CIPHER = "-----BEGIN AGE ENCRYPTED FILE-----\nc3ludGhldGljLWNpcGhlcnRleHQ=\n-----END AGE ENCRYPTED FILE-----\n"
TAG = "tag:org-node"

MINT_BODY = {"capabilities": {"devices": {"create": {"reusable": False, "ephemeral": False,
                                                     "preauthorized": True, "tags": [TAG]}}},
             "expirySeconds": 3600, "description": "org-node:node-a"}


# ---------------------------------------------------------------- the fake control plane

class FakeTailscale:
    """oauth token, create key, list devices, delete device: just enough of api.tailscale.com.

    `requests` records every call. `canned[(method, path)] = (status, payload, headers)` forces an
    answer; a payload may be a callable taking this fake, so an error can echo a live token."""

    def __init__(self):
        self.requests: list[dict] = []
        self.devices: list[dict] = []
        self.expires_in = 3600
        self.tokens: list[str] = []
        self.valid: set[str] = set()
        self.canned: dict = {}
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                pass

            def _send(self, status, payload=None, headers=None):
                data = json.dumps(payload if payload is not None else {}).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            def _handle(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(n) if n else b""
                method, path = self.command, self.path
                outer.requests.append({"method": method, "path": path, "body": body,
                                       "headers": {k.lower(): v for k, v in self.headers.items()}})
                forced = outer.canned.get((method, path))
                if forced is not None:
                    status, payload, headers = (tuple(forced) + (None,))[:3]
                    return self._send(status, payload(outer) if callable(payload) else payload, headers)
                if (method, path) == ("POST", "/api/v2/oauth/token"):
                    form = urllib.parse.parse_qs(body.decode())
                    if (form.get("client_id") != [CLIENT_ID] or form.get("client_secret") != [CLIENT_SECRET]
                            or form.get("grant_type") != ["client_credentials"]):
                        return self._send(401, {"error": "invalid_client", "message": "invalid client"})
                    token = f"tskey-api-kSynth{len(outer.tokens) + 1}CNTRL-" + "x" * 20
                    outer.tokens.append(token)
                    outer.valid.add(token)
                    return self._send(200, {"access_token": token, "token_type": "Bearer",
                                            "expires_in": outer.expires_in})
                auth = self.headers.get("Authorization", "")
                if not auth.startswith("Bearer ") or auth[7:] not in outer.valid:
                    return self._send(401, {"message": "invalid token"})
                if (method, path) == ("POST", "/api/v2/tailnet/-/keys"):
                    return self._send(200, {"id": "kSyn", "key": MINT_KEY, "description": "x"})
                if (method, path) == ("GET", "/api/v2/tailnet/-/devices"):
                    return self._send(200, {"devices": outer.devices})
                if method == "DELETE" and path.startswith("/api/v2/device/"):
                    dev_id = path.rsplit("/", 1)[1]
                    for d in outer.devices:
                        if d["id"] == dev_id:
                            outer.devices.remove(d)
                            return self._send(200, {})
                    return self._send(404, {"message": "device not found"})
                return self._send(404, {"message": "no such route"})

            do_GET = do_POST = do_DELETE = _handle

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._thread = threading.Thread(target=self.server.serve_forever,
                                        kwargs={"poll_interval": 0.02}, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)

    def calls(self, method=None, path=None):
        return [r for r in self.requests
                if (method is None or r["method"] == method) and (path is None or r["path"] == path)]

    def token_requests(self):
        return self.calls("POST", "/api/v2/oauth/token")

    def deletes(self):
        return [r["path"] for r in self.calls("DELETE")]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def dev(dev_id, hostname, tags=None):
    d = {"id": dev_id, "hostname": hostname, "name": f"{hostname}.tailnet.ts.net"}
    if tags is not None:
        d["tags"] = tags
    return d


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in (tailscale_api.ID_ENV, tailscale_api.SECRET_ENV, hq_join.W42_FLAG, "ORG_DB_URL",
                "ORG_JOIN_DB_URL", "JOIN_API_BIND", "JOIN_API_PUBLIC_URL", "JOIN_API_TRUST_FORWARDED",
                "JOIN_API_ALLOW_ORG_ROLE", "CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def ts():
    fake = FakeTailscale().start()
    yield fake
    fake.stop()


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def client(ts, clock):
    return TailscaleClient(CLIENT_ID, CLIENT_SECRET, base_url=ts.url, clock=clock)


def secrets_in(text: str, ts: FakeTailscale) -> list[str]:
    """Which credential strings (client secret, any access token handed out, the minted key) are in `text`."""
    return [s for s in (CLIENT_SECRET, MINT_KEY, *ts.tokens) if s in text]


def full_text(exc: BaseException) -> str:
    return str(exc) + repr(exc) + "".join(traceback.format_exception(exc))


# ---------------------------------------------------------------- the access token

def test_token_is_fetched_with_the_client_credentials_form(client, ts):
    assert client.mint_authkey("node-a") == MINT_KEY
    (req,) = ts.token_requests()
    assert req["headers"]["content-type"] == "application/x-www-form-urlencoded"
    assert urllib.parse.parse_qs(req["body"].decode()) == {
        "client_id": [CLIENT_ID], "client_secret": [CLIENT_SECRET], "grant_type": ["client_credentials"]}
    (mint,) = ts.calls("POST", "/api/v2/tailnet/-/keys")
    assert mint["headers"]["authorization"] == "Bearer " + ts.tokens[0]


def test_token_is_cached_until_sixty_seconds_before_it_expires_then_refreshed(client, ts, clock):
    client.mint_authkey("node-a")
    clock.now += 3600 - 61                                   # one second inside the cache window
    client.mint_authkey("node-a")
    assert len(ts.tokens) == 1
    clock.now += 2                                           # now 59 s from expiry: dropped
    client.mint_authkey("node-a")
    assert len(ts.tokens) == 2
    assert ts.calls("POST", "/api/v2/tailnet/-/keys")[-1]["headers"]["authorization"] == "Bearer " + ts.tokens[1]
    client.mint_authkey("node-a")
    assert len(ts.tokens) == 2                               # and the new one is cached again


def test_a_token_that_is_already_dead_is_replaced_once_on_a_401(client, ts):
    client.mint_authkey("node-a")
    ts.valid.clear()                                         # Tailscale revoked it early
    assert client.mint_authkey("node-a") == MINT_KEY
    assert len(ts.tokens) == 2


def test_two_401s_in_a_row_are_an_error_not_a_loop(client, ts):
    client.access_token()
    ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (401, {"message": "invalid token"})
    with pytest.raises(TailscaleError) as ei:
        client.mint_authkey("node-a")
    assert ei.value.status == 401
    assert len(ts.calls("POST", "/api/v2/tailnet/-/keys")) == 2 and len(ts.tokens) == 2


def test_a_wrong_client_secret_is_refused_with_the_status(ts):
    bad = TailscaleClient(CLIENT_ID, "wrong-secret", base_url=ts.url)
    with pytest.raises(TailscaleError) as ei:
        bad.mint_authkey("node-a")
    assert ei.value.status == 401 and "invalid client" in str(ei.value)
    assert "wrong-secret" not in full_text(ei.value)


def test_an_answer_with_no_access_token_is_an_error(client, ts):
    ts.canned[("POST", "/api/v2/oauth/token")] = (200, {"token_type": "Bearer"})
    with pytest.raises(TailscaleError, match="no access_token"):
        client.access_token()


# ---------------------------------------------------------------- mint_authkey

def test_mint_body_is_exactly_one_use_preauthorized_tagged_and_one_hour(client, ts):
    assert client.mint_authkey("node-a") == MINT_KEY
    (req,) = ts.calls("POST", "/api/v2/tailnet/-/keys")
    assert json.loads(req["body"]) == MINT_BODY
    assert req["headers"]["content-type"] == "application/json"


@pytest.mark.parametrize("host", ["", "a", "ab", "A-node", "node a", "node_a", "../x", "node-a\n",
                                  "-node", "node-", "x" * 40, "node-a;rm", None, 7])
def test_mint_refuses_a_bad_host_before_any_request(client, ts, host):
    with pytest.raises(ValueError) as ei:
        client.mint_authkey(host)
    assert str(ei.value) == "bad host name"                      # the host is never echoed
    assert ts.requests == []


@pytest.mark.parametrize("answer", [{}, {"key": ""}, {"key": "has space"}, {"key": 7}, {"key": "k" * 201},
                                    [], "text"])
def test_mint_refuses_an_answer_without_a_usable_key(client, ts, answer):
    ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (200, answer)
    with pytest.raises(TailscaleError, match="no usable key"):
        client.mint_authkey("node-a")


def test_mint_error_carries_the_status_and_tailscales_message_only(client, ts):
    ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (
        403, {"message": "requires scope auth_keys", "extra": "SHOULD-NOT-APPEAR", "detail": ["x"]})
    with pytest.raises(TailscaleError) as ei:
        client.mint_authkey("node-a")
    assert ei.value.status == 403
    assert str(ei.value) == "tailscale mint key failed: HTTP 403: requires scope auth_keys"


# ---------------------------------------------------------------- delete_device

def test_delete_picks_only_the_tagged_device_with_that_hostname(client, ts):
    ts.devices = [dev("1", "node-a"),                         # untagged: not a node of ours
                  dev("2", "node-a", [TAG]),
                  dev("3", "node-b", [TAG]),                  # another node
                  dev("4", "node-a", ["tag:other"]),          # another tag
                  dev("5", "node-a", [])]
    assert client.delete_device("node-a") is True
    assert ts.deletes() == ["/api/v2/device/2"]
    assert [d["id"] for d in ts.devices] == ["1", "3", "4", "5"]


def test_delete_with_no_tagged_match_touches_nothing_and_is_done(client, ts):
    ts.devices = [dev("1", "node-a"), dev("4", "node-a", ["tag:other"]), dev("3", "node-b", [TAG]),
                  {"id": "9", "hostname": "node-a", "tags": None}]
    assert client.delete_device("node-a") is False
    assert ts.deletes() == []
    ts.devices = []
    assert client.delete_device("node-a") is False


def test_delete_refuses_two_tagged_matches_and_deletes_neither(client, ts):
    ts.devices = [dev("2", "node-a", [TAG]), dev("6", "node-a", [TAG, "tag:x"])]
    with pytest.raises(TailscaleError, match="2 devices named node-a"):
        client.delete_device("node-a")
    assert ts.deletes() == [] and len(ts.devices) == 2


def test_a_404_on_the_delete_means_it_is_already_gone(client, ts):
    ts.devices = [dev("2", "node-a", [TAG])]
    ts.canned[("DELETE", "/api/v2/device/2")] = (404, {"message": "device not found"})
    assert client.delete_device("node-a") is False


def test_another_error_on_the_delete_is_raised_with_its_status(client, ts):
    ts.devices = [dev("2", "node-a", [TAG])]
    ts.canned[("DELETE", "/api/v2/device/2")] = (403, {"message": "requires scope devices:core"})
    with pytest.raises(TailscaleError) as ei:
        client.delete_device("node-a")
    assert ei.value.status == 403 and "requires scope devices:core" in str(ei.value)


def test_a_device_id_that_is_not_a_plain_id_is_never_put_in_a_url(client, ts):
    for bad in ("../../tailnet/-/keys", "2/x", "a b", "", "x" * 65, 12345, None):
        ts.devices = [{"id": bad, "hostname": "node-a", "tags": [TAG]}]
        with pytest.raises(TailscaleError, match="no usable id"):
            client.delete_device("node-a")
    assert ts.deletes() == []


def test_delete_with_a_list_answer_of_the_wrong_shape_is_an_error(client, ts):
    ts.canned[("GET", "/api/v2/tailnet/-/devices")] = (200, {"nodes": []})
    with pytest.raises(TailscaleError, match="no device list"):
        client.delete_device("node-a")


@pytest.mark.parametrize("host", ["", "NODE-A", "node a", "node-a/../x", "mac;"])
def test_delete_refuses_a_bad_host_before_any_request(client, ts, host):
    with pytest.raises(ValueError):
        client.delete_device(host)
    assert ts.requests == []


# ---------------------------------------------------------------- from_env

def test_from_env_with_neither_variable_is_none():
    assert tailscale_api.from_env({}) is None
    assert tailscale_api.from_env({tailscale_api.ID_ENV: "  ", tailscale_api.SECRET_ENV: ""}) is None


def test_from_env_with_both_builds_a_client_and_passes_kwargs_on(ts):
    c = tailscale_api.from_env({tailscale_api.ID_ENV: f" {CLIENT_ID} ", tailscale_api.SECRET_ENV: CLIENT_SECRET},
                               base_url=ts.url)
    assert isinstance(c, TailscaleClient)
    assert c.mint_authkey("node-a") == MINT_KEY                  # the id was stripped, the base url used


@pytest.mark.parametrize("env,missing", [({tailscale_api.ID_ENV: CLIENT_ID}, tailscale_api.SECRET_ENV),
                                         ({tailscale_api.SECRET_ENV: CLIENT_SECRET}, tailscale_api.ID_ENV),
                                         ({tailscale_api.ID_ENV: CLIENT_ID, tailscale_api.SECRET_ENV: " "},
                                          tailscale_api.SECRET_ENV)])
def test_from_env_with_one_variable_without_the_other_is_an_error_naming_them(env, missing):
    with pytest.raises(ValueError) as ei:
        tailscale_api.from_env(env)
    msg = str(ei.value)
    assert missing in msg and tailscale_api.ID_ENV in msg and tailscale_api.SECRET_ENV in msg
    assert CLIENT_ID not in msg and CLIENT_SECRET not in msg


def test_there_is_no_environment_variable_for_the_base_url(monkeypatch):
    monkeypatch.setenv("TAILSCALE_BASE_URL", "https://evil.example")
    monkeypatch.setenv("TS_API_URL", "https://evil.example")
    c = tailscale_api.from_env({tailscale_api.ID_ENV: CLIENT_ID, tailscale_api.SECRET_ENV: CLIENT_SECRET})
    assert c._base == tailscale_api.BASE_URL == "https://api.tailscale.com"


# ---------------------------------------------------------------- secrets stay out of sight

def test_a_hostile_error_body_that_echoes_every_credential_is_redacted(ts, clock, capsys, caplog):
    caplog.set_level(logging.DEBUG)
    client = TailscaleClient(CLIENT_ID, CLIENT_SECRET, base_url=ts.url, clock=clock)
    assert client.mint_authkey("node-a") == MINT_KEY
    echo = lambda fake: {"message": f"boom secret={CLIENT_SECRET} token={fake.tokens[-1]} key={MINT_KEY} "
                                    f"another=tskey-auth-kOTHER-zzzz"}                      # noqa: E731
    ts.canned[("GET", "/api/v2/tailnet/-/devices")] = (500, echo)
    with pytest.raises(TailscaleError) as ei:
        client.delete_device("node-a")
    text = full_text(ei.value) + repr(client) + str(client)
    assert ei.value.status == 500 and "boom" in text and "[redacted]" in text
    assert secrets_in(text, ts) == [] and "tskey-auth-kOTHER" not in text
    # the wire does carry the secret (so this test cannot pass by sending nothing):
    assert CLIENT_SECRET.encode() in ts.token_requests()[0]["body"]
    out = capsys.readouterr()
    assert secrets_in(out.out + out.err + caplog.text, ts) == []


def test_an_error_body_with_control_characters_adds_nothing_unsafe(ts, clock):
    client = TailscaleClient(CLIENT_ID, CLIENT_SECRET, base_url=ts.url, clock=clock)
    client.access_token()
    ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (500, {"message": "line1\nline2\x00\x1b[31m" + "z" * 500})
    with pytest.raises(TailscaleError) as ei:
        client.mint_authkey("node-a")
    msg = str(ei.value)
    assert "\n" not in msg and "\x00" not in msg and "\x1b" not in msg and len(msg) < 260


def test_a_network_failure_names_the_class_and_nothing_of_the_target():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    client = TailscaleClient(CLIENT_ID, CLIENT_SECRET, base_url=f"http://127.0.0.1:{port}", timeout=2)
    with pytest.raises(TailscaleError) as ei:
        client.mint_authkey("node-a")
    assert str(ei.value) == "tailscale token failed: URLError" and ei.value.status is None
    assert str(port) not in full_text(ei.value) and CLIENT_SECRET not in full_text(ei.value)


def test_a_redirect_is_not_followed_so_the_bearer_token_stays_put(ts, clock):
    elsewhere = FakeTailscale().start()
    try:
        client = TailscaleClient(CLIENT_ID, CLIENT_SECRET, base_url=ts.url, clock=clock)
        ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (
            307, {}, {"Location": elsewhere.url + "/api/v2/tailnet/-/keys"})
        with pytest.raises(TailscaleError) as ei:
            client.mint_authkey("node-a")
        assert ei.value.status == 307
        assert elsewhere.requests == []
    finally:
        elsewhere.stop()


# ---------------------------------------------------------------- join_api: the minter on the door

@pytest.fixture
def hub(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
    db.init()


class Door:
    """A running join endpoint (ephemeral port) and a tiny client."""

    def __init__(self, **kw):
        self.tokens = {}
        self.server = join_api.make_server(0, **kw)
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02},
                                        daemon=True)
        self._thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)

    def _post(self, route, obj):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        try:
            conn.request("POST", join_api.PREFIX + route, json.dumps(obj).encode(),
                         {"Content-Type": "application/json"})
            r = conn.getresponse()
            return r.status, r.read()
        finally:
            conn.close()

    def accept(self, host="node-a"):
        """mint + accept; returns (status, body). The token is kept in self.tokens[host]."""
        token = self.tokens[host] = hq_join.mint(host)["token"]
        return self._post("accept", {"token": token, "host": host, "os": "linux",
                                     "hq_root": "/opt/MoonieXHQ", "pubkey": PUB, "deploy_pubkey": DEPLOY})

    def sealed(self, host="node-a"):
        return self._post("sealed", {"host": host, "token": self.tokens[host]})

    @staticmethod
    def approve(host="node-a"):
        """What approve + provision leave behind: a sealed secret and identity_ready."""
        with db.get_conn() as conn:
            conn.execute("INSERT INTO node_secrets (host, ciphertext, infisical_client_secret_id, created_at) "
                         "VALUES (?, ?, ?, ?)", (host, CIPHER, "secret-id-1", "2026-10-01T00:00:00+00:00"))
            conn.execute("UPDATE hosts SET status = ? WHERE host = ?", (hq_join.STATUS_READY, host))


@pytest.fixture
def door(hub, caplog):
    caplog.set_level(logging.DEBUG)
    made = []

    def _door(**kw):
        d = Door(**kw)
        made.append(d)
        return d

    yield _door
    for d in made:
        d.close()


def test_accept_with_the_tailscale_client_wired_returns_no_key_and_never_calls_tailscale(door, ts, client):
    """CTO review F1: the key is released after the CEO's approval (/sealed), never at accept."""
    d = door(minter=client.mint_authkey)
    status, body = d.accept("node-a")
    assert status == 200
    assert json.loads(body) == {"host": "node-a", "status": "pending_identity"}
    assert ts.requests == []                                      # not even the token call
    assert secrets_in(body.decode(), ts) == []


def test_a_pending_host_gets_no_key_and_tailscale_is_not_called(door, ts, client):
    d = door(minter=client.mint_authkey)
    d.accept("node-a")
    for _ in range(2):
        status, body = d.sealed("node-a")
        assert (status, json.loads(body)) == (202, {"status": "pending"})
    assert ts.requests == []


def test_an_approved_host_gets_a_one_use_key_with_the_sealed_answer(door, ts, client, caplog):
    d = door(minter=client.mint_authkey)
    d.accept("node-a")
    d.approve("node-a")
    status, body = d.sealed("node-a")
    assert status == 200
    assert json.loads(body) == {"status": "ready", "ciphertext": CIPHER, "tailscale_authkey": MINT_KEY}
    (mint,) = ts.calls("POST", "/api/v2/tailnet/-/keys")
    assert json.loads(mint["body"]) == MINT_BODY
    assert secrets_in(caplog.text, ts) == []                      # the key is in the answer only


def test_a_refused_sealed_call_does_not_reach_tailscale_even_for_an_approved_host(door, ts, client):
    d = door(minter=client.mint_authkey)
    d.accept("node-a")
    d.approve("node-a")
    status, body = d._post("sealed", {"host": "node-a", "token": "hqj_" + "B" * 43})
    assert (status, json.loads(body)) == (403, {"error": "refused"})
    assert ts.requests == []


def test_sealed_returns_no_key_field_without_a_minter(door, ts):
    d = door()
    d.accept("node-a")
    d.approve("node-a")
    status, body = d.sealed("node-a")
    assert status == 200 and json.loads(body) == {"status": "ready", "ciphertext": CIPHER}
    assert ts.requests == []


def test_a_failing_tailscale_still_releases_the_identity_and_logs_class_and_status_only(door, ts, client, caplog):
    ts.canned[("POST", "/api/v2/tailnet/-/keys")] = (403, {"message": "FORBIDDEN-BY-ACL requires auth_keys"})
    d = door(minter=client.mint_authkey)
    d.accept("node-a")
    d.approve("node-a")
    status, body = d.sealed("node-a")
    assert status == 200 and json.loads(body) == {"status": "ready", "ciphertext": CIPHER}
    assert db.get_host("node-a")["status"] == hq_join.STATUS_READY
    warn = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warn) == 1
    assert warn[0].getMessage() == "tailscale minter failed for node-a: TailscaleError (HTTP 403)"
    assert "FORBIDDEN-BY-ACL" not in caplog.text and secrets_in(caplog.text + body.decode(), ts) == []


# ---------------------------------------------------------------- join_api.main wires it

class _Stub:
    """What main() sees as a server: the minter it was built with, nothing listening."""

    def __init__(self, port, **kw):
        self.kw = kw
        self.minter = kw.get("minter")
        self.server_address = ("127.0.0.1", port)

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        pass


@pytest.fixture
def main_stub(monkeypatch):
    made = []
    monkeypatch.setattr(join_api, "_preflight", lambda: None)
    monkeypatch.setattr(join_api, "make_server", lambda port, **kw: made.append(_Stub(port, **kw)) or made[-1])
    return made


def test_main_wires_the_minter_when_the_env_holds_the_client(main_stub, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.setenv(tailscale_api.ID_ENV, CLIENT_ID)
    monkeypatch.setenv(tailscale_api.SECRET_ENV, CLIENT_SECRET)
    assert join_api.main(["--port", "0"]) == 0
    minter = main_stub[0].kw["minter"]
    assert isinstance(minter.__self__, TailscaleClient) and minter.__func__ is TailscaleClient.mint_authkey
    assert "(minter wired)" in caplog.text
    assert CLIENT_SECRET not in caplog.text and CLIENT_ID not in caplog.text


def test_main_without_the_client_is_as_before_no_minter(main_stub, caplog):
    caplog.set_level(logging.INFO)
    assert join_api.main(["--port", "0"]) == 0
    assert main_stub[0].kw["minter"] is None
    assert "(minter not wired)" in caplog.text


@pytest.mark.parametrize("var,value", [(tailscale_api.ID_ENV, CLIENT_ID), (tailscale_api.SECRET_ENV, CLIENT_SECRET)])
def test_main_refuses_to_start_on_half_a_configuration(main_stub, monkeypatch, capsys, var, value):
    monkeypatch.setenv(var, value)
    with pytest.raises(SystemExit) as ei:
        join_api.main(["--port", "0"])
    assert ei.value.code == 2 and main_stub == []                 # refused before a server was built
    err = capsys.readouterr().err
    assert tailscale_api.ID_ENV in err and tailscale_api.SECRET_ENV in err
    assert CLIENT_ID not in err and CLIENT_SECRET not in err


# ---------------------------------------------------------------- hq_join leave --live

@pytest.fixture
def live(monkeypatch, ts):
    """ORG_W42_PROVISION=1, the OAuth client in the environment, and from_env pointed at the fake.
    The Infisical admin login is replaced by a stand-in nothing is asked of (no secret is recorded)."""
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setenv(tailscale_api.ID_ENV, CLIENT_ID)
    monkeypatch.setenv(tailscale_api.SECRET_ENV, CLIENT_SECRET)
    real = tailscale_api.from_env
    monkeypatch.setattr(tailscale_api, "from_env", lambda environ, **kw: real(environ, base_url=ts.url, **kw))
    monkeypatch.setattr(hq_join, "_live_org", lambda: object())


def _join(host="node-a"):
    token = hq_join.mint(host)["token"]
    hq_join.accept(token, host, "linux", "/opt/MoonieXHQ", PUB)


def _step(res, kind):
    (s,) = [s for s in res["steps"] if s["kind"] == kind]
    return s


def test_leave_live_with_the_flag_and_the_env_removes_the_tagged_device_and_ends_left(hub, ts, live):
    _join()
    ts.devices = [dev("1", "node-a"), dev("2", "node-a", [TAG]), dev("3", "node-b", [TAG])]
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert step["ok"] and step["detail"] == "deleted"
    assert ts.deletes() == ["/api/v2/device/2"] and [d["id"] for d in ts.devices] == ["1", "3"]
    assert res["status"] == "left" and res["left_behind"] == []
    res = hq_join.leave("node-a", live=True)                       # already left: nothing runs again
    assert res["status"] == "left" and ts.deletes() == ["/api/v2/device/2"]


def test_leave_live_converges_when_the_device_is_already_gone(hub, ts, live):
    _join()
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert step["ok"] and step["detail"] == "no tag:org-node device on the tailnet"
    assert ts.deletes() == []


def test_leave_live_reports_a_tailscale_failure_as_a_left_behind_step_without_a_secret(hub, ts, live):
    _join()
    ts.devices = [dev("2", "node-a", [TAG])]
    ts.canned[("DELETE", "/api/v2/device/2")] = (
        403, lambda fake: {"message": f"nope {CLIENT_SECRET} {fake.tokens[-1]}"})
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert not step["ok"] and "TailscaleError" in step["detail"] and "HTTP 403" in step["detail"]
    assert res["status"] == "partial" and res["left_behind"] == ["tailscale_device:node-a"]
    assert secrets_in(json.dumps(res), ts) == []
    with db.get_conn() as conn:
        events = json.dumps([dict(r) for r in conn.execute("SELECT * FROM events").fetchall()], default=str)
    assert secrets_in(events, ts) == []


def test_leave_live_without_the_flag_never_builds_a_client_even_with_the_env(hub, ts, monkeypatch):
    _join()
    monkeypatch.setenv(tailscale_api.ID_ENV, CLIENT_ID)
    monkeypatch.setenv(tailscale_api.SECRET_ENV, CLIENT_SECRET)
    monkeypatch.setattr(tailscale_api, "from_env", lambda *a, **k: pytest.fail("a client was built"))
    assert hq_join.default_revokers() is hq_join.UNWIRED_REVOKERS
    ts.devices = [dev("2", "node-a", [TAG])]
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert not step["ok"] and step["detail"].startswith("not wired yet") and tailscale_api.ID_ENV in step["detail"]
    assert ts.requests == [] and len(ts.devices) == 1


def test_leave_live_with_the_flag_but_no_client_in_the_env_stays_unwired(hub, ts, monkeypatch):
    _join()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setattr(hq_join, "_live_org", lambda: object())
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert not step["ok"] and step["detail"].startswith("not wired yet")
    assert ts.requests == [] and res["status"] == "partial"


@pytest.mark.parametrize("var,value", [(tailscale_api.ID_ENV, CLIENT_ID), (tailscale_api.SECRET_ENV, CLIENT_SECRET)])
def test_leave_live_with_half_a_client_refuses_the_step_and_says_why(hub, ts, monkeypatch, var, value):
    _join()
    monkeypatch.setenv(hq_join.W42_FLAG, "1")
    monkeypatch.setenv(var, value)
    monkeypatch.setattr(hq_join, "_live_org", lambda: object())
    ts.devices = [dev("2", "node-a", [TAG])]
    res = hq_join.leave("node-a", live=True)
    step = _step(res, "tailscale_device")
    assert not step["ok"] and "must be set together" in step["detail"] and value not in step["detail"]
    assert ts.requests == [] and len(ts.devices) == 1


def test_a_plan_without_live_calls_no_revoker_and_no_tailscale(hub, ts, live):
    _join()
    ts.devices = [dev("2", "node-a", [TAG])]
    res = hq_join.leave("node-a")
    assert res["status"] == "planned" and ts.requests == [] and len(ts.devices) == 1


def test_wired_revokers_takes_an_injected_client_without_reading_the_env():
    seen = []

    class Fake:
        def delete_device(self, host):
            seen.append(host)
            return True

    table = hq_join.wired_revokers(org=object(), tailscale=Fake())
    out = table["tailscale_device"](hq_join.Step("tailscale_device", "node-a", "x"))
    assert out == hq_join.Outcome(True, "deleted") and seen == ["node-a"]
    assert table["authorized_keys"] is hq_join.revoke_authorized_keys      # settled by what was placed

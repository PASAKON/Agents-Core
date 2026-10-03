"""Org Mesh W4.2b: tools/node_token_api.py -- the hub's node-token service.

A real ThreadingHTTPServer on an ephemeral 127.0.0.1 port (allow_loopback=True is the test-only
switch; main() never passes it), driven with http.client, against a throwaway ledger: SQLite in
tmp_path by default, and also the Postgres named by ORG_TEST_DB_URL when set (the pg param skips
otherwise). The sealer is a recording fake, except in the round-trip tests, which seal with the
real `age` binary to a freshly generated key. Nothing here calls Infisical, Tailscale, GitHub or
ssh, and no value in this file is a real secret: the token is a synthetic string.

What is pinned (CEO ruling 2026-10-03, R1-R5 in docs/ops/hq-join.md):
  * R2  a token is issued only to a row that is approved AND in an issuing status
  * R4  a leaving or left host is refused, for good, and a failed `leave` still refuses
  * the answer is sealed to hosts.pubkey: another key cannot open it
  * no response body, header, health answer or log record holds the value, its length or a part of it
  * the bind is tailnet-only, the start-up refusals name the variable, never a value

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token_api.py
"""
from __future__ import annotations

import contextlib
import http.client
import json
import logging
import os
import shutil
import socket
import sqlite3
import stat
import subprocess
import threading
from pathlib import Path

import pytest

from lib import db, db_pg
from tools import hq_join, infisical_setup, node_token_api

from test_w43_join_api import PUB, _drop_pg

ROOT = Path(__file__).resolve().parent.parent
UNIT = ROOT / "deploy" / "node-token" / "org-node-token.service"
BIND_SH = ROOT / "deploy" / "node-token" / "bind-tailnet.sh"
NAME = infisical_setup.NODE_SECRET_NAMES[0]
TOKEN = "sk-ant-oat01-SYNTHETIC-nottoken-0123456789abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMN"
DSN = "postgresql://org_node_token:Sy-nth-3tic-pw-0123456789abcdef@127.0.0.1:1/hub"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
APPROVED = "2026-10-03T10:00:00+00:00"
needs_age = pytest.mark.skipif(not (shutil.which("age") and shutil.which("age-keygen")),
                               reason="age and age-keygen needed")


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
        db_pg.evict(ORG_TEST_DB_URL)
        _drop_pg(ORG_TEST_DB_URL)
    else:
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "tasks.db")
        db.init()
        yield request.param


class Sealer:
    """Records every call; returns something that looks like armored age output and holds the
    plaintext as hex, so a test can read what the service decided to hand out."""

    def __init__(self, fail: Exception | None = None):
        self.calls = []
        self.fail = fail

    def __call__(self, recipient, plaintext):
        self.calls.append((recipient, plaintext))
        if self.fail:
            raise self.fail
        return (b"-----BEGIN AGE ENCRYPTED FILE-----\n" + plaintext.hex().encode() +
                b"\n-----END AGE ENCRYPTED FILE-----\n")


class Api:
    def __init__(self, **kw):
        kw.setdefault("tokens", {NAME: TOKEN})
        kw.setdefault("bind", "127.0.0.1")
        self.server = node_token_api.make_server(0, allow_loopback=True, **kw)
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever,
                                        kwargs={"poll_interval": 0.02}, daemon=True)
        self._thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self._thread.join(timeout=5)

    def request(self, method, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request(method, path)
            r = conn.getresponse()
            return r.status, r.read(), {k.lower(): v for k, v in r.getheaders()}
        finally:
            conn.close()

    def get(self, path):
        return self.request("GET", path)

    def token(self, host="node-a", extra=""):
        return self.get(f"/v1/token?host={host}{extra}")


@pytest.fixture
def start(caplog):
    caplog.set_level(logging.DEBUG)
    made = []

    def _start(**kw):
        kw.setdefault("sealer", Sealer())
        api = Api(**kw)
        made.append(api)
        return api

    yield _start
    for api in made:
        api.close()


@pytest.fixture
def api(start):
    return start()


def _row(host="node-a", status=hq_join.STATUS_READY, approved=True, pubkey=PUB):
    db.upsert_host(host, status=status, pubkey=pubkey, approved_at=APPROVED if approved else None)


def _everything_in(*parts) -> bytes:
    out = b""
    for p in parts:
        out += p if isinstance(p, bytes) else json.dumps(p, default=str).encode()
    return out


def _holds_no_value(blob: bytes) -> bool:
    """No part of the token as text or as hex (the fake sealer's armor), and no length field."""
    text = blob.decode("utf-8", "replace")
    pieces = (TOKEN, TOKEN[-4:], TOKEN[:12], TOKEN.encode().hex(), f'"length": {len(TOKEN)}', f'"len":{len(TOKEN)}')
    return not any(p in text for p in pieces)


# ---------------------------------------------------------------- the decision, over HTTP

# (status, approved_at set?, expected refusal code or None for a 200)
MATRIX = [
    (hq_join.STATUS_READY, True, None),
    ("online", True, None),
    (hq_join.STATUS_LEAVING, True, "left"),
    (hq_join.STATUS_LEFT, True, "left"),
    (hq_join.STATUS_LEAVING, False, "left"),
    (hq_join.STATUS_LEFT, False, "left"),
    (hq_join.STATUS_PENDING, False, "not_approved"),
    (hq_join.STATUS_READY, False, "not_approved"),
    ("online", False, "not_approved"),
    (hq_join.STATUS_PENDING, True, "not_issuing"),
    ("offline", True, "not_issuing"),
    (None, True, "not_issuing"),
    ("anything-new", True, "not_issuing"),
]


@pytest.mark.parametrize("status,approved,code", MATRIX)
def test_the_status_matrix(start, status, approved, code):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row(status=status, approved=approved)
    st, body, _ = a.token()
    if code is None:
        assert st == 200 and list(json.loads(body)) == ["ciphertext"]
        assert len(sealer.calls) == 1 and sealer.calls[0][0] == PUB
    else:
        assert (st, json.loads(body)) == (403, {"error": code})
        assert sealer.calls == []                       # refused before anything is sealed
        assert _holds_no_value(body)


def test_an_unknown_host_is_a_403_and_never_sealed(start):
    sealer = Sealer()
    st, body, _ = start(sealer=sealer).token("node-zz")
    assert (st, json.loads(body)) == (403, {"error": "unknown_host"}) and sealer.calls == []


def test_a_row_with_no_pubkey_is_unknown_host(start):
    """mac / contabo / winbox never joined through hq_join: no recipient, so nothing to seal to."""
    sealer = Sealer()
    a = start(sealer=sealer)
    db.upsert_host("contabo", status="online", approved_at=APPROVED)
    st, body, _ = a.token("contabo")
    assert (st, json.loads(body)) == (403, {"error": "unknown_host"}) and sealer.calls == []


def test_a_200_is_sealed_to_the_hosts_own_pubkey_and_says_what_it_is(start):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row("node-b")
    st, body, headers = a.token("node-b")
    assert st == 200 and headers["content-type"] == "application/json"
    assert headers["cache-control"] == "no-store"
    recipient, plaintext = sealer.calls[0]
    assert recipient == PUB
    payload = json.loads(plaintext)
    assert sorted(payload) == ["host", "issued_at", "name", "v", "value"]
    assert (payload["v"], payload["host"], payload["name"], payload["value"]) == (1, "node-b", NAME, TOKEN)
    assert TOKEN.encode() not in body                   # the response carries the ciphertext only


def test_the_secret_can_be_named_but_only_from_the_list_the_hub_hands_out(start):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row()
    assert a.token(extra=f"&name={NAME}")[0] == 200
    assert json.loads(sealer.calls[0][1])["name"] == NAME


def test_the_token_is_not_issued_to_a_host_for_another_hosts_row(start):
    """host= picks the row, and the payload names the same host: node-a cannot ask as node-b."""
    sealer = Sealer()
    a = start(sealer=sealer)
    _row("node-a")
    _row("node-b", status=hq_join.STATUS_LEFT)
    assert a.token("node-b")[0] == 403 and sealer.calls == []
    assert a.token("node-a")[0] == 200
    assert json.loads(sealer.calls[0][1])["host"] == "node-a"


def test_a_host_that_leaves_is_refused_from_then_on(start):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row()
    assert a.token()[0] == 200
    db.upsert_host("node-a", status=hq_join.STATUS_LEFT)
    for _ in range(3):
        st, body, _ = a.token()
        assert (st, json.loads(body)) == (403, {"error": "left"})
    db.upsert_host("node-a", approved_at=APPROVED)       # approving a left row does not bring it back
    assert a.token()[0] == 403 and len(sealer.calls) == 1


def test_a_leave_that_failed_still_refuses(start):
    """R4 through the service: `leave --live` flips the row to `leaving` FIRST, so a revoker that
    fails (Tailscale down, GitHub 502) leaves the host refused, and a re-run can finish it."""
    sealer = Sealer()
    a = start(sealer=sealer)
    db.upsert_host("node-a", status=hq_join.STATUS_READY, pubkey=PUB, approved_at=APPROVED,
                   deploy_pubkey="ssh-ed25519 AAAA org-node:node-a")
    assert a.token()[0] == 200

    def down(step):
        raise RuntimeError("provider down")
    out = hq_join.leave("node-a", live=True, revokers={k: down for k in
                        ("tailscale_device", "github_deploy_key", "authorized_keys")})
    assert out["status"] == "partial" and out["steps"][0]["ok"] is True       # status_leaving ran first
    assert db.get_host("node-a")["status"] == hq_join.STATUS_LEAVING
    st, body, _ = a.token()
    assert (st, json.loads(body)) == (403, {"error": "left"}) and len(sealer.calls) == 1


# ---------------------------------------------------------------- the real thing: age

def _keygen(tmp_path: Path, name: str) -> tuple[Path, str]:
    ident = tmp_path / f"{name}.txt"
    done = subprocess.run(["age-keygen", "-o", str(ident)], capture_output=True, text=True, check=True)
    pub = (done.stderr + done.stdout).split("Public key:")[1].split()[0]
    return ident, pub


@needs_age
def test_the_answer_opens_with_the_nodes_identity_and_with_no_other(tmp_path):
    mine, mine_pub = _keygen(tmp_path, "mine")
    other, _ = _keygen(tmp_path, "other")
    a = Api(tokens={NAME: TOKEN})                                  # no fake: the real lib.sealed.seal
    try:
        _row("node-a", pubkey=mine_pub)
        st, body, _ = a.token()
    finally:
        a.close()
    assert st == 200
    cipher = json.loads(body)["ciphertext"]
    assert "BEGIN AGE ENCRYPTED FILE" in cipher and TOKEN not in cipher
    opened = subprocess.run(["age", "-d", "-i", str(mine)], input=cipher.encode(), capture_output=True)
    assert opened.returncode == 0
    payload = json.loads(opened.stdout)
    assert (payload["v"], payload["host"], payload["name"], payload["value"]) == (1, "node-a", NAME, TOKEN)
    wrong = subprocess.run(["age", "-d", "-i", str(other)], input=cipher.encode(), capture_output=True)
    assert wrong.returncode != 0 and TOKEN.encode() not in wrong.stdout + wrong.stderr


@needs_age
def test_each_host_gets_an_answer_only_its_own_key_opens(tmp_path):
    ka, pa = _keygen(tmp_path, "a")
    kb, pb = _keygen(tmp_path, "b")
    a = Api(tokens={NAME: TOKEN})
    try:
        _row("node-a", pubkey=pa)
        _row("node-b", pubkey=pb)
        ca = json.loads(a.token("node-a")[1])["ciphertext"].encode()
        cb = json.loads(a.token("node-b")[1])["ciphertext"].encode()
    finally:
        a.close()
    assert subprocess.run(["age", "-d", "-i", str(ka)], input=ca, capture_output=True).returncode == 0
    assert subprocess.run(["age", "-d", "-i", str(kb)], input=ca, capture_output=True).returncode != 0
    assert subprocess.run(["age", "-d", "-i", str(kb)], input=cb, capture_output=True).returncode == 0
    assert subprocess.run(["age", "-d", "-i", str(ka)], input=cb, capture_output=True).returncode != 0


# ---------------------------------------------------------------- bad requests

@pytest.mark.parametrize("query,code", [
    ("", "bad_host"),
    ("?host=", "bad_host"),
    ("?host=Node-A", "bad_host"),
    ("?host=node_a", "bad_host"),
    ("?host=a", "bad_host"),
    ("?host=..%2F..%2Fetc", "bad_host"),
    ("?host=" + "a" * 64, "bad_host"),
    ("?host=node-a&host=node-b", "bad_request"),
    ("?host=node-a&x=1", "bad_request"),
    ("?host=node-a&name=OTHER_SECRET", "bad_name"),
    ("?host=node-a&name=", "bad_name"),
])
def test_bad_requests_are_400_and_never_sealed(start, query, code):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row()
    st, body, _ = a.get("/v1/token" + query)
    assert (st, json.loads(body)) == (400, {"error": code}) and sealer.calls == []


@pytest.mark.parametrize("method,path", [
    ("POST", "/v1/token?host=node-a"), ("PUT", "/v1/token?host=node-a"),
    ("DELETE", "/v1/token?host=node-a"), ("HEAD", "/v1/token?host=node-a"),
    ("GET", "/"), ("GET", "/v1/tokens?host=node-a"), ("GET", "/v1/token/?host=node-a"),
    ("GET", "/health/x"), ("POST", "/health"),
])
def test_anything_else_is_a_404_and_never_sealed(start, method, path):
    sealer = Sealer()
    a = start(sealer=sealer)
    _row()
    st, body, _ = a.request(method, path)
    assert st == 404 and sealer.calls == []
    assert method == "HEAD" or json.loads(body) == {"error": "not_found"}


def test_a_garbage_request_line_is_a_400_with_no_detail(start):
    a = start()
    with socket.create_connection(("127.0.0.1", a.port), timeout=10) as s:
        s.sendall(b"\x00\x01 not http at all\r\n\r\n")
        s.shutdown(socket.SHUT_WR)
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    assert data.startswith(b"HTTP/1.0 400") and data.endswith(b'{"error":"bad_request"}')


# ---------------------------------------------------------------- health

def test_health_says_booleans_and_nothing_else(api):
    st, body, _ = api.get("/health")
    assert (st, json.loads(body)) == (200, {"ok": True, "token_loaded": True, "db": True})
    assert _holds_no_value(body)


def test_health_is_503_when_the_database_is_down_and_names_no_error(api, monkeypatch):
    def boom():
        raise RuntimeError("password authentication failed for user org_node_token " + TOKEN)
    monkeypatch.setattr(db, "get_conn", boom)
    st, body, _ = api.get("/health")
    assert (st, json.loads(body)) == (503, {"ok": False, "token_loaded": True, "db": False})
    assert b"password" not in body and _holds_no_value(body)


@pytest.fixture
def hub_down_with_a_snapshot(monkeypatch, tmp_path):
    """The hub does not answer (HubConnectError) and a read-only ledger snapshot exists in which
    node-a is approved and online: what lib.db.get_conn() falls back to. A service that decided from
    it would issue the token to a host that has since left."""
    snap = tmp_path / "tasks.snapshot.db"
    conn = sqlite3.connect(str(snap))
    conn.row_factory = sqlite3.Row
    db.init_schema(conn, is_pg=False)
    db.init_snapshot_meta(conn)
    conn.execute("INSERT INTO hosts (host, status, pubkey, approved_at) VALUES (?, 'online', ?, ?)",
                 ("node-a", PUB, APPROVED))
    db.write_snapshot_meta(conn, "2026-10-03T00:00:00+00:00")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "SNAPSHOT_PATH", snap)
    monkeypatch.setenv("ORG_DB_URL", DSN)

    def down(url, timeout=None):
        raise db_pg.HubConnectError("hub down: " + DSN)
    monkeypatch.setattr(db_pg, "get_pooled", down)
    with db.get_conn() as c:       # the set-up does what it claims: lib.db would answer from the snapshot
        assert isinstance(c, db._SnapshotConnection)
        assert c.execute("SELECT status FROM hosts WHERE host = 'node-a'").fetchone()["status"] == "online"
    return snap


def test_a_down_hub_is_a_503_and_never_an_answer_from_the_snapshot(start, hub_down_with_a_snapshot, caplog):
    sealer = Sealer()
    a = start(sealer=sealer)
    st, body, headers = a.token()
    assert (st, json.loads(body)) == (503, {"error": "hub_unavailable"}) and "retry-after" in headers
    assert sealer.calls == []                                          # nothing was sealed, nothing issued
    assert b"Sy-nth" not in body + _logged(caplog) and _holds_no_value(body + _logged(caplog))


def test_a_down_hub_with_no_snapshot_at_all_is_the_same_503(start, hub_down_with_a_snapshot):
    hub_down_with_a_snapshot.unlink()
    st, body, _ = start().token()
    assert (st, json.loads(body)) == (503, {"error": "hub_unavailable"})


def test_health_says_db_false_when_the_hub_is_down_even_with_a_snapshot(start, hub_down_with_a_snapshot):
    st, body, _ = start().get("/health")
    assert (st, json.loads(body)) == (503, {"ok": False, "token_loaded": True, "db": False})


def test_the_start_up_check_does_not_pass_on_the_snapshot(hub_down_with_a_snapshot):
    with pytest.raises(RuntimeError, match="hub_unavailable"):
        node_token_api._preflight()


def test_a_connection_that_dies_mid_query_is_a_503_too(start, monkeypatch):
    psycopg = pytest.importorskip("psycopg")

    class Dying:
        def execute(self, *a):
            raise psycopg.OperationalError("server closed the connection unexpectedly")

    @contextlib.contextmanager
    def get_conn():
        yield Dying()
    monkeypatch.setattr(db, "get_conn", get_conn)
    st, body, _ = start().token()
    assert (st, json.loads(body)) == (503, {"error": "hub_unavailable"})


def test_health_is_503_when_no_token_is_loaded(start):
    st, body, _ = start(tokens={}).get("/health")
    assert (st, json.loads(body)) == (503, {"ok": False, "token_loaded": False, "db": True})


def test_health_refuses_a_query_string(api):
    assert api.get("/health?x=1")[0] == 400


# ---------------------------------------------------------------- rate limits

class _Clock:
    t = 0.0

    def __call__(self):
        return self.t


def test_a_host_is_limited_and_the_429_says_when_to_retry(start):
    sealer = Sealer()
    clock = _Clock()
    a = start(sealer=sealer, host_limiter=node_token_api.RateLimiter(2, 60.0, clock))
    _row()
    assert [a.token()[0] for _ in range(2)] == [200, 200]
    st, body, headers = a.token()
    assert (st, json.loads(body), headers["retry-after"]) == (429, {"error": "rate_limited"}, "60")
    assert len(sealer.calls) == 2
    clock.t = 61.0
    assert a.token()[0] == 200                                         # the window moved on


def test_one_host_limit_does_not_block_another(start):
    a = start(host_limiter=node_token_api.RateLimiter(1, 60.0, _Clock()))
    _row("node-a")
    _row("node-b")
    assert a.token("node-a")[0] == 200 and a.token("node-a")[0] == 429
    assert a.token("node-b")[0] == 200


def test_a_source_address_is_limited_across_hosts_and_routes(start):
    sealer = Sealer()
    a = start(sealer=sealer, source_limiter=node_token_api.RateLimiter(3, 60.0, _Clock()))
    _row("node-a")
    _row("node-b")
    assert [a.token("node-a")[0], a.get("/health")[0], a.token("node-b")[0]] == [200, 200, 200]
    for path in ("/v1/token?host=node-a", "/health", "/nope"):
        assert a.get(path)[0] == 429
    assert len(sealer.calls) == 2


def test_the_database_gate_answers_503_busy_when_it_stays_full(start, monkeypatch):
    gate = threading.BoundedSemaphore(1)
    gate.acquire()                                                    # every slot taken
    monkeypatch.setattr(node_token_api, "_DB_GATE", gate)
    monkeypatch.setattr(node_token_api, "DB_WAIT_S", 0.05)
    sealer = Sealer()
    a = start(sealer=sealer)
    _row()
    st, body, headers = a.token()
    assert (st, json.loads(body)) == (503, {"error": "busy"}) and "retry-after" in headers
    assert sealer.calls == []


# ---------------------------------------------------------------- what the logs and errors hold

def _logged(caplog) -> bytes:
    return _everything_in(*[(r.getMessage(), r.name, str(r.exc_text), str(r.exc_info)) for r in caplog.records])


def test_the_log_names_the_grant_and_never_the_value(start, caplog):
    a = start()
    _row()
    assert a.token()[0] == 200
    assert a.token("node-zz")[0] == 403
    assert a.get("/health")[0] == 200
    messages = [r.getMessage() for r in caplog.records if r.name == "node_token_api"]
    assert f"issued {NAME} to node-a" in messages
    assert "GET /v1/token 200 host=node-a" in messages
    assert "GET /v1/token 403 host=node-zz" in messages
    assert _holds_no_value(_logged(caplog))
    assert not any("node-zz" in m and "issued" in m for m in messages)    # a refusal is not a grant


def test_a_path_the_service_does_not_serve_is_not_written_to_the_log(start, caplog):
    start().get("/%0a%0dissued%20x%20to%20evil")
    messages = [r.getMessage() for r in caplog.records if r.name == "node_token_api"]
    assert messages == ["GET - 404 host=-"]


def test_a_sealer_that_fails_is_a_500_with_the_class_only(start, caplog):
    sealer = Sealer(fail=RuntimeError("age said no, plaintext was " + TOKEN))
    a = start(sealer=sealer)
    _row()
    st, body, _ = a.token()
    assert (st, json.loads(body)) == (500, {"error": "internal"})
    assert "RuntimeError" in " ".join(r.getMessage() for r in caplog.records)
    assert _holds_no_value(body + _logged(caplog))


def test_a_database_error_is_a_500_and_its_message_is_dropped(start, caplog, monkeypatch):
    def boom():
        raise RuntimeError("could not connect with " + DSN + " " + TOKEN)
    a = start()
    monkeypatch.setattr(db, "get_conn", boom)
    st, body, _ = a.token()
    assert (st, json.loads(body)) == (500, {"error": "internal"})
    assert b"Sy-nth" not in body + _logged(caplog) and _holds_no_value(body + _logged(caplog))


def test_no_header_of_any_answer_holds_the_value(start):
    a = start()
    _row()
    for path in ("/v1/token?host=node-a", "/v1/token?host=node-zz", "/health", "/nope", "/v1/token"):
        _, body, headers = a.get(path)
        assert _holds_no_value(_everything_in(headers))
        if path != "/v1/token?host=node-a":               # the 200 body is the (here hex-armored) answer
            assert _holds_no_value(body)


# ---------------------------------------------------------------- the bind

@pytest.mark.parametrize("addr", ["100.64.0.0", "100.64.0.1", "100.100.100.100", "100.127.255.254"])
def test_a_tailnet_address_is_accepted(addr):
    assert node_token_api.check_bind(addr) == addr


@pytest.mark.parametrize("addr", [
    "0.0.0.0", "127.0.0.1", "127.0.0.2", "192.168.1.5", "10.0.0.5", "172.17.0.1", "8.8.8.8",
    "100.63.255.255", "100.128.0.0", "194.233.80.26", "255.255.255.255",
    "::1", "::", "fd7a:115c:a1e0::1", "localhost", "hub.tailnet.ts.net", "", " ", "100.64.0", "100.64.0.1/10"])
def test_everything_else_is_refused(addr):
    with pytest.raises(ValueError):
        node_token_api.check_bind(addr)


def test_loopback_is_for_tests_only_and_0000_is_never_allowed():
    assert node_token_api.check_bind("127.0.0.1", allow_loopback=True) == "127.0.0.1"
    for addr in ("0.0.0.0", "192.168.1.5", "8.8.8.8"):
        with pytest.raises(ValueError):
            node_token_api.check_bind(addr, allow_loopback=True)


def test_the_server_refuses_a_public_bind_before_opening_a_socket():
    for addr in ("0.0.0.0", "127.0.0.1", "194.233.80.26"):
        with pytest.raises(ValueError):
            node_token_api.make_server(0, tokens={NAME: TOKEN}, bind=addr)


def test_main_never_passes_allow_loopback():
    src = (ROOT / "tools" / "node_token_api.py").read_text()
    main_src = src[src.index("def main("):]
    assert "allow_loopback" not in main_src


# ---------------------------------------------------------------- the token source

def test_load_tokens_takes_the_names_the_hub_hands_out():
    assert node_token_api.load_tokens({NAME: "  " + TOKEN + "\n", "OTHER": "x"}) == {NAME: TOKEN}


@pytest.mark.parametrize("value", [None, "", "   ", "\n"])
def test_a_missing_or_empty_token_names_the_variable(value):
    env = {} if value is None else {NAME: value}
    with pytest.raises(ValueError) as ei:
        node_token_api.load_tokens(env)
    assert NAME in str(ei.value)


@pytest.mark.parametrize("value", [TOKEN[:10] + " " + TOKEN[10:], TOKEN + "\x00", TOKEN[:20] + "\x1b[0m",
                                   "x" * (node_token_api.MAX_VALUE_LEN + 1)])
def test_a_value_that_is_not_a_token_is_refused_without_echoing_it(value):
    with pytest.raises(ValueError) as ei:
        node_token_api.load_tokens({NAME: value})
    assert NAME in str(ei.value) and value[:10] not in str(ei.value)


# ---------------------------------------------------------------- main(): start-up refusals

def _start_env(**over):
    env = {"NODE_TOKEN_BIND": "100.64.0.9", NAME: TOKEN, node_token_api.ORG_NODE_TOKEN_DB_ENV: DSN}
    env.update(over)
    return {k: v for k, v in env.items() if v is not None}


def _refused(argv, env, capsys) -> str:
    with pytest.raises(SystemExit) as ei:
        node_token_api.main(argv, env)
    assert ei.value.code == 2
    err = capsys.readouterr().err
    assert _holds_no_value(err.encode()) and "Sy-nth" not in err
    return err


@pytest.fixture
def no_server(monkeypatch):
    """main() without a socket, a database or a logging setup; ORG_DB_URL restored afterwards."""
    seen = {}
    monkeypatch.setenv("ORG_DB_URL", "x")
    monkeypatch.delenv("ORG_DB_URL")
    monkeypatch.setattr(logging, "basicConfig", lambda **k: None)
    monkeypatch.setattr(node_token_api, "_preflight", lambda: seen.setdefault("preflight", os.environ.get("ORG_DB_URL")))

    class Stub:
        server_address = ("100.64.0.9", 8792)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            seen["closed"] = True

    def make(port, **kw):
        seen["make"] = dict(kw, port=port)
        return Stub()
    monkeypatch.setattr(node_token_api, "make_server", make)
    return seen


def test_main_without_a_bind_address_is_exit_2(capsys, no_server):
    err = _refused([], _start_env(NODE_TOKEN_BIND=None), capsys)
    assert "NODE_TOKEN_BIND" in err and "preflight" not in no_server


@pytest.mark.parametrize("bind", ["0.0.0.0", "127.0.0.1", "194.233.80.26", "hub.example"])
def test_main_with_a_non_tailnet_bind_is_exit_2(capsys, no_server, bind):
    err = _refused([], _start_env(NODE_TOKEN_BIND=bind), capsys)
    assert "refused" in err or "not an IPv4" in err
    assert "preflight" not in no_server and "make" not in no_server


def test_main_with_the_token_missing_names_the_variable_and_touches_nothing(capsys, no_server):
    err = _refused([], _start_env(**{NAME: None}), capsys)
    assert NAME in err and "preflight" not in no_server and "make" not in no_server


def test_main_with_the_dsn_missing_names_it_and_never_uses_the_full_role(capsys, no_server):
    env = _start_env(**{node_token_api.ORG_NODE_TOKEN_DB_ENV: None, "ORG_DB_URL": "postgresql://org:fullrole@h/db"})
    err = _refused([], env, capsys)
    assert node_token_api.ORG_NODE_TOKEN_DB_ENV in err and "fullrole" not in err
    assert "preflight" not in no_server and "ORG_DB_URL" not in os.environ


def test_main_hands_the_role_dsn_to_lib_db_and_drops_the_secrets_from_the_environment(no_server, monkeypatch):
    monkeypatch.setenv(NAME, TOKEN)
    monkeypatch.setenv(node_token_api.ORG_NODE_TOKEN_DB_ENV, DSN)
    monkeypatch.setenv("NODE_TOKEN_BIND", "100.64.0.9")
    assert node_token_api.main(["--port", "8899"]) == 0
    assert no_server["preflight"] == DSN                       # lib.db reads ORG_DB_URL, and gets the role's
    assert no_server["make"]["tokens"] == {NAME: TOKEN} and no_server["make"]["bind"] == "100.64.0.9"
    assert no_server["make"]["port"] == 8899 and no_server["closed"] is True
    for gone in (NAME, node_token_api.ORG_NODE_TOKEN_DB_ENV):    # a child of this process inherits neither
        assert gone not in os.environ


def test_the_command_line_bind_beats_the_environment(no_server, monkeypatch):
    monkeypatch.setenv(NAME, TOKEN)
    monkeypatch.setenv(node_token_api.ORG_NODE_TOKEN_DB_ENV, DSN)
    monkeypatch.setenv("NODE_TOKEN_BIND", "100.64.0.9")
    assert node_token_api.main(["--bind", "100.64.0.20"]) == 0
    assert no_server["make"]["bind"] == "100.64.0.20"


def test_a_database_that_is_not_ready_stops_start_with_the_class_only(capsys, no_server, monkeypatch):
    def not_ready():
        raise RuntimeError("password authentication failed for user org_node_token " + DSN)
    monkeypatch.setattr(node_token_api, "_preflight", not_ready)
    monkeypatch.setenv(NAME, TOKEN)
    monkeypatch.setenv(node_token_api.ORG_NODE_TOKEN_DB_ENV, DSN)
    monkeypatch.setenv("NODE_TOKEN_BIND", "100.64.0.9")
    assert node_token_api.main([]) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "Sy-nth" not in err and "password" not in err and "make" not in no_server


# ---------------------------------------------------------------- the unit and bind-tailnet.sh

def _unit() -> str:
    return UNIT.read_text(encoding="utf-8")


def _live_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_the_unit_runs_the_two_fetches_then_drops_privileges_then_the_service_in_that_order():
    line = next(ln for ln in _unit().splitlines() if ln.startswith("ExecStart="))
    order = ["bind-tailnet.sh", "infisical_setup.py run Agents-Core prod --as contabo --path /node-token",
             "infisical_setup.py run Org-Node prod --as contabo", "setpriv --reuid=org-node-token",
             "-m tools.node_token_api --port 8792"]
    positions = [line.index(piece) for piece in order]
    assert positions == sorted(positions) and len(set(positions)) == len(order)


def test_the_unit_carries_no_secret_and_no_address():
    live = "\n".join(_live_lines(_unit()))
    for banned in ("ORG_DB_URL", "postgresql://", "CLAUDE_CODE_OAUTH_TOKEN=", "sk-ant", "0.0.0.0",
                   "EnvironmentFile", "/etc/infisical", "AGE-SECRET-KEY"):
        assert banned not in live, banned
    assert not [ln for ln in live.splitlines() if ln.startswith("Environment=") and "100." in ln]


def test_the_unit_is_sandboxed_like_the_join_unit_and_has_no_writable_path():
    live = _live_lines(_unit())
    for directive in ("NoNewPrivileges=yes", "ProtectSystem=strict", "ProtectHome=yes", "PrivateTmp=yes",
                      "ProtectKernelTunables=yes", "ProtectKernelModules=yes", "ProtectControlGroups=yes",
                      "RestrictSUIDSGID=yes", "LockPersonality=yes"):
        assert directive in live
    assert not [ln for ln in live if ln.startswith(("ReadWritePaths", "User=", "Group="))]
    assert "Restart=on-failure" in live and "After=network-online.target tailscaled.service" in live


def test_the_unit_points_at_files_that_exist():
    line = next(ln for ln in _unit().splitlines() if ln.startswith("ExecStart="))
    prefix = "/opt/MoonieXHQ/Agents/Core/"
    for rel in ("deploy/node-token/bind-tailnet.sh", "tools/infisical_setup.py"):
        assert prefix + rel in line and (ROOT / rel).is_file()
    assert (ROOT / "tools" / "node_token_api.py").is_file()


def _run_bind(tmp_path: Path, tailscale_body: str | None, command: list[str]):
    """bind-tailnet.sh with a fake `tailscale` first on PATH (or none at all)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    link = bin_dir / "awk"
    if not link.exists():
        link.symlink_to(shutil.which("awk"))
    if tailscale_body is not None:
        ts = bin_dir / "tailscale"
        ts.write_text("#!/bin/sh\n" + tailscale_body)
        ts.chmod(0o755)
    return subprocess.run(["/bin/sh", str(BIND_SH), *command], env={"PATH": str(bin_dir)},
                          capture_output=True, text=True, timeout=30)


def test_bind_tailnet_exports_the_address_to_the_command(tmp_path):
    r = _run_bind(tmp_path, 'echo 100.64.0.9\n', ["/bin/sh", "-c", 'echo "bind=$NODE_TOKEN_BIND"'])
    assert (r.returncode, r.stdout) == (0, "bind=100.64.0.9\n")


def test_bind_tailnet_takes_the_first_address_only(tmp_path):
    r = _run_bind(tmp_path, 'printf "100.64.0.9\\n100.64.0.10\\n"\n', ["/bin/sh", "-c", 'echo "$NODE_TOKEN_BIND"'])
    assert r.stdout == "100.64.0.9\n"


@pytest.mark.parametrize("body", ["exit 1\n", "exit 0\n", "echo\n", "echo >&2 down; exit 1\n"])
def test_bind_tailnet_fails_closed_and_never_runs_the_command(tmp_path, body):
    marker = tmp_path / "ran"
    r = _run_bind(tmp_path, body, ["/bin/sh", "-c", f"touch {marker}"])
    assert r.returncode == 1 and not marker.exists()
    assert "no tailnet IPv4 address" in r.stderr


def test_bind_tailnet_without_tailscale_installed_fails_closed(tmp_path):
    marker = tmp_path / "ran"
    r = _run_bind(tmp_path, None, ["/bin/sh", "-c", f"touch {marker}"])
    assert r.returncode == 1 and not marker.exists()


def test_bind_tailnet_is_executable_like_its_sibling_scripts():
    assert BIND_SH.stat().st_mode & stat.S_IXUSR, "chmod +x deploy/node-token/bind-tailnet.sh"

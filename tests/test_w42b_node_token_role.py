"""Org Mesh W4.2b: the least-privilege hub role of the node-token service, `org_node_token`.

deploy/node-token/org_node_token_role.sql grants SELECT on four columns of `hosts` and nothing
else; deploy/node-token/org_node_token_role.py runs it with a password it makes and prints the
role's URL on stdout only. Same shape and the same tests as tests/test_w46c_join_role.py.

Offline: the file's shape, that its grant is exactly the columns tools/node_token_api.py selects,
and the script with a psql shim. Postgres (skipped without ORG_TEST_DB_URL and psql): the service
answering over HTTP AS the role, every other thing the role must not be able to do, the file run
twice, the self-check catching a drifted attribute. They create the role `org_node_token` in the
cluster and leave it there (it holds no grant once the tables are dropped); use a throwaway
server, as the other pg tests do:

    ORG_TEST_DB_URL=postgresql://org@127.0.0.1:54329/org_test \\
        .venv/bin/python -m pytest -p no:warnings tests/test_w42b_node_token_role.py

No test writes a real secret: the role password is random per test and appears in no assertion
message.
"""
from __future__ import annotations

import http.client
import importlib.util
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lib import db, db_pg
from tools import hq_join, node_token_api

from test_w43_join_api import PUB, _PG_TABLES

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "deploy" / "node-token" / "org_node_token_role.sql"
SCRIPT = ROOT / "deploy" / "node-token" / "org_node_token_role.py"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
GRANTED = {"host", "status", "pubkey", "approved_at"}
APPROVED = "2026-10-03T10:00:00+00:00"
TOKEN = "sk-ant-oat01-SYNTHETIC-nottoken-0123456789abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMN"
NAME = "CLAUDE_CODE_OAUTH_TOKEN"

_spec = importlib.util.spec_from_file_location("org_node_token_role_script", SCRIPT)
role_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(role_script)


def _sql() -> str:
    return SQL.read_text(encoding="utf-8")


# ------------------------------------------------------------ the file's shape

def test_the_file_is_ascii_and_stops_on_the_first_error():
    assert not [b for b in SQL.read_bytes() if b > 127]
    assert "\\set ON_ERROR_STOP on" in _sql()


def test_the_file_takes_a_scram_verifier_never_a_password_and_never_a_literal():
    sql = _sql()
    live = "\n".join(ln for ln in sql.splitlines() if not ln.lstrip().startswith("--"))
    assert live.count("PASSWORD :'org_node_token_verifier'") == 2          # CREATE ROLE and ALTER ROLE
    assert not re.search(r"PASSWORD\s+'", live)                            # no literal, anywhere
    assert "ORG_NODE_TOKEN_VERIFIER" in sql and "SCRAM-SHA-256" in sql
    assert "org_node_token_password" not in live and "ORG_NODE_TOKEN_PASSWORD" not in live
    assert "< 24" not in live                                              # the length guard moved: see below


def test_the_file_refuses_anything_but_a_scram_verifier_before_it_touches_the_role():
    sql = _sql()
    guard, role = sql.index("bad_verifier"), sql.index("CREATE ROLE org_node_token")
    assert guard < role and "is not a SCRAM-SHA-256 verifier" in sql


def test_the_role_is_a_login_with_three_connections_and_no_attribute_that_widens_it():
    sql = _sql()
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS" in sql
    assert "CONNECTION LIMIT 3" in sql and "statement_timeout" in sql


def test_the_only_grants_are_usage_on_the_schema_and_four_columns_of_hosts():
    grants = re.findall(r"^\s*GRANT\b[^;]*;", _sql(), flags=re.MULTILINE)
    assert [" ".join(g.split()) for g in grants] == [
        "GRANT USAGE ON SCHEMA public TO org_node_token;",
        "GRANT SELECT (host, status, pubkey, approved_at) ON hosts TO org_node_token;"]
    assert "ALL PRIVILEGES" not in _sql() and "WITH GRANT OPTION" not in _sql()


def test_the_self_check_wants_the_same_four_columns():
    want = re.search(r"want text := '([^']+)'", _sql()).group(1)
    assert set(want.split()) == {f"hosts.{c}:SELECT" for c in GRANTED}


def test_the_grant_is_exactly_the_columns_the_service_selects():
    """The statements are in tools/node_token_api.py; a column the service starts to read must be
    added to the grant (and so to the file) in the same change, or the service fails at start."""
    src = (ROOT / "tools" / "node_token_api.py").read_text()
    selected, where = set(), set()
    for cols, tail in re.findall(r"SELECT ([a-z_, ]+) FROM hosts( WHERE [a-z_]+)?", src):
        selected |= {c.strip() for c in cols.split(",")}
        where |= set(re.findall(r"WHERE ([a-z_]+)", tail))
    assert selected == GRANTED and where == {"host"}


def test_the_service_issues_no_write_statement_at_all():
    src = (ROOT / "tools" / "node_token_api.py").read_text().split('"""', 2)[2]
    assert not re.search(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|CREATE|ALTER|DROP|GRANT)\b", src)


# ------------------------------------------------------------ deploy/node-token/org_node_token_role.py

_ADMIN = "postgresql://org:Ad%40min-pw-0123456789@db.example.internal:5433/hub?sslmode=require"

_SHIM = """#!/bin/sh
# records what psql was started with (argv, and the WHOLE environment); echoes the statement the way
# a server error would, with the verifier it was given, only when SHIM_ECHO=1
{ for a in "$@"; do printf 'ARG %s\\n' "$a"; done; env | sort; } > "$SHIM_LOG"
[ "${SHIM_ECHO:-}" = 1 ] && echo "ERROR: syntax error near PASSWORD '$ORG_NODE_TOKEN_VERIFIER'" >&2
exit "${SHIM_RC:-0}"
"""


@pytest.fixture
def shim(tmp_path, monkeypatch):
    psql = tmp_path / "psql"
    psql.write_text(_SHIM)
    psql.chmod(0o755)
    log = tmp_path / "psql.log"
    monkeypatch.setenv("SHIM_LOG", str(log))
    monkeypatch.setenv(role_script.PSQL_ENV, str(psql))
    return log


def _recorded(log: Path):
    lines = log.read_text().splitlines()
    args = [ln[4:] for ln in lines if ln.startswith("ARG ")]
    env = dict(ln.split("=", 1) for ln in lines if not ln.startswith("ARG ") and "=" in ln)
    return args, env


def _password_of(out: str) -> str:
    """The password, from the one URL the script prints (the only place it may appear)."""
    return urlsplit(out.strip()).password


def test_the_role_script_runs_the_sql_and_prints_the_role_url_and_nothing_else(shim, capsys):
    rc = role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN})
    out, err = capsys.readouterr()
    assert rc == 0
    args, env = _recorded(shim)
    password = _password_of(out)
    assert len(password) >= 24 and re.fullmatch(r"[A-Za-z0-9_-]+", password)
    assert out == f"postgresql://org_node_token:{password}@db.example.internal:5433/hub?sslmode=require\n"
    assert args == ["-X", "-v", "ON_ERROR_STOP=1", "-f", str(SQL)]
    assert password not in " ".join(args) and password not in err     # argv and stderr: never


_STALE = "stale-" + "plain-" + "0123456789"          # built from parts: gitleaks flags NAME = "word-123..." literals


def test_psql_is_given_the_verifier_of_the_password_and_the_password_nowhere(shim, capsys):
    """The statement psql sends is CREATE/ALTER ROLE ... PASSWORD :'org_node_token_verifier': what a
    server logs or echoes is the one-way verifier. The password is in no argument and no environment
    variable of psql, and the verifier is the one made from it."""
    assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN, "ORG_NODE_TOKEN_PASSWORD": _STALE}) == 0
    out, _ = capsys.readouterr()
    password = _password_of(out)
    log = shim.read_text()
    args, env = _recorded(shim)
    assert password not in log and _STALE not in log                # argv and the whole environment
    assert "ORG_NODE_TOKEN_PASSWORD" not in env                            # not even a stale one from the caller
    verifier = env[role_script.VERIFIER_ENV]
    assert re.fullmatch(r"SCRAM-SHA-256\$4096:[A-Za-z0-9+/]{22}==\$[A-Za-z0-9+/]{43}=:[A-Za-z0-9+/]{43}=", verifier)
    assert password not in verifier
    # made from THIS password: same salt and iteration count give the same verifier
    salt = role_script.base64.b64decode(verifier.split("$")[1].split(":")[1])
    assert role_script.scram_verifier(password, salt=salt) == verifier


def test_the_role_script_connects_through_pg_variables_and_keeps_no_admin_url(shim):
    assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN, "PGOPTIONS": "-c x=1"}) == 0
    args, env = _recorded(shim)
    assert (env["PGHOST"], env["PGPORT"], env["PGUSER"], env["PGDATABASE"], env["PGSSLMODE"]) == (
        "db.example.internal", "5433", "org", "hub", "require")
    assert env["PGPASSWORD"] == "Ad@min-pw-0123456789"                 # percent-decoded, in env only
    assert "PGOPTIONS" not in env                                      # no inherited PG* setting
    assert "Ad" not in " ".join(args) and "ORG_DB_URL" not in env


def test_each_run_makes_a_new_password_and_a_new_salt(shim, capsys):
    passwords, verifiers = set(), set()
    for _ in range(3):
        assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN}) == 0
        passwords.add(_password_of(capsys.readouterr().out))
        verifiers.add(_recorded(shim)[1][role_script.VERIFIER_ENV])
    assert len(passwords) == 3 and len(verifiers) == 3
    assert len({v.split("$")[1] for v in verifiers}) == 3                  # three salts


# RFC 7677, section 3: user "user", password "pencil", salt W22ZaJ0SNY7soEsUEjb6gQ==, i=4096.
_RFC_AUTH_MESSAGE = ("n=user,r=rOprNGfwEbeRWgbNEkqO,"
                     "r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0,s=W22ZaJ0SNY7soEsUEjb6gQ==,i=4096,"
                     "c=biws,r=rOprNGfwEbeRWgbNEkqO%hvYDpWUa2RaTCAfuxFIlj)hNlF$k0")
_RFC_CLIENT_PROOF = "dHzbZapWIk4jUhN+Ute9ytag9zjfMHgsqmmiz7AndVQ="
_RFC_SERVER_SIGNATURE = "6rriTRBi23WpRR/wtup+mMhUZUn/dB5nLTJRsjl95G4="


def test_the_verifier_is_the_scram_sha_256_one_by_the_rfc_7677_example():
    """The verifier is checked against the RFC's own exchange, not against a copy of this code: from
    StoredKey and ServerKey alone, the RFC's ServerSignature is HMAC(ServerKey, AuthMessage), and its
    ClientProof XOR HMAC(StoredKey, AuthMessage) is a ClientKey whose hash is the StoredKey."""
    import base64, hashlib, hmac
    salt = base64.b64decode("W22ZaJ0SNY7soEsUEjb6gQ==")
    verifier = role_script.scram_verifier("pencil", salt=salt)
    head, rest = verifier.split("$", 1)
    iterations, salt_b64 = rest.split("$", 1)[0].split(":")
    stored_b64, server_b64 = rest.split("$", 1)[1].split(":")
    assert (head, iterations, salt_b64) == ("SCRAM-SHA-256", "4096", "W22ZaJ0SNY7soEsUEjb6gQ==")
    stored, server = base64.b64decode(stored_b64), base64.b64decode(server_b64)
    auth = _RFC_AUTH_MESSAGE.encode()
    assert base64.b64encode(hmac.new(server, auth, hashlib.sha256).digest()).decode() == _RFC_SERVER_SIGNATURE
    signature = hmac.new(stored, auth, hashlib.sha256).digest()
    client_key = bytes(a ^ b for a, b in zip(base64.b64decode(_RFC_CLIENT_PROOF), signature))
    assert hashlib.sha256(client_key).digest() == stored


def test_the_verifier_has_the_shape_the_sql_guard_wants():
    verifier = role_script.scram_verifier("a" * 43)
    # Postgres's `$` is the end of the string, Python's is also before a final newline: use \Z
    guard = re.search(r"!~ '([^']+)'", _sql()).group(1).replace("[$]", r"\$")[:-1] + r"\Z"
    assert re.search(guard, verifier)
    for bad in ("", "a" * 43, verifier.replace("SCRAM-SHA-256", "SCRAM-SHA-1"), verifier + "x", "x" + verifier,
                verifier.replace("$4096:", "$:"), verifier.rsplit(":", 1)[0], verifier + "\n"):
        assert not re.search(guard, bad), bad


def test_a_failing_psql_leaves_stdout_empty_so_put_stores_nothing(shim, capsys, monkeypatch):
    monkeypatch.setenv("SHIM_RC", "3")
    monkeypatch.setenv("SHIM_ECHO", "1")
    rc = role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN})
    out, err = capsys.readouterr()
    verifier = _recorded(shim)[1][role_script.VERIFIER_ENV]
    assert rc == 1 and out == ""
    assert verifier not in err and "PASSWORD '***'" in err               # scrubbed in psql's own echo
    assert "psql exited 3" in err


@pytest.mark.parametrize("url", [
    "", "mysql://u:p@h/db", "postgresql://h/db", "postgresql://u:p@/db", "postgresql://u:p@h", "postgresql://u:p@h:port/db"])
def test_the_role_script_refuses_a_missing_or_odd_admin_url_before_running_psql(shim, capsys, url):
    assert role_script.main([], {**os.environ, "ORG_DB_URL": url}) == 2
    out, err = capsys.readouterr()
    assert out == "" and not shim.exists()
    assert "ORG_DB_URL" in err and "p@" not in err


def test_the_role_script_refuses_arguments_and_a_missing_psql(capsys, monkeypatch, tmp_path):
    assert role_script.main(["--password", "x"], {**os.environ, "ORG_DB_URL": _ADMIN}) == 2
    monkeypatch.setenv(role_script.PSQL_ENV, str(tmp_path / "no-such-psql"))
    assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN}) == 2
    out, err = capsys.readouterr()
    assert out == "" and "psql is not installed" in err and "--password" not in out


def test_the_role_script_url_of_an_ipv6_host_keeps_its_brackets():
    parts = role_script.urlsplit("postgresql://org:pw@[::1]:5432/hub")
    assert role_script.role_url(parts, "abc") == "postgresql://org_node_token:abc@[::1]:5432/hub"


# ------------------------------------------------------------ Postgres: the real thing

pg_only = pytest.mark.skipif(
    not ORG_TEST_DB_URL or not shutil.which("psql"),
    reason="ORG_TEST_DB_URL and psql needed -- runs against a throwaway org_test, never the hub")


def _drop_all(url: str) -> None:
    conn = db_pg.connect(url, timeout=10)
    try:
        for table in _PG_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        conn.commit()
    finally:
        conn.close()


def _with_login(url: str, user: str, password: str) -> str:
    p = urlsplit(url)
    host = f"{p.hostname}:{p.port}" if p.port else p.hostname
    return urlunsplit((p.scheme, f"{user}:{password}@{host}", p.path, p.query, p.fragment))


def _run_role_file(owner_url: str, verifier: str | None, *, via: str = "env", echo: bool = False):
    """psql on the role file, handed `verifier` (None: nothing). echo=True adds psql's -e, which prints
    every statement it sends to the server, variables already filled in."""
    env = {k: v for k, v in os.environ.items() if k not in ("ORG_NODE_TOKEN_VERIFIER", "ORG_NODE_TOKEN_PASSWORD")}
    argv = ["psql", "-X", "-v", "ON_ERROR_STOP=1"] + (["-e"] if echo else [])
    if verifier is not None and via == "env":
        env["ORG_NODE_TOKEN_VERIFIER"] = verifier
    if verifier is not None and via == "var":
        argv += ["-v", f"org_node_token_verifier={verifier}"]
    argv += ["-f", str(SQL), owner_url]
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=60)


class Hub:
    def __init__(self, owner_url: str, password: str, monkeypatch):
        self.owner_url = owner_url
        self.password = password
        self.role_url = _with_login(owner_url, "org_node_token", password)
        self._mp = monkeypatch

    def use(self, which: str):
        """Point lib.db (and so every server thread) at the owner or at org_node_token."""
        self._mp.setenv("ORG_DB_URL", self.owner_url if which == "owner" else self.role_url)

    def owner_rows(self, sql: str, params=()):
        conn = db_pg.connect(self.owner_url, timeout=10)
        try:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
        finally:
            conn.close()

    def owner_exec(self, sql: str, params=()):
        conn = db_pg.connect(self.owner_url, timeout=10)
        try:
            conn.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    def host(self, host="node-a", status=hq_join.STATUS_READY, approved=True):
        self.owner_exec("INSERT INTO hosts (host, status, pubkey, approved_at, deploy_pubkey, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (host, status, PUB, APPROVED if approved else None,
                         "ssh-ed25519 AAAA org-node:" + host, APPROVED))

    def attempt(self, sql: str, params=()) -> str:
        """Run one statement as org_node_token on a connection of its own: the error text, or RAN."""
        conn = db_pg.connect(self.role_url, timeout=10)
        try:
            try:
                conn.execute(sql, params)
                conn.commit()
            except Exception as exc:
                return str(exc)
            return "RAN"
        finally:
            conn.close()

    def owner_role(self) -> str:
        """The owner connection's login role, quoted: whatever the test database was created with."""
        return self.owner_rows("SELECT quote_ident(current_user) AS r")[0]["r"]

    def sessions(self) -> int:
        return self.owner_rows("SELECT count(*) AS n FROM pg_stat_activity WHERE usename = 'org_node_token'")[0]["n"]


@pytest.fixture
def pg(monkeypatch):
    if not ORG_TEST_DB_URL or not shutil.which("psql"):
        pytest.skip("ORG_TEST_DB_URL and psql needed")
    for var in ("ORG_NODE_TOKEN_DB_URL", "CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    password = secrets.token_hex(16)
    _drop_all(ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    db.init()
    r = _run_role_file(ORG_TEST_DB_URL, role_script.scram_verifier(password))
    assert r.returncode == 0, r.stderr
    h = Hub(ORG_TEST_DB_URL, password, monkeypatch)
    yield h
    db_pg.evict(h.owner_url)
    db_pg.evict(h.role_url)
    _drop_all(ORG_TEST_DB_URL)


class _Sealer:
    def __init__(self):
        self.calls = []

    def __call__(self, recipient, plaintext):
        self.calls.append(recipient)
        return b"-----BEGIN AGE ENCRYPTED FILE-----\nc3ludGhldGlj\n-----END AGE ENCRYPTED FILE-----\n"


def _serve(sealer=None):
    server = node_token_api.make_server(0, tokens={NAME: TOKEN}, bind="127.0.0.1", allow_loopback=True,
                                        sealer=sealer or _Sealer())
    t = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
    t.start()
    return server, t


def _stop(server, t):
    server.shutdown()
    server.server_close()
    t.join(timeout=5)


def _get(server, path):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=15)
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        return r.status, r.read()
    finally:
        conn.close()


@pg_only
def test_the_service_answers_over_http_as_the_least_privilege_role(pg):
    pg.host("node-a")
    pg.host("node-left", status=hq_join.STATUS_LEFT)
    pg.host("node-new", status=hq_join.STATUS_PENDING, approved=False)
    pg.use("role")
    sealer = _Sealer()
    server, t = _serve(sealer)
    try:
        assert _get(server, "/health") == (200, b'{"ok":true,"token_loaded":true,"db":true}')
        assert _get(server, "/v1/token?host=node-a")[0] == 200
        assert json.loads(_get(server, "/v1/token?host=node-left")[1]) == {"error": "left"}
        assert json.loads(_get(server, "/v1/token?host=node-new")[1]) == {"error": "not_approved"}
        assert json.loads(_get(server, "/v1/token?host=nobody")[1]) == {"error": "unknown_host"}
    finally:
        _stop(server, t)
    assert sealer.calls == [PUB]


@pg_only
def test_a_burst_of_requests_never_runs_the_role_out_of_its_three_connections(pg):
    pg.host("node-a")
    pg.use("role")
    server, t = _serve()
    try:
        with ThreadPoolExecutor(max_workers=12) as pool:
            statuses = list(pool.map(lambda i: _get(server, "/v1/token?host=node-a")[0], range(24)))
    finally:
        _stop(server, t)
    assert set(statuses) <= {200, 503} and statuses.count(200) >= 12     # busy is allowed, a 500 is not
    end, n = time.time() + 3.0, -1
    while time.time() < end:                                             # no connection outlives its request
        n = pg.sessions()
        if n == 0:
            break
        time.sleep(0.05)
    assert n == 0


@pg_only
def test_the_role_can_read_the_four_columns_and_nothing_else_of_hosts(pg):
    pg.host("node-a")
    assert pg.attempt("SELECT status, pubkey, approved_at FROM hosts WHERE host = ?", ("node-a",)) == "RAN"
    assert pg.attempt("SELECT host, status, pubkey, approved_at FROM hosts") == "RAN"
    assert pg.attempt("SELECT 1 FROM hosts LIMIT 1") == "RAN"
    for column in ("deploy_pubkey", "config_json", "os", "hq_root", "provides", "runners", "updated_at"):
        assert "permission denied" in pg.attempt(f"SELECT {column} FROM hosts"), column
    assert "permission denied" in pg.attempt("SELECT * FROM hosts")


@pg_only
@pytest.mark.parametrize("sql", [
    "UPDATE hosts SET approved_at = '2026-10-03' WHERE host = 'node-a'",      # cannot approve a node
    "UPDATE hosts SET status = 'online' WHERE host = 'node-a'",
    "UPDATE hosts SET pubkey = 'age1x' WHERE host = 'node-a'",                # cannot swap the recipient
    "INSERT INTO hosts (host, status) VALUES ('evil', 'online')",
    "DELETE FROM hosts WHERE host = 'node-a'",
    "TRUNCATE hosts",
    "SELECT * FROM node_secrets",
    "SELECT * FROM join_tokens",
    "SELECT * FROM tasks",
    "SELECT * FROM events",
    "SELECT * FROM letters",
    "SELECT * FROM locks",
    "SELECT * FROM c_level_sessions",
    "INSERT INTO events (actor, kind, payload, ts) VALUES ('x', 'y', '{}', '2026-10-03')",
    "CREATE TABLE public.sneaky (x int)",
    "CREATE ROLE sneaky LOGIN",
    "DROP TABLE hosts",
    "ALTER TABLE hosts ADD COLUMN x int",
    "GRANT SELECT ON tasks TO PUBLIC",
    "COPY hosts TO PROGRAM 'id'",
    "SET ROLE {owner}",                                                       # the hub owner: `org` live, `postgres` in CI
])
def test_everything_else_the_role_tries_is_refused(pg, sql):
    pg.host("node-a")
    result = pg.attempt(sql.replace("{owner}", pg.owner_role()))   # replace, not format: one case holds a literal {}
    assert result != "RAN", sql
    assert re.search(r"permission denied|must be (owner|superuser)", result), result
    assert [r["host"] for r in pg.owner_rows("SELECT host FROM hosts")] == ["node-a"]   # nothing changed
    row = pg.owner_rows("SELECT status, pubkey, approved_at FROM hosts")[0]
    assert (row["status"], row["pubkey"], row["approved_at"]) == (hq_join.STATUS_READY, PUB, APPROVED)
    assert pg.owner_rows("SELECT has_table_privilege('org_node_token', 'tasks', 'SELECT') AS t")[0]["t"] is False
    assert pg.owner_rows("SELECT count(*) AS n FROM events")[0]["n"] == 0


@pg_only
def test_a_statement_that_runs_long_is_cut_off(pg):
    assert "statement timeout" in pg.attempt("SELECT pg_sleep(8)")


_VERIFIER = "SELECT rolpassword AS p FROM pg_authid WHERE rolname = 'org_node_token'"


@pg_only
def test_the_file_run_twice_leaves_the_same_grants_and_a_new_password(pg):
    pg.host("node-a")
    before = pg.owner_rows(_VERIFIER)
    again = secrets.token_hex(16)
    r = _run_role_file(pg.owner_url, role_script.scram_verifier(again))
    assert r.returncode == 0 and "role and grants are in place and verified" in r.stdout
    assert pg.password not in r.stdout + r.stderr and again not in r.stdout + r.stderr
    grants = pg.owner_rows("SELECT string_agg(privilege_type || ':' || column_name, ' ' ORDER BY column_name) AS g "
                           "FROM information_schema.column_privileges WHERE grantee = 'org_node_token' "
                           "AND table_name = 'hosts'")[0]["g"]
    assert grants == "SELECT:approved_at SELECT:host SELECT:pubkey SELECT:status"
    assert pg.owner_rows(_VERIFIER) != before        # a fresh SCRAM verifier; the password is not readable


@pg_only
def test_a_verifier_given_as_a_psql_variable_rotates_too(pg):
    before = pg.owner_rows(_VERIFIER)
    new = secrets.token_hex(16)
    r = _run_role_file(pg.owner_url, role_script.scram_verifier(new), via="var")
    assert r.returncode == 0, r.stderr
    assert new not in r.stdout + r.stderr
    assert pg.owner_rows(_VERIFIER) != before


@pg_only
def test_postgres_stores_the_verifier_as_given_and_does_not_hash_it_again(pg):
    """A string that starts with SCRAM-SHA-256$ is kept as it is; a plain password would be hashed. The
    stored value is byte for byte the verifier this file was given. (The throwaway cluster trusts
    127.0.0.1, so a login here proves nothing about a password; the verifier's own correctness is the
    RFC 7677 test above.)"""
    pg.host("node-a")
    new = secrets.token_hex(16)
    verifier = role_script.scram_verifier(new)
    assert _run_role_file(pg.owner_url, verifier).returncode == 0
    assert pg.owner_rows(_VERIFIER)[0]["p"] == verifier
    pg.role_url = _with_login(pg.owner_url, "org_node_token", new)
    assert pg.attempt("SELECT count(*) FROM hosts") == "RAN"


@pg_only
def test_no_statement_psql_sends_to_the_server_holds_the_password(pg):
    """psql -e prints every statement it sends, variables filled in: the text a server would log. It
    holds the verifier twice (CREATE/ALTER ROLE and the shape check) and the password nowhere."""
    password = secrets.token_hex(16)
    verifier = role_script.scram_verifier(password)
    r = _run_role_file(pg.owner_url, verifier, echo=True)
    assert r.returncode == 0, r.stderr
    sent = r.stdout + r.stderr
    assert "ALTER ROLE org_node_token LOGIN CONNECTION LIMIT 3 PASSWORD '" + verifier + "'" in sent
    assert password not in sent


_GOOD = role_script.scram_verifier("a" * 43)


@pg_only
@pytest.mark.parametrize("bad", [
    None, "", "weakpw-1234", "x" * 43, secrets.token_urlsafe(32),                  # a plain password: refused, not hashed
    _GOOD.replace("SCRAM-SHA-256", "SCRAM-SHA-1"),
    _GOOD.rsplit(":", 1)[0],                                                       # no ServerKey
    _GOOD.replace("$4096:", "$4096:short"),
    _GOOD + "'; select 1; --"])
def test_anything_but_a_scram_verifier_stops_the_run_and_changes_nothing(pg, bad):
    before = pg.owner_rows(_VERIFIER)
    r = _run_role_file(pg.owner_url, bad)
    assert r.returncode != 0 and "is not a SCRAM-SHA-256 verifier" in r.stderr and "verified" not in r.stdout
    if bad:
        assert bad not in r.stdout
    assert pg.owner_rows(_VERIFIER) == before
    assert pg.attempt("SELECT count(*) FROM hosts") == "RAN"                      # the old password still works


@pg_only
def test_a_grant_added_by_hand_is_removed_by_the_next_run(pg):
    pg.owner_exec("GRANT UPDATE (approved_at) ON hosts TO org_node_token")
    pg.owner_exec("GRANT SELECT ON tasks TO org_node_token")
    assert pg.attempt("SELECT count(*) FROM tasks") == "RAN"
    assert _run_role_file(pg.owner_url, role_script.scram_verifier(pg.password)).returncode == 0
    assert "permission denied" in pg.attempt("SELECT count(*) FROM tasks")
    assert "permission denied" in pg.attempt("UPDATE hosts SET approved_at = NULL")


@pg_only
@pytest.mark.parametrize("attribute,undo", [("CREATEDB", "NOCREATEDB"), ("CREATEROLE", "NOCREATEROLE"),
                                            ("REPLICATION", "NOREPLICATION"), ("BYPASSRLS", "NOBYPASSRLS")])
def test_the_self_check_fails_the_run_when_an_attribute_has_drifted(pg, attribute, undo):
    pg.owner_exec(f"ALTER ROLE org_node_token {attribute}")
    try:
        r = _run_role_file(pg.owner_url, role_script.scram_verifier(pg.password))
        assert r.returncode != 0 and "role attribute it must not have" in r.stderr
        assert "verified" not in r.stdout
    finally:
        pg.owner_exec(f"ALTER ROLE org_node_token {undo}")
    assert _run_role_file(pg.owner_url, role_script.scram_verifier(pg.password)).returncode == 0


def pg_verifier_of_role() -> str:
    conn = db_pg.connect(ORG_TEST_DB_URL, timeout=10)
    try:
        return conn.execute(_VERIFIER).fetchone()["p"]
    finally:
        conn.close()


@pg_only
def test_the_role_script_against_a_real_postgres_makes_a_working_role(monkeypatch, capsys):
    for var in ("ORG_NODE_TOKEN_PSQL", "ORG_NODE_TOKEN_DB_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    _drop_all(ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    db.init()
    capsys.readouterr()                                                  # db.init() prints a line
    try:
        assert role_script.main([], {**os.environ, "ORG_DB_URL": ORG_TEST_DB_URL}) == 0
        out, err = capsys.readouterr()
        url = out.strip()
        assert out.count("\n") == 1 and urlsplit(url).username == "org_node_token"
        password = urlsplit(url).password
        assert password and password not in err
        assert "role and grants are in place and verified" in err
        stored = pg_verifier_of_role()                                   # made from the printed password
        assert role_script.scram_verifier(password, salt=role_script.base64.b64decode(
            stored.split("$")[1].split(":")[1])) == stored
        assert urlsplit(url).hostname == urlsplit(ORG_TEST_DB_URL).hostname
        conn = db_pg.connect(url, timeout=10)
        try:
            assert conn.execute("SELECT count(*) AS n FROM hosts").fetchone() is not None
        finally:
            conn.close()
    finally:
        db_pg.evict(ORG_TEST_DB_URL)
        _drop_all(ORG_TEST_DB_URL)

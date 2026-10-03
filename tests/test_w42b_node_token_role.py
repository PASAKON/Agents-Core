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


def test_the_password_is_never_in_the_file_and_must_be_long():
    sql = _sql()
    assert "PASSWORD :'org_node_token_password'" in sql
    assert not re.search(r"PASSWORD\s+'", sql)                      # no literal, anywhere
    assert "< 24" in sql and "ORG_NODE_TOKEN_PASSWORD" in sql


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
# records what psql was started with; never prints the password unless SHIM_ECHO=1
{ for a in "$@"; do printf 'ARG %s\\n' "$a"; done; env | grep -E '^(PG|ORG_NODE_TOKEN_PASSWORD)' | sort; } > "$SHIM_LOG"
[ "${SHIM_ECHO:-}" = 1 ] && echo "ERROR: syntax error near PASSWORD '$ORG_NODE_TOKEN_PASSWORD'" >&2
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
    env = dict(ln.split("=", 1) for ln in lines if not ln.startswith("ARG "))
    return args, env


def test_the_role_script_runs_the_sql_and_prints_the_role_url_and_nothing_else(shim, capsys):
    rc = role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN})
    out, err = capsys.readouterr()
    assert rc == 0
    args, env = _recorded(shim)
    password = env["ORG_NODE_TOKEN_PASSWORD"]
    assert len(password) >= 24 and re.fullmatch(r"[A-Za-z0-9_-]+", password)
    assert out == f"postgresql://org_node_token:{password}@db.example.internal:5433/hub?sslmode=require\n"
    assert args == ["-X", "-v", "ON_ERROR_STOP=1", "-f", str(SQL)]
    assert password not in " ".join(args) and password not in err     # argv and stderr: never


def test_the_role_script_connects_through_pg_variables_and_keeps_no_admin_url(shim):
    assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN, "PGOPTIONS": "-c x=1"}) == 0
    args, env = _recorded(shim)
    assert (env["PGHOST"], env["PGPORT"], env["PGUSER"], env["PGDATABASE"], env["PGSSLMODE"]) == (
        "db.example.internal", "5433", "org", "hub", "require")
    assert env["PGPASSWORD"] == "Ad@min-pw-0123456789"                 # percent-decoded, in env only
    assert "PGOPTIONS" not in env                                      # no inherited PG* setting
    assert "Ad" not in " ".join(args) and "ORG_DB_URL" not in env


def test_each_run_makes_a_new_password(shim):
    seen = set()
    for _ in range(3):
        assert role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN}) == 0
        seen.add(_recorded(shim)[1]["ORG_NODE_TOKEN_PASSWORD"])
    assert len(seen) == 3


def test_a_failing_psql_leaves_stdout_empty_so_put_stores_nothing(shim, capsys, monkeypatch):
    monkeypatch.setenv("SHIM_RC", "3")
    monkeypatch.setenv("SHIM_ECHO", "1")
    rc = role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN})
    out, err = capsys.readouterr()
    password = _recorded(shim)[1]["ORG_NODE_TOKEN_PASSWORD"]
    assert rc == 1 and out == ""
    assert password not in err and "PASSWORD '***'" in err              # scrubbed in psql's own echo
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


def _run_role_file(owner_url: str, password: str | None, *, via: str = "env"):
    env = {k: v for k, v in os.environ.items() if k != "ORG_NODE_TOKEN_PASSWORD"}
    argv = ["psql", "-X", "-v", "ON_ERROR_STOP=1"]
    if password is not None and via == "env":
        env["ORG_NODE_TOKEN_PASSWORD"] = password
    if password is not None and via == "var":
        argv += ["-v", f"org_node_token_password={password}"]
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
    r = _run_role_file(ORG_TEST_DB_URL, password)
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
    "SET ROLE org",
])
def test_everything_else_the_role_tries_is_refused(pg, sql):
    pg.host("node-a")
    result = pg.attempt(sql)
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
    r = _run_role_file(pg.owner_url, again)
    assert r.returncode == 0 and "role and grants are in place and verified" in r.stdout
    assert pg.password not in r.stdout + r.stderr and again not in r.stdout + r.stderr
    grants = pg.owner_rows("SELECT string_agg(privilege_type || ':' || column_name, ' ' ORDER BY column_name) AS g "
                           "FROM information_schema.column_privileges WHERE grantee = 'org_node_token' "
                           "AND table_name = 'hosts'")[0]["g"]
    assert grants == "SELECT:approved_at SELECT:host SELECT:pubkey SELECT:status"
    assert pg.owner_rows(_VERIFIER) != before        # a fresh SCRAM verifier; the password is not readable


@pg_only
def test_a_password_given_as_a_psql_variable_rotates_too(pg):
    before = pg.owner_rows(_VERIFIER)
    new = secrets.token_hex(16)
    r = _run_role_file(pg.owner_url, new, via="var")
    assert r.returncode == 0, r.stderr
    assert new not in r.stdout + r.stderr
    assert pg.owner_rows(_VERIFIER) != before


@pg_only
@pytest.mark.parametrize("password", [None, "", "weakpw-1234", "x" * 23])
def test_a_missing_or_short_password_stops_the_run_and_changes_nothing(pg, password):
    before = pg.owner_rows(_VERIFIER)
    r = _run_role_file(pg.owner_url, password)
    assert r.returncode != 0 and "missing or shorter than 24" in r.stderr and "verified" not in r.stdout
    if password:
        assert password not in r.stdout + r.stderr
    assert pg.owner_rows(_VERIFIER) == before


@pg_only
def test_a_grant_added_by_hand_is_removed_by_the_next_run(pg):
    pg.owner_exec("GRANT UPDATE (approved_at) ON hosts TO org_node_token")
    pg.owner_exec("GRANT SELECT ON tasks TO org_node_token")
    assert pg.attempt("SELECT count(*) FROM tasks") == "RAN"
    assert _run_role_file(pg.owner_url, pg.password).returncode == 0
    assert "permission denied" in pg.attempt("SELECT count(*) FROM tasks")
    assert "permission denied" in pg.attempt("UPDATE hosts SET approved_at = NULL")


@pg_only
@pytest.mark.parametrize("attribute,undo", [("CREATEDB", "NOCREATEDB"), ("CREATEROLE", "NOCREATEROLE"),
                                            ("REPLICATION", "NOREPLICATION"), ("BYPASSRLS", "NOBYPASSRLS")])
def test_the_self_check_fails_the_run_when_an_attribute_has_drifted(pg, attribute, undo):
    pg.owner_exec(f"ALTER ROLE org_node_token {attribute}")
    try:
        r = _run_role_file(pg.owner_url, pg.password)
        assert r.returncode != 0 and "role attribute it must not have" in r.stderr
        assert "verified" not in r.stdout
    finally:
        pg.owner_exec(f"ALTER ROLE org_node_token {undo}")
    assert _run_role_file(pg.owner_url, pg.password).returncode == 0


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
        assert urlsplit(url).hostname == urlsplit(ORG_TEST_DB_URL).hostname
        conn = db_pg.connect(url, timeout=10)
        try:
            assert conn.execute("SELECT count(*) AS n FROM hosts").fetchone() is not None
        finally:
            conn.close()
    finally:
        db_pg.evict(ORG_TEST_DB_URL)
        _drop_all(ORG_TEST_DB_URL)

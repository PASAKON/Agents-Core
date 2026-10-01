"""Org Mesh W4.6c F3: the public join endpoint runs with the least privilege that works.

Review task-79219f24 F3: tools/join_api.py is reachable from the internet and connected as the
full hub role `org`. Now it connects as `org_join` (deploy/join/org_join_role.sql), from its own
Infisical folder, under its own system user.

Offline tests: which database URL join_api takes and when it refuses, that a connection does not
outlive its request slot, the unit, the role file's shape and that its column grants are exactly
the columns hq_join's SQL touches. Postgres tests (skipped without ORG_TEST_DB_URL and psql): the
real accept and sealed paths, end to end over HTTP, as org_join; every other thing org_join must
not be able to do; the file run twice; the self-check catching drift. They create the role
`org_join` in the cluster and leave it there (it holds no grant once the tables are dropped);
use a throwaway server, as the other pg tests do:

    ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \\
        .venv/bin/python -m pytest -p no:warnings tests/test_w46c_join_role.py

No test writes a real secret: the role password is random per test and appears in no assertion
message.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest

from lib import db, db_pg
from tools import hq_join, join_api

from test_w43_join_api import Api, PUB, _accept_body, CIPHER, _PG_TABLES

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "deploy" / "join" / "org_join_role.sql"
UNIT = ROOT / "deploy" / "join" / "org-join.service"
ORG_TEST_DB_URL = os.environ.get("ORG_TEST_DB_URL", "").strip()
JOIN_URL = "postgresql://org_join:Sy-nth-3tic-pw-0123456789abcdef@127.0.0.1:1/hub"
ORG_URL = "postgresql://org:Sy-nth-3tic-org-pw-0123456789@127.0.0.1:1/hub"
NOW = "2026-10-01T00:00:00+00:00"


# ------------------------------------------------------------ which URL join_api takes

def test_the_join_role_url_wins():
    assert join_api.choose_db_url({"ORG_JOIN_DB_URL": JOIN_URL}) == (JOIN_URL, None)


def test_the_join_role_url_wins_over_the_org_url_and_says_the_org_one_is_ignored():
    url, note = join_api.choose_db_url({"ORG_JOIN_DB_URL": JOIN_URL, "ORG_DB_URL": ORG_URL})
    assert url == JOIN_URL
    assert "ORG_DB_URL" in note and "ignored" in note
    assert "Sy-nth" not in note


@pytest.mark.parametrize("flag", [None, "", "0", "true", "yes", "2", " "])
def test_the_org_role_is_refused_unless_the_flag_is_exactly_1(flag):
    env = {"ORG_DB_URL": ORG_URL}
    if flag is not None:
        env["JOIN_API_ALLOW_ORG_ROLE"] = flag
    with pytest.raises(ValueError) as ei:
        join_api.choose_db_url(env)
    msg = str(ei.value)
    assert "ORG_JOIN_DB_URL" in msg and "JOIN_API_ALLOW_ORG_ROLE=1" in msg
    assert "Sy-nth" not in msg and "postgresql" not in msg


def test_the_org_role_is_used_with_a_one_line_warning_when_the_flag_is_1():
    url, warning = join_api.choose_db_url({"ORG_DB_URL": ORG_URL, "JOIN_API_ALLOW_ORG_ROLE": "1"})
    assert url == ORG_URL
    assert "\n" not in warning
    assert "ORG_JOIN_DB_URL" in warning and "org role" in warning and "JOIN_API_ALLOW_ORG_ROLE=1" in warning
    assert "Sy-nth" not in warning and "postgresql" not in warning


def test_the_flag_does_nothing_when_the_join_url_is_set():
    assert join_api.choose_db_url({"ORG_JOIN_DB_URL": JOIN_URL, "JOIN_API_ALLOW_ORG_ROLE": "1"}) == (JOIN_URL, None)


@pytest.mark.parametrize("env", [{}, {"ORG_JOIN_DB_URL": "  ", "ORG_DB_URL": ""}, {"JOIN_API_ALLOW_ORG_ROLE": "1"}])
def test_with_neither_url_lib_db_keeps_its_own_default(env):
    assert join_api.choose_db_url(env) == (None, None)


class _Stub:
    server_address = ("127.0.0.1", 1)
    minter = None

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        pass


@pytest.fixture
def main_env(monkeypatch):
    """Run main() without a database or a socket; ORG_DB_URL is absent before and after the test."""
    seen = {}
    monkeypatch.setenv("ORG_DB_URL", "x")
    monkeypatch.delenv("ORG_DB_URL")              # registered: undone after the test, absent again
    for var in ("ORG_JOIN_DB_URL", "JOIN_API_ALLOW_ORG_ROLE", "JOIN_API_BIND"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(join_api, "_preflight", lambda: seen.setdefault("preflight", os.environ.get("ORG_DB_URL")))
    monkeypatch.setattr(join_api, "make_server", lambda *a, **k: _Stub())
    monkeypatch.setattr(logging, "basicConfig", lambda **k: None)
    return seen


def test_main_hands_the_join_url_to_lib_db_before_anything_touches_the_database(main_env, monkeypatch):
    monkeypatch.setenv("ORG_JOIN_DB_URL", JOIN_URL)
    assert join_api.main(["--bind", "127.0.0.1"]) == 0
    assert main_env["preflight"] == JOIN_URL


def test_main_with_both_urls_uses_the_join_one(main_env, monkeypatch):
    monkeypatch.setenv("ORG_JOIN_DB_URL", JOIN_URL)
    monkeypatch.setenv("ORG_DB_URL", ORG_URL)
    assert join_api.main(["--bind", "127.0.0.1"]) == 0
    assert main_env["preflight"] == JOIN_URL


def test_main_refuses_the_org_role_before_the_database_is_touched(main_env, monkeypatch, capsys):
    monkeypatch.setenv("ORG_DB_URL", ORG_URL)
    with pytest.raises(SystemExit) as ei:
        join_api.main(["--bind", "127.0.0.1"])
    assert ei.value.code == 2
    assert "preflight" not in main_env
    err = capsys.readouterr().err
    assert "ORG_JOIN_DB_URL" in err and "Sy-nth" not in err and "postgresql" not in err


def test_main_falls_back_to_the_org_role_only_with_the_flag_and_logs_the_warning(main_env, monkeypatch, caplog):
    monkeypatch.setenv("ORG_DB_URL", ORG_URL)
    monkeypatch.setenv("JOIN_API_ALLOW_ORG_ROLE", "1")
    with caplog.at_level(logging.WARNING, logger=join_api._log.name):
        assert join_api.main(["--bind", "127.0.0.1"]) == 0
    assert main_env["preflight"] == ORG_URL
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1 and "ORG_JOIN_DB_URL is not set" in warnings[0]
    assert "Sy-nth" not in caplog.text


def test_main_with_no_url_at_all_is_the_local_sqlite_default_and_sets_nothing(main_env):
    assert join_api.main(["--bind", "127.0.0.1"]) == 0
    assert main_env["preflight"] is None


# ------------------------------------------------------------ a connection does not outlive its slot

@pytest.fixture
def evictions(monkeypatch):
    seen = []
    monkeypatch.setattr(db, "pg_url", lambda: "postgresql://u@h/d")
    monkeypatch.setattr(db_pg, "evict", seen.append)
    return seen


def test_the_slot_closes_the_threads_connection_and_gives_the_slot_back(evictions):
    free = join_api._DB_GATE._value
    with join_api._db_slot():
        assert join_api._DB_GATE._value == free - 1
    assert evictions == ["postgresql://u@h/d"]
    assert join_api._DB_GATE._value == free


def test_the_slot_closes_the_connection_when_the_request_fails_too(evictions):
    free = join_api._DB_GATE._value
    with pytest.raises(RuntimeError):
        with join_api._db_slot():
            raise RuntimeError("boom")
    assert evictions == ["postgresql://u@h/d"]
    assert join_api._DB_GATE._value == free


def test_the_slot_is_given_back_even_if_closing_the_connection_fails(monkeypatch):
    monkeypatch.setattr(db, "pg_url", lambda: "postgresql://u@h/d")

    def boom(_url):
        raise OSError("close failed")

    monkeypatch.setattr(db_pg, "evict", boom)
    free = join_api._DB_GATE._value
    with pytest.raises(OSError):
        with join_api._db_slot():
            pass
    assert join_api._DB_GATE._value == free


def test_the_startup_check_closes_its_connection_on_success_and_on_failure(evictions, monkeypatch):
    class Conn:
        def __init__(self, fail):
            self.fail = fail

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql):
            if self.fail:
                raise RuntimeError("no such table")

    monkeypatch.setattr(db, "get_conn", lambda: Conn(False))
    join_api._preflight()
    assert evictions == ["postgresql://u@h/d"]
    monkeypatch.setattr(db, "get_conn", lambda: Conn(True))
    with pytest.raises(RuntimeError):
        join_api._preflight()
    assert evictions == ["postgresql://u@h/d"] * 2


def test_nothing_is_evicted_on_the_sqlite_default(monkeypatch):
    monkeypatch.setattr(db, "pg_url", lambda: None)
    monkeypatch.setattr(db_pg, "evict", lambda url: pytest.fail("evicted"))
    with join_api._db_slot():
        pass


# ------------------------------------------------------------ the unit

def _unit_code() -> list[str]:
    return [ln for ln in UNIT.read_text(encoding="ascii").splitlines() if ln.strip() and not ln.startswith("#")]


def test_the_unit_runs_the_endpoint_as_org_join_not_secretary():
    (exec_start,) = [ln for ln in _unit_code() if ln.startswith("ExecStart=")]
    assert "/usr/bin/setpriv --reuid=org-join --regid=org-join --init-groups" in exec_start
    assert "secretary" not in " ".join(_unit_code())
    # runs as root by default; an explicit User= (even root) plus NoNewPrivileges and a seccomp
    # directive strips CAP_SETUID and setpriv cannot drop (Contabo 2026-10-01)
    assert not any(ln.startswith("User=") for ln in _unit_code())


def test_the_unit_injects_only_the_org_join_folder_never_all_of_agents_core_prod():
    (exec_start,) = [ln for ln in _unit_code() if ln.startswith("ExecStart=")]
    runs = re.findall(r"infisical_setup\.py run (\S+) (\S+)( --as \S+)?( --path \S+)? --", exec_start)
    assert runs == [("Agents-Core", "prod", " --as contabo", " --path /org-join")]
    assert exec_start.count("infisical_setup.py") == 1


def test_the_unit_is_not_enabled_at_boot_and_says_why():
    text = UNIT.read_text(encoding="ascii")
    assert "[Install]" not in _unit_code() and not any(ln.startswith("WantedBy") for ln in _unit_code())
    assert "door.sh" in text and "NOT enabled" in text


def test_the_unit_keeps_its_machine_credential_where_it_was():
    # the credential is read by the root leg only; nothing widens /etc/infisical or hands it on
    text = UNIT.read_text(encoding="ascii")
    assert "/etc/infisical/contabo.env is root 0600 and stays that way" in text
    assert not any(ln.startswith(("EnvironmentFile=", "SupplementaryGroups=", "LoadCredential=",
                                  "ReadOnlyPaths=/etc/infisical", "BindReadOnlyPaths=")) for ln in _unit_code())


# ------------------------------------------------------------ the role file

def _sql() -> str:
    return SQL.read_text(encoding="utf-8")


def _names(part: str) -> list[str]:
    return [c.strip() for c in part.replace("\n", " ").split(",") if c.strip()]


def _grant(kind: str, table: str) -> list[str]:
    m = re.search(rf"GRANT\s+{kind}\s*\(([^)]*)\)\s+ON\s+{table}\s+TO\s+org_join", _sql(), re.S | re.I)
    assert m, f"no column grant {kind} on {table}"
    return _names(m.group(1))


def _select_and_update(table: str) -> tuple[list[str], list[str]]:
    m = re.search(rf"GRANT\s+SELECT\s*\(([^)]*)\)\s*,\s*UPDATE\s*\(([^)]*)\)\s+ON\s+{table}\s+TO\s+org_join",
                  _sql(), re.S | re.I)
    assert m, f"no combined SELECT/UPDATE grant on {table}"
    return _names(m.group(1)), _names(m.group(2))


def test_the_password_is_never_in_the_file_and_comes_from_a_variable_or_the_environment():
    text = _sql()
    assert re.search(r"PASSWORD\s+:'org_join_password'", text)
    assert not re.search(r"PASSWORD\s+'", text)
    assert "ORG_JOIN_PASSWORD" in text and ":{?org_join_password}" in text
    assert "length(:'org_join_password') < 24" in text


def test_the_role_is_limited_and_carries_no_widening_attribute():
    create = re.search(r"CREATE ROLE org_join.*?;", _sql(), re.S).group(0)
    assert "LOGIN" in create and "CONNECTION LIMIT 5" in create
    for attr in ("NOSUPERUSER", "NOCREATEDB", "NOCREATEROLE", "NOREPLICATION", "NOBYPASSRLS"):
        assert attr in create
    bare = re.sub(r"\bNO(SUPERUSER|CREATEDB|CREATEROLE|REPLICATION|BYPASSRLS)\b", "", create)
    for widening in ("SUPERUSER", "CREATEDB", "CREATEROLE", "REPLICATION", "BYPASSRLS"):
        assert widening not in bare, widening


def test_every_grant_is_a_column_grant_and_nothing_is_granted_wide():
    text = re.sub(r"--.*", "", _sql())              # the header comments talk about what is NOT granted
    grants = re.findall(r"GRANT\s+(.*?)\s+TO\s+org_join", text, re.S | re.I)
    assert grants, "no grants"
    for g in grants:
        if g.upper().startswith("USAGE ON SCHEMA"):
            continue
        assert re.fullmatch(r"(SELECT|INSERT|UPDATE)\s*\([^)]*\)(\s*,\s*(SELECT|INSERT|UPDATE)\s*\([^)]*\))*\s+ON\s+\w+",
                            g, re.S), g
    assert not re.search(r"GRANT\s+ALL|ON\s+ALL\s+TABLES\s+IN\s+SCHEMA[^;]*TO\s+org_join|WITH\s+GRANT\s+OPTION",
                         text, re.I)
    assert not re.search(r"\b(DELETE|TRUNCATE|REFERENCES|TRIGGER)\b[^;]*TO\s+org_join", text, re.I)


def test_it_starts_from_nothing_so_a_grant_removed_from_the_file_is_removed_from_the_role():
    text = _sql()
    assert text.index("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM org_join") < text.index("GRANT SELECT (token_hash")


def test_the_hosts_grants_are_exactly_the_columns_hq_join_writes():
    insert_cols = _names(re.search(r"INSERT INTO hosts \(([^)]*)\)", hq_join._INSERT_HOST_SQL).group(1))
    set_part = re.search(r"SET (.*?) WHERE", hq_join._REJOIN_HOST_SQL, re.S).group(1)
    set_cols = [m.group(1) for m in re.finditer(r"(?:^|,)\s*(\w+)\s*=", set_part)]
    assert _grant("INSERT", "hosts") == insert_cols
    assert sorted(_grant("UPDATE", "hosts")) == sorted(set_cols)
    # the WHERE of the rejoin and the RETURNING of both read host and status, and nothing else:
    # no `excluded.` anywhere, because Postgres would want SELECT on every column read through it
    assert _grant("SELECT", "hosts") == ["host", "status"]
    assert "excluded" not in hq_join._INSERT_HOST_SQL.lower() + hq_join._REJOIN_HOST_SQL.lower()
    assert re.search(r"WHERE host = \? AND status = 'left' RETURNING host$", hq_join._REJOIN_HOST_SQL)
    assert hq_join._INSERT_HOST_SQL.endswith("ON CONFLICT(host) DO NOTHING RETURNING host")


def test_the_token_grants_are_what_consume_diagnose_and_sealed_read():
    assert _select_and_update("join_tokens") == (["token_hash", "host", "used_at", "expires_at"], ["used_at"])
    assert "SET used_at" in hq_join._CONSUME_SQL and "RETURNING token_hash" in hq_join._CONSUME_SQL
    for col in ("token_hash", "host", "used_at", "expires_at"):
        assert col in hq_join._CONSUME_SQL


def test_the_sealed_grants_are_what_sealed_ciphertext_reads_and_stamps():
    assert _select_and_update("node_secrets") == (["host", "ciphertext", "fetched_at", "revoked_at"], ["fetched_at"])


def test_the_event_grant_is_the_columns_log_event_inserts():
    assert _grant("INSERT", "events") == ["task_id", "actor", "kind", "payload", "ts"]
    assert "INSERT INTO events (task_id,actor,kind,payload,ts)" in inspect.getsource(db.log_event)


def test_the_file_is_ascii_and_stops_on_the_first_error():
    assert not [b for b in SQL.read_bytes() if b > 127]
    assert "\\set ON_ERROR_STOP on" in _sql()


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
    env = {k: v for k, v in os.environ.items() if k != "ORG_JOIN_PASSWORD"}
    argv = ["psql", "-X", "-v", "ON_ERROR_STOP=1"]
    if password is not None and via == "env":
        env["ORG_JOIN_PASSWORD"] = password
    if password is not None and via == "var":
        argv += ["-v", f"org_join_password={password}"]
    argv += ["-f", str(SQL), owner_url]
    return subprocess.run(argv, env=env, capture_output=True, text=True, timeout=60)


_COLUMN_GRANTS = ("SELECT string_agg(privilege_type || ':' || column_name || ':' || table_name, ' ' "
                  "ORDER BY table_name, column_name, privilege_type) AS g "
                  "FROM information_schema.column_privileges WHERE grantee = 'org_join'")


class Hub:
    def __init__(self, owner_url: str, password: str, monkeypatch):
        self.owner_url = owner_url
        self.password = password
        self.join_url = _with_login(owner_url, "org_join", password)
        self._mp = monkeypatch

    def use(self, which: str):
        """Point lib.db (and so hq_join and every server thread) at the owner or at org_join."""
        self._mp.setenv("ORG_DB_URL", self.owner_url if which == "owner" else self.join_url)

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

    def pending_host(self, host: str = "node-x"):
        self.owner_exec("INSERT INTO hosts (host, status, pubkey, updated_at) VALUES (?, ?, ?, ?)",
                        (host, hq_join.STATUS_PENDING, PUB, NOW))

    def attempt(self, sql: str, params=()) -> str:
        """Run one statement as org_join on a connection of its own: the error text, or RAN."""
        conn = db_pg.connect(self.join_url, timeout=10)
        try:
            try:
                conn.execute(sql, params)
                conn.commit()
            except Exception as exc:
                return str(exc)
            return "RAN"
        finally:
            conn.close()


@pytest.fixture
def hub(monkeypatch):
    if not ORG_TEST_DB_URL or not shutil.which("psql"):
        pytest.skip("ORG_TEST_DB_URL and psql needed")
    for var in ("ORG_JOIN_DB_URL", "JOIN_API_ALLOW_ORG_ROLE"):
        monkeypatch.delenv(var, raising=False)
    password = secrets.token_hex(16)
    _drop_all(ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    db.init()
    r = _run_role_file(ORG_TEST_DB_URL, password)
    assert r.returncode == 0, r.stderr
    h = Hub(ORG_TEST_DB_URL, password, monkeypatch)
    yield h
    db_pg.evict(h.owner_url)
    db_pg.evict(h.join_url)
    _drop_all(ORG_TEST_DB_URL)


def _wait_no_join_sessions(h: Hub, seconds: float = 3.0) -> int:
    end = time.time() + seconds
    n = -1
    while time.time() < end:
        n = h.owner_rows("SELECT count(*) AS n FROM pg_stat_activity WHERE usename = 'org_join'")[0]["n"]
        if n == 0:
            break
        time.sleep(0.05)
    return n


@pg_only
def test_accept_and_sealed_work_over_http_as_org_join_and_nothing_else_is_granted(hub):
    hub.use("owner")
    token = hq_join.mint("node-a")["token"]
    hub.use("join")
    api = Api()
    try:
        status, body = api.post("accept", _accept_body(token, "node-a"))
        assert (status, json.loads(body)) == (200, {"host": "node-a", "status": "pending_identity"})
        status, body = api.post("sealed", {"host": "node-a", "token": token})
        assert (status, json.loads(body)) == (202, {"status": "pending"})
        # what W4.2 provision leaves behind, written as the owner (provision is not the endpoint's job)
        hub.owner_exec("INSERT INTO node_secrets (host, ciphertext, infisical_client_secret_id, created_at) "
                       "VALUES (?, ?, ?, ?)", ("node-a", CIPHER, "secret-id-1", NOW))
        hub.owner_exec("UPDATE hosts SET status = ? WHERE host = ?", (hq_join.STATUS_READY, "node-a"))
        status, body = api.post("sealed", {"host": "node-a", "token": token})
        assert (status, json.loads(body)) == (200, {"status": "ready", "ciphertext": CIPHER})
        assert api.post("sealed", {"host": "node-a", "token": token})[0] == 200     # a second poll
        assert api.post("sealed", {"host": "node-a", "token": "hqj_" + "x" * 43})[0] == 403
    finally:
        api.close()
    row = hub.owner_rows("SELECT status, approved_at, pubkey FROM hosts WHERE host = ?", ("node-a",))[0]
    assert row["status"] == hq_join.STATUS_READY and row["approved_at"] is None and row["pubkey"] == PUB
    assert hub.owner_rows("SELECT fetched_at FROM node_secrets WHERE host = ?", ("node-a",))[0]["fetched_at"]
    kinds = [r["kind"] for r in hub.owner_rows("SELECT kind FROM events ORDER BY id")]
    assert kinds == ["join_mint", "join_accept", "node_sealed_fetch"]


@pg_only
def test_a_rejoin_of_a_host_that_left_works_as_org_join(hub):
    hub.use("owner")
    first = hq_join.mint("node-a")["token"]
    hub.use("join")
    hq_join.accept(first, "node-a", "linux", "/opt/MoonieXHQ", PUB)
    hub.owner_exec("UPDATE hosts SET status = ?, approved_at = ? WHERE host = ?",
                   (hq_join.STATUS_LEFT, NOW, "node-a"))
    hub.use("owner")
    second = hq_join.mint("node-a")["token"]
    hub.use("join")
    assert hq_join.accept(second, "node-a", "linux", "/opt/MoonieXHQ", PUB)["status"] == hq_join.STATUS_PENDING
    row = hub.owner_rows("SELECT status, approved_at FROM hosts WHERE host = ?", ("node-a",))[0]
    assert row["status"] == hq_join.STATUS_PENDING and row["approved_at"] is None     # the old approval is gone


@pg_only
def test_a_host_that_is_not_left_cannot_be_taken_over_and_the_token_is_not_burned(hub):
    hub.use("owner")
    first = hq_join.mint("node-a")["token"]
    hub.use("join")
    hq_join.accept(first, "node-a", "linux", "/opt/MoonieXHQ", PUB)
    # hq_join.mint refuses a taken host, so the second token is a row written as the owner
    token = "hqj_" + "y" * 43
    hub.owner_exec("INSERT INTO join_tokens (token_hash, host, created_at, expires_at) VALUES (?, ?, ?, ?)",
                   (hq_join.hash_token(token), "node-a", NOW, "2999-01-01T00:00:00+00:00"))
    with pytest.raises(hq_join.JoinError) as ei:
        hq_join.accept(token, "node-a", "linux", "/opt/MoonieXHQ", PUB)
    assert ei.value.code == "host_in_use"
    used = hub.owner_rows("SELECT used_at FROM join_tokens WHERE token_hash = ?", (hq_join.hash_token(token),))
    assert used[0]["used_at"] is None


@pg_only
def test_sequential_requests_leave_no_org_join_connection_behind(hub):
    hub.use("owner")
    tokens = [hq_join.mint(f"node-{i}")["token"] for i in range(3)]
    hub.use("join")
    api = Api()
    try:
        for i, tok in enumerate(tokens):
            assert api.post("accept", _accept_body(tok, f"node-{i}"))[0] == 200
            assert api.post("sealed", {"host": f"node-{i}", "token": tok})[0] == 202
        assert api.post("accept", _accept_body("hqj_" + "z" * 43, "node-9"))[0] == 403
    finally:
        api.close()
    assert _wait_no_join_sessions(hub) == 0


@pg_only
@pytest.mark.parametrize("sql,expect", [
    ("SELECT id FROM tasks LIMIT 1", "permission denied for table tasks"),
    ("SELECT * FROM letters", "permission denied for table letters"),
    ("SELECT pubkey FROM hosts", "permission denied for table hosts"),
    ("SELECT deploy_pubkey FROM hosts", "permission denied for table hosts"),
    ("SELECT approved_at FROM hosts", "permission denied for table hosts"),
    ("SELECT created_at FROM join_tokens", "permission denied for table join_tokens"),
    ("SELECT infisical_client_secret_id FROM node_secrets", "permission denied for table node_secrets"),
    ("SELECT payload FROM events", "permission denied for table events"),
    ("SELECT * FROM c_level_sessions", "permission denied for table c_level_sessions"),
    ("DELETE FROM hosts", "permission denied for table hosts"),
    ("DELETE FROM join_tokens", "permission denied for table join_tokens"),
    ("DELETE FROM events", "permission denied for table events"),
    ("TRUNCATE hosts", "permission denied for table hosts"),
    ("UPDATE node_secrets SET ciphertext = 'x'", "permission denied for table node_secrets"),
    ("UPDATE join_tokens SET expires_at = '2999-01-01'", "permission denied for table join_tokens"),
    ("INSERT INTO join_tokens (token_hash, host, created_at, expires_at) VALUES ('h','n','a','b')",
     "permission denied for table join_tokens"),
    ("INSERT INTO node_secrets (host, created_at) VALUES ('n','a')", "permission denied for table node_secrets"),
    ("INSERT INTO tasks (id) VALUES ('t')", "permission denied for table tasks"),
    ("CREATE TABLE evil (x int)", "permission denied for schema public"),
    ("CREATE ROLE evil", "permission denied to create role"),
    ("DROP TABLE hosts", "must be owner of table hosts"),
    ("ALTER TABLE hosts DISABLE TRIGGER ALL", "must be owner of table hosts"),
    ("DROP TRIGGER org_join_guard ON hosts", "must be owner of relation hosts"),
    # approved_at can be reset by an UPDATE (a rejoin) but never set on a new row: no INSERT grant
    ("INSERT INTO hosts (host, status, pubkey, updated_at, approved_at) "
     "VALUES ('node-y', 'pending_identity', 'k', 'n', 'a')", "permission denied for table hosts"),
    ("COPY hosts TO PROGRAM 'true'", "permission denied"),
])
def test_org_join_cannot_do_anything_the_endpoint_does_not_do(hub, sql, expect):
    hub.pending_host()
    out = hub.attempt(sql)
    assert out != "RAN", sql
    assert expect in out, out
    assert hub.password not in out


GUARD_EVENT = "org_join may only write the join_accept and node_sealed_fetch events"
GUARD_REGISTER = "org_join may only register a host as pending_identity"


@pg_only
@pytest.mark.parametrize("sql,params,expect", [
    # approving its own node: the F1 gate
    ("UPDATE hosts SET approved_at = ? WHERE host = ?", (NOW, "node-x"), "org_join may only"),
    # rewriting the key of a host that is not `left`
    ("UPDATE hosts SET pubkey = ? WHERE host = ?", ("age1" + "q" * 58, "node-x"),
     "org_join may only take over a host that has left"),
    ("UPDATE hosts SET status = 'identity_ready' WHERE host = ?", ("node-x",), "org_join may only"),
    # registering a host that is already approved or not pending
    ("INSERT INTO hosts (host, status, pubkey, updated_at) VALUES (?, 'identity_ready', 'k', 'n')", ("node-y",),
     GUARD_REGISTER),
    # an event that is not one of the two the endpoint writes
    ("INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'hq_join', 'join_approve', '{}', 'n')",
     (), GUARD_EVENT),
    ("INSERT INTO events (task_id, actor, kind, payload, ts) VALUES (NULL, 'cto', 'join_accept', '{}', 'n')",
     (), GUARD_EVENT),
    ("INSERT INTO events (task_id, actor, kind, payload, ts) VALUES ('t1', 'hq_join', 'join_accept', '{}', 'n')",
     (), GUARD_EVENT),
])
def test_the_row_guards_stop_what_a_column_grant_cannot(hub, sql, params, expect):
    hub.pending_host()
    out = hub.attempt(sql, params)
    assert out != "RAN", sql
    assert expect in out, out
    assert hub.owner_rows("SELECT approved_at, status, pubkey FROM hosts WHERE host = ?", ("node-x",))[0] == {
        "approved_at": None, "status": hq_join.STATUS_PENDING, "pubkey": PUB}


@pg_only
def test_the_guards_do_nothing_for_any_other_role(hub):
    # the owner, and so `hq_join approve` run as the full role, is not slowed down by them
    hub.use("owner")
    token = hq_join.mint("node-a")["token"]
    hub.use("join")
    hq_join.accept(token, "node-a", "linux", "/opt/MoonieXHQ", PUB)
    hub.use("owner")
    assert hq_join.approve("node-a", hq_join.fingerprint(PUB))["changed"] is True
    assert hub.owner_rows("SELECT approved_at FROM hosts WHERE host = ?", ("node-a",))[0]["approved_at"]
    assert "join_approve" in [r["kind"] for r in hub.owner_rows("SELECT kind FROM events")]


@pg_only
def test_the_role_allows_five_connections_and_no_sixth(hub):
    conns = []
    try:
        for _ in range(5):
            conns.append(db_pg.connect(hub.join_url, timeout=10))
        with pytest.raises(db_pg.HubConnectError) as ei:
            db_pg.connect(hub.join_url, timeout=10)
        assert "too many connections for role" in str(ei.value)
    finally:
        for c in conns:
            c.close()


@pg_only
def test_the_role_times_out_a_stuck_statement_and_a_stuck_transaction(hub):
    rows = hub.owner_rows("SELECT unnest(rolconfig) AS c FROM pg_roles WHERE rolname = 'org_join' ORDER BY 1")
    assert [r["c"] for r in rows] == ["idle_in_transaction_session_timeout=15s", "statement_timeout=10s"]


@pg_only
def test_the_file_runs_twice_and_leaves_the_same_role(hub):
    before = hub.owner_rows(_COLUMN_GRANTS)
    r = _run_role_file(hub.owner_url, hub.password)
    assert r.returncode == 0, r.stderr
    assert "role and grants are in place and verified" in r.stdout
    assert hub.owner_rows(_COLUMN_GRANTS) == before and before[0]["g"]


@pg_only
def test_the_password_can_be_given_as_a_psql_variable_and_rotates(hub):
    before = hub.owner_rows("SELECT rolpassword AS p FROM pg_authid WHERE rolname = 'org_join'")
    new = secrets.token_hex(16)
    r = _run_role_file(hub.owner_url, new, via="var")
    assert r.returncode == 0, r.stderr
    assert new not in r.stdout + r.stderr
    after = hub.owner_rows("SELECT rolpassword AS p FROM pg_authid WHERE rolname = 'org_join'")
    assert after != before                     # a fresh SCRAM verifier; the password itself is not readable


@pg_only
@pytest.mark.parametrize("password", [None, "", "short-password", "x" * 23])
def test_the_file_refuses_a_missing_or_short_password_and_changes_nothing(hub, password):
    before = hub.owner_rows("SELECT rolpassword AS p FROM pg_authid WHERE rolname = 'org_join'")
    r = _run_role_file(hub.owner_url, password)
    assert r.returncode != 0
    assert "missing or shorter than 24 characters" in r.stderr
    assert "verified" not in r.stdout
    if password:
        assert password not in r.stdout + r.stderr
    assert hub.owner_rows("SELECT rolpassword AS p FROM pg_authid WHERE rolname = 'org_join'") == before


@pg_only
def test_a_grant_added_by_hand_is_removed_by_the_next_run(hub):
    hub.owner_exec("GRANT DELETE ON hosts TO org_join")
    hub.owner_exec("GRANT SELECT ON tasks TO org_join")
    assert hub.attempt("SELECT id FROM tasks LIMIT 1") == "RAN"
    r = _run_role_file(hub.owner_url, hub.password)
    assert r.returncode == 0, r.stderr
    assert "permission denied" in hub.attempt("SELECT id FROM tasks LIMIT 1")
    assert "permission denied" in hub.attempt("DELETE FROM hosts")


@pg_only
def test_the_self_check_fails_the_run_when_the_role_has_drifted_past_what_the_file_can_fix(hub):
    hub.owner_exec("ALTER ROLE org_join CREATEDB")
    try:
        r = _run_role_file(hub.owner_url, hub.password)
        assert r.returncode != 0
        assert "role attribute it must not have" in r.stderr
        assert "verified" not in r.stdout
    finally:
        hub.owner_exec("ALTER ROLE org_join NOCREATEDB")
    assert _run_role_file(hub.owner_url, hub.password).returncode == 0


# ------------------------------------------------------------ deploy/join/org_join_role.py

import importlib.util  # noqa: E402

_SCRIPT = ROOT / "deploy" / "join" / "org_join_role.py"
_spec = importlib.util.spec_from_file_location("org_join_role_script", _SCRIPT)
role_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(role_script)

_ADMIN = "postgresql://org:Ad%40min-pw-0123456789@db.example.internal:5433/hub?sslmode=require"

_SHIM = """#!/bin/sh
# records what psql was started with; never prints the password unless SHIM_ECHO=1
{ for a in "$@"; do printf 'ARG %s\\n' "$a"; done; env | grep -E '^(PG|ORG_JOIN_PASSWORD)' | sort; } > "$SHIM_LOG"
[ "${SHIM_ECHO:-}" = 1 ] && echo "ERROR: syntax error near PASSWORD '$ORG_JOIN_PASSWORD'" >&2
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
    password = env["ORG_JOIN_PASSWORD"]
    assert len(password) >= 24 and re.fullmatch(r"[A-Za-z0-9_-]+", password)
    assert out == f"postgresql://org_join:{password}@db.example.internal:5433/hub?sslmode=require\n"
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
        seen.add(_recorded(shim)[1]["ORG_JOIN_PASSWORD"])
    assert len(seen) == 3


def test_a_failing_psql_leaves_stdout_empty_so_put_stores_nothing(shim, capsys, monkeypatch):
    monkeypatch.setenv("SHIM_RC", "3")
    monkeypatch.setenv("SHIM_ECHO", "1")
    rc = role_script.main([], {**os.environ, "ORG_DB_URL": _ADMIN})
    out, err = capsys.readouterr()
    password = _recorded(shim)[1]["ORG_JOIN_PASSWORD"]
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
    assert role_script.role_url(parts, "abc") == "postgresql://org_join:abc@[::1]:5432/hub"


@pg_only
def test_the_role_script_against_a_real_postgres_makes_a_working_role(monkeypatch, capsys):
    for var in ("ORG_JOIN_DB_URL", "JOIN_API_ALLOW_ORG_ROLE", "ORG_JOIN_PSQL"):
        monkeypatch.delenv(var, raising=False)
    _drop_all(ORG_TEST_DB_URL)
    monkeypatch.setenv("ORG_DB_URL", ORG_TEST_DB_URL)
    db.init()
    capsys.readouterr()                                                  # db.init() prints a line
    try:
        assert role_script.main([], {**os.environ, "ORG_DB_URL": ORG_TEST_DB_URL}) == 0
        out, err = capsys.readouterr()
        url = out.strip()
        assert out.count("\n") == 1 and urlsplit(url).username == "org_join"
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

"""Org Mesh W4.2b: `python -m tools.join_api --check-db`, the drill's gap-7 preflight.

Run 4 (RUN-20261003-1420-fe8f) found a stale ORG_JOIN_DB_URL only as an HTTP 500 at /accept, after
the door was open. The drill now logs in with that DSN first, through db_pg.connect: lib.db.get_conn
WARNS and falls back to a read-only snapshot when the hub refuses the login, so a check through it
passes on a DSN that cannot log in. A role that logs in but cannot read `join_tokens`, `hosts` and
`node_secrets` is refused too.

Nothing here reaches a real network: the connector is a fake, or a real psycopg connect to a closed
loopback port. The DSN's password is a marker the tests look for in everything that was printed.

Run:  .venv/bin/python -m pytest -p no:warnings tests/test_w42b_join_check_db.py
"""
from __future__ import annotations

import pytest

from lib import db, db_pg
from tools import join_api

PASSWORD = "pw-MARKER-never-printed-0123"
DSN = f"postgresql://org_join:{PASSWORD}@hub.example:5432/org"


class _Conn:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, *args):
        self.log.append(sql)
        return self

    def close(self):
        self.log.append("close")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in ("ORG_JOIN_DB_URL", "JOIN_API_ALLOW_ORG_ROLE"):
        monkeypatch.delenv(var, raising=False)
    # lib.db must never be the connector: its fallback hides a refused login
    monkeypatch.setattr(db, "get_conn", lambda *a, **k: pytest.fail("lib.db.get_conn was used"))


def test_a_dsn_that_logs_in_runs_select_1_then_the_start_up_read_then_closes(monkeypatch, capsys):
    log: list[str] = []
    monkeypatch.setattr(db_pg, "connect", lambda url, timeout=None: _Conn(log))
    assert join_api.check_db({"ORG_JOIN_DB_URL": DSN}) == 0
    assert log == ["SELECT 1", *[f"SELECT 1 FROM {t} LIMIT 1" for t in ("join_tokens", "hosts", "node_secrets")],
                   "close"]
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_the_connection_is_made_with_the_join_dsn_not_the_org_role(monkeypatch):
    seen = []
    monkeypatch.setattr(db_pg, "connect", lambda url, timeout=None: seen.append(url) or _Conn([]))
    env = {"ORG_JOIN_DB_URL": DSN, "ORG_DB_URL": "postgresql://org:placeholder@hub.example:5432/org"}
    assert join_api.check_db(env) == 0
    assert seen == [DSN]


def test_a_dsn_that_cannot_log_in_exits_1_naming_the_class_and_never_the_dsn(monkeypatch, capsys):
    def refuse(url, timeout=None):
        raise RuntimeError(f'FATAL: password authentication failed for user "org_join" ({url})')
    monkeypatch.setattr(db_pg, "connect", refuse)
    assert join_api.check_db({"ORG_JOIN_DB_URL": DSN}) == 1
    err = capsys.readouterr().err
    assert "RuntimeError" in err and "ORG_JOIN_DB_URL" in err
    assert PASSWORD not in err and "hub.example" not in err and "authentication" not in err


def test_a_role_that_logs_in_but_cannot_read_the_join_tables_is_refused_and_still_closes(monkeypatch, capsys):
    log: list[str] = []

    class NoGrant(_Conn):
        def execute(self, sql, *args):
            if "FROM node_secrets" in sql:
                raise PermissionError(f"permission denied for table node_secrets ({DSN})")
            return super().execute(sql, *args)
    monkeypatch.setattr(db_pg, "connect", lambda url, timeout=None: NoGrant(log))
    assert join_api.check_db({"ORG_JOIN_DB_URL": DSN}) == 1
    err = capsys.readouterr().err
    assert "PermissionError" in err and PASSWORD not in err and log[-1] == "close"


def test_the_real_driver_against_a_closed_port_exits_1_and_never_falls_back_to_a_snapshot(capsys):
    pytest.importorskip("psycopg")
    assert join_api.check_db({"ORG_JOIN_DB_URL": f"postgresql://org_join:{PASSWORD}@127.0.0.1:1/org"}) == 1
    out = capsys.readouterr()
    assert "HubConnectError" in out.err and PASSWORD not in out.err and "127.0.0.1" not in out.err
    assert "snapshot" not in out.err and out.out == ""


def test_no_join_dsn_and_no_permission_to_use_the_org_role_exits_2(capsys):
    assert join_api.check_db({"ORG_DB_URL": "postgresql://org:placeholder@hub.example/org"}) == 2
    assert "JOIN_API_ALLOW_ORG_ROLE" in capsys.readouterr().err
    assert join_api.check_db({}) == 2
    assert "ORG_JOIN_DB_URL is not set" in capsys.readouterr().err


def test_main_takes_the_flag_and_starts_no_server_and_checks_no_bind(monkeypatch):
    monkeypatch.setattr(db_pg, "connect", lambda url, timeout=None: _Conn([]))
    monkeypatch.setenv("ORG_JOIN_DB_URL", DSN)
    monkeypatch.setattr(join_api, "make_server", lambda *a, **k: pytest.fail("a server was built"))
    monkeypatch.setattr(join_api, "check_bind", lambda *a, **k: pytest.fail("the bind was checked"))
    assert join_api.main(["--check-db"]) == 0

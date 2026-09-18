"""Root pytest conftest.

Autouse pin for tools.tmux_session.tmux_bin() (task-83ec62b6). tmux_bin() now
resolves argv[0] to an absolute path when it can find one (e.g.
/opt/homebrew/bin/tmux), but a long list of existing tests across
scripts/test_relay_mcp_server.py, scripts/test_cxo_crosstalk.py and
scripts/test_terminal_restart.py assert exact argv (or key a fake-subprocess
dispatch dict) against the literal "tmux". Pinning TMUX_BIN=tmux for every
test -- and resetting the resolver's module-level cache before and after --
keeps those assertions honest (argv[0] really does go through tmux_bin(),
nothing is hardcoded in the tests) without rewriting each one individually.

Tests that exercise tmux_bin()'s own resolution logic (scripts/test_tmux_
session.py) override this pin locally with their own monkeypatch calls,
which layer on top of this fixture within the same test's monkeypatch stack.
"""
from __future__ import annotations

import pytest

from tools import tmux_session


@pytest.fixture(autouse=True)
def _pin_tmux_bin(monkeypatch):
    monkeypatch.setenv("TMUX_BIN", "tmux")
    tmux_session._reset_tmux_bin_cache()
    yield
    tmux_session._reset_tmux_bin_cache()


@pytest.fixture(autouse=True)
def _clean_session_env(monkeypatch):
    """Strip C-level session identity out of every test's environment
    (task-78586938). pytest inherits whatever shell it was launched from --
    a C-level session's own CTO_SESSION_ID/CXO_* vars leak in, and
    lib.db.create_task's charter gate then raises "session (cto, <id>) has
    no charter set" for any test that creates a task without first
    monkeypatching these itself (5 real failures in
    scripts/test_watchdog_remote_heartbeat.py, verified reproducible only
    with these vars set).

    ORG_DB_URL is cleared for the same reason ADR 0021 exists: after the
    Postgres cutover the Mac's shell will carry it, and a test must never
    reach the real hub. ORG_TEST_DB_URL is left alone -- it's how
    tests/test_db_backend_pg.py opts INTO a (local, scratch) Postgres.

    A test that deliberately needs one of these set (e.g.
    test_charter_gate_blocks_then_passes) does its own monkeypatch.setenv
    after this fixture runs, which layers on top within the same test's
    monkeypatch stack -- same pattern as _pin_tmux_bin above.
    """
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "CTO_SESSION", "CXO_SESSION", "ORG_DB_URL"):
        monkeypatch.delenv(var, raising=False)

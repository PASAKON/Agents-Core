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

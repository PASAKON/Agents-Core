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
from tools import workdir as _workdir


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
    # WORK_DIR / WORKER_CTO_ID / WORK_EXPECT_GB (ADR 0030): delegate exports
    # them into every worker's shell, and flow_shoot / gen_loop / the
    # media-guard hook change behaviour when they are set — a test run from a
    # worker must not inherit them (26 runner tests failed that way,
    # 2026-09-23). Tests that need them set them with monkeypatch.
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "CTO_SESSION", "CXO_SESSION", "ORG_DB_URL",
                "WORK_DIR", "WORKER_CTO_ID", "WORK_EXPECT_GB"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _isolate_org_root(tmp_path, monkeypatch):
    """ADR 0021 addendum (2026-09-18): a worker's own shell exports ORG_ROOT
    pointing at the real hub checkout (runners/worker_init.py, GH #154) so
    lib.db can find state/ from inside a worktree -- which means a test run
    from a worker shell inherits that same ORG_ROOT. A subprocess-based test
    that spawns a fresh `python3 -c '...from lib import db...'` then has
    that fresh import's lib.db._resolve_root() resolve to the REAL checkout
    and write there -- measured: 29 test-proj rows + 13 events landed in the
    live Mac tasks.db this way, cleaned up by hand.

    Pinning ORG_ROOT to a per-test tmp_path here gives any subprocess a test
    spawns an isolated, nonexistent root instead -- its own fresh lib.db
    import creates state/tasks.db under tmp_path, never the real one.

    This does NOT touch this process's own already-imported `lib.db` module
    (its ROOT/DB_PATH were computed once, at first import, before any test
    ran) -- a test that calls lib.db directly still monkeypatches
    `db.DB_PATH` itself (existing convention, e.g. scripts/test_dev_message
    .py). lib/db.py's own _connect() carries the backstop for anything that
    doesn't: it refuses outright, under pytest, to open a sqlite file whose
    resolved root is a real checkout (has a `.git` entry).
    """
    monkeypatch.setenv("ORG_ROOT", str(tmp_path))


@pytest.fixture(autouse=True)
def _isolate_workdir_root(tmp_path, monkeypatch):
    """ADR 0030 / Work/RULES.md (task-36aaa3c4, iteration 1 fix): a test
    whose synthetic pilot owner passes `_storage_applies` -- e.g. tests/
    test_delegate_disk_floor.py's owner_cto="test-owner", added to the
    pilot list via its own fixture -- makes delegate_task call
    `_work_dir_for` -> `tools.workdir.create()` against the REAL
    `~/MoonieXHQ/Work/` root (config/storage-policy.yaml `work_dir.root`,
    unmocked). Measured: three real `task-<random>/{in,tmp,out}` folders
    (task-3ac4ba94, task-72526678, task-53ece1ab) appeared there from test
    runs alone -- none of those ids exist in tasks.db -- cleaned up by the
    CTO before this fixture existed.

    Pinning `tools.workdir._default_root()` to a per-test tmp_path here
    means no test anywhere, present or future, can write into the real
    Work/ tree just by exercising the pilot path -- whether or not it
    remembers to pass `root=` itself. A test that wants its OWN explicit
    root (tests/test_workdir.py, tests/test_delegate_workdir.py already
    pass `root=tmp_path` to every call) is unaffected: this only changes
    what `_default_root()` returns when nothing else overrides it, and a
    test-local `monkeypatch.setattr(workdir, "_default_root", ...)` layers
    on top within the same test's monkeypatch stack (same pattern as
    `_pin_tmux_bin` above)."""
    monkeypatch.setattr(_workdir, "_default_root", lambda: tmp_path / "Work")


# --- .env seal for EVERY test (moved here from tests/conftest.py 2026-09-22, task-3de56f59 found
# that scripts/ tests were outside the tests/ seal). tools/decide.py and lib/config.py read paid
# keys from os.environ then the gitignored .env; a test that only delenv()s them still goes LIVE.
# The reader itself is neutralised; a test ABOUT the reader opts out with @pytest.mark.allow_dotenv
# and must point it at a tmp .env. Live smoke is a CLI verb (DECIDE_LIVE=1), never pytest.
import importlib as _importlib
import pytest as _pytest

_PAID_VARS = ("OPENROUTER_API_KEY", "DECIDE_PROVIDER", "DECIDE_BUDGET_USD", "DECIDE_JEV_MODEL", "JEV_API_KEY", "JEV_API_URL")


@_pytest.fixture(autouse=True)
def _no_dotenv_no_paid_calls(request, monkeypatch):
    if request.node.get_closest_marker("allow_dotenv"):
        yield
        return
    for var in _PAID_VARS:
        monkeypatch.delenv(var, raising=False)
    for modname in ("tools.decide", "lib.config"):
        try:
            mod = _importlib.import_module(modname)
        except Exception:
            continue
        if hasattr(mod, "_read_dotenv_var"):
            monkeypatch.setattr(mod, "_read_dotenv_var", lambda name: None)
    yield


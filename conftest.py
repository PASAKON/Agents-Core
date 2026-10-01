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

import subprocess
from pathlib import Path

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
def _no_real_org_db_env(tmp_path, monkeypatch):
    """Org Mesh W1.6 (task-719e0c56): the MCP config generators
    (scripts/lib/cxo_mcp_config.py, lib/worker_mcp_config.py) route the org
    server through scripts/hub/with-org-db-env.sh when the host's node file says
    `org_db: hub` AND the hub env file exists (~/.config/mooniex/org-db.env,
    on the Mac and Contabo since before the cutover). A test that reaches
    either real file would pass on one box and fail on another. Point both
    overrides at files that do not exist; tests/test_w16_org_db_injection.py
    (and any other test that wants the wrapper) sets its own on top."""
    monkeypatch.setenv("MOONIEX_ORG_DB_ENV", str(tmp_path / "no-such-org-db.env"))
    monkeypatch.setenv("MOONIEX_NODE_YAML", str(tmp_path / "no-such-node.yaml"))


@pytest.fixture(autouse=True)
def _disk_watch_off(monkeypatch):
    """runners/watchdog.scan_once runs tools/disk_watch.check(), which on a
    full disk reclaims real worktrees and ships a letter to SomPong over ssh.
    No test may do either; tests/test_disk_watch.py turns it back on against
    injected free space, notify and reclaim."""
    monkeypatch.setenv("ORG_DISK_WATCH", "off")


@pytest.fixture(autouse=True)
def _router_off(monkeypatch):
    """delegate_task routes a NULL-runner row through tools.route, whose
    quota read is an ssh to Contabo plus the agy CLI. No test may reach
    those (task-ae42c0a7); tests/test_delegate_router.py re-enables it
    against a mocked pick_runner."""
    monkeypatch.setenv("ORG_ROUTER", "off")


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
def _isolate_trash_root(tmp_path, monkeypatch):
    """The HQ migration scripts "delete" by moving into TRASH_ROOT (default
    ~/.Trash). scripts/test_hq_migrate_step4a.py never overrode it, so every
    full run parked a hq-step4a-<ts>/ folder in the CEO's real Trash (258 of
    them by 2026-09-23 19:00) and two runs in one second collided on CI
    ("Destination path ... already exists"). Every test — and every script a
    test spawns with os.environ — now trashes into tmp_path."""
    monkeypatch.setenv("TRASH_ROOT", str(tmp_path / "Trash"))


@pytest.fixture(autouse=True)
def _isolate_storage_state(tmp_path, monkeypatch):
    """ADR 0030 state files that tests reach through delegate/watchdog paths:
    the disk-spawn queue (a refused spawn in tests/test_delegate_disk_floor.py
    enqueued real entries), the reclaim ledger and the Work watcher's state.
    Point all three at tmp_path so no test writes org state."""
    import importlib
    for mod, attr, name in (("tools.disk_queue", "QUEUE_PATH", "disk_queue.jsonl"),
                            ("tools.storage_reclaim", "LEDGER_PATH", "reclaim.jsonl"),
                            ("tools.work_watch", "STATE_PATH", "work_watch_state.json")):
        try:
            m = importlib.import_module(mod)
        except ImportError:
            continue
        monkeypatch.setattr(m, attr, tmp_path / "state" / name)


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


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} in {repo} failed: {r.stderr}")
    return r.stdout.strip()


@pytest.fixture
def fake_projects(tmp_path, monkeypatch):
    """A bare 'origin' repo + a clone standing in for a runtime checkout,
    wired into lib.config's project registry (Org Mesh W0.2, ADR 0021 —
    tmp_path only, never the real repo/origin/tasks.db).

    tools/git_ops.py, tools/revert_task.py, tools/rollback.py and
    lib/org_tools_registry.py all resolve a project via `get_project`,
    which in turn calls the module-level `projects()` in lib.config —
    patching that one function here covers every one of those modules
    for a test, without a separate monkeypatch per module (the older
    per-file `monkeypatch.setattr(git_ops, "get_project", ...)` pattern
    only ever covered tools.git_ops's own namespace).

    Returns a dict: `origin` (bare repo path), `runtime` (the clone
    standing in for this host's runtime checkout — same repo
    `_create_temp_worktree` will add its throwaway worktrees to), `proj`
    (the fake project dict), and `git(*args)` (run git in `runtime`).
    """
    from lib import config as config_module

    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "--initial-branch=main", str(origin))

    seed = tmp_path / "seed"
    _git(tmp_path, "clone", "-q", str(origin), str(seed))
    _git(seed, "config", "user.email", "test@example.com")
    _git(seed, "config", "user.name", "Test")
    (seed / "README.md").write_text("seed\n")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-q", "-m", "initial")
    _git(seed, "push", "-q", "origin", "main")

    runtime = tmp_path / "runtime"
    _git(tmp_path, "clone", "-q", str(origin), str(runtime))
    _git(runtime, "config", "user.email", "test@example.com")
    _git(runtime, "config", "user.name", "Test")

    host = config_module.self_host()
    proj = {
        "key": "test-project",
        "path": str(runtime),
        "paths": {host: str(runtime)},
        "default_branch": "main",
        "remote": str(origin),
        "auto_push": False,
    }
    monkeypatch.setattr(config_module, "projects", lambda: {"test-project": proj})

    return {"origin": origin, "runtime": runtime, "proj": proj,
            "git": lambda *args: _git(runtime, *args)}


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


@pytest.fixture
def pinned_mac_host(monkeypatch, tmp_path):
    """Make self_host() answer 'mac' from EVERY source, whatever box or env runs the suite.

    A test that asserts "this is the Mac" must not depend on the machine it
    runs on (Contabo, winbox) or on ORG_HOST / ~/.config/mooniex/node.yaml
    being unset. The four sources of lib.config.self_host() are pinned in
    resolution order: ORG_HOST unset, no node.yaml, ROOT = the Mac's
    agents_root, platform = Darwin. self_host() is lru_cached, so the cache
    is cleared on both sides of the test (task-6f6e5179).
    """
    from types import SimpleNamespace

    from lib import config

    mac_root = Path(config.hosts()["mac"]["agents_root"])
    monkeypatch.delenv("ORG_HOST", raising=False)
    monkeypatch.setattr(config, "NODE_CONFIG_PATH", tmp_path / "no-node.yaml")
    monkeypatch.setattr(config, "ROOT", mac_root)
    monkeypatch.setattr(config, "platform", SimpleNamespace(system=lambda: "Darwin"))
    config.self_host.cache_clear()
    yield "mac"
    config.self_host.cache_clear()


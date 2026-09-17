"""GH #153 (task task-e40fc5a1): spawn-worker.ps1's own probe verdict --
`GITHUB_SSH_ROUTE=unreachable` / `SPAWN_REFUSED=<reason>` -- must actually
GATE `tools.delegate._spawn_remote`'s success, not just get logged. Before
this task, a returncode==0 + a valid pid on the last stdout line always read
as a clean spawn even when the probe had already said the git route was
dead; `success("remote DEV spawned")` printed regardless.

windows/spawn-worker.ps1 itself is the paired multi-host task's file (not
touched here) -- these tests mock its stdout/returncode entirely (via
`delegate.subprocess.run`), no real ssh/network/winbox.

Run via:  pytest tests/test_delegate_probe_gate.py
(same convention as tests/test_multihost.py -- not in pytest.ini's default
testpaths; run explicitly alongside the default `pytest` run.)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.delegate as delegate  # noqa: E402


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    # owner_cto="test-owner" below is synthetic with no c_level_sessions row.
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


class _Result:
    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_fake_run(main_stdout: str, main_returncode: int = 0):
    """Fake `subprocess.run` covering every ssh/scp call `_spawn_remote`
    can make once `_ensure_remote_deploy` is stubbed out (see `patched`
    fixture below): the TASK.md `scp`, the main `ssh ... spawn-worker.ps1`
    call (controlled by this test), and a `taskkill` kill call if the
    unreachable-route branch issues one. Records every call's argv."""
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "osascript":
            # lib.notify's mac desktop-notification call -- delegate.subprocess
            # IS the process-wide `subprocess` module, so monkeypatching its
            # `.run` here also intercepts notify's, unrelated to this test.
            return _Result(0)
        if cmd[0] == "scp":
            return _Result(0)
        if cmd[0] == "ssh" and len(cmd) >= 3 and cmd[2] == "taskkill":
            return _Result(0)
        if cmd[0] == "ssh":
            return _Result(main_returncode, main_stdout,
                           "" if main_returncode == 0 else "boom")
        raise AssertionError(f"unexpected subprocess call: {cmd}")

    return fake_run, calls


@pytest.fixture()
def patched(monkeypatch):
    """Skip the real deploy-check (its own ssh/scp calls) -- out of scope
    for the probe-gate itself, already covered by test_multihost.py's
    dry-run deploy tests."""
    monkeypatch.setattr(delegate, "_ensure_remote_deploy", lambda *a, **k: [])


def _new_task(db_mod_) -> str:
    return db_mod_.create_task(
        project="mooniex-agents", role="developer",
        title="probe gate test", description="d",
        owner_cto="test-owner", host="winbox",
        touches=["tools/probe_gate_test_marker.py"],
    )


def _lock_count(db_mod_, task_id: str) -> int:
    with db_mod_.get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM locks WHERE owner=?", (task_id,),
        ).fetchone()[0]


# ---------------------------------------------------------------------------
# GITHUB_SSH_ROUTE=unreachable
# ---------------------------------------------------------------------------

def test_unreachable_route_sets_blocked_host_and_releases_lock(temp_db, patched, monkeypatch):
    fake_run, calls = _make_fake_run(
        "GITHUB_SSH_ROUTE=unreachable (both port 22 and 443 probes failed)\n",
        main_returncode=1,
    )
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = _new_task(temp_db)
    assert _lock_count(temp_db, tid) == 0  # not locked until delegate_task runs

    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))

    assert result["status"] == "blocked_host"
    assert "unreachable" in result["delegate_log"]
    assert "git route from winbox dead" in result["delegate_log"]
    assert _lock_count(temp_db, tid) == 0  # lock released, not left held
    assert not any(c[0] == "ssh" and len(c) >= 3 and c[2] == "taskkill" for c in calls)


def test_unreachable_route_kills_leaked_worker_pid(temp_db, patched, monkeypatch):
    """Current spawn-worker.ps1 never exits early on an unreachable route --
    it can still print a valid pid on the last line. blocked_host must fire
    AND the leaked worker must be killed via ssh taskkill."""
    fake_run, calls = _make_fake_run(
        "GITHUB_SSH_ROUTE=unreachable (both port 22 and 443 probes failed)\n42424\n",
        main_returncode=0,
    )
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = _new_task(temp_db)

    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))

    assert result["status"] == "blocked_host"
    assert "killed leaked pid 42424" in result["delegate_log"]
    assert _lock_count(temp_db, tid) == 0
    kill_calls = [c for c in calls if c[0] == "ssh" and len(c) >= 3 and c[2] == "taskkill"]
    assert len(kill_calls) == 1
    assert "42424" in kill_calls[0]


# ---------------------------------------------------------------------------
# SPAWN_REFUSED=<reason>
# ---------------------------------------------------------------------------

def test_spawn_refused_sets_conflict_and_keeps_lock(temp_db, patched, monkeypatch):
    fake_run, calls = _make_fake_run(
        "GITHUB_SSH_ROUTE=github.com:22\n"
        "SPAWN_REFUSED=worktree dirty: uncommitted changes present\n",
        main_returncode=1,
    )
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = _new_task(temp_db)

    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))

    assert result["status"] == "conflict"
    assert "worktree dirty: uncommitted changes present" in result["delegate_log"]
    # 'conflict' is an ACTIVE status (db.ACTIVE_STATUSES) -- lock stays held,
    # same as every other pre-existing 'conflict' path in delegate_task.
    assert _lock_count(temp_db, tid) == 1


# ---------------------------------------------------------------------------
# Regression: the ordinary success path is unchanged.
# ---------------------------------------------------------------------------

def test_normal_spawn_still_reaches_in_progress(temp_db, patched, monkeypatch):
    fake_run, calls = _make_fake_run(
        "GITHUB_SSH_ROUTE=github.com:22\n7777\n", main_returncode=0,
    )
    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    tid = _new_task(temp_db)

    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))

    assert result["status"] == "in_progress"
    assert result["pid"] == 7777
    assert _lock_count(temp_db, tid) == 1  # still held -- task is active

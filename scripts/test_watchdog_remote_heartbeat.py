"""Unit tests for runners/watchdog.py's HEARTBEAT-based remote stall check
(GH #152) — no real ssh, no real winbox; `remote_pid_alive` and
`read_remote_heartbeat` are monkeypatched.

Run via: pytest scripts/test_watchdog_remote_heartbeat.py
"""
from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402

# Never touch the live task DB — same guard pattern as scripts/test_watchdog_reap.py.
_LIVE_DB = (ROOT / "state" / "tasks.db").resolve()
if Path(db_mod.DB_PATH).resolve() == _LIVE_DB:
    db_mod.DB_PATH = Path(tempfile.mkdtemp(prefix="test-db-guard-")) / "tasks.db"
    db_mod.init()


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_task(monkeypatch, tmp_path, **overrides) -> dict:
    db_path = tmp_path / "tasks.db"
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init()
    task_id = db_mod.create_task(
        project="mooniex-agents", role="developer", title="t", description="d",
        owner_cto=None, host="winbox",
    )
    ts = _iso(datetime.now(timezone.utc) - timedelta(minutes=40))
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET status='in_progress', pid=?, updated_at=? WHERE id=?",
                     (4242, ts, task_id))
        conn.commit()
    task = db_mod.get_task(task_id)
    task.update(overrides)
    return task


def test_check_remote_stall_heartbeat_fresh_leaves_in_progress(monkeypatch, tmp_path):
    task = _make_task(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "get_host", lambda name: {"ssh": "winbox", "os": "windows"})
    monkeypatch.setattr(watchdog, "remote_pid_alive", lambda host_cfg, pid: True)
    fresh_ts = _iso(datetime.now(timezone.utc) - timedelta(minutes=2))
    monkeypatch.setattr(watchdog, "read_remote_heartbeat", lambda host_cfg, t: fresh_ts)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "should-not-be-called")

    result = watchdog._check_remote_stall(task, "winbox")

    assert result is None
    assert db_mod.get_task(task["id"])["status"] == "in_progress"


def test_check_remote_stall_heartbeat_old_marks_stalled(monkeypatch, tmp_path):
    task = _make_task(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "get_host", lambda name: {"ssh": "winbox", "os": "windows"})
    monkeypatch.setattr(watchdog, "remote_pid_alive", lambda host_cfg, pid: True)
    old_ts = _iso(datetime.now(timezone.utc) - timedelta(minutes=25))
    monkeypatch.setattr(watchdog, "read_remote_heartbeat", lambda host_cfg, t: old_ts)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "https://github.com/x/y/issues/9")

    result = watchdog._check_remote_stall(task, "winbox")

    assert result is not None
    assert result["pid_alive"] is True
    assert result["heartbeat_age_s"] >= 20 * 60
    t = db_mod.get_task(task["id"])
    assert t["status"] == "stalled"
    assert "heartbeat stale" in (t["delegate_log"] or "")


def test_check_remote_stall_no_heartbeat_file_does_not_decide(monkeypatch, tmp_path):
    """Old worker predating GH #152 (or one that hasn't touched a tool yet):
    missing HEARTBEAT must never be read as stale."""
    task = _make_task(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "get_host", lambda name: {"ssh": "winbox", "os": "windows"})
    monkeypatch.setattr(watchdog, "remote_pid_alive", lambda host_cfg, pid: True)
    monkeypatch.setattr(watchdog, "read_remote_heartbeat", lambda host_cfg, t: None)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "should-not-be-called")

    result = watchdog._check_remote_stall(task, "winbox")

    assert result is None
    assert db_mod.get_task(task["id"])["status"] == "in_progress"


def test_check_remote_stall_dead_pid_still_marks_stalled(monkeypatch, tmp_path):
    """Existing GAP-3 behavior (dead pid) must be unaffected by the new
    heartbeat branch — never even calls read_remote_heartbeat."""
    task = _make_task(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "get_host", lambda name: {"ssh": "winbox", "os": "windows"})
    monkeypatch.setattr(watchdog, "remote_pid_alive", lambda host_cfg, pid: False)

    def _boom(host_cfg, t):
        raise AssertionError("must not read heartbeat when pid is confirmed dead")
    monkeypatch.setattr(watchdog, "read_remote_heartbeat", _boom)
    monkeypatch.setattr(watchdog, "_file_stalled_issue", lambda t, s: "https://github.com/x/y/issues/1")

    result = watchdog._check_remote_stall(task, "winbox")

    assert result is not None
    assert result["pid_alive"] is False
    assert db_mod.get_task(task["id"])["status"] == "stalled"


def test_check_remote_stall_unreachable_host_never_acts(monkeypatch, tmp_path):
    task = _make_task(monkeypatch, tmp_path)
    monkeypatch.setattr(watchdog, "get_host", lambda name: {"ssh": "winbox", "os": "windows"})
    monkeypatch.setattr(watchdog, "remote_pid_alive", lambda host_cfg, pid: None)

    def _boom(host_cfg, t):
        raise AssertionError("must not read heartbeat when the host is unreachable")
    monkeypatch.setattr(watchdog, "read_remote_heartbeat", _boom)

    result = watchdog._check_remote_stall(task, "winbox")

    assert result is None
    assert db_mod.get_task(task["id"])["status"] == "in_progress"


def test_remote_worktree_dir_windows_slug():
    task = {"project": "mooniex-agents", "role": "browser_operator", "id": "task-abc123"}
    host_cfg = {"worktrees": r"C:\Users\UsEr\mooniex\worktrees", "os": "windows"}
    assert (watchdog._remote_worktree_dir(host_cfg, task)
            == r"C:\Users\UsEr\mooniex\worktrees\mooniex-agents__browser_operator__task-abc123")


def test_remote_worktree_dir_missing_field_returns_none():
    host_cfg = {"worktrees": r"C:\x", "os": "windows"}
    assert watchdog._remote_worktree_dir(host_cfg, {"project": "p", "role": "r"}) is None


def test_heartbeat_age_seconds_parses_z_suffix():
    ts = _iso(datetime.now(timezone.utc) - timedelta(minutes=5))
    age = watchdog._heartbeat_age_seconds(ts)
    assert age is not None
    assert 290 <= age <= 320


def test_heartbeat_age_seconds_malformed_returns_none():
    assert watchdog._heartbeat_age_seconds("not-a-timestamp") is None

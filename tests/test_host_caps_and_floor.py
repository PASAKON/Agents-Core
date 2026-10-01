"""Per-host limits that were declared but never enforced.

- winbox's disk probe: `ssh winbox df` runs through cmd.exe, which has no df,
  so the spawn floor always failed open there. Windows now probes with
  PowerShell (`Get-PSDrive`) on the drive that holds the worktrees.
- `host_floor_gb` in config/storage-policy.yaml: winbox's own 30 GB floor.
- hosts.yaml `max_workers` (CEO 2026-09-09: winbox at most 2 workers), read
  only by the off-by-default router until now.
- The watchdog's disk-queue drain gates each entry on its own host's disk.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
import tools.delegate as delegate  # noqa: E402
from tools import disk_queue  # noqa: E402


class _R:
    def __init__(self, rc=0, out=""):
        self.returncode, self.stdout, self.stderr = rc, out, ""


# --- Windows disk probe ----------------------------------------------------

def test_windows_probe_runs_powershell_on_the_worktree_drive(monkeypatch):
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return _R(0, "\r\n53687091200\r\n")  # 50 GiB

    monkeypatch.setattr(delegate.subprocess, "run", fake_run)
    got = delegate._remote_free_gb_for_host(
        {"os": "windows", "ssh": "winbox", "worktrees": r"D:\mooniex\worktrees"})
    assert got == pytest.approx(50.0)
    assert seen["cmd"][:2] == ["ssh", "winbox"]
    assert "Get-PSDrive -Name D" in seen["cmd"][2]


@pytest.mark.parametrize("out,rc", [("", 0), ("not a number\n", 0), ("123\n", 1)])
def test_windows_probe_fails_open(monkeypatch, out, rc):
    monkeypatch.setattr(delegate.subprocess, "run", lambda cmd, **kw: _R(rc, out))
    assert delegate._remote_free_gb_windows("winbox", "C") is None


def test_windows_probe_unreachable_fails_open(monkeypatch):
    def boom(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)
    monkeypatch.setattr(delegate.subprocess, "run", boom)
    assert delegate._remote_free_gb_windows("winbox", "C") is None


def test_linux_host_keeps_the_df_probe(monkeypatch):
    monkeypatch.setattr(delegate, "_remote_free_gb", lambda alias: 42.0)
    assert delegate._remote_free_gb_for_host({"os": "linux", "ssh": "mooniex-vps"}) == 42.0
    assert delegate._remote_free_gb_for_host({"os": "linux"}) is None


def test_windows_drive_letter():
    assert delegate._windows_drive(r"C:\Users\passg\mooniex\worktrees") == "C"
    assert delegate._windows_drive("e:/x") == "E"
    assert delegate._windows_drive(None) == "C"


# --- per-host floor --------------------------------------------------------

def test_host_floor_overrides_orange_for_winbox_only():
    assert delegate._disk_floor_gb_for_host("winbox") == 30.0
    assert delegate._disk_floor_gb_for_host("contabo") == delegate._disk_orange_floor_gb()
    assert delegate._disk_floor_gb_for_host(None) == delegate._disk_orange_floor_gb()


# --- max_workers -----------------------------------------------------------

@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    db_mod.init()
    return db_mod


def _task(db, host, status="pending", pid=None, updated_at=None):
    tid = db.create_task(project="mooniex-agents", role="developer", title="t",
                         description="d", owner_cto="test-owner", host=host)
    fields = {}
    if pid is not None:
        fields["pid"] = pid
    if fields:
        db.set_fields(tid, actor="cto", **fields)
    if status != "pending":
        db.update_status(tid, status, actor="cto")
    if updated_at is not None:
        with db.get_conn() as c:
            c.execute("UPDATE tasks SET updated_at=? WHERE id=?", (updated_at, tid))
    return tid


def test_live_workers_counts_remote_running_rows(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    _task(temp_db, "winbox", "in_progress", pid=111)
    _task(temp_db, "winbox", "in_progress", pid=222)
    _task(temp_db, "winbox", "stalled", pid=333)        # remote stalled: not provable
    _task(temp_db, "contabo", "in_progress", pid=444)  # other host
    assert delegate._live_workers_on("winbox") == 2
    assert delegate._live_workers_on("contabo") == 1


def test_live_workers_skips_old_pidless_rows(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
    _task(temp_db, "winbox", "in_progress", updated_at=old)   # hand claim, long ago
    _task(temp_db, "winbox", "in_progress")                   # spawn in flight
    assert delegate._live_workers_on("winbox") == 1


def test_live_workers_local_rows_need_a_live_pid(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(delegate, "pid_alive", lambda pid: pid == 1)
    _task(temp_db, "mac", "in_progress", pid=1)
    _task(temp_db, "mac", "in_progress", pid=999999)
    _task(temp_db, "mac", "stalled", pid=1)
    assert delegate._live_workers_on("mac") == 2


def test_delegate_queues_over_the_worker_cap(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "q.jsonl")
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 999.0)
    monkeypatch.setattr(delegate, "_remote_free_gb_for_host", lambda cfg: 999.0)
    monkeypatch.setattr(delegate, "_route_runner", lambda *a, **k: None)
    sent = []
    monkeypatch.setattr(delegate.send_to_cto, "send", lambda *a, **k: sent.append(a))
    _task(temp_db, "winbox", "in_progress", pid=111)
    _task(temp_db, "winbox", "in_progress", pid=222)
    tid = _task(temp_db, "winbox")
    result = asyncio.run(delegate.delegate_task(tid, host="winbox"))
    assert result["status"] == "pending"           # exempt from gc while queued
    assert disk_queue.is_queued(tid)
    assert "worker cap: 2/2" in result["delegate_log"]
    asyncio.run(delegate.delegate_task(tid, host="winbox"))
    assert len(sent) == 1, "the owner is told once, not on every retry"
    assert delegate.worker_slot_free("winbox") is False
    assert delegate.worker_slot_free("contabo") is True


def test_worker_cap_can_be_switched_off(temp_db, monkeypatch):
    monkeypatch.setattr(delegate, "self_host", lambda: "mac")
    monkeypatch.setenv("ORG_HOST_WORKER_CAP", "off")
    monkeypatch.setattr(delegate, "_free_gb", lambda path="/": 999.0)
    monkeypatch.setattr(delegate, "_remote_free_gb_for_host", lambda cfg: 999.0)
    _task(temp_db, "winbox", "in_progress", pid=111)
    _task(temp_db, "winbox", "in_progress", pid=222)
    tid = _task(temp_db, "winbox")
    result = asyncio.run(delegate.delegate_task(tid, host="winbox", dry_run=True))
    assert "worker cap" not in (result.get("delegate_log") or "")


# --- disk-queue drain is host-aware ---------------------------------------

@pytest.fixture()
def queue(monkeypatch, tmp_path):
    monkeypatch.setattr(disk_queue, "QUEUE_PATH", tmp_path / "disk_queue.jsonl", raising=False)
    monkeypatch.setattr(watchdog, "self_host", lambda: "mac")
    spawned = []

    async def fake_delegate(task_id, **kw):
        spawned.append(task_id)
    monkeypatch.setattr(watchdog.delegate, "delegate_task", fake_delegate)
    return spawned


def test_drain_waits_on_the_remote_hosts_disk_not_the_macs(temp_db, queue, monkeypatch):
    monkeypatch.setattr(watchdog.delegate, "_free_gb", lambda path="/": 999.0)
    monkeypatch.setattr(watchdog.delegate, "_remote_free_gb_for_host", lambda cfg: 10.0)
    tid = _task(temp_db, "winbox")
    disk_queue.enqueue(tid, "test-owner")
    assert watchdog._drain_disk_queue() is None      # winbox 10 GB < 30 + 1
    assert queue == []
    monkeypatch.setattr(watchdog.delegate, "_remote_free_gb_for_host", lambda cfg: 40.0)
    assert watchdog._drain_disk_queue()["task"] == tid
    assert queue == [tid]


def test_drain_spawns_a_remote_entry_while_the_mac_is_low(temp_db, queue, monkeypatch):
    monkeypatch.setattr(watchdog.delegate, "_free_gb", lambda path="/": 1.0)
    monkeypatch.setattr(watchdog.delegate, "_remote_free_gb_for_host", lambda cfg: 40.0)
    local = _task(temp_db, None)
    remote = _task(temp_db, "contabo")
    disk_queue.enqueue(local, "test-owner")
    disk_queue.enqueue(remote, "test-owner")
    assert watchdog._drain_disk_queue()["task"] == remote
    assert queue == [remote]


def test_drain_waits_for_a_worker_slot(temp_db, queue, monkeypatch):
    monkeypatch.setattr(watchdog.delegate, "self_host", lambda: "mac")
    monkeypatch.setattr(watchdog.delegate, "_free_gb", lambda path="/": 999.0)
    monkeypatch.setattr(watchdog.delegate, "_remote_free_gb_for_host", lambda cfg: 999.0)
    busy = [_task(temp_db, "winbox", "in_progress", pid=p) for p in (111, 222)]
    tid = _task(temp_db, "winbox")
    disk_queue.enqueue(tid, "test-owner")
    assert watchdog._drain_disk_queue() is None and queue == []
    temp_db.update_status(busy[0], "done", actor="cto")
    assert watchdog._drain_disk_queue()["task"] == tid

"""Host routing tests: fake probes only, no host or network access."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import sqlite3
from unittest.mock import Mock

import pytest

from lib import router
from tools import host_fill, host_queue

REAL_PROBE = host_fill.probe


def reading(name, fill=50, running=0, **facts):
    return dict(name=name, online=True, running=running,
                facts=dict(ram_free_gb=8, ram_total_gb=10,
                           free_gb=70, disk_total_gb=100, cpu_pct=fill, **facts))


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.delenv("ORG_HOST_ROUTER", raising=False)
    monkeypatch.setattr(router, "role_runners", lambda task: ["claude"])
    monkeypatch.setattr(router.config, "hosts", lambda: {
        n: dict(max_workers=c, runners=["claude"], provides=["api"])
        for n, c in (("contabo", 3), ("winbox", 3), ("mac", 2))})
    monkeypatch.setattr(router.config, "project_path_for_host", lambda *args: "/fake")
    monkeypatch.setattr(router.config, "projects",
                        lambda: {"demo": {}, "mooniex-expertadvisor": {}})
    monkeypatch.setattr(router.db, "list_hosts", lambda: [])    # hub table: nothing stored
    monkeypatch.setattr(host_fill, "probe", Mock(side_effect=AssertionError("unexpected probe")))
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "queue.jsonl")


TASK = dict(id="task-one", project="demo", role="developer")


def choose(*rows, **task):
    return router.pick_host({**TASK, **task}, hosts_rows=list(rows))


def test_contabo_first_and_boundary():
    assert choose(reading("contabo", 79.99), reading("winbox", 35)).host == "contabo"
    assert choose(reading("contabo", 80), reading("winbox", 35)).host == "winbox"
    pick = choose(reading("contabo", 80), reading("winbox", 80), reading("mac", 80))
    assert pick.host is None and pick.line.startswith("no_host:")


def test_remote_fill_then_worker_tie():
    assert choose(reading("winbox", 60), reading("mac", 50, 1)).host == "mac"
    assert choose(reading("winbox", 50, 1), reading("mac", 50)).host == "mac"


@pytest.mark.parametrize("name,cap", [("contabo", 3), ("winbox", 3), ("mac", 2)])
def test_caps_unknown_partial_offline(name, cap):
    row = reading(name, running=cap)
    assert choose(row).host is None
    row["running"] = 0
    row["online"] = False
    assert choose(row).host is None
    row["online"] = True
    del row["facts"]["disk_total_gb"]
    # A missing sensor is not proof of an empty host: winbox and the Mac are not
    # eligible. Contabo keeps the old rule while the readings it has are under 80%.
    assert (choose(row).host == "contabo") is (name == "contabo")
    row["facts"]["cpu_pct"] = 80
    assert choose(row).host is None


def test_pins_paths_needs_and_exclusion(monkeypatch):
    rows = [reading("contabo"), reading("mac", 40), reading("winbox", 30)]
    assert choose(*rows, host="mac").host == "mac"
    assert choose(*rows, host="winbox", project="mooniex-expertadvisor").host is None
    assert choose(*rows, description="needs: gpu").host is None
    monkeypatch.setattr(router.config, "project_path_for_host", Mock(side_effect=ValueError()))
    assert choose(*rows).host is None


def test_winbox_ram_and_ph_hold():
    row = reading("winbox")
    row["facts"]["ram_free_gb"] = 3.99
    assert choose(row).host is None
    row["facts"]["ram_free_gb"] = 4
    assert choose(row).host == "winbox"
    assert choose(row, role="project_head").host is None
    row["facts"]["ceo_hold"] = False
    assert choose(row, role="project_head").host == "winbox"


@pytest.mark.parametrize("ram,disk,free,allowed", [
    (70, 30, 2, True), (80, 30, 2, False), (70, 80, 2, False),
    (70, 30, 1.59, False), (70, 30, 1.6, True)])
def test_cpu_exception(monkeypatch, ram, disk, free, allowed):
    slot = Mock(return_value=True)
    monkeypatch.setattr(router, "_exception_slot", slot)
    row = reading("contabo", 95)
    row["facts"].update(ram_free_gb=free, ram_total_gb=free / (1 - ram / 100), free_gb=100-disk)
    assert (choose(row, host="contabo").host == "contabo") is allowed
    assert choose(row).host is None  # not contabo-only
    slot.return_value = False
    assert choose(row, host="contabo").host is None


def test_exception_slot_atomic_and_active_past_ttl(monkeypatch, tmp_path):
    path = tmp_path / "fake.db"
    @contextmanager
    def connection():
        with sqlite3.connect(path, timeout=5) as conn:
            conn.row_factory = sqlite3.Row
            yield conn
    monkeypatch.setattr(router.db, "get_conn", connection)
    with connection() as conn:
        conn.executescript("CREATE TABLE tasks(id TEXT PRIMARY KEY,status TEXT);"
                           "CREATE TABLE locks(key TEXT PRIMARY KEY,owner TEXT,expires_at TEXT);"
                           "INSERT INTO tasks VALUES('a','pending'),('b','pending');")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda tid: router._exception_slot(tid, True, 600), ("a", "b")))
    assert sum(results) == 1
    winner = "a" if results[0] else "b"
    assert router._exception_slot(winner, True, 600)  # same job's mesh recheck
    with connection() as conn:
        conn.execute("UPDATE tasks SET status='in_progress' WHERE id=?", (winner,))
        conn.execute("UPDATE locks SET expires_at='2000-01-01'")
    assert not router._exception_slot("c", True, 600)
    with connection() as conn:
        conn.execute("UPDATE tasks SET status='review'")
    assert router._exception_slot("c", True, 600)


def test_switch_reloads_config(monkeypatch, tmp_path):
    path = tmp_path / "hosts.yaml"
    monkeypatch.setattr(router.config, "HOSTS_CONFIG", path)
    path.write_text("router: {enabled: false}")
    assert not router.enabled()
    path.write_text("router: {enabled: true}")
    assert router.enabled()
    monkeypatch.setenv("ORG_HOST_ROUTER", "off")
    assert not router.enabled()


def test_probes_use_config_timeout_and_remotes_only_when_contabo_does_not_take_it(monkeypatch):
    fills = {"contabo": 90, "mac": 50, "winbox": 40}
    probe = Mock(side_effect=lambda name, **kw: reading(name, fills[name]))
    monkeypatch.setattr(host_fill, "probe", probe)
    assert router.pick_host(TASK).host == "winbox"
    assert sorted(c.args[0] for c in probe.call_args_list) == ["contabo", "mac", "winbox"]
    assert all(c.kwargs == {"timeout": 10} for c in probe.call_args_list)
    probe.reset_mock()
    probe.side_effect = lambda name, **kw: reading(name)
    assert router.pick_host(TASK).host == "contabo"
    assert [c.args[0] for c in probe.call_args_list] == ["contabo"]    # no remote probe needed


def test_queue_retries_pin_and_drops_cancelled(monkeypatch):
    from tools import delegate
    row = {**TASK, "status": "pending"}
    monkeypatch.setattr(host_queue.db, "get_task", lambda tid: row)
    calls = []
    async def fake(tid, **kw):
        calls.append((tid, kw))
        return row
    monkeypatch.setattr(delegate, "delegate_task", fake)
    host_queue.enqueue(TASK["id"], "owner", host="mac")
    host_queue.enqueue(TASK["id"], "owner", host="mac")
    asyncio.run(host_queue.drain())
    assert calls == [(TASK["id"], {"host": "mac"})]
    assert len(host_queue.disk_queue._load(host_queue.QUEUE_PATH)) == 1
    row["status"] = "cancelled"
    asyncio.run(host_queue.drain())
    assert host_queue.disk_queue._load(host_queue.QUEUE_PATH) == []


def test_local_winbox_probe_reports_lease(monkeypatch):
    from tools import spawn_ph
    monkeypatch.setattr(host_fill.config, "self_host", lambda: "winbox")
    monkeypatch.setattr(host_fill.config, "host", lambda name: {"os": "windows", "max_workers": 3})
    monkeypatch.setattr(host_fill.node_dispatch, "_fill_facts", lambda: reading("winbox")["facts"])
    monkeypatch.setattr(host_fill.node_dispatch, "_installed_runners", lambda: ["claude"])
    monkeypatch.setattr(host_fill.node_dispatch, "_running_workers", lambda name: 0)
    monkeypatch.setattr(spawn_ph, "ceo_hold_refusal", lambda: None)
    row = REAL_PROBE("winbox")
    assert row["online"] and row["facts"]["ceo_hold"] is False
    assert row["facts"]["runners"] == ["claude"]

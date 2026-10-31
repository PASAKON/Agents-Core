"""C2/C3 regressions; all external effects are faked."""
import asyncio
from unittest.mock import Mock

import pytest

from lib import router
from tools import clevel_gate, delegate, spawn_ph


@pytest.fixture(autouse=True)
def fake_executor(monkeypatch):
    # These tests exercise dispatch decisions, not asyncio executor shutdown.
    async def inline(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    monkeypatch.setattr(asyncio, "to_thread", inline)
    monkeypatch.setattr(delegate, "info", Mock())


@pytest.mark.parametrize("host", ["mac", "winbox", "unknown"])
def test_cto_guard_even_when_flag_off_or_emergency(monkeypatch, host):
    monkeypatch.setattr(clevel_gate, "single_on", lambda: False)
    monkeypatch.setenv("ORG_CLEVEL_EMERGENCY", "1")
    assert "Contabo only" in clevel_gate.refusal("cto", host=host)
    assert clevel_gate.refusal("cto", host="contabo") is None
    assert clevel_gate.refusal("cmo", host=host) is None


def test_delegate_pin_uses_picker(monkeypatch):
    pick = Mock(return_value=router.HostPick("mac", "host: mac"))
    monkeypatch.setattr(router, "pick_host", pick)
    assert asyncio.run(delegate._route_host({"host": "contabo"}, "mac"))[0] == "mac"
    assert pick.call_args.args[0]["host"] == "mac"


def test_ph_cross_host_keeps_cap(monkeypatch):
    cap = Mock(return_value="two workers already live")
    monkeypatch.setattr(delegate, "_ph_cap_refusal", cap)
    monkeypatch.setattr(delegate.resource_gate, "check", Mock(side_effect=AssertionError()))
    task = {"owner_role": "project_head"}
    assert delegate._p2_spawn_refusal(task, "mac", "contabo") == "two workers already live"
    cap.return_value = None
    assert delegate._p2_spawn_refusal(task, "winbox", "mac") is None


def test_ph_mac_cli_picker_dry_run(monkeypatch, capsys):
    monkeypatch.setattr(spawn_ph, "_caller", lambda: ("cto", "12345678"))
    monkeypatch.setattr(spawn_ph.roles, "ph_lane_refusal", lambda lane: None)
    monkeypatch.setattr(spawn_ph.roles, "ph_project_refusal", lambda project: None)
    pick = Mock(return_value=router.HostPick("mac", "host: mac"))
    monkeypatch.setattr(router, "pick_host", pick)
    monkeypatch.setattr(router, "enabled", lambda: True)
    assert spawn_ph.main(["mesh", "--project", "demo", "--host", "mac", "--dry-run"]) == 0
    assert '"host": "mac"' in capsys.readouterr().out
    assert pick.call_args.args[0]["role"] == "project_head"
    assert pick.call_args.args[0]["host"] == "mac"       # the named host is kept
    pick.return_value = router.HostPick(None, "no_host: mac(full 2/2)")
    assert spawn_ph.main(["mesh", "--project", "demo", "--host", "mac", "--dry-run"]) == 1
    assert "no_host: mac(full 2/2)" in capsys.readouterr().err


def test_darwin_remote_uses_mesh_without_admin_ssh(monkeypatch):
    monkeypatch.setattr(delegate, "get_host", lambda name: {"os": "darwin", "ssh": None})
    monkeypatch.setattr(delegate, "self_host", lambda: "contabo")
    monkeypatch.setattr(delegate.mesh, "enabled", lambda: False)
    spawn = Mock(return_value={"status": "in_progress"})
    monkeypatch.setattr(delegate, "mesh_spawn_worker", spawn)
    row = asyncio.run(delegate._spawn_remote({"id": "fake", "role": "developer", "project": "demo"}, "mac"))
    assert row["status"] == "in_progress"
    spawn.assert_called_once_with("fake", "mac")


def test_standard_ph_host_flag(monkeypatch, capsys):
    monkeypatch.setattr(spawn_ph, "_caller", lambda: ("cto", "12345678"))
    monkeypatch.setattr(spawn_ph, "ready_schedule", lambda *args: {"kind": "loop"})
    monkeypatch.setattr(router.config, "self_host", lambda: "contabo")
    monkeypatch.setattr(spawn_ph, "pick_ph_host", lambda *args: router.HostPick("mac", "host: mac"))
    assert spawn_ph.main(["--project", "demo", "--host", "mac", "--dry-run"]) == 0
    assert '"host": "mac"' in capsys.readouterr().out


def test_delegate_queues_without_spawn(monkeypatch, tmp_path):
    from tools import host_queue
    row = {"id": "task-test", "status": "pending", "project": "demo", "role": "developer"}
    monkeypatch.setattr(delegate.db, "get_task", lambda tid: row)
    monkeypatch.setattr(delegate.db, "set_fields", Mock())
    monkeypatch.setattr(delegate, "_ph_ownership_refusal", lambda task: None)
    monkeypatch.setattr(delegate, "warn", Mock())
    monkeypatch.setattr(router, "enabled", lambda: True)
    monkeypatch.setattr(router, "pick_host", lambda *args, **kwargs: router.HostPick(None, "queued for host"))
    monkeypatch.setattr(host_queue, "QUEUE_PATH", tmp_path / "queue.jsonl")
    result = asyncio.run(delegate._delegate_task("task-test", host="mac"))
    assert result["status"] == "pending"
    assert host_queue.disk_queue._load(host_queue.QUEUE_PATH)[0]["host"] == "mac"


def test_launcher_guard_wiring():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    cto = (root / "scripts/cto-claude.sh").read_text()
    cxo = (root / "scripts/cxo-claude.sh").read_text()
    win = (root / "windows/cxo-claude.ps1").read_text()
    assert "if org_flag ORG_SINGLE_CLEVEL; then" not in cto
    assert '[ "$ROLE" = "cto" ] || org_flag ORG_SINGLE_CLEVEL' in cxo
    assert "CTO runs on Contabo only" in win

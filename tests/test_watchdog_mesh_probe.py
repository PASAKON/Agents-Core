"""Periodic mesh probes: fake dispatch, key, clock and alert channel only."""
import json
from unittest.mock import Mock

import pytest

from runners import watchdog as w
from tools import gh_issue


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("ORG_MESH_PROBE", "1")
    monkeypatch.setenv("ORG_MESH_DISPATCH", "0")
    monkeypatch.delenv("ORG_MESH_PROBE_INTERVAL_S", raising=False)
    monkeypatch.setattr(w, "MESH_PROBE_STATE", tmp_path / "state/probe.json")
    monkeypatch.setattr(w, "_mesh_probe_state", None)
    monkeypatch.setattr(w, "_mesh_probe_skip_noted", False)
    key = tmp_path / "key"
    key.touch()
    monkeypatch.setattr(w.mesh, "SSH_KEY", str(key))
    monkeypatch.setattr(w, "self_host", lambda: "local")
    monkeypatch.setattr(w, "all_hosts", lambda: {
        "local": {"mesh_ssh": "me@local"}, "mac": {"mesh_ssh": None},
        "peer": {"mesh_ssh": "user@peer"}})
    monkeypatch.setattr(w.time, "time", Mock(return_value=10000))
    monkeypatch.setattr(w.mesh, "dispatch", Mock(return_value={"ok": True}))
    monkeypatch.setattr(gh_issue, "create_issue", Mock(return_value="issue-url"))
    for name in ("info", "warn", "error", "success"):
        monkeypatch.setattr(w, name, Mock())


def test_selection_and_dispatch_flag():
    assert w._probe_mesh_hosts() == {"peer": "ok"}
    w.mesh.dispatch.assert_called_once_with("peer", "probe")


@pytest.mark.parametrize("disabled", [True, False])
def test_skip(monkeypatch, tmp_path, disabled):
    if disabled:
        monkeypatch.setenv("ORG_MESH_PROBE", "0")
    else:
        monkeypatch.setattr(w.mesh, "SSH_KEY", str(tmp_path / "absent"))
    assert w._probe_mesh_hosts(force=True) == {}
    assert w._probe_mesh_hosts(force=True) == {}
    w.mesh.dispatch.assert_not_called()
    w.info.assert_called_once()
    assert not w.MESH_PROBE_STATE.exists()


@pytest.mark.parametrize("value,interval", [("60", 60), ("1200", 1200),
    ("59", 900), ("0", 900), ("1.5", 900), ("bad", 900)])
def test_interval(monkeypatch, value, interval):
    monkeypatch.setenv("ORG_MESH_PROBE_INTERVAL_S", value)
    assert w._probe_mesh_hosts() == {"peer": "ok"}
    w.time.time.return_value += interval - 1
    assert w._probe_mesh_hosts() == {}
    w.time.time.return_value += 1
    assert w._probe_mesh_hosts() == {"peer": "ok"}
    assert w.mesh.dispatch.call_count == 2
    assert w._probe_mesh_hosts(force=True) == {"peer": "ok"}


def test_classifications_and_exception_isolation(monkeypatch):
    monkeypatch.setattr(w, "all_hosts", lambda: {
        name: {"mesh_ssh": "u@host"} for name in ("a", "b", "c", "d")})
    w.mesh.dispatch.side_effect = [RuntimeError("broken"),
        w.mesh.MeshUnreachable("Permission denied (publickey)"),
        {"ok": False, "error": "hub unavailable"}, {"ok": True}]
    assert w._probe_mesh_hosts() == {
        "a": "refused/error", "b": "unreachable", "c": "refused/error", "d": "ok"}
    assert w.mesh.dispatch.call_count == 4


def test_outage_recovery_and_restart():
    w.mesh.dispatch.side_effect = w.mesh.MeshUnreachable("Permission denied (publickey)")
    assert w._probe_mesh_hosts() == {"peer": "unreachable"}
    gh_issue.create_issue.assert_not_called()
    # One bad probe and the interval both survive process restart.
    w._mesh_probe_state = None
    assert w._probe_mesh_hosts() == {}
    w.time.time.return_value += 900
    w._probe_mesh_hosts()
    gh_issue.create_issue.assert_called_once()
    w.error.assert_called_once()
    assert "Permission denied (publickey)" in w.error.call_args.args[0]
    w._mesh_probe_state = None
    w.time.time.return_value += 900
    w._probe_mesh_hosts()
    assert gh_issue.create_issue.call_count == 1
    assert w.warn.call_count == 2
    w.mesh.dispatch.side_effect = None
    w._probe_mesh_hosts(force=True)
    w._probe_mesh_hosts(force=True)
    w.success.assert_called_once_with("host peer reachable again after 30 min")
    assert gh_issue.create_issue.call_count == 1
    w.mesh.dispatch.side_effect = w.mesh.MeshUnreachable("timeout")
    w._probe_mesh_hosts(force=True)
    w._probe_mesh_hosts(force=True)
    assert gh_issue.create_issue.call_count == 2


def test_blip_resets_streak():
    w.mesh.dispatch.side_effect = [{"ok": False}, {"ok": True}, {"ok": False}]
    for _ in range(3):
        w._probe_mesh_hosts(force=True)
    gh_issue.create_issue.assert_not_called()


@pytest.mark.parametrize("contents", ["broken", "[]", '{"hosts": {}, "last_probe": "oops"}',
    '{"hosts": {"peer": {}}, "last_probe": 0}'])
def test_corrupt_state(contents):
    w.MESH_PROBE_STATE.parent.mkdir()
    w.MESH_PROBE_STATE.write_text(contents)
    assert w._probe_mesh_hosts() == {"peer": "ok"}
    assert json.loads(w.MESH_PROBE_STATE.read_text())["hosts"]["peer"]["bad_count"] == 0


def test_atomic_write(monkeypatch):
    original = w.os.replace
    calls = []
    def replace(src, dst):
        calls.append((src, dst))
        assert json.loads(w.Path(src).read_text())["hosts"]["peer"]["bad_count"] == 0
        original(src, dst)
    monkeypatch.setattr(w.os, "replace", replace)
    w._probe_mesh_hosts()
    assert len(calls) == 1
    assert list(w.MESH_PROBE_STATE.parent.iterdir()) == [w.MESH_PROBE_STATE]


def test_redacted_tail():
    secret = "ghp_" + "a" * 30
    w.mesh.dispatch.side_effect = w.mesh.MeshUnreachable("x" * 300 + " token " + secret)
    w._probe_mesh_hosts(force=True)
    w._probe_mesh_hosts(force=True)
    assert secret not in str(w.error.call_args)
    assert secret not in str(gh_issue.create_issue.call_args)
    assert secret not in w.MESH_PROBE_STATE.read_text()
    assert len(w._mesh_probe_details["peer"]) <= 200


def test_alert_failure_does_not_stop_peers(monkeypatch):
    monkeypatch.setattr(w, "all_hosts", lambda: {
        h: {"mesh_ssh": "u@host"} for h in ("a", "b")})
    w.mesh.dispatch.return_value = {"ok": False}
    gh_issue.create_issue.side_effect = RuntimeError("failed")
    w._probe_mesh_hosts(force=True)
    assert w._probe_mesh_hosts(force=True) == {"a": "refused/error", "b": "refused/error"}
    assert gh_issue.create_issue.call_count == 2


@pytest.mark.parametrize("outcome,exit_code", [({"ok": True}, 0), ({"ok": False}, 1), (None, 2)])
def test_cli(monkeypatch, capsys, outcome, exit_code):
    monkeypatch.setattr(w.sys, "argv", ["watchdog", "--mesh-probe"])
    monkeypatch.setattr(w.db, "init", Mock(side_effect=AssertionError("no DB init")))
    if outcome is None:
        monkeypatch.setenv("ORG_MESH_PROBE", "0")
    else:
        w.mesh.dispatch.return_value = outcome
        w._probe_mesh_hosts()
    assert w.main() == exit_code
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == (0 if outcome is None else 1)
    if lines:
        host, classification, detail = lines[0].split(" ", 2)
        assert host == "peer"
        assert classification == ("ok" if exit_code == 0 else "refused/error")
        assert len(detail) <= 120
        assert w.mesh.dispatch.call_count == 2


@pytest.mark.parametrize("raises", [False, True])
def test_scan_summary(monkeypatch, raises):
    monkeypatch.setattr(w.db, "list_tasks", lambda **kw: [])
    monkeypatch.setattr(w, "_mac_surfaces", lambda: False)
    for name in ("gc_stale_tasks", "sweep_terminal_surfaces", "_drain_disk_queue",
                 "_retry_queued_remote", "_retry_letters", "_provision_identities"):
        monkeypatch.setattr(w, name, lambda: [])
    monkeypatch.setenv("ORG_WATCHDOG_BRANCH_POLL", "0")
    monkeypatch.setattr(w.work_watch, "watch", Mock(return_value={}))
    if raises:
        monkeypatch.setattr(w, "_probe_mesh_hosts", Mock(side_effect=RuntimeError("oops")))
    assert w.scan_once()["mesh_probe"] == ({} if raises else {"peer": "ok"})
    w.work_watch.watch.assert_called_once()

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from lib import db, mesh
from tools import mesh_check as m, session_status


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.setattr(m, "_self_host_or_none", lambda: "mac")
    monkeypatch.setattr(m, "_mesh_ssh_for", lambda host: "node@host")
    monkeypatch.setattr(mesh, "enabled", lambda: True)
    monkeypatch.setattr(session_status, "list_sessions", lambda status: [])
    monkeypatch.setattr(session_status, "get", lambda role, sid: {"host": "contabo"})
    monkeypatch.setattr(db, "create_letter", Mock(return_value=42))
    monkeypatch.setattr(m, "_abandon_letter", Mock())
    monkeypatch.setattr(m.time, "sleep", Mock())
    replies = [
        {"ok": True, "result": {"session_id": "11111111"}},
        {"ok": True},
        {"ok": True, "result": {"stopped": True}},
        {"ok": True, "result": {"session_id": "22222222", "resumed_from": "11111111"}},
        {"ok": True, "result": {"stopped": True}},
    ]
    dispatch = Mock(side_effect=replies)
    monkeypatch.setattr(mesh, "dispatch", dispatch)
    return dispatch, replies


def test_happy_order(probe):
    dispatch, _ = probe
    cell = m.l9_probe("mac", "contabo")
    assert cell["ok"] and cell["note"] == "spawn 11111111, resume 11111111 -> 22222222, both stopped"
    assert [c.args for c in dispatch.call_args_list] == [
        ("contabo", "start_clevel", "cto", "--probe"),
        ("contabo", "deliver_letter", "42"),
        ("contabo", "stop_clevel", "cto", "11111111"),
        ("contabo", "start_clevel", "cto", "--resume", "11111111", "--probe"),
        ("contabo", "stop_clevel", "cto", "22222222"),
    ]
    assert m.time.sleep.call_args.args == (60,)
    assert db.create_letter.call_args.kwargs["to_session"] == "11111111"


def test_resume_refused(probe):
    dispatch, replies = probe
    replies[3] = {"ok": False, "error": "no resume uuid"}
    dispatch.side_effect = replies
    assert not m.l9_probe("mac", "contabo")["ok"]
    assert dispatch.call_args_list[2].args[1:] == ("stop_clevel", "cto", "11111111")
    assert dispatch.call_count == 4


@pytest.mark.parametrize("failure", [{"ok": False}, mesh.MeshUnreachable("offline")])
def test_cleanup_failure_fails_without_raising(probe, failure, capsys):
    dispatch, replies = probe
    replies[4] = failure
    dispatch.side_effect = replies
    assert not m.l9_probe("mac", "contabo")["ok"]
    assert "stop 22222222" in capsys.readouterr().err


def test_failed_first_stop_retried_in_finally(probe):
    dispatch, replies = probe
    dispatch.side_effect = replies[:2] + [{"ok": False}, replies[2]]
    assert not m.l9_probe("mac", "contabo")["ok"]
    assert dispatch.call_args_list[-1] == dispatch.call_args_list[-2]


def test_cap_skip(probe, monkeypatch):
    dispatch, _ = probe
    monkeypatch.setattr(session_status, "list_sessions", lambda status: [
        {"role": "cto", "host": "contabo"}] * 3)
    cell = m.l9_probe("mac", "contabo")
    assert m._judge(cell) == ("skip: cap", "skip")
    dispatch.assert_not_called()


def test_own_seat_and_waves(probe, monkeypatch):
    dispatch, _ = probe
    assert m.l9_probe("winbox", "contabo")["kind"] == "n/a"
    dispatch.assert_not_called()
    assert {(f, t): w for (l, f, t), w in m.EXPECT.items() if l == "L9"} == {
        (f, t): w for (l, f, t), w in m.EXPECT.items() if l == "L5"}
    for name in ("check_sec", "l5_probe", "l6_probe"):
        monkeypatch.setattr(m, name, lambda *args: m._green())
    monkeypatch.setattr(m, "l7_probe", lambda cases: {})
    check = Mock(return_value=m._green())
    monkeypatch.setattr(m, "l9_probe", check)
    combined = {l: {h: {} for h in m.HOSTS} for l in m.LEVELS}
    m._run_mesh_levels(combined, "mac", "w3")
    assert check.call_count == 2
    assert all(c.args[0] == "mac" for c in check.call_args_list)
    assert not combined["L9"]["winbox"]


def test_registration_timeout_cleans_up(probe, monkeypatch):
    dispatch, replies = probe
    dispatch.side_effect = [replies[0], replies[2]]
    monkeypatch.setattr(session_status, "get", lambda *args: {"host": "wrong"})
    monkeypatch.setattr(m.time, "monotonic", Mock(side_effect=[0, 0, 120]))
    assert not m.l9_probe("mac", "contabo")["ok"]
    assert dispatch.call_args.args == ("contabo", "stop_clevel", "cto", "11111111")


def test_bad_resume_metadata_still_cleans_up(probe):
    dispatch, replies = probe
    replies[3]["result"]["resumed_from"] = "33333333"
    dispatch.side_effect = replies
    assert not m.l9_probe("mac", "contabo")["ok"]
    assert dispatch.call_args.args[-1] == "22222222"


@pytest.mark.parametrize("live,ok,exit_code", [(False, False, 0), (True, True, 0), (True, False, 1)])
def test_main_live_gate_and_l9_exit_code(monkeypatch, tmp_path, live, ok, exit_code):
    monkeypatch.setattr(m, "_running_host_guess", lambda root: "mac")
    monkeypatch.setattr(m, "HOSTS", ["mac", "contabo"])
    monkeypatch.setattr(m.config, "host", lambda host: {"mesh_ssh": "node@host"})
    for name in ("check_l0", "check_l1", "l4_probe"):
        monkeypatch.setattr(m, name, lambda *args: (True, None))
    monkeypatch.setattr(m, "check_l2", AsyncMock(return_value=(True, None)))
    monkeypatch.setattr(m, "run_l3_probe", AsyncMock(return_value=(True, None)))
    for name in ("check_sec", "l5_probe", "l6_probe", "check_invariant"):
        monkeypatch.setattr(m, name, lambda *args: m._green())
    monkeypatch.setattr(m, "l7_probe", lambda cases: {})
    monkeypatch.setattr(m, "write_state", lambda *args: tmp_path / "latest.json")
    l9 = Mock(return_value=m._green() if ok else m._red("resume refused"))
    monkeypatch.setattr(m, "l9_probe", l9)
    args = ["--expect", "w2"] + (["--live"] if live else [])
    assert asyncio.run(m.amain(args)) == exit_code
    assert l9.call_count == int(live)

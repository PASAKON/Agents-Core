"""Host ownership and probe cleanup, with no live launchers or hub."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from tools import node_dispatch as nd
from tools import send_to_cxo, session_name, session_status, tmux_session

SID = "abcd1234"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(nd, "_self_host", lambda: "here")
    monkeypatch.setattr(nd.config, "live_c_level_roles", lambda: ["cto", "coo"])
    monkeypatch.setattr(nd, "_audit", Mock())
    monkeypatch.setattr(nd, "MESH_PROBE_DIR", tmp_path / "mesh-probe")
    monkeypatch.setattr(session_status, "LOCKS", tmp_path)
    monkeypatch.setattr(send_to_cxo, "LOCKS_DIR", tmp_path)
    monkeypatch.setattr(session_status, "get", Mock(return_value={"host": "here"}))
    monkeypatch.setattr(session_status, "record_close", Mock())
    for name in ("_claim", "_hold", "_release"):
        monkeypatch.setattr(nd, name, Mock(return_value="token"))
    monkeypatch.setattr(nd, "_live_clevel_count", lambda role: 0)
    for name in ("_start_clevel_tmux", "_start_clevel_schtask", "_start_clevel_iterm"):
        monkeypatch.setattr(nd, name, Mock(return_value={
            "role": "cto", "session_id": SID, "via": name,
            "tmux_session": "cto-abcd1234" if name.endswith("tmux") else None}))
    monkeypatch.setattr(nd, "_is_windows", lambda: False)
    monkeypatch.setattr(nd, "_os_name", lambda: "linux")
    monkeypatch.setattr(nd, "_pid_is_alive", Mock(return_value=True))
    monkeypatch.setattr(tmux_session, "has_session", Mock(return_value=True))
    monkeypatch.setattr(tmux_session, "tmux_bin", lambda: "tmux")
    monkeypatch.setattr(nd.subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0, "", "")))
    monkeypatch.setattr(nd.subprocess, "Popen", Mock(side_effect=AssertionError("no processes")))


def platform(monkeypatch, os_name):
    monkeypatch.setattr(nd, "_is_windows", lambda: os_name == "windows")
    monkeypatch.setattr(nd, "_os_name", lambda: os_name)


@pytest.mark.parametrize("os_name", ["linux", "windows", "darwin"])
@pytest.mark.parametrize("row,local,code", [
    ({"host": "elsewhere"}, True, 2), ({"host": None}, True, 0),
    ({"host": None}, False, 2), (None, True, 0), (None, False, 2),
    ({"host": ""}, False, 2), ({"host": ""}, True, 0),
    ({"host": "here"}, False, 0),
])
def test_resume_host(monkeypatch, tmp_path, os_name, row, local, code):
    platform(monkeypatch, os_name)
    session_status.get.return_value = row
    if local:
        (tmp_path / f"cto-{SID}.uuid").write_text("local uuid")
    out, actual = nd._run("start_clevel", ["cto", "--resume", SID])
    assert actual == code, out
    assert out["ok"] is (code == 0)
    session_status.get.assert_called_once_with("cto", SID)
    launchers = {"linux": nd._start_clevel_tmux, "windows": nd._start_clevel_schtask,
                 "darwin": nd._start_clevel_iterm}
    for name, launcher in launchers.items():
        if code == 0 and name == os_name:
            launcher.assert_called_once_with("cto", SID)
        else:
            launcher.assert_not_called()
    if code:
        nd._claim.assert_not_called()
        if row and row.get("host"):
            assert out["error"] == f"session cto-{SID} lives on elsewhere; resume it there"
        else:
            assert "no host on record and no local .uuid" in out["error"]


@pytest.mark.parametrize("os_name", ["linux", "windows", "darwin"])
def test_hub_error_is_failure(monkeypatch, os_name):
    platform(monkeypatch, os_name)
    session_status.get.side_effect = RuntimeError("hub down")
    with pytest.raises(nd.Failure, match="hub down"):
        nd.verb_start_clevel("cto", SID)
    out, code = nd._run("start_clevel", ["cto", "--resume", SID])
    assert code == 1 and not out["ok"]
    nd._claim.assert_not_called()
    for launcher in (nd._start_clevel_tmux, nd._start_clevel_schtask, nd._start_clevel_iterm):
        launcher.assert_not_called()


@pytest.mark.parametrize("args,expected", [
    (["cto"], ("cto", None, False)),
    (["cto", "--probe"], ("cto", None, True)),
    (["cto", "--resume", SID], ("cto", SID, False)),
    (["cto", "--resume", SID, "--probe"], ("cto", SID, True)),
])
def test_parser(args, expected):
    assert nd._parse_start_clevel(args) == expected


@pytest.mark.parametrize("args", [
    ["--probe", "--probe"], ["cto", "--probe", "--probe"], ["--probe", "cto"],
    ["cto", "--probe", "--resume", "x"], ["cto", "--probe", "--resume", SID],
])
def test_parser_refuses(args):
    with pytest.raises(nd.Refusal):
        nd._parse_start_clevel(args)


@pytest.mark.parametrize("os_name", ["linux", "windows", "darwin"])
@pytest.mark.parametrize("probe", [False, True])
def test_marker(monkeypatch, os_name, probe):
    platform(monkeypatch, os_name)
    replace = Mock(wraps=nd.os.replace)
    monkeypatch.setattr(nd.os, "replace", replace)
    out, code = nd._run("start_clevel", ["cto"] + (["--probe"] if probe else []))
    assert code == 0, out
    path = nd.MESH_PROBE_DIR / f"cto-{SID}.json"
    assert path.exists() is probe
    if probe:
        assert out["result"]["probe_marker"] is True
        marker = json.loads(path.read_text())
        assert marker == {"role": "cto", "session_id": SID, "host": "here",
                          "started_at": marker["started_at"],
                          "tmux_session": out["result"]["tmux_session"], "via": out["result"]["via"]}
        assert datetime.fromisoformat(marker["started_at"]).utcoffset() == timedelta(0)
        replace.assert_called_once()
        assert list(nd.MESH_PROBE_DIR.iterdir()) == [path]
    else:
        assert "probe_marker" not in out["result"]
        replace.assert_not_called()


@pytest.mark.parametrize("stage", ["mkdir", "write_text", "replace"])
@pytest.mark.parametrize("failures", [1, 2])
def test_probe_marker_write_retries(monkeypatch, stage, failures):
    owner = nd.os if stage == "replace" else type(nd.MESH_PROBE_DIR)
    original = getattr(owner, stage)
    calls = []

    def flaky(*args, **kwargs):
        calls.append(args)
        if len(calls) <= failures:
            raise OSError("marker write failed")
        return original(*args, **kwargs)

    monkeypatch.setattr(owner, stage, flaky)
    out, code = nd._run("start_clevel", ["cto", "--probe"])
    assert code == 0 and out["ok"], out
    assert out["result"]["session_id"] == SID
    assert out["result"]["probe_marker"] is (failures == 1)
    assert len(calls) == 2
    path = nd.MESH_PROBE_DIR / f"cto-{SID}.json"
    assert path.exists() is (failures == 1)
    if path.exists():
        assert json.loads(path.read_text())["session_id"] == SID
    assert not list(nd.MESH_PROBE_DIR.glob("*.tmp"))
    nd._start_clevel_tmux.assert_called_once_with("cto", None)
    nd._release.assert_not_called()
    nd._hold.assert_called_once()


def marker(**over):
    nd.MESH_PROBE_DIR.mkdir()
    path = nd.MESH_PROBE_DIR / f"cto-{SID}.json"
    path.write_text(json.dumps({"role": "cto", "session_id": SID, "host": "here",
                               "started_at": datetime.now(timezone.utc).isoformat(),
                               "tmux_session": None, "via": "tmux", **over}))
    return path


@pytest.mark.parametrize("case", ["missing", "stale", "darwin", "foreign"])
def test_stop_refuses(monkeypatch, case):
    if case != "missing":
        values = {}
        if case == "stale":
            values["started_at"] = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        if case == "foreign":
            values["host"] = "elsewhere"
        path = marker(**values)
    if case == "darwin":
        platform(monkeypatch, "darwin")
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == 2 and not out["ok"]
    assert {"missing": "not a probe session started on here", "stale": "stale probe marker",
            "darwin": "stop_clevel is not built for darwin yet",
            "foreign": "not a probe session started on here"}[case] in out["error"]
    nd.subprocess.run.assert_not_called()
    session_status.record_close.assert_not_called()
    if case != "missing":
        assert path.exists()


@pytest.mark.parametrize("name", [None, "custom-probe"])
def test_linux_stop(name):
    path = marker(tmux_session=name)
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == 0 and out["result"]["stopped"] is True
    assert nd.subprocess.run.call_args.args[0] == [
        "tmux", "kill-session", "-t", name or session_name.tmux_name("cto", SID)]
    session_status.record_close.assert_called_once_with("cto", SID, "closed", note="mesh probe stopped")
    assert not path.exists()


def test_windows_stop(monkeypatch, tmp_path):
    platform(monkeypatch, "windows")
    path = marker()
    (tmp_path / f"cto-{SID}.lock").write_text("4242")
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == 0 and out["result"]["stopped"] is True
    assert nd.subprocess.run.call_args.args[0] == ["taskkill", "/PID", "4242", "/T", "/F"]
    assert nd.subprocess.run.call_args.kwargs.get("shell") is not True
    session_status.record_close.assert_called_once_with("cto", SID, "closed", note="mesh probe stopped")
    assert not path.exists()


@pytest.mark.parametrize("case", ["linux", "missing-lock", "dead-pid", "junk-lock"])
def test_already_gone(monkeypatch, tmp_path, case):
    platform(monkeypatch, "linux" if case == "linux" else "windows")
    path = marker()
    tmux_session.has_session.return_value = False
    nd._pid_is_alive.return_value = False
    if case == "dead-pid":
        (tmp_path / f"cto-{SID}.lock").write_text("4242")
    if case == "junk-lock":
        (tmp_path / f"cto-{SID}.lock").write_text("not a pid")
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == 0
    assert out["result"] == {"role": "cto", "session_id": SID, "stopped": False, "detail": "already gone"}
    nd.subprocess.run.assert_not_called()
    if case == "junk-lock":
        nd._pid_is_alive.assert_called_once_with(None)
    session_status.record_close.assert_called_once()
    assert not path.exists()


@pytest.mark.parametrize("args", [["ceo", SID], ["cto", "../x"], ["cto"], ["cto", SID, "extra"]])
def test_stop_argument_validation(args):
    out, code = nd._run("stop_clevel", args)
    assert code == 2 and not out["ok"]
    nd.subprocess.run.assert_not_called()


@pytest.mark.parametrize("os_name", ["linux", "windows"])
@pytest.mark.parametrize("gone", [False, True])
def test_stop_command_failure_or_exit_race(monkeypatch, tmp_path, os_name, gone):
    platform(monkeypatch, os_name)
    path = marker()
    (tmp_path / f"cto-{SID}.lock").write_text("4242")
    nd.subprocess.run.return_value = subprocess.CompletedProcess([], 1, "", "failed")
    live = nd._pid_is_alive if os_name == "windows" else tmux_session.has_session
    live.side_effect = [True, not gone]
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == (0 if gone else 1), out
    assert path.exists() is not gone
    if gone:
        assert out["result"]["detail"] == "already gone"
        session_status.record_close.assert_called_once()
    else:
        session_status.record_close.assert_not_called()


def test_close_failure_keeps_marker():
    path = marker()
    session_status.record_close.side_effect = RuntimeError("hub down")
    out, code = nd._run("stop_clevel", ["cto", SID])
    assert code == 1 and "hub down" in out["error"]
    assert path.exists()


def test_probe_requires_launcher_session_id():
    nd._start_clevel_tmux.return_value["session_id"] = None
    out, code = nd._run("start_clevel", ["cto", "--probe"])
    assert code == 1 and "no valid session id" in out["error"]
    assert not nd.MESH_PROBE_DIR.exists()

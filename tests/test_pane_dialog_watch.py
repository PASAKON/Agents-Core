import json
import subprocess

import pytest

from tools import pane_dialog_watch as watch


class FakeTmux:
    def __init__(self):
        self.panes = {("cto-abc", "%1"): "Working"}
        self.calls = []
        self.fail_capture = False
        self.fail_list = False

    def __call__(self, args):
        self.calls.append(args)
        if args == ["list-panes", "-a", "-F", "#{session_name}\t#{pane_id}"]:
            if self.fail_list:
                raise subprocess.CalledProcessError(1, args)
            return "\n".join(f"{session}\t{pane}" for session, pane in self.panes)
        assert args[:3] == ["capture-pane", "-p", "-t"]
        assert len(args) == 4
        if self.fail_capture:
            raise subprocess.CalledProcessError(1, args)
        return next(text for (_, pane), text in self.panes.items() if pane == args[3])


@pytest.fixture
def rig(tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    monkeypatch.setenv("PANE_DIALOG_WATCH_STATE", str(state))
    monkeypatch.delenv("PANE_DIALOG_WATCH_SECONDS", raising=False)
    runner = FakeTmux()
    notices = []

    def notify(message):
        notices.append(message)
        return {"ok": True}

    def run(now):
        return watch.run_once(runner=runner, notifier=notify, now=now)

    return runner, notices, run, state


def test_no_dialog(rig):
    runner, notices, run, state = rig
    assert run(0) == 0
    assert run(600) == 0
    assert notices == []
    assert json.loads(state.read_text()) == {}


def test_wait_notify_once_and_reset(rig):
    runner, notices, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    assert run(0) == 0
    assert run(299) == 0
    assert notices == []
    assert run(301) == 0
    assert len(notices) == 1
    assert "cto-abc" in notices[0]
    assert "Do you want to proceed?" in notices[0]
    assert run(700) == 0
    assert len(notices) == 1
    runner.panes[("cto-abc", "%1")] = "Working again"
    assert run(800) == 0
    assert json.loads(state.read_text()) == {}
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    assert run(900) == 0
    assert run(1201) == 0
    assert len(notices) == 2


@pytest.mark.parametrize("session", ["cto-x", "cmo-x", "cgo-x", "cfo-x", "coo-x", "sompong"])
def test_c_level_sessions(rig, session):
    runner, notices, run, _ = rig
    runner.panes = {(session, "%2"): "Yes, I trust this folder"}
    run(0)
    run(300)
    assert len(notices) == 1


def test_non_c_level_ignored(rig):
    runner, notices, run, _ = rig
    runner.panes = {("developer-cto-x", "%9"): "Do you want to proceed?"}
    run(0)
    run(600)
    assert notices == []
    assert all(call[0] == "list-panes" for call in runner.calls)


@pytest.mark.parametrize("marker", watch.DIALOG_MARKERS)
def test_markers_and_text_limit(rig, marker):
    runner, notices, run, _ = rig
    runner.panes[("cto-abc", "%1")] = "unrelated text\n" + marker + "x" * 500 + "\nprivate tail"
    run(0)
    run(300)
    assert notices[0].split("\n", 1)[1] == (marker + "x" * 500)[:200]


def test_failed_delivery_retried(rig):
    runner, notices, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    run(0)
    assert watch.run_once(runner=runner, notifier=lambda _: {"ok": False}, now=300) == 1
    assert not next(iter(json.loads(state.read_text()).values()))["notified"]
    run(360)
    run(420)
    assert len(notices) == 1


def test_capture_failure_preserves_wait(rig):
    runner, notices, run, _ = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    run(0)
    runner.fail_capture = True
    assert run(100) == 1
    runner.fail_capture = False
    run(300)
    assert len(notices) == 1


def test_list_failure_preserves_state(rig):
    runner, _, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    run(0)
    original = state.read_text()
    runner.fail_list = True
    with pytest.raises(subprocess.CalledProcessError):
        run(300)
    assert state.read_text() == original


def test_disappeared_pane_forgotten(rig):
    runner, _, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?"
    run(0)
    runner.panes.clear()
    run(300)
    assert json.loads(state.read_text()) == {}


def test_threshold_override_and_independent_panes(rig, monkeypatch):
    runner, notices, run, _ = rig
    monkeypatch.setenv("PANE_DIALOG_WATCH_SECONDS", "10")
    runner.panes = {("cto-a", "%1"): "Do you want to proceed?"}
    run(0)
    runner.panes[("cto-a", "%2")] = "Do you want to proceed?"
    run(9)
    assert notices == []
    run(10)
    assert len(notices) == 1
    run(19)
    assert len(notices) == 2

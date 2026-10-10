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

    def notify(session, line, minutes):
        notices.append((session, line, minutes))
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
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
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
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    assert run(900) == 0
    assert run(1201) == 0
    assert len(notices) == 2


@pytest.mark.parametrize("session", ["cto-x", "cmo-x", "cgo-x", "cfo-x", "coo-x", "sompong"])
def test_c_level_sessions(rig, session):
    runner, notices, run, _ = rig
    runner.panes = {(session, "%2"): "❯ 1. Yes, I trust this folder"}
    run(0)
    run(300)
    assert len(notices) == 1


def test_non_c_level_ignored(rig):
    runner, notices, run, _ = rig
    runner.panes = {("developer-cto-x", "%9"): "Do you want to proceed?\n❯ 1. Yes\n  2. No"}
    run(0)
    run(600)
    assert notices == []
    assert all(call[0] == "list-panes" for call in runner.calls)


@pytest.mark.parametrize("marker", watch.DIALOG_MARKERS)
def test_markers_and_text_limit(rig, marker):
    runner, notices, run, _ = rig
    runner.panes[("cto-abc", "%1")] = "unrelated text\n" + marker + "x" * 500 + "\nprivate tail\n1. Yes"
    run(0)
    run(300)
    assert notices[0][1] == (marker + "x" * 500)[:200]


def test_failed_delivery_retried(rig):
    runner, notices, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    run(0)
    assert watch.run_once(runner=runner, notifier=lambda *_: {"ok": False}, now=300) == 1
    assert not next(iter(json.loads(state.read_text()).values()))["notified"]
    run(360)
    run(420)
    assert len(notices) == 1


def test_capture_failure_preserves_wait(rig):
    runner, notices, run, _ = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    run(0)
    runner.fail_capture = True
    assert run(100) == 1
    runner.fail_capture = False
    run(300)
    assert len(notices) == 1


def test_list_failure_preserves_state(rig):
    runner, _, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    run(0)
    original = state.read_text()
    runner.fail_list = True
    with pytest.raises(subprocess.CalledProcessError):
        run(300)
    assert state.read_text() == original


def test_disappeared_pane_forgotten(rig):
    runner, _, run, state = rig
    runner.panes[("cto-abc", "%1")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    run(0)
    runner.panes.clear()
    run(300)
    assert json.loads(state.read_text()) == {}


def test_threshold_override_and_independent_panes(rig, monkeypatch):
    runner, notices, run, _ = rig
    monkeypatch.setenv("PANE_DIALOG_WATCH_SECONDS", "10")
    runner.panes = {("cto-a", "%1"): "Do you want to proceed?\n❯ 1. Yes\n  2. No"}
    run(0)
    runner.panes[("cto-a", "%2")] = "Do you want to proceed?\n❯ 1. Yes\n  2. No"
    run(9)
    assert notices == []
    run(10)
    assert len(notices) == 1
    run(19)
    assert len(notices) == 2


@pytest.mark.parametrize("text", [
    'Quoted: Do you want to proceed?\n' + 'transcript\n' * 15 + '1. Yes',
    'Do you want to proceed?',
    'Do you want to proceed?\nquoted 1. Yes',
    'Do you want to proceed?\n1. Yesterday',
    '1. Yes\n' + 'transcript\n' * 15 + 'Do you want to proceed?',
])
def test_quoted_or_incomplete_dialog_ignored(rig, text):
    runner, notices, run, state = rig
    runner.panes[("cto-abc", "%1")] = text
    assert run(0) == 0
    assert run(600) == 0
    assert notices == []
    assert json.loads(state.read_text()) == {}


def test_bottom_dialog_with_blank_lines():
    text = 'transcript\n' * 30 + 'Do you want to proceed?\n' + '\n' * 20 + ' ❯ 1. Yes\n2. No\n'
    assert watch.dialog_line(text) == 'Do you want to proceed?'


@pytest.mark.parametrize("outcome", [0, 2, 3, "missing", "timeout", "oserror"])
def test_email_delivery_and_retry(rig, tmp_path, monkeypatch, capsys, outcome):
    runner, _, run, state = rig
    runner.panes[("cto-abc", "%1")] = 'Do you want to proceed?\n1. Yes'
    run(0)
    monkeypatch.setattr(watch, 'ROOT', tmp_path)
    helper = tmp_path / 'tools/email_ceo.py'
    if outcome != 'missing':
        helper.parent.mkdir()
        helper.write_text('# fake helper; never executed\n')
    monkeypatch.setenv('CXO_ROLE', 'cfo')
    monkeypatch.setenv('CXO_SESSION_ID', 'live-session')
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if outcome == 'timeout':
            raise subprocess.TimeoutExpired(args, 30)
        if outcome == 'oserror':
            raise FileNotFoundError('fake')
        return subprocess.CompletedProcess(args, outcome, 'hub refused\nprivate second line', '')

    monkeypatch.setattr(watch.subprocess, 'run', fake_run)
    delivered = outcome in (0, 2)
    for now in (300, 360):
        assert watch.run_once(runner=runner, now=now) == (0 if delivered else 1)
        assert next(iter(json.loads(state.read_text()).values()))['notified'] is delivered
    assert len(calls) == (0 if outcome == 'missing' else 1 if delivered else 2)
    if calls:
        args, kwargs = calls[0]
        assert args == [watch.sys.executable, str(helper), 'send', '--kind', 'action',
                        '--title', 'Session waiting on a permission dialog: cto-abc',
                        '--need', 'open the session and answer the dialog',
                        '--why', 'Do you want to proceed? (waiting 5 min)',
                        '--if-not', 'the session stays stopped until someone answers',
                        '--ref', 'pane-dialog:cto-abc']
        assert kwargs['timeout'] == 30
        assert kwargs['capture_output'] is True
        assert kwargs['env'] == {**watch.os.environ, 'CXO_ROLE': 'cto', 'CXO_SESSION_ID': 'dialog-watch'}
    output = capsys.readouterr()
    assert output.out == ''
    assert output.err == ('hub refused\n' if outcome == 2 else '')


def test_email_title_and_pane_text_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, 'ROOT', tmp_path)
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'tools/email_ceo.py').touch()
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, '', '')

    monkeypatch.setattr(watch.subprocess, 'run', fake_run)
    assert watch.notify_ceo('cto-' + 's' * 200, 'x' * 500, 8)['ok']
    args = calls[0]
    assert len(args[args.index('--title') + 1]) == 90
    assert args[args.index('--why') + 1] == 'x' * 200 + ' (waiting 8 min)'

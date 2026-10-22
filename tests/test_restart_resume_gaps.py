"""17 Oct 2026 real restart: 0/6 sessions came back. Three gaps, one test each.
No real tmux, launchers, sleeps, or hub access (fixtures from test_restart_run)."""
from unittest.mock import Mock
import subprocess

import pytest

from tests.test_restart_run import args, commands, entry, isolated, manifest, row  # noqa: F401
from tools import clevel_gate, restart_run as rr, spawn_ph, tmux_session


@pytest.mark.parametrize('active', [False, True])
@pytest.mark.parametrize('role', ['cto', 'cfo'])
def test_resume_clears_only_active_scope_before_create(tmp_path, active, role):
    manifest([entry('lazy', role=role)])
    unit = f'org-{role}-1234abcd.scope'
    events = []
    def execute(command, **kwargs):
        events.append(command)
        return subprocess.CompletedProcess(command, 0 if active else 3)
    rr.subprocess.run.side_effect = execute
    rr.tmux_session.create.side_effect = lambda *a: events.append('create')
    rr.tmux_session.has_session.side_effect = [False, True]
    assert rr.resume(args(tmp_path)) == 0
    assert events == ([['systemctl', 'is-active', '--quiet', unit]] +
                      ([['systemctl', 'stop', unit]] if active else []) + ['create'])


@pytest.mark.parametrize('dry', [False, True])
def test_resume_live_pane_never_probes_scope(tmp_path, dry):
    manifest([entry('lazy')])
    rr.tmux_session.has_session.return_value = True
    a = args(tmp_path)
    a.dry_run = dry
    assert rr.resume(a) == 0
    rr.subprocess.run.assert_not_called()
    rr.tmux_session.create.assert_not_called()


def test_resume_dry_run_probes_but_does_not_stop_scope(tmp_path, capsys):
    path = manifest([entry('lazy')])
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], 0)
    a = args(tmp_path)
    a.dry_run = True
    assert rr.resume(a) == 0
    rr.subprocess.run.assert_called_once_with(
        ['systemctl', 'is-active', '--quiet', 'org-cto-1234abcd.scope'],
        capture_output=True, timeout=30)
    assert 'systemctl stop org-cto-1234abcd.scope' in capsys.readouterr().out
    rr.tmux_session.create.assert_not_called()
    assert path.exists()


def test_scope_stop_failure_retains_manifest_and_retry_skips_live_rows(tmp_path, capsys):
    path = manifest([entry('lazy', role='cfo'), entry('lazy')])
    live = {'cfo-1234abcd'}
    rr.tmux_session.has_session.side_effect = lambda name: name in live
    def execute(command, **kwargs):
        if command[:2] == ['systemctl', 'stop']:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)
    rr.subprocess.run.side_effect = execute
    assert rr.resume(args(tmp_path)) == 1
    assert 'could not stop leftover scope: org-cto-1234abcd.scope' in capsys.readouterr().out
    rr.tmux_session.create.assert_not_called()
    assert path.exists()
    assert (rr.STATE / 'pending-contabo.json').exists()
    rr.subprocess.run.side_effect = None
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], 3)
    rr.tmux_session.create.side_effect = lambda name, *a: live.add(name)
    assert rr.resume(args(tmp_path)) == 0
    assert rr.tmux_session.create.call_args.args[0] == 'cto-1234abcd'
    rr.tmux_session.create.assert_called_once()
    assert not path.exists()
    assert not (rr.STATE / 'pending-contabo.json').exists()


@pytest.mark.parametrize('name', ['CTO (Kavin)', 'CTO\n' + 'ยาว ' * 100])
def test_missing_clevel_gets_resume_command_card(tmp_path, name):
    owner = entry()
    owner['name'] = name
    manifest([owner, entry(role='project_head')])
    rr.live_sessions.read_registry.return_value = [dict(role='project_head', sid='1234abcd')]
    assert rr.report(args(tmp_path, notify=True)) == 1
    command = commands()[0]
    assert command[:4] == ['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'create']
    options = dict(zip(command[4::2], command[5::2]))
    assert options == {
        '--host': 'contabo', '--role': 'cto', '--session': 'cto-1234abcd',
        '--command': 'bash scripts/hub/org-python.sh tools/restart_run.py --host contabo resume',
        '--cwd': '/opt/MoonieXHQ/Agents/Core', '--risk': 'amber',
        '--why': options['--why'], '--expected': 'กลับมา 2/2',
    }
    assert len(options['--why']) <= 90
    assert len(options['--why'].splitlines()) == 1
    assert 'กลับมา 1/2' in options['--why']


def test_prep_waits_until_saved_pane_is_gone(tmp_path):
    # session-kill records 'saved' at once and kills tmux a few seconds later.
    alive = iter([True, True, True, False])
    rr.tmux_session.has_session.side_effect = lambda name: next(alive, False)
    assert rr.prep(args(tmp_path, [row('resume_full')])) == 0
    assert next(alive, 'drained') == 'drained'
    assert not any('kill-session' in c for c in commands())


def test_prep_kills_a_saved_pane_that_never_closes(tmp_path):
    state = {'killed': False}
    rr.tmux_session.has_session.side_effect = lambda name: not state['killed']
    rr.subprocess.run.side_effect = lambda c, **kw: state.update(killed='kill-session' in c)
    assert rr.prep(args(tmp_path, [row('resume_full')])) == 0
    assert ['tmux', 'kill-session', '-t', 'cto-1234abcd'] in commands()


def test_resume_ignores_a_stale_registry(tmp_path):
    manifest([entry('lazy')])
    rr.live_sessions.read_registry.return_value = [dict(role='cto', sid='1234abcd')]
    rr.tmux_session.has_session.side_effect = [False, True]
    assert rr.resume(args(tmp_path)) == 0
    rr.tmux_session.create.assert_called_once()


def test_report_counts_a_live_pane_before_the_registry_catches_up(tmp_path, capsys):
    manifest([entry()])
    rr.tmux_session.has_session.return_value = True
    assert rr.report(args(tmp_path)) == 0
    assert 'กลับมา 1/1' in capsys.readouterr().out


SID = "12ab34cd"
NAME = f"project_head-{SID}"


@pytest.fixture
def parked(tmp_path, monkeypatch):
    monkeypatch.setattr(spawn_ph, "LOCKS_DIR", tmp_path)
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    monkeypatch.setattr(tmux_session, "create", Mock())
    monkeypatch.setattr(tmux_session, "capture", lambda *a: "")
    monkeypatch.setattr(clevel_gate, "live_lock", lambda *a: None)
    monkeypatch.setattr(spawn_ph, "SPAWN_PROMPT_DELAY_S", 0)
    (tmp_path / f"{NAME}.project.parked").write_text("Console")
    (tmp_path / f"{NAME}.spawned_by.parked").write_text("cxo:cto:abcdef12")
    return tmp_path


def test_parked_records_resume_and_come_back_live(parked):
    assert spawn_ph.live_projects(parked) == {}  # a parked claim holds no project
    out = spawn_ph.resume(SID)
    assert (out["project"], out["owner"]) == ("Console", "cto-abcdef12")
    assert (parked / f"{NAME}.project").read_text() == "Console"
    assert (parked / f"{NAME}.spawned_by").read_text() == "cxo:cto:abcdef12"
    assert not list(parked.glob("*.parked"))


def test_parked_resume_still_refuses_a_project_taken_since(parked, monkeypatch):
    monkeypatch.setattr(spawn_ph, "live_projects", lambda d: {"console": "deadbeef"})
    with pytest.raises(spawn_ph.Refused, match="live Project Head #deadbeef"):
        spawn_ph.resume(SID)
    assert len(list(parked.glob("*.parked"))) == 2

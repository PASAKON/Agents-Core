"""No real tmux, launchers, sleeps, or hub access."""
import argparse
import json
from unittest.mock import Mock

import pytest

from tools import restart_run as rr


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(rr, 'STATE', tmp_path / 'restart')
    monkeypatch.setattr(rr, 'ROOT', tmp_path)
    monkeypatch.setattr(rr.subprocess, 'run', Mock())
    monkeypatch.setattr(rr.tmux_session, 'has_session', Mock(return_value=False))
    monkeypatch.setattr(rr.tmux_session, 'create', Mock())
    monkeypatch.setattr(rr.tmux_session, 'capture', Mock(return_value='❯\n────────'))
    monkeypatch.setattr(rr.tmux_session, 'tmux_bin', lambda: 'tmux')
    monkeypatch.setattr(rr.session_status, 'get', Mock(return_value={'status': 'saved'}))
    monkeypatch.setattr(rr.live_sessions, 'session_dirs', Mock(return_value=[]))
    monkeypatch.setattr(rr.live_sessions, 'read_registry', Mock(return_value=[]))
    monkeypatch.setattr(rr.restart_plan, 'build_plan', Mock(side_effect=AssertionError('unexpected planner')))
    monkeypatch.setattr(rr.restart_plan, 'measure', Mock(return_value={'in_turn': True}))
    monkeypatch.setattr(rr.time, 'sleep', Mock())
    monkeypatch.setattr(rr.time, 'monotonic', Mock(side_effect=range(10000)))


def row(action='resume_full', role='cto', sid='1234abcd'):
    return dict(session_id=sid, role=role, name=f'{role} #{sid}', action=action,
                project='demo', transcript_path='not-real', in_turn=True)


def args(tmp_path, rows=(), **kwargs):
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(host='contabo', sessions=list(rows), warnings=kwargs.pop('warnings', []))))
    return argparse.Namespace(host='contabo', plan=plan, dry_run=False, wait_max=0,
                              force=False, json=False, **kwargs)


def manifest(entries):
    rr.STATE.mkdir(exist_ok=True)
    path = rr.STATE / 'contabo-resume.json'
    path.write_text(json.dumps(entries))
    return path


def entry(mode='full', role='cto', sid='1234abcd'):
    return dict(sid=sid, role=role, name=role, project='demo', mode=mode)


def commands():
    return [call.args[0] for call in rr.subprocess.run.call_args_list]


@pytest.mark.parametrize('text,expected', [
    ('❯', True), ('❯ draft', False), ('❯ \x1b[2mtry this\x1b[22m', True),
    ('❯ \x1b[2mghost\x1b[0mreal', False), ('working...', False),
    ('❯\n multiline draft\n──────', False), ('❯\n──────\nstatus', True),
    ('❯\nworking...', False),
    ('❯ \x1b[38;2;100;100;100mdraft\x1b[0m', False),
])
def test_empty_input(text, expected):
    assert rr.empty_input(text) is expected


def test_draft_never_sends(tmp_path):
    rr.tmux_session.capture.return_value = '❯ important draft'
    assert rr.prep(args(tmp_path, [row()])) == 1
    assert commands() == []
    rr.tmux_session.capture.assert_called_with('cto-1234abcd:0.0', escapes=True)


@pytest.mark.parametrize('rows,warnings', [([row('wait')], []), ([], ['worker active'])])
def test_gate(tmp_path, capsys, rows, warnings):
    assert rr.prep(args(tmp_path, rows, warnings=warnings)) == 3
    assert 'ยังทำอยู่:' in capsys.readouterr().out
    assert commands() == []
    assert not (rr.STATE / 'contabo-resume.json').exists()


def test_gate_remeasures(tmp_path):
    r = row('wait')
    r.update(C=100, charter=None, open_tasks=[], incomplete=False)
    rr.restart_plan.measure.return_value = {'in_turn': False}
    assert rr.prep(args(tmp_path, [r])) == 0
    rr.restart_plan.measure.assert_called_once()


def test_force_gate(tmp_path):
    a = args(tmp_path, [row('wait')], warnings=['warning'])
    a.force = True
    assert rr.prep(a) == 0
    assert commands()[0][-1] == '/session-save'


def test_actions_and_manifest(tmp_path, monkeypatch):
    rows = [row(action, sid=f'{n:08x}') for n, action in enumerate(
        ['park', 'resume_lazy', 'resume_full', 'compact_then_resume', 'close'])]
    monkeypatch.setattr(rr, 'boundary', Mock(side_effect=['old', 'new']))
    assert rr.prep(args(tmp_path, rows)) == 0
    typed = [c[-1] for c in commands() if '-l' in c]
    assert typed == ['/session-save', '/session-save', '/session-save', '/compact', '/session-save']
    assert commands()[-1] == ['bash', 'scripts/session-kill.sh', '--status', 'closed', 'cto-00000004']
    data = json.loads((rr.STATE / 'contabo-resume.json').read_text())
    assert [r['mode'] for r in data] == ['lazy', 'full', 'full']
    assert [r['sid'] for r in data] == ['00000001', '00000002', '00000003']
    assert set(data[0]) == {'sid', 'role', 'name', 'project', 'mode'}


def test_service_managed(tmp_path, capsys):
    assert rr.prep(args(tmp_path, [row('compact_then_resume', role='coo')])) == 0
    assert not commands()
    assert 'service_managed' in capsys.readouterr().out
    assert json.loads((rr.STATE / 'contabo-resume.json').read_text()) == []


@pytest.mark.parametrize('action', ['park', 'compact_then_resume'])
def test_timeout_fallback(tmp_path, monkeypatch, capsys, action):
    rr.tmux_session.has_session.return_value = True
    rr.session_status.get.return_value = {'status': 'open'}
    monkeypatch.setattr(rr, 'boundary', lambda r: 'old')
    assert rr.prep(args(tmp_path, [row(action)])) == 0
    assert commands()[-1] == ['bash', 'scripts/session-kill.sh', '--status', 'force_saved', 'cto-1234abcd']
    assert 'force_saved:' in capsys.readouterr().out


@pytest.mark.parametrize('role,script,extra', [
    ('project_head', 'spawn-ph.sh', []), ('cto', 'spawn-cto.sh', ['--id', '1234abcd']),
    ('cfo', 'spawn-cxo.sh', ['--id', '1234abcd']),
    ('cgo', 'spawn-cxo.sh', ['--id', '1234abcd']),
    ('cmo', 'spawn-cxo.sh', ['--id', '1234abcd']),
])
def test_launcher(role, script, extra):
    command = rr.launcher(entry(role=role), 'mac')
    assert command[:2] == ['bash', f'scripts/{script}']
    assert command[command.index('--resume') + 1] == '1234abcd'
    if extra:
        assert command[-2:] == extra
    if script == 'spawn-cxo.sh':
        assert command[2:4] == ['--role', role]
    assert '--initial-prompt' not in command


def test_coo_no_launcher():
    with pytest.raises(ValueError, match='cannot preserve'):
        rr.launcher(entry(role='coo'), 'contabo')


@pytest.mark.parametrize('host', ['contabo', 'linux-other'])
@pytest.mark.parametrize('role', ['cto', 'cmo', 'cfo', 'cgo'])
def test_linux_launcher(tmp_path, host, role):
    manifest([entry('lazy', role)])
    path = rr.STATE / 'contabo-resume.json'
    path.rename(rr.STATE / f'{host}-resume.json')
    a = args(tmp_path)
    a.host = host
    rr.tmux_session.has_session.side_effect = [False, True]
    assert rr.resume(a) == 0
    variable = 'CTO_SESSION_ID' if role == 'cto' else 'CXO_SESSION_ID'
    script = 'scripts/cto-claude.sh' if role == 'cto' else f'scripts/cxo-claude.sh --role {role}'
    rr.tmux_session.create.assert_called_once_with(
        f'{role}-1234abcd', str(tmp_path),
        f'export {variable}=1234abcd && exec bash {script} --resume 1234abcd')
    assert not commands()


@pytest.mark.parametrize('host', ['mac', 'contabo', 'linux-other'])
def test_ph_launcher_per_host(host):
    assert rr.launcher(entry(role='project_head'), host) == [
        'bash', 'scripts/spawn-ph.sh', '--resume', '1234abcd']


def test_windows_clevel_unsupported():
    with pytest.raises(ValueError, match='Linux'):
        rr.launcher(entry(), 'winbox')


@pytest.mark.parametrize('mode,count', [('lazy', 0), ('full', 1)])
def test_resume_messages(tmp_path, mode, count):
    path = manifest([entry(mode)])
    rr.tmux_session.has_session.side_effect = [False, True]
    assert rr.resume(args(tmp_path)) == 0
    assert len([c for c in commands() if c[-1] == rr.MESSAGE]) == count
    assert not path.exists()
    assert list(rr.STATE.glob('*done*'))


def test_resume_idempotent(tmp_path):
    manifest([entry()])
    rr.live_sessions.read_registry.return_value = [dict(role='cto', sid='1234abcd')]
    assert rr.resume(args(tmp_path)) == 0
    assert rr.resume(args(tmp_path)) == 0
    assert commands() == []


def test_resume_draft(tmp_path):
    path = manifest([entry()])
    rr.tmux_session.has_session.side_effect = [False, True]
    rr.tmux_session.capture.return_value = '❯ draft'
    assert rr.resume(args(tmp_path)) == 1
    assert not commands()
    rr.tmux_session.create.assert_called_once()
    assert path.exists()


@pytest.mark.parametrize('back', [False, True])
def test_report(tmp_path, capsys, back):
    manifest([entry()])
    if back:
        rr.live_sessions.read_registry.return_value = [dict(role='cto', sid='1234abcd')]
    a = args(tmp_path)
    assert rr.report(a) == int(not back)
    assert f'กลับมา {int(back)}/1' in capsys.readouterr().out
    a.json = True
    rr.report(a)
    result = json.loads(capsys.readouterr().out)
    assert result == dict(back=int(back), total=1, missing=[] if back else ['cto'])


def test_dry_run(tmp_path):
    a = args(tmp_path, [row('compact_then_resume')])
    a.dry_run = True
    assert rr.prep(a) == 0
    assert not rr.STATE.exists()
    assert not commands()
    rr.tmux_session.capture.assert_not_called()


def test_fresh_plan(tmp_path):
    a = args(tmp_path)
    a.plan = None
    rr.restart_plan.build_plan.side_effect = None
    rr.restart_plan.build_plan.return_value = dict(host='contabo', sessions=[], warnings=[])
    assert rr.prep(a) == 0
    rr.restart_plan.build_plan.assert_called_once()


def test_report_latest_done(tmp_path, capsys):
    path = manifest([entry()])
    path.rename(rr.STATE / 'contabo-resume.done-20261016.json')
    assert rr.report(args(tmp_path)) == 1
    assert 'กลับมา 0/1' in capsys.readouterr().out


def test_resume_dry_run(tmp_path):
    path = manifest([entry()])
    a = args(tmp_path)
    a.dry_run = True
    assert rr.resume(a) == 0
    assert path.exists()
    assert not commands()
    rr.tmux_session.capture.assert_not_called()


def test_capture_preserves_escapes():
    rr.subprocess.run.return_value.returncode = 0
    rr.subprocess.run.return_value.stdout = '❯ \x1b[2mghost\x1b[22m'
    # Access the real helper, which the fixture mocks for runner tests.
    from importlib import reload
    module = reload(rr.tmux_session)
    module.capture('cto-1234abcd:0.0', escapes=True)
    assert '-e' in commands()[-1]


def test_workers_are_never_saved_killed_or_resumed():
    from tools import restart_run
    assert restart_run.worker({"role": "developer"})
    assert not restart_run.worker({"role": "project_head"})
    assert not restart_run.worker({"role": "cto"})

"""No real tmux, launchers, sleeps, or hub access."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from tools import restart_run as rr

REAL_RUN = subprocess.run
REAL_BUILD_PLAN = rr.restart_plan.build_plan  # `isolated` swaps it out for every test
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(rr, 'STATE', tmp_path / 'restart')
    monkeypatch.setattr(rr, 'ROOT', tmp_path)
    monkeypatch.setattr(rr.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess([], 3)))
    monkeypatch.setattr(rr.tmux_session, 'has_session', Mock(return_value=False))
    monkeypatch.setattr(rr.tmux_session, 'create', Mock())
    monkeypatch.setattr(rr.tmux_session, 'capture', Mock(return_value='❯\n────────'))
    monkeypatch.setattr(rr.tmux_session, 'tmux_bin', lambda: 'tmux')
    # Record typing in the same argv shape the assertions read.
    monkeypatch.setattr(rr.tmux_session, 'send_keys',
                        lambda t, x: rr.subprocess.run(['tmux', 'send-keys', '-t', t, '-l', x]))
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
    (rr.STATE / 'pending-contabo.json').write_text(json.dumps(dict(manifest=str(path))))
    return path


def entry(mode='full', role='cto', sid='1234abcd'):
    return dict(sid=sid, role=role, name=role, project='demo', mode=mode)


def commands():
    # Read-only scope probes are not launcher/typing actions.
    return [call.args[0] for call in rr.subprocess.run.call_args_list
            if call.args[0][:2] != ['systemctl', 'is-active']]


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
    # The pane stays until force_saved's session-kill has run.
    rr.tmux_session.has_session.side_effect = lambda name: not any(
        'session-kill.sh' in ' '.join(c) for c in commands())
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
    (rr.STATE / f'pending-{host}.json').write_text(json.dumps(
        dict(manifest=str(rr.STATE / f'{host}-resume.json'))))
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


@pytest.mark.parametrize('mode,count', [('lazy', 0), ('full', 1)])
def test_resume_messages(tmp_path, mode, count):
    path = manifest([entry(mode)])
    rr.tmux_session.has_session.side_effect = [False, True]
    assert rr.resume(args(tmp_path)) == 0
    assert len([c for c in commands() if c[-1] == rr.MESSAGE]) == count
    assert not path.exists()
    assert list(rr.STATE.glob('*done*'))
    assert not (rr.STATE / 'pending-contabo.json').exists()


def test_resume_idempotent(tmp_path):
    manifest([entry()])
    rr.tmux_session.has_session.return_value = True
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
    assert (rr.STATE / 'pending-contabo.json').exists()


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


@pytest.mark.parametrize('marker_present', [False, True])
@pytest.mark.parametrize('hours,dry', [(7, False), (1, False), (7, True)])
def test_prep_pending_manifest_age(tmp_path, monkeypatch, capsys, marker_present, hours, dry):
    current = rr.now()
    monkeypatch.setattr(rr, 'now', lambda: current)
    timestamp = current - timedelta(hours=hours)
    path = manifest([entry()])
    marker = rr.STATE / 'pending-contabo.json'
    if marker_present:
        marker.write_text(json.dumps(dict(manifest=str(path), timestamp=timestamp.isoformat())))
    else:
        marker.unlink()
        os.utime(path, (timestamp.timestamp(), timestamp.timestamp()))
    before = {p.name: p.read_bytes() for p in rr.STATE.iterdir()}
    a = args(tmp_path)
    a.dry_run = dry
    if hours < rr.STALE_HOURS:
        with pytest.raises(ValueError, match='pending resume manifest exists'):
            rr.prep(a)
        assert path.read_bytes() == before[path.name]
        assert marker.exists() == marker_present
        assert not list(rr.STATE.glob('*stale-*'))
    else:
        assert rr.prep(a) == 0
        if dry:
            assert {p.name: p.read_bytes() for p in rr.STATE.iterdir()} == before
            assert 'would retire stale manifest:' in capsys.readouterr().out
        else:
            stale, = rr.STATE.glob('*stale-*')
            assert stale.read_bytes() == before[path.name]
            assert json.loads(path.read_text()) == []
            assert json.loads(marker.read_text())['timestamp'] == current.isoformat()
            assert f'retired stale manifest: {stale} (from {timestamp.isoformat()})' in capsys.readouterr().out
    assert not commands()


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
    assert (rr.STATE / 'pending-contabo.json').exists()
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


def test_marker_written_before_closing(tmp_path, monkeypatch):
    def check(*args, **kwargs):
        marker = json.loads((rr.STATE / 'pending-contabo.json').read_text())
        assert Path(marker['manifest']).exists()
        assert marker['timestamp']
    monkeypatch.setattr(rr.subprocess, 'run', Mock(side_effect=check))
    assert rr.prep(args(tmp_path, [row('close')])) == 0
    rr.subprocess.run.assert_called_once()


def test_no_marker_noop_even_with_manifest(tmp_path):
    path = manifest([entry()])
    (rr.STATE / 'pending-contabo.json').unlink()
    assert rr.resume(args(tmp_path)) == 0
    assert path.exists()
    assert not commands()
    rr.live_sessions.read_registry.assert_not_called()


@pytest.mark.parametrize('dry', [False, True])
def test_clean_selection(tmp_path, monkeypatch, capsys, dry):
    rows = []
    for action in ['park', 'close', 'resume_lazy', 'resume_full', 'compact_then_resume', 'wait']:
        r = row(action, role='project_head', sid=f'{len(rows):08x}')
        r['in_turn'] = False
        rows.append(r)
    for role in ['cto', 'cfo', 'cmo', 'cgo', 'coo', 'developer']:
        r = row('park', role=role)
        r['in_turn'] = False
        rows.append(r)
    rows[0]['status'] = 'saved'
    rows.extend([dict(rows[0], in_turn=True), dict(rows[0], service_managed=True),
                 dict(rows[0], name='wd-task'), dict(rows[0], incomplete=True),
                 dict(rows[0], status='open', sid='0000000f')])
    rr.restart_plan.build_plan.side_effect = None
    rr.restart_plan.build_plan.return_value = dict(host='contabo', sessions=rows)
    monkeypatch.setattr(rr, 'memory', lambda: {'MemFree_kB': 42, 'SwapFree_kB': 12})
    monkeypatch.setattr(rr, 'relay_open', lambda: None)
    a = args(tmp_path, chrome=False)
    a.dry_run, a.json = dry, True
    assert rr.clean(a) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result['events']) == 3
    assert result['before'] == result['after']
    assert commands() == ([] if dry else [
        ['bash', 'scripts/session-kill.sh', '--status', 'saved', 'project_head-00000000'],
        ['bash', 'scripts/session-kill.sh', '--status', 'closed', 'project_head-00000001']])


@pytest.mark.parametrize('relay,chrome,restarts', [(True, False, False), (True, True, False),
    (None, False, False), (None, True, True), (False, False, True)])
def test_clean_chrome(tmp_path, monkeypatch, relay, chrome, restarts):
    rr.restart_plan.build_plan.side_effect = None
    rr.restart_plan.build_plan.return_value = dict(host='contabo', sessions=[])
    monkeypatch.setattr(rr, 'relay_open', lambda: relay)
    assert rr.clean(args(tmp_path, chrome=chrome)) == 0
    assert commands() == ([['docker', 'restart', 'neko-pilot']] if restarts else [])


@pytest.mark.parametrize('prep_status', [0, 1, 3])
def test_restart_shell_prep_gate(tmp_path, prep_status):
    scripts = tmp_path / 'scripts'
    (scripts / 'hub').mkdir(parents=True)
    (scripts / 'org-restart.sh').write_text((REPO / 'scripts/org-restart.sh').read_text())
    (scripts / 'hub/org-python.sh').write_text(f'exit {prep_status}\n')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    mock = bindir / 'systemd-run'
    mock.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$CALL_LOG"\n')
    mock.chmod(0o755)
    log = tmp_path / 'calls'
    result = REAL_RUN(['bash', str(scripts / 'org-restart.sh'), 'contabo'],
                      env={**os.environ, 'PATH': f'{bindir}:' + os.environ['PATH'],
                           'CALL_LOG': str(log)}, capture_output=True, text=True)
    assert result.returncode == prep_status
    if prep_status:
        assert not log.exists()
        assert f'prep exited {prep_status}' in result.stdout
    else:
        assert '--on-active=90\nsystemctl\nreboot\n' in log.read_text()


def test_direct_script_help():
    result = REAL_RUN(['bash', 'scripts/hub/org-python.sh', 'tools/restart_run.py', '--help'],
                      cwd=REPO, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'clean' in result.stdout


@pytest.mark.parametrize('missing', [False, True])
def test_report_notification(tmp_path, missing):
    manifest([entry(role='project_head')])
    if not missing:
        rr.live_sessions.read_registry.return_value = [dict(role='project_head', sid='1234abcd')]
    a = args(tmp_path, notify=True)
    assert rr.report(a) == int(missing)
    command = commands()[0]
    assert command[:4] == ['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'ask']
    assert command[command.index('--role') + 1] == 'project_head'
    assert command[command.index('--session') + 1] == 'project_head-1234abcd'
    assert command[-4:] == ['--option', 'รับทราบ', '--option',
                            'ดูรายชื่อที่ขาด' if missing else 'ดูรายงาน']
    lines = (command[command.index('--question') + 1] + '\n' +
             command[command.index('--why') + 1]).splitlines()
    assert len(lines) <= 5
    assert all(len(line) <= 90 for line in lines)


@pytest.mark.parametrize('missing', [False, True])
def test_report_notification_prefers_c_level(tmp_path, missing):
    manifest([entry(role='project_head'), entry(role='cto'), entry(role='cmo')])
    rr.tmux_session.has_session.return_value = not missing
    assert rr.report(args(tmp_path, notify=True)) == int(missing)
    command = commands()[0]
    assert command[3] == ('create' if missing else 'ask')
    assert command[command.index('--role') + 1] == 'cto'
    assert command[command.index('--session') + 1] == 'cto-1234abcd'


def test_report_notification_empty_manifest(tmp_path):
    manifest([])
    assert rr.report(args(tmp_path, notify=True)) == 0
    assert '--role' not in commands()[0]
    assert '--session' not in commands()[0]


@pytest.mark.parametrize('missing', [False, True])
@pytest.mark.parametrize('error', [OSError('no notifier'),
    subprocess.CalledProcessError(1, ['ask_run.py']),
    subprocess.TimeoutExpired(['ask_run.py'], 300)])
def test_report_notification_failure(tmp_path, capsys, missing, error):
    manifest([entry(role='cto', sid=f'{i:08x}') for i in range(6)])
    rr.tmux_session.has_session.return_value = not missing
    rr.subprocess.run.side_effect = error
    assert rr.report(args(tmp_path, notify=True)) == 2
    out = capsys.readouterr().out
    assert f"กลับมา {0 if missing else 6}/6" in out
    assert f'notify failed: {error}' in out


def test_clean_refuses_pending_restart(tmp_path):
    manifest([])
    with pytest.raises(ValueError, match='pending restart'):
        rr.clean(args(tmp_path, chrome=False))
    assert not commands()


def test_clean_dry_chrome_never_runs(tmp_path, monkeypatch):
    rr.restart_plan.build_plan.side_effect = None
    rr.restart_plan.build_plan.return_value = dict(host='contabo', sessions=[])
    monkeypatch.setattr(rr, 'relay_open', lambda: False)
    a = args(tmp_path, chrome=True)
    a.dry_run = True
    assert rr.clean(a) == 0
    assert not commands()


def test_relay_open_reads_console_cli(monkeypatch):
    def fake(out=None, exc=None):
        def run(*a, **k):
            if exc:
                raise exc
            return type('R', (), {'stdout': out})()
        return run
    monkeypatch.setattr(rr.subprocess, 'run', fake('(no open requests)\n'))
    assert rr.relay_open() is False
    monkeypatch.setattr(rr.subprocess, 'run', fake('req-1 open google\n'))
    assert rr.relay_open() is True
    monkeypatch.setattr(rr.subprocess, 'run', fake(exc=OSError('no node')))
    assert rr.relay_open() is None


def _shell(tmp_path, *argv, fail='', prep_marker=False):
    """Run a copy of org-restart.sh with HOME unset and a logging org-python.sh."""
    scripts = tmp_path / 'scripts'
    (scripts / 'hub').mkdir(parents=True)
    (scripts / 'org-restart.sh').write_text((REPO / 'scripts/org-restart.sh').read_text())
    (scripts / 'hub/org-python.sh').write_text(
        'echo "$HOME|$*" >> "$CALL_LOG"\n'
        + ('case " $* " in *" prep "*) echo "{\\"run\\": $$}" > state/restart/pending-contabo.json;; esac\n'
           if prep_marker else '') +
        'case " $* " in *" $FAIL "*) exit 4;; esac\n')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    (bindir / 'systemd-run').write_text('#!/bin/sh\necho "systemd-run $*" >> "$CALL_LOG"\n')
    (bindir / 'systemd-run').chmod(0o755)
    log = tmp_path / 'calls'
    env = {k: v for k, v in os.environ.items() if k != 'HOME'}
    env.update(PATH=f'{bindir}:' + os.environ['PATH'], CALL_LOG=str(log), FAIL=fail or 'never')
    result = REAL_RUN(['bash', str(scripts / 'org-restart.sh'), 'contabo', *argv],
                      env=env, capture_output=True, text=True)
    return result, log.read_text().splitlines() if log.exists() else []


def test_restart_shell_sets_home_when_systemd_leaves_it_unset(tmp_path):
    result, calls = _shell(tmp_path, '--dry-run')
    assert result.returncode == 0, result.stdout + result.stderr
    home = calls[0].split('|')[0]
    assert home and home != '/.config'
    assert 'prep --wait-max 600 --dry-run' in calls[0]
    assert not any(c.startswith('systemd-run') for c in calls)
    assert 'would reboot' in result.stdout


def test_restart_shell_sessions_only_resumes_without_reboot(tmp_path):
    result, calls = _shell(tmp_path, '--sessions-only')
    assert result.returncode == 0, result.stdout + result.stderr
    assert [c.split('|')[1].split()[-1] for c in calls] == ['600', 'resume', '--notify']
    assert not any(c.startswith('systemd-run') for c in calls)


@pytest.mark.parametrize('mode', [('--sessions-only',), ()])
def test_restart_shell_rolls_back_when_prep_fails(tmp_path, mode):
    result, calls = _shell(tmp_path, *mode, fail='prep', prep_marker=True)
    assert result.returncode == 4
    assert calls[-1].endswith('--host contabo resume')
    assert not any('--notify' in c or c.startswith('systemd-run') for c in calls)


@pytest.mark.parametrize('preexisting', [False, True])
def test_restart_shell_failed_prep_does_not_resume_old_manifest(tmp_path, preexisting):
    if preexisting:
        marker = tmp_path / 'state/restart/pending-contabo.json'
        marker.parent.mkdir(parents=True)
        marker.write_text('{}')
    result, calls = _shell(tmp_path, '--sessions-only', fail='prep')
    assert result.returncode == 4
    assert len(calls) == 1
    assert ('fallback resume skipped: marker predates this run' in result.stdout) == preexisting


def test_restart_shell_resumes_when_prep_replaced_stale_marker(tmp_path):
    marker = tmp_path / 'state/restart/pending-contabo.json'
    marker.parent.mkdir(parents=True)
    marker.write_text('{}')
    result, calls = _shell(tmp_path, '--sessions-only', fail='prep', prep_marker=True)
    assert result.returncode == 4
    assert calls[-1].endswith('--host contabo resume')
    assert 'marker predates' not in result.stdout


@pytest.mark.parametrize('body', ['naive', 'no_timestamp', 'bad_json'])
def test_prep_odd_marker_ages_out(tmp_path, monkeypatch, body):
    current = rr.now()
    monkeypatch.setattr(rr, 'now', lambda: current)
    old = current - timedelta(hours=7)
    path = manifest([entry()])
    marker = rr.STATE / 'pending-contabo.json'
    marker.write_text({'naive': json.dumps(dict(timestamp=old.replace(tzinfo=None).isoformat())),
                       'no_timestamp': '{}', 'bad_json': '{'}[body])
    for p in (path, marker):
        os.utime(p, (old.timestamp(), old.timestamp()))
    assert abs((rr.pending_since(marker, path) - old).total_seconds()) < 1


def test_resume_unit_sets_home():
    assert 'Environment=HOME=/root' in (REPO / 'deploy/systemd/org-resume.service').read_text()


@pytest.fixture
def real_planner(monkeypatch):
    """The real build_plan on an empty host; only the `ask_run.py list` subprocess is faked."""
    from lib import config
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rr.restart_plan, 'build_plan', REAL_BUILD_PLAN)
    monkeypatch.setattr(rr.restart_plan, 'session_dirs', lambda host: [])
    monkeypatch.setattr(rr.restart_plan, 'read_registry', lambda dirs: [])
    monkeypatch.setattr(rr.restart_plan, 'read_hub', lambda: {'c_level_sessions': [], 'tasks': []})


def prep_fresh_plan(stdout, returncode=0):
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], returncode, stdout, '')
    return rr.prep(argparse.Namespace(host='contabo', plan=None, dry_run=False, wait_max=0,
                                      force=False, json=False))


def test_prep_stops_for_a_running_card(real_planner, capsys):
    assert prep_fresh_plan('[{"id": "RUN-20261027-0001", "status": "running"}]') == 3
    assert 'ยังทำอยู่: Do not cut: run card RUN-20261027-0001 (running)' in capsys.readouterr().out
    assert not [c for c in commands() if c[:2] != ['bash', 'scripts/hub/org-python.sh']]


@pytest.mark.parametrize('stdout,returncode', [('[]', 1), ('not json', 0), ('{"asks": []}', 0)])
def test_prep_stops_when_run_cards_are_unreadable(real_planner, capsys, stdout, returncode):
    assert prep_fresh_plan(stdout, returncode) == 3
    assert ('ยังทำอยู่: Run cards unavailable; a running card cannot be ruled out.'
            in capsys.readouterr().out)


def test_prep_says_nothing_about_cards_when_none_run(real_planner, capsys):
    prep_fresh_plan('[]')  # still 3: an empty registry is its own warning
    out = capsys.readouterr().out
    assert 'run card' not in out.lower()
    assert 'Run cards unavailable' not in out


# ---- winbox (SafeRestart on Windows Terminal tabs) ------------------------------------
# No real wake.ps1, wt, pc_lease or Windows API: every win_* edge is replaced or mocked.
WUUID = '0f0e0d0c-aaaa-bbbb-cccc-1234567890ab'
SID_A, SID_B = '1234abcd', 'abcd1234'


@pytest.fixture
def winbox(monkeypatch, tmp_path):
    """The console session, the lease free, every tab found: returns the wake mock."""
    wake = Mock(return_value=(0, 'ok'))
    monkeypatch.setattr(rr, 'win_session_id', lambda: 1)
    monkeypatch.setattr(rr, 'win_gate', Mock(return_value=True))
    monkeypatch.setattr(rr, 'win_wake', wake)
    monkeypatch.setattr(rr, 'win_live', Mock(return_value=set()))
    monkeypatch.setattr(rr, 'win_wt_running', lambda: False)
    monkeypatch.setattr(rr, 'win_boot_time', lambda: None)
    monkeypatch.setattr(rr, 'win_hub_ph', Mock(return_value=(None, 'the hub is not reachable in tests')))
    monkeypatch.setattr(rr.session_status, 'record_close', Mock())
    monkeypatch.setenv('LOCALAPPDATA', r'C:\Users\x\AppData\Local')
    return wake


def wrow(action='resume_full', role='cto', sid=SID_A):
    return dict(row(action, role, sid), uuid=WUUID)


def wargs(tmp_path, rows=(), **kwargs):
    plan = tmp_path / 'plan.json'
    plan.write_text(json.dumps(dict(host='winbox', sessions=list(rows), warnings=kwargs.pop('warnings', []))))
    return argparse.Namespace(host='winbox', plan=plan, dry_run=False, wait_max=0,
                              force=False, json=False, **kwargs)


def wentry(mode='full', role='cto', sid=SID_A, **extra):
    return {**entry(mode, role, sid), 'uuid': WUUID, 'lane': None, 'spawned_by': None, **extra}


def wmanifest(entries):
    rr.STATE.mkdir(exist_ok=True)
    path = rr.STATE / 'winbox-resume.json'
    path.write_text(json.dumps(entries))
    (rr.STATE / 'pending-winbox.json').write_text(json.dumps(dict(manifest=str(path))))
    return path


def wt_path():
    return str(Path(os.environ['LOCALAPPDATA']) / 'Microsoft/WindowsApps/wt.exe')


def typed_texts(wake):
    return [c.args[1] for c in wake.call_args_list if not c.args[2]]


@pytest.mark.parametrize('running,window', [(False, 'new'), (True, '0')])
def test_winbox_launcher_clevel(winbox, monkeypatch, tmp_path, running, window):
    monkeypatch.setattr(rr, 'win_wt_running', lambda: running)
    assert rr.launcher(wentry(), 'winbox') == [
        wt_path(), '-w', window, 'nt', '--title', f'cto #{SID_A}', '-d', str(tmp_path),
        'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(tmp_path / 'windows' / 'cxo-claude.ps1'), '-Role', 'cto', '-Session', SID_A,
        '--resume', WUUID]


def test_winbox_launcher_without_uuid_resumes_by_session_id(winbox):
    assert rr.launcher(dict(entry(), lane=None), 'winbox')[-2:] == ['--resume', SID_A]


def test_winbox_launcher_project_head(winbox):
    command = rr.launcher(wentry(role='project_head', lane='cto'), 'winbox')
    assert command[command.index('-Role'):] == [
        '-Role', 'project_head', '-Session', SID_A, '-Lane', 'cto', '-Project', 'demo', '--resume', WUUID]


def test_winbox_launcher_project_head_needs_its_lane(winbox):
    with pytest.raises(ValueError, match='lane'):
        rr.launcher(wentry(role='project_head'), 'winbox')


def test_winbox_launcher_coo_has_none(winbox):
    with pytest.raises(ValueError, match='cannot preserve'):
        rr.launcher(wentry(role='coo'), 'winbox')


def test_winbox_send_types_through_wake_not_tmux(winbox):
    assert rr.send(entry(), '/session-save', False, 'winbox') is True
    assert [c.args for c in winbox.call_args_list] == [(entry(), '/session-save', False)]
    rr.win_gate.assert_called_once()
    rr.tmux_session.capture.assert_not_called()
    assert not commands()


def test_winbox_send_dry_run_types_nothing(winbox, capsys):
    assert rr.send(entry(), '/session-save', True, 'winbox') is True
    assert f'type into tab #{SID_A}: /session-save' in capsys.readouterr().out
    winbox.assert_not_called()
    rr.win_gate.assert_not_called()


@pytest.mark.parametrize('gate,wake,text', [
    (False, (0, 'ok'), '/session-save'),                 # the CEO holds the PC, or the farm is on
    (True, (3, 'foreground check refused'), '/x'),       # wake.ps1 withheld Enter
    (True, (2, 'no tab'), '/x'),
    (True, (4, 'session 0'), '/x'),
    (True, (0, 'ok'), 'ระบบ restart เสร็จแล้ว'),         # wake.ps1 types printable ASCII only
])
def test_winbox_send_refusals_return_false(winbox, capsys, gate, wake, text):
    rr.win_gate.return_value = gate
    winbox.return_value = wake
    assert rr.send(entry(), text, False, 'winbox') is False
    assert 'draft_or_not_ready' in capsys.readouterr().out or not gate
    if not text.isascii():
        rr.win_gate.assert_not_called()
        winbox.assert_not_called()


def test_win_wake_argv(monkeypatch, tmp_path):
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], 0, 'sent\n', '')
    assert rr.win_wake(entry(), '/session-save', False) == (0, 'sent')
    assert rr.subprocess.run.call_args.args[0] == [
        'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
        str(tmp_path / 'windows' / 'wake.ps1'), '-Title', f'#{SID_A}', '-Marker', '/session-save', '-Contains']
    rr.win_wake(entry(), 'preflight', True)
    assert rr.subprocess.run.call_args.args[0][-1] == '-DryRun'


@pytest.mark.parametrize('code,expected', [(0, True), (3, False)])
def test_win_gate_asks_the_lease(code, expected):
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], code, '', 'REFUSED')
    assert rr.win_gate() is expected
    assert rr.subprocess.run.call_args.args[0] == [*rr.WIN_LEASE, 'gate', '--as', rr.WIN_LEASE_WHO]


NOW = datetime(2026, 10, 27, 9, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize('record,since,expected', [
    ({'status': 'saved', 'closed_at': '2026-10-27T09:05:00+00:00'}, NOW, True),
    ({'status': 'saved', 'closed_at': NOW + timedelta(minutes=1)}, NOW, True),
    ({'status': 'saved', 'closed_at': '2026-10-27T08:00:00+00:00'}, NOW, False),   # an old save
    ({'status': 'saved', 'closed_at': 'garbage'}, NOW, False),
    ({'status': 'saved', 'closed_at': None}, NOW, False),
    ({'status': 'active', 'closed_at': '2026-10-27T09:05:00+00:00'}, NOW, False),
    ({'status': 'saved'}, None, True),
    (None, NOW, False),
])
def test_winbox_saved_needs_a_record_newer_than_the_command(record, since, expected):
    rr.session_status.get.return_value = record
    assert rr.saved(entry(), 'winbox', since) is expected


def test_winbox_saved_ignores_tmux():
    rr.session_status.get.return_value = {'status': 'saved'}
    rr.tmux_session.has_session.return_value = True
    assert rr.saved(entry(), 'winbox') is True    # contabo would wait for the pane to go
    rr.tmux_session.has_session.assert_not_called()


def test_winbox_gone_never_kills(winbox, capsys):
    winbox_live = {('cto', SID_A)}
    rr.win_live.return_value = winbox_live
    assert rr.gone(entry(), 'winbox') is False
    assert 'live_until_reboot: cto' in capsys.readouterr().out
    assert not commands()
    rr.win_live.return_value = set()
    assert rr.gone(entry(), 'winbox') is True


def test_win_live_rejects_a_reused_pid(tmp_path, monkeypatch):
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    (sessions / '4242.json').write_text('{"procStart": 111}')
    monkeypatch.setattr(rr.live_sessions, 'session_dirs', lambda host: [sessions])
    monkeypatch.setattr(rr.live_sessions, 'read_registry',
                        lambda dirs: [dict(role='cto', sid=SID_A, pid=4242)])
    for actual, expected in [(111, {('cto', SID_A)}), (222, set()), (None, {('cto', SID_A)})]:
        monkeypatch.setattr(rr, 'win_started', lambda pid, actual=actual: actual)
        assert rr.win_live() == expected


def test_win_owner_reads_only_a_well_formed_record(tmp_path):
    locks = tmp_path / 'state/locks'
    locks.mkdir(parents=True)
    (locks / f'project_head-{SID_A}.spawned_by').write_text('cxo:cmo:cmo-08d5df68\n')
    (locks / f'project_head-{SID_B}.spawned_by').write_text('root:cmo:x; rm -rf')
    assert rr.win_owner(SID_A) == 'cxo:cmo:cmo-08d5df68'
    assert rr.win_owner(SID_B) is None
    assert rr.win_owner('0badc0de') is None


@pytest.mark.parametrize('present,dry,written', [(False, False, True), (False, True, False), (True, False, False)])
def test_win_restore_owner_only_fills_a_gap(tmp_path, present, dry, written):
    path = tmp_path / 'state/locks' / f'project_head-{SID_A}.spawned_by'
    if present:
        path.parent.mkdir(parents=True)
        path.write_text('cxo:cmo:keep-me')
    rr.win_restore_owner(wentry(role='project_head', lane='cto', spawned_by='cxo:cto:cto-08d5df68'), dry)
    assert path.exists() is (present or written)
    if written:
        assert path.read_text().strip() == 'cxo:cto:cto-08d5df68'
    if present:
        assert path.read_text() == 'cxo:cmo:keep-me'


def test_win_restore_owner_ignores_other_roles_and_bad_records(tmp_path):
    rr.win_restore_owner(wentry(spawned_by='cxo:cto:cto-08d5df68'), False)                       # a C-level
    rr.win_restore_owner(wentry(role='project_head', spawned_by='nonsense'), False)
    rr.win_restore_owner(wentry(role='project_head'), False)
    assert not (tmp_path / 'state').exists()


@pytest.mark.parametrize('boot_after_lock,removed', [(True, True), (False, False), (None, False)])
def test_win_clear_stale_lock(tmp_path, monkeypatch, boot_after_lock, removed):
    lock = tmp_path / 'state/locks' / f'cto-{SID_A}.lock'
    lock.parent.mkdir(parents=True)
    lock.write_text('4242')
    os.utime(lock, (1000, 1000))
    monkeypatch.setattr(rr, 'win_boot_time', lambda: None if boot_after_lock is None else
                        (2000 if boot_after_lock else 500))
    rr.win_clear_stale_lock(entry(), False)
    assert (not lock.exists()) is removed


def test_win_clear_stale_lock_dry_run_keeps_it(tmp_path, monkeypatch):
    lock = tmp_path / 'state/locks' / f'cto-{SID_A}.lock'
    lock.parent.mkdir(parents=True)
    lock.write_text('4242')
    os.utime(lock, (1000, 1000))
    monkeypatch.setattr(rr, 'win_boot_time', lambda: 2000)
    rr.win_clear_stale_lock(entry(), True)
    assert lock.exists()


def test_winbox_prep_saves_and_records_what_resume_needs(winbox, tmp_path):
    locks = tmp_path / 'state/locks'
    locks.mkdir(parents=True)
    (locks / f'project_head-{SID_B}.spawned_by').write_text('cxo:cto:cto-08d5df68')
    (locks / f'project_head-{SID_B}.project').write_text('LuminaSkies\n')
    rr.session_status.get.return_value = {'status': 'saved', 'closed_at': NOW + timedelta(days=1)}
    rows = [wrow('resume_full'), wrow('resume_lazy', 'project_head', SID_B), wrow('park', 'cmo', '0badc0de')]
    assert rr.prep(wargs(tmp_path, rows)) == 0
    # preflight on every tab (dry), then one /session-save per session
    assert [c.args[2] for c in winbox.call_args_list] == [True, True, True, False, False, False]
    assert typed_texts(winbox) == ['/session-save'] * 3
    data = json.loads((rr.STATE / 'winbox-resume.json').read_text())
    assert data == [
        dict(sid=SID_A, role='cto', name=f'cto #{SID_A}', project='demo', mode='full', uuid=WUUID,
             lane=None, spawned_by=None),
        dict(sid=SID_B, role='project_head', name=f'project_head #{SID_B}', project='demo', mode='lazy',
             uuid=WUUID, lane='cto', spawned_by='cxo:cto:cto-08d5df68')]
    assert (rr.STATE / 'pending-winbox.json').exists()
    rr.session_status.record_close.assert_not_called()    # /session-save wrote 'saved' itself
    assert not commands()                                 # no bash, no session-kill.sh


def test_winbox_prep_records_force_saved_without_killing(winbox, tmp_path, capsys):
    rr.session_status.get.return_value = {'status': 'active'}
    assert rr.prep(wargs(tmp_path, [wrow()])) == 0
    rr.session_status.record_close.assert_called_once_with(
        'cto', SID_A, 'force_saved', locks_dir=tmp_path / 'state/locks')
    out = capsys.readouterr().out
    assert f'force_saved: cto #{SID_A}' in out
    assert not commands()


def test_winbox_prep_ignores_a_saved_record_from_before_the_command(winbox, tmp_path):
    rr.session_status.get.return_value = {'status': 'saved', 'closed_at': NOW - timedelta(days=30)}
    assert rr.prep(wargs(tmp_path, [wrow()])) == 0
    rr.session_status.record_close.assert_called_once()
    assert rr.session_status.record_close.call_args.args[2] == 'force_saved'


def test_winbox_prep_close_records_closed(winbox, tmp_path):
    assert rr.prep(wargs(tmp_path, [wrow('close')])) == 0
    rr.session_status.record_close.assert_called_once_with(
        'cto', SID_A, 'closed', locks_dir=tmp_path / 'state/locks')
    assert typed_texts(winbox) == []
    assert json.loads((rr.STATE / 'winbox-resume.json').read_text()) == []


def test_winbox_prep_will_not_save_a_session_it_cannot_reopen(winbox, tmp_path, capsys):
    # a Project Head started by something other than cxo-claude.ps1: no owner record, no project
    rows = [wrow(), wrow('resume_full', 'project_head', SID_B)]
    assert rr.prep(wargs(tmp_path, rows)) == 1
    out = capsys.readouterr().out
    assert f'cannot_resume: project_head #{SID_B}' in out and 'cxo-claude.ps1' in out
    assert typed_texts(winbox) == [] and winbox.call_count == 0
    assert not (rr.STATE / 'pending-winbox.json').exists()
    rr.session_status.record_close.assert_not_called()


def test_winbox_prep_dry_run_shows_what_it_cannot_reopen(winbox, tmp_path, capsys):
    a = wargs(tmp_path, [wrow('resume_full', 'project_head', SID_B)])
    a.dry_run = True
    assert rr.prep(a) == 1
    assert 'cannot_resume' in capsys.readouterr().out


def test_winbox_prep_dry_run_types_and_writes_nothing(winbox, tmp_path, capsys):
    a = wargs(tmp_path, [wrow('compact_then_resume'), wrow('resume_lazy', 'cmo', SID_B), wrow('close', 'cfo', '0badc0de')])
    a.dry_run = True
    assert rr.prep(a) == 0
    out = capsys.readouterr().out
    assert f'type into tab #{SID_A}: /compact' in out
    assert f'type into tab #{SID_B}: /session-save' in out
    assert out.count('would preflight tab') == 2
    assert 'record force_saved in c_level_sessions' in out
    winbox.assert_not_called()
    rr.session_status.record_close.assert_not_called()
    assert not commands() and not rr.STATE.exists()


def test_winbox_prep_stops_before_saving_when_a_tab_is_missing(winbox, tmp_path, capsys):
    winbox.side_effect = lambda row_, text, dry: (2, 'no tab') if row_['session_id'] == SID_B else (0, 'ok')
    assert rr.prep(wargs(tmp_path, [wrow(), wrow('resume_full', 'cmo', SID_B)])) == 1
    assert typed_texts(winbox) == []                 # nothing was typed anywhere
    assert not (rr.STATE / 'pending-winbox.json').exists() and not (rr.STATE / 'winbox-resume.json').exists()
    assert f'tab_not_found: cmo #{SID_B}' in capsys.readouterr().out
    rr.session_status.record_close.assert_not_called()


def test_winbox_prep_stops_when_the_pc_is_not_ours(winbox, tmp_path):
    rr.win_gate.return_value = False
    assert rr.prep(wargs(tmp_path, [wrow()])) == 3
    winbox.assert_not_called()
    assert not (rr.STATE / 'pending-winbox.json').exists()


def test_winbox_prep_refuses_session_zero(winbox, monkeypatch, tmp_path):
    monkeypatch.setattr(rr, 'win_session_id', lambda: 0)
    with pytest.raises(ValueError, match='console session'):
        rr.prep(wargs(tmp_path, [wrow()]))
    winbox.assert_not_called()


def test_winbox_prep_failed_gate_during_typing_fails_the_prep(winbox, tmp_path):
    winbox.side_effect = lambda row_, text, dry: (0, 'ok') if dry else (3, 'Enter withheld')
    assert rr.prep(wargs(tmp_path, [wrow()])) == 1
    rr.session_status.record_close.assert_not_called()


def test_cards_checked_drops_only_the_run_card_warnings(monkeypatch):
    warnings = [rr.CARDS_UNAVAILABLE, f'{rr.CARD_RUNNING}RUN-1 (running)', 'Do not cut: tasks t1 (running)']
    monkeypatch.setattr(rr.restart_plan, 'build_plan',
                        lambda *a: dict(host='winbox', sessions=[], warnings=list(warnings)))
    assert rr.plan_for(argparse.Namespace(host='winbox'))['warnings'] == warnings
    assert rr.plan_for(argparse.Namespace(host='winbox', cards_checked=True))['warnings'] == [warnings[2]]


def test_card_warning_words_match_the_planner(real_planner):
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], 1, '', '')
    assert rr.CARDS_UNAVAILABLE in REAL_BUILD_PLAN('contabo', rr.now(), rr.STATE)['warnings']
    rr.subprocess.run.return_value = subprocess.CompletedProcess([], 0, '[{"id": "RUN-1"}]', '')
    assert f'{rr.CARD_RUNNING}RUN-1 (running)' in REAL_BUILD_PLAN('contabo', rr.now(), rr.STATE)['warnings']


def test_winbox_resume_opens_a_tab_per_session_and_types_once(winbox, tmp_path):
    path = wmanifest([wentry('full'), wentry('lazy', 'cmo', SID_B)])
    both = {('cto', SID_A), ('cmo', SID_B)}
    rr.win_live.side_effect = iter([set(), {('cto', SID_A)}, both])
    assert rr.resume(wargs(tmp_path)) == 0
    launched = [c for c in commands() if c[0] == wt_path()]
    assert [c[c.index('-Role') + 1] for c in launched] == ['cto', 'cmo']
    assert launched[0][-2:] == ['--resume', WUUID]
    assert typed_texts(winbox) == [rr.WIN_MESSAGE]       # the lazy session gets none
    rr.time.sleep.assert_called_once_with(rr.WIN_SETTLE_S)
    assert not path.exists() and list(rr.STATE.glob('winbox-resume.done-*.json'))
    assert not (rr.STATE / 'pending-winbox.json').exists()


def test_winbox_resume_restores_a_project_heads_owner_record_before_launching(winbox, tmp_path):
    # cxo-claude.ps1 deletes the record when claude exits and refuses a Project Head without it
    record = tmp_path / 'state' / 'locks' / f'project_head-{SID_B}.spawned_by'
    wmanifest([wentry('lazy', 'project_head', SID_B, project='Proj', lane='cto',
                      spawned_by='cxo:cto:c34459eb')])
    rr.win_live.side_effect = iter([set(), {('project_head', SID_B)}])
    on_disk_at_launch = []
    done = rr.subprocess.run.return_value
    rr.subprocess.run.side_effect = lambda *a, **k: on_disk_at_launch.append(record.exists()) or done
    assert rr.resume(wargs(tmp_path)) == 0
    assert on_disk_at_launch == [True]
    assert record.read_text().strip() == 'cxo:cto:c34459eb'
    launched = [c for c in commands() if c[0] == wt_path()][0]
    assert launched[launched.index('-Lane'):launched.index('-Lane') + 4] == ['-Lane', 'cto', '-Project', 'Proj']


def test_winbox_resume_never_overwrites_an_existing_owner_record(winbox, tmp_path):
    record = tmp_path / 'state' / 'locks' / f'project_head-{SID_B}.spawned_by'
    record.parent.mkdir(parents=True)
    record.write_text('cxo:cto:5ca1ab1e\n')
    wmanifest([wentry('lazy', 'project_head', SID_B, project='Proj', lane='cto',
                      spawned_by='cxo:cto:c34459eb')])
    rr.win_live.side_effect = iter([set(), {('project_head', SID_B)}])
    assert rr.resume(wargs(tmp_path)) == 0
    assert record.read_text().strip() == 'cxo:cto:5ca1ab1e'


def test_winbox_resume_skips_a_session_that_is_already_running(winbox, tmp_path, capsys):
    wmanifest([wentry('full')])
    rr.win_live.return_value = {('cto', SID_A)}
    assert rr.resume(wargs(tmp_path)) == 0
    assert 'already_live: cto' in capsys.readouterr().out
    assert not commands()
    winbox.assert_not_called()


def test_winbox_resume_keeps_the_manifest_when_the_message_is_refused(winbox, tmp_path):
    path = wmanifest([wentry('full')])
    rr.win_live.side_effect = iter([set(), {('cto', SID_A)}])
    winbox.return_value = (3, 'the CEO holds the PC')
    assert rr.resume(wargs(tmp_path)) == 1
    assert path.exists() and (rr.STATE / 'pending-winbox.json').exists()


def test_winbox_resume_reports_a_session_that_never_registers(winbox, tmp_path, capsys):
    wmanifest([wentry('full')])
    assert rr.resume(wargs(tmp_path)) == 1
    assert 'session did not become live' in capsys.readouterr().out
    winbox.assert_not_called()


def test_winbox_resume_refuses_session_zero(winbox, monkeypatch, tmp_path):
    monkeypatch.setattr(rr, 'win_session_id', lambda: 0)
    wmanifest([wentry('full')])
    with pytest.raises(ValueError, match='console session'):
        rr.resume(wargs(tmp_path))
    assert not commands()


def test_winbox_resume_dry_run_prints_the_tabs_and_changes_nothing(winbox, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rr, 'win_session_id', lambda: 0)    # a dry run may come over ssh
    path = wmanifest([wentry('full')])
    a = wargs(tmp_path)
    a.dry_run = True
    assert rr.resume(a) == 0
    out = capsys.readouterr().out
    assert wt_path() in out and f'type into tab #{SID_A}: {rr.WIN_MESSAGE}' in out
    assert not commands() and path.exists()
    winbox.assert_not_called()


def test_winbox_report_counts_registered_sessions_not_panes(winbox, tmp_path, capsys):
    wmanifest([wentry('full'), wentry('lazy', 'cmo', SID_B)])
    rr.win_live.return_value = {('cto', SID_A)}
    rr.tmux_session.has_session.return_value = True    # must not rescue the missing one
    a = wargs(tmp_path, notify=False)
    assert rr.report(a) == 1
    assert 'กลับมา 1/2\ncmo' in capsys.readouterr().out


def test_winbox_report_notify_uses_this_python_and_reports_no_token(winbox, tmp_path, capsys):
    wmanifest([wentry('full'), wentry('lazy', 'cmo', SID_B)])
    rr.win_live.return_value = {('cmo', SID_B)}
    rr.subprocess.run.side_effect = subprocess.CalledProcessError(3, ['ask_run.py'])
    assert rr.report(wargs(tmp_path, notify=True)) == 2
    out = capsys.readouterr().out
    assert 'notify failed:' in out
    first = rr.subprocess.run.call_args_list[0].args[0]
    assert first[:3] == [sys.executable, 'tools/ask_run.py', 'create'] and '--host' in first
    assert first[first.index('--command') + 1].endswith(r'windows\org-resume-logon.ps1')
    assert first[first.index('--cwd') + 1] == str(tmp_path)


def test_winbox_report_notify_all_back_asks_a_question(winbox, tmp_path):
    wmanifest([wentry('full')])
    rr.win_live.return_value = {('cto', SID_A)}
    assert rr.report(wargs(tmp_path, notify=True)) == 0
    first = commands()[0]
    assert first[:3] == [sys.executable, 'tools/ask_run.py', 'ask']
    assert first[first.index('--question') + 1].startswith('Restart winbox: ')


# ---- winbox: a Project Head that lost its owner record (rebuilt from the hub) ----------
HUB_PH = dict(project='LuminaSkies', lane='cto', spawned_by='cxo:cto:c34459eb')


class FakeHub:
    """The one query win_hub_ph makes, answered from `rows`."""
    def __init__(self, rows):
        self.rows, self.params = rows, None

    def execute(self, sql, params=()):
        assert 'FROM projects WHERE ph_session IN' in sql
        self.params = params
        return self

    def fetchall(self):
        return self.rows


def hub(monkeypatch, rows=(), url='postgres://hub', error=None):
    import contextlib
    from lib import db
    conn = FakeHub(list(rows))

    @contextlib.contextmanager
    def get_conn():
        if error:
            raise error
        yield conn
    monkeypatch.setattr(db, 'pg_url', lambda: url)
    monkeypatch.setattr(db, 'get_conn', get_conn)
    return conn


def hub_row(**extra):
    return {**dict(id='lumina-skies', name='LuminaSkies', lane='cto', owner_session='cto-c34459eb'), **extra}


def ph_entry(**extra):
    return {**wentry(role='project_head', sid=SID_B), 'name': f'project_head #{SID_B}',
            'project': None, 'lane': None, 'spawned_by': None, **extra}


def owner_files(tmp_path):
    locks = tmp_path / 'state/locks'
    return locks / f'project_head-{SID_B}.project', locks / f'project_head-{SID_B}.spawned_by'


@pytest.mark.parametrize('row_,expected', [
    (hub_row(), HUB_PH),
    # a name with a space cannot be started with, so the registry id stands in
    (hub_row(name='BLACK LIQUIDITY', id='black-liquidity', lane='cmo', owner_session='cmo-ef04792e'),
     dict(project='black-liquidity', lane='cmo', spawned_by='cxo:cmo:ef04792e')),
])
def test_win_hub_ph_reads_project_lane_and_owner(monkeypatch, row_, expected):
    conn = hub(monkeypatch, [row_])
    assert rr.win_hub_ph(SID_B) == (expected, '')
    assert conn.params == (SID_B, f'project_head-{SID_B}')


@pytest.mark.parametrize('rows,url,error,why', [
    ([], 'postgres://hub', None, 'no portfolio project'),
    ([hub_row(), hub_row(id='other')], 'postgres://hub', None, 'several portfolio projects'),
    ([hub_row(owner_session=None)], 'postgres://hub', None, 'no owner session'),
    ([hub_row(owner_session='cto-fresh')], 'postgres://hub', None, 'no owner session'),   # a placeholder, not a session
    ([hub_row(owner_session='cmo-c34459eb')], 'postgres://hub', None, 'no owner session'),  # another lane's session
    ([hub_row(lane='nobody')], 'postgres://hub', None, 'no usable lane'),
    ([hub_row(name='a b', id='c d')], 'postgres://hub', None, 'no name'),
    ([], None, None, 'ORG_DB_URL is unset'),
    ([], 'postgres://hub', OSError('down'), 'could not be read (OSError)'),
])
def test_win_hub_ph_gives_nothing_unless_every_field_is_known(monkeypatch, rows, url, error, why):
    hub(monkeypatch, rows, url, error)
    found, reason = rr.win_hub_ph(SID_B)
    assert found is None and why in reason


def test_win_rebuild_owner_writes_the_files_it_lacks(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rr, 'win_hub_ph', Mock(return_value=(HUB_PH, '')))
    e = ph_entry()
    rr.win_rebuild_owner(e, False)
    project_file, owner_file = owner_files(tmp_path)
    assert project_file.read_text() == 'LuminaSkies' and owner_file.read_text() == 'cxo:cto:c34459eb'
    assert (e['project'], e['lane'], e['spawned_by']) == ('LuminaSkies', 'cto', 'cxo:cto:c34459eb')
    assert f'rebuilt: project_head #{SID_B}' in capsys.readouterr().out
    assert rr.win_owner(SID_B) == 'cxo:cto:c34459eb'      # the record resume and cxo-claude.ps1 read


def test_win_rebuild_owner_dry_run_fills_the_entry_but_writes_nothing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rr, 'win_hub_ph', Mock(return_value=(HUB_PH, '')))
    e = ph_entry()
    rr.win_rebuild_owner(e, True)
    assert not any(p.exists() for p in owner_files(tmp_path))
    assert e['spawned_by'] == 'cxo:cto:c34459eb'
    assert 'would_rebuild' in capsys.readouterr().out


def test_win_rebuild_owner_writes_nothing_when_the_hub_does_not_know(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(rr, 'win_hub_ph', Mock(return_value=(None, 'no portfolio project names this session')))
    e = ph_entry()
    rr.win_rebuild_owner(e, False)
    assert not any(p.exists() for p in owner_files(tmp_path))
    assert (e['project'], e['lane'], e['spawned_by']) == (None, None, None)
    assert f'not_rebuilt: project_head #{SID_B}: no portfolio project' in capsys.readouterr().out


def test_win_rebuild_owner_writes_only_the_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(rr, 'win_hub_ph', Mock(return_value=(HUB_PH, '')))
    e = ph_entry(project='demo')
    rr.win_rebuild_owner(e, False)
    project_file, owner_file = owner_files(tmp_path)
    assert owner_file.exists() and not project_file.exists() and e['project'] == 'demo'


def test_win_rebuild_owner_never_overwrites_a_file_that_exists(tmp_path, monkeypatch, capsys):
    hub_ = Mock(return_value=(HUB_PH, ''))
    monkeypatch.setattr(rr, 'win_hub_ph', hub_)
    _, owner_file = owner_files(tmp_path)
    owner_file.parent.mkdir(parents=True)
    owner_file.write_text('garbage')
    rr.win_rebuild_owner(ph_entry(), False)
    assert owner_file.read_text() == 'garbage' and not hub_.called
    assert 'not_rebuilt' in capsys.readouterr().out


def test_win_rebuild_owner_leaves_a_complete_record_alone(tmp_path, monkeypatch, capsys):
    hub_ = Mock(return_value=(HUB_PH, ''))
    monkeypatch.setattr(rr, 'win_hub_ph', hub_)
    rr.win_rebuild_owner(ph_entry(project='demo', spawned_by='cxo:cto:c34459eb'), False)
    assert not hub_.called and f'owner_record_ok: project_head #{SID_B}' in capsys.readouterr().out


def test_winbox_prep_rebuilds_a_lost_owner_record_instead_of_cannot_resume(winbox, tmp_path, capsys):
    rr.win_hub_ph.return_value = (HUB_PH, '')
    rr.session_status.get.return_value = {'status': 'saved', 'closed_at': NOW + timedelta(days=1)}
    assert rr.prep(wargs(tmp_path, [wrow('resume_full', 'project_head', SID_B)])) == 0
    out = capsys.readouterr().out
    assert 'rebuilt:' in out and 'cannot_resume' not in out
    data = json.loads((rr.STATE / 'winbox-resume.json').read_text())
    assert (data[0]['project'], data[0]['lane'], data[0]['spawned_by']) == ('demo', 'cto', 'cxo:cto:c34459eb')
    assert owner_files(tmp_path)[1].read_text() == 'cxo:cto:c34459eb'


def test_winbox_prep_keeps_cannot_resume_when_the_hub_has_no_owner(winbox, tmp_path, capsys):
    assert rr.prep(wargs(tmp_path, [wrow(), wrow('resume_full', 'project_head', SID_B)])) == 1
    out = capsys.readouterr().out
    assert f'not_rebuilt: project_head #{SID_B}' in out and f'cannot_resume: project_head #{SID_B}' in out
    assert winbox.call_count == 0 and not any(p.exists() for p in owner_files(tmp_path))


def test_winbox_prep_dry_run_rebuilds_nothing_on_disk_but_shows_it(winbox, tmp_path, capsys):
    rr.win_hub_ph.return_value = (HUB_PH, '')
    a = wargs(tmp_path, [wrow('resume_full', 'project_head', SID_B)])
    a.dry_run = True
    assert rr.prep(a) == 0
    out = capsys.readouterr().out
    assert 'would_rebuild' in out and 'cannot_resume' not in out
    assert not any(p.exists() for p in owner_files(tmp_path))


# ---- winbox dry run: what a real run does with each session -------------------------------
def test_winbox_prep_dry_run_says_per_session_what_a_real_run_does(winbox, tmp_path, capsys):
    import re
    rows = [wrow('resume_full'), wrow('compact_then_resume', 'cmo', SID_B), wrow('park', 'cfo', '0badc0de'),
            wrow('close', 'cgo', 'c10c10c1'), wrow('resume_full', 'project_head', 'f00dcafe')]
    a = wargs(tmp_path, rows)
    a.dry_run = True
    assert rr.prep(a) == 1                              # the Project Head cannot be reopened
    out = capsys.readouterr().out
    assert '-- what a real run does, per session' in out
    for pattern in (rf'save\+reopen +cto #{SID_A}', rf'save\+reopen +cmo #{SID_B} .*\(/compact first\)',
                    r'save only \(park\) +cfo #0badc0de', r'close \(no reopen\) +cgo #c10c10c1',
                    r'cannot_resume +project_head #f00dcafe .*project_head-<sid>\.spawned_by'):
        assert re.search(pattern, out), pattern
    winbox.assert_not_called()


def test_winbox_prep_dry_run_with_a_session_mid_turn_still_lists_the_plan(winbox, tmp_path, capsys):
    import re
    a = wargs(tmp_path, [wrow('wait'), wrow('resume_full', 'cmo', SID_B)])
    a.dry_run = True
    assert rr.prep(a) == 3
    out = capsys.readouterr().out
    assert 'ยังทำอยู่' in out
    assert re.search(rf'wait +cto #{SID_A} .*mid-turn', out) and re.search(rf'save\+reopen +cmo #{SID_B}', out)
    winbox.assert_not_called()
    assert not rr.STATE.exists()


def test_winbox_prep_real_run_still_stops_at_a_session_mid_turn_without_the_table(winbox, tmp_path, capsys):
    assert rr.prep(wargs(tmp_path, [wrow('wait')])) == 3
    assert 'what a real run does' not in capsys.readouterr().out


def test_contabo_prep_dry_run_prints_no_winbox_plan(tmp_path, capsys):
    a = args(tmp_path, [row()])
    a.dry_run = True
    rr.prep(a)
    assert 'what a real run does' not in capsys.readouterr().out


# ---- scripts/winbox-restart.sh against a fake ssh/scp ----------------------------------------
SHA = '0123456789abcdef0123456789abcdef01234567'
FAKE_SSH = r'''#!/usr/bin/env python3
import base64, os, sys
fake = os.environ['FAKE_DIR']
def log(line):
    with open(os.path.join(fake, 'calls'), 'a') as f:
        f.write(line + '\n')
def put(name, text):
    with open(os.path.join(fake, name), 'w') as f:
        f.write(text)
def get(name, default=''):
    try:
        return open(os.path.join(fake, name)).read().strip()
    except OSError:
        return default
remote = sys.argv[-1]
if remote.startswith('powershell -NoProfile -NonInteractive -EncodedCommand '):
    ps = base64.b64decode(remote.rsplit(' ', 1)[1]).decode('utf-16-le')
    log('PS ' + ' '.join(ps.split()))
    if 'Register-ScheduledTask -TaskName' in ps and "'mooniex-restart-run'" in ps:
        verb = ps.split('-Verb ')[1].split()[0]
        put('verb', verb)
        code = os.environ.get('FAKE_RUN_EXIT', '0')
        put('run.exit', code)                      # the console-session task "ran" and finished
        if code == '0' and verb == 'register':
            put('logon_state', os.environ.get('FAKE_STATE_AFTER', 'Ready'))
        if code == '0' and verb == 'unregister':
            put('logon_state', 'not registered')
        print('started')
    elif 'Get-ScheduledTask' in ps:
        print(get('logon_state', 'not registered'))
    elif 'run.exit' in ps:
        print(get('run.exit'))
    sys.exit(0)
log('SSH ' + remote)
if 'rev-parse HEAD' in remote:
    print(os.environ.get('FAKE_HEAD', ''))
elif 'status --porcelain' in remote:
    print(os.environ.get('FAKE_DIRTY', ''))
elif remote.startswith('schtasks /query'):
    sys.exit(0 if get('logon_state', 'not registered') != 'not registered' else 1)
elif 'pending-winbox.json echo marker' in remote:
    print(os.environ.get('FAKE_MARKER', ''))
elif 'prep --dry-run' in remote:
    print('PREP-DRY-RUN-OUTPUT')
'''
FAKE_SCP = r'''#!/usr/bin/env python3
import os, shutil, sys
fake = os.environ['FAKE_DIR']
src, dst = sys.argv[-2], sys.argv[-1]
with open(os.path.join(fake, 'calls'), 'a') as f:
    f.write(f'SCP {src} {dst}\n')
if dst.startswith('winbox:'):
    shutil.copy(src, os.path.join(fake, 'uploaded.ps1'))
else:
    with open(dst, 'w') as f:
        f.write(os.environ.get('FAKE_RUN_OUT', 'output of the console-session task\n'))
'''


def _winbox_sh(tmp_path, *argv, logon_state='', **env):
    """Run a copy of winbox-restart.sh with ssh/scp replaced by scripts that answer and log."""
    scripts = tmp_path / 'scripts'
    (scripts / 'lib').mkdir(parents=True)
    (scripts / 'hub').mkdir()
    for name in ('winbox-restart.sh', 'lib/winbox_deploy.sh'):
        (scripts / name).write_text((REPO / 'scripts' / name).read_text())
    (scripts / 'hub/org-python.sh').write_text('#!/bin/sh\necho "${FAKE_CARDS:-[]}"\n')
    (scripts / 'pc-lease.sh').write_text('#!/bin/sh\necho "LEASE $*" >> "$FAKE_DIR/calls"\n')
    bindir, fake = tmp_path / 'bin', tmp_path / 'fake'
    bindir.mkdir()
    fake.mkdir()
    for name, body in (('ssh', FAKE_SSH), ('scp', FAKE_SCP)):
        (bindir / name).write_text(body)
        (bindir / name).chmod(0o755)
    if logon_state:
        (fake / 'logon_state').write_text(logon_state)
    full = {**os.environ, 'PATH': f'{bindir}:' + os.environ['PATH'], 'FAKE_DIR': str(fake),
            'WINBOX_POLL_SEC': '1', 'FAKE_HEAD': SHA, **env}
    result = REAL_RUN(['bash', str(scripts / 'winbox-restart.sh'), *argv],
                      env=full, capture_output=True, text=True, timeout=120)
    calls = (fake / 'calls').read_text().splitlines() if (fake / 'calls').exists() else []
    uploaded = (fake / 'uploaded.ps1').read_text() if (fake / 'uploaded.ps1').exists() else ''
    return result, calls, uploaded


def _called(calls, text):
    return [c for c in calls if text in c]


ONE_SHOT = "Register-ScheduledTask -TaskName 'mooniex-restart-run'"


def test_winbox_sh_register_runs_the_ps1_in_the_console_session_and_prints_the_state(tmp_path):
    result, calls, uploaded = _winbox_sh(tmp_path, '--register-logon-task', '--sha', SHA)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '-Verb register ' in _called(calls, ONE_SHOT)[0]
    assert 'register-org-resume.ps1' in uploaded and uploaded.isascii()
    assert 'MooniexOrgResume now: not registered' in result.stdout
    assert 'MooniexOrgResume state: Ready' in result.stdout
    assert 'output of the console-session task' in result.stdout
    assert len(_called(calls, "Unregister-ScheduledTask -TaskName 'mooniex-restart-run'")) >= 2   # the one-shot task goes
    assert not _called(calls, 'LEASE') and not _called(calls, 'shutdown') and not _called(calls, 'prep')


def test_winbox_sh_unregister_passes_remove(tmp_path):
    result, calls, uploaded = _winbox_sh(tmp_path, '--unregister-logon-task', '--sha', SHA, logon_state='Ready')
    assert result.returncode == 0, result.stdout + result.stderr
    assert '-Verb unregister ' in _called(calls, ONE_SHOT)[0]
    assert "if ($Verb -eq 'unregister') { $psArgs += '-Remove' }" in uploaded
    assert 'MooniexOrgResume now: Ready' in result.stdout and 'MooniexOrgResume state: not registered' in result.stdout


def test_winbox_sh_register_ps1_line_is_exactly_what_the_card_shows(tmp_path):
    result, _, _ = _winbox_sh(tmp_path, '--register-logon-task', '--dry-run', '--sha', SHA)
    reg = r'powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\passg\mooniex\repo\MoonieX-Agents\windows\register-org-resume.ps1'
    assert reg + '\n' in result.stdout
    result, _, _ = _winbox_sh(tmp_path / 'u', '--unregister-logon-task', '--dry-run', '--sha', SHA)
    assert reg + ' -Remove\n' in result.stdout


@pytest.mark.parametrize('flag', ['--register-logon-task', '--unregister-logon-task'])
def test_winbox_sh_dry_run_registers_nothing(tmp_path, flag):
    result, calls, uploaded = _winbox_sh(tmp_path, flag, '--dry-run', '--sha', SHA)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'nothing was changed' in result.stdout
    assert not _called(calls, ONE_SHOT) and not uploaded and not _called(calls, 'SCP')


@pytest.mark.parametrize('flag', ['--register-logon-task', '--unregister-logon-task'])
@pytest.mark.parametrize('env,fragment', [
    (dict(FAKE_HEAD='f' * 40), 'the card names'),                    # the clone is at another commit
    (dict(FAKE_DIRTY=' M tools/restart_run.py'), 'changed tracked files'),
])
def test_winbox_sh_logon_task_needs_the_clone_to_be_the_card_sha(tmp_path, flag, env, fragment):
    result, calls, uploaded = _winbox_sh(tmp_path, flag, '--sha', SHA, **env)
    assert result.returncode == 2 and fragment in result.stdout + result.stderr
    assert not _called(calls, ONE_SHOT) and not uploaded


def test_winbox_sh_logon_task_needs_a_sha_and_one_mode(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--register-logon-task')
    assert result.returncode == 2 and '--sha' in result.stdout + result.stderr and not calls
    result, calls, _ = _winbox_sh(tmp_path / 'b', '--register-logon-task', '--unregister-logon-task', '--sha', SHA)
    assert result.returncode == 2 and 'only one' in result.stdout + result.stderr


def test_winbox_sh_register_fails_when_the_ps1_fails(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--register-logon-task', '--sha', SHA, FAKE_RUN_EXIT='2')
    assert result.returncode == 1
    assert 'exited 2' in result.stdout + result.stderr and 'MooniexOrgResume state: not registered' in result.stdout


def test_winbox_sh_register_fails_when_the_task_is_not_ready_afterwards(tmp_path):
    result, _, _ = _winbox_sh(tmp_path, '--register-logon-task', '--sha', SHA, FAKE_STATE_AFTER='Disabled')
    assert result.returncode == 1 and "'Disabled' after register" in result.stdout + result.stderr


def test_winbox_sh_restart_refuses_without_the_logon_task_and_names_the_card(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--sha', SHA)
    assert result.returncode == 4
    assert f'--register-logon-task --sha {SHA}' in result.stdout + result.stderr
    assert not _called(calls, ONE_SHOT) and not _called(calls, 'shutdown')


def test_winbox_sh_restart_reboots_only_after_prep_exits_zero(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--sha', SHA, logon_state='Ready')
    assert result.returncode == 0, result.stdout + result.stderr
    assert '-Verb prep ' in _called(calls, ONE_SHOT)[0]
    assert _called(calls, 'LEASE take') and _called(calls, 'LEASE give-back')
    assert _called(calls, 'shutdown /r /t 60') and calls.index(_called(calls, 'shutdown /r /t 60')[0]) > calls.index(_called(calls, ONE_SHOT)[0])


def test_winbox_sh_restart_does_not_reboot_when_prep_fails(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--sha', SHA, logon_state='Ready', FAKE_RUN_EXIT='3')
    assert result.returncode == 3 and 'No reboot' in result.stdout
    assert not _called(calls, 'shutdown') and _called(calls, 'LEASE give-back')


def test_winbox_sh_restart_dry_run_runs_prep_dry_run_only(tmp_path):
    result, calls, _ = _winbox_sh(tmp_path, '--dry-run', '--sha', SHA, logon_state='Ready')
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PREP-DRY-RUN-OUTPUT' in result.stdout and '--register-logon-task' in result.stdout
    assert not _called(calls, ONE_SHOT) and not _called(calls, 'LEASE') and not _called(calls, 'shutdown')

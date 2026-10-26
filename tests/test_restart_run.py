"""No real tmux, launchers, sleeps, or hub access."""
import argparse
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

from tools import restart_run as rr

REAL_RUN = subprocess.run
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
    assert command[-4:] == ['--option', 'รับทราบ', '--option',
                            'ดูรายชื่อที่ขาด' if missing else 'ดูรายงาน']
    lines = (command[command.index('--question') + 1] + '\n' +
             command[command.index('--why') + 1]).splitlines()
    assert len(lines) <= 5
    assert all(len(line) <= 90 for line in lines)


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


def test_restart_shell_sessions_only_rolls_back_when_prep_fails(tmp_path):
    result, calls = _shell(tmp_path, '--sessions-only', fail='prep', prep_marker=True)
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


def test_resume_unit_sets_home():
    assert 'Environment=HOME=/root' in (REPO / 'deploy/systemd/org-resume.service').read_text()

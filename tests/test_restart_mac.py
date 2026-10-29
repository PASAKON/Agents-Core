"""SafeRestart on the Mac (task-6667f7ca): scripts/org-resume-mac.sh, scripts/mac-restart.sh and
the LaunchAgent plist. No Mac, no ssh, no hub: a stub `ssh`, `route`, `tailscale` and
org-python.sh on PATH record what the scripts would have done."""
import os
from pathlib import Path
import plistlib
import re
import subprocess

import pytest

REPO = Path(__file__).resolve().parents[1]
RESUME = REPO / 'scripts/org-resume-mac.sh'
RESTART = REPO / 'scripts/mac-restart.sh'
PLIST = REPO / 'deploy/launchd/com.mooniex.org-resume.plist'
SHA = 'a' * 40
OTHER_SHA = 'b' * 40


def stub(path, body):
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o755)


# --- static checks -------------------------------------------------------------------------

@pytest.mark.parametrize('script', [RESUME, RESTART, REPO / 'scripts/mac-restart-detach.sh',
                                    REPO / 'scripts/install-mac-resume.sh'], ids=lambda p: p.name)
def test_bash_syntax(script):
    result = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_resume_script_is_bash_3_2_and_bsd_safe():
    """The macOS /bin/bash is 3.2.57 and has no GNU userland (IRON-RULES §12)."""
    code = '\n'.join(line.split('#')[0] for line in RESUME.read_text().splitlines())
    bad = re.findall(r'declare -A|mapfile|readarray|\btimeout \d|date -d|readlink -f|sed -i|\$\{[^}]*(?:,,|\^\^)\}',
                     code)
    assert not bad, bad


def test_plist_runs_the_resume_script_at_load_only():
    plist = plistlib.loads(PLIST.read_bytes())
    assert plist['Label'] == 'com.mooniex.org-resume'
    assert plist['RunAtLoad'] is True
    assert 'KeepAlive' not in plist
    script = plist['ProgramArguments'][-1]
    assert script.endswith('/scripts/org-resume-mac.sh')
    assert (REPO / 'scripts/org-resume-mac.sh').is_file()
    assert plist['ProgramArguments'][0] == '/bin/bash'
    # launchd's log and the script's own log are one file
    log = 'state/restart/mac-resume.log'
    assert plist['StandardOutPath'].endswith('/' + log)
    assert plist['StandardErrorPath'] == plist['StandardOutPath']
    assert f'LOG={log}' in RESUME.read_text()
    assert plist['StandardOutPath'].startswith(plist['WorkingDirectory'])


# --- org-resume-mac.sh ---------------------------------------------------------------------

def run_resume(tmp_path, marker=True, **env):
    """Run a copy of the script in tmp_path with HOME unset, as launchd would."""
    scripts = tmp_path / 'scripts'
    (scripts / 'hub').mkdir(parents=True)
    (scripts / 'org-resume-mac.sh').write_text(RESUME.read_text())
    stub(scripts / 'hub/org-python.sh', '''
if [ "${1:-}" = "-c" ]; then echo probe >> "$CALL_LOG"; exit "${PROBE_RC:-0}"; fi
echo "$HOME|$ORG_HOST|$*" >> "$CALL_LOG"
case "$*" in
  *" resume"*) exit "${RESUME_RC:-0}" ;;
  *" report "*) exit "${REPORT_RC:-0}" ;;
esac
''')
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    stub(bindir / 'route', '''
if [ -n "${ROUTE_FAIL_FIRST:-}" ]; then
  n=$(cat "$ROUTE_FAIL_FIRST" 2>/dev/null || echo 0); echo $((n + 1)) > "$ROUTE_FAIL_FIRST"
  [ "$n" -ge 1 ]; exit $?
fi
exit "${ROUTE_RC:-0}"
''')
    stub(bindir / 'tailscale', 'exit "${TS_RC:-0}"\n')
    if marker:
        (tmp_path / 'state/restart').mkdir(parents=True)
        (tmp_path / 'state/restart/pending-mac.json').write_text('{"manifest": "m", "timestamp": "t"}')
    full = {k: v for k, v in os.environ.items() if k not in ('HOME', 'ORG_HOST')}
    full.update(PATH=f'{bindir}:' + os.environ['PATH'], CALL_LOG=str(tmp_path / 'calls'),
                MAC_RESUME_WAIT_S='5', MAC_RESUME_POLL_S='1')
    full.update(env)
    result = subprocess.run(['bash', str(scripts / 'org-resume-mac.sh')], env=full,
                            capture_output=True, text=True, timeout=60)
    log = tmp_path / 'calls'
    calls = log.read_text().splitlines() if log.exists() else []
    resume_log = (tmp_path / 'state/restart/mac-resume.log').read_text()
    return result, calls, resume_log


def test_resume_without_marker_does_nothing(tmp_path):
    result, calls, log = run_resume(tmp_path, marker=False)
    assert result.returncode == 0, result.stderr
    assert calls == []
    assert 'nothing to resume' in log


def test_resume_runs_resume_then_report_with_a_bare_environment(tmp_path):
    result, calls, log = run_resume(tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout == ''  # everything goes to the log
    assert calls[0] == 'probe'
    home, host, args = calls[1].split('|')
    assert home.startswith('/') and host == 'mac'  # HOME and ORG_HOST were exported
    assert args == 'tools/restart_run.py --host mac resume'
    assert calls[2].endswith('|tools/restart_run.py --host mac report --notify')
    assert len(calls) == 3
    assert 'resume exited 0' in log and 'report --notify exited 0' in log


def test_resume_waits_for_the_network_then_goes(tmp_path):
    result, calls, log = run_resume(tmp_path, ROUTE_FAIL_FIRST=str(tmp_path / 'route-count'))
    assert result.returncode == 0, result.stderr
    assert 'waiting for network' in log
    assert any(c.endswith('--host mac resume') for c in calls)


@pytest.mark.parametrize('env, gate', [
    ({'ROUTE_RC': '1'}, 'network'),
    ({'TS_RC': '1'}, 'tailnet'),
    ({'PROBE_RC': '1'}, 'hub'),
])
def test_resume_gives_up_when_a_gate_stays_down(tmp_path, env, gate):
    result, calls, log = run_resume(tmp_path, MAC_RESUME_WAIT_S='0', **env)
    assert result.returncode == 1
    assert not any('restart_run.py' in c for c in calls)  # nothing resumed
    assert f'gave up after 0 s: {gate} is still down' in log
    assert (tmp_path / 'state/restart/pending-mac.json').exists()


def test_resume_failure_still_reports_and_returns_the_first_failure(tmp_path):
    result, calls, _ = run_resume(tmp_path, RESUME_RC='4', REPORT_RC='3')
    assert result.returncode == 4
    assert calls[-1].endswith('report --notify')


def test_report_failure_alone_is_the_exit_code(tmp_path):
    result, calls, _ = run_resume(tmp_path, REPORT_RC='3')
    assert result.returncode == 3


# --- mac-restart.sh ------------------------------------------------------------------------

def run_restart(tmp_path, *argv, script=RESTART, **env):
    bindir = tmp_path / 'bin'
    bindir.mkdir(exist_ok=True)
    stub(bindir / 'ssh', '''
for a; do last=$a; done
printf '%s\\n' "$*" >> "$SSH_LOG"
case "$last" in
  *"git rev-parse HEAD"*) [ "${HEAD_RC:-0}" -eq 0 ] || exit 255; echo "$STUB_HEAD"; exit 0 ;;
  *" prep "*) echo prep-stub-output; exit "${PREP_RC:-0}" ;;
  *"shutdown -r +1"*) exit "${SUDO_RC:-0}" ;;
esac
exit 99
''')
    full = dict(os.environ)
    full.update(PATH=f'{bindir}:' + os.environ['PATH'], SSH_LOG=str(tmp_path / 'ssh'), STUB_HEAD=SHA)
    full.update(env)
    result = subprocess.run(['bash', str(script), *argv], env=full, capture_output=True, text=True, timeout=60)
    log = tmp_path / 'ssh'
    return result, log.read_text().splitlines() if log.exists() else []


def test_restart_schedules_the_shutdown_only_after_prep_succeeds(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA)
    assert result.returncode == 0, result.stderr
    assert len(calls) == 3
    assert 'git rev-parse HEAD' in calls[0]
    assert 'cd /Users/gob/MoonieXHQ/Agents/Core' in calls[1]
    assert 'bash scripts/hub/org-python.sh tools/restart_run.py --host mac prep --wait-max 600' in calls[1]
    assert '--dry-run' not in calls[1]
    assert calls[2].endswith('sudo -n shutdown -r +1 </dev/null >/dev/null 2>&1')
    for call in calls:  # the tailnet name, as the gob account, never prompting
        assert ' gob@macbook-pro--gob ' in call and '-o BatchMode=yes' in call
    assert 'scheduled in 1 minute' in result.stdout


def test_restart_refuses_when_the_mac_is_on_another_commit(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA, STUB_HEAD=OTHER_SHA)
    assert result.returncode == 4
    assert len(calls) == 1  # only the HEAD read: no prep, no shutdown
    assert OTHER_SHA in result.stderr and SHA in result.stderr


def test_restart_refuses_when_the_mac_cannot_be_read(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA, HEAD_RC='255')
    assert result.returncode == 5
    assert len(calls) == 1


@pytest.mark.parametrize('prep_status', [1, 3, 255])
def test_restart_sends_no_shutdown_when_prep_fails(tmp_path, prep_status):
    result, calls = run_restart(tmp_path, '--sha', SHA, PREP_RC=str(prep_status))
    assert result.returncode == prep_status
    assert len(calls) == 2
    assert not any('shutdown' in c for c in calls)
    assert f'prep exited {prep_status}' in result.stderr
    # 3 = a session is mid-turn and nothing was closed, so no recovery hint; the others may have closed some
    assert ('restart_run.py --host mac resume' in result.stderr) == (prep_status != 3)


def test_restart_tells_the_operator_what_to_do_when_sudo_is_refused(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA, SUDO_RC='1')
    assert result.returncode == 6
    assert any('shutdown' in c for c in calls)
    for needle in ('sudo shutdown -r +1', 'gob ALL=(root) NOPASSWD: /sbin/shutdown -r +1',
                   '/etc/sudoers.d/mooniex-restart', 'pending-mac.json', 'restart_run.py --host mac resume'):
        assert needle in result.stderr, needle


def test_restart_dry_run_preps_dry_and_never_shuts_down(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA, '--dry-run')
    assert result.returncode == 0, result.stderr
    assert len(calls) == 2
    assert calls[1].endswith('prep --wait-max 600 --dry-run')
    assert not any('shutdown' in c for c in calls)
    assert 'dry run' in result.stdout


def test_restart_dry_run_still_checks_the_sha(tmp_path):
    result, calls = run_restart(tmp_path, '--sha', SHA, '--dry-run', STUB_HEAD=OTHER_SHA)
    assert result.returncode == 4
    assert len(calls) == 1


@pytest.mark.parametrize('alias, target', [
    (None, 'gob@macbook-pro--gob'),
    ('mac-box', 'gob@mac-box'),
    ('other@100.64.0.9', 'other@100.64.0.9'),
])
def test_restart_host_alias(tmp_path, alias, target):
    argv = ['--sha', SHA, '--dry-run'] + (['--host-alias', alias] if alias else [])
    result, calls = run_restart(tmp_path, *argv)
    assert result.returncode == 0, result.stderr
    assert all(f' {target} ' in c for c in calls)


@pytest.mark.parametrize('argv', [
    [],
    ['--sha', 'abc1234'],                                       # short sha
    ['--sha', SHA.upper().replace('A', 'G')],                   # not hex
    ['--sha', SHA, '--host-alias', '-oProxyCommand=touch_x'],   # would be read as an ssh option
    ['--sha', SHA, '--host-alias', 'a;reboot'],
    ['--sha', SHA, '--repo', '/Users/gob/x; reboot'],           # would reach the Mac's shell
    ['--sha', SHA, '--repo', 'relative/path'],
    ['--sha', SHA, '--nope'],
    ['--sha'],
])
def test_restart_rejects_bad_arguments_before_any_ssh(tmp_path, argv):
    result, calls = run_restart(tmp_path, *argv)
    assert result.returncode == 2
    assert calls == []


def test_install_renders_and_bootstraps_template(tmp_path):
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    stub(bindir / 'launchctl', 'printf "%s\\n" "$#" > "$CALL_LOG"\n')
    home = tmp_path / 'home'
    env = dict(os.environ, HOME=str(home), PATH=f'{bindir}:' + os.environ['PATH'],
               CALL_LOG=str(tmp_path / 'calls'))
    result = subprocess.run(['bash', str(REPO / 'scripts/install-mac-resume.sh')],
                            env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    output = home / 'Library/LaunchAgents/com.mooniex.org-resume.plist'
    assert '__REPO__' not in output.read_text()
    data = plistlib.loads(output.read_bytes())
    assert data['WorkingDirectory'] == str(REPO)
    assert data['ProgramArguments'][1] == str(RESUME)
    assert (tmp_path / 'calls').read_text().strip() == '3'


def run_detached(tmp_path, *flags, **overrides):
    bindir = tmp_path / 'bin'
    bindir.mkdir()
    scripts = tmp_path / 'scripts/hub'
    scripts.mkdir(parents=True)
    stub(bindir / 'git', 'echo "$STUB_HEAD"\n')
    # Stubs log argument counts only, never environment values or command arguments.
    stub(bindir / 'launchctl', '''
printf '%s\\n' "$#" >> "$CALL_LOG"
case "$1" in
  list) exit "${DUPLICATE_RC:-1}" ;;
  remove) exit 0 ;;
  submit)
    shift 3
    out=$2
    shift 4
    [ "$1" = -- ] || exit 99
    shift
    "$@" > "$out" 2>&1
    exit 0 ;;
esac
exit 99
''')
    stub(bindir / 'sudo', '''
printf '%s\\n' "$#" >> "$SUDO_LOG"
shift
"$@"
''')
    stub(bindir / 'shutdown', 'printf "%s\\n" "$#" >> "$SHUTDOWN_LOG"\n')
    stub(scripts / 'org-python.sh', '''
printf '%s\\n' "$#" >> "$PREP_LOG"
for arg; do
  case "$arg" in
    --dry-run) touch "$DRY_MARKER" ;;
    --cards-checked) touch "$CARDS_MARKER" ;;
  esac
done
exit "${PREP_RC:-0}"
''')
    env = dict(os.environ, PATH=f'{bindir}:' + os.environ['PATH'], STUB_HEAD=SHA,
               CALL_LOG=str(tmp_path / 'calls'), SUDO_LOG=str(tmp_path / 'sudo'),
               SHUTDOWN_LOG=str(tmp_path / 'shutdown'), PREP_LOG=str(tmp_path / 'prep'),
               DRY_MARKER=str(tmp_path / 'dry'), CARDS_MARKER=str(tmp_path / 'cards'))
    env.update(overrides)
    return subprocess.run(['bash', str(RESTART), '--detach', '--repo', str(tmp_path),
                           '--sha', SHA, *flags], env=env, capture_output=True, text=True)


def test_detach_refuses_duplicate(tmp_path):
    result = run_detached(tmp_path, DUPLICATE_RC='0')
    assert result.returncode == 7
    assert 'already exists' in result.stderr
    assert (tmp_path / 'calls').read_text().splitlines() == ['2']
    assert not (tmp_path / 'prep').exists()


@pytest.mark.parametrize('dry,prep_rc', [(True, 0), (False, 0), (False, 3), (False, 1)])
def test_detached_job_gates_shutdown_and_cleans_up(tmp_path, dry, prep_rc):
    flags = ['--cards-checked'] + (['--dry-run'] if dry else [])
    result = run_detached(tmp_path, *flags, PREP_RC=str(prep_rc))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / 'cards').exists()
    assert (tmp_path / 'dry').exists() == dry
    assert (tmp_path / 'shutdown').exists() == (not dry and prep_rc == 0)
    assert (tmp_path / 'sudo').exists() == (not dry and prep_rc == 0)
    assert not list((tmp_path / 'state/restart').glob('mac-prep-job.*'))
    logs = list((tmp_path / 'state/restart').glob('mac-prep-*.log'))
    assert len(logs) == 1
    assert f'job exit: {prep_rc}' in logs[0].read_text()
    assert (tmp_path / 'calls').read_text().splitlines() == ['2', '10', '2']


def test_detach_sha_mismatch_never_submits(tmp_path):
    result = run_detached(tmp_path, STUB_HEAD=OTHER_SHA)
    assert result.returncode == 4
    assert not (tmp_path / 'calls').exists()

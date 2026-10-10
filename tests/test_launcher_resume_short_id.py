"""Offline resume resolution and launcher wiring guards (#240, #173)."""
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
UUID = '12345678-abcd-1234-abcd-1234abcd1234'


@pytest.fixture
def resolver(tmp_path):
    locks = tmp_path / 'locks'
    locks.mkdir()
    python = tmp_path / 'fake org-python'
    python.write_text('#!/bin/sh\nprintf "%s\\n" "$FAKE_UUID"\nprintf "%s\\n" "$@" > "$FAKE_ARGS"\n')
    python.chmod(0o755)
    args = tmp_path / 'args'
    env = dict(os.environ, RESOLVE_LOCKS_DIR=str(locks), RESOLVE_ORG_PYTHON=str(python),
               FAKE_UUID='', FAKE_ARGS=str(args))

    def run(value, output='', file=None):
        if file is not None:
            (locks / 'cfo-abcd1234.uuid').write_text(file)
        return subprocess.run(['bash', str(ROOT / 'scripts/resolve-resume-id.sh'), 'cfo', value],
                              env=dict(env, FAKE_UUID=output), capture_output=True, text=True)

    return run, args


@pytest.mark.parametrize('value', [UUID, UUID.upper()])
def test_full_uuid_unchanged(resolver, value):
    run, args = resolver
    result = run(value)
    assert result.returncode == 0
    assert result.stdout == value + '\n'
    assert result.stderr == ''
    assert not args.exists()


def test_uuid_file_first(resolver):
    run, args = resolver
    result = run('abcd1234', output='bad', file=UUID + '\n')
    assert result.returncode == 0
    assert result.stdout == UUID + '\n'
    assert not args.exists()


@pytest.mark.parametrize('file', [None, '', 'not-a-uuid'])
def test_session_status_fallback(resolver, file):
    run, args = resolver
    result = run('abcd1234', output=UUID, file=file)
    assert result.returncode == 0
    assert result.stdout == UUID + '\n'
    assert args.read_text().splitlines() == [
        '-m', 'tools.session_status', 'resume', '--role', 'cfo', '--session-id', 'abcd1234']


@pytest.mark.parametrize('output', ['', 'abcd1234', 'bad\n' + UUID])
def test_unresolved_refused(resolver, output):
    run, _ = resolver
    result = run('abcd1234', output=output)
    assert result.returncode == 2
    assert result.stdout == ''
    assert len(result.stderr.splitlines()) == 1
    assert 'cfo-abcd1234.uuid' in result.stderr
    assert 'c_level_sessions.resume_uuid' in result.stderr


@pytest.mark.parametrize('value', ['abc', 'ABCD1234', 'abcd12345', ''])
def test_invalid_input_refused(resolver, value):
    run, args = resolver
    result = run(value)
    assert result.returncode == 2
    assert result.stdout == ''
    assert 'expected 8 lowercase hex' in result.stderr
    assert not args.exists()


@pytest.mark.parametrize('name', ['cxo', 'cto'])
def test_bash_launcher_wiring(name):
    script = ROOT / f'scripts/{name}-claude.sh'
    result = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    code = script.read_text()
    block = code[code.index('# Resolve explicit resume'):code.index('done', code.index('# Resolve explicit resume'))]
    assert '-r|--resume)' in block
    assert '"${ARGS[i+1]}" != -*' in block
    assert 'ARGS[i+1]="$(bash "$ROOT/scripts/resolve-resume-id.sh"' in block
    assert '|| exit 2' in block
    assert code.index('resolve-resume-id.sh') < code.index('MCP_CONFIG=')
    assert '-r|--resume|-c|--continue) FORK_ARGS=(--fork-session)' in code
    assert '/opt/agents-wikis' not in code
    assert '/opt/mooniex-wikis' not in code


@pytest.mark.parametrize('name', ['cxo', 'cto'])
@pytest.mark.parametrize('flag', ['-r', '--resume'])
def test_bash_launcher_refuses_before_side_effects(name, flag):
    argv = ['bash', str(ROOT / f'scripts/{name}-claude.sh')]
    if name == 'cxo':
        argv += ['--role', 'cfo']
    result = subprocess.run(argv + [flag, 'invalid'], capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'refuse to resume: expected 8 lowercase hex characters or a full UUID\n'


def test_windows_resume_wiring():
    code = '\n'.join(line for line in (ROOT / 'windows/cxo-claude.ps1').read_text().splitlines()
                     if not line.lstrip().startswith('#'))
    block = code[code.index('$uuidPattern ='):code.index('$py3 =')]
    assert "@('-r', '--resume')" in block
    assert "$RemainingArgs[$i + 1].StartsWith('-')" in block
    assert "-cnotmatch '^[0-9a-f]{8}$'" in block
    assert 'if ($resumeId -cmatch $uuidPattern) { continue }' in block
    assert 'state\\locks\\$Role-$resumeId.uuid' in block
    assert '& $venvPy -m tools.session_status resume --role $Role --session-id $resumeId' in block
    assert block.index('Get-Content') < block.index('tools.session_status')
    assert '$RemainingArgs[$i] = $resumeTarget' in block
    assert '[Console]::Error.WriteLine' in block and 'exit 2' in block
    assert code.index('$RemainingArgs[$i] = $resumeTarget') < code.index('New-Item')
    assert '--fork-session' in code

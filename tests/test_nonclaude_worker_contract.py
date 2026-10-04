"""Offline contract selection and byte-for-byte Claude regressions."""
import hashlib
from pathlib import Path

import pytest

from runners.worker_init import _build_prompt
from tools.delegate import _remote_runner_prompt

ROOT = Path(__file__).resolve().parents[1]
MARKER = '<!-- NONCLAUDE CONTRACT -->\n'
TASK = dict(id='task-12345678', branch='agent/test', description='Fix widget; mcp__org__wiki_read')
PROJECT = dict(name='Example', key='example', stack=['python'], default_branch='main')


def test_claude_contract_matches_prechange_bytes():
    original = (ROOT / 'roles/_worker_remote.md').read_text().split(MARKER)[0]
    assert hashlib.sha256(original.encode()).hexdigest() == 'f7da267763237849b8ec2fce1461e45011a0a6d6afc40cbfcff74f7369b0253c'
    assert _remote_runner_prompt(TASK, PROJECT, '/tmp/tree', 'claude') == _build_prompt(TASK, PROJECT, '/tmp/tree')


@pytest.mark.parametrize('runner', ['codex', 'agy'])
def test_nonclaude_prompt_and_contract(runner):
    prompt = _remote_runner_prompt(TASK, PROJECT, '/tmp/tree', runner)
    contract = (ROOT / 'roles/_worker_remote.md').read_text().split(MARKER)[1]
    for text in (prompt, contract):
        assert 'mcp__org__' not in text
        assert 'date -u' not in text
        assert 'READ MAILBOX.md with your file tool if the file' in text
        assert '## Blockers' in text
        assert '## Skill learning' in text
        assert 'launcher owns HEARTBEAT' in text
    assert 'docs/reports/task-12345678/REPORT.md' in prompt
    assert '# REPORT task-12345678' in prompt
    assert 'call `mcp' not in prompt


def test_launchers_select_runner_contract():
    shell = (ROOT / 'scripts/spawn-worker-remote.sh').read_text()
    ps = (ROOT / 'windows/spawn-worker.ps1').read_text()
    assert "sed '/^<!-- NONCLAUDE CONTRACT -->/,$d'" in shell
    assert "sed '1,/^<!-- NONCLAUDE CONTRACT -->/d'" in shell
    assert 'sed "s/<task-id>/$TASK/g"' in shell
    assert "{ $contracts[1] } else { $contracts[0] }" in ps
    assert "$systemPrompt = $remoteContract" in ps


@pytest.mark.parametrize('runner', ['claude', 'codex', 'agy'])
def test_linux_actual_prompt_assembly(tmp_path, runner):
    """Run just the prompt-writing part, with no CLI, network or tmux."""
    import subprocess
    import shlex

    wt = tmp_path / 'work tree'
    wt.mkdir()
    brief = _build_prompt(TASK, PROJECT, str(wt))
    (wt / 'TASK.md').write_text(brief)
    source = (ROOT / 'scripts/spawn-worker-remote.sh').read_text()
    assembly = source.split('# --- 4. WORKER.md:', 1)[1]
    assembly = assembly[assembly.index('REMOTE_CONTRACT='):].split('# --- 6.', 1)[0]
    variables = dict(WT=str(wt), ROLES_DIR=str(ROOT / 'roles'), ROLE='developer',
                     RUNNER=runner, AGENTS_ROOT=str(tmp_path), TASK=TASK['id'])
    setup = '\n'.join(f'{key}={shlex.quote(value)}' for key, value in variables.items())
    subprocess.run(['bash', '-c', setup + '\n' + assembly], check=True)
    system = (tmp_path / f'.launch-{TASK["id"]}' / 'system_prompt.txt').read_text()
    if runner == 'claude':
        old_contract = (ROOT / 'roles/_worker_remote.md').read_text().split(MARKER)[0]
        expected = ((ROOT / 'roles/_worker_shared.md').read_text() + '\n\n'
                    + (ROOT / 'roles/developer.md').read_text() + '\n\n' + old_contract)
        assert system == expected
        assert (wt / 'TASK.md').read_text() == brief
    else:
        for text in (system, (wt / 'TASK.md').read_text(), (wt / 'WORKER.md').read_text()):
            assert 'mcp__org__' not in text
            assert 'date -u' not in text
            assert '## Blockers' in text
        assert f'docs/reports/{TASK["id"]}/REPORT.md' in system

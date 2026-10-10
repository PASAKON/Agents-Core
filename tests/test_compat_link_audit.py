"""Isolated fixtures for the read-only compatibility-link audit."""
import builtins
import io
import json
from pathlib import Path
import plistlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import compat_link_audit as audit


def put(path, text=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def completed(stdout='', code=0, stderr=''):
    return subprocess.CompletedProcess([], code, stdout, stderr)


@pytest.fixture
def tree(tmp_path):
    roots = {name: tmp_path / name for name in ('hq', 'links', 'home', 'services', 'cron', 'proc')}
    for path in roots.values():
        path.mkdir()
    (roots['hq'] / 'repo').mkdir()
    (roots['links'] / 'old').symlink_to(roots['hq'] / 'repo', target_is_directory=True)
    (roots['links'] / 'unrelated').symlink_to(tmp_path / 'elsewhere')
    return roots


def inspect(tree, runner=lambda args: completed(), platform='linux'):
    return audit.audit(tree['hq'], [tree['links']], platform, tree['home'], tree['services'],
                       tree['cron'], tree['proc'], runner)


def categories(result):
    return result['links'][0]['categories']


def test_full_audit_secrets_and_git(tree, monkeypatch):
    old = str(tree['links'] / 'old')
    repo = tree['hq'] / 'repo'
    script = put(repo / 'start.sh', f'#!/bin/sh\necho {old}/hooks\n')
    put(tree['services'] / 'nested' / 'worker.service', f'[Service]\nExecStart={script}\n')
    put(tree['cron'] / 'worker', f'* * * * * {old}/job\n')
    put(repo / 'venv' / 'pyvenv.cfg', f'home = {old}/python\n')
    put(repo / 'venv' / 'bin' / 'worker', f'#!{old}/python\nignored {old}\n')
    put(tree['home'] / '.claude' / 'settings.json', json.dumps({'path': old}))
    marker = 'private-value-must-never-appear'
    put(tree['home'] / '.claude.json', json.dumps({'projects': {old: {'token': marker}}}))
    secret_paths = [put(repo / name, old + marker) for name in
                    ('.env', '.env.local', 'prod.env', 'credentials-prod', 'cert.pem', 'private.key', '.credentials.json')]
    put(repo / 'prefix.txt', old + '-old\n')
    put(repo / 'many.txt', (old + '/file\n') * 25)
    for args in (['git', 'init', '-q', str(repo)], ['git', '-C', str(repo), 'add', '.']):
        subprocess.run(args, check=True, capture_output=True)
    # Guard Python reads; the real git grep count verifies its secret exclusions.
    opened = []
    original_io, original_builtin = io.open, builtins.open
    def guard(original):
        def wrapped(file, *args, **kwargs):
            if isinstance(file, (str, Path)):
                opened.append(str(file))
                assert Path(file) not in secret_paths
            return original(file, *args, **kwargs)
        return wrapped
    monkeypatch.setattr(io, 'open', guard(original_io))
    monkeypatch.setattr(builtins, 'open', guard(original_builtin))
    def runner(args):
        if args[0] == 'crontab':
            return completed(f'* * * * * {old}/cron\n')
        return audit.run(args)
    result = inspect(tree, runner)
    data = categories(result)
    assert data['scripts']['count'] == 1
    assert data['cron']['count'] == 2
    assert data['virtualenvs']['count'] == 2
    assert data['claude']['count'] == 2
    assert data['git']['count'] == 29
    assert len(data['git']['repos'][0]['hits']) == 20
    assert data['not scanned']['count'] == 2
    assert audit.exit_code(result) == 1
    output = audit.render(result) + json.dumps(result)
    assert marker not in output
    assert 'not scanned (secret file, check by hand)' in output
    assert not any(str(p) in opened for p in secret_paths)
    assert old in data['claude']['hits']


def test_clean_and_cli(tree, capsys):
    put(tree['hq'] / 'repo' / '.env', str(tree['links'] / 'old'))
    (tree['hq'] / 'repo' / '.git').mkdir()
    result = inspect(tree)
    assert audit.exit_code(result) == 0
    assert categories(result)['not scanned']['count'] == 1
    assert audit.main(['--json'], auditor=lambda *args: result, platform='linux', home=tree['home']) == 0
    assert json.loads(capsys.readouterr().out) == result


def test_unreadable_is_not_clean(tree):
    def denied(args):
        raise PermissionError(13, 'Permission denied')
    result = inspect(tree, denied)
    assert audit.exit_code(result) == 1
    assert 'unreadable: Permission denied' in audit.render(result)


@pytest.mark.parametrize('suffix, expected', [('', True), ('/file', True), ('"', True), (' ', True),
                                             ('-old', False), ('_old', False), ('.old', False)])
def test_boundary(suffix, expected):
    assert audit.matches('/opt/mooniex-agents' + suffix, '/opt/mooniex-agents') is expected


def test_walk_does_not_follow_links_or_excluded_dirs(tree):
    outside = put(tree['home'] / 'external' / 'pyvenv.cfg', 'outside').parent
    (tree['hq'] / 'linked').symlink_to(outside, target_is_directory=True)
    for name in ('worktrees', 'node_modules'):
        (tree['hq'] / name / 'repo' / '.git').mkdir(parents=True)
    repos, records, errors, _ = audit.read_hq(tree['hq'])
    assert repos == []
    assert records == []
    assert errors == []
    links, errors = audit.discover_links(tree['hq'], [tree['links']])
    assert links == [str(tree['links'] / 'old')]
    assert errors == []


def test_linux_process_redaction(tree):
    old = str(tree['links'] / 'old')
    pid = tree['proc'] / '123'
    put(pid / 'comm', 'worker\n')
    put(pid / 'cmdline', f'worker\0{old}/run\0--token=hidden-argument\0')
    (pid / 'cwd').symlink_to(tree['hq'])
    put(pid / 'environ', 'never-read')
    result = inspect(tree)
    assert categories(result)['processes']['hits'] == [{'pid': 123, 'name': 'worker'}]
    assert 'hidden-argument' not in json.dumps(result) + audit.render(result)
    put(pid / 'cmdline', 'worker\0')
    (pid / 'cwd').unlink()
    (pid / 'cwd').symlink_to(tree['links'] / 'old')
    assert categories(inspect(tree))['processes']['count'] == 1


def test_darwin_plist_and_processes(tree):
    old = str(tree['links'] / 'old')
    script = put(tree['hq'] / 'run.py', old + '/hook')
    with (tree['services'] / 'worker.plist').open('wb') as stream:
        plistlib.dump({'ProgramArguments': [str(script)], 'WorkingDirectory': old}, stream)
    def runner(args):
        if args[0] == 'crontab':
            return completed(code=1, stderr='no crontab for tester')
        return completed('42 worker\n' if args[-1] == 'pid=,comm=' else f'42 worker {old}/job --secret=hidden\n')
    result = inspect(tree, runner, 'darwin')
    assert categories(result)['services']['count'] == 1
    assert categories(result)['scripts']['count'] == 1
    assert categories(result)['processes']['hits'] == [{'pid': 42, 'name': 'worker'}]
    assert 'hidden' not in json.dumps(result)


def test_secret_and_symlink_files_are_not_opened(tree):
    target = put(tree['home'] / 'private', 'anything')
    link = tree['services'] / 'linked.service'
    link.symlink_to(target)
    records, errors, scripts = audit.read_services(tree['services'], 'linux')
    assert records == [] and errors == [] and scripts == set()
    assert audit.secret('/etc/infisical/config')
    assert audit.secret('/etc/mooniex/config')
    assert audit.secret('/etc/sompong/config')


def test_missing_commands_and_usage(tree):
    def missing(args):
        raise FileNotFoundError(2, 'No such file or directory')
    assert audit.read_cron(tree['cron'], 'linux', missing) == ([], [])
    entry, errors = audit.read_git(tree['hq'] / 'repo', '/old', missing)
    assert entry['count'] == 0 and errors
    with pytest.raises(SystemExit) as exc:
        audit.main(['--invalid'])
    assert exc.value.code == 2


def test_unreadable_file(tree, monkeypatch):
    unit = put(tree['services'] / 'denied.service', 'value')
    original = Path.open
    def denied(path, *args, **kwargs):
        if path == unit:
            raise PermissionError(13, 'Permission denied')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', denied)
    assert audit.exit_code(inspect(tree)) == 1


def test_execstart_via_compat_link(tree):
    old = tree['links'] / 'old'
    script = put(tree['hq'] / 'repo' / 'run.sh', f'{old}/hook\n')
    put(tree['services'] / 'worker.service', f'ExecStart={old}/run.sh\n')
    result = inspect(tree)
    assert categories(result)['scripts']['hits'] == [f'{script}:1']


def test_git_skips_symlink_ancestor(tree):
    repo = tree['hq'] / 'repo'
    old = str(tree['links'] / 'old')
    tracked = put(repo / 'directory' / 'file', old)
    subprocess.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True, capture_output=True)
    tracked.unlink()
    tracked.parent.rmdir()
    external = put(tree['home'] / 'outside' / 'file', old).parent
    (repo / 'directory').symlink_to(external, target_is_directory=True)
    data, errors = audit.read_git(repo, old)
    assert data['count'] == 0
    assert errors == []

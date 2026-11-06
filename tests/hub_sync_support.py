"""Local-only repositories and quiet executable protocol stubs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True).stdout.decode().strip()


def commit(repo, path, text):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    git(repo, 'add', path)
    git(repo, 'commit', '-m', 'fixture change')
    return git(repo, 'rev-parse', 'HEAD')


@pytest.fixture
def repository(tmp_path, monkeypatch):
    # Do not inherit user hooks, signing, alternate git dirs or real remotes.
    for name in list(os.environ):
        if name.startswith('GIT_'):
            monkeypatch.delenv(name)
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', '/dev/null')
    monkeypatch.setenv('GIT_ALLOW_PROTOCOL', 'file')
    remote, repo = tmp_path / 'origin.git', tmp_path / 'repo'
    remote.mkdir()
    repo.mkdir()
    git(remote, 'init', '--bare', '--initial-branch=main')
    git(repo, 'init', '--initial-branch=main')
    git(repo, 'config', 'user.name', 'Fixture')
    git(repo, 'config', 'user.email', 'fixture@example.com')
    commit(repo, 'readme', 'base\n')
    git(repo, 'remote', 'add', 'origin', str(remote))
    git(repo, 'push', '-u', 'origin', 'main')
    return repo, remote


@pytest.fixture
def stubs(tmp_path, monkeypatch):
    directory = tmp_path / 'bin'
    directory.mkdir()
    state = tmp_path / 'stub-state'
    state.mkdir()
    (state / 'prs.json').write_text('[]')
    (state / 'leaks.json').write_text('[]')
    script = '''
import json, os, pathlib, sys
s = pathlib.Path(os.environ['HUB_STUB_STATE'])
a = sys.argv[1:]
print(len(a), file=sys.stderr)
tool = pathlib.Path(sys.argv[0]).name
if tool == 'gh':
    if a[:2] == ['pr', 'list']:
        print((s / 'prs.json').read_text())
    elif a[:2] == ['pr', 'create']:
        assert '## Not checked / risk' in pathlib.Path(a[a.index('--body-file') + 1]).read_text()
        (s / 'created').touch()
        print('https://github.com/fixture/repo/pull/42')
    elif a[:2] == ['pr', 'close']:
        assert a[2:] == ['7', '--comment', 'superseded by #42']
        (s / 'closed').touch()
    else:
        sys.exit(2)
else:
    assert a[0] == 'git' and '--redact' in a and '--no-banner' in a
    assert a[a.index('--log-opts') + 1].startswith('origin/main..')
    data = (s / 'leaks.json').read_text()
    pathlib.Path(a[a.index('--report-path') + 1]).write_text(data)
    sys.exit(1 if json.loads(data) else 0)
'''
    for name in ('gh', 'gitleaks'):
        path = directory / name
        path.write_text('#!' + sys.executable + '\n' + script)
        path.chmod(0o755)
    monkeypatch.setenv('PATH', str(directory) + os.pathsep + os.environ['PATH'])
    monkeypatch.setenv('HUB_STUB_STATE', str(state))
    return state


def snapshot(repo):
    return (git(repo, 'rev-parse', 'HEAD'), (repo / '.git/HEAD').read_bytes(),
            (repo / '.git/index').read_bytes(),
            {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob('*')
             if p.is_file() and '.git' not in p.relative_to(repo).parts})

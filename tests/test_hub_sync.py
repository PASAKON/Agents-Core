import json
import pytest
from tools import hub_sync
from tests.hub_sync_support import repository, stubs, commit, git, snapshot


def invoke(repo, go=False):
    letters, output = [], []
    before = snapshot(repo)
    result = hub_sync.run(repo, go, send=lambda r, k, b: letters.append((k, b)), out=output.append)
    assert snapshot(repo) == before
    return result, letters, '\n'.join(output)


def test_nothing(repository, stubs):
    repo, remote = repository
    assert invoke(repo) == (0, [], 'nothing to publish')


@pytest.mark.parametrize('go', [False, True])
def test_publish(repository, stubs, go):
    repo, remote = repository
    original = git(remote, 'rev-parse', 'main')
    local = commit(repo, '.claude/skills/demo/SKILL.md', 'safe change\n')
    # Include staged, unstaged and untracked bytes in the preservation check.
    (repo / 'staged').write_text('staged\n')
    git(repo, 'add', 'staged')
    (repo / 'readme').write_text('dirty\n')
    (repo / 'untracked').write_bytes(b'\x00untracked')
    code, letters, output = invoke(repo, go)
    assert code == 0 and 'plan: 1 commits; 1 files; skills: demo' in output
    assert git(remote, 'rev-parse', 'main') == original
    branches = git(remote, 'for-each-ref', '--format=%(refname)', 'refs/heads/sync/')
    if go:
        assert branches.startswith('refs/heads/sync/contabo-main-')
        assert git(remote, 'rev-parse', branches + '^1') == local
        assert git(remote, 'rev-parse', branches + '^2') == original
        assert letters == [('report', 'hub sync PR #42 ready (1 commits; skills: demo)')]
    else:
        assert not branches and not letters and 'dry run' in output
        (stubs / 'dry-run-output').write_text(output + '\n')


def test_conflict(repository, stubs):
    repo, remote = repository
    base = git(repo, 'rev-parse', 'HEAD')
    commit(repo, 'readme', 'remote change\n')
    git(repo, 'push', 'origin', 'main')
    git(repo, 'reset', '--hard', base)  # fixture setup only
    commit(repo, 'readme', 'local change\n')
    code, letters, output = invoke(repo, True)
    assert code == 3 and letters[0][0] == 'blocker'
    assert not git(remote, 'for-each-ref', '--format=%(refname)', 'refs/heads/sync/')


def test_diverged_without_conflict(repository, stubs):
    repo, remote = repository
    base = git(repo, 'rev-parse', 'HEAD')
    commit(repo, 'remote-only', 'remote change')
    git(repo, 'push', 'origin', 'main')
    git(repo, 'reset', '--hard', base)
    commit(repo, 'local-only', 'local change')
    assert invoke(repo, True)[0] == 0
    branch = git(remote, 'for-each-ref', '--format=%(refname)', 'refs/heads/sync/')
    assert git(remote, 'show', branch + ':remote-only') == 'remote change'
    assert git(remote, 'show', branch + ':local-only') == 'local change'


@pytest.mark.parametrize('scanner', ['gitleaks', 'publish_scan'])
def test_findings(repository, stubs, scanner):
    repo, remote = repository
    value = 'person@private.invalid'
    commit(repo, 'sensitive.txt', value if scanner == 'publish_scan' else 'safe')
    if scanner == 'gitleaks':
        (stubs / 'leaks.json').write_text(json.dumps([{'File': 'sensitive.txt', 'StartLine': 1,
                                                     'RuleID': 'test-rule', 'Secret': value}]))
    code, letters, output = invoke(repo, True)
    assert code == 1 and letters[0][0] == 'blocker'
    assert 'sensitive.txt | 1 |' in letters[0][1]
    assert value not in output + letters[0][1]
    assert not git(remote, 'for-each-ref', '--format=%(refname)', 'refs/heads/sync/')


def test_superseded(repository, stubs):
    repo, remote = repository
    old = git(repo, 'rev-parse', 'HEAD')
    commit(repo, 'new', 'safe')
    (stubs / 'prs.json').write_text(json.dumps([{'number': 7, 'headRefName': 'sync/contabo-main-old', 'headRefOid': old}]))
    assert invoke(repo, True)[0] == 0
    assert (stubs / 'closed').exists()


def test_existing_candidate(repository, stubs):
    repo, remote = repository
    commit(repo, 'new', 'safe')
    assert invoke(repo, True)[0] == 0
    branch = git(remote, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/sync/')
    oid = git(remote, 'rev-parse', branch)
    (stubs / 'prs.json').write_text(json.dumps([{'number': 42, 'headRefName': branch, 'headRefOid': oid}]))
    code, letters, output = invoke(repo, True)
    assert code == 0 and not letters and 'already contains' in output


def test_errors_are_redacted(repository, stubs, monkeypatch, capsys):
    repo, remote = repository
    monkeypatch.setattr(hub_sync, 'run', lambda *a: (_ for _ in ()).throw(RuntimeError('secret-value')))
    assert hub_sync.main(['--repo', str(repo)]) == 2
    assert 'secret-value' not in capsys.readouterr().out

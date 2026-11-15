import pytest
from tools import publish_scan
from tests.hub_sync_support import repository, commit, git


@pytest.mark.parametrize('rule,value', [
    ('email', 'person@private.invalid'), ('thai-phone', '+6681-234-5678'),
    ('thai-phone', '0812345678'), ('line-id', 'U' + 'abcdef01' * 4),
    ('public-ipv4', '8.8.4.4'), ('thai-id', '1234567890123'),
    ('thai-id', '1-2345-67890-12-3'), ('bank-account', '123-4-56789-0'),
    ('private-key', 'BEGIN RSA PRIVATE KEY'), ('private-key', 'BEGIN PRIVATE KEY'),
    *[('url-credential', '?' + key + '=abcdefghij') for key in
      ('access_token', 'token', 'key', 'sig', 'signature', 'code')],
    *[('credential', key + '=abcdefghij') for key in ('password', 'secret', 'api_key', 'token')],
    ('credential', 'password="hello world"'),
    ('url-credential', '&signature=abcdefghij'),
])
def test_rules(repository, capsys, rule, value):
    repo, _ = repository
    commit(repo, 'sample.txt', value + '\n')
    hits, _ = publish_scan.scan(repo, 'origin/main', 'HEAD')
    assert rule in {h.rule for h in hits}
    assert publish_scan.main(['origin/main', 'HEAD', '--repo', str(repo)]) == 1
    output = capsys.readouterr().out
    assert value not in output
    assert 'sample.txt | ' + rule + ' | ' in output


@pytest.mark.parametrize('value', [
    'noreply@anthropic.com', '123@users.noreply.github.com', 'a@example.com',
    'a@example.org', 'a@localhost', '  @decorator(token="abcdefghij")',
    '10.1.2.3', '127.0.0.1', '0.1.2.3', '192.168.1.1', '100.64.0.1',
    '100.127.255.255', '999.8.8.8', "password = :'variable'", 'token=short',
])
def test_allowlist(repository, value):
    repo, _ = repository
    commit(repo, 'sample.txt', value)
    assert publish_scan.scan(repo, 'origin/main', 'HEAD')[0] == []


def test_known_and_removed(repository, capsys):
    repo, _ = repository
    known = 'old@private.invalid'
    fresh = 'new@private.invalid'
    commit(repo, 'existing', known)
    git(repo, 'push', 'origin', 'main')
    commit(repo, 'later', known + '\n' + fresh)
    commit(repo, 'later', 'removed')
    hits, _ = publish_scan.scan(repo, 'origin/main', 'HEAD')
    assert len(hits) == 1 and hits[0].line == 2
    assert publish_scan.main(['origin/main', 'HEAD', '--repo', str(repo)]) == 1
    output = capsys.readouterr().out
    assert known not in output and fresh not in output


def test_binary(repository, capsys):
    repo, _ = repository
    (repo / 'asset.bin').write_bytes(b'\0\x01\x02')
    git(repo, 'add', 'asset.bin')
    git(repo, 'commit', '-m', 'binary')
    assert publish_scan.main(['origin/main', 'HEAD', '--repo', str(repo)]) == 0
    assert 'asset.bin | binary | 3 bytes' in capsys.readouterr().out


def test_known_credential_value(repository):
    repo, _ = repository
    commit(repo, 'old', 'abcdefghij')
    git(repo, 'push', 'origin', 'main')
    commit(repo, 'new', 'password=abcdefghij\n?token=abcdefghij')
    assert publish_scan.scan(repo, 'origin/main', 'HEAD')[0] == []


def test_deleted_binary(repository):
    repo, _ = repository
    (repo / 'asset.bin').write_bytes(b'\x00abc')
    git(repo, 'add', 'asset.bin')
    git(repo, 'commit', '-m', 'binary')
    git(repo, 'push', 'origin', 'main')
    git(repo, 'rm', 'asset.bin')
    git(repo, 'commit', '-m', 'delete binary')
    hits, binaries = publish_scan.scan(repo, 'origin/main', 'HEAD')
    assert not hits and list(binaries.values()) == [4]


def test_error(repository, capsys):
    repo, _ = repository
    assert publish_scan.main(['missing', 'HEAD', '--repo', str(repo)]) == 2
    assert capsys.readouterr().out == 'publish_scan: scan failed\n'

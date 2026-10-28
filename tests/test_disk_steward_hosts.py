import io
import json
import os
import urllib.error
from pathlib import PureWindowsPath
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from tools import disk_steward as ds, drive_leg as dl
from scripts import drive_rest_rclone_shim as shim


@pytest.mark.parametrize('host,command', [('contabo', 'rclone_via_winbox.sh'),
    ('mac', 'drive_rest_rclone_shim.py'), ('winbox', 'rclone')])
def test_routing(monkeypatch, host, command):
    monkeypatch.setenv('ORG_HOST', host)
    monkeypatch.delenv('DRIVE_LEG_RCLONE', raising=False)
    assert dl.rclone_path().endswith(command)
    monkeypatch.setenv('DRIVE_LEG_RCLONE', '/fake')
    assert dl.rclone_path() == '/fake'


@pytest.mark.parametrize('system,command', [('Darwin', 'drive_rest_rclone_shim.py'),
    ('Windows', 'rclone'), ('Linux', 'rclone_via_winbox.sh')])
def test_os_routing(monkeypatch, system, command):
    monkeypatch.delenv('ORG_HOST', raising=False)
    monkeypatch.delenv('DRIVE_LEG_RCLONE', raising=False)
    monkeypatch.setattr(dl.platform, 'system', lambda: system)
    assert dl.rclone_path().endswith(command)


@pytest.mark.skipif(os.name != 'nt', reason='requires native Windows handles')
def test_native_windows_read_delete_and_junction(tmp_path):
    import subprocess
    source = tmp_path / 'source'
    source.mkdir()
    file = source / 'old'
    file.write_bytes(b'archive me')
    with dl._open_runner_source(file) as stream:
        assert stream.read() == b'archive me'
    junction = tmp_path / 'junction'
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(source)], check=True, capture_output=True)
    try:
        with pytest.raises(dl.DriveLegError):
            with dl._open_runner_source(junction / 'old'):
                pass
        st = file.stat()
        assert dl._delete_verified([(junction / 'old', st.st_size, st.st_mtime_ns)]) == 0
        assert dl._delete_verified([(file, st.st_size, st.st_mtime_ns)]) == 1
        assert not file.exists()
    finally:
        junction.rmdir()


def test_report_includes_last_steward(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(ds, 'HUB_DIRS', (tmp_path,))
    tick = '2026-10-28T12:00:00Z'
    (tmp_path / 'mac.json').write_text(json.dumps(dict(volumes=[dict(free_bytes=30*ds.GB)],
        steward=dict(band='orange', tick_at=tick, actions=3))))
    ds.report()
    assert 'steward orange | ' + tick in capsys.readouterr().out


def test_failed_push_does_not_fail_tick(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv('ORG_HOST', 'mac')
    monkeypatch.delenv('ORG_DB_URL', raising=False)
    monkeypatch.setattr(ds, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(ds, 'plan', lambda _: [])
    env = tmp_path / 'push.env'
    env.write_text('DISK_HUB_URL=https://example.test/disk\nDISK_PUSH_TOKEN=private\n')
    monkeypatch.setattr(ds, 'machine', lambda _: dict(hq=str(tmp_path), disk_push_env=str(env)))
    opener = Mock()
    opener.open.side_effect = urllib.error.URLError('private')
    monkeypatch.setattr(ds.urllib.request, 'build_opener', lambda _: opener)
    assert ds.tick('mac') == 0
    output = capsys.readouterr().out
    assert 'private' not in output
    assert json.loads(output.splitlines()[-1])['status'] == 'failed'


def test_windows_contract_and_open_dispatch(monkeypatch):
    monkeypatch.setenv('ORG_HOST', 'winbox')
    monkeypatch.delenv('CLAUDE_CONFIG_DIR', raising=False)
    assert PureWindowsPath(dl.config_dir()) == PureWindowsPath('C:/Users/passg/.claude')
    assert PureWindowsPath(dl.host_config()['home']) == PureWindowsPath('C:/Users/passg')
    monkeypatch.setattr(dl.os, 'name', 'nt')
    fake = Mock(return_value='safe handle')
    monkeypatch.setattr(dl, '_open_windows_source', fake)
    # A Path created before switching os.name keeps the native concrete class.
    from pathlib import PosixPath
    assert dl._open_runner_source(PosixPath('/safe/file')) == 'safe handle'


def test_reparse_attribute(monkeypatch):
    p = Mock()
    p.lstat.return_value = SimpleNamespace(st_mode=0, st_file_attributes=0x400)
    assert dl._linked(p)


@pytest.mark.parametrize('system', ['Darwin', 'Windows'])
def test_non_linux_plan(monkeypatch, system):
    monkeypatch.setattr(ds.platform, 'system', lambda: system)
    monkeypatch.setattr(ds.shutil, 'which', lambda _: '/docker')
    actions = {a['name']: a for a in ds.plan('green')}
    assert actions['journal']['skip'] and actions['build-cache']['skip']


@pytest.mark.parametrize('host', ['mac', 'winbox'])
def test_tick_without_db(monkeypatch, tmp_path, capsys, host):
    monkeypatch.setenv('ORG_HOST', host)
    monkeypatch.delenv('ORG_DB_URL', raising=False)
    monkeypatch.setattr(ds, 'STATE', tmp_path)
    monkeypatch.setattr(ds, 'machine', lambda _: dict(home=str(tmp_path), hq=str(tmp_path), claude_config_dir=str(tmp_path)))
    monkeypatch.setattr(ds, 'plan', lambda _: [dict(name=n, argv=['fake']) for n in ('reap', 'review-idle', 'orphans')])
    run = Mock(side_effect=AssertionError('no DB command should execute'))
    monkeypatch.setattr(ds.subprocess, 'run', run)
    assert ds.tick(host) == 0
    rows = [json.loads(s) for s in capsys.readouterr().out.splitlines()]
    assert all(r['status'] == 'skipped' for r in rows)
    assert {r['name'] for r in rows} == {'reap', 'review-idle', 'orphans', 'letters', 'hub-push'}


@pytest.mark.parametrize('failure', [False, True])
def test_push_no_token_leak(monkeypatch, tmp_path, capsys, failure):
    token = 'very-private-token'
    env = tmp_path / 'push.env'
    env.write_text(f'export DISK_HUB_URL="https://example.test/disk"\nDISK_PUSH_TOKEN={token}\n')
    monkeypatch.setattr(ds, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(ds, 'machine', lambda _: dict(disk_push_env=str(env)))
    calls = []
    class Opener:
        def open(self, req, timeout):
            calls.append(req)
            assert timeout == 10
            if failure:
                raise urllib.error.HTTPError(req.full_url, 500, token, {}, io.BytesIO(token.encode()))
            result = Mock(status=200)
            result.__enter__ = Mock(return_value=result)
            result.__exit__ = Mock(return_value=False)
            return result
    monkeypatch.setattr(ds.urllib.request, 'build_opener', lambda handler: Opener())
    ds.push_tick('mac', 'green', 2)
    out = capsys.readouterr()
    assert token not in out.out + out.err + (ds.STATE / 'steward.jsonl').read_text()
    row = json.loads(out.out)
    assert row['status'] == ('failed' if failure else 'run')
    payload = json.loads(calls[0].data)
    assert payload['steward']['actions'] == 2
    assert payload['volumes'][0]['name'] == '/'
    assert ds._NoRedirect().redirect_request(calls[0], None, 302, '', {}, 'https://elsewhere') is None


def test_shim_nested_and_flat(monkeypatch, capsys):
    from urllib.parse import urlsplit, parse_qs
    root = 'root-folder-id-1234567890'
    objects = []
    monkeypatch.setattr(shim.wa, '_access_token', lambda: 'fake')
    def http(method, url, headers=None, body=None):
        if method == 'GET':
            q = parse_qs(urlsplit(url).query)['q'][0]
            parent = q.split("'")[1]
            return 200, {}, json.dumps({'files': [f for f in objects if f['parents'] == [parent]]}).encode()
        obj = json.loads(body)
        obj['id'] = f'id-{len(objects)}'
        objects.append(obj)
        return 200, {}, json.dumps(obj).encode()
    monkeypatch.setattr(shim.wa, '_http', http)
    def upload(path, name, parent):
        from pathlib import Path
        import hashlib
        data = Path(path).read_bytes()
        obj = dict(id=f'id-{len(objects)}', name=name, parents=[parent], size=len(data), md5Checksum=hashlib.md5(data).hexdigest())
        objects.append(obj)
        return obj
    monkeypatch.setattr(shim, 'upload', upload)
    for _ in range(2):
        shim.main(['mkdir', 'gdrive:a/b/c', '--drive-root-folder-id', root])
    assert len(objects) == 3
    for remote in ('a/b/c/name', 'flat[1]'):
        monkeypatch.setattr(shim.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(b'archive')))
        shim.main(['rcat', 'gdrive:' + remote, '--drive-root-folder-id', root])
    capsys.readouterr()
    shim.main(['lsjson', '--hash', '--no-mimetype', '--files-only', '--drive-root-folder-id', root, 'gdrive:a/b/c'])
    row = json.loads(capsys.readouterr().out)[0]
    assert row['Name'] == 'name' and row['Size'] == 7 and row['ID'] and row['Hashes']['md5']
    shim.main(['lsjson', '--hash', '--files-only', '--no-mimetype', '--drive-root-folder-id', root, 'gdrive:', '--include', '/flat\\[1]'])
    assert json.loads(capsys.readouterr().out)[0]['Name'] == 'flat[1]'

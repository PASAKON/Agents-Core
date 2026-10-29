import hashlib
import io
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tools import disksteward_p2 as p2, drive_leg as drive, disk_steward as ds


def member(path):
    return dict(path=path.name, size=path.stat().st_size, md5=p2.digest(path))


@pytest.mark.parametrize('only', [None, *p2.STEPS, *p2.STEPS.values()])
def test_dry_run_no_calls(monkeypatch, tmp_path, only):
    monkeypatch.setattr(p2, 'execute', Mock(side_effect=AssertionError('mutation')))
    monkeypatch.setattr(p2.subprocess, 'run', Mock(side_effect=AssertionError('subprocess')))
    monkeypatch.setattr(p2, 'RECEIPTS', tmp_path / 'receipts')
    assert p2.main(['--dry-run'] + (['--only', only] if only else [])) == 0
    assert not p2.RECEIPTS.exists()


def test_step_c_sources_exclude_secret_archives(monkeypatch):
    backup = Mock(return_value={})
    monkeypatch.setattr(p2, 'backup', backup)
    monkeypatch.setattr(p2, 'save', Mock())
    monkeypatch.setattr(drive, 'config_dir', lambda: Path('/unused'))
    p2.execute('c')
    sources = [call.args[0] for call in backup.call_args_list]
    assert sources == [Path('/opt/MoonieXHQ/Archive/mooniex-vps/20260613T193125Z'),
                       Path('/opt/MoonieXHQ/Archive/mac-delta-20260924')]
    assert not any(part.startswith(('mac-secrets', 'winbox-keys', 'agents-core-presync'))
                   for source in sources for part in source.parts)


def test_backup_exclusions_and_verified_member_bytes(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    for name in ('data.txt', '.env.prod', 'id_rsa', 'x.pem', 'access_token.txt', 'Cookies'):
        (root / name).write_text('test bytes')
    (root / 'traefik_data').mkdir()
    (root / 'traefik_data' / 'data').write_text('never upload')
    (root / 'link').symlink_to(root / 'data.txt')
    def put(stream, folder, destination, name, ext, manifest, **kwargs):
        data = io.BytesIO()
        stream(data)
        data.seek(0)
        with tarfile.open(fileobj=data) as tf:
            assert tf.getnames() == ['data.txt']
            assert hashlib.md5(tf.extractfile('data.txt').read()).hexdigest() == manifest['files'][0]['md5']
        return dict(manifest, verified=True)
    monkeypatch.setattr(drive, 'put', put)
    verify = Mock()
    monkeypatch.setattr(p2, 'verify_receipt', verify)
    result = drive.lineposter(config_dir=tmp_path, source=root)
    assert len(result['excluded']) == 7
    verify.assert_called_once()
    assert (root / 'data.txt').exists()  # upload-only


def test_verify_requires_ids_tar_and_manifest_hashes(monkeypatch):
    receipt = dict(verified=True, drive={'id': 'tar-id'}, bytes=5, md5='tar-md5',
                   manifest_id='manifest-id', remote_dir='Archive/contabo',
                   tar_name='x.tar', manifest_name='x.manifest.json', files=[])
    uploaded = {k: v for k, v in receipt.items() if k in ('drive', 'bytes', 'md5', 'files')}
    data = (json.dumps(uploaded, indent=2, ensure_ascii=False) + '\n').encode()
    rows = [{'ID': 'tar-id', 'Size': 5, 'Hashes': {'md5': 'tar-md5'}},
            {'ID': 'manifest-id', 'Size': len(data), 'Hashes': {'md5': hashlib.md5(data).hexdigest()}}]
    monkeypatch.setattr(drive, '_lsjson', lambda *a: rows)
    p2.verify_receipt(receipt)
    rows[0]['ID'] = 'same-name-different-id'
    with pytest.raises(ValueError):
        p2.verify_receipt(receipt)
    rows[0]['ID'] = 'tar-id'
    rows[1]['Hashes']['md5'] = 'bad'
    with pytest.raises(ValueError):
        p2.verify_receipt(receipt)


def test_delete_guard_md5_symlink_and_traversal(tmp_path, monkeypatch):
    path = tmp_path / 'data'
    path.write_text('original')
    proof = member(path)
    path.write_text('changed!')
    p2.remove_member(tmp_path, proof)
    assert path.exists()
    path.write_text('original')
    guard = Mock(side_effect=ValueError('NEVER'))
    monkeypatch.setattr(ds, 'guard_path', guard)
    p2.remove_member(tmp_path, proof)
    assert path.exists()
    monkeypatch.setattr(ds, 'guard_path', lambda p: p)
    p2.remove_member(tmp_path, proof)
    assert not path.exists()
    path.symlink_to(tmp_path / 'target')
    (tmp_path / 'target').write_text('original')
    with pytest.raises(OSError):
        p2.remove_member(tmp_path, proof)
    assert (tmp_path / 'target').exists()
    with pytest.raises(ValueError):
        p2.remove_member(tmp_path, dict(proof, path='../target'))


def test_duplicate_mismatch_and_f_cannot_bypass_e(tmp_path, monkeypatch):
    vps, live = tmp_path / 'vps', tmp_path / 'live'
    (vps / 'line-poster').mkdir(parents=True)
    live.mkdir()
    (vps / 'line-poster' / 'data').write_text('old')
    (live / 'data').write_text('new')
    monkeypatch.setattr(p2, 'VPS', vps)
    monkeypatch.setattr(p2, 'LINEPOSTER', live)
    monkeypatch.setattr(p2, 'load', lambda key, root: {'files': [dict(path='line-poster/data', size=3, md5='anything')]})
    delete = Mock()
    monkeypatch.setattr(p2, 'remove_member', delete)
    p2.execute('e')
    delete.assert_not_called()
    monkeypatch.setattr(p2, 'MAC', vps)
    p2.execute('f')
    delete.assert_not_called()


def test_sparse_rolls_back_on_service_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(p2, 'ROOT', tmp_path)
    (tmp_path / 'deploy/systemd').mkdir(parents=True)
    wt = tmp_path / 'worktrees/spend-guard-deploy'
    (tmp_path / 'deploy/systemd/test.service').write_text(f'ExecStart={wt}/tools/run.py\n')
    calls = []
    def run(argv):
        calls.append(list(map(str, argv)))
        if argv[:3] == ['git', 'worktree', 'list']:
            return f'worktree {wt}\n'
        if argv[0] == 'systemctl':
            raise RuntimeError('failed')
        return ''
    monkeypatch.setattr(p2, 'run', run)
    with pytest.raises(RuntimeError):
        p2.sparse()
    assert calls[-1][-2:] == ['sparse-checkout', 'disable']


def test_existing_archive_never_guard_is_not_bypassed(tmp_path):
    root = tmp_path / 'Archive/agents-core-presync-20261010'
    root.mkdir(parents=True)
    path = root / 'data'
    path.write_text('backed up bytes')
    p2.remove_member(root, member(path))
    assert path.exists()


def test_failed_backup_does_not_save_receipt_or_delete(tmp_path, monkeypatch):
    source = tmp_path / 'LinePoster'
    source.mkdir()
    (source / 'data').write_text('keep me')
    monkeypatch.setattr(p2, 'LINEPOSTER', source)
    monkeypatch.setattr(p2, 'RECEIPTS', tmp_path / 'receipts')
    monkeypatch.setattr(drive, 'put', Mock(side_effect=drive.DriveLegError('failed')))
    with pytest.raises(drive.DriveLegError):
        p2.execute('d')
    assert not p2.RECEIPTS.exists()
    assert (source / 'data').read_text() == 'keep me'
    p2.execute('e')  # Missing receipt must skip before walking any duplicate.
    assert (source / 'data').exists()


def test_weekly_success_stamp_and_failure_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(ds, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(ds.policy, 'host_key', lambda host=None: host or 'contabo')
    monkeypatch.setattr(ds, 'machine', lambda host: {'hq': str(tmp_path)})
    monkeypatch.setattr(ds, 'letters', lambda *a: None)
    monkeypatch.setattr(ds, 'plan', lambda band: [dict(name='lineposter', argv=['fake'], weekly=True)])
    run = Mock(return_value=SimpleNamespace(returncode=1))
    monkeypatch.setattr(ds, 'run_action', run)
    ds.tick('contabo')
    ds.tick('contabo')
    assert run.call_count == 2
    run.return_value.returncode = 0
    ds.tick('contabo')
    ds.tick('contabo')
    assert run.call_count == 3

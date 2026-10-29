import copy
import json
from pathlib import PureWindowsPath
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml
from tools import disk_steward as ds, storage_policy as sp
from lib import resource_gate as gate


@pytest.mark.parametrize('host,free,expected', [('contabo',20,'green'), ('contabo',10,'yellow'),
    ('contabo',5,'orange'), ('contabo',4.9,'red'), ('winbox',60,'green'),
    ('winbox',30,'yellow'), ('winbox',15,'orange'), ('winbox',14,'red'), ('mac',8,'orange')])
def test_bands_and_gate(monkeypatch, host, free, expected):
    monkeypatch.setattr(gate.shutil, 'disk_usage', lambda _: SimpleNamespace(free=free*ds.GB))
    monkeypatch.setattr(gate, 'ram_available_mb', lambda _: 5000)
    monkeypatch.setattr(gate, 'disk_used_pct', lambda _: 91)
    monkeypatch.delenv('ORG_SPAWN_DISK_MAX_PCT', raising=False)
    monkeypatch.setenv('ORG_SPAWN_GATE', '1')
    assert gate.read(host=host).band == expected
    for kind in ('project_head', 'developer', 'video_editor', 'download'):
        assert bool(gate.check(host=host, kind=kind)) == (expected == 'red' or expected == 'orange' and kind in ('video_editor', 'download'))
    monkeypatch.setenv('ORG_SPAWN_DISK_MAX_PCT', '99')
    assert gate.check(host=host, kind='video_editor') is None
    monkeypatch.setenv('ORG_SPAWN_DISK_MAX_PCT', '80')
    assert gate.check(host=host)


@pytest.mark.parametrize('name', ['Cookies','Login Data','Local Storage/item','IndexedDB/a','Local State',
    'oauth.json','credentials.json','.credentials.json','.config/gh/hosts.yml','rclone.conf',
    '.env','auth.json','.ssh/id_rsa','Archive/mac-secrets-2026/a','Archive/winbox-keys/a',
    'Archive/mooniex-vps/.env.example','docker/volumes/x','docker/image/x'])
def test_never(name):
    for p in ('/safe/' + name, PureWindowsPath('C:/safe') / name):
        with pytest.raises(ValueError):
            ds.guard_path(p, cwds=[])


@pytest.mark.parametrize('name', [
    'mooniex-vps/20260613T193125Z/' + name for name in (
        'alphatrader/.env', 'option/.env', 'option/.env.example', 'option/.env.enc',
        'option/.env.bak.1781211822', 'docker-n8n/.env', 'claudeflow/.env',
        'line-automation/.env', 'line-automation/.env.example', 'id_rsa',
        'traefik_data/x', 'acme.json', 'line-poster/windows.security.credentials.dll')
] + ['mac-secrets-20260924/x', 'winbox-keys-20260924/x', 'agents-core-presync-20261010/x'])
def test_archive_secret_guards(name):
    for p in ('/safe/Archive/' + name, PureWindowsPath('C:/safe/Archive') / name):
        with pytest.raises(ValueError):
            ds.guard_path(p, cwds=[])


@pytest.mark.parametrize('name', ['line-poster/file', 'volumes/file'])
def test_archive_nonsecret_allowed(name):
    for p in ('/safe/Archive/mooniex-vps/20260613T193125Z/' + name,
              PureWindowsPath('C:/safe/Archive/mooniex-vps/20260613T193125Z') / name):
        assert ds.guard_path(p, cwds=[])


def test_cwd_tmp_images_and_safe_windows(tmp_path):
    for p, kwargs in [('/tmp/claude-0/a', {}), (tmp_path, {'cwds':[tmp_path/'child']}),
                      ('/safe/image', {'in_use_image':True})]:
        with pytest.raises(ValueError):
            ds.guard_path(p, **kwargs)
    path = PureWindowsPath('C:/Work/task-1/tmp/render')
    assert ds.guard_path(path, cwds=[]) == path
    with pytest.raises(ValueError):
        ds.guard_path(path.parent, cwds=[path])


def test_coverage():
    policy = sp.load(sp.POLICY_PATH)
    plans = yaml.safe_load((sp.ROOT/'config/plans.yaml').read_text())
    machines = yaml.safe_load(sp.MACHINES_PATH.read_text())
    sp.validate_coverage(policy, plans, machines)
    for runner in plans['buckets']:
        broken = copy.deepcopy(policy)
        del broken['runners'][runner]
        with pytest.raises(sp.PolicyError):
            sp.validate_coverage(broken, plans, machines)
    for host in machines['machines']:
        for field in ('band','scheduler','drive_leg'):
            broken = copy.deepcopy(machines)
            del broken['machines'][host][field]
            with pytest.raises(sp.PolicyError):
                sp.validate_coverage(policy, plans, broken)


def test_delegate_floor_uses_target_host():
    from tools import delegate
    assert delegate._disk_orange_floor_gb('contabo') == 5
    assert delegate._disk_orange_floor_gb('mac') == 5
    assert delegate._disk_orange_floor_gb('winbox') == 15


def test_guarded_reclaim_keeps_nested_login_state(tmp_path):
    from tools import storage_reclaim
    target = tmp_path / 'node_modules'
    target.mkdir()
    (target / 'Cookies').write_text('protected')
    assert storage_reclaim.apply([{'path':str(target)}], tmp_path/'ledger', steward_guard=True) == []
    assert (target / 'Cookies').exists()


@pytest.mark.parametrize('free,extra', [(25,[]),(15,['unread-caches']),
    (8,['unread-caches','rebuild','largest-lane']),(1,['rebuild','cto-red'])])
def test_dry_run_never_runs(monkeypatch, tmp_path, capsys, free, extra):
    monkeypatch.setattr(ds, 'cto_main_box', lambda: 'cto-primary')
    monkeypatch.setattr(ds, 'STATE', tmp_path/'state')
    monkeypatch.setattr(ds, 'lane_usage', lambda _: {})
    monkeypatch.setattr(ds.shutil, 'which', lambda _: '/bin/docker')
    run = Mock(side_effect=AssertionError('dry-run must never execute'))
    monkeypatch.setattr(ds.subprocess, 'run', run)
    ds.tick('contabo', True, free)
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    names = [row['name'] for row in rows]
    assert names[:4] == ['hub-band','reap','review-idle','build-cache']
    assert all(n in names for n in ['transcripts','runner-state','orphans'] + extra)
    assert ('rebuild' in names) == (free < 10)
    assert all('rc' in r and 'bytes_before' in r and 'bytes_after' in r for r in rows)
    run.assert_not_called()
    assert not ds.STATE.exists()


def test_daily_stamps_and_orphan_close(monkeypatch, tmp_path):
    monkeypatch.setenv('ORG_DB_URL', 'postgresql://unused-test-only')
    monkeypatch.setattr(ds, 'STATE', tmp_path/'state')
    monkeypatch.setattr(ds, 'lane_usage', lambda _: {})
    monkeypatch.setattr(ds, 'machine', lambda _: {'hq':str(tmp_path), 'home':str(tmp_path), 'claude_config_dir':str(tmp_path/'.claude')})
    monkeypatch.setattr(ds.shutil, 'disk_usage', lambda _: SimpleNamespace(free=25*ds.GB))
    run = Mock(side_effect=lambda argv, **_: SimpleNamespace(returncode=0, stdout='[{"task":"task-123"}]' if 'orphans' in argv else ''))
    monkeypatch.setattr(ds.subprocess, 'run', run)
    ds.tick('contabo')
    assert any('close' in c.args[0] and '--archive' in c.args[0] for c in run.call_args_list)
    run.reset_mock()
    ds.tick('contabo')
    assert not any('transcripts' in c.args[0] or 'orphans' in c.args[0] for c in run.call_args_list)


def test_letter_dedupe_reuses_delivery(monkeypatch, tmp_path):
    from lib import mailbox
    monkeypatch.setattr(ds, 'STATE', tmp_path)
    monkeypatch.setattr(ds, 'cto_main_box', lambda: 'cto-primary')
    monkeypatch.setattr(ds, 'lane_usage', lambda _: {'cmo-owner':123})
    send = Mock()
    monkeypatch.setattr(mailbox, 'send', send)
    stamps = {}
    ds.letters('contabo','red','2026-10-28',stamps,False)
    assert send.call_count == 3
    ds.letters('contabo','red','2026-10-28',stamps,False)
    assert send.call_count == 3
    assert all(c.args[0] != 'ceo' for c in send.call_args_list)

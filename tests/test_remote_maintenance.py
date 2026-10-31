"""C4/C5: no live DB, SSH or Drive; local Git fixture for outgoing history."""
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import textwrap

import pytest

from tools import remote_maintenance as rm
from lib import db, mesh

# Looked up before any fixture puts a fake first on PATH: the real-binary tests
# need it, and they are skipped on a host (a CI runner) that has none.
REAL_GITLEAKS = shutil.which('gitleaks')
ORIGINAL_PATH = os.environ['PATH']


class FakeGitleaks:
    """A `gitleaks` first on PATH. It records how it was called, writes the
    report it was told to, prints `noise` on both streams and exits `code`."""

    def __init__(self, monkeypatch, tmp_path):
        self.dir = tmp_path / 'fakebin'
        self.dir.mkdir()
        self.log = tmp_path / 'gitleaks-calls.jsonl'
        monkeypatch.setenv('PATH', str(self.dir) + os.pathsep + ORIGINAL_PATH)
        self.set()

    def set(self, code=0, findings=(), noise='', sleep=0):
        cfg = json.dumps(dict(log=str(self.log), code=code, findings=list(findings), noise=noise, sleep=sleep))
        script = self.dir / 'gitleaks'
        script.write_text(f'#!{sys.executable}\n' + textwrap.dedent('''\
            import json, os, sys, time
            cfg = json.loads(%r)
            argv = sys.argv[1:]
            report = argv[argv.index('--report-path') + 1]
            with open(cfg['log'], 'a') as stream:
                rules = open(argv[argv.index('--config') + 1]).read() if '--config' in argv else None
                stream.write(json.dumps(dict(argv=argv, cwd=os.path.realpath(os.getcwd()), report=report,
                                             config=rules)) + '\\n')
            time.sleep(cfg['sleep'])
            with open(report, 'w') as stream:
                json.dump(cfg['findings'], stream)
            sys.stdout.write(cfg['noise'])
            sys.stderr.write(cfg['noise'])
            sys.exit(cfg['code'])
            ''') % cfg)
        script.chmod(0o755)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []


@pytest.fixture(autouse=True)
def gitleaks(monkeypatch, tmp_path):
    """Default: a scanner that finds nothing, so a host without the binary runs
    every other test here. The tests of the scan itself reset it."""
    return FakeGitleaks(monkeypatch, tmp_path)


@pytest.fixture(autouse=True)
def hub_url(monkeypatch):
    """The URL the hub holds, in these tests: where the fixture repository's origin
    really is. The tests of the URL rules set their own."""
    monkeypatch.setattr(rm, 'publish_url', lambda wt: _run(wt, 'config', 'remote.origin.url').strip())


@pytest.mark.parametrize('path,root', [
    ('/other/task', '/allowed'), ('/allowed', '/allowed'),
    ('/allowed/../other', '/allowed'), ('C:\\Work\\x', '/allowed'),
    (PureWindowsPath('D:/Work/task'), PureWindowsPath('C:/Work')),
    (PureWindowsPath('C:/Work/../other'), PureWindowsPath('C:/Work')),
    (PureWindowsPath('//server/share/task'), PureWindowsPath('C:/Work')),
])
def test_outside_root(path, root):
    with pytest.raises(ValueError):
        rm.contained(path, root)


def test_windows_lexical():
    assert rm.contained(PureWindowsPath('C:/Work/task'), PureWindowsPath('C:/Work')).name == 'task'


@pytest.fixture
def remote(monkeypatch, tmp_path):
    host_root = tmp_path / 'trees'
    wt = host_root / 'project__developer__task-1234abcd'
    wt.mkdir(parents=True)
    work = tmp_path / 'Work' / 'task-1234abcd'
    (work / 'out').mkdir(parents=True)
    (work / 'out' / 'deliverable.txt').write_text('deliverable')
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'winbox')
    monkeypatch.setattr(rm.config, 'host', lambda _: {'worktrees': str(host_root)})
    monkeypatch.setattr(rm.disk_steward, 'machine', lambda _: {'hq': str(tmp_path)})
    monkeypatch.setitem(sys.modules, 'psutil', SimpleNamespace(process_iter=lambda: []))
    monkeypatch.setattr(rm.disk_steward, 'live_cwds', lambda: [])
    monkeypatch.setattr(rm, 'clean_origin', lambda *_: 'a' * 40)
    calls = []
    monkeypatch.setattr(rm, 'git', lambda wt, *args: calls.append(args) or '/fake/common')
    row = dict(id='task-1234abcd', host='winbox', worktree=str(wt),
               branch='agent/claude-task-1234abcd', status='done',
               updated_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat())
    return row, wt, work, calls


def test_default_dry_run(remote, monkeypatch):
    row, wt, work, calls = remote
    monkeypatch.setattr(rm.workdir, 'close', lambda *a, **k: pytest.fail('dry run closed'))
    result = rm.reap(rm.encode({'tasks': [row]}))
    assert result['results'][0]['status'] == 'planned'
    assert work.exists() and wt.exists() and not calls


@pytest.mark.parametrize('name', ['.env', 'nested/oauth.json', '.ssh/id_rsa', 'nested/token.txt'])
def test_never_descendants(remote, name):
    row, wt, work, calls = remote
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('protected')
    result = rm.reap(rm.encode({'tasks': [row], 'apply': True}))
    assert result['results'][0]['status'] == 'failed'
    assert 'NEVER' in result['results'][0]['error']
    assert path.exists() and not calls


def test_symlink_refused(remote, tmp_path):
    row, wt, work, calls = remote
    (work / 'out' / 'escape').symlink_to(tmp_path, target_is_directory=True)
    assert rm.reap(rm.encode({'tasks': [row]}))['results'][0]['status'] == 'failed'


def test_live_cwd_refuses_cleanup(remote, monkeypatch):
    row, wt, work, calls = remote
    monkeypatch.setattr(rm.disk_steward, 'live_cwds', lambda: [wt])
    result = rm.reap(rm.encode({'tasks': [row], 'apply': True}))
    assert 'live process cwd' in result['results'][0]['error']
    assert wt.exists() and work.exists() and not calls


def test_archive_failure_preserves_worktree(remote, monkeypatch):
    row, wt, work, calls = remote
    monkeypatch.setattr(rm.workdir, 'close', lambda *a, **k: {'closed': False})
    result = rm.reap(rm.encode({'tasks': [row], 'apply': True}))
    assert result['results'][0]['status'] == 'failed'
    assert wt.exists() and not calls


def test_archive_then_remove(remote, monkeypatch):
    row, wt, work, calls = remote
    def close(tid, **kw):
        assert kw == {'root': work.parent, 'archive': True}
        calls.append(('archive-verified',))
        return {'closed': True}
    monkeypatch.setattr(rm.workdir, 'close', close)
    assert rm.reap(rm.encode({'tasks': [row], 'apply': True}))['results'][0]['status'] == 'run'
    assert calls[0] == ('archive-verified',)
    assert calls[-1][-3:] == ('worktree', 'remove', str(wt))


def test_caps_and_grace(remote, monkeypatch):
    row, wt, work, calls = remote
    with pytest.raises(ValueError, match='cap'):
        rm.reap(rm.encode({'tasks': [row] * 4}))
    monkeypatch.setattr(rm, 'MAX_BYTES', 1)
    assert 'cap' in rm.reap(rm.encode({'tasks': [row]}))['results'][0]['error']
    row['updated_at'] = datetime.now(timezone.utc).isoformat()
    assert 'grace' in rm.reap(rm.encode({'tasks': [row]}))['results'][0]['error']


@pytest.mark.parametrize('dirty,remote_sha', [(True, 'a' * 40), (False, 'b' * 40)])
def test_clean_origin_refuses(monkeypatch, tmp_path, dirty, remote_sha):
    def git(wt, *args):
        return {'symbolic-ref': 'agent/test-task-1234abcd', 'status': ' M code.py' if dirty else '',
                'rev-parse': 'a' * 40,
                'ls-remote': remote_sha + '\trefs/heads/agent/test-task-1234abcd'}[args[0]]
    monkeypatch.setattr(rm, 'git', git)
    with pytest.raises(ValueError):
        rm.clean_origin(tmp_path, 'agent/test-task-1234abcd')


def test_hub_dispatch_and_accounting(remote, monkeypatch, tmp_path):
    row, _, _, _ = remote
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rm.disk_steward, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(db, 'list_tasks', lambda **kw: [row])
    calls, records = [], []
    def dispatch(host, verb, payload):
        request = rm.decode(payload)
        calls.append((host, verb, request))
        return {'ok': True, 'result': {'results': [dict(task_id=r['id'],
            status='run' if request['apply'] else 'planned') for r in request['tasks']]}}
    monkeypatch.setattr(mesh, 'dispatch', dispatch)
    monkeypatch.setattr(rm.disk_steward, 'record', lambda row, dry: records.append(row))
    assert rm.hub_reap() == 0
    assert all(not c[2]['apply'] for c in calls)
    assert {r['status'] for r in records} == {'planned'}
    calls.clear()
    assert rm.hub_reap(apply=True) == 0
    assert rm.hub_reap(apply=True) == 0
    assert calls[-2][2]['tasks'] == []  # successful rows do not starve next batch
    assert {'reap', 'orphans'} == {r['name'] for r in records}


def test_review_status_write_does_not_publish(monkeypatch):
    task = dict(id='task-1234abcd', host='winbox', status='review', branch='agent/claude-task-1234abcd')
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def execute(self, *a): return SimpleNamespace(rowcount=1)
    monkeypatch.setattr(db, 'get_conn', lambda: Conn())
    monkeypatch.setattr(db, 'get_task', lambda _: task)
    monkeypatch.setattr(db, 'log_event', lambda *a, **k: None)
    monkeypatch.setattr(db, 'release_task_locks', lambda *a: None)
    calls = []
    monkeypatch.setattr(mesh, 'dispatch', lambda *a: calls.append(a) or {'ok': True})
    assert db.update_status(task['id'], 'review')
    assert calls == []


@pytest.mark.parametrize('hours,eligible', [(19, False), (21, True)])
@pytest.mark.parametrize('host', ['winbox', 'mac'])
def test_remote_grace_independent_of_local_orphans(remote, monkeypatch, tmp_path, hours, eligible, host):
    row, _, _, _ = remote
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    row['host'] = host
    row['updated_at'] = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    assert rm.workdir._abandon_days() == 14
    assert rm.reap_grace_seconds() == 20 * 3600
    monkeypatch.setattr(rm.config, 'self_host', lambda: host)
    result = rm.reap(rm.encode({'tasks': [row]}))['results'][0]
    assert result['status'] == ('planned' if eligible else 'failed')
    if not eligible:
        assert 'grace' in result['error']
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rm.disk_steward, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(db, 'list_tasks', lambda **kw: [row])
    monkeypatch.setattr(rm.disk_steward, 'record', lambda *a: None)
    selected = []
    def dispatch(host, verb, payload):
        tasks = rm.decode(payload)['tasks']
        selected.extend(tasks)
        return {'ok': True, 'result': {'results': [
            dict(task_id=t['id'], status='planned') for t in tasks]}}
    monkeypatch.setattr(mesh, 'dispatch', dispatch)
    assert rm.hub_reap() == 0
    assert [t['id'] for t in selected] == ([row['id']] if eligible else [])


def test_remote_grace_reads_config(monkeypatch):
    monkeypatch.setattr(rm.disk_steward.policy, 'load',
                        lambda _: {'remote_reap': {'grace_hours': 12},
                                   'work_dir': {'abandon_days': 14}})
    assert rm.reap_grace_seconds() == 12 * 3600


def test_bootstrap_and_retry(monkeypatch):
    from runners import branch_poller as bp
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    monkeypatch.setattr(bp, 'self_host', lambda: 'contabo')
    task = dict(id='task-1234abcd', host='winbox', status='in_progress')
    changes = []
    monkeypatch.setattr(mesh, 'dispatch', lambda *a: {'ok': True, 'result': {'ready': True, 'report': 'report'}})
    monkeypatch.setattr(db, 'update_status', lambda *a, **k: changes.append((a, k)))
    bp._publish_via_mesh(task)
    assert changes[0][0] == (task['id'], 'review')
    calls = []
    monkeypatch.setattr(rm, 'hub_publish', lambda t: calls.append(t))
    bp._publish_via_mesh({**task, 'status': 'review'})
    assert calls


def test_ph_binding(remote):
    row, wt, _, _ = remote
    for branch in ['main', 'ph/deadbeef-topic', 'ph/1234abcd-topic:main']:
        with pytest.raises(ValueError, match='bound'):
            rm.publish(rm.encode({**row, 'session_id': '1234abcd', 'branch': branch}), ph=True)


def test_ph_publish_exact_commit(remote, monkeypatch):
    row, wt, _, calls = remote
    ph_wt = wt.parent / 'project__ph-1234abcd'
    ph_wt.mkdir()
    branch = 'ph/1234abcd-fix'
    checked = []
    monkeypatch.setattr(rm, 'outgoing_check', lambda *a, **k: checked.append((a, k)) or 'a' * 40)
    def git(wt, *args):
        calls.append(args)
        return branch if args[0] == 'symbolic-ref' else ''
    monkeypatch.setattr(rm, 'git', git)
    result = rm.publish(rm.encode({**row, 'session_id': '1234abcd', 'branch': branch,
                                  'worktree': str(ph_wt), 'status': 'review'}), ph=True)
    assert result == {'branch': branch, 'head': 'a' * 40, 'pushed': True}
    assert checked == [((ph_wt, branch), {'push': True})]     # the checked head is the pushed head


def test_completion_waits_for_launcher_commit(remote, monkeypatch, tmp_path):
    from lib import proc
    row, wt, _, _ = remote
    monkeypatch.setattr(proc, 'pid_alive', lambda _: False)
    gitdir = tmp_path / 'gitdir'
    gitdir.mkdir()
    row.update(pid=123, status='in_progress')
    def git(wt, *args):
        if args == ('rev-parse', '--absolute-git-dir'): return str(gitdir)
        if args[0] == 'rev-parse': return 'a' * 40
        if args[0] == 'show': return '# REPORT ' + row['id'] + '\n\nDone'
        return ''
    monkeypatch.setattr(rm, 'git', git)
    assert not rm.completion(rm.encode(row))['ready']
    (gitdir / 'org-publish-ready').write_text('b' * 40)
    assert not rm.completion(rm.encode(row))['ready']
    (gitdir / 'org-publish-ready').write_text('a' * 40)
    assert rm.completion(rm.encode(row))['ready']
    monkeypatch.setattr(proc, 'pid_alive', lambda _: True)
    assert not rm.completion(rm.encode(row))['ready']


@pytest.mark.parametrize('matching', [True, False])
def test_reap_drive_checksum_and_log(remote, monkeypatch, tmp_path, matching):
    from tools import work_archive
    row, wt, work, calls = remote
    log = tmp_path / 'drive-archive.log'
    monkeypatch.setattr(work_archive, 'LOG_PATH', str(log))
    def upload(path, name):
        return dict(id='fake-id', name=name,
                    md5Checksum=work_archive._hash_file(path)[1] if matching else '0' * 32)
    monkeypatch.setattr(work_archive, '_default_uploader', upload)
    result = rm.reap(rm.encode({'tasks': [row], 'apply': True}))['results'][0]
    assert result['status'] == ('run' if matching else 'failed')
    assert work.exists() is not matching
    if matching:
        assert log.exists() and 'fake-id' in log.read_text()
    else:
        assert (work / 'out' / 'deliverable.txt').exists()
        assert not calls


def test_mesh_metadata_no_remote_db(remote, monkeypatch, tmp_path):
    from tools import node_dispatch as nd
    row, _, _, _ = remote
    monkeypatch.setattr(nd, 'MAINTENANCE_AUDIT_DIR', tmp_path / 'audit')

    def no_db(*a, **k):  # this host holds no DB secret: the connection fails at once
        raise RuntimeError('no DB on this host')
    monkeypatch.setattr(db, 'get_conn', no_db)
    payload = rm.encode({'tasks': [row]})
    assert len('steward_reap ' + payload) > 256
    reply, code = nd.run_command('steward_reap ' + payload)
    assert code == 0 and reply['result']['dry_run']
    assert (nd.MAINTENANCE_AUDIT_DIR / 'maintenance.jsonl').exists()


def test_hub_artefact_gate_retained(monkeypatch):
    from runners import branch_poller as bp
    task = dict(id='task-1234abcd', host='winbox', status='review', runner='agy',
                project='project', branch='agent/agy-task-1234abcd')
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    monkeypatch.setattr(bp, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rm, 'hub_publish', lambda t: {'ok': True, 'result': {'head': 'a' * 40}})
    monkeypatch.setattr(bp, 'get_project', lambda _: {})
    monkeypatch.setattr(bp, '_repo_path_here', lambda _: '/fake/repo')
    monkeypatch.setattr(bp, 'fetch_branch', lambda *a: None)
    class FailedGate:
        reasons = ['tests failed']
        def __bool__(self): return False
    monkeypatch.setattr(bp, '_artefact_gate_for_external_runner', lambda *a: FailedGate())
    changes = []
    monkeypatch.setattr(db, 'update_status', lambda *a, **k: changes.append((a, k)))
    bp._publish_via_mesh(task)
    assert changes[0][0] == (task['id'], 'failed')


def test_remote_poll_batches_rotate():
    from runners import branch_poller as bp
    bp._REMOTE_CURSOR.clear()
    rows = [dict(id=f'task-{i:08x}', host='winbox') for i in range(7)]
    assert [r['id'] for r in bp._remote_batch(rows, 'test')] == [r['id'] for r in rows[:3]]
    assert [r['id'] for r in bp._remote_batch(rows, 'test')] == [r['id'] for r in rows[3:6]]
    bp._REMOTE_CURSOR.clear()


def test_git_worktree_removal_preserves_published_branch(tmp_path, monkeypatch):
    repo, origin, roots = tmp_path / 'repo', tmp_path / 'origin', tmp_path / 'trees'
    def run(*args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True)
    run('init', '--bare', str(origin))
    run('init', str(repo))
    run('config', 'user.email', 'test@example.test', cwd=repo)
    run('config', 'user.name', 'Test', cwd=repo)
    (repo / 'code.py').write_text('pass')
    run('add', '.', cwd=repo)
    run('commit', '-m', 'base', cwd=repo)
    run('remote', 'add', 'origin', str(origin), cwd=repo)
    branch = 'agent/test-task-1234abcd'
    wt = roots / 'project__developer__task-1234abcd'
    run('worktree', 'add', '-b', branch, str(wt), cwd=repo)
    run('push', 'origin', branch, cwd=repo)
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'mac')
    monkeypatch.setattr(rm.config, 'host', lambda _: {'worktrees': str(roots)})
    monkeypatch.setattr(rm.disk_steward, 'machine', lambda _: {'hq': str(tmp_path)})
    monkeypatch.setitem(sys.modules, 'psutil', SimpleNamespace(process_iter=lambda: []))
    row = dict(id='task-1234abcd', host='mac', branch=branch, worktree=str(wt), status='done',
               updated_at=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat())
    result = rm.reap(rm.encode({'tasks': [row], 'apply': True}))
    assert result['results'][0]['status'] == 'run', result
    assert not wt.exists()
    assert run('rev-parse', branch, cwd=repo).stdout.strip()
    assert run('ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch, cwd=repo).stdout.strip()


@pytest.mark.parametrize('filename,size', [('clip.mp4', 1048577), ('large.txt', 1048577), ('clip.png', 10)])
def test_deleted_outgoing_object_refused(tmp_path, filename, size):
    repo, origin = tmp_path / 'repo', tmp_path / 'origin'
    def run(*args, cwd=None):
        return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True)
    run('init', '--bare', str(origin))
    run('init', str(repo))
    run('config', 'user.email', 'test@example.test', cwd=repo)
    run('config', 'user.name', 'Test', cwd=repo)
    (repo / 'code.py').write_text('pass')
    run('add', '.', cwd=repo)
    run('commit', '-m', 'base', cwd=repo)
    run('remote', 'add', 'origin', str(origin), cwd=repo)
    run('push', 'origin', 'HEAD:main', cwd=repo)
    branch = 'agent/test-task-1234abcd'
    run('checkout', '-b', branch, cwd=repo)
    (repo / filename).write_bytes(b'x' * size)
    run('add', '.', cwd=repo)
    run('commit', '-m', 'media', cwd=repo)
    run('rm', filename, cwd=repo)
    run('commit', '-m', 'remove media', cwd=repo)
    with pytest.raises(ValueError, match='outgoing'):
        rm.outgoing_check(repo, branch)


# --- worker_completion: a dead worker whose launcher never committed ---------

def _run(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def dead_worker(monkeypatch, tmp_path):
    """Real git: a winbox worktree on its task branch, the worker's pid gone."""
    from lib import proc
    origin, root = tmp_path / 'origin.git', tmp_path / 'trees'
    wt = root / 'project__developer__task-1234abcd'
    root.mkdir()
    _run(tmp_path, 'init', '--bare', '-b', 'main', str(origin))
    _run(tmp_path, 'clone', '-q', str(origin), str(wt))
    _run(wt, 'config', 'user.email', 'test@example.test')
    _run(wt, 'config', 'user.name', 'Test')
    (wt / 'base.py').write_text('base = 1\n')
    _run(wt, 'add', 'base.py')
    _run(wt, 'commit', '-q', '-m', 'base')
    _run(wt, 'checkout', '-q', '-b', 'agent/claude-task-1234abcd')
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'winbox')
    monkeypatch.setattr(rm.config, 'host', lambda _: {'worktrees': str(root)})
    monkeypatch.setattr(proc, 'pid_alive', lambda _: False)
    monkeypatch.setattr(rm, 'RECOVERY_QUIET_S', 0)
    row = dict(id='task-1234abcd', host='winbox', worktree=str(wt), pid=4242,
               branch='agent/claude-task-1234abcd', status='in_progress',
               spawned_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat())
    return row, wt


def _stage_complete_diff(wt, report=True):
    (wt / 'feature.py').write_text('feature = 1\n')
    (wt / '.worker.json').write_text('{}')          # launcher scratch, staged by `add -A`
    (wt / 'clip.mp4').write_bytes(b'\0' * 2048)      # media never goes to git
    names = ['feature.py', '.worker.json', 'clip.mp4']
    if report:
        (wt / 'docs' / 'reports' / 'task-1234abcd').mkdir(parents=True)
        (wt / 'docs' / 'reports' / 'task-1234abcd' / 'REPORT.md').write_text('# REPORT task-1234abcd\n\nDone\n')
        names.append('docs/reports/task-1234abcd/REPORT.md')
    _run(wt, 'add', '-f', *names)
    (wt / 'notes.txt').write_text('untracked, stays untracked')


def test_dead_pid_with_staged_diff_and_no_marker_is_committed_by_the_hub(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt)
    before = _run(wt, 'rev-parse', 'HEAD').strip()

    result = rm.completion(rm.encode(row))

    head = _run(wt, 'rev-parse', 'HEAD').strip()
    assert result['ready'] and result['head'] == head != before
    assert result['report'].startswith('# REPORT task-1234abcd')
    committed = _run(wt, 'show', '--name-only', '--format=', 'HEAD').split()
    assert sorted(committed) == ['docs/reports/task-1234abcd/REPORT.md', 'feature.py']
    assert _run(wt, 'status', '--porcelain', '--untracked-files=no') == ''
    assert (wt / 'notes.txt').exists() and 'notes.txt' not in _run(wt, 'ls-files')
    marker = Path(_run(wt, 'rev-parse', '--absolute-git-dir').strip()) / 'org-publish-ready'
    assert marker.read_text() == head
    # a second call (publish retry) sees the marker and commits nothing more
    assert rm.completion(rm.encode(row))['head'] == head
    assert _run(wt, 'rev-parse', 'HEAD').strip() == head


def test_unstaged_tracked_edits_are_recovered_too(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt)
    _run(wt, 'commit', '-q', '-m', 'worker commit')   # report + feature committed ...
    (wt / 'base.py').write_text('base = 2\n')          # ... a tracked edit left unstaged
    assert rm.completion(rm.encode(row))['ready']
    assert _run(wt, 'show', 'HEAD:base.py') == 'base = 2\n'


def test_recovery_waits_while_git_state_is_recent_or_the_pid_lives(dead_worker, monkeypatch):
    from lib import proc
    row, wt = dead_worker
    _stage_complete_diff(wt)
    before = _run(wt, 'rev-parse', 'HEAD')
    monkeypatch.setattr(rm, 'RECOVERY_QUIET_S', 3600)          # launcher may still be mid-step
    assert not rm.completion(rm.encode(row))['ready']
    monkeypatch.setattr(rm, 'RECOVERY_QUIET_S', 0)
    monkeypatch.setattr(proc, 'pid_alive', lambda _: True)     # worker still running
    assert not rm.completion(rm.encode(row))['ready']
    (Path(_run(wt, 'rev-parse', '--absolute-git-dir').strip()) / 'index.lock').write_text('')
    monkeypatch.setattr(proc, 'pid_alive', lambda _: False)    # a git command holds the index
    assert not rm.completion(rm.encode(row))['ready']
    assert _run(wt, 'rev-parse', 'HEAD') == before             # nothing was committed


def test_recovery_refuses_without_a_report_and_commits_nothing(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt, report=False)
    before = _run(wt, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match='no report'):
        rm.completion(rm.encode(row))
    assert _run(wt, 'rev-parse', 'HEAD') == before


def test_recovery_refuses_a_report_for_another_task(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt)
    (wt / 'docs' / 'reports' / 'task-1234abcd' / 'REPORT.md').write_text('# REPORT task-ffffffff\n')
    with pytest.raises(ValueError, match='mismatch'):
        rm.completion(rm.encode(row))


def test_publish_never_recovers_on_its_own(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt)
    before = _run(wt, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match='launcher has not completed'):
        rm.publish(rm.encode({**row, 'status': 'review'}))
    assert _run(wt, 'rev-parse', 'HEAD') == before


# --- wire format, git output, duty split -------------------------------------

@pytest.mark.parametrize('bad', ['-', '', 'AB', 'abc', 'zz', '00', '5b5d', 'ab' * 3751, 'ABCD1234'])
def test_decode_refuses_anything_but_lowercase_hex_of_a_json_object(bad):
    with pytest.raises((ValueError, TypeError)):
        rm.decode(bad)


def test_encode_is_plain_lowercase_hex():
    assert re.fullmatch(r'[0-9a-f]+', rm.encode({'id': 'task-1234abcd', 'path': 'C:\\Users\\x y'}))


def test_git_failure_text_is_redacted_and_bounded(monkeypatch, tmp_path):
    token = 'ghp_' + 'A1b2C3d4' * 5
    err = 'x' * 900 + f" fatal: Authentication failed for 'https://x-access-token:{token}@github.com/o/r.git/'"
    monkeypatch.setattr(rm.subprocess, 'run',
                        lambda argv, **kw: subprocess.CompletedProcess(argv, 128, '', err))
    with pytest.raises(ValueError) as caught:
        rm.git(tmp_path, 'fetch', '--prune', 'origin')
    text = str(caught.value)
    assert 'https://***@github.com' in text and len(text) < 400
    assert token not in text and 'x-access-token' not in text


def test_hub_audit_redacts_every_string_of_a_remote_reply():
    token = 'ghp_' + 'Z' * 36
    reply = {'results': [{'error': f'push https://u:{token}@h/x failed', 'bytes': 1}], 'n': None}
    cleaned = rm.redact_reply(reply)
    assert token not in json.dumps(cleaned) and cleaned['results'][0]['bytes'] == 1


def _hub_poller(monkeypatch, bp, rows):
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    monkeypatch.setattr(bp, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(bp.db, 'list_tasks',
                        lambda status=None, limit=0: [r for r in rows if r['status'] == status])
    calls = []
    monkeypatch.setattr(mesh, 'dispatch', lambda host, verb, *a: calls.append((host, verb, rm.decode(a[0])['id'])) or {'ok': True, 'result': {'ready': False}})
    monkeypatch.setattr(bp, 'check_task', lambda t: bp._publish_via_mesh(t))
    return calls


def test_hub_only_asks_about_rows_it_dispatched(monkeypatch):
    from runners import branch_poller as bp
    rows = [dict(id=f'task-0000000{i}', host='winbox', dispatcher_host=d, status='in_progress')
            for i, d in enumerate(['contabo', 'mac', 'winbox', None])]
    calls = _hub_poller(monkeypatch, bp, rows)
    bp.tick()
    assert sorted(c[2] for c in calls) == ['task-00000000', 'task-00000003']   # contabo and NULL only


def test_hub_asks_about_three_rows_per_host_per_tick_and_rotates(monkeypatch):
    from runners import branch_poller as bp
    rows = [dict(id=f'task-0000000{i}', host='winbox', dispatcher_host='contabo', status='in_progress')
            for i in range(5)]
    calls = _hub_poller(monkeypatch, bp, rows)
    bp._REMOTE_CURSOR.clear()
    bp.tick()
    bp.tick()
    asked = [c[2] for c in calls]
    ids = [r['id'] for r in rows]
    assert len(asked) == 6
    assert sorted(asked[:3]) == ids[:3]                       # first tick: three rows
    assert sorted(asked[3:]) == sorted([ids[3], ids[4], ids[0]])   # next tick: the rest, then wraps
    bp._REMOTE_CURSOR.clear()


def test_hub_does_nothing_for_remote_rows_with_the_mesh_off(monkeypatch):
    from runners import branch_poller as bp
    rows = [dict(id='task-00000000', host='winbox', dispatcher_host='contabo', status='in_progress')]
    calls = _hub_poller(monkeypatch, bp, rows)
    monkeypatch.delenv(mesh.ENV_FLAG)
    bp.tick()
    assert calls == []


# --- iteration 7: no push without a secret scan, and one cat-file for the objects ---

SECRET = 'not-a-real-' + 'secret-marker-7f3a9c'      # any text that must never be replied or audited
BRANCH = 'agent/claude-task-1234abcd'


def _token():
    """A GitHub-token-shaped string built at run time, so no literal sits in this file."""
    return 'gh' + 'p_' + ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))


def _branch_worktree(tmp_path, branch=BRANCH, dirname='project__developer__task-1234abcd', files=None):
    """Real git. origin has `main`; the worktree (git worktree add, as workers get
    theirs) holds one outgoing commit. Returns (worktree, origin)."""
    origin, repo, root = tmp_path / 'origin.git', tmp_path / 'repo', tmp_path / 'trees'
    root.mkdir(exist_ok=True)
    if not origin.exists():
        _run(tmp_path, 'init', '-q', '--bare', '-b', 'main', str(origin))
        _run(tmp_path, 'init', '-q', '-b', 'main', str(repo))
        _run(repo, 'config', 'user.email', 'test@example.test')
        _run(repo, 'config', 'user.name', 'Test')
        (repo / 'base.py').write_text('base = 1\n')
        _run(repo, 'add', 'base.py')
        _run(repo, 'commit', '-q', '-m', 'base')
        _run(repo, 'remote', 'add', 'origin', str(origin))
        _run(repo, 'push', '-q', 'origin', 'main')
    wt = root / dirname
    _run(repo, 'worktree', 'add', '-q', '-b', branch, str(wt))
    for name, data in (files or {'feature.py': b'feature = 1\n'}).items():
        (wt / name).parent.mkdir(parents=True, exist_ok=True)
        (wt / name).write_bytes(data)
    _run(wt, 'add', '-A')
    _run(wt, 'commit', '-q', '-m', 'work')
    return wt, origin


def _on_mac(monkeypatch, tmp_path):
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'mac')
    monkeypatch.setattr(rm.config, 'host', lambda _: {'worktrees': str(tmp_path / 'trees')})


@pytest.fixture
def outgoing(monkeypatch, tmp_path):
    wt, origin = _branch_worktree(tmp_path)
    _on_mac(monkeypatch, tmp_path)
    row = dict(id='task-1234abcd', host='mac', worktree=str(wt), branch=BRANCH, status='review')
    return row, wt, origin


def _pushed(origin, branch):
    return _run(origin, 'branch', '--list', branch).strip() != ''


def _no_db(monkeypatch, tmp_path):
    """Audit goes to the local file, as on a host that holds no DB secret."""
    from tools import node_dispatch as nd
    monkeypatch.setattr(nd, 'MAINTENANCE_AUDIT_DIR', tmp_path / 'audit')

    def refuse(*a, **k):
        raise RuntimeError('no DB on this host')
    monkeypatch.setattr(db, 'get_conn', refuse)
    return nd


LEAK = dict(RuleID='github-pat', File='src/cfg.py', StartLine=7, Secret=SECRET,
            Match=f'token = "{SECRET}"', Description=SECRET, Message=SECRET,
            Fingerprint=f'abc:src/cfg.py:github-pat:7:{SECRET}')


def test_a_gitleaks_finding_refuses_the_push_and_no_secret_text_is_replied_or_audited(
        outgoing, gitleaks, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    gitleaks.set(code=1, findings=[LEAK], noise=SECRET)
    nd = _no_db(monkeypatch, tmp_path)

    reply, code = nd.run_command(f"publish_branch {row['id']} {rm.encode(row)}")

    assert code == 1 and not reply['ok']
    assert 'github-pat src/cfg.py:7' in reply['error'] and 'not publishing' in reply['error']
    audit = (tmp_path / 'audit' / 'maintenance.jsonl').read_text()
    assert 'github-pat src/cfg.py:7' in audit
    assert SECRET not in json.dumps(reply) and SECRET not in audit
    assert 'Fingerprint' not in audit and 'abc:' not in audit
    assert not _pushed(origin, row['branch'])                  # nothing reached the remote
    [call] = gitleaks.calls()
    assert not Path(call['report']).exists() and not Path(call['report']).parent.exists()   # temp file deleted


def test_every_publish_path_goes_through_the_scan(outgoing, gitleaks, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    gitleaks.set(code=1, findings=[LEAK])
    nd = _no_db(monkeypatch, tmp_path)
    ph_wt, _ = _branch_worktree(tmp_path, branch='ph/1234abcd-fix', dirname='project__ph-1234abcd')
    ph = dict(row, session_id='1234abcd', branch='ph/1234abcd-fix', worktree=str(ph_wt))
    for command in (f"publish_branch {row['id']} {rm.encode(row)}", f"publish_ph {rm.encode(ph)}"):
        reply, code = nd.run_command(command)
        assert code == 1 and 'github-pat src/cfg.py:7' in reply['error'], (command[:20], reply)
    assert not _pushed(origin, row['branch']) and not _pushed(origin, 'ph/1234abcd-fix')
    assert len(gitleaks.calls()) == 2


def test_a_secret_in_a_commit_the_hub_made_for_a_dead_worker_is_not_published(dead_worker, gitleaks):
    row, wt = dead_worker
    gitleaks.set(code=1, findings=[LEAK])
    _stage_complete_diff(wt)                                    # recovery commits with --no-verify
    assert rm.completion(rm.encode(row))['ready']
    before = _run(wt, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match=r'github-pat src/cfg\.py:7.*not publishing'):
        rm.publish(rm.encode({**row, 'status': 'review'}))
    assert _run(wt, 'rev-parse', 'HEAD') == before
    assert not _pushed(wt.parent.parent / 'origin.git', row['branch'])


def test_no_gitleaks_on_path_refuses_and_pushes_nothing(outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    only_git = tmp_path / 'only-git'
    only_git.mkdir()
    os.symlink(shutil.which('git'), only_git / 'git')
    monkeypatch.setenv('PATH', str(only_git))
    with pytest.raises(ValueError) as caught:
        rm.publish(rm.encode(row))
    assert str(caught.value) == 'no gitleaks on mac: not publishing'
    assert not _pushed(origin, row['branch'])


def test_a_clean_scan_lets_the_push_go_ahead_and_runs_gitleaks_without_a_shell(outgoing, gitleaks):
    row, wt, origin = outgoing
    result = rm.publish(rm.encode(row))
    head = _run(wt, 'rev-parse', 'HEAD').strip()
    assert result == {'branch': row['branch'], 'head': head, 'pushed': True}
    assert _run(origin, 'rev-parse', row['branch']).strip() == head
    [call] = gitleaks.calls()
    argv = call['argv']
    assert argv[0] == 'git' and f'--log-opts={head} --not --remotes=public -m' in argv   # one argv element, no shell
    assert {'--redact', '--no-banner', '--ignore-gitleaks-allow'} <= set(argv)
    assert argv[argv.index('--report-format') + 1] == 'json'
    # The source is the hub's own scratch repository, the working directory an
    # empty one, and the rules the hub's: nothing of the worker's is read.
    common = Path(_run(wt, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())
    assert Path(argv[-1]).name == 'scan.git' and common not in Path(argv[-1]).parents
    assert call['cwd'] != str(wt) and call['config'] == rm.HUB_GITLEAKS_TOML


@pytest.mark.parametrize('code,findings,text', [
    (1, [], 'gitleaks failed (exit 1): not publishing'),         # leak exit but no usable report
    (2, [], 'gitleaks failed (exit 2): not publishing'),         # the scanner itself broke
    (1, [{'RuleID': 'a b', 'File': 'x\ny', 'StartLine': 'z'}], '1 finding'),
])
def test_any_non_zero_exit_refuses_with_nothing_but_rule_and_location(outgoing, gitleaks, code, findings, text):
    row, wt, origin = outgoing
    gitleaks.set(code=code, findings=findings, noise=SECRET)
    with pytest.raises(ValueError, match=re.escape(text)) as caught:
        rm.publish(rm.encode(row))
    assert SECRET not in str(caught.value) and '\n' not in str(caught.value)
    assert not _pushed(origin, row['branch'])


def test_a_hung_gitleaks_is_refused_not_waited_for(outgoing, gitleaks, monkeypatch):
    row, wt, origin = outgoing
    gitleaks.set(sleep=30)
    monkeypatch.setattr(rm, 'GITLEAKS_TIMEOUT_S', 1)
    with pytest.raises(ValueError, match='gitleaks timed out: not publishing'):
        rm.publish(rm.encode(row))
    assert not _pushed(origin, row['branch'])


def test_findings_are_capped_and_each_is_rule_and_location_only(outgoing, gitleaks):
    row, wt, origin = outgoing
    gitleaks.set(code=1, findings=[dict(LEAK, StartLine=n) for n in range(1, 10)])
    with pytest.raises(ValueError) as caught:
        rm.outgoing_check(wt, row['branch'])
    message = str(caught.value)
    assert message.count('github-pat') == rm.MAX_FINDINGS and '9 finding' in message
    assert SECRET not in message


needs_gitleaks = pytest.mark.skipif(REAL_GITLEAKS is None, reason='gitleaks is not installed on this host')


@needs_gitleaks
def test_the_real_scanner_passes_clean_code_and_stops_a_committed_token(outgoing, monkeypatch):
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)                  # the real binary, not the fake
    assert rm.outgoing_check(wt, row['branch']) == _run(wt, 'rev-parse', 'HEAD').strip()
    token = _token()
    (wt / 'cfg.py').write_text(f'token = "{token}"\n')
    _run(wt, 'add', 'cfg.py')
    _run(wt, 'commit', '-q', '-m', 'config')
    with pytest.raises(ValueError) as caught:
        rm.publish(rm.encode(row))
    assert 'github-pat cfg.py:1' in str(caught.value) and token[4:] not in str(caught.value)
    assert not _pushed(origin, row['branch'])


@needs_gitleaks
@pytest.mark.parametrize('bypass', ['allowlist-config', 'ignore-file', 'allow-comment'])
def test_the_real_scanner_cannot_be_told_by_the_worker_to_look_away(bypass, outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)
    token = _token()
    allow = '  # gitleaks:allow' if bypass == 'allow-comment' else ''
    (wt / 'cfg.py').write_text(f'token = "{token}"{allow}\n')
    _run(wt, 'add', 'cfg.py')
    _run(wt, 'commit', '-q', '-m', 'config')
    if bypass == 'allowlist-config':
        (wt / '.gitleaks.toml').write_text("[allowlist]\npaths = ['''.*''']\nregexes = ['''.*''']\n")
    elif bypass == 'ignore-file':
        report = tmp_path / 'direct.json'
        subprocess.run([REAL_GITLEAKS, 'git', f'--log-opts=HEAD --not --remotes=origin', '--no-banner', '--redact',
                        '--report-format', 'json', '--report-path', str(report), str(wt)],
                       cwd=wt, capture_output=True)
        (wt / '.gitleaksignore').write_text(json.loads(report.read_text())[0]['Fingerprint'] + '\n')
    _run(wt, 'add', '-A')
    _run(wt, 'commit', '-q', '--allow-empty', '-m', 'the worker hides it')
    # All three hide the token from a scan that reads the worktree: that is what
    # the test is for. The hub scans the git dir from an empty directory.
    naive = subprocess.run([REAL_GITLEAKS, 'git', '--log-opts=HEAD --not --remotes=origin', '--no-banner',
                            str(wt)], cwd=wt, capture_output=True)
    assert naive.returncode == 0, 'the bypass no longer works against a naive scan; rethink this test'
    with pytest.raises(ValueError, match=r'github-pat cfg\.py:1'):
        rm.outgoing_check(wt, row['branch'])
    assert not _pushed(origin, row['branch'])


@needs_gitleaks
def test_the_real_scanner_looks_only_at_what_is_about_to_be_pushed(outgoing, monkeypatch):
    """A secret already on origin must not block every later publish."""
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)
    (wt / 'old.py').write_text(f'token = "{_token()}"\n')
    _run(wt, 'add', 'old.py')
    _run(wt, 'commit', '-q', '-m', 'already public')
    _run(wt, 'push', '-q', 'origin', 'HEAD:refs/heads/' + row['branch'])
    (wt / 'new.py').write_text('fine = 1\n')
    _run(wt, 'add', 'new.py')
    _run(wt, 'commit', '-q', '-m', 'more')
    assert rm.outgoing_check(wt, row['branch']) == _run(wt, 'rev-parse', 'HEAD').strip()


# --- the object listing: one cat-file --batch-check, same verdicts -------------

def _count_cat_file(monkeypatch):
    calls = []
    real = rm.git

    def spy(wt, *args, **kwargs):
        if args and args[0] == 'cat-file':
            calls.append(args)
        return real(wt, *args, **kwargs)
    monkeypatch.setattr(rm, 'git', spy)
    return calls


def test_a_big_branch_costs_one_cat_file_call(tmp_path, monkeypatch):
    files = {f'pkg{n}/mod{m}.py': f'v = {n * 100 + m}\n'.encode() for n in range(6) for m in range(5)}
    wt, _ = _branch_worktree(tmp_path, files=files)
    calls = _count_cat_file(monkeypatch)
    assert rm.outgoing_check(wt, BRANCH) == _run(wt, 'rev-parse', 'HEAD').strip()
    assert len(calls) == 1 and calls[0][1].startswith('--batch-check')


@pytest.mark.parametrize('name,size,message', [
    ('my clip.MP4', 10, 'outgoing media'),                  # name with a space, upper-case extension
    ('dir with space/shot.png', 10, 'outgoing media'),
    ('data/blob.bin', 1048577, 'outgoing object exceeds 1 MB'),
    ('data/blob.txt', 2 * 1048576, 'outgoing object exceeds 1 MB'),
])
def test_media_and_size_verdicts_are_unchanged_by_the_batch_call(tmp_path, name, size, message):
    wt, _ = _branch_worktree(tmp_path, files={'ok.py': b'ok = 1\n', name: b'x' * size})
    with pytest.raises(ValueError, match=message):
        rm.outgoing_check(wt, BRANCH)


def test_a_blob_of_exactly_one_megabyte_is_allowed_and_trees_are_not_blobs(tmp_path):
    wt, _ = _branch_worktree(tmp_path, files={'a/b/c/data.bin': b'x' * 1048576, 'a/b/d.py': b'd = 1\n'})
    assert rm.outgoing_check(wt, BRANCH) == _run(wt, 'rev-parse', 'HEAD').strip()


def test_a_media_name_on_a_large_object_reports_media_first(tmp_path):
    wt, _ = _branch_worktree(tmp_path, files={'big.mp4': b'x' * 2000000})
    with pytest.raises(ValueError, match='outgoing media'):
        rm.outgoing_check(wt, BRANCH)


def test_a_missing_outgoing_object_is_refused(tmp_path, monkeypatch):
    wt, _ = _branch_worktree(tmp_path)
    real = rm.git

    def lose_objects(wt, *args, **kwargs):
        out = real(wt, *args, **kwargs)
        if args and args[0] == 'cat-file':
            return '\n'.join(line.split()[0] + ' missing' for line in out.splitlines())
        return out
    monkeypatch.setattr(rm, 'git', lose_objects)
    with pytest.raises(ValueError, match='outgoing object missing'):
        rm.outgoing_check(wt, BRANCH)


def test_the_length_refusal_names_the_limit_that_applied():
    from tools import node_dispatch as nd
    with pytest.raises(nd.Refusal, match='longer than 256 chars'):
        nd.parse_command('probe ' + 'a' * 300)
    for command in ('worker_completion ' + 'a' * 9000, 'publish_branch task-1234abcd ' + 'a' * 9000):
        with pytest.raises(nd.Refusal, match='longer than 8192 chars'):
            nd.parse_command(command)


# --- iteration 8: the scan input and the push target belong to the hub --------

REAL_PUBLISH_URL = rm.publish_url          # before the autouse fixture replaces it


def _common(wt):
    return Path(_run(wt, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip())


def _commit_token(wt, name='cfg.py'):
    token = _token()
    (wt / name).write_text(f'token = "{token}"\n')
    _run(wt, 'add', name)
    _run(wt, 'commit', '-q', '-m', 'config')
    return token


def _fingerprint(wt, tmp_path):
    report = tmp_path / 'direct.json'
    subprocess.run([REAL_GITLEAKS, 'git', '--log-opts=HEAD --not --remotes=origin', '--no-banner', '--redact',
                    '--report-format', 'json', '--report-path', str(report), str(wt)], cwd=wt, capture_output=True)
    return json.loads(report.read_text())[0]['Fingerprint']


def _plant_in_git_dir(kind, wt, tmp_path):
    """What a worker can write into the repository it shares with the hub."""
    common = _common(wt)
    if kind == 'allowlist-config':
        (common / '.gitleaks.toml').write_text("[allowlist]\npaths = ['''.*''']\nregexes = ['''.*''']\n")
    elif kind == 'ignore-file':
        (common / '.gitleaksignore').write_text(_fingerprint(wt, tmp_path) + '\n')
    elif kind == 'replace-ref':
        twin = _run(wt, 'commit-tree', '-p', 'HEAD~1', '-m', 'clean twin', 'HEAD~1^{tree}').strip()
        _run(wt, 'replace', 'HEAD', twin)
    elif kind == 'public-head-symref':
        _run(wt, 'symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/heads/' + BRANCH)
    elif kind == 'binary-attribute':
        (common / 'info').mkdir(exist_ok=True)
        (common / 'info' / 'attributes').write_text('* -diff\n')
    elif kind == 'textconv':
        (common / 'info').mkdir(exist_ok=True)
        (common / 'info' / 'attributes').write_text('* diff=hide\n')
        _run(wt, 'config', 'diff.hide.textconv', 'true')
    elif kind == 'committed-attributes':
        (wt / '.gitattributes').write_text('* -diff\n')
        _run(wt, 'add', '.gitattributes')
        _run(wt, 'commit', '-q', '-m', 'attributes')


SHARED_GIT_DIR_STATE = ['allowlist-config', 'ignore-file', 'replace-ref', 'public-head-symref',
                        'binary-attribute', 'textconv', 'committed-attributes']


@needs_gitleaks
@pytest.mark.parametrize('kind', SHARED_GIT_DIR_STATE)
def test_scan_input_is_hub_owned(kind, outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)
    _commit_token(wt)
    _plant_in_git_dir(kind, wt, tmp_path)
    with pytest.raises(ValueError, match=r'github-pat cfg\.py:1'):
        rm.publish(rm.encode(row))
    assert not _pushed(origin, row['branch'])


@needs_gitleaks
def test_the_scan_of_a_planted_git_dir_is_what_the_old_input_missed(outgoing, monkeypatch, tmp_path):
    """The planted allow-all config does hide the token from a scan of the shared
    git dir: the guarantee above is not vacuous."""
    row, wt, origin = outgoing
    _commit_token(wt)
    _plant_in_git_dir('allowlist-config', wt, tmp_path)
    old_input = subprocess.run([REAL_GITLEAKS, 'git', '--log-opts=HEAD --not --remotes=origin', '--no-banner',
                                str(_common(wt))], cwd=tmp_path, capture_output=True)
    assert old_input.returncode == 0


@needs_gitleaks
def test_merge_commits_are_scanned(outgoing, monkeypatch):
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)
    _run(wt, 'checkout', '-q', '-b', 'side', 'HEAD~1')
    (wt / 'side.py').write_text('side = 1\n')
    _run(wt, 'add', 'side.py')
    _run(wt, 'commit', '-q', '-m', 'side')
    _run(wt, 'checkout', '-q', BRANCH)
    _run(wt, 'merge', '-q', '--no-ff', '--no-commit', 'side')
    _commit_token(wt)                      # the token enters only with the merge commit itself
    assert len(_run(wt, 'rev-list', '--merges', 'HEAD').split()) == 1
    with pytest.raises(ValueError, match=r'github-pat cfg\.py:1'):
        rm.publish(rm.encode(row))
    assert not _pushed(origin, row['branch'])


def _decoy_holding_the_branch(wt, tmp_path):
    decoy = tmp_path / 'decoy.git'
    _run(tmp_path, 'init', '-q', '--bare', str(decoy))
    _run(wt, 'push', '-q', str(decoy), 'HEAD:refs/heads/' + BRANCH)
    _run(wt, 'config', 'remote.origin.url', str(decoy))
    return decoy


@needs_gitleaks
def test_the_public_history_comes_from_the_hub_url_not_the_repos_remote(outgoing, monkeypatch, tmp_path):
    """A decoy named in remote.origin.url that already holds the commits must not
    make them look public: the token in them is still found."""
    row, wt, origin = outgoing
    monkeypatch.setenv('PATH', ORIGINAL_PATH)
    monkeypatch.setattr(rm, 'publish_url', lambda wt: str(origin))     # what the hub holds
    _commit_token(wt)
    _decoy_holding_the_branch(wt, tmp_path)
    with pytest.raises(ValueError, match=r'github-pat cfg\.py:1'):
        rm.publish(rm.encode(row))
    assert not _pushed(origin, row['branch'])


def test_the_outgoing_range_is_the_hub_urls_not_the_repos_remote(outgoing, monkeypatch, tmp_path):
    """The same guarantee without a scanner: the commit is still outgoing."""
    row, wt, origin = outgoing
    monkeypatch.setattr(rm, 'publish_url', lambda wt: str(origin))     # what the hub holds
    _decoy_holding_the_branch(wt, tmp_path)
    ranges, real = [], rm.git

    def spy(where, *args, **kwargs):
        out = real(where, *args, **kwargs)
        if args and args[0] == 'rev-list' and '--objects' not in args:
            ranges.append(out)
        return out
    monkeypatch.setattr(rm, 'git', spy)
    head = rm.outgoing_check(wt, BRANCH)
    assert ranges == [head]


def test_the_push_goes_to_the_hub_url_and_nowhere_else(outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    decoy = tmp_path / 'decoy.git'
    _run(tmp_path, 'init', '-q', '--bare', str(decoy))
    _run(wt, 'config', 'remote.origin.url', str(decoy))
    head = _run(wt, 'rev-parse', 'HEAD').strip()
    monkeypatch.setattr(rm, 'publish_url', lambda wt: str(origin))
    assert rm.publish(rm.encode(row))['head'] == head
    assert _run(origin, 'rev-parse', row['branch']).strip() == head
    assert _run(decoy, 'branch', '--list').strip() == ''


def test_a_pushurl_that_differs_from_url_is_refused(outgoing, gitleaks, tmp_path):
    row, wt, origin = outgoing
    _run(wt, 'config', 'remote.origin.pushurl', str(tmp_path / 'elsewhere.git'))
    with pytest.raises(ValueError, match='pushurl differs from url'):
        rm.publish(rm.encode(row))
    assert gitleaks.calls() == [] and not _pushed(origin, row['branch'])


def test_a_pushurl_equal_to_url_is_not_a_split(outgoing):
    row, wt, origin = outgoing
    _run(wt, 'config', 'remote.origin.pushurl', _run(wt, 'config', 'remote.origin.url').strip())
    assert rm.publish(rm.encode(row))['pushed']


def test_publish_url_is_the_projects_remote_in_ssh_form_and_nothing_from_the_repo(tmp_path):
    wt = tmp_path / 'mooniex-agents__developer__task-1234abcd'      # no repository at all
    assert REAL_PUBLISH_URL(wt) == 'git@github.com:PASAKON/mooniex-agents.git'
    with pytest.raises(ValueError, match='no publish URL'):
        REAL_PUBLISH_URL(tmp_path / 'no-such-project__developer__task-1234abcd')


# --- the hub's own git calls -------------------------------------------------

def test_hub_git_calls_ignore_replace_refs_and_hooks_and_carry_no_hub_secrets(outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    monkeypatch.setenv('ORG_DB_URL', 'postgresql://hub-secret-marker')
    monkeypatch.setenv('INFISICAL_TOKEN', 'hub-secret-marker')
    env = rm.hub_env()
    assert env['GIT_NO_REPLACE_OBJECTS'] == '1' and env['GIT_TERMINAL_PROMPT'] == '0'
    assert 'ORG_DB_URL' not in env and 'INFISICAL_TOKEN' not in env
    marker = tmp_path / 'hook-ran'
    hook = _common(wt) / 'hooks' / 'reference-transaction'
    hook.write_text(f'#!/bin/sh\necho "$ORG_DB_URL$GIT_NO_REPLACE_OBJECTS" >> {marker}\n')
    hook.chmod(0o755)
    rm.git(wt, 'update-ref', 'refs/hub/x', 'HEAD')
    assert not marker.exists()                                        # no hook of the worker's runs
    rm.git(wt, 'update-ref', 'refs/hub/y', 'HEAD', hooks=True)
    assert marker.exists() and 'hub-secret-marker' not in marker.read_text()   # the proof the hook was live


def test_the_recovery_commit_runs_the_repos_pre_commit_hook(dead_worker):
    row, wt = dead_worker
    _stage_complete_diff(wt)
    hook = wt / '.git' / 'hooks' / 'pre-commit'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)
    before = _run(wt, 'rev-parse', 'HEAD')
    with pytest.raises(ValueError, match='git commit failed'):
        rm.completion(rm.encode(row))
    assert _run(wt, 'rev-parse', 'HEAD') == before                    # unrecovered, nothing committed


# --- the free-RAM floor on winbox, entered through every verb -----------------

GIB = 1024**3


def _verb_commands(row, wt):
    ph = dict(row, session_id='1234abcd', branch='ph/1234abcd-fix', status='review')
    return {
        'publish_branch': f"publish_branch {row['id']} {rm.encode(dict(row, status='review'))}",
        'publish_ph': f'publish_ph {rm.encode(ph)}',
        'worker_completion': f'worker_completion {rm.encode(row)}',
        'steward_reap': f"steward_reap {rm.encode({'tasks': []})}",
    }


@pytest.mark.parametrize('free', [None, GIB, 4 * GIB - 1])
@pytest.mark.parametrize('verb', ['publish_branch', 'publish_ph', 'worker_completion', 'steward_reap'])
def test_every_winbox_verb_needs_4_gib_free_before_it_starts_git(verb, free, outgoing, gitleaks, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    nd = _no_db(monkeypatch, tmp_path)
    monkeypatch.setattr(rm, '_native_windows', lambda: True)
    monkeypatch.setattr(nd, '_win_avail_phys_bytes', lambda: free)
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'winbox')
    started = []
    monkeypatch.setattr(rm, 'git', lambda *a, **k: started.append(a) or '')
    reply, code = nd.run_command(_verb_commands(dict(row, host='winbox', pid=4242), wt)[verb])
    assert code == 1 and 'winbox requires 4 GB free RAM' in reply['error'], reply
    assert started == [] and gitleaks.calls() == [] and not _pushed(origin, row['branch'])


@pytest.mark.parametrize('verb', ['publish_branch', 'publish_ph', 'worker_completion', 'steward_reap'])
def test_with_4_gib_free_a_winbox_verb_gets_past_the_floor(verb, outgoing, monkeypatch, tmp_path):
    row, wt, origin = outgoing
    nd = _no_db(monkeypatch, tmp_path)
    monkeypatch.setattr(rm, '_native_windows', lambda: True)
    monkeypatch.setattr(nd, '_win_avail_phys_bytes', lambda: 4 * GIB)
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'winbox')
    reply, _ = nd.run_command(_verb_commands(dict(row, host='winbox', pid=4242), wt)[verb])
    assert 'free RAM' not in reply.get('error', '')


# --- the hub side: the flag, the PH's review state, the stamp file -----------

class PortfolioConn:
    def __init__(self, stages):
        self.stages = stages

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def execute(self, sql, params):
        assert 'FROM projects' in sql and params == ('1234abcd',)
        return SimpleNamespace(fetchall=lambda: [{'stage': s} for s in self.stages])


@pytest.mark.parametrize('stages,flag,allowed', [
    (['review'], '1', True), (['active', 'review'], '1', True),
    (['active'], '1', False), ([], '1', False),                  # the hub row says not in review
    (['review'], None, False),                                   # mesh dispatch off
])
def test_ph_publish_reads_the_hub_row_and_the_flag(stages, flag, allowed, monkeypatch):
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(db, 'get_conn', lambda **kw: PortfolioConn(stages))
    if flag:
        monkeypatch.setenv(mesh.ENV_FLAG, flag)
    sent = []
    monkeypatch.setattr(mesh, 'dispatch', lambda *a: sent.append(a) or {'ok': True})
    if allowed:
        assert rm.hub_publish_ph('winbox', '1234abcd', 'ph/1234abcd-fix', 'C:\\w\\x__ph-1234abcd') == {'ok': True}
        assert len(sent) == 1
    else:
        with pytest.raises(ValueError):
            rm.hub_publish_ph('winbox', '1234abcd', 'ph/1234abcd-fix', 'C:\\w\\x__ph-1234abcd')
        assert sent == []


def test_hub_reap_sends_nothing_with_the_mesh_flag_off(monkeypatch, tmp_path):
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rm.disk_steward, 'STATE', tmp_path / 'state')
    sent = []
    monkeypatch.setattr(mesh, 'dispatch', lambda *a: sent.append(a) or {'ok': True})
    assert rm.hub_reap(apply=True) == 0 and sent == []
    assert not (tmp_path / 'state').exists()                       # not even the lock


def _reap_state(monkeypatch, tmp_path):
    state = tmp_path / 'state'
    state.mkdir()
    monkeypatch.setenv(mesh.ENV_FLAG, '1')
    monkeypatch.setattr(rm.config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rm.disk_steward, 'STATE', state)
    monkeypatch.setattr(rm.disk_steward, 'record', lambda *a: None)
    monkeypatch.setattr(db, 'list_tasks', lambda **kw: [])
    monkeypatch.setattr(mesh, 'dispatch', lambda *a: {'ok': True, 'result': {'results': []}})
    return state


def test_the_reap_stamp_is_never_read_through_a_link(monkeypatch, tmp_path):
    state = _reap_state(monkeypatch, tmp_path)
    secret = tmp_path / 'elsewhere.json'
    secret.write_text('{"cursor:winbox": "planted"}')
    os.symlink(secret, state / 'remote-reaped.json')
    with pytest.raises(OSError):
        rm.hub_reap(apply=True)
    assert secret.read_text() == '{"cursor:winbox": "planted"}'


def test_the_reap_stamp_is_never_waited_for_on_a_pipe(monkeypatch, tmp_path):
    import signal
    state = _reap_state(monkeypatch, tmp_path)
    os.mkfifo(state / 'remote-reaped.json')
    signal.signal(signal.SIGALRM, lambda *a: pytest.fail('hub_reap blocked on a pipe'))
    signal.alarm(10)
    try:
        with pytest.raises(ValueError, match='not a regular file'):
            rm.hub_reap(apply=True)
    finally:
        signal.alarm(0)


def test_the_reap_stamp_is_written_without_following_a_planted_temp_link(monkeypatch, tmp_path):
    state = _reap_state(monkeypatch, tmp_path)
    victim = tmp_path / 'victim.txt'
    victim.write_text('keep')
    os.symlink(victim, state / 'remote-reaped.json.tmp')
    assert rm.hub_reap(apply=True) == 0
    assert victim.read_text() == 'keep'
    assert json.loads((state / 'remote-reaped.json').read_text()) == {}
    assert not (state / 'remote-reaped.json.tmp').exists()

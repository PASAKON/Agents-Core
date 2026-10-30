"""C4/C5: no live DB, SSH or Drive; local Git fixture for outgoing history."""
from datetime import datetime, timedelta, timezone
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
import json
import re
import subprocess
import sys

import pytest

from tools import remote_maintenance as rm
from lib import db, mesh


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
    monkeypatch.setattr(rm, 'outgoing_check', lambda *_: 'a' * 40)
    def git(wt, *args):
        calls.append(args)
        return branch if args[0] == 'symbolic-ref' else ''
    monkeypatch.setattr(rm, 'git', git)
    result = rm.publish(rm.encode({**row, 'session_id': '1234abcd', 'branch': branch,
                                  'worktree': str(ph_wt), 'status': 'review'}), ph=True)
    assert result['pushed']
    assert calls[-1] == ('push', 'origin', 'a' * 40 + ':refs/heads/' + branch)


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

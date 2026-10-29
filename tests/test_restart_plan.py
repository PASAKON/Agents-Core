import json
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from tools import restart_plan as rp

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
READ_RUNNING_CARDS = rp.read_running_cards
CARD_LIST = ['bash', 'scripts/hub/org-python.sh', 'tools/ask_run.py', 'list', '--status', 'running', '--json']
CARDS_UNAVAILABLE = 'Run cards unavailable; a running card cannot be ruled out.'


@pytest.fixture(autouse=True)
def _no_console(monkeypatch):
    """build_plan asks the Console for running run cards; no test here reaches it."""
    monkeypatch.setattr(rp, 'read_running_cards', lambda: [])


def entry(kind='assistant', minutes=0, **message):
    return {'type': kind, 'timestamp': (NOW-timedelta(minutes=minutes)).isoformat(),
            'message': {'id': 'request-1', 'usage': {'input_tokens': 100,
                        'cache_read_input_tokens': 200, 'cache_creation_input_tokens': 300}, **message}}


def transcript(tmp_path, entries):
    path = tmp_path / 'transcript.jsonl'
    path.write_text('\n'.join(json.dumps(e) for e in entries)+'\n')
    return path


def test_dedupe_last_request(tmp_path):
    path = transcript(tmp_path, [entry(id='old', usage={'input_tokens': 900}), entry(), entry()])
    assert rp.measure(path, NOW)['C'] == 600
    assert len(list(rp.tail_entries(path, 13))) == 3


@pytest.mark.parametrize('after,expected', [(False, 110000), (True, 600)])
def test_compaction(tmp_path, after, expected):
    entries = [entry(), {'type': 'system', 'subtype': 'compact_boundary'}]
    if after:
        entries.append(entry(id='new'))
    assert rp.measure(transcript(tmp_path, entries), NOW)['C'] == expected


@pytest.mark.parametrize('kind,stop,minutes,expected', [
    ('user', None, 0, True), ('user', None, 15, False),
    ('assistant', 'tool_use', 14, True), ('assistant', 'tool_use', 15, False),
    ('assistant', 'end_turn', 0, False), ('assistant', None, 0, False)])
def test_turn(tmp_path, kind, stop, minutes, expected):
    entries = [entry(), entry(kind, minutes, stop_reason=stop,
                             content=[{'type': 'tool_result', 'content': 'ok'}]),
               {'type': 'progress'}]
    assert rp.measure(transcript(tmp_path, entries), NOW)['in_turn'] is expected


@pytest.mark.parametrize('changes,action', [
    ({'in_turn': True, 'status': 'closed'}, 'wait'),
    ({'status': 'closed'}, 'close'),
    ({'charter': None}, 'park'),
    ({'only_waiting_on_ceo': True, 'open_tasks': [{'kind': 'ceo_card'}]}, 'park'),
    ({'last_active': NOW-timedelta(minutes=60, seconds=1)}, 'resume_lazy'),
    ({'last_active': NOW-timedelta(minutes=60)}, 'resume_full'),
    ({'C': 140000}, 'resume_full'), ({'C': 140001}, 'compact_then_resume'),
    ({'charter': None, 'open_tasks': [{'kind': 'task'}]}, 'resume_full'),
    ({'incomplete': True}, 'wait'), ({'override': 'park', 'in_turn': True}, 'park')])
def test_decide(changes, action):
    row = {'name': 'Example', 'C': 100000, 'last_active': NOW, 'charter': 'Work', 'open_tasks': []}
    row.update(changes)
    assert rp.decide(row, NOW)[0] == action


def test_override_file(tmp_path):
    path = tmp_path / 'overrides.json'
    assert rp.load_overrides(path) == {}
    path.write_text('{"abcdef12": "close"}')
    assert rp.load_overrides(path) == {'abcdef12': 'close'}
    path.write_text('{"abcdef12": "kill"}')
    with pytest.raises(ValueError):
        rp.load_overrides(path)


@pytest.mark.parametrize('role', [*rp.roles.c_level_roles(), 'project_head'])
@pytest.mark.parametrize('changes,expected', [
    ({}, 'resume_lazy'), ({'live': False}, 'park'),
    ({'status': 'parked'}, 'park'), ({'status': 'saved'}, 'resume_lazy'),
    ({'status': 'saved', 'charter': 'work', 'last_active': NOW}, 'resume_full'),
    ({'parked': True}, 'park'), ({'override': 'park'}, 'park'),
    ({'status': 'closed'}, 'close'), ({'incomplete': True}, 'wait'),
    ({'only_waiting_on_ceo': True, 'open_tasks': [{'kind': 'ceo_card'}]}, 'park'),
])
def test_live_leadership_no_charter(role, changes, expected):
    row = dict(role=role, live=True, name='Working session', charter=None, status=None,
               open_tasks=[], C=600, last_active=NOW)
    row.update(changes)
    assert rp.decide(row, NOW)[0] == expected


@pytest.mark.parametrize('suffix', ['project', 'spawned_by'])
def test_plan_parked_ph_lock(tmp_path, monkeypatch, suffix):
    from lib import config
    monkeypatch.setattr(rp, 'ROOT', tmp_path)
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    uuid = '00000000-0000-0000-0000-0000abcdef12'
    projects = tmp_path / 'projects' / '-cwd'
    projects.mkdir(parents=True)
    transcript(tmp_path, [entry()]).rename(projects / f'{uuid}.jsonl')
    monkeypatch.setattr(rp, 'session_dirs', lambda host: [tmp_path / 'sessions'])
    monkeypatch.setattr(rp, 'read_registry', lambda dirs: [
        dict(uuid=uuid, sid='abcdef12', role='project_head', name='Parked PH')])
    monkeypatch.setattr(rp, 'read_hub', lambda: {'tasks': [], 'c_level_sessions': []})
    lock = tmp_path / 'state/locks' / f'project_head-abcdef12.{suffix}.parked'
    lock.parent.mkdir(parents=True)
    lock.touch()
    assert rp.build_plan('contabo', NOW, tmp_path)['sessions'][0]['action'] == 'park'
    lock.unlink()
    assert rp.build_plan('contabo', NOW, tmp_path)['sessions'][0]['action'] == 'resume_lazy'


def test_plan_mocked_hub(tmp_path, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    sessions = tmp_path / 'sessions'
    projects = tmp_path / 'projects' / '-cwd'
    projects.mkdir(parents=True)
    uuid = '00000000-0000-0000-0000-0000abcdef12'
    transcript(tmp_path, [entry()]).rename(projects / f'{uuid}.jsonl')
    monkeypatch.setattr(rp, 'session_dirs', lambda host: [sessions])
    monkeypatch.setattr(rp, 'read_registry', lambda dirs: [
        {'uuid': uuid, 'sid': 'abcdef12', 'name': 'Example', 'role': 'cto'}])
    monkeypatch.setattr(rp, 'is_alive', lambda pid: True)
    monkeypatch.setattr(rp, 'read_hub', lambda: {
        'c_level_sessions': [{'session_id': 'abcdef12', 'role': 'cto', 'charter': 'Work', 'status': 'open'}],
        'tasks': [{'id': 'task-example', 'owner_cto': 'abcdef12', 'status': 'in_progress',
                   'host': 'contabo', 'pid': 123, 'runner': 'codex'}]})
    plan = rp.build_plan('contabo', NOW, tmp_path)
    assert plan['sessions'][0]['action'] == 'resume_full'
    assert plan['sessions'][0]['est_cost_M'] == pytest.approx(.0012)
    assert plan['extra_cost_M'] == pytest.approx(.00114)
    assert len(plan['running_workers']) == 1
    assert plan['warnings']
    assert rp.main(['--host', 'contabo', '--now', NOW.isoformat(), '--out-dir', str(tmp_path), '--json']) == 0
    assert len(list(tmp_path.glob('contabo-*.json'))) == 1


def test_unavailable_hub(tmp_path, monkeypatch):
    from lib import config
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rp, 'session_dirs', lambda host: [])
    monkeypatch.setattr(rp, 'read_registry', lambda dirs: [])
    def unavailable():
        raise RuntimeError('private connection details')
    monkeypatch.setattr(rp, 'read_hub', unavailable)
    plan = rp.build_plan('contabo', NOW, tmp_path)
    assert 'private' not in json.dumps(plan)
    assert plan['warnings']


FRESH_UUID = 'd405e3e2-5e46-406d-b9ae-a6f2f69c4825'


@pytest.mark.parametrize('tmux,lock_value,role', [
    ('cto-fresh:@82.%82', FRESH_UUID, 'cto'),
    ('cto-fresh:@82.%82', '00000000-0000-0000-0000-000000000000', 'unknown'),
    ('wd-f69c4825:@82.%82', FRESH_UUID, 'unknown'),
    ('ceo-fresh:@82.%82', FRESH_UUID, 'unknown'),
    ('czo-fresh:@82.%82', FRESH_UUID, 'unknown'),
])
def test_fresh_identity(tmp_path, monkeypatch, tmux, lock_value, role):
    from tools import live_sessions as ls
    monkeypatch.setattr(ls, 'LOCKS_DIR', tmp_path)
    (tmp_path / f'{tmux.split(":")[0]}.uuid').write_text(lock_value)
    assert ls._ids_from_record({'tmux': tmux}, '🌐 CTO (Kavin)', FRESH_UUID) == (
        role, 'f69c4825', role == 'cto')


@pytest.mark.parametrize('kind', ['missing', 'symlink', 'writable', 'hardlink'])
def test_fresh_identity_requires_safe_lock(tmp_path, monkeypatch, kind):
    from tools import live_sessions as ls
    monkeypatch.setattr(ls, 'LOCKS_DIR', tmp_path)
    lock = tmp_path / 'cto-fresh.uuid'
    target = tmp_path / 'target'
    target.write_text(FRESH_UUID)
    if kind == 'symlink':
        lock.symlink_to(target)
    elif kind == 'hardlink':
        lock.hardlink_to(target)
    elif kind == 'writable':
        lock.write_text(FRESH_UUID)
        lock.chmod(0o666)
    assert ls._ids_from_record({'tmux': 'cto-fresh:@82.%82'}, '🌐 CTO (Kavin)', FRESH_UUID) == (
        'unknown', 'f69c4825', False)


@pytest.mark.parametrize('status,action', [('saved', 'resume_full'), ('parked', 'park'), ('closed', 'close')])
def test_fresh_registry_to_plan(tmp_path, monkeypatch, status, action):
    from lib import config
    from tools import live_sessions as ls
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(ls, 'LOCKS_DIR', tmp_path)
    monkeypatch.setattr(ls, 'is_alive', lambda *a: True)
    (tmp_path / 'cto-fresh.uuid').write_text(FRESH_UUID)
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    (sessions / '123.json').write_text(json.dumps(dict(
        pid=123, sessionId=FRESH_UUID, tmux='cto-fresh:@82.%82', name='🌐 CTO (Kavin)')))
    projects = tmp_path / 'projects' / '-cwd'
    projects.mkdir(parents=True)
    transcript(tmp_path, [entry()]).rename(projects / f'{FRESH_UUID}.jsonl')
    monkeypatch.setattr(rp, 'session_dirs', lambda host: [sessions])
    monkeypatch.setattr(rp, 'read_hub', lambda: {'c_level_sessions': [
        dict(role='cto', session_id='fresh', charter='CTO Main charter', status=status),
        dict(role='cto', session_id='f69c4825', charter=None, status='parked')]})
    row = rp.build_plan('contabo', NOW, tmp_path)['sessions'][0]
    assert row['role'] == 'cto'
    assert row['launcher_id'] == 'fresh'
    assert row['charter'] == 'CTO Main charter'
    assert row['status'] == status
    assert row['action'] == action


def card_list(monkeypatch, stdout='[]', returncode=0, error=None):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if error:
            raise error
        return subprocess.CompletedProcess(argv, returncode, stdout, 'stderr is never reported')
    monkeypatch.setattr(rp.subprocess, 'run', run)
    return calls


def test_running_cards_call(monkeypatch):
    monkeypatch.delenv('HOME', raising=False)
    monkeypatch.setenv('KEEP_ME', '1')
    calls = card_list(monkeypatch, '[{"id": "RUN-1", "status": "running"}]')
    assert READ_RUNNING_CARDS() == [{'id': 'RUN-1', 'status': 'running'}]
    (argv, kwargs), = calls
    assert argv == CARD_LIST
    assert kwargs['cwd'] == rp.ROOT
    assert kwargs['timeout'] == 30
    assert kwargs['env']['HOME'] == '/root'
    assert kwargs['env']['KEEP_ME'] == '1'


def test_running_cards_keep_an_existing_home(monkeypatch):
    monkeypatch.setenv('HOME', '/home/operator')
    calls = card_list(monkeypatch)
    assert READ_RUNNING_CARDS() == []
    assert calls[0][1]['env']['HOME'] == '/home/operator'


@pytest.mark.parametrize('failure', [
    dict(returncode=1, stdout='[]'),
    dict(stdout='not json'),
    dict(stdout=''),
    dict(stdout='{"asks": []}'),
    dict(stdout='[1]'),
    dict(error=subprocess.TimeoutExpired(CARD_LIST, 30)),
    dict(error=FileNotFoundError('bash')),
])
def test_running_cards_unreadable(monkeypatch, failure):
    card_list(monkeypatch, **failure)
    assert READ_RUNNING_CARDS() is None


def cards_warnings(tmp_path, monkeypatch, cards):
    from lib import config
    monkeypatch.setattr(config, 'self_host', lambda: 'contabo')
    monkeypatch.setattr(rp, 'session_dirs', lambda host: [])
    monkeypatch.setattr(rp, 'read_registry', lambda dirs: [])
    monkeypatch.setattr(rp, 'read_hub', lambda: {'c_level_sessions': [], 'tasks': []})
    monkeypatch.setattr(rp, 'read_running_cards', lambda: cards)
    return rp.build_plan('contabo', NOW, tmp_path)['warnings']


def test_running_card_is_a_warning(tmp_path, monkeypatch):
    warnings = cards_warnings(tmp_path, monkeypatch, [{'id': 'RUN-20261027-0001'}, {'status': 'running'}])
    assert 'Do not cut: run card RUN-20261027-0001 (running)' in warnings
    assert 'Do not cut: run card ? (running)' in warnings
    assert CARDS_UNAVAILABLE not in warnings


def test_no_running_card_no_warning(tmp_path, monkeypatch):
    warnings = cards_warnings(tmp_path, monkeypatch, [])
    assert not [w for w in warnings if 'run card' in w.lower()]


def test_unreadable_cards_fail_closed(tmp_path, monkeypatch):
    assert CARDS_UNAVAILABLE in cards_warnings(tmp_path, monkeypatch, None)

"""PH status contract; temporary SQLite hub, no real panes, models or mail."""
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from lib import db, ph_state as p
from tools import ph_brain, run_watch_driver as driver


@pytest.fixture
def hub(monkeypatch, tmp_path):
    monkeypatch.delenv('ORG_DB_URL', raising=False)
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'hub.db')
    monkeypatch.setattr(p, 'require_hub', lambda: None)
    monkeypatch.setattr(p, 'host_name', lambda: 'contabo')
    db.init()
    return tmp_path


def rows():
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM ph_state ORDER BY host').fetchall()]


def turn(**kw):
    return p.turn(session_id='053', project='CookieRun', brain=kw.pop('brain', 'agy'),
                  model=kw.pop('model', 'argon'), doing='Plan\nnext step',
                  owner='cto-fresh', lane='cto', **kw)


@pytest.mark.parametrize('host', ['contabo', 'winbox', 'mac'])
@pytest.mark.parametrize('brain,model', [('agy', 'argon'), ('agy', 'flash'),
                                       ('agy', 'claude'), ('codex', 'future')])
def test_every_brain_and_host_records_start_end(hub, host, brain, model):
    with turn(host=host, brain=brain, model=model) as result:
        row = rows()[0]
        assert (row['host'], row['brain'], row['model']) == (host, brain, model)
        assert row['phase'] == 'thinking' and row['pid'] == os.getpid()
        assert row['doing'] == 'Plan next step' and row['ended'] is None
        result['returncode'] = 0
    assert rows()[0]['phase'] == 'idle'
    assert rows()[0]['exit_code'] == 0 and rows()[0]['ended'] is not None


def test_exception_always_records_exit(hub):
    with pytest.raises(ValueError), turn():
        raise ValueError('runner failed')
    assert rows()[0]['exit_code'] == 1


def test_state_boundaries_and_remote_pid(hub):
    with turn():
        row = rows()[0]
        now = row['updated']
        assert p.phase(row, now=now+600, local_host='contabo', alive=lambda _: True) == 'thinking'
        assert p.phase(row, now=now+601, local_host='contabo', alive=lambda _: True) == 'silent'
        assert p.phase(row, now=now, local_host='contabo', alive=lambda _: False) == 'silent'
        assert p.phase(row, now=now, local_host='mac', alive=lambda _: False) == 'thinking'


def test_actual_killed_pid(hub):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        assert p.pid_alive(child.pid)
        child.kill()
        child.wait(timeout=5)
        with turn():
            row = rows()[0] | {'pid': child.pid}
            assert p.phase(row, now=row['updated'], local_host='contabo') == 'silent'
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()


def test_waits_resolve_and_silent_letter_once(hub):
    with turn() as result:
        result['returncode'] = 0
    now = rows()[0]['updated']
    task = {'owner_cto': '053', 'status': 'running'}
    assert p.observe(rows(), now=now, local_host='contabo', tasks=[task])[0]['phase'] == 'waiting'
    task['status'] = 'done'
    assert p.observe(rows(), now=now, local_host='contabo', tasks=[task])[0]['phase'] == 'idle'
    p.wait('053', 'Q-test')
    assert p.observe(rows(), now=now, local_host='contabo', pending_card=lambda _: True)[0]['phase'] == 'waiting'
    assert p.observe(rows(), now=now, local_host='contabo', pending_card=lambda _: False)[0]['phase'] == 'idle'
    with turn():
        old = rows()
        p.observe(old, now=old[0]['updated']+601, local_host='contabo')
        p.observe(rows(), now=old[0]['updated']+602, local_host='contabo')
        with db.get_conn() as conn:
            letters = conn.execute('SELECT * FROM letters').fetchall()
        assert len(letters) == 1
        assert letters[0]['to_role'] == 'cto' and letters[0]['to_session'] == 'fresh'


def test_late_observer_cannot_alert_ended_turn(hub):
    with turn():
        old = rows()
    p.observe(old, now=old[0]['updated']+601, local_host='contabo')
    with db.get_conn() as conn:
        assert not conn.execute('SELECT * FROM letters').fetchall()


def test_native_pane_and_staleness(hub):
    session = {'session_id': '053', 'host': 'contabo', 'project': 'CookieRun'}
    p.observe_native(session, 'esc to interrupt', now=1000)
    assert rows()[0]['phase'] == 'thinking'
    assert p.phase(rows()[0], now=1001, local_host='contabo') == 'thinking'
    p.observe_native(session, '❯ 1. Yes\nEnter to select', now=1002)
    assert rows()[0]['phase'] == 'waiting'
    p.observe_native(session, '❯ ', now=1003)
    assert rows()[0]['phase'] == 'idle'
    snap = {'at': 1003, 'rows': rows()}
    assert '💤 #053 CookieRun · contabo · 3:00' == p.render(snap, now=1183)
    assert p.render(snap, now=1184).startswith('⚠️')
    assert p.render(None, now=1000).startswith('⚠️')
    assert p.suffix(rows()) == ' · PH 🧠0 ⏳0 🔴0'


def test_raw_runner_cannot_skip_turn():
    with pytest.raises(RuntimeError, match='run_turn'):
        ph_brain.invoke_agy('skip telemetry', model='any')


def test_future_adapter_must_use_same_door(hub, monkeypatch):
    def codex(*args, **kwargs):
        row = rows()[0]
        assert row['phase'] == 'thinking' and row['brain'] == 'codex'
        assert row['model'] == 'future-model'
        return dict(ok=True, returncode=0, response='planned', limit_hit=None)
    monkeypatch.setitem(ph_brain.BRAIN_RUNNERS, 'codex', codex)
    ph_brain.run_turn(ph_id='053', message='Plan', brain='codex',
                      preferred_model='future-model', brains_dir=hub / 'brains')
    assert rows()[0]['phase'] == 'idle'


@pytest.mark.parametrize('model', [m for m, _ in ph_brain.MODEL_CHAIN])
def test_all_real_model_paths_enter_turn(hub, monkeypatch, model):
    def invoke(*args, **kwargs):
        assert rows()[0]['phase'] == 'thinking'
        assert rows()[0]['model'] == model
        return dict(ok=True, returncode=0, response='planned', limit_hit=None)
    monkeypatch.setattr(ph_brain, 'invoke_agy', invoke)
    monkeypatch.setattr(ph_brain, 'select_model_chain', lambda *a, **kw: [model])
    ph_brain.run_turn(ph_id='053', message='Plan', brains_dir=hub / 'brains')
    assert rows()[0]['exit_code'] == 0


def test_display_independent_of_driver(hub, monkeypatch, capsys):
    from tools import run_watch
    monkeypatch.setenv('RUN_WATCH_STATE_DIR', str(hub))
    path = run_watch.state_file('contabo').with_name('ph.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'at': 1000, 'rows': []}))
    monkeypatch.setattr(run_watch.time, 'time', lambda: 1181)
    assert run_watch.ph_display('contabo', once=True) == 0
    assert '⚠️' in capsys.readouterr().out


def test_no_hub_refuses_local_recording(monkeypatch):
    monkeypatch.delenv('ORG_DB_URL', raising=False)
    with pytest.raises(db.HubUnavailable):
        p.require_hub()


@pytest.mark.parametrize('failure', ['no_url', 'connect', 'query', 'timeout', 'end'])
@pytest.mark.parametrize('fallback', [False, True])
def test_telemetry_failure_does_not_fail_brain_turn(monkeypatch, tmp_path, caplog, failure, fallback):
    from contextlib import contextmanager

    monkeypatch.delenv('ORG_DB_URL', raising=False)
    local_db = tmp_path / 'must-not-exist.db'
    monkeypatch.setattr(db, 'DB_PATH', local_db)
    calls = []
    if failure != 'no_url':
        monkeypatch.setenv('ORG_DB_URL', 'postgresql://test.invalid/hub')

    class Connection:
        def execute(self, sql, *args):
            calls.append(sql)
            if failure == 'query' or (failure == 'end' and sql.startswith('UPDATE')):
                raise RuntimeError('query failed')

    @contextmanager
    def connection():
        assert failure != 'no_url', 'must never open a local database'
        if failure == 'connect':
            raise ConnectionError('connection failed')
        if failure == 'timeout':
            raise TimeoutError('connection timed out')
        yield Connection()

    monkeypatch.setattr(db, 'get_conn', connection)
    monkeypatch.setattr(p, 'host_name', lambda: 'contabo')
    monkeypatch.setattr(ph_brain, 'select_model_chain', lambda *a, **kw: ['test-model', 'fallback'])
    def invoke(*args, model, **kwargs):
        failed = fallback and model == 'test-model'
        return dict(ok=not failed, returncode=1 if failed else 0,
                    response='planned', limit_hit='quota' if failed else None)
    monkeypatch.setattr(ph_brain, 'invoke_agy', invoke)
    with caplog.at_level('WARNING', logger='lib.ph_state'):
        result = ph_brain.run_turn(ph_id='053', message='Plan', brains_dir=tmp_path / 'brains')
    assert result['ok'] is True
    assert result['response'] == 'planned'
    warnings = [r for r in caplog.records if r.name == 'lib.ph_state']
    assert len(warnings) == 1
    assert warnings[0].levelname == 'WARNING'
    assert len(warnings[0].getMessage().splitlines()) == 1
    assert not local_db.exists()
    if failure == 'end':
        assert any(sql.startswith('INSERT') for sql in calls)
        assert any(sql.startswith('UPDATE') for sql in calls)


def test_snapshot_all_hosts_and_native_shell_does_not_override_brain(hub, monkeypatch):
    for host in ('contabo', 'winbox', 'mac'):
        with turn(host=host):
            pass
    with db.get_conn() as conn:
        conn.execute("""INSERT INTO c_level_sessions
            (role,session_id,spawned_at,host,status)
            VALUES ('project_head','053','now','contabo','open')""")
        conn.execute("""INSERT INTO c_level_sessions
            (role,session_id,spawned_at,host,status)
            VALUES ('project_head','054','now','contabo','open')""")
    def query(sql, params):
        with db.get_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]
    captures = []
    def capture(*args):
        captures.append(args)
        return SimpleNamespace(returncode=0, stdout='esc to interrupt')
    monkeypatch.setattr(driver.watch, '_query', query)
    monkeypatch.setattr(driver.rename_service, '_read', lambda name: '')
    monkeypatch.setattr(driver.rename_service, 'tmux', capture)
    snapshot = driver.ph_snapshot('contabo', p.time.time())
    assert not snapshot.get('error')
    assert {r['host'] for r in snapshot['rows']} == {'contabo', 'winbox', 'mac'}
    assert len(captures) == 1 and captures[0][-1] == '=project_head-054:0.0'
    assert next(r for r in snapshot['rows'] if r['session_id'] == '054')['phase'] == 'thinking'
    assert all(r['phase'] == 'idle' for r in snapshot['rows'] if r['session_id'] == '053')

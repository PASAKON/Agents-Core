import json
from datetime import timedelta
from unittest.mock import Mock

import pytest

from lib import mailbox
from tools import disk_steward as ds


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(ds, 'M4_HISTORY_DIR', tmp_path / 'history')
    monkeypatch.setattr(ds.policy, 'host_key', lambda host=None: host or 'contabo')
    ds.M4_HISTORY_DIR.mkdir()
    send = Mock(return_value='letter-id')
    monkeypatch.setattr(mailbox, 'send', send)
    return send


def history(host, samples):
    (ds.M4_HISTORY_DIR / f'{host}.hist.jsonl').write_text(''.join(
        json.dumps({'t': (ds.M4_DUE + timedelta(hours=hours)).timestamp(),
                    'free': free * ds.GB}) + '\n' for hours, free in samples))


def ticks():
    ds.STATE.mkdir(exist_ok=True)
    rows = [{'host': host, 'ts': ds.M4_DUE.isoformat()} for host in ds.M4_HOSTS]
    rows += [{'host': 'mac', 'ts': (ds.M4_DUE + timedelta(seconds=1)).isoformat()},
             {'host': 'mac', 'ts': (ds.M4_DUE - timedelta(days=8)).isoformat()},
             {'name': 'letter'}]
    (ds.STATE / 'steward.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))


def test_before_due(setup):
    assert ds.m4_report(ds.M4_DUE - timedelta(seconds=1)) == 0
    setup.assert_not_called()
    assert not (ds.STATE / 'm4-report.sent').exists()


def test_due_send_stamp_and_second_tick(setup, monkeypatch):
    monkeypatch.setattr(ds, 'plan', lambda _: [])
    monkeypatch.setattr(ds, 'machine', lambda _: {'hq': str(ds.STATE)})
    monkeypatch.setattr(ds, 'push_tick', Mock())
    monkeypatch.setattr(ds, 'letters', Mock())
    original = ds.m4_report
    monkeypatch.setattr(ds, 'm4_report', lambda **kw: original(ds.M4_DUE, **kw))
    assert ds.tick('contabo') == 0
    assert ds.tick('contabo') == 0
    setup.assert_called_once()
    args, kwargs = setup.call_args
    assert args[:2] == ('cto', ds.M4_CTO_SID)
    assert args[3:] == ('system', 'disk-steward')
    assert kwargs['kind'] == 'report'
    assert len(kwargs['subject']) <= 80
    stamp = json.loads((ds.STATE / 'm4-report.sent').read_text())
    assert stamp == {'subject': kwargs['subject'], 'time': ds.M4_DUE.isoformat()}
    rows = [json.loads(line) for line in (ds.STATE / 'steward.jsonl').read_text().splitlines()]
    assert [r['status'] for r in rows if r['name'] == 'm4-report'] == ['run', 'skipped']


def test_failed_send_retries(setup):
    setup.side_effect = RuntimeError('offline')
    assert ds.m4_report(ds.M4_DUE) == 1
    assert not (ds.STATE / 'm4-report.sent').exists()
    assert json.loads((ds.STATE / 'steward.jsonl').read_text())['status'] == 'failed'
    setup.side_effect = None
    assert ds.m4_report(ds.M4_DUE + timedelta(hours=1)) == 0
    assert setup.call_count == 2


def test_min_time_window_and_no_data(setup):
    history('contabo', [(1, 1), (-168, 20), (-4, 9.8), (-169, 2), (0, 18)])
    ticks()
    assert ds.m4_report(ds.M4_DUE + timedelta(days=1)) == 0
    body = setup.call_args.args[2]
    assert 'contabo | 9.8 | 2026-11-02T19:00:00+07:00 | 3 | 2026-11-02T23:00:00+07:00 | 1' in body
    assert 'mac | no data | no data | 0 | no data | 1' in body
    assert 'ผล M4: ไม่ผ่าน' in body
    assert 'P5' in body and 'CTO Main' in body
    assert '(<15)' in setup.call_args.kwargs['subject']


@pytest.mark.parametrize('samples,hours,passed', [
    ([(-100, 15), (-28, 16), (-27, 14), (0, 20)], 72, True),
    ([(-100, 15), (-40, 16), (-39, 14), (0, 20)], 60, False),
    ([(0, 15)], 0, False),
])
def test_longest_run(setup, samples, hours, passed):
    history('contabo', samples)
    ticks()
    ds.m4_report(ds.M4_DUE)
    body = setup.call_args.args[2]
    assert f'ยาวที่สุด {hours:.1f} ชั่วโมง' in body
    assert ('ผล M4: ผ่าน' in body) == passed


def test_missing_ticks_fails(setup):
    history('contabo', [(-72, 15), (0, 15)])
    ds.m4_report(ds.M4_DUE)
    assert 'ผล M4: ไม่ผ่าน' in setup.call_args.args[2]


def test_cli_dry_run(setup, capsys):
    assert ds.main(['m4-report', '--now', ds.M4_DUE.isoformat(), '--dry-run']) == 0
    setup.assert_not_called()
    assert not ds.STATE.exists()
    output = json.loads(capsys.readouterr().out)
    assert output['status'] == 'planned'
    assert 'no data' in output['body'] and 'DiskSteward M4' in output['subject']


@pytest.mark.parametrize('host', ['mac', 'winbox'])
def test_other_hosts_skip(setup, host):
    assert ds.m4_report(ds.M4_DUE, host=host) == 0
    setup.assert_not_called()


def test_cli_rejects_naive_time(setup):
    with pytest.raises(SystemExit):
        ds.main(['m4-report', '--now', '2026-11-03T00:00'])
    setup.assert_not_called()

from types import SimpleNamespace

import pytest

from tools import send_to_cto as sender


def test_live_recorded_owner_is_preserved(monkeypatch):
    monkeypatch.setattr(sender.agent_transport.tmux_session, 'has_session', lambda name: True)
    assert sender.resolve_owner('cmo', '12345678') == '12345678'


@pytest.mark.parametrize('recorded', ['fresh', 'deadbeef'])
@pytest.mark.parametrize('pointer', [True, False])
def test_owner_falls_back_to_live_role(monkeypatch, tmp_path, recorded, pointer):
    monkeypatch.setattr(sender, 'STATE_DIR', tmp_path)
    locks = tmp_path / 'locks'
    locks.mkdir()
    if pointer:
        (locks / 'cmo-active').write_text('e785343f')
    monkeypatch.setattr(sender.agent_transport.tmux_session, 'has_session',
                        lambda name: name == 'cmo-e785343f')
    monkeypatch.setattr(sender.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=0, stdout='cto-12345678\ncmo-e785343f\n'))
    letters = []
    monkeypatch.setattr(sender.mailbox, 'send', lambda *a, **kw: letters.append(a))
    assert sender.send('ph', 'blocker', cto_id=recorded, owner_role='cmo', wake=False)
    assert letters[0][:2] == ('cmo', 'e785343f')


def test_no_live_owner_reports_queued_destination(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sender, 'STATE_DIR', tmp_path)
    monkeypatch.setattr(sender.agent_transport.tmux_session, 'has_session', lambda name: False)
    monkeypatch.setattr(sender.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(returncode=1, stdout=''))
    letters = []
    monkeypatch.setattr(sender.mailbox, 'send', lambda *a, **kw: letters.append(a))
    assert sender.send('ph', 'blocker', cto_id='fresh', owner_role='cmo', wake=False)
    assert letters[0][:2] == ('cmo', 'fresh')
    assert 'no live session' in capsys.readouterr().err

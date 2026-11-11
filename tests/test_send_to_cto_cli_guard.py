"""The CLI refuses a swapped address and says when no live session will read the letter (11 Nov)."""
import sys

from tools import send_to_cto


def _run(monkeypatch, argv, live=True):
    sent = []
    monkeypatch.setattr(sys, "argv", ["send_to_cto", *argv])
    monkeypatch.setattr(send_to_cto, "send", lambda *a, **k: sent.append((a, k)) or True)
    monkeypatch.setattr(send_to_cto, "resolve_owner", lambda role, sid: sid)
    monkeypatch.setattr(send_to_cto.agent_transport.tmux_session, "has_session", lambda name: live)
    return send_to_cto.main(), sent


def test_swapped_id_and_role_is_refused_before_sending(monkeypatch, capsys):
    code, sent = _run(monkeypatch, ["fresh", "hi", "cto", "fresh", "project_head-8dbe4ccc"])
    assert code == 2 and sent == []
    assert "not a role name" in capsys.readouterr().err


def test_dead_mailbox_exits_3_and_names_it(monkeypatch, capsys):
    code, sent = _run(monkeypatch, ["fresh", "hi", "cto", "8dbe4ccc", "project_head"], live=False)
    assert code == 3 and len(sent) == 1
    assert "project_head-8dbe4ccc" in capsys.readouterr().out


def test_live_mailbox_exits_0(monkeypatch, capsys):
    code, _ = _run(monkeypatch, ["fresh", "hi", "cto", "8dbe4ccc", "project_head"])
    assert code == 0
    assert "queued to project_head-8dbe4ccc (live)" in capsys.readouterr().out

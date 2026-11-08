"""Captured-screen regression tests; no real tmux keys or mail."""
import json

import pytest

from tools import rc_reconnect as rc


DISCONNECTED = "● Remote Control disconnected — OAuth token unavailable — run /login to restore Remote Control\n"
PROMPT = "────────────────\n❯ \n────────────────\n/rc to reconnect\n"
IDLE = DISCONNECTED + PROMPT


@pytest.fixture
def host(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    monkeypatch.setattr(rc, "panes", lambda: [("cto-fresh", "%1")])
    monkeypatch.setattr(rc, "capture", lambda pane: IDLE)
    monkeypatch.setattr(rc, "auth_status", lambda: True)
    sent, letters = [], []
    monkeypatch.setattr(rc, "send", lambda *args: sent.append(args))
    monkeypatch.setattr(rc, "letter", lambda *args: letters.append(args) or True)
    return sent, letters


def test_disconnected_idle_types_footer_command(host):
    rc.tick(now=100)
    assert host[0] == [("%1", "/rc")]


@pytest.mark.parametrize("screen", [DISCONNECTED + "esc to interrupt\n" + PROMPT,
                                   IDLE + "Remote Control connected\n",
                                   IDLE + "Remote Control active\n",
                                   IDLE.replace("❯ ", "❯ draft")])
def test_busy_reconnected_or_draft_skips(host, monkeypatch, screen):
    monkeypatch.setattr(rc, "capture", lambda pane: screen)
    rc.tick(now=100)
    assert host[0] == []


@pytest.mark.parametrize("name", ["mooniex-task-123", "wd-task-123", "wd-123"])
def test_worker_skips(host, monkeypatch, name):
    monkeypatch.setattr(rc, "panes", lambda: [(name, "%1")])
    rc.tick(now=100)
    assert host[0] == []


def test_rate_limit_and_three_failures(host):
    for now in [100, 101, 1899, 1900, 3700, 5500, 7300]:
        rc.tick(now=now)
    assert len(host[0]) == 3
    assert host[1] == [("cto-fresh", "fyi")]


def test_kill_switch(host):
    (rc.ROOT / "state").mkdir()
    (rc.ROOT / "state/rc_reconnect.off").touch()
    assert rc.tick() == ["rc reconnect disabled"]
    assert host == ([], [])


def test_logged_out_letter_once_no_typing(host, monkeypatch):
    monkeypatch.setattr(rc, "auth_status", lambda: False)
    rc.tick(now=100)
    rc.tick(now=2000)
    assert host == ([], [("cto-fresh", "blocker")])


def test_unknown_auth_no_typing(host, monkeypatch):
    monkeypatch.setattr(rc, "auth_status", lambda: None)
    rc.tick()
    assert host == ([], [])


def test_dry_run_changes_nothing(host):
    assert "would send /rc" in rc.tick(dry_run=True)[0]
    assert not (rc.ROOT / "state").exists()
    assert host == ([], [])


def test_reconnected_resets_failures(host, monkeypatch):
    rc.tick(now=100)
    monkeypatch.setattr(rc, "capture", lambda pane: IDLE + "Remote Control connected\n")
    rc.tick(now=101)
    state = json.loads((rc.ROOT / "state/rc_reconnect.json").read_text())
    assert state["cto-fresh:%1"] == {"last": 100}


def test_send_checks_enter_landed(monkeypatch):
    screens = iter([IDLE, IDLE.replace("❯ ", "❯ /rc")])
    monkeypatch.setattr(rc, "capture", lambda pane: next(screens))
    calls = []
    monkeypatch.setattr(rc.agent_transport, "_wake_tmux_send", lambda *a: calls.append(a))
    with pytest.raises(RuntimeError, match="Enter did not submit"):
        rc.send("%1", "/rc")
    assert calls == [("%1", "/rc")]


def test_send_rechecks_idle(monkeypatch):
    monkeypatch.setattr(rc, "capture", lambda pane: IDLE + "esc to interrupt")
    with pytest.raises(RuntimeError, match="no longer idle"):
        rc.send("%1", "/rc")


def test_letter_never_wakes_login_pane(monkeypatch):
    from tools import send_to_cto
    calls = []
    monkeypatch.setattr(send_to_cto, "send", lambda *a, **kw: calls.append(kw) or True)
    rc.letter("project_head-12345678", "blocker")
    assert calls[0]["cto_id"] == "fresh"
    assert calls[0]["kind"] == "blocker"
    assert calls[0]["wake"] is False

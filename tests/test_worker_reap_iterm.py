"""close_dev's iTerm step is macOS-only and never stops the rest of the close.

On Contabo the close_dev MCP tool returned "[Errno 2] No such file or
directory: 'osascript'": tools/itermtab.close_tab ran osascript with nothing
to catch the error, so close_dev stopped before its tmux, ttyd and Chrome
steps (task-fabda3b9, 2026-10-14). No real iTerm, tmux or process is touched
here: every step close_dev takes is stubbed.
"""
from __future__ import annotations

import sys

import pytest

import tools.worker_reap as worker_reap

TID = "task-0a1b2c3d"


@pytest.fixture
def reap(monkeypatch):
    """A review task with a tmux session and a dead pid; records each step."""
    steps: list[str] = []
    monkeypatch.setattr(worker_reap.db, "get_task", lambda tid: {
        "id": tid, "status": "review", "pid": 999999, "tmux_session": "wd-0a1b2c3d",
        "ttyd_pid": None})
    monkeypatch.setattr(worker_reap, "_pid_matches_task", lambda pid, tid: False)
    monkeypatch.setattr(worker_reap, "_cleanup_tmux_ttyd",
                        lambda task: steps.append("tmux") or {"tmux_killed": True})
    monkeypatch.setattr(worker_reap, "_close_claimed_chrome_tabs",
                        lambda tid: steps.append("chrome") or [])
    monkeypatch.setattr(worker_reap, "warn", lambda *a, **kw: None)
    monkeypatch.setattr(worker_reap, "info", lambda *a, **kw: None)
    return steps


def _no_osascript(*a, **kw):
    raise FileNotFoundError(2, "No such file or directory", "osascript")


def test_off_a_mac_the_tab_step_is_skipped_and_the_rest_runs(reap, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    tab = []
    monkeypatch.setattr(worker_reap, "close_tab", lambda *a, **kw: tab.append(a) or _no_osascript())
    r = worker_reap.close_dev(TID, reason="test")
    assert tab == [], "no iTerm off a Mac: close_tab is never called"
    assert r["closed_tab"] is False and r["tmux_killed"] is True and r["refused"] is None
    assert reap == ["tmux", "chrome"]


def test_on_a_mac_a_failing_tab_step_never_stops_the_close(reap, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(worker_reap, "close_tab", _no_osascript)
    r = worker_reap.close_dev(TID, reason="test")
    assert r["closed_tab"] is False and r["tmux_killed"] is True
    assert reap == ["tmux", "chrome"]


def test_on_a_mac_the_tab_is_closed_by_title_for_an_unverified_pid(reap, monkeypatch):
    """Regression guard: the Mac path is unchanged, still title-only here."""
    monkeypatch.setattr(sys, "platform", "darwin")
    calls = []
    monkeypatch.setattr(worker_reap, "close_tab",
                        lambda tid, *, allow_pid: calls.append((tid, allow_pid)) or True)
    r = worker_reap.close_dev(TID, reason="test")
    assert r["closed_tab"] is True and calls == [(TID, False)]
    assert reap == ["tmux", "chrome"]

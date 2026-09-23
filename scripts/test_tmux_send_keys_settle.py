from unittest.mock import patch
import pytest

from tools import tmux_session


def test_send_keys_with_enter(monkeypatch):
    """Test send_keys with press_enter=True simulates typing, settle delay, and rescue enter."""
    calls = []

    def mock_run(cmd, check=True):
        calls.append(f"run: {' '.join(cmd[1:])}")  # cmd[0] is tmux bin

    def mock_sleep(seconds):
        calls.append(f"sleep: {seconds}")

    monkeypatch.setattr(tmux_session, "_run", mock_run)
    monkeypatch.setattr(tmux_session.time, "sleep", mock_sleep)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(tmux_session, "tmux_bin", lambda: "tmux")

    tmux_session.send_keys("mysess", "hello", press_enter=True)

    assert calls == [
        "run: send-keys -t mysess -l hello",
        "sleep: 0.4",
        "run: send-keys -t mysess Enter",
        "sleep: 0.3",
        "run: send-keys -t mysess Enter",
    ]


def test_send_keys_without_enter(monkeypatch):
    """Test send_keys with press_enter=False only types text and has no delay."""
    calls = []

    def mock_run(cmd, check=True):
        calls.append(f"run: {' '.join(cmd[1:])}")

    def mock_sleep(seconds):
        calls.append(f"sleep: {seconds}")

    monkeypatch.setattr(tmux_session, "_run", mock_run)
    monkeypatch.setattr(tmux_session.time, "sleep", mock_sleep)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(tmux_session, "tmux_bin", lambda: "tmux")

    tmux_session.send_keys("mysess", "hello", press_enter=False)

    assert calls == [
        "run: send-keys -t mysess -l hello",
    ]

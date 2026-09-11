"""Tests for scripts/session_list.py's tmux_lock_live() (task-bbdfa8d1).

Context: the CEO could not tell whether two Contabo CTO sessions were
actually running -- session_list.py's ONLY liveness signal was iTerm2
(osascript), which does not exist on Contabo at all, and even on the Mac it
misses the documented "closing the tab does NOT end the session" case
(scripts/session-kill.sh's own docstring). tmux_lock_live() adds a second,
cross-platform signal: the session's own tmux server session, or its
state/locks/<role>-<id>.lock pid.

Covers:
  1. tmux has-session alive -> True, regardless of the lock file.
  2. tmux not alive, lock pid alive -> True (tmux check failed/unavailable
     but the process itself is still running).
  3. tmux not alive, no lock file -> False.
  4. tmux not alive, lock file holds a dead pid -> False.
  5. tmux import/check raising an exception degrades to the lock-file check
     rather than raising (never let a listing tool crash on this).

tools.tmux_session.has_session is monkeypatched directly; the lock file is
a real file under tmp_path (REPO is monkeypatched to that tmp_path so the
function's own os.path.join(REPO, "state", "locks", ...) lands there, never
in the real repo's state/locks/).

Run via:   pytest scripts/test_session_list_liveness.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import session_list as sl  # noqa: E402
from tools import tmux_session  # noqa: E402


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(sl, "REPO", str(tmp_path))
    (tmp_path / "state" / "locks").mkdir(parents=True)
    return tmp_path


def _write_lock(fake_repo: Path, role: str, sid: str, pid: int) -> None:
    (fake_repo / "state" / "locks" / f"{role}-{sid}.lock").write_text(str(pid))


def test_tmux_alive_is_live_regardless_of_lock(fake_repo, monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: True)
    assert sl.tmux_lock_live("cto", "nolockatall") is True


def test_tmux_dead_lock_pid_alive_is_live(fake_repo, monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    _write_lock(fake_repo, "cto", "livepid01", os.getpid())  # this test process
    assert sl.tmux_lock_live("cto", "livepid01") is True


def test_tmux_dead_no_lock_is_not_live(fake_repo, monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    assert sl.tmux_lock_live("cto", "nolock02") is False


def test_tmux_dead_lock_pid_dead_is_not_live(fake_repo, monkeypatch):
    monkeypatch.setattr(tmux_session, "has_session", lambda name: False)
    # a pid essentially guaranteed not to exist
    _write_lock(fake_repo, "cto", "deadpid03", 999999)
    assert sl.tmux_lock_live("cto", "deadpid03") is False


def test_tmux_check_raising_falls_back_to_lock_file(fake_repo, monkeypatch):
    def _boom(name):
        raise RuntimeError("tmux binary missing")
    monkeypatch.setattr(tmux_session, "has_session", _boom)
    _write_lock(fake_repo, "cto", "fallback04", os.getpid())
    assert sl.tmux_lock_live("cto", "fallback04") is True


def test_name_is_case_insensitive_lowercased(fake_repo, monkeypatch):
    seen = []
    monkeypatch.setattr(tmux_session, "has_session",
                         lambda name: seen.append(name) or False)
    sl.tmux_lock_live("CTO", "AbCd1234")
    assert seen == ["cto-abcd1234"]

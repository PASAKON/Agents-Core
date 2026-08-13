"""Tests for tools/send_to_dev.py (GH #60).

`didSend` used to be computed by the AppleScript and then thrown away --
`osascript` exits 0 whether it matched an iTerm tab or looped over zero
windows, so `_send()` always "succeeded" and `send()` always returned a
"sent to tab matching ..." string, even when nothing received the message.

Testability: `_send()` takes AppleScript execution as an injectable
`runner` -- a callable that takes the assembled script string and returns
an object with `.returncode` / `.stdout` (matching `subprocess.CompletedProcess`).
Tests pass a fake runner directly to `_send()`, or monkeypatch the
module-level `_run_osascript` name (looked up dynamically inside `_send`,
not bound as a default-arg value) so callers like `send()` that don't pass
`runner` explicitly pick up the fake too. No real iTerm or `osascript`
process is ever invoked.

pytest style, tmp_path fixtures only (ADR 0021 §1). Points `lib.db.DB_PATH`
at a tmp_path sqlite file for every test that exercises `send()` -- never
touches the real state/tasks.db. No tmux session name is ever set on a
fixture task, so `tools.tmux_session.has_session()` (which shells out to
real `tmux`) is never reached.
"""
from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.send_to_dev as sd  # noqa: E402


def _fake_result(returncode: int, stdout: str) -> types.SimpleNamespace:
    return types.SimpleNamespace(returncode=returncode, stdout=stdout)


def _insert_task(conn, *, tmux_session: str | None = None) -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, tmux_session, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", "developer", "in_progress", "t", "d",
         "[]", "[]", tmux_session, ts, ts),
    )
    conn.commit()
    return tid


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point lib.db at a throwaway sqlite file for this test only."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


# --- _send() with an injected runner ----------------------------------------

def test_no_matching_tab_send_returns_false():
    """runner reports didSend=0 (osascript exit 0, zero iterations) ->
    _send() must return False, never True."""
    runner = lambda script: _fake_result(0, "0")  # noqa: E731
    assert sd._send("task-deadbeef", "hello", runner=runner) is False


def test_matching_tab_send_returns_true():
    runner = lambda script: _fake_result(0, "1")  # noqa: E731
    assert sd._send("task-deadbeef", "hello", runner=runner) is True


def test_osascript_nonzero_exit_returns_false():
    """A crashed osascript (non-zero exit) must fail, not silently succeed --
    even if stdout happens to contain "1" garbage."""
    runner = lambda script: _fake_result(1, "1")  # noqa: E731
    assert sd._send("task-deadbeef", "hello", runner=runner) is False


def test_fallback_branch_sets_didsend_on_match():
    """Structural check for the second half of GH #60: the 6-char fallback
    loop must flip didSend on a match, not just select the tab silently.
    Before the fix this branch had no success check at all."""
    captured: list[str] = []

    def runner(script: str):
        captured.append(script)
        return _fake_result(0, "1")

    ok = sd._send("task-deadbeef", "hello", runner=runner)
    assert ok is True
    script = captured[0]
    fallback = "task-deadbeef"[:6]
    fallback_idx = script.index(f'contains "{fallback}"')
    tail = script[fallback_idx:]
    assert "set didSend to true" in tail, (
        "fallback match branch must set didSend, or a fallback-only match "
        "silently no-ops exactly like the pre-fix primary branch did"
    )


def test_script_returns_didsend_to_caller():
    """The AppleScript `tell` block must return didSend so the Python side
    can parse it -- the whole point of GH #60's fix."""
    captured: list[str] = []

    def runner(script: str):
        captured.append(script)
        return _fake_result(0, "0")

    sd._send("task-deadbeef", "hello", runner=runner)
    script = captured[0]
    assert "if didSend then" in script
    assert 'return "1"' in script
    assert 'return "0"' in script


# --- send() end-to-end (db-backed) ------------------------------------------

def test_send_no_matching_tab_raises_and_never_returns_success_string(
    isolated_db, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn)

    monkeypatch.setattr(sd, "_run_osascript", lambda script: _fake_result(0, "0"))

    with pytest.raises(RuntimeError) as exc_info:
        result = sd.send(tid, "important instruction")
        # If no exception were raised, fail loudly here instead of letting
        # a "sent ..." string silently pass the test.
        assert "sent" not in result
    assert tid in str(exc_info.value)
    assert "not" in str(exc_info.value).lower()


def test_send_matching_tab_returns_success_string(isolated_db, monkeypatch):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn)

    monkeypatch.setattr(sd, "_run_osascript", lambda script: _fake_result(0, "1"))

    result = sd.send(tid, "status check")
    assert "sent to tab matching" in result
    assert tid in result


def test_send_osascript_crash_raises(isolated_db, monkeypatch):
    """osascript itself failing (non-zero exit) must not be swallowed into
    a success string either."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn)

    monkeypatch.setattr(sd, "_run_osascript", lambda script: _fake_result(1, ""))

    with pytest.raises(RuntimeError):
        sd.send(tid, "hello")


def test_send_prefers_tmux_when_session_alive(isolated_db, monkeypatch):
    """tmux branch is untouched by the GH #60 fix -- still returns a
    success string when tmux.has_session() is True, without touching
    osascript at all."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, tmux_session="dev-deadbeef")

    monkeypatch.setattr(sd.tmux, "has_session", lambda s: True)
    sent = []
    monkeypatch.setattr(sd.tmux, "send_keys",
                        lambda s, t, **kw: sent.append((s, t)))

    result = sd.send(tid, "hi via tmux")
    assert "sent via tmux dev-deadbeef" in result
    assert sent == [("dev-deadbeef", f"{sd.PREFIX} hi via tmux")]

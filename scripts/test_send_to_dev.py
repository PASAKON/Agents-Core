"""Tests for tools/send_to_dev.py's mailbox+wake delivery contract.

Task task-2f04a8ca (CEO directive 2026-08-14): mirrors the fixture/
injection style `scripts/test_cxo_crosstalk.py` established for
`tools/send_to_cxo.py`'s own mailbox+wake migration (task-de2cdc15,
task-cf325742) -- pytest, `tmp_path` fixtures only (ADR 0021 §1), never the
real `state/tasks.db` or `state/inbox/`. `tmux_session.has_session` is
monkeypatched on `tools.agent_transport` (task task-eb0d9863 moved the
shared wake implementation there -- `_attempt_wake()` in this file's
module now delegates to `agent_transport.attempt_wake()`). `_wake_tmux_send`
is still monkeypatched on `sd` (this file's `tools.send_to_dev` alias) --
`sd._attempt_wake()` passes its OWN imported `_wake_tmux_send` reference
as `send_fn=`, resolved fresh from `sd`'s globals on every call, so a
patch on `sd`'s copy (not agent_transport's) is what actually takes
effect. No real tmux binary anywhere.

Covers (task's required list, mapped to this file):
  * delivery succeeds via the mailbox write alone
  * wake attempted when a live tmux session exists on the task row
  * wake skipped (no session) / failed (raises) does not change delivery's
    success or the returned string
  * the wake nudge never contains the message body
  * the old `full_id[:6]` iTerm tab-title collision class is structurally
    impossible now: no substring/tab-matching code path is left in the
    module at all, and two task ids sharing the same 6-char prefix
    (GH #65's exact shape) resolve to two distinct, correct mailboxes
  * task-not-found still raises ValueError, no success string
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import lib.mailbox as mailbox  # noqa: E402
import tools.agent_transport as agent_transport  # noqa: E402
import tools.send_to_dev as sd  # noqa: E402


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point lib.db at a throwaway sqlite file for this test only.
    sd.db is the same module object (`from lib import db`), so this
    redirects sd.send()'s db.init()/db.get_task() calls too."""
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    return db_mod


@pytest.fixture()
def isolated_mailbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point lib.mailbox's default inbox root at a throwaway dir -- never
    the real state/inbox/. sd.send() calls mailbox.send() with no explicit
    root=, so it picks up whatever mailbox.INBOX_ROOT is at call time."""
    root = tmp_path / "inbox"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", root)
    return root


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch: pytest.MonkeyPatch):
    """current_identity()/_resolve_sender_role() read process env -- start
    every test from a blank slate so a stray CXO_ROLE/DEV_TASK_ID left over
    from this DEV's own harness process can never leak into a test."""
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "DEV_TASK_ID", "DEV_ROLE"):
        monkeypatch.delenv(var, raising=False)


def _insert_task(conn, *, task_id: str | None = None, role: str = "developer",
                 tmux_session: str | None = None,
                 owner_role: str | None = None, owner_cto: str | None = None) -> str:
    tid = task_id or ("task-" + uuid.uuid4().hex[:8])
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            depends_on, touches, tmux_session, owner_role, owner_cto,
            created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", role, "in_progress", "t", "d",
         "[]", "[]", tmux_session, owner_role, owner_cto, ts, ts),
    )
    conn.commit()
    return tid


# --- delivery succeeds via mailbox write alone ------------------------------

def test_send_delivers_via_mailbox_no_live_session(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    """No tmux session on the task row (the org's current reality for every
    project, per config/projects.yaml) -- delivery still succeeds; wake is
    silently skipped."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, role="developer")

    calls = []
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda s, t: calls.append((s, t)))

    result = sd.send(tid, "kickoff please")
    assert f"({tid})" in result
    assert "kickoff please" in result
    assert calls == []  # never even attempted -- no session to nudge

    letters = mailbox.peek("developer", tid, root=isolated_mailbox_root)
    assert len(letters) == 1
    assert letters[0]["body"] == "kickoff please"
    assert letters[0]["to"] == {"role": "developer", "session_id": tid}


def test_send_no_task_raises_no_success_string(isolated_db, isolated_mailbox_root):
    with pytest.raises(ValueError) as exc_info:
        result = sd.send("task-doesnotexist", "hello")
        assert "sent" not in result
        assert "queued" not in result
    assert "no task matching" in str(exc_info.value)


# --- wake attempt / skip / failure isolation --------------------------------

def test_wake_attempted_when_live_tmux_session_on_task_row(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, role="web_designer", tmux_session="wd-abc12345")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: s == "wd-abc12345")
    calls = []
    monkeypatch.setattr(sd, "_wake_tmux_send",
                        lambda session, text: calls.append((session, text)))
    monkeypatch.setenv("CXO_ROLE", "cto")
    monkeypatch.setenv("CTO_SESSION_ID", "ctosess01")

    sd.send(tid, "status check please")

    assert calls == [("wd-abc12345", "[New message from CTO]")]


def test_wake_skipped_silently_when_no_live_session(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, tmux_session="wd-deadsession")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: False)

    def _should_not_run(*a, **kw):
        raise AssertionError("must not attempt a tmux send when no session is live")

    monkeypatch.setattr(sd, "_wake_tmux_send", _should_not_run)

    result = sd.send(tid, "hello")
    assert f"({tid})" in result


def test_wake_failure_does_not_propagate_or_change_return(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, tmux_session="wd-livesession")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)

    def boom(*a, **kw):
        raise RuntimeError("tmux send-keys exploded")

    monkeypatch.setattr(sd, "_wake_tmux_send", boom)

    result = sd.send(tid, "hello")  # must not raise
    assert f"({tid})" in result

    letters = mailbox.peek("developer", tid, root=isolated_mailbox_root)
    assert len(letters) == 1  # delivery unaffected by the wake blowing up


def test_send_return_string_identical_wake_success_fail_skip(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid1 = _insert_task(conn, tmux_session="wd-a")
        tid2 = _insert_task(conn, tmux_session="wd-b")
        tid3 = _insert_task(conn, tmux_session="wd-c")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda session, text: None)
    ok_result = sd.send(tid1, "hi").replace(tid1, "TID")

    def boom(*a, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(sd, "_wake_tmux_send", boom)
    fail_result = sd.send(tid2, "hi").replace(tid2, "TID")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: False)
    skip_result = sd.send(tid3, "hi").replace(tid3, "TID")

    assert ok_result == fail_result == skip_result


def test_wake_nudge_never_contains_message_body(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, tmux_session="wd-livesession")

    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)
    calls = []
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda session, text: calls.append(text))

    secret_body = "the actual message body must never be retyped into any composer"
    sd.send(tid, secret_body)

    assert len(calls) == 1
    assert secret_body not in calls[0]


# --- GH #65: no substring tab-matching left; sharing a 6-char prefix -------
# is no longer a collision surface -------------------------------------------

def test_send_to_dev_has_no_tab_matching_helpers():
    """The whole `full_id[:6]` iTerm AppleScript fallback -- `_send`,
    `_run_osascript`, `PREFIX`, the tmux-typing helper -- is deleted, not
    kept dead or as a fallback."""
    assert not hasattr(sd, "_send")
    assert not hasattr(sd, "_run_osascript")
    assert not hasattr(sd, "_send_tmux")
    assert not hasattr(sd, "PREFIX")
    assert not hasattr(sd, "subprocess")


def test_gh65_shared_six_char_prefix_resolves_to_distinct_mailboxes(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    """The exact GH #65 shape: two real tasks whose ids share
    `full_id[:6]` ("task-a"...). Delivery is keyed by the DB's own unique
    row id (task["role"], task["id"]), never by any tab-name substring
    match, so each message lands in its own box -- never the other's."""
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda s, t: None)
    with isolated_db.get_conn() as conn:
        tid_a = _insert_task(conn, task_id="task-a1111111", role="developer")
        tid_b = _insert_task(conn, task_id="task-a2222222", role="tester")
    assert tid_a[:6] == tid_b[:6] == "task-a"

    sd.send(tid_a, "message meant for A only")
    sd.send(tid_b, "message meant for B only")

    letters_a = mailbox.peek("developer", tid_a, root=isolated_mailbox_root)
    letters_b = mailbox.peek("tester", tid_b, root=isolated_mailbox_root)
    assert [l["body"] for l in letters_a] == ["message meant for A only"]
    assert [l["body"] for l in letters_b] == ["message meant for B only"]


# --- sender label ------------------------------------------------------------

def test_sender_label_reflects_owning_c_level_not_hardcoded_cto(
    isolated_db, isolated_mailbox_root, monkeypatch,
):
    """A CFO-owned DEV task must show "[CFO]:", not the old hardcoded
    "[CTO]:" -- tasks.owner_role already lets any C-level own a DEV task."""
    with isolated_db.get_conn() as conn:
        tid = _insert_task(conn, owner_role="cfo", owner_cto="cfosess01")
    monkeypatch.setenv("CXO_ROLE", "cfo")
    monkeypatch.setenv("CXO_SESSION_ID", "cfosess01")
    monkeypatch.setattr(sd, "_wake_tmux_send", lambda s, t: None)

    result = sd.send(tid, "budget approved, proceed")
    assert "[CFO]" in result

    letters = mailbox.peek("developer", tid, root=isolated_mailbox_root)
    assert letters[0]["from"]["role"] == "cfo"

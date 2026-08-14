"""Tests for tools/send_to_cto.py's mailbox+wake delivery contract.

Task task-2f04a8ca (CEO directive 2026-08-14): same fixture/injection
style as scripts/test_send_to_worker.py and scripts/test_cxo_crosstalk.py --
pytest, tmp_path only (ADR 0021 §1), never the real state/tasks.db,
state/locks/, or state/inbox/. `_active_session_id` and
`tmux_session.has_session` live in `tools.agent_transport` (task
task-eb0d9863 moved the shared implementation there), so tests patch
`agent_transport` directly for those. `_wake_tmux_send` is still patched
on `sc` (this file's `tools.send_to_cto` alias) -- `sc._attempt_wake()`
passes its OWN imported `_wake_tmux_send` reference to
`agent_transport.attempt_wake(..., send_fn=_wake_tmux_send)`, resolved
fresh from `sc`'s globals on every call, so a monkeypatch on `sc`'s copy
(not agent_transport's) is what actually takes effect.

Covers (task's required list, mapped to this file):
  * delivery succeeds via the mailbox write alone (owned task, cto_id given)
  * wake attempted when a live tmux session exists for the owner
  * wake skipped (no session) / failed (raises) does not change delivery's
    success
  * the wake nudge never contains the message body
  * no substring/window-matching code path is left (`_read_winid`,
    osascript, `subprocess`) -- the old winid-lookup reachability check
    that could return False for a known owner is gone; a known owner now
    always succeeds
  * the ownerless-task fallback still logs to the same file and still
    respects SEND_TO_CTO_BROADCAST, transport swapped underneath
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.mailbox as mailbox  # noqa: E402
import tools.agent_transport as agent_transport  # noqa: E402
import tools.send_to_cto as sc  # noqa: E402


@pytest.fixture()
def isolated_mailbox_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "inbox"
    monkeypatch.setattr(mailbox, "INBOX_ROOT", root)
    return root


@pytest.fixture()
def isolated_locks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`_active_session_id()` (used by the broadcast path) is defined in
    `tools.agent_transport` and reads that module's own `LOCKS_DIR` global
    -- patch it there, not on `sc` (this file's `tools.send_to_cto`
    alias)."""
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(agent_transport, "LOCKS_DIR", locks)
    return locks


@pytest.fixture(autouse=True)
def isolated_state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Orphan-log writes go to sc.STATE_DIR -- never the real state/."""
    state = tmp_path / "state"
    monkeypatch.setattr(sc, "STATE_DIR", state)
    return state


@pytest.fixture(autouse=True)
def clean_broadcast_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SEND_TO_CTO_BROADCAST", raising=False)


@pytest.fixture(autouse=True)
def clean_identity_env(monkeypatch: pytest.MonkeyPatch):
    """`_attempt_wake()` calls `lib.notify.info()`, which reads `WORKER_TASK_ID`
    straight off the real process env (`lib.notify._detect_source()`) to
    label `state/logs/cto.log` lines -- independent of anything this file's
    own send() calls pass in. Without this, this DEV harness's own ambient
    `WORKER_TASK_ID`/`WORKER_ROLE` leaked real log lines into the real
    `state/logs/cto.log` during test runs (found via a state/ byte-identical
    check -- `lib.notify._under_test()`'s `sys.argv[0] == "pytest"` guard
    does not match a `python -m pytest` invocation, whose `sys.argv[0]`
    basename is `__main__.py`; every sibling test file masks this by
    clearing `WORKER_TASK_ID` for its own identity-isolation reasons, which
    this file didn't otherwise need). Same var list as
    `scripts/test_cxo_crosstalk.py` / `scripts/test_send_to_worker.py`."""
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID",
                "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)


# --- delivery succeeds via mailbox write alone (owned task) -----------------

def test_send_owned_task_delivers_via_mailbox(
    isolated_mailbox_root, monkeypatch,
):
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda s, t: None)

    ok = sc.send("task-abc12345", "patch ready, please review",
                 role="web_designer", cto_id="ctosess01", owner_role="cto")

    assert ok is True
    letters = mailbox.peek("cto", "ctosess01", root=isolated_mailbox_root)
    assert len(letters) == 1
    assert letters[0]["body"] == "patch ready, please review"
    assert letters[0]["from"] == {"role": "web_designer", "session_id": "task-abc12345"}
    assert letters[0]["to"] == {"role": "cto", "session_id": "ctosess01"}


def test_send_owned_task_routes_by_owner_role_not_always_cto(
    isolated_mailbox_root, monkeypatch,
):
    """CFO-owned DEV task -> lands in the CFO's box, not a CTO box."""
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda s, t: None)

    sc.send("task-abc12345", "budget question", role="developer",
            cto_id="cfosess01", owner_role="cfo")

    assert mailbox.peek("cfo", "cfosess01", root=isolated_mailbox_root)
    assert mailbox.peek("cto", "cfosess01", root=isolated_mailbox_root) == []


# --- wake attempt / skip / failure isolation --------------------------------

def test_wake_attempted_when_live_tmux_session_exists(
    isolated_mailbox_root, monkeypatch,
):
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: s == "cto-ctosess01")
    calls = []
    monkeypatch.setattr(sc, "_wake_tmux_send",
                        lambda session, text: calls.append((session, text)))

    sc.send("task-abc12345", "hello", role="developer",
            cto_id="ctosess01", owner_role="cto")

    assert calls == [("cto-ctosess01", "[New message from Developer task-abc12345]")]


def test_wake_skipped_silently_when_no_live_session(
    isolated_mailbox_root, monkeypatch,
):
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: False)

    def _should_not_run(*a, **kw):
        raise AssertionError("must not attempt a tmux send when no session is live")

    monkeypatch.setattr(sc, "_wake_tmux_send", _should_not_run)

    ok = sc.send("task-abc12345", "hello", role="developer",
                 cto_id="ctosess01", owner_role="cto")
    assert ok is True  # delivery is unaffected


def test_wake_failure_does_not_propagate_or_change_return(
    isolated_mailbox_root, monkeypatch,
):
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)

    def boom(*a, **kw):
        raise RuntimeError("tmux send-keys exploded")

    monkeypatch.setattr(sc, "_wake_tmux_send", boom)

    ok = sc.send("task-abc12345", "hello", role="developer",
                 cto_id="ctosess01", owner_role="cto")  # must not raise
    assert ok is True
    assert len(mailbox.peek("cto", "ctosess01", root=isolated_mailbox_root)) == 1


def test_wake_nudge_never_contains_message_body(
    isolated_mailbox_root, monkeypatch,
):
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: True)
    calls = []
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda session, text: calls.append(text))

    secret_body = "the actual reply body must never be retyped into any composer"
    sc.send("task-abc12345", secret_body, role="developer",
            cto_id="ctosess01", owner_role="cto")

    assert len(calls) == 1
    assert secret_body not in calls[0]


# --- old window/winid reachability check is gone ----------------------------

def test_send_to_cto_has_no_winid_or_typing_helpers():
    assert not hasattr(sc, "_read_winid")
    assert not hasattr(sc, "subprocess")


def test_known_owner_always_succeeds_even_if_no_window_ever_existed(
    isolated_mailbox_root, monkeypatch,
):
    """Old behaviour: a missing `<role>-<id>.winid` file (owner's window
    was never recorded, or closed) meant `_read_winid` returned None ->
    orphan-logged, return False. Mailbox delivery has no such dependency
    -- a known owner (cto_id given) always succeeds regardless of whether
    any window/lock file for it has ever existed."""
    monkeypatch.setattr(agent_transport.tmux_session, "has_session", lambda s: False)  # no live session at all

    ok = sc.send("task-abc12345", "hello", role="developer",
                 cto_id="neverspawnedsess", owner_role="cto")

    assert ok is True
    assert len(mailbox.peek("cto", "neverspawnedsess", root=isolated_mailbox_root)) == 1


# --- ownerless-task fallback preserved (log + opt-in broadcast) ------------

def test_log_orphan_writes_expected_fields(isolated_state_dir):
    """`_log_orphan` itself is untouched by this migration (still the same
    from=/role=/msg= line format) -- ported from the now-deleted
    scripts/test_send_to_cto_routing.py (task-2f04a8ca) rather than losing
    this format assertion when that file's winid/AppleScript-only tests
    were removed."""
    sc._log_orphan("cto1", "task-abc", "developer", "hello world")
    log = isolated_state_dir / "orphan-dev-replies-cto1.log"
    assert log.exists()
    content = log.read_text()
    assert "from=task-abc" in content
    assert "role=developer" in content
    assert "hello world" in content


def test_ownerless_task_logs_orphan_and_returns_false_by_default(
    isolated_mailbox_root, isolated_state_dir,
):
    ok = sc.send("task-abc12345", "orphaned reply", role="developer", cto_id=None)

    assert ok is False
    log = isolated_state_dir / "orphan-dev-replies-unowned.log"
    assert log.exists()
    content = log.read_text()
    assert "task-abc12345" in content
    assert "orphaned reply" in content
    # no mailbox write for any role when ownerless and not broadcasting
    for role in ("cto", "cmo", "cgo", "cfo"):
        assert mailbox.peek(role, "unowned", root=isolated_mailbox_root) == []


def test_ownerless_task_broadcast_opt_in_queues_every_live_c_level(
    isolated_mailbox_root, isolated_locks, monkeypatch,
):
    monkeypatch.setenv("SEND_TO_CTO_BROADCAST", "1")
    (isolated_locks / "cto-active").write_text("ctosess01")
    (isolated_locks / "cfo-active").write_text("cfosess01")
    # cmo, cgo have no active pointer -> not live, must be skipped
    monkeypatch.setattr(sc, "_wake_tmux_send", lambda s, t: None)

    ok = sc.send("task-abc12345", "broadcast reply", role="developer", cto_id=None)

    assert ok is True
    assert mailbox.peek("cto", "ctosess01", root=isolated_mailbox_root)[0]["body"] == "broadcast reply"
    assert mailbox.peek("cfo", "cfosess01", root=isolated_mailbox_root)[0]["body"] == "broadcast reply"
    assert mailbox.peek("cmo", "cmosess01", root=isolated_mailbox_root) == []


def test_ownerless_task_broadcast_off_by_default_env_gate(
    isolated_mailbox_root, isolated_locks, monkeypatch,
):
    """SEND_TO_CTO_BROADCAST unset (or not "1") -> no broadcast, orphan
    path taken, exactly as before this task."""
    (isolated_locks / "cto-active").write_text("ctosess01")
    monkeypatch.delenv("SEND_TO_CTO_BROADCAST", raising=False)

    ok = sc.send("task-abc12345", "should not broadcast", role="developer", cto_id=None)

    assert ok is False
    assert mailbox.peek("cto", "ctosess01", root=isolated_mailbox_root) == []

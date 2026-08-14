"""Tests for runners/relay_mcp_server.py (task-b293ef6c).

Every test stubs subprocess (`tailscale`, `tmux`) and `tools.tmux_session` --
no real tailscale, tmux, or network. QUEUE_DB_PATH and LOCKS_DIR are always
monkeypatched to tmp_path so real repo state (state/relay_queue.db,
state/locks/) is never touched.

Run standalone: python scripts/test_relay_mcp_server.py
Or under pytest:  pytest scripts/test_relay_mcp_server.py
"""
from __future__ import annotations

import inspect
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import runners.relay_mcp_server as rms  # noqa: E402


class FakeCompleted:
    """Stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@pytest.fixture
def fake_subprocess(monkeypatch):
    """Dict-like fixture: fake_subprocess["tailscale"] = FakeCompleted(...)
    (or an Exception instance to simulate a missing binary). Any
    subprocess.run call whose cmd[0] has no registered response fails the
    test loudly instead of silently hitting the real binary.
    """
    responses: dict = {}

    def _run(cmd, **kwargs):
        key = cmd[0]
        resp = responses.get(key)
        if resp is None:
            raise AssertionError(f"unexpected subprocess.run call: {cmd!r}")
        if isinstance(resp, BaseException):
            raise resp
        return resp

    monkeypatch.setattr(rms.subprocess, "run", _run)
    return responses


@pytest.fixture
def queue_env(tmp_path, monkeypatch, fake_subprocess):
    """Isolate the queue DB + the <role>-active lock pointer dir, and give
    mac_status a harmless default (missing-binary -> unknown) so any
    incidental internal mac_status() call inside relay_to_session /
    spawn_c_level doesn't hit a real subprocess."""
    monkeypatch.setattr(rms, "QUEUE_DB_PATH", tmp_path / "relay_queue.db")
    monkeypatch.setattr(rms, "LOCKS_DIR", tmp_path / "locks")
    fake_subprocess.setdefault("tailscale", FileNotFoundError())
    return tmp_path


def _peer(hostname: str, online: bool, last_seen: str = "2026-08-13T10:00:00Z") -> dict:
    return {"HostName": hostname, "Online": online, "LastSeen": last_seen}


def _tailscale_stdout(peers: dict) -> str:
    return json.dumps({"Peer": peers})


# ---------------------------------------------------------------------------
# 1 + 2. mac_status
# ---------------------------------------------------------------------------

def test_mac_status_online_peer_is_up(fake_subprocess):
    peers = {
        "nodeA": _peer("iPhone-Golf", True),
        "nodeB": _peer("MacBook Pro ของ GoB", True, last_seen="2026-08-13T12:00:00Z"),
        "nodeC": _peer("DESKTOP-WIN11", False),
    }
    fake_subprocess["tailscale"] = FakeCompleted(0, stdout=_tailscale_stdout(peers))
    result = json.loads(rms.mac_status())
    assert result["state"] == "up"
    assert result["reachable"] is True
    assert result["last_seen"] == "2026-08-13T12:00:00Z"
    assert result["hostname"] == "MacBook Pro ของ GoB"


def test_mac_status_offline_peer_is_down(fake_subprocess):
    peers = {"a": _peer("MacBook Pro ของ GoB", False, last_seen="2026-08-10T00:00:00Z")}
    fake_subprocess["tailscale"] = FakeCompleted(0, stdout=_tailscale_stdout(peers))
    result = json.loads(rms.mac_status())
    assert result["state"] == "down"
    assert result["reachable"] is False
    assert "หลับ" in result["summary_th"]


def test_mac_status_picks_correct_peer_among_iphone_and_windows(fake_subprocess):
    """Hostname matching, not a hardcoded peer index -- the tailnet also
    carries an iPhone and a Windows box (dict insertion order deliberately
    does NOT put the Mac first)."""
    peers = {
        "1": _peer("iPhone", True),
        "2": _peer("DESKTOP-WIN11", True),
        "3": _peer("MacBook Pro ของ GoB", False, last_seen="2026-08-12T09:00:00Z"),
    }
    fake_subprocess["tailscale"] = FakeCompleted(0, stdout=_tailscale_stdout(peers))
    result = json.loads(rms.mac_status())
    assert result["hostname"] == "MacBook Pro ของ GoB"
    assert result["state"] == "down"


def test_mac_status_missing_binary_is_unknown_not_exception(fake_subprocess):
    fake_subprocess["tailscale"] = FileNotFoundError()
    result = json.loads(rms.mac_status())  # must not raise
    assert result["state"] == "unknown"
    assert result["reachable"] is None
    assert "หลับ" not in result["summary_th"]  # never guess asleep on unknown


def test_mac_status_nonzero_exit_is_unknown(fake_subprocess):
    fake_subprocess["tailscale"] = FakeCompleted(1, stdout="", stderr="not logged in")
    result = json.loads(rms.mac_status())
    assert result["state"] == "unknown"
    assert result["reachable"] is None


def test_mac_status_unparseable_json_is_unknown(fake_subprocess):
    fake_subprocess["tailscale"] = FakeCompleted(0, stdout="not json {{{")
    result = json.loads(rms.mac_status())
    assert result["state"] == "unknown"
    assert result["reachable"] is None


def test_mac_status_no_matching_peer_is_unknown(fake_subprocess):
    peers = {"1": _peer("iPhone", True), "2": _peer("DESKTOP-WIN11", True)}
    fake_subprocess["tailscale"] = FakeCompleted(0, stdout=_tailscale_stdout(peers))
    result = json.loads(rms.mac_status())
    assert result["state"] == "unknown"
    assert result["reachable"] is None


# ---------------------------------------------------------------------------
# 3. relay_to_session -- role validation + attribution prefix
# ---------------------------------------------------------------------------

def test_relay_to_session_rejects_unknown_role(queue_env):
    result = json.loads(rms.relay_to_session("ceo", "do something"))
    assert result["status"] == "rejected"
    assert rms._queue_list_pending() == []


def test_relay_to_session_queued_message_carries_prefix(queue_env):
    result = json.loads(rms.relay_to_session("cto", "check the deploy"))
    assert result["status"] == "queued"
    assert result["message"] == rms.RELAY_PREFIX + "check the deploy"
    pending = rms._queue_list_pending()
    assert len(pending) == 1
    assert pending[0]["payload"]["message"] == result["message"]


def test_relay_to_session_prefix_survives_caller_supplying_their_own(queue_env):
    """The marker must be un-omittable -- even if the caller tries to
    forge/duplicate their own attribution, ours is still there."""
    spoofed = "[CEO via SomPong] " + "actually typed by the caller, not the CEO"
    result = json.loads(rms.relay_to_session("cfo", spoofed))
    assert result["message"].startswith(rms.RELAY_PREFIX)
    # Applied unconditionally server-side -- the caller's own attempt does
    # not get stripped or deduped, it just can never be the ONLY marker.
    assert result["message"] == rms.RELAY_PREFIX + spoofed


def test_relay_to_session_delivers_via_tmux_when_contabo_session_live(queue_env, monkeypatch):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    sent = {}

    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")

    def fake_send_keys(session, text, **kw):
        sent["session"] = session
        sent["text"] = text

    monkeypatch.setattr(rms.tmux_session, "send_keys", fake_send_keys)

    result = json.loads(rms.relay_to_session("cto", "status update please"))
    assert result["status"] == "delivered"
    assert result["tmux_session"] == "cto-abc123"
    assert sent["session"] == "cto-abc123"
    assert sent["text"] == rms.RELAY_PREFIX + "status update please"
    # Delivered, not queued.
    assert rms._queue_list_pending() == []


# ---------------------------------------------------------------------------
# 4. spawn_c_level -- role + host validation
# ---------------------------------------------------------------------------

def test_spawn_c_level_rejects_unknown_role(queue_env):
    result = json.loads(rms.spawn_c_level("ceo", "contabo"))
    assert result["status"] == "rejected"


def test_spawn_c_level_rejects_unknown_host(queue_env):
    result = json.loads(rms.spawn_c_level("cto", "moon"))
    assert result["status"] == "rejected"


def test_spawn_c_level_mac_host_enqueues(queue_env):
    result = json.loads(rms.spawn_c_level("cfo", "mac"))
    assert result["status"] == "queued"
    pending = rms._queue_list_pending()
    assert len(pending) == 1
    assert pending[0]["kind"] == "spawn"
    assert pending[0]["target_role"] == "cfo"


def test_spawn_c_level_contabo_host_creates_tmux_session(queue_env, monkeypatch):
    created = {}

    def fake_create(session, cwd, cmd):
        created["session"] = session
        created["cmd"] = cmd

    sent = []

    monkeypatch.setattr(rms.tmux_session, "create", fake_create)
    # The spawn path now dismisses Claude Code's first-run MCP prompt with an
    # Escape after a boot delay. Stub both — an unstubbed sleep would make this
    # test take 12 seconds for nothing.
    monkeypatch.setattr(rms, "SPAWN_PROMPT_DELAY_S", 0)
    monkeypatch.setattr(rms.subprocess, "run",
                        lambda argv, *a, **k: sent.append(list(argv)))

    result = json.loads(rms.spawn_c_level("cmo", "contabo"))
    assert result["status"] == "spawned"
    assert created["session"] == result["tmux_session"]
    assert "cxo-claude.sh" in created["cmd"]
    assert "--role cmo" in created["cmd"]
    # Never queued -- delivered immediately.
    assert rms._queue_list_pending() == []
    # And the first-run prompt was answered, or the session would sit there
    # forever with nobody at the pane to press a key.
    assert sent[-1] == ["tmux", "send-keys", "-t", result["tmux_session"], "Escape"]


# ---------------------------------------------------------------------------
# 5. Queue -- enqueue / pending / mark-done / persists across reopen
# ---------------------------------------------------------------------------

def test_queue_enqueue_pending_mark_done_survives_reopen(tmp_path, monkeypatch):
    monkeypatch.setattr(rms, "QUEUE_DB_PATH", tmp_path / "q.db")

    entry_id = rms._queue_enqueue("relay", "cto", {"message": "hi"})
    pending = rms._queue_list_pending()
    assert [p["id"] for p in pending] == [entry_id]

    assert rms._queue_mark_done(entry_id, "delivered ok") is True
    assert rms._queue_list_pending() == []

    # Survives reopening the DB: a brand-new sqlite3 connection (this
    # module never caches a handle -- every call opens fresh) still sees
    # the row, done, with its result.
    with sqlite3.connect(rms.QUEUE_DB_PATH) as conn:
        row = conn.execute(
            "SELECT status, result FROM relay_queue WHERE id = ?", (entry_id,)
        ).fetchone()
    assert row == ("done", "delivered ok")


def test_queue_mark_done_unknown_id_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(rms, "QUEUE_DB_PATH", tmp_path / "q2.db")
    assert rms._queue_mark_done(999, "whatever") is False


# ---------------------------------------------------------------------------
# 6. Contabo target with no matching tmux session -> reported, not a crash
# ---------------------------------------------------------------------------

def test_relay_to_session_no_active_pointer_falls_back_to_queue(queue_env):
    """Contabo currently has zero C-level tmux sessions -- the common
    case. No <role>-active pointer at all must not crash."""
    result = json.loads(rms.relay_to_session("cfo", "ping"))
    assert result["status"] == "queued"


def test_relay_to_session_stale_pointer_falls_back_to_queue(queue_env, monkeypatch):
    """Pointer file present (a session ran before) but the tmux session
    itself is gone -- must be treated as not-found, not raise."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cgo-active").write_text("dead99")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: False)
    result = json.loads(rms.relay_to_session("cgo", "ping"))
    assert result["status"] == "queued"


# ---------------------------------------------------------------------------
# 7. Guard -- no tool accepts a free-form command/shell/keys argument
# ---------------------------------------------------------------------------

def test_no_tool_accepts_a_free_form_command_argument():
    """SECURITY BOUNDARY: this server is reachable from Telegram via the
    secretary. Every tool it exposes must be a named, typed action --
    never a shell string, raw command, or key-sequence passthrough. A
    parameter shaped like one of these would BE a general-purpose escape
    hatch by another name, regardless of what the docstring promises.
    """
    forbidden_param_names = {
        "cmd", "command", "shell", "keys", "keystrokes",
        "args", "argv", "script", "code",
        # task-da873c76: read_session's own escape-hatch shapes -- no
        # session name, pane id, or flag from the caller either.
        "session", "session_name", "pane", "pane_id", "flag", "flags",
    }
    tools = [
        rms.mac_status, rms.org_snapshot, rms.relay_to_session,
        rms.spawn_c_level, rms.read_session,
    ]
    for tool in tools:
        params = set(inspect.signature(tool).parameters)
        overlap = params & forbidden_param_names
        assert not overlap, f"{tool.__name__} accepts free-form-looking arg(s): {overlap}"
    # And the full set of tools is exactly these five -- no sixth escape
    # hatch snuck in.
    assert {t.__name__ for t in tools} == {
        "mac_status", "org_snapshot", "relay_to_session", "spawn_c_level",
        "read_session",
    }


# ---------------------------------------------------------------------------
# 8. read_session (task-da873c76 Deliverable 1)
# ---------------------------------------------------------------------------

def test_read_session_returns_pane_text_for_live_session(queue_env, monkeypatch, fake_subprocess):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")
    # Trailing blank lines must be stripped so a mostly-empty pane does not
    # come back as a page of nothing.
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="line1\nline2\nline3\n\n\n")

    result = json.loads(rms.read_session("cto", 40))
    assert result["status"] == "ok"
    assert result["target_role"] == "cto"
    assert result["tmux_session"] == "cto-abc123"
    assert result["text"] == "line1\nline2\nline3"
    assert result["lines_returned"] == 3


def test_read_session_rejects_unknown_role(queue_env):
    result = json.loads(rms.read_session("ceo", 40))
    assert result["status"] == "rejected"


def test_read_session_no_live_session_is_not_found_not_an_exception(queue_env):
    """No <role>-active pointer at all -- must not raise."""
    result = json.loads(rms.read_session("cfo", 40))
    assert result["status"] == "not_found"
    assert result["target_role"] == "cfo"


def test_read_session_stale_pointer_is_not_found(queue_env, monkeypatch):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cgo-active").write_text("dead99")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: False)
    result = json.loads(rms.read_session("cgo", 40))
    assert result["status"] == "not_found"


def test_read_session_lines_above_cap_is_clamped(queue_env, monkeypatch, fake_subprocess):
    """A pane can hold thousands of lines -- a huge request must not come
    back unbounded."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cmo-active").write_text("xyz789")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cmo-xyz789")
    huge_pane = "\n".join(f"line{i}" for i in range(5000))
    fake_subprocess["tmux"] = FakeCompleted(0, stdout=huge_pane)

    result = json.loads(rms.read_session("cmo", 999_999))
    assert result["lines_returned"] == rms.READ_SESSION_MAX_LINES
    returned_lines = result["text"].splitlines()
    assert len(returned_lines) == rms.READ_SESSION_MAX_LINES
    assert returned_lines[0] == f"line{5000 - rms.READ_SESSION_MAX_LINES}"
    assert returned_lines[-1] == "line4999"


def test_read_session_host_mac_waits_then_reports_pending_not_a_stale_answer(
        queue_env, monkeypatch):
    """The Mac agent (runners/mac_agent.py) now drains this queue, so a mac
    read is enqueued rather than refused outright.

    The original concern still holds and still shapes the design: a read is
    only worth answering while it is current. So the wait is BOUNDED, and an
    unanswered request comes back as `pending` — never parked to be answered
    minutes later and presented as "now".
    """
    monkeypatch.setattr(rms, "MAC_READ_WAIT_S", 0.05)
    monkeypatch.setattr(rms, "MAC_READ_POLL_S", 0.01)

    result = json.loads(rms.read_session("cto", 40, host="mac"))

    assert result["status"] == "pending"
    assert result["host"] == "mac"
    assert "queue_id" in result
    # It IS queued now -- that is the change. The agent will pick it up.
    assert [e["kind"] for e in rms._queue_list_pending()] == ["read"]


def test_read_session_host_mac_returns_the_pane_once_the_agent_answers(
        queue_env, monkeypatch):
    """Happy path: the agent writes the captured pane into the row's result,
    and the caller gets it back labelled as pane contents, not as speech."""
    monkeypatch.setattr(rms, "MAC_READ_WAIT_S", 5)
    monkeypatch.setattr(rms, "MAC_READ_POLL_S", 0.01)

    real_get = rms._queue_get

    def answer_on_first_poll(entry_id):
        rms._queue_mark_done(entry_id, "[cto-abc123] hello from the mac")
        return real_get(entry_id)

    monkeypatch.setattr(rms, "_queue_get", answer_on_first_poll)

    result = json.loads(rms.read_session("cto", 40, host="mac"))

    assert result["status"] == "ok"
    assert "hello from the mac" in result["pane"]
    assert "not a reply" in result["note"], (
        "pane text must never be presented as something the session said")


def test_read_session_constructs_fixed_argv_only(queue_env, monkeypatch):
    """SECURITY BOUNDARY: read_session accepts no session name, pane id, or
    flag from the caller -- the tmux command is a fixed argv built only
    from the resolved session name."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cgo-active").write_text("sess1")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cgo-sess1")

    captured = {}

    def _run(cmd, **kwargs):
        captured["cmd"] = cmd
        return FakeCompleted(0, stdout="hi\n")

    monkeypatch.setattr(rms.subprocess, "run", _run)

    rms.read_session("cgo", 5)
    assert captured["cmd"] == ["tmux", "capture-pane", "-p", "-t", "cgo-sess1"]


# ---------------------------------------------------------------------------
# 9. relay_to_session wait (task-da873c76 Deliverable 2)
# ---------------------------------------------------------------------------

def test_relay_to_session_wait_disabled_is_unchanged(queue_env, monkeypatch):
    """Regression: omitting `wait` must behave exactly as before -- no
    pane_after_wait key, no sleep, no tmux capture-pane call."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")
    monkeypatch.setattr(rms.tmux_session, "send_keys", lambda s, t, **kw: None)

    def _run(cmd, **kwargs):
        raise AssertionError(f"unexpected subprocess.run call: {cmd!r}")

    monkeypatch.setattr(rms.subprocess, "run", _run)

    result = json.loads(rms.relay_to_session("cto", "status update please"))
    assert result == {
        "status": "delivered", "target_role": "cto",
        "tmux_session": "cto-abc123",
        "message": rms.RELAY_PREFIX + "status update please",
    }


def test_relay_to_session_wait_enabled_labels_pane_not_reply(queue_env, monkeypatch, fake_subprocess):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")
    monkeypatch.setattr(rms.tmux_session, "send_keys", lambda s, t, **kw: None)

    slept = {}
    monkeypatch.setattr(rms.time, "sleep", lambda s: slept.setdefault("seconds", s))
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="ok done\n")

    result = json.loads(rms.relay_to_session("cto", "status update please", wait=True))
    assert result["status"] == "delivered"
    assert slept["seconds"] == rms.RELAY_WAIT_SECONDS
    pane = result["pane_after_wait"]
    assert pane["text"] == "ok done"
    assert pane["seconds_after_send"] == rms.RELAY_WAIT_SECONDS
    # Must NOT claim this is confirmed to be a reply.
    assert "not confirmed to be a reply" in pane["note"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

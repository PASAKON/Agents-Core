"""Tests for tools/tmux_session.py.

Written after a live failure on Contabo: `create()` hardcoded `/bin/zsh`, which
does not exist on Debian. `tmux new-session -d ... /bin/zsh -l -c '...'` exits
**0** anyway — tmux makes the session, the missing shell dies instantly, the
session goes with it — so `create()` returned cleanly and `spawn_c_level`
reported "spawned" for a session that was never there. SomPong then told the CEO
over Telegram that a C-level had been opened.

So these are mostly "does the success path actually mean success" tests. No real
tmux anywhere: every subprocess is stubbed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import tmux_session as ts  # noqa: E402


class FakeRun:
    """Records argv for every subprocess.run call."""

    def __init__(self, returncode=0):
        self.calls: list[list[str]] = []
        self.returncode = returncode

    def __call__(self, argv, *a, **kw):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(argv, self.returncode, "", "")


# ---------------------------------------------------------------------------
# login_shell
# ---------------------------------------------------------------------------

def test_login_shell_prefers_the_invoking_users_shell(monkeypatch, tmp_path):
    shell = tmp_path / "myshell"
    shell.write_text("#!/bin/sh\n")
    monkeypatch.setenv("SHELL", str(shell))
    assert ts.login_shell() == str(shell)


def test_login_shell_skips_a_shell_that_does_not_exist(monkeypatch):
    """The Contabo case: $SHELL bogus and no zsh installed. Must fall through
    to something real rather than returning a path that isn't there."""
    monkeypatch.setenv("SHELL", "/nonexistent/shell")
    monkeypatch.setattr(ts.Path, "exists",
                        lambda self: str(self) in ("/bin/bash", "/bin/sh"))
    assert ts.login_shell() == "/bin/bash"


def test_login_shell_never_returns_a_missing_path(monkeypatch):
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr(ts.Path, "exists", lambda self: False)
    assert ts.login_shell() == "/bin/sh"  # POSIX guarantee, last resort


def test_login_shell_is_not_hardcoded_to_zsh(monkeypatch):
    """Guard against a revert. zsh is right on the Mac and absent on Debian;
    pinning either one is what caused the silent failure."""
    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr(ts.Path, "exists", lambda self: str(self) != "/bin/zsh")
    assert ts.login_shell() != "/bin/zsh"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_uses_the_resolved_shell_not_a_literal(monkeypatch):
    fake = FakeRun()
    seen = {"n": 0}

    def has_session(_s):
        # Absent on the pre-check, present on the post-check. Returning True
        # for both would make create() take its idempotent early return and
        # never build an argv to assert on.
        seen["n"] += 1
        return seen["n"] > 1

    monkeypatch.setattr(ts.subprocess, "run", fake)
    monkeypatch.setattr(ts, "has_session", has_session)
    monkeypatch.setattr(ts, "login_shell", lambda: "/bin/bash")

    ts.create("live-after", "/tmp", "echo hi")

    argv = fake.calls[-1]
    assert "/bin/bash" in argv
    assert "/bin/zsh" not in argv


def test_create_raises_when_the_session_is_not_alive_afterwards(monkeypatch):
    """THE test. tmux exits 0 for a command it could not run, so a clean exit
    code must never be reported as a live session."""
    fake = FakeRun(returncode=0)          # tmux says fine...
    monkeypatch.setattr(ts.subprocess, "run", fake)
    monkeypatch.setattr(ts, "has_session", lambda s: False)   # ...but nothing is there

    with pytest.raises(RuntimeError) as e:
        ts.create("ghost", "/tmp", "exec bash whatever.sh")

    assert "ghost" in str(e.value)
    assert "exited immediately" in str(e.value)


def test_create_is_idempotent_for_a_session_that_already_exists(monkeypatch):
    fake = FakeRun()
    monkeypatch.setattr(ts.subprocess, "run", fake)
    monkeypatch.setattr(ts, "has_session", lambda s: True)

    ts.create("already", "/tmp", "echo hi")

    assert fake.calls == [], "must not create a second session over a live one"


def test_create_succeeds_quietly_when_the_session_comes_up(monkeypatch):
    calls = {"n": 0}

    def has_session(_s):
        # False on the pre-check, True on the post-check — a real creation.
        calls["n"] += 1
        return calls["n"] > 1

    monkeypatch.setattr(ts.subprocess, "run", FakeRun())
    monkeypatch.setattr(ts, "has_session", has_session)

    ts.create("fresh", "/tmp", "echo hi")   # must not raise

"""Tests for tools/tmux_session.py.

Written after a live failure on Contabo: `create()` hardcoded `/bin/zsh`, which
does not exist on Debian. `tmux new-session -d ... /bin/zsh -l -c '...'` exits
**0** anyway — tmux makes the session, the missing shell dies instantly, the
session goes with it — so `create()` returned cleanly and `spawn_c_level`
reported "spawned" for a session that was never there. SomPong then told the CEO
over Telegram that a C-level had been opened.

So these are mostly "does the success path actually mean success" tests. No real
tmux anywhere: every subprocess is stubbed.

task-83ec62b6 adds tmux_bin() (below the login_shell() tests): launchd hands a
process a bare PATH that does not carry Homebrew's /opt/homebrew/bin, so a
plain "tmux" argv[0] resolved to nothing and live sessions came back as "no
live session" -- a confident wrong answer, not a clean error. tmux_bin() is
now the ONE resolver for the whole org (see the source-level guard test at the
bottom); every other module delegates to it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import tmux_session as ts  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_tmux_bin_cache():
    """The root conftest's autouse fixture already pins TMUX_BIN=tmux and
    resets the cache around every test -- this file's own tests need a clean
    slate on top of that so they can exercise resolution paths the pin would
    otherwise short-circuit."""
    ts._reset_tmux_bin_cache()
    yield
    ts._reset_tmux_bin_cache()


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


# ---------------------------------------------------------------------------
# tmux_bin
# ---------------------------------------------------------------------------

def test_tmux_bin_env_override_wins_over_everything(monkeypatch):
    monkeypatch.setenv("TMUX_BIN", "/custom/path/tmux")
    # Both other paths would also resolve successfully -- proves the override
    # short-circuits them rather than merely being tried first by luck.
    monkeypatch.setattr(ts.shutil, "which", lambda name: "/usr/bin/tmux")
    monkeypatch.setattr(ts.Path, "exists", lambda self: True)
    assert ts.tmux_bin() == "/custom/path/tmux"


def test_tmux_bin_prefers_which_over_hardcoded_candidates(monkeypatch):
    monkeypatch.delenv("TMUX_BIN", raising=False)
    monkeypatch.setattr(ts.shutil, "which", lambda name: "/opt/local/bin/tmux")
    # The hardcoded candidates would ALSO exist here -- which() must still win.
    monkeypatch.setattr(ts.Path, "exists", lambda self: True)
    assert ts.tmux_bin() == "/opt/local/bin/tmux"


def test_tmux_bin_launchd_case_path_stripped_finds_homebrew_candidate(monkeypatch):
    """THE bug this task fixes: launchd's bare PATH means shutil.which("tmux")
    finds nothing, but /opt/homebrew/bin/tmux is still there on disk. That is
    what must come back, not a silent "tmux not found"."""
    monkeypatch.delenv("TMUX_BIN", raising=False)
    monkeypatch.setattr(ts.shutil, "which", lambda name: None)
    monkeypatch.setattr(ts.Path, "exists",
                        lambda self: str(self) == "/opt/homebrew/bin/tmux")
    assert ts.tmux_bin() == "/opt/homebrew/bin/tmux"


def test_tmux_bin_nothing_found_anywhere_falls_back_to_bare_name(monkeypatch):
    """Never an empty string and never a path that does not exist -- an empty
    argv[0] is how a missing tool turns into a confusing error instead of a
    clear one."""
    monkeypatch.delenv("TMUX_BIN", raising=False)
    monkeypatch.setattr(ts.shutil, "which", lambda name: None)
    monkeypatch.setattr(ts.Path, "exists", lambda self: False)
    result = ts.tmux_bin()
    assert result == "tmux"
    assert result != ""


def test_tmux_bin_is_cached_across_calls(monkeypatch):
    monkeypatch.delenv("TMUX_BIN", raising=False)
    calls = {"n": 0}

    def fake_which(name):
        calls["n"] += 1
        return "/usr/bin/tmux"

    monkeypatch.setattr(ts.shutil, "which", fake_which)
    first = ts.tmux_bin()
    second = ts.tmux_bin()
    assert first == second == "/usr/bin/tmux"
    assert calls["n"] == 1, "cached -- shutil.which must run only once"


def test_tmux_bin_cache_is_resettable(monkeypatch):
    monkeypatch.setenv("TMUX_BIN", "/first/tmux")
    assert ts.tmux_bin() == "/first/tmux"

    monkeypatch.setenv("TMUX_BIN", "/second/tmux")
    assert ts.tmux_bin() == "/first/tmux", "cache should still hold the first answer"

    ts._reset_tmux_bin_cache()
    assert ts.tmux_bin() == "/second/tmux", "reset must let a new resolution happen"


# ---------------------------------------------------------------------------
# D3 guard -- tmux_bin() must stay the ONE resolver
# ---------------------------------------------------------------------------

def test_no_other_module_defines_its_own_tmux_candidate_list():
    """task-83ec62b6: runners/mac_agent.py and tools/org_inspector.py each
    used to hardcode this same /opt/homebrew/bin/tmux-style candidate list
    privately. Both are now thin delegates to tmux_bin() above. This guards
    against a third private copy ever showing up again."""
    literal = "/opt/homebrew/bin/tmux"
    canonical = ts.__file__ and Path(ts.__file__).resolve()
    offenders = []
    for path in sorted(ROOT.rglob("*.py")):
        # worktrees/ holds other tasks' in-flight checkouts of this same repo,
        # each a full copy at whatever commit that task branched from. They are
        # not this tree's source and are not ours to police — one still carrying
        # the old private list is a stale copy, not a new violation. Skipping
        # them is also what makes this test mean the same thing in a DEV
        # worktree (where the directory does not exist) and on main (where it
        # does): without it, the guard passed for the DEV who wrote it and
        # failed the moment it landed.
        if any(part.startswith(".") or part in ("__pycache__", "worktrees")
               for part in path.relative_to(ROOT).parts):
            continue
        if path.resolve() == canonical:
            continue
        if path.name.startswith("test_") or path.name == "conftest.py":
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        if literal in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == [], (
        f"private tmux candidate list found outside tools/tmux_session.py: {offenders}"
    )

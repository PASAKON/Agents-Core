"""The wake looks at the pane before it presses a key (2026-10-14).

tools/agent_transport.py `_wake_tmux_send` types "[New message from X]" into a
peer's tmux pane and presses Enter twice. Enter on a Claude Code choice prompt
picks the highlighted option ("1. Yes"), and text typed onto the CEO's draft is
submitted with it. Now it captures the pane (lib.pane_screen, the predicates
tools/rename_service.py uses) before typing and before each Enter.

No real tmux: `subprocess.run` inside agent_transport is a fake pane that fails
the test on any argv that is not a tmux capture-pane / send-keys on the one test
target. The screens are tests/test_rename_service.py's captures of a real pane
(14 Oct); QUESTION is drawn after Claude Code's question dialog (no real capture
of one is in the repo).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.mailbox as mailbox  # noqa: E402
from lib import pane_screen  # noqa: E402
from tools import agent_transport as at  # noqa: E402
from tools import rename_service as rs  # noqa: E402
from tools import send_to_cxo as sc  # noqa: E402
from tools import tmux_session  # noqa: E402

from test_rename_service import BUSY, DRAFT, DRAFT_BELOW, EMPTY, FRESH, PERMISSION, RULE  # noqa: E402

SESSION = "cfo-sess1234"
MARKER = "[New message from CTO]"
QUESTION = (f"out\n{RULE}\n ☐ Deploy\n\nWhich environment should I deploy to?\n\n"
            "❯ 1. Staging\n     Safe test environment\n  2. Production\n     Live traffic\n"
            "  3. Type something.\n\nEnter to select · ↑/↓ to navigate · Esc to cancel\n")
BOXED_PERMISSION = ("╭──────────────────────────────────╮\n│ Bash command                     │\n"
                    "│   rm -rf build                   │\n│ Do you want to proceed?          │\n"
                    "│ ❯ 1. Yes                         │\n│   2. No, and tell Claude what to │\n"
                    "╰──────────────────────────────────╯\n")
_CHOICE = re.compile(r"^[\s│┃|]*❯\s*\d+\.\s")   # a "❯ 1. Yes" row, never the input line


class FakePane:
    """One pane behind a fake `subprocess.run`. capture-pane prints `base` with
    whatever is in the input box drawn on its last ❯ line; send-keys -l types
    into the box; Enter submits a non-empty box (unless swallowed, GH #70)."""

    def __init__(self, base: str):
        self.base, self.box = base, ""
        self.calls: list[list[str]] = []
        self.submitted: list[str] = []
        self.capture_rc, self.capture_exc = 0, None
        self.swallow_enters = 0
        self.on_sleep: dict[float, object] = {}   # seconds -> fn(pane), run during that settle

    def screen(self) -> str:
        """`base` with the box drawn on its input line (the last ❯ line that is not
        a numbered choice); a dialog with no input line hides the box."""
        lines = self.base.split("\n")
        rows = [n for n, line in enumerate(lines) if "❯" in line and not _CHOICE.match(line)]
        if not self.box or not rows:
            return self.base
        lines[rows[-1]] = lines[rows[-1]].split("❯", 1)[0] + "❯ " + self.box
        return "\n".join(lines)

    def run(self, argv, **kw):
        argv = list(argv)
        assert argv[0] == "tmux", f"not the pinned tmux: {argv}"
        assert argv[argv.index("-t") + 1] == SESSION, f"wrong target: {argv}"
        assert kw.get("timeout"), f"tmux call without a timeout: {argv}"
        self.calls.append(argv)
        if argv[1] == "capture-pane":
            if self.capture_exc is not None:
                raise self.capture_exc
            ok = self.capture_rc == 0
            return subprocess.CompletedProcess(argv, self.capture_rc, self.screen() if ok else "",
                                               "" if ok else "can't find pane")
        if argv[1] == "send-keys":
            if "-l" in argv:
                self.box += argv[-1]
            elif argv[-1] == "Enter":
                if self.swallow_enters:
                    self.swallow_enters -= 1
                elif self.box:
                    self.submitted.append(self.box)
                    self.box = ""
            else:
                raise AssertionError(f"key the wake never sends: {argv}")
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"tmux {argv[1]} is never used by the wake: {argv}")

    def sleep(self, s):
        fn = self.on_sleep.get(s)
        if fn:
            fn(self)

    @property
    def keys(self) -> list[str]:
        """What reached the pane: the typed text, or the key name."""
        return [c[-1] for c in self.calls if c[1] == "send-keys"]


@pytest.fixture
def pane(monkeypatch):
    def make(base: str) -> FakePane:
        p = FakePane(base)
        monkeypatch.setattr(at.subprocess, "run", p.run)
        monkeypatch.setattr(at.time, "sleep", p.sleep)
        monkeypatch.setattr(tmux_session, "tmux_bin", lambda: "tmux")
        return p
    return make


def _held(p: FakePane) -> str:
    with pytest.raises(at.WakeHeld) as e:
        at._wake_tmux_send(SESSION, MARKER)
    return str(e.value)


# --- before typing ---------------------------------------------------------------------

@pytest.mark.parametrize("screen,why", [
    (PERMISSION, "choice prompt on screen"),
    (BOXED_PERMISSION, "choice prompt on screen"),
    (QUESTION, "choice prompt on screen"),
    (DRAFT, "draft in the input box"),
    (DRAFT_BELOW, "draft in the input box"),
    ("$ ls\nfile\n$ ", "no input box on screen"),
], ids=["permission", "boxed-permission", "question", "draft", "draft-below", "shell"])
def test_a_dialog_a_draft_or_no_box_gets_no_key_at_all(pane, screen, why):
    p = pane(screen)
    assert _held(p) == f"not woken: {why}; nothing typed"
    assert p.keys == []
    assert [c[1] for c in p.calls] == ["capture-pane"]


@pytest.mark.parametrize("screen", [EMPTY, FRESH, BUSY], ids=["empty", "fresh", "busy"])
def test_an_empty_box_idle_fresh_or_busy_is_woken_as_before(pane, screen):
    p = pane(screen)
    at._wake_tmux_send(SESSION, MARKER)
    assert p.keys == [MARKER, "Enter", "Enter"]
    assert p.submitted == [MARKER]
    assert [c[1] for c in p.calls] == ["capture-pane", "send-keys", "capture-pane", "send-keys",
                                       "capture-pane", "send-keys"]


def test_the_settle_delays_are_unchanged(pane, monkeypatch):
    p = pane(BUSY)
    sleeps = []
    monkeypatch.setattr(at.time, "sleep", lambda s: sleeps.append(s) or p.sleep(s))
    at._wake_tmux_send(SESSION, MARKER)
    assert sleeps == [0.4, 0.3]


@pytest.mark.parametrize("failure", [
    subprocess.TimeoutExpired(["tmux", "capture-pane"], 5),
    FileNotFoundError("tmux"),
], ids=["timeout", "no-tmux"])
def test_a_capture_that_raises_gets_no_key(pane, failure):
    p = pane(EMPTY)
    p.capture_exc = failure
    assert _held(p) == f"not woken: could not read the pane ({type(failure).__name__}); nothing typed"
    assert p.keys == []


def test_a_capture_that_exits_nonzero_gets_no_key(pane):
    p = pane(EMPTY)
    p.capture_rc = 1
    assert _held(p) == "not woken: could not read the pane (tmux exit 1); nothing typed"
    assert p.keys == []


# --- before each Enter -------------------------------------------------------------------

@pytest.mark.parametrize("dialog", [PERMISSION, QUESTION], ids=["permission", "question"])
@pytest.mark.parametrize("start", [EMPTY, BUSY], ids=["idle", "busy"])
def test_a_dialog_that_opens_after_typing_gets_no_enter(pane, start, dialog):
    p = pane(start)
    p.on_sleep[0.4] = lambda q: setattr(q, "base", dialog)
    assert "choice prompt on screen after typing; no Enter" in _held(p)
    assert p.keys == [MARKER]
    assert p.submitted == []


def test_a_dialog_that_opens_after_the_first_enter_gets_no_rescue_enter(pane):
    p = pane(BUSY)
    p.on_sleep[0.3] = lambda q: setattr(q, "base", PERMISSION)
    assert "choice prompt on screen before the rescue Enter" in _held(p)
    assert p.keys == [MARKER, "Enter"]


def test_keys_pressed_between_typing_and_enter_are_not_submitted(pane):
    p = pane(EMPTY)
    p.on_sleep[0.4] = lambda q: setattr(q, "box", q.box + "hel")
    assert "draft in the input box after typing; no Enter" in _held(p)
    assert p.keys == [MARKER] and p.submitted == []


def test_a_draft_started_after_the_first_enter_gets_no_rescue_enter(pane):
    p = pane(EMPTY)
    p.on_sleep[0.3] = lambda q: setattr(q, "box", "the CEO starts typing")
    assert "draft in the input box before the rescue Enter" in _held(p)
    assert p.keys == [MARKER, "Enter"]
    assert p.submitted == [MARKER]


def test_a_capture_that_fails_before_enter_gets_no_enter(pane):
    p = pane(EMPTY)
    p.on_sleep[0.4] = lambda q: setattr(q, "capture_exc", subprocess.TimeoutExpired(["tmux"], 5))
    assert _held(p) == "not woken: could not read the pane (TimeoutExpired) after typing; no Enter"
    assert p.keys == [MARKER]


def test_a_swallowed_first_enter_is_still_rescued(pane):
    """GH #70: the box still shows the marker before the second Enter, so it goes."""
    p = pane(EMPTY)
    p.swallow_enters = 1
    at._wake_tmux_send(SESSION, MARKER)
    assert p.keys == [MARKER, "Enter", "Enter"]
    assert p.submitted == [MARKER]


def test_a_box_not_yet_redrawn_still_gets_its_enter(pane):
    """The TUI may not have drawn all of the marker 0.4 s later; the start of it is ours."""
    p = pane(EMPTY)
    real = p.screen
    p.screen = lambda: real().replace(MARKER, MARKER[:8]) if p.box == MARKER else real()
    at._wake_tmux_send(SESSION, MARKER)
    assert p.keys == [MARKER, "Enter", "Enter"]


# --- the wrappers: never raise, letter still delivered ------------------------------------

def test_attempt_wake_reports_a_held_wake_as_not_woken_and_never_raises(pane, monkeypatch):
    p = pane(PERMISSION)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: s == SESSION)
    logs: list[str] = []
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: logs.append(m))
    assert at.attempt_wake(SESSION, "CTO", "send_to_cxo") is False
    assert p.keys == []
    assert logs[-1] == (f"[send_to_cxo] wake failed: {SESSION}: "
                        "not woken: choice prompt on screen; nothing typed")


def test_attempt_wake_on_a_busy_pane_is_still_true(pane, monkeypatch):
    p = pane(BUSY)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: s == SESSION)
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: None)
    assert at.attempt_wake(SESSION, "CTO", "send_to_cxo") is True
    assert p.keys == [MARKER, "Enter", "Enter"]


@pytest.mark.parametrize("screen", [PERMISSION, QUESTION, DRAFT], ids=["permission", "question", "draft"])
def test_send_to_cxo_still_delivers_the_letter_when_the_wake_is_held(pane, screen, tmp_path, monkeypatch):
    p = pane(screen)
    locks, inbox = tmp_path / "locks", tmp_path / "inbox"
    locks.mkdir()
    (locks / "cfo-active").write_text("sess1234")
    for var in ("CXO_ROLE", "CXO_SESSION_ID", "CTO_SESSION_ID", "WORKER_TASK_ID", "WORKER_ROLE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CEO_SESSION", "1")
    monkeypatch.setattr(sc, "LOCKS_DIR", locks)
    monkeypatch.setattr(mailbox, "INBOX_ROOT", inbox)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: s == SESSION)
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: None)
    assert sc._wake_tmux_send is at._wake_tmux_send      # the real wake, not a stub
    assert sc.send("cfo", "hello") == "queued to CFO #sess1234: [CEO] : hello"
    assert [x["body"] for x in mailbox.peek("cfo", "sess1234", root=inbox)] == ["hello"]
    assert p.keys == []


def test_rename_service_reads_the_same_predicates():
    """Moved, not copied: one definition, re-exported by tools/rename_service.py."""
    for name in ("pane_waiting", "box_empty", "pane_busy", "prompt_ready", "typed_text", "_squash"):
        assert getattr(rs, name) is getattr(pane_screen, name)
    assert at.pane_waiting is pane_screen.pane_waiting and at.box_empty is pane_screen.box_empty

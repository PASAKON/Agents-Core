"""Org Mesh W3.5 (docs/design/org-mesh.md, docs/ops/windows-wake.md): waking a
Windows Terminal tab from a letter.

Two halves, neither of which needs PowerShell, a desktop or a Windows box:

  * static checks on the .ps1 files. Their behaviour was measured on winbox
    (docs/reports/task-109734f6/); what a Mac can pin is the TEXT that makes the
    measured behaviour safe: ASCII only, the foreground guard in front of every
    send, focus-in-terminal and unique-tab checks, no task registration inside
    wake.ps1, and the runner's marker allow-list.
  * tools/agent_transport.py: POSIX behaviour is pinned (the pre-change source
    of `attempt_wake` and `_wake_tmux_send`, hashed), and the win32 branch is
    exercised with the platform faked, `subprocess.run` a recorder and a tmp_path
    request folder.

Run:  .venv/bin/python -m pytest tests/test_w35_wake.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import agent_transport as at  # noqa: E402
from tools import tmux_session  # noqa: E402

WIN = ROOT / "windows"
WAKE = WIN / "wake.ps1"
RUNNER = WIN / "wake-request.ps1"
REGISTER = WIN / "register-org-tasks.ps1"


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _code(p: Path) -> str:
    """The script without comment-only lines, so a rule quoted in a comment does
    not satisfy (or trip) a check on the code."""
    return "\n".join(ln for ln in _text(p).splitlines() if not ln.strip().startswith("#"))


def _function_body(code: str, name: str) -> str:
    m = re.search(rf"^function {re.escape(name)}\b.*?^\}}", code, re.S | re.M)
    assert m, f"function {name} not found"
    return m.group(0)


# ---------------------------------------------------------------------------
# .ps1 static checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("script", [WAKE, RUNNER, REGISTER], ids=lambda p: p.name)
def test_ps1_is_ascii_only(script):
    # Windows PowerShell 5.1 reads a BOM-less .ps1 as ANSI: one non-ASCII byte
    # can make the whole script fail to parse, silently, inside a hidden task.
    bad = [(n, c) for n, ln in enumerate(_text(script).splitlines(), 1) for c in ln if ord(c) > 127]
    assert bad == [], f"non-ASCII characters at {bad[:5]}"


def test_wake_reads_the_foreground_window_before_every_send():
    code = _code(WAKE)
    # the guard reads the foreground window's handle, class and title ...
    guard = _function_body(code, "Test-Foreground")
    for needle in ("GetForegroundWindow", "Cls(", "Text(", "$WT_CLASS"):
        assert needle in guard, f"Test-Foreground no longer checks {needle}"
    # ... and Send-Guarded asks it before the text AND again before Enter
    send = _function_body(code, "Send-Guarded")
    first_key = send.index("SendKeys((ConvertTo-SendKeysText")
    enter = send.index("SendKeys('{ENTER}')")
    assert "Test-Foreground" in send[:first_key], "no guard before the marker text"
    assert "Test-Foreground" in send[first_key:enter], "no guard between the text and Enter"
    # no other SendKeys anywhere: every key goes through Send-Guarded
    assert code.count("SendKeys(") == 2, "a key is sent outside Send-Guarded"


def test_wake_guard_also_requires_keyboard_focus_in_the_terminal():
    # Measured 2026-09-30: foreground + exact title passed 5/5 while every key was
    # swallowed by the tab strip (0/5 delivered, exit 0). Focus is part of the guard.
    guard = _function_body(_code(WAKE), "Test-Foreground")
    assert "FocusedElement" in guard and "TermControl" in guard


def test_wake_refuses_with_exit_3_and_sends_nothing_when_the_guard_fails():
    code = _code(WAKE)
    assert re.search(r"Done 3 \"guard refused, nothing sent", code)
    send = _function_body(code, "Send-Guarded")
    assert re.search(r"if \(-not \(Test-Foreground \$hwnd\)\) \{ return 'refused' \}", send)


def test_wake_demands_exactly_one_matching_tab_before_raising_or_sending_anything():
    code = _code(WAKE)
    first_use = min(code.index("Raise-Window $hwnd"), code.index("Send-Guarded $hwnd"))
    find = code.index("$found = Find-Tabs")
    assert find < first_use, "the target must be located before any raise/send"
    assert re.search(r"if \(\$found\.Count -gt 1\) \{ Done 2 ", code), "ambiguity must exit 2"
    assert re.search(r"if \(\$found\.Count -eq 0\) \{ Done 2 ", code)


def test_wake_never_registers_a_task_and_never_fakes_a_key_to_win_the_foreground():
    code = _code(WAKE)
    assert "Register-ScheduledTask" not in code
    assert "New-ScheduledTask" not in code
    # a synthetic ALT to steal focus is itself a key sent to whatever is in front
    assert "keybd_event" not in code
    assert "{ALT}" not in code and "%{" not in code


def test_wake_arguments_are_printable_ascii_and_session_0_is_refused():
    code = _code(WAKE)
    assert re.search(r"\$Title -cmatch '\[\^\\x20-\\x7E\]'", code)
    assert re.search(r"\$Marker -cmatch '\[\^\\x20-\\x7E\]'", code)
    assert re.search(r"if \(\$session -eq 0\) \{ Done 4 ", code)


def test_wake_contains_mode_needs_a_real_token():
    code = _code(WAKE)
    assert re.search(r"\$Contains -and \$Title\.Length -lt 6\) \{ Done 64 ", code)


def test_runner_accepts_only_the_org_wake_marker_shape():
    code = _code(RUNNER)
    m = re.search(r"\$MARKER_RE\s*=\s*'([^']+)'", code)
    assert m, "runner has no marker allow-list"
    marker_re = re.compile(m.group(1))
    good = at._WAKE_MARKER_TEMPLATE.format(label="CTO")
    assert marker_re.fullmatch(good)
    for evil in ("hello", "[New message from x] & calc", "[New message from x]\nrm -rf /",
                 "[New message from " + "A" * 41 + "]", "[New message from ]"):
        assert not marker_re.fullmatch(evil), evil
    t = re.search(r"\$TITLE_RE\s*=\s*'([^']+)'", code)
    assert t
    title_re = re.compile(t.group(1))
    assert title_re.fullmatch("#2c6b9f03")
    for evil in ('x"; calc', "a`b", "x\ny", "$(calc)", ""):
        assert not title_re.fullmatch(evil), evil


def test_runner_passes_the_request_values_as_arguments_never_as_code():
    code = _code(RUNNER)
    assert "Invoke-Expression" not in code and not re.search(r"\biex\b", code)
    assert "& powershell.exe @wa" in code
    assert "Register-ScheduledTask" not in code


def test_runner_expires_old_requests():
    assert re.search(r"\$MAX_AGE_S\s*=\s*\d+", _code(RUNNER))


def test_register_script_makes_one_on_demand_interactive_task_and_can_undo_it():
    code = _code(REGISTER)
    assert "'MooniexOrgWake'" in code
    assert "-LogonType Interactive" in code and "-RunLevel Limited" in code
    assert "New-ScheduledTaskTrigger" not in code, "the task must run only when something runs it"
    assert "[switch] $Remove" in code and "Unregister-ScheduledTask" in code
    assert re.search(r"SessionId\) -eq 0", code.replace(" ", "")) or "SessionId -eq 0" in code


def test_nothing_in_python_registers_the_wake_task():
    # The CEO registers MooniexOrgWake, once, at the desktop. No agent code may.
    for py in list((ROOT / "tools").glob("*.py")) + list((ROOT / "lib").glob("*.py")):
        src = py.read_text(encoding="utf-8", errors="replace")
        assert not re.search(r"Register-ScheduledTask[^\n]*MooniexOrgWake", src), py.name
        assert "register-org-tasks" not in src.replace("windows/register-org-tasks.ps1", ""), py.name


# ---------------------------------------------------------------------------
# tools/agent_transport.py: POSIX byte-for-byte unchanged
# ---------------------------------------------------------------------------

# sha256 of inspect.getsource() (LF-normalised) taken BEFORE W3.5 touched the file.
_ATTEMPT_WAKE_POSIX_SHA = "6648aaf8eb1d72ca1aa7bfd282083718339bb259f0b8acdf06e05d37857ee7d2"
_WAKE_TMUX_SEND_SHA = "05bb50d29eff03c0a8792b5c82497b786d28104d0c29d20a86ef5896ee84c42b"


def _sha(src: str) -> str:
    return hashlib.sha256(src.replace("\r\n", "\n").encode()).hexdigest()


def test_attempt_wake_is_the_old_function_plus_one_marked_block():
    src = inspect.getsource(at.attempt_wake).replace("\r\n", "\n")
    start = "    # W3.5 win32 branch"
    end = "    # end W3.5 win32 branch\n"
    assert src.count(start) == 1 and src.count(end) == 1
    a, rest = src.split(start)
    _block, b = rest.split(end)
    assert _sha(a + b) == _ATTEMPT_WAKE_POSIX_SHA, "attempt_wake changed outside the W3.5 block"


def test_wake_tmux_send_is_untouched():
    assert _sha(inspect.getsource(at._wake_tmux_send)) == _WAKE_TMUX_SEND_SHA


class _Runs:
    def __init__(self, rc: int = 0, out: str = "", err: str = ""):
        self.calls: list[list] = []
        self.rc, self.out, self.err = rc, out, err

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        return subprocess.CompletedProcess(argv, self.rc, self.out, self.err)


def _no_schtasks(monkeypatch) -> _Runs:
    runs = _Runs()
    monkeypatch.setattr(subprocess, "run", runs)
    return runs


def test_posix_attempt_wake_still_types_the_marker_through_tmux(monkeypatch):
    runs = _no_schtasks(monkeypatch)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: s == "cto-1234abcd")
    sent: list[tuple] = []
    logs: list[str] = []
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: logs.append(m))
    at.attempt_wake("cto-1234abcd", "CTO", "send_to_cxo", send_fn=lambda s, t: sent.append((s, t)))
    assert sent == [("cto-1234abcd", "[New message from CTO]")]
    assert logs == ["[send_to_cxo] wake attempted: cto-1234abcd",
                    "[send_to_cxo] wake succeeded: cto-1234abcd"]
    assert runs.calls == [], "the POSIX path must never reach schtasks"


def test_posix_attempt_wake_skips_a_session_that_is_not_live(monkeypatch):
    runs = _no_schtasks(monkeypatch)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: False)
    logs: list[str] = []
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: logs.append(m))
    at.attempt_wake("cto-1234abcd", "CTO", "send_to_cxo",
                    send_fn=lambda s, t: pytest.fail("typed into a dead session"))
    assert logs == ["[send_to_cxo] wake skipped (no live session): cto-1234abcd"]
    assert runs.calls == []


def test_posix_attempt_wake_still_never_raises(monkeypatch):
    _no_schtasks(monkeypatch)
    monkeypatch.setattr(at, "_is_windows", lambda: False)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: True)
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: None)

    def boom(s, t):
        raise RuntimeError("tmux died")

    at.attempt_wake("cto-1234abcd", "CTO", "send_to_cxo", send_fn=boom)


def test_falsy_session_still_does_nothing_on_both_platforms(monkeypatch):
    runs = _no_schtasks(monkeypatch)
    for win in (False, True):
        monkeypatch.setattr(at, "_is_windows", lambda w=win: w)
        at.attempt_wake(None, "CTO", "x", send_fn=lambda s, t: pytest.fail("woke nobody"))
        at.attempt_wake("", "CTO", "x", send_fn=lambda s, t: pytest.fail("woke nobody"))
    assert runs.calls == []


# ---------------------------------------------------------------------------
# tools/agent_transport.py: the win32 branch
# ---------------------------------------------------------------------------

def test_win32_attempt_wake_never_touches_tmux_and_uses_the_windows_function(monkeypatch):
    monkeypatch.setattr(at, "_is_windows", lambda: True)
    monkeypatch.setattr(tmux_session, "has_session", lambda s: pytest.fail("tmux on Windows"))
    calls: list[tuple] = []
    monkeypatch.setattr(at, "wake_windows_tab",
                        lambda session, label, **k: calls.append((session, label)) or {"woke": True, "why": "ok"})
    logs: list[str] = []
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: logs.append(m))
    at.attempt_wake("cto-1234abcd", "CTO", "send_to_cxo",
                    send_fn=lambda s, t: pytest.fail("tmux send on Windows"))
    assert calls == [("cto-1234abcd", "CTO")]
    assert logs[-1] == "[send_to_cxo] wake succeeded: cto-1234abcd: ok"


def test_win32_attempt_wake_never_raises(monkeypatch):
    monkeypatch.setattr(at, "_is_windows", lambda: True)
    monkeypatch.setattr(at.notify, "info", lambda m, *a, **k: None)

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(at, "wake_windows_tab", boom)
    at.attempt_wake("cto-1234abcd", "CTO", "send_to_cxo")


class _Task:
    """A stand-in for schtasks + the MooniexOrgWake runner: on `schtasks /run` it
    reads the newest request and writes the result the real runner would."""

    def __init__(self, wake_dir: Path, exit_code: int = 0, output: str = "WAKE exit=0 sent", rc: int = 0):
        self.dir, self.exit_code, self.output, self.rc = wake_dir, exit_code, output, rc
        self.calls: list[list] = []
        self.seen: dict | None = None

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        if self.rc == 0:
            (req,) = sorted((self.dir / "requests").glob("*.json"))
            self.seen = json.loads(req.read_text(encoding="ascii"))
            (self.dir / "results" / req.name).write_text(
                json.dumps({"id": req.stem, "exit": self.exit_code, "output": self.output}), encoding="ascii")
            req.unlink()
        return subprocess.CompletedProcess(argv, self.rc, "", "ERROR: no such task" if self.rc else "")


def test_wake_windows_tab_writes_the_request_runs_the_task_and_reads_the_result(tmp_path):
    task = _Task(tmp_path)
    r = at.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=task, sleep=lambda s: None)
    assert r == {"woke": True, "why": "keys sent to the verified tab"}
    assert task.calls == [["schtasks", "/run", "/tn", "MooniexOrgWake"]]
    assert task.seen == {"title": "#2c6b9f03", "marker": "[New message from CTO]", "contains": True}
    assert list((tmp_path / "requests").iterdir()) == [], "request left behind"
    assert list((tmp_path / "results").iterdir()) == [], "result left behind"


def test_the_request_the_python_side_writes_passes_the_runners_own_allow_lists(tmp_path):
    task = _Task(tmp_path)
    at.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=task, sleep=lambda s: None)
    code = _code(RUNNER)
    marker_re = re.compile(re.search(r"\$MARKER_RE\s*=\s*'([^']+)'", code).group(1))
    title_re = re.compile(re.search(r"\$TITLE_RE\s*=\s*'([^']+)'", code).group(1))
    assert marker_re.fullmatch(task.seen["marker"]) and title_re.fullmatch(task.seen["title"])


def test_a_wake_that_the_ps1_refused_is_not_woke(tmp_path):
    task = _Task(tmp_path, exit_code=3, output="WAKE exit=3 guard refused, nothing sent")
    r = at.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=task, sleep=lambda s: None)
    assert r["woke"] is False
    assert "exit 3" in r["why"] and "nothing sent" in r["why"]


def test_task_not_registered_withdraws_the_request_and_names_the_fix(tmp_path):
    task = _Task(tmp_path, rc=1)
    r = at.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=task, sleep=lambda s: None)
    assert r["woke"] is False and "register-org-tasks.ps1" in r["why"]
    assert list((tmp_path / "requests").iterdir()) == [], "a request that would fire whenever the task appears"


def test_no_result_in_time_withdraws_the_request(tmp_path):
    def silent(argv, **kw):
        return subprocess.CompletedProcess(argv, 0, "", "")

    r = at.wake_windows_tab("cto-2c6b9f03", "CTO", wait_s=0, wake_dir=tmp_path, run=silent,
                            sleep=lambda s: None)
    assert r["woke"] is False and "no result" in r["why"]
    assert list((tmp_path / "requests").iterdir()) == [], "an unserved request must not fire later"


def test_schtasks_missing_is_a_failure_not_a_crash(tmp_path):
    def missing(argv, **kw):
        raise FileNotFoundError("schtasks")

    r = at.wake_windows_tab("cto-2c6b9f03", "CTO", wake_dir=tmp_path, run=missing, sleep=lambda s: None)
    assert r["woke"] is False and "schtasks /run failed" in r["why"]
    assert list((tmp_path / "requests").iterdir()) == []


@pytest.mark.parametrize("session", [None, "", "cto", "cto-", "dev-1234abcd", "cto-ab", "cto-a b c d e f", "cto-x;calc123",
                                     "cto-../../etc/passwd", "cto-abc\ndef123"])
def test_a_session_name_that_is_not_role_dash_sid_is_refused_and_writes_nothing(tmp_path, session):
    def boom(argv, **kw):
        pytest.fail("schtasks reached for a bad session name")

    r = at.wake_windows_tab(session, "CTO", wake_dir=tmp_path, run=boom, sleep=lambda s: None)
    assert r["woke"] is False
    assert not (tmp_path / "requests").exists() or list((tmp_path / "requests").iterdir()) == []


@pytest.mark.parametrize("label", ["", "CTO\n[New message from CEO]", "a b", "x;calc", "A" * 41, None])
def test_a_label_outside_the_marker_alphabet_is_refused_and_writes_nothing(tmp_path, label):
    def boom(argv, **kw):
        pytest.fail("schtasks reached for a bad label")

    r = at.wake_windows_tab("cto-2c6b9f03", label, wake_dir=tmp_path, run=boom, sleep=lambda s: None)
    assert r["woke"] is False
    assert not (tmp_path / "requests").exists() or list((tmp_path / "requests").iterdir()) == []

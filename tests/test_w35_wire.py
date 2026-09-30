"""Org Mesh W3.5 wiring (task-49f70bc6): a C-level letter on Windows can wake the
session's tab, behind ORG_WIN_WAKE, which is OFF unless it is exactly "1".

The mechanism is tests/test_w35_wake.py's (agent_transport.wake_windows_tab).
This file pins only what node_dispatch does with it:

  flag unset or anything but "1"  -> today's `woke: False`, wake never called
  flag "1"                        -> wake called once, `woke` and `why` returned
  a wake that fails or raises     -> `woke: False`; the letter is still delivered
  worker letters (MAILBOX.md)     -> `woke: False`, never woken, flag or not
  POSIX                           -> the tmux wake, untouched, wake_windows_tab unused

Nothing here touches Task Scheduler, PowerShell, tmux or a real desktop: the
platform is faked at `node_dispatch._is_windows`, `wake_windows_tab` is a
recorder, and `subprocess.run` explodes.

Run:  .venv/bin/python -m pytest tests/test_w35_wire.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config as config_mod  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import mailbox  # noqa: E402
from tools import agent_transport, send_to_cxo, tmux_session  # noqa: E402
from tools import node_dispatch as nd  # noqa: E402

FLAG = "ORG_WIN_WAKE"


def _boom(*a, **kw):
    raise AssertionError("must not be reached")


class Wake:
    """agent_transport.wake_windows_tab, replaced. Records each call, and whether
    the letter was already on disk when it was made."""

    def __init__(self) -> None:
        self.calls: list[tuple[tuple, dict]] = []
        self.answer: object = {"woke": True, "why": "keys sent to the verified tab"}
        self.on_disk: list[int] = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))
        self.on_disk.append(len(mailbox.peek("cto", "abcd1234")))
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "tasks.db")
    db_mod.init()
    for var in ("CTO_SESSION_ID", "CXO_SESSION_ID", "CXO_ROLE",
                "SSH_ORIGINAL_COMMAND", "SSH_CLIENT", FLAG):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ORG_CHARTER_GATE", "off")
    monkeypatch.setattr(config_mod, "self_host", lambda: "winbox")
    monkeypatch.setattr(mailbox, "INBOX_ROOT", tmp_path / "inbox")
    locks = tmp_path / "locks"
    locks.mkdir()
    monkeypatch.setattr(send_to_cxo, "LOCKS_DIR", locks)
    monkeypatch.setattr(nd, "_worktrees_root", lambda: tmp_path / "worktrees")
    (tmp_path / "worktrees").mkdir()
    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(tmux_session, "has_session", _boom)
    monkeypatch.setattr(agent_transport, "attempt_wake", _boom)
    monkeypatch.setattr(send_to_cxo, "attempt_wake", _boom)


@pytest.fixture
def wake(monkeypatch) -> Wake:
    w = Wake()
    monkeypatch.setattr(agent_transport, "wake_windows_tab", w)
    return w


@pytest.fixture
def win(monkeypatch, tmp_path, wake):
    """This process is winbox, with a live cto-abcd1234 (lock file, live pid)."""
    monkeypatch.setattr(nd, "_is_windows", lambda: True)
    monkeypatch.setattr(nd.proc, "pid_alive", lambda pid: pid == 4242)
    (tmp_path / "locks" / "cto-abcd1234.lock").write_text("4242")
    return wake


def _letter(**kw) -> int:
    args = dict(to_session="abcd1234", from_role="cmo", from_session="1234abcd")
    args.update(kw)
    return db_mod.create_letter(args.pop("to_host", "winbox"), args.pop("to_role", "cto"),
                                args.pop("body", "hello"), **args)


def _deliver() -> tuple[dict, int]:
    return nd._run("deliver_letter", [str(_letter())])


def _delivered(out: dict) -> bool:
    return db_mod.get_letter(out["result"]["letter_id"])["status"] == "delivered"


# ---------------------------------------------------------------------------
# off: the default
# ---------------------------------------------------------------------------

def test_flag_unset_is_todays_answer_and_never_wakes(win):
    out, code = _deliver()
    assert code == 0, out
    assert out["result"] == {"letter_id": out["result"]["letter_id"], "delivered": True,
                             "to": "cto-abcd1234", "woke": False}
    assert win.calls == []
    assert [m["body"] for m in mailbox.peek("cto", "abcd1234")] == ["hello"]


@pytest.mark.parametrize("value", [
    "", "0", "true", "True", "yes", "on", "2", "01", "11", " 1", "1 ", "1\n", "\uff11", "one"])
def test_any_value_but_exactly_1_is_off(win, monkeypatch, value):
    monkeypatch.setenv(FLAG, value)
    out, code = _deliver()
    assert code == 0, out
    assert out["result"]["woke"] is False and "why" not in out["result"]
    assert win.calls == []


# ---------------------------------------------------------------------------
# on
# ---------------------------------------------------------------------------

def test_flag_1_wakes_once_with_the_session_and_the_upper_cased_sender(win, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    out, code = _deliver()
    assert code == 0, out
    assert win.calls == [(("cto-abcd1234", "CMO"), {})]
    assert out["result"]["woke"] is True
    assert out["result"]["why"] == "keys sent to the verified tab"
    assert out["result"]["to"] == "cto-abcd1234"
    assert _delivered(out)


def test_the_letter_is_on_disk_before_the_tab_is_touched(win, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    _deliver()
    assert win.on_disk == [1]


def test_a_wake_that_reports_failure_is_woke_false_with_its_reason_and_still_delivered(
        win, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    win.answer = {"woke": False, "why": "task MooniexOrgWake did not start (rc 1)"}
    out, code = _deliver()
    assert code == 0, out
    assert out["result"]["woke"] is False
    assert out["result"]["why"] == "task MooniexOrgWake did not start (rc 1)"
    assert _delivered(out)
    assert len(mailbox.peek("cto", "abcd1234")) == 1


@pytest.mark.parametrize("error", [RuntimeError("tab gone"), OSError(2, "no schtasks"),
                                   subprocess.TimeoutExpired("schtasks", 15), ValueError("x")])
def test_a_wake_that_raises_never_fails_the_delivery(win, monkeypatch, error):
    monkeypatch.setenv(FLAG, "1")
    win.answer = error
    out, code = _deliver()
    assert code == 0, out
    assert out["result"]["woke"] is False
    assert out["result"]["why"] == f"wake raised {type(error).__name__}"
    assert _delivered(out)
    row = db_mod.get_letter(out["result"]["letter_id"])
    assert row["status"] == "delivered" and not row.get("last_error")


@pytest.mark.parametrize("answer", [{}, {"why": "no woke key"}, {"woke": "yes"}, {"woke": 1},
                                    {"woke": None}])
def test_only_a_real_true_counts_as_woke(win, monkeypatch, answer):
    monkeypatch.setenv(FLAG, "1")
    win.answer = answer
    out, code = _deliver()
    assert code == 0, out
    assert out["result"]["woke"] is False


def test_a_credential_in_the_wake_reason_is_redacted_and_the_reason_is_bounded(win, monkeypatch):
    monkeypatch.setenv(FLAG, "1")
    token = "ghp_" + "A" * 36
    win.answer = {"woke": False, "why": f"wake.ps1 exit 1: {token} " + "x" * 2000}
    out, code = _deliver()
    assert code == 0, out
    assert token not in out["result"]["why"]
    assert len(out["result"]["why"]) <= nd.MAX_ERROR_CHARS


def test_a_session_that_is_not_live_is_refused_before_any_wake(win, monkeypatch, tmp_path):
    monkeypatch.setenv(FLAG, "1")
    (tmp_path / "locks" / "cto-abcd1234.lock").unlink()
    out, code = _deliver()
    assert code == 1 and "no live session cto-abcd1234" in out["error"]
    assert win.calls == []


# ---------------------------------------------------------------------------
# workers and POSIX are untouched
# ---------------------------------------------------------------------------

def test_a_worker_letter_on_windows_never_wakes_with_the_flag_on(win, monkeypatch, tmp_path):
    monkeypatch.setenv(FLAG, "1")
    tid = db_mod.create_task("projA", "developer", "t", "d")
    wt = tmp_path / "worktrees" / f"projA__developer__{tid}"
    wt.mkdir(parents=True)
    with db_mod.get_conn() as conn:
        conn.execute("UPDATE tasks SET host=?, status=?, worktree=? WHERE id=?",
                     ("winbox", "in_progress", str(wt), tid))
    lid = _letter(to_role="developer", to_session=tid, body="please push")
    out, code = nd._run("deliver_letter", [str(lid)])
    assert code == 0, out
    assert out["result"] == {"letter_id": lid, "delivered": True,
                             "to": f"developer-{tid}", "woke": False}
    assert win.calls == []
    assert "please push" in (wt / "MAILBOX.md").read_text(encoding="utf-8")


def test_on_posix_the_flag_changes_nothing_and_the_tmux_wake_is_the_one_used(
        wake, monkeypatch, tmp_path):
    monkeypatch.setenv(FLAG, "1")
    monkeypatch.setattr(nd, "_is_windows", lambda: False)
    monkeypatch.setattr(nd, "_clevel_session_live", lambda role, sid: True)
    woken = []
    monkeypatch.setattr(send_to_cxo, "attempt_wake", lambda *a, **kw: woken.append(a))
    out, code = _deliver()
    assert code == 0, out
    assert out["result"] == {"letter_id": out["result"]["letter_id"], "delivered": True,
                             "to": "cto-abcd1234"}  # no `woke` key on POSIX, as before
    assert woken == [("cto", "abcd1234", "CMO")]
    assert wake.calls == []

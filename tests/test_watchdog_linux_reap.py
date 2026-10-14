"""The watchdog closes finished workers on Linux too (session-steward case 1, 2026-10-14).

On Contabo four workers (wd-f7c291b6 done; wd-afe57b21, wd-5eb22787, wd-0bbb27f9 review)
stayed alive 5-11 h with the journal at `reaped=0 surface_reaped=0`. Two passes ran only
`if _mac_surfaces()`: the finished-DEV reap built no rows off a Mac, and
`sweep_terminal_surfaces` hit `if not mac: continue` before its pid/tmux probe. Only the
iTerm tab and the Chrome claim are Mac-only (close_dev skips both off Darwin).

No real tmux, db or kill: `subprocess.run` is a fake tmux that fails the test on any other
argv, `db.list_tasks` returns canned rows, and `close_dev` is a Mock. The screens are the
captures of a real Claude pane that tests/test_rename_service.py already holds (14 Oct).
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from runners import watchdog as w  # noqa: E402
from tools import worker_reap  # noqa: E402

from test_rename_service import BUSY, DRAFT, EMPTY, PERMISSION  # noqa: E402

TID = "task-f7c291b6"
WD = "wd-f7c291b6"
REAP_RESULT = {"pid_matched": True, "signal": "SIGTERM", "tmux_killed": True,
               "closed_tab": False, "chrome_tabs_closed": [], "refused": None}


def row(tid: str = TID, status: str = "review", pid: int | None = 4242,
        minutes: float = 61, **extra) -> dict:
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    return {"id": tid, "status": status, "pid": pid, "host": None,
            "dispatcher_host": None, "tmux_session": None,
            "updated_at": stamp.isoformat(timespec="seconds"), **extra}


class FakeTmux:
    """Root's tmux server. `panes` maps a session name to the screen its pane shows, or
    to None (capture-pane exits 1) or an Exception (the call raises). A tmux call this
    fake does not know is recorded in `bad`; the fixture fails the test on it, because
    the code under test swallows exceptions and would hide it."""

    def __init__(self, panes: dict):
        self.panes, self.calls, self.bad = panes, [], []

    def run(self, argv, **kw):
        argv = list(argv)
        self.calls.append(argv)
        if argv[0] != "tmux" or len(argv) < 2:
            self.bad.append(argv)
            return subprocess.CompletedProcess(argv, 1, "", "")
        if argv[1] == "list-sessions":
            return subprocess.CompletedProcess(argv, 0, "".join(f"{n}\n" for n in self.panes), "")
        if argv[1] == "capture-pane" and "-t" in argv:
            screen = self.panes.get(argv[argv.index("-t") + 1])
            if isinstance(screen, Exception):
                raise screen
            if screen is None:
                return subprocess.CompletedProcess(argv, 1, "", "can't find session")
            return subprocess.CompletedProcess(argv, 0, screen, "")
        self.bad.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "")

    @property
    def captures(self) -> list[list[str]]:
        return [c for c in self.calls if c[1:2] == ["capture-pane"]]


@pytest.fixture
def env(monkeypatch):
    """A Linux box: canned rows by status, a fake tmux, close_dev and every log call mocked."""
    state = {"rows": [], "pid_alive": True}
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(worker_reap, "self_host", lambda: "contabo")
    monkeypatch.setattr(w.db, "list_tasks", lambda status=None, limit=100, **kw:
                        [r for r in state["rows"] if r["status"] == status])
    monkeypatch.setattr(w, "_pid_alive", lambda pid: state["pid_alive"])
    monkeypatch.setattr(w, "close_dev", Mock(return_value=dict(REAP_RESULT)))
    monkeypatch.setattr(w.db, "set_fields", Mock())
    for name in ("info", "warn", "error", "success"):
        monkeypatch.setattr(w, name, Mock())
    # The macOS-only surfaces: none may be touched off a Mac (and each is a spy on a Mac).
    for name, ret in (("_live_task_tab_ids", set()), ("_log_unclaimed_org_tabs", None),
                      ("_close_tab", False)):
        monkeypatch.setattr(w, name, Mock(return_value=ret))
    monkeypatch.setattr("scripts.browser.tab_registry.all_claims", Mock(return_value={}))

    def install(panes: dict) -> FakeTmux:
        tmux = FakeTmux(panes)
        monkeypatch.setattr(subprocess, "run", tmux.run)
        state["tmux"] = tmux
        return tmux

    state["install"] = install
    yield state
    if "tmux" in state:
        assert not state["tmux"].bad, f"unexpected tmux call(s): {state['tmux'].bad}"


def reap(env, **kw):
    """Run the third pass on the canned rows; return (results, tmux)."""
    tmux = env["install"](kw.pop("panes", {WD: EMPTY}))
    return w._reap_finished_workers(), tmux


# -- the third pass: finished DEV, local row ----------------------------------

@pytest.mark.parametrize("status", ["review", "done"])
def test_idle_prompt_after_the_floor_is_closed(env, status):
    env["rows"] = [row(status=status, minutes=61)]
    out, tmux = reap(env)
    w.close_dev.assert_called_once_with(TID, reason="watchdog: no C-level decision in 60 min")
    assert [r["task"] for r in out] == [TID] and out[0]["tmux_killed"] is True
    assert [c[-1] for c in tmux.captures] == [WD]


@pytest.mark.parametrize("screen", [
    pytest.param(BUSY, id="a-turn-is-running"),
    pytest.param(PERMISSION, id="a-choice-prompt-is-waiting"),
    pytest.param("", id="nothing-on-screen"),
    pytest.param("Last login: Tue\nroot@contabo:~# ", id="a-shell-not-a-claude-prompt"),
])
def test_a_pane_not_proven_idle_is_left_alone(env, screen):
    env["rows"] = [row(minutes=300)]
    out, tmux = reap(env, panes={WD: screen})
    assert out == [] and not w.close_dev.called
    assert len(tmux.captures) == 1


def test_a_draft_in_the_input_box_does_not_hold_the_close(env):
    """Spec: only busy / waiting block (lib.pane_screen.prompt_ready would also block a draft)."""
    env["rows"] = [row(minutes=61)]
    out, _ = reap(env, panes={WD: DRAFT})
    assert len(out) == 1 and w.close_dev.call_count == 1


def test_59_minutes_is_under_the_floor(env):
    env["rows"] = [row(minutes=59)]
    out, tmux = reap(env)
    assert out == [] and not w.close_dev.called
    assert tmux.captures == [], "no pane is read before the floor has passed"


@pytest.mark.parametrize("fail", [None, subprocess.TimeoutExpired("tmux", 5), OSError("no tmux")],
                         ids=["exit-1", "timeout", "oserror"])
def test_a_capture_that_fails_means_skip(env, fail):
    env["rows"] = [row(minutes=300)]
    out, tmux = reap(env, panes={WD: fail})
    assert out == [] and not w.close_dev.called
    assert len(tmux.captures) == 1


def test_a_dead_pid_is_not_this_passs_job(env):
    env["rows"], env["pid_alive"] = [row(minutes=300)], False
    out, tmux = reap(env)
    assert out == [] and not w.close_dev.called and tmux.captures == []


def test_another_boxs_row_is_never_touched(env):
    env["rows"] = [row(minutes=300, host="winbox", dispatcher_host="winbox")]
    out, tmux = reap(env)
    assert out == [] and not w.close_dev.called and tmux.captures == []


def test_the_recorded_session_name_is_read_when_it_is_not_wd(env):
    """A row spawned by the remote launcher records `mooniex-task-<id>`, not `wd-<id>`."""
    env["rows"] = [row(minutes=61, tmux_session="mooniex-task-f7c291b6")]
    out, tmux = reap(env, panes={"mooniex-task-f7c291b6": EMPTY})
    assert len(out) == 1 and [c[-1] for c in tmux.captures] == ["mooniex-task-f7c291b6"]


def test_the_wd_session_is_read_when_the_recorded_one_is_gone(env):
    env["rows"] = [row(minutes=61, tmux_session="mooniex-task-f7c291b6")]
    out, tmux = reap(env, panes={WD: EMPTY})
    assert len(out) == 1
    assert [c[-1] for c in tmux.captures] == ["mooniex-task-f7c291b6", WD]


def test_scan_once_runs_the_pass_on_linux(env, monkeypatch):
    """The regression itself: reaped was always [] off a Mac."""
    env["rows"] = [row(minutes=61)]
    env["install"]({WD: EMPTY})
    monkeypatch.setattr(w, "gc_stale_tasks", Mock(return_value=[]))
    monkeypatch.setattr(w, "sweep_terminal_surfaces", Mock(return_value=[]))
    for name, ret in (("_drain_disk_queue", None), ("_retry_queued_remote", []),
                      ("_retry_letters", []), ("_provision_identities", []),
                      ("_probe_mesh_hosts", {})):
        monkeypatch.setattr(w, name, Mock(return_value=ret))
    monkeypatch.setattr(w.work_watch, "watch", Mock(return_value={}))
    monkeypatch.delenv("ORG_WATCHDOG_BRANCH_POLL", raising=False)
    out = w.scan_once()
    assert [r["task"] for r in out["reaped"]] == [TID]
    w.close_dev.assert_called_once()


def test_on_a_mac_the_pass_is_as_before_with_no_pane_read(env, monkeypatch):
    env["rows"] = [row(minutes=61)]
    tmux = env["install"]({})
    monkeypatch.setattr(sys, "platform", "darwin")
    out = w._reap_finished_workers()
    assert [r["task"] for r in out] == [TID] and w.close_dev.call_count == 1
    assert tmux.calls == [], "the Mac path never reads a pane"


# -- the terminal-surface sweep: local row ------------------------------------

def sweep(env, panes):
    tmux = env["install"](panes)
    return w.sweep_terminal_surfaces(), tmux


def test_sweep_closes_a_done_row_whose_wd_session_outlived_its_pid(env):
    env["rows"], env["pid_alive"] = [row(status="done", pid=None, minutes=10)], False
    out, _ = sweep(env, {WD: EMPTY})
    w.close_dev.assert_called_once_with(TID, reason="reaper: terminal status with live surface")
    assert out[0]["task"] == TID and out[0]["tmux_alive"] is True and out[0]["pid_alive"] is False
    assert out[0]["tab_open"] is False and out[0]["tab_claimed"] is False


def test_sweep_closes_a_row_whose_recorded_session_is_not_wd(env):
    env["rows"], env["pid_alive"] = [row(status="failed", pid=None, minutes=10,
                                         tmux_session="mooniex-task-f7c291b6")], False
    out, _ = sweep(env, {"mooniex-task-f7c291b6": EMPTY})
    assert [r["task"] for r in out] == [TID]


def test_sweep_closes_a_terminal_row_with_a_live_pid_and_no_session(env):
    env["rows"], env["pid_alive"] = [row(status="cancelled", minutes=10)], True
    out, _ = sweep(env, {})
    assert out[0]["pid_alive"] is True and out[0]["tmux_alive"] is False


def test_sweep_leaves_a_row_with_nothing_alive(env):
    env["rows"], env["pid_alive"] = [row(status="done", pid=None, minutes=10)], False
    out, _ = sweep(env, {"cto-c34459eb": EMPTY})
    assert out == [] and not w.close_dev.called


def test_sweep_respects_the_grace_period(env):
    env["rows"] = [row(status="done", pid=None, minutes=2)]
    out, _ = sweep(env, {WD: EMPTY})
    assert out == [] and not w.close_dev.called


def test_sweep_skips_review_and_in_progress(env):
    env["rows"] = [row(status="review", minutes=300), row("task-aabbccdd", "in_progress", minutes=300)]
    out, _ = sweep(env, {WD: EMPTY, "wd-aabbccdd": EMPTY})
    assert out == [] and not w.close_dev.called


def test_sweep_off_a_mac_never_reaches_for_a_tab(env):
    env["rows"] = [row(status="done", minutes=10)]
    sweep(env, {WD: EMPTY})
    for spied in (w._live_task_tab_ids, w._log_unclaimed_org_tabs, w._close_tab):
        assert not spied.called
    from scripts.browser import tab_registry
    assert not tab_registry.all_claims.called


def test_sweep_on_a_mac_still_asks_for_tabs_and_claims(env, monkeypatch):
    """Darwin is unchanged: a row whose only live surface is a tab or a claim is closed."""
    env["rows"] = [row(status="failed", pid=None, minutes=10),
                   row("task-0a0a0a0a", "done", pid=None, minutes=10)]
    env["pid_alive"] = False
    w._live_task_tab_ids.return_value = {TID}
    from scripts.browser import tab_registry
    tab_registry.all_claims.return_value = {"9": "task-0a0a0a0a"}
    monkeypatch.setattr(sys, "platform", "darwin")
    out, _ = sweep(env, {})
    assert {r["task"] for r in out} == {TID, "task-0a0a0a0a"}
    assert w._live_task_tab_ids.called and w._log_unclaimed_org_tabs.called
    by_task = {r["task"]: r for r in out}
    assert by_task[TID]["tab_open"] is True and by_task["task-0a0a0a0a"]["tab_claimed"] is True


# -- close_dev off a Mac -------------------------------------------------------

def test_close_dev_survives_a_chrome_claim_when_there_is_no_osascript(monkeypatch):
    """close_dev, unstubbed, on Linux: no iTerm step, the Chrome step finds no osascript,
    and the tmux step has already run. Nothing raises."""
    from scripts.browser import tab_registry
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(worker_reap.db, "get_task", lambda tid: {
        "id": tid, "status": "review", "pid": None, "tmux_session": WD, "ttyd_pid": None})
    monkeypatch.setattr(worker_reap, "_cleanup_tmux_ttyd", lambda task: {"tmux_killed": True})
    monkeypatch.setattr(tab_registry, "tabs_for", lambda tid: [{"tab_id": "123"}])
    clear = Mock()
    monkeypatch.setattr(tab_registry, "clear", clear)

    def no_osascript(argv, **kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    monkeypatch.setattr(subprocess, "run", no_osascript)
    monkeypatch.setattr(worker_reap, "warn", Mock())
    monkeypatch.setattr(worker_reap, "info", Mock())
    r = worker_reap.close_dev(TID, reason="test")
    assert r["refused"] is None and r["tmux_killed"] is True
    assert r["closed_tab"] is False and r["chrome_tabs_closed"] == []
    assert not clear.called, "a claim that could not be closed is kept, not dropped"

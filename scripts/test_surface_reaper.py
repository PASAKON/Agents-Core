"""Tests for the terminal-surface reaper (task-92118d4e, CEO rule
2026-09-07: "closing a worker means closing its window too") plus its two
CTO addenda.

Covers:
  runners/watchdog.py:sweep_terminal_surfaces() (ADDENDUM 2 grace period,
    'stalled' excluded, Chrome-tab-claim signal, unclaimed-org-tab logging)
  runners/watchdog.py:_live_org_chrome_tabs() / _log_unclaimed_org_tabs()
  tools/worker_reap.py:close_dev()'s no-pid path (now total, not refused)
    and its Chrome-tab-claim integration (ADDENDUM 1)
  tools/worker_reap.py:_close_chrome_tabs() / close_remote() (re-reads the
    task and refuses on a non-terminal status, ADDENDUM 2)

No live processes, no real tmux server, no real iTerm, no real Chrome:
`_pid_alive`, `_live_tmux_sessions`, `_live_task_tab_ids`, `_chrome_running`
and `close_dev` are stubbed for the sweep tests; `scripts.browser.
tab_registry.all_claims` and `_log_unclaimed_org_tabs` are stubbed in every
sweep test so a real (and possibly non-empty, shared-across-the-org) claim
registry or a real Chrome never gets touched; `close_tab` and
tmux_session.kill are stubbed for the close_dev no-pid test; `subprocess.run`
is stubbed for the close_remote and Chrome-tab tests (no real SSH/osascript).

Tests:
  1. terminal-status task with a live fake tmux session gets closed
  2. terminal-status task with an open fake tab (no pid, no tmux) gets closed
  3. in_progress task is never scanned/touched even with a live fake surface
  4. idempotent: second sweep on an already-reaped task is a no-op (no
     close_dev call, empty result)
  5. close_dev's no-pid path still kills tmux and closes the tab by title
  6. close_remote renders the right ssh command per host (winbox/contabo),
     refuses on host=None/mac/unknown, refuses a non-terminal status, and
     skips cleanly when the `host` column doesn't exist yet (task.get("host")
     on a plain dict)
  7. TERMINAL_SURFACE_STATUSES is exactly {done, merged, failed, cancelled,
     reverted} in both modules — 'stalled' is excluded (ADDENDUM 2)
  8. REAP_GRACE_S: a terminal task younger than the grace period is
     untouched; older, it is reaped (ADDENDUM 2)
  9. rate_limited (an active status) is never swept even with a live tab
  10. a Chrome-tab claim alone (no pid/tmux/iTerm-tab) is enough to trigger
      close_dev (ADDENDUM 1)
  11. an unclaimed org-domain Chrome tab is logged, never closed
  12. close_dev closes every Chrome tab the task claimed and clears the
      claim; a task with no claim never touches Chrome at all

Run via: python scripts/test_surface_reaper.py
"""
from __future__ import annotations

import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod  # noqa: E402
import tools.worker_reap as worker_reap  # noqa: E402
import runners.watchdog as watchdog  # noqa: E402
from tools import tmux_session  # noqa: E402

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _ts(delta_minutes: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)
    return dt.isoformat(timespec="seconds")


def _insert_task(*, status: str, pid: int | None = None,
                 tmux_session_name: str | None = None,
                 host: str | None = None,
                 age_minutes: float = 0,
                 project: str = "test-proj") -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = _ts(age_minutes)
    with db_mod.get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description, pid,
                tmux_session, host, depends_on, touches, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, project, "developer", status, "t", "d", pid,
             tmux_session_name, host, "[]", "[]", ts, ts),
        )
    return tid


# No-op stand-ins so a sweep test never reads the real (shared, possibly
# non-empty) browser-tabs registry or shells out to real Chrome/osascript.
_NO_CLAIMS = mock.patch("scripts.browser.tab_registry.all_claims",
                        mock.Mock(return_value={}))


# ---------------------------------------------------------------------------
# sweep_terminal_surfaces (1-4)
# ---------------------------------------------------------------------------

def test_sweep_closes_terminal_task_with_live_tmux() -> bool:
    tid = _insert_task(status="done", pid=None, age_minutes=10)
    session = tmux_session.session_name_for(tid)
    fake_close_dev = mock.Mock(return_value={
        "task_id": tid, "closed_tab": True, "pid": None, "pid_matched": False,
        "signal": None, "tmux_killed": True, "ttyd_killed": False,
        "reason": "reaper: terminal status with live surface", "refused": None,
        "found": {"pid": False, "tmux": True, "ttyd": False},
        "chrome_tabs_closed": [],
    })
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value={session})), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return (tid in ids and fake_close_dev.call_count == 1
           and fake_close_dev.call_args.kwargs.get("reason", "").startswith("reaper:"))


def test_sweep_closes_terminal_task_with_open_tab() -> bool:
    # status="failed", not "stalled": ADDENDUM 2 removed 'stalled' from the
    # terminal-surface set entirely — a stalled task is a suspicion, never
    # auto-swept. 'failed' keeps this test's original open-tab coverage.
    tid = _insert_task(status="failed", pid=None, age_minutes=10)
    fake_close_dev = mock.Mock(return_value={
        "task_id": tid, "closed_tab": True, "pid": None, "pid_matched": False,
        "signal": None, "tmux_killed": False, "ttyd_killed": False,
        "reason": "reaper: terminal status with live surface", "refused": None,
        "found": {"pid": False, "tmux": False, "ttyd": False},
        "chrome_tabs_closed": [],
    })
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value={tid})), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid in ids and fake_close_dev.call_count == 1


def test_sweep_ignores_in_progress() -> bool:
    """An in_progress task must never even be scanned, let alone reaped —
    even though its own tmux session/tab look live (it's supposed to be
    working). _pid_alive stays False here (not blanket-True): earlier tests
    in this run share one accumulating temp DB, and a blanket-True
    _pid_alive would also match their leftover terminal-status rows (pid is
    NULL on all of them) and reap those through the unmocked close_dev —
    the status filter is what this test is isolating, not pid detection."""
    tid = _insert_task(status="in_progress", pid=None)
    session = tmux_session.session_name_for(tid)
    fake_close_dev = mock.Mock()
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value={session})), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value={tid})), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid not in ids and fake_close_dev.call_count == 0


def test_sweep_idempotent_second_run() -> bool:
    tid = _insert_task(status="cancelled", pid=None, age_minutes=10)
    session = tmux_session.session_name_for(tid)
    alive = {"tmux": True}

    def fake_close_dev(task_id, *, reason):
        alive["tmux"] = False
        return {"task_id": task_id, "closed_tab": False, "pid": None,
                "pid_matched": False, "signal": None, "tmux_killed": True,
                "ttyd_killed": False, "reason": reason, "refused": None,
                "found": {"pid": False, "tmux": True, "ttyd": False},
                "chrome_tabs_closed": []}

    def fake_live_tmux():
        return {session} if alive["tmux"] else set()

    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", side_effect=fake_live_tmux), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", side_effect=fake_close_dev) as spy:
        first = watchdog.sweep_terminal_surfaces()
        second = watchdog.sweep_terminal_surfaces()
    return (len(first) == 1 and first[0]["task"] == tid
           and len(second) == 0 and spy.call_count == 1)


# ---------------------------------------------------------------------------
# close_dev: no-pid path is now total (5)
# ---------------------------------------------------------------------------

def test_close_dev_no_pid_still_closes_tmux_and_tab() -> bool:
    tid = _insert_task(status="done", pid=None, tmux_session_name="wd-fake")
    fake_close_tab = mock.Mock(return_value=True)
    with mock.patch.object(worker_reap, "close_tab", fake_close_tab), \
         mock.patch("tools.tmux_session.kill", mock.Mock(return_value=True)):
        r = worker_reap.close_dev(tid, reason="test")
    return (r["refused"] is None and r["pid"] is None and r["signal"] is None
           and r["found"]["pid"] is False and r["found"]["tmux"] is True
           and r["tmux_killed"] is True and r["closed_tab"] is True
           and fake_close_tab.call_args.kwargs.get("allow_pid") is False)


# ---------------------------------------------------------------------------
# close_remote (6)
# ---------------------------------------------------------------------------

def test_remote_command_rendering_winbox() -> bool:
    cmd = worker_reap._remote_kill_command("task-abc12345", 4242, "windows")
    return cmd == ["taskkill", "/PID", "4242", "/T", "/F"]


def test_remote_command_rendering_contabo() -> bool:
    cmd = worker_reap._remote_kill_command("task-abc12345", 4242, "linux")
    return (cmd[:2] == ["bash", "-lc"]
           and "tmux kill-session -t wd-abc12345" in cmd[2]
           and "kill 4242" in cmd[2])


def test_close_remote_winbox_ssh_command() -> bool:
    tid = _insert_task(status="done", pid=4242, host="winbox")
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run):
        r = worker_reap.close_remote({"id": tid})
    return (r["refused"] is None and r["ssh_ok"] is True
           and r["command"] == ["ssh", "winbox", "taskkill", "/PID", "4242", "/T", "/F"])


def test_close_remote_contabo_ssh_command() -> bool:
    tid = _insert_task(status="done", pid=4242, host="contabo")
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run):
        r = worker_reap.close_remote({"id": tid})
    return (r["refused"] is None and r["ssh_ok"] is True
           and r["command"][:2] == ["ssh", "mooniex-vps"])


def test_close_remote_refuses_local_or_unknown_host() -> bool:
    tid_none = _insert_task(status="done", pid=1, host=None)
    tid_mac = _insert_task(status="done", pid=1, host="mac")
    tid_unknown = _insert_task(status="done", pid=1, host="moon")
    r_none = worker_reap.close_remote({"id": tid_none})
    r_mac = worker_reap.close_remote({"id": tid_mac})
    r_unknown = worker_reap.close_remote({"id": tid_unknown})
    return (r_none["refused"] is not None and r_mac["refused"] is not None
           and r_unknown["refused"] is not None)


def test_close_remote_refuses_non_terminal_status() -> bool:
    """ADDENDUM 2: close_remote re-reads the task from the DB and refuses
    unless its (freshly-read) status is in the terminal set — a caller
    holding a stale dict must never be able to remote-kill a task that has
    since gone back active."""
    tid = _insert_task(status="in_progress", pid=4242, host="winbox")
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run):
        r = worker_reap.close_remote({"id": tid})
    return (r["refused"] is not None and "not terminal" in r["refused"]
           and fake_run.call_count == 0)


def test_close_remote_missing_host_column_is_a_plain_skip() -> bool:
    """A task dict from a pre-migration DB has no 'host' key at all —
    .get('host') must return None, not raise, exactly per the deliverable's
    guard (task.get("host") and skip). This id has no DB row at all, so the
    re-read fails and close_remote falls back to the passed-in dict — the
    fallback path is exercised here, not just the normal re-read one."""
    task_without_host_key = {"id": "task-nonexistent0", "pid": 1, "status": "done"}
    assert "host" not in task_without_host_key
    r = worker_reap.close_remote(task_without_host_key)
    return r["refused"] is not None and r["host"] is None


# ---------------------------------------------------------------------------
# TERMINAL_SURFACE_STATUSES exact set (7)
# ---------------------------------------------------------------------------

def test_terminal_surface_statuses_exact_set() -> bool:
    """ADDENDUM 2, CEO rule: exactly {done, merged, failed, cancelled,
    reverted} — 'stalled' excluded — in both modules that define it."""
    expected = {"done", "merged", "failed", "cancelled", "reverted"}
    return (set(watchdog.TERMINAL_SURFACE_STATUSES) == expected
           and set(worker_reap._TERMINAL_SURFACE_STATUSES) == expected)


# ---------------------------------------------------------------------------
# REAP_GRACE_S (8) and rate_limited exclusion (9)
# ---------------------------------------------------------------------------

def test_sweep_respects_grace_period() -> bool:
    tid = _insert_task(status="done", pid=None, age_minutes=2)
    session = tmux_session.session_name_for(tid)
    fake_close_dev = mock.Mock()
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value={session})), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid not in ids and fake_close_dev.call_count == 0


def test_sweep_reaps_after_grace_period() -> bool:
    tid = _insert_task(status="done", pid=None, age_minutes=6)
    session = tmux_session.session_name_for(tid)
    fake_close_dev = mock.Mock(return_value={
        "task_id": tid, "closed_tab": False, "pid": None, "pid_matched": False,
        "signal": None, "tmux_killed": True, "ttyd_killed": False,
        "reason": "reaper: terminal status with live surface", "refused": None,
        "found": {"pid": False, "tmux": True, "ttyd": False},
        "chrome_tabs_closed": [],
    })
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value={session})), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid in ids and fake_close_dev.call_count == 1


def test_sweep_ignores_rate_limited_with_tab() -> bool:
    tid = _insert_task(status="rate_limited", pid=None, age_minutes=10)
    fake_close_dev = mock.Mock()
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value={tid})), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid not in ids and fake_close_dev.call_count == 0


# ---------------------------------------------------------------------------
# ADDENDUM 1 — Chrome tabs are a surface too (10-12)
# ---------------------------------------------------------------------------

def test_sweep_reaps_via_chrome_tab_claim_alone() -> bool:
    """No pid, no tmux, no iTerm tab — only a Chrome-tab claim. That alone
    must be enough for the sweep to call close_dev (which itself closes the
    claimed tab and clears the claim)."""
    tid = _insert_task(status="done", pid=None, age_minutes=10)
    fake_close_dev = mock.Mock(return_value={
        "task_id": tid, "closed_tab": False, "pid": None, "pid_matched": False,
        "signal": None, "tmux_killed": False, "ttyd_killed": False,
        "reason": "reaper: terminal status with live surface", "refused": None,
        "found": {"pid": False, "tmux": False, "ttyd": False},
        "chrome_tabs_closed": ["999"],
    })
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         mock.patch("scripts.browser.tab_registry.all_claims",
                    mock.Mock(return_value={"999": tid})), \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return (tid in ids and fake_close_dev.call_count == 1
           and any(r.get("tab_claimed") for r in out if r["task"] == tid))


def test_log_unclaimed_org_tabs_logs_only_unclaimed() -> bool:
    logged: list[str] = []
    with mock.patch.object(watchdog, "_live_org_chrome_tabs", mock.Mock(return_value=[
             ("1", "https://higgsfield.ai/a"), ("2", "https://higgsfield.ai/b")])), \
         mock.patch.object(watchdog, "warn", side_effect=lambda m: logged.append(m)):
        watchdog._log_unclaimed_org_tabs({"1"})
    return len(logged) == 1 and "unclaimed org tab: 2" in logged[0]


def test_live_org_chrome_tabs_skips_when_chrome_not_running() -> bool:
    with mock.patch.object(watchdog, "_chrome_running", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog.subprocess, "run") as run_spy:
        out = watchdog._live_org_chrome_tabs()
    return out == [] and run_spy.call_count == 0


def test_live_org_chrome_tabs_filters_by_domain() -> bool:
    fake_run = mock.Mock(return_value=mock.Mock(
        returncode=0,
        stdout="1\thttps://higgsfield.ai/x\n2\thttps://example.com/y\n"
               "3\thttps://flow.google.com/z\n"))
    with mock.patch.object(watchdog, "_chrome_running", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog.subprocess, "run", fake_run):
        out = watchdog._live_org_chrome_tabs()
    return {tid for tid, _ in out} == {"1", "3"}


def test_close_chrome_tabs_skips_when_chrome_not_running() -> bool:
    with mock.patch.object(worker_reap, "_chrome_running", mock.Mock(return_value=False)), \
         mock.patch.object(worker_reap.subprocess, "run") as run_spy:
        closed = worker_reap._close_chrome_tabs([111, 222])
    return closed == [] and run_spy.call_count == 0


def test_close_chrome_tabs_builds_ids_and_parses_output() -> bool:
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stdout="111,222"))
    with mock.patch.object(worker_reap, "_chrome_running", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap.subprocess, "run", fake_run):
        closed = worker_reap._close_chrome_tabs(["111", "222"])
    script = fake_run.call_args[0][0][2]
    # Ids are quoted string literals in the script, not bare numbers: Chrome's
    # own `id of tab` is AppleScript class text (confirmed live, task-92118d4e)
    # — a bare-number list silently matches nothing.
    return (closed == ["111", "222"] and '"111", "222"' in script
           and 'tell application "Google Chrome"' in script)


def test_close_dev_closes_claimed_chrome_tabs_and_clears_registry() -> bool:
    tid = _insert_task(status="done", pid=None)
    from scripts.browser.tab_registry import cmd_claim, tabs_for
    cmd_claim(tid, "424242", "https://higgsfield.ai/gen")
    fake_close_chrome = mock.Mock(return_value=["424242"])
    with mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=False)), \
         mock.patch("tools.tmux_session.kill", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap, "_close_chrome_tabs", fake_close_chrome):
        r = worker_reap.close_dev(tid, reason="test")
    still_claimed = tabs_for(tid)
    return (r["chrome_tabs_closed"] == ["424242"] and fake_close_chrome.call_count == 1
           and still_claimed == [])


def test_close_dev_no_claim_never_touches_chrome() -> bool:
    tid = _insert_task(status="done", pid=None)
    fake_close_chrome = mock.Mock(return_value=[])
    with mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=False)), \
         mock.patch("tools.tmux_session.kill", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap, "_close_chrome_tabs", fake_close_chrome):
        r = worker_reap.close_dev(tid, reason="test")
    return r["chrome_tabs_closed"] == [] and fake_close_chrome.call_count == 0


# ---------------------------------------------------------------------------
# sweep_terminal_surfaces: remote pass (GAP 1, task-59780ac3). Before this
# fix, a winbox/contabo task in a terminal status was skipped by the sweep
# entirely (host not in (None, 'mac') -> continue).
# ---------------------------------------------------------------------------

def test_sweep_reaps_terminal_remote_task_via_close_remote() -> bool:
    """Must now reach close_remote for real — only the ssh layer
    (subprocess.run) is stubbed here — and the ssh command must carry the
    task's recorded pid.

    `subprocess.run` is patched at module level, so it also intercepts
    lib.notify's own desktop-notification call fired by the sweep's
    SURFACE-REAPED log line — pick out the ssh call specifically rather
    than assuming it's the only (or the last) call recorded.
    """
    tid = _insert_task(status="done", pid=4242, host="winbox", age_minutes=10)
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run), \
         mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS:
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    ssh_calls = [c for c in fake_run.call_args_list if c.args and c.args[0][:1] == ["ssh"]]
    return (tid in ids and len(ssh_calls) == 1
           and ssh_calls[0].args[0] == ["ssh", "winbox", "taskkill", "/PID", "4242", "/T", "/F"])


def test_sweep_remote_respects_grace_period() -> bool:
    tid = _insert_task(status="done", pid=4242, host="winbox", age_minutes=1)
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run), \
         mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS:
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid not in ids and fake_run.call_count == 0


def test_sweep_remote_no_pid_is_silent_noop() -> bool:
    """No pid ever recorded on a winbox task -> close_remote refuses before
    ever building an ssh command; the sweep must not log/count it, matching
    the local branch's "no live surface, no log line" behaviour."""
    tid = _insert_task(status="done", pid=None, host="winbox", age_minutes=10)
    fake_run = mock.Mock()
    with mock.patch.object(worker_reap.subprocess, "run", fake_run), \
         mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS:
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid not in ids and fake_run.call_count == 0


def test_sweep_local_task_never_touches_close_remote() -> bool:
    """LOCAL (mac) task must be unaffected by GAP 1's new remote path —
    close_remote must never be called for it. Checked by id, not a global
    call count: this file's tests share one accumulating temp DB, and a
    leftover winbox row from an earlier test legitimately reaches
    close_remote on this same sweep tick too — that is correct for it, not
    a leak in this test."""
    tid = _insert_task(status="done", pid=None, host=None, age_minutes=10)
    session = tmux_session.session_name_for(tid)
    seen_ids: list[str] = []

    def spy_close_remote(t, **kwargs):
        seen_ids.append(t.get("id"))
        return {"command": None, "ssh_ok": None, "refused": "test stub"}

    fake_close_dev = mock.Mock(return_value={
        "task_id": tid, "closed_tab": False, "pid": None, "pid_matched": False,
        "signal": None, "tmux_killed": True, "ttyd_killed": False,
        "reason": "reaper: terminal status with live surface", "refused": None,
        "found": {"pid": False, "tmux": True, "ttyd": False},
        "chrome_tabs_closed": [],
    })
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_live_tmux_sessions", mock.Mock(return_value={session})), \
         mock.patch.object(watchdog, "_live_task_tab_ids", mock.Mock(return_value=set())), \
         mock.patch.object(watchdog, "_log_unclaimed_org_tabs", mock.Mock()), \
         _NO_CLAIMS, \
         mock.patch.object(watchdog, "close_remote", side_effect=spy_close_remote), \
         mock.patch.object(watchdog, "close_dev", fake_close_dev):
        out = watchdog.sweep_terminal_surfaces()
    ids = {r["task"] for r in out}
    return tid in ids and tid not in seen_ids and fake_close_dev.call_count == 1


# ---------------------------------------------------------------------------
# close_remote: allow_review opt-in (GAP 2 plumbing, task-59780ac3)
# ---------------------------------------------------------------------------

def test_close_remote_allow_review_opt_in() -> bool:
    """Default (allow_review=False) still refuses status='review' exactly
    like before; passing allow_review=True accepts it, and every other
    guard (host/pid) still applies regardless."""
    tid = _insert_task(status="review", pid=4242, host="winbox")
    r_default = worker_reap.close_remote({"id": tid})
    fake_run = mock.Mock(return_value=mock.Mock(returncode=0, stderr=""))
    with mock.patch.object(worker_reap.subprocess, "run", fake_run):
        r_allowed = worker_reap.close_remote({"id": tid}, allow_review=True)
    return (r_default["refused"] is not None and "not terminal" in r_default["refused"]
           and r_allowed["refused"] is None and r_allowed["ssh_ok"] is True)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="surface-reaper-")
    db_mod.DB_PATH = Path(tmp) / "tasks.db"
    db_mod.init()

    print("== sweep_terminal_surfaces ==")
    _mark(test_sweep_closes_terminal_task_with_live_tmux(),
          "closes a terminal task with a live fake tmux session")
    _mark(test_sweep_closes_terminal_task_with_open_tab(),
          "closes a terminal task with an open fake tab (no pid, no tmux)")
    _mark(test_sweep_ignores_in_progress(),
          "never touches an in_progress task even with a live fake surface")
    _mark(test_sweep_idempotent_second_run(),
          "idempotent: second sweep on an already-reaped task is a no-op")

    print("== close_dev: no-pid path is total ==")
    _mark(test_close_dev_no_pid_still_closes_tmux_and_tab(),
          "no-pid task still gets tmux killed and tab closed by title")

    print("== close_remote ==")
    _mark(test_remote_command_rendering_winbox(), "renders taskkill for winbox")
    _mark(test_remote_command_rendering_contabo(), "renders tmux+kill for contabo")
    _mark(test_close_remote_winbox_ssh_command(), "close_remote builds the winbox ssh command")
    _mark(test_close_remote_contabo_ssh_command(), "close_remote builds the contabo ssh command")
    _mark(test_close_remote_refuses_local_or_unknown_host(),
          "refuses host=None/mac/unknown")
    _mark(test_close_remote_refuses_non_terminal_status(),
          "refuses a re-read in_progress status")
    _mark(test_close_remote_missing_host_column_is_a_plain_skip(),
          "missing 'host' key (pre-migration schema) is a clean skip, not a raise")

    print("== TERMINAL_SURFACE_STATUSES ==")
    _mark(test_terminal_surface_statuses_exact_set(),
          "exactly {done, merged, failed, cancelled, reverted} in both modules")

    print("== REAP_GRACE_S / rate_limited exclusion (ADDENDUM 2) ==")
    _mark(test_sweep_respects_grace_period(), "a 2-minute-old terminal task is untouched")
    _mark(test_sweep_reaps_after_grace_period(), "a 6-minute-old terminal task is reaped")
    _mark(test_sweep_ignores_rate_limited_with_tab(), "rate_limited is never swept")

    print("== ADDENDUM 1: Chrome tabs are a surface too ==")
    _mark(test_sweep_reaps_via_chrome_tab_claim_alone(),
          "a Chrome-tab claim alone triggers close_dev")
    _mark(test_log_unclaimed_org_tabs_logs_only_unclaimed(),
          "logs only the tab with no claim")
    _mark(test_live_org_chrome_tabs_skips_when_chrome_not_running(),
          "never shells out when Chrome is not running")
    _mark(test_live_org_chrome_tabs_filters_by_domain(),
          "keeps only higgsfield.ai/flow.google.com/grok.com tabs")
    _mark(test_close_chrome_tabs_skips_when_chrome_not_running(),
          "close_chrome_tabs never shells out when Chrome is not running")
    _mark(test_close_chrome_tabs_builds_ids_and_parses_output(),
          "close_chrome_tabs binds explicit ids and parses closed ids back")
    _mark(test_close_dev_closes_claimed_chrome_tabs_and_clears_registry(),
          "close_dev closes claimed Chrome tabs and clears the registry")
    _mark(test_close_dev_no_claim_never_touches_chrome(),
          "close_dev never touches Chrome when the task claimed nothing")

    print("== sweep_terminal_surfaces: remote pass (GAP 1) ==")
    _mark(test_sweep_reaps_terminal_remote_task_via_close_remote(),
          "terminal remote task reaches close_remote, ssh command carries the pid")
    _mark(test_sweep_remote_respects_grace_period(),
          "a 1-minute-old terminal remote task is untouched (REAP_GRACE_S)")
    _mark(test_sweep_remote_no_pid_is_silent_noop(),
          "no pid recorded on a remote task -> silent no-op, not logged")
    _mark(test_sweep_local_task_never_touches_close_remote(),
          "local (mac) task never calls close_remote")

    print("== close_remote: allow_review opt-in (GAP 2 plumbing) ==")
    _mark(test_close_remote_allow_review_opt_in(),
          "allow_review=True accepts 'review'; default still refuses it")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

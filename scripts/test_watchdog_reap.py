"""Tests for tools/worker_reap.py's close_dev() and runners/watchdog.py's
finished-DEV reap pass (task-78ab64ba).

No live processes and no real iTerm: `close_tab`, `_terminate_pid` and
`_pid_matches_task` are stubbed for close_dev; `close_dev` and `_pid_alive`
are stubbed for the watchdog-pass tests.

Tests:
  1. refuses a task in in_progress
  2. refuses a task in blocked_human
  3. no-pid task is no longer refused (task-92118d4e: close_dev is total)
  4. does not signal when the pid's command line lacks the task_id
     (recycled-pid case) but still closes the tab
  5. reaps a review task whose pid matches
  6. watchdog pass ignores a finished task younger than 60 minutes
  7. watchdog pass reaps one older than 60 minutes
  8. idempotent: a second close_dev on the same task does not raise
  9. stall pass: a silent in_progress task with a LIVE pid is flagged
     'suspect', never closed/stalled (ADDENDUM 2, task-92118d4e)
  10. a second silent-but-alive tick reuses the already-filed issue

Run via: python scripts/test_watchdog_reap.py
"""
from __future__ import annotations

import json
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

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _ts(delta_minutes: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)
    return dt.isoformat(timespec="seconds")


def _insert_task(*, status: str, age_minutes: float = 0,
                 pid: int | None = None, host: str | None = None,
                 project: str = "test-proj") -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts = _ts(age_minutes)
    with db_mod.get_conn() as conn:
        conn.execute(
            """INSERT INTO tasks
               (id, project, role, status, title, description, pid, host,
                depends_on, touches, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (tid, project, "developer", status, "t", "d", pid, host,
             "[]", "[]", ts, ts),
        )
    return tid


# ---------------------------------------------------------------------------
# close_dev: refuse branches (1-3)
# ---------------------------------------------------------------------------

def test_refuses_in_progress() -> bool:
    tid = _insert_task(status="in_progress", pid=12345)
    with mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=True)) as ct:
        r = worker_reap.close_dev(tid, reason="test")
    return (r["refused"] is not None and r["closed_tab"] is False
           and r["signal"] is None and ct.call_count == 0)


def test_refuses_blocked_human() -> bool:
    tid = _insert_task(status="blocked_human", pid=12345)
    r = worker_reap.close_dev(tid, reason="test")
    return r["refused"] is not None and r["closed_tab"] is False


def test_null_pid_is_no_longer_refused() -> bool:
    """task-92118d4e: close_dev used to refuse outright when pid was NULL,
    which is exactly the case that left a leaked tmux/tab behind for a task
    that never got a pid recorded at all (a direct sqlite status edit, a
    worker that exited before writing one). It is now total — no pid means
    no signal to send, but tmux/tab cleanup still runs."""
    tid = _insert_task(status="review", pid=None)
    with mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=False)):
        r = worker_reap.close_dev(tid, reason="test")
    return (r["refused"] is None and r["pid"] is None and r["signal"] is None
           and r["found"]["pid"] is False)


# ---------------------------------------------------------------------------
# close_dev: recycled-pid safety (4)
# ---------------------------------------------------------------------------

def test_recycled_pid_not_signalled_but_tab_closed() -> bool:
    tid = _insert_task(status="review", pid=99999)
    fake_terminate = mock.Mock(return_value="SIGTERM")
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=False)), \
         mock.patch.object(worker_reap, "_terminate_pid", fake_terminate), \
         mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=True)):
        r = worker_reap.close_dev(tid, reason="test")
    return (r["refused"] is None and r["pid_matched"] is False
           and r["signal"] is None and fake_terminate.call_count == 0
           and r["closed_tab"] is True)


def test_recycled_pid_closes_by_title_not_by_pid() -> bool:
    """The tab must be closed WITHOUT the pid path when the pid mismatches.

    The case above only asserts that a tab was closed — not *how*. That gap
    is what let the first version through review: `close_tab` starts with
    `_task_pid()` -> `_close_tab_by_pid()`, so it reached for the very pid
    `close_dev` had just refused to trust, and would have closed whichever
    tab now holds it. Assert the seam itself: allow_pid False on the
    unverified path, True on the verified one.
    """
    calls: list = []

    def spy(task_id, *, allow_pid=True):
        calls.append(allow_pid)
        return True

    tid = _insert_task(status="review", pid=99998)
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=False)), \
         mock.patch.object(worker_reap, "_terminate_pid", mock.Mock(return_value="SIGTERM")), \
         mock.patch.object(worker_reap, "close_tab", spy):
        worker_reap.close_dev(tid, reason="test")

    tid2 = _insert_task(status="review", pid=99997)
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap, "_terminate_pid", mock.Mock(return_value="SIGTERM")), \
         mock.patch.object(worker_reap, "close_tab", spy):
        worker_reap.close_dev(tid2, reason="test")

    return calls == [False, True]


def test_close_tab_allow_pid_false_skips_pid_lookup() -> bool:
    """`close_tab(..., allow_pid=False)` must not consult the pid at all."""
    from tools import itermtab
    by_pid = mock.Mock(return_value=True)
    task_pid = mock.Mock(return_value=4242)
    with mock.patch.object(itermtab, "_task_pid", task_pid), \
         mock.patch.object(itermtab, "_close_tab_by_pid", by_pid), \
         mock.patch.object(itermtab, "_run_api", mock.Mock(return_value=False)):
        itermtab.close_tab("task-deadbeef", allow_pid=False)
        skipped = task_pid.call_count == 0 and by_pid.call_count == 0
        itermtab.close_tab("task-deadbeef", allow_pid=True)
        used = task_pid.call_count == 1 and by_pid.call_count == 1
    return skipped and used


# ---------------------------------------------------------------------------
# close_dev: happy path + idempotency (5, 8)
# ---------------------------------------------------------------------------

def test_reaps_matching_review() -> bool:
    tid = _insert_task(status="review", pid=54321)
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap, "_terminate_pid", mock.Mock(return_value="SIGTERM")), \
         mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=True)):
        r = worker_reap.close_dev(tid, reason="test")
    return (r["refused"] is None and r["pid_matched"] is True
           and r["signal"] == "SIGTERM" and r["closed_tab"] is True)


def test_idempotent_second_call() -> bool:
    tid = _insert_task(status="done", pid=54321)
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=True)), \
         mock.patch.object(worker_reap, "_terminate_pid", mock.Mock(return_value="SIGTERM")), \
         mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=True)):
        r1 = worker_reap.close_dev(tid, reason="first")
    # Second call: process is now gone (or recycled) and the tab is already
    # closed — the natural post-reap state. Must not raise.
    with mock.patch.object(worker_reap, "_pid_matches_task", mock.Mock(return_value=False)), \
         mock.patch.object(worker_reap, "close_tab", mock.Mock(return_value=False)):
        try:
            r2 = worker_reap.close_dev(tid, reason="second")
        except Exception:
            return False
    return r1["refused"] is None and r2["refused"] is None and r2["signal"] is None


# ---------------------------------------------------------------------------
# watchdog finished-reap pass: 60-minute floor (6, 7)
# ---------------------------------------------------------------------------

def test_watchdog_ignores_young_finished() -> bool:
    tid = _insert_task(status="review", age_minutes=10, pid=11111)
    fake_close_dev = mock.Mock()
    # task-92118d4e added a fourth pass (sweep_terminal_surfaces) to
    # scan_once. It shares this mocked close_dev/_pid_alive, and the same
    # temp DB accumulates 'done'/'review' rows from every earlier test in
    # this file — stubbed out here so this test stays scoped to the
    # third pass (the 60-min finished-reap floor) it was written for.
    with mock.patch.object(watchdog, "close_dev", fake_close_dev), \
         mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        out = watchdog.scan_once()
    reaped_ids = {r["task"] for r in out["reaped"]}
    return tid not in reaped_ids and fake_close_dev.call_count == 0


def test_watchdog_reaps_old_finished() -> bool:
    tid = _insert_task(status="review", age_minutes=61, pid=22222)
    canned = {"task_id": tid, "closed_tab": True, "pid": 22222,
             "pid_matched": True, "signal": "SIGTERM", "tmux_killed": False,
             "ttyd_killed": False,
             "reason": "watchdog: no C-level decision in 60 min", "refused": None}
    fake_close_dev = mock.Mock(return_value=canned)
    # Same isolation as above — this test asserts fake_close_dev.call_count
    # == 1, which the fourth pass (sweeping unrelated leftover 'done' rows
    # from earlier tests via the same mocked close_dev) would break.
    with mock.patch.object(watchdog, "close_dev", fake_close_dev), \
         mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        out = watchdog.scan_once()
    reaped_ids = {r["task"] for r in out["reaped"]}
    called_reason = (fake_close_dev.call_args.kwargs.get("reason", "")
                     if fake_close_dev.call_args else "")
    return (tid in reaped_ids and fake_close_dev.call_count == 1
           and called_reason.startswith("watchdog:"))


# ---------------------------------------------------------------------------
# watchdog stall pass: live pid is never closed, only flagged suspect
# (ADDENDUM 2, task-92118d4e, CEO rule 2026-09-07)
# ---------------------------------------------------------------------------

def test_silent_in_progress_with_live_pid_is_suspect_not_stalled() -> bool:
    """3 hours silent, pid alive: status must stay in_progress, no tab/tmux
    close, and exactly one 'suspect' log line — not the old ceiling-reap."""
    tid = _insert_task(status="in_progress", age_minutes=180, pid=55555)
    logged: list[str] = []
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog, "_close_tab", mock.Mock()) as fake_close_tab, \
         mock.patch.object(watchdog, "_cleanup_tmux_ttyd", mock.Mock()) as fake_tmux, \
         mock.patch.object(watchdog, "_file_stalled_issue",
                          mock.Mock(return_value="https://github.com/x/y/issues/1")), \
         mock.patch.object(watchdog, "warn", side_effect=lambda m: logged.append(m)), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        watchdog.scan_once()
    task = db_mod.get_task(tid)
    review = json.loads(task["review"] or "{}")
    suspect_lines = [m for m in logged if m.startswith("SUSPECT ")]
    return (task["status"] == "in_progress" and review.get("watchdog") == "suspect"
           and fake_close_tab.call_count == 0 and fake_tmux.call_count == 0
           and len(suspect_lines) == 1)


def test_suspect_reuses_existing_issue_on_next_tick() -> bool:
    """A second tick while still silent-but-alive must not file a second GH
    issue — it reuses the one already recorded in review.issue."""
    tid = _insert_task(status="in_progress", age_minutes=180, pid=55556)
    fake_file_issue = mock.Mock(return_value="https://github.com/x/y/issues/2")
    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog, "_file_stalled_issue", fake_file_issue), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        watchdog.scan_once()
        watchdog.scan_once()
    return fake_file_issue.call_count == 1


# ---------------------------------------------------------------------------
# GAP 3 (task-59780ac3): remote in_progress stall detection. Before this
# fix, runners/watchdog.py's stall loop skipped every host != mac outright
# — a remote worker that died mid-task sat in_progress forever, silently.
# ---------------------------------------------------------------------------

def test_remote_stall_pid_gone_marks_stalled() -> bool:
    """The remote box answered and the pid is provably gone — stall it and
    file the same GH issue the local path files."""
    tid = _insert_task(status="in_progress", age_minutes=40, pid=7777, host="winbox")
    with mock.patch.object(watchdog, "get_host", mock.Mock(return_value={"ssh": "winbox"})), \
         mock.patch.object(watchdog, "remote_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_file_stalled_issue",
                          mock.Mock(return_value="https://github.com/x/y/issues/3")), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        out = watchdog.scan_once()
    task = db_mod.get_task(tid)
    stalled_ids = {r["task"] for r in out["stalled"]}
    return task["status"] == "stalled" and tid in stalled_ids


def test_remote_stall_unreachable_ssh_never_flips() -> bool:
    """None (ssh itself failed — box unreachable) must never collapse into
    'dead': a Wi-Fi/Tailscale blip must not stall a task that is still
    running fine."""
    tid = _insert_task(status="in_progress", age_minutes=40, pid=7778, host="winbox")
    with mock.patch.object(watchdog, "get_host", mock.Mock(return_value={"ssh": "winbox"})), \
         mock.patch.object(watchdog, "remote_pid_alive", mock.Mock(return_value=None)), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        out = watchdog.scan_once()
    task = db_mod.get_task(tid)
    stalled_ids = {r["task"] for r in out["stalled"]}
    return task["status"] == "in_progress" and tid not in stalled_ids


def test_remote_stall_alive_never_flips() -> bool:
    """The box answered and the pid IS alive — must also stay in_progress,
    not just the unreachable case above."""
    tid = _insert_task(status="in_progress", age_minutes=40, pid=7779, host="winbox")
    with mock.patch.object(watchdog, "get_host", mock.Mock(return_value={"ssh": "winbox"})), \
         mock.patch.object(watchdog, "remote_pid_alive", mock.Mock(return_value=True)), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        out = watchdog.scan_once()
    return db_mod.get_task(tid)["status"] == "in_progress"


def test_mac_task_never_uses_remote_stall_path() -> bool:
    """LOCAL (mac) task must be unaffected by GAP 3's new remote path — it
    must never even be handed to _check_remote_stall (only winbox/contabo
    rows reach that helper). Checked by id, not a global call count: this
    file's tests share one accumulating temp DB, and earlier tests in this
    run legitimately leave their own winbox rows in_progress, which would
    also reach _check_remote_stall on this tick — that is correct behaviour
    for THEM, not a leak in this test."""
    tid = _insert_task(status="in_progress", age_minutes=40, pid=7780, host=None)
    seen_ids: list[str] = []

    def spy(t, host_name):
        seen_ids.append(t["id"])
        return None

    with mock.patch.object(watchdog, "_pid_alive", mock.Mock(return_value=False)), \
         mock.patch.object(watchdog, "_check_remote_stall", side_effect=spy), \
         mock.patch.object(watchdog, "sweep_terminal_surfaces", mock.Mock(return_value=[])):
        watchdog.scan_once()
    return tid not in seen_ids


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="watchdog-reap-")
    db_mod.DB_PATH = Path(tmp) / "tasks.db"
    db_mod.init()

    print("== close_dev: refuse branches ==")
    _mark(test_refuses_in_progress(), "refuses a task in in_progress")
    _mark(test_refuses_blocked_human(), "refuses a task in blocked_human")
    _mark(test_null_pid_is_no_longer_refused(), "no-pid task is no longer refused")

    print("== close_dev: recycled-pid safety ==")
    _mark(test_recycled_pid_not_signalled_but_tab_closed(),
          "does not signal a recycled pid, still closes the tab")
    _mark(test_recycled_pid_closes_by_title_not_by_pid(),
          "recycled pid: tab closed by title only, pid path never reached")
    _mark(test_close_tab_allow_pid_false_skips_pid_lookup(),
          "close_tab(allow_pid=False) skips the pid lookup entirely")

    print("== close_dev: happy path + idempotency ==")
    _mark(test_reaps_matching_review(), "reaps a review task whose pid matches")
    _mark(test_idempotent_second_call(), "idempotent: second close_dev does not raise")

    print("== watchdog finished-reap pass (60 min floor) ==")
    _mark(test_watchdog_ignores_young_finished(), "ignores a finished task younger than 60 min")
    _mark(test_watchdog_reaps_old_finished(), "reaps a finished task older than 60 min")

    print("== watchdog stall pass: live pid is suspect, never closed (ADDENDUM 2) ==")
    _mark(test_silent_in_progress_with_live_pid_is_suspect_not_stalled(),
          "3h silent + live pid -> suspect, nothing closed, one log line")
    _mark(test_suspect_reuses_existing_issue_on_next_tick(),
          "a second silent-but-alive tick reuses the filed issue")

    print("== GAP 3: remote in_progress stall detection ==")
    _mark(test_remote_stall_pid_gone_marks_stalled(),
          "remote pid provably gone (False) -> stalled + issue filed")
    _mark(test_remote_stall_unreachable_ssh_never_flips(),
          "remote pid check unreachable (None) -> never flipped to stalled")
    _mark(test_remote_stall_alive_never_flips(),
          "remote pid alive (True) -> never flipped to stalled")
    _mark(test_mac_task_never_uses_remote_stall_path(),
          "local (mac) task never consults remote_pid_alive/get_host")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

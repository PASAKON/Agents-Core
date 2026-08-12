"""Watchdog — auto-ping silent DEVs, mark dead ones stalled.

Scans tasks WHERE status='in_progress'. For each:
  - silent < PING_AFTER_S          → leave alone
  - PING_AFTER_S <= silent < STALL_AFTER_S → send_to_dev "status check"
  - silent >= STALL_AFTER_S        → status=stalled + file gh issue

"Silent" = seconds since tasks.updated_at (Stop-hook relay touches this).

Usage:
    python -m runners.watchdog                   # one-shot scan
    python -m runners.watchdog --loop            # forever, sleep INTERVAL_S
    python -m runners.watchdog --interval 300    # custom sleep
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.notify import info, success, warn, error
from tools.dev_reap import _cleanup_tmux_ttyd, _pid_alive, close_dev
from tools.gc_stale_tasks import gc_stale_tasks

PING_AFTER_S = 10 * 60
STALL_AFTER_S = 30 * 60
INTERVAL_S = 300

# Layer 2 floor (task-78ab64ba): a DEV whose task reached review/done but
# whose process is still alive gets reaped after this long with no C-level
# decision (merge_task, which itself calls close_dev). This is a floor, not
# a decider — see tools/dev_reap.py's module docstring for the two-layer
# design the CEO ruled on 2026-08-12.
FINISHED_REAP_AFTER_S = 60 * 60

# When a DEV files a captcha/login blocker it self-flips status to
# 'blocked_human'. We do NOT ping these (the CEO needs human time, not
# pings) but if no human attention arrives within HUMAN_TIMEOUT_S we
# escalate to 'stalled' + file a GH issue so the task can't sit forever.
HUMAN_TIMEOUT_S = 24 * 3600


def _close_tab(task_id: str) -> bool:
    """Close the DEV's iTerm tab via tab-title match on task_id substring.

    Match is exact-substring, so it cannot collide with unrelated tabs.
    Returns True iff a tab was closed.
    """
    try:
        from tools.itermtab import close_tab
        return close_tab(task_id)
    except Exception as e:
        warn(f"close_tab failed for {task_id}: {e}")
        return False


def _silent_seconds(updated_at: str) -> float:
    try:
        upd = datetime.fromisoformat(updated_at)
    except ValueError:
        return 0.0
    if upd.tzinfo is None:
        upd = upd.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - upd).total_seconds()


def _send_ping(task_id: str, message: str) -> bool:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "tools.send_to_dev", task_id, message],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except Exception as e:
        warn(f"send_to_dev failed for {task_id}: {e}")
        return False


def _file_stalled_issue(task: dict, silent_s: float) -> str:
    try:
        from tools.gh_issue import create_issue
    except Exception as e:
        warn(f"gh_issue import failed: {e}")
        return ""
    body = (
        f"Task `{task['id']}` has been silent for "
        f"{int(silent_s/60)} min while status=in_progress.\n\n"
        f"**Role**: `{task.get('role')}`\n"
        f"**Worktree**: `{task.get('worktree') or '(none)'}`\n"
        f"**Branch**: `{task.get('branch') or '(none)'}`\n"
        f"**Last update**: `{task.get('updated_at')}`\n\n"
        "Watchdog flipped status to `stalled`. Investigate:\n"
        "1. Check iTerm tab for the task — is claude alive?\n"
        "2. `ps aux | grep <task_id>` — is the process running?\n"
        "3. If dead, reset to `pending` and re-delegate. If hung, kill PID + reset."
    )
    try:
        return create_issue(task["project"], f"watchdog: task {task['id']} stalled",
                            body, labels=["watchdog", "agent"])
    except Exception as e:
        warn(f"gh issue create failed: {e}")
        return ""


def scan_once() -> dict:
    pinged = []
    stalled = []
    rows = db.list_tasks(status="in_progress", limit=200)
    for t in rows:
        silent = _silent_seconds(t["updated_at"])
        if silent < PING_AFTER_S:
            continue
        if silent >= STALL_AFTER_S:
            issue = _file_stalled_issue(t, silent)
            pid = t.get("pid")
            pid_alive = _pid_alive(pid)
            # SAFETY: only close the tab when `pid` is recorded. PID is
            # written by runners/dev_init.py right before `os.execvpe`,
            # which only runs when the CTO delegate path spawned this
            # task. Legacy tasks and tabs the user opened or attached
            # interactively (e.g. a `spawn Web Designer` REPL) have
            # `pid IS NULL` and are left alone — they may be live work.
            if pid:
                tab_closed = _close_tab(t["id"])
            else:
                tab_closed = False
                info(f"watchdog: skip tab close for {t['id']} (no pid; "
                     "not delegate-spawned or pre-PID-tracking task)")
            tmux_cleanup = _cleanup_tmux_ttyd(t)
            try:
                review = json.loads(t.get("review") or "{}")
            except json.JSONDecodeError:
                review = {}
            review.update({
                "watchdog": "stalled",
                "silent_seconds": int(silent),
                "issue": issue,
                "pid": pid,
                "pid_alive": pid_alive,
                "tab_closed": tab_closed,
                **tmux_cleanup,
            })
            db.update_status(t["id"], "stalled", actor="watchdog",
                             review=json.dumps(review))
            stalled.append({"task": t["id"], "silent_s": int(silent),
                            "issue": issue, "pid": pid,
                            "pid_alive": pid_alive,
                            "tab_closed": tab_closed})
            error(
                f"STALLED {t['id']} silent={int(silent/60)}min "
                f"pid={pid} alive={pid_alive} tab_closed={tab_closed} "
                f"issue={issue}"
            )
            continue
        msg = (f"watchdog ping — silent {int(silent/60)} min. "
               f"Status check? If stuck, call mcp__org__file_blocker_issue.")
        if _send_ping(t["id"], msg):
            pinged.append({"task": t["id"], "silent_s": int(silent)})
            info(f"pinged {t['id']} silent={int(silent/60)}min")

    # Second pass: escalate long-overdue blocked_human tasks. These were
    # self-flipped by a DEV via mcp__org__file_blocker_issue (captcha,
    # login, 2FA, etc.). We do NOT ping or stall them on the 30-min
    # threshold — humans take longer — but after HUMAN_TIMEOUT_S we
    # treat the CEO as unavailable and escalate to 'stalled' + GH issue.
    human_rows = db.list_tasks(status="blocked_human", limit=200)
    for t in human_rows:
        silent = _silent_seconds(t["updated_at"])
        if silent < HUMAN_TIMEOUT_S:
            continue
        issue = _file_stalled_issue(t, silent)
        try:
            review = json.loads(t.get("review") or "{}")
        except json.JSONDecodeError:
            review = {}
        review.update({
            "watchdog": "stalled",
            "from_status": "blocked_human",
            "silent_seconds": int(silent),
            "issue": issue,
        })
        db.update_status(t["id"], "stalled", actor="watchdog",
                         review=json.dumps(review))
        stalled.append({"task": t["id"], "silent_s": int(silent),
                        "issue": issue, "from": "blocked_human"})
        error(
            f"STALLED-FROM-BLOCKED-HUMAN {t['id']} "
            f"silent={int(silent/3600)}h issue={issue}"
        )

    # Third pass — layer 2 floor (task-78ab64ba): a DEV whose task reached
    # review/done but whose process is still alive with no C-level decision
    # in FINISHED_REAP_AFTER_S. Layer 1 (merge_task -> close_dev) is the
    # normal path; this only fires when that never happened at all. Does
    # NOT touch task status — the task is already terminal, the reap is
    # recorded here and in the log, not in tasks.db.
    reaped = []
    finished_rows = (db.list_tasks(status="review", limit=200)
                     + db.list_tasks(status="done", limit=200))
    for t in finished_rows:
        pid = t.get("pid")
        if not pid or not _pid_alive(pid):
            continue
        silent = _silent_seconds(t["updated_at"])
        if silent < FINISHED_REAP_AFTER_S:
            continue
        reap = close_dev(t["id"], reason="watchdog: no C-level decision in 60 min")
        reaped.append({"task": t["id"], "status": t["status"],
                       "silent_s": int(silent), **reap})
        error(
            f"REAPED {t['id']} status={t['status']} silent={int(silent/60)}min "
            f"pid={pid} pid_matched={reap.get('pid_matched')} "
            f"signal={reap.get('signal')} tab_closed={reap.get('closed_tab')}"
        )

    # GC pass: cancel stale pending/conflict/rate_limited tasks and free locks.
    try:
        gc_cancelled = gc_stale_tasks()
        if gc_cancelled:
            success(f"watchdog gc: cancelled {len(gc_cancelled)} stale task(s)")
    except Exception as e:
        warn(f"watchdog gc error: {e}")
        gc_cancelled = []

    return {"pinged": pinged, "stalled": stalled, "reaped": reaped,
            "scanned": len(rows) + len(human_rows),
            "gc_cancelled": len(gc_cancelled)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Watchdog for stuck DEV tasks")
    ap.add_argument("--loop", action="store_true",
                    help="run forever, sleep --interval between scans")
    ap.add_argument("--interval", type=int, default=INTERVAL_S,
                    help=f"loop sleep seconds (default {INTERVAL_S})")
    args = ap.parse_args()

    db.init()
    if not args.loop:
        out = scan_once()
        print(json.dumps(out, indent=2))
        return 0

    info(f"watchdog loop started — interval={args.interval}s, "
         f"ping_after={PING_AFTER_S}s, stall_after={STALL_AFTER_S}s")
    while True:
        try:
            out = scan_once()
            if out["pinged"] or out["stalled"] or out["reaped"]:
                success(f"watchdog: pinged={len(out['pinged'])} stalled={len(out['stalled'])} "
                       f"reaped={len(out['reaped'])}")
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            error(f"watchdog scan error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())

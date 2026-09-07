"""Watchdog — auto-ping silent DEVs, mark dead ones stalled.

Scans tasks WHERE status='in_progress'. For each:
  - silent < PING_AFTER_S          → leave alone
  - PING_AFTER_S <= silent < STALL_AFTER_S → send_to_worker "status check"
  - silent >= STALL_AFTER_S, pid dead  → status=stalled + file gh issue
  - silent >= STALL_AFTER_S, pid alive → review.watchdog="suspect" + file/
    refresh gh issue; status, tab and tmux are never touched (ADDENDUM 2,
    CEO rule 2026-09-07: never close a surface under a worker that may
    still be working)

"Silent" = seconds since tasks.updated_at (Stop-hook relay touches this).

Usage:
    python -m runners.watchdog                   # one-shot scan
    python -m runners.watchdog --loop            # forever, sleep INTERVAL_S
    python -m runners.watchdog --interval 300    # custom sleep
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.notify import info, success, warn, error
from tools.worker_reap import _cleanup_tmux_ttyd, _pid_alive, close_dev, _chrome_running
from tools.gc_stale_tasks import gc_stale_tasks
from tools import tmux_session

# Chrome tabs on these org generation sites are the ones ADDENDUM 1's
# unclaimed-tab log line cares about — a stray shell/bank/docs tab is just
# the CEO's own browsing, not a leak.
_ORG_TAB_DOMAINS = ("higgsfield.ai", "flow.google.com", "grok.com")

PING_AFTER_S = 10 * 60
STALL_AFTER_S = 30 * 60
INTERVAL_S = 300

# Layer 2 floor (task-78ab64ba): a DEV whose task reached review/done but
# whose process is still alive gets reaped after this long with no C-level
# decision (merge_task, which itself calls close_dev). This is a floor, not
# a decider — see tools/worker_reap.py's module docstring for the two-layer
# design the CEO ruled on 2026-08-12.
FINISHED_REAP_AFTER_S = 60 * 60

# When a DEV files a captcha/login blocker it self-flips status to
# 'blocked_human'. We do NOT ping these (the CEO needs human time, not
# pings) but if no human attention arrives within HUMAN_TIMEOUT_S we
# escalate to 'stalled' + file a GH issue so the task can't sit forever.
HUMAN_TIMEOUT_S = 24 * 3600

# Terminal-surface sweep (task-92118d4e, CEO rule 2026-09-07: "closing a
# worker means closing its window too"). Every status where the task is
# over and no worker process/tmux/tab should still exist for it —
# db.VALID_STATUS minus db.ACTIVE_STATUSES (pending/in_progress/
# rate_limited/conflict — still working or awaiting retry) minus
# {'review', 'blocked_human'} (still awaiting a C-level/CEO decision, so a
# live surface there is expected, not a leak — see the FINISHED_REAP_AFTER_S
# floor above, which already covers 'review'/'done') minus {'stalled'}
# (ADDENDUM 2, CEO ruling 2026-09-07: stalled is a SUSPICION set by silence
# alone, not proof of death — a silent browser_operator is usually mid
# 20-40min render. Sweeping it would close a worker that may still be
# working, exactly the leak the CEO ruled against). Computed from the
# actual VALID_STATUS/ACTIVE_STATUSES sets rather than hand-copied so it
# can't silently drift if either set changes — exactly {done, failed,
# cancelled, reverted, merged} today.
TERMINAL_SURFACE_STATUSES = tuple(sorted(
    db.VALID_STATUS - set(db.ACTIVE_STATUSES)
    - {"review", "blocked_human", "stalled"}
))

# Grace period (ADDENDUM 2): a terminal-status task is only swept once its
# own `updated_at` is at least this old. The normal close_dev caller
# (merge_task, the CTO's close_dev MCP tool) needs a moment to actually run
# right after the status flip; sweeping instantly would race a legitimate
# in-flight close_dev and could act on a tab/tmux mid-teardown by its
# proper owner.
REAP_GRACE_S = 300

# Cap on tasks actually reaped (close_dev called) per sweep tick — a runaway
# state (many leaked tasks at once) must not stall the watchdog's main loop.
SWEEP_CAP = 20


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
            [sys.executable, "-m", "tools.send_to_worker", task_id, message],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0
    except Exception as e:
        warn(f"send_to_worker failed for {task_id}: {e}")
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


def _live_tmux_sessions() -> set[str]:
    """Every live tmux session name, in one `tmux list-sessions` call.

    Batched rather than one `has-session` subprocess per task — the sweep
    may look at up to 6 statuses x 200 rows each; one call here beats up to
    1200. Returns an empty set on no server / any error (tmux not running is
    not a leak signal, it just means nothing is alive to find).
    """
    try:
        r = subprocess.run(
            [tmux_session.tmux_bin(), "list-sessions", "-F", "#{session_name}"],
            capture_output=True, text=True, timeout=5,
        )
    except Exception as e:
        warn(f"sweep: tmux list-sessions failed: {e}")
        return set()
    if r.returncode != 0:
        return set()
    return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}


def _live_task_tab_ids() -> set[str]:
    """Every task id that appears in a live iTerm tab title, in one call.

    Delegates to tools.itermtab.list_task_tabs() (task-92118d4e) — the
    single batched osascript enumeration — rather than searching per-task,
    for the same reason as _live_tmux_sessions above.
    """
    try:
        from tools.itermtab import list_task_tabs
    except Exception as e:
        warn(f"sweep: itermtab import failed: {e}")
        return set()
    try:
        tabs = list_task_tabs()
    except Exception as e:
        warn(f"sweep: list_task_tabs failed: {e}")
        return set()
    ids: set[str] = set()
    for _window_id, title in tabs:
        m = re.search(r"task-[0-9a-fA-F]+", title)
        if m:
            ids.add(m.group(0))
    return ids


def _live_org_chrome_tabs() -> list[tuple[str, str]]:
    """Every live Chrome tab (id, url) on an org generation domain, in one
    osascript call — task-92118d4e ADDENDUM 1.

    Guarded by _chrome_running() first: `tell application "Google Chrome"`
    launches Chrome if it is not already running, which a background sweep
    must never do just to look.
    """
    if not _chrome_running():
        return []
    script = '''
tell application "Google Chrome"
  set outLines to {}
  repeat with w in windows
    repeat with t in tabs of w
      set end of outLines to ((id of t as text) & (ASCII character 9) & (URL of t))
    end repeat
  end repeat
  set AppleScript's text item delimiters to linefeed
  set outStr to outLines as text
  set AppleScript's text item delimiters to ""
  return outStr
end tell
'''
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=10)
    except Exception as e:
        warn(f"sweep: chrome tab listing failed: {e}")
        return []
    if r.returncode != 0:
        return []
    out: list[tuple[str, str]] = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        tid, _, url = line.partition("\t")
        if any(dom in url for dom in _ORG_TAB_DOMAINS):
            out.append((tid, url))
    return out


def _log_unclaimed_org_tabs(claimed_tab_ids: set[str]) -> None:
    """ADDENDUM 1: a live Chrome tab on an org generation site with no claim
    anywhere in the browser-tabs registry is suspicious — a browser_operator
    that never registered its tab, or a claim already cleared out from under
    a still-open one — but this sweep only ever LOGS it, never closes it;
    only a claimed tab under a terminal task is ever closed automatically.
    """
    for tab_id, url in _live_org_chrome_tabs():
        if tab_id not in claimed_tab_ids:
            warn(f"unclaimed org tab: {tab_id} {url}")


def sweep_terminal_surfaces() -> list[dict]:
    """Second watchdog pass (task-92118d4e): close any live pid/tmux/tab/
    Chrome-tab-claim a task left behind after reaching a terminal status
    WITHOUT going through close_dev — a direct sqlite status edit, a worker
    that exited on its own, a rate-limited/cancelled worker, a cancel. See
    docs/design/multi-host-workers.md "Teardown invariant".

    Only inspects LOCAL (Mac) surfaces — a task whose `host` (task-d1d6b2ef,
    may not exist yet) is set to a remote spoke is skipped here; nothing on
    this machine can tell whether its remote pid/tmux is still alive, and
    tools.worker_reap.close_remote is the (separately exposed, separately
    wired) teardown for that case.

    Runs close_dev — already idempotent, never raises — on every terminal-
    status task that still shows a live pid, live `wd-<id>` tmux session, an
    open iTerm tab, OR a claimed Chrome tab in the browser-tabs registry
    (ADDENDUM 1: "Chrome tabs are a surface too" — close_dev itself closes
    the claimed tab(s) by id and clears the claim). Logs one line per task
    actually acted on; a clean task (nothing left to close) produces no log
    line at all, so re-running this after a clean sweep is silent —
    matching close_dev's own idempotency, and the acceptance test's "run it
    again -> no output".

    Also logs (ADDENDUM 1), every tick and regardless of any task's status,
    any live Chrome tab on an org generation domain that has NO claim at
    all in the registry — `unclaimed org tab: <id> <url>`. That line is
    informational only; this sweep never closes an unclaimed tab.

    Capped at SWEEP_CAP tasks actually reaped per tick (not per task
    scanned) so a runaway state cannot stall the watchdog's main loop. Skips
    any task whose terminal `updated_at` is younger than REAP_GRACE_S
    (ADDENDUM 2) — a task that just went terminal gets a moment for its
    normal close_dev caller to run before the sweep treats it as a leak.
    """
    reaped: list[dict] = []

    try:
        from scripts.browser.tab_registry import all_claims
        claims = all_claims()
    except Exception as e:
        warn(f"sweep: tab_registry import failed: {e}")
        claims = {}
    _log_unclaimed_org_tabs(set(claims.keys()))
    claimed_task_ids = set(claims.values())

    rows: list[dict] = []
    for status in TERMINAL_SURFACE_STATUSES:
        rows.extend(db.list_tasks(status=status, limit=200))
    if not rows:
        return reaped

    live_tmux = _live_tmux_sessions()
    live_tab_ids = _live_task_tab_ids()

    for t in rows:
        if len(reaped) >= SWEEP_CAP:
            break
        task_id = t["id"]
        if t.get("host") not in (None, "mac"):
            continue
        if _silent_seconds(t.get("updated_at")) < REAP_GRACE_S:
            continue
        pid_alive = _pid_alive(t.get("pid"))
        tmux_alive = tmux_session.session_name_for(task_id) in live_tmux
        tab_open = task_id in live_tab_ids
        tab_claimed = task_id in claimed_task_ids
        if not (pid_alive or tmux_alive or tab_open or tab_claimed):
            continue
        reap = close_dev(task_id, reason="reaper: terminal status with live surface")
        # A recorded pid that is alive but no longer THIS task's process is a
        # recycled pid: close_dev rightly refuses to signal it, but leaving it on
        # the row makes every later tick see "pid alive" and re-log the task
        # forever (seen live: efa1d2dd / 5c0adb13 / 7cb85052 every 5 minutes).
        # Forget the pid so the row is quiet from the next tick on.
        if pid_alive and reap.get("pid_matched") is False:
            try:
                db.set_fields(task_id, actor="watchdog", pid=None)
            except Exception as e:  # never let bookkeeping stop the sweep
                warn(f"could not clear recycled pid on {task_id}: {e}")
        reaped.append({"task": task_id, "status": t["status"],
                       "pid_alive": pid_alive, "tmux_alive": tmux_alive,
                       "tab_open": tab_open, "tab_claimed": tab_claimed, **reap})
        error(
            f"SURFACE-REAPED {task_id} status={t['status']} "
            f"pid_alive={pid_alive} tmux_alive={tmux_alive} tab_open={tab_open} "
            f"tab_claimed={tab_claimed} "
            f"signal={reap.get('signal')} tmux_killed={reap.get('tmux_killed')} "
            f"tab_closed={reap.get('closed_tab')} "
            f"chrome_tabs_closed={reap.get('chrome_tabs_closed')}"
        )
    return reaped


def scan_once() -> dict:
    pinged = []
    stalled = []
    rows = db.list_tasks(status="in_progress", limit=200)
    for t in rows:
        silent = _silent_seconds(t["updated_at"])
        if silent < PING_AFTER_S:
            continue
        if silent >= STALL_AFTER_S:
            pid = t.get("pid")
            pid_alive = _pid_alive(pid)
            # CEO rule (ADDENDUM 2, task-92118d4e): never close a surface
            # under a worker that may be working. A live pid means silence
            # is suspicion, not proof of death — a Higgsfield render takes
            # 26-30 minutes (one measured 80+), well past STALL_AFTER_S, and
            # a DEV doing exactly what it was told got reaped on
            # 2026-08-12/13 (task-cda4f469) and again — via a raised but
            # still finite ceiling — later. There is no ceiling now: file or
            # refresh the blocker issue, mark the task suspect, and leave
            # its tab, tmux and status alone for as long as the pid lives.
            # A genuinely wedged live process is the human's call via the
            # filed issue, not the watchdog's to reap.
            if pid_alive:
                try:
                    review = json.loads(t.get("review") or "{}")
                except json.JSONDecodeError:
                    review = {}
                # Reuse an already-filed issue rather than filing a new one
                # every tick while the same worker stays silent-but-alive.
                issue = review.get("issue") or _file_stalled_issue(t, silent)
                review.update({
                    "watchdog": "suspect",
                    "silent_seconds": int(silent),
                    "issue": issue,
                    "pid": pid,
                    "pid_alive": True,
                })
                db.set_fields(t["id"], actor="watchdog",
                              review=json.dumps(review))
                warn(f"SUSPECT {t['id']} silent={int(silent/60)}min "
                     f"pid={pid} alive — status/tab/tmux left untouched, "
                     f"issue={issue}")
                continue
            issue = _file_stalled_issue(t, silent)
            # SAFETY: only close the tab when `pid` is recorded. PID is
            # written by runners/worker_init.py right before `os.execvpe`,
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
                "pid_alive": False,
                "tab_closed": tab_closed,
                **tmux_cleanup,
            })
            db.update_status(t["id"], "stalled", actor="watchdog",
                             review=json.dumps(review))
            stalled.append({"task": t["id"], "silent_s": int(silent),
                            "issue": issue, "pid": pid,
                            "pid_alive": False,
                            "tab_closed": tab_closed})
            error(
                f"STALLED {t['id']} silent={int(silent/60)}min "
                f"pid={pid} alive=False tab_closed={tab_closed} "
                f"issue={issue}"
            )
            continue
        # Do not ping a process that is demonstrably alive. This branch only
        # ever sees PING_AFTER_S <= silent < STALL_AFTER_S, i.e. 10-30
        # minutes — precisely the length of one Higgsfield render, so the
        # ping fired every INTERVAL_S at a worker doing exactly what it was
        # told (four times per render on 2026-08-30). The ping is not free
        # either: it lands in the worker's pane and kills the background
        # sleep it polls on, so nudging a busy worker is what stops it
        # working. Silence is a proxy for death and a bad one — the same
        # reasoning the stall branch above already applies. A live but
        # genuinely wedged process is now flagged suspect (never reaped)
        # once silence crosses STALL_AFTER_S — see the branch above.
        if _pid_alive(t.get("pid")):
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

    # Fourth pass — surface sweep (task-92118d4e): any terminal-status task
    # with a live pid/tmux/tab that never went through close_dev at all
    # (direct sqlite status edit, self-exited worker, a cancel). See
    # sweep_terminal_surfaces()'s docstring.
    try:
        surface_reaped = sweep_terminal_surfaces()
    except Exception as e:
        warn(f"watchdog surface sweep error: {e}")
        surface_reaped = []

    return {"pinged": pinged, "stalled": stalled, "reaped": reaped,
            "surface_reaped": surface_reaped,
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
            if out["pinged"] or out["stalled"] or out["reaped"] or out["surface_reaped"]:
                success(f"watchdog: pinged={len(out['pinged'])} stalled={len(out['stalled'])} "
                       f"reaped={len(out['reaped'])} "
                       f"surface_reaped={len(out['surface_reaped'])}")
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            error(f"watchdog scan error: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())

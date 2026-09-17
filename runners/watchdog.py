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
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.notify import info, success, warn, error
from lib.config import host as get_host
from tools.worker_reap import (_cleanup_tmux_ttyd, _pid_alive, close_dev,
                               close_remote, _chrome_running)
from runners.branch_poller import remote_pid_alive
from runners import branch_poller
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


def _sweep_remote_terminal_task(t: dict, host: str) -> dict | None:
    """Remote half of sweep_terminal_surfaces (GAP 1, task-59780ac3).

    No local pid/tmux/tab table can tell this box whether a winbox/contabo
    surface is still alive, so unlike the mac branch above there is no
    liveness check to gate the call on — `close_remote` is called
    unconditionally for every terminal remote task reaching here, and its
    own re-read-and-refuse-unless-terminal guard (ADDENDUM 2) is the safety
    net instead.

    Returns None (not counted toward SWEEP_CAP, not logged) only when there
    was truly nothing to act on — no pid ever recorded on this row, so
    close_remote never even attempted an identity check (matching the local
    branch's "no live surface found, no log line" behaviour). Once a pid was
    present, every outcome is logged — including the recycled-pid refusal
    and an unreachable box — because a "gone"/mismatched pid needs its
    stderr/refused reason visible, not silently swallowed the way the old
    ssh_ok-only gate used to swallow it (task-28866f08: the same `taskkill`
    retried forever, 12,061 log lines, because a nonzero exit code from an
    already-gone pid was indistinguishable from an unreachable box).

    Clears the row's `pid` when the kill actually succeeded (`ssh_ok`) OR
    the identity check proved the pid is no longer this task's process
    (`gone`) — either way there is nothing left worth re-checking next tick.
    Never clears it on `ssh_ok is None` (host unreachable): "could not
    check" must keep being retried, not be read as "handled". Logs at
    `warn` instead of `error` whenever nothing was actually killed (refused,
    gone, or unreachable) — only a real kill stays at `error` severity.
    """
    reap = close_remote(t, reason="reaper: terminal status with live surface")
    attempted = bool(t.get("pid")) or reap.get("command") is not None
    if not attempted:
        return None
    if reap.get("ssh_ok") or reap.get("gone"):
        try:
            db.set_fields(t["id"], actor="watchdog", pid=None)
        except Exception as e:  # never let bookkeeping stop the sweep
            warn(f"could not clear pid after remote reap on {t['id']}: {e}")
    log = error if reap.get("ssh_ok") else warn
    log(
        f"SURFACE-REAPED {t['id']} status={t['status']} host={host} "
        f"command={' '.join(reap.get('command') or [])} ssh_ok={reap.get('ssh_ok')} "
        f"gone={reap.get('gone')} refused={reap.get('refused')} "
        f"stderr={reap.get('stderr')!r}"
    )
    return {"task": t["id"], "status": t["status"], "host": host, **reap}


def sweep_terminal_surfaces() -> list[dict]:
    """Second watchdog pass (task-92118d4e): close any live pid/tmux/tab/
    Chrome-tab-claim a task left behind after reaching a terminal status
    WITHOUT going through close_dev — a direct sqlite status edit, a worker
    that exited on its own, a rate-limited/cancelled worker, a cancel. See
    docs/design/multi-host-workers.md "Teardown invariant".

    Two passes (task-59780ac3 GAP 1; before this, a task whose `host` was a
    remote spoke was skipped here entirely, so a winbox/contabo task that
    went terminal by any route other than close_remote's own callers — a
    direct sqlite edit, a cancel — was never reaped, unlike a mac one).
    Local (host is None/"mac"): the existing pid/tmux/tab/Chrome-tab-claim
    liveness probe below, gated on an actual live surface being found.
    Remote (host is a spoke): this machine cannot see winbox's/contabo's
    process table, tmux server or terminal, so there is no liveness probe to
    gate on — every terminal remote task past REAP_GRACE_S calls
    `tools.worker_reap.close_remote` unconditionally and relies on
    close_remote's own re-read-and-refuse-unless-terminal check (ADDENDUM 2)
    as the safety gate instead. See `_sweep_remote_terminal_task`.

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
        if _silent_seconds(t.get("updated_at")) < REAP_GRACE_S:
            continue
        host = t.get("host")
        if host not in (None, "mac"):
            remote_reap = _sweep_remote_terminal_task(t, host)
            if remote_reap is not None:
                reaped.append(remote_reap)
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


# GH #152: a remote worker's pid can be alive while it's genuinely stuck
# (waiting on the CEO, wedged on a page, etc.) — pid-alive alone proves
# nothing. The HEARTBEAT file the worker touches before every tool call
# (roles/_worker_remote.md) is the actual progress signal; this long past
# no movement means it has stopped working, not just stopped talking.
HEARTBEAT_STALE_S = 20 * 60


def _heartbeat_age_seconds(raw: str) -> float | None:
    """Seconds since an ISO-8601 UTC HEARTBEAT timestamp, or None if `raw`
    doesn't parse — a malformed value must read as "cannot judge", never as
    fresh or stale."""
    try:
        ts = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def _remote_worktree_dir(host_cfg: dict, task: dict) -> str | None:
    """`<host's worktrees root>/<project>__<role>__<task-id>` in the host's
    own path style — the same slug windows/spawn-worker.ps1 builds `$wt`
    from. None when hosts.yaml has no `worktrees` root configured for this
    host, or the task row is missing a field the slug needs (e.g. a legacy
    row created before `host`/`project`/`role` were all populated)."""
    root = host_cfg.get("worktrees")
    if not root or not task.get("project") or not task.get("role") or not task.get("id"):
        return None
    slug = f"{task['project']}__{task['role']}__{task['id']}"
    sep = "\\" if host_cfg.get("os") == "windows" else "/"
    return f"{root.rstrip(chr(92)).rstrip('/')}{sep}{slug}"


def read_remote_heartbeat(host_cfg: dict, task: dict) -> str | None:
    """Raw content of `<worktree>/HEARTBEAT` over ssh, or None when the host
    is unreachable, the worktree path can't be built, or the file simply
    doesn't exist yet — a worker from before GH #152, or one that hasn't
    reached its first tool call. All three cases must read as "cannot
    judge staleness", never as "stale"; only the caller comparing a
    successfully-read timestamp's age may decide that.
    """
    ssh_alias = host_cfg.get("ssh")
    if not ssh_alias:
        return None
    wt_dir = _remote_worktree_dir(host_cfg, task)
    if not wt_dir:
        return None
    if host_cfg.get("os") == "windows":
        cmd = ["ssh", ssh_alias, "type", f"{wt_dir}\\HEARTBEAT"]
    else:
        cmd = ["ssh", ssh_alias, "cat", f"{wt_dir}/HEARTBEAT"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def _check_remote_stall(t: dict, host_name: str) -> dict | None:
    """GAP 3 (task-59780ac3): a remote in_progress task whose worker died
    mid-task used to be invisible forever — this box's own process table
    can't see winbox's/contabo's pids, so the local stall loop always
    skipped host != mac entirely.

    Reuses `runners.branch_poller.remote_pid_alive` (do not reimplement) —
    True/False from a real remote query, or None when the ssh call itself
    failed. None must never collapse into False here: an unreachable box is
    "unknown", not "dead", and flipping a task to stalled on a Wi-Fi/Tailscale
    hiccup would be exactly the false-positive branch_poller.py already
    guards against on its own dead-pid path.

    Two ways to land on `stalled` (GH #152 adds the second):
      - pid confirmed dead (alive is False) — the original GAP 3 fix.
      - pid alive, but its HEARTBEAT file (roles/_worker_remote.md) hasn't
        moved in HEARTBEAT_STALE_S — a live-but-stuck worker, invisible to
        any pid check. A missing HEARTBEAT file (old worker, or one that
        hasn't reached its first tool call yet) is logged only, never
        treated as evidence of a stall either way.

    Never touches a task with no recorded pid (nothing to ask the box about)
    or one silent for less than STALL_AFTER_S. Returns the stall record dict
    (matching the local branch's shape) on stall, else None.
    """
    silent = _silent_seconds(t.get("updated_at"))
    if silent < STALL_AFTER_S:
        return None
    pid = t.get("pid")
    if not pid:
        return None
    try:
        host_cfg = get_host(host_name)
    except ValueError:
        return None
    alive = remote_pid_alive(host_cfg, pid)
    if alive is None:  # ssh unreachable — unknown, never treated as dead
        return None

    if alive is False:
        issue = _file_stalled_issue(t, silent)
        try:
            review = json.loads(t.get("review") or "{}")
        except json.JSONDecodeError:
            review = {}
        review.update({
            "watchdog": "stalled",
            "host": host_name,
            "silent_seconds": int(silent),
            "issue": issue,
            "pid": pid,
            "pid_alive": False,
        })
        db.update_status(t["id"], "stalled", actor="watchdog", review=json.dumps(review))
        error(
            f"STALLED-REMOTE {t['id']} host={host_name} silent={int(silent/60)}min "
            f"pid={pid} alive=False issue={issue}"
        )
        return {"task": t["id"], "silent_s": int(silent), "issue": issue,
               "pid": pid, "pid_alive": False, "host": host_name}

    # alive is True: pid alive proves nothing about progress (GH #152) —
    # check the worker's own heartbeat.
    hb_raw = read_remote_heartbeat(host_cfg, t)
    if hb_raw is None:
        info(f"remote task {t['id']} host={host_name}: no HEARTBEAT file "
             "yet (old worker, or none reached its first tool call) — "
             "cannot judge staleness, leaving in_progress")
        return None
    hb_age = _heartbeat_age_seconds(hb_raw)
    if hb_age is None:
        warn(f"remote task {t['id']} host={host_name}: unparseable "
             f"HEARTBEAT content {hb_raw!r} — cannot judge staleness")
        return None
    if hb_age < HEARTBEAT_STALE_S:
        return None
    issue = _file_stalled_issue(t, silent)
    try:
        review = json.loads(t.get("review") or "{}")
    except json.JSONDecodeError:
        review = {}
    review.update({
        "watchdog": "stalled",
        "host": host_name,
        "silent_seconds": int(silent),
        "issue": issue,
        "pid": pid,
        "pid_alive": True,
        "heartbeat_age_seconds": int(hb_age),
    })
    db.update_status(
        t["id"], "stalled", actor="watchdog", review=json.dumps(review),
        delegate_log=(f"heartbeat stale {int(hb_age/60)}min (pid {pid} alive) "
                      f"on {host_name}"),
    )
    error(
        f"STALLED-REMOTE-HEARTBEAT {t['id']} host={host_name} pid={pid} "
        f"alive=True heartbeat_age={int(hb_age/60)}min issue={issue}"
    )
    return {"task": t["id"], "silent_s": int(silent), "issue": issue,
           "pid": pid, "pid_alive": True, "heartbeat_age_s": int(hb_age),
           "host": host_name}


def scan_once() -> dict:
    pinged = []
    stalled = []
    rows = db.list_tasks(status="in_progress", limit=200)
    for t in rows:
        # Remote workers (host != mac) have pids that live on ANOTHER machine;
        # _pid_alive() here checks the Mac's process table and would read every
        # one of them as dead (a winbox browser_operator was flipped to
        # 'stalled' this way on 2026-09-07). _check_remote_stall asks the box
        # itself over ssh instead (GAP 3, task-59780ac3) — before that fix a
        # remote task whose worker actually died just sat in_progress forever.
        host = t.get("host") or "mac"
        if host != "mac":
            remote_stall = _check_remote_stall(t, host)
            if remote_stall is not None:
                stalled.append(remote_stall)
            continue
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

    # Fifth pass — branch poller (task-28866f08): runners/branch_poller.py
    # exists, is correct, and is scheduled by nothing (no launchd, no cron,
    # no systemd, no process) — this is the first thing that would ever call
    # it. DEFAULT OFF on purpose: task-41684e16's branch is pushed with a
    # REPORT.md on it, so the first tick here would flip it to `review`
    # (releasing its path locks) and then call close_remote on its recorded
    # pid — which the CEO's ruling (2026-09-07) says must never happen to a
    # worker that may still be working. Step 2's remote_pid_matches_task
    # guard makes that specific call safe (that pid is now BlueStacks, which
    # the guard refuses to kill), but the CEO still decides when to flip
    # this on, not the code — hence the flag, default unset.
    if os.environ.get("ORG_WATCHDOG_BRANCH_POLL") == "1":
        try:
            branch_poller.tick()
        except Exception as e:
            warn(f"watchdog branch_poll error: {e}")

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

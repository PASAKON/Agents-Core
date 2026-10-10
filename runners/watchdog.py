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

W1.5 duty split (org-mesh): on a shared ledger every duty has exactly one
owner per row. LOCAL duties (pid liveness, stall, tmux/tab close, finished-DEV
reap) act only on rows this box runs (`is_local_row`). REMOTE duties (ssh
stall, close_remote, branch poll, blocked_human escalation) act only on rows
this box dispatched (`is_remote_row` / `is_dispatched_here`). A row neither is
ours is skipped -- never stalled, never cancelled. Predicates:
tools/worker_reap.py; the per-duty table: docs/reports/task-a137ecca/REPORT.md.

Usage:
    python -m runners.watchdog                   # one-shot scan
    python -m runners.watchdog --loop            # forever, sleep INTERVAL_S
    python -m runners.watchdog --interval 300    # custom sleep
    python -m runners.watchdog --mesh-probe      # probe peers now
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db, mesh
from lib.notify import info, success, warn, error
from lib.config import host as get_host, hosts as all_hosts, self_host
from tools.worker_reap import (_cleanup_tmux_ttyd, _pid_alive, close_dev,
                               close_remote, _chrome_running, is_dispatched_here,
                               is_local_row, is_remote_row, row_host)
from runners.branch_poller import remote_pid_alive
from runners import branch_poller
from tools import delegate
from tools import disk_queue
from tools import send_to_cto
from tools import send_to_cxo
from tools import work_watch
from tools.gc_stale_tasks import gc_stale_tasks
from tools import tmux_session

# Chrome tabs on these org generation sites are the ones ADDENDUM 1's
# unclaimed-tab log line cares about — a stray shell/bank/docs tab is just
# the CEO's own browsing, not a leak.
_ORG_TAB_DOMAINS = ("higgsfield.ai", "flow.google.com", "grok.com")

PING_AFTER_S = 10 * 60
STALL_AFTER_S = 30 * 60
INTERVAL_S = 300
MESH_PROBE_INTERVAL_S = 900
MESH_PROBE_STATE = Path(__file__).resolve().parent.parent / "state/watchdog-mesh-probe.json"
_mesh_probe_state: dict | None = None
_mesh_probe_skip_noted = False
_mesh_probe_details: dict[str, str] = {}


def _mesh_probe_interval() -> int:
    try:
        value = int(os.environ.get("ORG_MESH_PROBE_INTERVAL_S", ""))
    except ValueError:
        return MESH_PROBE_INTERVAL_S
    return value if value >= 60 else MESH_PROBE_INTERVAL_S


def _mesh_probe_available() -> bool:
    return (os.environ.get("ORG_MESH_PROBE") != "0"
            and Path(mesh.SSH_KEY).expanduser().is_file())


def _mesh_probe_detail(value: object) -> str:
    try:
        from tools.node_dispatch import _redact
    except ImportError:
        return "detail unavailable (credential redactor unavailable)"
    return " ".join(_redact(str(value)).split())[-200:]


def _load_mesh_probe_state() -> dict:
    try:
        state = json.loads(MESH_PROBE_STATE.read_text(encoding="utf-8"))
        if not (isinstance(state, dict) and isinstance(state["hosts"], dict)
                and isinstance(state["last_probe"], (int, float))):
            raise ValueError("invalid mesh probe state")
        for row in state["hosts"].values():
            if not (isinstance(row, dict)
                    and type(row["bad_count"]) is int and row["bad_count"] >= 0
                    and type(row["alerted"]) is bool
                    and isinstance(row["bad_since"], (int, float))):
                raise ValueError("invalid mesh probe host state")
        return state
    except (OSError, ValueError, KeyError, TypeError):
        return {"last_probe": 0, "hosts": {}}


def _save_mesh_probe_state() -> None:
    MESH_PROBE_STATE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=MESH_PROBE_STATE.parent,
                                         delete=False) as f:
            temporary = f.name
            json.dump(_mesh_probe_state, f)
        os.replace(temporary, MESH_PROBE_STATE)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def _alert_mesh_probe(host: str, classification: str, detail: str) -> None:
    # Same durable CTO/CEO-visible channel as _file_stalled_issue; no task
    # owns a host outage, so _send_ping's worker mailbox is not appropriate.
    from tools.gh_issue import create_issue
    create_issue("mooniex-agents", f"watchdog: mesh host {host} {classification}",
                 f"Mesh probe from {self_host()} failed twice consecutively.\n\n"
                 f"Host: {host}\nClass: {classification}\nDetail: {detail}\n\n"
                 "This blocks remote spawns, letters and C-level starts. "
                 "Check the dispatch key and the host's mesh service.",
                 labels=["watchdog", "agent"])


def _probe_mesh_hosts(*, force: bool = False) -> dict[str, str]:
    """Probe configured peers, debounce outages and remember reported ones.

    dispatch's probe timeout is 30 s (including the ssh dial); no retries.
    force bypasses only the interval, never the key check or off switch.
    """
    global _mesh_probe_state, _mesh_probe_skip_noted, _mesh_probe_details
    _mesh_probe_details = {}
    if not _mesh_probe_available():
        if not _mesh_probe_skip_noted:
            info("watchdog: mesh probe skipped (disabled or no dispatch key)")
            _mesh_probe_skip_noted = True
        return {}
    if _mesh_probe_state is None:
        _mesh_probe_state = _load_mesh_probe_state()
    now = time.time()
    if not force and now - _mesh_probe_state["last_probe"] < _mesh_probe_interval():
        return {}
    _mesh_probe_state["last_probe"] = now
    result = {}
    for host, config in all_hosts().items():
        if host == self_host() or not config.get("mesh_ssh"):
            continue
        try:
            reply = mesh.dispatch(host, "probe")
            classification = "ok" if reply.get("ok") is True else "refused/error"
            detail = "probe succeeded" if classification == "ok" else reply.get("error", "probe failed")
        except mesh.MeshUnreachable as e:
            classification, detail = "unreachable", e
        except Exception as e:
            classification, detail = "refused/error", e
        detail = _mesh_probe_detail(detail)
        result[host] = classification
        _mesh_probe_details[host] = detail
        row = _mesh_probe_state["hosts"].setdefault(
            host, {"bad_count": 0, "bad_since": 0, "alerted": False})
        if classification == "ok":
            if row["bad_count"]:
                success(f"host {host} reachable again after {int((now - row['bad_since']) / 60)} min")
            row.update(bad_count=0, bad_since=0, alerted=False)
        else:
            if not row["bad_count"]:
                row["bad_since"] = now
            row["bad_count"] += 1
            if row["bad_count"] >= 2 and not row["alerted"]:
                error(f"watchdog: mesh host {host} {classification}: {detail}")
                try:
                    _alert_mesh_probe(host, classification, detail)
                    row["alerted"] = True
                except Exception as e:
                    warn(f"watchdog: mesh alert failed: {_mesh_probe_detail(e)}")
            else:
                warn(f"watchdog: mesh host {host} {classification}: {detail}")
    _save_mesh_probe_state()
    return result


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


def _mac_surfaces() -> bool:
    """iTerm tabs, osascript and the Chrome tab-claim registry exist only on
    the Mac. On any other platform the passes that close those surfaces
    (stall tab-close, finished-DEV reap, the local half of the terminal
    sweep) are skipped rather than left to raise on a missing `osascript`
    (Org Mesh W0.4; W1.5 gives Linux its own local duties)."""
    return sys.platform == "darwin"


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
    Local (`is_local_row`: host is None or self_host()): the existing pid/
    tmux/tab/Chrome-tab-claim liveness probe below, gated on an actual live
    surface being found. Darwin only -- see `_mac_surfaces`.
    Remote (`is_remote_row`: host is another box AND this box dispatched it,
    W1.5): this machine cannot see winbox's/contabo's process table, tmux
    server or terminal, so there is no liveness probe to gate on — every
    terminal remote task past REAP_GRACE_S calls
    `tools.worker_reap.close_remote` unconditionally and relies on
    close_remote's own re-read-and-refuse-unless-terminal check (ADDENDUM 2)
    as the safety gate instead. See `_sweep_remote_terminal_task`.
    A row that is neither (another box's own or another box's dispatch) is
    skipped: on a shared ledger each row has one owner per duty.

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
    mac = _mac_surfaces()

    claims: dict = {}
    if mac:
        try:
            from scripts.browser.tab_registry import all_claims
            claims = all_claims()
        except Exception as e:
            warn(f"sweep: tab_registry import failed: {e}")
        _log_unclaimed_org_tabs(set(claims.keys()))
    claimed_task_ids = set(claims.values())

    rows: list[dict] = []
    for status in TERMINAL_SURFACE_STATUSES:
        rows.extend(db.list_tasks(status=status, limit=200))
    if not rows:
        return reaped

    live_tmux = _live_tmux_sessions()
    live_tab_ids = _live_task_tab_ids() if mac else set()

    for t in rows:
        if len(reaped) >= SWEEP_CAP:
            break
        task_id = t["id"]
        if _silent_seconds(t.get("updated_at")) < REAP_GRACE_S:
            continue
        if not is_local_row(t):
            # W1.5: the box that dispatched a remote row reaps it; every other
            # box sharing the ledger leaves it alone (no second ssh kill).
            if is_remote_row(t):
                remote_reap = _sweep_remote_terminal_task(t, row_host(t))
                if remote_reap is not None:
                    reaped.append(remote_reap)
            continue
        if not mac:
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


# W2.7 F9 (task-42fdcda7): the slug below ends up inside a command that a
# remote shell parses (ssh joins its argv into one string for cmd.exe or sh,
# and tools/remote_worker_log puts it inside a PowerShell string). project and
# role come from the task row, which create_task does not check, so a row with
# project `x & <command> &` would run <command> under the admin key. Plain
# tokens only; anything else reads as "cannot build the path".
_SLUG_TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
_TASK_ID_RE = re.compile(r"task-[0-9a-f]{8}")


def _remote_worktree_dir(host_cfg: dict, task: dict) -> str | None:
    """`<host's worktrees root>/<project>__<role>__<task-id>` in the host's
    own path style — the same slug windows/spawn-worker.ps1 builds `$wt`
    from. None when hosts.yaml has no `worktrees` root configured for this
    host, or the task row is missing a field the slug needs (e.g. a legacy
    row created before `host`/`project`/`role` were all populated), or a
    field is not a plain `[A-Za-z0-9_-]` token (W2.7 F9)."""
    root = host_cfg.get("worktrees")
    if not root:
        return None
    for field in ("project", "role", "id"):
        value = task.get(field)
        if not isinstance(value, str) or not _SLUG_TOKEN_RE.fullmatch(value):
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
    if not isinstance(task.get("id"), str) or not _TASK_ID_RE.fullmatch(task["id"]):
        return None  # W2.7 F9: only a real task id reaches the remote shell
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


def _mesh_pid_alive(t: dict, host_name: str, host_cfg: dict, pid: int) -> bool | None:
    """W2.3 (ORG_MESH_DISPATCH): ask the box itself, `pid_alive <task-id>`, in
    place of the per-OS ssh query. Same True/False/None contract as
    `remote_pid_alive`: no answer is None (unknown, never dead). A box that
    answered "cannot say" (windows refuses pid_alive until W3.3; the row is not
    on its ledger) gets today's ssh query, so it is no blinder than with the
    flag off."""
    try:
        reply = mesh.dispatch(host_name, "pid_alive", t["id"])
    except mesh.MeshUnreachable:
        return None
    if not reply.get("ok"):
        return remote_pid_alive(host_cfg, pid)
    alive = (reply.get("result") or {}).get("alive")
    return alive if isinstance(alive, bool) else None


def _retry_queued_remote() -> list[dict]:
    """W2.3: one more spawn attempt for every `queued_remote` row this box
    dispatched to another host (a mesh spawn that got no answer). At most one
    attempt per row per pass: a pass that fails leaves the row queued, and
    tools.delegate.mesh_spawn_worker counts the attempts in `delegate_log` and
    the `status_queued_remote` events. Off unless ORG_MESH_DISPATCH is on.

    A host that gives no answer (the row comes back still `queued_remote`)
    ends that host's turn for this pass, as in `_retry_letters` (W2.7 F12):
    each dial can wait ConnectTimeout, or a verb's full timeout (300 s for
    spawn_worker) when the host hangs instead of refusing, so dialling every
    row of a dead host stalls the watchdog, and each row would spend an
    attempt on the same outage. Rows keep their order: the head of the host's
    queue is the one that spends attempts.

    A row that has been unreachable `mesh.max_attempts()` times (default 12,
    about 55 minutes at this tick; ORG_MESH_MAX_ATTEMPTS) is failed instead of
    dialled again: `delegate.give_up_queued_remote` releases its path locks and
    tells the owner once. That needs no dial, so it happens even for a row
    behind a silent host, and it does not make that host silent."""
    if not mesh.enabled():
        return []
    retried = []
    silent_hosts: set[str] = set()
    cap = mesh.max_attempts()
    for t in db.list_tasks(status="queued_remote", limit=200):
        if not is_remote_row(t):  # another box's row, or no target host yet
            continue
        host_name = row_host(t)
        try:
            attempts = delegate._queued_remote_attempts(t["id"])
            if attempts >= cap:
                row = delegate.give_up_queued_remote(t["id"], host_name, attempts)
                retried.append({"task": t["id"], "host": host_name, "status": row["status"]})
                info(f"watchdog: queued_remote {t['id']} host={host_name} gave up after "
                     f"{attempts} attempts -> {row['status']}")
                continue
        except Exception as e:  # one bad row must not stop the others
            warn(f"watchdog: queued_remote cap check failed for {t['id']}: {e}")
            continue
        if host_name in silent_hosts:
            continue
        try:
            row = delegate.mesh_spawn_worker(t["id"], host_name)
        except Exception as e:  # one bad row must not stop the others
            warn(f"watchdog: queued_remote retry failed for {t['id']}: {e}")
            continue
        retried.append({"task": t["id"], "host": host_name, "status": row["status"]})
        info(f"watchdog: queued_remote retry {t['id']} host={host_name} -> {row['status']}")
        if row["status"] == "queued_remote":
            silent_hosts.add(host_name)
    return retried


def _retry_letters() -> list[dict]:
    """W2.4: one more `deliver_letter` attempt for every pending letter THIS host
    sent to another host (a cross-host send_to_cxo whose host did not answer). At
    most one attempt per letter per pass; `send_to_cxo.dispatch_letter` counts it
    (`letters.attempts`, `failed` at 5), never re-sends a delivered letter, and
    never counts a letter that is no longer pending. Off unless ORG_MESH_DISPATCH
    is on.

    Only letters with `from_host` == this host are retried. On a shared ledger
    every box's watchdog sees every pending letter; without this filter they would
    all dial the same row, the receiver would get it twice and an outage would
    spend its attempts several times per pass. A letter whose `from_host` is NULL
    (written before that column existed) is retried by nobody: no owner is guessed.

    A host that gives no answer ends that host's turn for this pass: the rest of
    its queue is not dialled (each dial can wait ConnectTimeout) and, more to the
    point, does not each lose an attempt to one outage. Letters keep their order:
    the head of the queue is the one that spends attempts."""
    if not mesh.enabled():
        return []
    here = self_host()
    tried = []
    for host_name in all_hosts():
        if host_name == here:
            continue
        for letter in db.pending_letters(host_name, from_host=here):
            try:
                outcome = send_to_cxo.dispatch_letter(letter["id"])
            except Exception as e:  # one bad letter must not stop the others
                warn(f"watchdog: letter {letter['id']} retry failed: {e}")
                continue
            tried.append({"letter": letter["id"], "host": host_name, "outcome": outcome})
            info(f"watchdog: letter {letter['id']} -> {host_name}: {outcome}")
            if outcome == "unreachable":
                break
    return tried


def _check_remote_stall(t: dict, host_name: str) -> dict | None:
    """GAP 3 (task-59780ac3): a remote in_progress task whose worker died
    mid-task used to be invisible forever — this box's own process table
    can't see winbox's/contabo's pids, so the local stall loop always
    skipped host != self_host() entirely.

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
    if mesh.enabled():
        alive = _mesh_pid_alive(t, host_name, host_cfg, pid)
    else:
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


# Disk-queue drain headroom above the disk-red floor (ADR 0030 §D,
# task-dbe47b9b, CEO 2026-09-23): a spawn refused below gauge.orange is
# queued (tools/disk_queue.py) rather than dropped; this margin is how much
# free space must return before scan_once tries the oldest queued task
# again. +1 GB, not exactly `orange`, so a drain doesn't spawn a worker
# right at the same line that would immediately re-refuse the NEXT one.
DISK_QUEUE_RESUME_MARGIN_GB = 1.0


def _drain_disk_queue() -> dict | None:
    """Pop and spawn at most ONE queued task per scan_once tick, oldest
    first, through the same `tools.delegate.delegate_task` path the original
    spawn attempt used — never several at once (a burst of spawns the moment
    space returns is exactly the kind of thing that emptied the disk on
    2026-09-23; the next tick re-measures and drains one more).

    A task cancelled/closed while it waited is dropped from the queue
    without being spawned (checked here, not just left for `delegate_task`
    to refuse again) and the scan continues to the next-oldest entry within
    the SAME tick — only an actual `delegate_task` call counts against the
    "one per tick" limit, so skipping dead entries first doesn't cost extra
    ticks. Returns None when nothing was spawned (empty queue, space still
    below the resume margin, or every queued entry was dead), else a small
    dict describing what was spawned."""
    if not disk_queue.all_entries():
        return None
    free_gb = delegate._free_gb()
    orange_gb = delegate._disk_orange_floor_gb()
    if free_gb < orange_gb + DISK_QUEUE_RESUME_MARGIN_GB:
        return None

    for entry in disk_queue.all_entries():
        task_id = entry["task_id"]
        task = db.get_task(task_id)
        if task is None or task["status"] != "pending":
            disk_queue.pop(task_id)  # cancelled/closed/reset elsewhere meanwhile
            continue
        disk_queue.pop(task_id)
        try:
            asyncio.run(delegate.delegate_task(task_id))
        except Exception as e:
            error(f"watchdog: disk queue spawn failed for {task_id}: {e}")
            return {"task": task_id, "error": str(e)}
        success(f"watchdog: disk queue spawning {task_id} "
               f"(free {free_gb:.1f} GB >= {orange_gb + DISK_QUEUE_RESUME_MARGIN_GB:.1f} GB)")
        # No letter here (CEO 2026-09-23: permanent watchdog letters only when
        # critical or risky). The start is a good-news event: it is recorded
        # in the task's own delegate_log and the worker's kickoff; the owner
        # was already told once, at queue time, when its spawn was refused.
        return {"task": task_id, "free_gb": free_gb}
    return None


# W4.2: a host whose provision failed is left alone this long, so a broken row does
# not mint and revoke a client secret on every pass.
PROVISION_BACKOFF_S = 3600
_provision_retry_at: dict[str, float] = {}
# W4.6a F1: a pending host nobody approved is skipped by provision_pending. The pass says so once
# per PROVISION_BACKOFF_S, not on every scan. Kept apart from _provision_retry_at on purpose: that
# one would also hold the host back for up to an hour AFTER the operator approves it.
_unapproved_noted_until: dict[str, float] = {}


def _provision_identities() -> list[dict]:
    """W4.2 / W4.2b: provision every approved `pending_identity` host (tools.hq_join.provision):
    seal it a bundle {v: 2, host, token_url} to its age key and register its GitHub deploy
    key. It makes no Infisical call and creates no Infisical identity: the node asks the hub's
    token service (tools/node_token_api.py) at token_url for the Claude token. Off unless
    ORG_W42_PROVISION=1 (hq_join.provision_pending does nothing otherwise). token_url is read
    from ORG_NODE_TOKEN_URL (http://<hub tailnet IPv4>:792/v1/token); without it every row fails
    as `no_token_url`, which the loop below logs and retries after PROVISION_BACKOFF_S. A row
    without `approved_at` is skipped as `not_approved`, not failed. One bad row never stops the
    others."""
    from tools import hq_join  # lazy: keeps the watchdog's import list untouched
    now = time.time()
    results = hq_join.provision_pending(
        skip={h for h, at in _provision_retry_at.items() if at > now})
    waiting = set()
    for r in results:
        if "error" in r:
            _provision_retry_at[r["host"]] = now + PROVISION_BACKOFF_S
            warn(f"watchdog: provision of {r['host']} failed: {r['error']}")
        elif r.get("skipped") == "not_approved":
            waiting.add(r["host"])
            if _unapproved_noted_until.get(r["host"], 0) <= now:
                _unapproved_noted_until[r["host"]] = now + PROVISION_BACKOFF_S
                warn(f"watchdog: {r['host']} joined but is NOT approved, so it gets no identity: "
                     f"compare its key fingerprint (`hq_join status`) with the one on the "
                     f"node's screen, then `hq_join approve`")
        elif r.get("changed"):
            info(f"watchdog: provisioned identity for {r['host']}")
    for host in [h for h in _unapproved_noted_until if h not in waiting]:
        del _unapproved_noted_until[host]   # approved or gone: it is said again if it comes back
    return results


def scan_once() -> dict:
    pinged = []
    stalled = []
    rows = db.list_tasks(status="in_progress", limit=200)
    for t in rows:
        # Remote workers (host != self_host()) have pids that live on ANOTHER
        # machine; _pid_alive() here checks this box's process table and would
        # read every one of them as dead (a winbox browser_operator was flipped to
        # 'stalled' this way on 2026-09-07). _check_remote_stall asks the box
        # itself over ssh instead (GAP 3, task-59780ac3) — before that fix a
        # remote task whose worker actually died just sat in_progress forever.
        # W1.5: only the box that dispatched the row asks; on a shared ledger a
        # row dispatched elsewhere is not ours to stall (or to ssh about).
        if not is_local_row(t):
            if is_remote_row(t):
                remote_stall = _check_remote_stall(t, row_host(t))
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
                # No iTerm tab off the Mac (`_mac_surfaces`); the tmux
                # cleanup below is the surface on Linux.
                tab_closed = _close_tab(t["id"]) if _mac_surfaces() else False
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
        # W1.5: a status flip plus a GH issue touches no local resource, so the
        # one owner is the box that dispatched the row (else each box files one).
        if not is_dispatched_here(t):
            continue
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
    # close_dev closes an iTerm tab and Chrome tabs via osascript, so this
    # pass is Darwin-only (`_mac_surfaces`).
    finished_rows = []
    if _mac_surfaces():
        # W1.5: pid + tab are this box's own process table, so local rows only
        # (before, another box's pid could match a stranger's process here).
        finished_rows = [t for t in (db.list_tasks(status="review", limit=200)
                                     + db.list_tasks(status="done", limit=200))
                         if is_local_row(t)]
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

    # Sixth pass — disk queue drain (ADR 0030 §D, task-dbe47b9b): spawn at
    # most one task queued by tools/delegate.py's disk-floor refusal, once
    # free space clears gauge.orange + DISK_QUEUE_RESUME_MARGIN_GB. See
    # _drain_disk_queue()'s docstring.
    try:
        disk_queue_spawned = _drain_disk_queue()
    except Exception as e:
        warn(f"watchdog disk queue drain error: {e}")
        disk_queue_spawned = None

    # Sixth-b pass — mesh spawns that got no answer (W2.3): one retry per
    # queued_remote row this box dispatched. No-op unless ORG_MESH_DISPATCH is on.
    try:
        _retry_queued_remote()
    except Exception as e:
        warn(f"watchdog queued_remote retry error: {e}")

    # Sixth-c pass — cross-host letters that got no answer (W2.4): one retry per
    # pending letter addressed to another host. No-op unless ORG_MESH_DISPATCH is on.
    try:
        _retry_letters()
    except Exception as e:
        warn(f"watchdog letter retry error: {e}")

    # Sixth-d pass — identity for joined nodes (W4.2): provision every
    # pending_identity host. No-op unless ORG_W42_PROVISION=1 on the admin host.
    try:
        _provision_identities()
    except Exception as e:
        warn(f"watchdog identity provision error: {e}")

    # Sixth-e pass — periodic mesh reachability, independent of dispatch flag.
    try:
        mesh_probe = _probe_mesh_hosts()
    except Exception as e:
        warn(f"watchdog mesh probe error: {_mesh_probe_detail(e)}")
        mesh_probe = {}

    # Seventh pass — Work/ watcher (Work/RULES.md rules 7-8, ADR 0030 §D,
    # task-dbe47b9b): alert the owning CTO or raise a LungNote to-do for any
    # Work/<task-id>/ folder whose task ended (or whose worker died) with
    # bytes still unfiled. See tools/work_watch.py's module docstring.
    try:
        work_watch_result = work_watch.watch()
    except Exception as e:
        warn(f"watchdog work watch error: {e}")
        work_watch_result = {"alerted": [], "lungnote_filed": [], "green": []}

    return {"pinged": pinged, "stalled": stalled, "reaped": reaped,
            "surface_reaped": surface_reaped,
            "scanned": len(rows) + len(human_rows),
            "gc_cancelled": len(gc_cancelled),
            "disk_queue_spawned": disk_queue_spawned,
            "mesh_probe": mesh_probe,
            "work_watch": work_watch_result}


def main() -> int:
    ap = argparse.ArgumentParser(description="Watchdog for stuck DEV tasks")
    ap.add_argument("--mesh-probe", action="store_true",
                    help="probe mesh hosts now, ignoring the interval")
    ap.add_argument("--loop", action="store_true",
                    help="run forever, sleep --interval between scans")
    ap.add_argument("--interval", type=int, default=INTERVAL_S,
                    help=f"loop sleep seconds (default {INTERVAL_S})")
    args = ap.parse_args()

    if args.mesh_probe:
        if not _mesh_probe_available():
            return 2
        out = _probe_mesh_hosts(force=True)
        for host, classification in out.items():
            print(f"{host} {classification} {_mesh_probe_details[host][:120]}")
        return 0 if all(value == "ok" for value in out.values()) else 1

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

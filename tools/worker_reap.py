"""Single place that ends a DEV: terminate its process, close its iTerm tab
and any Chrome tab it claimed in the browser-tabs registry.

Context (task-78ab64ba): `mcp__org__submit_report` sets status='review' and
returns, but nothing ever closes the DEV's session — it sits at an idle
prompt forever. Two layers close the gap, in this order (CEO ruling
2026-08-12, do not collapse them):

  - Layer 1 — the C-level decides. `tools/git_ops.py:merge_task` calls
    `close_dev` once a merge lands. This is the normal path.
  - Layer 2 — `runners/watchdog.py`'s finished-reap pass is a floor, not a
    decider: it only calls `close_dev` when layer 1 never happened at all,
    after FINISHED_REAP_AFTER_S, and logs it as the anomaly it is.

`close_dev` is safe to call from both places (and by hand) because it never
raises: an ineligible task (wrong status, no pid, not found) is a refusal
recorded in the returned dict, not an exception, and a second call on an
already-reaped task returns cleanly too.

Usage:
    python3 -m tools.worker_reap <task_id> [--reason TEXT]   # reap one task
    python3 -m tools.worker_reap --list                      # DEVs alive now
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db
from lib.notify import info, warn
from tools.itermtab import close_tab
from tools import tmux_session

# Statuses close_dev is allowed to act on: 'review' (a CTO may reject/close a
# DEV without merging) plus the full terminal set (task-92118d4e) — every
# status where the task is over and won't restart on its own. Deliberately
# excludes db.ACTIVE_STATUSES (pending/in_progress/rate_limited/conflict —
# still working or awaiting retry) and 'blocked_human' (awaiting the CEO) —
# see close_dev's docstring point 1.
REAPABLE_STATUSES = ("review", "done", "failed", "cancelled", "stalled",
                    "reverted", "merged")

# Grace period between SIGTERM and SIGKILL escalation.
TERM_GRACE_S = 3

# The exact "surface must be torn down" set (ADDENDUM 2, task-92118d4e, CEO
# rule 2026-09-07): {done, failed, cancelled, reverted, merged}. Mirrors
# runners/watchdog.py's TERMINAL_SURFACE_STATUSES — duplicated rather than
# imported (watchdog already imports close_dev from this module, so an
# import the other way would cycle). Keep the two definitions in sync if
# either changes. Used only by close_remote's terminal-status guard below;
# REAPABLE_STATUSES (below) stays the broader set for a directed close_dev
# call, which may legitimately act on 'review'/'stalled' too.
_TERMINAL_SURFACE_STATUSES = frozenset(
    db.VALID_STATUS - set(db.ACTIVE_STATUSES)
    - {"review", "blocked_human", "stalled"}
)


def _pid_alive(pid: int | None) -> bool:
    """True if a process with this PID exists and is reachable.

    Uses kill(pid, 0) — sends no signal, just probes existence + permission.
    Returns False for None, 0, or any error.
    """
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _pid_matches_task(pid: int, task_id: str) -> bool:
    """True if the live process at `pid` still looks like this task's DEV.

    There is no such check anywhere else in the codebase — after a 60-minute
    delay the OS may well have recycled the pid onto something unrelated,
    and killing it blind would kill a stranger's process. Reads the
    process's command line and requires it to contain `task_id`. A dead
    pid, a permission error, or a missing `ps` all read as "does not
    match" — the safe default is to never signal.
    """
    try:
        r = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return False
    return r.returncode == 0 and task_id in r.stdout


def _terminate_pid(pid: int) -> str:
    """SIGTERM, wait TERM_GRACE_S, SIGKILL only if still alive.

    Returns which signal actually ended it ("SIGTERM" or "SIGKILL").
    """
    os.kill(pid, 15)  # SIGTERM
    time.sleep(TERM_GRACE_S)
    if _pid_alive(pid):
        os.kill(pid, 9)  # SIGKILL
        return "SIGKILL"
    return "SIGTERM"


def _cleanup_tmux_ttyd(task: dict) -> dict:
    """Kill tmux session + ttyd process for tmux-backed tasks.

    Factored out of runners/watchdog.py (task-78ab64ba) so its own
    stalled-in_progress reap and this module's finished-DEV reap share one
    implementation instead of two copies drifting apart. Idempotent:
    missing session / pid silently treated as already-cleaned.

    Tries both the DB's recorded `tmux_session` column AND the naming
    convention (`wd-<id>`, `tools.tmux_session.session_name_for`) — task-
    92118d4e: the two agree whenever a task went through the normal delegate
    spawn path (which writes the column from that same convention), but a
    task that reached its status by some other route (a direct sqlite edit,
    a tmux session started outside any spawn path — exactly what the
    watchdog's terminal-surface sweep exists to catch) may have a live
    `wd-<id>` session with nothing recorded in the column at all. tmux.kill
    on a name with no session is a safe no-op, so trying both never risks
    killing the wrong thing.
    """
    out = {"tmux_killed": False, "ttyd_killed": False}
    try:
        from tools import tmux_session as tmux
    except Exception as e:
        warn(f"tmux_session import failed: {e}")
        return out
    sessions = {s for s in (task.get("tmux_session"),
                           tmux.session_name_for(task.get("id") or "")) if s}
    for sess in sessions:
        try:
            if tmux.kill(sess):
                out["tmux_killed"] = True
        except Exception as e:
            warn(f"tmux kill failed for {sess}: {e}")
    ttyd_pid = task.get("ttyd_pid")
    if ttyd_pid:
        try:
            out["ttyd_killed"] = tmux.stop_ttyd(int(ttyd_pid))
        except Exception as e:
            warn(f"ttyd stop failed for pid={ttyd_pid}: {e}")
    return out


def _chrome_running() -> bool:
    """True iff Google Chrome has a live process, per System Events.

    A claimed tab in a Chrome that has since quit is not an error — there
    is nothing to close — so callers treat any False here as a silent skip,
    not a warning.
    """
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to (name of processes) '
             'contains "Google Chrome"'],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return False
    return r.returncode == 0 and r.stdout.strip() == "true"


def _close_chrome_tabs(tab_ids: list) -> list[str]:
    """Close each Chrome tab whose `id of tab` is in `tab_ids`.

    One osascript call, ids bound explicitly — never "current tab" or
    "front window" (tools/itermtab.py's list_task_tabs carries the same
    rule, for the same reason: an untargeted close has hit the wrong window
    before). Matching tabs are collected across every window BEFORE any is
    closed, then closed in a second pass — closing while still iterating
    `tabs of w` can invalidate the rest of that same live enumeration.

    Ids are cast through int() before being spliced into the AppleScript
    source, both to reject garbage and to rule out script injection via a
    malformed registry entry — then spliced back in as QUOTED string
    literals, not bare numbers: confirmed live (task-92118d4e) that Chrome's
    own `id of tab` is AppleScript class `text`, not a number, so a bare-
    number `targetIds` list silently matched nothing (`contains` never
    fired) and every close was a no-op that still went on to clear the
    registry claim, orphaning the tab from tracking while leaving it open.
    Returns the ids actually closed (as strings, matching the registry's
    own string tab_id); returns [] with no osascript call at all when
    there is nothing to close or Chrome is not running — the "skip
    silently if Chrome is not running" requirement.
    """
    try:
        numeric_ids = [int(t) for t in tab_ids if t is not None and str(t).strip()]
    except (TypeError, ValueError):
        return []
    if not numeric_ids or not _chrome_running():
        return []
    id_list = ", ".join(f'"{i}"' for i in numeric_ids)
    script = f'''
tell application "Google Chrome"
  set targetIds to {{{id_list}}}
  set matches to {{}}
  repeat with w in windows
    repeat with t in tabs of w
      if targetIds contains (id of t) then
        set end of matches to t
      end if
    end repeat
  end repeat
  set closedIds to {{}}
  repeat with m in matches
    set tid to id of m
    close m
    set end of closedIds to (tid as text)
  end repeat
  set AppleScript's text item delimiters to ","
  set outStr to closedIds as text
  set AppleScript's text item delimiters to ""
  return outStr
end tell
'''
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=15)
    except Exception as e:
        warn(f"close Chrome tabs failed: {e}")
        return []
    if r.returncode != 0:
        return []
    out = r.stdout.strip()
    return out.split(",") if out else []


def _open_chrome_tab_ids() -> set[str] | None:
    """Ids of every tab currently open in Chrome, as strings — or None when
    Chrome is not running (unknowable, not empty). Used to tell "the tab is
    already gone" (clear the claim) from "the close failed" (keep it)."""
    if not _chrome_running():
        return None
    try:
        r = subprocess.run(
            ["osascript", "-e",
             'tell application "Google Chrome" to set out to ""\n'
             'tell application "Google Chrome"\n'
             '  repeat with w in windows\n'
             '    repeat with t in tabs of w\n'
             '      set out to out & (id of t as text) & linefeed\n'
             '    end repeat\n'
             '  end repeat\n'
             'end tell\n'
             'return out'],
            capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None
        return {ln.strip() for ln in r.stdout.splitlines() if ln.strip()}
    except Exception:
        return None


def _close_claimed_chrome_tabs(task_id: str) -> list[str]:
    """Close every Chrome tab task_id has claimed in the browser-tabs
    registry (task-92118d4e ADDENDUM 1: "Chrome tabs are a surface too"),
    then clear its claim. Only ever touches ids in THIS task's own claim —
    never an org tab (higgsfield.ai/flow.google.com/grok.com) with no claim
    at all, which is the sweep's job to log, not close. Never raises: any
    import/registry failure degrades to "nothing to close".
    """
    try:
        from scripts.browser.tab_registry import tabs_for, clear
    except Exception as e:
        warn(f"tab_registry import failed for {task_id}: {e}")
        return []
    try:
        claimed = tabs_for(task_id)
    except Exception as e:
        warn(f"tab_registry read failed for {task_id}: {e}")
        return []
    if not claimed:
        return []
    claimed_ids = {str(t.get("tab_id")) for t in claimed}
    closed = _close_chrome_tabs([t.get("tab_id") for t in claimed])
    # A claimed id that Chrome no longer has at all is ALREADY GONE, not a
    # failed close: without this the stale claim retried every sweep forever
    # (seen on the first live run: task-1dd8002f, tab 53473010 closed days
    # earlier). Only ids still open after the close count as unresolved.
    still_open = _open_chrome_tab_ids()
    unresolved = (claimed_ids - set(closed))
    if still_open is not None:
        unresolved = {i for i in unresolved if i in still_open}
    if not unresolved:
        try:
            clear(task_id)
        except Exception as e:
            warn(f"tab_registry clear failed for {task_id}: {e}")
    else:
        # Do NOT clear a partial/failed close — that would drop the claim
        # while the tab (or our knowledge of it) still exists, orphaning it
        # from tracking forever. Leaving it claimed means the next sweep
        # tick retries; closing an already-gone tab is a safe no-op either
        # way (see _close_chrome_tabs).
        warn(f"tab_registry: {task_id} claim kept — could not close "
             f"{sorted(unresolved)}; will retry next sweep")
    return closed


def close_dev(task_id: str, *, reason: str) -> dict:
    """End a DEV's process + tmux/ttyd + tab + claimed Chrome tab(s) for
    `task_id`. See module docstring.

    Never raises. Refuses (returns a dict with `refused` set, everything
    else left at its no-op default) unless the task exists and its status is
    in REAPABLE_STATUSES. Idempotent: a second call on an already-reaped
    task finds a dead/mismatched pid and an already-gone tmux/tab/claim,
    sends no signal, and returns cleanly.

    Total (task-92118d4e): a missing pid used to short-circuit the whole
    function before tmux/tab cleanup ever ran — the exact case a task never
    spawned via close_dev's normal callers (a direct sqlite status edit, a
    worker that exited before writing a pid) leaves a tmux session and/or an
    iTerm tab open with nothing to reap them. Every step below now runs
    regardless of whether a pid was recorded; `found` says which of
    {pid, tmux, ttyd} were present in the task row so the sweep's log line
    is honest about what it actually saw versus what it closed.
    `chrome_tabs_closed` (ADDENDUM 1) lists the tab ids closed via the
    browser-tabs registry — empty when the task claimed none.
    """
    result: dict = {
        "task_id": task_id, "closed_tab": False, "pid": None,
        "pid_matched": None, "signal": None, "tmux_killed": False,
        "ttyd_killed": False, "reason": reason, "refused": None,
        "found": {"pid": False, "tmux": False, "ttyd": False},
        "chrome_tabs_closed": [],
    }

    task = db.get_task(task_id)
    if not task:
        result["refused"] = "task not found"
        return result

    if task["status"] not in REAPABLE_STATUSES:
        result["refused"] = (
            f"status={task['status']!r} not in {REAPABLE_STATUSES}"
        )
        return result

    pid = task.get("pid")
    matched = False
    if pid:
        pid = int(pid)
        result["pid"] = pid
        result["found"]["pid"] = True
        matched = _pid_matches_task(pid, task_id)
        result["pid_matched"] = matched
        if matched:
            result["signal"] = _terminate_pid(pid)
        else:
            info(f"worker_reap: {task_id} pid={pid} did not match this task's "
                 "command line (dead or recycled) — not signalling")
    else:
        result["pid_matched"] = False

    result["found"]["tmux"] = bool(task.get("tmux_session"))
    result["found"]["ttyd"] = bool(task.get("ttyd_pid"))

    # The pid may only be used for the tab lookup if it was verified. When it
    # was not (mismatched) or never existed at all (no-pid case above), the
    # tab still gets closed — but by title only. Reaching the pid path here
    # would close whichever tab now holds a pid we just refused to trust: the
    # same harm as killing it, moved to the other half of the job.
    result["closed_tab"] = close_tab(task_id, allow_pid=matched)
    result.update(_cleanup_tmux_ttyd(task))

    # ADDENDUM 1 (task-92118d4e): Chrome tabs are a surface too. Only ever
    # touches ids THIS task claimed in the browser-tabs registry — never an
    # unclaimed org tab, which is the sweep's job to log, not close.
    result["chrome_tabs_closed"] = _close_claimed_chrome_tabs(task_id)
    return result


def _elapsed_seconds(updated_at: str) -> float:
    try:
        upd = datetime.fromisoformat(updated_at)
    except (ValueError, TypeError):
        return 0.0
    if upd.tzinfo is None:
        upd = upd.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - upd).total_seconds()


def _fmt_elapsed(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, _s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


# Statuses where a live pid means "finished, waiting on a C-level decision"
# rather than "leak". Kept separate from REAPABLE_STATUSES (which is about
# close_dev's eligibility gate, now much broader) so list_alive's labeling
# doesn't relabel a leaked cancelled/failed/stalled/reverted/merged task's
# live pid as a pending decision.
_AWAITING_DECISION_STATUSES = ("review", "done")


def list_alive() -> list[dict]:
    """Every task whose DEV process is alive right now, with why.

    A C-level cannot decide about something it cannot see (deliverable 4) —
    this is that visibility. `in_progress` rows are working; `review`/`done`
    rows with a live pid are the ones that matter: they finished and are
    waiting on a C-level decision nobody has made yet. Any other status with
    a live pid (task-92118d4e: cancelled/failed/stalled/reverted/merged) is
    a leak — the surface reaper's job, not a decision to wait on.
    """
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, project, role, status, pid, updated_at FROM tasks "
            "WHERE pid IS NOT NULL ORDER BY updated_at DESC"
        ).fetchall()
    out = []
    for r in rows:
        t = dict(r)
        if not _pid_alive(t["pid"]):
            continue
        elapsed = _elapsed_seconds(t["updated_at"])
        if t["status"] in _AWAITING_DECISION_STATUSES:
            reason = "FINISHED — waiting on a C-level decision"
        elif t["status"] == "in_progress":
            reason = "working"
        elif t["status"] in REAPABLE_STATUSES:
            reason = f"status={t['status']} — LEAK, terminal with a live pid"
        else:
            reason = f"status={t['status']}"
        out.append({
            "task_id": t["id"], "role": t["role"], "status": t["status"],
            "elapsed_s": elapsed, "reason": reason,
        })
    return out


def _print_alive(rows: list[dict]) -> None:
    if not rows:
        print("no DEVs alive")
        return
    RED, RESET = "\033[31m", "\033[0m"
    for r in rows:
        finished = r["status"] in REAPABLE_STATUSES
        status_col = (
            f"{r['status']} {_fmt_elapsed(r['elapsed_s'])}" if finished
            else r["status"]
        )
        line = f"{r['task_id']:16s} {r['role']:18s} {status_col:16s} {r['reason']}"
        print(f"{RED}{line}{RESET}" if finished else line)


# ---------------------------------------------------------------------------
# Remote hosts (docs/design/multi-host-workers.md, Phase 1/2) — task-92118d4e
#
# `close_dev` above only ever looks at THIS machine's process table, tmux
# server and iTerm. A task delegated to winbox or Contabo has none of that
# here — its pid lives in a different machine's process namespace and its
# terminal (Windows Terminal / tmux over SSH) is not something this box can
# see. close_remote is the equivalent teardown for those two spokes, driven
# over SSH rather than local syscalls. Exposed for `runners/branch_poller.py`
# (task-d1d6b2ef, not yet merged) to call once it detects a remote task has
# finished; nothing in this repo calls it yet.
# ---------------------------------------------------------------------------

# host column value -> (ssh alias, OS kind). The ssh alias for Contabo is
# "mooniex-vps" (config/projects.yaml, runners/mac_agent.py SSH_HOST) even
# though the task row's own `host` value is the short form "contabo" (see
# docs/design/multi-host-workers.md's host table) — winbox's ssh alias
# matches its host name exactly.
_REMOTE_HOSTS = {
    "winbox": {"ssh": "winbox", "os": "windows"},
    "contabo": {"ssh": "mooniex-vps", "os": "linux"},
}


def _remote_kill_command(task_id: str, pid: int | None, os_kind: str) -> list[str]:
    """The argv to run ON the remote spoke to end one task's worker.

    Windows: `taskkill /PID <pid> /T /F` kills the process tree; the tab
    itself is not closed here on purpose — Phase 1's launcher runs `claude`
    without `-NoExit` (task-d1d6b2ef), so tab lifetime already equals
    process lifetime once that lands.

    Linux (Contabo): kills the tmux session AND the bare pid — a detached
    process outside tmux, or one tmux's own kill-session didn't reach,
    must not survive either.

    Returns [] when there is nothing to kill (no pid on a Windows target —
    taskkill has no other way to select a process).
    """
    session = tmux_session.session_name_for(task_id)
    if os_kind == "windows":
        if not pid:
            return []
        return ["taskkill", "/PID", str(int(pid)), "/T", "/F"]
    # linux
    cmd = f"tmux kill-session -t {session} 2>/dev/null"
    if pid:
        cmd += f"; kill {int(pid)} 2>/dev/null"
    return ["bash", "-lc", cmd]


def close_remote(task: dict, *,
                 reason: str = "reaper: terminal status with live surface",
                 allow_review: bool = False) -> dict:
    """End a remote (winbox/contabo) DEV's worker over SSH. See module note
    above and docs/design/multi-host-workers.md.

    ADDENDUM 2 (task-92118d4e, CEO rule 2026-09-07 — never close a surface
    under a worker that may be working): re-reads the task from the DB by
    id before doing anything else, so a caller (the branch poller) holding a
    stale dict from an earlier poll can't kill a worker whose task has since
    gone back active. Refuses unless the freshly-read status is in
    _TERMINAL_SURFACE_STATUSES — same safety gate as the local sweep. When
    the id can't be re-read at all (task deleted, or a synthetic dict with
    no matching row), falls back to the status the caller already had rather
    than crashing; that dict is then held to the same guard.

    `allow_review` (task-59780ac3 GAP 2, default False — a deliberate,
    narrow opt-in) additionally accepts status='review'. `review` is NOT in
    _TERMINAL_SURFACE_STATUSES on purpose: on the Mac a live pid there means
    "finished, waiting on a C-level decision" (see list_alive's
    _AWAITING_DECISION_STATUSES) and must never be auto-closed. But a remote
    worker in `review` has already pushed REPORT.md — its entire output is
    in git, there is no decision left that needs the process alive to make.
    Only `runners/branch_poller.py`, right after it flips a task to `review`
    and only once REPORT.md is confirmed still on the branch AND the
    branch's newest commit is several minutes old (proof it has stopped
    pushing, not mid-push), passes this. No other caller in this codebase
    does, and passing it does not touch _TERMINAL_SURFACE_STATUSES itself —
    every other guard below (fresh re-read, host/pid checks) still applies
    exactly as it does for a terminal-status call.

    Guards on `task.get("host")`, not `task["host"]`: the `host` column is
    being added by a separate in-flight task (task-d1d6b2ef) and a task dict
    read from a DB where that migration hasn't landed yet simply has no
    "host" key — `.get()` returns None for that exactly the same as it would
    for an explicit NULL, so the guard is correct either way and this never
    raises on the pre-migration schema.

    Never raises: an unset/local/unrecognized host, a non-terminal status,
    or the SSH call itself failing, is recorded in the returned dict, not
    thrown. This module has no way to verify a remote kill actually landed
    (no local process table to re-check) — `ssh_ok` reflects only the SSH
    command's exit code.
    """
    task_id = task.get("id")
    fresh = db.get_task(task_id) if task_id else None
    if fresh is not None:
        task = fresh

    host = task.get("host")
    result = {
        "task_id": task.get("id"), "host": host, "reason": reason,
        "command": None, "ssh_ok": None, "refused": None,
    }

    status = task.get("status")
    allowed_statuses = _TERMINAL_SURFACE_STATUSES | ({"review"} if allow_review else set())
    if status not in allowed_statuses:
        result["refused"] = f"status {status} is not terminal"
        return result

    if not host or host == "mac":
        result["refused"] = f"host={host!r} — not a remote spoke"
        return result

    spec = _REMOTE_HOSTS.get(host)
    if spec is None:
        result["refused"] = f"host={host!r} not in {sorted(_REMOTE_HOSTS)}"
        return result

    pid = task.get("pid")
    remote_argv = _remote_kill_command(task.get("id", ""), pid, spec["os"])
    if not remote_argv:
        result["refused"] = "no pid recorded — nothing to kill"
        return result

    ssh_cmd = ["ssh", spec["ssh"], *remote_argv]
    result["command"] = ssh_cmd
    try:
        r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        result["ssh_ok"] = r.returncode == 0
        if r.returncode != 0:
            result["stderr"] = (r.stderr or "")[:300]
    except Exception as e:
        result["ssh_ok"] = False
        result["stderr"] = str(e)[:300]
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="End a finished DEV's process + tab")
    ap.add_argument("task_id", nargs="?", help="task to reap")
    ap.add_argument("--reason", default="manual: python3 -m tools.worker_reap",
                    help="why (recorded in the result)")
    ap.add_argument("--list", action="store_true",
                    help="list DEVs alive right now, with why")
    args = ap.parse_args()

    db.init()

    if args.list:
        _print_alive(list_alive())
        return 0

    if not args.task_id:
        ap.print_usage()
        return 2

    result = close_dev(args.task_id, reason=args.reason)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

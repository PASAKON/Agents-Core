"""Single place that ends a DEV: terminate its process, close its iTerm tab.

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
    python3 -m tools.dev_reap <task_id> [--reason TEXT]   # reap one task
    python3 -m tools.dev_reap --list                      # DEVs alive now
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

# Statuses close_dev is allowed to act on. Everything else (pending,
# in_progress, blocked_human, rate_limited, conflict, stalled) is refused —
# see close_dev's docstring point 1.
REAPABLE_STATUSES = ("review", "done")

# Grace period between SIGTERM and SIGKILL escalation.
TERM_GRACE_S = 3


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
    """
    out = {"tmux_killed": False, "ttyd_killed": False}
    try:
        from tools import tmux_session as tmux
    except Exception as e:
        warn(f"tmux_session import failed: {e}")
        return out
    sess = task.get("tmux_session")
    if sess:
        try:
            out["tmux_killed"] = tmux.kill(sess)
        except Exception as e:
            warn(f"tmux kill failed for {sess}: {e}")
    ttyd_pid = task.get("ttyd_pid")
    if ttyd_pid:
        try:
            out["ttyd_killed"] = tmux.stop_ttyd(int(ttyd_pid))
        except Exception as e:
            warn(f"ttyd stop failed for pid={ttyd_pid}: {e}")
    return out


def close_dev(task_id: str, *, reason: str) -> dict:
    """End a DEV's process + tab for `task_id`. See module docstring.

    Never raises. Refuses (returns a dict with `refused` set, everything
    else left at its no-op default) unless the task exists, its status is
    'review' or 'done', and it has a recorded pid. Idempotent: a second
    call on an already-reaped task finds a dead/mismatched pid, sends no
    signal, and returns cleanly.
    """
    result: dict = {
        "task_id": task_id, "closed_tab": False, "pid": None,
        "pid_matched": None, "signal": None, "tmux_killed": False,
        "ttyd_killed": False, "reason": reason, "refused": None,
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
    if not pid:
        result["refused"] = "pid is NULL — not a delegate-spawned tab"
        return result
    pid = int(pid)
    result["pid"] = pid

    matched = _pid_matches_task(pid, task_id)
    result["pid_matched"] = matched
    if matched:
        result["signal"] = _terminate_pid(pid)
    else:
        info(f"dev_reap: {task_id} pid={pid} did not match this task's "
             "command line (dead or recycled) — not signalling")

    # The pid may only be used for anything at all if it was verified. When it
    # was not, the tab still gets closed — but by title only. Reaching the pid
    # path here would close whichever tab now holds a pid we just refused to
    # trust: the same harm as killing it, moved to the other half of the job.
    result["closed_tab"] = close_tab(task_id, allow_pid=matched)
    result.update(_cleanup_tmux_ttyd(task))
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


def list_alive() -> list[dict]:
    """Every task whose DEV process is alive right now, with why.

    A C-level cannot decide about something it cannot see (deliverable 4) —
    this is that visibility. `in_progress` rows are working; `review`/`done`
    rows with a live pid are the ones that matter: they finished and are
    waiting on a C-level decision nobody has made yet.
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
        if t["status"] in REAPABLE_STATUSES:
            reason = "FINISHED — waiting on a C-level decision"
        elif t["status"] == "in_progress":
            reason = "working"
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


def main() -> int:
    ap = argparse.ArgumentParser(description="End a finished DEV's process + tab")
    ap.add_argument("task_id", nargs="?", help="task to reap")
    ap.add_argument("--reason", default="manual: python3 -m tools.dev_reap",
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

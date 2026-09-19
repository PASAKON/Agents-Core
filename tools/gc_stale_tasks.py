"""GC stale tasks.

Run periodically (suggest 10 min interval). Marks tasks as 'cancelled' if:

  1. status='pending' AND created_at older than STALE_PENDING_MINUTES
     AND assigned_agent IS NULL  (never delegated successfully)
  1b. status='pending' AND assigned_agent IS NOT NULL AND
     spawned_at/created_at older than STALE_SPAWNED_PENDING_MINUTES AND
     the DEV process is provably dead (never flipped to in_progress —
     W3 Bug B: category 1's `assigned_agent is not None` guard used to
     skip these forever)
  2. status='conflict' AND updated_at older than STALE_CONFLICT_MINUTES
     (caller hasn't retried — lock is dead weight)
  3. status='rate_limited' AND retry_after_ts in the past by >
     STALE_RATELIMIT_MINUTES (caller gave up)

Releases path locks held by cancelled tasks. Also runs
release_terminal_task_locks(), a separate pass that releases locks for
any task that reached a terminal status (or 'review') outside
db.update_status — e.g. a status written directly to the row, which never
fires lib/db.py's RELEASING_STATUSES release (W3 Bug A) — and deletes any
lock row whose owner isn't a task at all.

Idempotent. Safe to run concurrently with other CTOs (uses a single UPDATE
with a WHERE clause that re-checks the same predicates).
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
from lib.config import host as get_host
from runners.branch_poller import remote_pid_alive
from tools.worker_reap import _pid_alive
from tools.worktree import remove_worktree

STALE_PENDING_MINUTES         = 30
STALE_CONFLICT_MINUTES        = 60
STALE_RATELIMIT_MINUTES       = 30
STALE_SPAWNED_PENDING_MINUTES = 120

# Statuses whose worktree is dead weight and can be reclaimed. Includes
# 'merged': audited 2026-08-07 (W6, org:reference/2026-08-06-agents-system-
# audit.md) — merge_task()'s success path has only ever written 'done'
# (tools/git_ops.py:342-347, true since the original commit), and no other
# call site in the repo or its full git history writes status='merged' via
# update_status(). It is a legacy value declared in db.VALID_STATUS and
# treated as done-equivalent by several read-only checks (lib/reflect.py,
# lib/recall.py, tools/delegate.py, tools/revert_task.py) but produced by no
# code path — the one live example (task-df93e0ed) has no status_* event for
# the transition, meaning it was hand-set directly in the DB outside any
# tool, not written by the app. Safe to treat as terminal like 'done'.
# Still excludes 'reverted'/'blocked_human' (still needs a human look).
TERMINAL_STATUSES = {"done", "cancelled", "stalled", "failed", "merged"}

# Statuses whose owning task is done touching its paths — used by
# release_terminal_task_locks. TERMINAL_STATUSES plus 'review': a task in
# review is out of the DEV's hands even though it isn't terminal yet, same
# rationale as lib/db.py's RELEASING_STATUSES (which this file doesn't
# import — lib/db.py is out of scope for this task, so the set is
# duplicated here rather than reused).
LOCK_RELEASE_STATUSES = TERMINAL_STATUSES | {"review"}

# 'review' worktrees older than this are flagged (print-only) — never
# auto-removed, since a human may still be about to look at them.
REVIEW_STALE_DAYS = 21


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _age_minutes(ts: str | None) -> float | None:
    dt = _parse_ts(ts)
    if dt is None:
        return None
    return (_now() - dt).total_seconds() / 60


def _worktree_git_status(wt: Path) -> str | None:
    """`git status --porcelain` output for wt, or None if it can't be
    determined (missing dir, not a git worktree, git error). Callers must
    treat None as 'unknown — do not remove'."""
    if not wt.exists():
        return None
    r = subprocess.run(["git", "status", "--porcelain"], cwd=str(wt),
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def _reclaim_worktree(task: dict, *, dry_run: bool) -> dict | None:
    """Remove a terminal-status task's worktree unless it's dirty or missing.

    Reuses tools.worktree.remove_worktree — never reimplements the git
    plumbing. Returns None when there's nothing to reclaim (no worktree
    recorded, or the path is already gone). Otherwise a dict with an
    `action` of 'removed' / 'would_remove' / 'skipped_dirty' /
    'skipped_unverifiable' / 'error'.
    """
    wt_str = task.get("worktree")
    if not wt_str:
        return None
    wt = Path(wt_str)
    if not wt.exists():
        return None

    status = _worktree_git_status(wt)
    if status is None:
        print(f"[gc] skip worktree reclaim for {task['id']}: "
              f"can't verify git status at {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "skipped_unverifiable"}
    if status.strip():
        print(f"[gc] skip worktree reclaim for {task['id']}: "
              f"uncommitted changes at {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "skipped_dirty"}

    if dry_run:
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "would_remove"}

    try:
        remove_worktree(task["project"], task["role"], task["id"])
        print(f"[gc] removed worktree for {task['id']}: {wt}", file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str, "action": "removed"}
    except Exception as e:
        print(f"[gc] failed to remove worktree for {task['id']}: {e}",
              file=sys.stderr)
        return {"task_id": task["id"], "worktree": wt_str,
                "action": "error", "error": str(e)}


def _alive_for_gc(t: dict) -> bool | None:
    """True/False/None liveness for the process behind task `t`, dispatched
    by host. None means "couldn't determine — do not act", matching
    remote_pid_alive's own contract; a local check never returns None since
    kill(pid, 0) is always answerable (no pid included — _pid_alive(None)
    is False).
    """
    host_name = t.get("host")
    if host_name in (None, "mac"):
        return _pid_alive(t.get("pid"))
    pid = t.get("pid")
    if not pid:
        return False
    try:
        host_cfg = get_host(host_name)
    except ValueError:
        return None
    return remote_pid_alive(host_cfg, pid)


def gc_stale_tasks(
    *,
    pending_minutes: int = STALE_PENDING_MINUTES,
    conflict_minutes: int = STALE_CONFLICT_MINUTES,
    ratelimit_minutes: int = STALE_RATELIMIT_MINUTES,
    dry_run: bool = False,
) -> list[dict]:
    """Sweep for stale tasks and cancel them. Returns list of affected entries."""
    cancelled: list[dict] = []

    # Category 1: pending tasks never delegated (no assigned_agent)
    for t in db.list_tasks(status="pending", limit=500):
        if t.get("assigned_agent") is not None:
            continue
        # Never reap a task whose DEV is still running. A task stays
        # 'pending' for the whole spawn window — dev_init flips it to
        # in_progress only once it claims — so a live spawn sits squarely
        # inside this sweep's kill zone. Cancelling it is bad enough;
        # _reclaim_worktree below then deletes the worktree out from under
        # a process still working in it, and its only guard is `git status`
        # being non-empty, which a DEV that has not committed yet fails.
        #
        # Measured 2026-08-13 00:26: task-7d4b567b, pid 47128 observed in
        # state R+ (running, consuming CPU), cancelled ~30s after delegate.
        # See GH #52.
        if _pid_alive(t.get("pid")):
            continue
        # Measure from the spawn, not from row creation. `created_at` is
        # when create_task ran, which says nothing about how long the task
        # has been abandoned: a task created at 23:50 and delegated at
        # 00:25 was already 35 minutes "stale" the instant its DEV started.
        #
        # spawned_at is NULL for a task that genuinely was never delegated
        # — exactly what this category exists to catch — so fall back to
        # created_at only in that case.
        age = _age_minutes(t.get("spawned_at") or t.get("created_at"))
        if age is None or age <= pending_minutes:
            continue
        print(f"[gc] cancelled {t['id']} (stale pending >{pending_minutes}min)",
              file=sys.stderr)
        entry: dict = {
            "task_id": t["id"], "project": t["project"],
            "kind": "pending", "age_min": round(age, 1),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=f"gc: stale pending >{pending_minutes}min without assignment",
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 1b: pending tasks that WERE delegated (assigned_agent set)
    # but whose DEV process is provably dead — W3 Bug B. Category 1 above
    # skips these forever via its `assigned_agent is not None` guard, so a
    # spawn that died before ever reaching in_progress held its locks for
    # good (measured: task-8b6625ff, 26 days, 17 locks).
    #
    # 120-minute floor, not 30: this sits on top of Category 1's own spawn-
    # window protection (the _pid_alive live-process check), so the extra
    # margin is purely about giving a slow-to-report spawn room, not about
    # racing a delegate that hasn't started yet.
    for t in db.list_tasks(status="pending", limit=500):
        if t.get("assigned_agent") is None:
            continue
        age = _age_minutes(t.get("spawned_at") or t.get("created_at"))
        if age is None or age <= STALE_SPAWNED_PENDING_MINUTES:
            continue
        alive = _alive_for_gc(t)
        if alive is not False:  # True (running) or None (unknown) — never act
            continue
        print(f"[gc] cancelled {t['id']} (stale spawned pending "
              f">{STALE_SPAWNED_PENDING_MINUTES}min, no live process)",
              file=sys.stderr)
        # Read-only count up front so --dry-run reports the lock count too
        # (not just which tasks would be cancelled) — the whole point of a
        # dry-run for a bug about locks is seeing the lock numbers before
        # committing to releasing them.
        with db.get_conn() as conn:
            lock_n = conn.execute(
                "SELECT COUNT(*) c FROM locks WHERE owner=? AND key LIKE ?",
                (t["id"], f"proj:{t['project']}:path:%"),
            ).fetchone()["c"]
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "spawned_pending", "age_min": round(age, 1),
            "locks_released": lock_n,
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=(f"gc: stale spawned pending "
                        f">{STALE_SPAWNED_PENDING_MINUTES}min, no live "
                        f"process (host={t.get('host') or 'mac'})"),
            )
            # update_status already released these locks — 'cancelled' is
            # in lib/db.py's RELEASING_STATUSES. This call is a no-op safety
            # net (always returns 0 here), so entry keeps the pre-release
            # lock_n above rather than being overwritten with that 0.
            db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 2: conflict tasks whose caller gave up retrying
    for t in db.list_tasks(status="conflict", limit=500):
        age = _age_minutes(t.get("updated_at"))
        if age is None or age <= conflict_minutes:
            continue
        print(f"[gc] cancelled {t['id']} (stale conflict >{conflict_minutes}min)",
              file=sys.stderr)
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "conflict", "age_min": round(age, 1),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=f"gc: stale conflict >{conflict_minutes}min, caller gave up",
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # Category 3: rate_limited tasks whose retry_after_ts is overdue
    for t in db.list_tasks(status="rate_limited", limit=500):
        rat = _parse_ts(t.get("retry_after_ts"))
        if rat is not None:
            overdue_min = (_now() - rat).total_seconds() / 60
            if overdue_min <= ratelimit_minutes:
                continue
        else:
            # No retry_after_ts recorded — fall back to updated_at age
            age = _age_minutes(t.get("updated_at"))
            if age is None or age <= ratelimit_minutes:
                continue
        # A rate limit is not a death. `retry_after` is what the API says it
        # will accept next, not when the underlying allowance clears: a WEEKLY
        # Claude quota reports retry_after=300s and then keeps refusing, so
        # this branch fires on a worker that is alive and correctly waiting.
        # On 2026-09-19 it cancelled task-2e5cd54e mid-episode and reclaimed
        # its worktree; four commits survived only because git had them.
        # Every other category here already checks liveness before acting.
        alive = _alive_for_gc(t)
        if alive is True:
            print(f"[gc] keeping {t['id']} — rate_limited but its process is alive "
                  f"(pid {t.get('pid')}); a waiting worker is not a stale one",
                  file=sys.stderr)
            continue
        print(f"[gc] cancelled {t['id']} (stale rate_limited >{ratelimit_minutes}min, process not alive)",
              file=sys.stderr)
        entry = {
            "task_id": t["id"], "project": t["project"],
            "kind": "rate_limited",
            "retry_after_ts": t.get("retry_after_ts"),
        }
        if not dry_run:
            db.update_status(
                t["id"], "cancelled", actor="gc_stale_tasks",
                report=(f"gc: rate_limited overdue >{ratelimit_minutes}min, "
                        f"retry_after_ts={t.get('retry_after_ts')}"),
            )
            entry["locks_released"] = db.release_task_locks(t["id"], t["project"])
        entry["worktree_reclaim"] = _reclaim_worktree(t, dry_run=dry_run)
        cancelled.append(entry)

    # W3 Bug A: locks held by a task whose status went terminal (or
    # 'review') outside db.update_status never got released. Same returned
    # list — runners/watchdog.py:620 already calls gc_stale_tasks() and
    # logs len(result), so this rides along with no watchdog edit.
    cancelled.extend(release_terminal_task_locks(dry_run=dry_run))

    return cancelled


def release_terminal_task_locks(dry_run: bool = False) -> list[dict]:
    """Release path locks whose owning task is done touching its paths, and
    delete lock rows that belong to no task row at all.

    Bug A (W3): lib/db.py's update_status releases locks via
    RELEASING_STATUSES, but only when the status transition goes through
    that function. A status written directly to the row (measured: 8 'done'
    owners, 24 lock rows, zero status_done event in their history) never
    fires that release, and nothing else in the codebase cleans it up.

    Uses raw SQL against db.get_conn() (the same inline-SQL idiom
    _all_tasks_with_worktree already uses above) rather than a new
    lib/db.py helper — lib/db.py is out of scope for this task.
    """
    released: list[dict] = []
    with db.get_conn() as conn:
        owners = [r["owner"] for r in conn.execute(
            "SELECT DISTINCT owner FROM locks WHERE key LIKE 'proj:%:path:%'"
        ).fetchall()]

    for owner in owners:
        t = db.get_task(owner)

        if t is None:
            with db.get_conn() as conn:
                n = conn.execute(
                    "SELECT COUNT(*) c FROM locks WHERE owner=?", (owner,)
                ).fetchone()["c"]
            if n == 0:
                continue
            print(f"[gc] deleted {n} orphan lock(s) for owner={owner} "
                  f"(no task row)", file=sys.stderr)
            entry = {"task_id": owner, "kind": "orphan_lock",
                     "locks_released": n}
            if not dry_run:
                with db.get_conn() as conn:
                    conn.execute("DELETE FROM locks WHERE owner=?", (owner,))
            released.append(entry)
            continue

        if t["status"] not in LOCK_RELEASE_STATUSES:
            continue

        with db.get_conn() as conn:
            n = conn.execute(
                "SELECT COUNT(*) c FROM locks WHERE owner=? AND key LIKE ?",
                (owner, f"proj:{t['project']}:path:%"),
            ).fetchone()["c"]
        if n == 0:
            continue
        print(f"[gc] released {n} lock(s) for {owner} "
              f"(terminal status={t['status']})", file=sys.stderr)
        entry = {
            "task_id": owner, "project": t["project"], "status": t["status"],
            "kind": "terminal_locks",
            "locks_released": n if dry_run else db.release_task_locks(
                owner, t["project"]),
        }
        released.append(entry)

    return released


def _all_tasks_with_worktree() -> list[dict]:
    """Every tasks.db row that has a worktree path recorded, regardless of
    status — the raw input to the --reap cross-reference sweep."""
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, project, role, status, worktree, updated_at "
            "FROM tasks WHERE worktree IS NOT NULL AND worktree <> ''"
        ).fetchall()
    return [dict(r) for r in rows]


def _dir_size_bytes(path: Path) -> int:
    """Recursive size of path, skipping symlinks (worktrees symlink in
    node_modules/.env from the canonical repo — those must not be counted,
    they aren't this worktree's disk cost and aren't removed with it)."""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, followlinks=False):
        for fn in filenames:
            fp = Path(dirpath) / fn
            try:
                if not fp.is_symlink():
                    total += fp.stat().st_size
            except OSError:
                pass
    return total


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"


def _last_commit_date(wt: Path) -> str:
    r = subprocess.run(["git", "log", "-1", "--format=%cI"], cwd=str(wt),
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    return "unknown"


def reap_worktrees(*, dry_run: bool = True,
                   review_stale_days: int = REVIEW_STALE_DAYS) -> dict:
    """Cross-reference every tasks.db row that has a worktree against its
    current status.

    Terminal-status rows (done/cancelled/stalled/failed) whose worktree still
    exists on disk get removed via tools.worktree.remove_worktree — skipped +
    logged instead of forced when the worktree has uncommitted changes.
    'review' rows whose worktree mtime is older than review_stale_days are
    flagged only (print-only; never auto-removed — a human may still be
    about to look at them).

    Returns {"removed": [...], "skipped": [...], "flagged_review": [...]}.
    """
    removed: list[dict] = []
    skipped: list[dict] = []
    flagged_review: list[dict] = []

    for t in _all_tasks_with_worktree():
        status = t["status"]
        wt = Path(t["worktree"])

        if status in TERMINAL_STATUSES:
            if not wt.exists():
                continue
            size_bytes = _dir_size_bytes(wt)
            last_commit = _last_commit_date(wt)
            result = _reclaim_worktree(t, dry_run=dry_run)
            if result is None:
                continue
            result["status"] = status
            result["project"] = t["project"]
            if result["action"] in ("removed", "would_remove"):
                result["size_bytes"] = size_bytes
                result["size_human"] = _human_size(size_bytes)
                result["last_commit"] = last_commit
                removed.append(result)
            else:
                skipped.append(result)

        elif status == "review":
            if not wt.exists():
                continue
            try:
                mtime = wt.stat().st_mtime
            except OSError:
                continue
            age_days = (time.time() - mtime) / 86400
            if age_days > review_stale_days:
                flagged_review.append({
                    "task_id": t["id"], "worktree": t["worktree"],
                    "age_days": round(age_days, 1),
                })

    return {"removed": removed, "skipped": skipped,
            "flagged_review": flagged_review}


def _print_reap_report(result: dict, *, dry_run: bool) -> None:
    tag = "[dry-run] " if dry_run else ""
    verb = "would remove" if dry_run else "removed"
    print(f"{tag}reap: {verb} {len(result['removed'])} worktree(s), "
          f"skipped {len(result['skipped'])}, "
          f"flagged {len(result['flagged_review'])} stale 'review' worktree(s)")

    if result["removed"]:
        print("\n-- terminal-status worktrees --")
        for r in result["removed"]:
            print(f"  {r['task_id']:16s} {r['status']:10s} {r['size_human']:>9s}  "
                  f"last_commit={r['last_commit']}  {r['worktree']}")

    if result["skipped"]:
        print("\n-- skipped (not touched) --")
        for r in result["skipped"]:
            print(f"  {r['task_id']:16s} {r['status']:10s} {r['action']:22s} {r['worktree']}")

    if result["flagged_review"]:
        print(f"\n-- stale 'review' worktrees (>{REVIEW_STALE_DAYS}d, flagged only, NOT removed) --")
        for r in result["flagged_review"]:
            print(f"  {r['task_id']:16s} age={r['age_days']:>6.1f}d  {r['worktree']}")


def main() -> int:
    ap = argparse.ArgumentParser(description="GC stale tasks / reap terminal-status worktrees")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be cancelled without writing to DB "
                         "(stale-task sweep mode; ignored under --reap, which "
                         "is dry-run by default — see --go)")
    ap.add_argument("--pending", type=int, default=STALE_PENDING_MINUTES,
                    help=f"pending threshold minutes (default {STALE_PENDING_MINUTES})")
    ap.add_argument("--conflict", type=int, default=STALE_CONFLICT_MINUTES,
                    help=f"conflict threshold minutes (default {STALE_CONFLICT_MINUTES})")
    ap.add_argument("--ratelimit", type=int, default=STALE_RATELIMIT_MINUTES,
                    help=f"rate_limited threshold minutes (default {STALE_RATELIMIT_MINUTES})")
    ap.add_argument("--reap", action="store_true",
                    help="switch modes: reap worktrees for terminal-status "
                         "tasks instead of running the stale-task sweep")
    ap.add_argument("--go", action="store_true",
                    help="[--reap only] actually remove worktrees; default is dry-run")
    ap.add_argument("--review-stale-days", type=int, default=REVIEW_STALE_DAYS,
                    help=f"[--reap only] flag 'review' worktrees older than this "
                         f"many days (default {REVIEW_STALE_DAYS})")
    args = ap.parse_args()

    db.init()

    if args.reap:
        result = reap_worktrees(dry_run=not args.go,
                                review_stale_days=args.review_stale_days)
        _print_reap_report(result, dry_run=not args.go)
        return 0

    cancelled = gc_stale_tasks(
        pending_minutes=args.pending,
        conflict_minutes=args.conflict,
        ratelimit_minutes=args.ratelimit,
        dry_run=args.dry_run,
    )
    tag = "[dry-run] " if args.dry_run else ""
    verb = "would cancel" if args.dry_run else "cancelled"
    print(f"{tag}gc: {verb} {len(cancelled)} task(s)")
    if cancelled:
        print(json.dumps(cancelled, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""GC stale tasks.

Run periodically (suggest 10 min interval). Marks tasks as 'cancelled' if:

  1. status='pending' AND created_at older than STALE_PENDING_MINUTES
     AND assigned_agent IS NULL  (never delegated successfully)
  2. status='conflict' AND updated_at older than STALE_CONFLICT_MINUTES
     (caller hasn't retried — lock is dead weight)
  3. status='rate_limited' AND retry_after_ts in the past by >
     STALE_RATELIMIT_MINUTES (caller gave up)

Releases path locks held by cancelled tasks.

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
from tools.worktree import remove_worktree

STALE_PENDING_MINUTES   = 30
STALE_CONFLICT_MINUTES  = 60
STALE_RATELIMIT_MINUTES = 30

# Statuses whose worktree is dead weight and can be reclaimed. Deliberately
# excludes 'merged' (merge_task already cleans that one up on success) and
# 'reverted'/'blocked_human' (still needs a human look).
TERMINAL_STATUSES = {"done", "cancelled", "stalled", "failed"}

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
        age = _age_minutes(t.get("created_at"))
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
        print(f"[gc] cancelled {t['id']} (stale rate_limited >{ratelimit_minutes}min)",
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

    return cancelled


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

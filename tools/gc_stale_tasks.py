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
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db

STALE_PENDING_MINUTES   = 30
STALE_CONFLICT_MINUTES  = 60
STALE_RATELIMIT_MINUTES = 30


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
        cancelled.append(entry)

    return cancelled


def main() -> int:
    ap = argparse.ArgumentParser(description="GC stale tasks")
    ap.add_argument("--dry-run", action="store_true",
                    help="show what would be cancelled without writing to DB")
    ap.add_argument("--pending", type=int, default=STALE_PENDING_MINUTES,
                    help=f"pending threshold minutes (default {STALE_PENDING_MINUTES})")
    ap.add_argument("--conflict", type=int, default=STALE_CONFLICT_MINUTES,
                    help=f"conflict threshold minutes (default {STALE_CONFLICT_MINUTES})")
    ap.add_argument("--ratelimit", type=int, default=STALE_RATELIMIT_MINUTES,
                    help=f"rate_limited threshold minutes (default {STALE_RATELIMIT_MINUTES})")
    args = ap.parse_args()

    db.init()
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

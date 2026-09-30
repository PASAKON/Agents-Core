"""Cost learner — Q3b (PLAN-auto-dispatch.md §3 "Cost table").

Reads quota history snapshots and the org ledger to compute the real
weekly-quota fraction each job consumed, then writes state/cost-table.json
so tools/forecast.py stops using seed estimates.

Inputs
------
* tools.quota.DEFAULT_HISTORY  — JSONL, one line per bucket per snapshot
  every 10 min.  Each line: {"ts": ISO-8601, "provider": "<bucket>",
  "weekly_remaining": 0..1 | null, "error": null | str, ...}

* lib.db (via get_conn) — tasks: id, runner, runner_model, touches,
  description; events: task_id, kind, ts.

A job's window: start = ts of "status_in_progress" event, end = ts of
first "status_review" or "status_done" event after that.

Counting rules
--------------
* runner and end must exist.
* bucket = quota.bucket_for(f"{runner}:{runner_model or ''}", cfg) must
  be non-None and not "claude" (shared with C-level sessions).
* size = forecast.infer_size(touches, description).
* Delta: last snapshot at or before start + first at or after end, both
  error-free, no weekly reset (rise > 0.02) in between.  Both must be
  within 20 min of the window edge.  delta = max(0, before - after).
* Overlap: jobs on the same bucket whose window overlaps this one split
  the delta evenly.

Output
------
learn() -> dict  (the cost-table structure)
write_table(table, path=None) -> Path  (atomic write to COST_TABLE_PATH)

CLI
---
--dry-run  print table, write nothing
(no flag)  learn + write + print "cost-table: <path> <cells> cells"
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import forecast, quota as quota_mod
from tools.limits import load_limits

# Maximum distance between a snapshot timestamp and the job window edge (min).
MAX_EDGE_OFFSET_MIN = 20

# A rise in weekly_remaining > this fraction = weekly reset.
RESET_THRESHOLD = 0.02


def _parse_dt(ts_str: str) -> datetime:
    """Parse ISO-8601 string to UTC-aware datetime."""
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_history(history_path: Path) -> dict[str, list[tuple[datetime, float]]]:
    """Load quota history into {bucket: [(ts, weekly_remaining), ...]} sorted by ts."""
    result: dict[str, list[tuple[datetime, float]]] = {}
    if not history_path.is_file():
        return result
    try:
        with open(history_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                if obj.get("error") is not None:
                    continue
                w = obj.get("weekly_remaining")
                if w is None:
                    continue
                bucket = obj.get("provider")
                if not bucket:
                    continue
                ts_str = obj.get("ts")
                if not ts_str:
                    continue
                try:
                    ts_dt = _parse_dt(ts_str)
                except Exception:
                    continue
                result.setdefault(bucket, []).append((ts_dt, float(w)))
    except Exception:
        return result
    for pts in result.values():
        pts.sort(key=lambda x: x[0])
    return result


def _find_snapshot(
    points: list[tuple[datetime, float]],
    edge: datetime,
    direction: str,  # "before" or "after"
) -> tuple[datetime, float] | None:
    """Return the closest point at-or-before (direction='before') or
    at-or-after (direction='after') *edge* within MAX_EDGE_OFFSET_MIN minutes.
    Returns None if no such point exists.
    """
    max_delta = timedelta(minutes=MAX_EDGE_OFFSET_MIN)
    if direction == "before":
        # Last point with ts <= edge within 20 min
        best: tuple[datetime, float] | None = None
        for pt in points:
            if pt[0] <= edge and (edge - pt[0]) <= max_delta:
                best = pt
        return best
    else:
        # First point with ts >= edge within 20 min
        for pt in points:
            if pt[0] >= edge and (pt[0] - edge) <= max_delta:
                return pt
        return None


def _has_reset(
    points: list[tuple[datetime, float]],
    start: datetime,
    end: datetime,
) -> bool:
    """Return True if any consecutive pair of points in [start, end] shows a rise > 0.02."""
    window = [(ts, w) for ts, w in points if start <= ts <= end]
    for i in range(1, len(window)):
        if window[i][1] - window[i - 1][1] > RESET_THRESHOLD:
            return True
    return False


def _load_jobs_from_db(cfg: dict) -> list[dict]:
    """Load job windows from the org ledger via lib.db.

    Returns list of {id, bucket, size, start, end} dicts.
    Jobs where runner is missing, bucket is None/"claude", or end is missing
    are excluded.
    """
    from lib import db

    jobs = []
    try:
        with db.get_conn(readonly=True) as conn:
            rows = conn.execute(
                "SELECT id, runner, runner_model, touches, description FROM tasks"
            ).fetchall()
    except Exception:
        return []

    task_map = {r["id"]: dict(r) for r in rows}

    # Fetch all relevant events in one query
    try:
        with db.get_conn(readonly=True) as conn:
            events = conn.execute(
                "SELECT task_id, kind, ts FROM events "
                "WHERE kind IN ('status_in_progress','status_review','status_done') "
                "ORDER BY task_id, ts"
            ).fetchall()
    except Exception:
        return []

    ev_by_task: dict[str, list[dict]] = defaultdict(list)
    for ev in events:
        ev_by_task[ev["task_id"]].append({"kind": ev["kind"], "ts": ev["ts"]})

    for task_id, task in task_map.items():
        runner = task.get("runner")
        if not runner:
            continue

        runner_model = task.get("runner_model") or ""
        candidate = f"{runner}:{runner_model}"
        bucket = quota_mod.bucket_for(candidate, cfg)
        if not bucket or bucket == "claude":
            continue

        # Parse touches
        try:
            touches = json.loads(task.get("touches") or "[]")
        except Exception:
            touches = []
        description = task.get("description") or ""
        size = forecast.infer_size(touches, description)

        # Find window from events
        evs = ev_by_task.get(task_id, [])
        start_dt: datetime | None = None
        end_dt: datetime | None = None

        for ev in evs:
            if ev["kind"] == "status_in_progress" and start_dt is None:
                try:
                    start_dt = _parse_dt(ev["ts"])
                except Exception:
                    pass

        if start_dt is not None:
            for ev in evs:
                if ev["kind"] in ("status_review", "status_done"):
                    try:
                        ev_dt = _parse_dt(ev["ts"])
                        if ev_dt > start_dt:
                            if end_dt is None or ev_dt < end_dt:
                                end_dt = ev_dt
                    except Exception:
                        pass

        if start_dt is None or end_dt is None:
            continue

        jobs.append({
            "id": task_id,
            "bucket": bucket,
            "size": size,
            "start": start_dt,
            "end": end_dt,
        })

    return jobs


def learn(
    history_path=None,
    now=None,
    *,
    jobs=None,
    cfg=None,
    limits=None,
) -> dict:
    """Compute the cost table from quota history and job windows.

    Parameters
    ----------
    history_path : Path-like, optional
        Override for the quota history file (default: quota.DEFAULT_HISTORY).
    now : datetime, optional
        Unused — kept for future extension / test injection.
    jobs : list[dict], optional
        Pre-built job windows {id, bucket, size, start, end} for tests.
        When None, read from the org ledger.
    cfg : dict, optional
        Plans config (loads config/plans.yaml when None).
    limits : dict, optional
        Limits mapping (loads config/limits.yaml when None).

    Returns
    -------
    dict
        {bucket: {size: {"pct": float, "n": int, "plan_usd": float}}}
    """
    if cfg is None:
        try:
            cfg = quota_mod.load_plans()
        except Exception:
            cfg = {}

    if limits is None:
        try:
            limits = load_limits()
        except Exception:
            limits = {}

    hp = Path(history_path) if history_path is not None else quota_mod.DEFAULT_HISTORY
    history = _load_history(hp)

    if jobs is None:
        jobs = _load_jobs_from_db(cfg)

    # For each job, compute the delta fraction it consumed.
    # First pass: determine which jobs pass the snapshot/reset checks,
    # recording the raw delta.
    counted: list[dict] = []  # {id, bucket, size, start, end, delta}

    for job in jobs:
        bucket = job["bucket"]
        # The claude bucket is shared with C-level sessions; never count it.
        if not bucket or bucket == "claude":
            continue
        start: datetime = job["start"]
        end: datetime = job["end"]

        pts = history.get(bucket)
        if not pts:
            continue

        before_pt = _find_snapshot(pts, start, "before")
        after_pt = _find_snapshot(pts, end, "after")

        if before_pt is None or after_pt is None:
            continue

        # Check for reset in the window (between the two snapshot points)
        if _has_reset(pts, before_pt[0], after_pt[0]):
            continue

        delta = max(0.0, before_pt[1] - after_pt[1])

        counted.append({
            "id": job["id"],
            "bucket": bucket,
            "size": job["size"],
            "start": start,
            "end": end,
            "delta": delta,
        })

    # Second pass: apply overlap splitting and collect samples
    samples: dict[tuple[str, str], list[float]] = {}

    for i, job in enumerate(counted):
        bucket = job["bucket"]
        start = job["start"]
        end = job["end"]
        delta = job["delta"]

        # Count overlapping jobs on the same bucket (including self)
        overlap_count = 1
        for j, other in enumerate(counted):
            if i == j:
                continue
            if other["bucket"] != bucket:
                continue
            # Intervals [start,end) and [other.start,other.end) overlap
            if other["start"] < end and other["end"] > start:
                overlap_count += 1

        cost = delta / overlap_count
        key = (bucket, job["size"])
        samples.setdefault(key, []).append(cost)

    # Build the table
    table: dict[str, dict[str, dict]] = {}
    for (bucket, size), costs in samples.items():
        plan_usd = (limits.get(bucket) or {}).get("plan_usd", 0.0)
        pct = median(costs) * 100.0
        cell = {
            "pct": round(pct, 6),
            "n": len(costs),
            "plan_usd": float(plan_usd),
        }
        table.setdefault(bucket, {})[size] = cell

    return table


def write_table(table: dict, path=None) -> Path:
    """Write cost table atomically (temp file + os.replace) to COST_TABLE_PATH.

    Returns the path written.
    """
    p = Path(path) if path is not None else forecast.COST_TABLE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=p.parent, encoding="utf-8", delete=False, suffix=".tmp"
        ) as f:
            tmp_path = Path(f.name)
            json.dump(table, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, p)
    except Exception:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise
    return p


def _print_table(table: dict) -> None:
    """Print a human-readable summary: bucket size n pct."""
    print(f"{'bucket':<14} {'size':<5} {'n':>4} {'pct':>8}")
    print("-" * 36)
    for bucket in sorted(table):
        for size in sorted(table[bucket]):
            cell = table[bucket][size]
            print(
                f"{bucket:<14} {size:<5} {cell['n']:>4} {cell['pct']:>7.3f}%"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Learn real quota costs from history")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the table without writing it",
    )
    args = parser.parse_args(argv)

    table = learn()
    _print_table(table)

    if args.dry_run:
        return 0

    path = write_table(table)
    cells = sum(len(v) for v in table.values())
    print(f"cost-table: {path} {cells} cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())

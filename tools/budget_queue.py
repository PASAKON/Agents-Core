"""FIFO of pending budget refusals; watchdog retries one ready entry per tick."""
from datetime import datetime, timezone
from pathlib import Path

from tools import disk_queue, usage_budget

QUEUE_PATH = Path(__file__).resolve().parent.parent / "state" / "budget_queue.jsonl"


def all_entries(*, path=None):
    return disk_queue.all_entries(path=path or QUEUE_PATH)


def enqueue(task_id, owner_cto, *, tier="normal", path=None):
    path = path or QUEUE_PATH
    entries = all_entries(path=path)
    for i, entry in enumerate(entries):
        if entry["task_id"] == task_id:
            return i
    rows = usage_budget.load_gate_rows() or {}
    entries.append({"task_id": task_id, "owner_cto": owner_cto, "tier": tier,
                    "queued_at": disk_queue.db.now_iso(),
                    "buckets": [b for b, r in rows.items() if r["state"] == "over"]})
    disk_queue._save(entries, path)
    return len(entries) - 1


def is_queued(task_id, *, path=None):
    return disk_queue.is_queued(task_id, path=path or QUEUE_PATH)


def pop(task_id, *, path=None):
    disk_queue.pop(task_id, path=path or QUEUE_PATH)


def ready(entry, *, now=None, budget_path=None):
    now = now or datetime.now(timezone.utc)
    queued = usage_budget.timestamp(entry["queued_at"])
    if queued.astimezone(usage_budget.THAI).date() < now.astimezone(usage_budget.THAI).date():
        return True
    rows = usage_budget.load_gate_rows(path=budget_path, now=now)
    # Retry through the router, which checks the task's specific tier and runners.
    if not rows:
        return True
    buckets = entry.get("buckets") or list(rows)
    if any(b not in rows for b in buckets):
        return True
    states = [rows[b]["state"] == "under" for b in buckets]
    return all(states) if entry.get("tier") == "low" else any(states)

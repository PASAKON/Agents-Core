"""FIFO of pending budget refusals; watchdog retries one ready entry per tick."""
import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools import disk_queue, usage_budget

try:
    import fcntl
except ImportError:          # Windows: no fcntl; the hub host (Linux) is where delegate + watchdog race
    fcntl = None

QUEUE_PATH = Path(__file__).resolve().parent.parent / "state" / "budget_queue.jsonl"


@contextlib.contextmanager
def _locked(path):
    """One writer at a time: delegate enqueues and the watchdog pops/rotates in other processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "a") as fh:
        if fcntl:
            fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_UN)


def _save(entries, path):
    """Write a temp file and rename it over the queue: a crash never leaves a truncated queue."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def all_entries(*, path=None):
    return disk_queue.all_entries(path=path or QUEUE_PATH)


def _entry(task_id, owner_cto, tier):
    rows = usage_budget.load_gate_rows() or {}
    return {"task_id": task_id, "owner_cto": owner_cto, "tier": tier,
            "queued_at": disk_queue.db.now_iso(),
            "buckets": [b for b, r in rows.items() if r["state"] == "over"]}


def enqueue(task_id, owner_cto, *, tier="normal", path=None):
    path = path or QUEUE_PATH
    with _locked(path):
        entries = all_entries(path=path)
        for i, entry in enumerate(entries):
            if entry["task_id"] == task_id:
                return i
        entries.append(_entry(task_id, owner_cto, tier))
        _save(entries, path)
        return len(entries) - 1


def requeue(task_id, owner_cto, *, tier="normal", path=None):
    """Move a task to the tail with a fresh queued_at, in one locked write."""
    path = path or QUEUE_PATH
    with _locked(path):
        entries = [e for e in all_entries(path=path) if e["task_id"] != task_id]
        entries.append(_entry(task_id, owner_cto, tier))
        _save(entries, path)


def is_queued(task_id, *, path=None):
    return disk_queue.is_queued(task_id, path=path or QUEUE_PATH)


def pop(task_id, *, path=None):
    path = path or QUEUE_PATH
    with _locked(path):
        entries = all_entries(path=path)
        kept = [e for e in entries if e["task_id"] != task_id]
        if len(kept) != len(entries):
            _save(kept, path)


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
    if entry.get("tier") == "low":
        buckets = [b for b in buckets if b in ("agy-gemini", "codex", "claude")]
    if any(b not in rows for b in buckets):
        return True
    states = [rows[b]["state"] == "under" for b in buckets]
    return all(states) if entry.get("tier") == "low" else any(states)

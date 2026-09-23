"""FIFO queue for tasks the ADR 0030 disk floor refused to spawn.

tools/delegate.py's `delegate_task` refuses a spawn when free space is below
`gauge.orange` (config/storage-policy.yaml) for a `disk_floor`-scoped task
(tools/delegate.py:1270-1278). Before this module the refusal only wrote a
`delegate_log` line and left the CEO to notice and re-delegate by hand
("สั่งเป็นกฎอย่างเดียวไม่ได้ ต้องทำระบบเข้าคิวไว้ด้วย รันตามคิว" — CEO
2026-09-23, task-dbe47b9b). This module is the queue; `runners/watchdog.py`'s
`scan_once` is the thing that drains it, one task per tick, once space is
back (see its own docstring for the drain logic).

Storage: `state/disk_queue.jsonl`, one JSON object per line, append-order ==
FIFO order (oldest first is just "read top to bottom", no sort key needed).
A flat file over a new sqlite table because: the whole queue is read and
rewritten as a whole on every pop (a handful of rows at most — the disk
floor refusing spawns is meant to be rare), nothing here is ever queried by
SQL, and it mirrors an existing convention already in this codebase
(`Work/_ledger.jsonl`, written by `tools/workdir.py close()`) rather than
adding a fourth persistence mechanism next to tasks.db, mailbox's per-file
inboxes, and the ledger.

Each entry: `{"task_id", "owner_cto", "queued_at"}`. `queued_at` is
`lib.db.now_iso()` (UTC, second precision) — same clock every other
timestamp in this codebase uses.
"""
from __future__ import annotations

import json
from pathlib import Path

from lib import db

ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "state" / "disk_queue.jsonl"


def _load(path: Path | None = None) -> list[dict]:
    p = path or QUEUE_PATH
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _save(entries: list[dict], path: Path | None = None) -> None:
    p = path or QUEUE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
        encoding="utf-8",
    )


def enqueue(task_id: str, owner_cto: str | None, *,
            path: Path | None = None) -> int:
    """Append `task_id` to the tail unless it is already queued (idempotent
    — a task can hit the disk-floor refusal more than once before the
    watchdog ever pops it, e.g. a caller retrying by hand). Returns its
    0-based position, i.e. how many tasks are ahead of it."""
    entries = _load(path)
    for i, e in enumerate(entries):
        if e.get("task_id") == task_id:
            return i
    entries.append({
        "task_id": task_id,
        "owner_cto": owner_cto,
        "queued_at": db.now_iso(),
    })
    _save(entries, path)
    return len(entries) - 1


def position(task_id: str, *, path: Path | None = None) -> int | None:
    """0-based FIFO position of `task_id`, or None if it isn't queued."""
    for i, e in enumerate(_load(path)):
        if e.get("task_id") == task_id:
            return i
    return None


def is_queued(task_id: str, *, path: Path | None = None) -> bool:
    return position(task_id, path=path) is not None


def peek(*, path: Path | None = None) -> dict | None:
    """The oldest queued entry, or None if the queue is empty."""
    entries = _load(path)
    return entries[0] if entries else None


def pop(task_id: str, *, path: Path | None = None) -> None:
    """Remove `task_id` from the queue, wherever it sits — the FIFO head in
    the normal drain path, but also a task cancelled/closed while it waited
    (dropped, never spawned). A no-op if it isn't queued."""
    entries = _load(path)
    kept = [e for e in entries if e.get("task_id") != task_id]
    if len(kept) != len(entries):
        _save(kept, path)


def all_entries(*, path: Path | None = None) -> list[dict]:
    """Every queued entry, oldest first."""
    return _load(path)

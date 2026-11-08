"""Host-capacity FIFO, retried by the existing watchdog (no new timer).

The watchdog runs as root and state/ is group-writable, so every open here goes through lib.safe_file: a link,
a FIFO or a second hard link at either file name is refused, never followed and never waited on.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path

from datetime import datetime, timedelta, timezone
from lib import db, safe_file

_DEFAULT_QUEUE_PATH = Path(__file__).resolve().parents[1] / "state" / "host_queue.jsonl"
QUEUE_PATH = _DEFAULT_QUEUE_PATH
QUEUE_LIMIT = 1024 * 1024    # bytes read back; a few thousand entries
_HUB_KEY_PREFIX = "host_queue:"


def _hub_sync_enabled() -> bool:
    return QUEUE_PATH == _DEFAULT_QUEUE_PATH and os.environ.get("ORG_HUB_QUEUE_SYNC") == "1"


def _hub_upsert(entry: dict) -> None:
    if not _hub_sync_enabled():
        return
    try:
        key = f"{_HUB_KEY_PREFIX}{entry['task_id']}"
        exp = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(timespec="seconds")
        payload = json.dumps(entry, ensure_ascii=False)
        with db.get_conn() as conn:
            conn.execute(
                "INSERT INTO locks (key, owner, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET owner=excluded.owner, expires_at=excluded.expires_at",
                (key, payload, exp),
            )
    except Exception:
        pass


def _hub_delete(task_id: str) -> None:
    if not _hub_sync_enabled():
        return
    try:
        with db.get_conn() as conn:
            conn.execute("DELETE FROM locks WHERE key=?", (f"{_HUB_KEY_PREFIX}{task_id}",))
    except Exception:
        pass


def _hub_entries() -> list[dict]:
    if not _hub_sync_enabled():
        return []
    out: list[dict] = []
    try:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with db.get_conn() as conn:
            rows = conn.execute(
                "SELECT owner FROM locks WHERE key LIKE ? AND expires_at > ?",
                (f"{_HUB_KEY_PREFIX}%", now),
            ).fetchall()
        for r in rows:
            try:
                item = json.loads(r["owner"])
                if isinstance(item, dict) and "task_id" in item:
                    out.append(item)
            except Exception:
                continue
    except Exception:
        pass
    out.sort(key=lambda e: str(e.get("queued_at") or ""))
    return out


@contextmanager
def _locked():
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = safe_file._open(QUEUE_PATH.with_suffix(".lock"), os.O_RDWR | os.O_CREAT,
                         mode=0o600, single_link=True)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)     # closing the fd drops the lock


def load() -> list[dict]:
    """The queued entries, oldest first; [] when there is no queue file. An unsafe file raises safe_file.Unsafe."""
    try:
        text = safe_file.read_text(QUEUE_PATH, QUEUE_LIMIT)
    except FileNotFoundError:
        return []
    out = []
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and "task_id" in entry:
            out.append(entry)
    return out


def _save(entries: list[dict]) -> None:
    safe_file.write_text_atomic(
        QUEUE_PATH, "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))


def enqueue(task_id, owner_cto, *, host=None) -> int:
    with _locked():
        entries = load()
        ahead = 0
        target_entry = None
        for idx, entry in enumerate(entries):
            if entry["task_id"] == task_id:
                entry["host"] = host
                ahead = idx
                target_entry = entry
                break
        else:
            ahead = len(entries)
            target_entry = dict(task_id=task_id, owner_cto=owner_cto,
                                host=host, queued_at=db.now_iso())
            entries.append(target_entry)
        _save(entries)
    if target_entry:
        _hub_upsert(target_entry)
    return ahead


def remove(task_id: str) -> bool:
    """Remove `task_id` from the host queue if present. Returns True if removed."""
    with _locked():
        entries = load()
        kept = [e for e in entries if e.get("task_id") != task_id]
        changed = len(kept) != len(entries)
        if changed:
            _save(kept)
    _hub_delete(task_id)
    return changed


async def drain(max_spawns: int = 3):
    """Scan queued entries in FIFO order and spawn up to `max_spawns` eligible tasks
    in a single pass so a blocked head-of-line entry never stalls tasks behind it."""
    from tools import delegate
    with _locked():
        local_entries = load()
        seen_ids = {e["task_id"] for e in local_entries}
        for he in _hub_entries():
            if he["task_id"] not in seen_ids:
                local_entries.append(he)
                seen_ids.add(he["task_id"])
        if not local_entries:
            return
        snapshot = list(local_entries)
        _save(local_entries)

    last_row = None
    spawned = 0
    for candidate in snapshot:
        if spawned >= max_spawns:
            break
        tid = candidate["task_id"]
        with _locked():
            entries = load()
            idx = next((i for i, e in enumerate(entries) if e.get("task_id") == tid), None)
            if idx is None:
                continue
            entry = entries.pop(idx)
            _save(entries)
        task = db.get_task(tid)
        if not task or task["status"] != "pending":
            _hub_delete(tid)
            continue
        try:
            row = await delegate.delegate_task(tid, host=entry.get("host"))
        except Exception:
            enqueue(tid, entry.get("owner_cto"), host=entry.get("host"))
            raise
        last_row = row
        if row and row.get("status") == "pending":
            enqueue(tid, entry.get("owner_cto"), host=entry.get("host"))
        else:
            _hub_delete(tid)
            spawned += 1
    return last_row

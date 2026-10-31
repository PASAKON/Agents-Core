"""Host-capacity FIFO, retried by the existing watchdog (no new timer).

The watchdog runs as root and state/ is group-writable, so every open here goes through lib.safe_file: a link,
a FIFO or a second hard link at either file name is refused, never followed and never waited on.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path

from lib import db, safe_file

QUEUE_PATH = Path(__file__).resolve().parents[1] / "state" / "host_queue.jsonl"
QUEUE_LIMIT = 1024 * 1024    # bytes read back; a few thousand entries


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


def enqueue(task_id, owner_cto, *, host=None):
    with _locked():
        entries = load()
        for entry in entries:
            if entry["task_id"] == task_id:
                entry["host"] = host
                break
        else:
            entries.append(dict(task_id=task_id, owner_cto=owner_cto,
                                host=host, queued_at=db.now_iso()))
        _save(entries)


async def drain():
    from tools import delegate
    with _locked():
        entries = load()
        if not entries:
            return
        entry = entries.pop(0)
        _save(entries)
    task = db.get_task(entry["task_id"])
    if not task or task["status"] != "pending":
        return
    try:
        row = await delegate.delegate_task(task["id"], host=entry.get("host"))
    except Exception:
        enqueue(task["id"], entry.get("owner_cto"), host=entry.get("host"))
        raise
    if row.get("status") == "pending":
        enqueue(task["id"], entry.get("owner_cto"), host=entry.get("host"))
    return row

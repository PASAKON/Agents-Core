"""Host-capacity FIFO, retried by the existing watchdog (no new timer)."""
from contextlib import contextmanager
import fcntl
from pathlib import Path

from lib import db
from tools import disk_queue

QUEUE_PATH = Path(__file__).resolve().parents[1] / "state" / "host_queue.jsonl"


@contextmanager
def _locked():
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with QUEUE_PATH.with_suffix(".lock").open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def enqueue(task_id, owner_cto, *, host=None):
    with _locked():
        entries = disk_queue._load(QUEUE_PATH)
        for entry in entries:
            if entry["task_id"] == task_id:
                entry["host"] = host
                break
        else:
            entries.append(dict(task_id=task_id, owner_cto=owner_cto,
                                host=host, queued_at=db.now_iso()))
        disk_queue._save(entries, QUEUE_PATH)


async def drain():
    from tools import delegate
    with _locked():
        entries = disk_queue._load(QUEUE_PATH)
        if not entries:
            return
        entry = entries.pop(0)
        disk_queue._save(entries, QUEUE_PATH)
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

#!/usr/bin/env python3
"""Bump a task's updated_at so the watchdog does not reap a healthy worker.

runners/watchdog.py measures a worker's silence from `tasks.updated_at`, not
from process liveness. A worker sitting in a long poll (a Higgsfield render is
26-30 minutes, one measured 80+) writes no DB row, so it looks silent. At
STALL_ALIVE_AFTER_S (150 min) the watchdog flips the task to `stalled`, files
a GH issue, and tears the tmux session down mid-queue.

That reaped a healthy worker on 2026-08-12/13 (the ceiling was raised 90->150
in response) and reaped two more on 2026-09-01 at 20:30 and 23:36, each time
losing an unreported queue. Raising the ceiling again only moves the cliff;
what was missing is a way for a waiting worker to say "still here".

    python3 scripts/worker-heartbeat.py <task_id>

Touches exactly one column on one row. Prints the new timestamp. Exits 1 if
the task does not exist, so a typo'd id fails loudly instead of silently
protecting nothing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.db import get_conn, now_iso  # noqa: E402


def beat(task_id: str) -> str:
    ts = now_iso()
    with get_conn() as conn:
        cur = conn.execute("UPDATE tasks SET updated_at=? WHERE id=?", (ts, task_id))
        if cur.rowcount == 0:
            raise SystemExit(f"worker-heartbeat: no such task {task_id!r}")
    return ts


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: worker-heartbeat.py <task_id>")
    print(f"heartbeat {sys.argv[1]} -> {beat(sys.argv[1])}")

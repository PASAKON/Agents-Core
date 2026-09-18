#!/usr/bin/env python3
"""Step-1 safety gate for scripts/hub/cutover-mac.sh (docs/design/
tasks-db-hub.md §3.3): refuse the cutover while real work is in flight,
without refusing forever on rows a reaper has already cleaned up.

Split out of the bash heredoc it used to be (task-7ad6ad8a) so the liveness
logic is importable and unit-testable -- scripts/hub/test_cutover_gate.py
stubs _pid_alive/_pid_matches_task and never touches a real pid or the real
DB.

Measured on the live Mac DB (task-7ad6ad8a brief): 55 `review` rows carry a
pid, every one of them a worker reaped days or weeks ago. The OLD gate --
"any review row with a pid" -- refused forever even though nothing was
running. `in_progress` always counts as in-flight: a worker only reaches
that status while actually claimed and running. `review` is different: the
watchdog/CTO leave a task in `review` long after its DEV process is gone,
and the row keeps whatever pid it last recorded (task-78ab64ba). A `review`
row only counts as in-flight when its pid is BOTH alive AND still matches
this task's command line (tools.worker_reap._pid_matches_task) -- the same
identity check the reaper itself uses before ever signalling a pid, so a
dead or recycled pid (the ordinary state after reaping) never blocks a
cutover that is otherwise safe.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db  # noqa: E402
from tools.worker_reap import _pid_alive, _pid_matches_task  # noqa: E402


def classify_tasks(rows: list[dict]) -> tuple[list[dict], int]:
    """Split `rows` into (in-flight rows, count of stale-pid review rows).

    In-flight = status `in_progress` (unconditionally), or status `review`
    with a pid that is both alive and identity-matched to the task. A
    `review` row with no pid, a dead pid, or a pid recycled onto an
    unrelated process is not in-flight -- it is counted as stale instead.
    """
    live: list[dict] = []
    stale = 0
    for r in rows:
        status = r.get("status")
        if status == "in_progress":
            live.append(r)
            continue
        if status == "review" and r.get("pid"):
            pid = int(r["pid"])
            if _pid_alive(pid) and _pid_matches_task(pid, r["id"]):
                live.append(r)
            else:
                stale += 1
    return live, stale


def main() -> int:
    rows = db.list_tasks(limit=2000)
    live, stale = classify_tasks(rows)
    if live:
        print("REFUSING: tasks still in flight:")
        for r in live:
            print(f"{r['id']}\t{r['status']}\t{r['role']}\t{r['title']}")
        return 1
    print("ok: no in_progress tasks, no review tasks with a live matching pid.")
    if stale:
        print(f"info: {stale} review row(s) carry a dead pid (normal after reaping)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

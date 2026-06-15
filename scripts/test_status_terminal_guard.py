"""Regression test for issue #13 — phantom path-locks after a successful merge.

Root cause: `db.update_status` overwrote a task's status unconditionally, so a
racing/duplicate merge_task (git-conflict branch) or re-delegate could flip an
already merged task (`done`) back to `conflict`. Because `conflict` is an
ACTIVE_STATUS, `find_conflicts` then reported the merged task as a live path-lock
(self-collision), blocking every future task touching the same paths.

Fix: an atomic terminal-guard in `update_status` refuses to resurrect a
`done`/`merged` task into an active status (pending/in_progress/conflict/
rate_limited) unless `force=True` (reopen/revert pass force).

Run via:  python scripts/test_status_terminal_guard.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _insert(tid: str, status: str, touches: list[str]) -> None:
    ts = db.now_iso()
    with db.get_conn() as c:
        c.execute(
            "INSERT INTO tasks(id,project,role,status,title,description,"
            "touches,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (tid, "mooniex-webapp", "data_analyst", status, "seed",
             "d", json.dumps(touches), ts, ts),
        )


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="t13-")
    db.DB_PATH = Path(tmp) / "tasks.db"
    db.init()

    paths = ["supabase/schema.sql", "supabase/migrations/"]

    # ---- Scenario 1: merged task must not be resurrected to conflict ----
    t1 = db.new_task_id()
    _insert(t1, "done", paths)               # simulate merged+done

    res = db.update_status(t1, "conflict")   # racing merge_task git-conflict path
    _mark(db.get_task(t1)["status"] == "done",
          "done task stays 'done' when a racing op tries to set 'conflict'")
    _mark(res is False,
          "update_status returns False on a refused terminal->active transition")

    # The phantom-lock symptom: find_conflicts must NOT see the merged task.
    hits = db.find_conflicts("mooniex-webapp", paths)
    _mark(hits == [],
          "find_conflicts returns no phantom lock for a merged task")

    # ---- Scenario 2: same guard for 'merged' + pending/in_progress ----
    t2 = db.new_task_id()
    _insert(t2, "merged", paths)
    db.update_status(t2, "pending")
    _mark(db.get_task(t2)["status"] == "merged",
          "merged task stays 'merged' against a stray 'pending'")
    db.update_status(t2, "in_progress")
    _mark(db.get_task(t2)["status"] == "merged",
          "merged task stays 'merged' against a stray 'in_progress'")

    # ---- Scenario 3: force=True still resurrects (reopen/revert path) ----
    t3 = db.new_task_id()
    _insert(t3, "done", paths)
    db.update_status(t3, "pending", force=True)
    _mark(db.get_task(t3)["status"] == "pending",
          "force=True resurrects a done task (reopen path preserved)")

    # ---- Scenario 4: legit non-terminal transitions are unaffected ----
    t4 = db.new_task_id()
    _insert(t4, "review", paths)             # DEV reported, awaiting merge
    db.update_status(t4, "conflict")         # a genuinely unmergeable review task
    _mark(db.get_task(t4)["status"] == "conflict",
          "review->conflict still allowed (real merge conflict on un-merged work)")

    t5 = db.new_task_id()
    _insert(t5, "pending", paths)
    db.update_status(t5, "in_progress")
    _mark(db.get_task(t5)["status"] == "in_progress",
          "pending->in_progress still allowed")

    print(f"\n{'ALL PASS' if _failures == 0 else f'{_failures} FAILURE(S)'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for tools/gc_stale_tasks.py.

Tests:
  1. Stale pending task (31 min old, no assigned_agent) → cancelled + lock released.
  2. Fresh pending task (5 min old) → NOT cancelled.
  3. Conflict task 30 min old → NOT cancelled (threshold is 60 min).
  4. Conflict task 61 min old → cancelled.
  5. --dry-run does not write to DB.
  6. Idempotent: running GC twice on a cancelled task produces no error.
  7. Path lock held by stale pending task is released after GC.

Run via: python scripts/test_gc_stale_tasks.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_mod
from tools.gc_stale_tasks import gc_stale_tasks

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _ts(delta_minutes: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)
    return dt.isoformat(timespec="seconds")


def _insert_task(conn, *, status: str, age_minutes: float,
                 project: str = "test-proj",
                 assigned_agent: str | None = None,
                 retry_after_ts: str | None = None,
                 touches: list[str] | None = None) -> str:
    tid = "task-" + uuid.uuid4().hex[:8]
    ts_old = _ts(age_minutes)
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            assigned_agent, retry_after_ts, touches,
            depends_on, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, project, "developer", status, "test", "test",
         assigned_agent, retry_after_ts,
         json.dumps(touches or []),
         "[]", ts_old, ts_old),
    )
    conn.commit()
    return tid


def run_tests(tmp_db: Path) -> None:
    # Point db module at temp DB for this test run.
    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = tmp_db
    try:
        db_mod.init()
        with db_mod.get_conn() as conn:

            # 1. Stale pending task (31 min, no agent) → should cancel
            tid1 = _insert_task(conn, status="pending", age_minutes=31)

            # 2. Fresh pending task (5 min, no agent) → should NOT cancel
            tid2 = _insert_task(conn, status="pending", age_minutes=5)

            # 3. Conflict task 30 min old → NOT cancelled (threshold=60)
            tid3 = _insert_task(conn, status="conflict", age_minutes=30)

            # 4. Conflict task 61 min old → should cancel
            tid4 = _insert_task(conn, status="conflict", age_minutes=61)

        # --- Test 1 & 2: basic pending GC ---
        cancelled = gc_stale_tasks(pending_minutes=30, conflict_minutes=60,
                                   ratelimit_minutes=30)
        cancelled_ids = {e["task_id"] for e in cancelled}
        _mark(tid1 in cancelled_ids,
              f"[1] stale pending (31 min) is cancelled — got {cancelled_ids}")
        _mark(tid2 not in cancelled_ids,
              "[2] fresh pending (5 min) NOT cancelled")

        # Verify DB reflects cancellation for tid1
        t1 = db_mod.get_task(tid1)
        _mark(t1 is not None and t1["status"] == "cancelled",
              f"[1b] DB status for {tid1} = cancelled (got {t1 and t1['status']})")

        # Verify DB NOT cancelled for tid2
        t2 = db_mod.get_task(tid2)
        _mark(t2 is not None and t2["status"] == "pending",
              f"[2b] DB status for {tid2} still pending (got {t2 and t2['status']})")

        # --- Test 3 & 4: conflict thresholds ---
        _mark(tid3 not in cancelled_ids,
              "[3] conflict 30 min NOT cancelled (threshold=60)")
        _mark(tid4 in cancelled_ids,
              "[4] conflict 61 min IS cancelled")

        # --- Test 5: dry-run writes nothing ---
        # Insert tid5 here (after first sweep) so it starts in pending state.
        with db_mod.get_conn() as conn:
            tid5 = _insert_task(conn, status="pending", age_minutes=40)
        result_dry = gc_stale_tasks(pending_minutes=30, conflict_minutes=60,
                                    ratelimit_minutes=30, dry_run=True)
        dry_ids = {e["task_id"] for e in result_dry}
        _mark(tid5 in dry_ids,
              f"[5a] dry-run reports stale pending (40 min) — dry_ids={dry_ids}")
        t5_after = db_mod.get_task(tid5)
        _mark(t5_after is not None and t5_after["status"] == "pending",
              "[5b] dry-run did NOT write to DB — status still pending")

        # --- Test 6: idempotent (tid1 already cancelled, re-run is no-op) ---
        cancelled2 = gc_stale_tasks(pending_minutes=30, conflict_minutes=60,
                                    ratelimit_minutes=30)
        cancelled2_ids = {e["task_id"] for e in cancelled2}
        _mark(tid1 not in cancelled2_ids,
              "[6] idempotent: already-cancelled tid1 not re-processed")

        # --- Test 7: lock release ---
        tid7 = "task-locktest"
        with db_mod.get_conn() as conn:
            ts_old = _ts(35)
            conn.execute(
                """INSERT INTO tasks
                   (id, project, role, status, title, description,
                    assigned_agent, retry_after_ts, touches,
                    depends_on, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid7, "test-proj", "developer", "pending", "lock-test", "lock-test",
                 None, None, json.dumps(["src/webhook/claude.js"]),
                 "[]", ts_old, ts_old),
            )
        lock_key = "proj:test-proj:path:src/webhook/claude.js"
        db_mod.acquire_lock(lock_key, owner=tid7, ttl_seconds=3600)
        with db_mod.get_conn() as conn:
            lock_before = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?", (lock_key, tid7)
            ).fetchone()
        _mark(lock_before is not None, "[7a] lock inserted before GC")

        gc_stale_tasks(pending_minutes=30, conflict_minutes=60, ratelimit_minutes=30)

        with db_mod.get_conn() as conn:
            lock_after = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?", (lock_key, tid7)
            ).fetchone()
        _mark(lock_after is None, "[7b] lock released after GC on stale pending task")

        # check_collisions returns empty for the same path now
        conflicts = db_mod.find_conflicts("test-proj", ["src/webhook/claude.js"])
        _mark(not conflicts,
              f"[7c] find_conflicts empty after GC (got {conflicts})")

    finally:
        db_mod.DB_PATH = original_path


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp_db = Path(td) / "test_tasks.db"
        run_tests(tmp_db)

    count = _failures
    print(f"\n{'ALL PASS' if count == 0 else str(count) + ' FAILED'}")
    return 1 if count else 0


if __name__ == "__main__":
    sys.exit(main())

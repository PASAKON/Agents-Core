"""Tests for tools/gc_stale_tasks.py.

Tests:
  1. Stale pending task (31 min old, no assigned_agent) → cancelled + lock released.
  2. Fresh pending task (5 min old) → NOT cancelled.
  3. Conflict task 30 min old → NOT cancelled (threshold is 60 min).
  4. Conflict task 61 min old → cancelled.
  5. --dry-run does not write to DB.
  6. Idempotent: running GC twice on a cancelled task produces no error.
  7. Path lock held by stale pending task is released after GC.
  8. Category 1b: pending + assigned_agent + no pid + 3h old → cancelled,
     locks released, find_conflicts empty afterward (W3 Bug B).
  9. Same shape at 40 min old → untouched (120min floor).
  10. 'done' row holding locks (status set outside db.update_status,
      simulating W3 Bug A) → locks released, status/worktree untouched.
  11. 'in_progress' row holding locks → untouched entirely — guards the
      live tasks this GC pass must never touch.
  12. Lock row whose owner has no task row at all → deleted.
  13. --dry-run writes nothing for any of the new categories either.

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

        # --- Test 8: Category 1b — spawned pending, no pid, 3h old → cancelled ---
        with db_mod.get_conn() as conn:
            tid8 = _insert_task(conn, status="pending", age_minutes=180,
                                assigned_agent="developer",
                                touches=["src/gc_test/a.py"])
        lock_key8 = "proj:test-proj:path:src/gc_test/a.py"
        db_mod.acquire_lock(lock_key8, owner=tid8, ttl_seconds=3600)

        # --- Test 9: same shape but 40 min old → untouched (floor is 120min) ---
        with db_mod.get_conn() as conn:
            tid9 = _insert_task(conn, status="pending", age_minutes=40,
                                assigned_agent="developer")

        # --- Test 10: 'done' row holding locks, simulating W3 Bug A (status
        # written outside db.update_status, so RELEASING_STATUSES never
        # fired) → locks released, status/worktree untouched ---
        with db_mod.get_conn() as conn:
            tid10 = _insert_task(conn, status="done", age_minutes=1000,
                                 touches=["src/gc_test/b.py"])
        lock_key10 = "proj:test-proj:path:src/gc_test/b.py"
        db_mod.acquire_lock(lock_key10, owner=tid10, ttl_seconds=3600)

        # --- Test 11: 'in_progress' row holding locks → must stay fully
        # untouched. This is the guard that protects the live tasks
        # task-bbdfa8d1 / task-41684e16. ---
        with db_mod.get_conn() as conn:
            tid11 = _insert_task(conn, status="in_progress", age_minutes=5,
                                 touches=["src/gc_test/c.py"])
        lock_key11 = "proj:test-proj:path:src/gc_test/c.py"
        db_mod.acquire_lock(lock_key11, owner=tid11, ttl_seconds=3600)

        # --- Test 12: orphan lock — owner has no task row at all ---
        orphan_owner = "task-" + uuid.uuid4().hex[:8]
        lock_key12 = "proj:test-proj:path:src/gc_test/d.py"
        db_mod.acquire_lock(lock_key12, owner=orphan_owner, ttl_seconds=3600)

        cancelled3 = gc_stale_tasks(pending_minutes=30, conflict_minutes=60,
                                    ratelimit_minutes=30)
        cancelled3_ids = {e["task_id"] for e in cancelled3}

        _mark(tid8 in cancelled3_ids,
              f"[8] spawned pending, no pid, 3h old IS cancelled — got {cancelled3_ids}")
        t8 = db_mod.get_task(tid8)
        _mark(t8 is not None and t8["status"] == "cancelled",
              f"[8b] DB status for {tid8} = cancelled (got {t8 and t8['status']})")
        with db_mod.get_conn() as conn:
            lock8_after = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?", (lock_key8, tid8)
            ).fetchone()
        _mark(lock8_after is None,
              "[8c] lock released for cancelled spawned-pending task")
        conflicts8 = db_mod.find_conflicts("test-proj", ["src/gc_test/a.py"])
        _mark(not conflicts8, f"[8d] find_conflicts empty after GC (got {conflicts8})")

        _mark(tid9 not in cancelled3_ids,
              "[9] spawned pending at 40 min NOT cancelled (floor is 120min)")
        t9 = db_mod.get_task(tid9)
        _mark(t9 is not None and t9["status"] == "pending",
              f"[9b] DB status for {tid9} still pending (got {t9 and t9['status']})")

        t10 = db_mod.get_task(tid10)
        _mark(t10 is not None and t10["status"] == "done",
              f"[10a] status for {tid10} untouched (got {t10 and t10['status']})")
        _mark(t10 is not None and not t10.get("worktree"),
              f"[10b] worktree for {tid10} untouched (got {t10 and t10.get('worktree')})")
        with db_mod.get_conn() as conn:
            lock10_after = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?", (lock_key10, tid10)
            ).fetchone()
        _mark(lock10_after is None,
              "[10c] locks released for terminal 'done' owner")

        with db_mod.get_conn() as conn:
            lock11_after = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?", (lock_key11, tid11)
            ).fetchone()
        _mark(lock11_after is not None,
              "[11a] lock for 'in_progress' owner untouched")
        t11 = db_mod.get_task(tid11)
        _mark(t11 is not None and t11["status"] == "in_progress",
              f"[11b] status for {tid11} untouched (got {t11 and t11['status']})")

        with db_mod.get_conn() as conn:
            lock12_after = conn.execute(
                "SELECT 1 FROM locks WHERE key=? AND owner=?",
                (lock_key12, orphan_owner)
            ).fetchone()
        _mark(lock12_after is None,
              "[12] orphan lock (owner has no task row) deleted")

        # --- Test 13: --dry-run writes nothing for the new categories either ---
        with db_mod.get_conn() as conn:
            tid13 = _insert_task(conn, status="pending", age_minutes=200,
                                 assigned_agent="developer",
                                 touches=["src/gc_test/e.py"])
            tid14 = _insert_task(conn, status="done", age_minutes=10,
                                 touches=["src/gc_test/f.py"])
        lock_key13 = "proj:test-proj:path:src/gc_test/e.py"
        lock_key14 = "proj:test-proj:path:src/gc_test/f.py"
        db_mod.acquire_lock(lock_key13, owner=tid13, ttl_seconds=3600)
        db_mod.acquire_lock(lock_key14, owner=tid14, ttl_seconds=3600)
        orphan_owner2 = "task-" + uuid.uuid4().hex[:8]
        lock_key15 = "proj:test-proj:path:src/gc_test/g.py"
        db_mod.acquire_lock(lock_key15, owner=orphan_owner2, ttl_seconds=3600)

        result_dry2 = gc_stale_tasks(pending_minutes=30, conflict_minutes=60,
                                     ratelimit_minutes=30, dry_run=True)
        dry2_ids = {e["task_id"] for e in result_dry2}
        _mark(tid13 in dry2_ids and tid14 in dry2_ids and orphan_owner2 in dry2_ids,
              f"[13a] dry-run reports all three new-category entries — got {dry2_ids}")

        t13 = db_mod.get_task(tid13)
        _mark(t13 is not None and t13["status"] == "pending",
              "[13b] dry-run: spawned-pending status untouched")
        t14 = db_mod.get_task(tid14)
        _mark(t14 is not None and t14["status"] == "done",
              "[13c] dry-run: done status untouched")
        with db_mod.get_conn() as conn:
            l13 = conn.execute("SELECT 1 FROM locks WHERE key=? AND owner=?",
                               (lock_key13, tid13)).fetchone()
            l14 = conn.execute("SELECT 1 FROM locks WHERE key=? AND owner=?",
                               (lock_key14, tid14)).fetchone()
            l15 = conn.execute("SELECT 1 FROM locks WHERE key=? AND owner=?",
                               (lock_key15, orphan_owner2)).fetchone()
        _mark(l13 is not None and l14 is not None and l15 is not None,
              "[13d] dry-run released/deleted no lock rows at all")

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

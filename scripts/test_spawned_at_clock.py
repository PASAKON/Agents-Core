"""Tests for `tasks.spawned_at` — the clock that answers "when was a DEV
last actually spawned for this task".

Context (GH #51, #52, #53): several subsystems asked `updated_at` that
question. `updated_at` means only "something wrote to this row", so every
unrelated write answered it wrongly:

  * `tools/delegate.py` read it as "a spawn was just issued", so the
    duplicate-spawn guard fired on a row `reopen_task` had merely touched.
    Worse, its own refusal wrote `delegate_log`, resetting the clock it had
    just read — so each retry pushed the lockout further out. Measured:
    six minutes of lockout on task-cda4f469, 2026-08-13 01:07.
  * `tools/gc_stale_tasks.py` Category 1 aged tasks off `created_at`, which
    is when create_task ran, not when the DEV started — and never checked
    whether a process was alive. Measured: task-7d4b567b cancelled ~30s
    after delegate with pid 47128 in state R+, its worktree then reclaimed
    out from under the running process.

These tests pin the behaviour the fix depends on.

Run via: python scripts/test_spawned_at_clock.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db as db_mod  # noqa: E402
from tools.gc_stale_tasks import gc_stale_tasks  # noqa: E402

FAILURES: list[str] = []


def _mark(ok: bool, label: str, got=None) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}"
          + (f" — got {got!r}" if got is not None else ""))
    if not ok:
        FAILURES.append(label)


def _ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _insert(conn, tid: str, *, created_min: float,
            spawned_min: float | None, pid: int | None) -> None:
    """Insert a pending, unclaimed task — the shape gc Category 1 sweeps."""
    conn.execute(
        """INSERT INTO tasks
           (id, project, role, status, title, description,
            assigned_agent, touches, depends_on,
            created_at, updated_at, spawned_at, pid)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, "test-proj", "developer", "pending", "test", "test",
         None, json.dumps([]), "[]",
         _ago(created_min), _ago(created_min),
         None if spawned_min is None else _ago(spawned_min), pid),
    )
    conn.commit()


def run_tests(tmp_db: Path) -> None:
    original_path = db_mod.DB_PATH
    db_mod.DB_PATH = tmp_db
    try:
        db_mod.init()

        with db_mod.get_conn() as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        _mark("spawned_at" in cols, "[0] migration added tasks.spawned_at")

        print("\n1) an unrelated write must not look like a fresh spawn")
        with db_mod.get_conn() as conn:
            _insert(conn, "task-sp01", created_min=90, spawned_min=90, pid=None)
        before = db_mod.get_task("task-sp01")["spawned_at"]
        # This is the exact write delegate_task's refusal performs. Before
        # the fix it reset the clock the refusal had just read.
        db_mod.set_fields("task-sp01", delegate_log="a refusal", actor="test")
        after = db_mod.get_task("task-sp01")
        _mark(after["spawned_at"] == before,
              "[1a] writing delegate_log leaves spawned_at untouched")
        _mark(after["updated_at"] != before,
              "[1b] ...while updated_at did move (proving they differ)")

        print("\n2) gc never reaps a pending task whose process is alive")
        with db_mod.get_conn() as conn:
            # Old on every clock, but the pid is this interpreter, so it is
            # provably running right now.
            _insert(conn, "task-sp02", created_min=600, spawned_min=600,
                    pid=os.getpid())
        gc_stale_tasks(pending_minutes=30)
        _mark(db_mod.get_task("task-sp02")["status"] == "pending",
              "[2] live-pid pending task survives gc",
              db_mod.get_task("task-sp02")["status"])

        print("\n3) gc still reaps a genuinely abandoned pending task")
        with db_mod.get_conn() as conn:
            _insert(conn, "task-sp03", created_min=600, spawned_min=600,
                    pid=None)
        gc_stale_tasks(pending_minutes=30)
        _mark(db_mod.get_task("task-sp03")["status"] == "cancelled",
              "[3] abandoned pending task is cancelled",
              db_mod.get_task("task-sp03")["status"])

        print("\n4) gc ages from the spawn, not from row creation")
        with db_mod.get_conn() as conn:
            # The regression: created long ago, delegated one minute ago.
            # Off created_at this read as 600 minutes stale the instant its
            # DEV started.
            _insert(conn, "task-sp04", created_min=600, spawned_min=1,
                    pid=None)
        gc_stale_tasks(pending_minutes=30)
        _mark(db_mod.get_task("task-sp04")["status"] == "pending",
              "[4] old row with a fresh spawn survives gc",
              db_mod.get_task("task-sp04")["status"])

        print("\n5) a task never delegated still falls back to created_at")
        with db_mod.get_conn() as conn:
            _insert(conn, "task-sp05", created_min=600, spawned_min=None,
                    pid=None)
        gc_stale_tasks(pending_minutes=30)
        _mark(db_mod.get_task("task-sp05")["status"] == "cancelled",
              "[5] never-spawned old task is still cancelled",
              db_mod.get_task("task-sp05")["status"])
    finally:
        db_mod.DB_PATH = original_path


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        run_tests(Path(td) / "tasks.db")
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

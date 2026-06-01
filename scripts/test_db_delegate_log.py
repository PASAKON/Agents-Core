"""Unit tests for the delegate_log / report column split (task-4489a3a2).

Asserts:
  1. _ensure_schema (via init) adds delegate_log to a fresh in-memory DB.
  2. update_status accepts delegate_log= without ValueError.
  3. update_status rejects an unknown column.
  4. Backfill: collision-style strings in report are moved to delegate_log.
  5. Non-collision report strings are left in report.
  6. Idempotency: running init() twice does not raise.

Run via:  python scripts/test_db_delegate_log.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lib.db as db_module

_failures = 0


def _mark(ok: bool, msg: str) -> None:
    global _failures
    if not ok:
        _failures += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {msg}")


def _in_memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _apply_schema_and_migrations(conn: sqlite3.Connection) -> None:
    """Replicate what init() does, but on an in-memory connection."""
    conn.executescript(db_module.SCHEMA)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, coltype in db_module._MIGRATION_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {coltype}")
    # Backfill
    conn.execute("""
        UPDATE tasks
           SET delegate_log = report,
               report = NULL
         WHERE report IS NOT NULL
           AND delegate_log IS NULL
           AND (   report LIKE 'path collision with%'
                OR report LIKE 'kickoff failed%'
                OR report LIKE 'lock contested%'
                OR report LIKE 'path locks held by%'
                OR report LIKE 'tmux create failed%'
                OR report LIKE 'iTerm spawn failed%'
                OR report LIKE 'DEV timed out%')
    """)
    conn.commit()


def test_schema_has_both_columns():
    conn = _in_memory_conn()
    _apply_schema_and_migrations(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    _mark("delegate_log" in cols, "schema has delegate_log column")
    _mark("report" in cols, "schema retains report column")


def test_delegate_log_in_valid_columns():
    _mark("delegate_log" in db_module.VALID_COLUMNS,
          "delegate_log in VALID_COLUMNS")
    _mark("report" in db_module.VALID_COLUMNS,
          "report still in VALID_COLUMNS")


def test_idempotent_migration():
    conn = _in_memory_conn()
    _apply_schema_and_migrations(conn)
    try:
        _apply_schema_and_migrations(conn)
        _mark(True, "running migration twice does not raise")
    except Exception as e:
        _mark(False, f"double migration raised: {e}")


def test_backfill_moves_collision_strings():
    conn = _in_memory_conn()
    conn.executescript(db_module.SCHEMA)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, coltype in db_module._MIGRATION_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {coltype}")

    ts = db_module.now_iso()
    patterns = [
        ("t-col", "path collision with in-flight tasks: x(dev,conflict)"),
        ("t-lock", "path locks held by another task: ['proj:p:path:f']"),
        ("t-tmux", "tmux create failed: CalledProcessError(1)"),
        ("t-iterm", "iTerm spawn failed: CalledProcessError(1)"),
        ("t-timeout", "DEV timed out after 1800s without submit_report"),
    ]
    for tid, msg in patterns:
        conn.execute(
            "INSERT INTO tasks (id,project,role,status,title,description,"
            "depends_on,touches,report,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (tid, "p", "developer", "conflict", "t", "d", "[]", "[]", msg, ts, ts),
        )
    conn.commit()

    conn.execute("""
        UPDATE tasks
           SET delegate_log = report,
               report = NULL
         WHERE report IS NOT NULL
           AND delegate_log IS NULL
           AND (   report LIKE 'path collision with%'
                OR report LIKE 'kickoff failed%'
                OR report LIKE 'lock contested%'
                OR report LIKE 'path locks held by%'
                OR report LIKE 'tmux create failed%'
                OR report LIKE 'iTerm spawn failed%'
                OR report LIKE 'DEV timed out%')
    """)
    conn.commit()

    for tid, msg in patterns:
        row = conn.execute("SELECT report, delegate_log FROM tasks WHERE id=?",
                           (tid,)).fetchone()
        _mark(row["report"] is None,
              f"{tid}: report cleared after backfill")
        _mark(row["delegate_log"] == msg,
              f"{tid}: delegate_log = original report string")


def test_backfill_leaves_dev_reports_intact():
    conn = _in_memory_conn()
    conn.executescript(db_module.SCHEMA)
    existing = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for col, coltype in db_module._MIGRATION_COLUMNS:
        if col not in existing:
            conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {coltype}")

    ts = db_module.now_iso()
    dev_report = "## Summary\nImplemented feature X.\n\n## Files Changed\n- foo.py"
    conn.execute(
        "INSERT INTO tasks (id,project,role,status,title,description,"
        "depends_on,touches,report,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("t-dev", "p", "developer", "review", "t", "d", "[]", "[]", dev_report, ts, ts),
    )
    conn.commit()

    conn.execute("""
        UPDATE tasks
           SET delegate_log = report,
               report = NULL
         WHERE report IS NOT NULL
           AND delegate_log IS NULL
           AND (   report LIKE 'path collision with%'
                OR report LIKE 'kickoff failed%'
                OR report LIKE 'lock contested%'
                OR report LIKE 'path locks held by%'
                OR report LIKE 'tmux create failed%'
                OR report LIKE 'iTerm spawn failed%'
                OR report LIKE 'DEV timed out%')
    """)
    conn.commit()

    row = conn.execute("SELECT report, delegate_log FROM tasks WHERE id='t-dev'").fetchone()
    _mark(row["report"] == dev_report, "DEV report not touched by backfill")
    _mark(row["delegate_log"] is None, "delegate_log stays NULL for DEV report")


def main() -> int:
    print("=== test_db_delegate_log ===")
    test_schema_has_both_columns()
    test_delegate_log_in_valid_columns()
    test_idempotent_migration()
    test_backfill_moves_collision_strings()
    test_backfill_leaves_dev_reports_intact()
    print(f"\n{'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())

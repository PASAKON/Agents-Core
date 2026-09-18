#!/usr/bin/env python3
"""Copy the task registry from a SQLite tasks.db into the Postgres hub.

docs/design/tasks-db-hub.md §3.1/§3.3. Copies `tasks`, `c_level_sessions`,
`events`, `locks` by primary key -- `INSERT ... ON CONFLICT DO NOTHING`
(idempotent: running it again after nothing changed moves zero rows), or
`--upsert` to overwrite an existing row with the source's version instead.
Ids do not need to be globally unique across runs -- the Mac's ~910-task db
and Contabo's ~11-task db are migrated separately into the same target
(runbook §3.3), and neither's ids collide with the other's.

Prints per-table row counts on BOTH sides, BEFORE and AFTER. Dry-run by
default -- pass --apply to actually write; without it this only shows what
would move.

Before counting on either side, the target schema is (re)initialised via
the same code path as `lib.db.init()` (PG_SCHEMA + the forward-only column
migrations) -- idempotent DDL, safe to run in dry-run mode too, and the fix
for the measured failure where a bare/fresh target had no `tasks` table at
all: the old code's `_counts()` silently reported 0 for a missing table,
then `psycopg.errors.InFailedSqlTransaction` on the very next statement
because a failed statement leaves a psycopg connection aborted until
rollback() is called.

Usage:
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL"              # dry run
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --upsert
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --skip-bad-rows
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import db as db_mod  # noqa: E402
from lib import db_pg  # noqa: E402

# table -> primary-key column(s), in the order INSERT will list them.
TABLES: dict[str, tuple[str, ...]] = {
    "tasks": ("id",),
    "c_level_sessions": ("role", "session_id"),
    "events": ("id",),
    "locks": ("key",),
}

_MISSING = "missing"


class RowCopyError(RuntimeError):
    """A single row failed to copy and --skip-bad-rows was not passed."""

    def __init__(self, table: str, pk: tuple, error: Exception):
        self.table = table
        self.pk = pk
        self.error = error
        super().__init__(f"table={table} pk={pk} error={error}")


def _sqlite_conn(path: Path) -> sqlite3.Connection:
    # Always SQLite, regardless of ORG_DB_URL -- the --from file is the
    # migration's source, never the (possibly Postgres) target get_conn()
    # would pick.
    return db_mod.sqlite_connect(path, readonly=True)


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _counts(execute) -> dict[str, object]:
    """Row counts per table. A table that can't be counted (missing, or any
    other error) reports the string "missing" instead of a silent 0 -- a
    real 0-row table and an absent table must never look the same."""
    out: dict[str, object] = {}
    for table in TABLES:
        try:
            out[table] = execute(f"SELECT COUNT(*) AS c FROM {table}")[0]["c"]
        except Exception as exc:
            out[table] = _MISSING
            print(f"    note: {table} count unavailable: {exc}", file=sys.stderr)
    return out


def _sqlite_execute(conn: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    return conn.execute(sql).fetchall()


def _pg_execute(conn, sql: str) -> list:
    """Run `sql` on the Postgres connection. On failure, roll back before
    re-raising -- a failed statement leaves a psycopg (autocommit=False)
    connection aborted until rollback(), so without this every *later*
    statement on the same connection raises InFailedSqlTransaction even
    though it has nothing to do with the original error (the measured bug:
    `_counts()` reporting `tasks: 0` on a schema-less target, then the first
    real INSERT blowing up with a transaction-abort error instead of its
    own)."""
    try:
        return conn.execute(sql).fetchall()
    except Exception:
        conn.rollback()
        raise


def _print_counts(label: str, counts: dict[str, object]) -> None:
    print(f"  {label}:")
    for table, n in counts.items():
        print(f"    {table:20s} {n}")


def _reset_events_identity_sequence(pconn) -> None:
    """Advance events.id's identity sequence past the highest id just copied
    in verbatim (the source's ids). Without this, the sequence stays at its
    fresh-schema default and the first INSERT INTO events done through the
    normal lib.db API after cutover collides with a duplicate key (measured
    failure item 3). `false` for is_called means nextval() returns exactly
    this value next -- correct whether the table is empty (sets next id to
    1, matching a brand-new identity column) or not (sets next id to
    max(id)+1)."""
    pconn.execute(
        "SELECT setval(pg_get_serial_sequence('events','id'), "
        "COALESCE((SELECT MAX(id) FROM events), 0) + 1, false)"
    )
    pconn.commit()


def _copy_table(sconn: sqlite3.Connection, pconn, table: str,
                 pk: tuple[str, ...], upsert: bool, apply: bool,
                 skip_bad_rows: bool) -> tuple[int, list[tuple[tuple, str]]]:
    """Copy every row of `table` from SQLite into Postgres. Returns
    (rows actually inserted/updated, [(pk_values, error_str), ...] skipped).

    Default (skip_bad_rows=False): the first failing row rolls back this
    table's entire uncommitted batch and raises RowCopyError -- a table is
    copied all-or-nothing, matching the single commit() at the end (already
    "per-table commits" before this fix; unchanged here).

    --skip-bad-rows: each row runs inside its own SAVEPOINT so one bad row's
    ROLLBACK TO SAVEPOINT doesn't discard the good rows already inserted in
    this same table/transaction -- still exactly one commit() at the end.
    """
    cols = _sqlite_columns(sconn, table)
    rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows or not apply:
        return 0, []

    col_list = ", ".join(cols)
    placeholders = ", ".join("?" * len(cols))
    non_pk = [c for c in cols if c not in pk]
    if upsert and non_pk:
        conflict = (
            f"ON CONFLICT ({', '.join(pk)}) DO UPDATE SET "
            + ", ".join(f"{c} = EXCLUDED.{c}" for c in non_pk)
        )
    else:
        conflict = f"ON CONFLICT ({', '.join(pk)}) DO NOTHING"
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) {conflict}"

    moved = 0
    skipped: list[tuple[tuple, str]] = []
    for row in rows:
        values = tuple(row[c] for c in cols)
        pk_values = tuple(row[c] for c in pk)
        if skip_bad_rows:
            pconn.execute("SAVEPOINT row_sp")
        try:
            cur = pconn.execute(sql, values)
            moved += cur.rowcount or 0
        except Exception as exc:
            if skip_bad_rows:
                pconn.execute("ROLLBACK TO SAVEPOINT row_sp")
                skipped.append((pk_values, str(exc)))
                continue
            pconn.rollback()
            raise RowCopyError(table, pk_values, exc) from exc
        else:
            if skip_bad_rows:
                pconn.execute("RELEASE SAVEPOINT row_sp")
    pconn.commit()
    return moved, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="src", required=True, type=Path,
                     help="path to the source SQLite tasks.db")
    ap.add_argument("--to", dest="dst", required=True,
                     help="target ORG_DB_URL (postgresql://...)")
    ap.add_argument("--apply", action="store_true",
                     help="actually write (default is dry-run: prints "
                          "counts and what would move, writes nothing)")
    ap.add_argument("--upsert", action="store_true",
                     help="ON CONFLICT DO UPDATE instead of DO NOTHING -- "
                          "overwrite a target row with the source's version")
    ap.add_argument("--skip-bad-rows", action="store_true",
                     help="on a failing row, skip it (recording table+pk+"
                          "error) and continue instead of aborting the "
                          "whole table copy")
    args = ap.parse_args(argv)

    if not args.src.exists():
        print(f"source not found: {args.src}", file=sys.stderr)
        return 1
    dst_stripped = args.dst.strip()
    if not dst_stripped.startswith("postgresql://") and \
       not dst_stripped.startswith("postgres://"):
        print(f"--to does not look like a postgresql:// URL: {args.dst}",
              file=sys.stderr)
        return 1

    sconn = _sqlite_conn(args.src)
    try:
        pconn = db_pg.connect(args.dst, timeout=10)
    except db_pg.HubConnectError as exc:
        print(f"cannot reach target: {exc}", file=sys.stderr)
        sconn.close()
        return 1

    try:
        print(f"source: {args.src}")
        print(f"target: {db_pg._host_from_url(args.dst)}")
        print(f"mode:   {'APPLY' if args.apply else 'DRY-RUN (pass --apply to write)'}"
              f"{' + upsert' if args.upsert else ''}"
              f"{' + skip-bad-rows' if args.skip_bad_rows else ''}")
        print()

        # Idempotent DDL (CREATE TABLE IF NOT EXISTS / guarded ALTER TABLE
        # ADD COLUMN) -- always run before counting, dry-run included, so a
        # fresh target reports real per-table counts instead of a
        # transaction-aborting error on the very first statement. This
        # never touches row data, so it does not compromise dry-run's
        # "writes nothing" contract for the migration itself.
        db_mod.init_schema(pconn, is_pg=True)
        pconn.commit()

        before_src = _counts(lambda sql: _sqlite_execute(sconn, sql))
        before_dst = _counts(lambda sql: _pg_execute(pconn, sql))
        print("before:")
        _print_counts("source (sqlite)", before_src)
        _print_counts("target (postgres)", before_dst)
        print()

        moved: dict[str, int] = {}
        all_skipped: list[tuple[str, tuple, str]] = []
        try:
            for table, pk in TABLES.items():
                n, skipped = _copy_table(sconn, pconn, table, pk,
                                          args.upsert, args.apply,
                                          args.skip_bad_rows)
                moved[table] = n
                all_skipped.extend((table, pk_values, err) for pk_values, err in skipped)
        except RowCopyError as exc:
            print(f"migrate failed: table={exc.table} pk={exc.pk} error={exc.error}",
                  file=sys.stderr)
            return 1

        if args.apply:
            _reset_events_identity_sequence(pconn)

        after_dst = _counts(lambda sql: _pg_execute(pconn, sql)) if args.apply else before_dst
        print("after:" if args.apply else "would move (dry-run, nothing written):")
        for table in TABLES:
            print(f"    {table:20s} +{moved[table]:<6d} target now: {after_dst[table]}")
        print()

        if all_skipped:
            print(f"skipped {len(all_skipped)} row(s) (--skip-bad-rows):")
            for table, pk_values, err in all_skipped:
                print(f"    {table:20s} pk={pk_values} error={err}")
            print()

        if not args.apply:
            print("dry-run only -- re-run with --apply to write.")
        return 0
    finally:
        sconn.close()
        pconn.close()


if __name__ == "__main__":
    raise SystemExit(main())

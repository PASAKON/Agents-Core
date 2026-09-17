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

Usage:
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL"              # dry run
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --upsert
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


def _sqlite_conn(path: Path) -> sqlite3.Connection:
    # Always SQLite, regardless of ORG_DB_URL -- the --from file is the
    # migration's source, never the (possibly Postgres) target get_conn()
    # would pick.
    return db_mod.sqlite_connect(path, readonly=True)


def _sqlite_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _counts(execute) -> dict[str, int]:
    out = {}
    for table in TABLES:
        try:
            out[table] = execute(f"SELECT COUNT(*) AS c FROM {table}")[0]["c"]
        except Exception:
            out[table] = 0  # table doesn't exist yet on the target
    return out


def _sqlite_execute(conn: sqlite3.Connection, sql: str) -> list[sqlite3.Row]:
    return conn.execute(sql).fetchall()


def _pg_execute(conn, sql: str) -> list:
    return conn.execute(sql).fetchall()


def _print_counts(label: str, counts: dict[str, int]) -> None:
    print(f"  {label}:")
    for table, n in counts.items():
        print(f"    {table:20s} {n}")


def _copy_table(sconn: sqlite3.Connection, pconn, table: str,
                 pk: tuple[str, ...], upsert: bool, apply: bool) -> int:
    """Copy every row of `table` from SQLite into Postgres. Returns the
    number of rows the INSERT actually affected (0 in dry-run)."""
    cols = _sqlite_columns(sconn, table)
    rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows or not apply:
        return 0

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
    for row in rows:
        values = tuple(row[c] for c in cols)
        cur = pconn.execute(sql, values)
        moved += cur.rowcount or 0
    pconn.commit()
    return moved


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
              f"{' + upsert' if args.upsert else ''}")
        print()

        before_src = _counts(lambda sql: _sqlite_execute(sconn, sql))
        before_dst = _counts(lambda sql: _pg_execute(pconn, sql))
        print("before:")
        _print_counts("source (sqlite)", before_src)
        _print_counts("target (postgres)", before_dst)
        print()

        moved: dict[str, int] = {}
        for table, pk in TABLES.items():
            moved[table] = _copy_table(sconn, pconn, table, pk,
                                        args.upsert, args.apply)

        after_dst = _counts(lambda sql: _pg_execute(pconn, sql)) if args.apply else before_dst
        print("after:" if args.apply else "would move (dry-run, nothing written):")
        for table in TABLES:
            print(f"    {table:20s} +{moved[table]:<6d} target now: {after_dst[table]}")
        print()
        if not args.apply:
            print("dry-run only -- re-run with --apply to write.")
        return 0
    finally:
        sconn.close()
        pconn.close()


if __name__ == "__main__":
    raise SystemExit(main())

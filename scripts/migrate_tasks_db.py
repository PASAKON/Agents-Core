#!/usr/bin/env python3
"""Copy the task registry from a SQLite tasks.db into the Postgres hub.

docs/design/tasks-db-hub.md §3.1/§3.3, docs/design/org-mesh.md (Org Mesh
W1.2). Copies `tasks`, `c_level_sessions`, `events` by primary key --
`INSERT ... ON CONFLICT DO NOTHING` (idempotent: running it again after
nothing changed moves zero rows), or `--upsert` / `--on-collision=keep-
source` to overwrite an existing row with the source's version instead.
`locks` is never migrated -- those are live path locks, not history.

TWO ledgers (the Mac's ~1100-task db and Contabo's ~11-task db) migrate into
the SAME target, one invocation per ledger:
  - `--default-host <name>` (required with `--apply`, validated against
    `lib.config.hosts()`) backfills a NULL `tasks.host`, `tasks.
    dispatcher_host` or `c_level_sessions.host` with that host's name as the
    row is copied. A non-NULL value is never overwritten.
  - `--append-events` is for the SECOND (and any later) ledger's `events`:
    it drops the source `id` column so Postgres assigns a fresh one --
    otherwise the second ledger's ids could collide with the first's -- and
    dedupes against the target by (task_id, ts, kind, payload) instead of
    by id, so a rerun inserts 0 rows.
  - A collision report (task ids / (role, session_id) pairs present in both
    source and target with differing data, ignoring the columns
    --default-host backfills) is always printed, dry run included. `--apply`
    refuses while collisions exist unless `--on-collision=skip|keep-target
    |keep-source` says how to resolve them.

Prints per-table row counts on BOTH sides, BEFORE and AFTER, plus (dry run)
how many rows would be inserted and how many of those would be backfilled.
Dry-run by default -- pass --apply to actually write; without it this only
shows what would move.

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
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host mac
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host contabo --append-events
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host mac --on-collision=keep-target
    python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host mac --skip-bad-rows
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config  # noqa: E402
from lib import db as db_mod  # noqa: E402
from lib import db_pg  # noqa: E402

# table -> primary-key column(s), in the order INSERT will list them.
# `locks` is deliberately absent (Org Mesh W1.2): those rows are live path
# locks, not history, and copying them across two ledgers would just
# reintroduce stale/duplicate lock rows. scripts/hub/verify_migration_counts
# .py keeps its own hand-synced copy of this list (its own docstring
# explains why it isn't imported from here).
TABLES: dict[str, tuple[str, ...]] = {
    "tasks": ("id",),
    "c_level_sessions": ("role", "session_id"),
    "events": ("id",),
}

# Tables whose collision report is meaningful. `events` is excluded: with
# --append-events it never carries its source id across, and without it the
# two ledgers' ids are assumed disjoint by convention (module docstring) --
# either way "same id, different content" isn't a question that makes sense
# for it the way it does for tasks/c_level_sessions.
COLLISION_TABLES: tuple[str, ...] = ("tasks", "c_level_sessions")

# Columns --default-host fills in when NULL, per table (task brief item 1).
# Also used as `ignore_cols` for collision detection -- a row that differs
# from the target ONLY because this run (or an earlier one) backfilled a
# host column must not be reported as a collision, or a plain rerun after a
# backfill would refuse itself forever.
BACKFILL_COLUMNS: dict[str, tuple[str, ...]] = {
    "tasks": ("host", "dispatcher_host"),
    "c_level_sessions": ("host",),
}

# Identity of an `events` row for --append-events dedupe (task brief item
# 2: "(task_id, ts, kind, payload)"). `id` is deliberately excluded --
# that's the whole point: two ledgers' ids are never expected to line up,
# but the same underlying event must never be inserted twice. `actor` is
# excluded too -- it is not part of the brief's dedupe key.
EVENT_DEDUPE_COLUMNS: tuple[str, ...] = ("task_id", "ts", "kind", "payload")

ON_COLLISION_CHOICES = ("skip", "keep-target", "keep-source")

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


def _sqlite_columns(conn, table: str) -> list[str]:
    """Real column names of `table` on `conn` -- works against either a
    SQLite connection (PRAGMA table_info, native) or a lib.db_pg.Connection
    (PRAGMA table_info is translated into an information_schema query that
    returns the same `name` column, see lib/db_pg.py's `_translate`)."""
    return [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def backfill_row(row: dict, backfill_cols: tuple[str, ...],
                  default_host: str | None) -> tuple[dict, bool]:
    """Return (row', changed) where row' has every NULL value among
    `backfill_cols` replaced by `default_host`. Never touches a non-NULL
    value (task brief item 1: "Non-NULL values are never overwritten").
    Pure -- does not mutate `row` -- so it's directly unit-testable."""
    if not default_host or not backfill_cols:
        return row, False
    out = dict(row)
    changed = False
    for col in backfill_cols:
        if col in out and out[col] is None:
            out[col] = default_host
            changed = True
    return out, changed


def event_dedupe_key(row: dict) -> tuple:
    """Identity of an events row for --append-events -- see
    EVENT_DEDUPE_COLUMNS."""
    return tuple(row.get(c) for c in EVENT_DEDUPE_COLUMNS)


def new_events(rows: list[dict], seen_keys: set[tuple]) -> list[dict]:
    """Rows (as dicts) not already represented in `seen_keys` by
    event_dedupe_key() -- also deduping a row against an earlier row in
    `rows` itself, so a source ledger with an internal duplicate doesn't
    insert it twice either. Pure function, no database."""
    seen = set(seen_keys)
    out = []
    for row in rows:
        key = event_dedupe_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def find_row_collisions(source_rows: list[dict], target_rows: list[dict],
                         pk: tuple[str, ...],
                         ignore_cols: frozenset[str] = frozenset()) -> list[tuple]:
    """PK tuples present in both `source_rows` and `target_rows` whose
    columns differ, other than `ignore_cols` and the pk itself. A row that
    is identical on both sides (or differs only in an ignored column) is
    NOT a collision -- ON CONFLICT DO NOTHING already leaves it alone
    safely, and flagging it would make a plain rerun refuse itself forever.
    Pure function, no database."""
    target_by_pk = {tuple(r[c] for c in pk): r for r in target_rows}
    collisions: list[tuple] = []
    for row in source_rows:
        key = tuple(row[c] for c in pk)
        tgt = target_by_pk.get(key)
        if tgt is None:
            continue
        for col, val in row.items():
            if col in ignore_cols or col in pk:
                continue
            if col in tgt and tgt[col] != val:
                collisions.append(key)
                break
    return collisions


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


def _rows_as_dicts(execute, table: str) -> list[dict]:
    """All rows of `table` as plain dicts, or [] if the table can't be read
    (e.g. an older source ledger missing a newer table) -- mirrors
    `_counts`'s "missing is not the same as empty" stance for counting, but
    here an unreadable table simply contributes no rows to compare."""
    try:
        return [dict(r) for r in execute(f"SELECT * FROM {table}")]
    except Exception:
        return []


def _print_counts(label: str, counts: dict[str, object]) -> None:
    print(f"  {label}:")
    for table, n in counts.items():
        print(f"    {table:20s} {n}")


def _find_all_collisions(sconn: sqlite3.Connection, pconn) -> dict[str, list[tuple]]:
    out: dict[str, list[tuple]] = {}
    for table in COLLISION_TABLES:
        pk = TABLES[table]
        ignore_cols = frozenset(BACKFILL_COLUMNS.get(table, ()))
        src_rows = _rows_as_dicts(lambda sql: _sqlite_execute(sconn, sql), table)
        tgt_rows = _rows_as_dicts(lambda sql: _pg_execute(pconn, sql), table)
        out[table] = find_row_collisions(src_rows, tgt_rows, pk, ignore_cols=ignore_cols)
    return out


def _print_collisions(collisions: dict[str, list[tuple]]) -> None:
    total = sum(len(v) for v in collisions.values())
    print(f"collisions (same key, differing data): {total}")
    if not total:
        return
    for table, keys in collisions.items():
        for key in keys:
            print(f"    {table:20s} pk={key}")


def _reset_events_identity_sequence(pconn) -> None:
    """Advance events.id's identity sequence past the highest id in the
    table (whether it got there via a verbatim copied id or an
    --append-events auto-assigned one). Without this, a fresh schema's
    sequence stays at its default and the first INSERT INTO events done
    through the normal lib.db API after cutover collides with a duplicate
    key (measured failure item 3). `false` for is_called means nextval()
    returns exactly this value next -- correct whether the table is empty
    (sets next id to 1) or not (sets next id to max(id)+1)."""
    pconn.execute(
        "SELECT setval(pg_get_serial_sequence('events','id'), "
        "COALESCE((SELECT MAX(id) FROM events), 0) + 1, false)"
    )
    pconn.commit()


def _copy_table(sconn: sqlite3.Connection, pconn, table: str,
                 pk: tuple[str, ...], *, upsert: bool, apply: bool,
                 skip_bad_rows: bool, default_host: str | None) -> dict:
    """Copy every row of `table` from SQLite into Postgres by primary key.

    Always computes (dry run included): how many source rows are new (pk
    not yet in target) and, of those, how many get a NULL backfill column
    (BACKFILL_COLUMNS[table]) filled from `default_host`. Only actually
    writes when apply=True.

    Returns {"to_insert": int, "backfilled": int, "moved": int,
    "skipped": [(pk_values, error_str), ...]}.

    Default (skip_bad_rows=False): the first failing row rolls back this
    table's entire uncommitted batch and raises RowCopyError -- a table is
    copied all-or-nothing, matching the single commit() at the end.

    --skip-bad-rows: each row runs inside its own SAVEPOINT so one bad row's
    ROLLBACK TO SAVEPOINT doesn't discard the good rows already inserted in
    this same table/transaction -- still exactly one commit() at the end.
    """
    cols = _sqlite_columns(sconn, table)
    rows = [dict(r) for r in sconn.execute(f"SELECT * FROM {table}").fetchall()]
    result = {"to_insert": 0, "backfilled": 0, "moved": 0, "skipped": []}
    if not rows:
        return result

    backfill_cols = BACKFILL_COLUMNS.get(table, ())
    existing_pks = {tuple(r[c] for c in pk)
                     for r in pconn.execute(f"SELECT {', '.join(pk)} FROM {table}").fetchall()}

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

    to_insert = backfilled = moved = 0
    skipped: list[tuple[tuple, str]] = []
    for row in rows:
        row, changed = backfill_row(row, backfill_cols, default_host)
        pk_values = tuple(row[c] for c in pk)
        if pk_values not in existing_pks:
            to_insert += 1
            if changed:
                backfilled += 1
        if not apply:
            continue
        values = tuple(row[c] for c in cols)
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
    if apply:
        pconn.commit()
    result.update(to_insert=to_insert, backfilled=backfilled, moved=moved, skipped=skipped)
    return result


def _copy_events_appending(sconn: sqlite3.Connection, pconn, *, apply: bool,
                            skip_bad_rows: bool) -> dict:
    """--append-events copy path for the `events` table (module docstring
    item 2): drop `id` so Postgres assigns a fresh one per source ledger,
    and dedupe against the target by event_dedupe_key() instead of by
    primary key. Same return shape as _copy_table (backfilled is always 0
    -- `events` has no BACKFILL_COLUMNS entry)."""
    cols = _sqlite_columns(sconn, "events")
    insert_cols = [c for c in cols if c != "id"]
    rows = [dict(r) for r in sconn.execute("SELECT * FROM events").fetchall()]
    result = {"to_insert": 0, "backfilled": 0, "moved": 0, "skipped": []}
    if not rows:
        return result

    existing = pconn.execute(
        f"SELECT {', '.join(EVENT_DEDUPE_COLUMNS)} FROM events").fetchall()
    seen_keys = {event_dedupe_key(dict(r)) for r in existing}
    fresh = new_events(rows, seen_keys)
    result["to_insert"] = len(fresh)
    if not apply or not fresh:
        return result

    col_list = ", ".join(insert_cols)
    placeholders = ", ".join("?" * len(insert_cols))
    sql = f"INSERT INTO events ({col_list}) VALUES ({placeholders})"
    moved = 0
    skipped: list[tuple[tuple, str]] = []
    for row in fresh:
        pk_values = event_dedupe_key(row)
        if skip_bad_rows:
            pconn.execute("SAVEPOINT row_sp")
        try:
            pconn.execute(sql, tuple(row[c] for c in insert_cols))
            moved += 1
        except Exception as exc:
            if skip_bad_rows:
                pconn.execute("ROLLBACK TO SAVEPOINT row_sp")
                skipped.append((pk_values, str(exc)))
                continue
            pconn.rollback()
            raise RowCopyError("events", pk_values, exc) from exc
        else:
            if skip_bad_rows:
                pconn.execute("RELEASE SAVEPOINT row_sp")
    pconn.commit()
    result.update(moved=moved, skipped=skipped)
    return result


def resolve_collision_mode(on_collision: str | None, upsert: bool) -> tuple[str | None, bool]:
    """Resolve the --on-collision / --upsert combination into
    (effective_on_collision, effective_upsert). `--upsert` alone means the
    same thing `--on-collision=keep-source` does (overwrite every row with
    the source's version) -- kept for backward compatibility with callers
    written before `--on-collision` existed. Pulled out of main() so it can
    be unit-tested without argparse or a database connection."""
    effective = on_collision or ("keep-source" if upsert else None)
    return effective, effective == "keep-source"


def should_refuse_apply(total_collisions: int, apply: bool, on_collision: str | None) -> bool:
    """True when --apply must be refused: real collisions exist, this run
    would actually write, and nothing said how to resolve them."""
    return bool(total_collisions) and apply and not on_collision


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="src", required=True, type=Path,
                     help="path to the source SQLite tasks.db")
    ap.add_argument("--to", dest="dst", required=True,
                     help="target ORG_DB_URL (postgresql://...)")
    ap.add_argument("--apply", action="store_true",
                     help="actually write (default is dry-run: prints "
                          "counts and what would move, writes nothing)")
    ap.add_argument("--default-host", dest="default_host", default=None,
                     help="required with --apply -- backfills a NULL "
                          "tasks.host/dispatcher_host or c_level_sessions."
                          "host with this host name (config/hosts.yaml key)")
    ap.add_argument("--append-events", action="store_true",
                     help="for a SECOND (or later) ledger: copy events "
                          "without their id (Postgres assigns a fresh one) "
                          "and dedupe by content instead of by id")
    ap.add_argument("--on-collision", choices=ON_COLLISION_CHOICES, default=None,
                     help="how to resolve a task/c_level_sessions row whose "
                          "key exists in both source and target with "
                          "differing data. Default: refuse --apply while "
                          "any such collision exists.")
    ap.add_argument("--upsert", action="store_true",
                     help="ON CONFLICT DO UPDATE instead of DO NOTHING -- "
                          "overwrite every target row with the source's "
                          "version. Equivalent to --on-collision=keep-source "
                          "for the collision gate; mutually exclusive with "
                          "--on-collision.")
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
    if args.apply and not args.default_host:
        print("--default-host is required with --apply", file=sys.stderr)
        return 1
    if args.default_host is not None:
        known_hosts = config.hosts()
        if args.default_host not in known_hosts:
            print(f"--default-host {args.default_host!r} is not a known host. "
                  f"Known: {sorted(known_hosts)}", file=sys.stderr)
            return 1
    if args.upsert and args.on_collision:
        print("--upsert and --on-collision are mutually exclusive "
              "(--upsert already means keep-source)", file=sys.stderr)
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
              f"{' + default-host=' + args.default_host if args.default_host else ''}"
              f"{' + append-events' if args.append_events else ''}"
              f"{' + upsert' if args.upsert else ''}"
              f"{' + on-collision=' + args.on_collision if args.on_collision else ''}"
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

        collisions = _find_all_collisions(sconn, pconn)
        _print_collisions(collisions)
        print()

        total_collisions = sum(len(v) for v in collisions.values())
        on_collision, effective_upsert = resolve_collision_mode(args.on_collision, args.upsert)
        if should_refuse_apply(total_collisions, args.apply, on_collision):
            print(f"refusing --apply: {total_collisions} colliding row(s) -- "
                  f"pass --on-collision=skip|keep-target|keep-source to proceed",
                  file=sys.stderr)
            return 1

        moved: dict[str, int] = {}
        backfilled: dict[str, int] = {}
        to_insert: dict[str, int] = {}
        all_skipped: list[tuple[str, tuple, str]] = []
        try:
            for table, pk in TABLES.items():
                if table == "events" and args.append_events:
                    stats = _copy_events_appending(
                        sconn, pconn, apply=args.apply,
                        skip_bad_rows=args.skip_bad_rows)
                else:
                    stats = _copy_table(
                        sconn, pconn, table, pk, upsert=effective_upsert,
                        apply=args.apply, skip_bad_rows=args.skip_bad_rows,
                        default_host=args.default_host)
                moved[table] = stats["moved"]
                backfilled[table] = stats["backfilled"]
                to_insert[table] = stats["to_insert"]
                all_skipped.extend(
                    (table, pk_values, err) for pk_values, err in stats["skipped"])
        except RowCopyError as exc:
            print(f"migrate failed: table={exc.table} pk={exc.pk} error={exc.error}",
                  file=sys.stderr)
            return 1

        if args.apply:
            _reset_events_identity_sequence(pconn)

        after_dst = _counts(lambda sql: _pg_execute(pconn, sql)) if args.apply else before_dst
        print("after:" if args.apply else "would move (dry-run, nothing written):")
        for table in TABLES:
            if args.apply:
                print(f"    {table:20s} +{moved[table]:<6d} "
                      f"backfilled={backfilled[table]:<4d} target now: {after_dst[table]}")
            else:
                print(f"    {table:20s} to_insert={to_insert[table]:<6d} "
                      f"backfilled={backfilled[table]:<4d} target now: {after_dst[table]}")
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

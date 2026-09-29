#!/usr/bin/env python3
"""Compare the SQLite source and the Postgres target of a
scripts/migrate_tasks_db.py --apply run (Org Mesh W1.1/W1.2,
docs/design/tasks-db-hub.md §3.3).

Shared by scripts/hub/cutover-mac.sh and scripts/hub/contabo-cutover-
remote.sh so the "verify nothing was lost, refuse otherwise" check exists
exactly once -- it used to be a copy-pasted heredoc in cutover-mac.sh only;
contabo-cutover.sh had none at all, which was the gap this closes.

Two modes (`--mode`, default `equal`):
  - `equal` (the FIRST ledger, e.g. the Mac): per-table row counts must
    match byte-for-byte between source and target -- the target was empty
    (or this table was) before this ledger's import, so sqlite count ==
    postgres count is the right check.
  - `subset` (a LATER ledger, e.g. Contabo importing into a hub that
    already holds the Mac's rows): the target legitimately holds MORE rows
    than this source (postgres = mac + contabo), so counts can never be
    equal. Instead this checks that every sqlite `tasks.id`, every
    `c_level_sessions` primary key, and every `events` row's dedupe key
    (scripts/migrate_tasks_db.event_dedupe_key -- reused, not
    reimplemented, so the identity used here always matches the identity
    --append-events actually deduped by) is present somewhere in postgres.

Exits 1 and prints details on any mismatch/missing row. The caller must run
this BEFORE archiving state/tasks.db: on a failure the SQLite source is
still sitting untouched at its original path (this script never moves or
deletes anything), so "leave the SQLite archive in place" falls out of the
call order in the caller, not from anything done here.

TABLES matches scripts/migrate_tasks_db.py's TABLES dict -- kept in sync by
hand (that script owns the copy, this one owns the check; not imported from
it, since migrate_tasks_db.py's TABLES also carries the primary-key columns
this script had no use for before `--mode subset` -- which instead imports
just the one function/constant it needs, event_dedupe_key, rather than
duplicating EVENT_DEDUPE_COLUMNS as a second hand-copied list). `locks` is
deliberately absent (Org Mesh W1.2): migrate_tasks_db.py never copies it --
those are live path locks, not history -- so comparing it here would always
"mismatch"/"miss everything" against a target that legitimately never
received it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db as db_mod  # noqa: E402
from lib import db_pg  # noqa: E402
from scripts import migrate_tasks_db as migrate_mod  # noqa: E402

TABLES: tuple[str, ...] = ("tasks", "c_level_sessions", "events")

MODE_CHOICES: tuple[str, ...] = ("equal", "subset")

# Identity of a row for `--mode subset`, per table -- the same key a row
# would need to already exist in the target under for it to count as "not
# lost". tasks/c_level_sessions use their plain primary key; events reuses
# migrate_tasks_db's own dedupe key (see module docstring) since that is
# the identity --append-events actually deduped new rows by.
SUBSET_IDENTITY: dict[str, Callable[[dict], tuple]] = {
    "tasks": lambda row: (row["id"],),
    "c_level_sessions": lambda row: (row["role"], row["session_id"]),
    "events": migrate_mod.event_dedupe_key,
}


def find_mismatches(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Table names whose count differs between the two snapshots."""
    return [t for t in TABLES if before.get(t) != after.get(t)]


def find_missing(source_rows: list[dict], target_rows: list[dict],
                  identity: Callable[[dict], tuple]) -> list[tuple]:
    """Identities present in `source_rows` (by `identity`) that are absent
    from `target_rows` -- the "no data lost" check for `--mode subset`.
    Pure function, no database; a target with extra rows (or duplicates)
    never counts against the source."""
    target_keys = {identity(row) for row in target_rows}
    return [identity(row) for row in source_rows if identity(row) not in target_keys]


def sqlite_counts(sqlite_path) -> dict[str, int]:
    conn = db_mod.sqlite_connect(sqlite_path, readonly=True)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                for t in TABLES}
    finally:
        conn.close()


def pg_counts(pg_url: str) -> dict[str, int]:
    conn = db_pg.connect(pg_url, timeout=10)
    try:
        return {t: conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]
                for t in TABLES}
    finally:
        conn.close()


def sqlite_rows(sqlite_path, table: str) -> list[dict]:
    """Every row of `table` in the SQLite source, as plain dicts (`--mode
    subset`'s source side)."""
    conn = db_mod.sqlite_connect(sqlite_path, readonly=True)
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    finally:
        conn.close()


def pg_rows(pg_url: str, table: str) -> list[dict]:
    """Every row of `table` in the Postgres target, as plain dicts (`--mode
    subset`'s target side)."""
    conn = db_pg.connect(pg_url, timeout=10)
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
    finally:
        conn.close()


def _run_equal(sqlite_path, pg_url: str) -> int:
    before = sqlite_counts(sqlite_path)
    after = pg_counts(pg_url)
    for table in TABLES:
        print(f"  {table:20s} sqlite={before.get(table)} postgres={after.get(table)}")

    mismatched = find_mismatches(before, after)
    if mismatched:
        print(f"REFUSING: count mismatch after migrate: {mismatched}", file=sys.stderr)
        return 1
    return 0


def _run_subset(sqlite_path, pg_url: str) -> int:
    missing_total = 0
    missing_tables: list[str] = []
    for table in TABLES:
        src_rows = sqlite_rows(sqlite_path, table)
        tgt_rows = pg_rows(pg_url, table)
        missing = find_missing(src_rows, tgt_rows, SUBSET_IDENTITY[table])
        print(f"  {table:20s} sqlite={len(src_rows)} missing_from_postgres={len(missing)}")
        if missing:
            missing_total += len(missing)
            missing_tables.append(table)

    if missing_total:
        print(f"REFUSING: {missing_total} row(s) present in sqlite but missing "
              f"from postgres: {missing_tables}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", required=True, help="path to the SQLite source db")
    ap.add_argument("--pg", required=True, help="Postgres target ORG_DB_URL")
    ap.add_argument("--mode", choices=MODE_CHOICES, default="equal",
                     help="'equal' (default, first ledger): sqlite count == "
                          "postgres count, every table. 'subset' (later "
                          "ledger): every sqlite row must be present in "
                          "postgres, which may legitimately hold more.")
    args = ap.parse_args(argv)

    if args.mode == "subset":
        return _run_subset(args.sqlite, args.pg)
    return _run_equal(args.sqlite, args.pg)


if __name__ == "__main__":
    raise SystemExit(main())

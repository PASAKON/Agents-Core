#!/usr/bin/env python3
"""Compare per-table row counts between the SQLite source and the Postgres
target of a scripts/migrate_tasks_db.py --apply run (Org Mesh W1.1,
docs/design/tasks-db-hub.md §3.3).

Shared by scripts/hub/cutover-mac.sh and scripts/hub/contabo-cutover-
remote.sh so the "record counts before/after, refuse on mismatch" check
exists exactly once -- it used to be a copy-pasted heredoc in cutover-
mac.sh only; contabo-cutover.sh had none at all, which was the gap this
closes.

Exits 1 and prints both count sets on any mismatch. The caller must run
this BEFORE archiving state/tasks.db: on a mismatch the SQLite source is
still sitting untouched at its original path (this script never moves or
deletes anything), so "leave the SQLite archive in place" falls out of the
call order in the caller, not from anything done here.

TABLES matches scripts/migrate_tasks_db.py's TABLES dict -- kept in sync by
hand (that script owns the copy, this one owns the check; not imported from
it, since migrate_tasks_db.py's TABLES also carries the primary-key columns
this script has no use for). `locks` is deliberately absent (Org Mesh
W1.2): migrate_tasks_db.py never copies it -- those are live path locks,
not history -- so comparing its count here would always "mismatch" against
a target that legitimately never received it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db as db_mod  # noqa: E402
from lib import db_pg  # noqa: E402

TABLES: tuple[str, ...] = ("tasks", "c_level_sessions", "events")


def find_mismatches(before: dict[str, int], after: dict[str, int]) -> list[str]:
    """Table names whose count differs between the two snapshots."""
    return [t for t in TABLES if before.get(t) != after.get(t)]


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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", required=True, help="path to the SQLite source db")
    ap.add_argument("--pg", required=True, help="Postgres target ORG_DB_URL")
    args = ap.parse_args(argv)

    before = sqlite_counts(args.sqlite)
    after = pg_counts(args.pg)
    for table in TABLES:
        print(f"  {table:20s} sqlite={before.get(table)} postgres={after.get(table)}")

    mismatched = find_mismatches(before, after)
    if mismatched:
        print(f"REFUSING: count mismatch after migrate: {mismatched}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

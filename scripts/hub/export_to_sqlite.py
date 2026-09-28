#!/usr/bin/env python3
"""Export the org ledger hub (Postgres, ORG_DB_URL) to a local read-only
SQLite snapshot at state/tasks.snapshot.db -- Org Mesh W1.7 (docs/design/
org-mesh.md, docs/design/tasks-db-hub.md §5 "SQLite fallback is for tests
only" risk, now closed for real).

lib.db.get_conn() reads this file when ORG_DB_URL is set but the hub can't
be reached (lib.db.HubUnavailable); this script is the writer side that
keeps it fresh. Run on a schedule -- see the sibling scheduler files:
  scripts/com.mooniex.org-snapshot.plist        (launchd, Mac)
  deploy/systemd/org-snapshot.{service,timer}   (systemd, Contabo/Linux)
Installing those is a later live step (not this task's DoD); this script
alone is what `python3 scripts/hub/export_to_sqlite.py` runs.

Exports the `tasks` and `c_level_sessions` tables in full, plus only the
last EVENTS_WINDOW_DAYS of `events` (the ledger's biggest table by far, and
the fallback only needs to answer "what happened recently").

Exit codes:
  0 -- wrote a fresh snapshot, OR ORG_DB_URL is unset ("hub not configured":
       every host without a hub keeps working exactly as before this file
       existed -- nothing to export).
  1 -- ORG_DB_URL is set but the hub could not be reached or read. The
       previous snapshot (if any) is left untouched -- see export()'s
       atomic-write note below.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib import db as db_lib  # noqa: E402
from lib import db_pg  # noqa: E402

EVENTS_WINDOW_DAYS = 30


def _events_cutoff() -> str:
    return (datetime.now(timezone.utc) - timedelta(days=EVENTS_WINDOW_DAYS)).isoformat(
        timespec="seconds"
    )


def _copy_table(src_conn, dst_conn: sqlite3.Connection, table: str,
                *, where: str = "", params: tuple = ()) -> int:
    """Copy every column of every matching row from `src_conn` (the hub) into
    `dst_conn` (the fresh snapshot file), preserving primary keys as-is --
    `events.id` in particular, since lib.db.recent_events() orders by it."""
    rows = src_conn.execute(f"SELECT * FROM {table}{where}", params).fetchall()
    if not rows:
        return 0
    cols = list(rows[0].keys())
    col_list = ",".join(cols)
    placeholders = ",".join("?" * len(cols))
    dst_conn.executemany(
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
        [tuple(r[c] for c in cols) for r in rows],
    )
    return len(rows)


def export(dst_path: Path) -> None:
    """Write a fresh snapshot at `dst_path`. Raises on any failure -- the
    caller (main()) is what turns that into an exit code and a message; this
    function never leaves a partial file at `dst_path` itself (it builds a
    temp file first, `os.replace`s only on full success -- see below).
    """
    url = db_lib.pg_url()
    if not url:
        print("hub not configured")
        return

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: build the whole snapshot in a temp file beside the real
    # one, then a single os.replace() swaps it in. A reader (lib.db's
    # fallback, or another concurrent export) either sees the old complete
    # file or the new complete file, never a half-written one -- and if
    # anything below raises, the temp file is discarded and dst_path is
    # never touched, so a stale-but-complete snapshot survives a failed
    # export exactly as a fresh one would have replaced it.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".tasks.snapshot.", suffix=".tmp", dir=str(dst_path.parent)
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    tmp_path.unlink()  # sqlite3.connect must create this file fresh

    try:
        # Direct db_pg.connect(), never lib.db.get_conn() -- get_conn()'s own
        # ORG_DB_URL branch is what this task teaches to fall back to
        # SNAPSHOT_PATH on a connect failure. Going through it here would let
        # a down hub "succeed" by quietly reading the very snapshot this
        # script is supposed to refresh, instead of exiting non-zero as the
        # task brief requires.
        src = db_pg.connect(url, timeout=10)
        try:
            dst = db_lib.sqlite_connect(tmp_path)
            try:
                # Reuses lib.db's own SQLite schema/init -- not a copy of the
                # DDL (task brief) -- so the snapshot's tasks/c_level_sessions/
                # events tables are always exactly what a fresh SQLite
                # backend would have, migration columns included.
                db_lib.init_schema(dst, is_pg=False)
                db_lib.init_snapshot_meta(dst)
                n_tasks = _copy_table(src, dst, "tasks")
                n_sessions = _copy_table(src, dst, "c_level_sessions")
                n_events = _copy_table(
                    src, dst, "events",
                    where=" WHERE ts >= ?", params=(_events_cutoff(),),
                )
                db_lib.write_snapshot_meta(dst, db_lib.now_iso())
                dst.commit()
            finally:
                dst.close()
        finally:
            src.close()
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    os.replace(tmp_path, dst_path)
    print(
        f"[export_to_sqlite] wrote {dst_path} "
        f"(tasks={n_tasks} c_level_sessions={n_sessions} "
        f"events={n_events}, last {EVENTS_WINDOW_DAYS}d)"
    )


def main() -> int:
    try:
        export(db_lib.SNAPSHOT_PATH)
    except Exception as exc:  # noqa: BLE001 -- hub unreachable/unreadable
        print(f"[export_to_sqlite] hub unreachable or read failed: {exc}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

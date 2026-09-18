#!/usr/bin/env python3
"""One-shot backfill for missing state/locks/<role>-<id>.uuid files.

task-a98788d7. `c_level_sessions.resume_uuid` is copied out of a session's
`.uuid` file at close time (tools/session_status.record_close) — but nothing
stops the file itself from later being deleted (measured 2026-09-18: 41 of 42
closed cto sessions with a DB resume_uuid had no `.uuid` file left on disk; a
disk-cleanup sweep is the presumed cause, since `.uuid` is documented as
"removed only by hand" in tools/session_name.py but evidently was anyway).

`scripts/spawn-cto.sh`/`spawn-cxo.sh` --resume now fall back to the DB column
when the file is missing, so a missing file no longer breaks resuming. This
script closes the *existing* gap on disk too, purely additively: it only ever
CREATES a `.uuid` file that does not exist yet, from a `resume_uuid` value
that is already sitting in the DB. It never invents a uuid for a session that
has none, and it never touches `state/tasks.db` (read-only here).

Usage:
    python scripts/backfill_resume_uuid_files.py --list     # dry run (default)
    python scripts/backfill_resume_uuid_files.py --apply    # actually write
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db  # noqa: E402
from tools.session_name import lock_basename  # noqa: E402
from tools.session_status import list_sessions, looks_like_uuid  # noqa: E402

LOCKS = db.ROOT / "state" / "locks"


def _missing_files(locks_dir: Path) -> list[dict]:
    """Rows with a DB resume_uuid but no `.uuid` file on disk."""
    out = []
    for row in list_sessions():
        uuid = row.get("resume_uuid")
        if not looks_like_uuid(uuid):
            continue
        path = locks_dir / f"{lock_basename(row['role'], row['session_id'])}.uuid"
        if not path.exists():
            out.append({**row, "path": path})
    return out


def cmd_list(locks_dir: Path) -> int:
    rows = _missing_files(locks_dir)
    if not rows:
        print("no gaps — every resume_uuid already has a .uuid file on disk")
        return 0
    print(f"{len(rows)} session(s) with a DB resume_uuid but no .uuid file:")
    for r in rows:
        print(f"  {r['path']}  <- role={r['role']} session_id={r['session_id']} "
              f"status={r['status']} resume_uuid={r['resume_uuid']}")
    print("\nWrite them with:\n  python scripts/backfill_resume_uuid_files.py --apply")
    return 0


def cmd_apply(locks_dir: Path) -> int:
    rows = _missing_files(locks_dir)
    if not rows:
        print("no gaps — every resume_uuid already has a .uuid file on disk")
        return 0
    locks_dir.mkdir(parents=True, exist_ok=True)
    for r in rows:
        r["path"].write_text(r["resume_uuid"] + "\n")
        print(f"wrote {r['path']}")
    print(f"\nbackfilled {len(rows)} .uuid file(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Backfill missing state/locks/<role>-<id>.uuid files "
                    "from c_level_sessions.resume_uuid (task-a98788d7)."
    )
    ap.add_argument("--list", action="store_true",
                     help="show what would be written (default)")
    ap.add_argument("--apply", action="store_true",
                     help="actually write the missing .uuid files")
    ap.add_argument("--locks-dir", default=None,
                     help="write here instead of the default state/locks")
    args = ap.parse_args()

    db.init()  # ensure resume_uuid column exists before reading it
    locks_dir = Path(args.locks_dir) if args.locks_dir else LOCKS

    if args.apply:
        return cmd_apply(locks_dir)
    return cmd_list(locks_dir)


if __name__ == "__main__":
    raise SystemExit(main())

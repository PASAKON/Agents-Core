#!/usr/bin/env python3
"""One-shot backfill for owner_cto / owner_role on in-flight tasks.

Routing (tools/send_to_cto.py) needs every task to carry the spawning
C-level session id (owner_cto) + its role (owner_role) so DEV reports type
back into the owner's iTerm tab instead of being orphaned or broadcast.
Tasks created before the Layer-1 stamp landed (issue #15) have NULL owners.

This script stamps them — explicitly, one row at a time. There is NO
guessing / auto-attribution: you supply --owner (and optionally --role).
Done / cancelled / merged rows are never touched, and --list only surfaces
in-flight ownerless work so a human can decide who each row belongs to.

Usage:
    python scripts/backfill_owner_cto.py --list
    python scripts/backfill_owner_cto.py --task task-1112d9d7 --owner 1a2b3c4d --role cfo
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import db  # noqa: E402

# Rows still moving through the pipeline — safe + useful to (re)stamp.
INFLIGHT_STATUSES = ("pending", "in_progress", "review", "conflict")
# Terminal rows — never restamp; their reports already landed (or never will).
IMMUTABLE_STATUSES = ("done", "cancelled", "merged")


def _ownerless_inflight() -> list[dict]:
    placeholders = ",".join("?" * len(INFLIGHT_STATUSES))
    q = (
        f"SELECT id, role, status, project, title, owner_cto, owner_role "
        f"FROM tasks WHERE status IN ({placeholders}) "
        f"AND (owner_cto IS NULL OR owner_cto = '') "
        f"ORDER BY created_at ASC"
    )
    with db.get_conn() as conn:
        return [dict(r) for r in conn.execute(q, INFLIGHT_STATUSES).fetchall()]


def cmd_list() -> int:
    rows = _ownerless_inflight()
    if not rows:
        print("no in-flight ownerless tasks — nothing to backfill")
        return 0
    print(f"{len(rows)} in-flight ownerless task(s):")
    for r in rows:
        print(
            f"  {r['id']}  {r['role']:14s} {r['status']:12s} "
            f"{r['project']:24s} {r['title']}"
        )
    print(
        "\nStamp one with:\n"
        "  python scripts/backfill_owner_cto.py "
        "--task <id> --owner <session_id> [--role <role>]"
    )
    return 0


def cmd_stamp(task_id: str, owner: str, role: str) -> int:
    t = db.get_task(task_id)
    if not t:
        print(f"ERROR: task {task_id} not found", file=sys.stderr)
        return 2
    if t["status"] in IMMUTABLE_STATUSES:
        print(
            f"ERROR: refusing to stamp {t['status']} task {task_id} — "
            f"done/cancelled/merged rows are left untouched",
            file=sys.stderr,
        )
        return 3
    db.set_fields(task_id, actor="backfill", owner_cto=owner, owner_role=role)
    print(f"stamped {task_id}: owner_cto={owner} owner_role={role}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Backfill owner_cto/owner_role on in-flight tasks (issue #15)."
    )
    ap.add_argument(
        "--list", action="store_true",
        help="list in-flight ownerless tasks (pending/in_progress/review/conflict)",
    )
    ap.add_argument("--task", help="task id to stamp")
    ap.add_argument(
        "--owner", help="owning C-level session id (CXO_SESSION_ID / CTO_SESSION_ID)"
    )
    ap.add_argument(
        "--role", default="cto",
        help="owning C-level role: cto/cfo/cmo/cgo (default: cto)",
    )
    args = ap.parse_args()

    # Ensure the owner_role column exists before we read/write it.
    db.init()

    if args.list:
        return cmd_list()
    if args.task and args.owner:
        return cmd_stamp(args.task, args.owner, args.role)
    ap.error("use --list, or --task <id> --owner <session_id> [--role <role>]")
    return 2  # unreachable (argparse exits), keeps type-checkers happy


if __name__ == "__main__":
    raise SystemExit(main())

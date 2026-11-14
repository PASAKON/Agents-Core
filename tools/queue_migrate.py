"""Copy legacy queues without deleting files. Quiesce JSONL writers for cutover."""
import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import db, org_queue
from tools import host_queue, budget_queue, disk_queue


def migrate(*, apply=False, paths=None):
    paths = paths if paths is not None else {
        "host": host_queue.QUEUE_PATH, "budget": budget_queue.QUEUE_PATH,
        "disk": disk_queue.QUEUE_PATH,
    }
    # Validate every source before opening a write transaction. Never silently
    # skip corrupt rows or collapse distinct payloads with the same task id.
    sources = {}
    for queue, path in paths.items():
        entries = {}
        lines = Path(path).read_text(encoding="utf-8").splitlines() if Path(path).exists() else []
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            if not isinstance(entry, dict) or not isinstance(entry.get("task_id"), str) or not entry["task_id"]:
                raise ValueError(f"{path}:{number}: missing task_id")
            tid = entry["task_id"]
            if tid in entries and entries[tid] != entry:
                raise ValueError(f"{path}:{number}: conflicting duplicate {tid}")
            entries[tid] = entry
        sources[queue] = entries
    counts = {}
    with db.get_conn() as conn:
        if apply:
            conn.execute(db.ORG_QUEUE_SCHEMA)
        if isinstance(conn, db.db_pg.Connection):
            exists = conn.execute("SELECT to_regclass('org_queue') AS name").fetchone()["name"] is not None
        else:
            exists = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='org_queue'").fetchone() is not None
        for queue, entries in sources.items():
            added = 0
            for tid, entry in entries.items():
                if apply:
                    added += org_queue.insert(conn, queue, entry)
                row = conn.execute(
                    "SELECT payload FROM org_queue WHERE queue=? AND task_id=?", (queue, tid),
                ).fetchone() if exists else None
                if row is not None and json.loads(row["payload"]) != entry:
                    raise ValueError(f"{queue}: conflicting hub payload for {tid}")
                if not apply and row is None:
                    added += 1
            total = conn.execute("SELECT COUNT(*) AS n FROM org_queue WHERE queue=?", (queue,)).fetchone()["n"] if exists else 0
            counts[queue] = dict(source=len(entries), added=added, total=total)
    for queue, count in counts.items():
        print(f"{queue}: source={count['source']} {'added' if apply else 'would_add'}={count['added']} total={count['total']}")
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    migrate(apply=args.apply)


if __name__ == "__main__":
    main()

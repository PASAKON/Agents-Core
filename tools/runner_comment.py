"""Record a reviewer's one-line assessment on a finished org task."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import db  # noqa: E402

KINDS = ("dev_small", "dev_medium", "dev_large", "review", "research",
         "devops", "docs", "creative", "browse")


def write_comment(task_id: str, *, kind: str, first_pass: str, line: str,
                  lane: str = "", by: str = "") -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; choose from {', '.join(KINDS)}")
    if first_pass not in ("y", "n"):
        raise ValueError("first_pass must be y or n")
    if lane not in ("", "cto", "cmo"):
        raise ValueError("lane must be cto or cmo")
    if not line.strip() or "\n" in line or "\r" in line:
        raise ValueError("line must be one nonempty line")
    comment = {"kind": kind, "first_pass": first_pass, "line": line.strip(),
               "lane": lane, "by": by,
               "at": datetime.now(timezone.utc).isoformat()}
    # A single transaction prevents two reviewers from losing each other's
    # metadata in the read/modify/write sequence.
    with db.get_conn() as conn:
        row = conn.execute("SELECT review FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"task not found: {task_id}")
        review = json.loads(row[0] or "{}")
        if not isinstance(review, dict):
            raise ValueError("task review is not a JSON object")
        review["runner_comment"] = comment
        conn.execute("UPDATE tasks SET review=?, updated_at=? WHERE id=?",
                     (json.dumps(review, ensure_ascii=False), db.now_iso(), task_id))
    return comment


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("--kind", required=True, choices=KINDS)
    parser.add_argument("--first-pass", required=True, choices=("y", "n"))
    parser.add_argument("--line", required=True)
    parser.add_argument("--lane", default="", choices=("", "cto", "cmo"))
    parser.add_argument("--by", default="")
    args = parser.parse_args()
    print(json.dumps(write_comment(args.task_id, kind=args.kind,
                                   first_pass=args.first_pass, line=args.line,
                                   lane=args.lane, by=args.by), ensure_ascii=False))


if __name__ == "__main__":
    main()

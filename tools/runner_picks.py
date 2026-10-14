"""Print observed runner picks from finished tasks with reviewer comments."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from lib import db  # noqa: E402


def build_table(db_path: Path) -> str:
    with db.get_conn(path=db_path, readonly=True) as conn:
        rows = conn.execute(
            "SELECT runner, runner_model, review FROM tasks "
            "WHERE status IN ('done', 'merged', 'failed') ORDER BY updated_at DESC"
        ).fetchall()
    groups = defaultdict(list)
    for row in rows:
        runner, model, raw = tuple(row)
        try:
            comment = json.loads(raw or "{}").get("runner_comment")
        except (ValueError, TypeError, AttributeError):
            continue
        if isinstance(comment, dict) and comment.get("kind") and comment.get("line"):
            groups[(comment["kind"], f"{runner or 'claude'}:{model or 'unknown'}")].append(comment)
    lines = ["| Job kind | Runner:model:effort | Runs | First-pass y/n | Last 3 comments |",
             "| --- | --- | ---: | ---: | --- |"]
    for (kind, model), comments in sorted(groups.items()):
        if len(comments) < 3:
            lines.append(f"| {kind} | {model} | — | — | — |")
            continue
        yes = sum(c.get("first_pass") == "y" for c in comments)
        no = sum(c.get("first_pass") == "n" for c in comments)
        recent = "; ".join(str(c["line"]).replace("|", "\\|") for c in comments[:3])
        lines.append(f"| {kind} | {model} | {len(comments)} | {yes}/{no} | {recent} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "state" / "tasks.db")
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()
    table = build_table(args.db)
    if args.write:
        args.write.write_text(table, encoding="utf-8")
    else:
        print(table, end="")


if __name__ == "__main__":
    main()

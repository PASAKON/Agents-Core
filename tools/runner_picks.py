"""Print the job × runner:model:effort table from reviewed runs (hub events `runner_fit`).

The reviewer's verdict is recorded once, by tools/runner_fit.py (CXO_Gate_RouteFirst Gate 5):
job type, pass/redo/fail, first_pass and a one-line `why`. This only reads those events.
A cell with fewer than MIN_RUNS reviewed runs prints "—": not enough runs to pick from.
Skill ALL_Knowledge_RunnerPicks is written from this table.
"""
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

MIN_RUNS = 3


def _payloads(db_path: Path, since: str | None) -> list[dict]:
    query = "SELECT payload FROM events WHERE kind = 'runner_fit'"
    params: list = []
    if since:
        query += " AND ts >= ?"
        params.append(since)
    query += " ORDER BY ts DESC"
    with db.get_conn(path=db_path, readonly=True) as conn:
        rows = conn.execute(query, params).fetchall()
    out = []
    for (raw,) in (tuple(r) for r in rows):
        try:
            p = json.loads(raw or "{}")
        except (ValueError, TypeError):
            continue
        if isinstance(p, dict) and p.get("runner") and p.get("job_type"):
            out.append(p)
    return out


def build_table(db_path: Path, since: str | None = None) -> str:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in _payloads(db_path, since):
        groups[(p["job_type"], f"{p['runner']}:{p.get('model') or 'unknown'}")].append(p)
    lines = ["| Job | Runner:model:effort | Runs | Pass/redo/fail | First pass | Last 3 comments |",
             "| --- | --- | ---: | --- | ---: | --- |"]
    for (job, pick), runs in sorted(groups.items()):
        if len(runs) < MIN_RUNS:
            lines.append(f"| {job} | {pick} | {len(runs)} | — | — | — |")
            continue
        res = "/".join(str(sum(r.get("result") == k for r in runs)) for k in ("pass", "redo", "fail"))
        first = sum(r.get("first_pass") is True for r in runs)
        recent = "; ".join(str(r.get("why") or "").replace("|", "\\|").replace("\n", " ")[:120]
                           for r in runs[:3])
        lines.append(f"| {job} | {pick} | {len(runs)} | {res} | {first}/{len(runs)} | {recent} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "state" / "tasks.db")
    parser.add_argument("--since", help="ISO date; only runs reviewed from then on")
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()
    table = build_table(args.db, args.since)
    if args.write:
        args.write.write_text(table, encoding="utf-8")
    else:
        print(table, end="")


if __name__ == "__main__":
    main()

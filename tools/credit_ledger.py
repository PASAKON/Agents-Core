#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Who spent which generation credits, on what, when, and for which channel.

CEO 2026-09-28: every credit spend (Flow, Higgsfield, TopView, H3 pod $, ...) gets
one row here, signed by the session that spent it, so parallel users of one
credit pool (ILAG films and the animal series share the Google AI Ultra pool)
can still back-calculate their own costs.

    python3 tools/credit_ledger.py add --who cmo-c7879552 --engine flow --credits 18 \
        --channel "บ้านนี้มีข้าวเหนียว" --purpose "smoke: dog inner voice, 3 shots 360p" \
        --kind test --task task-xxxx --before 3010 --after 2992
    python3 tools/credit_ledger.py sum --by channel --month 2026-09 --engine flow
    python3 tools/credit_ledger.py list --last 20

The ledger is JSON Lines (one JSON object per line) so appends never rewrite the
file, and git's union merge keeps both sides when two machines append at once
(.gitattributes). Commit the ledger after you add a row.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "docs" / "ops" / "credit-ledger.jsonl"
BKK = timezone(timedelta(hours=7))
KINDS = {"test", "production", "reshoot", "setup", "other"}
UNITS = {"credits", "usd", "thb"}


def _now() -> str:
    return datetime.now(BKK).isoformat(timespec="seconds")


def read_rows(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"{path}:{n}: not JSON ({e}); fix the line by hand")
    return rows


def add(args: argparse.Namespace, path: Path = LEDGER) -> dict:
    if args.credits < 0:
        raise SystemExit("--credits must be >= 0 (a refund is a separate row with kind=other and a note)")
    row = {
        "ts": args.when or _now(),
        "who": args.who,
        "engine": args.engine,
        "unit": args.unit,
        "amount": args.credits,
        "channel": args.channel,
        "purpose": args.purpose,
        "kind": args.kind,
        "task": args.task or "",
    }
    if args.before is not None:
        row["balance_before"] = args.before
    if args.after is not None:
        row["balance_after"] = args.after
    if args.before is not None and args.after is not None:
        delta = args.before - args.after
        if abs(delta - args.credits) > 1e-9:
            # Parallel spend by another session lands in the same pool window;
            # keep both numbers, flag it, never silently "fix" either one.
            row["delta_mismatch"] = delta
            print(f"WARNING: balance delta {delta} != amount {args.credits}; "
                  f"someone else may have spent in the same window. Recorded both.", file=sys.stderr)
    if args.note:
        row["note"] = args.note
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)
    return row


def summarise(rows: list[dict], by: str, month: str | None, engine: str | None) -> dict:
    out: dict[tuple, float] = defaultdict(float)
    for r in rows:
        if month and not r.get("ts", "").startswith(month):
            continue
        if engine and r.get("engine") != engine:
            continue
        out[(r.get(by, "?"), r.get("engine", "?"), r.get("unit", "?"))] += r.get("amount", 0)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="append one spend row")
    a.add_argument("--who", required=True, help="session or role that spent it, e.g. cmo-c7879552, cto-cb63de3a")
    a.add_argument("--engine", required=True, help="flow | higgsfield | topview | h3-runpod | runware | ...")
    a.add_argument("--credits", required=True, type=float, help="amount spent, in --unit")
    a.add_argument("--unit", default="credits", choices=sorted(UNITS))
    a.add_argument("--channel", required=True, help="the page/brand the spend is for, e.g. 'ILAG ละครสั้นคุณธรรม'")
    a.add_argument("--purpose", required=True, help="what it was spent on, one line")
    a.add_argument("--kind", default="production", choices=sorted(KINDS))
    a.add_argument("--task", help="task-id, if any")
    a.add_argument("--before", type=float, help="pool balance read before the spend")
    a.add_argument("--after", type=float, help="pool balance read after the spend")
    a.add_argument("--when", help="ISO time of the spend if not now (default now, +07:00)")
    a.add_argument("--note")

    s = sub.add_parser("sum", help="totals grouped by a field")
    s.add_argument("--by", default="channel", choices=["channel", "who", "engine", "kind", "task"])
    s.add_argument("--month", help="YYYY-MM prefix of ts")
    s.add_argument("--engine")

    l = sub.add_parser("list", help="last rows")
    l.add_argument("--last", type=int, default=20)

    args = ap.parse_args(argv)
    if args.cmd == "add":
        print(json.dumps(add(args), ensure_ascii=False))
    elif args.cmd == "sum":
        totals = summarise(read_rows(), args.by, args.month, args.engine)
        for (key, eng, unit), amt in sorted(totals.items(), key=lambda kv: -kv[1]):
            print(f"{amt:>10g} {unit:<7} {eng:<11} {key}")
        if not totals:
            print("(no rows)")
    elif args.cmd == "list":
        for r in read_rows()[-args.last:]:
            print(json.dumps(r, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

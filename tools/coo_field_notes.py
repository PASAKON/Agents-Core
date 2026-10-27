#!/usr/bin/env python3
"""Read the field notes SomPong filed through the COO gate (#24b), so a CTO or PH can fold them into
the skill by hand.

    bash scripts/hub/org-python.sh tools/coo_field_notes.py list [--since ISO]

Prints one line per note, oldest first: `skill · tag · ts · text`. Runs as root with ORG_DB_URL, the
hub owner's connection: the COO's own role (org_coo) can write a note but never read one back.

"Pending" is every note at or after --since. A note has no folded flag (events are append-only), so
write down the ts of the last note you folded and pass it next time, or you read the same notes
again. The skill file is changed by hand and never by this tool, by the gate or by the COO.

The text was written by the COO's tools: control characters are replaced before anything is printed,
so a note cannot move the cursor or paint over a line of a CTO's terminal.
"""
from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KIND = "coo_field_note"


def _iso(value: str) -> str:
    """`value` in the format lib.db.now_iso() writes into events.ts, so the comparison is on text."""
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as e:
        raise SystemExit(f"--since must be an ISO date or time (2026-10-27 or 2026-10-27T06:00:00Z): {e}") from e
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _plain(value: object) -> str:
    return "".join(" " if unicodedata.category(c) in ("Cc", "Cf", "Zl", "Zp") else c
                   for c in str(value if value is not None else ""))


def fetch(since: str | None = None) -> list[dict]:
    from lib import db
    sql, args = "SELECT id, payload, ts FROM events WHERE kind=?", [KIND]
    if since:
        sql, args = sql + " AND ts >= ?", args + [_iso(since)]
    with db.get_conn() as conn:
        rows = conn.execute(sql + " ORDER BY id", args).fetchall()
    return [{"id": r["id"], "payload": r["payload"], "ts": r["ts"]} for r in rows]


def render(rows: list[dict]) -> list[str]:
    lines = []
    for r in rows:
        raw = r["payload"]
        try:
            p = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except ValueError:
            p = {}
        if not isinstance(p, dict):
            p = {}
        lines.append(" · ".join(_plain(x) for x in (p.get("skill"), p.get("tag"), r["ts"], p.get("text"))))
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list", help="print the notes: skill · tag · ts · text")
    ls.add_argument("--since", help="only notes at or after this ISO date/time (UTC if no offset)")
    args = ap.parse_args(argv)
    try:
        rows = fetch(args.since)
    except SystemExit:
        raise
    except Exception as e:
        print(f"coo_field_notes: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}", file=sys.stderr)
        return 1
    for line in render(rows):
        print(line)
    print(f"{len(rows)} field note(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

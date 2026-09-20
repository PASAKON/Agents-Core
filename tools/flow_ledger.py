#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The per-shot memory for tools/flow_shoot.py — not a context window.

Parses a «บัญชี» shot sheet (docs/scripts/banchi-ACTn.md, the format
tools/build_shotsheet.py renders) into one ledger row per shot, and keeps
that ledger as a TSV file that survives a crash between any two writes.

    python3 tools/flow_ledger.py init   docs/scripts/banchi-ACT2.md state/banchi/ACT2.tsv
    python3 tools/flow_ledger.py status state/banchi/ACT2.tsv

`init` is idempotent: an existing row is never overwritten, only shots that
are not yet in the ledger are appended. Re-running it after a sheet edit does
not silently reset a row's progress.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

FIELDS = ["shot", "act", "dur_s", "chips", "prompt_sha", "status",
          "flow_clip_id", "file", "sha256", "got_dur", "attempts", "note"]

STATUSES = {"todo", "submitted", "generated", "downloaded", "verified",
            "refused", "needs_model", "failed"}

# "### SHOT 35 · 0:00–0:06 · 6s · Medium shot, static camera" — the en dash
# between the timecodes is literal, not a hyphen; build_shotsheet.py writes it.
_SHOT_RE = re.compile(
    r"^### SHOT (\d+) · [\d:]+–[\d:]+ · (\d+)s · .+$", re.MULTILINE)
_ATTACH_RE = re.compile(r"^\*\*ATTACH\*\*\s*(.+)$", re.MULTILINE)
_CHIP_RE = re.compile(r"`(@[A-Za-z0-9_]+)`")
_FENCE_RE = re.compile(r"```\n(.*?)\n```", re.DOTALL)


def parse_sheet(sheet_path: Path) -> list[dict]:
    """Return one dict per SHOT block: shot, act, dur_s, chips (in attach
    order), prompt (the fenced block verbatim), prompt_sha."""
    text = sheet_path.read_text(encoding="utf-8")
    m_act = re.search(r"ACT(\w+)", sheet_path.stem)
    act = m_act.group(1) if m_act else "?"

    headers = list(_SHOT_RE.finditer(text))
    shots = []
    for i, hm in enumerate(headers):
        shot_n = int(hm.group(1))
        dur_s = int(hm.group(2))
        block = text[hm.end(): headers[i + 1].start() if i + 1 < len(headers) else len(text)]

        attach_m = _ATTACH_RE.search(block)
        chips = _CHIP_RE.findall(attach_m.group(1)) if attach_m else []

        fence_m = _FENCE_RE.search(block)
        if not fence_m:
            raise ValueError(f"shot {shot_n}: no fenced prompt block in {sheet_path}")
        prompt = fence_m.group(1)

        shots.append({
            "shot": shot_n,
            "act": act,
            "dur_s": dur_s,
            "chips": chips,
            "prompt": prompt,
            "prompt_sha": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
    if not shots:
        raise ValueError(f"no '### SHOT n' headers found in {sheet_path}")
    return shots


def _row_to_line(row: dict) -> str:
    # TSV is one physical line per shot. Flow error/refusal messages can
    # contain newlines; allowing those through corrupts the next load by
    # turning the continuation into a fake row. Tabs/newlines are display
    # formatting only, so collapse them to spaces before the atomic write.
    return "\t".join(
        re.sub(r"[\t\r\n]+", " ", str(row.get(f, ""))).strip()
        for f in FIELDS
    )


def _line_to_row(line: str) -> dict:
    parts = line.split("\t")
    parts += [""] * (len(FIELDS) - len(parts))
    return dict(zip(FIELDS, parts[:len(FIELDS)]))


def load_ledger(ledger_path: Path) -> dict[int, dict]:
    """shot number -> row dict, in whatever order the file has them."""
    if not ledger_path.exists():
        return {}
    lines = ledger_path.read_text(encoding="utf-8").splitlines()
    rows: dict[int, dict] = {}
    for line in lines[1:]:  # skip header
        if not line.strip():
            continue
        row = _line_to_row(line)
        rows[int(row["shot"])] = row
    return rows


def save_ledger(ledger_path: Path, rows: dict[int, dict]) -> None:
    """Write temp, then rename — a crash between two steps loses nothing."""
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(FIELDS)]
    for shot in sorted(rows):
        lines.append(_row_to_line(rows[shot]))
    tmp = ledger_path.with_suffix(ledger_path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, ledger_path)


def init_ledger(sheet_path: Path, ledger_path: Path) -> dict:
    shots = parse_sheet(sheet_path)
    existing = load_ledger(ledger_path)
    added = 0
    for s in shots:
        n = s["shot"]
        if n in existing:
            continue  # idempotent: an existing row is never overwritten
        existing[n] = {
            "shot": n,
            "act": s["act"],
            "dur_s": s["dur_s"],
            "chips": ",".join(s["chips"]),
            "prompt_sha": s["prompt_sha"],
            "status": "todo",
            "flow_clip_id": "",
            "file": "",
            "sha256": "",
            "got_dur": "",
            "attempts": "0",
            "note": "",
        }
        added += 1
    save_ledger(ledger_path, existing)
    return {"total": len(shots), "existing": len(shots) - added, "added": added}


def status_summary(ledger_path: Path) -> str:
    rows = load_ledger(ledger_path)
    if not rows:
        return f"ledger empty or not found: {ledger_path}"
    counts: dict[str, int] = {}
    for r in rows.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines = [f"ledger: {ledger_path}  ({len(rows)} shots)"]
    for st in sorted(counts):
        lines.append(f"  {st:<12} {counts[st]}")
    next_todo = next((r for n, r in sorted(rows.items()) if r["status"] == "todo"), None)
    lines.append(f"next todo: shot {next_todo['shot']}" if next_todo else "next todo: none")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="parse a sheet, append missing rows")
    p_init.add_argument("sheet", type=Path)
    p_init.add_argument("ledger", type=Path)

    p_status = sub.add_parser("status", help="one-screen summary")
    p_status.add_argument("ledger", type=Path)

    args = ap.parse_args()
    if args.cmd == "init":
        r = init_ledger(args.sheet, args.ledger)
        print(f"init {args.ledger}: {r['total']} shots in sheet, "
              f"{r['existing']} already in ledger, {r['added']} appended")
    elif args.cmd == "status":
        print(status_summary(args.ledger))
    return 0


if __name__ == "__main__":
    sys.exit(main())

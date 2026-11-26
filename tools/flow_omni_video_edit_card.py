#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contabo Run Inbox bridge for Google Flow Omni 1.2 Flash In-Place Video-to-Video Edit + 1080p Upscale.
Executes the staged remote CDP edit on winbox:9226, verifies the --max-credits guard before submit,
exports 1080p, and logs the exact credit delta to docs/ops/credit-ledger.jsonl.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE_LEDGER = Path("/opt/MoonieXHQ/Agents/Core/docs/ops/credit-ledger.jsonl")
WINBOX_PY = r"C:\mooniex\pwvenv\Scripts\python.exe"
WINBOX_SCRIPT = r"C:\mooniex\mypasakon_neon\run_omni_sweater_4s.py"


def main() -> int:
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument("--max-credits", required=True, type=int)
    ap.add_argument("--channel", default="MYPASAKON")
    ap.add_argument("--purpose", default="MYPASAKON 4s Omni 1.2 Flash winter knit sweater + 1080p studio video edit test")
    ap.add_argument("--task", default="Q-20261125-1618-f177")
    ap.add_argument("--who", default="project_head-agy-5e00df47")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    remote_cmd = f"{WINBOX_PY} -u {WINBOX_SCRIPT} --max-credits {args.max_credits}"
    if args.dry_run:
        remote_cmd += " --dry-run"

    proc = subprocess.run(
        ["ssh", "winbox", remote_cmd],
        capture_output=True,
        text=True,
        timeout=300,
    )
    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    print(out, flush=True)
    if proc.returncode != 0:
        return proc.returncode

    if not args.dry_run and LIVE_LEDGER.parent.exists():
        m_b = re.search(r"BALANCE_BEFORE=(\d+)", out)
        m_a = re.search(r"BALANCE_AFTER=(\d+)", out)
        m_s = re.search(r"SPENT=(\d+)", out)
        before = int(m_b.group(1)) if m_b else None
        after = int(m_a.group(1)) if m_a else None
        spent = int(m_s.group(1)) if m_s else args.max_credits
        sys.path.insert(0, str(ROOT))
        from tools import credit_ledger
        credit_ledger.add(
            argparse.Namespace(
                who=args.who,
                engine="flow",
                unit="credits",
                credits=spent,
                channel=args.channel,
                purpose=args.purpose,
                task=args.task,
                kind="test",
                before=before,
                after=after,
                when=None,
                note="Omni 1.2 Flash 4s video edit (12 cr) + 1080p upscale (5 cr)",
                include_balances=True,
            ),
            path=LIVE_LEDGER,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

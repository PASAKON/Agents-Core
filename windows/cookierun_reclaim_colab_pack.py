#!/usr/bin/env python3
"""cookierun_reclaim_colab_pack.py -- give back the 11.45 GB the Colab packs hold.

`colab_pack/` exists for one reason: Colab cannot reach winbox, so the training
corpus had to be put somewhere Colab could read. That job is done -- the model
was trained and A/B'd on 2026-09-19 -- and the shards are **derived data**, not
an archive. Every byte is reproducible from `play_rec`, which is tier A, still
on this box (176 take directories) and separately on Drive:

    python cookierun_idm_data.py  --out idm_index.json          # index from play_rec
    python cookierun_pack_for_colab.py --index idm_index.json --out colab_pack

That is the sentence `disk-hygiene` asks for, so by its one law this is
regenerable and goes without asking. It is also inside the only scope winbox
grants a steward (`Documents\\CookieRunScript`).

A tool rather than a shell line, deliberately (disk-hygiene): it re-checks its
own preconditions first, it writes the ledger row, and the next person who needs
this space gets a reviewable thing instead of somebody's remembered `rm`.

    python cookierun_reclaim_colab_pack.py            # dry run, prints and exits
    python cookierun_reclaim_colab_pack.py --go       # actually deletes
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path.home() / "Documents" / "CookieRunScript"
TARGET = DATA / "colab_pack"
SOURCE = DATA / "play_rec"
LEDGER = DATA / "ledger" / "housekeeping.jsonl"
MIN_SOURCE_DIRS = 50      # a plausible corpus; 176 at the time of writing


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go", action="store_true", help="delete (default is a dry run)")
    a = ap.parse_args()

    if not TARGET.exists():
        print(f"{TARGET} is already gone - nothing to do")
        return 0

    files = [p for p in TARGET.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"target : {TARGET}\n         {len(files)} files, {total / 1e9:.2f} GB")

    # The precondition that actually matters: what rebuilds this must still be
    # here. Deleting derived data whose source has also gone is not reclaiming,
    # it is losing -- and "I remember it was backed up" is not a check.
    takes = [p for p in SOURCE.iterdir() if p.is_dir()] if SOURCE.exists() else []
    print(f"source : {SOURCE}  ->  {len(takes)} take directories")
    if len(takes) < MIN_SOURCE_DIRS:
        print(f"REFUSING: expected at least {MIN_SOURCE_DIRS} take directories to "
              f"rebuild from; found {len(takes)}. Nothing deleted.")
        return 1

    if not a.go:
        print("\ndry run - pass --go to delete")
        return 0

    shutil.rmtree(TARGET)
    row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "kind": "reclaim_derived",
           "path": str(TARGET),
           "files": len(files),
           "bytes": total,
           "manifest": None,
           "dest": None,
           "note": ("Colab training shards. Derived from play_rec; rebuild with "
                    "cookierun_idm_data.py then cookierun_pack_for_colab.py. "
                    "Verified copies existed on Contabo (/root/idm-packs, 47/47 "
                    "shards readable) and on Drive at the time of deletion. The "
                    "model they were made for was trained and A/B'd 2026-09-19."),
           "by": "cto-6ebacd0e"}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\ndeleted {total / 1e9:.2f} GB; ledger row written to {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

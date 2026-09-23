#!/usr/bin/env python3
"""bl_check.py — the P1 gate (task-42e3b6af deliverable 3).

  bl_check.py p1 <edl-dir> --media-root DIR

Checks, all against p1_layout.json in <edl-dir>:
  1. coverage       every second of the voice track covered, no gaps/overlaps
  2. media exists   every referenced media file is present under --media-root
  3. lipsync        every lipsync part seated at a media_start that has
                     actually begun by its event's t0 (bl_tools.py offsets math)
  4. avatar legal   avatar_mode is legal for the plate's role (shape check,
                     also enforced at compose time -- run again here so the
                     gate does not depend on having composed first)
  5. evidence box   HARD, §6d: a composited avatar never covers a real-footage
                     evidence box

Exits 0 and prints "P1 CHECK PASSED" only if every check is clean. Exits 1
and prints every FAIL otherwise -- never silently skip a category.

Stdlib only (see bl_edl.py's own note).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import bl_edl  # noqa: E402


def run_p1(edl_dir: Path, media_root: Path) -> list[str]:
    problems: list[str] = []
    p1 = bl_edl.load_json(edl_dir / "p1_layout.json")

    try:
        bl_edl.validate_p1(p1)
    except bl_edl.EDLError as e:
        # shape is broken enough that the other checks can't run meaningfully
        return [f"shape: {e}"]

    events = p1["events"]
    offsets = p1.get("lipsync_offsets", {})

    problems += [f"coverage: {m}" for m in bl_edl.check_coverage(events, float(p1["duration"]))]
    problems += [f"media: {m}" for m in bl_edl.check_media_exists(p1, media_root)]
    problems += [f"lipsync: {m}" for m in bl_edl.check_lipsync_seating(events, offsets)]
    problems += [f"evidence-box: {m}" for m in bl_edl.check_avatar_evidence_overlap(events, media_root)]
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("p1", help="the P1 gate")
    p1.add_argument("edl_dir", type=Path)
    p1.add_argument("--media-root", type=Path, required=True)

    a = ap.parse_args(argv)

    try:
        problems = run_p1(a.edl_dir, a.media_root)
    except bl_edl.EDLError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if not problems:
        print("P1 CHECK PASSED")
        return 0
    for p in problems:
        print(f"  FAIL {p}")
    print(f"\nP1 CHECK FAILED — {len(problems)} problem(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())

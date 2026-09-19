#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Concatenate a «บัญชี» act's clips into one file, and refuse to lie about it.

    python3 tools/assemble_act.py ~/Desktop/banchi-ACT1-v2 \
                                  docs/scripts/banchi-ACT1.data.py \
                                  ~/Desktop/banchi-ACT1.mp4

Two things this does that a hand-typed ffmpeg line does not:

It checks the act is COMPLETE before it writes anything. A cut assembled from
"whatever happened to be in the folder" is how a missing shot reaches a review
as a jump cut that everyone assumes was a directing choice.

It never re-encodes. The CEO judges quality from the file he is sent, so a
re-encoded review copy makes him rate our encoder instead of the footage. -c copy
or nothing.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path


def load(path: Path):
    spec = importlib.util.spec_from_file_location("sheetdata", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    clips, data, dest = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    allow_partial = "--partial" in sys.argv

    d = load(data)
    want = [sh[0] for sh in d.SHOTS]
    have = {int(re.sub(r"\D", "", f.stem)): f
            for f in clips.glob("shot-*.mp4")}
    missing = [n for n in want if n not in have]

    if missing:
        if not allow_partial:
            print(f"refusing to assemble: {len(missing)} shot(s) missing — {missing}")
            print("  a cut with a hole in it reads as a directing choice, not an absence.")
            print("  pass --partial if you deliberately want a rough cut, and say so"
                  " to whoever you send it to.")
            return 1
        print(f"PARTIAL cut — {len(missing)} shot(s) missing: {missing}")

    order = [n for n in want if n in have]
    listing = dest.with_suffix(".concat.txt")
    listing.write_text("".join(f"file '{have[n].resolve()}'\n" for n in order))

    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(dest), "-y"],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("ffmpeg failed:\n" + r.stderr)
        return 1

    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(dest)],
        capture_output=True, text=True).stdout.strip()
    expected = sum(sh[1] for sh in d.SHOTS if sh[0] in have)
    got = float(dur)
    mb = dest.stat().st_size / 1e6

    print(f"wrote {dest}")
    print(f"  {len(order)} shots · {got:.1f}s (sheet says {expected}s) · {mb:.1f} MB")
    # A concat that silently dropped a stream shows up here and nowhere else.
    if abs(got - expected) > 1.5:
        print(f"  ⚠ DURATION MISMATCH {got - expected:+.1f}s — do not send this out"
              " until you know why.")
        return 1
    listing.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find clips where the generator burned text into the picture — without watching them.

Veo adds its own Thai captions to shots nobody asked to caption, and the Thai it
writes is mangled: «ไม่ใส่ถั่วทอกใช่ไหเวิทย์» for "ไม่ใส่ถั่วงอกใช่ไหมวิทย์",
«แล้วมูลนนั่ติกินหู้ร้กาอกิทย์» for nothing readable at all. Measured 2026-09-23:
**14 of 173 shots, 8% of the film.** It survives a re-shoot — shot 43 was re-fired
for this exact defect and came back with different garbage in the same place.

The point of this file is that finding it costs almost nothing:

  * subtitles live in the bottom ~18% of the frame, so crop there and ignore 82%
    of every image;
  * they persist for seconds, so **four samples per clip** catch them — not 240;
  * tesseract reads the crop locally, free, no model and no network;
  * a hit is "≥8 Thai characters in the band", which needs no judgement at all.

173 clips scan in a couple of minutes. Nobody has to look at a frame until the
report says which frame to look at.

    python3 tools/burned_text_scan.py <clip-dir> [...] [--samples 4] [--out FILE.tsv]

Report: shot · t · text found. An empty report is a real answer, not a skipped check.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

THAI = re.compile(r"[฀-๿]")
BAND_TOP = 0.78      # subtitles sit below this fraction of the frame height
BAND_H = 0.18
MIN_CHARS = 8        # shorter than this is OCR noise on texture, not a caption


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 8.0


def scan(path: Path, samples: int, workdir: str) -> list[tuple[float, str]]:
    dur = duration(path)
    found = []
    for i in range(samples):
        frac = (i + 1) / (samples + 1)
        t = dur * frac
        png = os.path.join(workdir, f"{path.stem}-{i}.png")
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{t}", "-i", str(path),
             "-vf", f"crop=iw:ih*{BAND_H}:0:ih*{BAND_TOP},scale=iw*2:ih*2",
             "-frames:v", "1", png],
            capture_output=True)
        if not os.path.exists(png):
            continue
        txt = subprocess.run(["tesseract", png, "-", "-l", "tha", "--psm", "7"],
                             capture_output=True, text=True).stdout
        thai = "".join(THAI.findall(txt))
        if len(thai) >= MIN_CHARS:
            found.append((round(t, 1), thai[:60]))
        os.remove(png)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--samples", type=int, default=4,
                    help="frames sampled per clip (default 4)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    if not subprocess.run(["which", "tesseract"], capture_output=True).stdout:
        print("tesseract not on PATH — brew install tesseract tesseract-lang", file=sys.stderr)
        return 2

    clips: list[tuple[int, Path]] = []
    for d in args.dirs:
        for f in sorted(d.glob("shot-*.mp4")):
            m = re.match(r"shot-0*(\d+)\.mp4$", f.name)
            if m:
                clips.append((int(m.group(1)), f))
    clips.sort()
    if not clips:
        print("no shot-N.mp4 found", file=sys.stderr)
        return 1

    work = tempfile.mkdtemp()
    rows = []
    for n, f in clips:
        for t, text in scan(f, args.samples, work):
            rows.append((n, t, text))
            print(f"  shot {n:>3}  {t:>5.1f}s  «{text}»")

    shots = sorted({r[0] for r in rows})
    print(f"\n{len(shots)} of {len(clips)} clips carry burned-in text "
          f"({len(shots)/len(clips):.0%}) — shots {shots}")
    if not shots:
        print("(clean — this is a checked answer, not an unchecked one)")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("shot\tt\ttext\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

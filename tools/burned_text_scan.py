#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Find clips where the generator burned text into the picture — without watching them.

Veo adds its own Thai captions to shots nobody asked to caption, and the Thai it
writes is mangled: «ไม่ใส่ถั่วทอกใช่ไหเวิทย์» for "ไม่ใส่ถั่วงอกใช่ไหมวิทย์",
«แล้วมูลนนั่ติกินหู้ร้กาอกิทย์» for nothing readable at all. It survives a
re-shoot — shot 43 was re-fired for this exact defect and came back with
different garbage in the same place.

How many shots actually carry one, measured 2026-09-23 on the 173-shot «บัญชี»
cut: **3 (29, 43, 115)**. The first version of this file said 14, and that
number was wrong: it treated "tesseract read ≥8 Thai characters in the band" as
a caption, and tesseract reads Thai out of anything — a floral nightgown, table
grain, an apron, stair treads. Eleven of its fourteen hits were texture, and it
missed shot 115 entirely because four samples a clip fell between the lines.
Every one of those was settled by looking at one strip image; the fix below
makes that look unnecessary.

**A caption is a pixel fact before it is a text fact.** Burned subtitles are
near-white glyphs with a dark outline or box. Texture almost never has pure
white sitting next to near-black. So the test is:

  * crop the bottom band (78–96% of the height — where Veo puts them),
    scale it to a fixed 360×80 so the threshold does not depend on resolution;
  * sample at 2 fps — a caption is on screen for the length of a line, and
    2 fps cannot fall between two lines;
  * count pixels that are white (all channels > 225) with a near-black pixel
    (all channels < 90) three pixels to the left or right;
  * a shot is a hit when any frame scores ≥ GATE.

Measured on the whole film: the three real captions scored 160, 244 and 326;
the highest non-caption (a steel pot's highlight) scored 38. GATE sits at 80.

tesseract then reads the best frame of each hit, only to print what was
written; it no longer decides anything, and the scan runs without it.

173 clips scan in about a minute, locally, free. Nobody has to look at a frame
until the report says which frame to look at.

    python3 tools/burned_text_scan.py <clip-dir> [...] [--fps 2] [--out FILE.tsv]

Report: shot · t · score · text. An empty report is a real answer, not a skipped check.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

THAI = re.compile(r"[฀-๿]")
BAND_TOP = 0.78      # subtitles sit below this fraction of the frame height
BAND_H = 0.18
W, H = 360, 80       # fixed band size, so GATE means the same at 720p and 1080p
WHITE, DARK = 225, 90
REACH = 3            # px left/right to look for the glyph's dark outline
GATE = 80            # real captions 160-326, worst texture 38 (2026-09-23)


def band_scores(path: Path, fps: float) -> list[tuple[float, int]]:
    """(t, score) for every sampled frame of the caption band."""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path),
         "-vf", f"fps={fps},crop=iw:ih*{BAND_H}:0:ih*{BAND_TOP},scale={W}:{H}",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True).stdout
    size = W * H * 3
    step = REACH * 3
    out = []
    for k in range(len(raw) // size):
        f = raw[k * size:(k + 1) * size]
        n = 0
        for y in range(H):
            row = y * W * 3
            for x in range(REACH, W - REACH):
                i = row + x * 3
                if f[i] > WHITE and f[i + 1] > WHITE and f[i + 2] > WHITE:
                    a, b = i - step, i + step
                    if (max(f[a], f[a + 1], f[a + 2]) < DARK
                            or max(f[b], f[b + 1], f[b + 2]) < DARK):
                        n += 1
        out.append((round(k / fps, 1), n))
    return out


def read_text(path: Path, t: float, workdir: str) -> str:
    """What the caption says, for the report. Never used to decide a hit."""
    if not shutil.which("tesseract"):
        return ""
    png = os.path.join(workdir, f"{path.stem}-{t}.png")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t}", "-i", str(path),
         "-vf", f"crop=iw:ih*{BAND_H}:0:ih*{BAND_TOP},scale=iw*2:ih*2",
         "-frames:v", "1", png],
        capture_output=True)
    if not os.path.exists(png):
        return ""
    txt = subprocess.run(["tesseract", png, "-", "-l", "tha", "--psm", "7"],
                         capture_output=True, text=True).stdout
    os.remove(png)
    return "".join(THAI.findall(txt))[:60]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--fps", type=float, default=2.0,
                    help="band samples per second (default 2)")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

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
        scores = band_scores(f, args.fps)
        if not scores:
            print(f"  shot {n:>3}  UNREADABLE — ffmpeg returned no frames", file=sys.stderr)
            continue
        t, best = max(scores, key=lambda s: s[1])
        if best >= GATE:
            text = read_text(f, t, work)
            rows.append((n, t, best, text))
            print(f"  shot {n:>3}  {t:>5.1f}s  score {best:>4}  «{text}»")

    shots = [r[0] for r in rows]
    print(f"\n{len(shots)} of {len(clips)} clips carry burned-in text "
          f"({len(shots)/len(clips):.0%}) — shots {shots}")
    if not shots:
        print("(clean — this is a checked answer, not an unchecked one)")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("shot\tt\tscore\ttext\n")
            for r in rows:
                fh.write("\t".join(str(x) for x in r) + "\n")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

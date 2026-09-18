#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mechanically check «บัญชี» clips against the shot sheet that produced them.

Why this exists: the first Act 1 cut was rejected with "ดูไม่รู้เรื่องเลย", and
the cause turned out to be measurable — the film spoke for about two seconds of
every eight and was silent for the rest, against a reference reel that is silent
11% of the time. Nobody could see that by watching; it took a measurement. So
the measurement runs before anyone watches.

It reports ONLY what a machine can establish: the file exists, it is the length
its own shot heading asked for, it carries audio that is not silence, and how
much of it is dead air. It says nothing about whether the right character, set
or words are there — that is the CTO's eye on the contact sheet, and the CEO's
ear on the cut.

    python3 tools/clip_review.py <clips-dir> <sheet-dir> [data.py]

`clips-dir` holds `shot-NN.mp4`. Exit code is non-zero if any clip fails a
check, so this can gate an assembly step instead of being something to remember.
"""
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

DATA = Path("docs/scripts/banchi-ACT1.data.py")
# The reference reel that 1.9M people watched is silent 11% of the time with a
# longest gap of 1.7s. We hold ourselves tighter because our shots are shorter.
MAX_SILENT_RATIO = 0.35
MAX_SILENT_RUN = 1.2


def sh(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stderr + \
           subprocess.run(cmd, capture_output=True, text=True).stdout


def expected(data_path: Path) -> dict[int, int]:
    spec = importlib.util.spec_from_file_location("sheetdata", data_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {s[0]: s[1] for s in mod.SHOTS}


def probe_duration(f: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def mean_db(f: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af",
                        "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", r)
    return float(m.group(1)) if m else None


def silence(f: Path, dur: float) -> tuple[float, float]:
    """Return (silent seconds, longest silent run) using ffmpeg's own detector."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af",
                        "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start:\s*(-?[\d.]+)", r)]
    ends = [float(x) for x in re.findall(r"silence_end:\s*([\d.]+)", r)]
    total, longest = 0.0, 0.0
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else dur
        run = max(0.0, e - s)
        total += run
        longest = max(longest, run)
    return total, longest


def contact_sheet(f: Path, dest: Path, dur: float) -> bool:
    """Three frames spread across the clip's OWN length, not a fixed frame number.

    The old version of this check hard-coded frames 0/96/190, which only ever
    made sense for an 8-second clip. Shot lengths now vary 4-10s by design.
    """
    picks = [0.1, dur / 2, max(0.1, dur - 0.3)]
    sel = "+".join(f"between(t\\,{p:.2f}\\,{p + 0.06:.2f})" for p in picks)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(f),
         "-vf", f"select='{sel}',scale=360:-1,tile=3x1", "-frames:v", "1",
         str(dest), "-y"], capture_output=True, text=True)
    return dest.exists() and dest.stat().st_size > 0


def main() -> int:
    clips = Path(sys.argv[1])
    sheets = Path(sys.argv[2])
    data = Path(sys.argv[3]) if len(sys.argv) > 3 else DATA
    sheets.mkdir(parents=True, exist_ok=True)
    want = expected(data)

    print(f"{'SHOT':<5} {'WANT':<5} {'GOT':<6} {'dB':<8} {'SILENT':<8} "
          f"{'LONGEST':<8} {'SHEET':<6} NOTE")
    bad = 0
    for f in sorted(clips.glob("shot-*.mp4")):
        n = int(re.sub(r"\D", "", f.stem))
        dur = probe_duration(f)
        db = mean_db(f)
        sil, longest = silence(f, dur)
        ok_sheet = contact_sheet(f, sheets / f"shot-{n:02d}.jpg", dur)
        w = want.get(n)

        notes = []
        if w and abs(dur - w) > 0.6:
            notes.append(f"DURATION want {w}s")
        if db is None or db < -60:
            notes.append("NO AUDIO")
        ratio = sil / dur if dur else 1.0
        if ratio > MAX_SILENT_RATIO:
            notes.append(f"DEAD AIR {ratio:.0%}")
        if longest > MAX_SILENT_RUN:
            notes.append(f"GAP {longest:.1f}s")
        if not ok_sheet:
            notes.append("NO FRAMES")
        if notes:
            bad += 1

        print(f"{n:<5} {str(w) + 's' if w else '?':<5} {dur:<6.1f} "
              f"{db if db is not None else 'none':<8} {ratio:<8.0%} "
              f"{longest:<8.1f} {'ok' if ok_sheet else 'FAIL':<6} "
              f"{' · '.join(notes)}")

    print(f"\n{bad} of {len(list(clips.glob('shot-*.mp4')))} clips flagged. "
          f"Contact sheets in {sheets}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

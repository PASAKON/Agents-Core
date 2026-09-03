#!/usr/bin/env python3
"""previz-check.py — the Blender-previz acceptance gate (task-0718fc04).

Why this exists
----------------
4 of 33 previz files were rendered at 640x360 while the rest are 720p, and
nobody caught it until it broke three generations of S1C on 2026-09-03 and
cost two operator sessions (each Higgsfield @Video reference below the
output resolution silently fails generation). There was no gate before this
file. It is meant to run BEFORE a previz gets used as a Higgsfield video
reference, not after.

What it checks, mechanically, per docs/PREVIZ-INDEX.md's per-shot spec:
  - resolution is exactly 1280x720
  - frame rate is 24
  - duration/frame-count match the spec for that shot (exact frame count,
    since Blender's animation=True render is frame-perfect)
  - codec is h264, pixel format is yuv420p, and there is no audio stream
  - bitrate sits inside the band the existing 720p previz occupy
    (~80-900 kbps) — this is a FLAG, not a FAIL: it is descriptive of the
    corpus so far, not a hard spec.

It also writes a contact sheet per file (frames sampled at even intervals,
tiled into one PNG) so a human can judge the camera move at a glance without
opening 33 videos.

Usage
-----
    scripts/previz-check.py                      # docs/*-Render*.MP4, table
    scripts/previz-check.py docs/S1C-Render.MP4   # one file
    scripts/previz-check.py --json                # machine-readable
    scripts/previz-check.py --no-contact-sheets    # skip the PNG pass

A file with no matching row in docs/PREVIZ-INDEX.md still runs every other
check; its duration/frame-count are reported as unverified (flagged), not
failed, since there is no spec to fail against — that gap is itself worth
reporting, not silently pass-by-default.

Exit code is 1 if any file FAILs a hard check, 0 otherwise (flags never
affect the exit code).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from fractions import Fraction

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX = os.path.join(REPO_ROOT, "docs", "PREVIZ-INDEX.md")
DEFAULT_GLOB = os.path.join(REPO_ROOT, "docs", "*-Render*.MP4")
DEFAULT_OUT_DIR = os.path.join(REPO_ROOT, "docs", "reports", "previz-contacts")

EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 720
EXPECTED_FPS = 24
EXPECTED_CODEC = "h264"
EXPECTED_PIXFMT = "yuv420p"
BITRATE_MIN_KBPS = 80
BITRATE_MAX_KBPS = 900

# PREVIZ-INDEX.md rows look like: | `S5-Render.MP4` | 20s | off-axis ... |
# A handful of rows name several files at once, e.g. `S12a/b/c-Render.MP4`.
INDEX_ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)s")


def expand_multi(name: str) -> list[str]:
    """`S12a/b/c-Render.MP4` -> [S12a-Render.MP4, S12b-Render.MP4, S12c-Render.MP4]."""
    if "/" not in name:
        return [name]
    segs = name.split("/")
    first, last = segs[0], segs[-1]
    m = re.match(r"^([a-z])(.*)$", last)
    if not m:
        return [name]
    letter_last, suffix = m.groups()
    base, letter_first = first[:-1], first[-1]
    letters = [letter_first] + segs[1:-1] + [letter_last]
    return [f"{base}{letter}{suffix}" for letter in letters]


def parse_index(path: str) -> dict[str, int]:
    """Filename -> expected duration in seconds, from PREVIZ-INDEX.md's table."""
    spec: dict[str, int] = {}
    if not os.path.isfile(path):
        return spec
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = INDEX_ROW_RE.match(line.strip())
            if not m:
                continue
            name, secs = m.group(1), int(m.group(2))
            for fname in expand_multi(name):
                spec[fname] = secs
    return spec


def ffprobe_json(path: str) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or "ffprobe failed")
    return json.loads(r.stdout)


def count_frames(path: str) -> int | None:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    return int(out) if out.isdigit() else None


@dataclass
class CheckResult:
    file: str
    ok: bool = True
    failures: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.failures.append(msg)


def check_file(path: str, spec_seconds: int | None) -> CheckResult:
    res = CheckResult(file=os.path.basename(path))
    try:
        probe = ffprobe_json(path)
    except Exception as e:
        res.fail(f"ffprobe failed: {e}")
        return res

    vstreams = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    astreams = [s for s in probe.get("streams", []) if s.get("codec_type") == "audio"]
    fmt = probe.get("format", {})

    if not vstreams:
        res.fail("no video stream")
        return res
    v = vstreams[0]

    width, height = v.get("width"), v.get("height")
    res.info["width"], res.info["height"] = width, height
    res.info["resolution"] = f"{width}x{height}"
    if (width, height) != (EXPECTED_WIDTH, EXPECTED_HEIGHT):
        res.fail(f"resolution {width}x{height} != {EXPECTED_WIDTH}x{EXPECTED_HEIGHT}")

    try:
        fps = float(Fraction(v.get("r_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    res.info["fps"] = round(fps, 3)
    if abs(fps - EXPECTED_FPS) > 0.01:
        res.fail(f"fps {fps:g} != {EXPECTED_FPS}")

    codec = v.get("codec_name", "?")
    res.info["codec"] = codec
    if codec != EXPECTED_CODEC:
        res.fail(f"codec {codec} != {EXPECTED_CODEC}")

    pixfmt = v.get("pix_fmt", "?")
    res.info["pix_fmt"] = pixfmt
    if pixfmt != EXPECTED_PIXFMT:
        res.fail(f"pix_fmt {pixfmt} != {EXPECTED_PIXFMT}")

    res.info["audio"] = "yes" if astreams else "no"
    if astreams:
        res.fail(f"has audio stream ({len(astreams)})")

    duration = float(fmt.get("duration", 0.0) or 0.0)
    res.info["duration"] = round(duration, 3)
    frames = count_frames(path)
    res.info["frames"] = frames

    if spec_seconds is not None:
        expected_frames = spec_seconds * EXPECTED_FPS
        res.info["spec_seconds"] = spec_seconds
        if frames is None:
            res.fail("could not count frames")
        elif frames != expected_frames:
            res.fail(f"frames {frames} != spec {expected_frames} ({spec_seconds}s @ {EXPECTED_FPS}fps)")
    else:
        res.flags.append("no PREVIZ-INDEX.md spec entry -- duration/frame-count unverified")

    bitrate = fmt.get("bit_rate")
    if bitrate is not None:
        kbps = int(bitrate) / 1000
        res.info["bitrate_kbps"] = round(kbps, 1)
        if not (BITRATE_MIN_KBPS <= kbps <= BITRATE_MAX_KBPS):
            res.flags.append(f"bitrate {kbps:.0f}kbps outside {BITRATE_MIN_KBPS}-{BITRATE_MAX_KBPS}kbps band")
    else:
        res.flags.append("no bitrate reported")

    return res


def make_contact_sheet(path: str, res: CheckResult, out_path: str, n: int = 12) -> str | None:
    duration = res.info.get("duration")
    width, height = res.info.get("width"), res.info.get("height")
    if not duration or duration <= 0 or not width or not height:
        return None
    cols, rows = 4, 3
    tile_w = 320
    tile_h = int(tile_w * height / width)
    tile_h -= tile_h % 2
    fps = n / duration
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = [
        "ffmpeg", "-v", "error", "-y", "-i", path,
        "-vf", f"fps={fps},scale={tile_w}:{tile_h},tile={cols}x{rows}",
        "-frames:v", "1", "-q:v", "3", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return out_path if r.returncode == 0 else None


def print_table(results: list[CheckResult]) -> None:
    cols = ["FILE", "RES", "FPS", "DUR", "FRAMES", "CODEC", "PIXFMT", "AUDIO", "KBPS", "VERDICT", "NOTES"]
    rows = []
    for r in results:
        notes = "; ".join([f"FAIL: {m}" for m in r.failures] + [f"flag: {m}" for m in r.flags])
        rows.append([
            r.file,
            r.info.get("resolution", "?"),
            str(r.info.get("fps", "?")),
            str(r.info.get("duration", "?")),
            str(r.info.get("frames", "?")),
            r.info.get("codec", "?"),
            r.info.get("pix_fmt", "?"),
            r.info.get("audio", "?"),
            str(r.info.get("bitrate_kbps", "?")),
            "PASS" if r.ok else "FAIL",
            notes,
        ])
    widths = [max(len(cols[i]), *(len(row[i]) for row in rows)) if rows else len(cols[i])
              for i in range(len(cols))]
    def fmt_row(vals):
        return "  ".join(v.ljust(w) for v, w in zip(vals[:-1], widths[:-1])) + "  " + vals[-1]
    print(fmt_row(cols))
    print(fmt_row(["-" * w for w in widths[:-1]] + ["-" * 5]))
    for row in rows:
        print(fmt_row(row))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="previz MP4 files to check (default: docs/*-Render*.MP4)")
    ap.add_argument("--index", default=DEFAULT_INDEX, help="path to PREVIZ-INDEX.md")
    ap.add_argument("--glob", default=DEFAULT_GLOB, help="glob used when no files are given")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="where contact sheets land")
    ap.add_argument("--no-contact-sheets", action="store_true", help="skip the contact-sheet PNG pass")
    ap.add_argument("--json", action="store_true", help="machine-readable output instead of a table")
    args = ap.parse_args()

    files = args.files or sorted(glob.glob(args.glob))
    if not files:
        print(f"previz-check: no files matched {args.glob}", file=sys.stderr)
        return 1

    spec = parse_index(args.index)

    results = []
    for path in files:
        name = os.path.basename(path)
        res = check_file(path, spec.get(name))
        if not args.no_contact_sheets and res.info.get("width"):
            sheet = os.path.join(args.out_dir, os.path.splitext(name)[0] + ".contact.png")
            made = make_contact_sheet(path, res, sheet)
            res.info["contact_sheet"] = made or "FAILED"
        results.append(res)

    if args.json:
        print(json.dumps([{
            "file": r.file, "ok": r.ok, "failures": r.failures, "flags": r.flags, **r.info,
        } for r in results], indent=2))
    else:
        print_table(results)
        n_fail = sum(1 for r in results if not r.ok)
        n_flag = sum(1 for r in results if r.flags)
        print(f"\n{len(results)} files, {n_fail} FAIL, {n_flag} flagged, {len(results) - n_fail} PASS")

    return 1 if any(not r.ok for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())

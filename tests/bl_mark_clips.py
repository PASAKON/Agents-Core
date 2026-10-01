"""Synthetic 1080x1920 clips that carry (or do not carry) the BL brand mark and the legal pill, for
tests/test_bl_checker.py and tests/test_bl_merge.py (task-c32c40e8).

Not a test module (no `test_` prefix): pytest puts tests/ on sys.path, so both files `import bl_mark_clips`.

What a clip is: a dark plate at 30 fps. Every frame outside `flat` also carries a busy grid, so the empty-frame gate
sees content there; the frames in `flat` are the bare plate (what an empty KIN entry looks like). Over the plate:
  * the brand mark's neon rule (#FF2D40) at the geometry bl_checker.bug_rule_rect gives, one `drawbox` per segment of
    `segments` = [(first_frame, last_frame, alpha)], alpha 0 = nothing drawn. Default: opaque on every frame;
  * the legal pill, as thin light stripes inside the rect bl_checker.legal_pill_sample_rect reads. Thin on purpose: the
    real pill's grey text on a flat plate leaves the whole-frame std under the empty-frame threshold, and so do these.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

from tools import bl_checker as ck

FPS = 30
BG = "0x0A0C10"
NEON = "0xFF2D40"
PILL = "0xB9C0C6"


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def _in_ranges(ranges) -> str:
    """ffmpeg expression: n is inside any (first, last) range."""
    return "+".join(f"between(n,{a},{b})" for a, b in ranges)


def mark_filters(sides=("right",), segments=None, frames: int = 30) -> list[str]:
    """drawbox filters for the neon rule on each side. `segments` = [(first, last, alpha)]; None = opaque throughout."""
    segments = segments if segments is not None else [(0, frames - 1, 1.0)]
    out = []
    for side in sides:
        x, y, w, h = ck.bug_rule_rect(side)
        for first, last, alpha in segments:
            if alpha <= 0:
                continue
            out.append(f"drawbox=x={math.ceil(x)}:y={math.floor(y)}:w={math.ceil(w)}:h={math.ceil(h)}"
                       f":color={NEON}@{alpha}:t=fill:enable='between(n,{first},{last})'")
    return out


def legal_filters(off=()) -> list[str]:
    """The pill: 2 px light stripes every 16 px across the legal sample rect, absent on the `off` frame ranges."""
    x, y, w, h = ck.legal_pill_sample_rect()
    enable = f":enable='eq(0,{_in_ranges(off)})'" if off else ""
    return [f"drawbox=x={x + k}:y={y}:w=2:h={h}:color={PILL}:t=fill{enable}" for k in range(0, w - 1, 16)]


def marked_clip(path: Path, frames: int = 30, sides=("right",), segments=None, legal: bool = True,
                legal_off=(), flat=()) -> Path:
    """Write the clip (libx264 yuv420p crf 18, like the kit's renders). `flat` = (first, last) frame ranges left as the
    bare plate; `legal=False` leaves the pill out entirely, `legal_off` takes it off those frame ranges."""
    source = f"color=c={BG}:s={ck.CANVAS_W}x{ck.CANVAS_H}:r={FPS}:d={frames / FPS}"
    grid = "drawgrid=w=90:h=90:t=30:c=white@1"
    if flat:
        grid += f":enable='eq(0,{_in_ranges(flat)})'"
    # Drawn in RGB (gbrp): drawbox's alpha is linear in RGB, but in yuv420p it is not -- measured here, @0.9 over a dark
    # plate left the chroma at 98.7% of fully on -- and a fade-in fixture must be a real fade.
    filters = ["format=gbrp", grid] + (legal_filters(legal_off) if legal else []) + mark_filters(sides, segments, frames)
    _run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", source,
          "-vf", ",".join(filters) + ",format=yuv420p", "-frames:v", str(frames),
          "-c:v", "libx264", "-crf", "18", "-preset", "ultrafast", str(path)])
    return path

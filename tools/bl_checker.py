#!/usr/bin/env python3
"""BLACK LIQUIDITY Checker -- judge a rendered cut by machine (task-67bb7a11).

No images loop, no judgment calls at render-review time: given the finished
MP4 and the beats table the Scripter wrote, run four mechanical checks and
exit 1 if any fails.

Usage:
    python3 tools/bl_checker.py --video final.mp4 --beats beats.json \
        [--face-box x,y,w,h]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

CANVAS_W, CANVAS_H = 1080, 1920

# ═══════════════════════════════════════════════════════════════════════════
# 1. Empty frames -- EXACTLY the CTO's detector from
#    worktrees/mooniex-agents__video_editor__task-501f1d89/CTO-FEEDBACK.md
#    (fps=4, 270x480 gray, mask the bug + legal-label zones, std<12).
#    Target per that review: none after the first 0.25s.
# ═══════════════════════════════════════════════════════════════════════════

EMPTY_FRAME_W, EMPTY_FRAME_H, EMPTY_FRAME_FPS = 270, 480, 4
EMPTY_FRAME_STD_THRESHOLD = 12
EMPTY_FRAME_IGNORE_BEFORE = 0.25  # seconds -- an opening black frame is tolerated


def detect_empty_frames(video_path: Path, ignore_before: float = EMPTY_FRAME_IGNORE_BEFORE) -> list[float]:
    import numpy as np

    W, H = EMPTY_FRAME_W, EMPTY_FRAME_H
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video_path),
         "-vf", f"fps={EMPTY_FRAME_FPS},scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    if not raw:
        return []
    a = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    m = np.ones((H, W), bool)
    m[int(H * .12):int(H * .24), int(W * .55):] = False  # brand bug, top-right
    m[int(H * .66):int(H * .74), :] = False               # legal label band
    std = np.array([frame[m].std() for frame in a])
    times = [round(i / EMPTY_FRAME_FPS, 2) for i in range(len(std))]
    return [t for t, s in zip(times, std) if s < EMPTY_FRAME_STD_THRESHOLD and t >= ignore_before]


# ═══════════════════════════════════════════════════════════════════════════
# 2. Safe area -- TASK.md: read SKILL.md §6e for the margins; if it gives
#    none, use top 8%, bottom 20%, sides 5% and say so.
#
#    Checked 2026-09-25: .claude/skills/blackliquidity-cut/SKILL.md §6e
#    ("Brand names and image credits on screen") covers brand spelling +
#    third-party credit wording only -- it states NO pixel margins. The
#    margins in that skill (--safe-left 120px / --safe-top 252px / etc,
#    content ends x=840/y=1500 on a 1080x1920 canvas) live in §6c instead,
#    which is a different rule (the TikTok safe-area for the kit's own text
#    blocks) than what TASK.md asked us to read (§6e). Per TASK.md's own
#    instruction we therefore fall back to its stated default:
# ═══════════════════════════════════════════════════════════════════════════

SAFE_MARGINS = {"top": 0.08, "bottom": 0.20, "left": 0.05, "right": 0.05}


def safe_rect(canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> tuple[float, float, float, float]:
    """(left, top, right, bottom) of the safe rectangle in canvas px."""
    left = canvas_w * SAFE_MARGINS["left"]
    right = canvas_w * (1 - SAFE_MARGINS["right"])
    top = canvas_h * SAFE_MARGINS["top"]
    bottom = canvas_h * (1 - SAFE_MARGINS["bottom"])
    return left, top, right, bottom


# ── image placement -- replicated (read-only reference) from build_cut.py's
#    img_placement()/box_to_canvas() on origin/agent/video_editor-task-501f1d89,
#    prototypes/bl57-cut/build_cut.py. We never edit that file; this is our
#    own copy of the same, small, pure coordinate transform so the checker
#    can interpret a beat's `box` (native still px) against the canvas. ──

def img_placement(extra: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> tuple[int, int, int, int, float]:
    nw = extra.get("native_w", canvas_w)
    nh = extra.get("native_h", canvas_h)
    if nw == canvas_w and nh == canvas_h:
        return canvas_w, canvas_h, 0, 0, 1.0
    if nw == canvas_w:
        return canvas_w, nh, 0, 0, 1.0
    scale = canvas_w / nw
    disp_h = round(nh * scale)
    top = round((canvas_h - disp_h) / 2)
    return canvas_w, disp_h, top, 0, scale


def box_to_canvas(box, place) -> tuple[float, float, float, float] | None:
    if box is None:
        return None
    dw, dh, top, left, scale = place
    x, y, w, h = box
    return (left + x * scale, top + y * scale, w * scale, h * scale)


def rect_within_safe(rect: tuple[float, float, float, float], safe: tuple[float, float, float, float],
                      tol: float = 0.5) -> bool:
    x, y, w, h = rect
    L, T, R, B = safe
    return x >= L - tol and y >= T - tol and x + w <= R + tol and y + h <= B + tol


def check_out_of_safe_area(beats: list[dict]) -> list[str]:
    """Beats with an evidence `box` (COMP/EVID) whose canvas-placed box lands
    outside the safe rectangle -- likely cropped by TikTok's own UI chrome."""
    safe = safe_rect()
    bad = []
    for b in beats:
        if b.get("mode") not in ("COMP", "EVID"):
            continue
        extra = b.get("extra") or {}
        box = extra.get("box")
        if not box:
            continue
        canvas_box = box_to_canvas(box, img_placement(extra))
        if not rect_within_safe(canvas_box, safe):
            bad.append(b["tag"])
    return bad


CREDIT_CHIP_MIN_CLEARANCE = 40  # px of vertical room the credit chip needs above the evidence


def check_credit_missing(beats: list[dict]) -> list[str]:
    """A beat's `credit` (SKILL.md §6e: sits ON the image plate, in its own
    top-left corner, above the evidence box) needs clear vertical room
    between the safe area's top margin and where the evidence itself starts
    -- otherwise the credit chip has nowhere to sit without either falling
    in TikTok's own unsafe top band or overlapping the evidence it credits.
    Every beat's plate spans the full canvas width by construction (see
    img_placement -- left is always 0), so a left-margin check on the raw
    plate corner would flag every credit unconditionally; checking the
    vertical gap above the evidence is the geometry that actually varies."""
    safe = safe_rect()
    _, safe_top, _, _ = safe
    bad = []
    for b in beats:
        extra = b.get("extra") or {}
        credit = extra.get("credit")
        if not credit:
            continue
        place = img_placement(extra)
        _, _, top, _, _ = place
        box = extra.get("box")
        if box:
            canvas_box = box_to_canvas(box, place)
            content_top = canvas_box[1]
        else:
            content_top = top
        if content_top - safe_top < CREDIT_CHIP_MIN_CLEARANCE:
            bad.append(b["tag"])
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# 3. Text over face -- a caption/kinetic slot intersecting --face-box on
#    FF/COMP beats. beats.json carries no rendered caption position (that's
#    the HyperFrames generator's job downstream), so this is a documented
#    approximation of where the kit conventionally puts the spoken-caption
#    chip (SKILL.md §6d): "chest height" in full-frame, "~37-40% of the
#    height, just above the head" when composited. No --face-box -> skipped.
# ═══════════════════════════════════════════════════════════════════════════

def caption_band(mode: str, canvas_h: int = CANVAS_H) -> tuple[float, float] | None:
    if mode == "FF":
        return 0.62 * canvas_h, 0.72 * canvas_h
    if mode == "COMP":
        return 0.37 * canvas_h, 0.42 * canvas_h
    return None


def check_text_over_face(beats: list[dict], face_box: tuple[float, float, float, float] | None) -> list[str]:
    if face_box is None:
        return []
    fx, fy, fw, fh = face_box
    bad = []
    for b in beats:
        if b.get("mode") not in ("FF", "COMP"):
            continue
        if not (b.get("extra") or {}).get("cap"):
            continue
        band = caption_band(b["mode"])
        if band is None:
            continue
        y0, y1 = band
        if y1 >= fy and y0 <= fy + fh:
            bad.append(b["tag"])
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

def run_checker(video_path: Path, beats: list[dict], face_box: tuple[float, float, float, float] | None = None) -> dict:
    empty = detect_empty_frames(video_path)
    unsafe = check_out_of_safe_area(beats)
    text_over = check_text_over_face(beats, face_box)
    credit_bad = check_credit_missing(beats)
    return {
        "pass": not (empty or unsafe or text_over or credit_bad),
        "empty_frames": empty,
        "out_of_safe_area": unsafe,
        "text_over_face": text_over,
        "credit_missing": credit_bad,
    }


def parse_box(s: str | None) -> tuple[float, float, float, float] | None:
    if not s:
        return None
    x, y, w, h = (float(v) for v in s.split(","))
    return x, y, w, h


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video", required=True)
    ap.add_argument("--beats", required=True)
    ap.add_argument("--face-box", default=None, help="x,y,w,h in canvas px")
    ap.add_argument("--out", default=None, help="write the result JSON here too")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    beats = json.loads(Path(args.beats).read_text(encoding="utf-8"))
    result = run_checker(Path(args.video), beats, parse_box(args.face_box))
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

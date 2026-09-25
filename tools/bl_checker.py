#!/usr/bin/env python3
"""BLACK LIQUIDITY Checker -- judge a rendered cut by machine (task-67bb7a11).

No images loop, no judgment calls at render-review time: given the finished
MP4 and the beats table the Scripter wrote, run six mechanical checks and
exit 1 if any fails.

Usage:
    python3 tools/bl_checker.py --video final.mp4 --beats beats.json \
        [--face-box x,y,w,h] [--composition cut/index.html]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any

CANVAS_W, CANVAS_H = 1080, 1920

# ═══════════════════════════════════════════════════════════════════════════
# 1. Empty frames -- the CTO's original detector from
#    worktrees/mooniex-agents__video_editor__task-501f1d89/CTO-FEEDBACK.md
#    (fps=4, 270x480 gray, mask the bug + legal-label zones, std<12), UPGRADED
#    2026-09-25 (task-1678d38e, blackliquidity-cut SKILL.md field note
#    "2026-09-25 [MISSING] §gate"): that 4fps grid samples every 0.25s, so a
#    single dropped/black frame (1/30s = 0.033s) only gets caught if it
#    happens to land on a sampled instant -- it missed exactly this at
#    EP57 76.37s (whole-frame mean 13 vs 147 on both neighbouring frames).
#    Now sampled at the render's real 30fps, plus a per-frame MEAN dip check
#    that catches a single dark frame between two normal ones even when its
#    own std is high (a dark but non-uniform frame would slip the std<12
#    test alone). Target per the CTO review: none after the first 0.25s.
# ═══════════════════════════════════════════════════════════════════════════

EMPTY_FRAME_W, EMPTY_FRAME_H, EMPTY_FRAME_FPS = 270, 480, 30
EMPTY_FRAME_STD_THRESHOLD = 12
EMPTY_FRAME_IGNORE_BEFORE = 0.25  # seconds -- an opening black frame is tolerated

# Single-frame dip: a frame whose whole-frame mean drops well below BOTH its
# immediate neighbours, even if the frame itself isn't perfectly flat (so a
# std<12 check alone can miss it). EP57 76.37s measured mean 13 vs 147/147 --
# ratio ~0.09, gap ~134. These thresholds catch that with wide margin while
# leaving ordinary cut-to-cut brightness changes (a bright plate following a
# dark one) alone, because a real cut only differs from ONE neighbour, not
# both -- a dip is dark on both sides.
DIP_MIN_GAP = 40          # neighbour mean must exceed this frame's mean by >= this many levels (0-255)
DIP_MAX_RATIO = 0.5       # and this frame's mean must be <= this fraction of the DARKER neighbour's mean


def _frame_stats(video_path: Path, fps: int, w: int, h: int) -> tuple["np.ndarray", "np.ndarray"] | None:
    """(means, stds) per sampled frame, each masked to exclude the standing
    brand-bug and legal-label zones (they are never empty, so including them
    would hide a genuinely empty frame behind their own contrast)."""
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video_path),
         "-vf", f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    if not raw:
        return None
    a = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    m = np.ones((h, w), bool)
    m[int(h * .12):int(h * .24), int(w * .55):] = False  # brand bug, top-right
    m[int(h * .66):int(h * .74), :] = False               # legal label band
    means = np.array([frame[m].mean() for frame in a])
    stds = np.array([frame[m].std() for frame in a])
    return means, stds


def detect_empty_frames(video_path: Path, ignore_before: float = EMPTY_FRAME_IGNORE_BEFORE,
                         fps: int = EMPTY_FRAME_FPS) -> list[float]:
    stats = _frame_stats(video_path, fps, EMPTY_FRAME_W, EMPTY_FRAME_H)
    if stats is None:
        return []
    means, stds = stats
    times = [round(i / fps, 3) for i in range(len(stds))]

    flagged: set[float] = set()

    # flat/dark stretch (std<12 over the masked frame) -- catches a held
    # black/empty plate of any length.
    for t, s in zip(times, stds):
        if t >= ignore_before and s < EMPTY_FRAME_STD_THRESHOLD:
            flagged.add(t)

    # single-frame dip -- dark on BOTH sides, regardless of its own std, so a
    # one-frame drop between two busy (high-std) frames is still caught.
    for i in range(1, len(means) - 1):
        if times[i] < ignore_before:
            continue
        left, cur, right = means[i - 1], means[i], means[i + 1]
        darker_neighbour = min(left, right)
        if darker_neighbour - cur >= DIP_MIN_GAP and (darker_neighbour <= 0 or cur <= darker_neighbour * DIP_MAX_RATIO):
            flagged.add(times[i])

    return sorted(flagged)


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
#    approximation of where the caption band actually sits.
#
#    UPDATED 2026-09-25 (task-1678d38e): SKILL.md §6d's old per-mode chip
#    position ("chest height" in full-frame, "~37-40% of the height, just
#    above the head" when composited) is [SUPERSEDED] -- the CEO rejected
#    that three-look caption scheme (see SKILL.md §6d and §6f). The template's
#    single `caption()` generator now puts every caption at the SAME fixed
#    band regardless of mode (EP55's `.caplayer { top: 1300px }`, a
#    single/double line of 48px/600 text plus its 20px band padding spans
#    roughly y 1210-1390 on the 1920 canvas). That range is numerically the
#    same as the old FF-only band below, so the FF numbers are kept and now
#    apply to every mode with a caption, not just FF.
# ═══════════════════════════════════════════════════════════════════════════

def caption_band(mode: str, canvas_h: int = CANVAS_H) -> tuple[float, float] | None:
    if mode in ("FF", "COMP"):
        return 0.62 * canvas_h, 0.72 * canvas_h
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
# 4. One caption style per episode -- CEO 2026-09-25: EP57 shipped three
#    different caption looks (a 38px chip that changed height every line, a
#    flat full-width strip, and plain outlined text with no backing at all)
#    because its generator (`assemble.py`'s `addCap`, on
#    origin/agent/video_editor-task-501f1d89) branched its visual treatment
#    on a `kind` argument ("chip-ff" / "chip-comp" / "rail"). The template's
#    fix (SKILL.md §6f) is a single `caption(at, out, text)` generator with
#    no such branch -- a compliant composition's script only ever calls it
#    one way, so it can only ever produce one caption look.
#
#    Detector: read the distinct "style signatures" a composition's
#    <script> actually uses for its captions --
#      1. any `addCap(..., "<kind>", ...)` calls (the old, now-forbidden
#         shape) -- one signature per distinct `kind` literal;
#      2. else, if the new `caption(...)` generator is called at all, that
#         is one signature ("caption") regardless of call count -- it has
#         no style parameter to vary;
#      3. else, a hand-rolled `class="cap..."` div with its own inline
#         `style="..."` -- one signature per distinct inline style string
#         (covers a composition that bypasses both generators).
#    More than one distinct signature -- fail.
# ═══════════════════════════════════════════════════════════════════════════

_ADDCAP_KIND_RE = re.compile(
    r'addCap\(\s*[-\d.]+\s*,\s*[-\d.]+\s*,\s*"(?:[^"\\]|\\.)*"\s*,\s*"([a-zA-Z0-9_-]+)"')
_CAPTION_CALL_RE = re.compile(r'(?<![A-Za-z0-9_])caption\(')
_CAP_CLASS_STYLE_RE = re.compile(r'class="cap[^"]*"[^>]*?style="([^"]*)"')


def caption_style_signatures(html_text: str) -> set[str]:
    kinds = set(_ADDCAP_KIND_RE.findall(html_text))
    if kinds:
        return kinds
    if _CAPTION_CALL_RE.search(html_text):
        return {"caption"}
    return set(_CAP_CLASS_STYLE_RE.findall(html_text))


def check_one_caption_style(html_text: str | None) -> list[str]:
    """Returns the extra (2nd, 3rd, ...) style signatures found beyond the
    first -- empty means the composition passes (0 or 1 distinct style)."""
    if not html_text:
        return []
    styles = sorted(caption_style_signatures(html_text))
    return styles[1:] if len(styles) > 1 else []


# ═══════════════════════════════════════════════════════════════════════════
# 5. Kinetic text overflow -- task-9a4f1029: task-1a5eb073's Arm 1 pilot fed
#    kinetic() whole, unsplit sentences (one long string per `lines[]`
#    entry, instead of several short ones) and the render's Chrome wrapped
#    them wherever it ran out of room -- mid-word, no ICU Thai dictionary
#    (SKILL.md §6b) -- e.g. "วิกิ"/"เอฟเอ็กซ์" split across a line break at
#    56s, "เช็"/"ก" at 67s. index.html's kinetic() now forces nowrap and
#    shrinks to fit at render time (see its own comment); this gate catches
#    the same defect earlier, straight from the composed HTML's own
#    kinetic() calls, so a bad beats.json never even reaches a render.
#
#    Width is an ESTIMATE (character count * a measured px/char ratio), not
#    a real browser layout -- calibrated off two independent single-font
#    samples pulled from final-arm1.mp4 itself (Kanit ExtraBold 800, 82px,
#    ffmpeg frame grabs measured with PIL):
#      "สรุปแบบไม่โลกสวย" (14 visual chars, one line, no wrap) -> 660px
#      "เช็กต่อว่ามีใบ" / "อนุญาตซื้อขาย" / "ฟอเร็กซ์ไหม" (10/10/9 visual
#        chars -- the SAME sentence Chrome itself wrapped, three lines) ->
#        445/510/411px
#    -> 44.5-51.0 px/visual-char at 82px (mean ~47.1). KINETIC_CHAR_WIDTH_
#    RATIO below (0.58, i.e. ~47.6px @82px) sits a hair over that mean, so
#    the estimate over-calls a close line rather than under-calling a real
#    one -- a false alarm here just fails a check; a miss would ship a
#    defect. "Visual" chars exclude Unicode category Mn (Thai vowel/tone
#    marks such as ั ิ ี ึ ื ุ ู ่ ้ ๊ ๋ ์, which stack on the preceding
#    consonant and add no horizontal advance) -- both calibration samples
#    matched this exactly (16 codepoints -> 14 visual, etc).
# ═══════════════════════════════════════════════════════════════════════════

KINETIC_FONT_PX = {"bl-xl": 104, "bl-lg": 82, "bl-md": 62, "bl-sm": 44, "bl-xs": 34}
KINETIC_CHAR_WIDTH_RATIO = 0.58  # px of width per px of font-size, per visual char
KINETIC_SAFE_WIDTH = CANVAS_W - 120 - 240  # kinetic()'s block() never applies .wide -- index.html's --safe-left/--safe-right

_KINETIC_CALL_RE = re.compile(
    r'kinetic\(\s*[-\d.]+\s*,\s*[-\d.]+\s*,\s*[-\d.]+\s*,\s*\[(.*?)\]\s*,\s*[-\d.]+\s*\)\s*;'
    r'(?:[ \t]*//[ \t]*([^\r\n]*))?',
    re.DOTALL)
_KINETIC_ENTRY_RE = re.compile(r'\{c:"([a-zA-Z0-9_ -]*)"\s*,\s*h:("(?:[^"\\]|\\.)*")')
_HTML_TAG_RE = re.compile(r'<[^>]+>')


def _visual_len(text: str) -> int:
    """Spacing characters only -- see this section's own header comment."""
    return sum(1 for ch in text if unicodedata.category(ch) != "Mn")


def estimate_kinetic_line_width(html_fragment: str, css_class: str) -> int:
    plain = _HTML_TAG_RE.sub("", html_fragment)
    font_px = KINETIC_FONT_PX.get(css_class, KINETIC_FONT_PX["bl-lg"])
    return round(_visual_len(plain) * KINETIC_CHAR_WIDTH_RATIO * font_px)


def check_kinetic_overflow(html_text: str | None) -> list[str]:
    """Every kinetic() line whose estimated width exceeds the safe box --
    each entry identified by the beat's own tag when bl_compose.py's
    trailing `// TAG` comment is present (task-9a4f1029), else by its own
    (truncated) text. Empty means every kinetic line estimates as fitting
    on one line at its own font-size or smaller (down to no floor here --
    the render-time shrink-then-throw in kinetic() itself is the real
    floor; this gate only estimates the UNSHRUNK, as-authored width, since
    a beats.json author should split a too-long line rather than lean on
    the render-time shrink)."""
    if not html_text:
        return []
    bad: list[str] = []
    for call in _KINETIC_CALL_RE.finditer(html_text):
        lines_blob, tag_comment = call.group(1), call.group(2)
        label = (tag_comment or "").strip()
        for entry in _KINETIC_ENTRY_RE.finditer(lines_blob):
            css_class, h_json = entry.group(1), entry.group(2)
            text = json.loads(h_json)
            width = estimate_kinetic_line_width(text, css_class)
            if width > KINETIC_SAFE_WIDTH:
                plain = _HTML_TAG_RE.sub("", text)
                ident = label or plain[:24]
                bad.append(f"{ident}: ~{width}px > {KINETIC_SAFE_WIDTH}px safe width ({plain[:40]!r})")
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

def run_checker(video_path: Path, beats: list[dict], face_box: tuple[float, float, float, float] | None = None,
                 composition_html: str | None = None) -> dict:
    empty = detect_empty_frames(video_path)
    unsafe = check_out_of_safe_area(beats)
    text_over = check_text_over_face(beats, face_box)
    credit_bad = check_credit_missing(beats)
    caption_styles_bad = check_one_caption_style(composition_html)
    kinetic_overflow_bad = check_kinetic_overflow(composition_html)
    return {
        "pass": not (empty or unsafe or text_over or credit_bad or caption_styles_bad or kinetic_overflow_bad),
        "empty_frames": empty,
        "out_of_safe_area": unsafe,
        "text_over_face": text_over,
        "credit_missing": credit_bad,
        "extra_caption_styles": caption_styles_bad,
        "kinetic_overflow": kinetic_overflow_bad,
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
    ap.add_argument("--composition", default=None, help="the composed index.html (for the one-caption-style gate)")
    ap.add_argument("--out", default=None, help="write the result JSON here too")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    beats = json.loads(Path(args.beats).read_text(encoding="utf-8"))
    composition_html = Path(args.composition).read_text(encoding="utf-8") if args.composition else None
    result = run_checker(Path(args.video), beats, parse_box(args.face_box), composition_html)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

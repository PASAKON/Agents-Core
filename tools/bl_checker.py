#!/usr/bin/env python3
"""BLACK LIQUIDITY Checker -- judge a rendered cut by machine (task-67bb7a11).

No images loop, no judgment calls at render-review time: given the finished
MP4 and the beats table the Scripter wrote, run the mechanical checks
(sections 1-9 below) and exit 1 if any fails. The brand mark must be at
least 95% of its steady level on every frame (section 8); empty frames in the
first 4 frames of a KIN entry are excused while the mark and the legal pill are
on screen (section 9).

beats.json is either a bare list of beats (arm B, the look every episode so
far has) or `{"headline": {...}, "beats": [...]}` (arm A, the headline-plate
look, task-406c21f3). For arm A this module also owns the schema
(split_beats_doc / parse_headline) and the plate's geometry (headline_layout,
bug_zone) -- bl_compose.py imports them, so the plate it places and the
plate this checker judges are one rectangle. Section 7 below.

Usage:
    python3 tools/bl_checker.py --video final.mp4 --beats beats.json \
        [--face-box x,y,w,h] [--composition cut/index.html]
"""
from __future__ import annotations

import argparse
import json
import math
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
#    2026-09-25 (task-1678d38e, CMO_Procedure_BlackLiquidity_Cut SKILL.md field note
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


def _mask_canvas_rect(m: "np.ndarray", rect: tuple[float, float, float, float], w: int, h: int) -> None:
    """Blank a canvas-px rect (x, y, w, h) out of a (h, w) frame mask, rounding outward so a sliver of the
    standing element never leaks into the statistics."""
    import math
    x, y, rw, rh = rect
    m[max(0, math.floor(y / CANVAS_H * h)):math.ceil((y + rh) / CANVAS_H * h),
      max(0, math.floor(x / CANVAS_W * w)):math.ceil((x + rw) / CANVAS_W * w)] = False


def _frame_stats(video_path: Path, fps: int, w: int, h: int, bug_side: str = "right",
                 extra_zones: tuple = ()) -> tuple["np.ndarray", "np.ndarray"] | None:
    """(means, stds) per sampled frame, each masked to exclude the standing
    brand-bug and legal-label zones (they are never empty, so including them
    would hide a genuinely empty frame behind their own contrast).

    Arm A (task-406c21f3): `bug_side="left"` masks the top-left bug zone
    instead of the top-right one, and `extra_zones` (canvas-px rects) masks the
    headline plate, which is standing text on every frame for the same reason.
    Left at the defaults this is exactly the arm-B mask."""
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
    if bug_side == "left":
        _mask_canvas_rect(m, bug_zone("left"), w, h)      # brand bug, top-left (arm A)
    else:
        m[int(h * .12):int(h * .24), int(w * .55):] = False  # brand bug, top-right
    for zone in extra_zones:
        _mask_canvas_rect(m, zone, w, h)
    m[int(h * .66):int(h * .74), :] = False               # legal label band
    means = np.array([frame[m].mean() for frame in a])
    stds = np.array([frame[m].std() for frame in a])
    return means, stds


def detect_empty_frames(video_path: Path, ignore_before: float = EMPTY_FRAME_IGNORE_BEFORE,
                         fps: int = EMPTY_FRAME_FPS, bug_side: str = "right",
                         extra_zones: tuple = ()) -> list[float]:
    if bug_side == "right" and not extra_zones:
        stats = _frame_stats(video_path, fps, EMPTY_FRAME_W, EMPTY_FRAME_H)
    else:
        stats = _frame_stats(video_path, fps, EMPTY_FRAME_W, EMPTY_FRAME_H, bug_side, extra_zones)
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
#    Checked 2026-09-25: .claude/skills/CMO_Procedure_BlackLiquidity_Cut/SKILL.md §6e
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


def placed_box(beat: dict) -> tuple[float, float, float, float] | None:
    """The evidence `box` where it lands on screen. A COMP still is drawn `shift` px higher
    (bl_compose: `top - shift`, spotlight `by -= shift`); EVID never shifts."""
    extra = beat.get("extra") or {}
    box = box_to_canvas(extra.get("box"), img_placement(extra))
    if box is None:
        return None
    if beat.get("mode") == "COMP":
        x, y, w, h = box
        return (x, y - extra.get("shift", 0), w, h)
    return box


def check_out_of_safe_area(beats: list[dict]) -> list[str]:
    """Beats with an evidence `box` (COMP/EVID) whose canvas-placed box lands
    outside the safe rectangle -- likely cropped by TikTok's own UI chrome."""
    safe = safe_rect()
    bad = []
    for b in beats:
        if b.get("mode") not in ("COMP", "EVID"):
            continue
        canvas_box = placed_box(b)
        if canvas_box is None:
            continue
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


def check_text_over_face(beats: list[dict], face_box: tuple[float, float, float, float] | None,
                          headline: dict | None = None) -> list[str]:
    """Arm A (`headline` given): the plate is text on every frame, so every FF/COMP beat -- the ones with a face in
    them -- is also flagged when the plate's text rectangle meets the face box, caption or not."""
    if face_box is None:
        return []
    fx, fy, fw, fh = face_box
    plate_hits_face = headline is not None and _rects_overlap(headline_layout(headline)["text"], face_box)
    bad = []
    for b in beats:
        if b.get("mode") not in ("FF", "COMP"):
            continue
        if plate_hits_face:
            bad.append(b["tag"])
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
# 7. Arm A -- the headline plate (task-406c21f3, CMO ruling 2026-10-01).
#
#    Arm A is the Feb-2026 viral look (docs/research/2026-10-01-bl-viral-
#    anatomy-and-ab-week.md §5, §9): BL logo + date stamp top-left, a two-line
#    headline under it with one word red, on screen from frame 0 for the whole
#    clip, a topical real image behind the avatar at 0 / 1 / 2 s. Arm B is
#    today's look and stays a bare list of beats.
#
#    beats.json for arm A:
#      {"headline": {"lines": ["<line 1>", "<line 2>"],      # each <= 30 characters
#                    "red": "<substring>",                   # occurs exactly once across both lines
#                    "bug_side": "left",                     # "left" for arm A; default "right" (today)
#                    "backdrop": [{"t0": 0.0, "src": "real/a.png"},
#                                 {"t0": 1.0, "src": "real/b.png"},
#                                 {"t0": 2.0, "src": "real/c.png"}]},
#       "beats": [ ...the same beats an arm-B list holds... ]}
#
#    Characters are counted by `_visual_len` (section 5): spacing characters
#    only, Unicode Mn (Thai vowel and tone marks) excluded -- the same count
#    the kinetic-overflow gate uses, so one line of "30" means the same width
#    in both places.
#
#    `red` is an exact substring, not the CMO's "red_word index": Thai has no
#    spaces, so a word index is undefined.
#
#    Geometry is one source: bl_compose places the plate and the left bug with
#    these numbers and this checker judges the same rectangles.
# ═══════════════════════════════════════════════════════════════════════════

class ArmAError(ValueError):
    """An arm-A beats.json, or a use of it, the tools refuse. bl_compose and bl_checker print it and exit 2."""


HEADLINE_LINES = 2
HEADLINE_MAX_CHARS = 30
HEADLINE_KEYS = ("lines", "red", "bug_side", "backdrop")
BUG_SIDES = ("left", "right")
BACKDROP_T0S = (0.0, 1.0, 2.0)
BACKDROP_PREFIX = "real/"   # a backdrop carries no credit chip, so it may only be a first-party `real/` capture

# Canvas px (1080x1920). The plate spans the same horizontal box a `.blk.wide` block does: the template lets a block
# that ends above y=900 take the right margin back to 120, and this one ends near y=500 -- 120..960, centred on 540.
HEADLINE_BOX_LEFT, HEADLINE_BOX_RIGHT = 120, 960
HEADLINE_TOP = 276                    # 14.4% of the height; the two lines end by ~25.8% (CMO: about 12-26%)
HEADLINE_FONT_MAX = 88                # px, Kanit 800 -- 16 characters or fewer; a 30-character Thai line fits at 48
# Kanit 800 measured in Chromium (the render's engine) on the real template's fonts, task-406c21f3: Thai text 0.553 em
# per spacing character (30-character sample), Latin lowercase 0.539, digits 0.556 -- all under the 0.58 the kinetic
# gate uses -- but Latin CAPITALS 0.688 on average (W, M up to 0.94). A 30-character all-caps line at 0.58 rendered
# 870 px wide in an 840 px box. Capitals are therefore estimated at 0.70 and everything else at KINETIC_CHAR_WIDTH_RATIO.
HEADLINE_UPPER_WIDTH_RATIO = 0.70
HEADLINE_LINE_RATIO = 1.25
# The bug at the top-left: logo + divider + date on one row (the Feb sheets' shape). Origin is where compose pins it;
# the zone is that row padded -- the logo is 60 px high and ~164 wide, the date chip ~150, 14 px gaps.
BUG_LEFT_ORIGIN = (120, 190)
BUG_LEFT_ZONE = (100.0, 176.0, 400.0, 86.0)
BUG_LEFT_GAP = 14                     # px between the row's logo, divider and date chip (bl_compose.apply_arm_a emits it)
BUG_LEFT_RULE_SIZE = (5, 44)          # the divider, arm A (bl_compose.apply_arm_a emits it)
# bl_compose's credit() helper: `left: var(--safe-left); top: 40px`, 22px Kanit, 6px/14px padding.
CREDIT_CHIP_LEFT, CREDIT_CHIP_TOP, CREDIT_CHIP_FONT_PX, CREDIT_CHIP_H = 120, 40, 22, 45


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def parse_headline(raw: Any) -> dict:
    """Validate an arm-A `headline` object and return it normalised (backdrop sorted by t0, bug_side filled in).
    Raises ArmAError with the rule that failed."""
    if not isinstance(raw, dict):
        raise ArmAError("headline must be an object {lines, red, bug_side, backdrop}")
    unknown = sorted(set(raw) - set(HEADLINE_KEYS))
    if unknown:
        raise ArmAError(f"headline has unknown key(s) {unknown}; allowed: {list(HEADLINE_KEYS)}")

    lines = raw.get("lines")
    if not (isinstance(lines, list) and len(lines) == HEADLINE_LINES
            and all(isinstance(l, str) and l.strip() for l in lines)):
        raise ArmAError(f"headline.lines must be exactly {HEADLINE_LINES} non-empty strings, got {lines!r}")
    for n, line in enumerate(lines, 1):
        if any(c in line for c in "\r\n\t"):
            raise ArmAError(f"headline.lines[{n - 1}] holds a line break or tab; each entry is one line: {line!r}")
        count = _visual_len(line)
        if count > HEADLINE_MAX_CHARS:
            raise ArmAError(f"headline line {n} is {count} characters (Thai combining marks not counted, the way "
                            f"bl_checker._visual_len counts); the limit is {HEADLINE_MAX_CHARS}: {line!r}")

    red = raw.get("red")
    if not isinstance(red, str) or not red.strip():
        raise ArmAError('headline.red is required: the exact substring of one line to set in red '
                        '(Thai has no spaces, so it is a substring, not a word index)')
    hits = [(i, j) for i, line in enumerate(lines) for j in range(len(line)) if line.startswith(red, j)]
    if not hits:
        raise ArmAError(f"headline.red {red!r} occurs in neither line {lines!r}")
    if len(hits) > 1:
        raise ArmAError(f"headline.red {red!r} is ambiguous: it occurs {len(hits)} times across the two lines "
                        f"{lines!r}; it must occur exactly once -- lengthen it until it does")
    i, j = hits[0]
    end = j + len(red)
    if unicodedata.category(red[0]) == "Mn" or (end < len(lines[i]) and unicodedata.category(lines[i][end]) == "Mn"):
        raise ArmAError(f"headline.red {red!r} cuts a Thai syllable: a vowel or tone mark would end up outside the "
                        f"red span, away from its consonant. Start and end it on a whole syllable.")

    side = raw.get("bug_side", "right")
    if side not in BUG_SIDES:
        raise ArmAError(f"headline.bug_side must be one of {list(BUG_SIDES)}, got {side!r}")

    backdrop = raw.get("backdrop")
    if not isinstance(backdrop, list) or len(backdrop) != len(BACKDROP_T0S):
        raise ArmAError(f"headline.backdrop must be exactly {len(BACKDROP_T0S)} entries "
                        f'{{"t0", "src"}} at t0 {list(BACKDROP_T0S)}, got {backdrop!r}')
    entries = []
    for e in backdrop:
        if not isinstance(e, dict) or set(e) != {"t0", "src"} or not _is_number(e["t0"]):
            raise ArmAError(f'headline.backdrop entries are {{"t0": <number>, "src": "real/<file>"}}, got {e!r}')
        src = e["src"]
        if (not isinstance(src, str) or not src.startswith(BACKDROP_PREFIX) or len(src) == len(BACKDROP_PREFIX)
                or ".." in src.split("/") or "\\" in src):
            raise ArmAError(f"headline.backdrop src must be a path under media/ starting {BACKDROP_PREFIX!r} "
                            f"(no '..', no absolute path; a backdrop shows no credit chip), got {src!r}")
        entries.append({"t0": float(e["t0"]), "src": src})
    entries.sort(key=lambda e: e["t0"])
    if tuple(e["t0"] for e in entries) != BACKDROP_T0S:
        raise ArmAError(f"headline.backdrop t0 values must be exactly {list(BACKDROP_T0S)}, "
                        f"got {[e['t0'] for e in entries]}")
    return {"lines": list(lines), "red": red, "bug_side": side, "backdrop": entries}


def split_beats_doc(doc: Any) -> tuple[list[dict], dict | None]:
    """beats.json -> (beats, headline). A bare list is arm B (headline None); an object
    {"headline", "beats"} is arm A. Raises ArmAError for anything else."""
    if isinstance(doc, list):
        return doc, None
    if isinstance(doc, dict):
        extra = sorted(set(doc) - {"headline", "beats"})
        if extra or "headline" not in doc or "beats" not in doc or not isinstance(doc["beats"], list):
            raise ArmAError('an arm-A beats.json is exactly {"headline": {...}, "beats": [...]} '
                            f"(keys found: {sorted(doc)})")
        return doc["beats"], parse_headline(doc["headline"])
    raise ArmAError("beats.json must be a list of beats (arm B) or an object {headline, beats} (arm A)")


def _text_width_em(text: str) -> float:
    """Estimated width of `text` in em, Kanit 800: zero for Thai combining marks (they stack on a consonant), 0.70
    for a Latin capital, KINETIC_CHAR_WIDTH_RATIO for every other character -- spaces included, which over-counts."""
    return sum(0.0 if unicodedata.category(c) == "Mn"
               else HEADLINE_UPPER_WIDTH_RATIO if "A" <= c <= "Z" else KINETIC_CHAR_WIDTH_RATIO
               for c in text)


def headline_layout(headline: dict) -> dict:
    """Where the plate sits, in canvas px: `font_px`, `line_h`, `box` (the element compose emits -- full safe width,
    two lines high) and `text` (the estimated extent of the widest line, centred on the box; what the checks
    judge). Width is estimated by _text_width_em, and the font is the largest size, up to HEADLINE_FONT_MAX, at which
    the widest line fits the box -- so a 30-character Thai line comes out at 48 px and a 30-character all-caps Latin
    line at 40."""
    widest = max(_text_width_em(line) for line in headline["lines"])
    box_w = HEADLINE_BOX_RIGHT - HEADLINE_BOX_LEFT
    font = min(HEADLINE_FONT_MAX, int(box_w // widest))
    line_h = round(font * HEADLINE_LINE_RATIO)
    box = (HEADLINE_BOX_LEFT, HEADLINE_TOP, box_w, HEADLINE_LINES * line_h)
    text_w = min(box_w, widest * font)
    text = ((HEADLINE_BOX_LEFT + HEADLINE_BOX_RIGHT - text_w) / 2, HEADLINE_TOP, text_w, box[3])
    return {"font_px": font, "line_h": line_h, "box": box, "text": text}


def arm_mask_kwargs(headline: dict | None) -> dict:
    """The `detect_empty_frames` keywords for an arm: none for arm B, so its call is the one it always was; for arm A
    the left bug zone plus the plate's rectangle, both standing on every frame. Every empty-frame gate that can see an
    arm-A video (run_checker, bl_merge) takes its mask from here."""
    if headline is None:
        return {}
    return {"bug_side": headline["bug_side"], "extra_zones": (headline_layout(headline)["box"],)}


def bug_zone(side: str = "right") -> tuple[float, float, float, float]:
    """The brand bug's zone (x, y, w, h) in canvas px. Right is today's (the mask `_frame_stats` has always used);
    left is arm A's."""
    if side == "left":
        return BUG_LEFT_ZONE
    return (CANVAS_W * .55, CANVAS_H * .12, CANVAS_W * .45, CANVAS_H * .12)


def _rects_overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    """Positive-area overlap of two (x, y, w, h) rects; touching edges do not count."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def check_headline(headline: dict, beats: list[dict]) -> list[str]:
    """Problems with where the plate sits, as stable ids. Empty means it is clear.
      outside_safe_area        the text rect leaves safe_rect()
      overlaps_bug_<side>      it meets the brand bug's zone (bug_side "right" always does -- set "left")
      overlaps_evidence:<tag>  it meets the `box` of a COMP/EVID beat (the content the spotlight points at; a beat
                               with no `box` declares no content area, so there is nothing to meet)
      overlaps_credit:<tag>    it meets the credit chip of a COMP/EVID beat"""
    text = headline_layout(headline)["text"]
    problems = []
    if not rect_within_safe(text, safe_rect()):
        problems.append("outside_safe_area")
    side = headline["bug_side"]
    if _rects_overlap(text, bug_zone(side)):
        problems.append(f"overlaps_bug_{side}")
    for b in beats:
        if b.get("mode") not in ("COMP", "EVID"):
            continue
        extra = b.get("extra") or {}
        if extra.get("box") and _rects_overlap(text, placed_box(b)):
            problems.append(f"overlaps_evidence:{b['tag']}")
        if extra.get("credit"):
            chip_w = _visual_len(extra["credit"]) * KINETIC_CHAR_WIDTH_RATIO * CREDIT_CHIP_FONT_PX + 28
            if _rects_overlap(text, (CREDIT_CHIP_LEFT, CREDIT_CHIP_TOP, chip_w, CREDIT_CHIP_H)):
                problems.append(f"overlaps_credit:{b['tag']}")
    return problems


_HEADLINE_PLATE_RE = re.compile(r'<div id="hl"[^>]*?\bstyle="([^"]*)"')


def check_headline_plate(headline: dict, composition_html: str) -> list[str]:
    """The composed HTML carries the plate where `headline_layout` says (same left/top/width/height/font-size) and,
    for bug_side "left", the compose override that moves the bug. This is what ties the verdict above to what was
    actually rendered: the video itself cannot be read for a headline."""
    layout = headline_layout(headline)
    plates = _HEADLINE_PLATE_RE.findall(composition_html)
    if len(plates) != 1:
        return [f"plate_count={len(plates)}"]
    style = {k.strip(): v.strip() for k, v in (part.split(":", 1) for part in plates[0].split(";") if ":" in part)}
    left, top, width, height = layout["box"]
    want = {"left": f"{left}px", "top": f"{top}px", "width": f"{width}px", "height": f"{height}px",
            "font-size": f"{layout['font_px']}px"}
    problems = [f"plate_{k}={style.get(k)}!={v}" for k, v in want.items() if style.get(k) != v]
    if headline["bug_side"] == "left":
        bug = re.search(r'<style id="arm-a-bug">(.*?)</style>', composition_html, re.S)
        x, y = BUG_LEFT_ORIGIN
        if not bug:
            problems.append("bug_override_missing")
        elif f"left:{x}px" not in bug.group(1) or f"top:{y}px" not in bug.group(1):
            problems.append(f"bug_override_not_at_{x},{y}")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 8. The brand mark is on every frame (task-c32c40e8, CMO ruling 2026-10-01).
#
#    EP58's final blinked its logo + date chip at t=0 and at all 11 window seams: each window replayed the mark's
#    entrance from its own local t=0 (the template's tl.from("#bug", ...)), so the mark was absent for 8 frames and
#    then faded in over ~0.3 s. The empty-frame gate masks the bug zone -- a standing element would otherwise hide an
#    empty frame behind its own contrast -- so it cannot see this. This gate looks at the mark itself.
#
#    What is measured: the mark's neon rule (`.bug .rl`, #FF2D40 -- the logo is a PNG with no flat colour to read, the
#    rule is a solid fill). Per frame, the mean "redness" R - (G+B)/2 of the rule's pixels. Over a black background
#    that level is proportional to the mark's opacity; over any other background it is
#    a*neon + (1-a)*background, so the ratio to the steady level (the clip's 90th percentile) UNDER-states how absent the mark
#    is by (1-a) * redness(background)/redness(neon): exact on dark plates, a little lenient over a red-ish backdrop.
#    A frame whose level is below MARK_MIN_OPACITY of the steady level fails. If the steady level itself is far below
#    what a neon rule reads, the mark is not in the video at all and the gate fails on that, not on a ratio.
#
#    Geometry is the template's own CSS, measured in the render's Chromium (headless shell 152) on the real template:
#      arm B  .bug{right:150px;top:310px} column, gap 10, logo 163.59 x 60, rule 74 x 5   -> rule (856, 380, 74, 5)
#      arm A  bug at BUG_LEFT_ORIGIN, row, gap 14, centred, rule 5 x 44                    -> rule (297.59, 198, 5, 44)
#    The CMO measured arm B at x860-930 y380-385; the sample here is that rule inset by 1 px on every side, whole
#    pixels only, so codec ringing and 4:2:0 chroma bleed from the neighbouring rows never enter the statistic.
# ═══════════════════════════════════════════════════════════════════════════

MARK_MIN_OPACITY = 0.95
MARK_STEADY_PERCENTILE = 90                # the steady level = what the mark reaches; a median would be dragged down by a long fade
BRAND_NEON = (255, 45, 64)                 # template --neon #FF2D40
MARK_STEADY_FLOOR = 0.6                    # steady level below this fraction of the neon's redness = no mark in the video
MARK_SAMPLE_INSET = 1                      # px, each side of the rule
BUG_RIGHT_INSET, BUG_RIGHT_TOP = 150, 310  # template `.bug { right: 150px; top: 310px }`
BUG_LOGO_SIZE = (163.59, 60)               # `.bug .logo { height: 60px }`; the width follows assets/bl-logo.png (measured)
BUG_COLUMN_GAP = 10                        # `.bug { gap: 10px }` (arm B stacks logo, rule, date)
BUG_RIGHT_RULE_SIZE = (74, 5)              # `.bug .rl`


def bug_rule_rect(side: str = "right") -> tuple[float, float, float, float]:
    """The mark's neon rule (x, y, w, h) in canvas px: arm B under the logo, arm A between logo and date."""
    logo_w, logo_h = BUG_LOGO_SIZE
    if side == "left":
        x0, y0 = BUG_LEFT_ORIGIN
        rule_w, rule_h = BUG_LEFT_RULE_SIZE
        return (x0 + logo_w + BUG_LEFT_GAP, y0 + (logo_h - rule_h) / 2, rule_w, rule_h)
    rule_w, rule_h = BUG_RIGHT_RULE_SIZE
    return (CANVAS_W - BUG_RIGHT_INSET - rule_w, BUG_RIGHT_TOP + logo_h + BUG_COLUMN_GAP, rule_w, rule_h)


def mark_sample_rect(side: str = "right") -> tuple[int, int, int, int]:
    """bug_rule_rect inset by MARK_SAMPLE_INSET, whole pixels only (x, y, w, h) -- what the gate reads."""
    x, y, w, h = bug_rule_rect(side)
    x0, x1 = math.ceil(x + MARK_SAMPLE_INSET - 1e-6), math.floor(x + w - MARK_SAMPLE_INSET + 1e-6)
    y0, y1 = math.ceil(y + MARK_SAMPLE_INSET - 1e-6), math.floor(y + h - MARK_SAMPLE_INSET + 1e-6)
    return (x0, y0, x1 - x0, y1 - y0)


def _redness(rgb: tuple[float, float, float]) -> float:
    return rgb[0] - (rgb[1] + rgb[2]) / 2


def _read_crop(video_path: Path, rect: tuple[int, int, int, int], fps: int, gray: bool = False) -> "np.ndarray | None":
    """Every sampled frame's crop of `rect` (canvas px) as (n, h, w, channels) uint8, or None when ffmpeg returned no
    frames. A video that is not 1080x1920 is scaled to it first, so the rect always means canvas pixels."""
    import numpy as np

    x, y, w, h = rect
    fmt, channels = ("gray", 1) if gray else ("rgb24", 3)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video_path),
         "-vf", f"fps={fps},scale={CANVAS_W}:{CANVAS_H},crop={w}:{h}:{x}:{y},format={fmt}", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    if not raw:
        return None
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, channels)


def brand_mark_levels(video_path: Path, bug_side: str = "right", fps: int = EMPTY_FRAME_FPS) -> "np.ndarray | None":
    """The mark's level on every frame: mean redness of the rule's sample. None when the video yields no frames."""
    frames = _read_crop(video_path, mark_sample_rect(bug_side), fps)
    if frames is None:
        return None
    f = frames.astype("float32")
    return (f[..., 0] - (f[..., 1] + f[..., 2]) / 2).mean(axis=(1, 2))


def _mark_ratios(levels: "np.ndarray") -> tuple[float, "np.ndarray | None"]:
    """(steady level, each frame's level / steady). The ratios are None when the steady level is too low for a mark
    to be in the video at all."""
    import numpy as np

    steady = float(np.percentile(levels, MARK_STEADY_PERCENTILE))
    if steady < MARK_STEADY_FLOOR * _redness(BRAND_NEON):
        return steady, None
    return steady, levels / steady


def _ranges(frames: list[int], fps: int) -> list[dict]:
    """Consecutive frame indices -> [{"from": t, "to": t, "frames": n}] (to = the last frame's time)."""
    out: list[dict] = []
    for i in frames:
        if out and i == out[-1]["_last"] + 1:
            out[-1]["_last"] = i
            out[-1]["frames"] += 1
        else:
            out.append({"_first": i, "_last": i, "frames": 1})
    return [{"from": round(r["_first"] / fps, 3), "to": round(r["_last"] / fps, 3), "frames": r["frames"]} for r in out]


def judge_brand_mark(levels: "np.ndarray", bug_side: str = "right", fps: int = EMPTY_FRAME_FPS,
                     min_opacity: float = MARK_MIN_OPACITY) -> dict:
    """The gate's verdict from per-frame levels. `min_ratio` / `min_time` are the worst frame; `failing_times` every
    frame under `min_opacity`; `failing_ranges` the same grouped. `error` = "mark_missing" when no mark is in the video."""
    import numpy as np

    steady, ratios = _mark_ratios(levels)
    verdict = {"ok": True, "side": bug_side, "min_opacity": min_opacity, "steady_level": round(steady, 2),
               "frames": int(len(levels))}
    if ratios is None:
        failing = list(range(len(levels)))
        verdict.update(ok=False, error="mark_missing", expected_level=round(_redness(BRAND_NEON), 2),
                       min_ratio=None, min_time=None)
    else:
        failing = [int(i) for i in np.flatnonzero(ratios < min_opacity)]
        worst = int(np.argmin(ratios))
        verdict.update(ok=not failing, min_ratio=round(float(ratios[worst]), 4), min_time=round(worst / fps, 3))
    verdict.update(failing_frames=len(failing), failing_times=[round(i / fps, 3) for i in failing],
                   failing_ranges=_ranges(failing, fps))
    return verdict


def check_brand_mark(video_path: Path, bug_side: str = "right", fps: int = EMPTY_FRAME_FPS,
                     levels: "np.ndarray | None" = None) -> dict:
    """Fails any frame whose mark level is under MARK_MIN_OPACITY of the clip's steady level, and a video with no mark
    at all. A video that yields no frames cannot be verified and fails with error "no_frames". `levels` lets a caller
    that already read them (run_checker, the KIN grace) skip a second pass over the video."""
    if levels is None:
        levels = brand_mark_levels(video_path, bug_side, fps)
    if levels is None or not len(levels):
        return {"ok": False, "side": bug_side, "min_opacity": MARK_MIN_OPACITY, "error": "no_frames"}
    return judge_brand_mark(levels, bug_side, fps)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Empty frames at a KIN entry: grace (task-c32c40e8, CMO ruling 2026-10-01: ACCEPT).
#
#    The generator starts a KIN beat's text at t0 + 0.10 s (kinetic(760, t0 + 0.05, ...) plus its wipe), so the first
#    3-4 frames of the dark plate carry no text -- EP58 29.667-29.733 (MAIN-1) and 71.567-71.667 (CURIOSITY-5; the
#    brief called it SUMMARY-1, but 71.567 is the 71.57 s t0 of CURIOSITY-5). That is the kit's entrance, not a drop.
#    Up to KIN_ENTRY_GRACE_FRAMES empty frames counted from the beat's t0 are excused, and only a frame on which the
#    brand mark (section 8 -- at least MARK_MIN_OPACITY of steady) and the legal pill are both on screen: a black
#    frame with neither is a real defect. An empty frame on the 5th frame of the entry or later, or at any other beat,
#    is never excused. Both gates that see empty frames and have the beats call this: run_checker and bl_merge.
# ═══════════════════════════════════════════════════════════════════════════

KIN_ENTRY_GRACE_FRAMES = 4
# `.bl-legal { left: 120px; top: 1430px }`: a pill 720 wide that wraps to two lines (measured in Chromium, 80.78 high),
# padding 24 x 8. The sample is the text area inside it.
LEGAL_PILL_RECT = (120, 1430, 720, 81)
LEGAL_PILL_PADDING = (24, 8)
# Standard deviation of the pill's luma. Its grey text (#B9C0C6) on a flat dark plate reads ~40; the same zone with no
# pill is flat, ~0-2. Only ever asked on a frame the empty-frame gate already found flat, so the plate under the pill
# is flat there and the absolute threshold sits well clear of both.
LEGAL_MIN_STD = 15.0


def legal_pill_sample_rect() -> tuple[int, int, int, int]:
    x, y, w, h = LEGAL_PILL_RECT
    px, py = LEGAL_PILL_PADDING
    return (x + px, y + py, w - 2 * px, h - 2 * py)


def legal_pill_present(video_path: Path, fps: int = EMPTY_FRAME_FPS) -> "np.ndarray | None":
    """True on every frame where the legal pill's text is on screen (the sample's luma is not flat). None = no frames."""
    frames = _read_crop(video_path, legal_pill_sample_rect(), fps, gray=True)
    if frames is None:
        return None
    flat = frames.astype("float32").reshape(len(frames), -1)
    return flat.std(axis=1) >= LEGAL_MIN_STD


def kin_entry_frames(beats: list[dict], fps: int = EMPTY_FRAME_FPS,
                     grace: int = KIN_ENTRY_GRACE_FRAMES) -> dict[int, tuple[str, int]]:
    """frame index -> (tag, 1-based frame of the entry) for the first `grace` frames of every KIN beat, counted from
    the frame nearest its t0 (a window's first plate is pulled back to the window start, so the entry can sit a hair
    before t0: EP58 CURIOSITY-5 t0 71.57 enters on frame 2147 = 71.567)."""
    out: dict[int, tuple[str, int]] = {}
    for b in sorted(beats, key=lambda b: b["t0"]):
        if b.get("mode") != "KIN":
            continue
        first = round(b["t0"] * fps)
        for k in range(grace):
            out.setdefault(first + k, (b["tag"], k + 1))
    return out


def excuse_kin_entry(video_path: Path, empty_times: list[float], beats: list[dict], bug_side: str = "right",
                     fps: int = EMPTY_FRAME_FPS, levels: "np.ndarray | None" = None) -> tuple[list[float], list[dict]]:
    """(still_empty, excused) from the empty-frame gate's times. `excused` entries are
    {"t", "beat", "entry_frame"}. With no empty frame inside a KIN entry the video is not read again."""
    entry = kin_entry_frames(beats, fps)
    if not any(round(t * fps) in entry for t in empty_times):
        return list(empty_times), []
    if levels is None:
        levels = brand_mark_levels(video_path, bug_side, fps)
    ratios = None if levels is None or not len(levels) else _mark_ratios(levels)[1]
    legal = legal_pill_present(video_path, fps)
    still_empty: list[float] = []
    excused: list[dict] = []
    for t in empty_times:
        i = round(t * fps)
        hit = entry.get(i)
        on_screen = (hit is not None and ratios is not None and legal is not None
                     and i < len(ratios) and i < len(legal) and ratios[i] >= MARK_MIN_OPACITY and bool(legal[i]))
        if on_screen:
            excused.append({"t": t, "beat": hit[0], "entry_frame": hit[1]})
        else:
            still_empty.append(t)
    return still_empty, excused


# ═══════════════════════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════════════════════

def run_checker(video_path: Path, beats: list[dict], face_box: tuple[float, float, float, float] | None = None,
                 composition_html: str | None = None, headline: dict | None = None) -> dict:
    """`headline` (a parsed arm-A headline) switches on the arm-A mask and the plate checks and adds a "headline"
    key to the verdict, and makes the brand-mark gate read the left bug. `empty_frames` is what is left after the
    KIN-entry grace (section 9); the excused frames are listed under `empty_frames_excused`, and `brand_mark` is
    section 8's verdict."""
    side = headline["bug_side"] if headline is not None else "right"
    mark_levels = brand_mark_levels(video_path, side)
    empty, empty_excused = excuse_kin_entry(
        video_path, detect_empty_frames(video_path, **arm_mask_kwargs(headline)), beats, side, levels=mark_levels)
    brand_mark = check_brand_mark(video_path, side, levels=mark_levels)
    unsafe = check_out_of_safe_area(beats)
    text_over = check_text_over_face(beats, face_box, headline)
    credit_bad = check_credit_missing(beats)
    caption_styles_bad = check_one_caption_style(composition_html)
    kinetic_overflow_bad = check_kinetic_overflow(composition_html)
    headline_bad = []
    if headline is not None:
        headline_bad = check_headline(headline, beats)
        if composition_html:
            headline_bad += check_headline_plate(headline, composition_html)
    result = {
        "pass": not (empty or unsafe or text_over or credit_bad or caption_styles_bad or kinetic_overflow_bad
                      or headline_bad or not brand_mark["ok"]),
        "empty_frames": empty,
        "empty_frames_excused": empty_excused,
        "out_of_safe_area": unsafe,
        "text_over_face": text_over,
        "credit_missing": credit_bad,
        "extra_caption_styles": caption_styles_bad,
        "kinetic_overflow": kinetic_overflow_bad,
        "brand_mark": brand_mark,
    }
    if headline is not None:
        result["headline"] = headline_bad
    return result


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
    try:
        beats, headline = split_beats_doc(json.loads(Path(args.beats).read_text(encoding="utf-8")))
    except ArmAError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    composition_html = Path(args.composition).read_text(encoding="utf-8") if args.composition else None
    result = run_checker(Path(args.video), beats, parse_box(args.face_box), composition_html, headline)
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

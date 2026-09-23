"""Pure functions for jev_edit.py (task-5cfe20b1) — candidate building, slot
mapping, the confidence gate, and SCRIPT.tsv parsing.

No network, no tools.decide import here on purpose: tests/test_jev_edit.py
imports this module alone (importlib.util.spec_from_file_location, same
pattern as tests/test_hook_log_prompt_records.py) and must never reach the
network or a paid API. The CLI (jev_edit.py) is the only thing that calls
tools.decide.decide().
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

# ── canvas + fixed boxes (blackliquidity-cut SKILL.md §6d, edl/SCHEMA.md) ──

CANVAS_W = 1080
CANVAS_H = 1920

# §6d HARD rule / edl/SCHEMA.md "the evidence-box HARD rule": the avatar
# composite's fixed CSS box — bottom-anchored, top y=845 (56% of 1920),
# left x=0, right x=480 (44% — wider than the measured ~37% x-center on
# purpose, "a HARD safety check should err toward catching a real overlap").
AVATAR_BOX = {"x": 0, "y": 845, "w": 480, "h": CANVAS_H - 845}

# blackliquidity-cut SKILL.md §6c TikTok safe area, doubled onto this canvas.
SAFE_TOP = 252
SAFE_BOTTOM = 1500
SAFE_LEFT = 120
SAFE_RIGHT_NARROW = 240  # below the rail (y >= RAIL_Y)
SAFE_RIGHT_WIDE = 120  # above the rail — §6c "wide" rule
RAIL_Y = 900
BAND_HEIGHT = 180

# Clearance kept between a candidate text band and an obstacle box (avatar
# or focus box) or the frame edge. Not a measured constant like AVATAR_BOX —
# a starting value pending eval-set measurement; see RUNLOG.md.
CLEARANCE = 24

SLOT_LABELS = ["A", "B", "C", "D", "E", "F"]

TSV_COLUMNS = ("tag", "spoken", "shot", "beat", "screen")


class ScriptLine:
    """One row of SCRIPT.tsv (tag, spoken, shot, beat, screen — task-80d18826's
    format). `beat` is the writer's own tag if they already set one, else ''."""

    __slots__ = ("tag", "spoken", "shot", "beat", "screen")

    def __init__(self, tag: str, spoken: str, shot: str, beat: str, screen: str):
        self.tag = tag
        self.spoken = spoken
        self.shot = shot
        self.beat = beat
        self.screen = screen

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"ScriptLine(tag={self.tag!r}, beat={self.beat!r})"


def parse_script_tsv(path: Path) -> list[ScriptLine]:
    """Tab-separated, columns in TSV_COLUMNS order (tag, spoken, shot, beat,
    screen). A header row is optional and auto-detected (its own first two
    cells literally read 'tag'/'spoken') — task-80d18826's real
    `bl57-script/SCRIPT.tsv` ships with NO header, straight to data, and
    rows there commonly carry only 4 of the 5 columns (screen omitted when
    there's nothing to show). Missing trailing columns default to ''; a row
    missing `tag` or `spoken` is skipped, not crashed on — a blank trailing
    line in a hand-edited TSV is common."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))

    if rows:
        first = [c.strip().lower() for c in rows[0]]
        if first[:2] == ["tag", "spoken"]:
            rows = rows[1:]

    lines: list[ScriptLine] = []
    for row in rows:
        padded = row + [""] * (len(TSV_COLUMNS) - len(row))
        tag, spoken, shot, beat, screen = (c.strip() for c in padded[:5])
        if not tag or not spoken:
            continue
        lines.append(ScriptLine(tag=tag, spoken=spoken, shot=shot, beat=beat, screen=screen))
    return lines


# ────────────────────────────────────── beat -> avatar mode (SKILL.md §6d) ──

def mode_for_beat(beat: str | None) -> str | None:
    """§6d: full-frame for verdict/emotion/hook/cta lines, composite for
    lines naming something that can be shown. None (unknown/'other') means
    the caller cannot say — treat conservatively as no mode change."""
    if beat == "show":
        return "composite"
    if beat in ("hook", "verdict", "cta"):
        return "full"
    return None


def entry_mode_change(prev_mode: str | None, this_mode: str | None) -> str:
    p = prev_mode or "full"
    t = this_mode or "full"
    return f"{p}_to_{t}"


# ───────────────────────────────────────────────── rectangle geometry ──────

def rect_overlaps(a: dict, b: dict, margin: float = 0.0) -> bool:
    """True if rect `a`, inflated by `margin` on every side, intersects `b`."""
    ax0, ay0 = a["x"] - margin, a["y"] - margin
    ax1, ay1 = a["x"] + a["w"] + margin, a["y"] + a["h"] + margin
    bx0, by0 = b["x"], b["y"]
    bx1, by1 = b["x"] + b["w"], b["y"] + b["h"]
    return not (bx1 <= ax0 or bx0 >= ax1 or by1 <= ay0 or by0 >= ay1)


def text_bands() -> list[dict]:
    """Candidate horizontal text bands tiling the safe area top to bottom,
    each already narrowed/widened by the §6c rail rule. This is the
    'free rectangles for text' candidate pool before avatar/focus filtering."""
    bands = []
    y = SAFE_TOP
    while y + BAND_HEIGHT <= SAFE_BOTTOM:
        wide = y < RAIL_Y
        right_margin = SAFE_RIGHT_WIDE if wide else SAFE_RIGHT_NARROW
        bands.append({
            "x": SAFE_LEFT, "y": y,
            "w": CANVAS_W - SAFE_LEFT - right_margin, "h": BAND_HEIGHT,
        })
        y += BAND_HEIGHT
    return bands


def free_text_rects(
    avatar_box: dict | None, focus_box: dict | None = None, *, avatar_active: bool = True,
) -> list[dict]:
    """Bands that clear the avatar box (when the avatar is on screen this
    line) and the chosen focus box (when one was picked), each with CLEARANCE
    margin — task brief: 'free rectangles for text that avoid the focus box,
    the avatar box and a margin from every edge' (the edge margin is already
    baked into text_bands()'s SAFE_* constants)."""
    out = []
    for band in text_bands():
        if avatar_active and avatar_box and rect_overlaps(band, avatar_box, CLEARANCE):
            continue
        if focus_box and rect_overlaps(band, focus_box, CLEARANCE):
            continue
        out.append(band)
    return out


# ─────────────────────────────────────────── positional-slot candidates ────

def label_candidates(items: list[dict]) -> list[dict]:
    """First 6 items get labels A-F (task brief: 'The options are A…F +
    other, each meaning the candidate labelled A in the state'). Extra
    candidates beyond 6 are dropped — the caller falls to `other`."""
    return [{"label": label, **item} for label, item in zip(SLOT_LABELS, items)]


def resolve_label(labelled: list[dict], choice: str | None) -> dict | None:
    """The candidate Jev picked, or None for 'other'/an unresolved choice."""
    for c in labelled:
        if c.get("label") == choice:
            return c
    return None


# ──────────────────────────────────── DOM boxes from REAL_MANIFEST.json ────

def dom_candidates_for_tag(manifest: list[dict] | None, tag: str) -> list[dict]:
    """REAL_MANIFEST.json entries whose `covers` includes this line's tag,
    exploded to one candidate per `evidence_box` rect, sorted reading order
    (top to bottom, then left to right). The manifest format as
    tools/bl_realfootage.py writes it today carries no `evidence_box` field
    yet (blackliquidity-cut edl/SCHEMA.md) — entries without one simply
    contribute no candidates, same as no manifest at all."""
    if not manifest:
        return []
    out: list[dict] = []
    for entry in manifest:
        covers = entry.get("covers") or []
        if tag not in covers:
            continue
        for i, box in enumerate(entry.get("evidence_box") or []):
            out.append({
                "x": box["x"], "y": box["y"], "w": box["w"], "h": box["h"],
                "source": entry.get("file"), "box_index": i,
            })
    out.sort(key=lambda b: (b["y"], b["x"]))
    return out[:6]


# ───────────────────────────────────────── content words / numbers / brand ─

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d[\d,.]*%?(?![A-Za-z0-9])")
_LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*")


def load_brand_map(path: Path) -> dict[str, str]:
    """brand-display.yaml: spoken (Thai) -> display (English) — the mapping
    blackliquidity-cut SKILL.md §6e uses for on-screen brand spelling.
    Comment lines and non-string entries are skipped harmlessly."""
    import yaml  # local import: only jev_edit.py's CLI path touches disk/yaml

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}


def content_words(spoken: str, brand_map: dict[str, str] | None = None) -> list[dict]:
    """Highlight-word candidates in order of first appearance, deduped, capped
    at 6: brand mentions first (spoken Thai -> display form, §6e), then
    numbers/percentages, then Latin-script tokens (the channel's measured
    highlight targets are exactly this shape — SPREAD, REBATE, Exness, XM,
    GOLD, a percentage). Thai has no word-segmentation library in
    requirements.txt, so free Thai content words are not extracted here."""
    seen: set[str] = set()
    out: list[dict] = []
    for thai, display in (brand_map or {}).items():
        if thai and thai in spoken and display not in seen:
            out.append({"text": display, "kind": "brand"})
            seen.add(display)
    for m in _NUMBER_RE.finditer(spoken):
        val = m.group(0)
        if val not in seen:
            out.append({"text": val, "kind": "number"})
            seen.add(val)
    for m in _LATIN_RE.finditer(spoken):
        val = m.group(0)
        if val not in seen:
            out.append({"text": val, "kind": "word"})
            seen.add(val)
    return out[:6]


# ───────────────────────────────────────────────── confidence + the gate ───

def confidence_of(probs: dict[str, float]) -> float:
    """Decision.probs carries a probability per option (jev's `probabilities`
    dict); tools/decide.py's Decision has no separate .confidence field, so
    the gate value is the winning option's own probability mass."""
    return max(probs.values()) if probs else 0.0


def needs_review(choice: str | None, confidence_value: float, gate: float) -> bool:
    return choice is None or confidence_value < gate


CONFIDENCE_BUCKETS = ((0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 1.0 + 1e-9))


def bucket_confidence(rows: list[tuple[float, bool]]) -> dict[str, dict[str, Any]]:
    """rows: (confidence, correct) pairs. Same bucket edges as jev-ops
    SKILL.md's pooled table (<0.50, 0.50-0.70, 0.70-0.85, >=0.85)."""
    out: dict[str, dict[str, Any]] = {}
    for lo, hi in CONFIDENCE_BUCKETS:
        label = f"{lo:.2f}-{min(hi, 1.0):.2f}" if hi <= 1.0 + 1e-6 else f">={lo:.2f}"
        bucket_rows = [correct for conf, correct in rows if lo <= conf < hi]
        n = len(bucket_rows)
        acc = (sum(1 for c in bucket_rows if c) / n) if n else None
        out[label] = {"n": n, "accuracy": acc}
    return out

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
import hashlib
import json
import re
import statistics
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


def recommend_gate(rows: list[tuple[float, bool]]) -> float | None:
    """The smallest OBSERVED confidence value T such that every case with
    confidence >= T was correct — jev-ops SKILL.md's own methodology ("Gate
    at 0.7 kept 80% of answers and let zero wrong ones through"), but
    derived from this site's actual eval data rather than borrowed as a
    constant. None if no threshold achieves zero wrong answers above it
    (even the single highest-confidence case was wrong)."""
    if not rows:
        return None
    for t in sorted({round(c, 6) for c, _ in rows}):
        kept = [correct for conf, correct in rows if conf >= t]
        if kept and all(kept):
            return t
    return None


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


# ───────────────────── real ground truth: prototypes/bl-ref-census format ──
# task-82380776's groundtruth.tsv (the reference cut, frame-by-frame census)
# is NOT the tag/question/expected/state shape this tool originally guessed
# at before the file existed — it's one row per reference-video timespan:
# t0, t1, text, class, entry_type, focus_device, target, highlighted_word,
# sfx. `class` already uses this site's own vocabulary (hook/show/verdict/
# cta); entry_type/focus_device use the census's own vocabulary and need
# mapping onto this tool's option ids (see the two maps below).

CENSUS_COLUMNS = (
    "t0", "t1", "text", "class", "entry_type", "focus_device", "target",
    "highlighted_word", "sfx",
)

# entry_type "-" means no entry event this line (not applicable, excluded —
# same as jev_edit.py only asking bl.entry when the line index isn't 0).
ENTRY_TYPE_MAP = {"cut": "hard_cut", "shrink": "shrink"}

# Only the census values that are genuinely the same concept as one of
# bl.focus_device's options get mapped. avatar_shrink/avatar_slide/
# plate_dissolve/pop*/scroll are real P2 events but NOT evidence-focus
# devices in this site's sense (they're avatar motion or a different kind
# of pop-in/transition this site was never designed to answer) — mapping
# them to "other" would score "other" as correct ground truth for a
# question this site's vocabulary was never meant to cover, which is a
# different claim than "none of our four devices fit this evidence". Left
# unmapped on purpose; the caller filters these rows out rather than force
# a lossy label.
FOCUS_DEVICE_MAP = {"highlighter_sweep": "highlight_sweep", "pan+zoom": "zoom_only"}


def parse_census_groundtruth(path: Path) -> list[dict[str, str]]:
    """Raw rows from groundtruth.tsv, in file order. Each value is the
    stripped string cell; callers derive per-site expected labels/state."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def census_line_id(row: dict[str, str]) -> str:
    return f"t{row.get('t0', '?')}"


# ═══════════════════════════════════ Jev up-skill scoreboard (task-161643f7) ═
# freeze / final / score / report — the CEO's "tell us how many frames Jev
# helped with, going up or down, every episode" (2026-09-23) plus IRON §57's
# "prove it saved AI tokens" addition. Pure functions only; jev_edit.py's
# CLI does every filesystem/git/decide-ledger read and calls these.

FPS = 30


# ──────────────────────────────────────────────────────── freeze / integrity

def normalize_decision_rows(rows: list[dict]) -> list[list]:
    """Jev's immutable per-row answer — line_id, question, choice,
    confidence — as a plain list (stable JSON ordering) so freezing/scoring
    never depends on dict key order. `final()` adds `final`/`applied_by`/
    `jev_wrong_at_gate` to the SAME rows later; those mutable fields are
    deliberately excluded here so freezing before `final` runs still hashes
    to the same value after it does."""
    return [
        [r.get("line_id"), r.get("question"), r.get("choice"), r.get("confidence")]
        for r in rows
    ]


def sha256_of_rows(rows: list[dict]) -> str:
    blob = json.dumps(normalize_decision_rows(rows), sort_keys=False, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_frozen_stamp(
    decisions_path: str, rows: list[dict], site_yaml_sha: str, frozen_at: str,
) -> dict:
    """The `<decisions>.frozen.json` payload `freeze` writes: timestamp, the
    site YAMLs' git sha, and a sha256 tied to Jev's own answers (never the
    editor's later `final` calls) — "the score is only honest if Jev
    answered before anyone saw the editor's choices" (task brief)."""
    return {
        "frozen_at": frozen_at,
        "decisions_path": str(decisions_path),
        "decisions_sha256": sha256_of_rows(rows),
        "site_yaml_sha": site_yaml_sha,
        "row_count": len(rows),
    }


def frozen_path_for(decisions_path: Path | str) -> Path:
    decisions_path = Path(decisions_path)
    if decisions_path.suffix == ".jsonl":
        return decisions_path.with_suffix(".frozen.json")
    return decisions_path.with_name(decisions_path.name + ".frozen.json")


class FreezeError(Exception):
    """`score` refuses to run — reason is the message."""


def check_frozen(frozen: dict | None, rows: list[dict], current_site_yaml_sha: str) -> None:
    """Raises FreezeError (never returns a bool) when `score` must refuse:
    no `freeze` was ever run, the site YAMLs changed since freeze (Jev's
    criteria are no longer what was actually asked), or Jev's own answers
    in `rows` no longer match what was frozen (the plan was edited after
    Jev saw it, or before the editor did — either way not honest)."""
    if frozen is None:
        raise FreezeError(
            "plan is not frozen — run `freeze <decisions.jsonl>` before `score` "
            "(the score is only honest if Jev answered before anyone saw the "
            "editor's choices)"
        )
    if frozen.get("site_yaml_sha") != current_site_yaml_sha:
        raise FreezeError(
            f"site YAML sha changed since freeze (frozen={frozen.get('site_yaml_sha')!r}, "
            f"now={current_site_yaml_sha!r}) — the bl.*.yaml criteria Jev answered "
            "against are not the ones on disk now; re-run plan+freeze"
        )
    current_hash = sha256_of_rows(rows)
    if frozen.get("decisions_sha256") != current_hash:
        raise FreezeError(
            "decisions.jsonl's Jev answers (line_id/question/choice/confidence) "
            "changed since freeze — the plan was edited after freezing; re-run "
            "plan+freeze before scoring"
        )


# ────────────────────────────────────────── the gate: who decides (SKILL.md) ─
# "Who decides" table, CEO ruling 2026-09-23 (405349d4): Jev's answer is
# applied only at confidence >= 0.95 on a site with a MEASURED safe gate.
# question -> {state_lang: gate|None}. None (as a gate value, not a missing
# key) means "no measured safe gate — the editor decides every time,
# whatever the confidence" (bl.entry, bl.beat[en]). A question absent from
# this table entirely (the four unmeasured sites, SKILL.md rule 3) also has
# no gate, same result via the same lookup.
SAFE_GATES: dict[str, dict[str | None, float | None]] = {
    "bl.beat": {"th": 0.95, "en": None, None: None},
    "bl.entry": {None: None},
}


def safe_gate_for(question: str, state_lang: str | None) -> float | None:
    variants = SAFE_GATES.get(question)
    if not variants:
        return None
    return variants.get(state_lang, variants.get(None))


def final_call_record(
    question: str, state_lang: str | None, jev_choice: str | None,
    confidence: float | None, final_choice: str,
) -> dict:
    """The `applied_by`/`jev_wrong_at_gate` fields `final` writes onto a row.
    `applied_by` is 'jev' only when the gate passed (confidence >= the
    site's measured safe gate) AND the editor's final call matches Jev's
    answer as-is; 'editor' every other time. An editor override of an
    answer that WOULD have auto-applied (gate passed, but the editor picked
    something else) is allowed but flagged `jev_wrong_at_gate` — the safety
    metric that must stay 0."""
    gate = safe_gate_for(question, state_lang)
    gate_passed = gate is not None and confidence is not None and confidence >= gate
    if gate_passed and final_choice == jev_choice:
        return {"applied_by": "jev", "jev_wrong_at_gate": False}
    if gate_passed and final_choice != jev_choice:
        return {"applied_by": "editor", "jev_wrong_at_gate": True}
    return {"applied_by": "editor", "jev_wrong_at_gate": False}


TSV_FINAL_COLUMNS = ("line_id", "question", "choice")


def parse_final_tsv(path: Path) -> list[dict[str, str]]:
    """Bulk `final` input: `line_id  question  choice`, tab-separated,
    optional header (auto-detected the same way as `parse_script_tsv`)."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if rows:
        first = [c.strip().lower() for c in rows[0]]
        if first[:3] == list(TSV_FINAL_COLUMNS):
            rows = rows[1:]
    out = []
    for row in rows:
        if len(row) < 3:
            continue
        line_id, question, choice = (c.strip() for c in row[:3])
        if not line_id or not question:
            continue
        out.append({"line_id": line_id, "question": question, "choice": choice})
    return out


# ─────────────────────────────────────────────────────────── frames + timing

def parse_line_timings(path: Path) -> dict[str, tuple[float, float]]:
    """`tag  t0  t1` TSV, tab-separated, one row per script line's start/end
    time in the episode. **Where the editor gets it:** the episode's TTS
    transcript/word-timing export (the same lipsync render step already
    times each `lipsync_part_*` segment) or a hand-marked pass against the
    finished render — whichever the episode's `blackliquidity-cut` step
    already produces; this tool does not generate timings itself. Header
    optional (auto-detected: first cell reads 'tag'). A malformed t0/t1
    (non-numeric) or a short row is skipped, not crashed on."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if rows and rows[0][:1] and rows[0][0].strip().lower() == "tag":
        rows = rows[1:]
    out: dict[str, tuple[float, float]] = {}
    for row in rows:
        if len(row) < 3:
            continue
        tag = row[0].strip()
        if not tag:
            continue
        try:
            out[tag] = (float(row[1].strip()), float(row[2].strip()))
        except ValueError:
            continue
    return out


def parse_baseline_episodes_tsv(path: Path) -> list[dict]:
    """`episode  task_id  duration_seconds` TSV for the `baseline` command
    (CTO addition 2's BL52-BL55 table). `duration_seconds` may be blank —
    unknown, never guessed at; the caller reports it missing. Header
    optional (first cell 'episode')."""
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if rows and rows[0][:1] and rows[0][0].strip().lower() == "episode":
        rows = rows[1:]
    out = []
    for row in rows:
        if len(row) < 2:
            continue
        episode, task_id = row[0].strip(), row[1].strip()
        if not episode or not task_id:
            continue
        duration = None
        if len(row) >= 3 and row[2].strip():
            try:
                duration = float(row[2].strip())
            except ValueError:
                duration = None
        out.append({"episode": episode, "task_id": task_id, "duration_seconds": duration})
    return out


def video_duration_seconds(timings: dict[str, tuple[float, float]]) -> float:
    return max((t1 for _, t1 in timings.values()), default=0.0)


def jev_beat_frames(
    rows: list[dict], timings: dict[str, tuple[float, float]],
) -> dict[str, Any]:
    """Video time and frames (x30) whose calls Jev made — "the CEO's 'JEV
    ช่วยได้กี่ Frame'" — summed over lines whose `bl.beat` row has
    `applied_by == 'jev'`. A line with no timing entry is skipped and
    listed in `missing_tags`, never guessed at."""
    seconds = 0.0
    frames = 0
    missing: list[str] = []
    for r in rows:
        if r.get("question") != "bl.beat" or r.get("applied_by") != "jev":
            continue
        t = timings.get(r.get("line_id"))
        if t is None:
            missing.append(r.get("line_id"))
            continue
        dur = max(0.0, t[1] - t[0])
        seconds += dur
        frames += round(dur * FPS)
    return {"jev_seconds": seconds, "jev_frames": frames, "missing_tags": missing}


# ─────────────────────────────────────────────────────────── score aggregates

def site_key(question: str, state_lang: str | None) -> str:
    """Display/grouping key for the raw-accuracy learning curve — `bl.beat`
    needs the state variant distinguished (only `th` has a measured gate);
    every other question's key is just itself."""
    if question == "bl.beat" and state_lang:
        return f"{question}[{state_lang}]"
    return question


def applied_summary(rows: list[dict]) -> dict:
    total = len(rows)
    applied = sum(1 for r in rows if r.get("applied_by") == "jev")
    pct = (applied / total * 100.0) if total else 0.0
    return {"decisions_total": total, "jev_applied": applied, "jev_applied_pct": pct}


def raw_accuracy_by_site(rows: list[dict]) -> dict[str, dict[str, Any]]:
    """Jev's answer vs the editor's final call, on every line with both
    present — gated or not (SKILL.md: "That is the only way Jev gets
    better here" — the learning curve), grouped by `site_key`."""
    groups: dict[str, list[bool]] = {}
    for r in rows:
        if r.get("choice") is None or r.get("final") is None:
            continue
        key = site_key(r.get("question"), r.get("state_lang"))
        groups.setdefault(key, []).append(r["choice"] == r["final"])
    out: dict[str, dict[str, Any]] = {}
    for key, vals in groups.items():
        n = len(vals)
        out[key] = {"n": n, "correct": sum(vals), "accuracy": (sum(vals) / n) if n else None}
    return out


def count_jev_wrong_at_gate(rows: list[dict]) -> int:
    return sum(1 for r in rows if r.get("jev_wrong_at_gate"))


def total_usd(rows: list[dict]) -> float:
    return sum(float(r.get("cost_usd") or 0.0) for r in rows)


# ───────────────────────────────────── IRON §57 token proof (CTO-FEEDBACK.md) ─
# "ประหยัด Token ช่วยลดงาน AI ได้จริง พิสูจน์ได้เป็นตัวเลข และปริมาณ" — the
# scoreboard's first job is proving token savings, not just counting
# decisions. Three numbers, three different confidence levels:
#   jev_usd/jev_tokens        EXACT   — this plan's own decide-ledger rows
#   counterfactual_usd/tokens ESTIMATE — what an AI editor call would have
#                                        cost, tools/decide.py's own formula
#   editor_tokens_per_video_min MEASURED — real Claude session transcripts
# Never blend these into one number without saying which is which.

def index_ledger_by_id(ledger_rows: list[dict]) -> dict[str, dict]:
    return {r["ledger_id"]: r for r in ledger_rows if r.get("ledger_id")}


def jev_spend_and_tokens(rows: list[dict], ledger_by_id: dict[str, dict]) -> dict:
    """EXACT spend/tokens for THIS plan only — every row's `ledger_id`
    resolved against the decide ledger, never a whole-month sum (which
    could include other episodes' calls too). `counterfactual_usd` is
    summed only over rows where Jev's answer was actually APPLIED —
    counterfactual savings only mean something for a decision Jev actually
    made, not one the editor made anyway."""
    tokens_in = tokens_out = 0
    usd = 0.0
    counterfactual_usd = 0.0
    missing_ledger_ids: list[str] = []
    for r in rows:
        lid = r.get("ledger_id")
        if not lid:
            continue
        led = ledger_by_id.get(lid)
        if led is None:
            missing_ledger_ids.append(lid)
            continue
        tokens_in += int(led.get("tokens_in") or 0)
        tokens_out += int(led.get("tokens_out") or 0)
        usd += float(led.get("cost_usd") or 0.0)
        if r.get("applied_by") == "jev":
            counterfactual_usd += float(led.get("counterfactual_usd") or 0.0)
    return {
        "jev_tokens": tokens_in + tokens_out,
        "jev_tokens_in": tokens_in,
        "jev_tokens_out": tokens_out,
        "jev_usd": usd,
        "counterfactual_usd": counterfactual_usd,
        "missing_ledger_ids": missing_ledger_ids,
    }


def counterfactual_tokens(cfg: dict, state_chars: int) -> dict:
    """ESTIMATE — the would-have-cost token count `tools/decide.py
    _counterfactual_usd` prices but doesn't store, recomputed here from the
    same formula and the site's own `counterfactual:` yaml block (never
    called on a real ledger row without its matching site cfg)."""
    cf = cfg.get("counterfactual") or {}
    images = cf.get("images", 0)
    tokens_out = cf.get("big_model_tokens_out", 0)
    extra_chars = cf.get("extra_input_chars", 0)
    tokens_in = (state_chars + extra_chars) / 4 + images * 814
    return {"tokens_in": tokens_in, "tokens_out": tokens_out, "tokens_total": tokens_in + tokens_out}


def sum_transcript_usage(usage_lines: list[dict]) -> dict[str, int]:
    """Sum real token usage across a Claude Code session transcript's
    parsed JSONL lines. Each item is `{"message": {"id": ..., "usage":
    {...}}}` (a line with no `message`/`usage` — a user turn, tool result,
    meta line — contributes 0, not an error).

    **Deduped by `message.id`.** Claude Code's transcript log re-writes the
    same assistant message id multiple times (streaming updates / sidechain
    duplicates) with IDENTICAL cumulative `usage` each time — measured on
    task-52c669bb's real 31MB transcript: summing every line double-counted
    (106.2M raw tokens vs 55.5M deduped, 143 of 168 message ids repeated,
    every repeat byte-identical). Keeping the last write per id is a safe
    tie-break if a future transcript ever has a repeat with DIFFERENT
    usage; every repeat observed so far was identical."""
    by_id: dict[str, dict[str, int]] = {}
    unkeyed = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
    for line in usage_lines:
        msg = line.get("message") or {}
        usage = msg.get("usage")
        if not usage:
            continue
        row = {
            "input": int(usage.get("input_tokens") or 0),
            "output": int(usage.get("output_tokens") or 0),
            "cache_read": int(usage.get("cache_read_input_tokens") or 0),
            "cache_creation": int(usage.get("cache_creation_input_tokens") or 0),
        }
        mid = msg.get("id")
        if mid:
            by_id[mid] = row
        else:
            for k in unkeyed:
                unkeyed[k] += row[k]
    totals = dict(unkeyed)
    for row in by_id.values():
        for k in ("input", "output", "cache_read", "cache_creation"):
            totals[k] += row[k]
    totals["total"] = totals["input"] + totals["output"] + totals["cache_read"] + totals["cache_creation"]
    return totals


def tokens_per_video_minute(total_tokens: int | float, video_seconds: float | None) -> float | None:
    if not video_seconds or video_seconds <= 0:
        return None
    return total_tokens / (video_seconds / 60.0)


# ──────────────────────────────────────────────── BASELINE + pass/fail (§57) ─

def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def build_baseline_row(episodes: list[dict]) -> dict:
    """episodes: [{"episode": "BL52", "task_id": "task-b2d369ed",
    "editor_tokens_per_video_min": float|None, "missing": str|None}, ...].
    The median is taken over the episodes with a MEASURED value only — a
    missing transcript or duration is reported, never estimated (CTO
    addition 2: "If a transcript or a duration is missing, say which one;
    never estimate it")."""
    values = [
        e["editor_tokens_per_video_min"] for e in episodes
        if e.get("editor_tokens_per_video_min") is not None
    ]
    return {
        "episode": "BASELINE",
        "kind": "baseline",
        "editor_tokens_per_video_min": median(values),
        "n_measured": len(values),
        "n_total": len(episodes),
        "episodes": episodes,
    }


# jev_wrong_at_gate total at/above this across the 4 evaluated episodes is
# an automatic FAIL, whatever the token trend (SKILL.md "Goal and test").
FAIL_WRONG_AT_GATE_THRESHOLD = 2


def evaluate_hypothesis(episodes: list[dict], baseline_tokens_per_min: float | None) -> dict:
    """The pre-registered pass/fail rule, SKILL.md "Goal and test" / IRON
    §57 (2026-09-23, before any episode result). `episodes` are `score`
    rows in episode order (EP57, EP58, ...); only the last 4 are judged.

    pass: mean(EP59,EP60 editor tokens/min) <= baseline
          AND EP57->EP60 trends down (EP60 < EP57)
          AND jev_wrong_at_gate totals 0 across the four
          AND jev_applied_pct rises EP57->EP60 (EP60 > EP57)
    Once 4 episodes exist the CEO's rule is binary ("then PASS or FAIL") —
    any one of these four conditions failing is a FAIL, with the specific
    reason(s) listed; before 4 episodes it's IN_PROGRESS, never guessed at.
    """
    n = len(episodes)
    if n < 4:
        return {"verdict": "IN_PROGRESS", "n": n, "of": 4, "reasons": [f"{n}/4 episodes scored"]}

    last4 = episodes[-4:]
    tokens = [e.get("editor_tokens_per_video_min") for e in last4]
    applied = [e.get("jev_applied_pct") for e in last4]
    wrong_total = sum(e.get("jev_wrong_at_gate") or 0 for e in last4)

    if baseline_tokens_per_min is None or any(t is None for t in tokens):
        return {
            "verdict": "IN_PROGRESS", "n": n, "of": 4,
            "reasons": ["missing measured editor tokens/min for one or more episodes, or no baseline yet"],
        }

    mean_59_60 = (tokens[2] + tokens[3]) / 2.0
    trending_down = tokens[3] < tokens[0]
    applied_rising = applied[0] is not None and applied[3] is not None and applied[3] > applied[0]

    reasons = []
    if mean_59_60 > baseline_tokens_per_min:
        reasons.append(f"mean(EP59,EP60)={mean_59_60:.0f} tokens/min > baseline={baseline_tokens_per_min:.0f}")
    if wrong_total >= FAIL_WRONG_AT_GATE_THRESHOLD:
        reasons.append(f"jev_wrong_at_gate total={wrong_total} >= {FAIL_WRONG_AT_GATE_THRESHOLD}")
    if not trending_down:
        reasons.append("EP57->EP60 editor tokens/min does not trend down")
    if not applied_rising:
        reasons.append("jev_applied_pct does not rise EP57->EP60")

    return {
        "verdict": "FAIL" if reasons else "PASS",
        "mean_ep59_60": mean_59_60, "baseline": baseline_tokens_per_min,
        "wrong_at_gate_total": wrong_total, "trending_down": trending_down,
        "applied_rising": applied_rising, "reasons": reasons,
    }


# ─────────────────────────────────────────────────────────────── report.md

def format_delta(cur: float | None, prev: float | None, *, fmt: str = "{:.1f}") -> str:
    """'' when either side is missing (no previous episode, or a field
    that episode didn't measure) — never a fabricated 0."""
    if cur is None or prev is None:
        return ""
    diff = cur - prev
    if abs(diff) < 1e-9:
        return "→0"
    arrow = "↑" if diff > 0 else "↓"
    return f"{arrow}{fmt.format(abs(diff))}"


def previous_row(rows: list[dict], index: int) -> dict | None:
    """The row to diff `rows[index]` against — the immediately preceding
    row in file order (so the seeded REF-1300 baseline row naturally serves
    as the first real episode's comparison point; the very first row in the
    whole file has no previous row at all)."""
    return rows[index - 1] if index > 0 else None


def thai_summary_line(row: dict, prev: dict | None) -> str:
    """The CEO's one-line-per-episode summary, IRON §57 shape: applied
    count/%, frames, Jev's exact spend, the editor's measured tokens/min
    with its delta, then the safety count. Any field this row didn't
    measure (kind=eval/baseline rows, or an episode missing --editor-task)
    is left out of the line rather than printed as a fake zero."""
    ep = row.get("episode", "?")
    parts = [ep + ":"]
    total = row.get("decisions_total")
    applied = row.get("jev_applied")
    pct = row.get("jev_applied_pct")
    if total is not None and applied is not None:
        pct_s = f" ({pct:.0f}%)" if pct is not None else ""
        parts.append(f"Jev ตัดสินเอง {applied} จาก {total} จุด{pct_s}")
    secs, frames = row.get("jev_seconds"), row.get("jev_frames")
    if secs is not None and frames is not None:
        parts.append(f"= {secs:.0f} วินาที / {frames} เฟรม")
    jev_usd = row.get("jev_usd")
    if jev_usd is not None:
        parts.append(f"· ใช้ Jev ${jev_usd:.4f}")
    epm = row.get("editor_tokens_per_video_min")
    if epm is not None:
        d = format_delta(epm, prev.get("editor_tokens_per_video_min") if prev else None, fmt="{:.0f}")
        d_s = f" {d} จาก {prev.get('episode')}" if d and prev else ""
        parts.append(f"· editor ใช้ {epm:,.0f} token/นาทีวิดีโอ{d_s}")
    wrong = row.get("jev_wrong_at_gate")
    if wrong is not None:
        parts.append(f"· ผิดตอนมั่นใจ {wrong}")
    return " ".join(parts)


def hypothesis_line(verdict: dict) -> str:
    v = verdict.get("verdict")
    if v == "IN_PROGRESS":
        return f"IN PROGRESS ({verdict.get('n', 0)}/{verdict.get('of', 4)})"
    if v == "PASS":
        return (
            f"PASS — mean(EP59,EP60)={verdict['mean_ep59_60']:.0f} tokens/min "
            f"<= baseline={verdict['baseline']:.0f}, trending down, "
            f"wrong_at_gate={verdict['wrong_at_gate_total']}, applied% rising"
        )
    reasons = "; ".join(verdict.get("reasons") or [])
    return f"FAIL — Jev leaves the BL edit loop ({reasons})"


def render_scoreboard_md(rows: list[dict], verdict: dict | None = None) -> str:
    lines = ["# BLACK LIQUIDITY — Jev Editor Scoreboard", ""]
    lines.append(
        "Auto-generated by `jev_edit.py report` from `scoreboard.jsonl`. "
        "Do not hand-edit — re-run `report` instead."
    )
    lines.append("")
    if verdict is not None:
        lines.append(f"**Hypothesis (IRON §57):** {hypothesis_line(verdict)}")
        lines.append("")

    lines.append("## Episodes")
    lines.append("")
    lines.append(
        "| Episode | Kind | Decisions | Jev applied | Applied % | Δ applied % "
        "| Jev seconds | Jev frames | Δ frames | Wrong@gate | Jev $ | Editor tok/min | Δ tok/min |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, row in enumerate(rows):
        prev = previous_row(rows, i)

        def cell(v, fmt="{}"):
            return fmt.format(v) if v is not None else "—"

        pct_delta = format_delta(row.get("jev_applied_pct"), prev.get("jev_applied_pct") if prev else None)
        frames_delta = format_delta(row.get("jev_frames"), prev.get("jev_frames") if prev else None, fmt="{:.0f}")
        epm_delta = format_delta(
            row.get("editor_tokens_per_video_min"),
            prev.get("editor_tokens_per_video_min") if prev else None, fmt="{:.0f}",
        )
        lines.append(
            "| {ep} | {kind} | {tot} | {app} | {pct} | {pctd} | {sec} | {fr} | {frd} | {wrong} | {usd} | {epm} | {epmd} |".format(
                ep=row.get("episode", "?"), kind=row.get("kind", "cut"),
                tot=cell(row.get("decisions_total")), app=cell(row.get("jev_applied")),
                pct=cell(row.get("jev_applied_pct"), "{:.1f}%"), pctd=pct_delta or "—",
                sec=cell(row.get("jev_seconds"), "{:.0f}"), fr=cell(row.get("jev_frames")),
                frd=frames_delta or "—", wrong=cell(row.get("jev_wrong_at_gate")),
                usd=cell(row.get("jev_usd"), "${:.4f}"),
                epm=cell(row.get("editor_tokens_per_video_min"), "{:,.0f}"), epmd=epm_delta or "—",
            )
        )
    lines.append("")

    baseline_rows = [r for r in rows if r.get("kind") == "baseline"]
    if baseline_rows:
        b = baseline_rows[-1]
        lines.append("## Baseline detail (BL52-BL55, cut without Jev)")
        lines.append("")
        lines.append(
            f"Median over {b.get('n_measured', 0)}/{b.get('n_total', 0)} measured episodes: "
            f"**{cell(b.get('editor_tokens_per_video_min'), '{:,.0f}')} tokens/min**. "
            "A missing transcript or duration is reported below, never estimated."
        )
        lines.append("")
        lines.append("| Episode | Task | Duration (s) | Editor tok/min | Status |")
        lines.append("|---|---|---|---|---|")
        for e in b.get("episodes") or []:
            status = f"MISSING ({e['missing']})" if e.get("missing") else "measured"
            lines.append(
                "| {ep} | {task} | {dur} | {epm} | {status} |".format(
                    ep=e.get("episode", "?"), task=e.get("task_id", "?"),
                    dur=cell(e.get("duration_seconds"), "{:.2f}"),
                    epm=cell(e.get("editor_tokens_per_video_min"), "{:,.0f}"), status=status,
                )
            )
        lines.append("")

    lines.append("## Raw accuracy per site (the learning curve — gated or not)")
    lines.append("")
    sites: list[str] = []
    for row in rows:
        for key in (row.get("jev_raw_accuracy") or {}):
            if key not in sites:
                sites.append(key)
    if sites:
        lines.append("| Episode | " + " | ".join(sites) + " |")
        lines.append("|---|" + "---|" * len(sites))
        for row in rows:
            acc = row.get("jev_raw_accuracy") or {}
            cells = []
            for s in sites:
                v = acc.get(s)
                cells.append(f"{v['accuracy']*100:.1f}% ({v['correct']}/{v['n']})" if v and v.get("accuracy") is not None else "—")
            lines.append(f"| {row.get('episode', '?')} | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Summary for the CEO")
    lines.append("")
    for i, row in enumerate(rows):
        prev = previous_row(rows, i)
        lines.append(f"- {thai_summary_line(row, prev)}")
    lines.append("")

    return "\n".join(lines) + "\n"


# REF-1300 — the reference census eval (task-82380776), not a real cut. Seeds
# the chart with today's honest baseline before the up-skill loop starts.
# Numbers: RUNLOG.md "2026-09-23 23:05" real eval run (--reps 2, real Jev).
REF_1300_ROW: dict[str, Any] = {
    "episode": "REF-1300",
    "kind": "eval",
    "scored_at": "2026-09-23T16:05:00+00:00",
    "decisions_total": None,
    "jev_applied": None,
    "jev_applied_pct": None,
    "jev_seconds": None,
    "jev_frames": None,
    "jev_raw_accuracy": {
        "bl.beat[th]": {"n": 90, "correct": 38, "accuracy": 38 / 90},
        "bl.beat[en]": {"n": 90, "correct": 18, "accuracy": 18 / 90},
        "bl.entry": {"n": 32, "correct": 20, "accuracy": 20 / 32},
    },
    "jev_wrong_at_gate": None,
    "jev_usd": 0.007685,
    "site_yaml_sha": None,
    "editor_tokens_per_video_min": None,
    "note": (
        "reference census eval, not a cut — today's honest baseline before "
        "the up-skill loop starts (bl.beat th 42%, en 20%, entry 62.5%)"
    ),
}

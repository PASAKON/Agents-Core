#!/usr/bin/env python3
"""BLACK LIQUIDITY Scripter -- look once, write the cut table (task-67bb7a11).

Replaces an Editor session that re-reads N images every turn: read the script
+ timings + Jev decisions, extract ONE frame per line (a real still when the
line has one, else the avatar's own face from the matching lipsync part),
make ONE model call with every frame + the line table, and write beats.json
in the same row shape as `prototypes/bl57-cut/build_cut.py`'s BEATS list.

CEO ruling 2026-09-25 (supersedes the original TASK.md deliverable 1):
claude-p ONLY. No anthropic SDK, no API key lookup, no --cap-usd -- the
`claude -p` backend runs on the Max plan, not per-call API billing.

Usage:
    python3 tools/bl_scripter.py --script prototypes/bl57-script/SCRIPT.tsv \
        --timings prototypes/bl-jev-scoreboard/ep57/timings.tsv \
        --jev prototypes/bl-jev-scoreboard/ep57/decisions.jsonl \
        --media-dir ~/MoonieXHQ/Work/task-501f1d89/tmp/cut/media \
        --t-max 30.78 --backend claude-p --out beats.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

CANVAS_W, CANVAS_H = 1080, 1920
MAX_FRAME_W = 882  # task fact: a 1080-wide frame is downscaled by the API to ~882px anyway
MODES = ("FF", "COMP", "EVID", "KIN", "CHECK")
STILL_EXTS = (".png", ".jpg", ".jpeg")

# Sonnet 5 pricing, read 2026-09-25 platform.claude.com/docs/en/about-claude/pricing
# (used only to report an API-equivalent $ for the claude-p run; claude-p itself
# is billed on the Max plan, not per-call).
PRICE_PER_MTOK = {
    "input": 2.00,
    "cache_creation_input_tokens": 2.50,  # 5-min cache write
    "cache_read_input_tokens": 0.20,
    "output": 10.00,
}

# lipsync part -> (nominal absolute-time threshold used to pick it, matching
# build_cut.py's pick_lip()) and its measured true offset (offsets.json).
LIP_PICK_THRESHOLDS = [("lipsync_part_a.mp4", 15.5), ("lipsync_part_b.mp4", 84.0), ("lipsync_part_c.mp4", None)]
DEFAULT_LIP_OFFSETS = {"lipsync_part_a.mp4": 0.0, "lipsync_part_b.mp4": 68.3, "lipsync_part_c.mp4": 137.16}


# ═══════════════════════════════════════════════════════════════════════════
# Input parsing -- pure, no filesystem beyond the given paths
# ═══════════════════════════════════════════════════════════════════════════

def read_script_tsv(path: Path) -> list[dict]:
    """SCRIPT.tsv columns: tag, spoken, shot, beat, screen. CSV-quoted (a
    screen note can contain literal tabs/newlines inside "" quotes)."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.reader(f, delimiter="\t"):
            if not r or not r[0].strip():
                continue
            r = list(r) + [""] * (5 - len(r))
            tag, spoken, shot, beat, screen = r[:5]
            rows.append({"tag": tag.strip(), "spoken": spoken, "shot": shot.strip(),
                         "beat": beat.strip(), "screen": screen})
    return rows


def read_timings_tsv(path: Path) -> dict[str, tuple[float, float]]:
    timings: dict[str, tuple[float, float]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if rows and rows[0][:1] == ["tag"]:
        rows = rows[1:]
    for r in rows:
        if not r or not r[0].strip():
            continue
        timings[r[0].strip()] = (float(r[1]), float(r[2]))
    return timings


def read_jev_decisions(path: Path | None) -> dict[str, dict[str, dict]]:
    """line_id -> {question: record}. Missing file/None -> {} (Jev decisions
    are optional input, per TASK.md's `[--jev ...]` not being required)."""
    per_line: dict[str, dict[str, dict]] = {}
    if not path or not Path(path).exists():
        return per_line
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            tag, q = rec.get("line_id"), rec.get("question")
            if tag and q:
                per_line.setdefault(tag, {})[q] = rec
    return per_line


def build_line_table(script_rows: list[dict], timings: dict[str, tuple[float, float]],
                      jev_by_line: dict[str, dict[str, dict]], t_max: float | None) -> list[dict]:
    """(tag, t0, t1, spoken, screen, jev decision) per TASK.md deliverable 1,
    joined against timings.tsv (the timing authority) and sorted by t0."""
    lines = []
    for row in script_rows:
        tag = row["tag"]
        if tag not in timings:
            continue
        t0, t1 = timings[tag]
        if t_max is not None and t0 >= t_max - 1e-6:
            continue
        beat_rec = jev_by_line.get(tag, {}).get("bl.beat", {})
        jev_decision = beat_rec.get("final") or beat_rec.get("choice")
        lines.append({
            "tag": tag, "t0": t0, "t1": t1, "spoken": row["spoken"], "shot": row["shot"],
            "script_beat": row["beat"], "screen": row["screen"], "jev_decision": jev_decision,
        })
    lines.sort(key=lambda l: l["t0"])
    return lines


# ═══════════════════════════════════════════════════════════════════════════
# Frame preparation
# ═══════════════════════════════════════════════════════════════════════════

def find_still(media_dir: Path, shot: str) -> Path | None:
    if not shot:
        return None
    for sub in ("real", "third-party"):
        for ext in STILL_EXTS:
            p = media_dir / sub / f"{shot}{ext}"
            if p.exists():
                return p
    return None


def find_lipsync_part(media_dir: Path, t0: float) -> tuple[Path, float] | None:
    """Which lipsync_part_*.mp4 covers t0, and the local (media_start) time
    inside it -- matching build_cut.py's pick_lip()/lip_offset(). Looks for
    the part flat under media_dir, falling back to nothing if absent."""
    offsets = dict(DEFAULT_LIP_OFFSETS)
    offsets_json = media_dir / "offsets.json"
    if offsets_json.exists():
        try:
            for entry in json.loads(offsets_json.read_text()):
                fname = entry.get("file")
                if fname:
                    offsets[fname] = float(entry["true_s"])
        except (json.JSONDecodeError, KeyError, ValueError):
            pass
    for fname, threshold in LIP_PICK_THRESHOLDS:
        if threshold is None or t0 < threshold:
            part_path = media_dir / fname
            if part_path.exists():
                return part_path, round(t0 - offsets.get(fname, 0.0), 3)
    return None


def image_native_size(path: Path) -> tuple[int, int]:
    from PIL import Image
    with Image.open(path) as im:
        return im.width, im.height


def scale_still_to(src: Path, dst: Path, max_w: int = MAX_FRAME_W) -> tuple[int, int]:
    from PIL import Image
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        w, h = im.size
        if w > max_w:
            new_h = round(h * max_w / w)
            im = im.resize((max_w, new_h), Image.LANCZOS)
        im.save(dst, "JPEG", quality=90)
        return im.size


def extract_video_frame(video_path: Path, at_sec: float, dst: Path, max_w: int = MAX_FRAME_W) -> tuple[int, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    at_sec = max(0.0, at_sec)
    cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{at_sec:.3f}", "-i", str(video_path),
           "-frames:v", "1", "-vf", f"scale='min({max_w},iw)':-2", str(dst)]
    subprocess.run(cmd, check=True, capture_output=True)
    return image_native_size(dst)


def prepare_frames(lines: list[dict], media_dir: Path, workdir: Path) -> dict[str, Any]:
    """Returns {"stills": {shot: {"path":..., "frame_w":..., "frame_h":...,
    "native_w":..., "native_h":..., "rel_source":..., "source":...}},
    "avatars": {tag: {"path":..., "w":..., "h":..., "source":...,
    "media_start":...}}, "missing": [tag,...]}. Each real still is prepared
    ONCE and reused across every line that names it; every avatar-only line
    gets its own frame at its own t0 (TASK.md deliverable 1).

    frame_w/frame_h are the SCALED (<=882px) frame the model actually sees;
    native_w/native_h are the still's true original pixel size. The model
    only ever measures a box in the frame it was shown, so
    enrich_beats_with_still_metadata() rescales that box to native pixels
    afterwards -- asking the model to reason in a resolution it never saw
    is unreliable and was measured to produce a self-consistent but
    mislabeled "native" size (the scaled frame's own dimensions) in an
    earlier version of this tool."""
    stills: dict[str, dict] = {}
    avatars: dict[str, dict] = {}
    missing: list[str] = []
    frames_dir = workdir / "frames"
    for line in lines:
        tag, shot = line["tag"], line["shot"]
        if shot:
            if shot in stills:
                continue
            src = find_still(media_dir, shot)
            if src is None:
                missing.append(tag)
                continue
            native_w, native_h = image_native_size(src)
            dst = frames_dir / "stills" / f"{shot}.jpg"
            frame_w, frame_h = scale_still_to(src, dst)
            try:
                rel_source = str(src.relative_to(media_dir))
            except ValueError:
                rel_source = str(src)
            stills[shot] = {"path": dst, "frame_w": frame_w, "frame_h": frame_h,
                             "native_w": native_w, "native_h": native_h,
                             "rel_source": rel_source, "source": str(src)}
        else:
            part = find_lipsync_part(media_dir, line["t0"])
            if part is None:
                missing.append(tag)
                continue
            video_path, media_start = part
            dst = frames_dir / "avatar" / f"{tag}.jpg"
            w, h = extract_video_frame(video_path, media_start, dst)
            avatars[tag] = {"path": dst, "w": w, "h": h, "source": video_path.name, "media_start": media_start}
    return {"stills": stills, "avatars": avatars, "missing": missing}


# ═══════════════════════════════════════════════════════════════════════════
# Prompt construction
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_INSTRUCTIONS = """You are the BLACK LIQUIDITY Scripter. You look at the frames ONCE and write \
the episode's cut table as JSON -- a blind render pipeline executes your table with no further \
judgment calls, so every field must be exactly right.

Canvas: 1080x1920 @ 30fps. Output schema -- a JSON object {"beats": [...]}; each entry:
  tag (string, copy from the line table), t0 (number, seconds), t1 (number, seconds),
  mode (one of "FF", "COMP", "EVID", "KIN", "CHECK"),
  extra (object, keys depend on mode -- see below; omit keys that don't apply, never null them).

mode meanings:
  FF   = avatar full-frame, real lipsync video, no other footage on screen.
  COMP = avatar composited (shrunk, lower third) over an evidence still, both visible at once.
  EVID = the evidence still fills the frame, no avatar.
  KIN  = kinetic text only (no footage), used when the line has no real still and is not a
         plain avatar line -- e.g. a transition, a claim with no evidence photo, a summary beat.

Rules for picking mode, in order:
  1. If the line's Jev decision is present, follow it: "hook" or "verdict" -> FF (this channel's
     verdict/emotion lines run avatar full-frame, never composited). "show" -> COMP when the
     avatar is still speaking WHILE the evidence must stay visible, or EVID when the line is a
     continuation/pure evidence beat with no need to keep cutting back to the avatar's face.
  2. No Jev decision: a line with a still image and the avatar's own face in-frame -> COMP; a
     line with a still image continuing the same evidence with no avatar frame supplied -> EVID;
     a line with NO still and NO avatar frame supplied -> KIN; a line with no still but an avatar
     frame supplied -> FF.
  3. Consecutive lines about the SAME still image usually read as one EVID/COMP run, not a fresh
     COMP for every line -- only the first line of a run needs the avatar full-frame->composite
     transition; the rest can be EVID holds on the same still if the avatar isn't essential to
     re-establish per line.

extra fields by mode:
  FF:   cap (the line's spoken text, verbatim), avatar_src="lip", media0=t0.
  COMP: box=[x,y,w,h] IN THE PIXELS OF THE FRAME IMAGE YOU WERE SHOWN for that still (not its
        original resolution -- the tool rescales your box to the still's true native pixels
        itself, using the native size printed next to that still in the line table; just measure
        what you see in the frame), cap (verbatim spoken/screen text), avatar_src="lip", media0=t0,
        credit (only if the still is a third-party screenshot, e.g. "ขอบคุณภาพจาก WikiFX" --
        never for a real/ still, those are our own captures and need no credit).
        (img/native_w/native_h are filled in for you automatically from the still's own file --
        you do not need to write them.)
  EVID: box, cap, credit (same rules as COMP, no avatar_src/media0, img/native_w/native_h auto-filled).
  KIN:  lines=[[css_class, html], ...] (1-3 short Thai lines built from the spoken/screen text;
        css_class one of "bl-lg", "bl-md", "bl-sm", "bl-xl n", "bl-lg n" -- match line length to
        class: bl-xl n for a single big word/phrase, bl-lg for a headline, bl-md for body text).
  CHECK: not used in this window -- skip it.

cap / lines text: use the line's spoken text (and screen text for on-screen numbers/claims)
VERBATIM -- never paraphrase, never translate, never shorten.

t0/t1: copy the line's own t0/t1 from the table exactly, do not invent your own or try to close
the gaps between lines yourself -- the render pipeline holds each plate until the next line
starts, so gaps are already handled downstream and are not your job.

Every line in the table gets EXACTLY ONE beat row, in the same order as the table. Output ONLY
the JSON object, no markdown fences, no commentary before or after it."""


def render_line_table_text(lines: list[dict], frames: dict[str, Any]) -> str:
    out = ["LINE TABLE (one row per script line, in order):"]
    for i, l in enumerate(lines, 1):
        still_info = ""
        if l["shot"]:
            s = frames["stills"].get(l["shot"])
            if s:
                still_info = (f' | still="{l["shot"]}" frame={s["frame_w"]}x{s["frame_h"]} '
                              f'(native {s["native_w"]}x{s["native_h"]})')
            else:
                still_info = f' | still="{l["shot"]}" (MISSING -- no frame provided, treat as KIN)'
        jev = f' | jev_decision={l["jev_decision"]!r}' if l["jev_decision"] else ""
        out.append(
            f'{i}. tag={l["tag"]} t0={l["t0"]} t1={l["t1"]} spoken="{l["spoken"]}" '
            f'screen="{l["screen"]}"{still_info}{jev}'
        )
    return "\n".join(out)


def build_claude_p_prompt(lines: list[dict], frames: dict[str, Any]) -> str:
    parts = [SYSTEM_INSTRUCTIONS, "", render_line_table_text(lines, frames), ""]
    parts.append("FRAMES -- Read each file EXACTLY ONCE before writing your answer:")
    for shot, info in frames["stills"].items():
        parts.append(f'  - {info["path"]}  (real still "{shot}", frame {info["frame_w"]}x{info["frame_h"]})')
    for tag, info in frames["avatars"].items():
        parts.append(f'  - {info["path"]}  (avatar frame for line {tag} at t0)')
    parts.append("")
    parts.append('Now answer with ONLY the JSON object {"beats": [...]} -- no other text.')
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════
# Schema validation
# ═══════════════════════════════════════════════════════════════════════════

class ScripterSchemaError(ValueError):
    pass


def validate_beats(beats: Any, expected_tags: list[str]) -> list[dict]:
    if not isinstance(beats, list):
        raise ScripterSchemaError(f"beats must be a list, got {type(beats).__name__}")
    seen = []
    for i, row in enumerate(beats):
        if not isinstance(row, dict):
            raise ScripterSchemaError(f"beat[{i}] must be an object, got {type(row).__name__}")
        for key in ("tag", "t0", "t1", "mode", "extra"):
            if key not in row:
                raise ScripterSchemaError(f"beat[{i}] missing required key {key!r}")
        if row["mode"] not in MODES:
            raise ScripterSchemaError(f"beat[{i}] tag={row['tag']!r} has invalid mode {row['mode']!r}, "
                                       f"must be one of {MODES}")
        if not isinstance(row["extra"], dict):
            raise ScripterSchemaError(f"beat[{i}] tag={row['tag']!r} extra must be an object")
        try:
            float(row["t0"]); float(row["t1"])
        except (TypeError, ValueError):
            raise ScripterSchemaError(f"beat[{i}] tag={row['tag']!r} t0/t1 must be numeric")
        seen.append(row["tag"])
    missing = [t for t in expected_tags if t not in seen]
    extra = [t for t in seen if t not in expected_tags]
    if missing:
        raise ScripterSchemaError(f"beats missing tags: {missing}")
    if extra:
        raise ScripterSchemaError(f"beats has unexpected tags not in the line table: {extra}")
    return beats


def extract_json_text(raw: str) -> str:
    """The model is told to answer with ONLY JSON, but strip markdown fences
    defensively -- and if there's leading/trailing prose, take the outermost
    {...} span."""
    raw = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", raw, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    first, last = raw.find("{"), raw.rfind("}")
    if first != -1 and last != -1 and last > first:
        return raw[first:last + 1]
    return raw


# ═══════════════════════════════════════════════════════════════════════════
# claude-p backend
# ═══════════════════════════════════════════════════════════════════════════

def run_claude_p(prompt: str, model: str = "sonnet") -> dict:
    """Runs `claude -p` once, non-interactively, Read-only. Returns the
    parsed top-level wrapper JSON (session_id, usage, result, ...)."""
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "json", "--allowed-tools", "Read"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p exited {proc.returncode}: {proc.stderr[-2000:]}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude -p did not return valid JSON on stdout: {e}\nstdout[-2000:]={proc.stdout[-2000:]}")


def find_transcript(session_id: str, cwd: Path) -> Path | None:
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(cwd))
    p = Path.home() / ".claude" / "projects" / slug / f"{session_id}.jsonl"
    return p if p.exists() else None


def usage_from_transcript(transcript_path: Path) -> dict:
    """Token usage of one Claude Code session, read from its JSONL transcript.

    Deduplicated by ``message.id``. Claude Code writes one assistant API
    response as one transcript line per content block (text, tool_use,
    thinking ...), and every one of those lines repeats the same
    ``message.id`` with the same cumulative ``usage``. Summing every line
    therefore over-counts by the blocks-per-message ratio -- measured
    2026-09-25: the EP57 cut worker 1,418 lines / 760 ids ($188.60 raw vs
    $99.79 deduplicated), the A/B/C arms 2.0-4.3x. Same rule as
    ``jev_edit_lib.sum_transcript_usage``: keep the last write per id (every
    repeat seen so far was byte-identical); a line without an id counts once.

    Returns ``{"turns": <unique message ids>, "lines": <assistant lines
    carrying usage>, "tokens": {<the four usage components>}}``.
    """
    keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
    by_id: dict[str, dict[str, int]] = {}
    unkeyed: list[dict[str, int]] = []
    lines = 0
    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            usage = msg.get("usage")
            if not usage:
                continue
            lines += 1
            row = {k: int(usage.get(k, 0) or 0) for k in keys}
            mid = msg.get("id")
            if mid:
                by_id[mid] = row
            else:
                unkeyed.append(row)
    rows = list(by_id.values()) + unkeyed
    totals = {k: sum(r[k] for r in rows) for k in keys}
    return {"turns": len(rows), "lines": lines, "tokens": totals}


def _cost_from_token_dict(tokens: dict) -> float:
    return (
        tokens.get("input_tokens", 0) / 1e6 * PRICE_PER_MTOK["input"]
        + tokens.get("cache_creation_input_tokens", 0) / 1e6 * PRICE_PER_MTOK["cache_creation_input_tokens"]
        + tokens.get("cache_read_input_tokens", 0) / 1e6 * PRICE_PER_MTOK["cache_read_input_tokens"]
        + tokens.get("output_tokens", 0) / 1e6 * PRICE_PER_MTOK["output"]
    )


def enrich_beats_with_still_metadata(beats: list[dict], lines: list[dict], frames: dict[str, Any]) -> list[dict]:
    """The model measures a box in the SCALED frame it was shown; rescale it
    to the still's true native pixels and fill in img/native_w/native_h from
    our own deterministic line->shot mapping (the model never has to invent
    a file path or extension, which it was measured to get wrong)."""
    shot_by_tag = {l["tag"]: l["shot"] for l in lines}
    for b in beats:
        shot = shot_by_tag.get(b.get("tag"))
        info = frames["stills"].get(shot) if shot else None
        if not info:
            continue
        extra = dict(b.get("extra") or {})
        extra["img"] = info["rel_source"]
        extra["native_w"] = info["native_w"]
        extra["native_h"] = info["native_h"]
        box = extra.get("box")
        if box and info["frame_w"] and info["frame_h"]:
            sx = info["native_w"] / info["frame_w"]
            sy = info["native_h"] / info["frame_h"]
            x, y, w, h = box
            extra["box"] = [round(x * sx, 1), round(y * sy, 1), round(w * sx, 1), round(h * sy, 1)]
        b["extra"] = extra
    return beats


def run_scripter_claude_p(lines: list[dict], frames: dict[str, Any], workdir: Path) -> tuple[list[dict], dict]:
    prompt = build_claude_p_prompt(lines, frames)
    t_start = time.monotonic()
    wrapper = run_claude_p(prompt)
    wall_seconds = time.monotonic() - t_start

    result_text = wrapper.get("result", "")
    parsed = json.loads(extract_json_text(result_text))
    beats = parsed["beats"] if isinstance(parsed, dict) and "beats" in parsed else parsed
    beats = validate_beats(beats, [l["tag"] for l in lines])
    beats = enrich_beats_with_still_metadata(beats, lines, frames)

    session_id = wrapper.get("session_id")
    transcript = find_transcript(session_id, Path.cwd()) if session_id else None
    if transcript:
        t_usage = usage_from_transcript(transcript)
        tokens, turns = t_usage["tokens"], t_usage["turns"]
        transcript_lines = t_usage["lines"]
    else:
        usage = wrapper.get("usage", {})
        tokens = {k: usage.get(k, 0) for k in
                  ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}
        turns = wrapper.get("num_turns", 1)
        transcript_lines = None

    usage_out = {
        "backend": "claude-p",
        "model": "claude-sonnet-5",
        "session_id": session_id,
        "transcript": str(transcript) if transcript else None,
        "turns": turns,
        "transcript_lines": transcript_lines,
        "tokens": tokens,
        "cost_usd_reported_max_plan": wrapper.get("total_cost_usd"),
        "cost_usd_api_equivalent": round(_cost_from_token_dict(tokens), 6),
        "wall_seconds": round(wall_seconds, 2),
        "pricing_table_per_mtok": PRICE_PER_MTOK,
    }
    return beats, usage_out


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--script", required=True, help="SCRIPT.tsv path")
    ap.add_argument("--timings", required=True, help="timings.tsv path")
    ap.add_argument("--jev", default=None, help="decisions.jsonl path (optional)")
    ap.add_argument("--media-dir", required=True, help="dir holding real/, third-party/, broll/, lipsync_part_*.mp4")
    ap.add_argument("--t-max", type=float, default=None, help="only lines with t0 < t-max")
    ap.add_argument("--backend", choices=["claude-p"], default="claude-p",
                     help="claude-p only -- CEO ruling 2026-09-25 dropped the api backend")
    ap.add_argument("--out", default="beats.json")
    ap.add_argument("--usage-out", default=None, help="default: <out>'s dir / scripter_usage.json")
    ap.add_argument("--workdir", default=None, help="frame-extraction scratch dir (default: a temp dir)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    script_rows = read_script_tsv(Path(args.script))
    timings = read_timings_tsv(Path(args.timings))
    jev_by_line = read_jev_decisions(Path(args.jev) if args.jev else None)
    lines = build_line_table(script_rows, timings, jev_by_line, args.t_max)
    if not lines:
        print("no script lines in range -- nothing to do", file=sys.stderr)
        return 1

    media_dir = Path(args.media_dir).expanduser()
    workdir = Path(args.workdir).expanduser() if args.workdir else Path(tempfile.mkdtemp(prefix="bl_scripter_"))
    frames = prepare_frames(lines, media_dir, workdir)
    if frames["missing"]:
        print(f"WARNING: no frame found for tags: {frames['missing']}", file=sys.stderr)

    beats, usage = run_scripter_claude_p(lines, frames, workdir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(beats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    usage_path = Path(args.usage_out) if args.usage_out else out_path.parent / "scripter_usage.json"
    usage_path.write_text(json.dumps(usage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"wrote {out_path} ({len(beats)} beats) and {usage_path}")
    if not args.workdir:
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

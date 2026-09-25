#!/usr/bin/env python3
"""BLACK LIQUIDITY Split -- dead-air segment plan for the split-editor A/B
(docs/ops/bl-split-ab-2026-09-25/PLAN.md, task-1678d38e).

Implements PLAN.md's "Dead-air split rule" exactly:
  - Candidates: pauses >= 0.45s detected by `silencedetect=n=-35dB:d=0.3` on
    the episode audio.
  - Forbidden: a pause that overlaps a multi-line visual block (e.g. EP57's
    checklist card, 129.38-141.48s) -- never cut inside one.
  - Walk forward from the previous cut (starting at t=0): take the longest
    allowed pause whose midpoint sits between +25s and +50s after the
    previous cut; if none, take the longest allowed pause anywhere after
    +25s. The cut itself is the pause's midpoint, floored to the 30fps frame
    grid. Repeat until no candidate remains -- N segments is whatever falls
    out, never fixed.

Usage:
    python3 tools/bl_split.py audio-hq.mp3 --script SCRIPT.tsv \\
        --timings timings.tsv --blocks ep57-blocks.json -o segments.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

FPS = 30
CANDIDATE_MIN_DUR = 0.45   # seconds -- PLAN.md "Candidates: pauses >= 0.45s"
DETECT_NOISE_DB = -35.0    # silencedetect n=
DETECT_MIN_DUR = 0.3       # silencedetect d= -- the RAW detection floor
WALK_MIN_GAP = 25.0        # seconds after the previous cut
WALK_MAX_GAP = 50.0
MIN_SEG_TAIL = 20.0        # seconds -- task-99f3d2e8: no short final segment


class SplitError(RuntimeError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# ffmpeg/ffprobe -- pause detection + audio duration
# ═══════════════════════════════════════════════════════════════════════════

_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?[\d.]+)")


def parse_silencedetect(stderr_text: str) -> list[tuple[float, float]]:
    """Pairs up ffmpeg's silencedetect log lines into (start, end) pauses.
    An unmatched trailing silence_start (silence runs to EOF) is dropped --
    it has no end and cannot be a cut candidate (its "midpoint" is undefined)."""
    starts = [float(m.group(1)) for m in _SILENCE_START_RE.finditer(stderr_text)]
    ends = [float(m.group(1)) for m in _SILENCE_END_RE.finditer(stderr_text)]
    return list(zip(starts, ends))


def detect_pauses(audio_path: Path, noise_db: float = DETECT_NOISE_DB,
                   min_dur: float = DETECT_MIN_DUR) -> list[tuple[float, float]]:
    proc = subprocess.run(
        ["ffmpeg", "-i", str(audio_path),
         "-af", f"silencedetect=n={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return parse_silencedetect(proc.stderr)


def audio_duration(audio_path: Path) -> float:
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio_path)],
        capture_output=True, text=True, check=True,
    )
    return float(proc.stdout.strip())


# ═══════════════════════════════════════════════════════════════════════════
# Frame grid
# ═══════════════════════════════════════════════════════════════════════════

def frame_floor(t: float, fps: int = FPS) -> float:
    """Floor `t` to the nearest fps frame boundary -- a tiny epsilon guards
    against a value like 30.299999999996 (float error) flooring one frame
    short of the intended 30.3."""
    return math.floor(t * fps + 1e-6) / fps


# ═══════════════════════════════════════════════════════════════════════════
# Candidates / forbidden spans
# ═══════════════════════════════════════════════════════════════════════════

def candidate_pauses(pauses: list[tuple[float, float]], min_dur: float = CANDIDATE_MIN_DUR
                      ) -> list[tuple[float, float]]:
    return [(s, e) for s, e in pauses if e - s >= min_dur - 1e-9]


def load_blocks(path: Path | None) -> list[tuple[float, float]]:
    if path is None:
        return []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    blocks: list[tuple[float, float]] = []
    for item in data:
        if isinstance(item, dict):
            blocks.append((float(item["t0"]), float(item["t1"])))
        else:
            t0, t1 = item
            blocks.append((float(t0), float(t1)))
    return blocks


def is_forbidden(pause: tuple[float, float], blocks: list[tuple[float, float]]) -> bool:
    s, e = pause
    return any(s < be and e > bs for bs, be in blocks)


# ═══════════════════════════════════════════════════════════════════════════
# The walk -- PLAN.md's "Dead-air split rule"
# ═══════════════════════════════════════════════════════════════════════════

def select_cut_points(candidates: list[tuple[float, float]], blocks: list[tuple[float, float]],
                       fps: int = FPS, min_gap: float = WALK_MIN_GAP, max_gap: float = WALK_MAX_GAP
                       ) -> list[float]:
    """Returns the sorted list of interior cut times (frame-floored), never
    including t=0 or the episode end -- those are the outer segment bounds,
    added by build_segments()."""
    allowed = [(s, e, (s + e) / 2.0, e - s) for s, e in candidates if not is_forbidden((s, e), blocks)]

    cuts: list[float] = []
    prev = 0.0
    while True:
        window = [c for c in allowed if prev + min_gap <= c[2] <= prev + max_gap]
        if window:
            chosen = max(window, key=lambda c: c[3])
        else:
            fallback = [c for c in allowed if c[2] > prev + min_gap]
            if not fallback:
                break
            chosen = max(fallback, key=lambda c: c[3])
        cut = frame_floor(chosen[2], fps)
        if cut <= prev:
            break  # defensive: a pathological rounding tie must never loop forever
        cuts.append(cut)
        prev = cut
    return cuts


def enforce_min_tail(cuts: list[float], total_dur: float, min_seg: float = MIN_SEG_TAIL,
                      fps: int = FPS) -> list[float]:
    """The walk above only guarantees WALK_MIN_GAP (25s) between interior
    cuts -- the FINAL segment's length is whatever is left after the last
    cut to the episode end, which can be short (EP57's un-merged plan left
    a 7.1s seg05). Drop trailing cut points until the tail is long enough,
    or none remain (a single short episode stays one segment)."""
    end = frame_floor(total_dur, fps)
    cuts = list(cuts)
    while cuts and (end - cuts[-1]) < min_seg - 1e-9:
        cuts.pop()
    return cuts


# ═══════════════════════════════════════════════════════════════════════════
# SCRIPT.tsv / timings.tsv
# ═══════════════════════════════════════════════════════════════════════════

def load_script(path: Path) -> dict[str, dict[str, str]]:
    """tag -> {text, shot, verb, note} -- SCRIPT.tsv has no header (SKILL.md:
    tag, Thai caption line, shot basename, Jev decision verb, note)."""
    out: dict[str, dict[str, str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if not row or not row[0]:
                continue
            tag = row[0]
            cols = row[1:] + [""] * max(0, 4 - len(row[1:]))
            out[tag] = {"text": cols[0], "shot": cols[1], "verb": cols[2], "note": cols[3]}
    return out


def load_timings(path: Path) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    if not rows:
        return out
    header = [c.strip().lower() for c in rows[0]]
    body = rows[1:] if header[:3] == ["tag", "t0", "t1"] else rows
    for row in body:
        if not row or not row[0]:
            continue
        out[row[0]] = (float(row[1]), float(row[2]))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Segments
# ═══════════════════════════════════════════════════════════════════════════

def build_segments(cuts: list[float], total_dur: float, timings: dict[str, tuple[float, float]],
                    script: dict[str, dict[str, str]] | None = None, fps: int = FPS) -> list[dict[str, Any]]:
    end = frame_floor(total_dur, fps)
    bounds = [0.0] + sorted(cuts) + [end]
    tag_order = sorted(timings.keys(), key=lambda t: timings[t][0])

    segments = []
    for i in range(len(bounds) - 1):
        t0, t1 = bounds[i], bounds[i + 1]
        tags_in = [tag for tag in tag_order if t0 <= timings[tag][0] < t1]
        lines = []
        for tag in tags_in:
            lt0, lt1 = timings[tag]
            entry = {"tag": tag, "t0": lt0, "t1": lt1}
            if script and tag in script:
                entry["text"] = script[tag]["text"]
            lines.append(entry)
        frame_count = int(round((t1 - t0) * fps))
        segments.append({
            "id": f"seg{i + 1:02d}",
            "t0": round(t0, 4),
            "t1": round(t1, 4),
            "frame_count": frame_count,
            "lines": lines,
        })
    return segments


def split_episode(audio_path: Path, timings: dict[str, tuple[float, float]],
                   script: dict[str, dict[str, str]] | None = None,
                   blocks: list[tuple[float, float]] | None = None,
                   fps: int = FPS, min_gap: float = WALK_MIN_GAP, max_gap: float = WALK_MAX_GAP,
                   candidate_min_dur: float = CANDIDATE_MIN_DUR,
                   min_seg: float = MIN_SEG_TAIL) -> dict[str, Any]:
    pauses = detect_pauses(audio_path)
    total_dur = audio_duration(audio_path)
    cands = candidate_pauses(pauses, candidate_min_dur)
    cuts = select_cut_points(cands, blocks or [], fps, min_gap, max_gap)
    cuts = enforce_min_tail(cuts, total_dur, min_seg, fps)
    segments = build_segments(cuts, total_dur, timings, script, fps)
    return {
        "audio": str(audio_path),
        "total_duration": round(total_dur, 4),
        "fps": fps,
        "candidate_pause_min_s": candidate_min_dur,
        "walk_min_gap_s": min_gap,
        "walk_max_gap_s": max_gap,
        "min_seg_tail_s": min_seg,
        "pauses_detected": len(pauses),
        "candidates": len(cands),
        "cuts": cuts,
        "segments": segments,
    }


def format_plan(plan: dict[str, Any]) -> str:
    lines = [
        f"audio: {plan['audio']}  total_duration={plan['total_duration']}s  "
        f"pauses_detected={plan['pauses_detected']}  candidates(>=0.45s)={plan['candidates']}",
        f"cuts (frame-floored, s): {plan['cuts']}",
        f"N segments = {len(plan['segments'])}",
    ]
    for seg in plan["segments"]:
        tags = ", ".join(l["tag"] for l in seg["lines"]) or "(none)"
        lines.append(f"  {seg['id']}  t0={seg['t0']:>7.3f}  t1={seg['t1']:>7.3f}  "
                      f"dur={seg['t1'] - seg['t0']:.3f}s  frames={seg['frame_count']:<5}  tags: {tags}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio")
    ap.add_argument("--script", required=True, help="SCRIPT.tsv")
    ap.add_argument("--timings", required=True, help="timings.tsv (tag/t0/t1)")
    ap.add_argument("--blocks", default=None, help="JSON list of forbidden [t0,t1]/{t0,t1} spans")
    ap.add_argument("-o", "--out", required=True, help="segments.json to write")
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--min-gap", type=float, default=WALK_MIN_GAP)
    ap.add_argument("--max-gap", type=float, default=WALK_MAX_GAP)
    ap.add_argument("--candidate-min-dur", type=float, default=CANDIDATE_MIN_DUR)
    ap.add_argument("--min-seg", type=float, default=MIN_SEG_TAIL,
                     help="merge a final segment shorter than this (seconds) into the one before it")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    script = load_script(Path(args.script))
    timings = load_timings(Path(args.timings))
    blocks = load_blocks(Path(args.blocks) if args.blocks else None)

    plan = split_episode(Path(args.audio), timings, script, blocks,
                          fps=args.fps, min_gap=args.min_gap, max_gap=args.max_gap,
                          candidate_min_dur=args.candidate_min_dur, min_seg=args.min_seg)
    Path(args.out).write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(format_plan(plan))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SplitError as e:
        print(f"error: {e}", file=sys.stderr)
        raise SystemExit(1)

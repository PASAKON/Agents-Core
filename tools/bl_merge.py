#!/usr/bin/env python3
"""BLACK LIQUIDITY Merge -- concat segment renders, mux audio once, gate
(docs/ops/bl-split-ab-2026-09-25/PLAN.md, task-1678d38e).

Arm 2 of the split-editor A/B: N editors each render ONLY their own
[t0, t1) segment as video-only MP4 (§ Segment contract in PLAN.md -- same
template, same caption style, same encoder settings so they concat with
`-c copy`). This tool is the CTO's merge step: concatenate the parts frame-
exact, mux the master narration audio once, then run every PLAN.md merge
gate and refuse to ship on any failure.

Merge gates (PLAN.md "Merge gates -- the CTO refuses to ship on any failure"):
    1. Frame count = floor(audio_duration * fps) +/- 1.
    2. Zero empty/black frames at 30fps, incl. single-frame dips
       (tools/bl_checker.py::detect_empty_frames, reused here as-is).
    3. Seam check +/- 3 frames around every join.
    4. One caption style across the whole episode (every segment's own
       composed index.html, tools/bl_checker.py::caption_style_signatures).
    5. Audio offset < 40ms against the master.

Usage:
    python3 tools/bl_merge.py segments.json --parts renders/ \\
        --audio audio-hq.mp3 -o final.mp4 [--compositions builds/]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import bl_checker  # noqa: E402  -- reuse the empty-frame + caption-style gates verbatim

FPS = 30
SEAM_WINDOW_FRAMES = 3
AUDIO_OFFSET_MAX_S = 0.040
FRAME_COUNT_TOLERANCE = 1

CODEC_FIELDS = ("codec_name", "width", "height", "pix_fmt", "r_frame_rate")


class MergeError(RuntimeError):
    pass


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# ═══════════════════════════════════════════════════════════════════════════
# ffprobe helpers
# ═══════════════════════════════════════════════════════════════════════════

def probe_video_stream(path: Path) -> dict[str, Any]:
    r = _run(["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=" + ",".join(CODEC_FIELDS),
              "-of", "json", str(path)])
    streams = json.loads(r.stdout or "{}").get("streams") or []
    if not streams:
        raise MergeError(f"no video stream in {path}")
    return streams[0]


def count_video_frames(path: Path) -> int:
    r = _run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
              "-show_entries", "stream=nb_read_frames", "-of", "default=nk=1:nw=1", str(path)])
    out = r.stdout.strip()
    if not out or out == "N/A":
        raise MergeError(f"could not count frames in {path}")
    return int(out)


def probe_duration(path: Path) -> float:
    r = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "default=nk=1:nw=1", str(path)])
    return float(r.stdout.strip())


def probe_audio_start_time(path: Path) -> float:
    r = _run(["ffprobe", "-v", "error", "-select_streams", "a:0",
              "-show_entries", "stream=start_time", "-of", "default=nk=1:nw=1", str(path)])
    out = r.stdout.strip()
    return float(out) if out and out != "N/A" else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Pre-flight: identical codec params
# ═══════════════════════════════════════════════════════════════════════════

def verify_same_codec(parts: list[Path]) -> list[str]:
    """Returns a list of mismatch descriptions (empty = every part shares
    the same codec/resolution/pix_fmt/frame rate -- required for `-c copy`
    concat to produce a valid file at all, let alone a clean seam)."""
    if not parts:
        return ["no part files given"]
    probes = [(p, probe_video_stream(p)) for p in parts]
    reference_path, reference = probes[0]
    mismatches = []
    for path, probe in probes[1:]:
        for field in CODEC_FIELDS:
            if probe.get(field) != reference.get(field):
                mismatches.append(
                    f"{path.name}: {field}={probe.get(field)!r} != {reference_path.name}: {field}={reference.get(field)!r}")
    return mismatches


# ═══════════════════════════════════════════════════════════════════════════
# Concat + mux
# ═══════════════════════════════════════════════════════════════════════════

def concat_copy(parts: list[Path], out_path: Path) -> Path:
    list_path = out_path.with_suffix(".concat.txt")
    list_path.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    r = _run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
              "-i", str(list_path), "-c", "copy", str(out_path)])
    if r.returncode != 0:
        raise MergeError(f"concat failed: {r.stderr.strip()}")
    return out_path


def mux_master_audio(video_path: Path, audio_path: Path, out_path: Path) -> Path:
    r = _run(["ffmpeg", "-y", "-v", "error",
              "-i", str(video_path), "-i", str(audio_path),
              "-map", "0:v:0", "-map", "1:a:0",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
              str(out_path)])
    if r.returncode != 0:
        raise MergeError(f"audio mux failed: {r.stderr.strip()}")
    return out_path


# ═══════════════════════════════════════════════════════════════════════════
# Gates
# ═══════════════════════════════════════════════════════════════════════════

def check_frame_count(actual_frames: int, audio_duration: float, fps: int = FPS,
                       tolerance: int = FRAME_COUNT_TOLERANCE) -> dict[str, Any]:
    import math
    expected = int(math.floor(audio_duration * fps))
    ok = abs(actual_frames - expected) <= tolerance
    return {"ok": ok, "actual": actual_frames, "expected": expected, "tolerance": tolerance}


def check_seams(empty_frame_times: list[float], seam_frame_indices: list[int],
                 fps: int = FPS, window: int = SEAM_WINDOW_FRAMES) -> list[dict[str, Any]]:
    """Flags any of the (already-detected) empty/black frames that land
    within `window` frames of a join -- the same defect class as an ordinary
    empty frame, but attributed to a specific seam so a CTO reviewing a
    failed merge knows which two parts to re-render, not just that the
    153s file has a bad frame somewhere."""
    bad = []
    empty_frame_indices = [round(t * fps) for t in empty_frame_times]
    for seam_idx in seam_frame_indices:
        hits = [t for t, fi in zip(empty_frame_times, empty_frame_indices) if abs(fi - seam_idx) <= window]
        if hits:
            bad.append({"seam_frame": seam_idx, "seam_time": round(seam_idx / fps, 3), "empty_frames_near": hits})
    return bad


def check_audio_offset(final_path: Path, max_offset: float = AUDIO_OFFSET_MAX_S) -> dict[str, Any]:
    """The muxed audio stream's own start_time should be ~0 -- it is mapped
    directly from the master file's own t=0. A nonzero start_time means the
    mux introduced a container-level offset against the master."""
    offset = abs(probe_audio_start_time(final_path))
    return {"ok": offset <= max_offset, "offset_s": round(offset, 4), "max_offset_s": max_offset}


def check_caption_styles(segment_ids: list[str], compositions_dir: Path | None) -> list[str]:
    if compositions_dir is None:
        return []
    styles: set[str] = set()
    for seg_id in segment_ids:
        html_path = compositions_dir / f"{seg_id}.html"
        if not html_path.is_file():
            html_path = compositions_dir / seg_id / "index.html"
        if html_path.is_file():
            styles |= bl_checker.caption_style_signatures(html_path.read_text(encoding="utf-8"))
    return sorted(styles)[1:] if len(styles) > 1 else []


# ═══════════════════════════════════════════════════════════════════════════
# Orchestration
# ═══════════════════════════════════════════════════════════════════════════

def merge(segments: list[dict[str, Any]], parts_dir: Path, audio_path: Path, out_path: Path,
          compositions_dir: Path | None = None, fps: int = FPS) -> dict[str, Any]:
    seg_ids = [s["id"] for s in segments]
    parts = [parts_dir / f"{sid}.mp4" for sid in seg_ids]
    missing = [str(p) for p in parts if not p.is_file()]
    if missing:
        raise MergeError(f"missing part file(s): {missing}")

    mismatches = verify_same_codec(parts)
    if mismatches:
        raise MergeError("parts do not share identical codec params, refusing to concat:\n  "
                          + "\n  ".join(mismatches))

    part_frame_counts = [count_video_frames(p) for p in parts]
    seam_frame_indices: list[int] = []
    running = 0
    for count in part_frame_counts[:-1]:
        running += count
        seam_frame_indices.append(running)

    concat_path = out_path.with_suffix(".concat.mp4")
    concat_copy(parts, concat_path)
    mux_master_audio(concat_path, audio_path, out_path)

    actual_frames = count_video_frames(out_path)
    audio_duration = probe_duration(audio_path)

    frame_count_result = check_frame_count(actual_frames, audio_duration, fps)
    empty_frames = bl_checker.detect_empty_frames(out_path)
    seam_bad = check_seams(empty_frames, seam_frame_indices, fps)
    audio_offset_result = check_audio_offset(out_path)
    caption_bad = check_caption_styles(seg_ids, compositions_dir)

    gates = {
        "frame_count": frame_count_result,
        "empty_frames": empty_frames,
        "seam_failures": seam_bad,
        "audio_offset": audio_offset_result,
        "extra_caption_styles": caption_bad,
    }
    passed = (frame_count_result["ok"] and not empty_frames and not seam_bad
              and audio_offset_result["ok"] and not caption_bad)
    return {
        "pass": passed,
        "out": str(out_path),
        "part_frame_counts": dict(zip(seg_ids, part_frame_counts)),
        "seam_frame_indices": seam_frame_indices,
        "gates": gates,
    }


def failed_gate_names(result: dict[str, Any]) -> list[str]:
    g = result["gates"]
    bad = []
    if not g["frame_count"]["ok"]:
        bad.append("frame_count")
    if g["empty_frames"]:
        bad.append("empty_frames")
    if g["seam_failures"]:
        bad.append("seam_failures")
    if not g["audio_offset"]["ok"]:
        bad.append("audio_offset")
    if g["extra_caption_styles"]:
        bad.append("extra_caption_styles")
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("segments_json")
    ap.add_argument("--parts", required=True, help="dir holding <segment id>.mp4 video-only renders")
    ap.add_argument("--audio", required=True, help="master narration audio, muxed once")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--compositions", default=None,
                     help="dir holding each segment's composed <id>.html or <id>/index.html "
                          "(for the one-caption-style gate; omit to skip that gate)")
    ap.add_argument("--fps", type=int, default=FPS)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    data = json.loads(Path(args.segments_json).read_text(encoding="utf-8"))
    segments = data["segments"] if isinstance(data, dict) else data

    try:
        result = merge(
            segments, Path(args.parts), Path(args.audio), Path(args.out),
            Path(args.compositions) if args.compositions else None, args.fps,
        )
    except MergeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["pass"]:
        print("MERGE OK")
        return 0
    print(f"MERGE REFUSED -- failed gate(s): {failed_gate_names(result)}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

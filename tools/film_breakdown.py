#!/usr/bin/env python3
"""Offline shot tables. Optional dependency: pip install 'scenedetect[opencv]'.

ffmpeg and ffprobe are required. Without PySceneDetect, ffmpeg's scene score
uses a fixed 0.3 threshold (not the ContentDetector threshold).
Storyboard images are naturally sorted by filename; their first sample is t=0.
"""

import argparse
import csv
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys


def command(args):
    return subprocess.run(args, check=True, capture_output=True)


def ffmpeg_input(path):
    # Also prohibit network protocols referenced inside local media containers.
    return ["ffmpeg", "-nostdin", "-hide_banner", "-threads", "1",
            "-filter_threads", "1", "-protocol_whitelist", "file,pipe",
            "-i", str(path)]


def video_duration(path):
    data = json.loads(command([
        "ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
        "-select_streams", "v:0", "-show_entries",
        "stream=duration:format=duration", "-of", "json", str(path)
    ]).stdout)
    if not data.get("streams"):
        raise ValueError("Input has no video stream")
    duration = data["streams"][0].get("duration", "N/A")
    if duration == "N/A":
        duration = data.get("format", {}).get("duration")
    duration = float(duration)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Video duration must be positive and finite")
    return duration


def ffmpeg_cuts(path):
    result = command(ffmpeg_input(path) + [
        "-an", "-vf", "select='gt(scene,0.3)',showinfo", "-fps_mode", "vfr",
        "-f", "null", "-"
    ])
    return [float(value) for value in re.findall(
        r"pts_time:([0-9.eE+\-]+)", result.stderr.decode(errors="replace"))]


def video_cuts(path, threshold):
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        return ffmpeg_cuts(path), "ffmpeg"
    scenes = detect(str(path), ContentDetector(threshold=threshold),
                    start_in_scene=True)
    return [start.get_seconds() for start, _ in scenes[1:]], "pyscenedetect"


def natural_key(path):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.name)]


def storyboard_cuts(folder, interval, threshold):
    frames = sorted((p for p in folder.iterdir() if p.is_file() and
                     p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}),
                    key=natural_key)
    if not frames:
        raise ValueError("Storyboard folder contains no supported images")
    cuts, previous = [], None
    for index, frame in enumerate(frames):
        pixels = command(ffmpeg_input(frame) + [
            "-v", "error", "-vf", "scale=64:64", "-frames:v", "1",
            "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"
        ]).stdout
        if len(pixels) != 64 * 64 * 3:
            raise ValueError(f"Cannot decode storyboard frame: {frame}")
        if previous is not None:
            difference = sum(abs(a - b) for a, b in zip(previous, pixels)) / len(pixels)
            if difference > threshold:
                cuts.append(index * interval)
        previous = pixels
    return cuts, frames


def shot_table(cuts, runtime, method):
    boundaries = [0.0] + sorted({c for c in cuts if 0 < c < runtime}) + [runtime]
    return [dict(shot_no=i, start_s=start, end_s=end, len_s=end-start,
                 method=method)
            for i, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1)]


def summarize(shots, runtime, method):
    lengths = [shot["len_s"] for shot in shots]
    buckets = [0] * math.ceil(runtime / 60)
    for shot in shots:
        buckets[int(shot["start_s"] // 60)] += 1
    return dict(n_shots=len(shots), runtime_s=runtime,
                avg_shot_len_s=statistics.mean(lengths),
                median_shot_len_s=statistics.median(lengths),
                shots_per_min=buckets,
                shots_per_min_definition="Shot starts in [60*i, 60*(i+1)); final bucket may be partial",
                longest_shots=sorted(shots, key=lambda s: -s["len_s"])[:5],
                method=method, coarse=method == "storyboard")


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be positive and finite")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, nargs="?")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=positive, default=27,
                        help="ContentDetector threshold or storyboard mean RGB difference (default 27)")
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--interval-s", type=positive)
    args = parser.parse_args(argv)
    frames = None
    if args.storyboard:
        if not args.storyboard.is_dir() or args.interval_s is None:
            parser.error("--storyboard requires a local folder and --interval-s")
        cuts, frames = storyboard_cuts(args.storyboard, args.interval_s, args.threshold)
        runtime, method = len(frames) * args.interval_s, "storyboard"
    else:
        if args.video is None or not args.video.is_file():
            parser.error("a local video file is required")
        if args.interval_s is not None:
            parser.error("--interval-s requires --storyboard")
        runtime = video_duration(args.video)
        cuts, method = video_cuts(args.video, args.threshold)
    shots = shot_table(cuts, runtime, method)
    summary = summarize(shots, runtime, method)
    summary["threshold"] = 0.3 if method == "ffmpeg" else args.threshold
    if frames:
        summary["notes"] = (
            "Coarse storyboard estimate: natural filename order, first sample at 0; "
            "cuts assigned to the later sample. Cuts between samples can be missed; "
            "motion can create false cuts. Runtime estimated as frame count * interval; "
            "thumbnails use the nearest available sample to each shot midpoint.")
        summary["interval_s"] = args.interval_s
    elif method == "ffmpeg":
        summary["notes"] = "PySceneDetect unavailable; ffmpeg scene score > 0.3; --threshold does not apply."
    thumbs = args.out / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    for shot in shots:
        midpoint = (shot["start_s"] + shot["end_s"]) / 2
        if frames:
            source = frames[min(int(midpoint / args.interval_s + 0.5), len(frames)-1)]
            cmd = ffmpeg_input(source)
        else:
            cmd = ffmpeg_input(args.video)
            # Input seeking avoids decoding the whole film once per thumbnail.
            cmd[-2:-2] = ["-ss", str(midpoint)]
        command(cmd + ["-v", "error", "-y", "-an", "-frames:v", "1",
                       "-vf", "scale=320:-1", "-threads", "1",
                       str(thumbs / f"shot_{shot['shot_no']:04d}.jpg")])
        if not (thumbs / f"shot_{shot['shot_no']:04d}.jpg").is_file():
            raise ValueError(f"No thumbnail produced for shot {shot['shot_no']}")
    with (args.out / "shots.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(shots[0]))
        writer.writeheader()
        writer.writerows(shots)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"film_breakdown: {error}", file=sys.stderr)
        sys.exit(1)

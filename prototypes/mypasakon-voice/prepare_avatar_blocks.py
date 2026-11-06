#!/usr/bin/env python3
"""Prepare 3 x 15s avatar voice segments and lipsync_job.json manifest.

Uses Python standard library and ffmpeg subprocess only.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_WORK_DIR = "/opt/MoonieXHQ/Work/mypasakon-voice/v3"
DEFAULT_VOICE = "/opt/MoonieXHQ/Work/mypasakon-voice/v3/mypasakon-v3-voice-tight.mp3"
DEFAULT_REF_VIDEO = "/opt/MoonieXHQ/Work/mypasakon-voice/v3/avatar_ref.mp4"
MODEL_NAME = "lipsync-1.9.0-beta"
SYNC_MODE = "cut_off"

# (name, start_seconds, duration_seconds) corresponding to 0-15s, 40-55s, 85-100s
SEGMENTS: List[Tuple[str, int, int]] = [
    ("part_01", 0, 15),
    ("part_02", 40, 15),
    ("part_03", 85, 15),
]


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split voice MP3 into 3x15s avatar takes and write lipsync_job.json."
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Path to source voice MP3 (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--ref-video",
        default=DEFAULT_REF_VIDEO,
        help=f"Path to reference avatar MP4 (default: {DEFAULT_REF_VIDEO})",
    )
    parser.add_argument(
        "--work-dir",
        default=DEFAULT_WORK_DIR,
        help=f"Working directory for takes/, parts/, and lipsync_job.json (default: {DEFAULT_WORK_DIR})",
    )
    return parser.parse_args(argv)


def split_mp3_segment(
    voice_path: Path,
    out_path: Path,
    start_sec: int,
    duration_sec: int,
) -> None:
    cmd_reencode = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_sec),
        "-t",
        str(duration_sec),
        "-i",
        str(voice_path),
        "-vn",
        "-c:a",
        "libmp3lame",
        "-q:a",
        "2",
        str(out_path),
    ]
    res = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and out_path.is_file():
        return

    cmd_copy = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_sec),
        "-t",
        str(duration_sec),
        "-i",
        str(voice_path),
        "-vn",
        "-c:a",
        "copy",
        str(out_path),
    ]
    subprocess.run(cmd_copy, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def prepare_blocks(voice: Path, ref_video: Path, work_dir: Path) -> Dict[str, object]:
    voice_abs = Path(os.path.abspath(str(voice)))
    ref_video_abs = Path(os.path.abspath(str(ref_video)))
    work_dir_abs = Path(os.path.abspath(str(work_dir)))

    takes_dir = work_dir_abs / "takes"
    parts_dir = work_dir_abs / "parts"
    takes_dir.mkdir(parents=True, exist_ok=True)
    parts_dir.mkdir(parents=True, exist_ok=True)

    calls: List[Dict[str, str]] = []
    for part_name, start_sec, duration_sec in SEGMENTS:
        out_mp3 = Path(os.path.abspath(str(takes_dir / f"{part_name}.mp3")))
        split_mp3_segment(
            voice_path=voice_abs,
            out_path=out_mp3,
            start_sec=start_sec,
            duration_sec=duration_sec,
        )
        calls.append(
            {
                "name": part_name,
                "audio_file": str(out_mp3),
                "sync_mode": SYNC_MODE,
            }
        )

    job_payload: Dict[str, object] = {
        "model": MODEL_NAME,
        "reference_video": str(ref_video_abs),
        "out_dir": str(parts_dir),
        "calls": calls,
    }

    job_path = work_dir_abs / "lipsync_job.json"
    job_path.write_text(json.dumps(job_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return job_payload


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    job = prepare_blocks(
        voice=Path(args.voice),
        ref_video=Path(args.ref_video),
        work_dir=Path(args.work_dir),
    )
    print(json.dumps(job, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

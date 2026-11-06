#!/usr/bin/env python3
"""Headless Playwright recorder for mypasakon-voice illustrative HTML scenes.

Renders the 4 HTML scenes at 1080x1920 into MP4 clips via ffmpeg and removes
temporary frame directories after encoding.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from playwright.sync_api import sync_playwright

DEFAULT_OUT_DIR = "/opt/MoonieXHQ/Work/mypasakon-voice/footage"
VIEWPORT_WIDTH = 1080
VIEWPORT_HEIGHT = 1920

SCENES: List[Tuple[str, str]] = [
    ("scene1_terminal_start.html", "clip1_terminal.mp4"),
    ("scene2_overnight_log.html", "clip2_log.mp4"),
    ("scene3_candle_chart.html", "clip3_chart.mp4"),
    ("scene4_morning_results.html", "clip4_table.mp4"),
]


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render 4 illustrative 1080x1920 HTML scenes to MP4 via Playwright and ffmpeg."
    )
    parser.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help=f"Output directory for rendered MP4 clips (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--scenes-dir",
        default=str(Path(__file__).resolve().parent),
        help="Directory containing the scene HTML files.",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=24,
        help="Frame rate for captured clips (default: 24).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Duration in seconds for each clip (default: 5.0).",
    )
    return parser.parse_args(argv)


def encode_frames_to_mp4(frames_dir: Path, out_mp4: Path, fps: int) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        str(frames_dir / "frame_%04d.png"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        f"scale={VIEWPORT_WIDTH}:{VIEWPORT_HEIGHT}",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def record_all_scenes(
    scenes_dir: Path,
    out_dir: Path,
    fps: int = 24,
    duration: float = 5.0,
) -> List[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, int(round(fps * duration)))
    written_clips: List[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                device_scale_factor=1,
            )
            page = context.new_page()

            for html_name, mp4_name in SCENES:
                html_path = (scenes_dir / html_name).resolve()
                if not html_path.is_file():
                    raise FileNotFoundError(f"Scene HTML file not found: {html_path}")

                out_mp4 = (out_dir / mp4_name).resolve()
                tmp_frames_dir = Path(
                    tempfile.mkdtemp(prefix=f".tmp_frames_{out_mp4.stem}_", dir=str(out_dir))
                )
                try:
                    page.goto(html_path.as_uri(), wait_until="load")
                    for frame_idx in range(total_frames):
                        time_ms = (frame_idx / float(fps)) * 1000.0
                        page.evaluate(
                            "ms => { if (typeof window.__setTime === 'function') window.__setTime(ms); }",
                            time_ms,
                        )
                        frame_file = tmp_frames_dir / f"frame_{frame_idx:04d}.png"
                        page.screenshot(path=str(frame_file), type="png")

                    encode_frames_to_mp4(tmp_frames_dir, out_mp4, fps=fps)
                    written_clips.append(out_mp4)
                finally:
                    shutil.rmtree(tmp_frames_dir, ignore_errors=True)

            context.close()
        finally:
            browser.close()

    return written_clips


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    scenes_dir = Path(args.scenes_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    clips = record_all_scenes(
        scenes_dir=scenes_dir,
        out_dir=out_dir,
        fps=args.fps,
        duration=args.duration,
    )
    for clip in clips:
        print(f"Rendered: {clip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

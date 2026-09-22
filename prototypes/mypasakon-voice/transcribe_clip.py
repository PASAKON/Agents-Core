#!/usr/bin/env python3
"""Download one MYPASAKON rawcut clip from Drive, extract audio, transcribe via
fal-ai/whisper, save the transcript, delete local media. One clip per run —
caller loops over indices so at most one 100-600MB video sits on disk at a time.

Usage: python3 transcribe_clip.py <index>
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gdrive-bridge"))
from ilag_sync import access_token  # noqa: E402

import fal_client  # noqa: E402

HERE = Path(__file__).resolve().parent
SCRATCH = Path(os.environ.get("MYPASAKON_SCRATCH", "/tmp/mypasakon-voice-scratch"))
SCRATCH.mkdir(parents=True, exist_ok=True)
TRANSCRIPTS_DIR = HERE / "transcripts"
TRANSCRIPTS_DIR.mkdir(exist_ok=True)


def slug(name: str) -> str:
    s = re.sub(r"[|\[\]!?]", " ", name)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s[:60].strip("-")


def download_video(file_id: str, dest: Path) -> None:
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token()}"})
    with urllib.request.urlopen(req, timeout=300) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def extract_audio(video_path: Path, audio_path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)],
        check=True, capture_output=True,
    )


def transcribe(audio_path: Path) -> str:
    audio_url = fal_client.upload_file(audio_path)
    result = fal_client.subscribe(
        "fal-ai/whisper",
        arguments={"audio_url": audio_url, "task": "transcribe", "language": "th"},
        with_logs=False,
    )
    return result.get("text", "")


def main() -> int:
    idx = int(sys.argv[1])
    clips = json.loads((HERE / "rawcut_videos.json").read_text(encoding="utf-8"))
    item = next(c for c in clips if c["i"] == idx)
    out_path = TRANSCRIPTS_DIR / f"{idx}-{slug(item['clip'])}.txt"
    if out_path.exists() and out_path.stat().st_size > 0:
        print(f"[skip] {out_path} already exists")
        return 0

    video_path = SCRATCH / f"{idx}.mp4"
    audio_path = SCRATCH / f"{idx}.mp3"
    try:
        print(f"[{idx}] downloading {item['clip'][:60]!r} id={item['id']}")
        download_video(item["id"], video_path)
        size_mb = video_path.stat().st_size / (1 << 20)
        print(f"[{idx}] downloaded {size_mb:.1f} MB, extracting audio")
        extract_audio(video_path, audio_path)
        video_path.unlink()
        print(f"[{idx}] transcribing via fal-ai/whisper")
        text = transcribe(audio_path)
        out_path.write_text(text, encoding="utf-8")
        print(f"[{idx}] saved {len(text)} chars -> {out_path}")
    finally:
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

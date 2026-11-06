#!/usr/bin/env python3
"""Assemble the 102.7-second MYPASAKON EP1 vertical master with ffmpeg.

The normal mode uses the three paid lipsync outputs.  ``--preview-no-lipsync``
is deliberately local and cost-free: it reuses ``avatar_ref.mp4`` for the
three presenter windows so editorial timing, subtitles, and the 9:16 delivery
can be reviewed before a lipsync purchase is approved.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


WORK = Path("/opt/MoonieXHQ/Work/mypasakon-voice")
V3 = WORK / "v3"
FOOTAGE = WORK / "footage"
VOICE = V3 / "mypasakon-v3-voice-tight.mp3"
AVATAR_REF = V3 / "avatar_ref.mp4"
OUTPUT = V3 / "mypasakon-ep1-final.mp4"
DURATION = 102.7

# One short thought per line.  The ASS header uses WrapStyle: 2, the subtitle
# equivalent of CSS white-space: nowrap, and leaves TikTok's bottom controls
# clear by placing captions around y=1380 in a 1920-high frame.
CAPTIONS = [
    (0.0, 7.5, "AI ที่ผมใช้เทรดจริงมาแปดเดือน คือ Claude Code นะครับ"),
    (7.5, 15.0, "ลองมาหมดแล้ว แต่ตัวนี้ถูกใจที่สุดนะครับ"),
    (15.0, 22.5, "ผู้ช่วยวิเคราะห์การเทรด ทำสถิติ และคำนวณความเสี่ยง"),
    (22.5, 32.0, "สั่งให้ทดสอบข้อมูลเก่าย้อนหลังได้หมดเลย"),
    (32.0, 40.0, "ที่ชอบที่สุดคือ มันไม่หลับไม่นอนนะครับ"),
    (40.0, 47.5, "ก่อนนอน ผมสั่งให้วิจัยกลยุทธ์ย้อนหลังห้าปี"),
    (47.5, 55.0, "แล้วผมก็ไปนอน รอผลตอนเช้านะครับ"),
    (55.0, 62.5, "ตื่นมาเจอกราฟย้อนหลังที่มันไล่ดูให้ทั้งคืน"),
    (62.5, 72.5, "ทดสอบเป็นหมื่นๆ รอบ แล้วสรุปเป็นตารางให้แล้ว"),
    (72.5, 85.0, "บอกได้ว่ากลยุทธ์ไหนอยู่รอด และพังตอนไหนนะครับ"),
    (85.0, 92.5, "งานที่ทำคนเดียวเป็นเดือน มันทำให้เสร็จได้ในคืนเดียว"),
    (92.5, 100.0, "ต่อจากนี้ ผมจะสอนใช้ AI เป็นผู้ช่วยตัวเองนะครับ"),
    (100.0, 102.7, "คอมเมนต์คำว่า Claude ไว้ได้เลยนะครับ"),
]


def ass_time(seconds: float) -> str:
    hours, rem = divmod(seconds, 3600)
    minutes, rem = divmod(rem, 60)
    return f"{int(hours)}:{int(minutes):02d}:{rem:05.2f}"


def escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def write_captions(path: Path) -> None:
    header = """[Script Info]
; TikTok safe-zone captions. WrapStyle: 2 means no automatic wrapping.
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: SafeCaption,Noto Sans Thai,54,&H00FFFFFF,&H000000FF,&H00101010,&H90000000,1,0,0,0,100,100,0,0,1,3,1,2,90,90,430,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    events = "".join(
        f"Dialogue: 0,{ass_time(start)},{ass_time(end)},SafeCaption,,0,0,0,,{escape_ass(text)}\n"
        for start, end, text in CAPTIONS
    )
    path.write_text(header + events, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=WORK,
        help=f"Directory containing v3/ and footage/ (default: {WORK}).",
    )
    parser.add_argument("--preview-no-lipsync", action="store_true", help="Use avatar_ref.mp4 for all avatar windows.")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Output MP4 path.")
    return parser.parse_args()


def require_files(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise SystemExit("Missing required media:\n" + "\n".join(f"- {item}" for item in missing))


def lipsync_part(v3: Path, name: str) -> Path:
    """Use the actual fal extension; MP4 is the expected and diagnostic default."""
    for extension in (".mp4", ".mov", ".webm"):
        candidate = v3 / "parts" / f"{name}{extension}"
        if candidate.is_file():
            return candidate
    return v3 / "parts" / f"{name}.mp4"


def main() -> int:
    args = parse_args()
    work_dir = args.work_dir.resolve()
    v3 = work_dir / "v3"
    footage = work_dir / "footage"
    voice = v3 / "mypasakon-v3-voice-tight.mp3"
    avatar_ref = v3 / "avatar_ref.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")

    clips = [
        (avatar_ref if args.preview_no_lipsync else lipsync_part(v3, "part_01"), 15.0),
        (footage / "clip1_terminal.mp4", 12.5),
        (footage / "clip2_log.mp4", 12.5),
        (avatar_ref if args.preview_no_lipsync else lipsync_part(v3, "part_02"), 15.0),
        (footage / "clip3_chart.mp4", 15.0),
        (footage / "clip4_table.mp4", 15.0),
        (avatar_ref if args.preview_no_lipsync else lipsync_part(v3, "part_03"), 15.0),
        (footage / "clip4_table.mp4", 2.7),
    ]
    require_files([voice, *(path for path, _ in clips)])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mypasakon-ep1-") as temp_dir:
        subtitles = Path(temp_dir) / "captions.ass"
        write_captions(subtitles)
        # Loop each visual at demuxer level so five-second footage cleanly fills
        # its assigned editorial window.  Every leg is normalized to 1080x1920.
        cmd = [ffmpeg, "-y"]
        for path, _duration in clips:
            cmd.extend(["-stream_loop", "-1", "-i", str(path)])
        cmd.extend(["-i", str(voice)])
        filter_parts = []
        labels = []
        for index, (_path, duration) in enumerate(clips):
            label = f"v{index}"
            labels.append(f"[{label}]")
            filter_parts.append(
                f"[{index}:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                f"crop=1080:1920,setsar=1,trim=duration={duration},setpts=PTS-STARTPTS[{label}]"
            )
        filter_parts.append("".join(labels) + f"concat=n={len(clips)}:v=1:a=0,subtitles='{subtitles}'[video]")
        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", "[video]", "-map", f"{len(clips)}:a:0",
            "-t", str(DURATION), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(args.output),
        ])
        print("Running:", " ".join(cmd))
        subprocess.run(cmd, check=True)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

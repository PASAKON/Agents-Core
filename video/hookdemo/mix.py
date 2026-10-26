"""Mix the ILAG hook demo (task-ee1dbcf0): the clips' own sound (already low, from ilag_cut) + ONE narration file, then
loudnorm to -16 LUFS.  The narration starts at 0 and is not sped up: its alignment times are the timeline times.

usage: mix.py <work dir> --audio take.mp3 --out mixed.mp4 [--print]
reads work/build/seg/joined.mp4 (ilag_cut encode); no overlay is added, so the kit title card carries no watermark.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("work")
ap.add_argument("--audio", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--voice-gain", default="1.6")
ap.add_argument("--print", action="store_true")
a = ap.parse_args()
W = Path(a.work)
total = json.loads((W / "timing.json").read_text())["total_s"]
fc = (f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={a.voice_gain}[vo];"
      "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[bed];"
      f"[bed][vo]amix=inputs=2:duration=first:normalize=0,atrim=0:{total},asetpts=PTS-STARTPTS,"
      "loudnorm=I=-16:TP=-1.5:LRA=11[a];[0:v]setsar=1,format=yuv420p[v]")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(W / "build/seg/joined.mp4"), "-i", a.audio, "-filter_complex", fc,
       "-map", "[v]", "-map", "[a]", "-t", str(total),
       "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "24",
       "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", a.out]
if a.print:
    print(" ".join(cmd))
    sys.exit()
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.returncode, r.stderr[-1500:])
sys.exit(r.returncode)

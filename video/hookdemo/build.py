#!/usr/bin/env python3
"""Whole chain of the ILAG hook demo (task-ee1dbcf0), one narration file in, three deliverables out:
  one audio file + alignment -> align.py phrase times -> make_edl.py (edl.json, timing.json) -> ilag_cut cards + encode
  -> mix.py (narration + clip bed, -16 LUFS) -> 720p H.264 -> 2 fps contact sheet.

usage: build.py <hookdemo dir> --audio take.mp3 --align take.json --out out/rehearsal --name hook-rehearsal
         [--ilag-cut tools/ilag_cut.py] [--kit .../brands/ilag/templates] [--py CORE_VENV_PYTHON]
Run it under the render lock, after free -m:   flock /opt/MoonieXHQ/Work/.bl-render.lock nice -n 19 python3 build.py ...
(ilag_cut's own --lock is not used: flock on the same file from a child would wait for its parent forever.)
Result in <out>: <name>-720p.mp4, <name>-master-1080.mp4, <name>-contact-2fps.jpg, timing.json.
"""
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = "/opt/MoonieXHQ/Agents/Core"
ap = argparse.ArgumentParser()
ap.add_argument("hookdemo")
ap.add_argument("--audio", required=True)
ap.add_argument("--align", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--name", default="hook-rehearsal")
ap.add_argument("--ilag-cut", default=f"{CORE}/worktrees/mooniex-agents__developer__task-b7e13b61/tools/ilag_cut.py")
# the only copy whose render_kit.py has build_kit() (PR #468); main's script-style render_kit.py crashes ilag_cut
ap.add_argument("--kit", default=f"{CORE}/worktrees/mooniex-agents__developer__task-b7e13b61/knowledge/brand-knowledge/brands/ilag/templates")
ap.add_argument("--py", default=f"{CORE}/.venv/bin/python")
a = ap.parse_args()
H, OUT = Path(a.hookdemo).resolve(), Path(a.out)
if not OUT.is_absolute():
    OUT = H / OUT
OUT.mkdir(parents=True, exist_ok=True)
WORK, B = H / "work", H / "work/build"


SFX = {  # synthesised, $0: the kit has no sfx files yet (thud on every cut, whoosh on the rewcard, boom on the title)
    "thud": ["-f", "lavfi", "-i", "aevalsrc='0.9*sin(2*PI*(70+90*exp(-t*30))*t)*exp(-t*14)':d=0.3:s=48000"],
    "boom": ["-f", "lavfi", "-i", "aevalsrc='0.9*sin(2*PI*(45+60*exp(-t*6))*t)*exp(-t*3.2)':d=1.4:s=48000"],
    "whoosh": ["-f", "lavfi", "-i", "anoisesrc=d=0.7:c=pink:r=48000:a=0.8", "-af",
               "highpass=f=400,lowpass=f=5000,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.35"],
}


def run(cmd, label):
    print(f"== {label}", flush=True)
    r = subprocess.run([str(c) for c in cmd])
    if r.returncode:
        sys.exit(f"build.py: {label} failed with exit {r.returncode}")


(WORK / "sfx").mkdir(parents=True, exist_ok=True)
for name, args in SFX.items():
    if not (WORK / "sfx" / f"{name}.wav").exists():
        run(["ffmpeg", "-v", "error", "-y", *args, "-ac", "2", WORK / "sfx" / f"{name}.wav"], f"sfx {name}")
run(["python3", HERE / "make_edl.py", WORK, "--audio", a.audio, "--align", a.align], "alignment -> edl.json + timing.json")
run([a.py, a.ilag_cut, "cards", WORK / "edl.json", "--out", B, "--kit", a.kit, "--root", H], "kit cards")
run(["python3", a.ilag_cut, "encode", WORK / "edl.json", "--out", B, "--root", H], "encode segments")
master = OUT / f"{a.name}-master-1080.mp4"
run(["python3", HERE / "mix.py", WORK, "--audio", a.audio, "--out", master], "mix + loudnorm")
p720 = OUT / f"{a.name}-720p.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", master, "-vf", "scale=720:1280:flags=lanczos,setsar=1,format=yuv420p", "-r", "24",
     "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p",
     "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", p720], "720p")
total = json.loads((WORK / "timing.json").read_text())["total_s"]
rows = math.ceil(total * 2 / 6)
run(["ffmpeg", "-v", "error", "-y", "-i", p720, "-vf",
     "fps=2,scale=270:-1,drawtext=text='%{pts\\:flt}':fontcolor=yellow:fontsize=18:x=4:y=4:box=1:boxcolor=black@0.5,"
     f"tile=6x{rows}", "-frames:v", "1", "-q:v", "3", OUT / f"{a.name}-contact-2fps.jpg"], "contact sheet 2 fps")
shutil.copy(WORK / "timing.json", OUT / "timing.json")
mib = p720.stat().st_size / 2 ** 20
print(f"done: {p720.name} {mib:.1f} MiB (limit 30)")
sys.exit(0 if mib <= 30 else "720p over 30 MiB")

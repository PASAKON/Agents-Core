import json, re, subprocess, sys
from pathlib import Path
H = Path(sys.argv[1]); B = H / "work/build"
T = json.loads((H / "work/timing.json").read_text())
DUR = json.loads((H / "work/vo/durs.json").read_text())
wm = next((B / "cards").glob("wm-*.png"))
inputs = ["-i", str(B / "seg/joined.mp4"), "-loop", "1", "-framerate", "24", "-t", "15", "-i", str(wm)]
chains, labels = [], []
n = 2
for i, row in enumerate(DUR, 1):
    for j, _ in enumerate(row, 1):
        inputs += ["-i", str(H / f"work/vo/{i}{j}.wav")]
        ms = int(round(T["phrase_start"][f"{i}.{j}"] * 1000))
        chains.append(f"[{n}:a]aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms},volume=1.6[v{n}]")
        labels.append(f"[v{n}]"); n += 1
gain = sys.argv[2] if len(sys.argv) > 2 else "loudnorm=I=-16:TP=-1.5:LRA=11"
fc = (";".join(chains) +
      f";[0:a]aformat=sample_rates=48000:channel_layouts=stereo[bed];[bed]{''.join(labels)}amix=inputs={n-1}:duration=first:normalize=0,"
      f"atrim=0:15,asetpts=PTS-STARTPTS,{gain}[a];"
      "[0:v][1:v]overlay=enable='between(t,12.0,14.0)',setsar=1,format=yuv420p[v]")
out = sys.argv[3] if len(sys.argv) > 3 else str(H / "work/mixed.mp4")
cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-t", "15",
       "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "24",
       "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", out]
if "--print" in sys.argv: print(" ".join(cmd)); sys.exit()
r = subprocess.run(cmd, capture_output=True, text=True); print(r.returncode, r.stderr[-1500:])

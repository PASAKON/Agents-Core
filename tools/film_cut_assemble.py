#!/usr/bin/env python3
"""Assemble an episode cut from a JSON manifest (zero-model: ffmpeg only).

Built for «บ้านนี้มีมีมี่» (EP1 cut v2 approved by the CEO 2026-10-01); works for any 9:16 short film made of
generated clips plus text cards.  Recipe and traps: skill CMO_Workflow_ShortFilm, Step 9 · Edit.

  tools/film_cut_assemble.py docs/scripts/khaoniao-ep1-cut-manifest.json --var PROD=... --var RS1=... --var CARDS=... --var OUT=...

Manifest keys
  out          output mp4 (variables ${NAME} are filled from --var NAME=value or the environment)
  size         [w, h] of the cut, default [720, 1280];  fps default 24
  mid_roll_s   second at which Facebook may break the video (default 60); the tool says what falls there
  segments     in order, each either
                 {"clip": path, "ss": start_s, "dur": seconds, "fade_out": s}   (clip with audio; ss/fade_out optional)
                 {"card": png, "dur": seconds}                                  (still card, silent)
  overlays     [{"png": transparent card, "segment": index, "dur": seconds}]    (label laid over the start of a segment)

It prints every segment's start time and warns when (a) the first segment is a card (CEO 2026-10-01: nothing but the
hook may stand in the first 3 s), (b) a card starts before 3 s, (c) the mid-roll second lands on plain footage.
The music bed is a separate step: tools/film_music_mix.sh <cut> <music> <out>.
"""
import argparse, json, os, string, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("manifest")
ap.add_argument("--var", action="append", default=[], help="NAME=value for ${NAME} in the manifest")
ap.add_argument("--out", help="override the manifest's out path")
ap.add_argument("--print-only", action="store_true", help="print the plan and the ffmpeg command, render nothing")
a = ap.parse_args()

vars_ = dict(os.environ); vars_.update(v.split("=", 1) for v in a.var)
def fill(x): return string.Template(x).substitute(vars_) if isinstance(x, str) else x
m = json.load(open(a.manifest, encoding="utf-8"))
W, H = m.get("size", [720, 1280]); FPS = m.get("fps", 24); MID = m.get("mid_roll_s", 60)
out = a.out or fill(m["out"])

cmd = ["ffmpeg", "-y", "-v", "error"]; fc = []; labels = ""; k = 0; t = 0.0; plan = []
for i, s in enumerate(m["segments"]):
    dur = float(s["dur"]); plan.append((i, "card" if "card" in s else "clip", round(t, 2), round(t + dur, 2), os.path.basename(fill(s.get("card") or s["clip"]))))
    if "clip" in s:
        fo = float(s.get("fade_out", 0.03))
        if s.get("ss"): cmd += ["-ss", str(s["ss"])]
        cmd += ["-t", str(dur), "-i", fill(s["clip"])]
        fc.append(f"[{k}:v]scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},format=yuv420p[v{i}]")
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,afade=t=in:d=0.03,afade=t=out:st={dur - fo:.2f}:d={fo}[a{i}]")
        k += 1
    else:
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(dur), "-i", fill(s["card"]), "-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=48000:cl=mono"]
        fc.append(f"[{k}:v]scale={W}:{H}:flags=lanczos,setsar=1,fps={FPS},format=yuv420p[v{i}]")
        fc.append(f"[{k + 1}:a]aformat=channel_layouts=mono[a{i}]")
        k += 2
    labels += f"[v{i}][a{i}]"; t += dur
for j, o in enumerate(m.get("overlays", [])):
    d = float(o["dur"]); seg = int(o["segment"])
    cmd += ["-loop", "1", "-framerate", str(FPS), "-t", str(d), "-i", fill(o["png"])]
    fc.append(f"[{k}:v]scale={W}:{H}:flags=lanczos,format=rgba,fade=t=in:st=0:d=0.3:alpha=1,fade=t=out:st={d - 0.3:.1f}:d=0.3:alpha=1[ov{j}]")
    fc = [x.replace(f"[v{seg}]", f"[v{seg}pre{j}]") if x.endswith(f"[v{seg}]") else x for x in fc]
    fc.append(f"[v{seg}pre{j}][ov{j}]overlay=0:0:eof_action=pass,format=yuv420p[v{seg}]")
    k += 1
fc.append(f"{labels}concat=n={len(m['segments'])}:v=1:a=1[v][a]")
cmd += ["-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "21", "-preset", "medium",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]

for p in plan: print("%2d %-4s %7.2f-%7.2f  %s" % p)
print("total %.2f s" % t)
if plan[0][1] == "card": print("WARN first segment is a card: the hook must start at frame 0 (CMO_Standard_Story_FamilyDogSeries §2 item 10)")
for p in plan:
    if p[1] == "card" and p[2] < 3 and p[0] > 0: print("WARN card #%d starts at %.1f s, before the 3-second hook is over" % (p[0], p[2]))
at = [p for p in plan if p[2] <= MID < p[3]]
if at: print("mid-roll %.0f s falls in %s #%d (%s)%s" % (MID, at[0][1], at[0][0], at[0][4], "" if at[0][1] == "card" else "  WARN: plain footage — put a card or an open question here"))
else: print("WARN mid-roll %.0f s is outside the cut" % MID)
if a.print_only: print(" ".join(cmd)); sys.exit(0)
subprocess.run(cmd, check=True); print("wrote", out)

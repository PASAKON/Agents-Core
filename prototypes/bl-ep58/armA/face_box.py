#!/usr/bin/env python3
"""Face box (canvas px) of the matted COMP avatar, per lipsync take, for bl_checker --face-box.
Head = from the topmost opaque row to the neck, the narrowest row of the upper body (alpha profile of the matte,
sampled twice a second inside the COMP windows). Matte is 1080x1920, drawn at height 56%, translateX(-6%):
canvas = matte * 0.56, x - 0.06 * 605, y + 845 (template .avatar-comp)."""
import subprocess, sys, json
import numpy as np

M = "/opt/MoonieXHQ/Work/bl-ep58/generator/media/matte/%s-matte.webm"
WINDOWS = {"lip_a": (0.0, 15.9, 0.0), "lip_b": (39.28, 55.9, 38.77), "lip_c": (88.69, 95.0, 80.84)}  # abs start, end, take offset
S = 0.56
def frame_alpha(name, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-ss", f"{t}", "-i", M % name, "-frames:v", "1",
                          "-vf", "format=rgba,alphaextract,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080) if len(raw) == 1920 * 1080 else None
out = {}
for name, (a, b, off) in WINDOWS.items():
    boxes = []
    for t in np.arange(a, b, 0.5):
        al = frame_alpha(name, round(float(t - off), 2))
        if al is None: continue
        rows = (al > 128).sum(axis=1)
        ys = np.where(rows > 8)[0]
        if len(ys) == 0: continue
        top = ys[0]
        # neck: narrowest row in the 120..520 px below the head top, ignoring a row's first/last arm spill
        seg = rows[top + 120: top + 520]
        neck = top + 120 + int(np.argmin(seg))
        cols = np.where((al[top:neck] > 128).any(axis=0))[0]
        boxes.append((cols[0], top, cols[-1], neck))
    b = np.array(boxes)
    x0, y0, x1, y1 = b[:, 0].min(), b[:, 1].min(), b[:, 2].max(), b[:, 3].max()
    cx0, cy0, cx1, cy1 = x0 * S - 0.06 * 1080 * S, y0 * S + 845, x1 * S - 0.06 * 1080 * S, y1 * S + 845
    out[name] = [round(cx0), round(cy0), round(cx1 - cx0), round(cy1 - cy0)]
    print(name, len(boxes), "matte", (x0, y0, x1, y1), "canvas x,y,w,h", out[name])
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "/dev/stdout", "w"))

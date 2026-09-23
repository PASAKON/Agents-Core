"""Frame-to-frame difference signal for the reference edit — finds shot
boundaries (hard cut = 1-frame spike, dissolve = multi-frame ramp, shrink/
slide = smooth low-diff motion already caught by the head tracker).

Usage: python cutdetect.py ref.mp4 > measurements/frame_diff.csv
Output columns: frame,t,diff   (diff = mean abs gray delta vs prev frame, 0-1)
"""
import subprocess, sys
import numpy as np

SRC = sys.argv[1]
W, H = 180, 320
DUR = 85.24
N = int(round(DUR * 30))

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", SRC, "-frames:v", str(N),
     "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
    capture_output=True).stdout
arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32) / 255.0

print("frame,t,diff")
prev = None
for i, f in enumerate(arr):
    d = 0.0 if prev is None else float(np.abs(f - prev).mean())
    print(f"{i},{i/30:.4f},{d:.5f}")
    prev = f

"""Frame-to-frame diff restricted to one region of the frame — catches plate
swaps / text pop-in / highlight sweeps that a full-frame diff dilutes because
the avatar (which is moving/talking on every frame) dominates the signal.

Usage: python roi_diff.py ref.mp4 y0 y1 x0 x1 > measurements/roi_TAG.csv
y0,y1,x0,x1 are fractions of frame height/width (0..1).
Output columns: frame,t,diff
"""
import subprocess, sys
import numpy as np

SRC = sys.argv[1]
Y0, Y1, X0, X1 = (float(x) for x in sys.argv[2:6])
W, H = 180, 320
DUR = 85.24
N = int(round(DUR * 30))

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", SRC, "-frames:v", str(N),
     "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
    capture_output=True).stdout
arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32) / 255.0
y0, y1 = int(Y0 * H), int(Y1 * H)
x0, x1 = int(X0 * W), int(X1 * W)
roi = arr[:, y0:y1, x0:x1]

print("frame,t,diff")
prev = None
for i, f in enumerate(roi):
    d = 0.0 if prev is None else float(np.abs(f - prev).mean())
    print(f"{i},{i/30:.4f},{d:.5f}")
    prev = f

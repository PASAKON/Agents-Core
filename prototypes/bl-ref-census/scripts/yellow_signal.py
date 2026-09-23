"""Fraction of frame pixels that are yellow (kit's --yellow #F4DF14, R&G high,
B low) per frame — a direct signal for highlighter-sweep / yellow-chip onsets,
which a grayscale diff can miss when the sweep is a color change more than a
luminance change.

Usage: python yellow_signal.py ref.mp4 > measurements/yellow_signal.csv
Output columns: frame,t,yellow_frac
"""
import subprocess, sys
import numpy as np

SRC = sys.argv[1]
W, H = 216, 384
DUR = 85.24
N = int(round(DUR * 30))

raw = subprocess.run(
    ["ffmpeg", "-v", "error", "-i", SRC, "-frames:v", str(N),
     "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    capture_output=True).stdout
arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.int16)

r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
# yellow: high R, high G, low B, R~G
mask = (r > 170) & (g > 160) & (b < 110) & (np.abs(r - g) < 60)
frac = mask.reshape(mask.shape[0], -1).mean(axis=1)

print("frame,t,yellow_frac")
for i, f in enumerate(frac):
    print(f"{i},{i/30:.4f},{f:.5f}")

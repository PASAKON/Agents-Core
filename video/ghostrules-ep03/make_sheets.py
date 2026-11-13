#!/usr/bin/env python3
"""Contact sheets for EP3. usage: make_sheets.py OUT_DIR MP4
 sheet_shots.jpg : one numbered frame per shot (mid-shot, read from the final mp4)
 sheet_cmo.jpg   : a frame every 30 s + frames 6400..6420 (the jump-scare cut at 6410)"""
import sys, json, subprocess, numpy as np, cv2
OUT, MP4 = sys.argv[1], sys.argv[2]
shots = json.load(open(f"{OUT}/shots.json")); FPS = 30
def frame(f, w=384):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{f / FPS:.4f}", "-i", MP4, "-frames:v", "1", "-vf", f"scale={w}:-1", "-f", "image2pipe", "-vcodec", "bmp", "-"], capture_output=True)
    return cv2.imdecode(np.frombuffer(r.stdout, np.uint8), 1)
def label(img, txt):
    cv2.rectangle(img, (0, 0), (img.shape[1], 22), (0, 0, 0), -1); cv2.putText(img, txt, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA); return img
def tile(imgs, cols):
    h, w = imgs[0].shape[:2]; rows = []
    for i in range(0, len(imgs), cols):
        row = imgs[i:i + cols]; row += [np.zeros_like(imgs[0])] * (cols - len(row)); rows.append(np.hstack(row))
    return np.vstack(rows)
tiles = []
for n, r in enumerate(shots, 1):
    f = (r["f0"] + r["f1"]) // 2; tiles.append(label(frame(f), f"{n:02d} {r['id']} {r['plate']} f{f}"))
cv2.imwrite(f"{OUT}/sheet_shots.jpg", tile(tiles, 8), [cv2.IMWRITE_JPEG_QUALITY, 82])
total = shots[-1]["f1"]; tiles = []
for f in list(range(0, total, 30 * FPS)):
    tiles.append(label(frame(f), f"t={f // FPS}s f{f}"))
for f in range(6400, 6421): tiles.append(label(frame(f, 320), f"f{f}" + (" STING CUT" if f == 6410 else "")))
w = tiles[0].shape[1]; tiles = [cv2.resize(t, (w, int(t.shape[0] * w / t.shape[1]))) for t in tiles]
cv2.imwrite(f"{OUT}/sheet_cmo.jpg", tile(tiles, 8), [cv2.IMWRITE_JPEG_QUALITY, 82])
print("sheets ok", len(shots))

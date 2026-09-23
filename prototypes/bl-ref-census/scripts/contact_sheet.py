"""Grab frames at given timestamps and tile them into one labeled contact
sheet (Pillow only — no ffmpeg drawtext, no cv2). Used to eyeball shot
boundaries, avatar mode, plate content and text blocks before writing them
into census.json. Confirmation output only — never committed as media.

Usage: python contact_sheet.py ref.mp4 out.jpg "0.0,1.8,1.867,1.9,5.2" [cols] [thumb_w]
"""
import subprocess, sys
from PIL import Image, ImageDraw

SRC, OUT = sys.argv[1], sys.argv[2]
TIMES = [float(x) for x in sys.argv[3].split(",")]
COLS = int(sys.argv[4]) if len(sys.argv) > 4 else 5
TW = int(sys.argv[5]) if len(sys.argv) > 5 else 270  # thumb width; height = TW*16/9


def grab(t):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", SRC, "-frames:v", "1",
         "-vf", f"scale={TW}:-1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True).stdout
    import io
    return Image.open(io.BytesIO(raw)).convert("RGB")


thumbs = [grab(t) for t in TIMES]
th = thumbs[0].height
rows = (len(thumbs) + COLS - 1) // COLS
sheet = Image.new("RGB", (TW * COLS, (th + 18) * rows), (20, 20, 20))
d = ImageDraw.Draw(sheet)
for i, (t, im) in enumerate(zip(TIMES, thumbs)):
    x, y = (i % COLS) * TW, (i // COLS) * (th + 18)
    sheet.paste(im, (x, y + 18))
    d.rectangle([x, y, x + TW, y + 17], fill=(0, 0, 0))
    d.text((x + 2, y + 2), f"t={t:.3f}", fill=(255, 255, 0))
sheet.save(OUT, quality=88)
print(OUT, sheet.size)

"""Lift the existing ILAG Page logo off its black square: the disc inside the gold ring stays opaque,
the glow outside the ring becomes see-through gold (alpha = brightness over black). Nothing is redrawn."""
import sys
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
a = np.asarray(Image.open(src).convert("RGB")).astype(float)
h, w, _ = a.shape
cy, cx = (h - 1) / 2, (w - 1) / 2
yy, xx = np.mgrid[0:h, 0:w]
d = np.hypot(xx - cx, yy - cy)
R_RING, R_OUT = 461.0, 500.0           # ring's outer edge at x=80 of 1080; glow fades out by x~44
m = a.max(axis=2)
alpha = np.where(d <= R_RING, 255.0, m)
alpha = np.where(d > R_OUT, 0.0, alpha)
edge = np.clip(R_RING + 1.0 - d, 0, 1)   # 1 px blend between the opaque disc and the glow
alpha = edge * 255.0 + (1 - edge) * alpha
safe = np.maximum(m, 1.0)[..., None]
rgb = np.where((d > R_RING)[..., None], np.clip(a * 255.0 / safe, 0, 255), a)
img = Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), "RGBA")
img = img.crop((int(cx - R_OUT), int(cy - R_OUT), int(cx + R_OUT) + 1, int(cy + R_OUT) + 1))
img.save(out)
al = np.asarray(img)[:, :, 3]
print("saved", img.size, "corner", al[0, 0], "glow sample", al[al.shape[0] // 2, 20:44:4].tolist(), "centre", al[500, 500])

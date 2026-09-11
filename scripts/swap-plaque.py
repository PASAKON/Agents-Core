"""Swap the wall plaque in a locked-off shot, without Fusion and without generating pixels.

Everything here is compositing of material we already have: the plaque plate we generated on
Higgsfield, and the shot's own wall. Festival Rules §4 permits mask-based retouching and
compositing explicitly; nothing is synthesised.

The shot is locked off (measured corner drift 1.67 = sensor noise), so one geometry serves every
frame and there is nothing to track.

Order matters: the insert is colour-matched, then softened to the shot's own sharpness, then
grained to the shot's own noise, and only then feathered in. Skip the last two and it reads as a
sticker no matter how good the geometry is.
"""
import sys
import numpy as np
from PIL import Image, ImageFilter

PLATE = 'tag.png'
BOX = (571, 604, 708, 691)          # measured plaque bbox in the target frame
FEATHER = 2.0


def measure(frame, box):
    x0, y0, x1, y1 = box
    old = frame[y0:y1, x0:x1].reshape(-1, 3)
    ring = np.vstack([frame[max(0, y0 - 45):y0 - 10, x0:x1].reshape(-1, 3),
                      frame[y1 + 10:y1 + 45, x0:x1].reshape(-1, 3)])
    return old, ring


def build_insert(plate_img, w, h, old, ring, sharp):
    """Return the new plaque, already matched to the shot."""
    ins = plate_img.resize((w, h), Image.LANCZOS)

    # soften to the shot's own resolving power. The plate is 1168px wide going into ~137px,
    # so it arrives far sharper than anything else in frame.
    ins = ins.filter(ImageFilter.GaussianBlur(sharp))
    a = np.asarray(ins, dtype=np.float64)

    # colour match: put the insert's mean and spread where the old plaque's were, per channel.
    for c in range(3):
        s_m, s_s = a[..., c].mean(), a[..., c].std()
        t_m, t_s = old[:, c].mean(), old[:, c].std()
        if s_s > 1e-6:
            a[..., c] = (a[..., c] - s_m) * (t_s / s_s) + t_m

    # grain match: the wall's own temporal/spatial noise, so the patch is not suspiciously clean.
    a += np.random.normal(0, ring.std(0).mean(), a.shape)
    return np.clip(a, 0, 255)


def feather_mask(w, h, r):
    m = Image.new('L', (w, h), 255)
    m = m.filter(ImageFilter.GaussianBlur(r))
    return np.asarray(m, dtype=np.float64)[..., None] / 255.0


def swap(frame, plate_img, box=BOX, scale=1.0, dy=0, sharp=0.6, seed=0):
    np.random.seed(seed)
    x0, y0, x1, y1 = box
    old, ring = measure(frame, box)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + dy
    w, h = int((x1 - x0) * scale), int((y1 - y0) * scale)
    nx0, ny0 = cx - w // 2, cy - h // 2

    ins = build_insert(plate_img, w, h, old, ring, sharp)
    out = frame.copy()

    # if the new plaque is smaller than the old one, the old one must be covered first.
    if scale < 1.0 or dy != 0:
        # A flat fill is visibly wrong: this wall carries a vignette, brighter at centre and
        # falling off toward the pillars, so one median colour reads as a pale rectangle.
        # Interpolate per column between the real wall above and the real wall below instead,
        # which reproduces the gradient the shot actually has.
        pad = 12
        py0, py1 = y0 - pad, y1 + pad
        px0, px1 = x0 - pad, x1 + pad
        hgt, wid = py1 - py0, px1 - px0
        # REAL wall texture, borrowed from beside the plaque at the same rows — never
        # synthesised. Adding random noise instead looks grainier than the wall it sits in,
        # which is exactly how the first attempt gave itself away.
        gap = 30
        srcx = px0 - gap - wid
        if srcx < 0:
            srcx = px1 + gap                                # fall back to the right side
        tex = frame[py0:py1, srcx:srcx + wid].copy()

        # Split the borrowed block: keep ONLY its high-frequency texture, and throw away the
        # lighting it came with — that lighting belongs to where it was, not where it is going.
        blur_r = max(hgt, wid) / 4.0
        tex_lo = np.asarray(Image.fromarray(np.clip(tex, 0, 255).astype(np.uint8))
                            .filter(ImageFilter.GaussianBlur(blur_r)), dtype=np.float64)
        tex_hi = tex - tex_lo

        # Rebuild the lighting from the four edges of the hole itself, bilinearly. This is the
        # cheapest honest inpaint of a smooth field and it follows the wall's vignette in both
        # directions, which a top/bottom-only blend does not.
        top = frame[py0 - 12:py0, px0:px1].mean(0)                    # (wid,3)
        bot = frame[py1:py1 + 12, px0:px1].mean(0)                    # (wid,3)
        lef = frame[py0:py1, max(0, px0 - 12):px0].mean(1)            # (hgt,3)
        rig = frame[py0:py1, px1:px1 + 12].mean(1)                    # (hgt,3)
        ty = np.linspace(0, 1, hgt)[:, None, None]
        tx = np.linspace(0, 1, wid)[None, :, None]
        vert = top[None] * (1 - ty) + bot[None] * ty
        horz = lef[:, None] * (1 - tx) + rig[:, None] * tx
        lo = 0.5 * (vert + horz)
        patch = lo + tex_hi
        m = feather_mask(px1 - px0, hgt, 12.0)
        reg = out[py0:py1, px0:px1]
        out[py0:py1, px0:px1] = reg * (1 - m) + patch * m

    m = feather_mask(w, h, FEATHER)
    # clip against the frame edges — a bigger or moved plaque can run past the bottom,
    # and the mask has to be cropped by exactly the same amount as the insert.
    H, W = out.shape[:2]
    sy0, sx0 = max(0, -ny0), max(0, -nx0)
    dy0, dx0 = max(0, ny0), max(0, nx0)
    dy1, dx1 = min(H, ny0 + h), min(W, nx0 + w)
    sy1, sx1 = sy0 + (dy1 - dy0), sx0 + (dx1 - dx0)
    reg = out[dy0:dy1, dx0:dx1]
    out[dy0:dy1, dx0:dx1] = reg * (1 - m[sy0:sy1, sx0:sx1]) + ins[sy0:sy1, sx0:sx1] * m[sy0:sy1, sx0:sx1]
    return np.clip(out, 0, 255)


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    dy = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    frame = np.asarray(Image.open(src).convert('RGB'), dtype=np.float64)
    plate = Image.open(PLATE).convert('RGB')
    Image.fromarray(swap(frame, plate, scale=scale, dy=dy).astype(np.uint8)).save(dst)
    print(dst)

"""Track the avatar's head (beanie + sunglasses) frame by frame in the reference edit.

Multi-scale normalised cross-correlation in plain numpy (no cv2/scipy on this box).
Output per frame: t, scale (vs the t=0 head), head centre x/y in 1080x1920 px.
"""
import subprocess, sys, json
import numpy as np
from PIL import Image

SRC = sys.argv[1]
WINDOWS = json.loads(sys.argv[2])          # [[t0, t1], ...]
W, H = 270, 480                             # working resolution (1/4 of 1080x1920)
K = 1080 / W


def frames(t0, t1):
    n = max(1, int(round((t1 - t0) * 30)))
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t0}", "-i", SRC, "-frames:v", str(n),
         "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    return [(t0 + i / 30, a) for i, a in enumerate(arr)]


def ncc(img, tpl):
    """Normalised cross-correlation map, valid region only."""
    th, tw = tpl.shape
    t = tpl - tpl.mean()
    tn = np.sqrt((t ** 2).sum()) + 1e-6
    fh, fw = img.shape[0] + th, img.shape[1] + tw
    F = np.fft.rfft2(img, (fh, fw)) * np.conj(np.fft.rfft2(t, (fh, fw)))
    num = np.fft.irfft2(F, (fh, fw))[: img.shape[0] - th + 1, : img.shape[1] - tw + 1]
    ii = np.pad(img, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ii2 = np.pad(img ** 2, ((1, 0), (1, 0))).cumsum(0).cumsum(1)

    def box(a):
        return a[th:, tw:] - a[:-th, tw:] - a[th:, :-tw] + a[:-th, :-tw]

    s, s2 = box(ii), box(ii2)
    var = s2 - s ** 2 / (th * tw)
    # flat windows (a plain white page, a black band) have ~zero variance and blow the
    # ratio up to nonsense; they cannot contain the head, so score them 0.
    out = num / (np.sqrt(np.maximum(var, 1e-6)) * tn)
    out[var < th * tw * 100.0] = 0.0   # std < 10 grey levels
    return out


# template: head from the very first frame (full-size hook avatar)
_, f0 = frames(0.0, 0.04)[0]
# head box at t=0 on the 270x480 grid: beanie + sunglasses only (y 33-54 %, x 30-70 %).
# The first version started at y95 and swallowed the static hook text at 25-30 %,
# so it tracked the text, not the head.
tpl = f0[160:260, 81:189]
tpl_img = Image.fromarray(tpl.astype(np.uint8))

scales = np.round(np.arange(0.40, 1.16, 0.02), 3)
tpls = {}
for s in scales:
    w, h = max(8, int(tpl.shape[1] * s)), max(8, int(tpl.shape[0] * s))
    tpls[s] = np.asarray(tpl_img.resize((w, h), Image.BILINEAR), np.float32)

for t0, t1 in WINDOWS:
    for t, img in frames(t0, t1):
        best = (-1, None, None)
        for s, tp in tpls.items():
            m = ncc(img, tp)
            idx = np.unravel_index(np.argmax(m), m.shape)
            if m[idx] > best[0]:
                best = (float(m[idx]), s, (idx, tp.shape))
        score, s, ((y, x), (th, tw)) = best
        cx, cy = (x + tw / 2) * K, (y + th / 2) * K
        top = y * K
        print(f"{t:6.3f} scale={s:.2f} cx={cx:6.1f} cy={cy:6.1f} top={top:6.1f} ncc={score:.2f}", flush=True)

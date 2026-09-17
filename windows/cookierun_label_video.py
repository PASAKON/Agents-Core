#!/usr/bin/env python3
"""cookierun_label_video.py -- read presses off a video the IDM has never seen.

Gate 2. Gate 1 showed the IDM recovers 96.5% of real presses on held-out takes
of OUR OWN footage. This asks the question that actually decides the plan:
does it survive a stranger's phone recording?

There is no key log for a YouTube clip -- that is the entire point of the
exercise -- so it cannot be scored against truth. It is checked two ways that
need no truth at all:

  RATE    a manual 300K farm run presses a few hundred times a minute. Zero
          means the labeller has gone blind (or the video is an AFK farm, the
          poison that killed v8). Thousands means it is firing on noise.

  PHYSICS a jump is not an opinion. Press jump and the cookie leaves the ground
          for about t2 + 0.67 s, which is visible as upward motion in the frames
          that follow. If predicted presses are not followed by that motion,
          the labels are wrong however plausible the rate looks.

The physics check is calibrated on OUR data first, where the presses are known.
A validator nobody has validated is just another opinion.

    python cookierun_label_video.py <frames_dir> --model idm_v1.pt
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
from cookierun_idm_train import Net, OFFSETS_S, W, H            # noqa: E402
from cookierun_register import register                          # noqa: E402

# The cookie runs at a fixed place on the left of the crop. Its vertical motion
# is the physics signal; the rest of the frame scrolls horizontally and would
# only add noise.
COOKIE_BAND = (0.08, 0.34)      # x fraction of the 384-wide crop


def vertical_shift(a, b, max_dy=14):
    """How far the cookie band moved vertically between two crops, in pixels.

    Row-profile cross-correlation rather than anything cleverer: the band is
    small, the motion is pure translation, and a method with no parameters to
    tune is a method that cannot be tuned into agreeing with me.
    """
    x0, x1 = int(COOKIE_BAND[0] * a.shape[1]), int(COOKIE_BAND[1] * a.shape[1])
    pa = a[:, x0:x1].astype(np.float32).mean(axis=1)
    pb = b[:, x0:x1].astype(np.float32).mean(axis=1)
    pa -= pa.mean()
    pb -= pb.mean()
    best, best_dy = -1e9, 0
    for dy in range(-max_dy, max_dy + 1):
        if dy >= 0:
            s = float(np.dot(pa[dy:], pb[:len(pb) - dy])) if dy < len(pa) else 0.0
        else:
            s = float(np.dot(pa[:dy], pb[-dy:]))
        if s > best:
            best, best_dy = s, dy
    return best_dy          # negative = content moved UP = cookie rose


def rise_after(frames, i, look=4):
    """Upward motion in the `look` frames after i. Positive = went up."""
    if i + look >= len(frames):
        return 0.0
    return -float(np.mean([vertical_shift(frames[i], frames[i + k])
                           for k in range(1, look + 1)]))


def load_registered(d: Path):
    crops, times = [], []
    meta = json.loads((d / "times.json").read_text()) if (d / "times.json").exists() else None
    files = sorted(d.glob("*.jpg"))
    for n, f in enumerate(files):
        im = cv2.imread(str(f))
        if im is None:
            continue
        if im.shape[1] == W * 2 and im.shape[0] == H * 2 or im.shape[1] == 384:
            crop = im            # already registered
        else:
            crop, rep = register(im)
            if crop is None:
                continue
        crops.append(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop)
        times.append(meta[n] if meta else n / 18.2)
    return crops, np.array(times, np.float64)


def predict(model, frames, times, thr=0.7):
    small = [cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA) for f in frames]
    probs = np.zeros(len(small), np.float32)
    with torch.no_grad():
        for s in range(0, len(small), 256):
            idxs = list(range(s, min(s + 256, len(small))))
            batch = np.empty((len(idxs), len(OFFSETS_S), H, W), np.uint8)
            for n, i in enumerate(idxs):
                for c, off in enumerate(OFFSETS_S):
                    j = int(np.argmin(np.abs(times - (times[i] + off))))
                    batch[n, c] = small[j]
            p = torch.sigmoid(model(torch.from_numpy(batch).float() / 255.0)).numpy()
            probs[idxs] = p[:, 0]
    return probs > thr, probs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frames_dir")
    ap.add_argument("--model", required=True)
    ap.add_argument("--thr", type=float, default=0.7)
    a = ap.parse_args()

    frames, times = load_registered(Path(a.frames_dir))
    if len(frames) < 100:
        print(f"only {len(frames)} usable frames - not enough to judge")
        return 2
    dur = times[-1] - times[0]
    print(f"{len(frames)} registered frames, {dur:.0f}s "
          f"({len(frames) / max(dur, 1):.1f} fps)")

    model = Net(len(OFFSETS_S))
    model.load_state_dict(torch.load(a.model))
    model.eval()
    pred, probs = predict(model, frames, times, a.thr)
    n = int(pred.sum())
    print(f"\nRATE  {n} predicted jump presses = {60 * n / max(dur, 1):.0f}/min")
    print(f"      mean p {probs.mean():.3f}, and {100 * (probs > 0.9).mean():.1f}% "
          f"of frames above 0.9")

    idx = np.where(pred)[0]
    rises_hit = [rise_after(frames, int(i)) for i in idx]
    other = np.where(~pred)[0]
    rng = np.random.default_rng(0)
    sample = rng.choice(other, size=min(len(other), len(idx) * 3), replace=False)
    rises_miss = [rise_after(frames, int(i)) for i in sample]

    mh, mm = float(np.mean(rises_hit)), float(np.mean(rises_miss))
    print(f"\nPHYSICS  upward motion in the 4 frames after a frame")
    print(f"  predicted PRESS  {mh:+.2f} px   (n={len(rises_hit)})")
    print(f"  no press         {mm:+.2f} px   (n={len(rises_miss)})")
    print(f"  separation       {mh - mm:+.2f} px")
    if mh - mm > 0.5:
        print("  -> presses are followed by the cookie rising. The labels move "
              "with the physics.")
    else:
        print("  -> NO separation. Whatever it is predicting, it is not jumps. "
              "Do not train on this.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

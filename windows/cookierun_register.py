#!/usr/bin/env python3
"""cookierun_register.py -- put a YouTube frame into our training geometry.

The IDM is trained on one exact crop of one exact capture: 0.05..1.0 x
0.16..0.87 of a 1580x889 BlueStacks game rect, squashed to 384x160. Feed it a
phone recording at 1280x592 and it is reading a different picture of the same
game -- different field of view, different scale, different framing. Whatever it
says about that is not what it learned to say.

Applying our crop FRACTIONS to a differently-shaped source does not fix it: the
two sources have different aspect (1.78 vs 2.16), so the same fractions cut a
different part of the world. Measured: our crop lands 2.379 wide, the same
fractions on the YouTube frame land 2.888.

So register on landmarks the game itself draws in a fixed place: the Jump and
Slide buttons. They sit at the bottom corners of every run, in both sources.

The catch is that matchTemplate is not scale-invariant, which is why our
`btn_jump` template scores 0.88 on our own frame and 0.41 on YouTube -- the same
button, drawn smaller. So sweep the scale, take the best, and the winning scale
IS the registration: it converts any source into ours.

    python cookierun_register.py <frame.png> [--out crop.png] [--debug]
"""
import argparse
import sys
from pathlib import Path

# Windows defaults stdout to cp1252, and everything here prints text that
# came from somewhere else -- a lease holder's name, a window title, a
# screen name. On 2026-09-18 a lease taken with a U+25D1 in it crashed
# this whole check on the print, so the farm's health was unreadable
# because of a character in somebody's label. Third instance of this same
# cp1252 fault today (esc's ESC_HOLD write, session-rename, this).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np

ROOT = Path(r"C:\Users\UsEr\cookierun-bot")

# Our reference: measured on a real in-run frame of the 1580x889 game rect.
REF_W, REF_H = 1580, 889
REF_JUMP = (201, 772)
REF_SLIDE = (1379, 772)
# The model's crop, in reference-frame fractions.
X0, X1, Y0, Y1 = 0.05, 1.0, 0.16, 0.87
OUT_W, OUT_H = 384, 160


def best_scale_match(frame, tpl, scales):
    """(score, centre, scale) for the best-scoring size of tpl in frame."""
    best = (-1.0, None, None)
    for s in scales:
        w, h = int(tpl.shape[1] * s), int(tpl.shape[0] * s)
        if w < 8 or h < 8 or w > frame.shape[1] or h > frame.shape[0]:
            continue
        t = cv2.resize(tpl, (w, h), interpolation=cv2.INTER_AREA)
        r = cv2.matchTemplate(frame, t, cv2.TM_CCOEFF_NORMED)
        _, sc, _, loc = cv2.minMaxLoc(r)
        if sc > best[0]:
            best = (float(sc), (loc[0] + w // 2, loc[1] + h // 2), s)
    return best


def register(frame, debug=False):
    """Map `frame` into the reference geometry via the Jump/Slide buttons.

    Returns (crop 384x160, report dict) or (None, report) if the landmarks are
    not confidently found -- in which case the frame must NOT be used. A bad
    registration produces labels that look exactly like good ones.
    """
    jump = cv2.imread(str(ROOT / "templates" / "btn_jump.png"))
    slide = cv2.imread(str(ROOT / "templates" / "btn_slide.png"))
    if jump is None or slide is None:
        return None, {"ok": False, "why": "button templates missing"}

    scales = np.arange(0.40, 1.61, 0.02)
    js, jc, jsc = best_scale_match(frame, jump, scales)
    ss, sc_, ssc = best_scale_match(frame, slide, scales)
    rep = {"jump": {"score": round(js, 4), "centre": jc, "scale": round(jsc or 0, 3)},
           "slide": {"score": round(ss, 4), "centre": sc_, "scale": round(ssc or 0, 3)}}

    if js < 0.60 or ss < 0.60:
        rep.update(ok=False, why=f"landmarks not found (jump {js:.3f}, slide {ss:.3f})")
        return None, rep

    # Horizontal scale from the distance between the two buttons -- a span is a
    # far steadier measure than either centre on its own.
    span_ref = REF_SLIDE[0] - REF_JUMP[0]
    span_src = sc_[0] - jc[0]
    if span_src <= 0:
        rep.update(ok=False, why="slide is left of jump; landmarks crossed")
        return None, rep
    k = span_src / span_ref
    rep["scale_from_span"] = round(k, 4)

    # The two template scales should agree with the span scale. When they do
    # not, something matched the wrong thing and the registration is a guess.
    if abs(jsc - k) > 0.25 or abs(ssc - k) > 0.25:
        rep.update(ok=False, why=(f"scales disagree: span {k:.3f} vs jump {jsc:.3f} "
                                  f"slide {ssc:.3f} - probably a false landmark"))
        return None, rep

    # reference (x,y) -> source: x*k + dx, y*k + dy
    dx = jc[0] - REF_JUMP[0] * k
    dy = ((jc[1] - REF_JUMP[1] * k) + (sc_[1] - REF_SLIDE[1] * k)) / 2.0
    rep["offset"] = [round(dx, 1), round(dy, 1)]

    x0 = int(X0 * REF_W * k + dx)
    x1 = int(X1 * REF_W * k + dx)
    y0 = int(Y0 * REF_H * k + dy)
    y1 = int(Y1 * REF_H * k + dy)
    rep["source_box"] = [x0, y0, x1, y1]
    H, W = frame.shape[:2]
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        # Cropping past the edge would pad with black where the model expects
        # game, which it has never seen and cannot interpret.
        rep.update(ok=False, why=f"crop {[x0, y0, x1, y1]} falls outside the {W}x{H} frame")
        return None, rep

    crop = cv2.resize(frame[y0:y1, x0:x1], (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
    rep["ok"] = True
    return crop, rep


def lock_transform(frames, sample=9):
    """One crop box for a whole video, from a sample of its frames.

    Sweeping the scale per frame is both slow (~2 s each) and wrong. The UI does
    not move within a recording, so the transform is a property of the VIDEO,
    not of the frame - and a per-frame answer that wobbles by a pixel produces a
    frame stack whose frames do not line up with each other, which is precisely
    what a stacked-input model cannot tolerate.

    Measured on a 517 s clip: 23 of 26 samples registered and every one returned
    scale 0.7827. So take the median of what agrees and apply it to everything.
    """
    boxes = []
    step = max(1, len(frames) // sample)
    for f in frames[::step][:sample]:
        img = cv2.imread(str(f)) if not isinstance(f, np.ndarray) else f
        if img is None:
            continue
        _, rep = register(img)
        if rep.get("ok"):
            boxes.append(rep["source_box"])
    if len(boxes) < 3:
        return None, {"ok": False, "why": f"only {len(boxes)} of {sample} samples registered"}
    box = [int(np.median([b[i] for b in boxes])) for i in range(4)]
    spread = max(max(abs(b[i] - box[i]) for i in range(4)) for b in boxes)
    if spread > 8:
        # Frames of one video disagreeing by more than a few pixels means the
        # landmarks are not being found reliably, and a median of unreliable
        # answers is still unreliable.
        return None, {"ok": False, "why": f"sampled boxes disagree by {spread}px", "boxes": boxes}
    return box, {"ok": True, "box": box, "samples": len(boxes), "spread_px": spread}


def apply_box(frame, box):
    x0, y0, x1, y1 = box
    H, W = frame.shape[:2]
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        return None
    return cv2.resize(frame[y0:y1, x0:x1], (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    frame = cv2.imread(a.frame)
    if frame is None:
        print(f"cannot read {a.frame}")
        return 2
    print(f"source {frame.shape[1]}x{frame.shape[0]}")
    crop, rep = register(frame)
    for k, v in rep.items():
        print(f"  {k}: {v}")
    if crop is None:
        print("\nREFUSED - this frame cannot be registered, so it must not be labelled.")
        return 1
    if a.out:
        cv2.imwrite(a.out, crop)
        print(f"\nwrote {a.out} ({OUT_W}x{OUT_H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

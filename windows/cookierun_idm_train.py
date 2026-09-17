#!/usr/bin/env python3
"""cookierun_idm_train.py -- can a model read a press off the frames around it?

This is the gate the whole YouTube plan stands on, and it is deliberately run on
our OWN data, where the answer is already known, before a single frame of video
is labelled or a single GPU-hour is spent. If a model cannot recover presses we
have the key log for, it will certainly not recover presses from a stranger's
phone recording, and everything downstream would be trained on confident
nonsense -- the v8 failure again, but this time invisible, because a wrong label
looks exactly like a right one.

Why it should be possible at all: the policy has to guess what to do next from
the past, but this only has to say what already happened, and it gets to see the
FUTURE. A jump is unmistakable two frames later -- the cookie is in the air.

    python cookierun_idm_train.py --index idm_index.json --runs 20 --epochs 6

Three choices that keep the number honest:

**Frames are picked by TIME, not by frame number.** Offsets are +-110/55 ms, and
the nearest frame to each offset is used. Our recorder delivers 18.2 fps against
a claimed 24, and YouTube arrives at 24-60 -- a stack defined in frame counts
would mean a different span of real time on every source, and the model would
learn the recorder rather than the game.

**Validation takes never appear in training.** Whole takes, split at the source.

**The score reported is precision/recall on onsets, never accuracy.** 88% is what
you get for answering "no press" every time.
"""
import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn

W, H = 192, 80                      # half our 384x160 crop; the cookie is still clear
OFFSETS_S = (-0.11, -0.055, 0.0, 0.055, 0.11)


def augment(stack, rng):
    """Break the model's assumption that every frame comes from our capture.

    Gate 2 failed because of exactly that assumption. Trained on one BlueStacks
    pipeline, the model met a phone recording and its probabilities collapsed
    into the middle - floor up from 0.05 to 0.21, ceiling never reaching 0.9,
    confident about nothing. It had no reason to believe the game could look any
    other way.

    Each transform here targets a difference measured between the two sources
    rather than a generic image trick:

      scale/shift  registration lands the crop within a few px, not exactly
      brightness   a phone screen grab is not a desktop framebuffer
      contrast     recompression flattens it
      JPEG         YouTube frames have been encoded twice; ours once
      blur         downscaling from a different source resolution softens edges

    Applied per STACK, not per frame: all five frames of a sample share one
    transform, because the real difference between sources is constant within a
    clip. Jittering frames independently would teach it that the camera shakes.
    """
    import cv2 as _cv
    out = stack.astype(np.float32)

    if rng.random() < 0.8:                       # geometry
        k = 1.0 + rng.uniform(-0.06, 0.06)
        dx, dy = rng.integers(-4, 5), rng.integers(-3, 4)
        M = np.float32([[k, 0, dx], [0, k, dy]])
        for c in range(out.shape[0]):
            out[c] = _cv.warpAffine(out[c], M, (W, H), borderMode=_cv.BORDER_REPLICATE)

    if rng.random() < 0.8:                       # photometry
        out = out * rng.uniform(0.75, 1.30) + rng.uniform(-28, 28)

    if rng.random() < 0.5:                       # recompression
        q = int(rng.integers(35, 80))
        for c in range(out.shape[0]):
            ok, enc = _cv.imencode(".jpg", np.clip(out[c], 0, 255).astype(np.uint8),
                                   [int(_cv.IMWRITE_JPEG_QUALITY), q])
            if ok:
                out[c] = _cv.imdecode(enc, _cv.IMREAD_GRAYSCALE).astype(np.float32)

    if rng.random() < 0.3:                       # resample softness
        for c in range(out.shape[0]):
            out[c] = _cv.GaussianBlur(out[c], (3, 3), rng.uniform(0.4, 1.1))

    return np.clip(out, 0, 255).astype(np.uint8)


class Net(nn.Module):
    """Small on purpose. If the task needs a big model to work at all, it is not
    the easy problem this plan assumes it is, and that is worth finding out now
    rather than after renting a GPU."""

    def __init__(self, cin: int):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv2d(cin, 32, 5, 2, 2), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, 2, 1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 96, 3, 2, 1), nn.BatchNorm2d(96), nn.ReLU(),
            nn.Conv2d(96, 128, 3, 2, 1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(1), nn.Flatten(),
            nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 2))

    def forward(self, x):
        return self.f(x)


def load_run(run_dir: Path, rows):
    """(frames uint8 [N,H,W], times [N], labels [N,2]) for one run, cached in RAM.

    Whole runs are loaded rather than scattered samples: every frame is reused by
    up to five stacks, so caching per-run is what makes this fit on a CPU box.
    """
    fj = run_dir / "frames.jsonl"
    try:
        meta = [json.loads(l) for l in fj.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return None
    by_path = {r[0]: (r[1], r[2]) for r in rows}
    imgs, times, labs = [], [], []
    for m in meta:
        p = str(run_dir / "img" / f"f{m['i']:06d}.jpg")
        if p not in by_path:
            continue
        im = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if im is None:
            continue
        imgs.append(cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA))
        times.append(m["t"])
        labs.append(by_path[p])
    if len(imgs) < 200:
        return None
    return np.array(imgs, np.uint8), np.array(times, np.float64), np.array(labs, np.float32)


def stacks_for(run, idxs):
    imgs, times, labs = run
    out = np.empty((len(idxs), len(OFFSETS_S), H, W), np.uint8)
    for n, i in enumerate(idxs):
        for c, off in enumerate(OFFSETS_S):
            j = int(np.argmin(np.abs(times - (times[i] + off))))
            out[n, c] = imgs[j]
    return out, labs[idxs]


def gather(index: dict, want_runs: int, seed: int):
    """Load up to want_runs runs, spread across as many takes as possible."""
    rng = random.Random(seed)
    per_take = {}
    for take, rows in index.items():
        by_run = {}
        for r in rows:
            by_run.setdefault(str(Path(r[0]).parent.parent), []).append(r)
        per_take[take] = by_run
    picked, takes = [], sorted(per_take)
    rng.shuffle(takes)
    while len(picked) < want_runs and takes:
        for t in list(takes):
            runs = per_take[t]
            if not runs:
                takes.remove(t)
                continue
            k = sorted(runs)[0]
            rows = runs.pop(k)
            r = load_run(Path(k), rows)
            if r is not None:
                picked.append(r)
            if len(picked) >= want_runs:
                break
    return picked


def evaluate(model, runs, thr: float):
    model.eval()
    tp = fp = fn = tn = 0
    with torch.no_grad():
        for run in runs:
            n = len(run[0])
            for s in range(0, n, 512):
                idxs = list(range(s, min(s + 512, n)))
                x, y = stacks_for(run, idxs)
                p = torch.sigmoid(model(torch.from_numpy(x).float() / 255.0)).numpy()
                pred = p[:, 0] > thr
                true = y[:, 0] > 0.5
                tp += int((pred & true).sum())
                fp += int((pred & ~true).sum())
                fn += int((~pred & true).sum())
                tn += int((~pred & ~true).sum())
    prec = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    acc = (tp + tn) / max(tp + tn + fp + fn, 1)
    return prec, rec, f1, acc, tp, fp, fn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--val-runs", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--out", default=None)
    ap.add_argument("--augment", action="store_true",
                    help="train against the domain gap, not just the data")
    a = ap.parse_args()

    torch.manual_seed(0)
    idx = json.loads(Path(a.index).read_text(encoding="utf-8"))
    print("loading runs into memory ...", flush=True)
    train = gather(idx["train"], a.runs, seed=1)
    val = gather(idx["val"], a.val_runs, seed=2)
    ntr = sum(len(r[0]) for r in train)
    nva = sum(len(r[0]) for r in val)
    pos = sum(int(r[2][:, 0].sum()) for r in train)
    print(f"train {len(train)} runs / {ntr:,} frames  ({pos:,} jump onsets, "
          f"{100 * pos / max(ntr, 1):.1f}%)")
    print(f"val   {len(val)} runs / {nva:,} frames   (different takes entirely)")
    if not train or not val:
        print("not enough data loaded")
        return 1

    model = Net(len(OFFSETS_S))
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    # The positive class is ~1 frame in 9; without this the cheapest way to cut
    # the loss is to predict "no press" forever, which is exactly the failure
    # this whole exercise exists to avoid.
    w = torch.tensor([(ntr - pos) / max(pos, 1), 8.0])
    lossf = nn.BCEWithLogitsLoss(pos_weight=w)

    rng = random.Random(0)
    aug_rng = np.random.default_rng(0)
    for ep in range(a.epochs):
        model.train()
        order = [(ri, i) for ri, r in enumerate(train) for i in range(len(r[0]))]
        rng.shuffle(order)
        tot = nb = 0
        for s in range(0, len(order), a.batch):
            chunk = order[s:s + a.batch]
            xs, ys = [], []
            for ri, i in chunk:
                x, y = stacks_for(train[ri], [i])
                if a.augment:
                    x = augment(x[0], aug_rng)[None]
                xs.append(x)
                ys.append(y)
            x = torch.from_numpy(np.concatenate(xs)).float() / 255.0
            y = torch.from_numpy(np.concatenate(ys))
            opt.zero_grad()
            loss = lossf(model(x), y)
            loss.backward()
            opt.step()
            tot += float(loss)
            nb += 1
        p, r, f1, acc, tp, fp, fn = evaluate(model, val, 0.5)
        print(f"epoch {ep + 1}/{a.epochs}  loss {tot / max(nb, 1):.4f}  "
              f"| VAL jump: precision {p:.3f} recall {r:.3f} F1 {f1:.3f} "
              f"(acc {acc:.3f}, tp {tp} fp {fp} fn {fn})", flush=True)

    print("\nthreshold sweep on held-out takes (jump onsets):")
    for thr in (0.3, 0.5, 0.7, 0.9):
        p, r, f1, acc, tp, fp, fn = evaluate(model, val, thr)
        print(f"  thr {thr:.1f}  precision {p:.3f}  recall {r:.3f}  F1 {f1:.3f}")
    if a.out:
        torch.save(model.state_dict(), a.out)
        print(f"\nsaved {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

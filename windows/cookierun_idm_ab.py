#!/usr/bin/env python3
"""cookierun_idm_ab.py -- did the model get better or worse, and WHERE.

The CEO asked for the second half of that sentence, not the first: "จะได้รู้ว่า
Model เก่งขึ้นหรือแย่ลง ตรงไหนจะได้ปรับถูกจุด". A single F1 answers "which model"
and hides every decision that follows from it, so this reports one number per
place a press can be got wrong:

  1. JUMP and SLIDE separately.  Slide is 1.20% of frames against jump's 10.73%.
     A model can improve its headline score while getting strictly worse at
     slides, and the headline would never show it.

  2. TIMING, in frames, not right/wrong.  For every press the model finds, how
     far off was it? A model that is 1 frame late everywhere is a different
     problem -- and a different fix -- from one that scatters.

  3. IN-DOMAIN vs YOUTUBE.  The whole reason the corpus grew is domain shift.
     A model can gain on our own footage and lose on a stranger's recording;
     those are the two numbers that decide whether the YouTube plan is alive.

  4. CONFIDENT vs HESITANT.  The share of frames the model is sure about
     (>0.9) at all, per source. Gate 2 failed the first time not because the
     model was wrong but because it stopped being sure of anything.

Both models are scored on IDENTICAL frames in the same process. That is the only
part of this that must not be compromised -- two numbers measured on two
different frame sets are not a comparison.

    python cookierun_idm_ab.py --a baseline.pt --b idm_full.pt \
        --packs D:/colab_pack --youtube D:/yt_frames --out ab_report.json

--youtube is optional; without it the domain-shift half is skipped and said so.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

import cookierun_idm_train_colab as T   # Net, Shard, OFFSETS_S -- one definition


def load_model(path, dev):
    m = T.Net(len(T.OFFSETS_S)).to(dev)
    m.load_state_dict(torch.load(path, map_location=dev))
    m.eval()
    return m


def predict(model, ds, dev, batch=512):
    """Probabilities for every frame of a shard, jump and slide."""
    from torch.utils.data import DataLoader
    out = []
    with torch.no_grad():
        for xb, _ in DataLoader(ds, batch_size=batch, num_workers=T.WORKERS):
            p = torch.sigmoid(model(xb.to(dev).float() / 255.0)).cpu().numpy()
            out.append(p.astype(np.float32))
    return np.concatenate(out) if out else np.zeros((0, 2), np.float32)


def prf(pred, true):
    tp = int((pred & true).sum())
    fp = int((pred & ~true).sum())
    fn = int((~pred & true).sum())
    pre = tp / max(tp + fp, 1)
    rec = tp / max(tp + fn, 1)
    return {"precision": round(pre, 4), "recall": round(rec, 4),
            "f1": round(2 * pre * rec / max(pre + rec, 1e-9), 4),
            "tp": tp, "fp": fp, "fn": fn}


def timing_offsets(p, truth, thr, window=4):
    """For each true onset, the signed frame offset of the nearest prediction.

    Reported as a distribution, not a mean. 'On average zero' is exactly what
    you get from a model that is half 3 frames early and half 3 frames late,
    and that model needs a different fix from one that is actually on time.
    """
    pred_idx = np.flatnonzero(p > thr)
    true_idx = np.flatnonzero(truth)
    if not len(pred_idx) or not len(true_idx):
        return {"matched": 0}
    pos = np.searchsorted(pred_idx, true_idx)
    offs = []
    for ti, k in zip(true_idx, pos):
        cands = pred_idx[max(k - 1, 0):k + 1]
        if not len(cands):
            continue
        d = cands - ti
        best = d[np.argmin(np.abs(d))]
        if abs(best) <= window:
            offs.append(int(best))
    if not offs:
        return {"matched": 0}
    o = np.array(offs)
    return {"matched": len(o),
            "on_time_pct": round(100 * float((o == 0).mean()), 2),
            "within_1_pct": round(100 * float((np.abs(o) <= 1).mean()), 2),
            "early_pct": round(100 * float((o < 0).mean()), 2),
            "late_pct": round(100 * float((o > 0).mean()), 2),
            "median_offset": int(np.median(o)),
            "p10": int(np.percentile(o, 10)), "p90": int(np.percentile(o, 90))}


def confidence(p):
    return {"mean": round(float(p.mean()), 4),
            "p90": round(float(np.percentile(p, 90)), 4),
            "over_0.7_pct": round(100 * float((p > 0.7).mean()), 2),
            "over_0.9_pct": round(100 * float((p > 0.9).mean()), 2)}


def score_indomain(models, shards, dev, thr):
    """Both models, every val shard, identical frames."""
    acc = {k: {"jump_p": [], "slide_p": []} for k in models}
    truth_j, truth_s = [], []
    for sp in shards:
        ds = T.Shard(sp, train=False)
        for k, m in models.items():
            p = predict(m, ds, dev)
            acc[k]["jump_p"].append(p[:, 0])
            acc[k]["slide_p"].append(p[:, 1])
        truth_j.append(ds.y[:, 0] > 0.5)
        truth_s.append(ds.y[:, 1] > 0.5)
    tj, ts = np.concatenate(truth_j), np.concatenate(truth_s)
    out = {"frames": int(len(tj)),
           "jump_onsets": int(tj.sum()), "slide_onsets": int(ts.sum())}
    for k in models:
        pj = np.concatenate(acc[k]["jump_p"])
        ps = np.concatenate(acc[k]["slide_p"])
        out[k] = {
            "jump": {**prf(pj > thr, tj), "confidence": confidence(pj),
                     "timing": timing_offsets(pj, tj, thr)},
            "slide": {**prf(ps > thr, ts), "confidence": confidence(ps),
                      "timing": timing_offsets(ps, ts, thr)},
        }
    return out


def score_youtube(models, frame_dir, dev):
    """No labels here -- nobody logged a stranger's key presses.

    So this measures the one thing that is measurable without them, and it is
    the thing that actually failed before: whether the model is still WILLING to
    be sure. A model whose probabilities collapse into the middle on foreign
    footage cannot label it, whatever its in-domain F1 says.
    """
    import cv2
    paths = sorted(Path(frame_dir).glob("*.jpg")) + sorted(Path(frame_dir).glob("*.png"))
    if len(paths) < len(T.OFFSETS_S):
        return {"error": f"only {len(paths)} frames in {frame_dir}"}
    imgs = []
    for p in paths:
        im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if im is not None:
            imgs.append(cv2.resize(im, (T.W, T.H), interpolation=cv2.INTER_AREA))
    a = np.array(imgs, np.uint8)
    # Frames are consecutive at an unknown fps, so the stack is built by INDEX
    # here rather than by time -- there is no timestamp to pick by. Offsets are
    # rounded from OFFSETS_S at the recorder's 18.2 fps so the span of real time
    # stays the same as training.
    steps = [int(round(o * 18.2)) for o in T.OFFSETS_S]
    idx = np.clip(np.arange(len(a))[:, None] + np.array(steps)[None, :], 0, len(a) - 1)
    out = {"frames": int(len(a))}
    for k, m in models.items():
        probs = []
        with torch.no_grad():
            for s in range(0, len(a), 512):
                x = torch.from_numpy(a[idx[s:s + 512]]).to(dev).float() / 255.0
                probs.append(torch.sigmoid(m(x))[:, 0].cpu().numpy())
        out[k] = {"jump_confidence": confidence(np.concatenate(probs))}
    return out


def delta(a, b, key):
    return round(b[key] - a[key], 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="baseline checkpoint")
    ap.add_argument("--b", required=True, help="new checkpoint")
    ap.add_argument("--packs", required=True, help="dir holding val_*.npz")
    ap.add_argument("--youtube", default=None, help="dir of consecutive frames")
    ap.add_argument("--thr", type=float, default=0.5)
    ap.add_argument("--out", default="ab_report.json")
    g = ap.parse_args()

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    models = {"A_baseline": load_model(g.a, dev), "B_full": load_model(g.b, dev)}
    val = sorted(Path(g.packs).glob("val_*.npz"))
    if not val:
        print(f"no val_*.npz in {g.packs}")
        return 1
    print(f"scoring both models on {len(val)} val shards, device {dev} ...", flush=True)

    rep = {"threshold": g.thr, "val_shards": [p.name for p in val],
           "in_domain": score_indomain(models, val, dev, g.thr)}
    if g.youtube:
        print("scoring both models on YouTube frames ...", flush=True)
        rep["youtube"] = score_youtube(models, g.youtube, dev)
    else:
        rep["youtube"] = {"skipped": "no --youtube given; domain shift not measured"}

    d = rep["in_domain"]
    print(f"\n{'':22} {'A baseline':>12} {'B full':>12} {'delta':>10}")
    for cls in ("jump", "slide"):
        print(f"-- {cls.upper()}  ({d[cls + '_onsets']:,} onsets)")
        for k in ("precision", "recall", "f1"):
            a, b = d["A_baseline"][cls][k], d["B_full"][cls][k]
            print(f"   {k:19} {a:12.4f} {b:12.4f} {b - a:+10.4f}")
        ta, tb = d["A_baseline"][cls]["timing"], d["B_full"][cls]["timing"]
        if ta.get("matched") and tb.get("matched"):
            for k in ("on_time_pct", "within_1_pct", "early_pct", "late_pct"):
                print(f"   {k:19} {ta[k]:12.2f} {tb[k]:12.2f} {tb[k] - ta[k]:+10.2f}")
        ca, cb = d["A_baseline"][cls]["confidence"], d["B_full"][cls]["confidence"]
        for k in ("over_0.7_pct", "over_0.9_pct"):
            print(f"   {k:19} {ca[k]:12.2f} {cb[k]:12.2f} {cb[k] - ca[k]:+10.2f}")
    if "frames" in rep["youtube"]:
        print(f"-- YOUTUBE  ({rep['youtube']['frames']:,} frames, no labels)")
        ca = rep["youtube"]["A_baseline"]["jump_confidence"]
        cb = rep["youtube"]["B_full"]["jump_confidence"]
        for k in ("mean", "p90", "over_0.7_pct", "over_0.9_pct"):
            print(f"   {k:19} {ca[k]:12.4f} {cb[k]:12.4f} {cb[k] - ca[k]:+10.4f}")

    Path(g.out).write_text(json.dumps(rep, indent=1))
    print(f"\nwrote {g.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

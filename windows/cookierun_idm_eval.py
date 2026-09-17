#!/usr/bin/env python3
"""cookierun_idm_eval.py -- is a false positive wrong, or just early?

The first IDM scored recall 0.93 and precision 0.48 on held-out takes, and those
two numbers cannot both be taken at face value. Scoring demands the model name
the EXACT frame of a press, but a jump is visible across several frames at 18
fps, so a prediction one frame off is counted as two errors at once: a false
positive and, if it displaced the real one, a false negative.

Those are very different problems. "Fires 55 ms early" is a usable label for
teaching a policy when to jump. "Fires where nothing happened" is the poison
that killed v8. Exact-frame precision cannot tell them apart, so it is the wrong
question to stop on.

This measures the distance from every predicted press to the nearest real one
and reports precision at a tolerance of 0, 1 and 2 frames. The gap between those
numbers IS the answer.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import torch

import sys
sys.path.insert(0, str(Path(__file__).parent))
from cookierun_idm_train import Net, OFFSETS_S, gather, stacks_for   # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--val-runs", type=int, default=5)
    ap.add_argument("--thr", type=float, default=0.7)
    a = ap.parse_args()

    idx = json.loads(Path(a.index).read_text(encoding="utf-8"))
    val = gather(idx["val"], a.val_runs, seed=2)
    model = Net(len(OFFSETS_S))
    model.load_state_dict(torch.load(a.model))
    model.eval()

    dists, n_pred, n_true = [], 0, 0
    matched_true = 0
    gaps_ms = []
    with torch.no_grad():
        for imgs, times, labs in val:
            n = len(imgs)
            probs = np.zeros(n, np.float32)
            for s in range(0, n, 512):
                idxs = list(range(s, min(s + 512, n)))
                x, _ = stacks_for((imgs, times, labs), idxs)
                p = torch.sigmoid(model(torch.from_numpy(x).float() / 255.0)).numpy()
                probs[idxs] = p[:, 0]
            pred = np.where(probs > a.thr)[0]
            true = np.where(labs[:, 0] > 0.5)[0]
            n_pred += len(pred)
            n_true += len(true)
            if len(true) == 0:
                dists.extend([99] * len(pred))
                continue
            for i in pred:
                dists.append(int(np.min(np.abs(true - i))))
            for t in true:
                if len(pred) and np.min(np.abs(pred - t)) <= 1:
                    matched_true += 1
            g = np.diff(sorted(times))
            gaps_ms.append(float(np.median(g)) * 1000)

    d = np.array(dists)
    print(f"held-out takes: {len(val)} runs, {n_true:,} real jump onsets, "
          f"{n_pred:,} predicted (threshold {a.thr})")
    print(f"median frame gap {np.median(gaps_ms):.0f} ms\n")
    print("precision by how far the prediction sits from a real press:")
    for tol in (0, 1, 2, 3):
        hit = int((d <= tol).sum())
        print(f"  within {tol} frame(s) ({tol * np.median(gaps_ms):.0f} ms): "
              f"{hit:,}/{n_pred:,} = {hit / max(n_pred, 1):.3f}")
    print(f"\nrecall with 1-frame tolerance: {matched_true}/{n_true} = "
          f"{matched_true / max(n_true, 1):.3f}")
    far = int((d > 3).sum())
    print(f"\npredictions nowhere near a real press (>3 frames): {far:,} "
          f"({far / max(n_pred, 1):.1%} of predictions)")
    print("That last number is the one that matters -- it is the share of labels "
          "that would teach a policy to press where nobody pressed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""cookierun_idm_train_colab.py -- the full-corpus IDM run, as one Colab cell.

Paste this whole file into a single Colab cell and run it. It is written to be
pasted rather than imported because Colab has no other way in: the shards live in
the CEO's Drive, the repo is private, and typing code line-by-line into a cell
corrupts the indentation (measured 2026-09-18 -- each line's indent stacks on the
previous one). Clipboard paste preserves whitespace; this file is the clipboard.

WHAT IS DELIBERATELY UNCHANGED from cookierun_idm_train.py, and why:

    Net(), W/H, OFFSETS_S, pos_weight, lr, augment()

All copied verbatim. The previous run is the baseline the CEO wants an A/B
against ("Model เก่งขึ้นหรือแย่ลง ตรงไหน") -- change the architecture in the same
step as the data and neither half of the answer means anything. The ONLY
intended difference is the amount of data: 20 runs (~50k frames) became the
whole corpus (799,300).

WHAT HAD TO CHANGE, and why each one is forced rather than chosen:

  * **Shards, not loose JPEGs.** There is no winbox filesystem here. The packer
    already resized to 192x80, so nothing is decoded twice.

  * **Run boundaries are recovered from the timestamps.** The packer wrote x/y/t
    and no run marker, which matters because the stack is picked by TIME: without
    boundaries, the last frame of one run would reach across a gap of minutes and
    grab the first frame of the next. Inside a run the gap is ~55 ms; between
    runs it is minutes. Splitting on a 2 s gap recovers them exactly.

  * **searchsorted instead of argmin.** The original scans the whole time array
    for every frame and every offset. That is O(N^2) and fine at 50k frames; at
    799k it would not finish. Times inside a segment are monotonic, so the
    neighbour is a binary search, precomputed once per segment as an [N,5] table.

  * **Streaming by shard.** 799,300 x 80 x 192 = 12.3 GB of frames against free
    Colab's ~12.7 GB of RAM. One shard at a time is ~250 MB.

  * **Local disk, not the Drive mount.** Copied once up front. Reading 11.45 GB
    through Drive FUSE on every epoch is the slowest thing in the job by a wide
    margin, and it buys nothing.

Everything the DataLoader touches lives at module level rather than inside
main(). That is not style: a Dataset defined inside a function cannot be pickled,
so it survives only where workers are forked (Linux) and dies where they are
spawned (Windows) -- which would have made the worker path the one path that
could not be smoke-tested on winbox before the real run.

The T4 check at the top is not politeness. Colab bills premium accelerators the
moment you CONNECT, not when compute starts (measured), so landing on G4 by
accident and running for an hour spends compute units on a card that -- for this
model -- finishes at the same wall-clock time as the free one.

    # Colab: paste and run, no arguments.
    # winbox smoke test (same file, real data, one shard):
    #   set IDM_DEVICE=cpu & set IDM_MAX_SHARDS=1 & set IDM_EPOCHS=1
    #   set IDM_LOCAL=C:\\Users\\UsEr\\Documents\\CookieRunScript\\colab_pack
    #   python cookierun_idm_train_colab.py
"""
import json
import os
import random
import shutil
import time
import zipfile
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset


def _env(k, d):
    return os.environ.get(k, d)


# Defaults are the Colab run; every one can be overridden by an env var so the
# exact same file can be smoke-tested on winbox (CPU, one shard, one epoch)
# before an hour of someone else's GPU time is spent finding a typo.
DRIVE_PACKS = _env("IDM_PACKS", "/content/drive/MyDrive/BACKUP/CookieRun Backup/colab_packs")
LOCAL = Path(_env("IDM_LOCAL", "/content/packs"))
OUT = Path(_env("IDM_OUT", "/content/idm_out"))
# Epochs AND a wall-clock budget, whichever ends first.
#
# Profiled on winbox rather than guessed, because the first guess was wrong. The
# CPU smoke test ran at 198 stacks/s and the obvious reading was "augmentation is
# the bottleneck, free Colab has 2 vCPUs, four epochs will not fit". Timing the
# pieces says otherwise:
#
#     full augment()   0.57 ms/stack   = 1,769/s on ONE core
#       of which jpeg  0.53 ms         (the rest is noise)
#
# So 198/s was the CNN's forward/backward on a CPU, which on Colab is the GPU's
# job. Two worker cores feed ~3,500 stacks/s against a T4 measured at 5,348
# samples/s: data-bound, but at a rate where 799,300 x 4 epochs is roughly 20-35
# minutes, not the two hours the wrong reading implied.
#
# The budget stays anyway. It costs nothing when the estimate holds and it is the
# only thing that guarantees a trained, evaluated, saved model if the estimate is
# wrong again -- or if Colab's unmeasured idle timeout turns out to be shorter
# than the run.
EPOCHS = int(_env("IDM_EPOCHS", "4"))
MAX_MINUTES = float(_env("IDM_MAX_MINUTES", "75"))
BATCH = int(_env("IDM_BATCH", "64"))
MAX_SHARDS = int(_env("IDM_MAX_SHARDS", "0"))   # 0 = all; smoke test uses 1
MAX_BATCHES = int(_env("IDM_MAX_BATCHES", "0"))  # 0 = the whole shard
WORKERS = int(_env("IDM_WORKERS", "2"))
DEVICE = _env("IDM_DEVICE", "cuda")
LR = 1e-3
RUN_GAP_S = 2.0         # a time gap this big is a run boundary, not a dropped frame
W, H = 192, 80
OFFSETS_S = (-0.11, -0.055, 0.0, 0.055, 0.11)
ALLOW_PAID = False      # flip only with a reason; see the docstring


def say(m):
    print(m, flush=True)


def augment(stack, rng):
    """Verbatim from cookierun_idm_train.py -- see that file for why each
    transform is here. Copied rather than imported, and copied rather than
    improved: this is the half of the experiment that must not move."""
    out = stack.astype(np.float32)
    if rng.random() < 0.8:
        k = 1.0 + rng.uniform(-0.06, 0.06)
        dx, dy = rng.integers(-4, 5), rng.integers(-3, 4)
        M = np.float32([[k, 0, dx], [0, k, dy]])
        for c in range(out.shape[0]):
            out[c] = cv2.warpAffine(out[c], M, (W, H), borderMode=cv2.BORDER_REPLICATE)
    if rng.random() < 0.8:
        out = out * rng.uniform(0.75, 1.30) + rng.uniform(-28, 28)
    if rng.random() < 0.5:
        q = int(rng.integers(35, 80))
        for c in range(out.shape[0]):
            ok, enc = cv2.imencode(".jpg", np.clip(out[c], 0, 255).astype(np.uint8),
                                   [int(cv2.IMWRITE_JPEG_QUALITY), q])
            if ok:
                out[c] = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE).astype(np.float32)
    if rng.random() < 0.3:
        for c in range(out.shape[0]):
            out[c] = cv2.GaussianBlur(out[c], (3, 3), rng.uniform(0.4, 1.1))
    return np.clip(out, 0, 255).astype(np.uint8)


class Net(nn.Module):
    def __init__(self, cin):
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


def stack_table(t):
    """[N,5] of frame indices, nearest by TIME, never crossing a run boundary.

    Segment first, then binary-search inside each segment. Doing it globally
    would be simpler and wrong: the nearest frame in time to the last frame of a
    run is the first frame of the NEXT run, minutes of gameplay away, and the
    model would be asked to read a press across a scene cut.
    """
    bounds = np.flatnonzero(np.diff(t) > RUN_GAP_S) + 1
    segs = np.split(np.arange(len(t)), bounds)
    table = np.empty((len(t), len(OFFSETS_S)), np.int64)
    for seg in segs:
        if not len(seg):
            continue
        ts = t[seg]
        if len(ts) < 2:
            # A one-frame segment has no neighbour to search for, and
            # searchsorted would happily hand back an index past the end.
            table[seg, :] = seg[0]
            continue
        for c, off in enumerate(OFFSETS_S):
            tgt = ts + off
            j = np.clip(np.searchsorted(ts, tgt), 1, len(ts) - 1)
            pick = np.where(np.abs(ts[j - 1] - tgt) <= np.abs(ts[j] - tgt), j - 1, j)
            table[seg, c] = seg[0] + pick
    return table, len(segs)


class Shard(Dataset):
    def __init__(self, path, train, salt=0):
        d = np.load(path)
        order = np.argsort(d["t"], kind="stable")
        self.x, self.y, t = d["x"][order], d["y"][order], d["t"][order]
        self.tab, self.nseg = stack_table(t)
        self.train, self.salt = train, salt

    def __len__(self):
        return len(self.x)

    def __getitem__(self, i):
        s = self.x[self.tab[i]]
        if self.train:
            # Seeded per (epoch, shard, frame). The original advanced one shared
            # RNG, which workers cannot share; seeding on the frame alone would
            # hand the same frame the same jitter every epoch and quietly turn
            # augmentation into a fixed relabelling.
            s = augment(s, np.random.default_rng(self.salt * 1_000_003 + i))
        return torch.from_numpy(np.ascontiguousarray(s)), torch.from_numpy(self.y[i])


def fetch_shards():
    """Drive -> local disk, once. Returns (train, val) shard paths."""
    if not LOCAL.exists() or not list(LOCAL.glob("*.npz")):
        from google.colab import drive
        if not Path("/content/drive/MyDrive").exists():
            drive.mount("/content/drive")
        src = Path(DRIVE_PACKS)
        if not src.exists():
            say(f"STOP: {src} not found. Check the Drive mount and the path.")
            return [], []
        LOCAL.mkdir(parents=True, exist_ok=True)
        shards = sorted(src.glob("*.npz"))
        say(f"copying {len(shards)} shards off Drive to local disk "
            f"(once -- every epoch after this reads local) ...")
        t0 = time.time()
        for n, p in enumerate(shards, 1):
            shutil.copy2(p, LOCAL / p.name)
            # Every 5, not every 10: 11.45 GB through the Drive mount is the
            # longest silent stretch in the job, and a watcher with no output
            # for four minutes concludes it has hung and kills a healthy run.
            if n % 5 == 0 or n == len(shards):
                gb = sum(f.stat().st_size for f in LOCAL.glob("*.npz")) / 1e9
                el = time.time() - t0
                say(f"  {n}/{len(shards)}  {gb:.2f} GB  {el:.0f}s  "
                    f"({gb * 1000 / max(el, 1):.0f} MB/s)")
    tr = sorted(LOCAL.glob("train_*.npz"))
    va = sorted(LOCAL.glob("val_*.npz"))
    if MAX_SHARDS:
        tr, va = tr[:MAX_SHARDS], va[:MAX_SHARDS]
    return tr, va


def evaluate(model, dev, val_shards, thr_list=(0.3, 0.5, 0.7, 0.9)):
    model.eval()
    counts = {t: [0, 0, 0, 0] for t in thr_list}
    probs = []
    with torch.no_grad():
        for p in val_shards:
            dl = DataLoader(Shard(p, train=False), batch_size=512, num_workers=WORKERS)
            for xb, yb in dl:
                pr = torch.sigmoid(model(xb.to(dev).float() / 255.0))[:, 0].cpu().numpy()
                tr = yb[:, 0].numpy() > 0.5
                probs.append(pr.astype(np.float16))
                for t in thr_list:
                    c, pd = counts[t], pr > t
                    c[0] += int((pd & tr).sum())
                    c[1] += int((pd & ~tr).sum())
                    c[2] += int((~pd & tr).sum())
                    c[3] += int((~pd & ~tr).sum())
    out = {}
    for t, (tp, fp, fn, tn) in counts.items():
        pre, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
        out[str(t)] = {"precision": round(pre, 4), "recall": round(rec, 4),
                       "f1": round(2 * pre * rec / max(pre + rec, 1e-9), 4),
                       "tp": tp, "fp": fp, "fn": fn}
    return out, (np.concatenate(probs) if probs else np.zeros(0, np.float16))


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ the card
    if DEVICE == "cpu":
        gpu = "cpu (smoke test)"
        say("running on CPU -- smoke test only, this is not the real run")
    else:
        if not torch.cuda.is_available():
            say("STOP: no GPU. Runtime > Change runtime type > T4 GPU, then rerun.")
            return 1
        gpu = torch.cuda.get_device_name(0)
        say(f"GPU: {gpu}")
        if "T4" not in gpu and not ALLOW_PAID:
            say(f"STOP: this is not the free lane -- '{gpu}' bills compute units on "
                f"connect. Delete the runtime, reconnect asking for T4, rerun. "
                f"(If a paid card is genuinely wanted, set ALLOW_PAID = True.)")
            return 1

    # ------------------------------------------------------------ the data
    train_shards, val_shards = fetch_shards()
    say(f"{len(train_shards)} train shards, {len(val_shards)} val shards")
    if not train_shards or not val_shards:
        say("STOP: a split is missing -- expected train_*.npz and val_*.npz")
        return 1

    dev = torch.device(DEVICE)
    model = Net(len(OFFSETS_S)).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=LR)

    # pos_weight needs the real class balance; count it rather than assume it.
    npos = ntot = 0
    for p in train_shards:
        y = np.load(p)["y"]
        npos += int((y[:, 0] > 0.5).sum())
        ntot += len(y)
    say(f"train {ntot:,} frames, {npos:,} jump onsets ({100 * npos / max(ntot, 1):.2f}%)")
    w = torch.tensor([(ntot - npos) / max(npos, 1), 8.0], device=dev)
    lossf = nn.BCEWithLogitsLoss(pos_weight=w)

    report = {"gpu": gpu, "epochs_planned": EPOCHS, "budget_minutes": MAX_MINUTES,
              "train_frames": ntot, "train_onsets": npos,
              "shards": len(train_shards), "epoch_log": []}
    t_start = time.time()
    out_of_time = False
    for ep in range(EPOCHS):
        if out_of_time:
            break
        model.train()
        order = list(range(len(train_shards)))
        random.Random(ep).shuffle(order)
        tot = nb = seen = 0
        for si, k in enumerate(order, 1):
            if (time.time() - t_start) / 60 > MAX_MINUTES:
                # Stop on a shard boundary, then fall through to the epoch's
                # eval and save. A partial epoch is still a trained model; a
                # killed session is not.
                say(f"budget of {MAX_MINUTES:.0f} min reached at epoch {ep + 1} "
                    f"shard {si}/{len(order)} -- evaluating and saving")
                report["stopped_early"] = {"epoch": ep + 1, "shard": si,
                                           "of": len(order)}
                out_of_time = True
                break
            ds = Shard(train_shards[k], train=True, salt=ep * 1000 + k)
            dl = DataLoader(ds, batch_size=BATCH, shuffle=True, num_workers=WORKERS,
                            drop_last=True)
            for bi, (xb, yb) in enumerate(dl):
                opt.zero_grad()
                loss = lossf(model(xb.to(dev).float() / 255.0), yb.to(dev))
                loss.backward()
                opt.step()
                tot += float(loss.detach())
                nb += 1
                seen += len(xb)
                if MAX_BATCHES and bi + 1 >= MAX_BATCHES:
                    break
            el = time.time() - t_start
            say(f"ep{ep + 1} shard {si}/{len(order)}  loss {tot / max(nb, 1):.4f}  "
                f"{seen:,} frames  {seen / max(el, 1):.0f}/s  {el / 60:.1f} min")
            # Written every shard, not every epoch: the idle timeout is unmeasured,
            # so the run must never be able to die with nothing on disk.
            (OUT / "progress.json").write_text(json.dumps(
                {"epoch": ep + 1, "shard": si, "of": len(order),
                 "loss": tot / max(nb, 1), "rate": seen / max(el, 1),
                 "minutes": el / 60}, indent=1))
        if nb == 0:
            break
        m, probs = evaluate(model, dev, val_shards)
        report["epoch_log"].append({"epoch": ep + 1, "loss": tot / max(nb, 1),
                                    "minutes": (time.time() - t_start) / 60, "val": m})
        say(f"--- epoch {ep + 1}: thr0.5 P {m['0.5']['precision']:.3f} "
            f"R {m['0.5']['recall']:.3f} F1 {m['0.5']['f1']:.3f}")
        torch.save(model.state_dict(), OUT / "idm_full.pt")
        (OUT / "report.json").write_text(json.dumps(report, indent=1))
        np.save(OUT / "val_probs.npy", probs)

    report["minutes_total"] = (time.time() - t_start) / 60
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    zp = OUT.parent / "idm_colab_out.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.iterdir()):
            z.write(f, f.name)
    say(f"\nDONE in {report['minutes_total']:.1f} min -> {zp} "
        f"({zp.stat().st_size / 1e6:.1f} MB)")
    say("Download it from the Files pane on the left, then DELETE THE RUNTIME.")
    try:
        from google.colab import files
        files.download(str(zp))
    except Exception as e:
        say(f"(auto-download unavailable: {e} -- use the Files pane)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

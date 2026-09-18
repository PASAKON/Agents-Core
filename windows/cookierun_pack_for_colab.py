#!/usr/bin/env python3
"""cookierun_pack_for_colab.py -- turn 799k loose JPEGs into something uploadable.

The corpus lives on winbox as one JPEG per frame, ~799,300 of them across 295
run directories. That shape is fine for local training and hopeless for Drive:
the upload is dominated by per-file overhead, not by bytes, and a training loop
that opens 799k files off a mounted Drive is slower than the CPU it was meant to
replace.

So pack it the way the trainer actually consumes it -- already decoded, already
resized to the model's 192x80, already uint8 -- into a handful of big shards.
Nothing is decoded twice and nothing is uploaded that the model will not read.

    frames  799,300 x 80 x 192 bytes = 12.3 GB raw
    shards  ~250 MB each, so ~50 files instead of 799,300

Labels ride along in the same shard, so a shard is self-contained: losing one
costs you that shard, not the alignment of everything after it.

    python cookierun_pack_for_colab.py --index idm_index.json --out D:/colab_pack
    python cookierun_pack_for_colab.py --index idm_index.json --out ... --max-runs 40
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W, H = 192, 80
SHARD_BYTES = 250 * 1024 * 1024


def pack(index_path: Path, out_dir: Path, split: str, max_runs):
    idx = json.loads(index_path.read_text(encoding="utf-8"))[split]
    runs = {}
    for take, rows in idx.items():
        for r in rows:
            runs.setdefault(str(Path(r[0]).parent.parent), []).append(r)
    names = sorted(runs)
    if max_runs:
        names = names[:max_runs]

    out_dir.mkdir(parents=True, exist_ok=True)
    per_shard = SHARD_BYTES // (H * W)
    buf_x, buf_y, buf_t, shard = [], [], [], 0
    kept = skipped = 0

    def flush():
        nonlocal buf_x, buf_y, buf_t, shard
        if not buf_x:
            return
        p = out_dir / f"{split}_{shard:03d}.npz"
        np.savez(p, x=np.array(buf_x, np.uint8),
                 y=np.array(buf_y, np.float32), t=np.array(buf_t, np.float64))
        print(f"  {p.name}  {len(buf_x):,} frames  {p.stat().st_size/1e6:.0f} MB")
        buf_x, buf_y, buf_t = [], [], []
        shard += 1

    for rn in names:
        rows = runs[rn]
        # Times come from frames.jsonl, not from the file order. The trainer
        # picks its stack by TIME (+-110/55 ms) because our recorder runs at
        # 18.2 fps against a claimed 24 -- pack the timestamps or that choice
        # cannot be reproduced on the other side.
        fj = Path(rn) / "frames.jsonl"
        try:
            meta = {f"f{json.loads(l)['i']:06d}.jpg": json.loads(l)["t"]
                    for l in fj.read_text(encoding="utf-8").splitlines() if l.strip()}
        except OSError:
            skipped += len(rows)
            continue
        for path, j, s in rows:
            im = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            t = meta.get(Path(path).name)
            if im is None or t is None:
                skipped += 1
                continue
            buf_x.append(cv2.resize(im, (W, H), interpolation=cv2.INTER_AREA))
            buf_y.append([j, s])
            buf_t.append(t)
            kept += 1
            if len(buf_x) >= per_shard:
                flush()
    flush()
    print(f"{split}: {kept:,} frames packed, {skipped:,} skipped, {shard} shards")
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-runs", type=int, default=None)
    a = ap.parse_args()
    out = Path(a.out)
    total = 0
    for split in ("train", "val"):
        print(f"--- {split}")
        total += pack(Path(a.index), out, split, a.max_runs)
    gb = sum(f.stat().st_size for f in out.glob("*.npz")) / 1e9
    print(f"\n{total:,} frames in {gb:.2f} GB across {len(list(out.glob('*.npz')))} files")
    print("Upload the directory, not the frames. One mount, a few big reads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

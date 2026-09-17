#!/usr/bin/env python3
"""cookierun_idm_data.py -- build the inverse-dynamics dataset from our own takes.

The plan for YouTube footage rests on one unproven claim: that a model shown the
frames BEFORE and AFTER a moment can say whether the player pressed jump there.
If that works, the 906k frames we already have (image + the exact key that was
pressed) can teach it, and it can then label any amount of video that has no key
log at all. If it does not work, nothing downstream is worth building, and the
cheapest way to find out is to test it against our own data where the answer is
known.

This builds that dataset. It does not train anything.

    python cookierun_idm_data.py                 # report what the corpus holds
    python cookierun_idm_data.py --out idx.json  # also write the sample index

Two decisions in here matter more than the model will:

**Split by take, never by frame.** Frames 40 ms apart are nearly the same
picture. Shuffling frames into train and test means the test set is a copy of
the training set, and the score comes back beautiful and means nothing. Whole
takes go to one side or the other.

**Score onsets, not frames.** A press onset happens on roughly 1 frame in 12, so
a model that answers "no press" to everything is already ~92% accurate. Accuracy
is the wrong number here; precision and recall on onsets are the right ones.
"""
import argparse
import json
import os
from pathlib import Path

DATA = Path.home() / "Documents" / "CookieRunScript"
PLAY_REC = DATA / "play_rec"

# A press is attributed to the frame whose timestamp is nearest the key event,
# and the window for that has to come from the frames, not from meta.json.
#
# meta.json says fps_target 24.0. The recorder actually delivers a median gap of
# **54.8 ms** -- about 18 fps -- with p90 at 68 ms. A hardcoded 30 ms window
# (half of a nominal 42 ms frame) therefore rejected 5.2% of all presses, and
# measuring them showed exactly what they were: median miss 33 ms, max 42 ms,
# i.e. presses landing in the middle of a longer-than-nominal gap. Not clock
# drift, not a broken recorder -- a window narrower than the data it filters.
#
# So derive it per run: half the median gap, with margin. Too wide would smear
# one press across two frames and teach the model that jumps come in pairs.
MATCH_FRACTION = 0.65     # of the median frame gap
MATCH_FLOOR_S = 0.030
MIN_FRAMES = 300          # anything shorter never really ran


def run_samples(run: Path):
    """[(img_path, jump, slide)] for one run, or None if it is not usable."""
    fj, kj = run / "frames.jsonl", run / "keys.jsonl"
    img = run / "img"
    if not (fj.exists() and kj.exists() and img.is_dir()):
        return None
    try:
        frames = [json.loads(l) for l in fj.read_text(encoding="utf-8").splitlines() if l.strip()]
        keys = [json.loads(l) for l in kj.read_text(encoding="utf-8").splitlines() if l.strip()]
    except (OSError, ValueError):
        return None
    if len(frames) < MIN_FRAMES:
        return None

    # Onsets only: a held key repeats "d" in some recorders, and a hold is one
    # decision, not forty. (Ours does not repeat -- measured -- but a dataset
    # builder that depends on that staying true is a trap for a later recorder.)
    held, onsets = set(), []
    for e in keys:
        k = str(e.get("k", "")).lower()
        if e.get("e") != "d":
            held.discard(k)
            continue
        if k in held:
            continue
        held.add(k)
        onsets.append((float(e["t"]), k))

    times = [f["t"] for f in frames]
    gaps = sorted(b - a for a, b in zip(times, times[1:]))
    median_gap = gaps[len(gaps) // 2] if gaps else 0.042
    match_s = max(median_gap * MATCH_FRACTION, MATCH_FLOOR_S)
    lab = [[0, 0] for _ in frames]
    lost = 0
    for t, k in onsets:
        # nearest frame by time; frames.jsonl is in order so a scan is fine
        lo, hi = 0, len(times) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if times[mid] < t:
                lo = mid + 1
            else:
                hi = mid
        best = min((abs(times[j] - t), j) for j in range(max(0, lo - 2), min(len(times), lo + 3)))
        if best[0] > match_s:
            lost += 1
            continue
        if k in ("space", "up", "w"):
            lab[best[1]][0] = 1
        elif k in ("down", "s"):
            lab[best[1]][1] = 1

    out = []
    for f, (j, s) in zip(frames, lab):
        p = img / f"f{f['i']:06d}.jpg"
        if p.exists():
            out.append((str(p), j, s))
    return {"samples": out, "onsets": len(onsets), "unmatched": lost,
            "frames": len(frames), "median_gap": median_gap}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="write the sample index here")
    ap.add_argument("--max-takes", type=int, default=None)
    a = ap.parse_args()

    takes = sorted(p for p in PLAY_REC.glob("bot_session-*") if p.is_dir())
    if a.max_takes:
        takes = takes[-a.max_takes:]

    index, tot_f, all_gaps = {}, 0, []
    tot_j = tot_s = tot_on = tot_lost = 0
    for take in takes:
        rows = []
        on = lost = 0
        take_gaps = []
        for run in sorted(p for p in take.iterdir() if p.is_dir()):
            r = run_samples(run)
            if not r:
                continue
            rows += r["samples"]
            on += r["onsets"]
            lost += r["unmatched"]
            take_gaps.append(r["median_gap"])
        if not rows:
            continue
        j = sum(x[1] for x in rows)
        s = sum(x[2] for x in rows)
        index[take.name] = rows
        tot_f += len(rows)
        tot_j += j
        tot_s += s
        tot_on += on
        tot_lost += lost
        all_gaps.extend(take_gaps)

    print(f"takes with usable runs : {len(index)}")
    print(f"frames on disk         : {tot_f:,}")
    print(f"jump onsets            : {tot_j:,}  ({100 * tot_j / max(tot_f, 1):.2f}% of frames)")
    print(f"slide onsets           : {tot_s:,}  ({100 * tot_s / max(tot_f, 1):.2f}% of frames)")
    print(f"key onsets in logs     : {tot_on:,}")
    print(f"  unmatched to a frame : {tot_lost:,}  ({100 * tot_lost / max(tot_on, 1):.2f}%)")
    if all_gaps:
        g = sorted(all_gaps)[len(all_gaps) // 2]
        print(f"median frame gap       : {g * 1000:.1f} ms  = {1 / g:.1f} fps actual "
              f"(meta.json claims 24.0)")
    print()
    print("A model that answers 'no press' to every frame would already score "
          f"{100 * (1 - (tot_j + tot_s) / max(tot_f, 1)):.1f}% accuracy.")
    print("So accuracy is not the number to watch -- precision/recall on onsets is.")

    if tot_lost > tot_on * 0.02:
        print(f"\nWARNING: {100 * tot_lost / max(tot_on, 1):.1f}% of presses could not be "
              f"attributed to any frame. Either the "
              f"recorder dropped frames or the two clocks disagree -- labels built "
              f"on this would be quietly wrong.")

    if a.out:
        # Split by TAKE. Every frame of a take lands on one side of the line.
        names = sorted(index)
        cut = int(len(names) * 0.85)
        payload = {"train": {n: index[n] for n in names[:cut]},
                   "val": {n: index[n] for n in names[cut:]}}
        Path(a.out).write_text(json.dumps(payload), encoding="utf-8")
        tr = sum(len(v) for v in payload["train"].values())
        va = sum(len(v) for v in payload["val"].values())
        print(f"\nwrote {a.out}: {len(payload['train'])} takes / {tr:,} frames train, "
              f"{len(payload['val'])} takes / {va:,} frames val (no take spans both)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""cookierun_press_audit.py -- what is actually IN the play corpus, per source.

Training runs on takes, and a take can be worthless in a way no aggregate metric
shows. On 2026-09-09 two recordings finished with no key events at all -- the
recorder was running, the game was playing, nothing wrote to keys.jsonl. They
contributed 12.8 % "never press" rows to the training set and every v8 arm
learned, correctly, that the right move is usually to do nothing. The arms were
compared against each other, all of them equally poisoned, so the comparison
looked clean.

So: before any training run, print presses per source and refuse the sources
that have none. A take with zero presses is not a quiet take, it is a broken
recorder, and the difference is invisible once the rows are shuffled together.

    python cookierun_press_audit.py              # every source, one line each
    python cookierun_press_audit.py --takes      # one line per take, worst first
    python cookierun_press_audit.py --since 3    # only takes from the last 3 days

Exit 1 if any source contributes takes with no presses at all -- so a build
script can gate on it rather than relying on somebody reading the output.
"""
import argparse
import json
import sys
import time
from pathlib import Path

# Windows defaults stdout to cp1252, and everything here prints text that
# came from somewhere else -- a lease holder's name, a window title, a
# screen name. On 2026-09-18 a lease taken with a U+25D1 in it crashed
# this whole check on the print, so the farm's health was unreadable
# because of a character in somebody's label. Third instance of this same
# cp1252 fault today (esc's ESC_HOLD write, session-rename, this).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path.home() / "Documents" / "CookieRunScript"
# Both trees hold runs in the same shape (<take>/<run-*>/keys.jsonl); they differ
# only in who was pressing, which is exactly what this is here to tell apart.
ROOTS = [DATA / "play_rec", DATA / "modelplay"]


def source_of(take: Path) -> str:
    """Who produced this take -- the only grouping that matters for training.

    'play_rec' is not a synonym for human play, whatever its name suggests: 145
    of its 157 takes are bot_session-*, the champion recording itself. A corpus
    that is entirely one model playing is a corpus that can only teach the next
    model to be that model.
    """
    n = take.name
    if n.startswith("bot_session"):
        return "bot self-play (play_rec)"
    if n.startswith("session"):
        return "model play (modelplay)"
    if n.startswith("jumpsweep"):
        return "jump sweep (no keys)"
    return "human / unlabelled"


# Sources that hold no key recording by design -- counting them as "dead takes"
# would be an accusation against a file that was never meant to exist.
NO_KEYS = {"jump sweep (no keys)"}


def run_stats(run: Path) -> tuple[int, int, int]:
    """(frames, jump presses, slide presses) for one run.

    Three layouts live under these trees and only one of them is a recording of
    somebody pressing keys:

      play_rec/<take>/run-*/   frames.jsonl + keys.jsonl -- what was PRESSED
      modelplay/<take>/run-*/  decisions.jsonl           -- what the model CHOSE
      play_rec/jumpsweep*/     frames/ + meta.json       -- a controlled sweep

    Reading only the first layout made the other two report zero presses across
    1265 runs, which reads as "1265 broken recorders" when the truth is "wrong
    file". Both numbers are worth having, but they answer different questions:
    keys.jsonl is an imitation target, decisions.jsonl is the champion's own
    output and training on it teaches a model to be the model it already has.
    """
    frames = 0
    fj = run / "frames.jsonl"
    if fj.exists():
        try:
            with fj.open(encoding="utf-8", errors="replace") as f:
                frames = sum(1 for _ in f)
        except OSError:
            pass

    dj = run / "decisions.jsonl"
    if not fj.exists() and dj.exists():
        jump = slide = 0
        try:
            with dj.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    frames += 1
                    try:
                        act = json.loads(line).get("act")
                    except ValueError:
                        continue
                    if act == "jump":
                        jump += 1
                    elif act == "slide":
                        slide += 1
        except OSError:
            pass
        return frames, jump, slide
    # keys.jsonl is {"t": <mono>, "k": "space"|"down", "e": "d"|"u"} -- "space"
    # is jump and "down" is slide, and only "d" is a press. Counting releases
    # too would double every rate and hide nothing, but it would also make the
    # per-1000-frames number meaningless to compare against a model's output.
    jump = slide = 0
    held: set[str] = set()
    kj = run / "keys.jsonl"
    if kj.exists():
        try:
            with kj.open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except ValueError:
                        continue
                    k = str(e.get("k", "")).lower()
                    if e.get("e") != "d":
                        held.discard(k)
                        continue
                    # Count ONSETS, not "d" events. Holding a key emits a
                    # repeat stream, and a label built from raw downs says the
                    # player pressed jump forty times where they pressed it
                    # once and held -- which is a different action, and the one
                    # the model would be asked to imitate.
                    if k in held:
                        continue
                    held.add(k)
                    if k in ("space", "up", "w"):
                        jump += 1
                    elif k in ("down", "s"):
                        slide += 1
        except OSError:
            pass
    return frames, jump, slide


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--takes", action="store_true", help="one line per take, worst first")
    ap.add_argument("--since", type=float, default=None, help="only takes newer than N days")
    a = ap.parse_args()

    cutoff = time.time() - a.since * 86400 if a.since else 0
    rows = []
    for root in ROOTS:
        if not root.is_dir():
            continue
        for take in sorted(p for p in root.iterdir() if p.is_dir()):
            if take.stat().st_mtime < cutoff:
                continue
            runs = [r for r in take.iterdir() if r.is_dir()]
            if not runs:
                continue
            f = j = s = 0
            for r in runs:
                rf, rj, rs = run_stats(r)
                f += rf
                j += rj
                s += rs
            rows.append({"take": take.name, "src": source_of(take), "runs": len(runs),
                         "frames": f, "jump": j, "slide": s})

    if not rows:
        print("no takes found")
        return 1

    # A take with a handful of frames is an aborted round, not a broken
    # recorder -- the bot opened a directory and the run never started. Those
    # are worth excluding from a training set too, but they are not evidence of
    # anything and listing 55 of them buries the ones that matter.
    dead = [r for r in rows if r["jump"] + r["slide"] == 0
            and r["frames"] >= 100 and r["src"] not in NO_KEYS]
    stub = [r for r in rows if r["frames"] < 100 and r["src"] not in NO_KEYS]

    if a.takes:
        print(f"{'take':<34} {'src':<26} {'runs':>4} {'frames':>8} {'jump':>6} {'slide':>6} {'per 1k':>7}")
        for r in sorted(rows, key=lambda r: (r["jump"] + r["slide"]) / max(r["frames"], 1)):
            rate = 1000 * (r["jump"] + r["slide"]) / max(r["frames"], 1)
            flag = "  <-- NO PRESSES" if r["jump"] + r["slide"] == 0 else ""
            print(f"{r['take']:<34} {r['src']:<26} {r['runs']:>4} {r['frames']:>8} "
                  f"{r['jump']:>6} {r['slide']:>6} {rate:>7.1f}{flag}")
        print()

    print(f"{'source':<26} {'takes':>6} {'runs':>6} {'frames':>9} {'f/run':>6} {'jump':>7} "
          f"{'slide':>7} {'per 1k':>7} {'per run':>8} {'dead':>5}")
    for src in sorted({r["src"] for r in rows}):
        g = [r for r in rows if r["src"] == src]
        f = sum(r["frames"] for r in g)
        j = sum(r["jump"] for r in g)
        s = sum(r["slide"] for r in g)
        n = sum(r["runs"] for r in g)
        d = len([r for r in g if r in dead])
        print(f"{src:<26} {len(g):>6} {n:>6} {f:>9} {f / max(n, 1):>6.0f} {j:>7} {s:>7} "
              f"{1000 * (j + s) / max(f, 1):>7.1f} {(j + s) / max(n, 1):>8.0f} {d:>5}")
    print("  'model play' counts decisions the champion made, not keys a player pressed.")
    # Compare sources on PER RUN, never per 1000 frames. The two trees sample at
    # different rates -- key recordings land near 12 fps, decision logs near 30 --
    # so the same behaviour shows up as 125/1k against 43/1k, a 3x gap that is
    # entirely the denominator. Per round they agree (about 380 and 330), which
    # is the answer: the bot presses about the same either way.

    if stub:
        print(f"\n{len(stub)} take(s) hold under 100 frames -- rounds that opened and "
              f"never ran. Harmless, but they are not data; drop them from the set.")
    if dead:
        print(f"\nREFUSE: {len(dead)} take(s) played a full round and recorded not one "
              f"press. That is a broken recorder, not careful play -- and mixed into a "
              f"set it teaches the model that doing nothing is usually right.")
        for r in dead[:10]:
            print(f"  {r['take']}  ({r['frames']} frames, {r['runs']} runs)")
        return 1
    print("\nevery take that ran a round has presses")
    return 0


if __name__ == "__main__":
    sys.exit(main())

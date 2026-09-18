#!/usr/bin/env python3
"""cookierun_match_test.py -- score every screen detector against one frame.

When the navigator sits on a screen it should know, there are only three
possibilities, and guessing between them has cost this project days:

  the template does not match      -> the detector is broken
  it matches but nothing happens   -> the CLICK is wrong (game_settings, 2026-09-16:
                                      matched 0.9987 every time, pressed 115 px
                                      past the X, forever)
  it matches and something else     -> another screen outranks it

This answers the first and third directly: it runs every entry in screens[]
against a saved frame of the game rect and prints the score next to the
threshold, so "it should have matched" becomes a number instead of an opinion.

    python cookierun_match_test.py <frame.png>
"""
import json
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

ROOT = Path(r"C:\Users\UsEr\cookierun-bot")


def main() -> int:
    frame = cv2.imread(sys.argv[1])
    if frame is None:
        print(f"cannot read {sys.argv[1]}")
        return 2
    H, W = frame.shape[:2]
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    print(f"frame {W}x{H}\n")
    rows = []
    for s in cfg["screens"]:
        tpl_rel = s.get("template")
        rel = s.get("rel")
        if not tpl_rel or not rel:
            continue
        tpl = cv2.imread(str(ROOT / tpl_rel))
        if tpl is None:
            rows.append((s["name"], None, s.get("threshold", 0.85), "template file missing"))
            continue
        x, y, w, h = rel
        x0, y0 = int(x * W), int(y * H)
        x1, y1 = x0 + int(w * W), y0 + int(h * H)
        box = frame[y0:y1, x0:x1]
        th, tw = tpl.shape[:2]
        if box.shape[0] < th or box.shape[1] < tw:
            # The bug that made 11 detectors dead on 2026-09-16: int() floors the
            # box, so a search box specified exactly the template's size lands a
            # pixel short and matchTemplate refuses outright.
            rows.append((s["name"], None, s.get("threshold", 0.85),
                         f"search box {box.shape[1]}x{box.shape[0]} SMALLER than "
                         f"template {tw}x{th}"))
            continue
        res = cv2.matchTemplate(box, tpl, cv2.TM_CCOEFF_NORMED)
        _, score, _, _ = cv2.minMaxLoc(res)
        rows.append((s["name"], float(score), s.get("threshold", 0.85), ""))

    hits = [r for r in rows if r[1] is not None and r[1] >= r[2]]
    print("MATCHES (score >= threshold):")
    for n, sc, th, _ in sorted(hits, key=lambda r: -r[1]):
        print(f"  {n:<22} {sc:.4f}  >= {th}")
    if not hits:
        print("  none -- the navigator cannot name this screen at all")
    print("\nnear misses (within 0.15 of threshold):")
    for n, sc, th, _ in sorted((r for r in rows if r[1] is not None and th_miss(r)),
                               key=lambda r: -r[1]):
        print(f"  {n:<22} {sc:.4f}   threshold {th}")
    broken = [r for r in rows if r[1] is None]
    if broken:
        print("\nBROKEN ENTRIES (can never match):")
        for n, _, _, why in broken:
            print(f"  {n:<22} {why}")
    return 0


def th_miss(r):
    _, sc, th, _ = r
    return th - 0.15 <= sc < th


if __name__ == "__main__":
    raise SystemExit(main())

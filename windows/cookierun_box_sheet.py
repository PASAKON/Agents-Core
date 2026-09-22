"""One image with each EP6 round's Result panel, so boxes can be counted in one look.

Picks the real no-control rounds after a start time from rounds.jsonl, takes
each run's last end frame (the Result panel), and stacks a downscaled copy of
the whole panel with the round's time and length burned in. Whole panel, not a
guessed crop: the box badge's position on an EP6 Result has not been measured
yet, and a crop in the wrong place would report zero boxes very convincingly.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

DATA = Path.home() / "Documents" / "CookieRunScript" / "modelplay"
since = sys.argv[1] if len(sys.argv) > 1 else "2026-09-23T04:38"
out = Path(sys.argv[2] if len(sys.argv) > 2 else r"C:\mooniex\pclease\box_sheet.png")

rows = []
for line in (DATA / "rounds.jsonl").read_text(encoding="utf-8").splitlines():
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if (r.get("no_control") is True and r.get("dry") is False
            and (r.get("seconds") or 0) > 10 and str(r.get("t", "")) >= since
            and r.get("end") != "stop-file"):
        rows.append(r)

tiles = []
for r in rows:
    # rounds.jsonl keeps only the folder NAME ("run-1790115045"); the folder
    # itself lives under whichever session wrote it.
    hits = list(DATA.glob(f"session-*/{r.get('dir')}")) if r.get("dir") else []
    d = hits[0] if hits else None
    ends = sorted((d / "end").glob("end_*.jpg"), key=lambda p: int(p.stem.split("_")[1])) if d else []
    if not ends:
        print(f"{r['t']}: no end frames in {d}")
        continue
    im = cv2.imread(str(ends[-1]))
    im = cv2.resize(im, (632, 356), interpolation=cv2.INTER_AREA)
    label = f"{str(r['t'])[11:19]}  {r.get('seconds', 0):.0f}s  coins {r.get('coins')}  end {r.get('end')}"
    cv2.rectangle(im, (0, 0), (632, 26), (0, 0, 0), -1)
    cv2.putText(im, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    tiles.append(im)
    print(f"{r['t']}  {r.get('seconds', 0):.0f}s  end={r.get('end')}  frame={ends[-1].name}")

if tiles:
    pad = [np.zeros_like(tiles[0])] * (len(tiles) % 2)
    tiles += pad
    grid = np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)])
    cv2.imwrite(str(out), grid)
    print(f"wrote {out}  ({len(rows)} rounds)")

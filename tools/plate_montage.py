#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tile every character/location/prop plate into ONE labelled sheet to look at.

Why: a script written from remembered descriptions drifts from the plates, and
the writer never notices. The rule (CEO 2026-09-18) is that nobody writes a shot
sheet without having looked at every plate at least once.

Why one sheet and not N images: an image costs context whether you needed it or
not, and looking at fifteen of them one at a time costs fifteen times as much as
looking at one. Sized so faces stay readable and the whole thing is a single
look.

    python3 tools/plate_montage.py <out.jpg> <dir-or-file> [more...]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

EXT = {".png", ".jpg", ".jpeg", ".webp"}
LABEL_H = 22
# One look has a budget: keep the whole sheet near 1600px wide and give each
# plate as much room as the count allows, so faces stay readable.
SHEET_W = 1600
COLS_MAX = 5


def collect(args):
    out = []
    for a in args:
        p = Path(a)
        if p.is_dir():
            out += sorted(q for q in p.iterdir() if q.suffix.lower() in EXT)
        elif p.suffix.lower() in EXT:
            out.append(p)
    return out


def build(paths, dest: Path):
    if not paths:
        raise SystemExit("no images found")
    # Fewer columns for a small set, so each plate is big enough to judge a face.
    import math
    cols = max(1, min(COLS_MAX, len(paths), math.ceil(math.sqrt(len(paths)))))
    rows = (len(paths) + cols - 1) // cols
    cell_w = SHEET_W // cols
    cells = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((cell_w, cell_w * 2))     # portrait plates keep their shape
        cells.append((p.stem, im))
    cell_h = max(im.height for _, im in cells) + LABEL_H
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "black")
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(cells):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        d.text((x + 6, y + 5), name[:46], fill="yellow")
        sheet.paste(im, (x + (cell_w - im.width) // 2, y + LABEL_H))
    sheet.save(dest, quality=85)
    print(f"{dest}  {sheet.size[0]}x{sheet.size[1]}  {len(cells)} plates  "
          f"{dest.stat().st_size//1024} KB")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(2)
    build(collect(sys.argv[2:]), Path(sys.argv[1]))

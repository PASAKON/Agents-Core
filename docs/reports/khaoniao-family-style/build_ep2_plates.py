#!/usr/bin/env python3
"""Build round7.json for tools/chatgpt_images.py — the two NEW EP2 plates for Flow (free stills).

CEO 2026-10-01: "อนุมัติงบ 400 เครดิต ยิง EP 2". Everything else EP2 needs (mimi__dry, mimi__wet, mother__home,
brother__wfh, loc__living, loc__dining) already exists from EP1 and is reused as it is.
Both new plates are EMPTY sets (no people, no animals) so a shot's own cast is the only cast; each attaches the
approved page cover that holds the house look. Every prompt is ONE line (the composer drops newlines).
    python build_ep2_plates.py [outfile]
"""
import json
import pathlib
import sys

from build_ep1_plates import ATTACH, LOC_STYLE

ITEMS = [
    ("loc__bathroom", "cover2", LOC_STYLE +
     " THE SET: a small Thai home bathroom of the same house by day: glossy pale-blue wall tiles, a cream tiled floor, an open doorway on the LEFT side of the picture, "
     "a low BLUE plastic basin full of warm water with white soap bubbles standing on the tiled floor on the RIGHT side of the picture, a RED plastic dipper bowl with a handle floating in the basin, "
     "a small plastic stool, a plain white bath mat, a small window with soft daylight. Wide enough to kneel beside the basin. No towel in the picture."),
    ("loc__sofa_low", "cover2", LOC_STYLE +
     " THE SET: the living room of the same house by day seen from FLOOR LEVEL, right in front of the small tidy sofa: the low front edge and four short wooden legs of the sofa frame a wide, low, shadowy hollow under the sofa "
     "with a clean cream marble floor inside it, a slanting shaft of warm daylight reaching into the hollow so the floor under the sofa is clearly readable (not black), "
     "and the brighter living room (a desk with a laptop, a round dog bed, a plant shelf) visible beyond at the left and right sides. The camera is a few centimetres above the floor."),
]


def build():
    return [{"name": n, "prompt": p.replace("\n", " "), "attach": ATTACH[a]} for n, a, p in ITEMS]


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("round7.json")
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(build()), "prompts")

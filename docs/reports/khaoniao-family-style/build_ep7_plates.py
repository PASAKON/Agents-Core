#!/usr/bin/env python3
"""Build the EP7 plates JSON for tools/chatgpt_images.py — six NEW plates for Flow (free stills).

CEO 2026-10-14: EP7 = the 12-shot episode (~180 credits). Reused as they are: mimi__dry, brother__wfh.
New: mother__night (the mother in pyjamas), cat__riao (a front crop of sheet-riao-v1), and four NIGHT sets
(CMO_Gate_Flow_Omni1.1_Continuity: night needs a night plate): loc__living_night, loc__momroom_night,
loc__landing_night, loc__broroom_night. Sets are EMPTY (no people, no animals); each attaches the page cover that holds
the house look. Every prompt is ONE line (the composer drops newlines).
    python build_ep7_plates.py [outfile]
"""
import json
import pathlib
import sys

from build_ep1_plates import ATTACH, CHAR_STYLE, FR, LOC_STYLE

NIGHT = ("It is two o'clock in the morning: low-key cinematic night lighting, most of the room in soft blue shadow with warm "
         "pools of dim orange lamp light, every object still clearly readable, no pitch-black areas. No mirror, no framed picture, "
         "no photograph on any wall.")

ITEMS = [
    ("mother__night", FR + "mother_front.png", CHAR_STYLE +
     " CHANGE: she wears a soft pale-blue short-sleeved floral pyjama top and matching long pyjama trousers instead of the apron and sarong, bare feet, "
     "her hair in a loose low bun with NO ladle in it, a sleepy kind half-closed smile; her face, round rosy cheeks and gold amulet necklace are exactly as in image 1."),
    ("cat__riao", FR + "riao_front.png",
     "Stylised Thai family-comedy cartoon in 3D, clearly a CARTOON and not a photograph, the same rendering as image 1. "
     "Image 1 is the approved reference of the cat Riao: keep his face, fur colours, markings, proportions and giant plume tail exactly as in image 1. "
     "ONE single figure, full body, standing on four short legs, in three-quarter view facing the camera, centred, on a PLAIN LIGHT GREY studio background with nothing else in the frame. "
     "No text, no letters, no numbers, no logo, no watermark, no second figure, no turnaround sheet, no labels."),
    ("loc__living_night", ATTACH["cover2"], LOC_STYLE +
     " THE SET: the living room of the same house AT NIGHT: a work-from-home desk with a closed laptop beside a window at the LEFT with the curtains drawn and a faint blue glow behind them, "
     "a tidy small sofa in the middle, a round coffee table, a small round dog bed in a corner, a wooden shelf with potted plants lit by one dim warm orange lamp, the dark dining area behind on the RIGHT, "
     "a wooden front door at the far RIGHT edge with a woven straw doormat in front of it and a low wooden shoe rack beside it, and a dark corridor opening to the bedrooms at the far LEFT edge with one closed wooden bedroom door visible in it, cream marble floor. " + NIGHT),
    ("loc__momroom_night", ATTACH["cover2"], LOC_STYLE +
     " THE SET: a Thai mother's bedroom in the same house AT NIGHT: a closed wooden bedroom door at the far LEFT edge of the picture, a double bed with a cream floral bedspread and two pillows on the RIGHT side, "
     "a small wooden bedside table with a bedside lamp glowing dim warm orange next to the bed, a wooden wardrobe against the back wall, cream marble floor, a clear empty floor space in front of the door wide enough for a small dog to sit. The bed is EMPTY. " + NIGHT),
    ("loc__landing_night", ATTACH["cover2"], LOC_STYLE +
     " THE SET: the upstairs landing of the same Thai townhouse AT NIGHT: a dark wooden stair banister on the LEFT side where the stairs go down, cream marble floor, "
     "two closed white wooden doors, one in the centre-left with a small woven straw mat in front of it and one on the RIGHT side, a single small dim warm night-light on the wall, a clear floor space in front of the doors. " + NIGHT),
    ("loc__broroom_night", ATTACH["cover2"], LOC_STYLE +
     " THE SET: a tidy young man's bedroom in the same house AT NIGHT: a single bed with a plain grey sheet and one pillow on the LEFT side, a small wooden desk with a closed laptop against the back wall, "
     "a window with a closed blue curtain glowing faintly blue, a dim warm bedside lamp, and on the RIGHT side a round soft BROWN cushion dog bed lying on the cream marble floor against the wall. The room is EMPTY of people and animals. " + NIGHT),
]


def build():
    return [{"name": n, "prompt": p.replace("\n", " "), "attach": a} for n, a, p in ITEMS]


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("round8.json")
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(build()), "prompts")

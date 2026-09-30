#!/usr/bin/env python3
"""Build round6.json for tools/chatgpt_images.py — the EP1 plates for Flow (free stills).

CEO 2026-09-30: "เตรียมเนื้อหาเลยได้ อนุมัติ 300 credit ยิง EP แรก".
One plate = ONE single image (Flow binds each chip as one picture; never a sheet). Plain light-grey grounds for
characters so the model takes the figure and nothing else; locations are EMPTY (no people, no animals) so a
shot's own cast is the only cast. Characters attach a front crop of the approved sheet (refs/fronts/); the
locations attach the page covers, which already hold the house (marble floor, wooden door frame, white fridge).
Every prompt is ONE line (the composer drops newlines).
    python build_ep1_plates.py [outfile]
"""
import json
import pathlib
import sys

from build_page_assets import MIMI, WIN_REFS

FR = WIN_REFS + "\\fronts\\"
OUT = r"C:\mooniex\khaoniao\out" + "\\"

CHAR_STYLE = (
    "Stylised Thai family-comedy cartoon in 3D, clearly a CARTOON and not a photograph: chunky rounded shapes, funny big-head proportions, "
    "very large friendly expressive eyes, high-end 3D finish with a warm key light, a cool rim light and soft shadows. "
    "Image 1 is the approved reference: keep the face, hair, outfit, markings and proportions exactly as in image 1 except for the change named below. "
    "ONE single figure, full body head to toe, standing, facing the camera three-quarter, centred, on a PLAIN LIGHT GREY studio background with nothing else in the frame. "
    "No text, no letters, no numbers, no logo, no watermark, no second figure, no turnaround sheet, no labels."
)
LOC_STYLE = (
    "Stylised Thai family-comedy cartoon in 3D, the SAME rendering as image 1 (chunky rounded shapes, warm key light, cool rim light, soft global illumination), clearly a cartoon and not a photograph. "
    "Image 1 shows the family's house and its look: keep the marble floor tiles, the wooden door frame, the plants and the colour palette. "
    "This is an EMPTY set: no people, no animals, no figures, no shadows of figures. "
    "No text, no letters, no numbers, no house number, no sign, no logo, no watermark anywhere in the picture."
)

ITEMS = [
    ("mimi__wet", "mimi", CHAR_STYLE + " " + MIMI +
     " CHANGE: she is SOAKED by flood water: wet clumpy fur plastered flat and dripping, water beading on the silver beard, heavy wet dripping ears, "
     "a miserable betrayed face with big shiny eyes; no towel. She stands on all four paws."),
    ("mother__out", "mother",
     CHAR_STYLE + " CHANGE: she wears bright pink rubber rain boots instead of the pink slippers and carries an empty woven bamboo basket on her forearm; everything else is exactly as in image 1."),
    ("seller__truck", "mother",
     "Stylised Thai family-comedy cartoon in 3D, clearly a cartoon and not a photograph: chunky rounded shapes, funny big-head proportions, very large friendly expressive eyes, high-end 3D finish with a warm key light, a cool rim light and soft shadows. "
     "Image 1 is the STYLE reference only (the same 3D cartoon rendering, proportions and lighting): do NOT copy her face, hair or clothes. "
     "NEW CHARACTER: a cheerful Thai vegetable-truck seller, a lean wiry sun-tanned man of about fifty-five with a big toothy grin and crinkled eyes, a sun-faded wide straw hat, "
     "a faded green short-sleeve polo shirt with the sleeves rolled, a blue-and-white checked pha khao ma scarf around his neck, dark knee-length shorts and black rubber boots, holding a bunch of green morning glory. "
     "ONE single figure, full body head to toe, standing, facing the camera three-quarter, centred, on a PLAIN LIGHT GREY studio background. "
     "No text, no letters, no numbers, no logo, no watermark, no second figure, no turnaround sheet, no labels."),
    ("loc__doorway", "cover3", LOC_STYLE +
     " THE SET: the open front doorway of the Thai townhouse seen from INSIDE the room, looking out: warm yellow indoor light, cream marble floor in the foreground, "
     "the wooden door frame, and beyond the doorway a steel gate with the street outside UNDER BROWN FLOOD WATER up to the lower bars of the gate, grey rainy daylight outside, a few potted plants by the door."),
    ("loc__doorway_v2", "cover3", LOC_STYLE +
     " THE SET: the open front doorway of the Thai townhouse seen from INSIDE the room, looking out, at a low camera height like a small dog's eye level: warm yellow indoor light on the cream marble floor and the wooden door frame. "
     "THE FLOOD IS THE SUBJECT: the whole ground outside the door is completely covered by a wide sheet of opaque muddy CHOCOLATE-BROWN flood water that has risen right up to the door threshold and is lapping over the doorstep, with ripples and floating leaves, "
     "the steel gate standing in the brown water with the water covering its lower bars, heavy grey rain falling outside, the street beyond also under brown water; the indoor floor stays dry and clean."),
    ("loc__living", "cover2", LOC_STYLE +
     " THE SET: the living room of the same house by day: a work-from-home desk with an open laptop and a mug beside a window, a tidy small sofa, a small round dog bed in a corner, "
     "a wooden shelf with potted plants, cream marble floor, warm light, the open dining area and the white two-door fridge visible behind."),
    ("loc__dining", "cover2", LOC_STYLE +
     " THE SET: the dining area of the same house in warm evening light: a wooden table with a bamboo basket of sticky rice with steam rising, a plate of grilled chicken and a bowl of papaya salad, "
     "four chairs, cream marble floor, the white two-door fridge and open kitchen shelves behind."),
    ("loc__street", "cover3", LOC_STYLE +
     " THE SET: a Thai village street under knee-deep BROWN FLOOD WATER in grey overcast daylight, a small blue pickup truck parked in the water loaded with baskets of green morning glory, bok choy and long beans, "
     "a loudspeaker on the cab roof, townhouse fronts and electric poles along the street, a steel gate at the side."),
]

ATTACH = {
    "mimi": FR + "mimi_front.png", "mother": FR + "mother_front.png",
    "cover3": OUT + "cover-3-doorway.png", "cover2": OUT + "cover-2-table.png",
}


def build():
    return [{"name": n, "prompt": p.replace("\n", " "), "attach": ATTACH[a]} for n, a, p in ITEMS]


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("round6.json")
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(build()), "prompts")

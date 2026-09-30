#!/usr/bin/env python3
"""Build round5.json for tools/chatgpt_images.py — page profile pictures (3) and covers (3).

CEO 2026-09-30: "ทำ ปก และ cover และตั้งชื่อเพจ … อย่างละ 3 ทำรูปมาอย่างละ 3 จะเลือกเอง".
The cast is the one in STYLE-CARD.md (sheets v3 + sister v4). References are crops of the approved sheets:
  refs/mimi_cartoon_ref.jpg      Mimi alone (profile pictures)
  refs/family_lineup_ref.jpg     mother, brother, Mimi, sister side by side (covers)
Pictures carry NO text: an image model garbles Thai letters, and the page name is shown by Facebook itself.
Every prompt is ONE line (the composer drops newlines).
    python build_page_assets.py [outfile]
"""
import json
import pathlib
import sys

WIN_REFS = r"C:\mooniex\khaoniao\refs"

STYLE = (
    "Stylised Thai family-comedy cartoon in 3D, clearly a CARTOON and not a photograph: chunky rounded shapes, funny big-head proportions, "
    "very large friendly expressive eyes, high-end 3D finish with a warm key light, a cool rim light, soft global illumination and soft shadows. "
    "Image 1 is the approved character reference: keep every face, hair, outfit, marking and proportion exactly as in image 1. "
    "No text, no letters, no numbers, no logo, no watermark anywhere in the picture."
)

MIMI = (
    "Mimi is the small fluffy BLACK female dog from image 1: wavy black coat, silver-white eyebrow tufts, silver beard with tan under the chin, "
    "a white bib on the chest, long drop ears with silver tips, dark brown eyes, a little pink tongue. Never brown, never solid black."
)

PROFILE = "SQUARE 1:1 profile picture for a Facebook page, face or subject centred so it survives a circular crop, bold and readable at 40 pixels. "
COVER = (
    "WIDE PANORAMIC 16:9 Facebook cover banner. Keep every important subject inside the middle horizontal band and leave the top 18 percent "
    "and bottom 18 percent as calm background, because the cover is cropped to 2.6:1. "
)

ITEMS = [
    ("profile-1-face", "mimi", PROFILE + MIMI + " A close-up head-and-shoulders portrait filling the frame: huge shiny eyes looking straight at the viewer, "
     "a happy open mouth with the pink tongue out. Plain warm turmeric-yellow background with a soft glow behind her head."),
    ("profile-2-basket", "mimi", PROFILE + MIMI + " She sits proudly in front of a traditional woven bamboo sticky-rice basket with a little steam rising from it, "
     "head tilted, sweet hopeful eyes. Soft cream background with faint green rice-leaf shapes, dog and basket centred."),
    ("profile-3-wet", "mimi", PROFILE + MIMI + " Soaked by the flood: wet clumpy fur plastered down, a pink bath towel draped over her head, "
     "big sulky betrayed eyes, water droplets flying, a small puddle under her. Plain soft sky-blue background. Funny and cute."),
    ("cover-1-lineup", "family", COVER + "The whole family stands in a row facing the camera, smiling, on a plain warm turmeric-yellow studio background with soft floor shadows, "
     "like a funny movie poster. Left to right exactly as in image 1: the mother with the ladle in her bun, the brother in the navy blazer and elephant-print shorts, "
     "Mimi sitting at the centre in front, the sister in the Thai office outfit. " + MIMI),
    ("cover-2-table", "family", COVER + "A warm Thai home dinner scene, cosy evening light: the four of them around a table with sticky rice, grilled chicken and papaya salad and steam rising; "
     "the mother serves with her ladle, the brother holds a mug and stares at a laptop, the sister in the office outfit with the lanyard slumps tired, "
     "and Mimi sits on her own chair at the table with a little bowl, eyes on the food. Cream marble floor tiles, a white two-door fridge and open kitchen shelves behind. "
     "No house number, no framed pictures. Everyone exactly as in image 1. " + MIMI),
    ("cover-3-doorway", "family", COVER + "Mimi seen from behind in the open front doorway of a Thai townhouse, looking out at a rain-soaked street with brown puddles and a steel gate, "
     "turning her head back to the camera with big pleading eyes; behind her inside the room the mother, the brother (phone to his ear) and the sister watch with comic worried faces. "
     "Grey-blue rainy light outside, warm yellow light inside. No house number, no framed pictures. Everyone exactly as in image 1. " + MIMI),
]

ATTACH = {"mimi": WIN_REFS + r"\mimi_cartoon_ref.jpg", "family": WIN_REFS + r"\family_lineup_ref.jpg"}


def build():
    return [{"name": n, "prompt": " ".join([STYLE, body]).replace("\n", " "), "attach": ATTACH[a]} for n, a, body in ITEMS]


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("round5.json")
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(build()), "prompts")

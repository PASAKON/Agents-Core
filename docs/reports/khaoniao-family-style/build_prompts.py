#!/usr/bin/env python3
"""Build round1.json for tools/chatgpt_images.py — one ONE-LINE prompt per character sheet.

Design lives in STYLE-CARD.md; change it there first, then here. The composer drops newlines,
so every prompt is joined with spaces (CMO_Procedure_ChatGPTImage_LakornCover, logo template note).
    python build_prompts.py [outfile]      # default: round1.json beside this file
"""
import json
import pathlib
import sys

VERSION = "v3"  # v1 Mimi photoreal -> v2 pushed cartoon -> v3 CEO: "การ์ตูนสไตล์ไทยๆ"

STYLE = (
    "Stylised Thai cartoon character in a Thai family-comedy cartoon style, clearly a CARTOON and not a photograph: "
    "in the spirit of Thai gag comics and Thai 3D animated films, with the funny deformed proportions of a Japanese family-comedy cartoon. "
    "Chunky rounded shapes, an oversized head about 40 percent of body height, a short stubby body and limbs, small hands, "
    "very large friendly expressive eyes, exaggerated funny faces, bold simple shapes. "
    "Thai facial features: dark brown eyes, warm tan skin, a soft low nose bridge. Warm tropical colours. "
    "Rendered in 3D with a high-end finish: warm key light with a cool rim light, soft global illumination, "
    "subtle subsurface scattering, soft contact shadow under the feet. Not photorealistic, not anime, not flat 2D."
)

STYLE_2D = (
    "Thai gag-comic cartoon character in the style of Thai comic magazines: bold black ink outlines, flat bright colours with simple cel shading, "
    "exaggerated funny faces, an oversized head about 40 percent of body height, a short stubby body and limbs, small hands, big friendly expressive eyes. "
    "Thai facial features: dark brown eyes, warm tan skin, a soft low nose bridge. Warm tropical colours. "
    "A flat 2D illustration, not 3D, not a photograph, not anime."
)

LAYOUT = (
    "CHARACTER DESIGN SHEET on a plain light-grey studio background, landscape 3:2: on the left one large full-body front view "
    "standing relaxed; in the middle one full-body three-quarter view; on the right a column of four head close-ups with four "
    "different expressions ({expr}). The same character in every view, identical face, hair, outfit and proportions. "
    "No text, no letters, no numbers, no labels, no watermark, no frame."
)

CHARACTERS = {
    "mimi": dict(
        expr="1 calm sitting neutral, 2 head tilted curious, 3 happy open mouth with tongue, 4 guilty eyes 'I did nothing'",
        attach=r"C:\mooniex\khaoniao\refs\mimi_crop.jpg",
        body=(
            "Image 1 is a photo of a real small dog named Mimi. Redesign her as a cartoon character from a 3D animated film, not a photo of a real dog, "
            "while keeping her exactly recognisable: a small long-haired fluffy dog, wavy black coat (never brown, never solid black), silver-white eyebrow "
            "tufts above the eyes, a silver-grey beard with tan under the chin, a white patch on the chest and a white bib, "
            "cream-tan on two of the paws, long drop ears with silver tips, dark brown eyes, a little pink tongue. Older, wiser face. "
            "Turn her into a cartoon: a huge head, huge eyes and huge ears, a round chubby stubby body, simplified fur in bold clumps, but keep every marking in the same place. "
            "She is a dog on four legs, no clothes, no collar. The silhouette is a fluffy mop with two huge ears."
        ),
    ),
    "mother": dict(
        expr="1 dreamy blank 'huh?' face with mouth slightly open, 2 proud delighted smile holding the ladle, 3 tender worry, 4 eyes closed tasting something delicious",
        body=(
            "A Thai mother in her mid fifties: the shortest person in the family, a soft dumpling-and-pear shaped body widest at the hips, "
            "round soft face, big sleepy half-closed warm brown eyes, tiny dot nose, rosy cheeks, slow gentle open-mouth expression. "
            "Short black hair with a few grey strands in a messy bun with a wooden cooking ladle pushed through it. "
            "Faded oversized pale-yellow T-shirt, a floral-print Thai sarong wrap skirt (pha thung), a checkered Thai cotton cloth (pha khao ma) over one shoulder, "
            "a half apron with small red chili stains, a small gold Buddha-amulet necklace, pink rubber slippers. "
            "A faint curl of food steam drifts around her. Sweet, dreamy, a little clueless, obviously a genius cook."
        ),
    ),
    "brother": dict(
        expr="1 smug confident smirk with one eyebrow raised, 2 fake-serious on a phone call, 3 sudden panic, 4 triumphant grin",
        body=(
            "A Thai businessman in his early thirties, played as an over-the-top tycoon, drawn with a big head and a short stubby body: "
            "broad square shoulders, a big square jaw, glossy side-parted black hair with a bright highlight, thin rectangular black glasses, "
            "thin sharp eyebrows with one always raised, warm tan skin. Immaculate navy double-breasted blazer with gold buttons, crisp white shirt, "
            "silk tie with a gold tie pin, gold wristwatch, a beaded lucky-stone bracelet, a wireless earbud, a coffee mug in one hand and a phone in the other. "
            "Below the blazer he wears loose blue Thai elephant-print shorts and blue-and-white rubber flip-flops (he works from home), shown as a funny contrast. "
            "Smug, self-important, secretly hard-working."
        ),
    ),
    "sister": dict(
        expr="1 deadpan cold stare, 2 fierce shouting with sharp eyebrows, 3 melted soft smile, 4 sharp smirk",
        body=(
            "A tough young Thai woman in her late twenties with an angular design, drawn with a big head and a short stubby body: sharp heart-shaped face with a pointed chin, "
            "a high tight ponytail of jet-black hair with one burgundy streak that stands up like a flame, winged eyeliner, bold deep-red lips, "
            "thin arched eyebrows, gold hoop earrings, warm tan skin. Black fitted blazer over a white blouse with the top button open, slim black trousers, white sneakers, "
            "a lanyard with a completely blank white badge around her neck and a car key with a cute small plush charm hanging from one finger. "
            "Strong, blunt, intimidating, stylish. Every shape is a sharp diagonal, nothing round."
        ),
    ),
}


def build():
    items = []
    for name, c in CHARACTERS.items():
        prompt = " ".join([STYLE, LAYOUT.format(expr=c["expr"]), c["body"]]).replace("\n", " ")
        item = {"name": f"sheet-{name}-{VERSION}", "prompt": prompt}
        if "attach" in c:
            item["attach"] = c["attach"]
        items.append(item)
    m = CHARACTERS["mother"]  # the same mother as a 2D Thai gag comic, for the CEO to compare
    items.append({"name": f"sheet-mother-2d-{VERSION}",
                  "prompt": " ".join([STYLE_2D, LAYOUT.format(expr=m["expr"]), m["body"]]).replace("\n", " ")})
    return items


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).with_name("round1.json")
    out.write_text(json.dumps(build(), ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, len(build()), "prompts")

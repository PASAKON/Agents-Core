#!/usr/bin/env python3
"""Build the round-1 reference-image prompts for THE LAST BELL.

Character words come from CAST.md (copied here as data, one place); the look comes
from BIBLE.md §2. Output: docs/ops/briefs/last-bell-refs-round1.json, the list
format tools/chatgpt_images.py --json reads ([{"name", "prompt"}]).

    python3 docs/prompts/last-bell/build_refs.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/ops/briefs/last-bell-refs-round1.json"

LOOK = ("Colour grade: a surreal yellow-green world. Acid yellow-green sky, chartreuse highlights, "
        "deep olive shadows, warm gold lamp light, soft haze. Photorealistic, epic fantasy film still, "
        "anamorphic lens, rich detail.")

SHEET_HEAD = ("Character reference sheet for a live-action epic fantasy film, landscape 3:2.\n"
              "Background: plain white studio background, even soft studio lighting, no shadows, no props, "
              "no scene. The same character in every panel; only the expression and the pose change.")

SHEET_BODY = ("RIGHT SIDE: one full-body panel, larger than the close-ups. The character stands straight in a "
              "neutral pose, arms at the sides, whole wardrobe visible from head to toe, same plain white background.")

SHEET_TAIL = ("Photorealistic, natural skin texture, an ordinary real-looking person, not a celebrity. "
              "No text except the panel labels. No watermark.")

CHARACTERS = {
    "kaew": {
        "who": ("KAEW, a Thai girl about 12 years old, small and wiry. Warm deep-brown sun-tanned skin. Round face, "
                "high cheekbones, large dark eyes, thick straight brows, a tiny pale scar through the left brow. "
                "Short straight black bob with one small topknot tied with crimson thread. Loose short-sleeved "
                "crimson cotton tunic, patched at the left elbow. Knee-length indigo chong kraben (Thai wrapped "
                "trousers). Barefoot. A thin brass anklet with one tiny bell on the right ankle."),
        "emotions": ["01 DETERMINED: jaw set, eyes narrowed, chin up",
                     "02 LAUGHING: wide open laugh, eyes creased",
                     "03 TERRIFIED: eyes wide, mouth open, soaked hair stuck to the forehead",
                     "04 GUILT: horror at what she has done, hand near her mouth",
                     "05 SINGING SOFTLY: eyes half closed, a calm lullaby"],
    },
    "yai": {
        "who": ("YAI BUA, a Thai grandmother about 78 years old. Very thin, slightly hunched. Dark weathered skin, "
                "deep wrinkles, age spots. Silver-white hair in a low tight bun with a small white jasmine garland "
                "pinned around it. Gentle hooded eyes. Teeth and lips stained dark red from chewing betel. A faded "
                "indigo mor hom cotton shirt with wooden buttons, sleeves rolled. A dark brown checked sarong to the "
                "ankles. Worn rubber sandals. A string of small brass bells on the left wrist."),
        "emotions": ["01 WARM SMILE: betel-stained smile, kind eyes",
                     "02 SLY: one eyebrow up, teasing",
                     "03 HUMMING: eyes closed, lips barely open, singing a lullaby",
                     "04 WEAK AND PROUD: tired, lying back, but smiling with pride"],
    },
    "mek": {
        "who": ("MEK, a Thai boy about 14 years old. Lanky with long arms. Dark tanned skin. Messy shoulder-length "
                "black hair with sun-bleached reddish tips. A gap-toothed grin. A turquoise-and-white checked pha "
                "khao ma cloth tied as a headband. A sleeveless washed-out turquoise cotton vest. Rolled-up black "
                "fisherman trousers. Barefoot. Rope-burn scars on both palms."),
        "emotions": ["01 CHEEKY GRIN: gap-toothed, teasing",
                     "02 SHOUTING: calling out across water, hand at mouth",
                     "03 SCARED: eyes wide, breathing hard",
                     "04 STEADY: serious, holding on, determined"],
    },
    "governor": {
        "who": ("THE GOVERNOR, a fictional Thai provincial governor, a heavyset man in his fifties, not resembling "
                "any real person. Round smooth face, a thin moustache, slicked-back black hair, small cold eyes. A "
                "high-collared white silk jacket with a row of gold buttons. Mustard-gold brocade chong kraben. A "
                "heavy gold chain with a medallion, many heavy gold rings. Black leather slip-on shoes. No crown, no "
                "royal regalia."),
        "emotions": ["01 SMUG: half smile, chin raised",
                     "02 GREEDY: eyes on something valuable, lips pursed",
                     "03 SHOUTING ORDERS: mouth wide, finger pointing",
                     "04 COWARDLY PANIC: sweating, eyes darting"],
    },
}

NAGA = ("Creature reference sheet for a live-action epic fantasy film, landscape 3:2.\n"
        "Background: plain white studio background, even soft studio lighting, no props, no scene. The same "
        "creature in every panel.\n\n"
        "CREATURE: PHAYA NAK, a colossal single-headed serpent in the form of a Thai temple naga brought to life. "
        "Jade-green scales, each rimmed with thin gold. A pale gold segmented underbelly. A tall flame-shaped "
        "gold-and-jade crest on the head that runs down the spine as a fin. Large amber eyes with slit pupils. Long "
        "curling whiskers like a carp. Short curved fangs. Old weathered bronze bands sunk into the scales of the "
        "neck, like chains worn for a hundred years. One head only. No wings, no legs.\n\n"
        "LEFT SIDE: four head close-ups in a labelled grid, each numbered and titled top-left in bold sans-serif:\n"
        "01 ASLEEP: eyes closed, head resting\n"
        "02 RAGING: jaws open in a roar, crest flared\n"
        "03 LISTENING: head lowered, eyes soft and curious\n"
        "04 SORROWFUL: eyes half closed, ancient and sad\n\n"
        "RIGHT SIDE: one large full-body panel. The whole serpent coiled in a loose S so its full length, the crest, "
        "the underbelly and the tail tip are visible, with a small human silhouette beside it for scale.\n\n"
        "Photorealistic creature design, detailed scales. No text except the panel labels. No watermark.")

PLACES = {
    "loc_city": ("Wide establishing shot, landscape 3:2, no people anywhere. SUWANNAWARI, a vast fictional floating "
                 "city on a lagoon at dawn: hundreds of teak stilt houses with steep gabled roofs and crossed kalae "
                 "finials, connected by long wooden footbridges and canals with empty long-tail boats. Small brass "
                 "bells and wind chimes hang from every eave. In the centre, on its own island, a giant white-and-gold "
                 "chedi with a naga stair rail spiralling to the top, where a huge bronze bell hangs in a pavilion."),
    "loc_bell_pavilion": ("Wide shot, landscape 3:2, no people anywhere. The top of the giant chedi: an open pavilion "
                          "with a gilded tiered roof and four carved pillars, and the GREAT BELL hanging in the centre, "
                          "bronze, as tall as three people, a frayed broken rope dangling from it. Beyond the railing, "
                          "the floating city far below and the open sea to the horizon."),
    "loc_yai_house": ("Interior, landscape 3:2, no people anywhere. A small teak stilt house of a poor old woman: "
                      "worn floor planks, a woven sleeping mat, a brass betel box, a clay water jar, dried herbs, rows of "
                      "small brass bells on strings hung by the open window, the canal visible outside. Warm oil lamp. "
                      "Simple, patched and lived-in, not luxurious."),
    "loc_canal": ("Landscape 3:2, no people anywhere. A wide canal between stilt houses, a long rickety wooden "
                  "footbridge on posts crossing it toward the chedi island, an empty long-tail boat tied at a ladder, "
                  "jasmine garlands and small bells hanging from the houses."),
}

PROPS = {
    "prop_great_bell": ("Prop reference sheet, landscape 3:2, plain white studio background, even light, no people. "
                        "THE GREAT BELL in three views (front, side, back): a Thai temple bell of dark weathered bronze "
                        "with a gold patina, as tall as three people, a lotus-bud crown on top. Engraved all around it: "
                        "a long naga serpent bound in chains. Label each view top-left in bold sans-serif: FRONT, SIDE, "
                        "BACK. No other text, no watermark."),
    "prop_mallet": ("Prop reference sheet, landscape 3:2, plain white studio background, even light, no people. "
                    "THE MALLET in three views (front, side, top): a small hand bell mallet, a dark teak handle as long "
                    "as a forearm, the head wrapped tightly in crimson thread, a little brass bell tied to the end of "
                    "the handle. Label each view top-left in bold sans-serif: FRONT, SIDE, TOP. No other text, no watermark."),
}

KEYART = {
    "key_bell_naga": ("Epic key art, landscape 3:2. A small Thai girl (KAEW: crimson tunic, indigo wrapped trousers, "
                      "short black bob with a crimson-thread topknot, barefoot) stands at the edge of a bell pavilion on "
                      "top of a giant chedi in a storm, holding a crimson-wrapped mallet beside a huge bronze bell. Rising "
                      "out of the sea behind her, a colossal jade-and-gold Thai naga serpent, one head, its amber eye level "
                      "with her, larger than the chedi. The floating city of stilt houses far below."),
    "key_storm_city": ("Epic key art, landscape 3:2, no people visible. A floating city of Thai teak stilt houses and "
                       "a giant white-and-gold chedi under a black-green storm sky with yellow lightning. On the horizon, "
                       "a wave as tall as a mountain. Wind tearing bells and jasmine garlands from the eaves."),
}


def sheet(c: dict) -> str:
    grid = "\n".join(c["emotions"])
    return (f"{SHEET_HEAD}\n\nCHARACTER (identical in every panel): {c['who']}\n\n"
            f"LEFT SIDE: {len(c['emotions'])} close-ups in a labelled grid, each numbered and titled top-left in bold "
            f"sans-serif:\n{grid}\n\n{SHEET_BODY}\n\n{SHEET_TAIL}")


def main() -> None:
    items = []
    for key, c in CHARACTERS.items():
        for v in ("a", "b"):  # a and b run in separate new chats: two castings to choose from
            items.append({"name": f"ch_{key}_{v}", "prompt": sheet(c)})
    for v in ("a", "b"):
        items.append({"name": f"ch_naga_{v}", "prompt": NAGA})
    for name, text in PLACES.items():
        items.append({"name": name, "prompt": f"{text}\n\n{LOOK}\n\nNo text, no watermark."})
    for name, text in PROPS.items():
        items.append({"name": name, "prompt": text})
    for name, text in KEYART.items():
        items.append({"name": name, "prompt": f"{text}\n\n{LOOK}\n\nNo text, no watermark."})
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(items)} prompts -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

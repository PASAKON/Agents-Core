# -*- coding: utf-8 -*-
"""«น้ำไม่เลือกบ้าน» (film 3) ACT1 = EP1 + EP2, shots 1-23 (0:00-3:04). Source of truth
for tools/build_shotsheet.py.

CEO 2026-09-26: "เยี่ยมเอาแบบนี้เลย ลุยได้" · "อนุมัติ 1,300 เครดิต ลุยต่อได้".

The dialogue and its per-line direction are NOT typed here: they are read from
docs/scripts/ep3-sabiang-SCRIPT-v1.md at import time, so the script the CEO reads and the
prompts the runner fires can never disagree. This file adds only what the script does not
carry: who is in each shot (in which STATE), where, the time of day, the English action
with its emotion, props and negatives. States: docs/scripts/ep3-CAST-STATES.md.

Plates come from docs/ops/briefs/ep3-plates-round1.json (ChatGPT on winbox) and are
uploaded to the Flow project under exactly these names. Each named character is attached
as FACE plate (identity) + STATE plate labelled as the wardrobe reference; the clerk and
the neighbour have one full-body plate each and no wardrobe chip.

Rules carried in from films 1-2 (see the lessons table at the top of the script):
- the speaker's action happens WHILE the line is said, never before it ("then" is banned);
- the first speaker's action is written first, because Flow speaks in ACTION order;
- every person in frame has their own physical action and a loud, physical emotion;
- no children, no uniforms, no night, at most 3 people, no money in frame, no real brand.
The narrator (S73-S75) is added in the edit. S74 and S75 are not shot in Flow at all: they
are slow push-ins on the porch__kitchen and soi__after plates, made in the edit for $0.
"""
import re
from pathlib import Path

STYLE = ("Contemporary Thai realist drama, vertical 9:16, shot on 35mm, soft natural "
         "daylight in a flooded Bangkok neighbourhood, strong expressive acting, faces "
         "clearly readable.")

_KIJ = ("a stocky, broad-shouldered Thai-Chinese man of fifty-five with a heavy build, a "
        "square jaw, thick black eyebrows, short buzz-cut black hair greying at the sides and "
        "a small mole on his left cheek")
_MINT = ("a slim Thai woman of twenty-two, clearly an adult university student, with a fresh "
         "oval face, bright dark eyes and straight black hair in a high ponytail, no make-up")

# key: (face handle, full appearance block written from the plate, short reference)
CHAR = {
 "kij1": ("@kij__face",
   _KIJ + ", clean-shaven, wearing a royal-blue short-sleeved button-up shirt with a slight "
   "sheen tucked into grey slacks rolled up to mid-shin, a brown leather belt, a thick gold "
   "wristwatch and black leather slip-on sandals",
   "The stocky man in the royal-blue shirt"),
 "kij2": ("@kij__face",
   _KIJ + ", with grey stubble, messy flattened hair and puffy tired eyes, wearing a "
   "sweat-stained pale-blue sleeveless cotton vest and dark-navy knee-length shorts soaked "
   "dark, barefoot, no wristwatch",
   "The stocky man in the pale-blue vest"),
 "kij5": ("@kij__face",
   _KIJ + ", clean-shaven with his hair neatly combed, wearing a plain royal-blue cotton "
   "T-shirt, khaki knee-length shorts and black rubber sandals, no watch and no jewellery",
   "The stocky man in the blue T-shirt"),
 "noi": ("@noi__face",
   "a Thai woman of forty-eight of medium build with a warm round face, lively dark eyes "
   "with laugh lines, black hair in a low bun held back by a green cloth headband and small "
   "gold stud earrings, wearing a faded green short-sleeved cotton blouse, a green-and-white "
   "checked cloth apron, black knee-length trousers and black rubber sandals",
   "The woman in the checked apron"),
 "yen": ("@yen__face",
   "a very small, frail, slightly stooped Thai woman of seventy-eight with deeply wrinkled "
   "sun-tanned skin, thin white hair in a tiny bun and gentle watery dark eyes, wearing a "
   "faded lilac long-sleeved blouse buttoned to the neck, a dark-purple patterned Thai sarong "
   "and old rubber flip-flops",
   "The old woman in the lilac blouse"),
 "mint_h": ("@mint__face",
   _MINT + ", wearing an oversized plain mustard-yellow T-shirt, light-blue denim shorts and "
   "black rubber flip-flops",
   "The young woman in the mustard-yellow T-shirt"),
 "mint_f": ("@mint__face",
   _MINT + ", a few wet strands loose from her ponytail, wearing a mustard-yellow hooded rain "
   "jacket open over a plain grey T-shirt and black leggings rolled up to the knee, barefoot",
   "The young woman in the yellow rain jacket"),
 "clerk": ("@clerk__work",
   "a slim Thai man of about twenty-four with short neat black hair and a friendly ordinary "
   "face, wearing a plain dark-teal polo shirt with no logo and no name tag, black work "
   "trousers rolled up to the knee and black rubber rain boots",
   "The young man in the teal polo shirt"),
 "nb": ("@neighbour__work",
   "a wiry, sun-tanned Thai man of about forty-five with short black hair flecked with grey "
   "and a lined friendly face, wearing a faded orange T-shirt and dark knee-length shorts, "
   "barefoot",
   "The man in the orange T-shirt"),
}

# The STATE plate of each key, attached as the wardrobe reference next to the face.
# clerk and nb have a single full-body plate (their CHAR handle) and no wardrobe chip.
WARDROBE = {
 "kij1": "@kij__day1", "kij2": "@kij__day2", "kij5": "@kij__day5",
 "noi": "@noi__kitchen", "yen": "@yen__home",
 "mint_h": "@mint__home", "mint_f": "@mint__flood",
}

# Timbre, pitch and age ONLY (CTO_Story_ThaiMoralDrama §Emotion rule 3): any mood in here
# is pasted into every line and flattens the whole film.
_V = "(prompt only, no bound voice)"
_VK = (_V, "the nasal baritone voice of a Thai-Chinese man of fifty-five")
_VM = (_V, "the clear, bright voice of a Thai woman of twenty-two")
VOICE = {
 "kij1": _VK, "kij2": _VK, "kij5": _VK,
 "noi": (_V, "the warm, mid-pitched, slightly husky voice of a Thai woman of forty-eight"),
 "yen": (_V, "the thin, high voice of a Thai woman of seventy-eight"),
 "mint_h": _VM, "mint_f": _VM,
 "clerk": (_V, "the light tenor voice of a Thai man in his twenties"),
 "nb": (_V, "the plain, mid-pitched voice of a Thai man of forty-five"),
}

_LANE = ("a narrow residential lane in an old Bangkok neighbourhood: on the left an old modest "
         "wooden row-house with a raised wooden porch about one metre above the lane and three "
         "wooden steps going down; on the right a new white two-storey concrete townhouse with "
         "a glass-and-aluminium front door at lane level and a small window and balcony "
         "upstairs; at the far end a small old wooden house on short stilts patched with rusty "
         "zinc sheets; tangled electricity cables overhead and a concrete lamp post with a "
         "dirty water line on it")
_PORCH = ("the raised wooden porch of an old wooden row-house in a Bangkok lane, set up as a "
          "shared community kitchen: a long wooden table with a two-burner gas stove on a hose "
          "to a plain unmarked grey gas cylinder, a very large dented aluminium cooking pot, "
          "stacks of plastic and enamel bowls, a ladle, a wooden bench, a high wooden shelf on "
          "the wall holding plain white rice sacks and plain unlabelled cans, potted plants "
          "along the porch edge and wooden steps going down to the lane")
_KIJ_ROOM = ("the ground floor of a new two-storey modern townhouse: glossy white marble-look "
             "floor tiles, white walls, a tall stainless-steel double-door fridge, a microwave "
             "on a kitchen counter, a white staircase with a metal handrail at the back and a "
             "wide glass-and-aluminium front door onto the lane")

LOC = {
 "mart": ("@mart__flood",
   "the inside of a small generic neighbourhood convenience store in Bangkok with no brand, "
   "no logo and no store name: ankle-deep murky brown floodwater over the white floor tiles, "
   "rows of white metal shelves almost completely empty, an empty glass-door drinks fridge, a "
   "small checkout counter beside the glass front door, a flooded street outside in grey "
   "daylight, bright white ceiling lights"),
 "soi1": ("@soi__w1", _LANE + ", the whole lane under ankle-deep murky brown floodwater, an "
   "old wooden rowboat resting on the ground under the small house at the far end"),
 "soi3": ("@soi__w3", _LANE + ", the whole lane now under waist-deep murky brown floodwater "
   "with floating debris, the porch standing just above the water, the old wooden rowboat "
   "floating, tied by a rope to the porch steps"),
 "porch1": ("@porch__kitchen", _PORCH + ", the steps disappearing into ankle-deep murky "
   "brown floodwater"),
 "porch3": ("@porch__kitchen", _PORCH + ", the porch still dry but the lane below now under "
   "waist-deep murky brown floodwater that covers the steps, the old wooden rowboat tied at "
   "the porch edge"),
 "porch5": ("@porch__kitchen", _PORCH + ", the water in the lane below gone down to "
   "ankle-deep and clearing, a brown mud line on the walls at waist height"),
 "kij0": ("@kij__dry", _KIJ_ROOM + ", completely dry, with a big pile of plain brown cardboard "
   "cartons and shrink-wrapped packs of water bottles stacked on the floor in the middle of "
   "the room, the lane outside the glass door under ankle-deep water"),
 "kij2": ("@kij__flooded", _KIJ_ROOM + ", now flooded knee-deep with murky brown water, the "
   "cartons soaked, split open and floating, water packs floating, the fridge dark with its "
   "door ajar, the lowest stairs under water, every light off, grey daylight through the "
   "front door"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere "
           "in the frame.",
 # CEO 2026-09-26: the store is fictional; the real chain is never shown or named.
 "nologo": "Every package, carton, bottle, sachet and shelf is plain and unprinted: no brand "
           "names, no logos, no store name, no price tags and no readable text anywhere.",
 # "ขวดละร้อย" is spoken in S19, S21 and S61. The price is only ever said, never shown.
 "nocash": "Nobody holds, counts or hands over banknotes or coins; only water packs, food "
           "and bowls change hands.",
 # Taachang S25: a man shouting at someone and reaching for them vanished. Distance is
 # stated as what IS, not only what is not.
 "notouch": "Nobody touches anyone: they stay a full arm's length apart the whole time.",
}

PROP_FOR_NOT = {}

PROPS_BY_SHOT = {
    1: ["@cart__full", "@water_pack"], 2: ["@cart__full"], 4: ["@porridge_pack"],
    5: ["@porridge_pack"], 6: ["@cart__full"], 8: ["@cart__full"], 13: ["@cart__full"],
    14: ["@water_pack"], 18: ["@rowboat"], 19: ["@water_pack"],
}

T1 = "the first morning of the flood, grey overcast daylight"
T2 = "the first day of the flood, late morning, overcast daylight"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (8, "Medium wide inside the flooded store, both faces three-quarters to camera",
     ["clerk", "kij1"], "mart", T1,
     "the young man in the teal polo shirt, anxious and pleading, scratches his head and leans "
     "toward the stocky man while he speaks; at the same moment the stocky man, greedy and "
     "gleeful, eyes shining, laughs and keeps sweeping shrink-wrapped water packs off the shelf "
     "into an overflowing shopping trolley with both arms, answering without stopping. One "
     "continuous shot with no cuts", ["nologo", "nocash", "nosubs"]),
 2: (8, "Close-up on the overflowing trolley, the stocky man's grinning face above it",
     ["kij1", "clerk"], "mart", T1,
     "the stocky man, proud and grinning wide, tosses plain white milk cartons and bagged "
     "loaves of bread onto the overflowing trolley and pats the pile while he boasts; behind "
     "him the young man in the teal polo shirt shakes his head and sighs",
     ["nologo", "nosubs"]),
 3: (8, "Medium shot at the glass front door, the old woman three-quarters to camera",
     ["yen", "clerk"], "mart", T1,
     "the old woman, out of breath and wincing at her knee, wades slowly in through the glass "
     "door, one hand gripping the door frame and a small plastic pill box in the other, her "
     "knees trembling, and speaks hopefully while she walks; the young man in the teal polo "
     "shirt hurries toward her through the water", ["nosubs"]),
 4: (8, "Two-shot, the clerk and the old woman, the porridge shelf between them",
     ["clerk", "yen"], "mart", T1,
     "the young man in the teal polo shirt, relieved, points quickly at the bottom shelf where "
     "one small pale-orange porridge sachet is left while he speaks; at the same time the old "
     "woman, delighted, her eyes lighting up, smiles and reaches her hand toward the sachet "
     "as she answers", ["nologo", "nosubs"]),
 5: (8, "Close-up on the bottom shelf with both faces above it",
     ["kij1", "yen"], "mart", T1,
     "the stocky man, mocking, one eyebrow raised, snatches the last pale-orange porridge "
     "sachet off the shelf a moment before the old woman's hand reaches it and waggles it at "
     "her while he speaks; the old woman, shocked, freezes with her hand in mid-air, her lips "
     "trembling, her voice cracking as she answers", ["notouch", "nologo", "nosubs"]),
 # 10 s: two speakers and 34 syllables, over the 8 s ceiling (lint warn, dry build 09-26).
 6: (10, "Medium two-shot beside the overflowing trolley",
     ["clerk", "kij1"], "mart", T1,
     "the young man in the teal polo shirt, urgent, voice rising, grips the trolley's handle "
     "to hold it while he speaks; at the same moment the stocky man, dismissive, chin up, "
     "pulls the trolley back toward himself and answers", ["notouch", "nologo", "nocash", "nosubs"]),
 7: (8, "Medium close-up, the old woman alone by the empty shelves",
     ["yen"], "mart", T1,
     "the old woman, tearful, lips trembling, clutches her small pill box tight against her "
     "chest and stares at the empty shelves while she speaks to herself, her voice fading, "
     "ankle-deep brown water around her feet", ["nosubs"]),
 8: (8, "Medium shot from the flooded street, facing the stocky man as he pushes the trolley "
        "out through the glass door, the old woman small inside behind him",
     ["kij1", "yen"], "mart", T1,
     "the stocky man, laughing out loud and gloating, shoves the overflowing trolley out "
     "through the glass door into the flooded street, shouting back over his shoulder toward "
     "the store while he goes; inside, behind him, the old woman stands by the empty shelf "
     "with her head bowed, tears running down her face", ["nologo", "nocash", "nosubs"]),
 9: (8, "Wide establishing shot looking down the flooded lane",
     ["noi", "yen"], "soi1", T2,
     "the woman in the checked apron, warm and firm, smiling, leads the old woman by the arm "
     "through the ankle-deep water toward her raised porch while she speaks; the old woman, "
     "relieved, leans on her arm and thanks her", ["nosubs"]),
 10: (8, "Medium shot on the raised porch",
      ["noi", "yen"], "porch1", T2,
      "the woman in the checked apron, energetic, sweat on her brow, heaves the very large "
      "aluminium pot onto the table beside the gas stove while she calls out loudly down the "
      "lane; behind her the old woman sits on the wooden bench, watching", ["nosubs"]),
 11: (8, "Medium shot from the lane: the young woman on the upstairs balcony of the white "
         "townhouse, the woman in the checked apron below on her porch, both faces visible",
      ["mint_h", "noi"], "soi1", T2,
      "the young woman, bright and eager, leans over the balcony rail and calls down while "
      "she speaks; below, the woman in the checked apron, beaming, looks up and waves to her "
      "from the porch as she answers", ["nosubs"]),
 12: (8, "Medium two-shot at the porch table",
      ["noi", "yen"], "porch1", T2,
      "the woman in the checked apron, focused and serious, writes in a small notebook with a "
      "pen, reading aloud what she writes; beside her the old woman, touched and embarrassed, "
      "lowers her head and answers", ["nosubs"]),
 13: (8, "Medium wide from the porch down to the lane",
      ["noi", "kij1"], "soi1", T2,
      "the woman in the checked apron, polite and smiling, calls out from her raised porch "
      "while she speaks; at the same moment the stocky man, irritated, pushes his overflowing "
      "trolley through the ankle-deep water past the porch without stopping and answers "
      "without looking up", ["nologo", "nosubs"]),
 14: (8, "Medium shot inside the townhouse ground floor",
      ["mint_h", "kij1"], "kij0", T2,
      "the young woman, shocked, eyes wide, a plastic shopping bag in her hand, stares at the "
      "pile of cartons while she speaks; at the same time the stocky man, satisfied, drops one "
      "more water pack onto the pile on the marble floor, dusts off his hands and answers",
      ["nologo", "nosubs"]),
 15: (8, "Close-up at the kitchen counter, the fridge beside it",
      ["kij1", "mint_h"], "kij0", T2,
      "the stocky man, smug, grinning, pats the microwave on the counter and taps the fridge "
      "door while he boasts; beside him the young woman frowns, arms crossed",
      ["nologo", "nosubs"]),
 16: (8, "Medium shot at the open glass front door, the lane's ankle-deep water outside",
      ["noi", "kij1"], "kij0", T2,
      "the woman in the checked apron, earnest and worried, stands at the open front door and "
      "points at the cartons on the floor while she speaks; at the same time the stocky man, "
      "annoyed, waves her off with one hand and answers", ["nologo", "nosubs"]),
 17: (8, "Medium two-shot on the porch",
      ["yen", "noi"], "porch1", T2,
      "the old woman, shy, a small smile, holds out a bunch of fresh green morning glory with "
      "both hands while she speaks; the woman in the checked apron, moved, takes it with both "
      "hands and answers", ["nosubs"]),
 18: (8, "Medium shot at the small wooden house on stilts at the end of the lane",
      ["yen", "mint_h"], "soi1", T2,
      "the old woman, proud and nostalgic, eyes shining, points at the old wooden rowboat "
      "under her small house while she speaks; beside her the young woman, excited, bends "
      "down to look at the boat and thanks her", ["nosubs"]),
 19: (8, "Medium shot from the porch down to the lane",
      ["kij1", "noi"], "soi1", T2,
      "the stocky man, a sly grin, wades past the porch with a water pack on his shoulder and "
      "calls out like a street vendor while he walks; up on the porch the woman in the checked "
      "apron, outraged, face tight, grips a ladle and shouts back", ["nocash", "nologo", "nosubs"]),
 20: (8, "Close-up at the porch table",
      ["mint_h", "noi"], "porch1", T2,
      "the young woman, ashamed, face red, voice shaking, puts down a vegetable knife and turns "
      "to the woman in the checked apron while she speaks; the woman in the checked apron, "
      "soothing, lays a hand on her shoulder and answers", ["nosubs"]),
 21: (8, "Medium shot at the steaming pot",
      ["noi", "mint_h"], "porch1", T2,
      "the woman in the checked apron, firm and loud, ladles rice porridge into the first bowl "
      "and raises the ladle while she announces it to the whole lane; beside her the young "
      "woman sets out bowls in a row and nods", ["nocash", "nosubs"]),
 22: (8, "Medium close-up at the porch table",
      ["yen", "noi"], "porch1", T2,
      "the old woman, tearful and smiling, takes the first steaming bowl of rice porridge in "
      "both hands, her small pill box on the table beside it, while she speaks; the woman in "
      "the checked apron, warm, smiles down at her and answers", ["nosubs"]),
 23: (8, "Medium shot at the open front door, the young woman behind her father",
      ["noi", "kij1", "mint_h"], "kij0", T2,
      "the woman in the checked apron, a notebook ready in her hand, stands at the open front "
      "door and asks while she speaks; at the same time the stocky man, lying with a straight "
      "face, shrugs and answers; behind him the young woman, eyes wide, mouth open, stares at "
      "the pile of cartons on the floor", ["nologo", "nosubs"]),
}

_NAME = {"kij1": "เฮียกิจ", "kij2": "เฮียกิจ", "kij5": "เฮียกิจ", "noi": "ป้าน้อย", "yen": "ยาย",
         "mint_h": "มิ้นท์", "mint_f": "มิ้นท์", "clerk": "พนักงาน", "nb": "เพื่อนบ้าน"}
_NARRATOR = "ผู้บรรยาย"   # S73-S75: voice-over added in the edit, never generated


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from SCRIPT-v1."""
    text = (Path(__file__).with_name("ep3-sabiang-SCRIPT-v1.md")).read_text(encoding="utf-8")
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1)); out[cur] = []; continue
        # The narrator's lines carry no " — direction" suffix, so this pattern skips them;
        # _build also skips the name, in case a direction is ever added.
        m = re.match(r'\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
        if m and cur is not None:
            out[cur].append((m.group(1), m.group(3).strip(), m.group(2)))
    return out


def _build(meta):
    lines = _lines_from_script()
    shots = []
    for n in sorted(meta):
        secs, framing, chars, loc, tod, action, nots = meta[n]
        spoken = []
        for who, direction, line in lines[n]:
            if who == _NARRATOR:
                continue
            key = next((c for c in chars if _NAME[c] == who), None)
            if key is None:
                raise SystemExit(f"shot {n}: speaker {who} is not in the shot's cast {chars}")
            spoken.append((key, direction, line))
        shots.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return shots


SHOTS = _build(_META)

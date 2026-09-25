# -*- coding: utf-8 -*-
"""«ตาชั่งของเสี่ย» ACT1 = EP1 + EP2, shots 1-23 (0:00-3:04). Source of truth for
tools/build_shotsheet.py.

CEO 2026-09-25: "Go for ACT1" · "Approve Maximum 500 Credit".

The dialogue and its per-line direction are NOT typed here: they are read from
docs/scripts/taachang-SCRIPT-v2.md at import time, so the script the CEO reads and
the prompts the runner fires can never disagree. This file adds only what the
script does not carry: who is in each shot (in which STATE), where, the time of
day, the English action with its emotion, props and negatives.

Plates (ChatGPT, approved by the CEO 2026-09-25) are uploaded to the Flow project
«ตาชั่งของเสี่ย» under exactly these names. Each character is attached as FACE plate
(identity) + STATE plate labelled as the wardrobe reference. That is the pairing that
held a face in the banchi A/B (CTO_Flow_Omni1.1_Continuity rule 4).
"""
import re
from pathlib import Path

STYLE = ("Contemporary Thai realist drama, vertical 9:16, shot on 35mm, natural bright "
         "daylight, strong expressive acting, faces clearly readable.")

# key: (face handle, full appearance block written from the plate, short reference)
CHAR = {
 "yai_c": ("@yai__face",
   "a small, thin Thai woman of seventy with sun-darkened, deeply wrinkled skin, kind "
   "deep-set eyes and short cropped grey hair, wearing a wide-brimmed faded cloth sun hat, "
   "a faded mauve floral long-sleeved cotton blouse, a cream towel around her neck, white "
   "cotton work gloves, loose dusty black trousers and grey rubber flip-flops",
   "The old woman in the cloth sun hat"),
 "yai_h": ("@yai__face",
   "a small, thin Thai woman of seventy with sun-darkened, deeply wrinkled skin, kind "
   "deep-set eyes and short cropped grey hair, bare-headed, in a faded pink floral "
   "short-sleeved blouse and a purple woven Thai sarong, barefoot",
   "The old woman in the purple sarong"),
 "sia_b": ("@sia__face",
   "a heavy-set Thai-Chinese man of fifty with a round fleshy face, small narrow eyes, black "
   "hair slicked straight back with grey at the temples and a thin moustache, wearing a loud "
   "red, black and gold dragon-print short-sleeved shirt open over a white vest, a thick gold "
   "chain, a gold wristwatch, khaki shorts and brown leather sandals",
   "The heavy man in the dragon-print shirt"),
 "kla_s": ("@kla__face",
   "a slim Thai boy of sixteen with messy short black hair and earnest dark eyes, in a plain "
   "white short-sleeved school shirt with no badge and no embroidery, long black trousers, a "
   "black belt and black school shoes",
   "The schoolboy in the white shirt"),
 "tor_h": ("@tor__face",
   "a small Thai boy of eleven with round cheeks and a straight black bowl-cut, in a faded "
   "navy T-shirt and khaki shorts, barefoot",
   "The little boy in the navy T-shirt"),
 "pa": ("@pa__face",
   "a stocky Thai woman of sixty with sharp eyes and greying hair tied back, wearing a wide "
   "woven straw hat, a blue-grey checked long-sleeved shirt with dark cloth arm sleeves, dark "
   "trousers, brown sandals and reading glasses hanging on a cord around her neck",
   "The woman in the straw hat"),
}

# The STATE plate of each key, attached as the wardrobe reference next to the face.
WARDROBE = {
 "yai_c": "@yai__collect", "yai_h": "@yai__home", "sia_b": "@sia__boss",
 "kla_s": "@kla__school", "tor_h": "@tor__home", "pa": "@pa__collect",
}

# Timbre, pitch and age ONLY (thai-moral-drama §Emotion rule 3): any mood in here is
# pasted into every line and flattens the whole film, which is what happened on banchi.
# No voice is bound in Flow: these are uploaded images, not Flow Characters (open
# question, tested in the 360p smoke before the act is shot).
_V = "(prompt only, no bound voice)"
VOICE = {
 "yai_c": (_V, "the thin, soft, slightly husky voice of a Thai woman of seventy"),
 "yai_h": (_V, "the thin, soft, slightly husky voice of a Thai woman of seventy"),
 "sia_b": (_V, "the thick, deep, gravelly voice of a heavy-set Thai-Chinese man of fifty"),
 "kla_s": (_V, "the clear, light voice of a sixteen-year-old Thai boy"),
 "tor_h": (_V, "the high, bright voice of an eleven-year-old Thai boy"),
 "pa":    (_V, "the loud, sharp, slightly nasal voice of a Thai woman of sixty"),
}

LOC = {
 "lan": ("@lan__busy",
   "a small open recycling yard in a Bangkok side street under a rusty corrugated-metal roof "
   "on steel posts: a low rusty blue steel platform scale with a round cream dial on a short "
   "post stands in the front centre, piles of white woven sacks stuffed with clear plastic "
   "bottles, stacks of flattened cardboard, a heap of crushed cans, a battered wooden desk "
   "with one drawer beside the scale and a red plastic chair, a corrugated metal fence at "
   "the back"),
 "baan": ("@baan__inside",
   "the inside of a small, poor corrugated-zinc shack: walls of rusty zinc sheets and rough "
   "planks, a bare cracked concrete floor with a thin striped woven plastic mat, no furniture "
   "at all, two stacked plastic crates (green on red) used as a shelf, clothes hanging on "
   "nails, a rolled-up thin mattress and pillow in the corner, plastic bags of belongings, a "
   "small electric fan on the floor, a bare bulb hanging on a wire, daylight coming through "
   "gaps in the zinc and a small window over a canal"),
 "soi": ("@soi__canal",
   "a narrow concrete footpath along a small canal in an old Bangkok neighbourhood: old "
   "wooden houses and sheds on one side, murky green water on the other, a long row of "
   "concrete electricity poles with tangled cables running along the path, banana plants"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere "
           "in the frame.",
 # The scale's dial must never be read: the grandmother cannot read it, and Flow garbles
 # digits. Said as what the dial IS, not only what it is not.
 # Smoke 2026-09-25 (S11, S13): without a scale chip, and even with one in S11, Veo drew a
 # small hanging/kitchen dial scale. Say what the scale IS, every time it is in frame.
 "dial": "The scale is the large, low, rusty blue steel platform scale standing on the ground "
         "from the reference, big enough for a sack to lie on, with a round cream dial on a "
         "short post at the back edge: never a small hanging scale, a kitchen scale or a "
         "tabletop scale. Its dial shows only plain black tick marks and one needle: no "
         "numbers, no letters, no text on it at all, and it is never in sharp close-up.",
 # Describes the actual @money plate: pastel fake notes, a corner numeral only.
 # 2026-09-25: S7 and S19 (grandmother + the 11-year-old + banknotes in frame) both vanished
 # with no card; S6 (same two, no money) rendered. n=2. Those shots now keep the money
 # inside a closed cloth pouch and say so.
 "nomoney": "No banknotes, coins or money of any kind are visible anywhere in the frame: the "
            "day's money stays inside the small closed cloth pouch the whole time.",
 "money": "Any banknotes in this shot are the fictional prop money from the reference: "
          "soft pastel paper notes with a plain abstract line pattern and a simple numeral "
          "in one corner, nothing else. No portrait or face of any kind, no crest, seal, "
          "emblem, flag or country name, no real currency of any country, no coins.",
}

PROP_FOR_NOT = {"money": "@money"}

PROPS_BY_SHOT = {
    1: ["@sack", "@yard_scale"], 2: ["@sack", "@yard_scale"],
    3: ["@wallet"], 4: ["@wallet"],
    6: ["@jar__third"],
    9: ["@cart", "@sack", "@yard_scale"], 10: ["@sack", "@yard_scale"], 11: ["@yard_scale"],
    12: ["@yard_scale"], 13: ["@yard_scale"], 14: ["@yard_scale"],
    15: ["@cart"], 16: ["@yard_scale"], 17: ["@yard_scale"], 18: ["@sack"],
    21: ["@jar__full"],
}

# n: (seconds, framing, [char keys, subject first], loc, time of day, action, [nots])
_META = {
 1: (8, "Close-up low on the scale platform, the camera tilting up to the heavy man's grin, both faces three-quarters to camera",
     ["sia_b", "yai_c", "kla_s"], "lan", "hot afternoon, bright daylight",
     "the heavy man's sandalled foot hooks the corner of the old woman's sack of bottles off "
     "the edge of the platform scale so it rests on the ground, and he keeps it there while he "
     "calls the weight with a sly, falsely jolly grin; the old woman stands opposite him "
     "smiling trustingly and nodding; behind them the schoolboy, carrying a sack, freezes and "
     "stares at the man's foot with a frown", ["dial", "nosubs"]),
 2: (8, "Medium two-shot, the schoolboy sharp in the background",
     ["yai_c", "sia_b", "kla_s"], "lan", "hot afternoon, bright daylight",
     "the old woman takes the money from the heavy man with a humble little bow while she "
     "speaks, grateful and trusting; he smirks down at her; behind them the schoolboy stops "
     "lifting, bites his lip and stares at his father's foot still pinning the sack corner",
     ["money", "dial", "nosubs"]),
 3: (8, "Medium close-up on the old woman holding out a wallet",
     ["yai_c", "sia_b"], "lan", "hot afternoon, bright daylight",
     "the old woman proudly holds out an old brown leather wallet to the heavy man with both "
     "hands, eyes shining, while she speaks", ["nosubs"]),
 4: (8, "Close-up on the heavy man counting, the old woman's face three-quarters to camera beside him",
     ["sia_b", "yai_c"], "lan", "hot afternoon, bright daylight",
     "the heavy man counts the notes in the wallet with narrowed, suspicious eyes while he "
     "talks, snorts, and with his other hand pushes a few pastel notes at the old woman "
     "without looking at her", ["money", "nosubs"]),
 5: (8, "Two-shot of father and son beside the scale",
     ["sia_b", "kla_s"], "lan", "hot afternoon, bright daylight",
     # 2026-09-25: first take vanished (no card, 9-min timeout). Softened "nasty glee" and
     # removed the un-chipped old woman in the background; she is simply gone from the yard.
     "the heavy man tosses the wallet into the desk drawer and turns to his son beside the "
     "scale, chuckling smugly; the schoolboy stares back at his father, shocked, eyes wide",
     ["nosubs"]),
 6: (8, "Medium close-up, grandmother and grandson sitting on the mat",
     ["tor_h", "yai_h"], "baan", "late afternoon, daylight through the gaps in the zinc",
     "the old woman drops one small pebble into a clear glass jar with a soft click while "
     "she answers the little boy, who sits beside her on the mat watching with his head "
     "tilted, curious; she smiles at him tenderly", ["nosubs"]),
 7: (8, "Close two-shot over the notes on the mat, both faces three-quarters to camera",
     ["yai_h", "tor_h"], "baan", "late afternoon, daylight through the gaps in the zinc",
     # 2026-09-25: first take vanished (no card). Hands stay on the notes: no touching the child.
     "the little boy speaks with a worried frown; the old woman sits with a small closed cloth "
     "pouch in her lap and, while she answers, looks up at him and forces a smile with "
     "glistening eyes",
     ["nomoney", "nosubs"]),
 8: (8, "Medium close-up, the heavy man jabbing a finger at his son",
     ["sia_b", "kla_s"], "lan", "late afternoon, bright daylight",
     "the heavy man, furious, face flushed red and the veins standing out on his neck, jabs "
     "a finger into his son's chest and shouts right into his face; the schoolboy goes pale "
     "and steps half a pace back", ["nosubs"]),
 9: (8, "Wide shot on the scale, the schoolboy standing in front of it, eyes down",
     ["yai_c", "sia_b", "kla_s"], "lan", "the next afternoon, bright daylight",
     "the schoolboy stands in front of the scale with his eyes on the ground while the old "
     "woman pushes her cart in with two sacks, beaming and out of breath; the heavy man barks "
     "at the boy without looking at him", ["dial", "nosubs"]),
 10: (8, "Medium three-shot at the scale",
     ["sia_b", "pa", "yai_c"], "lan", "the next afternoon, bright daylight",
     "the heavy man's foot nudges the sack corner off the platform again as he calls the "
     "weight fast, not meeting anyone's eyes; the woman in the straw hat frowns, points at "
     "the old woman's sack and compares it with her own, puzzled and loud", ["dial", "nosubs"]),
 11: (8, "Close-up on the old woman",
     ["yai_c", "sia_b"], "lan", "the next afternoon, bright daylight",
     "the old woman presses her gloved palms together and smiles too widely, nervous and "
     "pleading, her voice small, looking up at the heavy man", ["dial", "nosubs"]),
 12: (8, "Medium close-up on the heavy man, playing to the onlooker",
     ["sia_b", "yai_c", "pa"], "lan", "the next afternoon, bright daylight",
     "the heavy man points in the old woman's face and shouts with contempt, laughing loudly "
     "and turning to the woman in the straw hat as if for applause; the old woman's face "
     "falls and her eyes redden", ["nosubs", "dial"]),
 13: (8, "Medium shot, pastel notes fluttering down into the dirt",
     ["sia_b", "yai_c"], "lan", "the next afternoon, bright daylight",
     "the heavy man flicks a few pastel notes into the dusty ground with contempt while he "
     "speaks; the old woman, fighting back tears with her eyes brimming, slowly lowers "
     "herself to her knees to pick them up and answers politely, her voice trembling",
     ["money", "nosubs", "dial"]),
 14: (8, "Close two-shot, the schoolboy kneeling beside her, his body hiding his hand, both faces three-quarters to camera",
     ["kla_s", "yai_c"], "lan", "the next afternoon, bright daylight",
     "the schoolboy kneels beside the old woman to help gather the notes and, hidden by his "
     "own body, slips a folded pastel note of his own into her pile, speaking quickly and low and "
     "glancing guiltily toward his father; a tear rolls down her cheek as she smiles her "
     "thanks", ["money", "nosubs", "dial"]),
 15: (8, "Two-shot walking, the two women pushing their carts along the canal path",
     ["pa", "yai_c"], "soi", "the next afternoon, bright daylight",
     "the woman in the straw hat walks the old woman away along the canal path, leaning in "
     "to her and speaking low and urgently; the old woman answers, hoarse and defeated, her "
     "eyes wet", ["nosubs"]),
 16: (8, "Medium two-shot, son facing father across the scale",
     ["kla_s", "sia_b"], "lan", "the next afternoon, bright daylight",
     "the schoolboy slams a sack down and confronts his father, eyes red, voice shaking with "
     "anger; the heavy man answers icily without even looking up", ["dial", "nosubs"]),
 17: (8, "Close-up on the heavy man",
     ["sia_b"], "lan", "the next afternoon, bright daylight",
     "the heavy man dusts the scale with a rag, bitter and aggressive, speaking through "
     "gritted teeth", ["dial", "nosubs"]),
 18: (8, "Medium two-shot",
     ["kla_s", "sia_b"], "lan", "the next afternoon, bright daylight",
     "the schoolboy shouts back at his father in disgust; the heavy man explodes, roaring at "
     "full volume, and shoves an empty sack into the boy's chest", ["nosubs"]),
 19: (8, "Medium close-up on the mat, notes in her hands",
     ["yai_h", "tor_h"], "baan", "late afternoon, daylight through the gaps in the zinc",
     "the old woman peers into a small cloth pouch in her lap, puzzled, murmuring as she "
     "feels inside it without taking anything out; the little boy leans in wide-eyed",
     ["nomoney", "nosubs"]),
 20: (10, "Close two-shot, both faces three-quarters to camera",
     ["tor_h", "yai_h"], "baan", "late afternoon, daylight through the gaps in the zinc",
     "the little boy leans toward her, hopeful and wheedling; the old woman pulls the cloth "
     "pouch shut and shakes her head, firm but loving", ["nomoney", "nosubs"]),
 21: (8, "Close-up on the glass jar, the pebble dropping",
     ["yai_h", "tor_h"], "baan", "late afternoon, daylight through the gaps in the zinc",
     "the old woman drops a pebble into the nearly full glass jar with a tired, fond smile "
     "while she speaks; the little boy peers into the jar, amazed", ["nosubs"]),
 22: (8, "Medium shot, the old woman holding out a folded note",
     ["yai_c", "sia_b", "pa"], "lan", "the next morning, bright daylight",
     "the old woman holds out a folded pastel note to the heavy man with an earnest, simple "
     "smile; the woman in the straw hat stands beside her, shaking her head fondly",
     ["money", "nosubs"]),
 23: (8, "Medium close-up, the heavy man swinging round to his son",
     ["sia_b", "kla_s"], "lan", "the next morning, bright daylight",
     "the heavy man snatches the note, his suspicion turning to explosive rage, whips round "
     "and bellows hoarsely, pointing at his son; the schoolboy goes pale", ["money", "nosubs"]),
}

_NAME = {"yai_c": "ยาย", "yai_h": "ยาย", "sia_b": "เสี่ย", "kla_s": "กล้า", "tor_h": "ต่อ", "pa": "ป้า"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from SCRIPT-v2."""
    text = (Path(__file__).with_name("taachang-SCRIPT-v2.md")).read_text(encoding="utf-8")
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1)); out[cur] = []; continue
        m = re.match(r'\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
        if m and cur is not None:
            out[cur].append((m.group(1), m.group(3).strip(), m.group(2)))
    return out


def _build():
    lines = _lines_from_script()
    shots = []
    for n in sorted(_META):
        secs, framing, chars, loc, tod, action, nots = _META[n]
        spoken = []
        for who, direction, line in lines[n]:
            key = next((c for c in chars if _NAME[c] == who), None)
            if key is None:
                raise SystemExit(f"shot {n}: speaker {who} is not in the shot's cast {chars}")
            spoken.append((key, direction, line))
        shots.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return shots


SHOTS = _build()

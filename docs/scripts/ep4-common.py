# -*- coding: utf-8 -*-
"""Shared blocks for «ขายฝากนาแม่» (film 4) ACT1-3 data files: cast, wardrobe, voices,
languages, locations, negatives, and the script parser. Each ep4-ACTn.data.py imports this
file by path and adds only its own _META (who, where, when, the English action) and props.

CEO 2026-09-27: "ลุยได้เลย อณุมติ 1100 Credit ก่อน Charactor อยากให้ มีเอกลักษ์ เป็นของตัวเอง
กว่า เรื่อง 1 2 3 นะ / และตัวเอก หน้าตาดี แบบบ้านๆ ได้เลย".

The dialogue and its per-line direction are read from docs/scripts/ep4-khaifak-SCRIPT-v1.md
at import time, so the script the CEO reads and the prompts the runner fires cannot disagree.
Plates: docs/ops/briefs/ep4-plates-round1.json. States: docs/scripts/ep4-CAST-STATES.md.

Language (CEO passed voice-test clip 1 on 2026-09-27): every villager's line is written in
Isan spelling AND carries an explicit Isan-accent phrase through LANG. เจ๊หงส์ is the outsider
and speaks Central Thai with a Bangkok accent, on purpose.
"""
import re
from pathlib import Path

STYLE = ("Contemporary Thai realist drama, vertical 9:16, shot on 35mm, bright natural "
         "daylight in a rice-farming village in Northeast Thailand (Isan) at harvest time, "
         "strong expressive acting, faces clearly readable.")

_KP = ("a strong, wiry Thai woman of fifty-five from Northeast Thailand with high cheekbones, a "
       "firm square jaw, deep laugh lines, very dark sun-baked skin and fingertips permanently "
       "stained deep indigo-blue from dyeing cloth, a red-and-white checked pha khao ma cloth "
       "wrapped around her head like a turban, wearing a hand-dyed deep indigo long-sleeved "
       "cotton blouse with the sleeves pushed up, a long indigo mudmee ikat tube skirt and "
       "worn black rubber flip-flops")
_SA = ("a handsome Thai man of twenty-seven from Northeast Thailand with rustic village good "
       "looks, golden-brown sun-tanned skin, thick straight black eyebrows, warm dark eyes, "
       "deep dimples in both cheeks, a strong square jaw with light stubble, short slightly "
       "overgrown black hair, a lean build and a small silver Buddha amulet on a black cord")

# key: (face handle, full appearance block written from the plate, short reference)
CHAR = {
 "kp1": ("@kampun__face", _KP + ", a thin gold chain necklace at her throat",
         "The woman in the indigo blouse"),
 "kp2": ("@kampun__face", _KP + ", her neck bare with no necklace",
         "The woman in the indigo blouse"),
 "sa_c": ("@saen__face", _SA + ", wearing a plain white crew-neck T-shirt, faded blue jeans "
          "and plain white canvas sneakers", "The young man in the white T-shirt"),
 "sa_i": ("@saen__face", _SA + ", wearing a hand-dyed deep indigo long-sleeved cotton work "
          "shirt with the sleeves rolled up, dark cotton trousers rolled to mid-calf and a "
          "red-and-white checked pha khao ma cloth tied around his forehead, barefoot",
          "The young man in the indigo shirt"),
 "hong": ("@hong__face",
   "a plump, wealthy Thai woman of fifty-two with a round face under heavy powdered make-up, "
   "thin arched drawn-on eyebrows, glossy bright-red lipstick, jet-black hair lacquered into a "
   "tall shiny bun with a hot-pink silk flower clip and hot-pink sunglasses pushed up on top, "
   "three thick gold chain necklaces, a green jade bangle, a loose hot-pink silk blouse with "
   "large darker-pink peonies, cream wide-leg trousers and hot-pink heeled sandals, a carved "
   "sandalwood folding fan always in her right hand",
   "The woman in hot pink"),
 "bm": ("@boonma__face",
   "a lean Thai village headman of sixty with a sun-darkened lined face, short grey hair, a "
   "thin grey moustache and round thin wire-rimmed glasses, wearing a faded light-blue "
   "short-sleeved cotton shirt with no print and no badge, a red-and-white checked pha khao "
   "ma cloth tied around his waist, loose grey trousers, worn black rubber sandals and a "
   "woven bamboo sun hat",
   "The headman in the light-blue shirt"),
 "pa": ("@pa__face",
   "a sturdy, cheerful Thai farm woman of about fifty with a round sunburnt face, full cheeks "
   "and short black hair grey at the temples, a wide woven straw hat, wearing a leaf-green "
   "long-sleeved cotton blouse with a small white flower print, a dark-brown tube skirt to "
   "mid-calf, black cloth arm sleeves and rubber flip-flops",
   "The woman in the green blouse"),
 "ai": ("@ai__work",
   "a stocky, cheerful Thai man of about thirty with a round friendly face, a short buzz cut "
   "and sun-tanned skin, a red-and-white checked pha khao ma cloth tied around his forehead, "
   "wearing a faded mustard-yellow T-shirt, dark knee-length shorts and rubber flip-flops",
   "The man in the mustard-yellow T-shirt"),
}

# The STATE plate of each key, attached as the wardrobe reference next to the face.
# ai has a single full-body plate (his CHAR handle) and no wardrobe chip.
WARDROBE = {
 "kp1": "@kampun__chain", "kp2": "@kampun__nochain",
 "sa_c": "@saen__city", "sa_i": "@saen__indigo",
 "hong": "@hong__pink", "bm": "@boonma__day", "pa": "@pa__work",
}

# Timbre, pitch and age ONLY (CTO_Story_ThaiMoralDrama §Emotion rule 3).
_V = "(prompt only, no bound voice)"
_VKP = (_V, "the strong, slightly hoarse alto voice of a Thai woman of fifty-five")
_VSA = (_V, "the clear, warm baritone voice of a Thai man of twenty-seven")
VOICE = {
 "kp1": _VKP, "kp2": _VKP, "sa_c": _VSA, "sa_i": _VSA,
 "hong": (_V, "the high, bright, sing-song voice of a Thai woman of fifty-two"),
 "bm": (_V, "the thin, slightly raspy tenor voice of a Thai man of sixty"),
 "pa": (_V, "the loud, round, mid-pitched voice of a Thai woman of fifty"),
 "ai": (_V, "the loud, cheerful baritone voice of a Thai man of thirty"),
}

# The phrase replaces the bare "Thai" in "speaks Thai" (tools/build_shotsheet.py LANG).
# Isan wording is voice-test clip 1's, minus its mood word "warm" (§Emotion rule 3: a block
# repeated on every line must carry no mood).
_ISAN = ("in the Isan dialect of Northeast Thailand, with a thick Isan accent and Isan tones, "
         "not Bangkok Thai")
LANG = {
 "kp1": _ISAN, "kp2": _ISAN, "sa_c": _ISAN, "sa_i": _ISAN, "bm": _ISAN, "pa": _ISAN,
 "ai": _ISAN,
 "hong": "polished standard Central Thai with a Bangkok accent, not the Isan dialect",
}

_HOME = ("the shaded open space under a traditional wooden Isan house raised high on thick "
         "wooden stilts: a low bamboo slat platform to sit on, a small clay charcoal stove with "
         "a conical woven bamboo sticky-rice steamer, a big brown glazed clay water jar, an old "
         "dented tin trunk against a stilt, lengths of hand-dyed indigo cloth drying on a bamboo "
         "line, a small wooden rice barn on stilts to one side and a packed red-dirt yard, with "
         "golden rice paddies and tall sugar palms beyond")
_NA = ("a wide flat rice paddy in rural Northeast Thailand: narrow raised earth dykes, a small "
       "thatched bamboo field hut on stilts at the edge, tall sugar palms across the fields and "
       "a dirt farm track")
_MILL = ("the concrete yard of a small-town rice mill in Northeast Thailand: three large "
         "combine harvesters painted dark green and cream with no logos, no letters and no "
         "numbers anywhere on them, a tall corrugated-metal mill building, stacks of plain "
         "white woven sacks and a small office with a hot-pink door")

LOC = {
 "home": ("@home__under", _HOME),
 "na_ripe": ("@na__ripe", _NA + ", full of waist-high golden ripe rice heavy with grain"),
 "na_thr": ("@na__threshing", _NA + ", half harvested by hand: cut stubble and bundled "
            "sheaves on the near side, a big blue tarpaulin with a slanted wooden threshing "
            "board and a heap of golden threshed grain near the hut, standing golden rice on "
            "the far side"),
 "na_stub": ("@na__stubble", _NA + ", fully harvested: short golden stubble and round "
             "stacks of straw"),
 "mill_open": ("@mill__open", _MILL + ", the wide roll-up shutter half open and the steel "
               "front gate open"),
 "mill_closed": ("@mill__closed", _MILL + ", seen from just outside the front gate: the steel "
                 "sliding gate shut and wrapped with a heavy chain and padlock, the roll-up "
                 "shutter pulled all the way down, a dusty kerb in front"),
 "land": ("@land__steps", "the front of a plain single-storey white government office "
          "building in a Thai district town: wide concrete steps up to a covered porch with "
          "square white pillars, glass double doors standing open, potted plants and a small "
          "paved car park, with no flags, no emblems and no signs"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere "
           "in the frame.",
 "nologo": "Every vehicle, machine, sack and object is plain: no brand names, no logos, no "
           "badges, no letters or numbers and no readable text anywhere.",
 # Every amount is spoken, never shown (script: numbers table).
 "nocash": "Nobody holds, counts or hands over banknotes or coins.",
 "noletter": "Any paper is seen from the back or edge-on: no readable writing, no printed "
             "form and no stamp ever faces the camera.",
 "noextra": "Nobody else is in the frame: no passers-by, no crowd, no children.",
 "nouniform": "Nobody wears a uniform, a badge, a lanyard or an official insignia.",
}

# S63: the son answers เจ๊หงส์ in Central Thai on purpose (script direction "in Central
# Thai"), so that one shot uses a copy of his indigo key with a Central-Thai LANG.
CHAR["sa_ic"] = CHAR["sa_i"]
WARDROBE["sa_ic"] = WARDROBE["sa_i"]
VOICE["sa_ic"] = VOICE["sa_i"]
LANG["sa_ic"] = ("standard Central Thai, deliberately switching from his Isan dialect to "
                 "answer her in her own language")

PROP_FOR_NOT = {}

_NAME = {"kp1": "แม่คำปุน", "kp2": "แม่คำปุน", "sa_c": "แสน", "sa_i": "แสน",
         "sa_ic": "แสน", "hong": "เจ๊หงส์", "bm": "ผู้ใหญ่", "pa": "ป้าข้างบ้าน", "ai": "อ้ายหนุ่ม"}
_NARRATOR = "ผู้บรรยาย"   # S73-S74: voice-over added in the edit, never generated

T1 = "the first day, bright late-morning sun in the dry harvest season"
T2 = "the next day, bright morning sun"
T3 = "Friday afternoon, strong bright sun"
T4 = "the next day, bright midday sun"
T5 = "a few days later, hot bright afternoon"
T6 = "one month later, soft bright morning sun"


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from SCRIPT-v1."""
    text = (Path(__file__).with_name("ep4-khaifak-SCRIPT-v1.md")).read_text(encoding="utf-8")
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1)); out[cur] = []; continue
        m = re.match(r'\*\*บทพูด\*\* (\S+) `"(.+)"` — (.+)$', ln)
        if m and cur is not None:
            out[cur].append((m.group(1), m.group(3).strip(), m.group(2)))
    return out


def build_shots(meta):
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

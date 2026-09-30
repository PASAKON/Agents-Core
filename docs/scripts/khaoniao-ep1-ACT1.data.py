# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP1 «ทำไมมีมี่กลัวน้ำ แต่ยอมลุยน้ำท่วม?» — 15 shots x 10 s = 2:30. Source of
truth for tools/build_shotsheet.py (pattern: docs/scripts/ep3-ACT1.data.py).

CEO 2026-09-30: "เตรียมเนื้อหาเลยได้ อนุมัติ 300 credit ยิง EP แรก".

The dialogue and its manner tag are NOT typed here: they are read from
docs/scripts/khaoniao-ep1-SCRIPT-v1.md at import time, so the script the CEO reads and the
prompts the runner fires can never disagree. This file adds only what the script does not carry:
who is in each shot (in which STATE), where, the time of day, the English action with its
emotion, and the negatives.

Plates: docs/reports/khaoniao-family-style/build_ep1_plates.py (ChatGPT on winbox, free stills) +
the four approved front crops, all in Assets/Agents/Core/khaoniao-family/plates/ and uploaded to the
Flow project under exactly these handles. One plate per state: Mimi dry / wet, the mother at home /
out in the flood. No wardrobe chips: every plate is already the whole character in that state.

Rules carried in (CMO_Standard_Story_ThaiMoralDrama, CMO_Gate_Flow_Omni1.1_Continuity):
- the speaker's action happens WHILE the line is said, never before it ("then" is banned);
- the first speaker's action is written first, because Flow speaks in ACTION order;
- every character in frame has their own physical action and a loud, physical emotion;
- one speaker per clip; the listener reacts only with the body;
- no money in frame, no children, no uniforms, no night, no text in frame.
Mimi talks to us, never to the humans: they do not understand her and only react to her whining.
"""
import re
from pathlib import Path

STYLE = ("Stylised Thai family-comedy 3D cartoon, vertical 9:16, clearly a cartoon and not a "
         "photograph: chunky rounded shapes, funny big-head proportions, very large friendly "
         "expressive eyes, a high-end 3D finish with a warm key light, a cool rim light and soft "
         "shadows, strong expressive acting, faces clearly readable.")

_MIMI = ("a small fluffy black female dog with a wavy black coat, silver-white eyebrow tufts, a "
         "silver beard with tan under the chin, a white bib on the chest, long drop ears with "
         "silver tips, big dark-brown eyes and a little pink tongue, with no collar and no accessories")
_MOM = ("a plump Thai woman in her fifties with a round rosy face and a kind half-closed smile, "
        "grey-black hair in a messy bun with a wooden ladle stuck through it, a gold amulet "
        "necklace, a pale-yellow short-sleeved top, a cream apron splashed with orange sauce and "
        "a pink-and-green floral sarong, a tartan cloth over one shoulder")

# key: (handle, full appearance block written from the plate, short reference = the speaker's name)
CHAR = {
 "mimi_d": ("@mimi__dry", _MIMI + ", her fur dry and fluffy", "The small black dog"),
 "mimi_w": ("@mimi__wet",
   _MIMI + ", soaked by flood water: wet clumpy fur plastered flat and dripping, water beading "
   "on the silver beard, heavy dripping ears", "The small black dog"),
 "mom_h": ("@mother__home", _MOM + ", wearing pink rubber-soled slippers",
   "The woman with the wooden ladle in her bun"),
 "mom_o": ("@mother__out", _MOM + ", wearing bright pink rubber rain boots and carrying an empty "
   "woven bamboo basket on her forearm", "The woman with the wooden ladle in her bun"),
 "bro": ("@brother__wfh",
   "a stocky Thai man of thirty with a chubby face, square black-rimmed glasses and slicked-back "
   "black hair, wearing a navy double-breasted blazer with gold buttons over a white shirt and a "
   "blue patterned tie, blue elephant-print shorts, blue flip-flops and a gold wristwatch",
   "The stocky man in the navy blazer"),
 "sis": ("@sister__office",
   "a slim Thai woman of twenty-eight with sharp narrow eyes and winged eyeliner, a long black "
   "ponytail with a burgundy streak, large gold hoop earrings, wearing a white short-sleeved "
   "blouse with a work lanyard, a fitted black knee-length skirt, black high heels and a black "
   "shoulder bag",
   "The slim woman in the white blouse"),
 "man": ("@seller__truck",
   "a lean wiry sun-tanned Thai man of fifty-five with a big toothy grin and crinkled eyes, a "
   "sun-faded wide straw hat, a faded green short-sleeved polo shirt with the sleeves rolled, a "
   "blue-and-white checked cloth scarf around his neck, dark knee-length shorts and black rubber "
   "boots",
   "The lean man in the straw hat"),
}

WARDROBE = {}   # every plate is already the whole character in that state

# Timbre, pitch and age ONLY (CMO_Standard_Story_ThaiMoralDrama §Emotion rule 3).
_V = "(prompt only, no bound voice)"
VOICE = {
 "mimi_d": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mimi_w": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mom_h": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "mom_o": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "bro": (_V, "the smooth, mid-low baritone voice of a Thai man of thirty"),
 "sis": (_V, "the clear, quick, sharp voice of a Thai woman of twenty-eight"),
 "man": (_V, "the loud, rough, cheerful voice of a Thai man of fifty-five"),
}

_HOUSE = ("the same Thai townhouse: cream marble floor tiles, a wooden door frame, potted plants, "
          "the white two-door fridge, warm wood furniture")
LOC = {
 "door": ("@loc__doorway_v2",
   "the open front doorway of the Thai townhouse seen from inside at a low, dog's-eye height: "
   "warm yellow indoor light on the dry cream marble floor and the wooden door frame, and "
   "outside a wide sheet of opaque muddy chocolate-brown flood water risen right up to the "
   "threshold with ripples and floating leaves, the steel gate standing in the water, heavy "
   "grey rain falling"),
 "living": ("@loc__living",
   "the living room of " + _HOUSE + ": a work-from-home desk with an open laptop and a white mug "
   "beside a window, a tidy small sofa, a round coffee table, a small round dog bed in a corner, "
   "a wooden shelf with plants, the open dining area behind"),
 "dining": ("@loc__dining",
   "the dining area of " + _HOUSE + ": a wooden table with a bamboo basket of steaming sticky "
   "rice, a plate of grilled chicken and a bowl of papaya salad, four chairs, open kitchen "
   "shelves behind, warm lamps"),
 "street": ("@loc__street",
   "a Thai village street under knee-deep opaque brown flood water in grey overcast rain, a "
   "small blue pickup truck parked in the water loaded with baskets of green morning glory, "
   "bok choy and long beans with a loudspeaker on the cab roof, townhouse fronts and electric "
   "poles along the street"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere in the "
           "frame.",
 "noother": "Only the named characters appear: no other person and no other animal is visible "
            "anywhere in the frame.",
 "nocash": "Nobody holds, counts or hands over banknotes or coins.",
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}

T_AM = "a grey rainy morning, soft light through the window"
T_FLOOD = "late morning, heavy grey rain, flood water everywhere"
T_DAY = "a grey rainy afternoon with warm lamps on indoors"
T_EVE = "evening, warm lamp light, rain still falling outside"
_N = ["nosubs", "noother"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Low medium shot at dog's-eye height on the threshold, her face three-quarters to camera",
     ["mimi_d"], "door", T_FLOOD,
     "the small dog, terrified, shaking from nose to tail, stands at the very edge of the dry "
     "threshold staring at the brown flood water, her ears pinned flat, and squeaks the whole line "
     "while she edges one paw forward and snatches it back; on the very last words she squeezes "
     "her eyes shut and leaps off the threshold into the brown water with a big splash", _N),
 2: (10, "Medium shot in the living room, her face three-quarters to camera",
     ["mom_h"], "living", T_AM,
     "the woman with the wooden ladle in her bun, cheerful and beaming, cocks her head toward the "
     "window at the faint jingle of a passing vegetable truck's loudspeaker and swings an empty "
     "bamboo basket by its handle while she speaks, bouncing on her toes with delight", _N),
 3: (10, "Medium shot at the desk, the dog at his feet looking up, his face above her",
     ["mimi_d", "bro"], "living", T_AM,
     "the small dog, wheedling and sugar-sweet, rears up with both front paws on the seated "
     "man's knee, tail wagging, huge shining eyes begging up at him while she speaks; the stocky "
     "man, distracted, eyes glued to the laptop screen, pats her head without looking down, a white "
     "mug in his other hand", _N),
 4: (10, "Medium shot at the desk, the man's face to camera, the dog at his feet",
     ["bro", "mimi_d"], "living", T_AM,
     "the stocky man in the navy blazer, hurried and strained, holds a tight fake smile toward the "
     "laptop screen, one hand waving the dog away below the desk while he speaks, eyes darting "
     "between the screen and the dog; the small dog, hopeful, sits upright at his feet and wags her "
     "tail slowly, ears up", _N),
 5: (10, "Wide shot across the living room floor",
     ["mom_h", "mimi_d"], "living", T_AM,
     "the woman with the wooden ladle in her bun, laughing and shouting, chases the dog across "
     "the marble floor flapping a pink towel while she speaks, cheeks puffed, waddling fast; the "
     "small dog, panicked, bolts away from her with her ears flying and her claws skidding on the "
     "tiles", _N),
 6: (10, "Low medium shot under the coffee table, her face to camera",
     ["mimi_d"], "living", T_AM,
     "the small dog, whimpering and trembling, crouches under the round coffee table with both "
     "paws clamped over her nose, peeking out with enormous wet eyes at a pink towel that "
     "dangles into the frame from above while she speaks, shivering", _N),
 7: (10, "Medium shot from inside the doorway, the woman outside at the threshold",
     ["mom_o"], "door", T_FLOOD,
     "the woman with the wooden ladle in her bun, bright and singsong, stands just outside the "
     "threshold with the brown water over her ankles, facing the house, waving goodbye with one "
     "hand and holding the empty basket on her other arm while she speaks, and starts wading "
     "toward the gate as she finishes", _N + ["nocash"]),
 8: (10, "Low medium shot at dog's-eye height on the threshold, her face to camera",
     ["mimi_d"], "door", T_FLOOD,
     "the small dog, torn and trembling, stands on the threshold whining, dips one front paw "
     "toward the brown water and snatches it back again and again while she speaks, ears "
     "flattened, eyes darting between the water and the gate", _N),
 9: (10, "Low medium shot on the flood water at her eye level, her face to camera",
     ["mimi_w"], "street", T_FLOOD,
     "the small dog, panicky and comic, paddles through the brown flood water with her chin "
     "stretched high and her teeth chattering while she speaks, squeaking each word, water "
     "lapping at her nose, the blue pickup truck with its baskets of vegetables ahead of her", _N),
 10: (10, "Medium wide shot at the truck, the man in the middle, the woman beside him",
      ["man", "mom_o", "mimi_w"], "street", T_FLOOD,
      "the lean man in the straw hat, amazed and laughing out loud, points down at the water "
      "beside the truck while he speaks and holds out a bunch of green morning glory to the "
      "woman with his other hand; the woman with the wooden ladle in her bun, startled, spins "
      "around with her basket on her arm and her eyes wide; the small soaked dog paddles up "
      "beside the truck's wheel, shivering", _N + ["nocash"]),
 11: (10, "Medium shot at the truck, the woman and the dog in her arms",
      ["mom_o", "mimi_w"], "street", T_FLOOD,
      "the woman with the wooden ladle in her bun, surprised then delighted, laughing, bends "
      "down and scoops the dripping dog out of the water into her arms while she speaks, "
      "hugging her to her chest, the basket swinging on her forearm; the small soaked dog, "
      "shaking, presses her trembling body against her and blinks up at her", _N + ["nocash"]),
 12: (10, "Medium wide shot at the front door, the man inside, the woman on the threshold",
      ["bro", "mom_o", "mimi_w"], "door", T_FLOOD,
      "the stocky man in the navy blazer and elephant-print shorts, exasperated and theatrical, "
      "stands inside the open front door with his palm pressed to his forehead, stamping one "
      "flip-flop in a puddle of dripped water while he speaks; the woman with the wooden ladle in "
      "her bun stands on the threshold holding the dripping dog in her arms, smiling "
      "obliviously; the small soaked dog, shivering, looks down guiltily", _N),
 13: (10, "Medium shot on the living room floor, the woman kneeling, the man at the desk behind",
      ["mom_h", "bro", "mimi_w"], "living", T_DAY,
      "the woman with the wooden ladle in her bun, gentle and puzzled, kneels on the marble "
      "floor rubbing the small soaked dog with a pink towel while she speaks, stroking her own "
      "cheek, her eyes a little teary; the stocky man in the navy blazer, sheepish, slowly stops "
      "typing and lowers his gaze to the dog, his mug forgotten beside the laptop; the small "
      "dog, wrapped in the towel, looks up at them shivering", _N),
 14: (10, "Close medium shot on the floor, the dog's face to camera, the man kneeling beside her",
      ["mimi_w", "bro"], "living", T_DAY,
      "the small dog, crying, tears streaming down her face, nuzzles into a pink towel while "
      "she speaks, her voice breaking; the stocky man in the navy blazer, guilty and moved, "
      "kneels on the floor beside her and gently tucks the towel around her with both hands, "
      "his eyes wet", _N),
 15: (10, "Medium shot at the dining table, the woman kneeling with the dog",
      ["sis", "mimi_d"], "dining", T_EVE,
      "the slim woman in the white blouse, melting from stern to gooey, squealing with delight, "
      "kicks off her black heels and kneels to hug the small fluffy dog while she speaks; the "
      "small dog, dry and fluffy, wags her whole body with her tongue out beside a table of "
      "steaming sticky rice and grilled chicken", _N),
}

_NAME = {"mimi_d": "มีมี่", "mimi_w": "มีมี่", "mom_h": "แม่", "mom_o": "แม่", "bro": "พี่ชาย",
         "sis": "น้องสาว", "man": "ลุงผัก"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep1-SCRIPT-v1.md")).read_text(encoding="utf-8")
    out, cur = {}, None
    for ln in text.splitlines():
        m = re.match(r"### SHOT (\d+) ", ln)
        if m:
            cur = int(m.group(1)); out[cur] = []; continue
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
            key = next((c for c in chars if _NAME[c] == who), None)
            if key is None:
                raise SystemExit(f"shot {n}: speaker {who} is not in the shot's cast {chars}")
            spoken.append((key, direction, line))
        shots.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return shots


SHOTS = _build(_META)

# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP1 «ทำไมมีมี่กลัวน้ำ แต่ยอมลุยน้ำท่วม?» — 18 shots x 10 s = 3:00. Source of
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
Mimi talks to the person or the flood in front of her, never to the viewer: the humans do not understand her and only react
to her whining. Every shot states facing, addressee and direction of movement (CMO_Standard_Film_PromptFormat rule 12).
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
 1: (10, "Low over-the-shoulder shot from INSIDE the house at dog's-eye height, the camera just behind "
     "and a little to the left of the small dog: she stands on the threshold with her BACK and left "
     "flank to the camera, facing OUT toward the flood, her head turned in three-quarter rear profile "
     "toward screen-right so the side of her muzzle and her moving mouth stay visible; she never "
     "looks at the camera",
     ["mimi_d"], "door", T_FLOOD,
     "the small dog, terrified, shaking from nose to tail, stands at the very edge of the dry "
     "threshold with her back to the camera, staring out over the brown flood water, her ears pinned "
     "flat, and squeaks the whole line out into the rain, calling after someone far ahead who is "
     "off-screen, while she edges one paw forward and snatches it back; on the very last words she "
     "squeezes her eyes shut and leaps FORWARD off the threshold, away from the camera, into the "
     "brown water with a big splash", _N),

 2: (10, "Medium shot in the living room from the front at chest height: she stands at screen-centre facing "
     "screen-right in three-quarter profile, her eyes on the window at screen-right and never on the "
     "camera, talking to the household at large",
     ["mom_h"], "living", T_AM,
     "the woman with the wooden ladle in her bun, cheerful and beaming, turns her head toward the "
     "window at screen-right at the faint jingle of a passing vegetable truck's loudspeaker and swings "
     "an empty bamboo basket by its handle while she speaks, bouncing on her toes with delight", _N),
 3: (10, "Medium shot from the side at the desk: the desk and laptop are at screen-left, the stocky man sits "
     "facing screen-left in three-quarter profile with his eyes on the laptop, and the small dog stands "
     "at his knee at screen-right facing screen-left and looking UP at him, her muzzle in profile to the "
     "camera so her mouth shows; she speaks to him",
     ["mimi_d", "bro"], "living", T_AM,
     "the small dog, wheedling and sugar-sweet, rears up with both front paws on the seated man's knee, "
     "tail wagging, huge shining eyes begging up at his face while she speaks to him; the stocky man, "
     "distracted, eyes glued to the laptop screen at screen-left, pats her head without looking down, a "
     "white mug in his other hand", _N),
 4: (10, "Medium shot from just behind the open laptop, so the man is three-quarters to the lens while he "
     "looks at his screen, and the small dog sits at his feet at screen-right facing up and to the left "
     "toward him; he answers the dog below him while he forces a smile at the laptop",
     ["bro", "mimi_d"], "living", T_AM,
     "the stocky man in the navy blazer, hurried and strained, holds a tight fake smile at the laptop "
     "screen, one hand waving the dog away below the desk at screen-right while he speaks to her, his "
     "eyes darting between the screen and the dog; the small dog, hopeful, sits upright at his feet and "
     "wags her tail slowly, ears up, looking up at him", _N),
 5: (10, "Wide shot from the sofa side across the living room floor: everyone runs from screen-right to "
     "screen-left, the small dog in front with her head turned back over her shoulder toward the woman, "
     "the woman close behind her facing screen-left and shouting at the dog",
     ["mom_h", "mimi_d"], "living", T_AM,
     "the woman with the wooden ladle in her bun, laughing and shouting, chases the dog across the "
     "marble floor toward screen-left flapping a pink towel while she speaks to the dog, cheeks puffed, "
     "waddling fast; the small dog, panicked, bolts away from her toward screen-left with her ears "
     "flying and her claws skidding on the tiles", _N),
 6: (10, "Low shot at floor level from the front: the small dog crouches under the round coffee table at "
     "screen-centre, three-quarters to the camera, with her head turned up and toward screen-right at "
     "the pink towel dangling in from the top-right; she speaks up to the woman, who is off-screen "
     "above her at screen-right",
     ["mimi_d"], "living", T_AM,
     "the small dog, whimpering and trembling, crouches under the round coffee table with both paws "
     "clamped over her nose, peeking up and to the right with enormous wet eyes at a pink towel "
     "dangling into the frame from the top-right while she pleads with the woman above her, shivering", _N),
 7: (10, "Medium shot from inside the doorway at dog's-eye height: the woman stands just outside the "
     "threshold at screen-centre facing the house, toward the camera, her eyes down on the small dog "
     "who stands just behind the camera (she talks to the dog, who is off-screen and low); at the end "
     "she turns and wades away from the camera toward the gate at screen-right",
     ["mom_o"], "door", T_FLOOD,
     "the woman with the wooden ladle in her bun, bright and singsong, stands just outside the "
     "threshold with the brown water over her ankles, waving goodbye with one hand and holding the "
     "empty basket on her other arm while she speaks down to the dog, and on her last words turns and "
     "wades away from the camera toward the gate at screen-right", _N + ["nocash"]),
 8: (10, "Low over-the-shoulder shot from INSIDE the house at dog's-eye height, the same set-up as the "
     "opening leap: the camera just behind and a little to the left of the small dog, who stands on the "
     "threshold with her BACK and left flank to the camera, facing OUT toward the flood, her head turned "
     "in three-quarter rear profile toward screen-right so the side of her muzzle and moving mouth "
     "show; she speaks to the woman who has just waded off, out of sight ahead at screen-right; she "
     "never looks at the camera",
     ["mimi_d"], "door", T_FLOOD,
     "the small dog, torn and trembling, stands on the threshold with her back to the camera, whining "
     "out over the brown water toward the right, dips one front paw toward the water and snatches it "
     "back again and again while she speaks, ears flattened, eyes darting between the water and the "
     "street ahead; she stays on the threshold", _N),
 9: (10, "Low shot on the flood water at her eye level, from ahead of her and to the left: the small dog "
     "paddles from screen-left to screen-right, in three-quarter profile to the camera facing "
     "screen-right with her chin high, her eyes on the blue pickup truck far ahead at screen-right; "
     "she talks to herself, never to the camera",
     ["mimi_w"], "street", T_FLOOD,
     "the small dog, panicky and comic, paddles through the brown flood water toward screen-right with "
     "her chin stretched high and her teeth chattering while she encourages herself, squeaking each "
     "word, water lapping at her nose, the blue pickup truck with its baskets of vegetables ahead of "
     "her at screen-right", _N),
 10: (10, "Medium wide shot across the flooded street at the truck: the blue pickup stands at screen-right "
      "with the seller at its tailgate, the woman stands at screen-centre facing screen-right in "
      "three-quarter profile with her eyes on the vegetables, and she talks to him; nobody else is in the frame",
      ["mom_o", "man"], "street", T_FLOOD,
      "the woman with the wooden ladle in her bun, cheerful and oblivious, stands in the brown water "
      "holding her empty basket out toward the truck and pointing at the baskets of green morning glory "
      "and bok choy with her free hand, bouncing on her toes while she speaks to the man; the lean man "
      "in the straw hat faces screen-left toward her, grinning, and weighs a bunch of morning glory in "
      "his hand", _N + ["nocash"]),
 11: (10, "Medium wide shot at the truck: the truck stands at screen-right, the man faces screen-left "
      "toward the woman in three-quarter profile and points down and to screen-left at the water where "
      "the small dog is arriving from screen-left, the woman stands at screen-centre spinning round to "
      "face screen-left, and the man talks to the woman",
      ["man", "mom_o", "mimi_w"], "street", T_FLOOD,
      "the lean man in the straw hat, amazed and laughing out loud, points down and to screen-left at "
      "the water beside the truck while he speaks to the woman and holds out a bunch of green morning "
      "glory to her with his other hand; the woman with the wooden ladle in her bun, startled, spins "
      "around toward screen-left with her basket on her arm and her eyes wide; the small soaked dog "
      "paddles up from screen-left to the truck's wheel, shivering, looking up at the woman", _N + ["nocash"]),
 12: (10, "Medium shot at the truck from in front of the woman: she faces the camera in three-quarters, her "
      "eyes down on the small dog in her arms, and she talks to the dog, whose head rests over her forearm "
      "toward screen-left, looking up at her face",
      ["mom_o", "mimi_w"], "street", T_FLOOD,
      "the woman with the wooden ladle in her bun, surprised then delighted, laughing, bends down and "
      "scoops the dripping dog out of the water into her arms while she speaks to the dog, hugging her "
      "to her chest, the basket swinging on her forearm; the small soaked dog, shaking, presses her "
      "trembling body against her and blinks up at her", _N + ["nocash"]),
 13: (10, "Medium wide shot from the dry floor inside at the front door: the stocky man stands inside at "
      "screen-left in profile facing screen-right toward the door with his eyes down on the dog, the woman "
      "stands on the threshold at screen-right facing into the house, toward screen-left, holding the "
      "small dripping dog in her arms, and the man talks to the DOG",
      ["bro", "mom_o", "mimi_w"], "door", T_FLOOD,
      "the stocky man in the navy blazer and elephant-print shorts, exasperated and theatrical, stands "
      "inside the open front door at screen-left with his palm pressed to his forehead, stamping one "
      "flip-flop in a puddle of dripped water while he scolds the dog at screen-right; the woman with "
      "the wooden ladle in her bun stands on the threshold holding the dripping dog in her arms, "
      "smiling obliviously at him; the small soaked dog, shivering, looks down guiltily", _N),
 14: (10, "Low shot at floor level from the front in the living room: the small dog sits on the marble floor "
      "wrapped in a pink towel at screen-centre, her body in three-quarter profile facing screen-left, "
      "her eyes on the doorway at screen-left where the man stood (off-screen), and she talks to him, "
      "her muzzle in profile so her mouth shows; nobody else is in the frame",
      ["mimi_w"], "living", T_DAY,
      "the small dog, wounded and tearful, sits dripping inside a pink towel draped over her "
      "shoulders, her ears low, tears welling in her big eyes, and pleads toward the doorway at "
      "screen-left while she speaks, her chin trembling, shaking her head once", _N),
 15: (10, "Medium shot on the living room floor: the woman kneels in the foreground at screen-right facing "
      "screen-left in profile, her eyes on the stocky man at the desk at screen-left in the background, "
      "and she tells him what the seller said; the small dog in the towel sits between them at "
      "screen-centre looking up at the woman, and the man faces screen-right toward her",
      ["mom_h", "bro", "mimi_w"], "living", T_DAY,
      "the woman with the wooden ladle in her bun, gentle and puzzled, kneels on the marble floor "
      "rubbing the small soaked dog with a pink towel while she speaks to the man at the desk, stroking "
      "her own cheek, her eyes a little teary; the stocky man in the navy blazer, sheepish, slowly "
      "stops typing, turns his face toward her and lowers his gaze to the dog, his mug forgotten beside "
      "the laptop; the small dog, wrapped in the towel, looks up at the woman shivering", _N),
 16: (10, "Close medium shot on the floor from the front: the small dog, wrapped in the towel, looks up "
      "and toward screen-right in three-quarters at the stocky man who kneels beside her at screen-right "
      "facing screen-left with his eyes on her; she speaks to him",
      ["mimi_w", "bro"], "living", T_DAY,
      "the small dog, crying, tears streaming down her face, nuzzles into a pink towel while she "
      "speaks to him, her voice breaking; the stocky man in the navy blazer, guilty and moved, kneels "
      "on the floor beside her and gently tucks the towel around her with both hands, his eyes wet", _N),
 17: (10, "Medium close shot on the floor from the side: the stocky man kneels at screen-right facing "
      "screen-left in profile with his eyes on the small dog, the dog sits at screen-left facing "
      "screen-right in three-quarters looking up at him, and he talks to her",
      ["bro", "mimi_w"], "living", T_DAY,
      "the stocky man in the navy blazer, remorseful and choked up, kneels on the marble floor and "
      "cradles the small dog's face gently in both hands while he speaks to her, his glasses fogged, "
      "his eyes wet and a small smile breaking through; the small dog, wrapped in the same pink towel, looks up "
      "at him and her tail starts to wag slowly", _N),
 18: (10, "Medium shot at the dining table: the slim woman kneels at screen-right facing screen-left in "
      "three-quarters toward the small dog, her eyes on her, and talks to her; the dog stands at "
      "screen-left facing screen-right toward her with her tongue out",
      ["sis", "mimi_d"], "dining", T_EVE,
      "the slim woman in the white blouse, melting from stern to gooey, squealing with delight, kicks "
      "off her black heels and kneels to hug the small fluffy dog while she speaks to her; the small "
      "dog, dry and fluffy, wags her whole body with her tongue out beside a table of steaming sticky "
      "rice and grilled chicken", _N),
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

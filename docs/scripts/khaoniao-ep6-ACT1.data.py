# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP6 «ทำไมมีมี่หูตั้งทุกครั้งที่ได้ยินเสียงรถขายผัก?» — 18 shots
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep5-ACT1.data.py).

CEO 2026-10-13 (via COO): EP6 airs Sat 17 Oct 19:30, <=330 credits; hook B (CCTV cold-open, composed in post) chosen.
Dialogue and manner tags are read from docs/scripts/khaoniao-ep6-SCRIPT-v1.md at import time. Plates reused as they
are: mimi__dry, mother__home, mother__out, brother__wfh, seller__truck, loc__living, loc__dining, loc__street.
The sister, Ryo, the father and the grandmother are NOT in this episode.

Direction plan (CMO_Standard_Film_PromptFormat rule 12): house shots as EP5 (desk at screen-LEFT beside the window, the
small sofa in the middle, the dining area behind at screen-centre-right, the wooden front door at the FAR RIGHT edge). In
the street shots the road runs left-right, the village truck stands at screen-RIGHT, everyone leaves the house toward
screen-RIGHT, Mimi walks on the ROAD side (nearest the camera) between her mother and the traffic. A white pickup rolls
slowly past far away at screen-LEFT with nobody visible in it. Mimi never talks to the viewer; the humans do not
understand her.

The loc__street plate was made for EP1 under flood water: every street shot says the road is DRY and carries NOFLOOD;
shot 9 is the 360p test for it (script ช่อง credits).
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
 "mom_h": ("@mother__home", _MOM + ", wearing pink rubber-soled slippers",
   "The woman with the wooden ladle in her bun"),
 "mom_o": ("@mother__out", _MOM + ", wearing bright pink rubber rain boots and carrying an empty "
   "woven bamboo basket on her forearm", "The woman with the wooden ladle in her bun"),
 "bro": ("@brother__wfh",
   "a stocky Thai man of thirty with a chubby face, square black-rimmed glasses and slicked-back "
   "black hair, wearing a navy double-breasted blazer with gold buttons over a white shirt and a "
   "blue patterned tie, blue elephant-print shorts, blue flip-flops and a gold wristwatch",
   "The stocky man in the navy blazer"),
 "man": ("@seller__truck",
   "a lean wiry sun-tanned Thai man of fifty-five with a big toothy grin and crinkled eyes, a "
   "sun-faded wide straw hat, a faded green short-sleeved polo shirt with the sleeves rolled, a "
   "blue-and-white checked cloth scarf around his neck, dark knee-length shorts and black rubber "
   "boots",
   "The lean man in the straw hat"),
}

WARDROBE = {}   # every plate is already the whole character in that state

# Timbre, pitch and age ONLY (CMO_Standard_Story_ThaiMoralDrama §Emotion rule 3). Same words as EP1.
_V = "(prompt only, no bound voice)"
VOICE = {
 "mimi_d": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mom_h": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "mom_o": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "bro": (_V, "the smooth, mid-low baritone voice of a Thai man of thirty"),
 "man": (_V, "the loud, rough, cheerful voice of a Thai man of fifty-five"),
}

_HOUSE = ("the same Thai townhouse: cream marble floor tiles, a wooden door frame, potted plants, "
          "the white two-door fridge, warm wood furniture")
LOC = {
 "living": ("@loc__living",
   "the living room of " + _HOUSE + ": a work-from-home desk with an open laptop and a white mug "
   "beside a window at screen-left, a tidy small sofa in the middle, a round coffee table, a small "
   "round dog bed in a corner, a wooden shelf with plants, the open dining area behind at screen-right, "
   "a wooden front door at the far right edge of the room with a woven straw doormat in front of it "
   "and a low wooden shoe rack beside it holding a few pairs of slippers, and a dark corridor opening "
   "to the bedrooms at the far left edge"),
 "dining": ("@loc__dining",
   "the dining and kitchen area of " + _HOUSE + ": a wooden table, four chairs, a rice pot and a "
   "steaming pot on the counter, open kitchen shelves behind, a woven bamboo basket hanging on a hook "
   "beside the counter"),
 "street": ("@loc__street",
   "a DRY Thai village street on a bright sunny morning with a clear blue sky, a dry grey concrete road with "
   "no puddles and no water anywhere, townhouse fronts with potted plants and electric poles along the road, "
   "and at screen-right a small blue pickup truck parked at the roadside loaded with baskets of green morning "
   "glory, bok choy and long beans with a loudspeaker on the cab roof"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere in the "
           "frame.",
 "noother": "Only the named characters appear: no other person and no other animal is visible "
            "anywhere in the frame.",
 "nocash": "Nobody holds, counts or hands over banknotes or coins.",
 "noscreen": "The laptop screen faces away from the camera: no face, no picture and no text on any screen is visible.",
 "nopics": "No framed pictures or photographs hang on any wall or stand on any shelf.",
 "nonumber": "No house number, no plaque and no sign appears on the door or anywhere else in the frame.",
 "noflood": "There is no flood, no puddle and no water on the ground anywhere: the road is completely dry.",
 "nodriver": "No driver and no passenger is visible in any vehicle: the windows are tinted dark.",
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}

T_AM = ("ten o'clock in the morning, bright warm daylight, sunlight slanting through the window at screen-left "
        "across the cream marble floor")
T_ST = "ten o'clock in the morning, bright sunny daylight with crisp shadows under a clear blue sky"
_N = ["nosubs", "noother", "noscreen", "nopics", "nonumber"]
_NS = ["nosubs", "noother", "nonumber", "noflood", "nodriver", "nocash"]
_BOWL = "a full bowl of rice with a fried egg on top"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Medium close shot at floor level in the living room from the front: the small dog stands very upright "
     "beside " + _BOWL + " on the marble floor at screen-centre-right in three-quarter profile, her face turned toward "
     "the closed wooden front door at the far right edge, her whole face and moving mouth visible from the first "
     "frame, her ears pricked straight up; she never looks at the camera",
     ["mimi_d"], "living", T_AM,
     "the small dog, whispering and thrilled, freezes with both ears shot straight up and her head tilted toward the "
     "door, her nose twitching, lifts one front paw off the floor as she listens and says the line in a hushed "
     "excited voice, her tail tip quivering", _N),

 2: (10, "Medium shot in the living room from the front: the stocky man sits at the desk at screen-left in "
     "three-quarter profile with his finger pressed to his lips and a white mug beside the open laptop, whose screen faces "
     "away from the camera; at screen-centre-right the small dog stands beside the bowl looking at the front door, seen "
     "from the side",
     ["bro", "mimi_d"], "living", T_AM,
     "the stocky man in the navy blazer, whispering and pleading, holds one finger to his lips, points the other "
     "hand flat down at the floor in a sit-down gesture toward the dog and mimes 'ten minutes' by holding up all "
     "his fingers as he speaks; the small dog at screen-centre-right, silent, keeps her ears up and her eyes on the door",
     _N),

 3: (10, "Medium close shot at floor level from the front: the small dog stands at screen-centre-right beside the "
     "bowl in three-quarter profile, her face turned toward the front door at the far right edge, her whole face and "
     "moving mouth visible",
     ["mimi_d"], "living", T_AM,
     "the small dog, breathless and determined, spins away from the bowl and kicks it with her back paw so the rice "
     "scatters across the cream marble floor, then bounds toward the door at screen-right with her ears flying "
     "back as she says the line over her shoulder to the unseen woman", _N),

 4: (10, "Medium shot in the living room from the front: the stocky man sits at the desk at screen-left in "
     "three-quarter profile, his body twisted toward screen-right, looking at the white rice scattered across the "
     "marble floor at screen-centre and the empty bowl lying on its side; the closed front door stands at the far "
     "right edge",
     ["bro"], "living", T_AM,
     "the stocky man in the navy blazer, stifled and exasperated, drags both hands down his face, then points "
     "at the scattered rice and shakes his head slowly, whispering through clenched teeth so the meeting will not hear",
     _N),

 5: (10, "Medium shot in the dining and kitchen area from the front: the woman stands at the counter at screen-centre "
     "reaching up for the woven bamboo basket on its hook, her body turned three-quarter toward screen-right and her "
     "face looking over her shoulder toward the living room beyond the right edge, and she talks toward it",
     ["mom_h"], "dining", T_AM,
     "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green floral "
     "sarong showing at her knees, sweet and dreamy, lifts the bamboo basket off its hook with a happy little hum, "
     "glances back over her shoulder with a gentle half-smile and nods on the last words", _N),

 6: (10, "Medium close shot at floor level in the dining area from the front: the small dog plants herself in "
     "front of the woman's feet at screen-centre in three-quarter profile, her head tilted up and turned toward "
     "screen-right where the unseen door is, her whole face and moving mouth visible",
     ["mimi_d"], "dining", T_AM,
     "the small dog, firm and tiny, blocks the way with her body, sits very upright, lifts one front paw as if to say stop, "
     "glances at the door and back up at the unseen woman and says the line with her chin lifted", _N),

 7: (10, "Medium wide shot in the living room from the front: the stocky man turns in his desk chair at screen-left "
     "and looks toward screen-right, where the woman stands by the front door at the far right edge with her basket on her "
     "arm and the small dog at her feet; he talks to the woman",
     ["bro", "mom_o", "mimi_d"], "living", T_AM,
     "the stocky man in the navy blazer, worried and teasing, half rises from the chair with the white mug in one hand "
     "and points the mug toward the dog while he speaks across the room to the woman; the woman with the wooden "
     "ladle in her bun, silent, smiles and shifts the basket on her arm; the small dog at her feet stares up at the door knob",
     _N),

 8: (10, "Medium shot in the living room from the front: the woman stands at the front door at the far right edge, one hand "
     "on the knob, her face in three-quarter profile turned toward screen-left toward the stocky man at the desk, and she "
     "talks to him; the small dog sits at her feet looking up at her",
     ["mom_o", "mimi_d"], "living", T_AM,
     "the woman with the wooden ladle in her bun, serene and warm, smiles and waves her free hand lightly at him as if "
     "brushing the worry away, then bends and pats the small dog on the head and turns the knob on the last words; the "
     "small dog at her feet, silent, wags her whole body", _N),

 9: (10, "Medium wide shot from the road side across the dry street: the woman walks at screen-centre toward "
     "screen-right with her basket on her arm, her face in profile; the small dog trots beside her on the road side "
     "nearest the camera, her face in profile and her whole face and moving mouth visible; the blue vegetable truck "
     "stands at the roadside far ahead at screen-right; far behind them at screen-left a white pickup truck rolls slowly "
     "along the road",
     ["mimi_d", "mom_o"], "street", T_ST,
     "the small dog, whispering and focused, trots with her ears pricked, flicking her eyes left toward the far pickup "
     "and right toward the road ahead, and keeps her body between the woman and the road edge while she says the line; "
     "the woman with the wooden ladle in her bun, silent, strolls humming and swinging her basket",
     _NS),

 10: (10, "Medium wide shot at the truck: the blue pickup stands at screen-right with the seller at its tailgate "
      "facing screen-left in three-quarter profile, the woman stands at screen-centre facing screen-right in "
      "three-quarter profile choosing vegetables, and the small dog sits at her feet on the road side looking toward "
      "screen-left; the seller talks to the woman",
      ["man", "mom_o", "mimi_d"], "street", T_ST,
      "the lean man in the straw hat, cheerful and puzzled, holds up a bunch of green morning glory toward the woman "
      "with a big grin, then points his chin toward the small dog while he speaks; the woman with the wooden ladle in her "
      "bun, silent, reaches out for the bunch of morning glory; the small dog at her feet keeps her gaze fixed past the truck "
      "toward the road at screen-left", _NS),

 11: (10, "Medium close shot at the roadside from the front: the small dog stands on the road edge at screen-centre in "
      "three-quarter profile facing screen-left toward the road, her whole face and moving mouth visible, the woman and "
      "the blue truck blurred behind her at screen-right; far down the road at screen-left a white pickup rolls "
      "slowly toward them",
      ["mimi_d", "mom_o"], "street", T_ST,
      "the small dog, fierce and tiny, plants all four paws wide, puffs out her chest and barks and scolds toward the "
      "far pickup with her ears flat back and her teeth showing, stamping one front paw on every word, while the woman "
      "behind her, silent, keeps choosing vegetables", _NS),

 12: (10, "Medium shot at the truck: the seller leans on the tailgate at screen-right facing screen-left in "
      "three-quarter profile, the woman stands at screen-centre with her back half turned, and the small dog stands "
      "at the roadside at screen-centre-left; the seller talks to the woman",
      ["man", "mom_o", "mimi_d"], "street", T_ST,
      "the lean man in the straw hat, startled and joking, flaps his hat at the dog and then holds a bundle of long "
      "beans out to the woman, wagging a finger toward the dog while he speaks and laughing out loud; the woman with the "
      "wooden ladle in her bun, silent, smiles and shakes her head; the small dog, silent, keeps her chest out and watches "
      "the road", _NS),

 13: (10, "Medium close shot at the roadside from the front: the small dog trots beside the woman's boots at screen-"
      "centre toward screen-left on the way home, her face in three-quarter profile turned up toward the woman, her whole "
      "face and moving mouth visible; the woman's boots and the basket full of green vegetables at the right edge",
      ["mimi_d", "mom_o"], "street", T_ST,
      "the small dog, relieved and soft, lets her ears relax and her tail swing, looks up at the woman with a tender "
      "smile and leans the side of her body against the woman's boot as she says the line while they walk; the woman, "
      "silent, hums with her basket full of vegetables", _NS),

 14: (10, "Medium shot in the living room from the front: the stocky man sits at the desk at screen-left in "
      "three-quarter profile with the laptop open and angled away from the camera, one hand on the mouse, his eyes narrowed "
      "at the screen; the closed front door stands at the far right edge with a few grains of rice still scattered on the floor",
      ["bro"], "living", T_AM,
      "the stocky man in the navy blazer, suspicious and grumbling, leans toward the laptop, drums his fingers on the desk "
      "and mutters his line, raising one eyebrow, and clicks the mouse twice on the last words", _N),

 15: (10, "Medium close shot of the stocky man at the desk at screen-left from the front: his face in three-quarter profile "
      "lit softly from the side by the laptop, which faces away from the camera, his eyes widening as he watches it",
      ["bro"], "living", T_AM,
      "the stocky man in the navy blazer, slowly realising and hushed, leans closer to the laptop, his eyes widening and his "
      "mouth falling open a little, lifts one finger to point at the screen and then presses the hand to his chest as he "
      "speaks", _N),

 16: (10, "Medium wide shot in the living room from the front: the front door at the far right edge stands open and the "
      "woman stands on the threshold with the basket of vegetables, the small dog sits on the doormat beside her; the stocky "
      "man walks over from the desk and crouches in front of the dog at screen-centre, his face in three-quarter profile "
      "turned toward her, and talks to her",
      ["bro", "mom_h", "mimi_d"], "living", T_AM,
      "the stocky man in the navy blazer, soft and sorry, crouches down to the small dog, bows his head a little and "
      "rests one hand gently on her head as he says the line; the woman with the wooden ladle in her bun, silent, holds the "
      "basket and watches with a tender smile; the small dog sits very still with her ears up, silent", _N),

 17: (10, "Medium close shot in the living room from the front: the woman stands at screen-centre holding the basket of "
      "green vegetables against her hip, her face in three-quarter profile turned toward the small dog who sits at "
      "screen-right on the doormat, and she talks to her",
      ["mom_h", "mimi_d"], "living", T_AM,
      "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green floral "
      "sarong showing at her knees, voice breaking and tender, dabs the corner of her eye with the tartan cloth and "
      "presses her other hand to her heart as she speaks; the small dog on the doormat at the right edge, silent, looks "
      "back at her with her head tilted", _N),

 18: (10, "Medium wide shot in the living room from the front: the small dog sits on the doormat at screen-right with "
      "the empty rice bowl beside her, her head turned toward screen-left in three-quarter profile toward the stocky man "
      "and the woman who sit on the floor beside her, her whole face and moving mouth visible; the front door stands "
      "closed at the far right edge",
      ["mimi_d", "bro", "mom_h"], "living", T_AM,
      "the small dog, cheeky and sleepy, licks her chops with her tongue out, pats the floor beside her with one paw "
      "to invite them and yawns on the last words; the stocky man in the navy blazer and the woman with the wooden "
      "ladle in her bun, both sitting cross-legged on the floor beside her, smile and nod, silent", _N),
}

_NAME = {"mimi_d": "มีมี่", "mom_h": "แม่", "mom_o": "แม่", "bro": "พี่ชาย", "man": "คนขายผัก"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep6-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

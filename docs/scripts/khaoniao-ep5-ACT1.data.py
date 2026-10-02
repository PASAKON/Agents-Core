# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP5 «ทำไมมีมี่นั่งเฝ้าประตูทุกเย็น ทั้งที่น้องสาวไม่เคยสนใจเธอ?» — 18 shots
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep4-ACT1.data.py).

CEO 2026-10-02: "ทำ EP3-EP5 ต่อได้เลย", "เอาตามนั้นได้เลย ทำมาก่อนไม่ต้องกลัวผิด" (go with the script as drafted,
including the sister's one gruff line in shot 16 and the [แต่ง] points; he reviews at the 540p preview).

Dialogue and manner tags are read from docs/scripts/khaoniao-ep5-SCRIPT-v1.md at import time. Plates reused as they
are: mimi__dry, mother__home, brother__wfh, sister__office, loc__living, loc__dining. The front door, doormat, shoe
rack and the dog's rice bowl are words only (written into the living-room set). Ryo, the father and the seller are NOT
in this episode.

Direction plan (CMO_Standard_Film_PromptFormat rule 12): desk at screen-LEFT beside the window, the small sofa in the
middle, the dining area behind at screen-centre-right, the wooden front door at the FAR RIGHT edge with the doormat in
front of it where Mimi sits facing it. The bedroom corridor is at the far LEFT. The sister enters through the front door
(right) and walks LEFT past the camera into the corridor. Mimi never talks to the viewer; the humans do not understand
her. The sister never looks down at, touches or speaks to Mimi.
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
   _MIMI + ", her fur damp and clumpy, flattened and dripping a little, a few white soap bubbles "
   "on her head and back", "The small black dog"),
 "mimi_x": ("@mimi__wet",
   _MIMI + ", her fur damp and clumped flat, wet through but not dripping, with no soap bubbles left",
   "The small black dog"),
 "mom_h": ("@mother__home", _MOM + ", wearing pink rubber-soled slippers",
   "The woman with the wooden ladle in her bun"),
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
}

WARDROBE = {}   # every plate is already the whole character in that state

# Timbre, pitch and age ONLY (CMO_Standard_Story_ThaiMoralDrama §Emotion rule 3). Same words as EP1.
_V = "(prompt only, no bound voice)"
VOICE = {
 "mimi_d": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mimi_w": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mimi_x": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mom_h": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "bro": (_V, "the smooth, mid-low baritone voice of a Thai man of thirty"),
 "sis": (_V, "the clear, quick, sharp voice of a Thai woman of twenty-eight"),
}

_HOUSE = ("the same Thai townhouse: cream marble floor tiles, a wooden door frame, potted plants, "
          "the white two-door fridge, warm wood furniture")
LOC = {
 "living": ("@loc__living",
   "the living room of " + _HOUSE + ": a work-from-home desk with an open laptop and a white mug "
   "beside a window at screen-left, a tidy small sofa in the middle, a round coffee table, a small "
   "round dog bed in a corner, a wooden shelf with plants, the open dining area behind at screen-right"),
 "dining": ("@loc__dining",
   "the dining and kitchen area of " + _HOUSE + ": a wooden table, four chairs, a rice pot and a "
   "steaming pot on the counter, open kitchen shelves behind"),
 "bath": ("@loc__bathroom",
   "a small Thai home bathroom with glossy pale-blue wall tiles and a cream tiled floor, an open "
   "doorway at screen-left, a low blue plastic basin of warm water with white soap bubbles on the "
   "tiled floor right of centre with a red plastic dipper bowl with a handle floating in it, a "
   "plastic stool, a white bath mat, a small window with soft daylight"),
 "under": ("@loc__sofa_low",
   "the living room seen from floor level at the front of the small tidy sofa: its low front edge and "
   "short wooden legs frame a wide, low, shadowy hollow under the sofa with a clean cream marble floor "
   "inside, a slanting shaft of warm daylight lighting the hollow, the bright living room beyond at the "
   "sides"),
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
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}



LOC["living"] = (LOC["living"][0], LOC["living"][1] + ", a wooden front door at the far right edge of the room with a "
  "woven straw doormat in front of it and a low wooden shoe rack beside it holding a few pairs of slippers, and a dark "
  "corridor opening to the bedrooms at the far left edge")

T_EVE = ("seven o'clock in the evening, warm orange ceiling lamps switched on inside, the window at screen-left showing "
         "a deep dusk-blue sky")
_N = ["nosubs", "noother", "noscreen", "nopics", "nonumber"]
_BOWL = "a full bowl of rice with a fried egg on top"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Medium close shot at floor level in the living room from the front: the small dog sits very upright on the "
     "woven doormat at screen-right in three-quarter profile, her face turned toward the closed wooden front door at "
     "the far right edge, her whole face and moving mouth visible from the first frame, her ears pricked; she never "
     "looks at the camera",
     ["mimi_d"], "living", T_EVE,
     "the small dog, whispering and alert, stares at the door knob without blinking, her ears pricked, rises an inch "
     "onto her front paws and sits straight again as she says the line, her tail tip twitching on the mat", _N),

 2: (10, "Medium shot in the living room from the front: the stocky man sits on the small sofa at screen-centre in "
     "three-quarter profile holding a white mug, his laptop closed on the desk behind him at screen-left; at the far "
     "right edge the small dog sits on the doormat facing the front door, seen from the side",
     ["bro", "mimi_d"], "living", T_EVE,
     "the stocky man in the navy blazer, amused and tired, looks across the room toward the doormat at the right, "
     "lifts his mug toward her as he teases, and points with his thumb over his shoulder toward the kitchen on the last "
     "words; the small dog at the far right edge, silent, keeps staring at the door without turning her head", _N),

 3: (10, "Medium close shot at floor level from the front: the small dog sits on the woven doormat at screen-right in "
     "three-quarter profile, her face turned toward the front door at the far right edge, her whole face and moving "
     "mouth visible",
     ["mimi_d"], "living", T_EVE,
     "the small dog, excited and squeaking, snaps both ears up and leaps to her feet with her tail whipping, staring at "
     "the door, then slowly sinks back down with her ears drooping and her tail slowing, and says the last words "
     "resigned but brave", _N),

 4: (10, "Medium shot in the dining and kitchen area from the front: the woman stands at the counter at screen-centre "
     "ladling rice into a bowl, her body turned three-quarter toward screen-left and her face looking over her shoulder "
     "toward the living room beyond the left edge, and she talks toward it",
     ["mom_h"], "dining", T_EVE,
     "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green floral sarong "
     "showing at her knees, sweet and dreamy, scoops steaming rice into a bowl with a big steel spoon and glances back "
     "over her shoulder with a gentle half-smile, nodding proudly on the last words", _N),

 5: (10, "Medium close shot at floor level from the front: the small dog sits on the woven doormat at screen-right, "
     "her head turned back over her shoulder toward the room at screen-left in three-quarter profile, her whole face and "
     "moving mouth visible; the closed front door stands at the far right edge behind her",
     ["mimi_d"], "living", T_EVE,
     "the small dog, gentle and firm, glances back over her shoulder at the unseen woman with a polite little smile, "
     "shakes her head once, and turns her face straight back to the door on the last words with her chin lifted", _N),

 6: (10, "Medium shot in the living room from the front: the stocky man crouches on the doormat at screen-right and sets "
     "a bowl down in front of the small dog, his face in three-quarter profile turned toward her, the closed front door "
     "behind them at the far right edge",
     ["bro", "mimi_d"], "living", T_EVE,
     "the stocky man in the navy blazer, teasing and puzzled, sets down " + _BOWL + " in front of the small dog with "
     "both hands, pats the floor beside it and talks to her with a half-grin; the small dog sits upright with her eyes "
     "on the door, not looking at the bowl, silent, the bowl untouched", _N),

 7: (10, "Close shot at floor level from the front: the small dog sits on the woven doormat at screen-right with the "
     "full bowl of rice untouched beside her, her face in three-quarter profile turned toward the front door, her whole "
     "face and moving mouth visible, whispering",
     ["mimi_d"], "living", T_EVE,
     "the small dog, whispering and tender, glances at the knob and then at the dark empty doorway, lowers her gaze "
     "shyly, then lifts her eyes to the door again with a soft smile as she says the line", _N),

 8: (10, "Medium shot in the living room from the front: the stocky man sits back on the small sofa at screen-centre in "
     "three-quarter profile, one arm along the sofa back; at the far right edge the small dog sits on the doormat "
     "facing the door with the full bowl untouched beside her",
     ["bro", "mimi_d"], "living", T_EVE,
     "the stocky man in the navy blazer, sighing and muttering, shrugs both shoulders, shakes his head and waves one hand "
     "dismissively toward the doormat on the last words; the small dog at the far right edge, silent, lowers her ears "
     "a little but keeps her eyes on the door", _N),

 9: (10, "Close shot at floor level from the front: the small dog sits on the woven doormat at screen-right with the "
     "full bowl untouched beside her, her face in three-quarter profile turned toward the front door, her whole face "
     "and moving mouth visible, her eyes wet",
     ["mimi_d"], "living", T_EVE,
     "the small dog, wounded and whimpering, keeps her eyes fixed on the door with big shining wet eyes, her ears sinking "
     "and her chin trembling, swallows and gives one small brave nod on the last words while she says the line", _N),

 10: (10, "Medium shot in the living room from the front: the woman stands at the dining threshold at screen-centre-"
      "right with a dish towel in her hands, her head tilted toward the front door at the far right edge; the stocky man "
      "sits on the small sofa at screen-left of her; the small dog on the doormat at the far right edge has her ears "
      "shot up",
      ["mom_h", "bro", "mimi_d"], "living", T_EVE,
      "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green floral "
      "sarong showing at her knees, surprised and soft, tilts her head toward the door, listening, then turns her face "
      "to the stocky man and nods at the door on the last words; the stocky man in the navy blazer looks up from his "
      "mug; the small dog, silent, springs up onto all four paws facing the door", _N),

 11: (10, "Medium wide shot in the living room from the front: the wooden front door at the far right edge swings "
      "open; the slim woman steps in through it and walks toward screen-left across the room, her face in three-quarter "
      "profile turned forward and slightly down toward the corridor at the far left edge, never toward the small dog; "
      "the small dog stands on the doormat at the far right edge by the open door",
      ["sis", "mimi_d"], "living", T_EVE,
      "the slim woman in the white blouse, tired and crisp, kicks the door shut behind her with one heel, drops her black "
      "shoulder bag on the sofa arm as she walks and rubs the back of her neck, speaking toward nobody in particular "
      "and not looking down once; the small dog on the doormat, silent, bounces on her toes with her whole body "
      "wagging as the woman walks straight past her", _N),

 12: (10, "Medium wide shot in the living room from the front: the small dog bounds from the doormat at screen-right "
      "toward screen-left right behind the slim woman, who walks away from the camera toward the dark corridor at the "
      "far left edge, her back and ponytail to us; the small dog's whole face and moving mouth visible as she looks "
      "up at the woman's back",
      ["mimi_d", "sis"], "living", T_EVE,
      "the small dog, overjoyed and squealing, bounces on her hind legs trailing the woman, her tail whirling and her "
      "eyes shining, speaking up at the woman's back; the slim woman in the white blouse, silent, keeps walking "
      "toward the corridor without turning her head", _N),

 13: (10, "Medium shot in the living room from the front: the stocky man sits forward on the small sofa at screen-left "
      "in three-quarter profile, his eyes on the doormat at the far right edge where the full bowl of rice sits "
      "untouched and the small dog stands beside it; the corridor at the far left edge is empty",
      ["bro", "mimi_d"], "living", T_EVE,
      "the stocky man in the navy blazer, slowly realising and soft, looks from the full bowl to the small dog and back, "
      "sets his mug down on the sofa arm, his eyes widening and his mouth falling open a little as he speaks; the "
      "small dog stands by the bowl at the far right edge, silent, with her head tilted", _N),

 14: (10, "Medium close shot in the living room from the front: the woman stands at screen-centre holding the dish "
      "towel against her chest, her face in three-quarter profile turned toward the doormat at the right where the small "
      "dog sits beside the full bowl, and she talks to her",
      ["mom_h", "mimi_d"], "living", T_EVE,
      "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green floral "
      "sarong showing at her knees, voice breaking and tender, dabs the corner of her eye with the dish towel and "
      "presses her other hand to her heart as she speaks; the small dog on the doormat at the right edge, silent, looks "
      "back at her with her head tilted", _N),

 15: (10, "Medium shot at floor level on the doormat from the front: the stocky man crouches at screen-centre facing "
      "the small dog who sits at screen-right beside the full bowl, his face in three-quarter profile turned toward "
      "her, his hand resting on the floor",
      ["bro", "mimi_d"], "living", T_EVE,
      "the stocky man in the navy blazer, humbled and gentle, bows his head a little toward the small dog as he says "
      "the line and then rests one hand lightly on the floor beside her paw; the small dog sits very still with her "
      "ears up, silent", _N),

 16: (10, "Medium wide shot in the living room from the front: the slim woman stands at the dark corridor opening at "
      "the far left edge with her black shoulder bag in one hand, her body half turned back toward the room, her face "
      "turned toward the stocky man who sits on the small sofa at screen-centre-left; at the far right edge the small "
      "dog sits on the doormat beside the full bowl with her ears up, listening",
      ["sis", "bro", "mimi_d"], "living", T_EVE,
      "the slim woman in the white blouse, gruff and brisk, jerks her chin toward the doormat without looking at it, "
      "talks to the stocky man only, then turns and walks into the corridor on the last words with her back to the "
      "camera; the stocky man in the navy blazer nods, silent; the small dog at the far right edge, silent, never "
      "takes her eyes off the woman", _N),

 17: (10, "Close shot at floor level from the front: the small dog sits on the woven doormat at screen-right in "
      "three-quarter profile with the full bowl of rice in front of her, her whole face and moving mouth visible, her "
      "tail wagging against the straw",
      ["mimi_d"], "living", T_EVE,
      "the small dog, giddy and relieved, spins in a happy circle, tucks her muzzle into the bowl and lifts it again "
      "with a grain of rice stuck to her beard, her tail wagging hard as she says the line", _N),

 18: (10, "Medium wide shot in the living room from the front: the small dog sits on the doormat at screen-right with "
      "the empty bowl in front of her, her head turned toward screen-left in three-quarter profile toward the stocky man "
      "and the woman who sit on the floor beside her, her whole face and moving mouth visible; the front door stands "
      "closed at the far right edge",
      ["mimi_d", "bro", "mom_h"], "living", T_EVE,
      "the small dog, cheeky and sleepy, licks her chops with her tongue out, pats the floor beside her with one paw "
      "to invite them and yawns on the last words; the stocky man in the navy blazer and the woman with the wooden "
      "ladle in her bun, both sitting cross-legged on the floor beside her, smile and nod, silent", _N),
}

_NAME = {"mimi_d": "มีมี่", "mom_h": "แม่", "bro": "พี่ชาย", "sis": "น้องสาว"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep5-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

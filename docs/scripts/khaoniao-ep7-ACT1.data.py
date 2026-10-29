# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP7 «ทำไมมีมี่ไม่ยอมนอนกับแม่ ต้องรอพี่ชายกลับดึก?» — 12 shots
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep6-ACT1.data.py).

CEO 2026-10-14 (chat): option 3 = the short episode of 12 shots, about 180 credits; airs Sun 18 Oct 19:30.
Real facts from the CEO the same day (story bible §1): Mimi will not sleep with Mother; behind the closed bedroom
door she cries and sits at it, scratches it softly with a paw so only the brother hears, and waits until the brother
gets home at 2-3 a.m. after a film; her brown cushion bed is in the brother's room; she snores loudly asleep. Riao
(the sister's cat, male, neutered, sleepy, speaks in a man's warm slow sleepy voice) sleeps in the sister's room; the
brother lets no cat into his room. The sister and the father are NOT in this episode.
Dialogue and manner tags are read from docs/scripts/khaoniao-ep7-SCRIPT-v1.md at import time.

Plates: REUSED as they are: mimi__dry, brother__wfh. NEW (one-off free stills, made with the ChatGPT runner by
docs/reports/khaoniao-family-style/build_ep7_plates.py): mother__night, cat__riao (from sheet-riao-v1, 2026-10-14),
loc__living_night (night needs its own plate), loc__momroom_night, loc__landing_night, loc__broroom_night.

Direction plan (CMO_Standard_Film_PromptFormat rule 12): mother's room: the door at the FAR LEFT edge, the bed at
screen-RIGHT with the bedside lamp; Mimi faces screen-LEFT toward the door. Living room (as EP5/EP6): the wooden
front door at the FAR RIGHT edge, the dark corridor to the bedrooms at the FAR LEFT edge: Mimi leaves the mother's room
toward screen-LEFT and runs through the living room toward screen-RIGHT. Upstairs landing: the stairs at screen-LEFT,
the sister's door at screen-centre-left, the brother's door at screen-RIGHT. Brother's room: the bed at screen-left, the
brown round cushion on the floor at screen-right. Mimi never talks to the viewer; the humans do not understand her;
Riao and Mimi do understand each other.
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
_MOM = ("a plump Thai woman in her fifties with a round rosy face and a kind half-closed sleepy smile, "
        "grey-black hair in a loose low bun with no ladle in it, a gold amulet necklace, a soft pale-blue "
        "short-sleeved floral pyjama top and matching long pyjama trousers, bare feet")

# key: (handle, full appearance block written from the plate, short reference = the speaker's name)
CHAR = {
 "mimi_d": ("@mimi__dry", _MIMI + ", her fur dry and fluffy", "The small black dog"),
 "mom_n": ("@mother__night", _MOM, "The woman in the pale-blue floral pyjamas"),
 "bro": ("@brother__wfh",
   "a stocky Thai man of thirty with a chubby face, square black-rimmed glasses and slicked-back "
   "black hair, wearing a navy double-breasted blazer with gold buttons over a white shirt and a "
   "blue patterned tie, blue elephant-print shorts, blue flip-flops and a gold wristwatch",
   "The stocky man in the navy blazer"),
 "cat": ("@cat__riao",
   "a fluffy long-haired male cat with a pale cream and white coat, soft golden-apricot patches on the top of the "
   "head, ears, back and a giant feather-duster plume tail, a white chest, muzzle and four white paws, a flat round "
   "face with a tiny flat pink nose, big round dark eyes with heavy sleepy half-closed lids and small rounded ears, "
   "a very round chubby loaf-shaped body on short stubby legs, with no collar",
   "The fluffy cream-and-apricot cat"),
}

WARDROBE = {}   # every plate is already the whole character in that state

# Timbre, pitch and age ONLY (CMO_Standard_Story_ThaiMoralDrama §Emotion rule 3). Same words as EP1 / EP6.
_V = "(prompt only, no bound voice)"
VOICE = {
 "mimi_d": (_V, "the small, sweet, high-pitched voice of a young girl"),
 "mom_n": (_V, "the warm, slow, slightly nasal voice of a Thai woman in her late fifties"),
 "bro": (_V, "the smooth, mid-low baritone voice of a Thai man of thirty"),
 "cat": (_V, "the warm, slow, sleepy, mid-low voice of a lazy Thai man"),
}

_HOUSE = ("the same Thai townhouse: cream marble floor tiles, a wooden door frame, potted plants, "
          "warm wood furniture")
LOC = {
 "momroom": ("@loc__momroom_night",
   "the mother's bedroom at night in " + _HOUSE + ": a double bed with a cream floral bedspread and two pillows at "
   "screen-right, a small bedside lamp on a wooden table glowing a dim warm orange, a wooden wardrobe against the "
   "back wall, a closed wooden bedroom door at the far left edge, cream marble floor, with no mirror and no pictures on "
   "the walls"),
 "living": ("@loc__living_night",
   "the living room at night in " + _HOUSE + ": a work-from-home desk beside a window at screen-left with the "
   "curtains drawn, a tidy small sofa in the middle, a round coffee table, a small round dog bed in a corner, a wooden "
   "shelf with plants, the dark dining area behind at screen-right, a wooden front door at the far right edge of the "
   "room with a woven straw doormat in front of it and a low wooden shoe rack beside it, and a dark corridor to the "
   "bedrooms at the far left edge with one closed bedroom door visible in it; the only light is one dim warm lamp on "
   "the shelf and a faint blue glow from the window"),
 "landing": ("@loc__landing_night",
   "the upstairs landing at night in " + _HOUSE + ": a dark wooden stair banister at screen-left where the stairs go "
   "down, cream marble floor, two closed white wooden doors, one at screen-centre-left with a small straw mat in front "
   "of it and one at screen-right, lit by a single dim warm night-light on the wall"),
 "broroom": ("@loc__broroom_night",
   "a tidy young man's bedroom at night in " + _HOUSE + ": a single bed with a grey sheet and one pillow at "
   "screen-left, a small wooden desk with a closed laptop at the back wall, a window with a closed blue curtain, "
   "and a round soft brown cushion dog bed on the floor against the wall at screen-right, with no mirror and no "
   "pictures on the walls; the only light is a dim warm bedside lamp and a faint blue glow from the window"),
}

NOT = {
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear anywhere in the "
           "frame.",
 "noother": "Only the named characters appear: no other person and no other animal is visible "
            "anywhere in the frame.",
 "noscreen": "The laptop is closed and no screen shows any face, picture or text.",
 "nopics": "No framed pictures or photographs hang on any wall or stand on any shelf.",
 "nonumber": "No house number, no plaque and no sign appears on any door or anywhere else in the frame.",
 "nomirror": "There is no mirror and no reflective glass anywhere in the frame.",
 "nobrand": "No logo and no brand name or lettering appears on any object, cup or clothing.",
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}

T_NIGHT = ("two o'clock at night, a dim warm orange lamp glow in a dark room with soft blue shadows, low-key "
           "cinematic night lighting")
_N = ["nosubs", "noother", "nopics", "nonumber", "nomirror", "nobrand"]
_POP = "a small paper cup of popcorn with no printing on it"

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Medium close shot at floor level in the mother's bedroom from the front: the small dog sits very upright at "
     "screen-centre-left right beside the closed wooden door at the far left edge, in three-quarter profile with her "
     "face turned toward the door, her whole face and moving mouth visible from the first frame, one front paw lifted "
     "and resting on the lower edge of the door; she never looks at the camera",
     ["mimi_d"], "momroom", T_NIGHT,
     "the small dog, whispering and restless, scratches the door with her front paw in tiny soft taps, her ears "
     "drooping, her head tilted to the side, and says the line in a hushed small voice, ending with a little sigh and a "
     "soft whine", _N),

 2: (10, "Medium shot in the mother's bedroom from the front: the woman sits on the edge of the double bed at screen-right "
     "in three-quarter profile with her face turned toward screen-left, patting the bedspread beside her with one hand; "
     "the small dog sits by the closed door at the far left edge with her back half-turned, silent",
     ["mom_n", "mimi_d"], "momroom", T_NIGHT,
     "the woman in the pale-blue floral pyjamas, wistful and sleepy, pats the empty spot on the bedspread twice, tilts "
     "her head with a tired hurt little smile and rubs one eye as she says the line toward the small dog; the small dog "
     "by the door, silent, glances back at her once and turns her nose back to the door", _N),

 3: (10, "Medium close shot at floor level in the mother's bedroom from the front: the small dog sits at the closed door at "
     "screen-left with her body toward the door and her head turned back over her shoulder toward screen-right in "
     "three-quarter profile, her whole face and moving mouth visible, the lamp-lit bed at the far right edge",
     ["mimi_d"], "momroom", T_NIGHT,
     "the small dog, soft and patient, looks back at the unseen woman on the bed with big kind eyes, says the line in a "
     "gentle small voice, then turns her head back to the door and lies down with her chin on her front paws",
     _N),

 4: (10, "Medium shot at floor level in the dark living room from the front: the fluffy cat sits like a loaf in the "
     "dark corridor mouth at the far left edge, in three-quarter profile with his face turned toward the closed bedroom "
     "door at the far left edge of the frame, his whole face and moving mouth visible, his huge tail curled around his "
     "feet",
     ["cat"], "living", T_NIGHT,
     "the fluffy cream-and-apricot cat, drowsy and lazy, talks to the closed door with his eyes half shut, flicks one "
     "ear, slowly stretches one front paw forward, and on the last words yawns very wide and turns around to pad away "
     "toward screen-right, his plume tail swaying", _N),

 5: (10, "Medium close shot at floor level in the mother's bedroom from the front: the small dog sits at the closed door at "
     "screen-left in three-quarter profile with her face turned toward the door, her whole face and moving mouth visible; "
     "at the far right edge the woman lies asleep on her side on the bed under the cream bedspread, her eyes closed",
     ["mimi_d", "mom_n"], "momroom", T_NIGHT,
     "the small dog, whispering and thrilled, shoots both ears straight up, her head snapping toward the door, her nose "
     "twitching and her whole body quivering, then she rises onto all four paws with her tail wagging and says the line in "
     "a thrilled hush; the sleeping woman, silent, breathes slowly and does not move", _N),

 6: (10, "Medium shot in the mother's bedroom from the front: the woman stands at the open wooden door at the far left "
     "edge holding the door knob, in three-quarter profile with her face turned down toward the small dog at her feet; the "
     "small dog stands at her feet facing screen-left toward the dark corridor beyond the open door",
     ["mom_n", "mimi_d"], "momroom", T_NIGHT,
     "the woman in the pale-blue floral pyjamas, sleepy and soft, her hair a little messy, rubs her eye with the back of "
     "her wrist, tilts her head as she says the line to the dog, and opens the door wide with a small smile; the small "
     "dog at her feet, silent, trembles with excitement and darts out through the open door toward screen-left the "
     "moment it opens", _N),

 7: (10, "Medium wide shot in the dark living room from the front: the stocky man stands just inside the wooden front door "
     "at the far right edge holding " + _POP + " in one hand and the door in the other, in three-quarter profile with his "
     "face turned down toward screen-left; the small dog charges in from the dark corridor at the far left edge across the "
     "marble floor toward him and jumps up against his knees",
     ["bro", "mimi_d"], "living", T_NIGHT,
     "the stocky man in the navy blazer, tired and touched, slides his flip-flops off, bends down with his free hand "
     "toward the dog and ruffles her ears while he says the line in a hushed voice, then glances toward the dark corridor "
     "and gives a tired smile; the small dog, silent, wags her whole body and licks his hand",
     _N),

 8: (10, "Medium wide shot in the dark living room from the front: the woman stands in the dark corridor mouth at the far "
     "left edge in her pyjamas, in three-quarter profile with her face turned toward screen-right; at screen-centre-right "
     "the stocky man crouches beside the small dog, who leans against his knee, both facing screen-left toward her",
     ["mom_n", "bro", "mimi_d"], "living", T_NIGHT,
     "the woman in the pale-blue floral pyjamas, realising and tender, leans one shoulder against the door frame with her "
     "hand over her heart, shakes her head slowly with a soft smile and says the line toward the two of them; the stocky "
     "man in the navy blazer, silent, looks up at her and nods; the small dog, silent, leans on his knee with her eyes "
     "on the woman", _N),

 9: (10, "Medium wide shot on the upstairs landing from the front: the stocky man stands at the closed brother's door at "
     "screen-right with one hand on the door handle, in three-quarter profile with his face turned down toward the small "
     "dog at his feet; the small dog sits at his feet looking up at him; at screen-left in front of the closed door with "
     "the straw mat the fluffy cat lies curled up asleep",
     ["bro", "mimi_d", "cat"], "landing", T_NIGHT,
     "the stocky man in the navy blazer, soft and drained, pushes the door open with his foot and sweeps one hand toward "
     "the dark room inside as he says the line down to the dog, with a sleepy kind smile; the small dog at his feet, "
     "silent, wags her tail slowly and looks into the room; the fluffy cat at screen-left, silent, sleeps curled around "
     "his own plume tail and twitches one ear", _N),

 10: (10, "Medium close shot at floor level in the brother's bedroom from the front: the small dog lies curled up on the "
      "round soft brown cushion on the floor at screen-right with her chin on its edge, in three-quarter profile facing "
      "screen-left, her whole face and moving mouth visible, her eyes half closed",
      ["mimi_d"], "broroom", T_NIGHT,
      "the small dog, drowsy and content, turns around once on the brown cushion, flops down with a long sigh, and says "
      "the line slowly in a sleepy small voice, her eyelids sinking lower on every word, until her eyes close on the last "
      "word and her tail stops wagging", _N),

 11: (10, "Medium shot in the brother's bedroom from the front: the stocky man sits on the edge of the single bed at "
      "screen-left in three-quarter profile with his face turned toward screen-right, a hand over his mouth, looking down "
      "at the small dog asleep on the round brown cushion on the floor at screen-right",
      ["bro", "mimi_d"], "broroom", T_NIGHT,
      "the stocky man in the navy blazer, chuckling and fond, presses his fist to his mouth to hold in a laugh, shakes "
      "his head and says the line in a low whisper; the small dog on the cushion, silent, lies on her side asleep with "
      "her mouth a little open, her whole body rising and falling and a loud rumbling snore coming from her on every "
      "breath", _N),

 12: (10, "Medium shot in the dark living room from the front: the woman stands in the dark corridor mouth at the far left "
      "edge with one hand on the half-closed bedroom door, in three-quarter profile with her face turned toward screen-right "
      "toward the stairs beyond the right edge of the frame, and she talks toward them",
      ["mom_n"], "living", T_NIGHT,
      "the woman in the pale-blue floral pyjamas, warm and sleepy, listens with her head tilted toward the faint rumbling "
      "snore from upstairs, smiles softly, says the line gently toward the stairs, and then slips into her bedroom and "
      "closes the door softly behind her", _N),
}

_NAME = {"mimi_d": "มีมี่", "mom_n": "แม่", "bro": "พี่ชาย", "cat": "เรียว"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep7-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

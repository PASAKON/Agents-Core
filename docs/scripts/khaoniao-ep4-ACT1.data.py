# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP4 «ทำไมมีมี่ลากพี่ชายออกไปเดินทุกครั้งที่เขาประชุมซูมไม่หยุด?» — 18 shots
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep3-ACT1.data.py).

CEO 2026-10-02: "ทำ EP3-EP5 ต่อได้เลย" + OK on the EP4 concept and on <=330 credits per episode.

The dialogue and its manner tag are NOT typed here: they are read from
docs/scripts/khaoniao-ep4-SCRIPT-v1.md at import time, so the script the CEO reads and the prompts the
runner fires can never disagree. This file adds only what the script does not carry: who is in each shot, where,
the time of day, the English action with its emotion, and the negatives.

Plates (Assets/Agents/Core/khaoniao-family/plates/): all reused as they are — mimi__dry, mother__home,
brother__wfh, loc__living, loc__dining. No new plate: the covered lunch plate, the cold mug, the round dog bed
and the front door are words only (written into the living-room set so every shot carries them). The sister, Ryo
and the seller are NOT in this episode.

Direction plan (CMO_Standard_Film_PromptFormat rule 12; CMO_Standard_Story_FamilyDogSeries §2.8): the desk
(brother, laptop screen facing AWAY from the camera) is at screen-LEFT of the living room beside the window, the sofa
in the middle, the round dog bed on the floor beside the desk, the open dining area and the wooden front door at
screen-RIGHT. Everyone who goes out walks toward screen-RIGHT, away from the camera. The mother stands in the dining
area and talks over her shoulder toward screen-left; she enters the living room from the right. Mimi never talks to the
viewer: the humans do not understand her. The brother stays SEATED until shot 12 (he bends from the chair in shot 6).
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
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}


LOC["living"] = (LOC["living"][0], LOC["living"][1] + ", on the desk beside the laptop a plate of rice with a fried egg "
  "and a bowl of clear soup under a clear plastic cover stands full and untouched next to a white mug of coffee gone "
  "cold, a small round pink dog bed lies on the floor beside the desk, and the wooden front door stands closed at the "
  "far right edge of the room")

T_AFT = "a warm late afternoon, low golden sunlight slanting through the window across the cream marble floor"
_N = ["nosubs", "noother", "noscreen", "nopics"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Medium shot in the living room from the front: the stocky man sits at the desk at screen-left turned "
     "three-quarter toward us with a white earbud in one ear, his eyes on the laptop; the small dog stands beside "
     "his chair at screen-centre-left in side profile facing screen-left up at him, her whole face and moving mouth "
     "visible from the first frame; she never looks at the camera",
     ["mimi_d", "bro"], "living", T_AFT,
     "the small dog, urgent and squeaking, hooks one front paw under the strap of the man's blue flip-flop and "
     "tugs it, then pats his shin, her tail wagging hard and her eyes huge, saying the whole line up at him; the "
     "stocky man in the navy blazer types at the laptop and nods at the call, one hand cupping his earbud, not "
     "looking down at her", _N),

 2: (10, "Medium close shot at the desk from the front: the stocky man sits at screen-centre in three-quarter "
     "profile with a white earbud in one ear, his eyes on the laptop whose back lid faces us at screen-left, the "
     "covered plate and the cold mug at the desk edge in front of the laptop, the top of the small dog's head just "
     "visible at the bottom-right edge pawing at his foot",
     ["bro", "mimi_d"], "living", T_AFT,
     "the stocky man in the navy blazer, hurried and polite, nods at the laptop and speaks to the call in a "
     "hushed voice, then glances down toward screen-right and points one finger at the small dog on the last "
     "words, whispering sharply; the small dog's ears and eyes show at the bottom edge, silent",
     _N),

 3: (10, "Medium close shot at floor level beside the desk from the front: the small dog sits at screen-centre "
     "with her head turned up toward screen-left, in three-quarter profile, at the desk edge where the covered "
     "plate and the cold mug stand, her whole face and moving mouth visible; the man's legs are out of frame",
     ["mimi_d"], "living", T_AFT,
     "the small dog, pleading and worried, looks up at the covered plate and the cold mug, then up toward the man "
     "out of frame at the left, her forehead creased and her ears drooping, patting the air with one front paw "
     "on the last words while she says the line", _N),

 4: (10, "Medium shot in the dining and kitchen area from the front: the woman stands at the counter at "
     "screen-centre stirring a steaming pot, her body turned three-quarter toward screen-left and her face "
     "looking over her shoulder toward the living room beyond the left edge, and she talks toward it",
     ["mom_h"], "dining", T_AFT,
     "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green "
     "floral sarong showing at her knees, sweet and dreamy, stirs a steaming pot with a big steel spoon and glances "
     "back over her shoulder with a gentle half-smile, shaking her head a little while she speaks toward the "
     "unseen dog", _N),

 5: (10, "Medium shot in the living room from the front at floor level: the small dog stands at screen-centre "
     "between the desk at screen-left and the dining area at screen-right, her head turned toward screen-right in "
     "three-quarter profile with her whole face and moving mouth visible, answering the woman; on the last words "
     "she turns toward screen-left to the desk",
     ["mimi_d"], "living", T_AFT,
     "the small dog, earnest and squeaking, faces screen-right and speaks up to the unseen woman with her "
     "chest puffed out, then turns and rears up with her front paws on the side of the man's chair at the left "
     "edge and tugs the strap of his flip-flop again, her tail wagging, finishing the line", _N),

 6: (10, "Medium shot in the living room from the front: the stocky man, still seated in his chair at "
     "screen-left, leans down from the chair toward screen-right in three-quarter profile, scoops the small dog up "
     "with both hands and sets her gently into the round pink dog bed on the floor at screen-centre, looking "
     "down at her while he talks",
     ["bro", "mimi_d"], "living", T_AFT,
     "the stocky man in the navy blazer, firm and tired, wearing a white earbud, lifts the small dog gently with "
     "both hands and sets her down in the round pink dog bed, then wags one finger at her and turns back to the "
     "laptop on the last words; the small dog, set down in the bed, sits with her ears flat and her mouth "
     "shut, silent, staring after him", _N),

 7: (10, "Medium close shot at floor level from the front: the small dog sits in the round pink dog bed at "
     "screen-centre with her face in three-quarter profile turned up toward screen-left where the man sits out "
     "of frame, her whole face and moving mouth visible, whispering",
     ["mimi_d"], "living", T_AFT,
     "the small dog, worried and whispering, glances up toward the man's chair at the left edge and then at her "
     "own front paws, counting with little dips of her head and then lifting her chin with a stubborn, resolute "
     "look on the last words while she speaks", _N),

 8: (10, "Medium close shot at the desk from the front: the stocky man sits at screen-centre in three-quarter "
     "profile with a white earbud in one ear, looking at the laptop whose back lid faces us at screen-left; the "
     "round pink dog bed at the bottom-right edge with the small dog's head just visible in it",
     ["bro", "mimi_d"], "living", T_AFT,
     "the stocky man in the navy blazer, embarrassed and polite, leans toward the laptop with an apologetic "
     "smile, rolls his eyes toward screen-right at the dog bed on the word dog, then taps the desk beside the "
     "laptop to mute it on the last words; the small dog's head shows at the bottom edge, ears flat, silent",
     _N),

 9: (10, "Close shot at floor level from the front: the small dog sits in the round pink dog bed at "
     "screen-centre, her face in three-quarter profile turned up toward screen-left, her whole face and moving mouth "
     "visible, her eyes wet",
     ["mimi_d"], "living", T_AFT,
     "the small dog, wounded and whimpering, looks up toward the man at the left edge with big shining wet eyes, "
     "her ears sinking and her chin trembling, then drops her gaze to her paws on the last words while she says the "
     "line", _N),

 10: (10, "Medium wide shot in the living room from the front: the small dog stands up in the round pink dog bed "
      "at screen-centre and trots to the man's feet at the desk at screen-left; at the end she bolts toward "
      "screen-right toward the front door with a blue flip-flop in her mouth",
      ["mimi_d", "bro"], "living", T_AFT,
      "the small dog, determined and mischievous, climbs out of the bed, trots to the man's chair at the left and "
      "says the first half of the line looking up at him, then tugs his blue flip-flop off his foot, grips it by the "
      "strap in her teeth and bolts toward screen-right, saying the last words muffled; the stocky man in the "
      "navy blazer sits with his eyes on the laptop, one hand on his earbud, not noticing", _N),

 11: (10, "Medium shot at the desk from the front: the stocky man at screen-left pushes his chair back and rises "
      "halfway with both hands flat on the desk, one foot bare, his face in three-quarter profile turned toward "
      "screen-right, looking at the small dog bounding away toward the front door at the far right edge of the "
      "frame, and he talks to her",
      ["bro", "mimi_d"], "living", T_AFT,
      "the stocky man in the navy blazer, startled and alarmed, taps the desk to mute the laptop, pulls out his "
      "earbud and half-rises with his bare foot on the cool floor, pointing toward screen-right and calling after the "
      "small dog; the small dog, tiny in the far right of the frame, trots away with his blue flip-flop in her "
      "mouth, silent", _N),

 12: (10, "Medium full-length shot in the living room from the front: the stocky man stands up straight for the "
      "first time at screen-left beside the desk, one blue flip-flop on and one foot bare; at the far right edge the "
      "small dog stands at the closed front door looking back at him with the flip-flop in her mouth",
      ["bro", "mimi_d"], "living", T_AFT,
      "the stocky man in the navy blazer and blue elephant-print shorts, groaning and stiff, unfolds from the "
      "chair with a loud dry crack of his back and a creak of his knees, both hands pressed to the small of his "
      "back, his knees wobbling like a rusty robot and his face scrunched in surprise while he speaks; the small "
      "dog at the far right edge, silent, watches him with her ears up and the flip-flop in her mouth", _N),

 13: (10, "Medium shot in the living room from the front: the woman walks in from screen-right to the desk at "
      "screen-left and holds up the full covered plate of rice, her face in three-quarter profile turned toward "
      "screen-left to the man who stands rubbing his back at the left edge, and she talks to him",
      ["mom_h", "bro"], "living", T_AFT,
      "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green "
      "floral sarong showing at her knees, soft and realising, lifts the full covered plate of rice from the desk "
      "and holds it up toward the man with one hand on her heart, her eyes shining and her voice breaking, then "
      "points toward the front door on the last words; the stocky man at the left edge keeps both hands on his "
      "lower back", _N),

 14: (10, "Medium close shot in the living room from the front: the stocky man stands at screen-centre with one "
      "hand on his lower back, his face in three-quarter profile turned toward screen-right where the small dog "
      "stands at the far right edge by the front door, and he talks to her",
      ["bro", "mimi_d"], "living", T_AFT,
      "the stocky man in the navy blazer, humbled and gentle, looks at the full plate in the woman's hand at the "
      "left edge and then across at the small dog, his eyes glistening, pressing the back of his hand to one eye "
      "and then lowering it as he speaks; the small dog at the far right edge, silent, sits very still with the "
      "blue flip-flop in her mouth and her head tilted", _N),

 15: (10, "Medium shot in the living room from the front at floor level: the small dog trots from the far right "
      "edge toward screen-left to the man's bare foot at screen-left and sits, her face in three-quarter profile "
      "turned up toward screen-left, her whole face and moving mouth visible, and she talks up to him",
      ["mimi_d", "bro"], "living", T_AFT,
      "the small dog, cheeky and relieved, trots across the floor, drops the blue flip-flop neatly beside the "
      "man's bare foot and sits wagging her whole body with her tongue out, then pats the flip-flop with one paw "
      "on the last words while she says the line; the stocky man in the navy blazer at the left edge looks down at "
      "her with a soft smile, silent", _N),

 16: (10, "Medium close shot in the living room from the front: the woman stands at screen-centre holding the "
      "covered plate against her chest, her face in three-quarter profile turned toward screen-left toward the man at "
      "the left edge, and she talks to him while shooing toward screen-right",
      ["mom_h", "bro"], "living", T_AFT,
      "the woman with the wooden ladle in her bun and the tartan cloth over her shoulder, her pink-and-green "
      "floral sarong showing at her knees, laughing and warm, shoos with her free hand toward screen-right and the "
      "front door, tapping the air as if tapping a tiny laptop on the word meeting; the stocky man in the navy "
      "blazer at the left edge nods, silent", _N),

 17: (10, "Medium shot in the living room from the front at low height: the stocky man at screen-left leans "
      "carefully on the desk with one hand and slips his bare foot into the blue flip-flop, his face in "
      "three-quarter profile turned toward screen-right to the small dog who sits at screen-centre looking up at "
      "him, and he talks to the dog",
      ["bro", "mimi_d", "mom_h"], "living", T_AFT,
      "the stocky man in the navy blazer and blue elephant-print shorts, warm and amused, slides his foot into the "
      "flip-flop with a small wince and a soft laugh, straightens one hand on his back, and offers the small dog "
      "a fist-bump of his knuckles on the last words; the small dog sits wagging at screen-centre, silent, and the "
      "woman with the wooden ladle in her bun waits smiling at the right edge, holding the plate", _N),

 18: (10, "Medium wide shot in the living room from the front: the wooden front door at the far right edge stands "
      "wide open to golden sunlight; the small dog bounces on the threshold at screen-right, her head turned toward "
      "screen-left in three-quarter profile toward the man who walks toward her from screen-left, her whole face "
      "and moving mouth visible, and at the end she runs out through the door toward screen-right with him following",
      ["mimi_d", "bro", "mom_h"], "living", T_AFT,
      "the small dog, cheeky and giggling, bounces on the doorstep in the golden light with her tail whirling, "
      "says the line looking back at the man and then bolts out through the open door toward screen-right on the "
      "last words; the stocky man in the navy blazer, one hand on his back, walks toward her in his blue "
      "flip-flops laughing and follows her out; the woman with the wooden ladle in her bun waves from the "
      "dining area at the back, smiling", _N),
}

_NAME = {"mimi_d": "มีมี่", "mom_h": "แม่", "bro": "พี่ชาย"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep4-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

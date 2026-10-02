# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP3 «ทำไมมีมี่อาบน้ำเสร็จ ถึงไม่ยอมสะบัดตัว แต่ต้องกลิ้งทับผ้าไปมาแทน?» — 18 shots x 10 s = 3:00.
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep2-ACT1.data.py).

CEO 2026-10-02: "ทำ EP3-EP5 ต่อได้เลย" + the new fact (Mimi shivers in the bath, then rolls on a fluffy towel to dry
herself). Credits for EP3 wait on the CEO's number (script docs/scripts/khaoniao-ep3-SCRIPT-v1.md, §เครดิต).

The dialogue and its manner tag are NOT typed here: they are read from
docs/scripts/khaoniao-ep3-SCRIPT-v1.md at import time, so the script the CEO reads and the prompts the
runner fires can never disagree. This file adds only what the script does not carry: who is in each shot, where,
the time of day, the English action with its emotion, and the negatives.

Plates (Assets/Agents/Core/khaoniao-family/plates/): all reused as they are — mimi__dry, mimi__wet, mother__home,
brother__wfh, loc__living, loc__bathroom. No new plate: the big pink towel and the wicker basket of folded white
towels are words only (the basket is written into the living-room set so every shot carries it). The sister, Ryo and
the seller are NOT in this episode.

Direction plan (CMO_Standard_Film_PromptFormat rule 12; CMO_Standard_Story_FamilyDogSeries §2.8): the desk (brother)
is at screen-LEFT of the living room, the sofa in the middle, the wicker basket at the sofa's RIGHT end, the kitchen
and the bathroom lie to the RIGHT. Bathroom: doorway at screen-LEFT, basin at screen-RIGHT, so Mimi leaving the bath
goes toward screen-LEFT and then runs into the living room from screen-RIGHT to the towel at screen-centre. The brother
takes the towel off toward screen-RIGHT (the washing machine) and returns from the right. Mimi's dive into the
basket is toward screen-RIGHT. Mimi never talks to the viewer: the humans do not understand her.
Mimi's fur: S1-S2 wet and dripping with bubbles (@mimi__wet), S3 on damp and clumped but NOT dripping — the whole
episode turns on the floor staying dry.
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
 "feetonly": "Only a pair of pink slippered feet and the hem of a floral sarong reach into the top-right "
             "edge of the frame; no face and no other person is visible, and no other animal.",
 "nomimi": "The small dog is under the sofa out of sight: no dog is visible anywhere in the frame.",
 "nobath": "Nobody is bathing and no bathroom is visible in this shot.",
}

PROP_FOR_NOT = {}
PROPS_BY_SHOT = {}

LOC["living"] = (LOC["living"][0], LOC["living"][1] + ", the cream marble floor freshly mopped and shining, a wicker "
  "basket of neatly folded white towels standing at the right end of the small sofa")

T_DAY = "a bright late morning, warm natural daylight filling the house"
_N = ["nosubs", "noother"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Medium shot in the bathroom from the front: the small dog stands on the white bath mat at screen-centre, "
     "in side profile facing screen-left toward the open doorway, her whole face and moving mouth visible from "
     "the first frame; through the doorway a big soft pink towel lies spread flat on a glossy cream floor; she "
     "never looks at the camera",
     ["mimi_w"], "bath", T_DAY,
     "the small dog, soaking wet with a few white soap bubbles on her head and back, shivers violently from nose to "
     "tail with her cheeks puffed out and her eyes squeezed tight, her fur standing on end and her teeth "
     "chattering, gripping the bath mat with all four paws and visibly forcing herself not to shake the water "
     "off, while she says the whole line in a squeaky, determined voice, her gaze fixed through the doorway on "
     "the pink towel", _N),

 2: (10, "Medium shot in the bathroom from the front: the woman stands at screen-right beside the blue basin in "
     "three-quarter profile facing screen-left toward the open doorway, her eyes down on the small dog who stands "
     "on the bath mat at screen-left, and she talks to the dog",
     ["mom_h", "mimi_w"], "bath", T_DAY,
     "the woman with the wooden ladle in her bun and the tartan cloth still draped over her shoulder, her "
     "pink-and-green floral sarong showing at her knees, sweet and dreamy, dries her hands on the tartan cloth and "
     "smiles down at the dog, then presses a hand to the small of her back with a wince and a sigh while she "
     "speaks; a yellow plastic bucket with a mop standing in it waits by the doorway at screen-left; the small "
     "dog, soaking wet and trembling, stands on the bath mat looking up at her", _N),

 3: (10, "Medium wide shot in the living room from the front: a big soft pink towel lies spread flat on the glossy "
     "cream marble floor at screen-centre in front of the small sofa, the wicker basket of folded white towels at "
     "the right end of the sofa at screen-right; the small dog bursts in from the right edge, runs to the towel "
     "and rolls on it",
     ["mimi_x"], "living", T_DAY,
     "the small dog, damp and shivering, sprints in from the right edge, skids onto the big pink towel at "
     "screen-centre and flops down, rolling over and over from side to side across the soft pile with her legs in "
     "the air and her eyes squeezed shut in bliss, the towel bunching around her, while she says the line "
     "breathlessly, giggling; the floor around the towel stays glossy and spotless", _N),

 4: (10, "Medium shot from the side at the desk: the desk and laptop are at screen-left, the stocky man sits turned "
     "in his chair toward screen-right in three-quarter profile with his eyes on the pink towel on the floor "
     "at screen-right, and he talks toward it; behind him at screen-right the small dog rolls on the pink towel",
     ["bro", "mimi_x"], "living", T_DAY,
     "the stocky man in the navy blazer, amused and grumbling, spins his chair away from the laptop toward the "
     "noise, rests one elbow on the desk and shakes his head with a tired smile while he speaks; behind him at "
     "screen-right on the floor the small damp dog rolls back and forth on the big pink towel with her paws in "
     "the air, silent", _N),

 5: (10, "Medium close shot in the living room from the front at floor level: the small dog lies on the pink towel "
     "at screen-centre, her head turned toward screen-left in three-quarter profile with her face and moving "
     "mouth visible, her eyes up and to the left toward the desk where the man sits out of frame, and she talks "
     "to him while still wriggling",
     ["mimi_x"], "living", T_DAY,
     "the small dog, earnest and puffing, wriggles from side to side on the soft pink towel with her paws in the "
     "air, her mouth moving, glancing up and to the left with big shining eyes, rolling twice more on the last "
     "words; the glossy floor around the towel stays spotless", _N),

 6: (10, "Medium wide shot in the living room from the front: the stocky man strides in from screen-left and stops at "
     "the pink towel at screen-centre where the small dog lies, facing screen-right, and looks down at her while he "
     "talks; at the end he gathers the towel and walks off toward screen-right",
     ["bro", "mimi_x"], "living", T_DAY,
     "the stocky man in the navy blazer, firm and huffing, strides over from the desk, bends and gently pulls the "
     "big pink towel out from under the small damp dog, who slides softly off it onto the bare glossy floor with "
     "her paws up, then tucks the towel under his arm and walks off toward screen-right; the small dog sits up, "
     "stunned and shivering, staring after him, silent", _N),

 7: (10, "Low medium shot in the living room from the front: the small dog stands alone on the bare glossy cream "
     "floor at screen-centre where the towel was, in side profile facing screen-right toward the spot where the man "
     "left, her face and moving mouth visible; she never looks at the camera",
     ["mimi_x"], "living", T_DAY,
     "the small dog, panicked and shivering, stands rigid on the bare glossy floor lifting her paws one by one as "
     "if the tiles were cold, her fur clumped and damp but not dripping, her eyes darting between the shiny floor "
     "and the empty spot where the pink towel was, whimpering the whole line, her cheeks puffing as she clamps "
     "her mouth shut on the last words to keep from shaking", _N),

 8: (10, "Medium shot in the living room from the front: the stocky man stands at screen-right beside the sofa, his "
     "body in three-quarter profile facing screen-left toward the small dog on the floor at screen-left, and he "
     "talks to her",
     ["bro", "mimi_x"], "living", T_DAY,
     "the stocky man in the navy blazer, sighing and grumbling, stands with his arms folded, looking down at the "
     "small damp dog at his feet, and shakes his head slowly while he mutters his line; the small dog sits "
     "trembling and silent, looking up at him with her ears drooping", _N),

 9: (10, "Low medium shot in the living room from the front at floor level: the small dog sits on the bare floor at "
     "screen-centre in side profile facing screen-right, looking up toward the man standing at screen-right out "
     "of frame, her face and moving mouth visible, and she speaks up to him; she never looks at the camera",
     ["mimi_x"], "living", T_DAY,
     "the small dog, wounded and whimpering, sits trembling on the glossy floor with her chin quivering and her big "
     "eyes wet, ears drooping, one paw lifting a little toward the unseen man and pulling back, her whole body "
     "shivering but her mouth clamping shut between phrases to hold back a shake", _N),

 10: (10, "Medium shot in the living room from the front: the woman sits on the small sofa at screen-centre facing "
      "screen-left in three-quarter profile with her eyes down on the small dog on the floor at screen-left, patting "
      "her lap with one hand, and she talks to the dog",
      ["mom_h", "mimi_x"], "living", T_DAY,
      "the woman with the wooden ladle in her bun and the tartan cloth still draped over her shoulder, her "
      "pink-and-green floral sarong showing at her knees, tender and tired, sinks onto the sofa with a small groan, "
      "rubs the small of her back, then pats her lap and opens her arms to the dog while she speaks; the small damp "
      "dog stands on the glossy floor at screen-left looking up at her, trembling and torn, her tail low", _N),

 11: (10, "Low shot at floor level from the front: the small dog stands at screen-centre on the glossy cream floor in "
      "side profile facing screen-right toward the sofa, where a pair of pink slippered feet and the hem of a floral "
      "sarong show at the top-right edge, her face and moving mouth visible; she speaks up to them and never looks "
      "at the camera",
      ["mimi_x"], "living", T_DAY,
      "the small dog, trembling and brave, stands rooted to the floor with every muscle clenched, her cheeks puffed, "
      "shaking her head no, then squeezing her eyes shut, while she says the line up to the slippered feet at the "
      "top-right edge, her tail tucked and her fur on end, counting with little nods on the last three words",
      ["nosubs", "feetonly"]),

 12: (10, "Medium wide shot in the living room from the front: the stocky man stands at screen-left in three-quarter "
      "profile facing screen-right, his arm thrust toward the wicker basket of folded white towels at the right end of "
      "the sofa at screen-right where the small dog dives in; the woman sits on the sofa at screen-centre, silent",
      ["bro", "mimi_x", "mom_h"], "living", T_DAY,
      "the stocky man in the navy blazer, shocked and shouting, jabs a finger toward the wicker basket and calls "
      "toward the woman while he speaks; at screen-right the small damp dog takes a flying leap and dives headfirst "
      "into the basket of folded white towels so that only her wriggling hind legs and tail stick out, towels "
      "tumbling; the woman with the wooden ladle in her bun sits on the sofa at screen-centre, silent, her eyes "
      "wide", ["nosubs"]),

 13: (10, "Medium close shot in the living room from the front: the woman stands up from the sofa at screen-centre, "
      "facing screen-left in three-quarter profile toward the man out of frame, and she points down at the glossy "
      "floor at her feet, her face fully visible; she speaks softly",
      ["mom_h"], "living", T_DAY,
      "the woman with the wooden ladle in her bun and the tartan cloth still draped over her shoulder, her "
      "pink-and-green floral sarong showing at her knees, soft and realizing, rises with one hand on her back, "
      "looks down at the clean glossy floor and sweeps one hand across it, then glances toward the wicker basket "
      "at screen-right with her hand pressed to her chest and her eyes brimming on the last words",
      ["nosubs", "nomimi"]),

 14: (10, "Medium shot in the living room from the front at low height: the stocky man crouches at screen-centre in "
      "profile facing screen-right, one palm flat on the glossy cream floor, his eyes on the floor and then up toward "
      "the basket at screen-right, and he talks; the woman stands beside him at screen-left, silent",
      ["bro", "mom_h"], "living", T_DAY,
      "the stocky man in the navy blazer, humbled and gentle, crouches and runs his palm over the dry glossy tiles, "
      "looks up toward the wicker basket at screen-right with his brows knitting in remorse and rubs the back of his "
      "neck while he speaks, a sorry little smile on the last words; the woman with the wooden ladle in her bun, the "
      "tartan cloth over her shoulder, stands beside him with her hand on her chest, silent", ["nosubs", "nomimi"]),

 15: (10, "Medium close shot in the living room from the front: the small dog's head and front paws poke out of the "
      "wicker basket at screen-centre with towels tumbled around her, her head turned in side profile toward "
      "screen-left toward the man out of frame, her face and moving mouth visible; she speaks to him",
      ["mimi_x"], "living", T_DAY,
      "the small dog, cheeky and relieved, pops her head out of the wicker basket of white towels with a folded "
      "towel draped over one ear, her chin resting on the rim, wriggling deeper into the soft pile and blinking "
      "sleepily while she speaks to the unseen man, her tail wagging against the wicker", _N),

 16: (10, "Medium close shot in the living room from the front: the woman kneels at screen-centre on the glossy "
      "floor beside the wicker basket, facing screen-right in three-quarter profile toward the small dog in the "
      "basket, and she talks to her",
      ["mom_h", "mimi_x"], "living", T_DAY,
      "the woman with the wooden ladle in her bun and the tartan cloth still draped over her shoulder, her "
      "pink-and-green floral sarong showing at her knees, laughing through her tears, lifts a big fluffy white "
      "towel from the basket and wraps the small damp dog in it, hugging her to her chest and kissing the top of "
      "her head while she speaks; the small dog, wrapped to her chin, looks up at her with big shining eyes and a "
      "tiny tail wag", _N),

 17: (10, "Medium wide shot in the living room from the front at low height: the stocky man kneels at screen-left "
      "facing screen-right with a fluffy white towel in his hands, rubbing the back of the small dog who sits wrapped "
      "on the lap of the woman at screen-right, the woman sitting upright on the sofa so that her pale-yellow top, "
      "cream apron and the wooden ladle in her bun are fully visible, and he talks to the dog",
      ["bro", "mimi_x", "mom_h"], "living", T_DAY,
      "the stocky man in the navy blazer and blue elephant-print shorts, warm and sincere, kneels and gently rubs "
      "the small dog's back through a fluffy white towel, glancing up at her face with a promising nod on the last "
      "words; the small dog, snuggled in the towel on the lap of the woman with the wooden ladle in her bun, in her "
      "pale-yellow top and cream apron, who sits upright on the sofa smiling and stroking her head, closes her "
      "eyes in bliss", ["nosubs"]),

 18: (10, "Medium close shot in the living room from the front: the small dog sits in the woman's lap at screen-centre "
      "wrapped in a white towel, her head turned toward screen-left in three-quarter profile toward the man at the "
      "left edge, her face and moving mouth visible; at the end she throws off the towel and shakes",
      ["mimi_x", "bro", "mom_h"], "living", T_DAY,
      "the small dog, cheeky and giggling, sits up in the woman's lap and counts with little nods, then on the last "
      "words lets the towel drop and shakes her whole body hard from nose to tail, sending a spray of droplets "
      "toward screen-left; at the left edge the stocky man in the navy blazer flinches with his eyes shut and arms "
      "raised, laughing, while the woman with the wooden ladle in her bun and the tartan cloth over her shoulder "
      "laughs aloud with her hand over her mouth", ["nosubs"]),
}

_NAME = {"mimi_d": "มีมี่", "mimi_w": "มีมี่", "mimi_x": "มีมี่", "mom_h": "แม่", "bro": "พี่ชาย"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep3-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

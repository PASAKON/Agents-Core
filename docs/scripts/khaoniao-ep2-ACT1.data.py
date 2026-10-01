# -*- coding: utf-8 -*-
"""«บ้านนี้มีมีมี่» EP2 «ทำไมมีมี่ได้ยินคำว่า "แม่อาบน้ำให้นะ" แล้วหายตัวไปทั้งบ้าน?» — 18 shots x 10 s = 3:00.
Source of truth for tools/build_shotsheet.py (pattern: docs/scripts/khaoniao-ep1-ACT1.data.py).

CEO 2026-10-01: "อนุมัติงบ 400 เครดิต ยิง EP 2" (after the formula check, docs/scripts/khaoniao-ep2-SCRIPT-v1.md).

The dialogue and its manner tag are NOT typed here: they are read from
docs/scripts/khaoniao-ep2-SCRIPT-v1.md at import time, so the script the CEO reads and the prompts the
runner fires can never disagree. This file adds only what the script does not carry: who is in each shot, where,
the time of day, the English action with its emotion, and the negatives.

Plates (Assets/Agents/Core/khaoniao-family/plates/): EP1's seven reused as they are — mimi__dry, mimi__wet,
mother__home, brother__wfh, loc__living, loc__dining — plus two NEW empty sets built by
docs/reports/khaoniao-family-style/build_ep2_plates.py: loc__bathroom (the blue basin and the red dipper are in
the set) and loc__sofa_low (the shadow under the sofa). The pink towel is words only, as in EP1.
The sister, Ryo and the seller are NOT in this episode.

Direction plan (CMO_Standard_Film_PromptFormat rule 12; series plan in CMO_Standard_Story_FamilyDogSeries §2.8):
the desk (brother) is at screen-LEFT of the living room, the sofa in the middle, the kitchen and the bathroom
lie to the RIGHT, so everyone who goes to bathe goes toward screen-RIGHT and Mimi runs from the kitchen (right)
to the sofa (left). In the bathroom the doorway is at screen-LEFT and the basin at screen-RIGHT. Under the sofa
Mimi lies with her head toward screen-RIGHT, looking up and to the right at the mother's slippers.
Mimi never talks to the viewer: the humans do not understand her and answer only with the body.
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
   "tiled floor at screen-right with a red plastic dipper bowl with a handle floating in it, a "
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

T_DAY = "a bright late morning, warm natural daylight filling the house"
_N = ["nosubs", "noother"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (10, "Low shot at floor level from the front-left, looking into the shadowy hollow under the sofa: "
     "the small dog lies flat in the shaft of light with her head toward screen-right in side profile, so "
     "her whole face and moving mouth are visible from the first frame; she looks up and to the right at "
     "a pair of slippered feet passing at the top-right edge, and whispers to herself; she never looks at "
     "the camera",
     ["mimi_d"], "under", T_DAY,
     "the small dog, panicking, trembling from nose to tail with her ears flat, lies pressed against the "
     "floor under the sofa with a soft pink bath towel clamped between her front paws, her eyes darting up "
     "and to the right at the slippered feet that shuffle past and away at the top-right edge, and she "
     "whispers the whole line to herself, tucking her chin down and shrinking further back into the shadow "
     "on the last words", ["nosubs", "feetonly"]),

 2: (10, "Medium shot in the kitchen from the front at chest height: the woman stands at the counter at "
     "screen-right in profile facing screen-left, her eyes down on the small dog at her feet at "
     "screen-centre, and she talks to the dog; the dog nuzzles her ankle, looking up at her",
     ["mom_h", "mimi_d"], "dining", T_DAY,
     "the woman with the wooden ladle in her bun, sweet and dreamy, humming, stirs a steaming pot with the "
     "ladle at the counter, sniffs the air, wrinkles her nose and glances down at the dog at her ankles while "
     "she speaks to her, then wiggles her fingers in a playful scolding; the small dog, fluffy and adoring, "
     "rubs her cheek against the woman's shin and wags her tail, looking up at her", _N),

 3: (10, "Medium shot in the kitchen from the front at dog's-eye height: the small dog stands at screen-centre "
     "facing screen-right, her muzzle in profile so her mouth shows, her eyes up at the woman at "
     "screen-right who towers over her; at the end she bolts away toward screen-left",
     ["mimi_d", "mom_h"], "dining", T_DAY,
     "the small dog, suddenly pale with horror, ears flat and eyes huge, squeaks the whole line up at the woman, "
     "snatches a soft pink bath towel hanging over the back of a chair in her teeth on the words about the "
     "towel, and on the last word spins round and bolts away from the camera toward screen-left, claws "
     "skidding on the tiles; the woman, humming and oblivious, keeps stirring the pot at screen-right and "
     "glances down in puzzlement", _N),

 4: (10, "Medium shot in the bathroom from the front: the woman kneels at screen-right beside the blue basin, "
     "her body in three-quarter profile facing screen-left toward the open doorway, her eyes on the "
     "doorway, and she calls toward it; nobody else is in the frame",
     ["mom_h"], "bath", T_DAY,
     "the woman with the wooden ladle in her bun, sweet and coaxing, kneels on the white bath mat pouring "
     "warm water from the red dipper into the blue basin, testing it with her fingertips, humming, then "
     "leans toward the open doorway at screen-left and beckons with one hand while she speaks, smiling "
     "kindly", _N + ["nomimi"]),

 5: (10, "Medium shot from the side at the desk: the desk and laptop are at screen-left, the stocky man sits "
     "facing screen-left in three-quarter profile with his eyes on the laptop screen, and he talks to the "
     "laptop; behind him at screen-right the sofa stands with a black tail tip and a corner of pink towel "
     "poking out from under it",
     ["bro", "mimi_d"], "living", T_DAY,
     "the stocky man in the navy blazer, smooth and strained-polite, holds a fixed professional smile at the "
     "laptop, one hand on his chest, then freezes and glances over his shoulder toward the sofa at "
     "screen-right at a faint noise and back to the screen while he speaks; at the sofa behind him only the "
     "tip of a small black dog's tail and a corner of a pink towel stick out from under the sofa, the rest "
     "of the dog hidden in the shadow", ["nosubs"]),

 6: (10, "Medium shot in the kitchen from the front at chest height: the woman stands at screen-centre facing "
     "screen-left, toward the living room, and talks to herself; at the end she points toward the sofa at "
     "screen-left; nobody else is in the frame",
     ["mom_h"], "dining", T_DAY,
     "the woman with the wooden ladle in her bun, dreamy and cheerfully clueless, peers into the white fridge, "
     "then lifts the lid of the rice pot and peers in, then peeks into her own pink slipper, shrugging at each, "
     "and on the last words snaps her fingers, beams and points toward screen-left", _N + ["nomimi"]),

 7: (10, "Medium shot in the living room from the front: the woman sits down heavily on the small sofa at "
     "screen-centre and faces screen-left toward the desk, her eyes on the room and never on the floor, and "
     "she talks to herself; nobody else is in the frame",
     ["mom_h"], "living", T_DAY,
     "the woman with the wooden ladle in her bun, tired and dreamy, plops down onto the sofa with a groan, "
     "rubs the small of her back with one hand and fans herself with the tartan cloth while she speaks, "
     "gazing around the room, her slippered feet planted on the floor in front of the sofa", _N + ["nomimi"]),

 8: (10, "Low shot at floor level from the front-left, the same set-up as the opening shot: the small dog lies "
     "under the sofa with her head toward screen-right in side profile, her face and moving mouth visible, "
     "her eyes up and to the right at the slippered feet planted at the top-right edge, and she speaks "
     "up to them; she never looks at the camera",
     ["mimi_d"], "under", T_DAY,
     "the small dog, torn and whispering, lies under the sofa with a soft pink bath towel between her front "
     "paws, her tail thumping the floor behind her, her eyes shining up at the slippered feet planted at the "
     "top-right edge while she speaks up to them, ears flat, her whole body leaning toward the feet and "
     "then shrinking back", ["nosubs", "feetonly"]),

 9: (10, "Medium wide shot in the living room: the desk at screen-left, the stocky man sits at it turned in "
     "his chair toward screen-right in three-quarter profile with his eyes on the woman, who sits on the sofa "
     "at screen-right facing screen-left toward him; he talks to her, whispering",
     ["bro", "mom_h"], "living", T_DAY,
     "the stocky man in the navy blazer, irritated and whispering, clamps one hand over the laptop's "
     "microphone and leans toward the woman while he speaks, jabbing a finger toward the floor under the "
     "sofa and shaking his head in disapproval; the woman with the wooden ladle in her bun, sitting on the "
     "sofa, listens with a puzzled frown and her hands in her lap, looking at him", ["nosubs", "nomimi"]),

 10: (10, "Medium close shot in the living room from the front: the woman sits on the sofa at screen-centre, her "
      "head bowed and turned toward screen-left at the empty round dog bed in the corner at screen-left, "
      "and she talks to herself, her face fully visible; nobody else is in the frame",
      ["mom_h"], "living", T_DAY,
      "the woman with the wooden ladle in her bun, hurt and tearful, sags on the sofa gazing at the empty "
      "round dog bed in the corner, her bottom lip trembling, and dabs the corner of her eye with the tartan "
      "cloth while she speaks in a cracking voice, forcing a brave little smile on the last words",
      ["nosubs", "nomimi"]),

 11: (10, "Low shot at floor level from the front-left, the same set-up as the opening shot: the small dog lies "
      "under the sofa with her head toward screen-right in side profile, her face and moving mouth visible, "
      "her eyes up and to the right at the slippered feet at the top-right edge, and she speaks up to them; "
      "she never looks at the camera",
      ["mimi_d"], "under", T_DAY,
      "the small dog, wounded and whimpering, lies under the sofa, her tail now still, tears welling in her "
      "big eyes and her chin trembling while she speaks up to the slippered feet at the top-right edge, ears "
      "drooping, one front paw reaching a little toward them and pulling back", ["nosubs", "feetonly"]),

 12: (10, "Low shot at floor level from the front-left, the same set-up as the opening shot, then the camera "
      "holds as she bursts out: the small dog lies under the sofa with her head toward screen-right in side "
      "profile, her face and moving mouth visible, speaking up and to the right at the slippered feet at the "
      "top-right edge; on the last words she scrambles out toward screen-right",
      ["mimi_d"], "under", T_DAY,
      "the small dog, trembling and determined, lies under the sofa with a soft pink bath towel between her "
      "front paws, her wet eyes on the slippered feet at the top-right edge, whimpering at first and then "
      "squeezing her eyes shut on the last words, and on the very last word she snatches the towel in her teeth "
      "and scrambles out from under the sofa toward screen-right", ["nosubs", "feetonly"]),

 13: (10, "Medium shot in the living room from the front at low height: the woman sits at the edge of the sofa at "
      "screen-right, leaning forward, facing screen-left in three-quarter profile with her eyes down on the "
      "small dog who stands in front of her at screen-centre, a pink towel in her mouth, facing screen-right "
      "up at her; the woman talks to the dog",
      ["mom_h", "mimi_d"], "living", T_DAY,
      "the woman with the wooden ladle in her bun, voice breaking and eyes brimming, leans forward from the "
      "sofa with both hands pressed to her chest and then reaches out toward the dog while she speaks to her, "
      "a tearful smile spreading; the small dog, shivering all over, stands in front of her holding a soft pink "
      "bath towel in her teeth, her tail low and wagging in tiny sweeps, looking up at her face", _N),

 14: (10, "Medium shot in the bathroom from the front: the small dog sits in the blue basin at screen-right, "
      "in three-quarter profile facing screen-left with her eyes squeezed shut and her muzzle in profile so her "
      "mouth shows, soap bubbles heaped on her head, and she talks to the woman who kneels beside the basin at "
      "the right edge of the frame",
      ["mimi_w", "mom_h"], "bath", T_DAY,
      "the small dog, squeaking and shivering, sits up to her chest in the blue basin of bubbly water with her "
      "eyes squeezed shut and a heap of white bubbles on her head, her ears floating on the water, "
      "trembling with each word and then lifting her chin bravely on the last line; the woman with the wooden "
      "ladle in her bun kneels at the basin's edge and gently pours a dipperful of warm water over the dog's "
      "back, her face soft", _N),

 15: (10, "Medium shot in the bathroom from the front: the woman kneels at the basin at screen-right facing "
      "screen-left in three-quarter profile with her eyes down on the small dog in the basin at screen-centre, "
      "and she talks to the dog",
      ["mom_h", "mimi_w"], "bath", T_DAY,
      "the woman with the wooden ladle in her bun, laughing through her tears, tender, kneels at the blue basin "
      "scooping warm water over the dog's back with the red dipper and wiping a tear from her cheek with her "
      "wrist while she speaks to the dog; the small dog, wet and bubbly, sits in the basin with her eyes now "
      "open, her tail swishing the water, gazing up at the woman", _N),

 16: (10, "Medium wide shot in the bathroom from the front: the stocky man stands in the open doorway at screen-left "
      "in profile facing screen-right, a closed laptop under his arm, his eyes on the small dog in the blue basin "
      "at screen-right, and he talks to the dog; the woman kneels beside the basin at the right edge and stays "
      "silent",
      ["bro", "mimi_w", "mom_h"], "bath", T_DAY,
      "the stocky man in the navy blazer and elephant-print shorts, amused and warm, leans in the doorway "
      "with a closed laptop tucked under one arm and his other hand on the door frame, grinning at the dog "
      "while he speaks to her and nodding softly on the last words; the small dog, wet and bubbly in the "
      "basin, looks up at him; the woman with the wooden ladle in her bun kneels beside the basin smiling "
      "and wiping a tear", ["nosubs"]),

 17: (10, "Medium close shot in the living room from the front: the woman sits on the sofa at screen-centre with the small "
      "dog wrapped in the pink towel in her lap, her face bent toward the dog's face in three-quarter profile "
      "facing screen-left, and she talks to the dog, who looks up at her",
      ["mom_h", "mimi_w"], "living", T_DAY,
      "the woman with the wooden ladle in her bun, soft and a little teary, wraps the small damp dog snugly in a "
      "soft pink bath towel on her lap and hugs her to her chest while she speaks, rocking her gently and "
      "kissing the top of her head; the small dog, wrapped up to her chin in the pink towel, looks up at her "
      "with big shining eyes and a tiny tail wag", _N),

 18: (10, "Medium close shot in the living room from the front: the small dog lies in the woman's lap on the sofa "
      "at screen-centre wrapped in the pink towel, her head turned toward screen-left in three-quarter profile "
      "toward the woman's face (the woman's hand at screen-left strokes her head), and she speaks to the "
      "woman; her mouth is visible",
      ["mimi_w", "mom_h"], "living", T_DAY,
      "the small dog, sleepy and cheeky, snuggled in the pink towel in the woman's lap, blinks slowly and "
      "yawns while she speaks up to the woman, her eyes sliding half shut on the last words with a sly little "
      "smile; the woman with the wooden ladle in her bun gently strokes the dog's head with one hand, smiling "
      "down at her", _N),
}

_NAME = {"mimi_d": "มีมี่", "mimi_w": "มีมี่", "mom_h": "แม่", "bro": "พี่ชาย"}


def _lines_from_script():
    """{shot: [(thai speaker, english direction, thai line), ...]} from the script md."""
    text = (Path(__file__).with_name("khaoniao-ep2-SCRIPT-v1.md")).read_text(encoding="utf-8")
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

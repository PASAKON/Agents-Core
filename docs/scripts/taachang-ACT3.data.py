# -*- coding: utf-8 -*-
"""«ตาชั่งของเสี่ย» ACT3 = EP5 + EP6, shots 54-75 (7:04-10:00), the last act.
Source of truth for tools/build_shotsheet.py.

Loads ACT2 (which loads ACT1) for every shared block and adds the ACT3 states: เสี่ย humbled
(S54-68) and reformed (S69-72), the outside of the zinc shack, and the little boy in his
school clothes described WITHOUT the word "school" (see below). Dialogue is read from
SCRIPT-v2 at import; the narrator's closing line (S75) is added in the edit, never by Flow.

Applied before the first shot (CTO_Flow_Omni1.1_Continuity §What Flow silently deletes,
promoted 2026-09-26): a child and money never share a prompt — not in the picture, not in
the words. S59's sum moved to กล้า (16), S62/S63 are solo shots with a sealed envelope,
S73 is a collar, not school fees.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "taachang_act2", Path(__file__).with_name("taachang-ACT2.data.py"))
_a2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a2)
_a1 = _a2._a1

STYLE = _a2.STYLE
CHAR = dict(_a2.CHAR)
WARDROBE = dict(_a2.WARDROBE)
VOICE = dict(_a2.VOICE)
LOC = dict(_a2.LOC)
NOT = dict(_a2.NOT)
PROP_FOR_NOT = dict(_a2.PROP_FOR_NOT)
_V = _a2._V

CHAR["sia_hum"] = ("@sia__face",
  "a heavy-set Thai-Chinese man of fifty with a round fleshy face, small narrow eyes, black hair "
  "falling messily over his forehead with grey at the temples and a thin moustache, in the same "
  "cream polo shirt now crumpled, sweat-stained and untucked, dark slacks, no sunglasses and no gold "
  "chain, a drained tired face with red-rimmed eyes",
  "The heavy man in the crumpled cream polo")
WARDROBE["sia_hum"] = "@sia__humbled"
VOICE["sia_hum"] = VOICE["sia_b"]

CHAR["sia_ref"] = ("@sia__face",
  "a heavy-set Thai-Chinese man of fifty with a round fleshy face, small narrow eyes, black hair cut "
  "short and neat with grey at the temples and a thin moustache, in a plain grey button-up work "
  "shirt with a tan canvas work apron over it, dark trousers and sandals, no jewellery at all",
  "The heavy man in the grey work shirt and apron")
WARDROBE["sia_ref"] = "@sia__reformed"
VOICE["sia_ref"] = VOICE["sia_b"]

# The 11-year-old in his school clothes. ACT2 S29 take 1 (this plate + the words "primary-school
# shirt" and "school shoes", no money) was deleted by Flow; the police A/B found the WORD trips
# the filter while the plate carries the look. So the plate stays and the word goes.
CHAR["tor_s"] = ("@tor__face",
  "a small Thai boy of eleven with round cheeks and a straight black bowl-cut, in a plain white "
  "short-sleeved shirt with nothing written or embroidered on it, navy-blue shorts, white socks, "
  "black shoes and a small plain dark backpack",
  "The little boy in the white shirt")

LOC["baan_out"] = ("@baan__outside",
  "the outside of a small, poor zinc shack beside a canal: rusty, dented corrugated zinc sheets "
  "nailed onto a rough wooden frame, patched with old plywood and a faded tarpaulin, a low lean-to "
  "roof held down with old tyres, one rickety wooden step up to a low doorway with a cloth curtain "
  "for a door, plastic buckets, plants in old tins, laundry on a wire, a dirt path in front and the "
  "canal beside it")

# The 11-year-old is described in WORDS, with no reference chip (tools/build_shotsheet.py TEXT_ONLY).
# From ~01:00 on 2026-09-26 Flow deleted every prompt carrying his plates with his face in frame:
# 57a, 58a, 64 and 360p arms 9064/9164/9074 — 6 of 6. The same S74 and S69 with his chips removed
# rendered (arms 9274, 9269); S75 with the chips but his back to camera rendered too (9275). Keep
# him at medium/wide: without the plate his face is only close to the ACT1/ACT2 boy.
TEXT_ONLY = {"tor_h", "tor_s"}

PROPS_BY_SHOT = {
    54: ["@pickup__empty"], 56: ["@jar__full"], 57: ["@jar__full"],
    62: ["@envelope"], 63: ["@envelope"],
    69: ["@yard_scale"], 70: ["@yard_scale"], 71: ["@cart", "@yard_scale"],
    74: ["@notebook"],
}

OUT = "late afternoon, warm daylight"
HOME = _a2.HOME
LAN = "a bright morning some days later, clear daylight"
SOI = "late afternoon, soft golden light"

# n: (seconds, framing, [char keys, subject first], loc, time of day, action, [nots])
_META = {
 54: (8, "Wide on the zinc shack by the canal, the empty white pickup parked on the path",
      ["yai_h", "sia_hum"], "baan_out", OUT,
      "the old woman pulls back the curtain of her doorway and finds the heavy man standing on the "
      "path outside; she is frightened and trembling, shrinking back into the doorway as she speaks, "
      "voice shaking; he stands still with his head lowered", ["nosubs"]),
 55: (8, "Medium shot, the woman in the straw hat hurrying over from next door",
      ["pa", "kla_w", "sia_hum"], "baan_out", OUT,
      "the woman in the straw hat hurries over from next door and plants herself between the heavy "
      "man and the doorway, protective and fierce; the boy in the grey T-shirt raises both hands to "
      "calm her", ["nosubs"]),
 56: (8, "Close two-shot, the old woman holding the jar of pebbles, both faces three-quarters to camera",
      ["sia_hum", "yai_h"], "baan", HOME,
      "the heavy man looks down at the glass jar of pebbles the old woman holds close to her chest; "
      "he asks quietly for the first time, polite, unable to meet her eyes; she answers warily, "
      "hugging the jar", ["nosubs"]),
 # take 1 (with the 11-year-old kneeling beside them) was deleted by Flow, 2026-09-26. Without him.
 57: (8, "Medium shot from a little above, pebbles poured out onto the woven mat in small piles of ten",
      ["kla_w", "sia_hum"], "baan", HOME,
      "the pebbles from the jar are poured out onto the mat; the boy in the grey T-shirt kneels and "
      "sorts them into small piles of ten while the heavy man, heavy-voiced and holding back his "
      "feelings, asks his son to count; his son counts out loud, concentrating", ["nosubs"]),
 # take 1 (the 11-year-old in frame with the heavy man, as in S57) was deleted by Flow. Without him.
 # take 2 (the boy + the heavy man, no child) was deleted too. Solo, as every solo shot has passed.
 58: (8, "Close-up on the boy in the grey T-shirt alone, kneeling by the piles of pebbles, his face three-quarters to camera",
      ["kla_w"], "baan", HOME,
      "the boy in the grey T-shirt sets down the last pile of pebbles on the mat, then looks up at his "
      "father off-frame and states the total in a hard voice, staring at him", ["nosubs"]),
 59: (8, "Medium two-shot, the woman in the straw hat gasping beside the boy in the grey T-shirt",
      ["kla_w", "pa"], "baan", HOME,
      "the boy in the grey T-shirt works the sum out carefully and says it to the old woman; the "
      "woman in the straw hat gasps, shocked, one hand pressed to her chest", ["nosubs"]),
 60: (8, "Close-up on the heavy man alone, his face three-quarters to camera",
      ["sia_hum"], "baan", HOME,
      "the heavy man clutches a single pebble tightly in his fist and breaks down, tears running down "
      "his face, his voice sobbing", ["nosubs"]),
 61: (8, "Medium shot, the heavy man kneeling and bowing his forehead to the floor before the old woman, the neighbour watching",
      ["sia_hum", "yai_h", "pa"], "baan", HOME,
      "the heavy man kneels on the mat in front of the old woman and bows his forehead down to the "
      "floor in a Thai prostration of apology, weeping, voice quavering, sincere; the old woman and "
      "the woman in the straw hat watch, stunned", ["nosubs"]),
 62: (8, "Close-up on the heavy man alone, offering a sealed brown envelope with both hands",
      ["sia_hum"], "baan", HOME,
      "the heavy man, still on his knees, holds out a thin sealed brown paper envelope with both "
      "hands toward someone off-frame, tearful and humble", ["nosubs"]),
 63: (8, "Close-up on the old woman alone, her face three-quarters to camera",
      ["yai_h"], "baan", HOME,
      "the old woman takes a thin sealed brown paper envelope in both hands, crying and smiling at "
      "once, her voice trembling", ["nosubs"]),
 64: (8, "Two-shot, the little boy hugging the old woman, both faces visible",
      ["tor_h", "yai_h"], "baan", HOME,
      "the little boy throws his arms around the old woman, overjoyed; she hugs him back, sobbing "
      "with happiness", ["nosubs"]),
 65: (8, "Medium two-shot, the woman in the straw hat and the heavy man",
      ["pa", "sia_hum"], "baan", HOME,
      "the woman in the straw hat crosses her arms, sceptical; the heavy man hangs his head, "
      "ashamed", ["nosubs"]),
 66: (8, "Close-up on the heavy man alone, rising to his feet",
      ["sia_hum"], "baan", HOME,
      "the heavy man gets up off his knees and stands straight, wiping his face, determined and "
      "sincere, his voice strong", ["nosubs"]),
 67: (8, "Close-up on the old woman alone, her face three-quarters to camera",
      ["yai_h"], "baan", HOME,
      "the old woman laughs softly through her drying tears, amused, teasing him gently", ["nosubs"]),
 68: (8, "Two-shot, the woman in the straw hat and the heavy man face to face",
      ["pa", "sia_hum"], "baan", HOME,
      "the woman in the straw hat stares the heavy man down, challenging; he answers quietly but "
      "surely, holding her gaze for the first time", ["nosubs"]),
 69: (8, "Medium shot at the yard entrance, the little boy bending over the platform scale, the old woman beside him",
      ["tor_s", "yai_c"], "lan", LAN,
      "the old platform scale now stands right at the front of the yard by the entrance with the old "
      "woman's sack on it; the little boy bends over to read the dial for her and straightens up "
      "proud, chest puffed out; she beams at him, delighted", ["dial", "nosubs"]),
 70: (8, "Wide shot, the heavy man standing a clear step back from the scale, both hands raised",
      ["sia_ref", "yai_c"], "lan", LAN,
      "the heavy man stands a clear step back from the platform scale with both hands raised in the "
      "air, well away from the sack, earnest, with a sheepish smile", ["dial", "nosubs"]),
 71: (8, "Medium shot, the woman in the straw hat pushing her cart back into the yard",
      ["pa", "sia_ref"], "lan", LAN,
      "the woman in the straw hat pushes her loaded cart back in through the yard entrance past the "
      "scale, satisfied and smiling; the heavy man waves her in, relieved, with a big smile",
      ["dial", "nosubs"]),
 72: (8, "Close two-shot, the father's hand on his son's shoulder, both faces three-quarters to camera",
      ["sia_ref", "kla_w"], "lan", LAN,
      "the heavy man puts his hand on his son's shoulder and squeezes it, moved, eyes wet; the boy "
      "answers with a shy smile", ["nosubs"]),
 73: (8, "Medium two-shot, the old woman straightening the little boy's shirt collar, both faces three-quarters to camera",
      ["yai_h", "tor_s"], "baan", HOME,
      "the old woman straightens the collar of the little boy's white shirt and smooths it down, "
      "content and warm; he presses his palms together in a wai to thank her, beaming", ["nosubs"]),
 74: (8, "Medium two-shot, the little boy holding up a notebook with its pages angled away from camera",
      ["tor_h", "yai_h"], "baan", HOME,
      "the little boy holds up his light-blue notebook to show her, the pages turned away from the "
      "camera, proud and showing off; the old woman is moved, her eyes misting", ["nosubs"]),
 75: (8, "Wide, the old woman and the little boy walking away hand in hand down the canal path",
      ["yai_h", "tor_h"], "soi", SOI,
      "the old woman and the little boy walk away hand in hand along the canal path under the row of "
      "electricity poles, chatting and laughing, their backs to the camera, the path stretching "
      "ahead; no one speaks to the camera", ["nosubs"]),
}

_NAME = dict(_a2._NAME)
_NAME.update({"sia_hum": "เสี่ย", "sia_ref": "เสี่ย"})
_NARRATOR = "ผู้บรรยาย"   # S75: voice-over added in the edit, never generated


def _build():
    lines = _a1._lines_from_script()
    shots = []
    for n in sorted(_META):
        secs, framing, chars, loc, tod, action, nots = _META[n]
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


SHOTS = _build()

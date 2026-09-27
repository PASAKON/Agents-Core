# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT1 = EP1 + EP2, shots 1-23 (0:00-3:04). Source of truth for
tools/build_shotsheet.py. Shared cast, voices, languages, locations and negatives live in
ep4-common.py; this file adds who is in each shot, where, when and the English action.

Rules carried in from films 1-3:
- the speaker's action happens WHILE the line is said, never before it ("then" is banned);
- the first speaker's action is written first, because Flow speaks in ACTION order;
- every person in frame has their own physical action and a loud, physical emotion;
- no children, no uniforms, day only, at most 3 people, no money in frame, no real brand.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T1 = _c.T1

PROPS_BY_SHOT = {
    1: ["@parasol_pink"], 3: ["@kratip"], 4: ["@kratip"], 6: ["@trunk_letters"],
    7: ["@parasol_pink"], 9: ["@trunk_letters"], 11: ["@motorbike"],
}

_N = ["nosubs", "noextra"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (8, "Medium wide at the edge of the golden paddy, both faces three-quarters to camera",
     ["hong", "bm"], "na_ripe", T1,
     "the woman in hot pink, gloating, smiling wide with shining eyes, stands under an open "
     "hot-pink silk parasol and flicks the heavy rice ears with her closed fan while she "
     "speaks; at the same moment the headman in the light-blue shirt, uneasy, eyes down, "
     "holds his old black bicycle with one hand and twists the checked cloth from his waist "
     "in the other while he answers", _N + ["nocash"]),
 2: (8, "Close two-shot, the fan tapping the headman's chest",
     ["hong", "bm"], "na_ripe", T1,
     "the woman in hot pink, sugary, one eyebrow raised, taps the headman's chest lightly "
     "with her closed fan while she speaks; at the same time the headman, ashamed, face "
     "flushed, with a forced smile, presses his palms together in a wai and answers",
     _N + ["nocash"]),
 3: (8, "Medium under the house on stilts, steam rising from the sticky-rice steamer",
     ["kp1", "bm"], "home", T1,
     "the woman in the indigo blouse, cheerful and loud, beaming, scoops hot sticky rice into "
     "a round woven bamboo basket with her indigo-stained fingers and waves her free hand "
     "while she calls out; at the same time the headman rides his old black bicycle into the "
     "yard and brakes, smiling stiffly", _N),
 4: (8, "Two-shot at the bamboo platform, the sticky-rice basket between them",
     ["bm", "kp1"], "home", T1,
     "the headman, touched and guilty, eyes wet and red, receives the woven sticky-rice "
     "basket in both hands while he speaks; at the same time the woman in the indigo blouse, "
     "in a good mood, ties the basket's cord tight and chatters while she answers; at the "
     "son's name the headman's face freezes", _N),
 5: (8, "Medium beside the big clay jar next to the rice barn",
     ["pa", "kp1"], "home", T1,
     "the woman in the green blouse, shy, bowing her head, holds out an empty plastic bucket "
     "while she speaks; at the same time the woman in the indigo blouse, generous and "
     "laughing, scoops raw rice from the big clay jar into the bucket until it heaps over "
     "and adds one more scoop while she answers", _N),
 6: (8, "Close-up on the old tin trunk, a plain envelope going in",
     ["pa", "kp1"], "home", T1,
     "the woman in the green blouse, curious, holds out a plain white envelope while she "
     "speaks; at the same time the woman in the indigo blouse, carefree, with a shy "
     "embarrassed laugh, lifts the lid of the old tin trunk and drops the envelope in "
     "unopened on top of other envelopes while she answers", _N + ["noletter"]),
 7: (8, "Medium in the red-dirt yard, the woman in hot pink arriving under her parasol",
     ["hong", "kp1"], "home", T1,
     "the woman in hot pink, sickly sweet, smiling with cold eyes, fanning herself nonstop, "
     "walks into the yard under her open hot-pink parasol while she speaks; at the same time "
     "the woman in the indigo blouse, puzzled, smiling politely, wipes her hands on a checked "
     "cloth and walks out to meet her while she answers", _N),
 8: (8, "Close two-shot, the fan stopped, both faces in profile to each other",
     ["hong", "kp1"], "home", T1,
     "the woman in hot pink, cold and sweet with a thin one-sided smile, stops fanning and "
     "tilts her head while she speaks; at the same time the woman in the indigo blouse, "
     "shocked, face draining pale, steps half a step back, grips her checked cloth and "
     "shakes her head hard while she answers", _N + ["nocash"]),
 9: (8, "Medium, kneeling at the open tin trunk, envelopes spilling on the ground",
     ["kp1", "hong"], "home", T1,
     "the woman in the indigo blouse, panicking, hands shaking, kneels at the open tin trunk "
     "tipping envelopes out onto the ground and tears open an empty faded red cloth bundle, "
     "crying out in a breaking voice while she speaks; at the same time behind her the woman "
     "in hot pink, bored and sweet, fans herself slowly and answers", _N + ["noletter", "nocash"]),
 10: (8, "Medium, the woman in pink walking away, the mother collapsing onto the bamboo platform",
      ["hong", "kp1"], "home", T1,
      "the woman in hot pink, gleeful, walks away across the yard without turning back and "
      "calls over her shoulder while she speaks; at the same time behind her the woman in the "
      "indigo blouse, wailing, body shaking, sinks down onto the bamboo platform hugging the "
      "empty red cloth to her chest", _N + ["nocash"]),
 11: (8, "Medium wide, the son riding into the yard on a red-and-black motorbike",
      ["sa_c", "kp1"], "home", T1,
      "the young man in the white T-shirt, happy, grinning with deep dimples, stops a small "
      "red-and-black motorbike in the yard and lifts a plastic bag of oranges off the "
      "handlebar while he calls out, his grin fading as he sees his mother; at the same time "
      "the woman in the indigo blouse sits sobbing on the bamboo platform, head down, "
      "clutching the empty red cloth", _N),
 12: (8, "Two-shot, the mother holding up the empty red cloth, oranges rolling in the dust",
      ["kp1", "sa_c"], "home", T1,
      "the woman in the indigo blouse, furious and heartbroken, tears streaming, voice "
      "shaking, thrusts the empty faded red cloth toward her son's face while she shouts; at "
      "the same time the young man in the white T-shirt, face pale, lips trembling, lets the "
      "bag of oranges slip from his hand so oranges roll across the red dirt, and stammers "
      "while he backs away", _N),
 13: (8, "Close-up on the son reading a letter, the paper edge-on to camera",
      ["sa_c", "kp1"], "home", T1,
      "the young man in the white T-shirt, face drained, eyes welling, voice cracking, reads a "
      "letter aloud while his hands shake so hard the paper trembles; behind him the woman in "
      "the indigo blouse, trembling, stares at him", _N + ["noletter", "nocash"]),
 14: (8, "Medium, the son on his knees in the red dust",
      ["sa_c", "kp1"], "home", T1,
      "the young man in the white T-shirt, sobbing out a confession, drops to his knees in the "
      "red dirt with his fists clenched in the dust while he speaks; at the same time the "
      "woman in the indigo blouse, rigid, arms folded tight, tears running, listens in "
      "disbelief", _N + ["nocash"]),
 15: (8, "Two-shot, the mother gripping her kneeling son's shoulders",
      ["kp1", "sa_c"], "home", T1,
      "the woman in the indigo blouse, shouting in rage, eyes red, grips her kneeling son by "
      "both shoulders and shakes him while she speaks; at the same time the young man in the "
      "white T-shirt keeps his head bowed, shoulders shaking, unable to meet her eyes", _N),
 16: (8, "Close-up on the son, the mother recoiling behind him",
      ["sa_c", "kp1"], "home", T1,
      "the young man in the white T-shirt, sobbing, words breaking apart, lifts his wet face "
      "to his mother while he speaks; at the same time the woman in the indigo blouse, "
      "shocked, mouth open, lets go of his shoulders, presses a hand over her mouth and steps "
      "back two paces", _N + ["noletter"]),
 17: (8, "Medium close-up on the mother, the tin trunk behind her",
      ["kp1"], "home", T1,
      "the woman in the indigo blouse, wailing, voice hoarse, clutches the front of her "
      "blouse over her heart with tears pouring down her face while she speaks", _N),
 18: (8, "Medium, the son prostrating at his mother's feet",
      ["sa_c", "kp1"], "home", T1,
      "the young man in the white T-shirt, crying, bows down and presses his forehead to his "
      "mother's feet on the red dirt while he speaks; at the same time the woman in the "
      "indigo blouse, tears running, hands shaking, turns her face away but does not pull her "
      "feet back", _N),
 19: (8, "Medium wide from behind, the mother at the edge of the golden paddy, the son following",
      ["kp1", "sa_c"], "na_ripe", T1,
      "the woman in the indigo blouse, steeling herself, jaw set, wipes her tears with her "
      "checked cloth while she looks over the ripe golden rice and speaks; at the same time "
      "the young man in the white T-shirt, eyes swollen, hopeless, walks up and stands just "
      "behind her and answers", _N + ["nocash"]),
 20: (8, "Close-up, her indigo-stained fingers on the thin gold chain at her neck",
      ["kp1", "sa_c"], "na_ripe", T1,
      "the woman in the indigo blouse, wistful, smiling through tears, strokes the thin gold "
      "chain at her throat with her indigo-stained fingers while she speaks; at the same time "
      "the young man in the white T-shirt, alarmed, shakes his head hard and grabs her hand",
      _N + ["nocash"]),
 21: (8, "Close two-shot, her hands closing his fingers over the gold chain",
      ["kp2", "sa_c"], "na_ripe", T1,
      "the woman in the indigo blouse, firm, voice trembling but not giving way, her neck now "
      "bare, closes both her hands around her son's fist with the thin gold chain inside it "
      "while she speaks; at the same time the young man in the white T-shirt, crying, nods "
      "hard and grips the chain tight", _N + ["nocash"]),
 22: (8, "Medium under the house, the headman arriving on his bicycle, the son on the phone",
      ["bm", "sa_c"], "home", T1,
      "the headman in the light-blue shirt, over-eager, eyes darting, props his old black "
      "bicycle and pats the young man on the back while he speaks; at the same time the young "
      "man in the white T-shirt, hopeful, holds a phone to his ear waiting for an answer",
      _N + ["nocash"]),
 23: (8, "Medium close-up on the son lowering the phone, the mother behind him",
      ["sa_c", "kp2"], "home", T1,
      "the young man in the white T-shirt, stunned, face pale, voice hollow, slowly lowers the "
      "phone from his ear while he speaks; at the same time behind him the woman in the "
      "indigo blouse, crushed, sinks down onto the bamboo platform with a hand pressed over "
      "her mouth", _N),
}

SHOTS = _c.build_shots(_META)

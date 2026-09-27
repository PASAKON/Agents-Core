# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT3 = EP5 + EP6, shots 54-72 (7:04-9:36). Source of truth for
tools/build_shotsheet.py. Shared blocks: ep4-common.py. Rules: see ep4-ACT1.data.py.

S73-S74 (narrator) are not shot in Flow: slow push-ins on the na__stubble and kratip
plates, made in the edit for no credits.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T3, T4, T5, T6 = _c.T3, _c.T4, _c.T5, _c.T6

PROPS_BY_SHOT = {
    54: ["@pickup_old"], 55: ["@pickup_old"], 56: ["@pickup_old"], 63: ["@parasol_pink"],
    65: ["@kratip"], 68: ["@kratip"], 70: ["@trunk_letters"], 72: ["@kratip"],
}

_N = ["nosubs", "noextra"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 54: (8, "Medium at the old white pickup, the headman pulling its door open",
      ["bm", "sa_i", "kp2"], "mill_closed", T3,
      "the headman in the light-blue shirt, fast and certain, yanks the passenger door of "
      "the old white pickup open while he speaks; at the same time the young man in the "
      "indigo shirt, hope rising in his face, and the woman in the indigo blouse, hesitant, "
      "look at each other", _N + ["nologo"]),
 55: (8, "Two-shot at the open pickup door, the mother deciding",
      ["bm", "kp2"], "mill_closed", T3,
      "the headman, pleading, eyes wet, sweeps an open hand toward the passenger seat while "
      "he speaks; at the same time the woman in the indigo blouse, hurt but resolved, looks "
      "him straight in the face, grips the edge of the pickup door and answers",
      _N + ["nologo"]),
 56: (8, "Medium wide, the old pickup stopped at the foot of the white building's steps",
      ["sa_i", "bm"], "land", T3,
      "the young man in the indigo shirt, breathless and excited, jumps down from the old "
      "white pickup and checks the time on his phone while he speaks; at the same time the "
      "headman leans out of the driver's window, urgent, waving them on while he answers",
      _N + ["nologo", "nouniform"]),
 57: (8, "Medium, the son pulling his mother by the hand up the concrete steps",
      ["sa_i", "kp2"], "land", T3,
      "the young man in the indigo shirt, desperately hopeful, runs up the concrete steps "
      "pulling his mother by the hand while he speaks; at the same time the woman in the "
      "indigo blouse, out of breath, lifts the hem of her ikat skirt to run after him, her "
      "eyes fixed on the open glass doors, while she answers", _N + ["nouniform"]),
 58: (8, "Medium, the son coming out through the glass doors holding up a paper receipt",
      ["sa_i", "kp2"], "land", T3,
      "the young man in the indigo shirt, overjoyed, trembling, laughing through tears, "
      "walks out through the glass doors holding up a small paper receipt, its back to the "
      "camera, while he speaks, his voice shaking so hard he stops for breath; at the same "
      "time on the porch the woman in the indigo blouse waits with her palms pressed "
      "together", _N + ["noletter", "nouniform", "nocash"]),
 59: (8, "Close two-shot on the porch, the mother pressing the receipt to her chest",
      ["kp2", "sa_i"], "land", T3,
      "the woman in the indigo blouse, weeping with joy, body shaking, presses the small "
      "paper receipt flat against her chest while she speaks; at the same time the young man "
      "in the indigo shirt, crying, wraps both arms around her and holds her tight while he "
      "answers", _N + ["noletter", "nouniform"]),
 60: (8, "Medium, the headman standing apart at the foot of the steps",
      ["bm", "kp2"], "land", T3,
      "the headman in the light-blue shirt, repentant, voice steady, stands apart at the "
      "foot of the steps holding his woven hat against his chest while he speaks; at the "
      "same time on the steps above the woman in the indigo blouse turns and looks at him, "
      "still and unsmiling", _N + ["nouniform", "nocash"]),
 61: (8, "Medium, the woman in pink at a desk just inside the open hot-pink office door",
      ["hong"], "mill_open", T4,
      "the woman in hot pink, outraged, face flushed red, eyes bulging, veins standing out on "
      "her neck, reads a letter out loud and crushes it in her fist while she speaks",
      _N + ["noletter", "nologo"]),
 62: (8, "Close-up, the woman in pink shouting into her phone",
      ["hong"], "mill_open", T4,
      "the woman in hot pink, beside herself with rage, face twisted, shouts into the phone "
      "pressed to her ear, stamping her foot and slamming her closed fan down on the desk "
      "while she speaks", _N + ["nologo"]),
 63: (8, "Medium in the harvested paddy of stubble and straw stacks",
      ["hong", "sa_ic"], "na_stub", T4,
      "the woman in hot pink, furious, storms across the stubble under her open hot-pink "
      "parasol and jabs her closed fan at the young man while she speaks; at the same time "
      "the young man in the indigo shirt, calm and sure, sets down a bundle of straw, "
      "straightens up and looks her in the eye while he answers", _N),
 64: (8, "Medium, the neighbour stepping up beside the son with a bundle of straw",
      ["hong", "pa", "sa_i"], "na_stub", T4,
      "the woman in hot pink, scowling, threatens them while she speaks; at the same time the "
      "woman in the green blouse, a bundle of straw under one arm, strides up beside the "
      "young man, plants her free hand on her hip and laughs at her while she answers; the "
      "young man in the indigo shirt smiles", _N),
 65: (8, "Medium, the woman in pink stalking off, the mother calling after her from the field hut",
      ["kp2", "hong"], "na_stub", T4,
      "the woman in the indigo blouse, calm and kind with no anger left, holds out a woven "
      "sticky-rice basket and calls after her while she speaks; at the same time the woman in "
      "hot pink, humiliated, face flushing red, stops short, turns with her mouth open and "
      "answers", _N),
 66: (8, "Wide, the mill yard with every combine harvester parked and idle",
      ["hong"], "mill_open", T5,
      "the woman in hot pink, anxious and restless, drenched in sweat, fans herself hard "
      "with her fan and holds a phone to her ear while she walks in circles around the idle "
      "combine harvesters and speaks", _N + ["nologo"]),
 67: (8, "Medium close-up, the woman in pink sinking onto an empty rice sack",
      ["hong"], "mill_open", T5,
      "the woman in hot pink, pleading into her phone, voice cracking, sinks slowly down onto "
      "an empty plain white sack while she speaks, the fan slipping from her fingers to the "
      "concrete", _N + ["nologo", "nocash"]),
 68: (8, "Two-shot under the house beside the tin trunk",
      ["sa_i", "kp2"], "home", T5,
      "the young man in the indigo shirt, serious and unreadable, turns to his mother while "
      "he speaks; at the same time the woman in the indigo blouse, frightened, sets a woven "
      "sticky-rice basket down on the bamboo platform while she answers", _N),
 69: (8, "Two-shot on the bamboo platform, the son breaking into a dimpled grin",
      ["sa_i", "kp2"], "home", T5,
      "the young man in the indigo shirt, playful and warm, breaks into a wide grin that "
      "shows both dimples while he speaks; at the same time the woman in the indigo blouse, "
      "laughing through tears, swats his arm with her checked cloth", _N),
 70: (8, "Close-up on the bamboo platform, the mother wrapping a folded paper in the faded red cloth",
      ["kp2", "sa_i"], "home", T6,
      "the woman in the indigo blouse, proud, smiling wide, wraps a folded paper in the same "
      "faded red cloth and ties it with her indigo-stained fingers while she speaks; at the "
      "same time the young man in the indigo shirt, warm, squats beside her watching while "
      "he answers", _N + ["noletter"]),
 71: (8, "Medium, the son and the neighbour harvesting her golden paddy side by side",
      ["pa", "sa_i"], "na_ripe", T6,
      "the woman in the green blouse, kind and beaming, cuts golden rice side by side with "
      "the young man while she speaks; at the same time the young man in the indigo shirt, "
      "laughing, touched, cuts beside her and answers", _N),
 72: (8, "Medium under the house, the mother handing the headman the sticky-rice basket",
      ["kp2", "bm"], "home", T6,
      "the woman in the indigo blouse, warm and forgiving, smiling, holds out a woven "
      "sticky-rice basket while she speaks; at the same time the headman in the light-blue "
      "shirt, moved, eyes wet and red, receives it in both hands and smiles fully at last "
      "while he answers", _N + ["nocash"]),
}

SHOTS = _c.build_shots(_META)

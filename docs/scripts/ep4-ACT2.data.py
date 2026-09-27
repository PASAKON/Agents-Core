# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT2 = EP3 + EP4, shots 24-53 (3:04-7:04). Source of truth for
tools/build_shotsheet.py. Shared blocks: ep4-common.py. Rules: see ep4-ACT1.data.py.

At most 3 people per frame: S34 (the mother sharing sticky rice with "everyone") frames
the son, the mother and the neighbour only; the other helpers are spoken, not shown.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T1, T2, T3 = _c.T1, _c.T2, _c.T3

PROPS_BY_SHOT = {34: ["@kratip"], 40: ["@kratip"], 41: ["@motorbike"], 49: ["@pickup_old"]}

_N = ["nosubs", "noextra"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 24: (8, "Medium wide across the mill yard, the combine harvesters parked in a row behind her",
      ["hong"], "mill_open", T1,
      "the woman in hot pink, arrogant and gleeful, laughing out loud in a shrill voice, "
      "holds a phone to her ear and jabs her closed fan at the parked combine harvesters one "
      "by one while she speaks", _N + ["nologo"]),
 25: (8, "Two-shot at the hot-pink office door, the headman holding his hat in his hands",
      ["hong", "bm"], "mill_open", T1,
      "the woman in hot pink, sweet-voiced with hard angry eyes, points her closed fan at the "
      "headman's face while she speaks; at the same time the headman, afraid and guilty, eyes "
      "down, his woven hat in his hands, twists the checked cloth at his waist and bows his "
      "head while he answers", _N + ["nologo"]),
 26: (8, "Wide, the son alone in the huge golden paddy, a sickle in his hand",
      ["sa_i"], "na_ripe", T2,
      "the young man in the indigo shirt, stubborn, gritting his teeth, panting and drenched "
      "in sweat, his palms red and blistered, hacks clumsily at the standing rice with a "
      "sickle all alone while he talks to himself", _N),
 27: (8, "Two-shot in the rice, the mother guiding his hands on the sickle",
      ["kp2", "sa_i"], "na_ripe", T2,
      "the woman in the indigo blouse, face still stern and hurt but her hands gentle, takes "
      "her son's hands, fixes his grip on the sickle and cuts one clean handful of rice to "
      "show him while she speaks; at the same time the young man in the indigo shirt, moved, "
      "eyes welling, watches her hands", _N),
 28: (8, "Medium wide, the two of them small against the endless gold",
      ["sa_i", "kp2"], "na_ripe", T2,
      "the young man in the indigo shirt, despairing, shoulders dropping, straightens up and "
      "stares across the endless ripe rice while he speaks; at the same time the woman in "
      "the indigo blouse, stubborn, never looking up, keeps bending and cutting faster while "
      "she answers", _N),
 29: (8, "Medium, the neighbour striding down off the paddy dyke with a raised sickle",
      ["pa", "kp2"], "na_ripe", T2,
      "the woman in the green blouse, fierce and loud, strides down off the dyke into the "
      "rice raising her sickle high while she shouts; at the same time the woman in the "
      "indigo blouse, startled, turns with her sickle frozen in her hand and bursts into "
      "tears", _N),
 30: (8, "Two-shot, the mother and the neighbour face to face in the rice",
      ["kp2", "pa"], "na_ripe", T2,
      "the woman in the indigo blouse, worried and afraid for her friend, grips the "
      "neighbour's arm while she speaks; at the same time the woman in the green blouse, "
      "defiant, laughing in her face, shakes her arm free and bends straight down to cut the "
      "rice while she answers", _N),
 31: (8, "Medium, a stocky man jogging into the rice with a sickle, the son turning",
      ["ai", "sa_i", "pa"], "na_thr", T2,
      "the man in the mustard-yellow T-shirt, cheerful, grinning wide, jogs down into the "
      "paddy waving a sickle while he calls out; at the same time the young man in the "
      "indigo shirt, astonished, eyes wide, turns toward the dyke and answers; behind them the "
      "woman in the green blouse smiles while she cuts", _N),
 32: (8, "Close-up on the son in the rice, the sickle in his blistered hand",
      ["sa_i", "kp2"], "na_thr", T2,
      "the young man in the indigo shirt, weeping, shaking with emotion, raises his pressed "
      "palms high above his head toward the dyke in a deep wai while he speaks; behind him "
      "the woman in the indigo blouse wipes her tears with her checked cloth", _N),
 33: (8, "Medium, three harvesters bent over the rice side by side, laughing",
      ["pa", "ai", "sa_i"], "na_thr", T2,
      "the woman in the green blouse, playful, cuts rice fast without stopping while she "
      "teases; at the same time the man in the mustard-yellow T-shirt, laughing out loud, "
      "points his sickle at the young man and teases him while he speaks; the young man in "
      "the indigo shirt, embarrassed, laughs along and cuts slowly", _N),
 34: (8, "Medium at the thatched field hut, the mother sharing out sticky rice",
      ["sa_i", "kp2", "pa"], "na_thr", T2,
      "the young man in the indigo shirt, worried, frowning, leans close to his mother and "
      "whispers while he speaks; at the same time the woman in the indigo blouse, generous, "
      "smiling bravely, keeps pulling sticky rice from a big woven bamboo basket and pressing "
      "it into the neighbour's hands while she answers; the woman in the green blouse eats "
      "gratefully", _N),
 35: (8, "Medium, threshing on the big blue tarp",
      ["sa_i", "kp2"], "na_thr", T2,
      "the young man in the indigo shirt, fired up, sweat pouring, grinning, slams a sheaf of "
      "rice against the slanted wooden threshing board so grain flies while he speaks; at "
      "the same time the woman in the indigo blouse, proud, sweeps the golden grain into the "
      "heap with her hands while she answers", _N),
 36: (8, "Two-shot on the paddy dyke, the headman beside his old black bicycle",
      ["sa_i", "bm"], "na_thr", T2,
      "the young man in the indigo shirt, desperate, pleading, hands pressed together, pleads "
      "with the headman while he speaks; at the same time the headman in the light-blue "
      "shirt, tense and torn, pulls a buzzing phone from his shirt pocket and presses to "
      "reject the call without looking at it", _N),
 37: (8, "Close two-shot, the son hugging the stiff headman",
      ["bm", "sa_i"], "na_thr", T2,
      "the headman in the light-blue shirt, guilty, eyes red, speaks low while the young man "
      "in the indigo shirt, relieved and grateful, throws his arms around him and hugs him "
      "tight; the headman stands stiff with his arms at his sides and cannot hug him back",
      _N),
 38: (8, "Medium at the mill building, the woman in pink pulling down the roll-up shutter",
      ["hong"], "mill_open", T2,
      "the woman in hot pink, cunning, eyes glinting, chuckling low, hauls the roll-up "
      "shutter down with one hand and switches off her phone with the other, dropping it "
      "into a small hot-pink handbag, while she talks to herself", _N + ["nologo"]),
 39: (8, "Medium, sacks of paddy stacked beside the dirt farm track at the harvested field",
      ["sa_i", "ai"], "na_stub", T3,
      "the young man in the indigo shirt, eager, panting and smiling, heaves a plain white "
      "sack of paddy up onto a stack of sacks by the track while he speaks; at the same time "
      "the man in the mustard-yellow T-shirt, hearty, carries another sack on his shoulder "
      "and drops it onto the stack while he answers", _N + ["nologo"]),
 40: (8, "Two-shot under the house, a smaller sticky-rice basket between them",
      ["kp2", "bm"], "home", T3,
      "the woman in the indigo blouse, tired but kind, holds out a small woven sticky-rice "
      "basket while she speaks; at the same time the headman, so guilty his hands tremble, "
      "takes it in both hands and opens his mouth to confess while he answers, swallowing "
      "the words", _N),
 41: (8, "Medium in the yard, the son handing over his motorbike key",
      ["sa_i", "ai"], "home", T3,
      "the young man in the indigo shirt, wistful, with a forced smile, strokes the seat of "
      "the red-and-black motorbike and presses its key into the other man's palm while he "
      "speaks; at the same time the man in the mustard-yellow T-shirt, touched, claps him on "
      "the shoulder while he answers", _N + ["nocash"]),
 42: (8, "Close two-shot on the bamboo platform, the mother's hand on her bare neck",
      ["sa_i", "kp2"], "home", T3,
      "the young man in the indigo shirt, hurting, eyes red, kneels beside his mother while "
      "he speaks; at the same time the woman in the indigo blouse, smiling bravely through "
      "tears, touches her bare neck with her indigo-stained fingers while she answers",
      _N + ["nocash"]),
 43: (8, "Medium, the headman walking fast into the yard",
      ["bm", "kp2", "sa_i"], "home", T3,
      "the headman in the light-blue shirt, hurried and excited, strides fast into the yard "
      "while he speaks; at the same time the woman in the indigo blouse and the young man in "
      "the indigo shirt jump up together from the bamboo platform, hands clasped, and she "
      "answers", _N + ["nocash"]),
 44: (8, "Close two-shot, the son counting on his fingers, the mother's face lighting up",
      ["sa_i", "kp2"], "home", T3,
      "the young man in the indigo shirt, ecstatic, voice shaking, counts out the sums on "
      "his fingers out loud while he speaks; at the same time the woman in the indigo "
      "blouse, laughing and crying at once, presses a hand to her chest", _N + ["nocash"]),
 45: (8, "Medium, the chained steel gate in front of the shuttered mill",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, frantic, shouting at the top of his voice, rattles "
      "the chained steel gate with both hands while he speaks; at the same time behind him "
      "the woman in the indigo blouse, anxious, hugging a plain cloth bag to her chest, looks "
      "left and right while she answers", _N + ["nologo", "nocash"]),
 46: (8, "Two-shot at the gate, the son with a phone at his ear",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, despairing, holds a phone to his ear and rakes his "
      "other hand through his hair while he speaks; at the same time the woman in the indigo "
      "blouse, realising, going pale, stares at the chained gate while she answers",
      _N + ["nologo"]),
 47: (8, "Medium, the mother sitting on the dusty kerb shading her eyes from the sun",
      ["kp2", "sa_i"], "mill_closed", T3,
      "the woman in the indigo blouse, drained, voice faint, sits on the dusty kerb shading "
      "her eyes from the sun with one hand while she speaks; at the same time the young man "
      "in the indigo shirt, restless and stubborn, paces back and forth in front of the gate "
      "while he answers", _N + ["nologo"]),
 48: (8, "Close-up, the son slumped against the chained gate",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, sobbing hard, body shaking, slides down to sit "
      "against the chained steel gate clutching a plain cloth bag of papers while he speaks; "
      "behind him the woman in the indigo blouse strokes his head", _N + ["nologo", "nocash"]),
 49: (8, "Medium wide, an old white pickup pulling up, the headman climbing out",
      ["bm", "kp2", "sa_i"], "mill_closed", T3,
      "the headman in the light-blue shirt, resolved, face strained, eyes red, climbs out of "
      "an old white pickup truck and walks toward them while he speaks; at the same time the "
      "woman in the indigo blouse, puzzled, and the young man in the indigo shirt, his face "
      "tear-streaked, look up at him from the kerb", _N + ["nologo"]),
 50: (8, "Close-up on the headman, the mother behind him",
      ["bm", "kp2"], "mill_closed", T3,
      "the headman, confessing, voice shaking, tears falling, pulls off his wire glasses and "
      "clenches them in his fist while he speaks; at the same time behind him the woman in "
      "the indigo blouse, rigid, slowly rises to her feet", _N),
 51: (8, "Two-shot, the headman and the son",
      ["bm", "sa_i"], "mill_closed", T3,
      "the headman, ashamed, head bowed low, keeps confessing while he speaks; at the same "
      "time the young man in the indigo shirt, enraged, fists clenched, jumps up and glares "
      "into his face", _N + ["nocash"]),
 52: (8, "Medium close-up on the mother facing the headman",
      ["kp2", "bm"], "mill_closed", T3,
      "the woman in the indigo blouse, betrayed, voice trembling, tears running down her "
      "cheeks, walks right up to the headman while she speaks; at the same time the headman, "
      "crying, bows his head lower and lower and cannot look up", _N),
 53: (8, "Close-up, the headman looking up and grabbing the son's arm",
      ["bm", "sa_i"], "mill_closed", T3,
      "the headman, urgent, eyes blazing, looks up and grabs the young man's raised arm while "
      "he speaks; at the same time the young man in the indigo shirt, stunned, freezes with "
      "his fist still in the air while he answers", _N),
}

SHOTS = _c.build_shots(_META)

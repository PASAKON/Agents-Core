# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT3 = EP5 + EP6, shots 54-72 (7:04-9:36). Source of truth for
tools/build_shotsheet.py. Shared blocks: ep4-common.py. Rules: see ep4-ACT1.data.py.

Overflow acting (CEO 2026-09-27, CTO_Story_ThaiMoralDrama §Overflow acting): every person in
frame keeps a physical timeline for the whole shot, every spoken direction is 4-5/5 and
physical (DIRECTION below), and STYLE carries the ensemble rule (ep4-common STYLE_ACTING).

S73-S74 (narrator) are not shot in Flow: slow push-ins on the na__stubble and kratip
plates, made in the edit for no credits.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE_ACTING, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
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
      "the headman in the light-blue shirt, fired up and certain, yanks the passenger door of "
      "the old white pickup wide open, slaps its roof twice and jabs a finger toward the road "
      "while he speaks; the whole time he talks the young man in the indigo shirt, hope rising "
      "in his face, grabs his mother's arm, nods hard at every word and looks from the headman "
      "to her, and the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her head like a turban, hesitant, twists the strap of her cloth bag "
      "in both hands, looks at her son and back at the headman, lips pressed tight; dust blows across "
      "the concrete yard in the hot wind", _N + ["nologo"]),
 55: (8, "Two-shot at the open pickup door, the mother deciding",
      ["bm", "kp2"], "mill_closed", T3,
      "the headman in the light-blue shirt, pleading, eyes wet and red, sweeps an open hand "
      "toward the passenger seat, pats his own chest and bows his head low while he speaks; the "
      "whole time he talks the woman in the indigo blouse, hurt, grips the edge of the pickup "
      "door, looks away, swallows hard and slowly turns back to face him; the instant he "
      "finishes she lifts her chin, climbs up onto the passenger seat in one firm step and "
      "slaps the dashboard while she answers; dry leaves skitter across the concrete yard",
      _N + ["nologo"]),
 56: (8, "Medium wide, the old pickup stopped at the foot of the white building's steps",
      ["sa_i", "bm"], "land", T3,
      "the young man in the indigo shirt, breathless and excited, jumps down from the old "
      "white pickup, jabs at the time on his phone screen and bounces on his toes while he "
      "speaks; the whole time he talks the headman in the light-blue shirt leans far out of the driver's window, drums "
      "both hands on the door and keeps glancing at the building's glass doors; the instant he "
      "finishes the headman flaps both hands at him toward the steps while he answers; the "
      "leaves of the potted plants by the steps shiver in the hot wind",
      _N + ["nologo", "nouniform"]),
 57: (8, "Medium, the son pulling his mother by the hand up the concrete steps",
      ["sa_i", "kp2"], "land", T3,
      "the young man in the indigo shirt, desperately hopeful, runs up the concrete steps two "
      "at a time pulling his mother by the hand, pointing ahead at the open glass doors and "
      "looking back at her again and again while he speaks; the whole time he talks the woman "
      "in the indigo blouse, out of breath, lifts the hem of her ikat skirt with her free hand, "
      "stumbles on one step, catches herself and keeps climbing, her eyes fixed on the doors; "
      "the instant he finishes she lets go of his hand and pushes him on ahead, panting, while "
      "she answers; a sparrow flutters off the step railing", _N + ["nouniform"]),
 58: (8, "Medium, the son coming out through the glass doors holding up a paper receipt",
      ["sa_i", "kp2"], "land", T3,
      "the young man in the indigo shirt, overjoyed, trembling, laughing through tears, bursts "
      "out through the glass doors waving a small paper receipt high, its back to the camera, "
      "presses his other fist to his mouth and stops for breath as his voice shakes while he "
      "speaks; the whole time he talks the woman in the indigo blouse on the porch, her red-and-white checked cloth still wrapped around her head like a turban, presses her "
      "palms together at her lips, rises on her toes, gasps at each word, her eyes filling, "
      "and grabs the rail as her knees give way a little; a warm breeze lifts the hem of her "
      "skirt", _N + ["noletter", "nouniform", "nocash"]),
 59: (8, "Close two-shot on the porch, the mother pressing the receipt to her chest",
      ["kp2", "sa_i"], "land", T3,
      "the woman in the indigo blouse, weeping with joy, body shaking, presses the small paper "
      "receipt flat against her chest with both hands, its face against her blouse, rocks back "
      "and forth and lifts her wet face to the sky while she speaks; the whole time she talks "
      "the young man in the indigo shirt, crying, wraps both arms around her, rubs her back and "
      "nods hard against her hair; the instant she finishes he pulls back, holds her face in "
      "both hands and wipes her tears with his thumbs while he answers; a bird flutters up "
      "from the porch railing", _N + ["noletter", "nouniform"]),
 60: (8, "Medium, the headman standing apart at the foot of the steps",
      ["bm", "kp2"], "land", T3,
      "the headman in the light-blue shirt, repentant, eyes red, stands apart at the foot of "
      "the steps crushing his woven hat against his chest, lifts his head to meet her eyes "
      "and taps his own chest twice with his fist on the promise while he speaks; the whole "
      "time he talks the woman in the indigo blouse on the steps above turns slowly to look "
      "at him, unsmiling, arms folded, jaw tight; at his promise her arms loosen and she gives "
      "one small slow nod; dust swirls across the empty car park behind him",
      _N + ["nouniform", "nocash"]),
 61: (8, "Medium, the woman in pink at a desk just inside the open hot-pink office door, reading a message on her phone",
      ["hong"], "mill_open", T4,
      "the woman in hot pink, outraged, face flushed red, eyes bulging, reads a message on her phone out loud, the back of the phone toward the "
      "camera, brings it closer to her face, puts the phone face-down on the desk and throws up both hands while she speaks, shaking her head in "
      "disbelief; outside the open door a sparrow hops across the sunlit concrete",
      _N + ["nologo"]),
 62: (8, "Close-up, the woman in pink shouting into her phone",
      ["hong"], "mill_open", T4,
      "the woman in hot pink, beside herself with rage, face twisted, shouts into the phone "
      "pressed to her ear, stamps her foot, slams her closed fan down on the desk again and "
      "again, jabs the phone screen with her thumb to redial and presses it back to her ear "
      "while she speaks, a lock of hair falling loose that she shoves off her face; outside "
      "the open door the bright yard shimmers in the heat", _N + ["nologo"]),
 63: (8, "Medium in the harvested paddy of stubble and straw stacks",
      ["hong", "sa_ic"], "na_stub", T4,
      "the woman in hot pink, annoyed and loud, walks across the stubble under her open hot-pink "
      "parasol, flicks the loose straw aside with her foot and waves her closed fan in the air "
      "while she speaks; the whole time she talks the young man in the indigo shirt, calm and "
      "sure, keeps twisting a bundle of straw tight, sets it down on a stack, dusts his palms "
      "against each other and turns to her; the instant she finishes he "
      "looks at her calmly and gives a small polite smile while he "
      "answers; loose straw blows across the stubble", _N),
 64: (8, "Medium, the neighbour stepping up beside the son with a bundle of straw",
      ["hong", "pa", "sa_i"], "na_stub", T4,
      "the woman in hot pink, scowling, stabs her closed fan toward the whole field, stamps "
      "her foot in the stubble and wags her finger at them while she speaks; the whole time "
      "she talks the woman in the green blouse, a bundle of straw under one arm, strides up "
      "beside the young man, rolls her eyes and plants her free hand on her hip, and the young "
      "man in the indigo shirt folds his arms and bites back a grin; the instant she finishes "
      "the woman in the green blouse throws her head back laughing, swings the straw onto her "
      "shoulder and waves her off while she answers, and the young man laughs out loud; straw "
      "dust glitters in the sunlight", _N),
 65: (8, "Medium, the woman in pink stalking off, the mother calling after her from the field hut",
      ["kp2", "hong"], "na_stub", T4,
      "the woman in the indigo blouse, calm and kind with no anger left, steps down from the "
      "field hut, holds out a woven sticky-rice basket in both hands, lifts its lid and smiles "
      "while she calls after her and speaks; the whole time she talks the woman in hot pink, "
      "stalking away across the stubble, slows, her shoulders stiffen, she stops short and "
      "grips her closed fan hard; the instant she finishes the woman in hot pink turns with her "
      "mouth open, face flushing red, snaps her fan open in front of her face and spins away "
      "while she answers; a hen pecks at the stubble between them", _N),
 66: (8, "Wide, the mill yard with every combine harvester parked and idle",
      ["hong"], "mill_open", T5,
      "the woman in hot pink, anxious and restless, drenched in sweat, fans herself hard with "
      "a phone pressed to her ear and walks in fast circles around the idle combine "
      "harvesters, slapping the dusty side of one, checking the phone screen and jamming it "
      "back to her ear while she speaks, her voice climbing; the empty yard shimmers in the "
      "heat and a dry leaf skitters past her feet", _N + ["nologo"]),
 67: (8, "Medium close-up, the woman in pink sinking onto an empty rice sack",
      ["hong"], "mill_open", T5,
      "the woman in hot pink, pleading into her phone, voice cracking, clutches the phone in "
      "both hands and bows to it as if the caller could see her, sinks slowly down onto an "
      "empty plain white sack, the fan slipping from her fingers to the concrete, and presses "
      "the back of her wrist to her wet eyes while she speaks, her shoulders shaking; behind "
      "her the idle harvesters sit silent under a film of dust", _N + ["nologo", "nocash"]),
 68: (8, "Two-shot under the house beside the tin trunk, the son holding a small bundle wrapped in red cloth",
      ["sa_i", "kp2"], "home", T5,
      "the young man in the indigo shirt, a red-and-white checked cloth tied round his head, a small bundle wrapped in red cloth in both hands, serious and unreadable, sits down on the bamboo "
      "platform, rests the red cloth bundle on his knees, turns to his mother and holds her eyes "
      "without blinking while he speaks; the whole time he talks the woman in the indigo "
      "blouse, her red-and-white checked cloth still wrapped around her head like a turban, frightened, freezes with a woven sticky-rice basket half lowered, her smile "
      "falling away, her free hand creeping to her chest; the instant he finishes she sets "
      "the basket down on the bamboo platform with a thump, grabs his wrist and leans in close "
      "while she answers; a hen clucks and scurries under the platform", _N),
 69: (8, "Two-shot on the bamboo platform, the son breaking into a dimpled grin",
      ["sa_i", "kp2"], "home", T5,
      "the young man in the indigo shirt, playful and warm, breaks into a wide grin that shows "
      "both dimples, spreads his arms wide, mimes swinging a sickle through rice and thumps "
      "his own chest while he speaks; the whole time he talks the woman in the indigo blouse, "
      "her red-and-white checked cloth still wrapped around her head like a turban, gasps, clutches her chest, bursts into laughter through her tears, swats his arm again "
      "and again with the flat of her hand and pulls him into a rough hug; a hen struts across "
      "the red dirt behind them", _N),
 70: (8, "Close-up on the bamboo platform, the mother wrapping a folded paper in the faded red cloth",
      ["kp2", "sa_i"], "home", T6,
      "the woman in the indigo blouse, proud, smiling wide, eyes shining, smooths a folded "
      "paper flat on the bamboo platform, wraps it in the same faded red cloth, ties it in a "
      "firm double knot with her indigo-stained fingers, pats the bundle twice and lays it in "
      "the open old tin trunk beside her while she speaks; the whole time she talks the young "
      "man in the indigo shirt squats beside her, grinning and nodding, reaches to help and "
      "gets his hand swatted away playfully; the instant she finishes he laughs, points to her "
      "bare neck where the gold chain used to hang and nods solemnly while he answers; soft "
      "morning light moves across the dust", _N + ["noletter"]),
 71: (8, "Medium, the son and the neighbour harvesting her golden paddy side by side",
      ["pa", "sa_i"], "na_ripe", T6,
      "the woman in the green blouse, kind and beaming, grabs a fistful of golden rice "
      "stalks, cuts them with a quick stroke of her sickle, lays the bundle on the pile and "
      "nudges the young man with her elbow while she speaks; the whole time she talks the "
      "young man in the indigo shirt keeps cutting beside her, stops, wipes the sweat from his "
      "brow with his forearm and stares at her, his eyes filling; the instant she finishes he "
      "laughs, touched, presses his palms together in a quick wai with the rice still in his "
      "hand and bows while he answers; the golden rice sways in the wind around them", _N),
 72: (8, "Medium under the house, the mother handing the headman the sticky-rice basket",
      ["kp2", "bm"], "home", T6,
      "the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her head like a turban, warm and forgiving, smiling, lifts the lid of a woven "
      "sticky-rice basket, holds it out with both hands and pats the bamboo platform beside "
      "her, inviting him to sit, while she speaks; the whole time she talks the headman in the "
      "light-blue shirt, moved, eyes wet and red, twists his woven hat in his hands and takes "
      "one unsure step closer; the instant she finishes he receives the basket in both hands, "
      "bows over it, sits down heavily beside her and smiles fully at last, his chin "
      "trembling, while he answers; a hen scurries past and steam drifts up from the steamer",
      _N + ["nocash"]),
}

# (shot, speaker) -> overflow-acting direction, 4-5/5 and physical; strict in apply_directions.
DIRECTION = {
 (54, "bm"): "fired up and certain, almost shouting with urgency, slapping the pickup roof, jabbing a "
             "finger at the road",
 (55, "bm"): "pleading, voice thick with tears, eyes wet and red, patting his own chest, head bowed low",
 (55, "kp2"): "hurt but fiercely resolved, voice hard and loud, chin lifted, slapping the dashboard",
 (56, "sa_i"): "breathless and frantic with excitement, almost shouting, jabbing at the phone screen, "
               "bouncing on his toes",
 (56, "bm"): "urgent, shouting out of the driver's window, flapping both hands",
 (57, "sa_i"): "desperately hopeful, shouting over his shoulder as he runs, voice cracking with hope",
 (57, "kp2"): "gasping for breath, laughing and panting at once, pushing him on",
 (58, "sa_i"): "overjoyed, sobbing and laughing at once, voice shaking so hard he gulps for breath, "
               "waving the receipt high",
 (59, "kp2"): "weeping with joy, loud broken sobs, voice breaking on every word, rocking with the "
              "receipt pressed to her chest",
 (59, "sa_i"): "crying openly, voice thick and trembling, holding her face in both hands",
 (60, "bm"): "repentant, voice rough and low but firm, eyes red, fist tapping his chest on the promise",
 (61, "hong"): "outraged, shrill, face red, eyes wide, throwing up her hands",
 (62, "hong"): "hysterical with rage, screaming into the phone, slamming the fan on the desk again and "
               "again",
 (63, "hong"): "annoyed, shrill, waving her fan",
 (63, "sa_ic"): "calm and polite, in Central Thai, a small smile, "
                "every word calm and clear",
 (64, "hong"): "threatening, shouting and stamping, wagging her finger, face twisted in a scowl",
 (64, "pa"): "defiant and mocking, laughing out loud, hand on hip, waving her off",
 (65, "kp2"): "warm and generous, calling out loud and bright, smiling, holding out the basket",
 (65, "hong"): "humiliated, face burning red, voice cracking into a shrill snap, hiding behind her fan",
 (66, "hong"): "frantic, sweat pouring, voice rising to a panicky shout, fanning herself furiously",
 (67, "hong"): "broken and begging, voice cracking and collapsing into sobs, pressing her wrist to her "
               "wet eyes",
 (68, "sa_i"): "grave and unreadable, voice low and slow, holding her eyes without blinking",
 (68, "kp2"): "frightened, voice trembling and high, grabbing his wrist",
 (69, "sa_i"): "bursting with playful joy, grinning with both dimples, loud and teasing, thumping his "
               "chest",
 (70, "kp2"): "proud and beaming, voice strong and bright, patting the tied bundle",
 (70, "sa_i"): "warm and solemn, grinning through wet eyes, pointing at her bare neck",
 (71, "pa"): "kind and beaming, loud and cheerful, nudging him with her elbow",
 (71, "sa_i"): "laughing, deeply touched, voice catching, a quick wai with the rice in his hand",
 (72, "kp2"): "warm and forgiving, loud and welcoming, laughing, patting the platform beside her",
 (72, "bm"): "overcome, voice cracking, tears spilling, chin trembling, a full smile at last",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

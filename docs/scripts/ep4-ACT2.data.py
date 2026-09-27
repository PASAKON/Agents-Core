# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT2 = EP3 + EP4, shots 24-53 (3:04-7:04). Source of truth for
tools/build_shotsheet.py. Shared blocks: ep4-common.py. Rules: see ep4-ACT1.data.py.

At most 3 people per frame: S34 (the mother sharing sticky rice with "everyone") frames
the son, the mother and the neighbour only; the other helpers are spoken, not shown.

Overflow acting (CEO 2026-09-27, story skill §Overflow acting): every action is a timeline for
everyone in frame, every spoken direction is 4-5/5 (DIRECTION below), STYLE is STYLE_ACTING.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE_ACTING, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T1, T2, T3 = _c.T1, _c.T2, _c.T3

PROPS_BY_SHOT = {34: ["@kratip"], 40: ["@kratip"], 41: ["@motorbike"], 49: ["@pickup_old"]}

_N = ["nosubs", "noextra"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 24: (8, "Medium wide across the mill yard, the combine harvesters parked in a row behind her",
      ["hong"], "mill_open", T1,
      "the woman in hot pink, arrogant and gleeful, laughing out loud in a shrill voice, "
      "presses a phone to her ear and struts along the row of parked combine harvesters, "
      "jabbing her closed fan at each one in turn, slapping the fan against her palm and "
      "tossing her head back to cackle in the middle of her line while she speaks; dust and "
      "chaff drift through the hot sunlight across the mill yard behind her", _N + ["nologo"]),
 25: (8, "Two-shot at the hot-pink office door, the headman holding his hat in his hands",
      ["hong", "bm"], "mill_open", T1,
      "the woman in hot pink, sweet-voiced with hard angry eyes, flicks her fan open and snaps "
      "it shut, jabs it at the headman's face and taps the brim of the hat in his hands with "
      "it, leaning in close while she speaks; the whole time she talks the headman in the "
      "light-blue shirt, afraid and guilty, clutches his woven hat to his stomach, twists the "
      "checked cloth at his waist into a knot, shifts from foot to foot and flinches at every "
      "jab of the fan; the instant she finishes he bows his head again and again, nodding too "
      "fast, while he answers; chaff drifts across the sunny yard behind them",
      _N + ["nologo"]),
 26: (8, "Wide, the son alone in the huge golden paddy, a sickle in his hand",
      ["sa_i"], "na_ripe", T2,
      "the young man in the indigo shirt, stubborn, gritting his teeth, panting and drenched "
      "in sweat, hacks clumsily at the standing rice with a sickle all alone while he grumbles "
      "out loud: he grabs a fistful of stalks and saws at them, winces and shakes out his "
      "red blistered palm, wipes the sweat from his eyes with his forearm, blows on his hand "
      "and grabs the next fistful even harder; the tall golden rice sways all around him in "
      "the hot wind", _N),
 27: (8, "Two-shot in the rice, the mother guiding his hands on the sickle",
      ["kp2", "sa_i"], "na_ripe", T2,
      "the woman in the indigo blouse, face still stern and hurt but her hands gentle, takes "
      "her son's hands, fixes his grip on the sickle, taps his knuckles to loosen them, pulls "
      "a handful of rice toward them and cuts one clean stroke to show him while she speaks; "
      "the whole time she talks the young man in the indigo shirt, moved, eyes welling, "
      "watches her hands closely, nods hard, copies the grip, sniffs and blinks back tears "
      "with trembling lips; loose rice ears fall at their feet and the paddy sways in the "
      "wind", _N),
 28: (8, "Medium wide, the two of them small against the endless gold",
      ["sa_i", "kp2"], "na_ripe", T2,
      "the young man in the indigo shirt, despairing, shoulders dropping, straightens up, "
      "flings one arm wide at the endless ripe rice and lets it fall slapping against his leg, "
      "shaking his head while he speaks; the whole time he talks the woman in the indigo "
      "blouse, stubborn, never looks up: she keeps bending, grabbing and cutting faster and "
      "faster, tossing each cut handful onto the pile behind her; the instant he finishes she "
      "jabs her sickle at the next row without looking at him while she answers; the whole "
      "golden field ripples in the hot wind around the two small figures", _N),
 29: (8, "Medium, the kind neighbour walking down off the paddy bank to help with the harvest, waving",
      ["pa", "kp2"], "na_ripe", T2,
      "the woman in the green blouse, warm, loud and determined, walks briskly down off the "
      "paddy bank into the rice with a big smile, rolls up her sleeve, pats her own chest with one "
      "hand and sweeps it over the field while she calls out; the whole time she talks the "
      "woman in the indigo blouse, her red-and-white checked cloth still wrapped around her "
      "head like a turban, turns with a bundle of cut rice stalks in her hands, her mouth "
      "falls open, her chin trembles and she bursts into grateful tears; the ripe rice parts "
      "and sways as the neighbour pushes through it", _N),
 30: (8, "Two-shot, the mother and the neighbour face to face in the rice",
      ["kp2", "pa"], "na_ripe", T2,
      "the woman in the indigo blouse, worried and afraid for her friend, grips the "
      "neighbour's arm with both hands, glances back toward the road and shakes the arm "
      "urgently, eyes wet, while she speaks; the whole time she talks the woman in the green "
      "blouse, defiant, rolls her eyes, snorts and grins; the instant she finishes the woman "
      "in the green blouse laughs right in her face, shakes her arm free, flaps a dismissive "
      "hand and bends straight down to grab a fistful of rice and cut it with one hard stroke "
      "while she answers; cut stalks fly and the paddy sways", _N),
 31: (8, "Medium, a friendly stocky neighbour hurrying into the rice to help with the harvest, waving, the son turning",
      ["ai", "sa_i", "pa"], "na_thr", T2,
      "the man in the mustard-yellow T-shirt, cheerful, grinning wide, jogs down off the paddy bank "
      "into the half-cut paddy, waving both empty hands high over his head and laughing "
      "while he calls out; the whole time he talks the young man in the indigo "
      "shirt, astonished, straightens up with an armful of cut rice stalks, eyes wide, "
      "mouth open, and wipes his face in disbelief; the instant he finishes the young man "
      "spins toward the paddy bank and points while he answers; behind them the woman in the green "
      "blouse keeps gathering sheaves fast, laughing and stacking them; chaff drifts "
      "in the sun", _N),
 32: (8, "Close-up on the grateful son in the rice, thanking the neighbours who came to help with the harvest, cut sheaves stacked around him",
      ["sa_i", "kp2"], "na_thr", T2,
      "the young man in the indigo shirt, overwhelmed with gratitude, happy tears, raises his pressed "
      "palms high above his head toward the paddy bank in a deep wai, bows twice and turns to wai "
      "the other way, tears running down his face, while he speaks; the whole time he talks "
      "the woman in the indigo blouse behind him, her red-and-white checked cloth still wrapped around her head like a turban, wipes her tears with the back of her hand, "
      "nods again and again, presses her hand to her chest and smiles through her crying; "
      "rice sheaves stand stacked around them and chaff drifts in the sunlight", _N),
 33: (8, "Medium, three harvesters bent over the rice side by side, laughing",
      ["pa", "ai", "sa_i"], "na_thr", T2,
      "the woman in the green blouse, playful, cuts rice fast without stopping and tosses "
      "each handful onto the pile behind her with a flourish, grinning over her shoulder, "
      "while she teases; the whole time she talks the man in the mustard-yellow T-shirt "
      "chuckles and speeds up his cutting to race her; the instant she finishes he stops, "
      "laughing out loud, points his sickle at the young man and waggles it while he teases; "
      "the young man in the indigo shirt, embarrassed, laughs along, scratches his head, "
      "flaps a hand at them and keeps cutting slowly and clumsily; chaff flies up and drifts "
      "in the sun", _N),
 34: (8, "Medium at the thatched field hut, the mother sharing out sticky rice",
      ["sa_i", "kp2", "pa"], "na_thr", T2,
      "the young man in the indigo shirt, worried, frowning, leans close to his mother, "
      "glances at the woman in the green blouse and cups his hand beside his mouth while he "
      "speaks low and urgent; the whole time he talks the woman in the indigo blouse, generous, keeps "
      "pulling sticky rice from a big woven bamboo basket, rolling it into balls in her "
      "fingers and pressing them into the neighbour's hands; the instant he finishes she "
      "waves his warning away with a laugh, pats his cheek and pushes a ball of rice into his "
      "hand too while she answers; the woman in the green blouse eats gratefully, nodding and "
      "licking her fingers; a hen pecks at dropped grains beside the thatched hut", _N),
 35: (8, "Medium, threshing on the big blue tarp",
      ["sa_i", "kp2"], "na_thr", T2,
      "the young man in the indigo shirt, fired up, sweat pouring, grinning, swings a sheaf "
      "of rice high and slams it against the slanted wooden threshing board again and again "
      "so grain flies, whooping between strikes, while he speaks; the whole time he talks the "
      "woman in the indigo blouse, proud, crouches on the big blue tarp sweeping the golden "
      "grain into the heap with her hands and flicking the straw away; the instant he "
      "finishes she sits back on her heels, laughs and slaps the heap while she answers; "
      "golden grain bounces across the blue tarp and chaff sparkles in the sun", _N),
 36: (8, "Two-shot on the paddy bank, the headman beside his old black bicycle",
      ["sa_i", "bm"], "na_thr", T2,
      "the young man in the indigo shirt, worried, hands pressed together in a polite wai, points back at the heaps of threshed rice, his "
      "voice cracking, while he speaks; the whole time he talks the headman in the "
      "light-blue shirt, uneasy, grips the handlebar of his old black bicycle, looks down and rubs the back of his neck, and when a phone buzzes in his shirt pocket he glances at it and silences it; the "
      "rice stubble around them rustles in the wind", _N),
 37: (8, "Close two-shot, the son hugging the stiff headman",
      ["bm", "sa_i"], "na_thr", T2,
      "the headman in the light-blue shirt, guilty, eyes red, rubs his face with both hands, "
      "looks away across the field and pats the shirt pocket where his phone is, speaking "
      "low while he speaks; the whole time he talks the young man in the indigo shirt leans "
      "in, hanging on every word, his eyes widening with hope; the instant he finishes the "
      "young man, relieved and grateful, laughs out loud, grabs his hand in both of his and shakes it hard while he answers; the headman nods, blinking fast, and pats his shoulder once; the old black "
      "bicycle leans on the paddy bank behind them", _N),
 38: (8, "Medium at the mill building, the woman in pink pulling down the roll-up shutter",
      ["hong"], "mill_open", T2,
      "the woman in hot pink, cunning, eyes glinting, chuckling low, hauls the roll-up "
      "shutter down with one hand, switches off her phone with the other and drops it into a "
      "small hot-pink handbag, snaps the bag shut, slaps the dust off her palms and flicks "
      "her fan open with a satisfied smirk, all while she gloats out loud; the shutter "
      "rattles and clangs down behind her and dust puffs up off the concrete",
      _N + ["nologo"]),
 39: (8, "Medium, sacks of paddy stacked beside the dirt farm track at the harvested field",
      ["sa_i", "ai"], "na_stub", T3,
      "the young man in the indigo shirt, eager, panting and smiling, heaves a plain white "
      "sack of paddy up onto the stack by the track, slaps it flat with both hands and counts "
      "the stack with a jabbing finger while he speaks; the whole time he talks the man in "
      "the mustard-yellow T-shirt, hearty, trudges up with another sack on his shoulder, "
      "grunting and grinning; the instant he finishes the man drops the sack onto the stack "
      "with a thump, dusts off his shoulder and thumps his own chest while he answers; dust "
      "puffs up from the sacks and the stubble field glows in the sun", _N + ["nologo"]),
 40: (8, "Two-shot under the house, a smaller sticky-rice basket between them",
      ["kp2", "bm"], "home", T3,
      "the woman in the indigo blouse, tired but kind, holds out a small woven sticky-rice "
      "basket in both hands, pushes it toward him when he hesitates and brushes a bit of "
      "chaff off his sleeve, smiling, while she speaks; the whole time she talks the "
      "headman, so guilty his hands tremble, stares at the basket, swallows hard and wipes "
      "his palms on his trousers; the instant she finishes he takes the basket in both "
      "trembling hands, opens his mouth to confess, lifts one hand as if to say something and "
      "swallows the words, shaking his head with a sick smile, while he answers; a hen "
      "scratches in the red dirt under the house", _N),
 41: (8, "Medium in the yard, the son handing over his motorbike key",
      ["sa_i", "ai"], "home", T3,
      "the young man in the indigo shirt, wistful, with a forced smile, strokes the seat of "
      "the red-and-black motorbike, pats its tank twice and presses its key into the other "
      "man's palm, folding the man's fingers over it, while he speaks; the whole time he "
      "talks the man in the mustard-yellow T-shirt, touched, shakes his head, tries to push "
      "the key back and looks away blinking; the instant he finishes the man in the "
      "mustard-yellow T-shirt claps him hard on the shoulder, squeezes it and pats the "
      "motorbike's seat too while he answers; hens scatter across the red-dirt yard",
      _N + ["nocash"]),
 42: (8, "Close two-shot on the bamboo platform, the mother's hand on her bare neck",
      ["kp2", "sa_i"], "home", T3,
      "the young man in the indigo shirt, hurting, eyes red, kneels beside his mother on the "
      "bamboo platform, grips her hand, stares at her bare neck and bites his lip hard, his "
      "voice breaking, while he speaks; the whole time he talks the woman in the indigo "
      "blouse, her red-and-white checked cloth still wrapped around her head like a turban, "
      "strokes his hair; the instant he finishes she touches her bare neck with her "
      "indigo-stained fingers, gives a little laugh, taps his nose and wipes his tears with "
      "her thumb, her own tears spilling, while she answers; steam drifts from the "
      "sticky-rice steamer behind them", _N + ["nocash"]),
 43: (8, "Medium, the headman walking fast into the yard",
      ["bm", "kp2", "sa_i"], "home", T3,
      "the headman in the light-blue shirt, hurried and excited, out of breath and grinning, "
      "strides fast into the yard waving his phone high over his head while he speaks; the "
      "whole time he talks the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her head like a turban, her neck bare with no necklace, and the young man in the indigo "
      "shirt jump up together from the bamboo platform, clutching each other's hands, "
      "bouncing on their toes, their mouths falling open; the instant he finishes she presses "
      "her clasped hands to her lips and bows to him again and again while she answers; hens "
      "flap out of the headman's way across the red dirt", _N + ["nocash"]),
 44: (8, "Close two-shot, the son counting on his fingers, the mother's face lighting up",
      ["sa_i", "kp2"], "home", T3,
      "the young man in the indigo shirt, ecstatic, voice shaking, counts out the sums on "
      "the fingers of both hands out loud, bouncing on his knees and shaking his fists in the "
      "air, laughing and crying, while he speaks; the whole time he talks the woman in the "
      "indigo blouse, laughing and crying at once, presses a hand to her chest, grabs his "
      "shoulders and shakes him, strokes his face and looks up at the sky mouthing thanks; "
      "the sticky-rice steamer puffs steam behind them", _N + ["nocash"]),
 45: (8, "Medium, the locked steel gate in front of the closed mill",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, desperate, calling out loudly, holds the locked steel gate with both hands and looks "
      "through the bars toward the empty mill office while he speaks; the whole time he talks the woman in "
      "the indigo blouse behind him, anxious, hugs a plain cloth bag to her chest, cranes her "
      "neck left and right down the empty road and rises on tiptoe to look over the gate; the "
      "instant he finishes she tugs his sleeve and shakes her head while she answers; the "
      "chain clanks against the bars and dust blows across the empty concrete yard",
      _N + ["nologo", "nocash"]),
 46: (8, "Two-shot at the gate, the son with a phone at his ear",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, despairing, holds a phone to his ear, pulls it away "
      "to glare at it and jabs at it again, raking his other hand through his hair, while he "
      "speaks; the whole time he talks the woman in the indigo blouse, her red-and-white "
      "checked cloth still wrapped around her head like a turban, realising, going pale, "
      "stares at the chained gate, one hand rising slowly to her mouth, the other clutching "
      "the cloth bag; the instant he finishes she grips the gate bars with a shaking hand and "
      "turns to him wide-eyed while she answers; dry leaves skitter across the empty yard",
      _N + ["nologo"]),
 47: (8, "Medium, the mother sitting on the dusty kerb shading her eyes from the sun",
      ["kp2", "sa_i"], "mill_closed", T3,
      "the woman in the indigo blouse, drained, voice faint, sits on the dusty kerb shading "
      "her eyes from the sun with one hand, fanning her face with the other and squinting up "
      "at the sky to judge the time, lips trembling, while she speaks; the whole time she "
      "talks the young man in the indigo shirt, restless and stubborn, paces back and forth "
      "in front of the gate, kicks a pebble and grips his hair; the instant she finishes he "
      "stops, plants his feet, crosses his arms and glares at the road while he answers; "
      "heat shimmers over the concrete and dust blows past the gate", _N + ["nologo"]),
 48: (8, "Close-up, the son slumped against the chained gate",
      ["sa_i", "kp2"], "mill_closed", T3,
      "the young man in the indigo shirt, sobbing hard, body shaking, slides down the chained "
      "steel gate to sit on the ground clutching a plain cloth bag of papers to his chest, "
      "beats his fist against his knee and rocks back and forth, tears running, while he "
      "speaks; the whole time he talks the woman in the indigo blouse, her red-and-white "
      "checked cloth still wrapped around her head like a turban, kneels behind him, "
      "strokes his head, pulls him against her shoulder and rocks with him, her own tears "
      "falling; the chain on the gate clinks and dust blows across the yard",
      _N + ["nologo", "nocash"]),
 49: (8, "Medium wide, an old white pickup pulling up, the headman climbing out",
      ["bm", "kp2", "sa_i"], "mill_closed", T3,
      "the headman in the light-blue shirt, resolved, face strained, eyes red, climbs out of "
      "an old white pickup truck, swings the door shut behind him and walks toward them "
      "rubbing his palms together, his voice cracking, while he speaks; the whole time he "
      "talks the woman in the indigo blouse, puzzled, rises halfway from the kerb clutching "
      "the cloth bag, and the young man in the indigo shirt, his face tear-streaked, wipes "
      "his face with his sleeve and scrambles to his feet, both staring at him; dust drifts "
      "up behind the pickup's wheels", _N + ["nologo"]),
 50: (8, "Close-up on the headman, the mother behind him",
      ["bm", "kp2"], "mill_closed", T3,
      "the headman in the light-blue shirt and his woven bamboo sun hat, confessing, voice shaking, tears falling, pulls off his wire glasses, "
      "clenches them in his fist, presses the fist to his chest and bows his head, sobbing "
      "between the words, while he speaks; the whole time he talks the woman in the indigo "
      "blouse behind him, her red-and-white checked cloth still wrapped around her head like a turban, rigid, slowly rises to her feet, her face turning from confusion to "
      "horror, one hand covering her mouth, the other clutching the cloth bag tight to her "
      "chest; dust blows across the empty concrete yard", _N),
 51: (8, "Two-shot, the headman and the son",
      ["bm", "sa_i"], "mill_closed", T3,
      "the headman, ashamed, head bowed low, keeps confessing, wringing his glasses in both "
      "hands and shaking his head at himself, tears dripping, while he speaks; the whole time "
      "he talks the young man in the indigo shirt, enraged, jumps up, fists clenched, "
      "breathing hard, and steps right into his face, jaw tight, veins standing out on his "
      "neck, one fist drawing back to shoulder height; dust blows past the chained gate",
      _N + ["nocash"]),
 52: (8, "Medium close-up on the mother facing the headman",
      ["kp2", "bm"], "mill_closed", T3,
      "the woman in the indigo blouse, betrayed, voice trembling, tears running down her "
      "cheeks, walks right up to the headman, jabs a finger at his chest, grabs his shirt "
      "front and shakes it, her voice rising to a cry, while she speaks; the whole time she "
      "talks the headman, crying, bows his head lower and lower, sags at the knees, presses "
      "his palms together and cannot look up; heat shimmers over the empty yard behind them",
      _N),
 53: (8, "Close-up, the headman looking up and grabbing the son's arm",
      ["bm", "sa_i"], "mill_closed", T3,
      "the headman, urgent, eyes blazing, looks up sharply, grabs the young man's raised arm "
      "with one hand and jabs the other toward the road while he speaks; the whole time he "
      "talks the young man in the indigo shirt, stunned, freezes with his fist still in the "
      "air, his angry face slackening into confusion, his chest heaving; the instant he "
      "finishes the young man lowers his fist slowly, grips the headman's wrist and leans in "
      "while he answers; dust whirls up off the road beside the gate", _N),
}

DIRECTION = {
 (24, "hong"): "gleeful and shrill, cackling out loud in the middle of the line, jabbing the fan at each harvester",
 (25, "hong"): "syrupy sweet voice with ice-cold eyes, hissing the threat, jabbing the fan at his face",
 (25, "bm"): "terrified and cowed, voice shrinking, bobbing his head, twisting his cloth",
 (26, "sa_i"): "panting hard, gritting his teeth, growling the words, hacking at the rice",
 (27, "kp2"): "stern and hurt, voice thick with held-back tears, her hands gentle",
 (28, "sa_i"): "despairing, voice breaking, shoulders slumping, one arm flung at the field",
 (28, "kp2"): "stubborn and fierce, snapping the words without looking up, cutting faster",
 (29, "pa"): "warm and very loud, calling across the paddy, big smile, one arm waving",
 (30, "kp2"): "frightened for her friend, voice urgent and shaking, gripping her arm",
 (30, "pa"): "defiant, laughing out loud in her face, already cutting",
 (31, "ai"): "booming and cheerful, grinning ear to ear, waving his hand",
 (31, "sa_i"): "astonished, voice cracking with disbelief, eyes wide, pointing",
 (32, "sa_i"): "grateful, weeping with happiness, voice breaking, palms pressed high above his head",
 (33, "pa"): "playful and teasing, cackling, cutting fast",
 (33, "ai"): "roaring with laughter, teasing loudly, waggling his sickle",
 (34, "sa_i"): "anxious, low and urgent but clearly audible, frowning hard, hand cupped to his mouth",
 (34, "kp2"): "warm and generous, laughing, pressing rice into their hands",
 (35, "sa_i"): "fired up and shouting, sweat pouring, whooping between strikes",
 (35, "kp2"): "proud and laughing, slapping the grain heap",
 (36, "sa_i"): "worried and asking, voice cracking, palms pressed together",
 (37, "bm"): "low and guilty, voice hoarse, eyes red, rubbing his face",
 (37, "sa_i"): "overjoyed with relief, laughing and choking up, shaking his hand",
 (38, "hong"): "cunning and gloating, a low wicked chuckle, eyes glinting",
 (39, "sa_i"): "eager and breathless, beaming, slapping the sacks",
 (39, "ai"): "hearty and booming, thumping his chest",
 (40, "kp2"): "tired but warm, coaxing, smiling, pushing the basket at him",
 (40, "bm"): "choked with guilt, stammering, hands trembling, swallowing the words with a sick smile",
 (41, "sa_i"): "wistful, a forced bright smile over a cracking voice, stroking the seat",
 (41, "ai"): "touched, voice thick, clapping his shoulder hard",
 (42, "sa_i"): "hurting, voice breaking, eyes red, gripping her hand",
 (42, "kp2"): "a brave bright smile through spilling tears, touching her bare neck",
 (43, "bm"): "breathless and excited, shouting the news, waving his phone",
 (43, "kp2"): "overjoyed, voice shaking, clasped hands at her lips, bowing",
 (44, "sa_i"): "ecstatic, laughing and crying, voice shaking, counting on his fingers",
 (45, "sa_i"): "desperate, calling out as loud as he can toward the empty mill",
 (45, "kp2"): "anxious, voice trembling, tugging his sleeve",
 (46, "sa_i"): "despairing and furious, voice cracking, raking his hair",
 (46, "kp2"): "horrified realisation, going pale, voice breaking",
 (47, "kp2"): "exhausted to the bone, voice cracking and faint, lips trembling, close to tears",
 (47, "sa_i"): "stubborn and angry, jaw clenched, arms crossed, glaring down the road",
 (48, "sa_i"): "sobbing hard, wailing, body shaking, beating his knee",
 (49, "bm"): "resolved but shaking, voice cracking, eyes red, face strained",
 (50, "bm"): "confessing through sobs, voice shaking, tears streaming, fist pressed to his chest",
 (51, "bm"): "wretched with shame, sobbing, head bowed low, wringing his glasses",
 (52, "kp2"): "betrayed and heartbroken, voice rising to a cry, tears streaming, shaking his shirt",
 (53, "bm"): "urgent and fierce, eyes blazing, gripping his arm, voice hard",
 (53, "sa_i"): "stunned, breathless, fist still raised, voice shaky",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

# -*- coding: utf-8 -*-
"""«ขายชื่อ» EP1 (film 5) ACT1 = shots 1-23 (0:00-3:04). Source of truth for
tools/build_shotsheet.py. Shared cast, voices, languages, locations and negatives live in
ep5-common.py; this file adds who is in each shot, where, when and the English action.

Rules carried in from films 1-4:
- the speaker's action happens WHILE the line is said, never before it ("then" is banned);
- the first speaker's action is written first, because Flow speaks in ACTION order;
- every person in frame has their own physical action and a loud, physical emotion;
- no children, no uniforms, day only, at most 3 people, no money in frame, no real brand.
- Overflow acting: every person in frame keeps a physical timeline for the whole shot.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep5common", Path(__file__).with_name("ep5-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE_ACTING, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T1, T2 = _c.T1, _c.T2

PROPS_BY_SHOT = {
    1: ["@mortar_clay"], 2: ["@mortar_clay"], 3: ["@mortar_clay", "@motorbike_old", "@toolbox_red"],
    4: ["@mortar_clay"], 5: ["@mortar_clay"], 6: ["@mortar_clay"], 7: ["@mortar_clay"],
    8: ["@motorbike_old"], 9: ["@toolbox_red"], 10: ["@scooter_pink", "@toolbox_red"],
    11: ["@scooter_pink", "@toolbox_red"], 12: ["@scooter_pink", "@toolbox_red"], 13: ["@scooter_pink"],
    14: ["@pickup_black"], 15: ["@toolbox_red"], 16: ["@cards_pouch"], 17: ["@cards_pouch"],
    19: ["@cards_pouch"], 23: ["@cards_pouch"],
}

_N = ["nosubs", "noextra", "daylight"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
    1: (8, "Medium two-shot at a som-tam stall in a daytime fresh market, the woman pounding papaya in a big clay mortar, a man in a cap tapping the stall's wooden edge",
        ["col", "sri"], "market_stall", T1,
        "the man in the navy-blue cap, cold and impassive, taps the wooden stall counter with his knuckles while he speaks; "
        "the whole time he talks, the woman in the papaya-orange apron pounds the clay mortar without stopping, her strikes "
        "growing harder with every word, jaw clenched tight, refusing to look up; the instant he finishes, her pestle "
        "freezes in mid-air and she lifts her chin; the orange canvas umbrella ripples in the morning breeze",
        _N + ["nouniform", "nocash"]),

    2: (8, "Close-up on the woman lowering the pestle, the man in the cap turning away",
        ["sri", "col"], "market_stall", T1,
        "the woman in the papaya-orange apron, desperate and pleading, presses her palms together in a respectful wai, "
        "forcing a polite strained smile while she speaks; the whole time she talks, the man in the navy-blue cap ignores "
        "her gaze, taps his wristwatch twice, turns his back and steps toward the market aisle; the instant she finishes, "
        "he looks over his shoulder and points a finger firmly back at the stall while answering; melted ice drips steadily "
        "from the red cooler box onto the concrete floor",
        _N + ["nouniform", "nocash"]),

    3: (8, "Medium, a young man on an old motorbike with a red toolbox strapped behind the seat pulling up beside the stall",
        ["ton", "sri"], "market_stall", T1,
        "the young man in the grey T-shirt, wary with furrowed brows, cuts the motorcycle engine with a twist of his key "
        "and tracks the departing rent collector with sharp eyes while he speaks; the whole time he talks, the woman in "
        "the papaya-orange apron hastily grabs a green papaya from the wooden counter, rubs a corner of her apron over her "
        "cheek and flashes an exaggerated bright smile; the instant he finishes, she shoves the papaya into his grease-stained "
        "hands while answering; morning dust drifts in the sunlight behind the motorcycle",
        _N + ["nocash"]),

    4: (8, "Two-shot across the clay mortar",
        ["ton", "sri"], "market_stall", T1,
        "the young man in the grey T-shirt, deeply hurt with his voice cracking, sets the papaya down firmly onto the wooden "
        "counter and leans forward, staring straight into his mother's eyes while he speaks; the whole time he talks, the "
        "woman in the papaya-orange apron refuses to meet his gaze, grabs the wooden pestle and pounds the shredded papaya "
        "faster and harder, her shoulder muscles tightening; the instant he finishes, she snaps her chin up and barks back "
        "while answering; stray shreds of papaya fly over the clay rim onto the table",
        _N + ["nocash"]),

    5: (8, "Close-up, the woman holding her phone at arm's length and squinting, the screen turned away from camera",
        ["ton", "sri"], "market_stall", T1,
        "the young man in the grey T-shirt, earnest and pleading, points a grease-stained finger directly at the front pocket "
        "of his mother's apron while he speaks; the whole time he talks, the woman in the papaya-orange apron pulls out her "
        "smartphone, holds it out at full arm's length, tilts her head back and squints with one eye at the dark display facing "
        "away from the lens; the instant he finishes, she clutches the phone against her chest and smiles proudly while answering; "
        "a stray market cat walks past the empty adjacent wooden table",
        _N + ["nocash", "noscreen"]),

    6: (8, "Close-up on the mother, phone pressed to her chest, the pestle pointed at her son",
        ["sri", "ton"], "market_stall", T1,
        "the woman in the papaya-orange apron, fierce with glistening eyes and a tight voice, clutches the smartphone tightly "
        "against her heart with one hand and points the heavy wooden pestle directly at her son's face while she speaks; the "
        "whole time she talks, the young man in the grey T-shirt lowers his head, tears brimming in his eyes, hands trembling "
        "against the counter; the instant she finishes, he nods slowly and bites his lower lip; a light gust of wind flutters "
        "the orange canvas fringe above her head",
        _N + ["nocash", "noscreen"]),

    7: (8, "Medium, the son straightening up, a friend in a sleeveless jersey stopping a bicycle behind him",
        ["ton", "sri", "fri"], "market_stall", T1,
        "the young man in the grey T-shirt, resolute with his jaw set, pulls the red work rag from his back pocket and vigorously "
        "wipes his grease-stained hands while he speaks; the whole time he talks, the woman in the papaya-orange apron keeps her "
        "head down, chopping garlic cloves with a heavy knife, sighing with a heavy shoulder drop; behind them, the young man "
        "in the basketball jersey rolls in on an old bicycle, skidding his foot on the gravel and casually waving; the instant "
        "the mother finishes her warning, the son turns sharply toward his friend; garlic husks flutter on the cutting board",
        _N + ["nocash"]),

    8: (8, "Two-shot at the son's motorbike by the roadside edge of the market, the mother small in the background pounding",
        ["fri", "ton"], "market_road", T1,
        "the young man in the basketball jersey, excited with wide eager eyes, grips his friend's bicep and leans in to whisper "
        "urgently while he speaks; the whole time he talks, the young man in the grey T-shirt stands frozen beside his motorcycle, "
        "his eyes widening in disbelief as he glances back toward the som-tam stall; the instant his friend finishes, the son "
        "stares at him with lips parted, repeating the words in shock while answering; in the distant background, his mother "
        "continues pounding the mortar under the orange umbrella, oblivious to their conversation",
        _N + ["nocash"]),

    9: (8, "Wide, a roadside repair spot under a tamarind tree in a soi, a blue tarp, a red toolbox, the son squatting at a motorbike wheel, his friend on a wooden bench",
        ["ton", "fri"], "repair_soi", T2,
        "the young man in the grey T-shirt, stubborn and focused, squats beside a disassembled motorcycle wheel and tightens "
        "an axle bolt with a steel wrench with all his strength while he speaks; the whole time he talks, the young man in "
        "the basketball jersey lounges on the wooden bench, bouncing his knee rapidly and tossing a pebble from hand to hand; "
        "the instant the friend finishes his sarcastic reply, the mechanic pauses his wrench mid-turn and glares up; the blue "
        "plastic tarp overhead flaps loudly in a sudden gust of wind",
        _N + ["nocash"]),

    10: (8, "Medium, a young woman in a mint shirt pushing a dead pale-pink scooter into the repair spot",
        ["fon", "ton", "fri"], "repair_soi", T2,
        "the young woman in the mint-green shirt, panting and exhausted, pushes her dead pale-pink scooter under the blue tarp, "
        "wiping sweat from her brow with her sleeve while she speaks; the whole time she talks, the young man in the grey "
        "T-shirt rises from his crouch, tucks his wrench into his back pocket and offers a gentle, reassuring smile; the friend "
        "on the bench sits up and slides aside to make room; the instant the mechanic answers with a welcoming nod, the young "
        "woman lets out a relieved sigh; dry tamarind leaves drift down onto the concrete ground",
        _N + ["nocash"]),

    11: (8, "Close-up, the son's grease-stained fingers holding up a cracked spark-plug wire",
        ["ton", "fon"], "repair_soi", T2,
        "the young man in the grey T-shirt, confident and skilled, lifts a cracked black spark-plug wire toward her, pointing "
        "out the visible fracture with his grease-stained thumb while he speaks; the whole time he talks, the young woman in "
        "the mint-green shirt fumbles inside her small crossbody sling bag with nervous fingers, her cheeks self-conscious; "
        "the instant he finishes, she looks down at her open bag and replies with embarrassment; water ripples in the galvanized "
        "testing basin nearby",
        _N + ["nocash"]),

    12: (8, "Medium three-shot, the scooter engine starting, the friend shaking his head",
        ["ton", "fri", "fon"], "repair_soi", T2,
        "the young man in the grey T-shirt, proud and grinning with his snaggletooth, kicks the scooter starter and revs the "
        "handlebar throttle until the engine hums cleanly while he speaks; the whole time he talks, the young man in the "
        "basketball jersey throws both hands up in utter disbelief, slaps his own forehead and groans loudly; the young woman "
        "in the mint-green shirt laughs softly in sheer relief and bows her head; the instant the friend finishes his scolding, "
        "the mechanic shrugs cheerfully; exhaust smoke puffs lightly into the bright soi daylight",
        _N + ["nocash"]),

    13: (8, "Close two-shot, the young woman holding out her phone, the screen turned away from camera",
        ["fon", "ton"], "repair_soi", T2,
        "the young woman in the mint-green shirt, deeply grateful with a warm smile, holds out her dark smartphone with both "
        "hands while she speaks; the whole time she talks, the young man in the grey T-shirt wipes his oily fingers on his red "
        "pocket rag and accepts the phone, holding the blank screen facing away from the camera as his thumbs type; the instant "
        "he finishes speaking his name, a loud double horn blast from a pickup truck blares from the soi entrance; tamarind "
        "branches rustle above them",
        _N + ["nocash", "noscreen"]),

    14: (8, "Medium, a lowered matte-black four-door pickup with chrome wheels rolling into the soi, a man in a tiger-print shirt and a thick gold chain leaning out of the window",
        ["boy", "fon", "ton"], "repair_soi", T2,
        "the man in the tiger-print shirt, loud and arrogant, leans halfway out of the lowered pickup window, slides his gold "
        "sunglasses down his nose and gestures disdainfully toward the roadside workshop while he speaks; the whole time he "
        "talks, the young woman in the mint-green shirt spins around, her body stiffening as she clutches her scooter handlebars; "
        "the mechanic stands upright, holding his ground with a puzzled frown; the instant the brother finishes his sneer, the "
        "sister steps forward defensively while answering; dust settles around the truck's chrome wheels",
        _N + ["nologo", "nocash"]),

    15: (8, "Medium, the man in tiger print stepping down and nudging the red toolbox over with his sneaker, wrenches spilling on the ground",
        ["boy", "ton", "fri"], "repair_soi", T2,
        "the man in the tiger-print shirt, smirking maliciously, saunters forward and kicks the open red metal toolbox with the "
        "toe of his shoe, sending steel wrenches clattering across the concrete while he laughs out loud; the whole time he "
        "talks, the young man in the grey T-shirt drops to his knees, collecting his scattered tools with white-knuckled fists, "
        "swallowing his rage; the friend by the bench chuckles nervously to appease the hustler; the instant the man finishes, "
        "the mechanic stands up and stares him down; sunlight glints off the polished chrome wrenches on the ground",
        _N + ["nocash"]),

    16: (8, "Three-shot, the friend stepping up to the man in tiger print",
        ["fri", "boy", "ton"], "repair_soi", T2,
        "the young man in the basketball jersey, fawning with an eager grin, steps eagerly right up to the man in the tiger-print "
        "shirt and points an enthusiastic finger back at the mechanic while he speaks; the whole time he talks, the man in the "
        "tiger-print shirt reaches into his pocket, pulls out a fat canvas pouch and swings it temptingly by its lanyard cord, "
        "his eyes lighting up with predatory greed; the mechanic steps forward, shaking his head in warning; the instant the "
        "friend finishes, the hustler grins wide and answers with smooth confidence; dry leaves crunch beneath his leather loafers",
        _N + ["nocash"]),

    17: (8, "Close-up, the man fanning a stack of blank plastic cards like a hand of playing cards, no text and no logo on any card",
        ["boy", "fri", "ton"], "repair_soi", T2,
        "the man in the tiger-print shirt, slick and predatory, fans out a stack of totally blank white plastic cards like playing "
        "cards, waving them right before their eyes with a wide salesman grin while he speaks; the whole time he talks, the "
        "friend's eyes bulge with excitement as he leans forward to touch them, while the mechanic steps back half a pace, eyes "
        "narrowed in sharp suspicion; the instant the man finishes, he snaps the cards together with a sharp plastic smack; "
        "the gold chain at his collar glints in the direct sunlight",
        _N + ["nocash"]),

    18: (8, "Close two-shot, the son and the man face to face",
        ["ton", "boy"], "repair_soi", T2,
        "the young man in the grey T-shirt, sharp and cautious, looks the older man dead in the eye and asks his question with "
        "unwavering intensity while he speaks; the whole time he talks, the man in the tiger-print shirt never blinks, chuckles "
        "under his breath and casually claps two heavy hands onto the young man's shoulder; the instant the young man finishes, "
        "the hustler leans in closer and speaks his lie with total breezy nonchalance; a stray gust rustles the blue tarpaulin",
        _N + ["nocash"]),

    19: (8, "Three-shot, the friend reaching for the cards, the son catching his wrist",
        ["fri", "ton", "boy"], "repair_soi", T2,
        "the young man in the basketball jersey, dazzled by greed, lunges both hands forward toward the cards with wide eyes while "
        "he speaks; the whole time he talks, the young man in the grey T-shirt moves instantly, seizing his friend's wrist in an "
        "iron grip and yanking him backward; the man in the tiger-print shirt crosses his arms and smirks with amused contempt; "
        "the instant the friend finishes, the mechanic steps between them and barks his refusal with fierce loyalty; dust kicks "
        "up around their shoes",
        _N + ["nocash"]),

    20: (8, "Three-shot, the man in tiger print roaring with laughter, the friend stalking out of frame",
        ["ton", "boy", "fri"], "repair_soi", T2,
        "the young man in the grey T-shirt, unyielding and firm with his jaw locked, releases his friend and faces the hustler "
        "alone while he speaks; the whole time he talks, the man in the tiger-print shirt throws his head back and erupts into "
        "a booming, mocking roar of laughter, jabbing a finger at the mechanic's face; behind them, the offended friend scowls, "
        "turns sharply and stalks off down the soi; the instant the young man finishes, the hustler taunts him with sneering "
        "condescension; the blue tarp billows in the hot midday breeze",
        _N + ["nocash"]),

    21: (8, "Close two-shot, the man leaning in close, chewing gum",
        ["boy", "ton"], "repair_soi", T2,
        "the man in the tiger-print shirt, leaning within inches of the young man's face, chews his gum rhythmically with a "
        "mocking sneer while he speaks; the whole time he talks, the young man in the grey T-shirt casts his eyes downward, "
        "twisting his red cotton pocket rag between both fists until his knuckles whiten with humiliation; the instant the older "
        "man finishes his taunt, the mechanic swallows hard and confesses his urgency while answering; heat ripples rise from "
        "the sunbaked asphalt lane",
        _N + ["nocash"]),

    22: (8, "Close-up on the man's face, sunglasses pushed up onto his head, eyes lighting up, the young woman at the edge of frame by her scooter",
        ["ton", "boy", "fon"], "repair_soi", T2,
        "the young man in the grey T-shirt, speaking with bitter pride and a trembling voice, shakes his head softly as he speaks "
        "of his mother's sacrifice; the whole time he talks, the man in the tiger-print shirt pushes his gold sunglasses onto "
        "his gelled hair, his eyes narrowing with sudden ravenous calculation; over by the pink scooter, the sister looks up with "
        "a sudden gasp of dread; the instant the mechanic finishes, the hustler leans forward eagerly, interrogating him with "
        "a sugary veneer while answering; a dry leaf skitters across the pavement",
        _N + ["nocash"]),

    23: (8, "Three-shot, the son typing into the man's phone with a happy smile, the screen turned away from camera, the young woman frozen behind them",
        ["ton", "boy", "fon"], "repair_soi", T2,
        "the young man in the grey T-shirt, beaming with innocent filial pride, speaks his mother's name while happily accepting "
        "the hustler's smartphone and tapping into it with the blank screen facing away from camera; the whole time he talks, "
        "the man in the tiger-print shirt watches him with an enormous predatory grin stretching ear to ear; behind them, the "
        "sister raises both trembling hands to cover her mouth in utter horror; the instant the young man finishes, the hustler "
        "snatches the phone back with a triumphant chuckle; the music swells into a harsh dramatic sting",
        _N + ["nocash", "noscreen"]),
}

DIRECTION = {
    (1, "col"): "cold and impassive, flat dry voice, tapping his knuckles against the wooden board",
    (2, "sri"): "pleading with a strained forced smile, voice trembling, pressing palms together in a respectful wai",
    (2, "col"): "bored and dismissive, checking his wristwatch, turning away without looking at her",
    (3, "ton"): "wary and suspicious, brow furrowed, eyes tracking the man",
    (3, "sri"): "nervously cheerful, an exaggerated bright smile to cover her distress, pushing papaya into his hands",
    (4, "ton"): "deeply hurt, voice cracking with emotion, staring intensely at her",
    (4, "sri"): "stubborn and defensive, pounding the mortar with furious strength, refusing to meet his eyes",
    (5, "ton"): "earnest and pleading, pointing urgently at her apron pocket",
    (5, "sri"): "fiercely proud, head held back, squinting at her phone with an affectionate smirk",
    (6, "sri"): "fierce and resolute, eyes wet with tears, brandishing the pestle like a weapon",
    (7, "ton"): "determined, jaw set hard, voice firm with youthful pride",
    (7, "sri"): "worried sigh, voice heavy with motherly concern, chopping without looking up",
    (8, "fri"): "whispering with conspiratorial excitement, eyes wide, tugging his friend's arm",
    (8, "ton"): "stunned and breathless, eyes widening as he glances back toward his mother",
    (9, "ton"): "stubborn and proud, wrenching the axle bolt with fierce effort",
    (9, "fri"): "teasing and cynical, bouncing his leg carelessly on the bench",
    (10, "fon"): "out of breath, exhausted and timid, wiping sweat from her forehead",
    (10, "ton"): "warm, welcoming and gentle, wiping his hands with a reassuring smile",
    (11, "ton"): "confident and knowledgeable, holding up the cracked wire with authority",
    (11, "fon"): "embarrassed and apologetic, voice small, digging through her purse",
    (12, "ton"): "proud and satisfied, revving the throttle with a bright snaggletooth grin",
    (12, "fri"): "exasperated and loud, slapping his own forehead in utter disbelief",
    (13, "fon"): "warmly grateful, eyes glowing with relief and sincere respect",
    (13, "ton"): "modest and shy, smiling gently as he enters his number",
    (14, "boy"): "loud, arrogant and sneering, lowering his sunglasses with disdain",
    (14, "fon"): "tense, defensive and protective, turning sharply to confront her brother",
    (15, "boy"): "cruel and mocking, laughing harshly as he kicks the toolbox over",
    (16, "fri"): "fawning and eager, smiling broadly as he points out his friend",
    (16, "boy"): "predatory and confident, eyes gleaming, swinging the cloth pouch",
    (17, "boy"): "smooth and theatrical, like a slick salesman fanning a winning hand",
    (18, "ton"): "cautious and searching, holding the older man's gaze with unwavering suspicion",
    (18, "boy"): "lying smoothly with a breezy, comforting laugh, patting his shoulder",
    (19, "fri"): "greedy and impulsive, lunging forward with wide hungry eyes",
    (19, "ton"): "fierce, protective and decisive, gripping his friend's wrist like an iron clamp",
    (20, "ton"): "resolute and unwavering, standing tall alone",
    (20, "boy"): "booming mocking laughter, pointing an accusing finger with pure derision",
    (21, "boy"): "sneering and intrusive, chewing gum loudly right in his face",
    (21, "ton"): "ashamed and humiliated, eyes cast down, twisting his rag with bitter honesty",
    (22, "ton"): "proud yet sorrowful, a bitter tender smile honoring his mother",
    (22, "boy"): "ravenously greedy, sunglasses shoved up, voice purring with cunning interest",
    (23, "ton"): "beaming with innocent pride, trusting and joyful for his mother",
    (23, "boy"): "predatory, wearing a wide sinister grin as he collects his prize",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

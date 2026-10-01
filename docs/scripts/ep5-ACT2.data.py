# -*- coding: utf-8 -*-
"""«ขายชื่อ» EP1 (film 5) ACT2 = shots 24-53 (3:04-7:04). Source of truth for
tools/build_shotsheet.py. Shared blocks: ep5-common.py. Rules: see ep5-ACT1.data.py.

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
T3, T4 = _c.T3, _c.T4

PROPS_BY_SHOT = {
    24: ["@cards_pouch"], 26: ["@cards_pouch"], 33: ["@cards_pouch"],
    37: ["@mortar_clay"], 38: ["@mortar_clay"], 39: ["@mortar_clay"], 40: ["@mortar_clay"],
    48: ["@mortar_clay"], 51: ["@mortar_clay"], 52: ["@mortar_clay"],
    53: ["@mortar_clay", "@motorbike_old"],
}

_N = ["nosubs", "noextra", "daylight"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
    24: (8, "Interior of the pickup cab, the man at the wheel, the son in the passenger seat holding out a blank plastic card, the young woman in the back seat",
        ["ton", "boy", "fon"], "pickup_cab", T3,
        "the young man in the grey T-shirt, nervous with slightly trembling fingers, holds out a freshly opened blank white plastic card while he speaks; "
        "the whole time he talks, the man in the tiger-print shirt snatches the card with a greedy swipe and inspects it with a wide grin; behind them, "
        "the young woman in the mint-green shirt keeps her head lowered, typing on her phone with the blank dark screen facing away from the lens; "
        "the instant the young man finishes, the hustler flicks the edge of the card against his thumbnail with a sharp plastic click while answering; "
        "bright midday sun streams through the pickup windshield",
        _N + ["nocash", "noscreen", "nologo"]),

    25: (8, "Close-up, the man's phone held with its screen away from camera, his thumb tapping",
        ["boy", "ton", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, boastful and smug, taps rapidly on his smartphone held with the dark screen turned away from camera while he speaks; "
        "the whole time he talks, the young man in the grey T-shirt sits rigidly in the passenger seat, nodding slowly while chewing his lower lip in unease; "
        "in the rear seat, the sister pauses her typing and looks up with sorrowful eyes; the instant the hustler finishes, he claps a heavy hand onto the mechanic's shoulder; "
        "sunlight reflects off his heavy gold wristwatch",
        _N + ["nocash", "noscreen", "nologo"]),

    26: (8, "Close-up, the blank card dropping into a fat cloth pouch full of blank cards",
        ["boy", "fon", "ton"], "pickup_cab", T3,
        "the man in the tiger-print shirt, proud of his illicit harvest, drops the blank white plastic card into a fat canvas pouch and checks the rear-view mirror while he speaks; "
        "the whole time he talks, the young woman in the mint-green shirt looks down at her notes, keeping her expression masked in stony silence; the mechanic in the front passenger "
        "seat stares with wide eyes at the swollen pouch full of blank cards; the instant the brother finishes his question, the sister answers with flat compliance and zips the pouch shut; "
        "dust motes swirl in the hot sunbeam across the dashboard",
        _N + ["nocash", "noscreen", "nologo"]),

    27: (8, "Close-up, the man patting the closed lid of the pickup's center console",
        ["boy", "ton", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, gloating with chilling arrogance, taps his knuckles twice on the closed plastic lid of the center console while he speaks; "
        "the whole time he talks, the young man in the grey T-shirt stares at the closed console and swallows hard with rising apprehension; in the rear seat, the sister turns her face "
        "sharply toward the passenger window; the instant the man finishes, he lets out a low mocking chuckle in his throat; the leather steering wheel gleams in the afternoon sun",
        _N + ["nocash", "nologo"]),

    28: (8, "Close-up, the son looking at his own phone with the screen turned away from camera, relief flooding his face",
        ["boy", "ton", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, casually benevolent, confirms the transfer on his phone held screen-away while he speaks; "
        "the whole time he talks, the young man in the grey T-shirt watches his own smartphone screen facing away from camera, his face melting from terror into overwhelming relief; "
        "in the rear seat, the sister watches him in the mirror with deep pity; the instant the older man finishes, the mechanic shuts his eyes tightly, exhaling a breathless prayer of thanks "
        "while answering; a heavy weight visibly lifts from his hunched shoulders",
        _N + ["nocash", "noscreen", "nologo"]),

    29: (8, "Medium, the son opening the passenger door to step out of the pickup",
        ["ton", "boy", "fon"], "pickup_cab", T3,
        "the young man in the grey T-shirt, trusting and naive, pushes the heavy passenger door open and steps onto the pavement while he speaks; "
        "the whole time he talks, the man in the tiger-print shirt leans over the steering wheel and winks slyly at his sister in the rear-view mirror; the young woman avoids her brother's eyes "
        "and stares down at her lap; the instant the mechanic finishes his farewell, the hustler calls out a mocking goodbye while waving a casual hand; the truck door shuts with a solid thud",
        _N + ["nologo", "nocash"]),

    30: (8, "Medium, the man alone in front with his phone to his ear and his feet up on the console, the young woman in the back seat looking up",
        ["boy", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, triumphant and gleeful, kicks his loafers up onto the center console and dials his phone with a loud cackle while he speaks; "
        "the whole time he talks, the young woman in the mint-green shirt slowly lifts her head from the rear seat, her face draining of all color in mounting dread; "
        "the instant he finishes his opening greeting, the sister leans forward across the seat back, her knuckles whitening as she grips the headrest; heat shimmers on the hood outside",
        _N + ["noscreen", "nologo", "nocash"]),

    31: (8, "Close-up, the man grinning into the phone, drumming on the steering wheel",
        ["boy", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, dripping with predatory greed, drums his gold-ringed fingers against the steering wheel rim with an excited smirk while he speaks; "
        "the whole time he talks, the young woman in the mint-green shirt lowers her phone to her lap, her jaw dropping open in utter disbelief and heartbreak; "
        "the instant he finishes disclosing the mother's savings, the sister opens her mouth to shout in protest; bright glare reflects off his gold sunglasses on the dash",
        _N + ["noscreen", "nologo", "nocash"]),

    32: (8, "Two-shot, the young woman leaning forward between the front seats, the man raising a hand to silence her",
        ["fon", "boy"], "pickup_cab", T3,
        "the young woman in the mint-green shirt, horrified and pleading, lunges between the front seats and grabs the driver's seat armrest while she cries out; "
        "the whole time she talks, the man in the tiger-print shirt raises an open palm backward without turning his head, cutting her off cold while continuing to bark instructions into his phone; "
        "the sister shakes her head in tearful anguish; the instant she finishes her protest, the brother chuckles coldly into the phone receiver; the leather interior creaks under her grip",
        _N + ["noscreen", "nologo", "nocash"]),

    33: (8, "Close-up on the man, a grin that does not reach his eyes, shaking the cloth pouch of cards",
        ["boy", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, wearing a chilling smile with cold unblinking eyes, brandishes the pouch of blank plastic cards and shakes it vigorously while he speaks; "
        "the whole time he talks, the young woman in the mint-green shirt shakes her head in horror, her lips quivering as tears well up; the instant he finishes giving his orders, "
        "he tosses the pouch onto the passenger seat with careless finality; sunlight flares across the metallic chrome door handle",
        _N + ["nocash", "nologo"]),

    34: (8, "Two-shot, the man hanging up and turning toward the back seat",
        ["fon", "boy"], "pickup_cab", T3,
        "the young woman in the mint-green shirt, weeping openly with tears streaming down her cheeks, points out the window toward the street where the mechanic walked away while she speaks; "
        "the whole time she talks, the man in the tiger-print shirt ends the call, drapes his heavy arm across the back of the passenger seat and smirks with icy indifference; "
        "the instant she finishes her tearful plea, he shrugs his wide shoulders dismissively and delivers a callous truth while answering; hot sunlight floods the cabin",
        _N + ["nocash", "nologo"]),

    35: (8, "Close-up, the man leaning over the seat toward his sister, a finger pointed at her from a distance",
        ["boy", "fon"], "pickup_cab", T3,
        "the man in the tiger-print shirt, menacing and stern, leans deep over the seat gap and points a stiff index finger inches from her face without touching her while he speaks; "
        "the whole time he talks, the young woman in the mint-green shirt presses her back hard against the rear passenger door, hugging her handbag to her ribs and sobbing quietly; "
        "the instant he finishes his chilling ultimatum, she lets out a muffled gasp of terror; the shadows inside the vehicle deepen",
        _N + ["nocash", "nologo"]),

    36: (8, "Close-up, the young woman's thumb hovering over her phone, the screen turned away from camera, the man starting the engine",
        ["fon", "boy"], "pickup_cab", T3,
        "the young woman in the mint-green shirt, paralyzed by guilt with tears dripping from her chin, hovers her trembling thumb over the dark smartphone screen facing away from camera while she whispers; "
        "the whole time she talks, the man in the tiger-print shirt turns the ignition key, revs the loud diesel engine and checks his mirrors with breezy satisfaction; "
        "the instant the sister finishes, the brother laughs casually, snaps his seatbelt and accelerates onto the street; the truck jerks forward into the blinding afternoon sun",
        _N + ["noscreen", "nologo", "nocash"]),

    37: (8, "Medium, the som-tam stall, the woman holding her ringing phone at arm's length and squinting, the screen turned away from camera",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, holding her buzzing smartphone at full arm's length with the dark screen facing away from camera, squints with deep crow's feet and answers "
        "while wiping her other hand on her apron; the whole time she talks, her brows knit into a confused frown as she strains to hear over the distant market chatter; "
        "the instant she finishes her greeting, she stops pounding the mortar and tilts her ear closer to the receiver; the orange market umbrella sways in the warm three-o'clock wind",
        _N + ["noscreen", "nocash"]),

    38: (8, "Close-up, the woman's face draining, the pestle frozen in mid-air",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, paralyzed with terror as all color drains from her face, repeats the caller's shocking accusation phrase by phrase while her wooden pestle freezes "
        "mid-air above the mortar; the whole time she talks, her knuckles whiten around the pestle handle and her breath catches in her throat; the instant she finishes her cry of disbelief, "
        "the heavy pestle slips from her limp grip and crashes into the clay mortar with a hollow thud; dramatic music hits a jarring cliffhanger sting",
        _N + ["nocash"]),

    39: (8, "Close-up, the woman clutching the phone to her ear, her other hand gripping the stall's edge",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, frantic and desperate, shakes her head vigorously and grips the wooden counter edge until her nails dig in while she speaks; "
        "the whole time she talks, her voice climbs in pitch with every word, tears springing to her wide horrified eyes; the instant she finishes her frantic denial, "
        "she presses the phone harder against her ear and listens in frozen dread; a warm breeze flutters the plastic bags hanging from the counter",
        _N + ["nocash"]),

    40: (8, "Medium, the woman sinking onto a red plastic stool, phone at her ear",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, knees giving way beneath her, collapses heavily onto the red plastic stool and clutches the phone with both trembling hands while she repeats the warning; "
        "the whole time she talks, her chest heaves with rapid shallow breaths and her left hand frantically bunches the fabric of her apron; the instant she finishes, she swallows hard "
        "with dry trembling lips; beneath the counter, the market cat darts out and disappears into the aisle",
        _N + ["nocash"]),

    41: (8, "Two-shot, the man in the cap passing by the stall, the woman covering the phone's mouthpiece with her palm",
        ["col", "sri"], "market_stall", T4,
        "the man in the navy-blue cap, strolling past with an indifferent gaze, taps the wooden counter once with his knuckle while delivering his routine reminder; "
        "the whole time he talks, the woman in the papaya-orange apron clamps her sweaty palm tightly over the phone mouthpiece, plastering on a panicky grimace; "
        "the instant he finishes, she flaps her other hand rapidly to shoo him away while rushing her response; the rent collector raises an eyebrow and ambles onward down the aisle",
        _N + ["nouniform", "nocash"]),

    42: (8, "Close-up, the woman turning her back to the aisle, phone pressed hard to her ear",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, hunched over with her back turned to the aisle, drops her voice to a frantic terrified whisper while repeating the caller's harsh condition; "
        "the whole time she talks, her anxious gaze darts constantly toward the market entrance where her son might appear; the instant she finishes, she squeezes her eyes shut in agonized surrender; "
        "the heavy orange fabric umbrella flaps against its metal ribs in the hot breeze",
        _N + ["nocash"]),

    43: (8, "Extreme close-up, the woman's eyes widening as she believes",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, eyes widening in pure stunned shock, clutches her chest with a trembling hand as total belief overwhelms her while she speaks; "
        "the whole time she talks, her chin quivers and tears spill over her sun-darkened cheeks; the instant she finishes, she nods her head in helpless, devastated submission; "
        "sweat beads glisten along her forehead in the bright afternoon glare",
        _N + ["nocash"]),

    44: (8, "Medium, the woman fumbling to open an app on her phone, the screen turned away from camera",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, wedging the phone awkwardly between her ear and shoulder, taps the dark screen facing away from the lens with shaking fingers while repeating the orders; "
        "the whole time she talks, her breathing stumbles in panicked gasps and her trembling thumbs slip repeatedly against the glass; the instant she finishes, her thumb hovers rigidly above the app icon; "
        "red chili peppers in the woven bamboo tray roll off the table onto the ground",
        _N + ["noscreen", "nocash"]),

    45: (8, "Close-up, the woman half-standing as if to leave the stall",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, clutching her cloth shoulder bag, half-rises from her plastic stool in a desperate bid to visit the bank in person while she speaks; "
        "the whole time she talks, the caller's harsh refusal echoes into her ear and her face loses its last glimmer of resistance; the instant she finishes, she sinks back down onto the stool, "
        "nodding weakly in defeat; the market umbrella groans in a sudden gust of afternoon wind",
        _N + ["nocash"]),

    46: (8, "Close-up, the woman holding the phone far from her face and squinting hard, the screen turned away from camera",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, thrusting the smartphone far out with both arms, squints until her entire face wrinkles in vain struggle to decipher the small text facing away from camera while she speaks; "
        "the whole time she talks, she pumps the phone back and forth trying to find focus without her spectacles; the instant she finishes, she gives up in despair and prepares to obey blindly; "
        "afternoon sun glares off the polished surface of the clay mortar",
        _N + ["noscreen", "nocash"]),

    47: (8, "Close-up, the woman's thumb hovering, tears welling",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, thumb trembling millimeters above the dark phone screen facing away from camera, weeps openly as she speaks of her son's future; "
        "the whole time she talks, huge tears stream down into her mouth and her chest heaves with agonizing hesitation; the instant she finishes her plea, she draws in a deep shuddering breath "
        "and steels herself for the sacrifice; a warm draft stirs the loose strands of hair around her bun",
        _N + ["noscreen", "nocash"]),

    48: (8, "Close-up, the thumb pressing down, the woman exhaling with relief",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, pressing her thumb firmly down onto the dark screen facing away from camera, lets out a long tremulous sigh of false relief while she speaks; "
        "the whole time she talks, her tense shoulders drop heavily and a fragile tearful smile breaks across her face; the instant she finishes, she clutches the phone to her cheek with heartfelt gratitude; "
        "afternoon shadows lengthen across the market counter",
        _N + ["noscreen", "nocash"]),

    49: (8, "Medium, the woman's smile fading as she listens",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, her frail smile instantly freezing and crumbling as she hears the caller's new demand, grips the phone until her knuckles whiten while she speaks; "
        "the whole time she talks, cold realization dawns in her widening eyes; the instant she finishes her bewildered question, she pulls the phone from her ear and stares in horror at the silent receiver; "
        "the hum of distant traffic rumbles from the street outside",
        _N + ["nocash"]),

    50: (8, "Close-up, the woman calling back with the phone at her ear, then pulling it away",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, hands shaking violently as she frantically redials the number, repeats the recorded automated operator message in mounting hysteria while she speaks; "
        "the whole time she talks, the phone nearly slips through her clammy palms as she dials again and again; the instant she finishes, she stares blankly at the silent phone with parted trembling lips; "
        "a dry leaf drifts down onto the cutting board beside her",
        _N + ["nocash"]),

    51: (8, "Close-up, the phone slipping from the woman's fingers onto the stall table",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, shattered by catastrophic reality, lets the smartphone slip from her limp fingers onto the wooden counter while her voice breaks in agony; "
        "the whole time she talks, both of her hands fly up to clamp over her mouth to stifle a scream of pure horror; the instant she finishes, her body convulses and knocks against the table, "
        "spilling fresh red chilies from the bamboo tray; the orange umbrella suddenly falls dead still as the breeze dies",
        _N + ["nocash"]),

    52: (8, "Medium, the woman collapsing onto the red stool, hugging the empty clay mortar",
        ["sri"], "market_stall", T4,
        "the woman in the papaya-orange apron, completely broken and destroyed, collapses forward onto the red stool, wrapping both arms around the heavy clay mortar and rocking in soundless sobs while she speaks; "
        "the whole time she talks, her forehead presses hard against the rough clay rim, her back heaving with devastating grief; the instant she finishes her despairing wail, she buries her face into her apron; "
        "afternoon sun beats down relentlessly on the quiet stall",
        _N + ["nocash"]),

    53: (8, "Deep two-shot, the mother on the stool in the foreground, her son riding up on his motorbike in the background waving",
        ["ton", "sri"], "market_stall", T4,
        "the young man in the grey T-shirt, riding his motorcycle into the background with a triumphant beam on his face, waves one hand high in the air and shouts the good news while he arrives; "
        "the whole time he talks, in the foreground the mother jerks upright on her plastic stool, stiffening in sheer terror as she violently scrubs tears from her face with her apron; "
        "the instant the son cuts his engine, the mother gasps his name with trembling lips; dramatic music hits a jarring cliffhanger sting",
        _N + ["nocash"]),
}

DIRECTION = {
    (24, "ton"): "nervous and hesitant, hand trembling slightly as he offers the card",
    (24, "boy"): "smug, delighted and condescending, snatching the card with an arrogant grin",
    (25, "boy"): "boastful and brazen, tapping his phone with cocky self-assurance",
    (26, "boy"): "triumphant and boastful, glancing back to savor his victory",
    (26, "fon"): "stony, flat and completely devoid of emotion, avoiding his eyes",
    (27, "boy"): "cynical and chilling, tapping the console with ruthless amusement",
    (28, "boy"): "mock-generous and breezy, flashing a patronizing grin",
    (28, "ton"): "overcome with relief, eyes closed, smiling through grateful tears",
    (29, "ton"): "innocent and trusting, offering a polite respectful farewell",
    (29, "boy"): "sly, cunning and duplicitous, winking with amused contempt",
    (30, "boy"): "gleeful, exuberant and brimming with sinister excitement",
    (31, "boy"): "ravenously greedy, eyes glittering, drumming on the wheel like a predator",
    (32, "fon"): "shivering with horror, lunging forward in desperate tearful protest",
    (32, "boy"): "coldly dismissive, waving his hand to silence her without a glance",
    (33, "boy"): "chillingly remorseless, brandishing the cards with unfeeling cruelty",
    (34, "fon"): "weeping with sorrow and indignation, pointing outside with trembling hands",
    (34, "boy"): "callous and icy, shrugging his shoulders with brutal indifference",
    (35, "boy"): "dark, low and venomously threatening, pointing his finger with lethal menace",
    (35, "fon"): "paralyzed with dread, crying silently, terrified into submission",
    (36, "fon"): "whispering in heartbroken anguish, tears dripping onto her hands",
    (36, "boy"): "flippant, upbeat and utterly casual, revving the loud engine",
    (37, "sri"): "puzzled, head tilted, squinting at her phone with confused concern",
    (38, "sri"): "struck by sudden terror, face draining pale, voice trembling with horror",
    (39, "sri"): "desperate, frantic, voice rising in pitch as she pleads her innocence",
    (40, "sri"): "frightened out of her wits, breathing fast, clutching her chest",
    (41, "col"): "monotone, bored and completely indifferent, tapping the board once",
    (41, "sri"): "panicky and flustered, waving him away while covering the phone",
    (42, "sri"): "hushed, terrified whisper, glancing back in desperate motherly protection",
    (43, "sri"): "stunned into total submission, eyes wide with terrifying belief",
    (44, "sri"): "frantic, hands shaking wildly, fumbling with the touchscreen",
    (45, "sri"): "pleading for an alternative, then collapsing into weary defeat",
    (46, "sri"): "squinting desperately, voice breaking as she gives up on reading",
    (47, "sri"): "heartbroken hesitation, tears flooding her face, begging for mercy",
    (48, "sri"): "exhausted, fragile relief, smiling weakly through streaming tears",
    (49, "sri"): "uneasy, smile instantly evaporating, voice tight with sudden dread",
    (50, "sri"): "hysterical panic, redialing with trembling fingers, voice cracking",
    (51, "sri"): "shattered, gasping in horror, hands flying to cover her mouth",
    (52, "sri"): "broken, rocking back and forth in soundless, agonizing despair",
    (53, "ton"): "beaming with joyful pride, shouting happily from his motorcycle",
    (53, "sri"): "startled in sheer panic, wiping tears fast, voice choking on his name",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

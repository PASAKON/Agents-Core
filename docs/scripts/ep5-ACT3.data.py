# -*- coding: utf-8 -*-
"""«ขายชื่อ» EP1 (film 5) ACT3 = shots 54-68 (7:04-9:04). Source of truth for
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
T5 = _c.T5

PROPS_BY_SHOT = {
    54: ["@mortar_clay"], 55: ["@mortar_clay"], 56: ["@mortar_clay"], 57: ["@mortar_clay"],
    58: ["@mortar_clay"], 63: ["@mortar_clay"], 65: ["@mortar_clay"],
    66: ["@motorbike_old"], 67: ["@motorbike_old"], 68: ["@motorbike_old", "@mortar_clay"],
}

_N = ["nosubs", "noextra", "daylight"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
    54: (8, "Two-shot at the stall, the son hopping off the bike, the mother forcing a smile",
        ["sri", "ton"], "market_stall", T5,
        "the woman in the papaya-orange apron, forcing a quivering smile with tear-rimmed eyes, grasps the wooden pestle and turns to her son while she speaks; "
        "the whole time she talks, the young man in the grey T-shirt straightens his spine with brimming filial pride and pats his pocket; "
        "the mother gently taps the empty clay mortar, avoiding direct eye contact; the instant she finishes, the son reaches over, snatches a shredded green papaya strip "
        "and pops it into his mouth while delivering his proud lie; late afternoon sunlight filters softly through the orange umbrella",
        _N + ["nocash"]),

    55: (8, "Close-up on the mother flinching at every word",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, radiant with triumphant goodwill, lifts the bamboo basket of red chilies and rearranges the stall table while he speaks; "
        "the whole time he talks, the woman in the papaya-orange apron flinches visibly at every cheerful word, turning her face toward the interior of the clay mortar; "
        "her knuckles whiten around the pestle and she bites her trembling lip; the instant he finishes, she bows her head lower to conceal her agony; "
        "warm sunlight reflects off the polished surface of the clay mortar",
        _N + ["nocash"]),

    56: (8, "Two-shot, the son grinning at his mother, the mother's eyes brimming",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, beaming with a wide snaggletooth smile, leans across the wooden table with boundless warmth while he speaks; "
        "the whole time he talks, the woman in the papaya-orange apron lifts her trembling hand and gently strokes her son's cropped hair, her eyes brimming with unshed tears; "
        "the mechanic closes his eyes, savoring his mother's tender touch; the instant he finishes, she holds her voice steady with superhuman effort while answering, "
        "quickly withdrawing her hand; the late-afternoon market breeze rustles the orange umbrella fringe",
        _N + ["nocash"]),

    57: (8, "Close two-shot, the son peering at his mother's red eyes",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, lowering his head with furrowed brows, inspects his mother's tear-streaked eyes with sharp concern while he speaks; "
        "the whole time he talks, the woman in the papaya-orange apron grabs a handful of fresh red chilies, throws them into the mortar and pounds furiously with both hands; "
        "her arms shake with intense effort to mask her distress; the instant he finishes, she offers a breathless excuse without stopping her pestle; "
        "the heavy thumping of the pestle echoes through the stall",
        _N + ["nocash"]),

    58: (8, "Medium, the mother untying her apron and handing the pestle to her son",
        ["sri", "ton"], "market_stall", T5,
        "the woman in the papaya-orange apron, voice hurried with urgent tension, unties the orange apron strings from behind her waist and passes the wooden pestle to her son while she speaks; "
        "the whole time she talks, the young man in the grey T-shirt takes the pestle with an easy reassuring grin, giving her a gentle nod of encouragement; "
        "the mother clutches her smartphone deep inside her pocket; the instant the son answers, the mother slips past the counter and rushes toward the rear aisle; "
        "warm shadows stretch across the wooden market floor",
        _N + ["nocash"]),

    59: (8, "Medium, a narrow back aisle behind the market stalls stacked with empty crates, the mother alone with her phone at her ear",
        ["sri_noapron"], "market_back", T5,
        "the woman in the cream blouse, crouching in the shadowy service alley beside towering stacks of empty plastic crates, clutches her phone to her ear and whispers in breathless haste while she speaks; "
        "the whole time she talks, her anxious gaze darts back toward the bright market stall where her son works; she drops her voice to an absolute minimum, her chin trembling with humiliation; "
        "the instant she finishes, she presses the phone tightly to her cheek, listening with bated breath; dry leaves stir on the concrete alley floor",
        _N + ["nocash"]),

    60: (8, "Close-up, the mother nodding along with the operator, wiping her face with the back of her hand",
        ["sri_noapron"], "market_back", T5,
        "the woman in the cream blouse, listening to the emergency hotline officer, nods her head vigorously with every word and repeats the instructions while a fragile ray of hope touches her face; "
        "the whole time she talks, she scrubs away drying tears with the back of her wrist, her chest heaving with deep tremulous breaths; the instant she finishes her confirmation, "
        "she sniffs softly and clutches the phone with both hands; afternoon sunlight slants between the blue plastic crates",
        _N + ["nocash"]),

    61: (8, "Close-up, the mother pressing the phone to her lips, looking toward the stall where her son is",
        ["sri_noapron"], "market_back", T5,
        "the woman in the cream blouse, pressing the smartphone firmly against her trembling lips, peers through the gap between plastic crates toward her son pounding som tam in the bright stall while she speaks; "
        "the whole time she talks, her jaw sets with ferocious maternal determination, biting her lip to lock the secret deep inside; the instant she finishes her vow, she ends the call, "
        "hugging the phone against her heart; dust motes glow in the warm amber sunlight",
        _N + ["nocash"]),

    62: (8, "Medium, the young woman alone in the back seat of the parked pickup, her phone at her ear",
        ["fon"], "pickup_cab", T5,
        "the young woman in the mint-green shirt, huddled in the rear corner of the parked pickup cab, presses her smartphone to her ear and speaks with fearful urgency while watching the driver's door; "
        "the whole time she talks, her left hand twists the fabric of her skirt into tight knots, her breath catching in her throat; the instant she finishes her anxious inquiry, "
        "she holds her breath, waiting in agony for the mechanic's voice; outside the open driver's door, warm afternoon light fills the street",
        _N + ["noscreen", "nologo", "nocash"]),

    63: (8, "Medium, the son alone at the stall pounding som tam, phone wedged between ear and shoulder",
        ["ton"], "market_stall", T5,
        "the young man in the grey T-shirt, working diligently alone at the counter, wedges his buzzing smartphone between his ear and shoulder and continues pounding the pestle while he answers; "
        "the whole time he talks, his strikes gradually slow down as a puzzled frown creases his brow, listening to the unexpected caller; the instant he finishes his question, "
        "he halts the wooden pestle completely and stands upright in curiosity; late afternoon sunlight warms the market counter",
        _N + ["nocash", "noscreen"]),

    64: (8, "Two-shot, the man in tiger print rapping on the pickup's window, the young woman lowering her phone",
        ["boy", "fon"], "pickup_cab", T5,
        "the man in the tiger-print shirt, glaring with sharp suspicion, leans his bulky frame through the open window and raps hard knuckles against the glass while he demands answers; "
        "the whole time he talks, the young woman in the mint-green shirt flinches in pure panic, tears spilling down her cheeks as she swiftly speaks her choked apology into the receiver; "
        "the instant she finishes, she abruptly taps the disconnect button and drops the phone into her lap, avoiding her brother's piercing glare; the truck's chrome mirror reflects the setting sun",
        _N + ["noscreen", "nologo", "nocash"]),

    65: (8, "Two-shot at the stall, the son lowering his phone as it rings again, the mother returning from the back aisle",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, staring in bewilderment at his dark smartphone screen held facing away from camera as it begins to ring with an unknown number, speaks while stepping back; "
        "the whole time he talks, the woman in the papaya-orange apron emerges from the rear alley, tying her apron strings behind her waist with puffy eyes and forcing her voice into everyday calm; "
        "the mechanic retreats toward the street curb to take the call; the instant the mother finishes, she picks up the wooden pestle and begins pounding; market awnings flutter gently",
        _N + ["noscreen", "nocash"]),

    66: (8, "Medium, the son beside his motorbike at the roadside edge of the market, phone at his ear, the stall far behind",
        ["ton"], "market_road", T5,
        "the young man in the grey T-shirt, gripping the handlebars of his motorcycle with an iron fist, repeats the caller's devastating announcement in rising panic while he speaks; "
        "the whole time he talks, he glances back in mounting desperation toward his mother's stall across the market pavement, his voice cracking with shock; "
        "the instant he finishes, he pivots his back to the market, his knees trembling violently on the asphalt; afternoon dust drifts along the roadside curb",
        _N + ["nocash"]),

    67: (8, "Close-up, the son's face draining as he hears the amount",
        ["ton"], "market_road", T5,
        "the young man in the grey T-shirt, all color draining from his face until his lips turn pale, whispers the devastating news into the receiver while his eyes widen in horror; "
        "the whole time he talks, the hand holding the smartphone shakes uncontrollably and his breath shudders in his chest; the instant he finishes speaking, "
        "he freezes in absolute paralysis, his mouth hanging slightly open; the golden late-afternoon sun catches the small silver amulet cord at his neck",
        _N + ["nocash"]),

    68: (8, "Close-up, the son turning slowly toward the stall, his mother small and blurred in the background pounding the mortar",
        ["ton", "sri"], "market_road", T5,
        "the young man in the grey T-shirt, his entire world shattering around him in agonizing realization, speaks his mother's full name into the phone while turning his head toward the stall; "
        "the whole time he talks, in the distant blurred background, his mother continues pounding the som-tam mortar with dedicated rhythm, completely unaware of the catastrophe; "
        "the instant the son finishes his final realization, the phone slips limply down against his hip, his eyes staring in desolate disbelief; the music hits a massive dramatic cliffhanger, cutting to black",
        _N + ["nocash"]),
}

DIRECTION = {
    (54, "sri"): "forced smile, lips trembling with held-back agony, trying to sound normal",
    (54, "ton"): "overflowing with proud satisfaction, lying smoothly with an earnest face",
    (55, "ton"): "bright, cheerful and affectionate, tidying the chili basket with energetic pride",
    (56, "ton"): "deeply warm, earnest and hopeful, grinning with innocent filial devotion",
    (56, "sri"): "voice held steady with agonizing effort, tenderly stroking his hair with brimming tears",
    (57, "ton"): "puzzled and intensely concerned, brow furrowed, leaning in to inspect her eyes",
    (57, "sri"): "frantically covering, pounding chilies with furious deflection, voice strained",
    (58, "sri"): "hurried, anxious and evasive, untying her apron with trembling fingers",
    (58, "ton"): "easy, cheerful and reassuring, accepting the pestle with a warm smile",
    (59, "sri_noapron"): "ashamed, desperate, speaking in a frantic hushed whisper behind the crates",
    (60, "sri_noapron"): "nodding frantically, a tiny thread of desperate hope entering her trembling voice",
    (61, "sri_noapron"): "fierce, resolute maternal sacrifice, whispering through gritted teeth while watching him",
    (62, "fon"): "terrified yet pushing herself, whispering in urgent breathless dread",
    (63, "ton"): "puzzled, slowing the pestle, voice rising in polite curiosity",
    (64, "boy"): "harsh, suspicious and menacing, rapping hard knuckles against the glass",
    (64, "fon"): "crying in helpless sorrow, rushing out her choked gratitude before hanging up",
    (65, "ton"): "uneasy, brow furrowed in confusion, stepping away toward the curb",
    (65, "sri"): "puffy-eyed and exhausted, steadying her voice with heroic maternal composure",
    (66, "ton"): "struck by sudden panic, voice cracking with horror, gripping the motorcycle seat",
    (66, "ton"): "struck by sudden panic, voice cracking with horror, gripping the motorcycle seat",
    (67, "ton"): "complete shock, voice draining to a hollow whisper, eyes wide with horror",
    (68, "ton"): "world collapsing in utter heartbreak, whisper cracking as the truth dawns on him",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

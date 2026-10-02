# -*- coding: utf-8 -*-
"""«ขายชื่อ» EP3 (film 5) closing act = shots 69-78. Source of truth for
tools/build_shotsheet.py. Lines: ep5-EP3-SCRIPT-v1.md (loaded by ep5-common.py).

Same rules as ep5-ACT3.data.py:
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
T3, T5 = _c.T3, _c.T5

PROPS_BY_SHOT = {
    69: ["@mortar_clay"], 70: ["@mortar_clay"], 71: ["@mortar_clay"],
    72: ["@scooter_pink", "@cards_pouch"], 73: ["@scooter_pink", "@cards_pouch"],
    74: ["@cards_pouch"], 75: ["@pickup_black"],
    76: ["@mortar_clay"], 77: ["@scooter_pink", "@toolbox_red"], 78: ["@mortar_clay"],
}

_N = ["nosubs", "noextra", "daylight"]

# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
    69: (8, "Two-shot at the stall, the son rushing back and dropping to his knees beside his mother",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, sobbing with his voice cracking, drops to his knees beside the stall and clutches the hem of his mother's apron with both oily hands while he confesses; "
        "the whole time he talks, the woman in the papaya-orange apron lowers the wooden pestle inch by inch, her eyes widening, her free hand trembling in the air above his head; "
        "the instant he finishes, she bends down to stare into his face and whispers her stunned question while the pestle slips from her fingers onto the table; "
        "the orange umbrella fringe flutters in the late afternoon breeze",
        _N + ["nocash"]),

    70: (8, "Close two-shot, the mother gripping her son's shoulders, both in tears",
        ["sri", "ton"], "market_stall", T5,
        "the woman in the papaya-orange apron, crying openly with tears streaming down her cheeks, grips her kneeling son by both shoulders and shakes him gently while she confesses her own lie; "
        "the whole time she talks, the young man in the grey T-shirt shakes his head and sobs, twisting the red work rag in both fists, his chest heaving; "
        "the instant she finishes, he chokes out one word and buries his face against her shoulder; a few shredded papaya strands scatter across the wooden table",
        _N + ["nocash"]),

    71: (8, "Medium, the mother wiping her son's face, the son straightening up with resolve",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, eyes red but jaw set with fierce resolve, straightens his back and wipes his tears with the back of his hand while he makes his promise; "
        "the whole time he talks, the woman in the papaya-orange apron dabs his cheeks with the corner of her apron and nods hard through her tears, lips pressed together; "
        "the instant he finishes, she squeezes both of his hands in hers and answers with a wet, proud smile; warm sunlight glows on the clay mortar beside them",
        _N + ["nocash"]),

    72: (8, "Medium at the roadside curb, the young woman braking her pink scooter beside the son, a cloth pouch in her hands",
        ["fon", "ton"], "market_road", T5,
        "the young woman in the mint-green shirt, breathless and trembling, brakes her pale pink scooter at the curb and pushes a small cloth pouch of plain blank plastic cards into the young man's hands while she speaks; "
        "the whole time she talks, the young man in the grey T-shirt hurries over, takes the pouch in both hands and stares at her in open bewilderment, his brow knotted; "
        "the instant she finishes, he grips the pouch to his chest and asks his short question; afternoon dust drifts along the roadside",
        _N + ["nocash", "nologo"]),

    73: (8, "Close two-shot, the young woman answering with wet eyes, the son holding the pouch",
        ["fon", "ton"], "market_road", T5,
        "the young woman in the mint-green shirt, tears brimming and voice shaking but sure, grips the handlebar of her pink scooter with white knuckles while she explains; "
        "the whole time she talks, the young man in the grey T-shirt hugs the cloth pouch against his chest and nods slowly, his eyes glistening with gratitude; "
        "the instant she finishes, she glances fearfully over her shoulder down the empty road and bites her lip; a warm breeze lifts loose strands of her ponytail",
        _N + ["nocash", "nologo"]),

    74: (10, "Three-shot at the roadside, the man in tiger print storming up, the son stepping in front of the young woman",
        ["boy", "fon", "ton"], "market_road", T5,
        "the man in the tiger-print shirt, face red with rage and veins standing out on his neck, storms up the curb and jabs a thick finger at the cloth pouch while he shouts; "
        "the whole time he shouts, the young man in the grey T-shirt steps between him and the young woman, hugging the pouch tightly to his chest with his feet planted; "
        "the instant the man finishes, the young woman in the mint-green shirt steps out beside the mechanic, crying but defiant, and answers her brother straight to his face with her fists clenched; "
        "nobody touches anybody; the man's gold chain flashes in the late afternoon sun",
        _N + ["nocash", "nologo"]),

    75: (8, "Close-up on the man in tiger print beside his black pickup, phone at his ear, the colour leaving his face",
        ["boy"], "market_road", T5,
        "the man in the tiger-print shirt, panic rising in his cracking voice, leans against the door of his matte-black pickup and repeats the caller's words while his gold-rimmed sunglasses slide down his sweating nose; "
        "the whole time he talks, his jaw stops chewing gum mid-bite and the hand holding the smartphone trembles harder and harder; "
        "the instant he finishes, his knees give way and he slumps down to sit on the roadside curb, the phone dangling from his hand; dust settles around the chrome wheels",
        _N + ["noscreen", "nologo", "nouniform", "nocash"]),

    76: (8, "Two-shot at the stall, the son hurrying back with his phone, the mother looking up",
        ["ton", "sri"], "market_stall", T5,
        "the young man in the grey T-shirt, laughing and crying at once, hurries back to the stall waving his smartphone with its dark screen turned away from camera while he gives the news; "
        "the whole time he talks, the woman in the papaya-orange apron rises slowly from her red plastic stool and lifts both hands to cover her mouth, her shoulders starting to shake; "
        "the instant he finishes, she sobs out her question with relief flooding her face; the orange umbrella glows in the warm late light",
        _N + ["noscreen", "nocash"]),

    77: (8, "Medium at the roadside repair spot, the son fixing the pink scooter, the young woman standing by",
        ["fon", "ton"], "repair_soi", T3,
        "the young woman in the mint-green shirt, eyes still a little puffy but smiling warmly, holds out her open hand toward the mechanic with a teasing tilt of her head while she speaks; "
        "the whole time she talks, the young man in the grey T-shirt crouches beside the pale pink scooter tightening a wheel nut with a wrench, grinning wider at every word; "
        "the instant she finishes, he wipes his oily hands on the red rag and answers with bright pride; the blue tarp overhead ripples in the midday breeze",
        _N + ["nocash", "nologo"]),

    78: (8, "Two-shot at the stall in warm late light, the mother handing her son the pestle",
        ["sri", "ton"], "market_stall", T5,
        "the woman in the papaya-orange apron, tender and proud with glistening eyes, presses the wooden pestle into her son's hand while she gives him her lesson; "
        "the whole time she talks, the young man in the grey T-shirt takes the pestle and pounds the clay mortar slowly, looking up at her face with deep emotion; "
        "the instant she finishes, he answers with an earnest grin and both of them burst out laughing together; golden light spills across the chilies and the green papaya",
        _N + ["nocash"]),
}

DIRECTION = {
    (69, "ton"): "sobbing hard, voice cracking on every word, clutching the hem of her apron",
    (69, "sri"): "stunned breathless whisper, eyes wide, the pestle slipping from her fingers",
    (70, "sri"): "crying openly, voice breaking, shaking his shoulders as she confesses",
    (70, "ton"): "a single choking sob, collapsing against her shoulder",
    (71, "ton"): "firm through tears, jaw set, voice steady with hard-won resolve",
    (71, "sri"): "wet proud smile, voice trembling, squeezing his hands hard",
    (72, "fon"): "breathless and trembling, pushing the pouch into his hands with urgent courage",
    (72, "ton"): "stunned and bewildered, gripping the pouch to his chest",
    (73, "fon"): "tears brimming, voice shaking but sure, white knuckles on the handlebar",
    (74, "boy"): "shouting at full volume, face red with rage, jabbing a finger at the pouch",
    (74, "fon"): "crying yet defiant, voice rising, fists clenched as she stands her ground",
    (75, "boy"): "panic rising, voice cracking into a frightened croak, sunglasses sliding off",
    (76, "ton"): "laughing and crying at once, breathless with joy, waving the phone",
    (76, "sri"): "sobbing with relief through the hands over her mouth",
    (77, "fon"): "warm teasing smile, playful insistence, eyes still a little puffy",
    (77, "ton"): "beaming with bright pride, wiping his oily hands on the red rag",
    (78, "sri"): "tender and proud, voice soft and glistening with emotion",
    (78, "ton"): "earnest grin, voice full of feeling, pounding the mortar slowly",
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

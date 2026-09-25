# -*- coding: utf-8 -*-
"""«ตาชั่งของเสี่ย» ACT2 = EP3 + EP4, shots 24-53 (3:04-7:04). Source of truth for
tools/build_shotsheet.py.

Shares every block with ACT1 (characters, voices, locations, negatives) by loading
docs/scripts/taachang-ACT1.data.py, and adds only the states and places ACT2 needs:
เสี่ย's factory clothes, กล้า's work clothes, the factory scale-man and worker, the
half-empty yard, the factory weigh yard. Dialogue is read from SCRIPT-v2 at import.

Lessons from ACT1 already applied (CTO_Flow_Omni1.1_Continuity notes 2026-09-25):
- the 11-year-old and money are never in one prompt with positive money words (S30:
  the day's pay stays in a closed cloth pouch, the `nomoney` block);
- nobody whispers or murmurs (burned captions); every scale shot carries the
  platform-scale block and @yard_scale.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "taachang_act1", Path(__file__).with_name("taachang-ACT1.data.py"))
_a1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a1)

STYLE = _a1.STYLE
CHAR = dict(_a1.CHAR)
WARDROBE = dict(_a1.WARDROBE)
VOICE = dict(_a1.VOICE)
LOC = dict(_a1.LOC)
NOT = dict(_a1.NOT)
PROP_FOR_NOT = dict(_a1.PROP_FOR_NOT)
_V = _a1._V

CHAR["sia_f"] = ("@sia__face",
  "a heavy-set Thai-Chinese man of fifty with a round fleshy face, small narrow eyes, black hair "
  "slicked straight back with grey at the temples and a thin moustache, wearing a cream polo shirt "
  "with no logo tucked into dark slacks, a leather belt, a thick gold chain and black sunglasses "
  "pushed up on top of his head",
  "The heavy man in the cream polo shirt")
WARDROBE["sia_f"] = "@sia__factory"
VOICE["sia_f"] = VOICE["sia_b"]

CHAR["kla_w"] = ("@kla__face",
  "a slim Thai boy of sixteen with messy short black hair and earnest dark eyes, in a plain grey "
  "T-shirt, faded jeans, white cotton work gloves and worn canvas sneakers",
  "The boy in the grey T-shirt")
WARDROBE["kla_w"] = "@kla__work"
VOICE["kla_w"] = VOICE["kla_s"]

CHAR["tor_s"] = ("@tor__face",
  "a small Thai boy of eleven with round cheeks and a straight black bowl-cut, in a plain white "
  "primary-school shirt with nothing written or embroidered on it, navy-blue shorts, white socks, "
  "black school shoes and a small plain dark backpack",
  "The little boy in the school uniform")
WARDROBE["tor_s"] = "@tor__school"
VOICE["tor_s"] = VOICE["tor_h"]

# Uploaded as full-body plates only: the plate is both face and clothes, no wardrobe chip.
CHAR["scale"] = ("@scaleman__work",
  "a lean Thai man of forty-five with a hard weathered face and short black hair, in a faded "
  "light-blue work shirt with no logo, dark work trousers, a plain cap and black rubber boots, a "
  "pencil tucked behind one ear",
  "The scale-man in the blue work shirt")
VOICE["scale"] = (_V, "the flat, dry, mid-low voice of a Thai man of forty-five")
CHAR["worker"] = ("@worker__work",
  "a sturdy sunburnt Thai man of thirty with short black hair, in a plain grey work shirt and grey "
  "work trousers, cotton work gloves and black rubber boots",
  "The worker in grey")
VOICE["worker"] = (_V, "the loud, rough voice of a Thai man of thirty")

LOC["lan_half"] = ("@lan__halfempty",
  "the same small recycling yard under the rusty corrugated-metal roof, now mostly empty: only "
  "three or four sacks left, bare dusty concrete floor, one empty crumpled sack on the ground, the "
  "low rusty blue platform scale with its round cream dial, the battered wooden desk and the red "
  "plastic chair")
LOC["fac"] = ("@fac__weigh",
  "the weighing yard of a large recycling factory on the outskirts of Bangkok: open concrete, a "
  "large flat steel truck platform scale set into the ground with a small booth beside it, tall "
  "stacks of compressed bales of crushed clear plastic bottles bound with wire, a forklift in the "
  "background, a high corrugated steel warehouse wall")

PROPS_BY_SHOT = {
    24: ["@yard_scale"], 25: ["@yard_scale"], 26: ["@yard_scale"], 27: ["@sack", "@cart", "@yard_scale"],
    28: ["@cart"], 29: ["@cart"], 31: ["@cart"], 32: ["@sack", "@yard_scale"], 33: ["@pickup__empty"],
    36: ["@jar__full"], 37: ["@jar__full"], 38: ["@jar__full"], 39: ["@jar__full"],
    40: ["@pickup__loaded"], 49: ["@pickup__loaded"], 51: ["@pickup__loaded"],
}

LANAFT = "hot afternoon, bright daylight"
HOME = "late afternoon, daylight through the gaps in the zinc"
FACT = "the next morning, harsh bright daylight"

# n: (seconds, framing, [char keys, subject first], loc, time of day, action, [nots])
_META = {
 24: (8, "Close-up on the schoolboy, his father at the edge of frame", ["kla_s", "sia_b"], "lan", LANAFT,
      "the schoolboy lifts his chin and answers his father, scared but defiant, voice trembling but "
      "clear", ["nosubs"]),
 # v2.4 (2026-09-26): the three-shot vanished from Flow twice (once with him pointing at her face,
 # once from a step away). CEO chose a solo shot, as S19/S30 passed when solo.
 25: (8, "Close-up on the heavy man alone, pointing off-frame, his face three-quarters to camera",
      ["sia_b"], "lan", LANAFT,
      "the heavy man stands alone in frame, points off-frame toward someone and shouts his accusation "
      "for everyone in the yard to hear, vicious and loud, glancing sideways at an onlooker off-frame",
      ["dial", "nosubs"]),
 26: (8, "Two-shot, the old woman standing straight, both faces three-quarters to camera",
      ["yai_c", "sia_b"], "lan", LANAFT,
      "the old woman straightens her back and speaks while crying openly, tears streaming down her "
      "face, voice breaking with sobs but standing her ground; the heavy man barks back, cutting her "
      "off", ["dial", "nosubs"]),
 # v2.6 (CEO 2026-09-26): take 1 had her wheel the SCALE away as if it were her cart. The action no
 # longer mentions the scale at all; her sacks are already on her own cart.
 27: (8, "Medium shot, she wheels her own loaded push-cart away", ["yai_c", "sia_b"], "lan", LANAFT,
      "the old woman wipes her tears with the back of a gloved hand and, suddenly calm and resolute, "
      "grips the handles of her own small rusty push-cart, already loaded with her two sacks of "
      "bottles, and turns it toward the gate while she speaks, her eyes still wet; the heavy man "
      "stares at her. The low platform scale stays fixed on the ground behind them and nobody "
      "touches it", ["dial", "nosubs"]),
 28: (8, "Medium close-up on the heavy man shouting after her", ["sia_b"], "lan", LANAFT,
      "the heavy man jeers and laughs, shouting after the old woman as she pushes her cart away out "
      "of frame, his mouth twisted in a sneer", ["nosubs"]),
 # 2026-09-25: the first take (the 11-year-old in his school-uniform plate) vanished; every shot with
 # him in home clothes rendered. Hypothesis n=1: child + school uniform. Home clothes here.
 29: (8, "Tracking two-shot along the canal path", ["tor_h", "yai_c"], "soi",
      "hot afternoon, bright sun",
      "the little boy helps the old woman push her loaded cart along the canal "
      "path, cheerful and sweating; she pants but smiles as she answers, the row of electricity "
      "poles running ahead of them", ["nosubs"]),
 # v2.3 (2026-09-26): the two-shot with the little boy and the day's money (notes, then a closed
 # pouch) vanished from Flow three times with no card. Now the old woman alone, no money at all.
 30: (8, "Close-up on the old woman alone on the mat, her face three-quarters to camera", ["yai_h"],
      "baan", HOME,
      "the old woman sits alone on the mat with her empty hands in her lap, stunned, hands trembling, "
      "voice cracking and tears welling, slowly realising it as she speaks to herself", ["nosubs"]),
 31: (8, "Medium shot, the woman in the straw hat pushing her cart past the yard gate",
      ["pa", "sia_b"], "lan", LANAFT,
      "the woman in the straw hat pushes her cart past the yard gate, pleased, calling out with a "
      "small mocking smile; the heavy man panics, waving both arms and shouting after her",
      ["nosubs"]),
 32: (8, "Medium shot, the heavy man alone in the half-empty yard", ["sia_b"], "lan_half", LANAFT,
      "the heavy man kicks an empty sack across the bare floor, frustrated, cursing loudly at the "
      "empty yard", ["dial", "nosubs"]),
 33: (8, "Two-shot, father and son by the white pickup", ["sia_b", "kla_w"], "lan_half", LANAFT,
      "the heavy man slaps the side of his old white pickup, eyes lighting up as he announces his "
      "plan; his son in a grey T-shirt listens", ["nosubs"]),
 34: (8, "Two-shot, father and son", ["kla_w", "sia_b"], "lan_half", LANAFT,
      "the boy asks, doubtful and quiet; the heavy man laughs arrogantly and taps his own temple "
      "while he answers", ["nosubs"]),
 35: (8, "Medium shot at the doorway of the zinc shack", ["kla_w", "yai_h"], "baan", HOME,
      "the boy in the grey T-shirt stands at the doorway, head bowed, pressing his palms together in "
      "a wai, ashamed, small shaky voice; the old woman answers warmly and takes his arm to bring him "
      "in", ["nosubs"]),
 36: (8, "Medium three-shot, the little boy holding up the jar of pebbles",
      ["tor_h", "kla_w", "yai_h"], "baan", HOME,
      "the little boy proudly holds up the glass jar full of small pebbles to show the older boy, "
      "whose face falls as the meaning dawns on him; the old woman sits beside them", ["nosubs"]),
 37: (8, "Close two-shot, the older boy beside the old woman, looking into the jar", ["yai_h", "kla_w"],
      "baan", HOME,
      "the old woman speaks first, plainly, without complaint; only after she has finished, the boy "
      "takes a single pebble out of the jar and stares at it, horrified, voice hoarse", ["nosubs"]),
 38: (8, "Close two-shot, her hand on his wrist, both faces three-quarters to camera",
      ["kla_w", "yai_h"], "baan", HOME,
      "the boy lifts the jar with a determined face and glistening eyes; the old woman, frightened "
      "and pleading, grips his wrist to stop him", ["nosubs"]),
 39: (8, "Close-up, the boy setting the jar down", ["kla_w", "yai_h"], "baan", HOME,
      "the boy sets the jar gently back down and speaks quietly, steady and resolved", ["nosubs"]),
 # v2.6 (CEO 2026-09-26): take 1 had him climb out THROUGH the closed door. Parked, both stay seated.
 40: (8, "Medium two-shot through the open driver's window of the parked white pickup, the factory weigh yard behind",
      ["sia_f", "kla_w"], "fac", FACT,
      "the old white pickup piled high with bales is already parked, engine off, in the factory weigh "
      "yard; the heavy man in a cream polo sits behind the wheel with the door closed and turns to "
      "his son, grinning broadly, excited; his son in the passenger seat answers flatly. Both stay "
      "seated inside the cab the whole time; nobody opens a door or gets out", ["nosubs"]),
 41: (8, "Medium shot, the heavy man and the factory scale-man", ["sia_f", "scale"], "fac", FACT,
      "the heavy man swaggers up and claps the scale-man on the shoulder, cocky; the scale-man "
      "answers bored and flat", ["nosubs"]),
 42: (8, "Close-up low on the truck scale, the scale-man's boot nudging a bale corner off the edge "
          "(the same framing as the yard's first shot)", ["kla_w", "sia_f", "scale"], "fac", FACT,
      "the scale-man's rubber boot nudges the corner of a bale off the edge of the platform onto the "
      "ground; the boy sees it, alarmed, tugs his father's arm and tells him urgently, low but "
      "clearly spoken; the heavy man brushes him off, annoyed", ["nosubs"]),
 43: (8, "Two-shot at the weigh booth", ["scale", "sia_f"], "fac", FACT,
      "the scale-man calls the weight deadpan while writing on a clipboard turned away from the "
      "camera; the heavy man's eyes bulge and he shouts in shock", ["nosubs"]),
 44: (8, "Close-up on the scale-man, the heavy man at the edge of frame", ["scale", "sia_f"], "fac", FACT,
      "the scale-man shrugs with a thin smirk while he answers; the heavy man boils over and shouts "
      "back", ["nosubs"]),
 45: (8, "Medium shot, the heavy man pointing at the scale-man's boot", ["sia_f", "scale"], "fac", FACT,
      "the heavy man, raging and trembling with fury, points down at the scale-man's boot and "
      "screams at him", ["nosubs"]),
 46: (8, "Medium three-shot, a worker laughing behind", ["scale", "sia_f", "worker"], "fac", FACT,
      "the scale-man laughs in the heavy man's face, mocking and loud, while the worker behind them "
      "roars with laughter", ["nosubs"]),
 47: (8, "Close-up on the boy, loud enough for the workers to hear", ["kla_w", "sia_f"], "fac", FACT,
      "the boy steps up beside his father and shouts, anguished, tears in his eyes, voice cracking; "
      "his father freezes, stunned and pale", ["nosubs"]),
 48: (8, "Medium shot, the worker turning to the heavy man", ["worker", "sia_f"], "fac", FACT,
      "the worker points at the heavy man and laughs at him, jeering", ["nosubs"]),
 49: (8, "Close-up on the heavy man, cornered, the loaded pickup behind him", ["sia_f"], "fac", FACT,
      "the heavy man looks at his truck heaped with bales, beaten, shoulders sagging, voice hoarse "
      "and hollow", ["nosubs"]),
 # v2.3 (2026-09-26): the stack of prop notes vanished from Flow with no card. A sealed envelope.
 # v2.4: the envelope two-shot vanished too. CEO chose a solo shot; the scale-man's line is cut and
 # the heavy man says the amount himself.
 50: (8, "Close-up on the heavy man alone, holding a sealed brown envelope", ["sia_f"], "fac", FACT,
      "the heavy man stands alone in frame holding a thin sealed brown paper envelope he has just been "
      "handed, staring down at it, choking on it, voice shaking with humiliation", ["nosubs"]),
 51: (8, "Medium two-shot, the heavy man slumped on the truck's step", ["sia_f", "kla_w"], "fac", FACT,
      "the heavy man sits down heavily on the step of the pickup, collapsed, voice breaking and "
      "bitter; the boy standing beside him answers gently but pointedly", ["nosubs"]),
 52: (8, "Close-up on the boy crouching to his father's level", ["kla_w", "sia_f"], "fac", FACT,
      "the boy crouches down to his father's eye level and speaks firmly, eyes wet, holding his "
      "father's gaze", ["nosubs"]),
 53: (8, "Close two-shot, both faces three-quarters to camera", ["sia_f", "kla_w"], "fac", FACT,
      "the heavy man whips his head round to his son, disbelieving and confused; the boy answers "
      "deliberately, word by word", ["nosubs"]),
}

_NAME = {"yai_c": "ยาย", "yai_h": "ยาย", "sia_b": "เสี่ย", "sia_f": "เสี่ย", "kla_s": "กล้า",
         "kla_w": "กล้า", "tor_h": "ต่อ", "tor_s": "ต่อ", "pa": "ป้า", "scale": "คนชั่ง", "worker": "คนงาน"}


def _build():
    lines = _a1._lines_from_script()
    shots = []
    for n in sorted(_META):
        secs, framing, chars, loc, tod, action, nots = _META[n]
        spoken = []
        for who, direction, line in lines[n]:
            key = next((c for c in chars if _NAME[c] == who), None)
            if key is None:
                raise SystemExit(f"shot {n}: speaker {who} is not in the shot's cast {chars}")
            spoken.append((key, direction, line))
        shots.append((n, secs, framing, chars, loc, tod, action, spoken, nots))
    return shots


SHOTS = _build()

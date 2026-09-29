# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) acting test, shots 1-5 only.

CEO 2026-09-27: "รอบนี้ขอ Acting แบบล้นๆ ได้ไหม ... อยากให้ AI ในฉาก ดูมีชีวิตชีวา ไม่แข็งทื่อ
ยืนฟังคนอื่น ใครที่อยู่ในฉาก จะต้องมีอะไร ทำตามบทของตัวเอง ไม่ยืนนิ่ง รอคนพูดจบ
ลอง ทำ S1-S5 มาให้ดูก่อนได้ เดี๋ยวจะบอกว่าต้องปรับทั้งเรื่องด้วย Skill ใหม่ไหม"

Same cast, plates, voices, languages and spoken lines as ep4-ACT1.data.py. Three things change:
1. ACTION: every person in frame gets a continuous timeline. The listener keeps doing their
   own task and reacts to each phrase, and never waits for the speaker to finish.
2. Line directions are pushed to 4-5/5, physical and loud.
3. STYLE carries one ensemble-acting rule for the whole shot.
If the CEO passes it, the same pattern goes into ACT1-3 and the story skill.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4act1", Path(__file__).with_name("ep4-ACT1.data.py"))
_a = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a)
_c = _a._c

CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _a.CHAR, _a.WARDROBE, _a.VOICE, _a.LANG, _a.LOC, _a.NOT, _a.PROP_FOR_NOT)

STYLE = _c.STYLE_ACTING  # identical text to what was shot 2026-09-27 (moved to ep4-common)

PROPS_BY_SHOT = {n: h for n, h in _a.PROPS_BY_SHOT.items() if n <= 5}

ACTION = {
 1: "the woman in hot pink, gloating and triumphant, grinning ear to ear with shining eyes, "
    "strolls along the paddy edge under her open hot-pink silk parasol, flicks the heavy golden "
    "rice ears with her closed fan, sweeps the fan wide over the whole field as if she already "
    "owns it, and laughs out loud in the middle of her line while she speaks; the whole time she "
    "talks, the headman in the light-blue shirt squirms beside her without a word: he rocks his "
    "old black bicycle back and forth by the handlebar, twists the checked cloth from his waist "
    "into a tight rope, shifts from foot to foot, darts his eyes to the empty road and back, and "
    "gives a sick nervous chuckle at her laugh; the instant she finishes he leans in close, "
    "hunches his shoulders and wags one finger nervously while he answers; the ripe rice sways "
    "in the wind around them",
 2: "the woman in hot pink, sugary and smug, one eyebrow high, taps the headman's chest three "
    "times with her closed fan, straightens his collar with two fingers and pats his cheek twice "
    "while she speaks; the whole time she talks the headman flinches at every tap, glances left "
    "and right to check nobody is watching, mops the sweat off his forehead with the checked "
    "cloth and bobs his head again and again; the instant she finishes he presses his palms "
    "together in a deep wai, bowing twice, face flushed red, with a wide sick forced smile while "
    "he answers",
 3: "the woman in the indigo blouse, cheerful and loud, beaming, scoops hot sticky rice out of "
    "the steaming basket into a round woven bamboo basket with her indigo-stained fingers, shakes "
    "her hot fingertips and blows on them with a laugh, and waves her whole arm high over her "
    "head while she calls out; at the same moment the headman rides his old black bicycle into "
    "the red-dirt yard, wobbles, skids to a stop with one foot down, lifts his hand in a stiff "
    "half-wave, and his smile is too wide and keeps slipping as she talks; a hen scurries out "
    "from under the front wheel; thick steam billows around her",
 4: "the headman, touched and guilty, eyes wet and red, lifts the warm woven sticky-rice basket "
    "in both hands, hugs it to his chest, breathes in its smell with his eyes shut and shakes "
    "his head slowly while he speaks; the whole time he talks the woman in the indigo blouse "
    "bustles around him without stopping: she yanks the basket's cord into a tight double knot, "
    "brushes a grain of rice off his shoulder, tucks a small banana-leaf parcel into his shirt "
    "pocket and slaps his arm with a big laugh while she answers; the moment she says her son's "
    "name the headman's whole body freezes, his smile drops and his eyes slide away from her",
 5: "the woman in the green blouse, shy and embarrassed, bowing her head again and again, holds "
    "out an empty plastic bucket in both hands, scratches the back of her neck and glances away "
    "while she speaks; the whole time she talks the woman in the indigo blouse is already "
    "moving: she pulls the wooden lid off the big clay jar, plunges a coconut-shell scoop deep "
    "into the raw rice and pours scoop after scoop into the bucket until it heaps over, laughing "
    "and shaking her head; the woman in the green blouse grabs her wrist to stop her, and the "
    "woman in the indigo blouse pushes her hand away playfully and throws in one more big scoop "
    "while she answers; rice grains spill over the rim onto the ground",
}

DIRECTION = {
 (1, "hong"): "gloating and triumphant, grinning ear to ear, laughing out loud in the middle "
              "of the line, sweeping her fan over the field",
 (1, "bm"): "uneasy and squirming, a nervous chuckle, voice dropped low, eyes darting to the road",
 (2, "hong"): "sugary and smug, one eyebrow high, tapping his chest with her fan",
 (2, "bm"): "ashamed, face flushed red, bowing twice with a sick forced smile, palms pressed together",
 (3, "kp1"): "cheerful and very loud, beaming, waving her whole arm high over her head",
 (4, "bm"): "touched and guilty, voice cracking, eyes wet, hugging the basket to his chest",
 (4, "kp1"): "cheerful and bustling, laughing, slapping his arm",
 (5, "pa"): "shy and embarrassed, bowing her head again and again, voice small",
 (5, "kp1"): "generous and laughing out loud, waving the refusal away, scooping more",
}

# _META row: (secs, framing, chars, loc, tod, action, nots); only the action is replaced.
_META = {n: m[:5] + (ACTION[n],) + m[6:] for n, m in _a._META.items() if n in ACTION}

SHOTS = []
for (n, secs, framing, chars, loc, tod, action, spoken, nots) in _c.build_shots(_META):
    spoken = [(k, DIRECTION[(n, k)], line) for k, _d, line in spoken]
    SHOTS.append((n, secs, framing, chars, loc, tod, action, spoken, nots))

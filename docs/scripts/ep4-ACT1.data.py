# -*- coding: utf-8 -*-
"""«ขายฝากนาแม่» (film 4) ACT1 = EP1 + EP2, shots 1-23 (0:00-3:04). Source of truth for
tools/build_shotsheet.py. Shared cast, voices, languages, locations and negatives live in
ep4-common.py; this file adds who is in each shot, where, when and the English action.

Rules carried in from films 1-3:
- the speaker's action happens WHILE the line is said, never before it ("then" is banned);
- the first speaker's action is written first, because Flow speaks in ACTION order;
- every person in frame has their own physical action and a loud, physical emotion;
- no children, no uniforms, day only, at most 3 people, no money in frame, no real brand.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("ep4common", Path(__file__).with_name("ep4-common.py"))
_c = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_c)

STYLE, CHAR, WARDROBE, VOICE, LANG, LOC, NOT, PROP_FOR_NOT = (
    _c.STYLE_ACTING, _c.CHAR, _c.WARDROBE, _c.VOICE, _c.LANG, _c.LOC, _c.NOT, _c.PROP_FOR_NOT)
T1 = _c.T1

PROPS_BY_SHOT = {
    1: ["@parasol_pink"], 3: ["@kratip"], 4: ["@kratip"], 6: ["@trunk_letters"],
    7: ["@parasol_pink"], 9: ["@trunk_letters"], 11: ["@motorbike"],
}

_N = ["nosubs", "noextra"]

# Overflow acting (CEO 2026-09-27, story skill): every person in frame keeps a timeline;
# S1-S5 are the approved acting test, identical to ep4-ACTacting.data.py.
# n: (seconds, framing, [char keys, first speaker first], loc, time of day, action, [nots])
_META = {
 1: (8, 'Medium wide at the edge of the golden paddy, both faces three-quarters to camera',
    ['hong', 'bm'], 'na_ripe', T1,
    'the woman in hot pink, gloating and triumphant, grinning ear to ear with shining eyes, '
    'strolls along the paddy edge under her open hot-pink silk parasol, flicks the heavy '
    'golden rice ears with her closed fan, sweeps the fan wide over the whole field as if she'
    ' already owns it, and laughs out loud in the middle of her line while she speaks; the '
    'whole time she talks, the headman in the light-blue shirt squirms beside her without a '
    'word: he rocks his old black bicycle back and forth by the handlebar, twists the checked'
    ' cloth from his waist into a tight rope, shifts from foot to foot, darts his eyes to the'
    ' empty road and back, and gives a sick nervous chuckle at her laugh; the instant she '
    'finishes he leans in close, hunches his shoulders and wags one finger nervously while he'
    ' answers; the ripe rice sways in the wind around them', _N + ['nocash']),
 2: (8, "Close two-shot, the fan tapping the headman's chest",
    ['hong', 'bm'], 'na_ripe', T1,
    "the woman in hot pink, sugary and smug, one eyebrow high, taps the headman's chest three"
    ' times with her closed fan, straightens his collar with two fingers and pats his cheek '
    'twice while she speaks; the whole time she talks the headman flinches at every tap, '
    'glances left and right to check nobody is watching, mops the sweat off his forehead with'
    ' the checked cloth and bobs his head again and again; the instant she finishes he '
    'presses his palms together in a deep wai, bowing twice, face flushed red, with a wide '
    'sick forced smile while he answers', _N + ['nocash']),
 3: (8, 'Medium under the house on stilts, steam rising from the sticky-rice steamer',
    ['kp1', 'bm'], 'home', T1,
    'the woman in the indigo blouse, cheerful and loud, beaming, scoops hot sticky rice out '
    'of the steaming basket into a round woven bamboo basket with her indigo-stained fingers,'
    ' shakes her hot fingertips and blows on them with a laugh, and waves her whole arm high '
    'over her head while she calls out; at the same moment the headman rides his old black '
    'bicycle into the red-dirt yard, wobbles, skids to a stop with one foot down, lifts his '
    'hand in a stiff half-wave, and his smile is too wide and keeps slipping as she talks; a '
    'hen scurries out from under the front wheel; thick steam billows around her', _N),
 4: (8, 'Two-shot at the bamboo platform, the sticky-rice basket between them',
    ['bm', 'kp1'], 'home', T1,
    'the headman, touched and guilty, eyes wet and red, lifts the warm woven sticky-rice '
    'basket in both hands, hugs it to his chest, breathes in its smell with his eyes shut and'
    ' shakes his head slowly while he speaks; the whole time he talks the woman in the indigo'
    " blouse bustles around him without stopping: she yanks the basket's cord into a tight "
    'double knot, brushes a grain of rice off his shoulder, tucks a small banana-leaf parcel '
    'into his shirt pocket and slaps his arm with a big laugh while she answers; the moment '
    "she says her son's name the headman's whole body freezes, his smile drops and his eyes "
    'slide away from her', _N),
 5: (8, 'Medium beside the big clay jar next to the rice barn',
    ['pa', 'kp1'], 'home', T1,
    'the woman in the green blouse, shy and embarrassed, bowing her head again and again, '
    'holds out an empty plastic bucket in both hands, scratches the back of her neck and '
    'glances away while she speaks; the whole time she talks the woman in the indigo blouse '
    'is already moving: she pulls the wooden lid off the big clay jar, plunges a coconut-'
    'shell scoop deep into the raw rice and pours scoop after scoop into the bucket until it '
    'heaps over, laughing and shaking her head; the woman in the green blouse grabs her wrist'
    ' to stop her, and the woman in the indigo blouse pushes her hand away playfully and '
    'throws in one more big scoop while she answers; rice grains spill over the rim onto the '
    'ground', _N),
 6: (8, 'Close-up on the old tin trunk, a plain envelope going in',
    ['pa', 'kp1'], 'home', T1,
    'the woman in the green blouse, curious and nosy, head tilted, holds out a plain white '
    'envelope in both hands, taps it twice with one finger and peers at it while she speaks; '
    'the whole time she talks the woman in the indigo blouse, carefree, wipes her wet hands '
    'on her checked cloth, flips open the lid of the old tin trunk and laughs shyly behind '
    'the back of her hand; the instant the woman in the green blouse finishes, the woman in '
    'the indigo blouse takes the envelope, drops it unopened on top of the other envelopes, '
    'slaps the lid shut and waves the matter away while she answers; a hen pecks in the dust '
    'beside the trunk', _N + ['noletter']),
 7: (8, 'Medium in the red-dirt yard, the woman in hot pink arriving under her parasol',
    ['hong', 'kp1'], 'home', T1,
    'the woman in hot pink, sickly sweet, smiling with cold eyes, sweeps into the red-dirt '
    'yard under her open hot-pink parasol, fanning herself nonstop, looks the house up and '
    'down and flicks her fan toward the rice fields beyond the house while she speaks; the '
    'whole time she talks the woman in the indigo blouse, puzzled, keeps wiping her hands on '
    'her checked cloth, glances back at the steaming rice basket and walks out to meet her '
    'with a polite, uncertain smile that slowly freezes; the instant the woman in hot pink '
    'finishes, the woman in the indigo blouse stops dead, plants her hands on her hips, '
    'laughs in disbelief and points firmly at the ground while she answers; a hen scatters '
    "out of the parasol's path", _N),
 8: (8, 'Close two-shot, the fan stopped, both faces in profile to each other',
    ['hong', 'kp1'], 'home', T1,
    'the woman in hot pink, cold and sweet with a thin one-sided smile, snaps her fan shut, '
    'leans in close, taps her own palm with the closed fan on every point and tilts her head '
    'while she speaks; the whole time she talks the woman in the indigo blouse, shocked, face'
    ' draining pale, twists her checked cloth in both fists, her eyes darting between the '
    "woman's face and the fan, her breath quickening; the instant the woman in hot pink "
    'finishes, the woman in the indigo blouse steps half a step back and shakes her head '
    "hard, again and again, while she answers; the parasol's pink shadow trembles on the dust", _N + ['nocash']),
 9: (8, 'Medium, kneeling at the open tin trunk, envelopes spilling on the ground',
    ['kp1', 'hong'], 'home', T1,
    'the woman in the indigo blouse, panicking, hands shaking, drops to her knees at the open'
    ' tin trunk, flings envelopes out onto the ground by the handful, digs to the bottom and '
    'tears open a faded red cloth bundle to find it empty, crying out in a breaking voice '
    'while she speaks; the whole time she talks the woman in hot pink stands behind her, '
    'bored and sweet, fanning herself slowly, admiring her own fingernails and rolling her '
    'eyes at the sky; the instant the woman in the indigo blouse finishes, the woman in hot '
    'pink yawns behind her fan and nudges an envelope with the tip of her shoe while she '
    'answers; envelopes flutter across the red dirt in the breeze', _N + ['noletter', 'nocash']),
 10: (8, 'Medium, the woman in pink walking away, the mother collapsing onto the bamboo platform',
     ['hong', 'kp1'], 'home', T1,
     'the woman in hot pink, gleeful, twirls her open parasol and struts away across the yard '
     'without turning back, waggling her fan over her shoulder in a mocking goodbye while she '
     'calls out; the whole time she talks the woman in the indigo blouse, wailing, body '
     'shaking, staggers two steps after her with one hand reaching out, her knees give way and'
     ' she sinks down onto the bamboo platform hugging the empty red cloth to her chest, '
     'rocking back and forth; a hen flaps up off the platform and away', _N + ['nocash']),
 11: (8, 'Medium wide, the son riding into the yard on a red-and-black motorbike',
     ['sa_c', 'kp1'], 'home', T1,
     'the young man in the white T-shirt, happy, grinning with deep dimples, rides a small '
     'red-and-black motorbike into the yard, brakes, kicks down the stand and lifts a plastic '
     'bag of oranges high off the handlebar while he calls out, his grin fading as he sees his'
     ' mother; the whole time he talks the woman in the indigo blouse sits sobbing on the '
     'bamboo platform, rocking, head down, clutching the empty red cloth, and slowly lifts her'
     ' red, swollen eyes to him; red dust drifts up behind the motorbike', _N),
 12: (8, 'Two-shot, the mother holding up the empty red cloth, oranges rolling in the dust',
     ['kp1', 'sa_c'], 'home', T1,
     'the woman in the indigo blouse, furious and heartbroken, tears streaming, jumps up from '
     'the platform, marches at her son and shakes the empty faded red cloth in his face, '
     'jabbing a finger at it while she shouts; the whole time she talks the young man in the '
     'white T-shirt, face pale, lips trembling, lets the bag of oranges slip from his hand so '
     'oranges roll across the red dirt, raises both palms and backs away step by step; the '
     'instant she finishes, he stumbles over an orange and stammers while he answers, both '
     'hands still raised', _N),
 13: (8, 'Close-up on the son reading a letter, the paper edge-on to camera',
     ['sa_c', 'kp1'], 'home', T1,
     'the young man in the white T-shirt, face drained, eyes welling, reads a letter aloud '
     'with both hands shaking so hard the paper rattles, lips quivering, and on the last words'
     ' he crushes the letter against his chest as his face collapses into tears while he '
     'speaks; the whole time he reads, behind him the woman in the indigo blouse, trembling, '
     'presses the red cloth to her mouth, shakes her head slowly and sways on her feet', _N + ['noletter', 'nocash']),
 14: (8, 'Medium, the son on his knees in the red dust',
     ['sa_c', 'kp1'], 'home', T1,
     'the young man in the white T-shirt, sobbing out a confession, drops to his knees in the '
     'red dirt, pounds his fists into the dust and grabs handfuls of it while he speaks; the '
     'whole time he talks the woman in the indigo blouse, rigid, arms folded tight across her '
     'chest, tears running, stares down at him with her chin trembling, turns her face away '
     'and back again, her breath coming in short gasps; dust rises around his knees', _N + ['nocash']),
 15: (8, "Two-shot, the mother gripping her kneeling son's shoulders",
     ['kp1', 'sa_c'], 'home', T1,
     'the woman in the indigo blouse, shouting in rage, eyes red, grabs her kneeling son by '
     'both shoulders and shakes him hard on every word, slapping his shoulder once with her '
     'open hand while she speaks; the whole time she talks the young man in the white T-shirt '
     'keeps his head bowed, shoulders heaving with sobs, flinches at every shake and presses '
     'his palms together begging, unable to meet her eyes', _N),
 16: (8, 'Close-up on the son, the mother recoiling behind him',
     ['sa_c', 'kp1'], 'home', T1,
     'the young man in the white T-shirt, still on his knees in the red dirt, sobbing, words '
     'breaking apart, lifts his wet face up to his mother and wrings his hands together while '
     'he speaks; the whole time he talks the woman in the indigo blouse, shocked, mouth '
     'falling open, lets go of his shoulders finger by finger, presses a hand over her mouth, '
     'staggers back two paces and bumps against a wooden house post', _N + ['noletter']),
 17: (8, 'Medium close-up on the mother, the tin trunk behind her',
     ['kp1'], 'home', T1,
     'the woman in the indigo blouse, wailing, voice hoarse, clutches the front of her blouse '
     'over her heart, beats her chest twice with her fist and jabs a finger at her own eyes, '
     'tears pouring down her face while she speaks; her whole body shakes and she grips a '
     'wooden house post to stay on her feet', _N),
 18: (8, "Medium, the son prostrating at his mother's feet",
     ['sa_c', 'kp1'], 'home', T1,
     'the young man in the white T-shirt, crying, bows down and presses his forehead to his '
     "mother's feet on the red dirt, hands clasped over his head, his back heaving while he "
     'speaks; the whole time he talks the woman in the indigo blouse, tears running, hands '
     'shaking, turns her face away and bites hard on her knuckle, one hand hovering over his '
     'head without touching it, and she does not pull her feet back; a hen wanders past behind'
     ' them', _N),
 19: (8, 'Medium wide from behind, the mother at the edge of the golden paddy, the son following',
     ['kp1', 'sa_c'], 'na_ripe', T1,
     'the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her'
     ' head like a turban, steeling herself, jaw set, wipes her tears hard with the back of '
     'her wrist, strides to the edge of the golden paddy and grabs a heavy rice ear, weighing '
     'it in her palm while she speaks; the whole time she talks the young man in the white '
     'T-shirt, eyes swollen, hopeless, trudges up behind her, wiping his nose on his wrist and'
     ' scuffing his feet on the dyke; the instant she finishes, he spreads both open hands toward the field while he answers; the ripe rice ripples in the wind', _N + ['nocash']),
 20: (8, 'Close-up, her indigo-stained fingers on the thin gold chain at her neck',
     ['kp1', 'sa_c'], 'na_ripe', T1,
     'the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her'
     ' head like a turban, wistful, smiling through tears, strokes the thin gold chain at her '
     'throat with her indigo-stained fingers, lifts it to her lips and kisses it while she '
     'speaks; the whole time she talks the young man in the white T-shirt stares at the chain,'
     ' eyes going wide, shaking his head faster and faster; the instant she finishes, he '
     'lunges and grabs her hand in both of his, pulling it away from the clasp while he '
     'answers; rice ears sway behind them', _N + ['nocash']),
 21: (8, 'Close two-shot, her hands closing his fingers over the gold chain',
     ['kp2', 'sa_c'], 'na_ripe', T1,
     'the woman in the indigo blouse, her red-and-white checked cloth still wrapped around her'
     ' head like a turban, firm, voice trembling but not giving way, her neck now bare, '
     "presses the thin gold chain into her son's palm, folds his fingers over it one by one "
     'and squeezes his fist in both hands, nodding at him while she speaks; the whole time she'
     ' talks the young man in the white T-shirt, crying, tries to push the chain back, fails, '
     'and stares at his closed fist with his mouth trembling; the instant she finishes, he '
     'nods hard again and again, grips the chain to his chest and wipes his face with his '
     'forearm while he answers; rice ears sway behind them', _N + ['nocash']),
 22: (8, 'Medium under the house, the headman arriving on his bicycle, the son on the phone',
     ['bm', 'sa_c'], 'home', T1,
     'the headman in the light-blue shirt, over-eager, eyes darting, rolls in on his old black'
     ' bicycle, props it against a house post, rubs his hands together and pats the young man '
     'on the back twice with a wide helpful grin, glancing toward the rice fields and back '
     'while he speaks; the whole time he talks the young man in the white T-shirt, hopeful, '
     'holds a phone to his ear, paces two steps away and back, nods at the headman '
     'distractedly and chews his thumbnail waiting for an answer; a hen pecks around the '
     'bicycle wheel', _N + ['nocash']),
 23: (8, 'Medium close-up on the son lowering the phone, the mother behind him',
     ['sa_c', 'kp2'], 'home', T1,
     'the young man in the white T-shirt, stunned, face pale, voice hollow, slowly lowers the '
     'phone from his ear, stares at the dark screen and lets his arm fall against his side '
     'while he speaks; the whole time he talks, behind him the woman in the indigo blouse, '
     'crushed, stops mid-step, her hands flying to her mouth, and sinks down onto the bamboo '
     'platform, her shoulders starting to shake; the bamboo platform creaks under her', _N),
}

DIRECTION = {
 (1, 'bm'): 'uneasy and squirming, a nervous chuckle, voice dropped low, eyes darting to the road',
 (1, 'hong'): 'gloating and triumphant, grinning ear to ear, laughing out loud in the middle of the line, sweeping her fan over the field',
 (2, 'bm'): 'ashamed, face flushed red, bowing twice with a sick forced smile, palms pressed together',
 (2, 'hong'): 'sugary and smug, one eyebrow high, tapping his chest with her fan',
 (3, 'kp1'): 'cheerful and very loud, beaming, waving her whole arm high over her head',
 (4, 'bm'): 'touched and guilty, voice cracking, eyes wet, hugging the basket to his chest',
 (4, 'kp1'): 'cheerful and bustling, laughing, slapping his arm',
 (5, 'kp1'): 'generous and laughing out loud, waving the refusal away, scooping more',
 (5, 'pa'): 'shy and embarrassed, bowing her head again and again, voice small',
 (6, 'kp1'): 'carefree and embarrassed, laughing shyly behind her hand, waving it away',
 (6, 'pa'): 'curious and nosy, head tilted, tapping the envelope with one finger',
 (7, 'hong'): 'sickly sweet and sing-song, smiling with cold eyes, fanning herself nonstop',
 (7, 'kp1'): 'puzzled turning indignant, laughing in disbelief, hands on hips, pointing at the ground',
 (8, 'hong'): 'cold and sweet, a thin one-sided smile, tapping her palm with the closed fan on every point',
 (8, 'kp1'): 'shocked, face drained white, shaking her head hard, almost shouting the denial',
 (9, 'hong'): 'bored and sweet, yawning behind her fan, nudging an envelope with her shoe',
 (9, 'kp1'): 'panicking, voice breaking into a cry, tearing at the empty red cloth',
 (10, 'hong'): 'gleeful and mocking, sing-song, calling over her shoulder, waggling her fan goodbye',
 (11, 'sa_c'): 'cheerful and loud, grinning with dimples, waving the bag of oranges high, the grin sliding off his face at the end',
 (12, 'kp1'): 'furious and heartbroken, screaming through tears, shaking the empty cloth in his face',
 (12, 'sa_c'): 'panicked and stammering, palms raised, backing away, voice climbing',
 (13, 'sa_c'): 'reading aloud, voice cracking apart, tears spilling, crushing the letter to his chest on the apology',
 (14, 'sa_c'): 'confessing through heavy sobs, pounding the dirt with his fists, voice cracking',
 (15, 'kp1'): 'shouting in raw rage, eyes red, shaking him hard on every word',
 (16, 'sa_c'): 'sobbing so hard the words break apart, wringing his hands, forcing out the truth',
 (17, 'kp1'): 'wailing, voice hoarse and cracking, beating her chest with her fist',
 (18, 'sa_c'): 'crying, forehead pressed to her feet, begging in a muffled, broken voice',
 (19, 'kp1'): 'steeling herself, voice hard and firm, wiping her tears, weighing a rice ear in her palm',
 (19, 'sa_c'): 'hopeless, voice thick with tears, open hands toward the field',
 (20, 'kp1'): 'wistful, smiling through tears, kissing the chain, voice soft but trembling',
 (20, 'sa_c'): 'alarmed, almost shouting, grabbing her hand with both of his',
 (21, 'kp2'): 'firm, voice trembling but steady, squeezing his fist in both hands, nodding',
 (21, 'sa_c'): 'crying, nodding hard, voice choked with determination',
 (22, 'bm'): 'over-eager and too friendly, voice loud, rubbing his hands, patting his back, eyes darting',
 (23, 'sa_c'): 'stunned, voice hollow and shaking, the phone sliding down from his ear',
}

SHOTS = _c.apply_directions(_c.build_shots(_META), DIRECTION)

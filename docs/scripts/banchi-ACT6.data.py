# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 6 — รอยที่เตียง. The evidence, and the arrest.

The whole film has been building one reversal: the person everyone treated as
too old to understand is the only one who kept an account. This act spends its
first half making her marks matter and its second half making เชิด's own Act 2
lie — "ผมไม่มีเจ้านายหรอกพี่ เงินผมทั้งนั้น" — the thing that takes him down.

He repeats the opposite of it in the last shot. That is the point of the act and
the reason the lie was planted seventy shots earlier.

⚠ NUMBERS: same rule as Act 5. Every numeral is followed by a classifier or a
particle before any form of address, because a numeral running straight into a
vocative made the synthesiser stutter once already.

⚠ NEW LOCATION CHIP: `@bedrail_marks` is used as a location reference for the
insert on the bedframe. The plate is on disk; it must exist as an ingredient in
the Flow project before this act is shot.

Blocks IMPORTED from Act 2 (which itself imports Act 1).
"""
import importlib.util as _il
from pathlib import Path as _P

_s2 = _il.spec_from_file_location("act2", _P(__file__).with_name("banchi-ACT2.data.py"))
_a2 = _il.module_from_spec(_s2); _s2.loader.exec_module(_a2)
_s4 = _il.spec_from_file_location("act4", _P(__file__).with_name("banchi-ACT4.data.py"))
_a4 = _il.module_from_spec(_s4); _s4.loader.exec_module(_a4)

STYLE = _a2.STYLE
CHAR = dict(_a4.CHAR); LOC = dict(_a2.LOC); VOICE = dict(_a4.VOICE)
NOT = dict(_a2.NOT); APRON = _a2.APRON
PROP_FOR_NOT = dict(_a2.PROP_FOR_NOT)
PROPS_BY_SHOT = dict(_a2.PROPS_BY_SHOT)
WARDROBE = dict(_a2.WARDROBE)

# วิทย์ in uniform — the reveal (CEO 2026-09-23, docs/scripts/banchi-police-insert-DRAFT.md).
# The face block is word for word the plainclothes "wit" block: only the clothes
# change, so the model has nothing to reinterpret about who he is.
# Staging, 2026-09-23: every two-shot in this scene keeps both faces angled
# three-quarters to camera. A character seen only in profile lost his plate in
# 106 (hair, twice), old 149 and new 149/150 (the father's white shirt and
# apron became a grey T-shirt); old 150/151, faces toward camera, held.
# WIT_UNIFORM_HANDLE is set by the CTO after looking at the worker's two stills
# (task-f78ca70e: @cop_wit_uniform_A reference-led, _B description-only). Until
# then it names a plate that cannot exist, so check_plates refuses the build
# instead of guessing.
WIT_UNIFORM_HANDLE = "@cop_wit"   # 2026-09-23 A/B: his FACE plate; the uniform rides on WARDROBE below.
# Was "@cop_wit_uniform_A" (a full-body still): in 149/151 and A/B arm A that plate
# gave him the father's older, greying face.
# NO WORD "police" anywhere in his block (A/B 2026-09-23, 360p/4s): with the
# uniform plate attached AND "police" in the text, Flow began the clip and then
# silently removed it — 179 twice, 149 and 151 once, arm A once — no card, no
# error. Same text with the plainclothes plate (arm B) and the uniform plate
# with "police" removed (arm C) both came back; Flow's own auto-title still read
# "Police officer enters noodle shop", so the plate carries the look by itself.
CHAR["wit_uniform"] = (WIT_UNIFORM_HANDLE,
  "a Thai man of 32, medium athletic build, short neat black hair, clean-shaven, calm steady "
  "eyes, in an everyday khaki duty uniform: a khaki-brown short-sleeved uniform "
  "shirt with shoulder boards, a metal badge above the left pocket and a blank name plate "
  "above the right pocket, khaki-brown trousers and a black belt",
  "The 32-year-old man in the khaki uniform")
VOICE["wit_uniform"] = VOICE["wit"]
WARDROBE["wit_uniform"] = "@police_uniform"   # wardrobe plate, no person in it

LOC["bedrail"] = ("@bedrail_marks",
  "a close view along the painted steel side rail of an old bed in a dim upstairs room, "
  "the paint worn down to bare metal in one patch where dozens of short scratch marks "
  "have been cut into it in uneven rows")

NOT["noledger"] = ("There is no notebook, no ledger, no printed receipt and no paperwork "
  "anywhere in the frame.")
# The arrest shots (183-186): cuffs are the point now, so they are said as what
# DOES happen, and everything else as what does not.
NOT["cuffed"] = ("The younger man's wrists stay together in front of him in metal "
  "handcuffs for the whole shot. Nobody is hit, pushed, dragged or pinned, and no "
  "weapon is drawn.")
NOT["nocuffs"] = ("No handcuffs, no weapon, no violence and no physical contact between "
  "anyone in the frame.")

SHOTS = [
 (133, 8, "Medium two-shot, static camera", ["muay","somchai"], "shop", "late morning",
  "stands at the end of the counter with her arms folded, looking out at the empty tables while he wipes the same spot",
  [("muay","careful","เช้านี้ยังไม่มีใครเข้าเลยเหรอพี่"),
   ("somchai","flat","สามวันแล้วครับเจ๊")], ["money"]),

 (134, 8, "Medium two-shot, static camera", ["muay","somchai"], "shop", "late morning",
  "lowers her voice and leans in over the counter, he keeps his hands moving on the cloth",
  [("muay","reluctant","เขาพูดกันทั้งตลาดว่าร้านพี่มีปัญหา"),
   ("somchai","even","ผมรู้ครับเจ๊")], ["money"]),

 (135, 6, "Medium two-shot, static camera", ["muay","somchai"], "shop", "late morning",
  "straightens up and looks at him, he finally stops wiping and looks back",
  [("muay","quiet","ใครพูดล่ะพี่"),
   ("somchai","plain","คนที่ผมเลิกจ่ายเขาแล้วครับ")], ["money"]),

 (136, 8, "Medium two-shot, static camera", ["ton","somchai"], "stairs", "night",
  "comes halfway down the stairs and stops on the step, his father standing at the bottom",
  [("ton","low","พ่อ เมื่อคืนมีคนมาเคาะประตูหลังครับ"),
   ("somchai","immediate","อย่าเปิดนะลูก")], []),

 (137, 8, "Medium two-shot, static camera", ["ton","somchai"], "stairs", "night",
  "sits down on the step so he is level with his father, both keeping their voices down",
  [("ton","tight","ย่าตื่นทั้งคืนเลยครับพ่อ"),
   ("ton","deciding","พรุ่งนี้ผมจะไปหาพี่วิทย์ครับ")], []),

 (138, 8, "Medium two-shot, static camera", ["ton","ya"], "room", "morning",
  "crouches beside the bed with his phone in his hand, the old woman lying back against the pillow watching him",
  [("ton","gentle","ย่าครับ ขอถ่ายรูปเตียงย่าหน่อยนะครับ"),
   ("ya","puzzled","จะถ่ายเตียงทำไมล่ะลูก")], ["ya"]),

 (139, 8, "Medium shot, static camera, the marks and his hands both in frame", ["ton"], "bedrail", "morning",
  "runs his thumb along the scratched patch on the rail, counting under his breath as he photographs it",
  [("ton","counting","ร้อยสี่รอยพอดีครับ"),
   ("ton","to himself","ย่านับให้พ่อมาแปดปีเต็ม ไม่มีใครรู้เลย")], ["noledger"]),

 (140, 8, "Medium two-shot, static camera", ["ya","ton"], "room", "morning",
  "lifts one hand a little off the blanket toward the rail, the young man still crouched beside her",
  [("ya","mild","ย่าไม่ได้ทำอะไรเลยนะลูก"),
   ("ya","simple","ย่าแค่นับ"),
   ("ton","barely","ย่านับให้เราทั้งบ้านเลยครับ")], ["ya"]),

 (141, 10, "Medium two-shot, static camera", ["ya","ton"], "room", "morning",
  "taps the rail twice with one finger to show him how, he stays very still and lets her",
  [("ya","remembering","ได้ยินประตูหลังเปิดทีไร ย่าก็ขีดทีหนึ่ง"),
   ("ya","matter-of-fact","ย่านอนอยู่ตรงนี้ ย่าได้ยินหมดแหละลูก"),
   ("ton","quiet","ย่าจำได้ทุกครั้งเลยเหรอครับ")], ["ya"]),

 (142, 8, "Medium two-shot, static camera", ["somchai","ton"], "room", "morning",
  "stands in the doorway with one hand still on the frame, his son turning from the bedside to answer",
  [("somchai","tired","ลูกจะเอารอยขีดไปให้ใครดูล่ะ"),
   ("ton","level","ให้คนที่เขาดูเป็นครับพ่อ")], ["noya"]),

 (143, 8, "Medium two-shot, static camera", ["somchai","ton"], "room", "morning",
  "comes one step into the room and stops, his son standing up from the bedside to face him",
  [("somchai","gently","ไม่มีใครเชื่อคนแก่หรอกลูก"),
   ("ton","firm","ผมเชื่อครับพ่อ")], ["noya"]),

 (144, 8, "Medium two-shot, static camera", ["ton","wit"], "shop", "midday",
  "puts the phone flat on the counter and turns it around, the officer leaning in over it",
  [("ton","direct","พี่วิทย์ดูรูปนี้หน่อยครับ"),
   ("wit","studying it","นี่รอยอะไรครับ")], []),

 (145, 8, "Medium two-shot, static camera", ["ton","wit"], "shop", "midday",
  "keeps one finger on the screen while he explains, the officer following it",
  [("ton","steady","ย่าผมขีดไว้ทุกครั้งที่มีคนมาเก็บเงินครับ"),
   ("wit","even","ขีดมาตั้งแต่เมื่อไหร่ครับ")], []),

 (146, 10, "Medium two-shot, static camera", ["ton","wit"], "shop", "midday",
  "swipes to the next photograph and leaves his hand on the counter, the officer standing back a little",
  [("ton","clear","ตั้งแต่วันแรกครับ ร้อยสี่รอยพอดี"),
   ("wit","checking","แล้วในแอปธนาคารล่ะครับ"),
   ("ton","flat","อีกร้อยสี่ครั้งครับ รวมสองร้อยแปด")], []),

 (147, 8, "Medium two-shot, static camera", ["wit","ton"], "shop", "midday",
  "shakes his head once and sets his hand flat on the counter, the young man watching him closely",
  [("wit","honest","รอยขีดอย่างเดียวใช้ไม่ได้หรอกครับ"),
   ("ton","fast","แล้วแบบนี้ล่ะครับ")], []),

 (148, 10, "Medium two-shot, static camera", ["wit","ton"], "shop", "midday",
  "turns the phone back toward the young man and taps the screen twice while he says it",
  [("wit","careful","แต่รอยขีดที่ตรงกับวันโอนเงินทุกครั้ง อันนี้ใช้ได้ครับ"),
   ("wit","quieter","สองร้อยแปดครั้ง มันมากเกินไปครับ")], []),

 # ── Police line: the reveal. Numbered past 173 so no existing number moves. ──
 (178, 6, "Medium two-shot, static camera", ["wit","ton"], "shop", "midday",
  "slides the phone back across the counter to the young man and gets up from the stool",
  [("wit","even","บ่ายนี้พี่จะกลับมาคุยกับพ่อนะ"),
   ("ton","doubtful","พ่อไม่ยอมคุยหรอกครับพี่"),
   ("wit","certain","ครั้งนี้ลุงจะยอมครับ")], ["nosubs"]),

 (179, 6, "Wide shot from behind the counter toward the street, static camera", ["wit_uniform"], "shop", "afternoon",
  "walks in through the open roll-up shutter wearing a khaki peaked cap and stops one step inside, the empty shop going still around him",
  [("wit_uniform","quiet, formal","สวัสดีครับลุง")], ["nosubs"]),

 (180, 8, "Medium two-shot behind the counter, static camera", ["somchai","ton"], "shop", "afternoon",
  "both stop dead behind the counter, facing the camera as they stare past it toward the door, the father's ladle held still over the pot, the son slowly lowering the tray in his hands",
  [("somchai","almost no voice","วิทย์..."),
   ("ton","disbelieving","พี่วิทย์... เป็นตำรวจเหรอครับ")], ["nosubs"]),

 (181, 10, "Medium two-shot across the counter, static camera", ["wit_uniform","somchai"], "shop", "afternoon",
  "takes off his peaked cap and holds it in both hands as he comes up to the counter, facing the older man, the two of them angled three-quarters toward the camera so both faces stay clearly visible",
  [("wit_uniform","apologetic, steady","ผมขอโทษที่ต้องปิดลุงมาตลอดครับ"),
   ("wit_uniform","plain","ผมตามคนปล่อยเงินกู้สายนี้มาปีกว่าแล้ว"),
   ("wit_uniform","quieter","ไม่มีใครในซอยยอมพูดสักคนครับ")], ["nosubs"]),

 (182, 8, "Medium two-shot across the counter, static camera", ["somchai","wit_uniform"], "shop", "afternoon",
  "sets the ladle down and looks the younger man in the face for a long moment, the cap still in the younger man's hands, the two of them angled three-quarters toward the camera so both faces stay clearly visible",
  [("somchai","slow, moved","ยี่สิบปีที่วิทย์มากินร้านลุง..."),
   ("wit_uniform","a small smile","ผมมากินก๋วยเตี๋ยวจริงๆ ครับลุง")], ["nosubs"]),

 # 149-151 re-shot in uniform: same words, he is now in the uniform the father just saw.
 (149, 8, "Medium two-shot, static camera", ["wit_uniform","somchai"], "shop", "afternoon",
  "sits down across the counter from the older man, both with their hands on the wood, the two of them angled three-quarters toward the camera so both faces stay clearly visible",
  [("wit_uniform","conversational","ลุงครับ เขาเคยบอกลุงไหมว่าเงินใคร"),
   ("somchai","remembering","เขาบอกว่าเงินเขาเองครับ ไม่มีเจ้านาย")], ["nosubs"]),

 (150, 6, "Medium two-shot, static camera", ["wit_uniform","somchai"], "shop", "afternoon",
  "leans back slightly and lets that sit between them, the older man looking up at him, the two of them angled three-quarters toward the camera so both faces stay clearly visible",
  [("wit_uniform","plain","นั่นแหละครับที่ไม่จริง"),
   ("somchai","slowly","แล้วเงินเป็นของใครครับ")], ["nosubs"]),

 (151, 8, "Medium two-shot, static camera", ["wit_uniform","somchai"], "shop", "afternoon",
  "puts both hands flat on the counter and asks it straight, the older man very still, the two of them angled three-quarters toward the camera so both faces stay clearly visible",
  [("wit_uniform","direct","ผมขอให้ลุงนัดเขาอีกครั้งเดียวครับ"),
   ("somchai","after a moment","ได้ครับ")], ["nosubs"]),

 (152, 6, "Medium shot, static camera", ["somchai"], "alley", "night",
  "stands under the bulb by the steel door with his hands empty at his sides, talking to no one",
  [("somchai","to himself","ครั้งสุดท้ายแล้วนะ"),
   ("somchai","steadying himself","แปดปีแล้ว วันนี้ผมจะถามเขาสักคำ")], ["money"]),

 (153, 8, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "walks in easily with both hands loose at his sides, the older man not moving from the door",
  [("cherd","pleased","ผมดีใจนะครับที่พี่เปลี่ยนใจ"),
   ("somchai","even","ผมขอดูบัญชีก่อนครับ")], ["noledger"]),

 (154, 10, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "opens his empty hands, smiling, the older man watching the hands and not the face",
  [("cherd","amused","พี่ไม่เคยขอดูมาแปดปีนะครับ"),
   ("somchai","steady","วันนี้ผมขอครับ"),
   ("cherd","easy","ผมไม่ได้จดครับพี่ ผมจำเอา")], ["noledger"]),

 (155, 8, "Medium two-shot, static camera", ["somchai","cherd"], "alley", "night",
  "takes one step forward so the light is on his face, the younger man's smile staying exactly where it is",
  [("somchai","clear","งั้นผมจดให้ครับ"),
   ("somchai","unhurried","สองร้อยแปดครั้งครับ")], ["noledger"]),

 # CEO 2026-09-23 on cut v3: the arrest is วิทย์ IN UNIFORM, and เชิด gets an ending —
 # "ใส่กุญแจมือ เดินขึ้นรถ มีบทพูดว่าเขาทำผิดอะไร ต้องโดนอะไรบ้าง เชิดไม่รับสารภาพ
 # และพยายามปกป้องตัวเอง" / วิทย์: "งั้นปล่อยให้เป็นหน้าที่ของกฎหมายนะครับ หน้าที่ของ
 # ผมหมดแล้วครับ แค่ส่งตัวพี่ไปโรงพักก็พอ". Design: docs/scripts/banchi-arrest-ending-DRAFT.md.
 # 156's lines are unchanged; only the uniform is new.
 (156, 10, "Medium two-shot, static camera", ["wit_uniform","cherd"], "alley", "night",
  "steps into the light from the far end of the alley in his khaki duty uniform and stops a few paces away with his hands visible, the younger man turning to him, both faces angled three-quarters toward the camera",
  [("wit_uniform","calm","ผมขอเชิญคุณไปคุยที่สถานีครับ"),
   ("cherd","the smile gone","ผมแค่เก็บให้เขาครับ"),
   ("cherd","fast, to anyone","ผมไม่ใช่เจ้าของเงินนะครับ")], ["nocuffs","noledger","nosubs"]),

 (183, 8, "Medium two-shot, static camera", ["wit_uniform","cherd"], "alley", "night",
  "closes a pair of metal handcuffs around the younger man's wrists in front of him, calmly and without force, both faces angled three-quarters toward the camera",
  [("wit_uniform","even, formal","คุณถูกจับในข้อหาปล่อยเงินกู้ดอกเบี้ยเกินกฎหมาย และข่มขู่ทวงหนี้ครับ"),
   ("cherd","quick, indignant","ผมไม่ได้ข่มขู่ใครเลยนะครับ")], ["cuffed","noledger","nosubs"]),

 (184, 10, "Medium two-shot, slow tracking alongside them", ["wit_uniform","cherd"], "alley", "night",
  "walk side by side down the wet alley toward its mouth, where a plain white pickup with a red-and-blue light bar on its roof and no writing anywhere on it waits with its lights flashing, the younger man's cuffed hands in front of him",
  [("wit_uniform","plain","เก็บเกินหนี้ไปห้าสิบแปดงวด ขู่คนป่วย ขู่คนทั้งซอย"),
   ("wit_uniform","steady","ทั้งสองข้อหา โทษมีทั้งจำคุกและปรับครับ"),
   ("cherd","defensive","ผมทำตามที่เจ้านายสั่งเท่านั้นครับ")], ["cuffed","noledger","nosubs"]),

 (185, 8, "Medium two-shot, static camera", ["cherd","wit_uniform"], "alley", "night",
  "stop beside the white pickup at the mouth of the alley, red and blue light moving across both faces, the younger man's cuffed hands in front of him, both faces angled three-quarters toward the camera",
  [("cherd","refusing, chin up","ผมไม่รับหรอกครับ ผมไม่ได้ทำอะไรผิด"),
   ("wit_uniform","calm, final","งั้นปล่อยให้เป็นหน้าที่ของกฎหมายนะครับ")], ["cuffed","noledger","nosubs"]),

 (186, 8, "Medium two-shot, static camera", ["wit_uniform","cherd"], "alley", "night",
  "opens the rear door of the white pickup and waits with an open hand toward the seat while the younger man, cuffed hands in front of him, gets in on his own",
  [("wit_uniform","quiet","หน้าที่ของผมหมดแล้วครับ"),
   ("wit_uniform","quieter","แค่ส่งตัวพี่ไปโรงพักก็พอ")], ["cuffed","noledger","nosubs"]),

 (187, 6, "Wide shot from behind him, static camera", ["somchai"], "alley", "night",
  "stands alone at the mouth of the alley watching the white pickup pull away down the wet street, its red-and-blue lights growing small, and lets out one long breath, saying nothing",
  [], ["noledger","nosubs"]),
]

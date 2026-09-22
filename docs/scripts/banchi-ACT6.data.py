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

LOC["bedrail"] = ("@bedrail_marks",
  "a close view along the painted steel side rail of an old bed in a dim upstairs room, "
  "the paint worn down to bare metal in one patch where dozens of short scratch marks "
  "have been cut into it in uneven rows")

NOT["noledger"] = ("There is no notebook, no ledger, no printed receipt and no paperwork "
  "anywhere in the frame.")
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

 (149, 8, "Medium two-shot, static camera", ["wit","somchai"], "shop", "afternoon",
  "sits down across the counter from the older man, both with their hands on the wood",
  [("wit","conversational","ลุงครับ เขาเคยบอกลุงไหมว่าเงินใคร"),
   ("somchai","remembering","เขาบอกว่าเงินเขาเองครับ ไม่มีเจ้านาย")], []),

 (150, 6, "Medium two-shot, static camera", ["wit","somchai"], "shop", "afternoon",
  "leans back slightly and lets that sit between them, the older man looking up at him",
  [("wit","plain","นั่นแหละครับที่ไม่จริง"),
   ("somchai","slowly","แล้วเงินเป็นของใครครับ")], []),

 (151, 8, "Medium two-shot, static camera", ["wit","somchai"], "shop", "afternoon",
  "puts both hands flat on the counter and asks it straight, the older man very still",
  [("wit","direct","ผมขอให้ลุงนัดเขาอีกครั้งเดียวครับ"),
   ("somchai","after a moment","ได้ครับ")], []),

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

 (156, 10, "Medium two-shot, static camera", ["wit","cherd"], "alley", "night",
  "steps into the light from the far end of the alley and stops a few paces away with his hands visible, the younger man turning to him",
  [("wit","calm","ผมขอเชิญคุณไปคุยที่สถานีครับ"),
   ("cherd","the smile gone","ผมแค่เก็บให้เขาครับ"),
   ("cherd","fast, to anyone","ผมไม่ใช่เจ้าของเงินนะครับ")], ["nocuffs","noledger"]),
]

# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 7 — เล่มแรกของบ้านนี้. One year later.

The act exists to answer one line. In Act 3 the father told his son
"ไม่ต้องรู้ว่ามันมาจากไหน แค่ใช้มันให้คุ้ม" and meant it as love. Everything since
has been the cost of that sentence, so the film cannot end until the son asks
the opposite and the father is glad he did.

The grandmother has died between the acts. It is said once, plainly, and the
marks on the rail are not painted over — they are the house's first ledger and
the reason there is now a second one.

⚠ NEW LOCATION CHIP: `@noodle_shop_thriving` must exist as an ingredient in the
Flow project before this act is shot. The plate is on disk. `@bedrail_marks`
was already needed by Act 6.

Blocks IMPORTED from Act 6.
"""
import importlib.util as _il
from pathlib import Path as _P

_s6 = _il.spec_from_file_location("act6", _P(__file__).with_name("banchi-ACT6.data.py"))
_a6 = _il.module_from_spec(_s6); _s6.loader.exec_module(_a6)

STYLE = _a6.STYLE
CHAR = dict(_a6.CHAR); LOC = dict(_a6.LOC); VOICE = dict(_a6.VOICE)
NOT = dict(_a6.NOT); APRON = _a6.APRON

LOC["shop2"] = ("@noodle_shop_thriving",
  "the same deep old Bangkok shophouse noodle restaurant, a year on and full — every "
  "bright red, blue and green stool taken, the staircase in the middle of the room "
  "beside its pillar, the open street bright at the far end")

NOT["nodebt"] = ("There is no cash, no banknotes and no money of any kind in the frame.")

SHOTS = [
 (157, 8, "Medium two-shot, static camera", ["muay","somchai"], "shop2", "midday",
  "stands at the end of the busy counter with a bowl in each hand, he is working fast beside her",
  [("muay","pleased","ร้านพี่คนแน่นทุกวันเลยนะ"),
   ("somchai","light","ค่อยยังชั่วแล้วครับเจ๊")], ["nodebt"]),

 (158, 8, "Medium two-shot, static camera", ["muay","somchai"], "shop2", "midday",
  "sets the bowls down on the counter and looks at him, he keeps working but slows",
  [("muay","carefully","แล้วเรื่องที่ศาลล่ะพี่"),
   ("somchai","even","ตัดสินไปเมื่อเดือนที่แล้วครับ")], ["nodebt"]),

 (159, 10, "Medium two-shot, static camera", ["muay","somchai"], "shop2", "midday",
  "wipes her hands on her apron and asks it plainly, he stops and answers her properly",
  [("muay","direct","แล้วพี่ได้เงินคืนไหมล่ะ"),
   ("somchai","honest","ได้คืนไม่หมดหรอกครับเจ๊"),
   ("somchai","quieter","แต่ผมนอนหลับแล้วครับ")], ["nodebt"]),

 (160, 8, "Medium two-shot, static camera", ["ton","muay"], "shop2", "midday",
  "comes to the counter with a thick school notebook open in one hand and a pen in the other",
  [("muay","curious","นั่นอะไรน่ะต้น"),
   ("ton","easy","สมุดบัญชีร้านครับเจ๊"),
   ("ton","matter-of-fact","ผมจดเองทุกวันตั้งแต่ปีที่แล้ว")], []),

 (161, 8, "Medium two-shot, static camera", ["ton","muay"], "shop2", "midday",
  "turns the open notebook around on the counter so she can see the columns, she leans over it",
  [("muay","surprised","จดทุกบาทเลยเหรอ"),
   ("ton","plain","ทุกบาทครับ ใครอยากดูก็ดูได้")], []),

 (162, 8, "Medium two-shot, static camera", ["muay","ton"], "shop2", "midday",
  "puts one finger on the page and traces down a column, he lets her",
  [("muay","half joking","เจ๊ก็อยากมีสักเล่มเหมือนกัน"),
   ("ton","warm","เดี๋ยวผมสอนให้ครับเจ๊")], []),

 (163, 10, "Medium two-shot, static camera", ["muay","ton"], "shop2", "midday",
  "straightens up and lowers her voice although the room is loud, he closes the notebook to listen",
  [("muay","lower","เจ๊รู้จักคนนึงกำลังจะไปยืมเขาอยู่"),
   ("ton","immediate","พาเขามาคุยกับพ่อผมก่อนครับ"),
   ("ton","steady","พ่อผมเล่าให้ฟังได้ทั้งวันเลยครับ")], []),

 (164, 8, "Medium shot, static camera", ["somchai"], "room", "afternoon",
  "stands just inside the doorway of the quiet upstairs room looking at the stripped, empty bed",
  [("somchai","to himself","เงียบจังเลยนะห้องนี้"),
   ("somchai","quieter","ผมยังเผลอเดินขึ้นมาทุกเช้าเลยแม่")], ["ya","noledger"]),

 (165, 8, "Medium shot, static camera, his hand and the marks both in frame", ["somchai"], "bedrail", "afternoon",
  "sits on the edge of the bare bed and lays his palm flat over the scratched patch on the rail",
  [("somchai","quiet","แม่นับไว้ให้ผมหมดเลยนะ"),
   ("somchai","softer","ผมไม่เคยรู้เลยสักครั้ง")], ["noledger"]),

 (166, 8, "Medium two-shot, static camera", ["ton","somchai"], "room", "afternoon",
  "comes in and stands beside the bed, his father not getting up from the edge of it",
  [("ton","careful","พ่อยังไม่ทาสีทับเหรอครับ"),
   ("somchai","certain","ไม่ทาหรอกลูก")], ["ya","noledger"]),

 (167, 8, "Medium two-shot, static camera", ["somchai","ton"], "room", "afternoon",
  "keeps his hand on the rail and looks up at his son as he says it",
  [("somchai","plain","ย่าไม่อยู่แล้ว แต่รอยยังอยู่"),
   ("somchai","steady","นี่บัญชีเล่มแรกของบ้านเรานะลูก")], ["ya","noledger"]),

 (168, 8, "Medium two-shot, static camera", ["ton","somchai"], "room", "afternoon",
  "sits down on the bed beside his father, both looking at the rail and not at each other",
  [("ton","tentative","พ่อครับ ผมขอถามอะไรสักอย่าง"),
   ("somchai","open","ถามมาสิลูก")], ["ya"]),

 (169, 10, "Medium two-shot, static camera", ["ton","somchai"], "room", "afternoon",
  "turns on the bed to face his father properly, the older man letting his hand fall from the rail",
  [("ton","quiet","ตอนนั้นพ่อบอกผมว่าไม่ต้องรู้ว่าเงินมาจากไหน"),
   ("somchai","without flinching","พ่อจำได้ลูก")], ["ya"]),

 (170, 8, "Medium two-shot, static camera", ["ton","somchai"], "room", "afternoon",
  "says it without any edge in it, his father listening with both hands on his knees",
  [("ton","simple","ผมอยากรู้ครับพ่อ ทุกบาทเลย"),
   ("somchai","after a beat","พ่อก็อยากให้ลูกรู้เหมือนกันลูก")], ["ya"]),

 (171, 10, "Medium two-shot, static camera", ["somchai","ton"], "room", "afternoon",
  "turns to his son and says the whole thing to his face, not to the room",
  [("somchai","even","เงินที่พ่อตั้งใจหามาให้ลูก"),
   ("somchai","steady","มันไม่ควรต้องปิดบังลูกเลยสักบาทเดียว")], ["ya"]),

 (172, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop2", "evening",
  "stands at the counter in the full shop writing in the open notebook, his father working beside him",
  [("ton","calling over","วันนี้ได้สามพันแปดร้อยบาทครับพ่อ"),
   ("ton","writing it","จดแล้วนะครับ")], []),

 (173, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop2", "evening",
  "looks over at the open page his son is writing on and nods once, then goes back to the pot",
  [("somchai","warm","จดไว้เถอะลูก"),
   ("somchai","final","ต่อไปใครถามอะไร เราตอบได้หมด")], []),
]

# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 4 — จุดพลิก และราคาของมัน. Rendered by tools/build_shotsheet.py.

The turning point is an ACT, not a speech: the father asks to see the book, and
there is no book. He stops paying. Then the film makes him pay for that, because
a reversal the weak side never suffers for is unearned.

Blocks are IMPORTED from Act 2 (which already carries เชิด and the alley).
"""
import importlib.util as _il
from pathlib import Path as _P

_s1 = _il.spec_from_file_location("act1", _P(__file__).with_name("banchi-ACT1.data.py"))
_a1 = _il.module_from_spec(_s1); _s1.loader.exec_module(_a1)
_s2 = _il.spec_from_file_location("act2", _P(__file__).with_name("banchi-ACT2.data.py"))
_a2 = _il.module_from_spec(_s2); _s2.loader.exec_module(_a2)

STYLE = _a1.STYLE
CHAR = dict(_a2.CHAR)
LOC = dict(_a2.LOC)
VOICE = dict(_a2.VOICE)
NOT = dict(_a2.NOT)
APRON = _a1.APRON

# เจ๊หมวย, the neighbour who carries the rumour. Written from her plate.
CHAR["muay"] = ("@jae_muay",
  "a Thai woman of 60, sturdy, with short grey curly hair, sunglasses pushed up onto her "
  "head, in a dark floral-print blouse and a thin gold chain",
  "The 60-year-old woman in the floral blouse")
VOICE["muay"] = ("Laomedeia @jae_muay",
  "the bright, quick, mid-high voice of a woman of sixty who has known everyone here for years")

SHOTS = [
 (83, 8, "Medium two-shot, static camera", ["cherd","somchai"], "shop", "midday",
  "walks in and rests a hand on the counter while the older man keeps working the pot, neither of them smiling now",
  [("cherd","easy","วันพฤหัสแล้วนะครับพี่"),
   ("somchai","steady","งวดที่แล้วผมจ่ายงวดสุดท้ายไปแล้วนี่ครับ")], []),

 (84, 10, "Medium two-shot, static camera", ["cherd","somchai"], "shop", "midday",
  "turns his wrist over to check the time while he answers, the older man setting down the ladle to listen",
  [("cherd","light","นั่นต้นครับพี่ ยังมีส่วนต่างอีกนิดหน่อย"),
   ("somchai","flat","เท่าไหร่ครับ"),
   ("cherd","unbothered","เดี๋ยวผมคิดให้ครับ")], []),

 (85, 6, "Close-up on the father, static camera", ["somchai"], "shop", "midday",
  "wipes his hands slowly on his apron and looks straight at the man across the counter as he asks",
  [("somchai","even, careful","เชิดครับ ขอดูสมุดหน่อยได้ไหมครับ")], ["nobook"]),

 (86, 4, "Close-up on the younger man, static camera", ["cherd"], "shop", "midday",
  "keeps his hand on the counter and his face pleasant while he answers",
  [("cherd","light","สมุดอะไรเหรอครับพี่")], ["nobook"]),

 (87, 8, "Close-up on the father, static camera", ["somchai"], "shop", "midday",
  "puts both hands flat on the counter and keeps his voice completely level",
  [("somchai","steady","ที่เชิดจดไว้ว่าผมจ่ายไปแล้วเท่าไหร่ครับ"),
   ("somchai","quieter","สี่ปีแล้วนะครับ")], ["nobook"]),

 (88, 10, "Medium two-shot, static camera", ["cherd","somchai"], "shop", "midday",
  "taps his own temple with one finger while he talks, the older man watching him do it",
  [("cherd","warm, wounded","ผมจำได้หมดในหัวครับพี่"),
   ("cherd","softer","พี่ไม่เชื่อผมเหรอครับ"),
   ("somchai","quiet","ผมแค่อยากเห็นครับ")], ["nobook"]),

 (89, 8, "Close-up on the younger man, static camera", ["cherd"], "shop", "midday",
  "spreads both hands a little and keeps smiling while he explains it away",
  [("cherd","reasonable","เรื่องแบบนี้เขาไม่จดกันหรอกครับพี่"),
   ("cherd","easy","มันคิดกันตามเวลาน่ะครับ")], ["nobook"]),

 # ── THE TURN. An act, not a speech. ──
 (90, 4, "Close-up on the father, static camera", ["somchai"], "shop", "midday",
  "takes his hands off the counter and puts them behind his back while he says it",
  [("somchai","level","งวดนี้ผมยังไม่จ่ายครับ")], []),

 (91, 4, "Close-up on the younger man, static camera", ["cherd"], "shop", "midday",
  "stops smiling for the first time and leans in a little as he asks",
  [("cherd","quiet","พี่พูดจริงหรือเปล่าครับ")], []),

 (92, 6, "Medium two-shot, static camera", ["somchai","cherd"], "shop", "midday",
  "picks the ladle back up and goes on working the pot while he answers, not looking at the man",
  [("somchai","ordinary","จริงครับ"),
   ("cherd","flat, pleasant again","พี่คิดดีแล้วนะครับ")], []),

 (93, 4, "Medium shot, static camera", ["ton","somchai"][:2], "shop", "midday",
  "comes out from the back with a tray and stops halfway when he sees the two men, his father speaking without turning",
  [("ton","uncertain","พ่อ..."),
   ("somchai","firm, calm","เข้าไปในร้านก่อนลูก")], []),

 # ── THE PRICE ──
 (94, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "late afternoon",
  "stacks four unused chairs back against the wall while his father wipes an empty table beside him",
  [("ton","flat","วันนี้ทั้งวันได้สี่โต๊ะเองนะครับพ่อ"),
   ("somchai","even","พ่อรู้ลูก")], []),

 (95, 10, "Medium two-shot, static camera", ["muay","somchai"], "shop", "late afternoon",
  "leans in at the open shutter with a bag of vegetables on her arm, talking across to the man at the counter",
  [("muay","quick, worried","สมชาย มีคนไปพูดแถวตลาดนะ"),
   ("somchai","looking up","พูดว่าอะไรครับเจ๊"),
   ("muay","lowering her voice","ว่าน้ำซุปร้านเธอไม่สะอาด")], []),

 (96, 8, "Medium two-shot, static camera", ["somchai","muay"], "shop", "late afternoon",
  "keeps wiping the counter while he answers her, she watching his hands",
  [("somchai","quiet","ใครพูดครับเจ๊"),
   ("muay","shrugging, unhappy","ไม่มีใครรู้หรอก มันพูดต่อๆกันมา")], []),

 (97, 8, "Medium two-shot, static camera", ["wit","somchai"], "shop", "evening",
  "sits down at the counter and looks around the empty shop while the older man sets a bowl in front of him",
  [("wit","surprised","ลุงครับ วันนี้คนน้อยจังเลยนะครับ"),
   ("somchai","light","ช่วงนี้เงียบหน่อยน่ะวิทย์")], []),

 (98, 8, "Medium two-shot, static camera", ["wit","somchai"], "shop", "evening",
  "stirs his bowl without eating and keeps watching the older man work",
  [("wit","careful","มีอะไรหรือเปล่าครับลุง"),
   ("somchai","easy","ไม่มีอะไรหรอก กินเถอะวิทย์ เดี๋ยวเส้นอืด")], []),

 (99, 6, "Medium two-shot, static camera", ["wit","somchai"], "shop", "evening",
  "slides folded money across the counter while he stands to leave, the older man reaching to push it back",
  [("wit","gentle","ลุงครับ ผมวางไว้ให้นะครับ"),
   ("somchai","firm","วิทย์")], ["money"]),

 (100, 10, "Medium two-shot, static camera", ["wit","somchai"], "shop", "evening",
  "keeps his hand on the money while the older man pushes it back toward him, both of them holding it",
  [("wit","insisting, kind","ลุงเอาไว้เถอะครับ วันนี้ผมมีเยอะ"),
   ("somchai","steady","ลุงไม่เคยรับของวิทย์มายี่สิบปี วันนี้ก็ไม่รับ"),
   ("wit","quiet","ลุง ร้านมันเงียบขนาดนี้...")], ["money"]),

 (101, 4, "Close-up on the father, static camera", ["somchai"], "shop", "evening",
  "folds the money back into the young man's hand and closes his fingers over it",
  [("somchai","warm, final","ลุงยังไหวอยู่ครับวิทย์")], ["money"]),

 (102, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "holds up an empty pill strip to the light while his father counts the day's takings at the counter",
  [("ton","flat","ยาย่าหมดตั้งแต่เมื่อวานแล้วนะครับพ่อ"),
   ("somchai","not looking up","เดี๋ยวพ่อหาให้ลูก")], []),

 (103, 6, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "sets the empty strip down on the counter between them while his father keeps his hands on the money",
  [("ton","level","หาจากไหนครับพ่อ"),
   ("somchai","quiet","พ่อกำลังคิดอยู่")], ["money"]),

 (104, 8, "Medium two-shot, static camera", ["ya","ton"], "room", "night",
  "lies propped on the pillows while her grandson sits on the bed edge holding the empty strip, both talking low",
  [("ya","thin","...ไม่ต้องซื้อหรอกลูก..."),
   ("ton","gentle, firm","ย่าอย่าพูดแบบนั้นครับ"),
   ("ya","fainter","...ย่าอยู่ได้..." )], ["ya"]),

 (105, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "holds his phone out to his son across the counter while his son wipes his hands to take it",
  [("somchai","ordinary","ต้น ในบัญชีพ่อเหลือเท่าไหร่ ลองเปิดดูให้พ่อทีลูก"),
   ("ton","surprised","พ่อจำรหัสไม่ได้เหรอครับ")], []),

 (106, 10, "Close-up on the two of them over the phone, static camera", ["somchai","ton"], "shop", "night",
  "takes the phone and turns it toward himself while his father watches the screen over his hands",
  [("somchai","plain","พ่อไม่เคยเปิดเลยลูก ตั้งแต่วันที่ลูกลงให้"),
   ("ton","quiet","สี่ปีไม่เคยเปิดเลยเหรอครับ"),
   ("somchai","even","พ่อไม่มีอะไรจะดูนี่ลูก")], []),
]

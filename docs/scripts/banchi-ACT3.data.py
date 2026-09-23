# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 3 — การเปิดเผย. Rendered by tools/build_shotsheet.py.

Act 2 ended with ต้น at the foot of the stairs asking why his father goes out
back. Act 3 is him answering his own question, out loud, with arithmetic — and
then refusing the money it bought.

The two lines at shots 78 and 79 are the film's title line. They were locked
before the rework and are reproduced here exactly. Nothing edits them.

Blocks are IMPORTED from Act 1, never copied — see the Act 2 header for why.
"""
import importlib.util as _il
from pathlib import Path as _P

_s1 = _il.spec_from_file_location("act1", _P(__file__).with_name("banchi-ACT1.data.py"))
_a1 = _il.module_from_spec(_s1); _s1.loader.exec_module(_a1)
_s2 = _il.spec_from_file_location("act2", _P(__file__).with_name("banchi-ACT2.data.py"))
_a2 = _il.module_from_spec(_s2); _s2.loader.exec_module(_a2)

STYLE = _a1.STYLE
CHAR = dict(_a2.CHAR)        # Act 2's CHAR already carries เชิด
LOC = dict(_a2.LOC)          # and the alley
VOICE = dict(_a2.VOICE)
NOT = dict(_a2.NOT)
PROP_FOR_NOT = dict(_a2.PROP_FOR_NOT)
PROPS_BY_SHOT = dict(_a2.PROPS_BY_SHOT)
WARDROBE = dict(_a2.WARDROBE)
APRON = _a1.APRON

# The wording rules this act obeys, all proved on this production's own footage
# (see google-flow-ops "A policy refusal comes from the DIALOGUE"):
#  · never a dependent named alongside a demand or a warning
#  · never money framed as an absolute prohibition — say what it is FOR
#  · the character acts WHILE speaking; no "then" in an action; no action that
#    is itself a silence
#  · a particle between any numeral and a vocative
SHOTS = [
 (59, 8, "Close-up, static camera", ["ton"], "stairs", "night",
  "sits down on the third step with his back to the wall, counting on his fingers while he talks himself through it",
  [("ton","working it out","สี่ปี... สี่ปีพอดีเลยเหรอ"),
   ("ton","slower, cold","ผมเข้ามหาลัยปีไหนนะ... ก็ปีนั้นแหละ")], []),

 (60, 10, "Close-up, static camera", ["ton"], "stairs", "night",
  "grips the stair rail with one hand as he keeps talking, working forward year by year",
  [("ton","quiet, certain","ปีหนึ่ง ปีสอง ปีสาม ปีสี่ ค่าเทอมทุกเทอมเลย"),
   ("ton","barely out loud","พ่อไม่เคยบอกผมเลยสักคำ"),
   ("ton","to himself","ผมนึกว่าร้านมันพอ")], []),

 (61, 8, "Medium shot, static camera", ["ton"], "stairs", "night",
  "climbs two more steps and stops with his hand flat against the stairwell wall, speaking upward toward the bedroom",
  [("ton","low","ย่ารู้มาตลอดใช่ไหมครับ"),
   ("ton","softer","ย่าถึงพูดว่าได้ยินหมด")], []),

 (62, 6, "Medium shot, static camera", ["ya"], "room", "night",
  "lies propped on the pillows with her eyes open in the dark, speaking toward the doorway",
  [("ya","thin, awake","...ต้นเหรอลูก..."),
   ("ya","slower","...ย่าไม่ได้หลับหรอก...")], ["ya"]),

 (63, 10, "Medium two-shot, static camera", ["ton","ya"], "room", "night",
  "sits down on the edge of her bed and takes her hand while she turns her face toward him, both talking quietly",
  [("ton","careful","ย่าครับ ผมถามอะไรหน่อยได้ไหมครับ"),
   ("ya","faint","...ถามสิลูก..."),
   ("ton","quiet","พ่อไปเอาเงินค่าเทอมผมมาจากไหนครับ")], ["ya"]),

 (64, 8, "Close-up on the old woman, static camera", ["ya"], "room", "night",
  "keeps hold of his hand while she answers, her eyes going past him to the doorway",
  [("ya","thin, careful","...ย่าบอกไม่ได้หรอกลูก..."),
   ("ya","slower","...พ่อเขาสั่งย่าไว้..."),
   ("ya","almost nothing","...ว่าอย่าให้ลูกรู้...")], ["ya"]),

 (65, 8, "Close-up, static camera", ["ton"], "room", "night",
  "lets go of her hand slowly and sits back, talking to her without looking at her",
  [("ton","flat","ผมรู้แล้วครับย่า"),
   ("ton","quieter","ผมนั่งนับเองอยู่ข้างล่างเมื่อกี้")], ["noya"]),

 (66, 6, "Medium shot, static camera", ["somchai"], "shop", "night",
  "comes in through the rear door and leans both hands on the counter, talking to the empty shop",
  [("somchai","worn out","เหนื่อยจังเลยวันนี้"),
   ("somchai","to himself","อีกงวดเดียวก็จบแล้ว")], []),

 (67, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "comes down the last steps into the shop while his father straightens up from the counter, both stopping where they are",
  [("ton","even","พ่อครับ"),
   ("somchai","tired, warm","ยังไม่นอนอีกเหรอลูก"),
   ("ton","steady","ผมรอพ่ออยู่ครับ")], []),

 (68, 10, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "takes a folded envelope from his apron and holds it out across the counter while his son stands with his hands at his sides",
  [("somchai","gentle","นี่ลูก เอาไว้ค่ารถไปสัมภาษณ์"),
   ("ton","not taking it","ผมไม่เอาเงินนี้ครับพ่อ"),
   ("somchai","light, tired","เอาไปเถอะลูก")], ["money"]),

 (69, 8, "Close-up on the son, static camera", ["ton"], "shop", "night",
  "keeps his hands at his sides and talks straight at his father across the counter",
  [("ton","level","พ่อไม่ต้องปกป้องผมแบบนี้ก็ได้ครับ"),
   ("ton","clear","ผมรู้เรื่องลุงเชิดแล้วครับ")], []),

 (70, 4, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "lowers the envelope to the counter and keeps his hand flat on top of it while he answers",
  [("somchai","quiet","ใครบอกลูก"),
   ("somchai","softer","ย่าเหรอ")], ["money"]),

 (71, 10, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "steps up to the counter opposite his father and puts both hands on it, the two of them facing each other across it",
  [("ton","steady","ไม่มีใครบอกผมครับ ผมนับเอง"),
   ("ton","firmer","สี่ปี ค่าเทอมผมสี่ปีพอดีเลยนะครับพ่อ"),
   ("somchai","quiet","อือ")], []),

 (72, 8, "Close-up on the son, static camera", ["ton"], "shop", "night",
  "keeps his hands on the counter and talks without raising his voice at all",
  [("ton","tight","ผมเรียนจบมาด้วยเงินแบบนั้นเหรอครับ"),
   ("ton","quieter","แล้วพ่อปล่อยให้ผมคิดว่าร้านมันพอ")], []),

 (73, 10, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "keeps his palm on the envelope and answers looking straight at his son",
  [("somchai","even","ตอนนั้นพ่อมีทางเลือกอยู่สองทางลูก"),
   ("somchai","steady","ทางหนึ่งคือบอกลูกว่าไม่มี"),
   ("somchai","quiet","พ่อเลือกอีกทาง")], ["money"]),

 (74, 6, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "pushes the envelope back across the counter toward his father with two fingers while his father watches his hand",
  [("ton","low","งวดนี้เท่าไหร่ครับ"),
   ("somchai","flat","ลูกไม่ต้องรู้")], ["money"]),

 (75, 8, "Close-up on the son, static camera", ["ton"], "shop", "night",
  "keeps his fingers on the envelope where he pushed it and talks down at it",
  [("ton","quiet","ผมจะหางานให้ได้ครับ"),
   ("ton","firmer","แล้วผมจะเป็นคนจ่ายเอง")], ["money"]),

 (76, 10, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "picks the envelope up and puts it into his son's shirt pocket himself, keeping his hand there while he talks",
  [("somchai","gentle, final","งวดนี้เป็นงวดสุดท้ายแล้วลูก"),
   ("somchai","warm","พ่อจ่ายมาสี่ปี อีกงวดเดียวพ่อก็ไหว"),
   ("ton","thin","พ่อ...")], ["money"]),

 (77, 8, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "keeps his hand flat on his son's chest over the pocket and talks quietly to him",
  [("somchai","steady","ลูกไม่ต้องรู้สึกผิดอะไรทั้งนั้นนะ"),
   ("somchai","softer","พ่ออยากให้ลูกได้เรียน พ่อก็เลยให้ลูกเรียน")], []),

 # ── THE TITLE LINE. Locked before the rework. Reproduced exactly. ──
 (78, 4, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "takes his hand back and squares his son's collar with both hands while he says it",
  [("somchai","warm, certain","เงินนี้พ่อตั้งใจหามาให้ลูก")], []),

 (79, 6, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "keeps hold of his son's collar and talks straight into his face",
  [("somchai","gentle","ไม่ต้องรู้ว่ามันมาจากไหน"),
   ("somchai","firmer","แค่ใช้มันให้คุ้ม")], []),

 (80, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "turns to the pot and ladles a bowl for his son while he talks, his son standing where he left him",
  [("somchai","ordinary again","กินก่อนไปสมัครงานนะลูก"),
   ("somchai","light","เดี๋ยวพ่อลวกเส้นให้")], []),

 (81, 8, "Medium shot, static camera", ["ton"], "shop", "night",
  "sits down at the nearest table and puts his hand flat on his own shirt pocket while he talks to his father's back",
  [("ton","quiet","ครับพ่อ"),
   ("ton","to himself","อีกงวดเดียว... ผมจำไว้แล้วนะครับ")], []),

 (82, 6, "Medium shot, static camera", ["ya"], "room", "night",
  "lies with her eyes open in the dark listening to the voices below, talking to the ceiling",
  [("ya","thin","...ได้ยินหมด..."),
   ("ya","slower","...ย่าจดไว้หมดแล้วลูก...")], ["ya"]),
]

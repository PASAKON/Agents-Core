# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 5 — สองร้อยแปด. The reversal. Rendered by build_shotsheet.py.

The arithmetic is done out loud, on screen, by the son — because a reversal the
audience watches being worked out lands harder than one they are told.

Two halves the technology cannot do alone: the bank app only goes back two years
(104 payments), and the grandmother's bedframe carries the other 104. Neither is
enough by itself. That is the point of her having been awake this whole film.

⚠ NUMBERS: this act is full of them, and a numeral running straight into a
vocative made the synthesiser stutter once already (ไปอีกสองที่พ่อ → "ไปอีก 2
ไปอีก 2 ที่พ่อ"). Every number here is followed by a particle or a classifier
before any form of address. Do not remove those particles.

Blocks IMPORTED from Act 2.
"""
import importlib.util as _il
from pathlib import Path as _P

_s1 = _il.spec_from_file_location("act1", _P(__file__).with_name("banchi-ACT1.data.py"))
_a1 = _il.module_from_spec(_s1); _s1.loader.exec_module(_a1)
_s2 = _il.spec_from_file_location("act2", _P(__file__).with_name("banchi-ACT2.data.py"))
_a2 = _il.module_from_spec(_s2); _s2.loader.exec_module(_a2)

STYLE = _a1.STYLE
CHAR = dict(_a2.CHAR); LOC = dict(_a2.LOC); VOICE = dict(_a2.VOICE)
NOT = dict(_a2.NOT); APRON = _a1.APRON
PROP_FOR_NOT = dict(_a2.PROP_FOR_NOT)
PROPS_BY_SHOT = dict(_a2.PROPS_BY_SHOT)

SHOTS = [
 (107, 6, "Close-up on the two of them over the phone, static camera", ["ton","somchai"], "shop", "night",
  "holds the phone flat on the counter so his father can see it too, scrolling with one thumb while he reads out",
  [("ton","reading","เหลือสามร้อยยี่สิบบาทครับพ่อ"),
   ("somchai","flat","อือ")], []),

 (108, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "keeps scrolling with his thumb beside his father, both of them looking down at the screen",
  [("ton","slowing","พ่อ... ทำไมพ่อถอนเงินทุกวันพฤหัสครับ"),
   ("somchai","quick","ปิดเถอะลูก")], []),

 (109, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "turns the phone toward his father and holds it there while his father keeps his hands on the counter",
  [("ton","steady","สองพันบาท ทุกอาทิตย์ ไม่เคยขาดสักครั้งเลยนะครับ"),
   ("somchai","warning","ต้น")], []),

 (110, 10, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "sets the phone down between them and looks up at his father, both leaning on the counter",
  [("ton","level","พ่อกู้มาทั้งหมดเท่าไหร่ครับ"),
   ("somchai","quiet","เทอมละสองหมื่นห้า แปดเทอมลูก"),
   ("ton","doing it aloud","ก็สองแสนพอดีสิครับ")], []),

 (111, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "keeps both hands flat on the counter answering his son, who stays leaning in beside him",
  [("somchai","even","เชิดบอกรวมแล้วเป็นสามแสนลูก"),
   ("ton","off it, fast","แล้วพ่อรู้ไหมครับว่าต้องจ่ายกี่งวด")], []),

 (112, 6, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "shakes his head once while he answers, still looking at his own hands",
  [("somchai","plain","พ่อไม่รู้หรอกลูก"),
   ("somchai","quieter","เชิดเป็นคนคิดให้")], []),

 (113, 10, "Close-up on the son, static camera", ["ton"], "shop", "night",
  "counts it out on the counter with his finger as he speaks, tapping once for each figure",
  [("ton","working it","สามแสน หารอาทิตย์ละสองพัน"),
   ("ton","certain","เท่ากับร้อยห้าสิบงวดครับพ่อ"),
   ("ton","turning","แล้วพ่อจ่ายมากี่งวดแล้วครับ")], []),

 (114, 4, "Close-up on the father, static camera", ["somchai"], "shop", "night",
  "keeps his eyes down on the counter while he answers his son",
  [("somchai","quiet","พ่อไม่เคยนับเลยลูก")], []),

 (115, 10, "Close-up on the son, static camera", ["ton"], "shop", "night",
  "scrolls back through the app with his thumb, counting under his breath as the screen moves",
  [("ton","reading, tight","แอปย้อนได้แค่สองปีครับ"),
   ("ton","counting","หนึ่งร้อยสี่ครั้งพอดีเลย"),
   ("ton","flat","ก่อนหน้านั้นไม่มีใครรู้เลยครับ")], []),

 (116, 4, "Medium shot, static camera", ["ya"], "room", "night",
  "lies with her eyes open in the dark, speaking toward the sound of the voices below",
  [("ya","thin, reaching","...พฤ... หัส..."),
   ("ya","finding it","...วัน... พฤหัส... ลูก...")], ["ya"]),

 (117, 4, "Medium two-shot, static camera", ["ton","ya"], "room", "night",
  "comes to the side of her bed still holding the phone and crouches down beside her face",
  [("ton","gentle","ย่าพูดอะไรนะครับ"),
   ("ya","slower","...ย่า... นับ... ไว้...")], ["ya"]),

 (118, 4, "Medium two-shot, static camera", ["ton","ya"], "room", "night",
  "puts the phone face-down on the blanket and leans closer to hear her, his hand on her arm",
  [("ton","careful","นับอะไรครับย่า"),
   ("ya","fainter","...ที่... เตียง...")], ["ya"]),

 (119, 8, "Close-up on the son, static camera", ["ton"], "room", "night",
  "runs his fingertips along the underside of the wooden bed rail while he talks, feeling the marks",
  [("ton","under his breath","อะไรอยู่ตรงนี้..."),
   ("ton","realising","รอยขีด... ย่าขีดไว้ทุกอาทิตย์เหรอครับ")], []),

 (120, 10, "Close-up on the bed rail and his hands, static camera", ["ton"], "room", "night",
  "counts the carved marks with his finger, moving along the rail and saying the numbers as he goes",
  [("ton","counting aloud","สิบ ยี่สิบ สามสิบ สี่สิบ ห้าสิบ"),
   ("ton","steadier","เก้าสิบ ร้อย"),
   ("ton","stopping","หนึ่งร้อยสี่รอยพอดีเลยครับย่า")], []),

 (121, 8, "Close-up on the son, static camera", ["ton"], "room", "night",
  "sits back on his heels with his hand still on the rail, saying it out loud to himself",
  [("ton","adding it","ร้อยสี่ที่นี่ บวกร้อยสี่ในแอป"),
   ("ton","quiet, certain","สองร้อยแปดงวดครับ")], []),

 (122, 4, "Close-up on the father in the doorway, static camera", ["somchai"], "room", "night",
  # 2026-09-23: was two lines, both saying the number, inside four seconds — it
  # played as a stutter rather than as shock (transcript read "208 งวด" then
  # "208"). One line and the silence after it does the same job: a man who cannot
  # get the rest of the sentence out is more stunned than one who repeats himself.
  "stands in the bedroom doorway with one hand on the frame, hearing the number without moving, his mouth open on a sentence he never finishes",
  [("somchai","hollow, trailing off","สองร้อยแปดงวด...")], []),

 (123, 10, "Medium two-shot, static camera", ["ton","somchai"], "room", "night",
  "stands up from the bed and faces his father in the doorway, holding the phone at his side",
  [("ton","level","หนี้พ่อร้อยห้าสิบงวดครับ"),
   ("ton","firmer","พ่อจ่ายเกินมาห้าสิบแปดงวด"),
   ("ton","flat","หนึ่งแสนหนึ่งหมื่นหกพันบาทครับพ่อ")], []),

 (124, 8, "Close-up on the son, static camera", ["ton"], "room", "night",
  "keeps his eyes on his father and says the last of it without raising his voice",
  [("ton","quiet","หนี้พ่อหมดตั้งแต่ปีที่แล้วแล้วครับ"),
   ("ton","softer","ปีที่แล้วครับพ่อ")], []),

 (125, 6, "Medium two-shot, static camera", ["somchai","ya"], "room", "night",
  "comes to the bedside and crouches down by his mother, taking her hand in both of his",
  [("somchai","breaking","แม่นับทำไมครับ"),
   ("ya","thin","...กลัว... ลูก... จำ... ไม่ได้...")], ["ya"]),

 # ── 5b: he goes to เชิด with nothing in his hands ──
 (126, 4, "Medium shot, static camera", ["somchai"], "alley", "night",
  "walks up the alley with both hands empty at his sides and stops under the bulb, calling ahead",
  [("somchai","even","เชิดครับ"),
   ("somchai","steady","ผมมาคุยด้วยหน่อยครับ")], []),

 (127, 8, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "comes out of the dark already smiling and puts his hands in his pockets as he arrives",
  [("cherd","warm","มาแล้วเหรอครับพี่ คิดได้แล้วใช่ไหมครับ"),
   ("somchai","flat","สองร้อยแปดงวดครับ")], []),

 (128, 8, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "takes his hands out of his pockets slowly while he answers the older man facing him",
  [("cherd","careful","อะไรนะครับพี่"),
   ("somchai","off it, steady","หนี้ผมร้อยห้าสิบงวด ผมจ่ายมาสองร้อยแปดครับ")], []),

 (129, 10, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "takes half a step closer while the older man stays exactly where he is, both keeping their voices low",
  [("cherd","quiet","พี่เอาตัวเลขมาจากไหนครับ"),
   ("somchai","even","จากคนที่นับให้ผมทุกอาทิตย์ ตั้งแต่วันแรกครับ"),
   ("cherd","testing","แล้วพี่มีอะไรในมือบ้างล่ะครับ")], ["nobook"]),

 (130, 6, "Medium two-shot, static camera", ["somchai","cherd"], "alley", "night",
  "opens both empty hands in front of him and keeps them open, the younger man watching them",
  [("somchai","plain","ไม่มีครับ"),
   ("cherd","off it","งั้นพี่จะทำอะไรได้ครับ")], []),

 (131, 6, "Close-up on the father, static camera", ["somchai"], "alley", "night",
  "lowers his hands and turns to walk back toward the shop as he says it",
  [("somchai","calm","ไม่ทำอะไรเลยครับ"),
   ("somchai","steady","ผมแค่จะไม่จ่ายอีกแล้ว")], []),

 (132, 6, "Medium shot, static camera", ["cherd"], "alley", "night",
  "stands alone in the alley watching the older man go, speaking after him",
  [("cherd","cold, pleasant","พี่อาจจะเสียใจทีหลังนะครับ"),
   ("cherd","softer, worse","ผมเป็นห่วงพี่จริงๆนะ")], []),
]

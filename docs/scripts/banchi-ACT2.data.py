# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 2 — source of truth. tools/build_shotsheet.py renders the sheet.

Act 2 opens where Act 1 stopped. Act 1 ended warm: the off-duty policeman eats
free and the father waves the money away. Act 2 brings in the man the whole film
turns on — and the audience is supposed to almost like him.

CHAR, LOC, VOICE, NOT and STYLE are IMPORTED from the Act 1 data file, not
copied. A face or a set that drifts between acts is the single most expensive
mistake this production can make, and copying the blocks is how that happens.
Anything genuinely new to Act 2 is added below the import and nowhere else.
"""
import importlib.util as _il
from pathlib import Path as _P

_spec = _il.spec_from_file_location("act1", _P(__file__).with_name("banchi-ACT1.data.py"))
_a1 = _il.module_from_spec(_spec); _spec.loader.exec_module(_a1)

STYLE = _a1.STYLE
CHAR = dict(_a1.CHAR)
LOC = dict(_a1.LOC)
VOICE = dict(_a1.VOICE)
NOT = dict(_a1.NOT)
APRON = _a1.APRON

# ── NEW IN ACT 2 ─────────────────────────────────────────────────────────────
# เชิด. Everything the film does later depends on the audience liking him here.
# His plate: lean, navy polo, grey trousers, sunglasses pushed up on his head,
# a silver bracelet, ordinary short hair. Written from the plate, not from memory.
CHAR["cherd"] = ("@lender_cherd",
  "a Thai man of 45, lean, with an even unlined face, short ordinary black hair, "
  "sunglasses pushed up onto the top of his head, in a plain navy polo shirt, grey "
  "trousers and a silver bracelet on his right wrist",
  "The 45-year-old man in the navy polo shirt")

# 19 Sep: the operator read the LIVE binding on @lender_cherd as Umbriel, which is
# what this ledger said all along — so the 18 Sep audit (task-68653632) that reported
# "algieba" is an audit error, and this line is back to Umbriel. Note the preset name
# is bookkeeping only: build_shotsheet writes VOICE[1] (the description) into prompts
# and never VOICE[0], so no shot was ever affected either way.
# The CEO's standing instruction (19 Sep) is that เชิด gets a CUSTOM voice based on
# this preset, not the bare preset — "บางที AI ลืม".
VOICE["cherd"] = ("Umbriel @lender_cherd — custom voice, base preset Umbriel",
  "the smooth, low, unhurried voice of a man of forty-five who never has to raise it")

LOC["alley"] = ("@back_alley",
  "a narrow service alley behind an old Bangkok shophouse at night — a steel rear door "
  "with a small barred window, stacked plastic crates against one wall, a bicycle leaning, "
  "cables strung overhead, wet uneven concrete, one weak bulb over the door and the alley "
  "falling away into darkness behind")

NOT["nobook"] = ("Also in this shot: no notebook, no ledger, no receipt book, no paper of "
                 "any kind changes hands. Nothing is written down by anyone.")

# n, seconds, framing, [character keys in attach order], location key, time of day,
# action, [(speaker key, direction, thai line), ...], [not-list keys]
#
# RULES THIS ACT WAS WRITTEN TO OBEY (all measured on Act 1's own footage):
#  · the character ACTS WHILE SPEAKING — never an action that finishes first.
#    No "then" anywhere in an action line; a sequence is two shots.
#  · no action that is itself a silence (no "pauses", "lets out a breath").
#  · the camera is on the mouth of whoever speaks; off-frame voices come out wrong.
#  · never a numeral running straight into a vocative — put a particle between.
#  · max 3 chips; the 4th is silently disabled.
SHOTS = [
 (35, 6, "Medium shot, static camera", ["ton","somchai"], "shop", "midday",
  "carries two bowls past his father toward a table while his father works the pot, both talking across the room",
  [("somchai","calling, busy","ลูกชิ้นพิเศษโต๊ะห้า"),
   ("ton","bright, moving","ได้ครับ เดี๋ยวก่อนนะครับ")], []),

 (36, 8, "Medium shot from inside the shop looking toward the street, static camera", ["cherd"], "shop", "midday",
  "steps in out of the glare and puts a hand on the back of a chair, smiling around the room as he speaks",
  [("cherd","warm, easy","สวัสดีครับพี่ชาย มาทานก๋วยเตี๋ยวหน่อย"),
   ("cherd","looking around, pleased","ร้านนี้คนแน่นดีนะครับ")], []),

 (37, 6, "Medium two-shot, static camera", ["somchai","cherd"], "shop", "midday",
  "wipes his hands on his apron and gestures to a table while the other man stays standing, both smiling",
  [("somchai","polite, a beat too quick","เชิญนั่งก่อนครับ เดี๋ยวผมมา"),
   ("cherd","unhurried","ไม่ต้องรีบครับพี่ ผมรอได้")], []),

 (38, 8, "Medium two-shot, static camera", ["ton","cherd"], "shop", "midday",
  "sets a bowl down in front of the seated man and straightens the spoon while the man looks up at him",
  [("ton","friendly","เส้นเล็กน้ำใสนะครับ ร้อนๆเลย"),
   ("cherd","pleasant, to him","โตขึ้นเยอะเลยนะ จำได้ตั้งแต่ยังวิ่งเล่นอยู่แถวนี้")], []),

 (39, 8, "Medium shot, static camera", ["ton","somchai"], "shop", "midday",
  "collects an empty bowl from the next table while his father ladles behind him, glancing back as he speaks",
  [("ton","curious, light","พ่อรู้จักลุงคนนั้นด้วยเหรอครับ"),
   ("somchai","not looking up, flat","รู้จักมานานแล้ว")], []),

 (40, 10, "Medium two-shot across the counter, static camera", ["cherd","somchai"], "shop", "midday",
  "eats while the older man refills a sauce tray beside him, both facing each other over the counter",
  [("cherd","conversational","งวดนี้ไม่น่ามีปัญหาอะไรเนอะพี่"),
   ("somchai","steady, too steady","ไม่มีครับ"),
   ("cherd","light, friendly","ผมก็ว่างั้น ร้านพี่คนเยอะออก")], []),

 (41, 8, "Close-up on the seated man, static camera", ["cherd"], "shop", "midday",
  "stirs his bowl slowly while he talks, looking up at someone standing off to the side",
  [("cherd","easy, almost kind","ผมไม่ชอบมากวนใครหรอกครับ ไม่ใช่นิสัยผม"),
   ("cherd","smiling","ผมชอบให้ทุกคนสบายใจกันทุกฝ่ายมากกว่า")], []),

 (42, 10, "Medium two-shot, static camera", ["somchai","cherd"], "shop", "midday",
  "stacks clean bowls at the counter beside the seated man while both keep their voices low and pleasant",
  [("somchai","carefully casual","เชิดเองก็ต้องส่งใครเหมือนกันใช่ไหมครับ"),
   ("cherd","immediate, smooth","ผมไม่มีเจ้านายหรอกพี่ เงินผมทั้งนั้น"),
   ("somchai","quiet","อือ")], []),

 (43, 6, "Close-up, static camera", ["ton"], "shop", "midday",
  "wipes the next table down without looking away from the two men across the room, talking to himself",
  [("ton","low, to himself","เงินเขาทั้งนั้น... เงินตัวเองแท้ๆ"),
   ("ton","slower, working it out","แล้วมานั่งกินร้านเราทุกอาทิตย์ทำไม")], []),

 (44, 8, "Medium shot, static camera", ["cherd","somchai"], "shop", "midday",
  "stands and slides a folded note under the edge of his empty bowl while the older man watches him do it",
  [("cherd","warm, rising to go","อร่อยเหมือนเดิมครับพี่"),
   ("cherd","lighter, half-turned","เย็นนี้ผมแวะหลังร้านนะครับ")], ["nobook"]),

 (45, 6, "Close-up on the counter, static camera", ["somchai"], "shop", "midday",
  "lifts the empty bowl off the folded note and reads it where he stands, talking quietly as he reads",
  [("somchai","under his breath","สามวันแล้วเหรอ เร็วจังเลย"),
   ("somchai","quieter, counting in his head","เย็นนี้... ผมยังไม่ได้เตรียมเลย")], ["nobook"]),

 (46, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "midday",
  "reaches past his father for the sauce tray while his father folds the note into his apron pocket",
  [("ton","light, probing","ลุงเขาฝากอะไรไว้เหรอครับพ่อ"),
   ("somchai","easy, dismissive","ใบเสร็จค่าของเก่าน่ะ ไม่มีอะไร")], ["nobook"]),

 (47, 6, "Medium shot, static camera", ["ton"], "shop", "late afternoon",
  "stacks chairs onto a table while the light goes orange, calling toward the back of the shop",
  [("ton","calling, ordinary","พ่อครับ ผมเก็บหน้าร้านแล้วนะครับ"),
   ("ton","lighter","เดี๋ยวผมขึ้นไปดูย่าก่อนนะครับ")], []),

 (48, 8, "Medium shot, static camera", ["somchai"], "shop", "dusk",
  "unties his apron at the counter and folds it as he answers, already turning toward the rear of the shop",
  [("somchai","even, ordinary","ไปเถอะลูก เดี๋ยวพ่อเก็บที่เหลือเอง"),
   ("somchai","a shade too light","พ่อออกไปทิ้งขยะหลังร้านแป๊บนึง")], []),

 (49, 8, "Medium shot, static camera", ["somchai"], "alley", "night",
  "pulls the steel rear door shut behind him and stands under the weak bulb, speaking toward the dark end of the alley",
  [("somchai","quiet, braced","มาแล้วเหรอครับ ผมรออยู่พอดี"),
   ("somchai","steady, holding it together","งวดนี้ผมเตรียมไว้แล้วครับ ไม่ต้องห่วง")], []),

 (50, 10, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "walks up out of the dark and stops close, hands in his pockets, talking while the older man stands very still",
  [("cherd","friendly, unhurried","งวดนี้ช้าไปสามวันนะครับพี่ ผมเลยแวะมาเอง"),
   ("somchai","fast","พรุ่งนี้ผมหาให้ครบแน่นอนครับ"),
   ("cherd","gently","พี่พูดแบบนี้ทุกงวดเลยนะครับ")], ["nobook"]),

 (51, 10, "Medium two-shot, static camera", ["cherd","somchai"], "alley", "night",
  "takes the folded money and counts it against his thumb while he talks, the older man watching his hands",
  [("cherd","conversational","ได้ยินว่าคุณแม่ไม่ค่อยสบายนะครับ"),
   ("cherd","softer, worse for being soft","เดือนหน้าค่าหมอคงอีกก้อน ผมห่วงแทนพี่ครับ"),
   ("somchai","tight","แม่ผมสบายดีครับ")], ["money","nobook"]),

 (52, 8, "Close-up on the younger man, static camera", ["cherd"], "alley", "night",
  "folds the money into his shirt pocket while he speaks, unbothered, already easing back a step",
  [("cherd","matter-of-fact","สี่ปีแล้วนะครับพี่ เวลามันไม่รอใครเลย"),
   ("cherd","warm again","อาทิตย์หน้าเวลาเดิมนะครับ")], ["money","nobook"]),

 (53, 8, "Medium shot, static camera", ["somchai"], "alley", "night",
  "stands alone under the bulb with his empty hands open in front of him, talking to no one",
  [("somchai","hollow","สี่ปีแล้วจริงๆด้วย ผมนับไม่ไหวแล้ว"),
   ("somchai","quieter, to himself","อีกงวดเดียว แค่งวดเดียวก็หมดแล้ว")], []),

 (54, 6, "Medium shot from inside the shop, static camera", ["ton"], "shop", "night",
  "comes down the last of the stairs into the dark shop and stops, looking toward the rear door as he speaks",
  [("ton","calling, ordinary","พ่อครับ ย่าหลับแล้วนะครับ"),
   ("ton","slower, puzzled","พ่อ...อยู่ไหนครับ")], []),

 (55, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "night",
  "comes in through the rear door wiping his hands on his shirt while his son stands watching him cross the room",
  [("somchai","light, too light","อยู่นี่ลูก พ่อออกไปทิ้งขยะมา"),
   ("ton","flat","ขยะอะไรใช้เวลาตั้งนานครับพ่อ"),
   ("ton","quieter","ผมยืนรออยู่ตั้งนานแล้ว")], []),

 (56, 10, "Medium two-shot, static camera", ["ton","somchai"], "shop", "night",
  "picks up the last chair and sets it on the table while his father wipes the counter beside him, neither looking at the other",
  [("ton","careful","พ่อ... ลุงคนกลางวันนั่น เขาชื่ออะไรนะครับ"),
   ("somchai","not looking up","เชิด"),
   ("ton","quiet","เขามาทุกอาทิตย์เลยเหรอครับ")], []),

 (57, 8, "Close-up, static camera", ["somchai"], "shop", "night",
  "keeps wiping the same patch of counter while he answers, eyes down",
  [("somchai","even","เขามากินก๋วยเตี๋ยวลูก"),
   ("somchai","firmer","ไปนอนเถอะ พรุ่งนี้ต้องตื่นเช้า")], []),

 (58, 8, "Medium shot, static camera", ["ton"], "stairs", "night",
  "climbs two steps and stops with his hand on the rail, looking back down into the dark shop as he speaks",
  [("ton","low, to himself","เงินเขาทั้งนั้น..."),
   ("ton","quieter","แล้วทำไมพ่อต้องออกไปหลังร้าน")], []),
]

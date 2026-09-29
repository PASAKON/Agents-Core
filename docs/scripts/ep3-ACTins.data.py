# -*- coding: utf-8 -*-
"""«น้ำไม่เลือกบ้าน» (film 3) inserts, shots 76-79, added after the CEO watched the full rough cut.
Source of truth for tools/build_shotsheet.py.

CEO 2026-09-27: "ฉากที่ชาวบ้านช่วยกันเอาออกมาบริจาค ... เป็นตัวประกอบอย่างเดียว ไม่ต้องมีบทพูด
ให้มีแค่ป้าที่ทำข้าวเลี้ยง พูดว่าขอบคุณที่เอาออกมาฝากนะคะ" (2-3 donation shots) and "ฉากที่เห็นว่า
น้ำเริ่มขึ้นแล้ว เป็นฉากเปลี่ยนผ่าน ระหว่างน้ำระดับเท้ากับน้ำขึ้นสูง". Approved the same day:
"อณุมติให้ยิง 4 ฉาก + Retry 3 / video".

Numbered 76-79 so the shot ledgers of ACT1-3 never change (S74-S75 are the edit's push-ins).
Where each one goes in the cut:
  76 after S13  - the orange-shirt neighbour (the man in the S53 queue) brings rice, right after
                  เฮียกิจ says "ของผม ผมกินเอง"
  77 after S35  - a neighbour woman brings eggs and bananas
  78 after 77   - a neighbour man brings vegetables and dried fish; then S36-S37, where ป้าน้อย
                  says "ทุกบ้านช่วยกันเติม" - the two inserts show it instead of only claiming it
  79 after S38  - nobody in frame: floodwater seeps under เฮียกิจ's door toward the hoard he left
                  on the floor (the payoff of S14 and S16); S39 then opens waist-deep
  80 after S54  - the queue the dialogue only talked about, shown: two neighbours with bowls in
                  the water, เฮียกิจ wading up to the very end (CEO 2026-09-27: "ฉากที่ชาวบ้าน
                  มาต่อแถว แล้วคุณพ่อต่อแถวท้ายสุดเลย ... ตัวประกอบ 2-3 คน"). Two extras, not
                  three, so the frame stays at three people
Extras never speak. Every Thai line keeps a space between phrases (CEO 2026-09-27).
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "ep3_act1", Path(__file__).with_name("ep3-ACT1.data.py"))
_a1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_a1)

STYLE = _a1.STYLE
CHAR = dict(_a1.CHAR)
CHAR.update({
 "d1": ("@donor1__work",
   "a thin Thai woman of about sixty-two with a narrow weathered face, deep smile lines and "
   "grey-streaked black hair tied back in a small low knot, wearing a faded maroon "
   "short-sleeved cotton blouse with no print and loose black cotton trousers rolled up to the "
   "knee, barefoot",
   "The thin woman in the maroon blouse"),
 "d2": ("@donor2__work",
   "a lean, sun-tanned Thai man of about thirty-five with short black hair and a thin "
   "moustache, wearing a plain charcoal-grey T-shirt with no print and black knee-length "
   "shorts, barefoot",
   "The man in the grey T-shirt"),
})
WARDROBE = dict(_a1.WARDROBE)
VOICE = dict(_a1.VOICE)
LOC = dict(_a1.LOC)
LOC["kij_seep"] = ("@kij__dry", _a1._KIJ_ROOM + ", the glossy white floor still dry, a big pile "
   "of plain brown cardboard cartons and shrink-wrapped packs of water bottles stacked on the "
   "floor in the middle of the room, the glass front door shut, rain falling on the flooded "
   "lane outside")
NOT = dict(_a1.NOT)
NOT["extrasilent"] = ("Only the woman in the checked apron speaks in this shot. The other person "
   "never says a single word: no lines, no murmur, no reply; they only smile and nod.")
NOT["kijonly"] = ("Only the stocky man speaks in this shot. The other two people never say a single "
   "word: no lines, no murmur, no reply; the thin woman only glances back and nods. Exactly three "
   "people in the whole frame, nobody on the porch, nobody else in the water.")
NOT["nopeople"] = ("No people appear in this shot at all, not even in the distance or behind the "
   "glass. Nobody speaks: no dialogue, no words, no voices, no narrator; the only sounds are "
   "rain, trickling water and distant thunder.")
PROP_FOR_NOT = dict(_a1.PROP_FOR_NOT)
PROPS_BY_SHOT = {79: ["@water_pack"]}

T2 = _a1.T2
T3 = "the first day of the flood, afternoon, overcast daylight"
T3R = "the first day of the flood, late afternoon, grey rainy daylight"
T5 = "the same day around noon, grey overcast daylight"   # = ACT3 T5, the S54-S55 queue

_NAME = dict(_a1._NAME)
_NAME.update({"d1": "ชาวบ้านหญิง", "d2": "ชาวบ้านชาย"})

_THANKS = "ขอบคุณที่เอาออกมาฝากนะคะ"   # the CEO's line, word for word, in all three

# n: (seconds, framing, [char keys, speaker first], loc, time of day, action, [(key, direction, line)], [nots])
_META = {
 76: (8, "Medium shot at the porch steps, both faces three-quarters to camera",
      ["noi", "nb"], "porch1", T2,
      "the man in the orange T-shirt, shy and quiet, has waded up to the porch steps through the "
      "ankle-deep water with a plain white unprinted rice sack on his shoulder and lifts it up to "
      "her; the woman in the checked apron, touched and grateful, eyes shining, bends down and "
      "takes the sack in both arms while she speaks, and he smiles and nods without a word",
      [("noi", "touched and grateful, smiling wide",
        _THANKS + " ข้าวสารถุงนี้ พรุ่งนี้หุงได้อีกหลายหม้อเลย")],
      ["extrasilent", "nologo", "nocash", "nosubs"]),
 77: (8, "Medium two-shot at the porch steps",
      ["noi", "d1"], "porch1", T3,
      "the thin woman in the maroon blouse, humble and a little shy, stands on the lowest step in "
      "the water holding up a small plastic bag of eggs and a bunch of green bananas; the woman in "
      "the checked apron, delighted, takes them from her with both hands while she speaks, and "
      "the thin woman smiles and nods without a word",
      [("noi", "delighted and warm, laughing softly",
        _THANKS + " ไข่กับกล้วย เยอะขนาดนี้ ยายเย็นได้กินไข่ต้มแล้ว")],
      ["extrasilent", "nologo", "nocash", "nosubs"]),
 78: (8, "Medium two-shot at the porch table, the steaming pot behind them",
      ["noi", "d2"], "porch1", T3,
      "the man in the grey T-shirt, dripping from the lane, sets a plastic basin of fresh green "
      "vegetables and a few dried fish on the porch table; the woman in the checked apron, moved "
      "and grateful, lifts the vegetables and tips them into the steaming pot while she speaks, "
      "and he smiles and nods without a word",
      [("noi", "moved and grateful, bright",
        _THANKS + " ผักกับปลาแห้ง เติมหม้อได้อีกทั้งวันเลย")],
      ["extrasilent", "nologo", "nocash", "nosubs"]),
 79: (8, "Low static shot at floor level from inside the room toward the shut glass front door, "
         "the stacked water packs and cartons in the foreground",
      [], "kij_seep", T3R,
      "nobody is in the room. Muddy brown floodwater seeps in under the shut glass front door and "
      "creeps slowly across the white marble floor in a thin spreading sheet, reaching the bottom "
      "of the stacked water packs and cartons and darkening the cardboard, while rain drums on the "
      "flooded lane outside",
      [],
      ["nopeople", "nologo", "nosubs"]),
 80: (8, "Medium wide from the water at eye level, the porch steps and the steaming pot in the "
         "background, the short queue in the foreground",
      ["kij2", "nb", "d1"], "porch3", T5,
      "the man in the orange T-shirt and the thin woman in the maroon blouse stand one behind the "
      "other in waist-deep water in front of the porch steps, each holding an empty bowl in both "
      "hands, waiting their turn; the stocky man, humbled, head bowed, wades up behind them with "
      "his own empty bowl and stops at the very end of the queue while he speaks softly to the "
      "thin woman in front of him; she glances back over her shoulder and nods without a word",
      [("kij2", "humbled and quiet, eyes down",
        "ขอต่อท้ายนะครับป้า ผมไม่แซงใครแล้ว ใครลำบากก่อน ได้กินก่อน ผมยืนตรงนี้แหละครับ")],
      ["kijonly", "nologo", "nocash", "nosubs"]),
}

SHOTS = [(n, secs, framing, chars, loc, tod, action, spoken, nots)
         for n, (secs, framing, chars, loc, tod, action, spoken, nots) in sorted(_META.items())]

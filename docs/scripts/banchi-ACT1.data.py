# -*- coding: utf-8 -*-
"""«บัญชี» องก์ 1 — source of truth. tools/build_shotsheet.py renders the sheet from this.

Written from docs/scripts/banchi-ACT1-REWORK-SPEC.md. Every block below is pasted
verbatim into every shot that uses it, so a set or a face cannot drift between
two shots the way it did in the first shoot.
"""

STYLE = "Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light."

# key: (handle, full appearance block, short reference used in dialogue lines)
CHAR = {
 "somchai": ("@lung_somchai",
   "a Thai man of 58, lean, with a weathered square face, short greying black hair, "
   "deep-set brown eyes and light stubble, wearing a faded dark-blue cotton shopkeeper's "
   "apron over a plain white short-sleeved shirt and a worn leather watch on his left wrist",
   "The 58-year-old man in the dark-blue apron"),
 "ton": ("@nong_daeng",
   "a Thai man of 24, slim, oval-faced, with thick black hair swept back, dark brown eyes, "
   "clean-shaven, in a plain grey short-sleeved polo shirt",
   "The 24-year-old man in the grey polo shirt"),
 "ya": ("@grandma_pranom",
   "a frail Thai woman of 79, thin, fine wispy silver-white hair in a short bob, deeply wrinkled papery skin, sunken cheeks, cloudy but alert dark eyes, no glasses, "
   "in a faded floral-print cotton nightgown, lying propped on two stacked pillows with a thin "
   "nasal cannula looped over her ears and a small brass amulet on a string at her neck",
   "The 79-year-old woman in the bed"),
 # ต้น dressed to go looking for work — CEO 2026-09-18: "ชุดสูทไม่หรูมาก ล็อกหน้าเดิม".
 # The face block is word-for-word identical to "ton" on purpose: only the clothes
 # change, so the model has nothing to reinterpret about who he is.
 "ton_suit": ("@nong_daeng_suit",
   "a Thai man of 24, slim, oval-faced, with thick black hair swept back, dark brown eyes, "
   "clean-shaven, in a plain inexpensive dark-grey suit jacket over a white shirt with an "
   "open collar and no tie, the jacket a little loose on the shoulders",
   "The 24-year-old man in the grey suit jacket"),
 "wit": ("@cop_wit",
   "a Thai man of 32, medium athletic build, short neat black hair, clean-shaven, calm steady "
   "eyes, in a plain dark-grey polo shirt with an open two-button collar and a simple steel "
   "wristwatch on his left wrist",
   "The 32-year-old man in the dark-grey polo shirt"),
}

# ── VOICE ────────────────────────────────────────────────────────────────────
# Flow's own "save a customised voice" button is dead (proved 3 ways, 2026-09-18:
# task-36507a6a, task-881f8f0c). So the customisation the CEO asked for lives
# HERE instead, and the builder pastes it into every line that character speaks.
# Same effect in the ear, and it stays in the script under version control
# rather than inside Google's account state.
#
# key: (the CUSTOM voice bound in Flow, the description pasted into every line)
# Custom voices exist and are bound as of 2026-09-18 (task-989c3527), 5/5 verified
# after reload. The per-line description is KEPT for now even though the bound voice
# already encodes the identity — whether it reinforces or over-steers is decided by
# looking at this batch, not by guessing.
# The presets are cast as far apart as this set allows — low / mid-low / mid for
# the three men who share scenes, because Achird measured 150 Hz against ต้น's
# 148 and the two read as one person.
# The block describes WHO the voice is — timbre, pitch, age. It must never
# describe pace or mood: that is the per-line direction's job, and a voice block
# saying "unhurried" under a line marked "fast and placating" is two orders to
# the model at once.
VOICE = {
 "somchai": ("Algenib @lung_somchai",
   "the worn, low, gravelly voice of a tired man in his late fifties"),
 "ton": ("Iapetus @nong_daeng",
   "the clear, light voice of a man in his twenties, higher than his father's"),
 "ya": ("Vindemiatrix @grandma_pranom",
   "the thin, breathy, faintly wavering voice of a very frail woman near eighty"),
 # Same man as "ton", so the same voice, word for word. A wardrobe variant with
 # its own CHAR key silently fell through the builder's VOICE lookup and would
 # have spoken with no voice block at all in every Act 2/3 shot he wears the suit.
 "ton_suit": ("Iapetus @nong_daeng",
   "the clear, light voice of a man in his twenties, higher than his father's"),
 "wit": ("Rasalgethi @cop_wit",
   "the even, mid-pitched voice of a calm man in his early thirties"),
}

# CEO 2026-09-18: ต้น wears NO apron, ever. "เขาแค่ช่วยงานพ่อแปปเดียว เขาต้องหางาน
# ข้างนอกบ้านทำด้วย" — the apron would read as a man who works here, and the whole
# story is that he is trying not to be. Kept as a constant so the reason survives.
APRON = ""

LOC = {
 "shop": ("@noodle_shop",
   "a narrow Bangkok shophouse ground floor turned noodle shop — five worn wooden tables with "
   "bright red, blue and green plastic stools, a square structural pillar standing in the middle "
   "of the room with a small chalkboard menu hung on it, a narrow wooden staircase rising from "
   "the middle of the room beside that pillar, the room deep and narrow with the street at the "
   "far end, "
   "a stainless-steel soup cart with a steaming broth pot against the left wall, an open roll-up "
   "shutter onto a busy street, bare bulbs strung overhead, walls stained pale yellow with age, a "
   "laminated payment sign on the counter"),
 "room": ("@upstairs_bedroom",
   "a small upstairs bedroom in an old Bangkok shophouse — a single low wooden bed with a "
   "scratched wooden side rail against a bare plaster wall marked with cracks and water stains, a "
   "folded reddish-brown striped blanket, a small side table holding medicine bottles and a "
   "glass of water, an "
   "oscillating pedestal fan, one bare bulb hanging from the ceiling and no table lamp, a piece of "
   "cloth hanging on the wall near the window, wooden floorboards with visible gaps, a shuttered "
   "window letting in one thin band of daylight"),
 "stairs": ("@staircase",
   "a narrow steep wooden staircase inside an old Bangkok shophouse — worn treads, a wooden "
   "handrail, stairwell walls painted teal-turquoise with peeling paint, a pipe running down the "
   "wall, cluttered shop stock on shelving at the foot of the stairs, a single bare bulb on the "
   "landing above"),
 "wall": ("@side_wall",
   "the side exterior wall of an old Bangkok shophouse before dawn — rough grey concrete with "
   "peeling paint and long water stains, an air-conditioner bracket, a rusted pipe running down to "
   "the ground, wet pavement, a single distant streetlamp"),
}

# เชิด, defined here since 2026-09-23 because the rain opening (shots 1-2) shows
# him. Everything the film does later still depends on the audience liking him
# in Act 2 — the opening makes that dramatic irony: they have seen who he is.
# His plate: lean, navy polo, grey trousers, sunglasses pushed up on his head,
# a silver bracelet, ordinary short hair. Written from the plate, not from memory.
CHAR["cherd"] = ("@lender_cherd",
  "a Thai man of 45, lean, with an even unlined face, short ordinary black hair, "
  "sunglasses pushed up onto the top of his head, in a plain navy polo shirt, grey "
  "trousers and a silver bracelet on his right wrist",
  "The 45-year-old man in the navy polo shirt")
# 19 Sep: live binding read as Umbriel (the 18 Sep "algieba" audit was an error).
# build_shotsheet writes VOICE[1] into prompts, never VOICE[0].
VOICE["cherd"] = ("Umbriel @lender_cherd — custom voice, base preset Umbriel",
  "the smooth, low, unhurried voice of a man of forty-five who never has to raise it")

NOT = {
 # CEO 2026-09-18: the money in this film is invented prop money, not currency.
 # Not "hide the notes" — change what the notes ARE, so a counting scene can be
 # shot openly. Foreign currency is NOT the safer option: dollars, euro, yen and
 # yuan all carry portraits and protected designs of their own.
 # Describes the ACTUAL @money_fold plate (regenerated 2026-09-22), not an idea
 # of one. A description of a specific existing image beats a description of a
 # category: the earlier wording asked for "pastel paper, no portrait" in the
 # abstract and lost to the model's prior for Thai banknotes in a Thai shop.
 # Act 3's money scenes are ENVELOPE scenes — the action lines say so and the
 # notes are never meant to be seen. Says where the money is rather than only
 # what it must not look like, because a prohibition alone lost to the model's
 # prior six times (2026-09-22).
 "money": "The money is inside a plain brown paper envelope, folded once, and "
          "stays inside it: the envelope is never opened in this shot and not a "
          "single banknote is visible — no note in a hand, none protruding from "
          "the flap, none on the counter, none anywhere in frame. If any edge of "
          "a note shows at all it is plain soft pastel paper, dusty rose or pale "
          "sage, blank, with no printing on the visible part. No face, portrait "
          "or bust; no crest, seal, emblem, flag or monument; no country name "
          "and no readable script. It resembles no real currency of any country. "
          "Also in this shot: no notebook, no pen, no paper, no ledger of any "
          "kind.",
 # Per-shot, never global. Veo burned mangled Thai captions into 3 of 173
 # shots (29, 43, 115, measured by tools/burned_text_scan.py 2026-09-23), and
 # a re-fire of 43 came back captioned again. Two of the three described
 # speech meant not to be heard ("talking to himself", "counting under his
 # breath") — a hypothesis, n=2, so those lines were also rewritten as spoken
 # aloud. Used on the re-shoots and the new police shots only, so the other
 # 170 prompts stay exactly as they were rendered.
 # CEO 2026-09-23 on the rain opening: "ไม่มีการทำร้ายร่างกายนะ". A threat in
 # words only. Said as what DOES happen (he stands close, never touches) as well
 # as what does not, because a bare prohibition has lost to context before.
 "noviolence": "The younger man never touches him: he stands close and speaks "
               "quietly, and that is all. No hitting, pushing, grabbing, shoving or "
               "pinning, no raised hand and no weapon anywhere in the frame.",
 "nosubs": "No subtitles, no captions and no on-screen text of any kind appear "
           "anywhere in the frame.",
 "ya":    "She stays lying propped on the pillows and does not sit up. She wears no glasses. The "
          "nasal cannula stays on.",
 # Keeps her out of frame WITHOUT handing her sickroom equipment to whoever is
 # left in it. Measured 2026-09-22: ten shots listed "ya" meaning "exclude her"
 # and got the continuity rule instead, so shot 65 rendered the son wearing her
 # nasal cannula at her bedside. Nine of the ten were unshot, including Act 7,
 # which is set a year after she dies.
 "noya":  "The grandmother is not in this shot: no second person in the bed, no face on the "
          "pillow. Any oxygen tubing runs away under the blanket and touches nobody's face. "
          "The young man and his father wear nothing on their faces — no tube, no cannula, "
          "no mask, no medical equipment of any kind on either of them.",
}

# Props that must LOOK a specific way get an Element, not a paragraph. A shot
# that declares NOT["money"] has banknotes in frame, so the builder attaches
# @money_fold to it automatically — keyed off the declaration the writer already
# makes, so nobody has to remember a second list.
# Props attached PER SHOT, decided by reading the action line — never derived
# from a flag. Audited 2026-09-22: NOT["money"] is a prohibition carried by 22
# shots, most with no money in frame, so keying off it would have put banknotes
# into scenes written to be empty of them.
#
# Act 3's money scenes are the case that matters: every one of their action
# lines says ENVELOPE — "takes a folded envelope from his apron", "pushes the
# envelope back", "puts the envelope into his son's shirt pocket". The notes are
# meant to stay inside it and never be seen. Six clips rendered a real Thai
# 500-baht note with the royal portrait instead, because the only thing bound
# was nothing at all and the model filled the gap with its prior.
# Wardrobe plates, per CHARACTER key (not per shot): the face comes from the
# character's own plate, the clothes from a separate plate with no person in it.
# A/B 2026-09-23 (360p/4s, shot 149's text): the uniformed วิทย์ as ONE full-body
# still came back older and greying — the father's face leaking in — while his
# face plate + a wardrobe plate held his face. google-flow-ops §Wardrobe says
# the same. build_shotsheet attaches the plate and labels it a wardrobe reference.
WARDROBE = {}

PROPS_BY_SHOT = {
    1: ["@prop_envelope"], 2: ["@prop_envelope"],   # rain opening, CEO 2026-09-23
    68: ["@prop_envelope"], 70: ["@prop_envelope"], 73: ["@prop_envelope"],
    74: ["@prop_envelope"], 75: ["@prop_envelope"], 76: ["@prop_envelope"],
}

PROP_FOR_NOT = {
    "money": "@money_fold",
}

# n, seconds, framing, [character keys in attach order], location key, time of day,
# action, [(speaker key, direction, thai line), ...], [not-list keys]
SHOTS = [
 # Rain opening, CEO 2026-09-23: "ฉากเปิดเรื่องอยากให้เป็น Hook หน่อยๆ เรียกคน
 # ดูมีการขู่จริง และฝนตกด้วย มีเสียงฝน ฟ้าร้องจริง" — "แต่ไม่มีการทำร้ายร่างกายนะ".
 # The lender is now on screen, dry under his umbrella while the father is soaked:
 # the audience knows who he is before Act 2 introduces him as a friendly regular.
 (1, 10, "Medium two-shot in the rain, static camera with a slight handheld sway", ["somchai","cherd"], "wall", "just before dawn, in pouring rain",
  "stands with his back to the wet wall, soaked through, while the younger man stands close in front of him under a black umbrella, completely dry; heavy rain hammering the pavement and thunder rolling overhead, both faces angled three-quarters toward the camera",
  [("cherd","quiet, pleasant, cold","งวดนี้ขาดอีกแล้วนะครับพี่"),
   ("somchai","pleading","พรุ่งนี้ผมหาให้ครบครับ ผมสัญญา"),
   ("cherd","leaning a little closer, very calm","ร้านนี้ แม่พี่ ลูกพี่ ผมรู้จักหมดนะครับ")], ["money","noviolence","nosubs"]),

 (2, 6, "Close-up, static camera at a low angle", ["somchai"], "wall", "just before dawn, in pouring rain",
  "watches a thin brown envelope drop from above into the puddle at his feet, then crouches in the rain to pick it up, calling after someone walking away out of frame, a flash of lightning lighting his wet face and thunder cracking overhead",
  [("somchai","hoarse, calling after him","พรุ่งนี้... ผมสัญญาครับ"),
   ("somchai","louder, desperate","ขอแค่อย่าให้ลูกผมรู้นะครับ")], ["money","nosubs"]),

 (3, 4, "Medium shot, static camera, from above on the landing", ["somchai"], "stairs", "just before dawn",
  "stops halfway up the stairs in bare feet and looks back down toward the dark shop, a small cloth pouch in one hand",
  [("somchai","whispered to himself","เบาๆ... อย่าให้แม่ตื่น"),
   ("somchai","under his breath","ยังไม่ทันสว่างเลย")], []),
 (4, 10, "Medium two-shot, static camera", ["somchai","ya"], "room", "just before dawn",
  "sits at the bedside setting pill bottles out on a tray while the old woman wakes and turns her head toward him",
  [("somchai","gentle, unhurried","แม่ ตื่นแล้วเหรอ นี่ยาเม็ดขาวก่อนนอน เม็ดเหลืองตอนเช้า"),
   ("ya","running out of air mid-sentence","...ลูก..."),
   ("somchai","tender","ครับ ผมเอง")], ["ya"]),
 (5, 8, "Medium two-shot, static camera", ["somchai","ya"], "room", "just before dawn",
  "draws the blanket up over her shoulders and stays leaning in close",
  [("somchai","warm","เดี๋ยวพรุ่งนี้พาไปหาหมอนะแม่"),
   ("ya","weak, protesting","...ไม่ต้อง... เปลือง..."),
   ("somchai","firm but gentle","ไม่เปลืองหรอกแม่ เรื่องของแม่ไม่เปลือง")], ["ya"]),
 (6, 8, "Medium shot, static camera, his face and the tray both in frame", ["somchai"], "room", "just before dawn",
  "counts coins and folded notes into the cloth pouch at the bedside, his lips moving with the count",
  [("somchai","counting under his breath","สี่สิบ ห้าสิบ หกสิบ เจ็ดสิบห้าบาท"),
   ("somchai","flat","อีกสามร้อยก็ครบค่ารักษาแม่เดือนนี้แล้ว")], ["money"]),
 (7, 6, "Close-up, static camera", ["somchai"], "room", "just before dawn",
  "lets a breath out and looks toward the doorway that leads down to the shop",
  [("somchai","flat, to himself","เดือนนี้ไม่พออีกแล้ว"),
   ("somchai","quiet, deciding","ต้องหาทางอื่น")], []),

 (8, 6, "Medium shot, static camera", ["somchai"], "shop", "early morning",
  "hauls the roll-up shutter open and turns to the street, the broth pot already steaming behind him",
  [("somchai","calling out, warm","เปิดแล้วครับ เชิญเลยครับ"),
   ("somchai","easy","วันนี้มาเช้ากันจังนะครับ")], []),
 (9, 10, "Medium two-shot across the counter, static camera", ["ton","somchai"], "shop", "mid-morning",
  "ties his apron behind his back while the older man works the pot beside him, both facing each other",
  [("ton","tired but forcing cheerfulness","เมื่อคืนผมส่งใบสมัครไปอีกสองแห่งแล้วนะพ่อ"),
   ("somchai","not looking up","ที่ไหนบ้างล่ะ"),
   ("ton","matter-of-fact","โรงงานแถวบางนา กับบริษัทขนส่ง")], []),
 (10, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "mid-morning",
  "sets down a ladle and turns to face his son properly",
  [("somchai","reassuring","ดีแล้ว ค่อยๆหาไป อย่าไปเร่ง"),
   ("ton","tight, held back","ผมเรียนจบมาปีนึงแล้วนะพ่อ")], []),
 (11, 8, "Close-up, static camera, steam drifting past him", ["somchai"], "shop", "mid-morning",
  "goes back to the wok, talking over his shoulder, then glances at his son with a small smile",
  [("somchai","unhurried","พ่อขายก๋วยเตี๋ยวมาสามสิบปี ไม่เห็นต้องรีบไปไหน"),
   ("somchai","through a smile","กินข้าวยังลูก")], []),
 (12, 6, "Medium shot, slight handheld", ["ton"], "shop", "mid-morning",
  "leans toward a seated customer with a small notepad, then calls the order back toward the counter",
  [("ton","polite","เส้นเล็กหรือเส้นใหญ่ครับ"),
   ("ton","brisk","ได้ครับ สองชาม เดี๋ยวมาครับ")], []),
 (13, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "mid-morning",
  "pours broth into the big pot while his son stacks bowls beside him",
  [("somchai","brisk, routine","ต้น เก็บโต๊ะสองทีนึง แล้วเติมน้ำซุปด้วยนะ"),
   ("ton","wry, affectionate","พ่อสั่งงานเก่งกว่าใครในซอยเลยนะเนี่ย")], []),
 (14, 6, "Medium shot, static camera", ["somchai"], "shop", "late morning",
  "sets a bowl down in front of a regular and straightens up, wiping his hands on the apron",
  [("somchai","pleased but weary","ขอบคุณครับ แวะมาเรื่อยๆนะครับ"),
   ("somchai","warm","พรุ่งนี้มีต้มยำด้วยนะ")], []),

 (15, 8, "Close-up, slow push-in", ["ton"], "stairs", "late morning",
  "stands alone in the back stairwell reading his phone, the shop noise muffled behind the wall, the screen angled away from camera and never legible",
  [("ton","reading aloud, flat","ขอบคุณที่ให้ความสนใจ แต่ตำแหน่งนี้เต็มแล้ว"),
   ("ton","to himself","...อีกแล้ว")], []),
 (16, 6, "Close-up, static camera", ["ton"], "stairs", "late morning",
  "lowers the phone and leans his head back against the stairwell wall",
  [("ton","quiet, resigned","ที่นี่ก็ไม่รับ สามที่แล้วเดือนนี้"),
   ("ton","to himself, flat","เรียนมาสี่ปี ทำไมมันยากขนาดนี้")], []),
 (17, 6, "Medium shot, static camera", ["ton"], "shop", "late morning",
  "steps back in from the stairwell pocketing the phone, face forced neutral, and answers the room",
  [("ton","level, face not matching","มาแล้วครับ คิดเงินโต๊ะสามใช่ไหมครับ")], []),
 (18, 8, "Medium two-shot, static camera", ["somchai","ton"], "shop", "late morning",
  "looks up from the wok as his son comes back in, reads his face in one look, then lets it go",
  [("somchai","careful","ต้น... มีอะไรหรือเปล่าลูก"),
   ("ton","quick, deflecting","ไม่มีอะไรพ่อ ร้อนน่ะ"),
   ("somchai","not pressing","อือ")], []),

 (19, 4, "Medium shot, static camera, from the landing above", ["ton"], "stairs", "early afternoon",
  "climbs the stairs carrying a covered bowl of rice porridge on a tray, looking up toward the bedroom door",
  [("ton","calling ahead","ย่าครับ ต้นเองครับ ขึ้นมาแล้วนะครับ")], []),
 (20, 10, "Medium two-shot, static camera", ["ton","ya"], "room", "early afternoon",
  "sits at the bedside and spoons porridge toward the old woman propped on her pillows",
  [("ton","soft","วันนี้ย่าดูสดใสนะครับ กินข้าวต้มก่อนนะครับ"),
   ("ya","running out of air","...ต้น..."),
   ("ton","tender","ครับย่า อ้าปากหน่อยครับ")], ["ya"]),
 (21, 8, "Medium two-shot, static camera", ["ton","ya"], "room", "early afternoon",
  "wipes the corner of her mouth with a cloth, then glances at the gaps in the floorboards",
  [("ton","deliberately cheerful","ข้างล่างเสียงดังไปไหมครับย่า"),
   ("ya","barely audible","...ได้ยิน... หมด..."),
   ("ton","half laughing","งั้นย่าก็รู้หมดเลยสิครับ")], ["ya"]),
 (22, 8, "Close-up two-shot, static camera, her hand and the bed rail in frame", ["ya","ton"], "room", "early afternoon",
  "her thin fingers close on his sleeve as he starts to rise; her other hand rests on the bed's wooden side rail, fingertips on the dense little scratches cut into it, and neither of them looks at it",
  [("ya","straining, halting","...ต้น... ย่า..."),
   ("ton","stopping, gentle","ย่าจะบอกอะไรผมเหรอครับ"),
   ("ya","trailing off","...ไม่... ไม่มีอะไร...")], ["ya"]),
 (23, 6, "Medium shot, static camera", ["ton","ya"], "room", "early afternoon",
  "eases his sleeve free, pats her hand, and gathers the empty bowl",
  [("ton","tender","เดี๋ยวผมขึ้นมาใหม่นะครับย่า พักก่อนนะครับ")], ["ya"]),

 (24, 10, "Medium shot, static camera, his face in frame above the counter", ["somchai"], "shop", "afternoon lull",
  "sits alone at the back counter with nothing on it but a glass of water, counting off costs on his fingers, lips moving",
  [("somchai","muttering, working through it","ค่าเส้น ค่าหมู ค่าน้ำแข็ง แล้วก็ค่าแก๊ส"),
   ("somchai","counting","วันนี้ได้มาสามพันสอง เหลือเท่านี้"),
   ("somchai","firm with himself","อันนี้แยกไว้เป็นค่ารักษาแม่เดือนนี้นะ")], []),
 (25, 8, "Close-up, static camera", ["somchai"], "shop", "afternoon lull",
  "begins to separate a third, smaller fold and stops, then tucks it aside without finishing the sentence",
  [("somchai","trailing off","แล้วอันนี้..."),
   ("somchai","flat, closing it off","เก็บไว้ก่อน วันพฤหัสค่อยว่ากัน")], ["money"]),
 (26, 8, "Medium two-shot, static camera", ["ton","somchai"], "shop", "afternoon lull",
  "leans in the doorway to the back counter watching the older man, who does not stop what he is doing",
  [("ton","casual","พ่อนับเงินอยู่เหรอ"),
   ("somchai","quick","เปล่า เช็คยอดเฉยๆ"),
   ("ton","half-teasing","มีเก็บเยอะขนาดนี้เลยเหรอพ่อ")], ["money"]),
 (27, 6, "Close-up, static camera", ["somchai"], "shop", "afternoon lull",
  "smiles without looking up and closes the drawer",
  [("somchai","deflecting, through a smile","เยอะที่ไหนล่ะ พอค่าเส้นพรุ่งนี้ก็หมดแล้ว")], ["money"]),

 (28, 8, "Medium shot, static camera", ["wit"], "shop", "late afternoon",
  "steps in off the street, turns the stool before he sits so that he faces the open shutter, and settles with the bag still on his shoulder",
  [("wit","easy, familiar","ลุงครับ เส้นเล็กน้ำใสเหมือนเดิมครับ"),
   ("wit","conversational","วันนี้คนเยอะนะครับลุง")], []),
 (29, 8, "Medium two-shot across the counter, static camera", ["somchai","wit"], "shop", "late afternoon",
  "answers from the wok without looking up and without pausing his hands, then holds a flat palm low beside his hip showing a height",
  [("somchai","matter-of-fact","ไม่ใส่ถั่วงอกใช่ไหมวิทย์"),
   ("wit","smiling","ลุงจำได้ทุกทีเลย"),
   ("somchai","unhurried","ก็กินมาตั้งแต่ตัวเท่านี้")], ["nosubs"]),
 (30, 10, "Medium two-shot at the counter, static camera", ["wit","somchai"], "shop", "late afternoon",
  "stands with a worn wallet half open while the older man waves it off without looking at it",
  [("wit","polite","เท่าไหร่ครับลุง"),
   ("somchai","waving it away","เอาไว้ก่อน วันหลังค่อยจ่าย"),
   ("wit","half laughing","ลุงพูดแบบนี้ทุกทีนะครับ"),
   ("somchai","unbothered","ก็จริงทุกที")], []),
 (31, 8, "Medium two-shot, static camera, both faces in frame above the counter", ["wit","somchai"], "shop", "late afternoon",
  "sets a small fold of banknotes down on the counter, backs of the notes upward and a hand still covering them, as the older man's hand is already moving toward it",
  [("wit","insisting gently","ผมวางไว้ตรงนี้นะลุง"),
   ("somchai","flat and final","วิทย์ เอาคืนไป"),
   ("wit","one more try","ลุงครับ...")], ["money"]),
 (32, 8, "Close-up, static camera, his face and his hand both in frame", ["somchai"], "shop", "late afternoon",
  "pushes the covered fold back across the counter and holds it there until it is taken",
  [("somchai","not angry, not negotiating","เอาคืนไป ลุงไม่รับหรอก"),
   ("somchai","warm","วิทย์กินให้อร่อยก็พอแล้ว ลุงพอใจแล้ว")], ["money"]),
 (33, 10, "Medium two-shot, static camera", ["ton","somchai"], "shop", "late afternoon",
  "watches the empty street doorway where someone has just left, then turns to the older man who is already wiping down the counter",
  [("ton","curious","พ่อไม่เคยเก็บตังค์พี่วิทย์เลยใช่ไหม"),
   ("somchai","without stopping","ตั้งแต่เขายังไม่สูงเท่าเคาน์เตอร์"),
   ("ton","half amazed","ยี่สิบปีเลยนะพ่อ")], []),
 (34, 6, "Close-up, static camera", ["somchai"], "shop", "late afternoon",
  "keeps wiping the counter, not looking up, as if the question were not worth stopping for",
  [("somchai","matter-of-fact","ก็แค่ก๋วยเตี๋ยวชามเดียวลูก"),
   ("somchai","quiet","ไม่เห็นต้องจดไว้")], []),
]

# «บัญชี» — องก์ 1 · ช็อต 1–48 · 0:00–6:24

Omni 1.1 Flash · 9:16 · 8 วินาทีทุกช็อต · **720p ตอนยิงจริง · 360p ตอนทดสอบ**
โหมด **องค์ประกอบ** เสมอ (เสียงผูกกับตัวละครแล้ว ใช้โหมดเฟรมไม่ได้)

## กฎที่ใช้กับทุกช็อตในไฟล์นี้

1. **ATTACH ORDER คือความจริง** ใส่ chip ตามลำดับที่เขียนไว้เท่านั้น แล้ว**ดูแถว thumbnail
   เทียบกับ prompt ก่อนกด Submit ทุกครั้ง** — prompt คือสิ่งที่เราเชื่อ แถว thumbnail คือสิ่งที่จริง
2. **หน้าตาต้องเขียนเป็นข้อความเสมอ** ต่อให้แนบ chip แล้ว — prompt ชนะรูป สิ่งที่ไม่พูดถึงจะถูกเปลี่ยนเงียบๆ
3. **ห้ามแนบ voice chip** เสียงผูกกับตัวละครแล้ว แนบตัวละคร = ได้เสียงนั้นมาด้วย
4. **ไม่มีคำว่า "No music."** Google บอกให้บรรยายสิ่งที่อยากได้ ไม่ใช่สั่งห้าม
5. ตัวหนังสือที่ต้องอ่านออก **ต้องเขียนคำนั้นลง prompt ในเครื่องหมายคำพูด** (พิสูจน์แล้ว) ที่ไม่ได้เขียน = โมเดลแต่งเอง
6. **ทุกช็อตมีบทพูด** ไม่มีข้อยกเว้น — `python3 tools/shotsheet_lint.py` ต้อง PASS ก่อนใช้เครดิตแม้แต่หน่วยเดียว
7. **คนพูดต้องถูกแนบเป็น chip เสมอ** แม้อยู่นอกจอ — ไม่แนบ = เสียงสุ่ม ไม่ใช่เสียงที่ล็อกไว้
8. **พูดตรง ไม่ให้คนดูตีความ** — `"โดนปฏิเสธอีกแล้ว"` ไม่ใช่ `"...อีกแล้ว"`
9. **ใครอยู่ในระยะได้ยินบ้าง** — ก่อนให้ตัวละครพูดความลับ ถามว่าอีกคนในฉากได้ยินไหม ถ้าไม่ควรได้ยิน ย้ายเขาออกไปก่อน

## บล็อกหน้าตา — คัดลอกจากที่นี่เท่านั้น ห้ามเขียนจากความจำ

- **สมชาย** `a Thai man of 58, lean, with a weathered square face, short greying black hair, deep-set brown eyes and light stubble, wearing a faded dark-blue cotton shopkeeper's apron over a plain white short-sleeved shirt and a worn leather watch on his left wrist`
- **ต้น** `a Thai man of 24, slim, oval-faced, with thick black hair swept back, dark brown eyes, clean-shaven, in a plain grey short-sleeved polo shirt and a thin silver chain`
- **ย่าประนอม** `a frail Thai woman of 79, thin, with silver-white hair cropped short and thinning at the temples, deeply wrinkled papery skin, sunken cheeks and cloudy but alert dark eyes, in a faded floral-print cotton nightgown, propped on two stacked pillows, a thin nasal cannula looped over her ears and a small brass amulet on a string at her neck`
- **วิทย์** `medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist`
  *(อ่านจากรูปจริงที่ worker สร้าง ไม่ได้เดา — รูปยังมีแขนกอดอกและพื้นหลังไล่เฉด ซึ่งไม่ได้สั่ง แต่ไม่ต้องเขียนลง prompt ช็อต เพราะท่าทางเปลี่ยนทุกช็อตอยู่แล้ว)*
- **ร้าน** `a narrow Bangkok shophouse ground floor turned noodle shop: five worn wooden tables with mismatched plastic stools, a stainless-steel soup cart with a steaming broth pot against the left wall, an open roll-up shutter onto a busy street, a narrow wooden staircase at the back, bare bulbs strung overhead, walls stained pale yellow with age`

**STYLE** (ต่อท้ายทุก prompt) `Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.`

---

## ฉาก A — ก่อนรุ่งสาง ข้างตึก (ช็อต 1–2)

### SHOT 1 · 0:00–0:08 · Medium · handheld sway
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@side_wall`→REF_1
**บทพูด** สมชาย `"ผมหาให้ครับ...พรุ่งนี้"` — เค้น เจ็บ
```
Use <IMAGE_REF_0> as the character reference for the man's face, hair and build.
Use <IMAGE_REF_1> as the location reference for the wall and the alley.

A Thai man of 58 <IMAGE_REF_0>, lean, weathered square face, short greying black
hair, light stubble, in a faded dark-blue apron over a white short-sleeved shirt,
is shoved hard against the rough concrete side wall of a shophouse <IMAGE_REF_1>,
his body jolting against it, an arm from off-frame doing the shoving. Just before
dawn, nobody else in sight. Near-total darkness lit only by a distant streetlamp,
a harsh side shadow across his face.
Winded, he speaks Thai and says: "ผมหาให้ครับ...พรุ่งนี้" — forced out against the pain.


Medium shot, static camera with a slight handheld sway.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a dull impact thud, late-night traffic humming far off.
```

### SHOT 2 · 0:08–0:16 · Close-up · low angle, static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@side_wall`→REF_1
**บทพูด** สมชาย `"...พรุ่งนี้จริงๆ"` — แผ่ว พูดกับความมืด
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the wall and wet pavement.

The same Thai man of 58 <IMAGE_REF_0> slides down the wall <IMAGE_REF_1> into a
crouch, breathing hard, as a folded envelope drops out of frame and lands in a
shallow puddle beside his feet. Just before dawn. One distant streetlamp, deep
shadow, wet pavement catching the light.
He speaks Thai, barely audible, to nobody: "...พรุ่งนี้จริงๆ".


Close-up, static camera at a low angle.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the envelope hitting wet pavement, footsteps retreating and fading.
```

## ฉาก B — ชั้นบน ห้องย่า (ช็อต 3–8)

### SHOT 3 · 0:16–0:24 · Medium · handheld, follow from behind
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@staircase`→REF_1
**บทพูด** สมชาย `"เบาๆ...เบาๆ"` — กระซิบกับตัวเอง
```
Use <IMAGE_REF_0> as the character reference for the man's face, hair and clothing.
Use <IMAGE_REF_1> as the location reference for the staircase and stairwell.

A Thai man of 58 <IMAGE_REF_0> in a dark-blue apron over a white shirt climbs a
narrow wooden staircase <IMAGE_REF_1> in bare feet, a small cloth pouch in one
hand, placing each foot carefully so the steps do not creak. Just before dawn. A
single dim bulb above, the rest of the house dark.
He murmurs to himself in Thai: "เบาๆ...เบาๆ", coaching his own feet.


Medium shot, handheld, following from behind.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: bare feet on wood, the house completely still.
```

### SHOT 4 · 0:24–0:32 · Medium · static  ★ FINDING 1 — ปลูกขอบเตียงครั้งที่ 1
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@grandma_pranom`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** สมชาย `"เม็ดนี้ก่อนนอน เม็ดนี้ตอนเช้า"` — ทบทวนความจำ
> รอยขีดอยู่หลังมือพ่อ เบลอ ไม่มีใครมอง **ห้ามโฟกัส ห้ามพูดถึง** — คนดูต้องรู้สึกตอนองก์ 5 ว่า "เห็นมาตลอดแต่ไม่ได้มอง"
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the character reference for the old woman's face and hair.
Use <IMAGE_REF_2> as the location reference for the bedroom and its furniture.

A Thai man of 58 <IMAGE_REF_0> sits at a bedside in a small upstairs bedroom
<IMAGE_REF_2> and sets small pill bottles out on a tray, careful and practiced.
His free hand rests on the bed's wooden side rail; behind his fingers the rail is
covered in dense little scratches, soft and out of focus, and nobody looks at
them. In
the bed a frail Thai woman of 79 <IMAGE_REF_1>, silver-white hair cropped short,
deeply wrinkled skin, a thin nasal cannula looped over her ears, stirs and wakes
slowly. Just before dawn, dim lamp light, the curtains still dark.
He speaks Thai quietly as he sets them out, reciting the schedule to himself: "เม็ดนี้ก่อนนอน เม็ดนี้ตอนเช้า".


Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a pill bottle set on a tray, a ceiling fan creaking.
```

### SHOT 5 · 0:32–0:40 · Close-up · static — **ย่าประนอม พูด**
**ATTACH** 1) `@grandma_pranom`→REF_0 · 2) `@upstairs_bedroom`→REF_1
**บทพูด** ย่าประนอม `"...ลูก..."` — แผ่ว จำได้
```
Use <IMAGE_REF_0> as the character reference for the old woman's face, hair and
nightgown. Use <IMAGE_REF_1> as the location reference for the bedroom.

A frail Thai woman of 79 <IMAGE_REF_0>, sunken cheeks, cloudy but alert dark eyes,
a thin nasal cannula over her ears, lies propped on two pillows in a small
upstairs bedroom <IMAGE_REF_1>. Her eyes focus slowly on someone beside the bed,
recognition arriving, her lips parting around one weak word. She speaks Thai and
says: "...ลูก..." — faint, recognising.
Just before dawn, dim lamp light.

Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: her breath, the ceiling fan creaking.
```

### SHOT 6 · 0:40–0:48 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@grandma_pranom`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** สมชาย `"เดี๋ยวพรุ่งนี้พาไปหาหมอนะแม่"` — นุ่ม ปลอบ
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the character reference for the old woman.
Use <IMAGE_REF_2> as the location reference for the bedroom.

A Thai man of 58 <IMAGE_REF_0>, short greying hair, light stubble, in a dark-blue
apron over a white shirt, pulls a blanket up over the shoulders of a frail Thai
woman of 79 <IMAGE_REF_1> in a small upstairs bedroom <IMAGE_REF_2>. He speaks
Thai, low and reassuring, and says: "เดี๋ยวพรุ่งนี้พาไปหาหมอนะแม่".
Just before dawn, dim lamp light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a blanket drawn up, slow breathing.
```

### SHOT 7 · 0:48–0:56 · Close-up · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@upstairs_bedroom`→REF_1
**บทพูด** สมชาย `"สี่สิบ...ห้าสิบ...หกสิบ"` — นับเบาๆ ใต้ลมหายใจ
```
Use <IMAGE_REF_0> as the character reference for the man's hands and sleeves.
Use <IMAGE_REF_1> as the location reference for the bedside table.

The hands of a Thai man of 58 <IMAGE_REF_0>, sleeves of a white shirt rolled back
under a dark-blue apron, count a small stack of coins and worn banknotes into a
soft cloth pouch at a bedside in an upstairs bedroom <IMAGE_REF_1>, then add two
more folded notes taken from his own shirt pocket. No writing or numbers visible
anywhere. Just before dawn, dim lamp light.
He counts under his breath in Thai as the coins go in: "สี่สิบ...ห้าสิบ...หกสิบ".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: coins and paper counted softly.
```

### SHOT 8 · 0:56–1:04 · Close-up · static  ⟵ **จุดโฆษณา 1:00**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@upstairs_bedroom`→REF_1
**บทพูด** สมชาย `"เดือนนี้...ไม่พออีกแล้ว"` — เรียบ พูดกับตัวเอง ย่าได้ยิน (ตั้งใจ)
```
Use <IMAGE_REF_0> as the character reference for the man's face.
Use <IMAGE_REF_1> as the location reference for the bedroom doorway behind him.

A Thai man of 58 <IMAGE_REF_0>, weathered square face, deep-set brown eyes, light
stubble, exhales slowly in an upstairs bedroom <IMAGE_REF_1> and glances toward
the doorway that leads down to the shop, doing arithmetic nobody else can see.
Just before dawn, dim lamp light.
He lets the breath out and says quietly in Thai, to himself: "เดือนนี้...ไม่พออีกแล้ว".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the ceiling fan creaking, the street beginning to wake below.
```

## ฉาก C — เปิดร้าน (ช็อต 9–20)

### SHOT 9 · 1:04–1:12 · Wide · slow pan L→R
**ATTACH** 1) `@noodle_shop`→REF_0 · 2) `@lung_somchai`→REF_1
**บทพูด** สมชาย `"เปิดแล้วครับ"` — ร้องบอกถนน
```
Use <IMAGE_REF_0> as the location reference for the shop, its tables, soup cart
and shutter. Use <IMAGE_REF_1> as the character reference for the man's hand,
arm and apron.

A roll-up shutter is pulled open by the hand of a Thai man of 58 <IMAGE_REF_1>
inside a narrow Bangkok noodle shop <IMAGE_REF_0>, the last foot lifted with a wince quickly smoothed over.
Morning light floods in; steam is already rising from the broth pot on the cart.
Early morning, warm low sun angling through the doorway, soft haze in the air.
A Thai man of 58 <IMAGE_REF_1> in a dark-blue apron calls out to the street in Thai as the shutter goes up: "เปิดแล้วครับ".


Wide shot, slow pan left to right.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the shutter chain rattling upward, birds outside.
```

### SHOT 10 · 1:12–1:20 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"สวัสดีครับ นั่งได้เลยครับ"` — อบอุ่นแต่เหนื่อย
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the shop interior.

A Thai man of 58 <IMAGE_REF_0> in a faded dark-blue apron over a white
short-sleeved shirt gestures a customer toward an empty table inside his noodle
shop <IMAGE_REF_1> with an open palm, smiling. He speaks Thai, warm but tired, and
says: "สวัสดีครับ นั่งได้เลยครับ". The smile catches for one frame as he turns back
toward the kitchen, a hand brushing his side, then it is gone. Mid-morning, warm
daylight through the open shutter.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a chair scraping the floor, broth simmering.
```

### SHOT 11 · 1:20–1:28 · Medium · static — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"ส่งใบสมัครไปอีกสองที่เมื่อคืน ยังไม่มีใครติดต่อกลับเลยพ่อ"` — เหนื่อย แต่ยังหวัง
```
Use <IMAGE_REF_0> as the character reference for the young man's face and hair.
Use <IMAGE_REF_1> as the location reference for the shop counter behind him.

A Thai man of 24 <IMAGE_REF_0>, slim, oval face, thick black hair swept back,
clean-shaven, in a plain grey short-sleeved polo shirt and a thin silver chain,
ties his apron strings behind his back at the counter of a noodle shop
<IMAGE_REF_1>, speaking across it to his father. He speaks Thai, tired but trying
to sound light, and says: "ส่งใบสมัครไปอีกสองที่เมื่อคืน ยังไม่มีใครติดต่อกลับเลยพ่อ".
Mid-morning, warm daylight.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: apron strings pulled tight, the shop waking around them.
```

### SHOT 12 · 1:28–1:36 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@nong_daeng`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** สมชาย `"ใจเย็นๆ ของแบบนี้ต้องรอ"` — อบอุ่น ปลอบ
```
Use <IMAGE_REF_0> as the character reference for the older man's face and clothing.
Use <IMAGE_REF_1> as the character reference for the young man beside him.
Use <IMAGE_REF_2> as the location reference for the shop counter.

A Thai man of 58 <IMAGE_REF_0> in a dark-blue apron sets down a ladle at the
counter of his noodle shop <IMAGE_REF_2> and glances at his son, a Thai man of 24
<IMAGE_REF_1> in a grey polo shirt, with a small warm reassurance. He speaks Thai
and says: "ใจเย็นๆ ของแบบนี้ต้องรอ". Mid-morning, warm daylight.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a ladle set down against the counter.
```

### SHOT 13 · 1:36–1:44 · Close-up · rack focus ladle→bowl
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"สองชามครับ"` — ตอบรับออเดอร์
```
Use <IMAGE_REF_0> as the character reference for the young man's hands and sleeves.
Use <IMAGE_REF_1> as the location reference for the counter and soup pot.

The hands of a Thai man of 24 <IMAGE_REF_0> in a grey polo shirt ladle hot broth
from a steaming pot into a ceramic bowl behind the counter of a noodle shop
<IMAGE_REF_1>. Mid-morning, warm daylight, steam catching the light.
He calls back over his shoulder in Thai: "สองชามครับ".


Close-up, static camera with a rack focus from the ladle to the bowl.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the ladle scraping metal, steam hissing.
```

### SHOT 14 · 1:44–1:52 · Medium · slight handheld — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"เส้นเล็กหรือเส้นใหญ่ครับ"` — สุภาพ
```
Use <IMAGE_REF_0> as the character reference for the young man's face and hair.
Use <IMAGE_REF_1> as the location reference for the tables and shutter.

A Thai man of 24 <IMAGE_REF_0>, thick black hair swept back, in a grey polo shirt
under an apron, leans toward a seated customer inside a noodle shop <IMAGE_REF_1>
with a small notepad in hand. He speaks Thai, politely, and says:
"เส้นเล็กหรือเส้นใหญ่ครับ". His phone buzzes once in his apron pocket and a flicker
crosses his face before he refocuses on the customer. Mid-morning, warm daylight.

Medium shot, slight handheld movement.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: one muffled phone buzz, kitchen clatter.
```

### SHOT 15 · 1:52–2:00 · Close-up · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"หมูหมดแล้วนะ เดี๋ยวสั่งเพิ่ม"` — พูดกับตัวเอง ไม่หยุดมือ
```
Use <IMAGE_REF_0> as the character reference for the man's hands, forearms and brow.
Use <IMAGE_REF_1> as the location reference for the counter.

The hands of a Thai man of 58 <IMAGE_REF_0> chop roasted pork on a worn wooden
board behind the counter of a noodle shop <IMAGE_REF_1>, sweat on his brow, eyes
fixed on the blade. Mid-morning, warm daylight, wok steam drifting through frame.
Without stopping the knife he says in Thai: "หมูหมดแล้วนะ เดี๋ยวสั่งเพิ่ม".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the knife tapping the board, the wok hissing.
```

### SHOT 16 · 2:00–2:08 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ต้น เก็บโต๊ะสองทีนึง"` — ห้วนๆ สั่งงาน
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the counter and dining area.

A Thai man of 58 <IMAGE_REF_0> in a dark-blue apron calls out over his shoulder
toward the dining area of his noodle shop <IMAGE_REF_1> without looking up, one
hand still stirring a pot. He speaks Thai, brisk, and says: "ต้น เก็บโต๊ะสองทีนึง".
Mid-morning, warm daylight.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: dishes clattering, street murmur through the shutter.
```

### SHOT 17 · 2:08–2:16 · Medium · handheld — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"พ่อสั่งงานเก่งกว่าใครในซอยเลยนะเนี่ย"` — ทีเล่นทีจริง รักพ่อ
```
Use <IMAGE_REF_0> as the character reference for the young man's face and hair.
Use <IMAGE_REF_1> as the location reference for the tables.

A Thai man of 24 <IMAGE_REF_0> in a grey polo shirt stacks empty chairs onto a
table inside a noodle shop <IMAGE_REF_1>, calling back with a tired, wry
half-smile. He speaks Thai and says: "พ่อสั่งงานเก่งกว่าใครในซอยเลยนะเนี่ย".
Mid-morning, warm daylight.

Medium shot, handheld.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: chair legs set down on a tabletop.
```

### SHOT 18 · 2:16–2:24 · Medium two-shot · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@nong_daeng`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** สมชาย `"อย่าลืมเติมน้ำซุปด้วยนะ"` — เรียบๆ งานประจำ
```
Use <IMAGE_REF_0> as the character reference for the older man.
Use <IMAGE_REF_1> as the character reference for the younger man.
Use <IMAGE_REF_2> as the location reference for the counter.

A Thai man of 58 <IMAGE_REF_0> pours broth into a large pot behind the counter of
a noodle shop <IMAGE_REF_2> while speaking to a Thai man of 24 <IMAGE_REF_1>
stacking bowls beside him. He speaks Thai, matter-of-fact, and says:
"อย่าลืมเติมน้ำซุปด้วยนะ". Mid-morning, warm daylight, steam rising between them.

Medium two-shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: broth pouring, kitchen clatter.
```

### SHOT 19 · 2:24–2:32 · Wide · static, deep focus
**ATTACH** 1) `@street_front`→REF_0
**บทพูด** เสียงรถเข็นนอกจอ `"ขนมจีบ ซาลาเปา!"` — เสียงประกาศจากรถเข็น ไม่เห็นตัว *(ไม่ใช่ตัวละคร ไม่ต้องล็อกเสียง เสียงสุ่มถูกต้องแล้ว)*
```
Use <IMAGE_REF_0> as the location reference for the street, shopfronts and cables.

Motorbikes and a street-food cart pass along a narrow Bangkok street
<IMAGE_REF_0> in front of an open shophouse shutter, the morning crowd moving
past. Mid-morning, bright open daylight. Any faces are distant and out of focus.
A vendor's recorded call carries in from off-frame in Thai: "ขนมจีบ ซาลาเปา!".


Wide shot, static camera, deep focus.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: motorbike engines, a vendor's cart bell.
```

### SHOT 20 · 2:32–2:40 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ขอบคุณครับ แวะมาเรื่อยๆนะ"` — พอใจ แต่ล้า
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the tables.

A Thai man of 58 <IMAGE_REF_0> sets a bowl down in front of a seated regular
inside his noodle shop <IMAGE_REF_1>, nodding at something the customer just said,
a small pleased smile crossing his tired face. He speaks Thai and says:
"ขอบคุณครับ แวะมาเรื่อยๆนะ". Late morning, warm daylight, soft shadow.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a bowl set on wood, background chatter.
```

## ฉาก D — ลูกปิดข่าวร้าย (ช็อต 21–25)

### SHOT 21 · 2:40–2:48 · Close-up · static
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"เดี๋ยวครับ"` — ตอบลูกค้าโดยไม่เงยหน้า
```
Use <IMAGE_REF_0> as the character reference for the young man's hand and sleeve.
Use <IMAGE_REF_1> as the location reference for the table and shop.

The hand of a Thai man of 24 <IMAGE_REF_0> wipes down a table with a damp rag
inside a noodle shop <IMAGE_REF_1>, his eyes flicking toward a faint glow coming
from his apron pocket. Late morning, warm daylight.
Without looking up he answers a customer in Thai: "เดี๋ยวครับ".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the rag dragging on wood, a muffled phone buzz.
```

### SHOT 22 · 2:48–2:56 · Close-up · slow push-in  ★ ย้ายออกนอกระยะได้ยินของพ่อ
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@staircase`→REF_1
**บทพูด** ต้น `"โดนปฏิเสธอีกแล้ว...เฮ้อ ที่นี่ก็ไม่รับ"` — พูดกับตัวเอง ตรงๆ ไม่ต้องตีความ
> อยู่ที่บันไดหลังร้าน **พ่อไม่ได้ยิน** — ถ้าพูดในร้าน ช็อต 23 ที่ลูกปิดข่าวจะพังทันที
```
Use <IMAGE_REF_0> as the character reference for the young man's face.
Use <IMAGE_REF_1> as the location reference for the stairwell behind him.

A Thai man of 24 <IMAGE_REF_0>, thick black hair swept back, in a grey polo shirt
under an apron, has stepped out of the shop into the narrow back stairwell
<IMAGE_REF_1> to read something on the phone cupped in his hand, out of sight and
earshot of the shop. His face falls, his jaw tightens, his eyes lower. The screen
is angled away from camera and never legible. Late morning, the stairwell's
single bulb, shop noise muffled behind him.

Alone, he says it out loud in Thai, flatly, to himself: "โดนปฏิเสธอีกแล้ว...เฮ้อ
ที่นี่ก็ไม่รับ".

Close-up, slow push-in.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: shop noise muffled through a wall, the phone screen clicking off.
```

### SHOT 23 · 2:56–3:04 · Close-up · static  ⟵ **จุดโฆษณา 3:00**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"ได้ครับ กำลังไป"` — เสียงปกติ หน้าไม่ปกติ
```
Use <IMAGE_REF_0> as the character reference for the young man's face and hand.
Use <IMAGE_REF_1> as the location reference for the counter.

A Thai man of 24 <IMAGE_REF_0> steps back in from the rear stairwell into the
noodle shop <IMAGE_REF_1>, pocketing the phone as he comes, and forces his face
neutral as a customer calls for the bill. He does not look toward his father. The screen is never legible. Late morning, warm daylight.
He answers the room in Thai, voice level and face not: "ได้ครับ กำลังไป".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a phone screen going dark, a dish set down nearby.
```

### SHOT 24 · 3:04–3:12 · Close-up · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ต้น...ไม่มีอะไร"` — เริ่มจะถาม แล้วเปลี่ยนใจ
```
Use <IMAGE_REF_0> as the character reference for the man's face.
Use <IMAGE_REF_1> as the location reference for the wok station.

A Thai man of 58 <IMAGE_REF_0>, deep-set brown eyes, light stubble, glances up
from the wok in his noodle shop <IMAGE_REF_1> as his son comes back in from out
the back, reads the changed face in one look, and lowers his eyes to his work. Late
morning, warm daylight, wok steam rising past his face.
He starts to speak in Thai, gets one word out and changes his mind: "ต้น...ไม่มีอะไร".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the wok sizzling under him.
```

### SHOT 25 · 3:12–3:20 · Wide · locked off
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@nong_daeng`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** ต้น `"เดี๋ยวผมเอาข้าวไปให้ย่านะพ่อ"` — เรียบ ไม่มองหน้า
```
Use <IMAGE_REF_0> as the character reference for the older man.
Use <IMAGE_REF_1> as the character reference for the younger man.
Use <IMAGE_REF_2> as the location reference for the counter and shop.

A Thai man of 58 <IMAGE_REF_0> and a Thai man of 24 <IMAGE_REF_1> work at opposite
ends of the counter of a noodle shop <IMAGE_REF_2> without speaking, steam
drifting in the space between them. Late morning, warm daylight through the
shutter.
The younger man <IMAGE_REF_1> says in Thai, without looking across: "เดี๋ยวผมเอาข้าวไปให้ย่านะพ่อ".


Wide shot, locked-off camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: steam hissing, distant traffic.
```

## ฉาก E — ป้อนข้าวย่า (ช็อต 26–33)

### SHOT 26 · 3:20–3:28 · Medium · handheld, follow from behind
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@staircase`→REF_1
**บทพูด** ต้น `"ย่าครับ ต้นเองครับ"` — ร้องบอกล่วงหน้า
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the location reference for the staircase.

A Thai man of 24 <IMAGE_REF_0> in a grey polo shirt climbs a narrow wooden
staircase <IMAGE_REF_1> carrying a covered bowl of rice porridge on a small tray.
Early afternoon, dim light from a single bulb above.
He calls ahead up the stairs in Thai: "ย่าครับ ต้นเองครับ".


Medium shot, handheld, following from behind.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: footsteps on creaking wood, a bowl clinking faintly.
```

### SHOT 27 · 3:28–3:36 · Medium · static — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@grandma_pranom`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** ต้น `"ย่า กินข้าวก่อนนะครับ"` — เบา อ่อนโยน
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the character reference for the old woman.
Use <IMAGE_REF_2> as the location reference for the bedroom.

A Thai man of 24 <IMAGE_REF_0> sits at a bedside in a small upstairs bedroom
<IMAGE_REF_2>, spooning porridge gently toward a frail Thai woman of 79
<IMAGE_REF_1> propped against pillows, a thin nasal cannula over her ears. He
speaks Thai, softly, and says: "ย่า กินข้าวก่อนนะครับ". Early afternoon, soft light
through a thin curtain.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a spoon against a ceramic bowl.
```

### SHOT 28 · 3:36–3:44 · Close-up · static
**ATTACH** 1) `@grandma_pranom`→REF_0 · 2) `@upstairs_bedroom`→REF_1 · 3) `@nong_daeng`→REF_2 *(นอกจอ แต่ต้องแนบเพื่อให้ได้เสียง Iapetus)*
**บทพูด** ต้น `"วันนี้ย่าดูสดใสนะครับ"` — อ่อนโยน จากนอกจอ
```
Use <IMAGE_REF_0> as the character reference for the old woman's face and eyes.
Use <IMAGE_REF_1> as the location reference for the bedroom.

A frail Thai woman of 79 <IMAGE_REF_0>, silver-white hair, deeply wrinkled papery
skin, cloudy but alert dark eyes, lies in a small upstairs bedroom <IMAGE_REF_1>.
Her eyes track slowly across the room, alert but unable to form clear words, her
lips parting slightly. Early afternoon, soft filtered light.
From just off-frame her grandson <IMAGE_REF_2> says in Thai: "วันนี้ย่าดูสดใสนะครับ".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the ceiling fan creaking.
```

### SHOT 29 · 3:44–3:52 · Close-up · slow push-in — **ย่าประนอม พูด**
**ATTACH** 1) `@grandma_pranom`→REF_0 · 2) `@upstairs_bedroom`→REF_1
**บทพูด** ย่าประนอม `"...ต้น..."` — สั่น เค้น
```
Use <IMAGE_REF_0> as the character reference for the old woman's face and hands.
Use <IMAGE_REF_1> as the location reference for the bed and sheets.

A frail Thai woman of 79 <IMAGE_REF_0> strains to speak in a small upstairs
bedroom <IMAGE_REF_1>, her mouth trembling around a single syllable, her hand
twitching against the bedsheet. She speaks Thai, straining, and says: "...ต้น...".
Early afternoon, soft filtered light.

Close-up, slow push-in.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the fan creaking, faint shop noise rising from below.
```

### SHOT 30 · 3:52–4:00 · Medium · static — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@grandma_pranom`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** ต้น `"อร่อยไหมครับย่า"` — อ่อนโยน
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the character reference for the old woman.
Use <IMAGE_REF_2> as the location reference for the bedroom.

A Thai man of 24 <IMAGE_REF_0> smiles gently and wipes a drop from the corner of
the mouth of a frail Thai woman of 79 <IMAGE_REF_1> with a cloth, in a small
upstairs bedroom <IMAGE_REF_2>. He speaks Thai, tenderly, and says:
"อร่อยไหมครับย่า". Early afternoon, soft filtered light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a spoon set down, quiet breathing.
```

### SHOT 31 · 4:00–4:08 · Close-up · slow tilt down
**ATTACH** 1) `@grandma_pranom`→REF_0 · 2) `@upstairs_bedroom`→REF_1 · 3) `@nong_daeng`→REF_2 *(นอกจอ แต่ต้องแนบเพื่อให้ได้เสียง Iapetus)*
**บทพูด** ต้น `"ข้างล่างเสียงดังไปไหมครับย่า"` — ถามเบาๆ
```
Use <IMAGE_REF_0> as the character reference for the old woman's face and gaze.
Use <IMAGE_REF_1> as the location reference for the floorboards under the bed.

The gaze of a frail Thai woman of 79 <IMAGE_REF_0> drifts downward in a small
upstairs bedroom <IMAGE_REF_1>, fixing on a narrow gap between the wooden
floorboards beneath her bed. Early afternoon, soft filtered light, a sliver of
light rising through the gap.
Off-frame, her grandson <IMAGE_REF_2> asks in Thai: "ข้างล่างเสียงดังไปไหมครับย่า".


Close-up, slow tilt down toward the floorboards.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: faint clatter and voices rising from the shop below.
```

### SHOT 32 · 4:08–4:16 · Close-up · static  ★ FINDING 1 — ปลูกขอบเตียงครั้งที่ 2
**ATTACH** 1) `@grandma_pranom`→REF_0 · 2) `@nong_daeng`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** ต้น `"ย่าจะบอกอะไรผมเหรอครับ"` — นิ่ง รอคำตอบที่ไม่มา
> มืออีกข้างวางบนรอยขีด **ยังห้ามอธิบาย** นี่คือครั้งสุดท้ายที่คนดูเห็นมันก่อนองก์ 5
```
Use <IMAGE_REF_0> as the character reference for the old woman's hands and face.
Use <IMAGE_REF_1> as the character reference for the young man's sleeve and arm.
Use <IMAGE_REF_2> as the location reference for the bedroom.

The thin fingers of a frail Thai woman of 79 <IMAGE_REF_0> close around the sleeve
of a Thai man of 24 <IMAGE_REF_1> as he starts to rise from her bedside in a small
upstairs bedroom <IMAGE_REF_2>, gripping a beat longer than she needs to, her
breath catching as if there is more she wants to say. Her other hand lies on the
bed's wooden side rail, her fingertips resting on the dense little scratches cut
into it. She does not look at them and neither does he. Early afternoon, soft
filtered light.
The young man <IMAGE_REF_1> stops and asks in Thai: "ย่าจะบอกอะไรผมเหรอครับ". No answer comes.


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: fabric gripped, a catch of breath.
```

### SHOT 33 · 4:16–4:24 · Wide · static
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@grandma_pranom`→REF_1 · 3) `@upstairs_bedroom`→REF_2
**บทพูด** ต้น `"เดี๋ยวผมขึ้นมาใหม่นะครับ"` — อ่อนโยน
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the character reference for the old woman.
Use <IMAGE_REF_2> as the location reference for the bedroom and curtain.

A Thai man of 24 <IMAGE_REF_0> pats the hand of a frail Thai woman of 79
<IMAGE_REF_1> gently, eases his sleeve free with care, then rises and gathers the
empty bowl to leave a small upstairs bedroom <IMAGE_REF_2>. Early afternoon, soft
light through a shifting curtain.
He says in Thai as he gathers the bowl: "เดี๋ยวผมขึ้นมาใหม่นะครับ".


Wide shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the curtain shifting in a breeze, a floorboard creaking.
```

## ฉาก F — นับเงินสามกอง (ช็อต 34–38)

### SHOT 34 · 4:24–4:32 · Medium · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ค่าเส้น...ค่าหมู...ค่าน้ำแข็ง"` — นับงานประจำ
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the back counter.

A Thai man of 58 <IMAGE_REF_0> sits alone at the back counter of his noodle shop
<IMAGE_REF_1> with a small cash drawer open in front of him, sorting worn
banknotes between his fingers. Afternoon lull, soft warm light, the shop otherwise
empty. No writing or numbers legible anywhere.
He works through it aloud in Thai: "ค่าเส้น...ค่าหมู...ค่าน้ำแข็ง".


Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: notes rustling, a fan somewhere behind him.
```

### SHOT 35 · 4:32–4:40 · Close-up · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"อันนี้ค่ายาแม่"` — เรียบ แน่นอน
```
Use <IMAGE_REF_0> as the character reference for the man's hands.
Use <IMAGE_REF_1> as the location reference for the counter surface.

The hands of a Thai man of 58 <IMAGE_REF_0> separate a stack of worn banknotes
into two distinct piles on the back counter of a noodle shop <IMAGE_REF_1>, one
visibly larger than the other. Afternoon lull, soft warm light. No numbers or text
legible.
He sets the second pile down and says in Thai: "อันนี้ค่ายาแม่".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: notes counted and stacked.
```

### SHOT 36 · 4:40–4:48 · Close-up · static
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"แล้วอันนี้...เก็บไว้ก่อน"` — พูดค้าง แล้วปัดจบ ต้นได้ยินจากประตู (ตั้งใจ — นำไปสู่ช็อต 37)
```
Use <IMAGE_REF_0> as the character reference for the man's hands.
Use <IMAGE_REF_1> as the location reference for the counter.

The hands of a Thai man of 58 <IMAGE_REF_0> set apart a third, smaller stack of
worn banknotes on the back counter of a noodle shop <IMAGE_REF_1>, folding it
differently from the other two before tucking it aside. Afternoon lull, soft warm
light. No numbers or text legible.
He begins a third sentence in Thai, stops, and closes it off: "แล้วอันนี้...เก็บไว้ก่อน".


Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: paper folded and set down quietly.
```

### SHOT 37 · 4:48–4:56 · Medium · static — **ต้น พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@lung_somchai`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** ต้น `"พ่อนับเงินอยู่เหรอ"` — ปกติ ไม่ได้สงสัยอะไร
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the character reference for the older man.
Use <IMAGE_REF_2> as the location reference for the back counter and doorway.

A Thai man of 24 <IMAGE_REF_0> leans against the doorway to the back counter of a
noodle shop <IMAGE_REF_2>, watching with ordinary curiosity as a Thai man of 58
<IMAGE_REF_1> counts money. He speaks Thai, casually, and says: "พ่อนับเงินอยู่เหรอ".
Afternoon lull, soft warm light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a ceiling fan whirring.
```

### SHOT 38 · 4:56–5:04 · Medium · static — **ต้น พูด**  ⟵ **จุดโฆษณา 5:00**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** ต้น `"มีเก็บเยอะขนาดนี้เลยเหรอพ่อ"` — ทีเล่นทีจริง แต่อยากรู้จริง
```
Use <IMAGE_REF_0> as the character reference for the young man's face.
Use <IMAGE_REF_1> as the location reference for the back counter.

A Thai man of 24 <IMAGE_REF_0> tilts his head, one eyebrow raised, half-teasing but
genuinely curious, waiting on an answer at the back counter of a noodle shop
<IMAGE_REF_1>. He speaks Thai and says: "มีเก็บเยอะขนาดนี้เลยเหรอพ่อ". Afternoon lull,
soft warm light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the ceiling fan whirring on.
```

---

## ★ ฉาก G — พี่วิทย์ (ช็อต 39–48) — ของใหม่ ทั้งตอนจบอยู่ที่ฉากนี้

⚠️ **ทุกช็อตในฉากนี้ใช้ `@cop_wit` ซึ่ง task-a55713c5 กำลังสร้างอยู่**
บล็อกหน้าตาของวิทย์ยังเป็น `medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist` — **ห้ามยิงฉากนี้จนกว่าจะเติมจาก
รูปจริง** ถ้าเดาหน้าเขาตอนนี้ รูปที่เพิ่งสร้างจะไร้ความหมาย เพราะ prompt ชนะรูป

### SHOT 39 · 5:04–5:12 · Medium · static
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** วิทย์ `"ลุงครับ"` — ทักทายแบบคนคุ้นเคย
```
Use <IMAGE_REF_0> as the character reference for the man's face, hair and clothing.
Use <IMAGE_REF_1> as the location reference for the shop and its tables.

A Thai man of 32 <IMAGE_REF_0>, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, steps in off the street
into a noodle shop <IMAGE_REF_1> and sits down at the same corner table without
looking for one, the way someone does in a place they have been coming to for
twenty years. He turns the stool before he sits so that he is facing the open
street door, and settles with his bag still on his shoulder. Late afternoon, warm
low light through the shutter.
He calls toward the counter in Thai as he sits: "ลุงครับ".


Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a plastic stool dragged out, street noise easing as he sits.
```

### SHOT 40 · 5:12–5:20 · Medium · static — **วิทย์ พูด**
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** วิทย์ `"ลุง เส้นเล็กน้ำใสครับ"` — สบายๆ คุ้นเคย
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the shop.

A Thai man of 32 <IMAGE_REF_0>, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, calls his order toward the
counter of a noodle shop <IMAGE_REF_1> without picking up a menu. He speaks Thai,
easy and familiar, and says: "ลุง เส้นเล็กน้ำใสครับ". Late afternoon, warm low light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the broth pot bubbling, a fan turning.
```

### SHOT 41 · 5:20–5:28 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ไม่ใส่ถั่วงอก ใช่ไหมวิทย์"` — ไม่เงยหน้า ไม่ต้องคิด
```
Use <IMAGE_REF_0> as the character reference for the man's face and clothing.
Use <IMAGE_REF_1> as the location reference for the wok station.

A Thai man of 58 <IMAGE_REF_0>, short greying hair, light stubble, in a dark-blue
apron over a white shirt, answers from the wok station of his noodle shop
<IMAGE_REF_1> without looking up and without pausing his hands. He speaks Thai and
says: "ไม่ใส่ถั่วงอก ใช่ไหมวิทย์". Late afternoon, warm low light, steam rising past him.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: the wok hissing, a ladle against metal.
```

### SHOT 42 · 5:28–5:36 · Close-up · static — **วิทย์ พูด**
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** วิทย์ `"ลุงจำได้ทุกทีเลย"` — ยิ้ม อบอุ่น
```
Use <IMAGE_REF_0> as the character reference for the man's face.
Use <IMAGE_REF_1> as the location reference for the shop behind him.

The face of a Thai man of 32 <IMAGE_REF_0>, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, breaks into an
easy smile at a corner table in a noodle shop <IMAGE_REF_1>. He speaks Thai and
says: "ลุงจำได้ทุกทีเลย". Late afternoon, warm low light.

Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: background chatter, chopsticks set down.
```

### SHOT 43 · 5:36–5:44 · Medium · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@noodle_shop`→REF_1
**บทพูด** สมชาย `"ก็กินมาตั้งแต่ตัวเท่านี้"` — เรียบๆ ไม่ได้อวด
```
Use <IMAGE_REF_0> as the character reference for the man's face and hands.
Use <IMAGE_REF_1> as the location reference for the counter.

A Thai man of 58 <IMAGE_REF_0> in a dark-blue apron lowers a basket of noodles into
boiling water at the counter of his noodle shop <IMAGE_REF_1> and holds a flat palm
low beside his hip, showing a height, without turning around. He speaks Thai,
matter-of-fact, and says: "ก็กินมาตั้งแต่ตัวเท่านี้". Late afternoon, warm low light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: water boiling, the basket shaken twice.
```

### SHOT 44 · 5:44–5:52 · Medium · static — **วิทย์ + สมชาย พูด**
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@lung_somchai`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** วิทย์ `"เท่าไหร่ครับลุง"` → สมชาย `"เอาไว้ก่อน วันหลังค่อยจ่าย"`
```
Use <IMAGE_REF_0> as the character reference for the younger man.
Use <IMAGE_REF_1> as the character reference for the older man in the apron.
Use <IMAGE_REF_2> as the location reference for the counter.

A Thai man of 32 <IMAGE_REF_0>, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, stands at the counter of a
noodle shop <IMAGE_REF_2> with a worn wallet half open. He speaks Thai and says:
"เท่าไหร่ครับลุง". A Thai man of 58 <IMAGE_REF_1> in a dark-blue apron waves it off
without looking at the wallet and answers in Thai: "เอาไว้ก่อน วันหลังค่อยจ่าย".
Late afternoon, warm low light.

Medium shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a wallet opened, a cloth wiped across the counter.
```

### SHOT 45 · 5:52–6:00 · Medium two-shot · static — **วิทย์ + สมชาย พูด**
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@lung_somchai`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** วิทย์ `"ลุงพูดแบบนี้ทุกทีนะ"` → สมชาย `"ก็จริงทุกที"`
```
Use <IMAGE_REF_0> as the character reference for the younger man.
Use <IMAGE_REF_1> as the character reference for the older man.
Use <IMAGE_REF_2> as the location reference for the counter.

A Thai man of 32 <IMAGE_REF_0>, medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist, and a Thai man of 58
<IMAGE_REF_1> in a dark-blue apron stand on opposite sides of the counter of a
noodle shop <IMAGE_REF_2>. The younger one speaks Thai, half laughing, and says:
"ลุงพูดแบบนี้ทุกทีนะ". The older one answers in Thai, unbothered: "ก็จริงทุกที".
Late afternoon, warm low light.

Medium two-shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: steam, a stool pushed back.
```

### SHOT 46 · 6:00–6:08 · Close-up · static — **วิทย์ + สมชาย พูด**  ⟵ ท่อนหัวใจของฉาก
**ATTACH** 1) `@cop_wit`→REF_0 · 2) `@lung_somchai`→REF_1 · 3) `@money_fold`→REF_2 · 4) `@noodle_shop`→REF_3
**บทพูด** วิทย์ `"ผมวางไว้ตรงนี้นะลุง"` → สมชาย `"วิทย์ เอาคืนไป"`
```
Use <IMAGE_REF_0> as the character reference for the younger man's hand and sleeve.
Use <IMAGE_REF_1> as the character reference for the older man's hand and apron.
Use <IMAGE_REF_2> as the prop reference for the folded banknotes.
Use <IMAGE_REF_3> as the location reference for the counter surface.

The hand of a Thai man of 32 <IMAGE_REF_0> sets a small fold of worn banknotes
<IMAGE_REF_2> down on the counter of a noodle shop <IMAGE_REF_3>. He speaks Thai
and says: "ผมวางไว้ตรงนี้นะลุง". The hand of a Thai man of 58 <IMAGE_REF_1>, sleeve
rolled back under a dark-blue apron, is already moving toward it. He answers in
Thai, flat and final: "วิทย์ เอาคืนไป". No numbers or text legible on the notes.
Late afternoon, warm low light.

Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: paper set on wood, a hand sliding across the counter.
```

### SHOT 47 · 6:08–6:16 · Close-up · static — **สมชาย พูด**
**ATTACH** 1) `@lung_somchai`→REF_0 · 2) `@money_fold`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** สมชาย `"เอาคืนไป ลุงไม่รับ"` — ไม่โกรธ ไม่ต่อรอง
```
Use <IMAGE_REF_0> as the character reference for the man's hand and face.
Use <IMAGE_REF_1> as the prop reference for the folded banknotes.
Use <IMAGE_REF_2> as the location reference for the counter.

The hand of a Thai man of 58 <IMAGE_REF_0> pushes a small fold of worn banknotes
<IMAGE_REF_1> back across the counter of a noodle shop <IMAGE_REF_2>, and holds it
there until it is taken. He speaks Thai, not angry and not negotiating, and says:
"เอาคืนไป ลุงไม่รับ". Late afternoon, warm low light.

Close-up, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: paper sliding on wood, the shutter rattling in a breeze outside.
```

### SHOT 48 · 6:16–6:24 · Medium two-shot · static — **ต้น + สมชาย พูด**
**ATTACH** 1) `@nong_daeng`→REF_0 · 2) `@lung_somchai`→REF_1 · 3) `@noodle_shop`→REF_2
**บทพูด** ต้น `"พ่อไม่เคยเก็บตังค์พี่วิทย์เลยใช่ไหม"` → สมชาย `"ตั้งแต่เขายังไม่สูงเท่าเคาน์เตอร์"` → ต้น `"ยี่สิบปีเลยนะพ่อ"` → สมชาย `"ก็แค่ก๋วยเตี๋ยวชามเดียวลูก"`
> ⚠️ สี่บรรทัดใน 8 วินาทีอาจแน่นไป — ถ้าตัดคำหาย ให้แยกเป็นสองช็อต (48 = สองบรรทัดแรก, 48b = สองบรรทัดหลัง) แล้วเลื่อนเลขช็อตทั้งองก์ 2 ไปหนึ่ง
```
Use <IMAGE_REF_0> as the character reference for the young man.
Use <IMAGE_REF_1> as the character reference for the older man.
Use <IMAGE_REF_2> as the location reference for the counter and the empty doorway.

A Thai man of 24 <IMAGE_REF_0> in a grey polo shirt watches the street doorway of a
noodle shop <IMAGE_REF_2>, where someone has just left, then turns to a Thai man of
58 <IMAGE_REF_1> in a dark-blue apron who is already wiping down the counter. The
younger one speaks Thai: "พ่อไม่เคยเก็บตังค์พี่วิทย์เลยใช่ไหม". The older one answers
without stopping: "ตั้งแต่เขายังไม่สูงเท่าเคาน์เตอร์". The younger one says: "ยี่สิบปีเลย
นะพ่อ". The older one, still wiping: "ก็แค่ก๋วยเตี๋ยวชามเดียวลูก".
Late afternoon, warm low light.

Medium two-shot, static camera.
Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.
Sound: a cloth on wood, the street outside, no reply expected.
```

---

## สรุปองก์ 1

| | |
|---|---|
| ช็อต | 48 · 6:24 |
| จุดโฆษณา | 1:00 (ช็อต 8) · 3:00 (ช็อต 23) · 5:00 (ช็อต 38) — ทั้งสามจุดค้างที่คำถามที่ยังไม่มีคำตอบ |
| ตัวละคร | สมชาย · ต้น · ย่าประนอม · **วิทย์ (ใหม่)** |
| Location | `@side_wall` `@staircase` `@upstairs_bedroom` `@noodle_shop` `@street_front` |
| Prop | `@money_fold` (ช็อต 46–47) |
| ยิงได้เลย | ช็อต 1–38 — asset ครบทุกตัวแล้ว |
| **ยังยิงไม่ได้** | ช็อต 39–48 — รอ `@cop_wit` จาก task-a55713c5 แล้วเติม `medium athletic build, short neat black hair, clean-shaven, calm steady eyes, wearing a plain dark-grey polo shirt with an open two-button collar and a simple steel wristwatch on his left wrist` |

**เครดิต** 48 ช็อต × 12 = 576 · ทดสอบที่ 360p = 6/ช็อต

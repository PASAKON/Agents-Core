# Master Character Prompt Template

Template กลางสำหรับ generate ตัวละครทุกตัวในหนังของเรา (ประตูวาป, ป๊อก...ป๊อก...คลื่ด..., และเรื่องถัดๆ ไป)

ใช้ template นี้ทุกครั้งที่สร้างตัวละครใหม่ เพื่อให้ output คงที่ + reuse ข้าม prompt ได้ผ่าน `@CharacterN`

---

## ⚠️ รูปแบบที่ถูกต้อง — Character Reference Sheet (แก้ 2026-08-08)

รูป cinematic เดี่ยว (มู้ด/แสงดราม่า) **ไม่ใช่** reference sheet ที่ถูกต้อง — reference sheet ต้องเอาไว้เป็น "ต้นแบบกลาง" ที่โมเดลดึงไปใช้ relight/จัดฉากใหม่ได้ทุกสถานการณ์ ถ้า bake มู้ดใส่ไปแล้วจะเอาไปใช้ฉากอื่นไม่ได้

**กฎ 3 ข้อ (จากตัวอย่างจริงที่ CEO ส่งมา):**

1. **พื้นหลังขาว/เทาอ่อนล้วน** สตูดิโอ ไม่มีฉาก ไม่มีพร็อพ แสงนวลสม่ำเสมอ ไม่มีเงาดราม่า
2. **ซีนอารมณ์ 3-6 ซีน** (ขึ้นกับตัวละคร/การใช้งาน) แต่ละซีนเป็น headshot/close-up มีเลข+ชื่ออารมณ์กำกับมุมซ้ายบน เช่น:
   `01 NEUTRAL/NORMAL` · `02 SUBTLE SMILE` · `03 LAUGHING` · `04 CRYING` · `05 TERROR/HORROR` (เลือกอารมณ์ตามที่ตัวละครต้องใช้จริงในเรื่อง)
3. **1 ซีนเต็มตัว** ยืนตรง ท่าเป็นกลาง เห็นชุด/รูปร่างเต็ม แยกเป็นพาเนลใหญ่กว่าซีนอารมณ์ (จัด layout แบบ grid ซีนอารมณ์ฝั่งซ้าย + เต็มตัวฝั่งขวา ตามตัวอย่าง)

ทุกพาเนลต้องเป็นคนเดียวกัน หน้าตา/ทรงผม/ผิวเหมือนกันเป๊ะทุกซีน ต่างกันแค่สีหน้า+ท่าทาง

---

## โครงสร้าง (9 ช่อง กรอกทุกช่อง ห้ามข้าม)

```
[ชื่อ/บทบาท]        — ชื่อตัวละคร + role ในเรื่อง (1 บรรทัด)
[Age / Ethnicity]   — อายุ, เพศ, เชื้อชาติ
[Face]               — รูปหน้า, ตา (สี+แววตา), จุดเด่นบนใบหน้า
[Hair]               — สี, ทรง, เท็กซ์เจอร์
[Skin]                — โทนผิว, ร่องรอย/ตำหนิ (ถ้ามี)
[Build]              — ส่วนสูง, รูปร่าง, ท่าทางที่ยืน/เดินเป็นปกติ
[Personality read]   — บุคลิกที่ "อ่านออก" จากรูปลักษณ์ ไม่ใช่คำบรรยายนามธรรม
[Default wardrobe]   — ชุดที่ใส่เป็นค่าเริ่มต้น วัสดุ สภาพ (ใหม่/เก่า/เปื้อน)
[Style lock]         — photoreal หรือ stylized, โทนแสง/สีที่ใช้กับตัวละครนี้ตลอดเรื่อง
```

**กฎสำคัญ:** เขียนแบบนี้ **ก่อนตัวละครปรากฏตัวครั้งแรกในฉากไหนก็ตาม** แม้จะมีรูปอ้างอิง (`@Image`) อยู่แล้วก็ตาม — เพื่อให้โมเดล "ล็อก" หน้าตาไว้ข้ามการ generate หลายรอบ ครั้งต่อๆ ไปให้อ้างด้วย `@CharacterN` แทนการพิมพ์ซ้ำ

---

## ตัวอย่างจริงที่ใช้ generate สำเร็จแล้ว — @Character1 Mother

```
@Character1 — Mother
Age/Ethnicity: real woman, early 40s
Face: rounded and warm, large expressive dark eyes, soft full cheeks, gentle laugh lines
Hair: shoulder-length dark hair, loosely tied back, a few loose strands
Skin: warm, lived-in, no heavy stylization
Build: sturdy, capable, medium height
Personality read: warm, unhurried, comfortable running a busy kitchen, confident half-smile as default expression
Default wardrobe: cream blouse under a flour-dusted apron, sleeves pushed up to the forearm
Style lock: photoreal with warm animated-character-inspired exaggeration — real performer styled like a hand-painted late-1990s family-film aesthetic, vivid saturated warm color grading
```

---

## ตัวอย่างใหม่ พร้อมใช้ทันที — @Character4 The Alien (ประตูวาป)

`output/warp-door/character4-alien.png` ที่ generate ไปรอบแรก **เป็นรูปแบบ cinematic ผิด** (มู้ดมืด/แสงดราม่า bake ไปในรูป) — ต้อง regenerate ใหม่เป็น reference sheet ตามกฎ 3 ข้อด้านบน พรอมต์ที่ถูกต้อง:

```
Character reference sheet, plain white/light-grey studio background, even
soft studio lighting, no shadows, no props, no scene — identical character
in every panel, only expression and pose change.

LEFT SIDE — 5 emotion close-ups in a labeled grid, each panel numbered and
titled top-left in bold sans-serif:
01 NEUTRAL/NORMAL — calm, unreadable, resting alien expression
02 CURIOUS — head tilted slightly, watching
03 PAIN — eyes tightened, jaw clenched from captivity
04 PLEADING — eyes wide, searching, silently asking for help
05 FEAR — recoiling, eyes wide with alarm

RIGHT SIDE — 1 full-body panel, larger than the emotion grid, character
standing straight in a neutral pose, arms at sides, full wardrobe and body
visible head to toe, same plain white background.

CHARACTER (identical across all 6 panels): a sexless, ageless humanoid
alien being. Gaunt, elongated face, no hair, smooth hairless scalp. Pale,
near-translucent, sickly grey-white skin, faint teal bioluminescent veins
visible near cable connection points on the neck and forearms. Thin,
frail, slightly stooped build. Torn lab-issue containment wrap, medical
tubing and cables connecting its body to external ports, restraint marks
on the wrists. High resolution, detailed textures, no text other than the
panel labels, no watermark.
```

---

## วิธีใช้ต่อ

1. กรอก template ให้ครบทุกช่องก่อน generate ตัวละครใหม่ทุกตัว (Alien, Guards, Ae, Bee ที่ยังไม่มี — ใช้โครงเดียวกันนี้)
2. Generate แล้ว save เป็น Character reference ใน Higgsfield ตั้งชื่อให้ตรง `@CharacterN`
3. ทุก scene prompt ถัดไปอ้างด้วย `@CharacterN` แทนการพิมพ์รายละเอียดซ้ำ (ประหยัด token + คงหน้าตาตรงกันทุก scene)

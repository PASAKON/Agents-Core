> **HISTORY since 2026-09-25 — edit the skills, not this file.** The working copy of these rules is
> `.claude/skills/CTO_Film_PromptFormat/SKILL.md` (every engine) and `.claude/skills/CTO_Seedance2.5_Higgsfield/SKILL.md`
> (Seedance-only: `@Video 1` once, previz ≥ output resolution, the open chip-per-mention question). This file stays as the original evidence.

# AUTHORING-RULES.md — กฎการเขียน prompt ของ «Sorry, Sir»

เขียน 2026-09-03 หลัง S1C fail 3 ครั้งติด กิน operator ไป 2 session
คู่กับ `PROMPT-STYLE.md` (โครงสร้าง prompt) — ไฟล์นี้คือ **อะไรห้ามอยู่ในตัว prompt**
ทุกบรรทัดที่อ้างในนี้ verify ด้วยตาแล้ว ไม่ได้ลอกจาก report

---

## สรุปการกวาดทั้ง corpus (16 ไฟล์)

พูดตรง ๆ ก่อน เพื่อไม่ให้ใครไปแก้ของที่ไม่พัง:

- **`@Video` chip ซ้ำ ไม่มีในไฟล์ไหนเลย** นับจริงแล้ว: `videoref-inserts.txt` มี `@Video` 10 ตัว
  = 1 ตัวในคู่มือ (L15) + 9 ตัว หนึ่งตัวต่อหนึ่ง block พอดี ส่วน `s1-v3-videoref.txt`,
  `s2b-v3-split-videoref.txt`, `s7-reshoot-videoref.txt` มี `@Video` เฉพาะใน header
  **ใต้ paste marker เป็นศูนย์ทั้งสามไฟล์** อีก 11 ไฟล์ไม่มี video reference เลย
- ดังนั้น**สิ่งที่พังใน S1C ไม่ใช่ chip ตัวที่สอง** แต่คือ *สตริงหน้าตาเหมือน reference*
  ที่ถูก quote ไว้ใน body: `s1-angles.txt:89` `a bare "Video — the cart design" line`
- **ปัญหาจริงที่เกิดซ้ำทั้ง corpus ไม่ใช่ video reference** แต่คือ 3 อย่างนี้:
  (1) โน้ตของ operator/CTO/CEO นั่งอยู่ในเนื้อที่ operator copy
  (2) ข้อความค้างจากเวอร์ชันเก่าที่ยังสั่งตรงข้ามกับช็อตปัจจุบัน — ผลของ sweep แบบ
  "Add-only — nothing removed" (`s1-angles.txt:1` และอีก 13 ไฟล์)
  (3) การห้ามด้วยการ **บรรยายสิ่งที่ห้าม** ซึ่งโมเดลอ่านเป็นคำสั่ง

---

# PART 1 — สิ่งที่ต้องแก้ตอนนี้

## ก. ด่วน — จะทำให้ generation เสีย

### A1 · อุบัติเหตุเอง + blocker ที่ยังไม่ปลดล็อก

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 1 | `s1-angles.txt:67-96` | **ลบทั้งบล็อก** `⚠️ S1C-ONLY OVERRIDES` ออกจาก body ย้ายไปโซนโน้ต ทั้ง 5 bullet เป็นโน้ตถึงคน ไม่ใช่คำบรรยายภาพ และ 4 ใน 5 bullet บรรยายสิ่งที่ตัวเองห้าม: L71-72 บรรยายรถเข็นไม่มีล้อ, L77-81 พิมพ์คำว่า `"locked"` กับ `"Hold"`, L89 quote `"Video — the cart design"`, L91 ใส่ token ต้องห้าม `@prop_cart_b` พร้อมประโยค `that one has the painting in it` เข้าไปในช็อตที่ rack ต้องว่าง |
| 2 | `s1-angles.txt:12` | **แก้ที่ต้นทาง** header `ALL SEVEN` เขียน `camera LOCKED or one stated move` → คำว่า LOCKED เข้า S1C ทาง header นี้ (grep ยืนยัน: S1C L55-65 ไม่มีคำว่า locked/Hold เลย bullet L77-81 คือแหล่งเดียว) แยก header เป็น "S1A/B/D–G: locked" กับ "S1C: one lateral track, the camera never stops" ลบ bullet ทิ้งอย่างเดียวไม่พอ |
| 3 | `s1-angles.txt:21` vs `74-76` | **BLOCKER — ห้ามยิง S1C จนกว่าจะเคลียร์** L21 ผูก `@project_absence_prop_cart` แต่ L74-76 สั่งให้ผูก Element ที่ล้อหมุนเห็นได้ ไฟล์ไม่เคยบอกว่าตัวเดิมมีล้อหรือไม่ ลบ override ทิ้งเฉย ๆ = ยิงด้วยรถเข็นไม่มีล้อ ซึ่งคือ defect ที่ CEO flag |
| 4 | `s1-angles.txt:103-106` | S1D: **เก็บแค่ 2 ประโยคท้าย** (`The shoulder in the foreground...SAME MAN.` / `There is no second cleaner...`) ลบ 2 ประโยคแรกที่มี take id `(be929c0a)` และบรรยายเฟรมที่มี **TWO Dupes** |

### A2 · ข้อความค้างที่สั่งตรงข้ามกับช็อต — เผา take แน่ แม้ลบโน้ตหมดแล้ว

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 5 | `s4-s5.txt:170-173` + `:196-198` | **หนักสุดในไฟล์นี้** L134-137 ประกาศเปลี่ยนกล้อง (`No hero wall, no crack, no plaque anywhere in this frame`) และ L128-132 สั่ง low three-quarter + **lateral DRIFT** แต่ beat แรก L170 ยังเขียน `Locked one-point wide at waist height, crack and plaque on the axis` และ L172-173 `The slow push-in down the axis begins` แล้ว negative L197-198 ยังปิดท้ายด้วย `no camera move except the single specified push-in` → **ประกาศ ≠ การแก้** เขียน beat L170-187 ใหม่ให้เป็น drift และแก้ negative ให้ห้ามทุก move ยกเว้น drift |
| 6 | `s2-accident.txt:40-43,117-118,101-102,125` | ปมป้ายทองเหลือง: ไฟล์บอกว่า**ป้ายตก 4 ที่** และ **ป้ายไม่ขยับ 5 ที่** ลบ/แก้ให้เหลือเวอร์ชันเดียว (ป้ายไม่ตก ตาม L60-62, L76, L81-82): ① L42-43 ลบประโยค `CEO 2026-08-30: THE PLAQUE FALLS TOO — ... fresh plaque in P1` ② L117-118 ลบ `no plaque left hanging on the wall at the end, no plaque back on the wall` (negative ตัวนี้สั่งให้เอาป้ายออก ซึ่งคือตรงข้ามกับช็อต) ③ L101-102 ลบ `one metallic clatter` (ขัด L63-64 `No metallic clatter`) ④ L125 แก้ `except the brass plaque before it falls` → `except the brass plaque` |
| 7 | `s6-s18.txt:132` และ `:332-333` | negative เขียน `no un-mirrored plaque text` ทั้งที่ reference ของช็อตเดียวกันสั่ง `THE PLAQUE READS CORRECT-WAY-ROUND — never mirrored` (L104, L303) → **negative สั่งให้กลับด้าน** แก้เป็น `no mirrored plaque text` ทั้งสองที่ (ซากจาก wall-POV เวอร์ชันเก่า; `s4-s5.txt:112` มีบรรทัดเดียวกันแต่**ถูกต้อง** เพราะ S4 ผูก plate ที่ป้าย MIRROR-REVERSED จริง — อย่าไปแก้ตัวนั้น) |
| 8 | `s4-s5.txt:123` | House negative ปิดท้ายด้วย `no large crack` ทั้งที่ reference L65 สั่ง `The CRACK floats in the near plane across the missing wall, large and unmistakable` → ลบ `no large crack` ออกจาก S4 |
| 9 | `s2-accident.txt:17-18` vs `:121` | cart design ระบุ `ladder` เป็นของบนรถเข็น แต่ negative L121 ห้าม `no ladder` ตัดสินมาข้อเดียว: ถ้าเจตนาคือ "Dupe ไม่ปีน" ให้แก้ negative เป็น `no climbing, no tiptoe reaching` และปล่อยบันไดไว้บนรถ |
| 10 | `s4-s5.txt:83-85` | นับคนไม่ตรง: เขียน `two of the three unnamed extras` แล้วบรรยายสามคน; ผูกแขก 6 + Dupe + extras 3 = 10 แต่บอก `EIGHT PEOPLE total` (L85), `Eight people stand in NEAT ROWS` (L87), negative `no crowd beyond eight people` (L110) นับใหม่แล้วเขียนตัวเลขเดียวทั้งบล็อก |

### A3 · ประโยคที่ห้ามโดยการบรรยายสิ่งที่ห้าม — โมเดลอ่านคำบรรยาย ไม่ได้อ่านเจตนา

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 11 | `s7-s9.txt:158-165, 204-211, 253-260, 294-301` | บล็อก `⚠️ ONE VALDER` ซ้ำคำต่อคำ **4 ครั้ง** ทุกครั้งบรรยาย `two identical men in panelled jackets standing side by side` และพิมพ์คำ `SYMMETRICAL` เข้าไปในช็อตที่ S8b L226-227 สั่ง `THE CROWD PARTS SYMMETRICALLY` และ S8c L249-250 สั่ง `symmetrical rows` **แทนทั้ง 4 บล็อกด้วยประโยคบวกที่ฝังอยู่ในนั้นแล้ว**: `EXACTLY ONE VALDER, dead centre, unmirrored. He is the ONLY person in a panelled multi-colour jacket; all guests are in plain single-colour coats.` — ประหยัด ~32 บรรทัด ไม่เสีย constraint สักข้อ |
| 12 | `s-arrivals.txt:217-219` | `REFERENCES — jobs.` ตามด้วย post-mortem ที่ **quote วลีที่ห้าม** (`said only "the row of four"`) พร้อม take id `(cbfb41e0)` และบรรยาย output ที่ผิด (`four strangers in the wrong costumes`) ย้ายทั้งหมดออก เหลือแค่ `REFERENCES — jobs:` |
| 13 | `s-arrivals.txt:261-262` + `:256` | L262 เขียน `never write "the row of five"` แต่ L256 ในบล็อกเดียวกันเขียนว่า `The row of five, motionless.` จริง ๆ → ลบคำสั่งที่ L262 และแก้ L256 ให้ระบุชื่อทั้งห้าคนแทน |
| 14 | `s4-s5.txt:100-102` | ใน beat `[11s]`: `Take 1 rendered him twice — two cleaners, two carts — so state his position once` ลบ ประโยคบวกที่ต้องการอยู่ครบแล้วที่ L98-100 |
| 15 | `s2-accident.txt:34-35` | ลบประโยคแรกของ SIZE CONTINUITY (`earlier takes rendered the painting BIGGER on the wall than it is in the cart`) เก็บ L36-38 ที่บรรยายขนาดที่ถูกต้อง |
| 16 | `s2-accident.txt:85-90` และ `:92-99` | ย้ายออกทั้งสองบล็อก: L85-90 เป็นเรียงความเหตุผลถึงคนอ่าน (`do not "restore" the earlier version`) และบรรยาย `A cracked wall with nothing on it`; L92-99 เป็น **QC rubric ตอน review** (PASS/FAIL) ที่ไล่ชื่อรอยแตกทุกแบบที่ห้ามแบบไม่มี "no" นำหน้า (`a dense mesh of many fine lines`, `concentric rings`, `a hole/crater with rubble`) |
| 17 | `s6-s18.txt:95-107` และ `:294-306` | บล็อก `VIEWPOINT REBALANCE (CEO 17:15)` ซ้ำคำต่อคำ 2 ที่ เก็บเฉพาะคำบรรยายเฟรมปัจจุบัน (L97-103) **ลบประวัติ**: `NO LONGER the in-wall glass POV`, `The mirroring existed only because we used to stand behind the wall`, `that darkness belonged to the wall we are no longer inside` — สามประโยคนี้ทิ้งภาพ POV ในกำแพง / ป้ายกลับด้าน / scrim ไว้ใน prompt |

### A4 · ข้อความรั่วเข้าเครื่องหมายคำพูด — คลาสความพังที่ **วัดมาแล้ว**

`PROMPT-STYLE.md:65-95` บันทึกไว้ว่า S15a take 1 (`35b4edd4`) โมเดล **พูด stage direction ออกมาดัง ๆ**
และ visual review ผ่านหมด จับได้ด้วยการ transcribe เท่านั้น สามรายการนี้ยังอยู่:

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 18 | `s7-s9.txt:309` | `[12s] This is the line the film turns on. Softest of all: "I have been...` — วลี `and this is the line the film turns on:` อยู่ในรายการ **UNSAFE ตรงตัว** ที่ `PROMPT-STYLE.md:82` แก้เป็น: `[12s] Softest of all: "I have been collecting..."` และย้ายเหตุผลออก ที่เดียวกัน L271-272 (`This silence is the most important beat in the scene; hold it.`) และ L313 (`By this line he believes it himself. Cut.`) ก็เอาออก |
| 19 | `s6-s18.txt:617-619` | โน้ตอนุมัติเชื่อมติดท้ายบทพูดของยาย: `"One hundred million. For the artist." (CTO-drafted lines — CEO confirmed the mechanism: the money goes to DUPE, not Valder. She bid on an artwork; the maker just confessed; she pays the maker.)` ลบวงเล็บทั้งก้อน — negative ของฉากเดียวกัน (L635) ห้าม `no speaking anything outside the quotation marks` อยู่แล้ว |
| 20 | `s4-s5.txt:161-165` | `⚠️ CTO casting call, flagged:` เป็นคำถามค้างถึง CEO + คำสั่ง operator (`swap the reference`) และ **ลากบทของฉากอื่นเข้ามา**: `(A5: "That is the thing itself.")` ในช็อตที่บทที่อนุญาตมีแค่ `"I understand it."` กับ `"Five million."` ย้ายทั้งบล็อกไป QUEUE.md เป็นคำถามค้าง |

### A5 · บล็อกที่ paste แล้วไม่ได้ prompt ที่ใช้ได้

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 21 | `s13-the-back-door.txt:18-22` | `⚠️ THIS MENTION IS STALE.` นั่งคั่นระหว่างหัวข้อ `REFERENCES — each with a job:` (L17) กับ declaration ที่มันบอกว่าใช้ไม่ได้ (L24) มี error string ของ composer (`"Not eligible"`), ชื่อไฟล์ (`PLATE-loc_exterior_b.md`) และขั้นตอนตอน re-shoot ย้ายออก **แล้วแก้ L24 ให้เป็น mention string จริงของ replacement plate** ไม่งั้นก็ยัง blocked อยู่ดี |
| 22 | `s13-the-back-door.txt:65` | `REFERENCES — same three as S13a, same jobs.` = S13b ไม่มี reference สักตัว **และไม่มีคำบรรยายตัวละครเลยทั้งบล็อก** (ชุดของ Valder/ช่างอยู่ที่ L27-30 ในบล็อก S13a เท่านั้น) เขียน reference ทั้งสามซ้ำลงไปใน S13b รูปแบบเดียวกันอยู่ที่ `s7-s9.txt:292`, `s6-s18.txt:413,445,606-607` แก้เหมือนกันทุกที่ |
| 23 | `s-dupe-inserts.txt:28-38` | D1–D5 เป็น **5 ช็อตอยู่ในบล็อกเดียว** paste ทีเดียวได้ micro-event 5 อันที่ขัดกัน (กระพริบ / ก้มมองมือ / พยักหน้า / ชำเลืองไม้ถู / มองภาพ) และคำนำหน้าแต่ละข้อ `after "It's about death."` ฯลฯ ลาก **บทพูด 5 บรรทัดเข้าไปในช็อตที่ L13 เขียน `NO DIALOGUE` และ L42 ห้าม `no speech, no mouth movement`** แยกเป็น 5 บล็อก ตัดคำนำหน้า `after "…"` ทิ้ง |
| 24 | `s7-reshoot-videoref.txt:32-37` | โน้ตถูกยัดกลางประโยค: L32 จบด้วย `— EXACTLY` แล้ว L33 ขึ้น `⚠️ THE PLATE NOW CONTAINS EXACTLY TWO MEN — bind it whole; the old six-guard plate is retired.` ทำให้ประโยคขาด ลบ L33-34 (ศัพท์ Elements panel) และลบ L37 ที่เป็นเศษบรรทัดลอย `TWO guards, not six` (ซ้ำกับ L36 อยู่แล้ว) |
| 25 | `s-extras.txt:150-152` | `⚠️ CTO reading of the CEO's "รายการทีวีจริง"` นั่งระหว่าง spec (L147-148) กับ beat แรก (L154) เป็นการตีความ brief ไม่ใช่คำบรรยายภาพ ย้ายออก |
| 26 | `s-price-inserts.txt:22-25` | อยู่ใน body ของทั้ง P1/P2/P3: `the film cuts to` ในช็อตที่ L12 สั่ง `no cuts` และ L66 ห้าม `no cut inside the clip`; `the room goes mad` ในช็อตที่ L20 สั่ง `NO face, NO body, NO reflection of a person anywhere, ever`; และ `Fire any time; they bind only the hall.` เป็นคำสั่ง scheduling ตรง ๆ **ลบทั้งย่อหน้า** |
| 27 | `s13-the-back-door.txt:93-94` | `HANDOFF:` ระหว่าง colour grade กับ CRITICAL NEGATIVES พูดถึง Dupe และเหตุการณ์นอกเฟรม (`walks to the wall in S14`, `brings Dupe running in S15`) ในหนังสองคนที่ negative L96 ห้าม `no third person, no passers-by` ลบ |
| 28 | `s-price-inserts.txt:34-35` | `⚠️ REWRITTEN 30 Aug (CEO): the arrivals see a BARE cracked wall — no plaque.` นั่งระหว่างหัวบล็อก P1 (L33) กับ beat แรก (L36) เป็นบันทึกการแก้ไข และวลี `the arrivals see` ใส่**คน**เข้าไปในช็อตที่ L20 สั่ง `NO face, NO body, NO reflection of a person anywhere, ever` และ L61 ห้าม `no faces, no people, no bodies` ลบทั้งสองบรรทัด |
| 29 | `s-extras.txt:181-191` | X8a กับ X8b อยู่บล็อกเดียวใต้ spec `8s each` แต่มี **สอง timeline** (`X8a [0s]` ที่ L181, `X8b [0s]` ที่ L185) paste ทั้งบล็อก = ส่ง 2 ช็อตเป็น prompt เดียว แยกเป็นสองบล็อก |

### A6 · marker ที่ถูกยกเลิกด้วยประโยคของตัวเอง — แก้คำเดียว 3 ไฟล์

| # | ไฟล์ / บรรทัด | ทำอะไร |
|---|---|---|
| 30 | `s1-v3-videoref.txt:8` · `s2b-v3-split-videoref.txt:13` · `s7-reshoot-videoref.txt:8` | ทั้งสามเขียน `then paste THIS ENTIRE TEXT as the prompt.` ขณะที่ marker `=== THE PROMPT (paste from here down) ===` อยู่ต่ำลงไปแค่ 4-6 บรรทัด (L14 / L17 / L14) **operator อ่าน L8 ก่อน L14 เสมอ** ถ้าทำตาม L8 จะได้ `@Video 1` สองตัว + คำสั่ง `do NOT generate an image for it` (s2b L8) + คำสั่งให้ drop character เข้า composer แก้เป็น `paste everything below the marker.` — คำเดียว ปิดช่องทางเดียวที่ทำให้ header ทั้งหมดหลุดเข้า prompt |

---

## ข. Hygiene — เปลืองโทเคน ไม่ทำให้ generation เสีย

จัดเป็นคลาส แก้ทีเดียวทั้งคลาสได้:

1. **Word-count tally ใน body** — ลบทิ้งทุกอัน: `s7-s9.txt:282,315` · `s13-the-back-door.txt:57,84` ·
   `s2b-v3-split-videoref.txt:93` · `s6-s18.txt:275,467,519,588,630,748`
   (`s2b:93` เขียน `(19 spoken words.)` แต่นับจริงได้ 18 — เป็นข้อความเท็จเกี่ยวกับตัวเองที่อยู่ใน prompt)
2. **โน้ตลำดับตัดต่อใน spec line** — ลบส่วนหลัง: `s-dollhouse.txt:47,67,113` (`Cuts against S1 / A1 / S6 or S11`) ·
   `s-extras.txt:148` (`Plays right after S11 / the 100M hammer`), `:176` (`Bookends: X8a near the film's open`) ·
   `s-price-inserts.txt:33,42,49` (`plays after A5, before S4` ฯลฯ) · `s6-s18.txt:290` (`CEO order: S12 → P3 → this scene`)
3. **แสตมป์ผู้สั่ง/วันที่ใน body** — ลบวงเล็บ เก็บกฎ: `s-dollhouse.txt:27` `(CEO 29 Aug)` ·
   `s-arrivals.txt:94,126-127` · `s1-multicut.txt:30` `(CEO, locked)` · `s6-s18.txt:110,145,191,241,336,476,481` ·
   `s4-s5.txt:151` `(CEO 30 Aug)` · `s2-accident.txt:24` `(CEO: the crack must carry a real reference)`
4. **Thai brief ดิบใน body ที่ซ้ำกับ beat ภาษาอังกฤษข้างล่าง** — ย้ายไปโซนโน้ต:
   `s6-s18.txt:138,342-343,410-411` · `s4-s5.txt:134-135`
5. **ศัพท์ composer ใน body** — `chip / plate / bind / Elements panel / UUID / upload / picker`:
   `s6-s18.txt:539,556-558,560-561,349-350,550` · `s7-s9.txt:87-88,167-170,213-216,262-265,338-341` ·
   `s4-s5.txt:146-147,151` · `s-price-inserts.txt:18` `(his recostume, CEO 30 Aug — not the plate's ivory)`
6. **โน้ตนำทางในเอกสาร** — `s-dollhouse.txt:31` `(plus the character named in each scene below)` ·
   `s1-angles.txt:23-25` (บอกลำดับยิง + ชื่อไฟล์อื่น + `photographed seven ways so the editor can build rhythm`
   ซึ่งขัดกับ `no cuts inside any clip` ที่ L12) · `s-extras.txt:44-45` (`the editor can lay under any cut`) ·
   `s-arrivals.txt:158-159,288` · `s6-s18.txt:768`
7. **ตัวเลขที่นับไม่ตรง** (สัญญาณว่าไฟล์ถูกแก้ทีหลังแล้วไม่นับใหม่):
   `s7-s9.txt:52` บอก S8 มี `THREE CLIPS` แต่มี 4 (L242 ประกาศ S8d เอง) · `s7-s9.txt:363` `ALL FIVE CLIPS ABOVE`
   แต่มี 6 · `s7-reshoot-videoref.txt:11` บอก `11 chips total (1 video + 10 elements)` แต่ body มี element token 11 ตัว
   → 12 chips · `s1-angles.txt:16` `REFERENCES — all seven` ตามด้วย 3 รายการ
8. **บรรทัดขาดจากการแก้ค้าง** — `s-arrivals.txt:66-68` (`the brass` แล้วขึ้นบรรทัดใหม่เป็น `**NO PLAQUE...`
   คำนามหาย) · `s-arrivals.txt:142-143` (`the crack (the camera), the mirror-reversed` / `the red door...`
   คำนามหาย) · `s7-s9.txt:30-31` และ `s6-s18.txt:26-27` (`is bound for the` แล้วชนเข้า ⚠️)
9. **`videoref-inserts.txt:1`** อ้างว่า audio-endpoint bans ถูก restore เข้าทุก scene ในไฟล์ —
   grep แล้ว **ไฟล์นี้มีศูนย์** (ของจริงมาจาก scene file ที่ paste ต่อท้าย จึงไม่กระทบภาพ แต่ banner โกหก)
   และ `videoref-inserts.txt:189,210` (S6, S11) forever-line ตกหล่น: เหลือ `same spots,` ไม่มี `same paths, same timing`
   ที่อีก 7 block มี
10. **`videoref-inserts.txt:8`** เขียน `dd it into your session scratchpad` — `dd` เป็นคำสั่ง shell ที่ทำลายข้อมูลได้
    แก้เป็น `copy it`

---

# PART 2 — กฎการเขียน prompt

อ่าน 2 นาทีก่อนแตะไฟล์ prompt ทุกครั้ง ทุกข้อมีที่มาจากของจริง เพื่อไม่ให้ใครมาลดระดับทีหลัง

### 1. หนึ่งไฟล์มีสองโซนเท่านั้น ไม่มีโซนที่สาม

โซนโน้ต (คนอ่าน) กับโซน prompt (โมเดลอ่าน) ทุกอย่างที่ไม่ใช่คำบรรยายภาพ/เสียง/กล้อง = โซนโน้ต

> เกิดจาก: `s1-angles.txt` ไม่มี marker เลย โน้ต 30 บรรทัด (L67-96) จึงนอนอยู่กลางบล็อก S1C
> ระหว่าง beat กับ separator — operator ไม่มีทางรู้ว่าต้องข้าม

### 2. Marker ต้องอธิบายตัวเองในบรรทัดเดียว และต้องมี **หัวและท้าย**

รูปแบบมาตรฐาน คัดลอกไปใช้ตรง ๆ:

```
=== NOTES · DO NOT PASTE ANY OF THIS ===
(ทุกอย่างที่นี่: post-mortem, take id, ชื่อคนสั่ง, วันที่, ขั้นตอน composer, ลำดับตัดต่อ, คำถามค้าง)
=== END NOTES ===

=== ↓↓↓ PASTE FROM HERE ↓↓↓ · everything above is notes, never paste it ===
...prompt...
=== ↑↑↑ PASTE STOPS HERE ↑↑↑ · everything below is notes, never paste it ===
```

marker ต้องอ่านรู้เรื่องโดยไม่ต้องเคยเห็นไฟล์นี้ ถ้าต้องอธิบายด้วยปากว่า marker แปลว่าอะไร แปลว่า marker ไม่ทำงาน
**ไฟล์ที่ยังไม่มี marker เลย 13 จาก 16 ไฟล์** (มีเฉพาะ `s1-v3-videoref.txt`, `s2b-v3-split-videoref.txt`,
`s7-reshoot-videoref.txt`) ต้องใส่ให้ครบ

### 3. ห้ามมีประโยคใดในไฟล์ที่ยกเลิก marker

> เกิดจาก: `s1-v3-videoref.txt:8`, `s2b-v3-split-videoref.txt:13`, `s7-reshoot-videoref.txt:8`
> เขียน `paste THIS ENTIRE TEXT` ในขณะที่ marker อยู่ต่ำลงไป 4-6 บรรทัด operator อ่านบนก่อนล่างเสมอ
> marker ที่ถูกยกเลิกด้วยบรรทัดข้างบนมัน = ไม่มี marker

คำที่ใช้ได้คำเดียว: **`paste everything below the marker`**

### 4. `@Video 1` พูดครั้งเดียว — และ **คำเตือนก็นับเป็นการพูด**

กฎของ CEO: video file ถูกเอ่ยถึงครั้งเดียวในรูป `@Video 1` เท่านั้น
ถ้าจะเขียนกฎข้อนี้ลงไฟล์ **ห้ามพิมพ์ token ลงในกฎ** เขียนว่า `the video chip is bound at its first mention only`

> เกิดจาก: `s1-angles.txt:82-85` เขียนว่า `mentioned ONCE and never again` แล้วเอ่ยถึงมันต่ออีก 3 บรรทัด
> ในย่อหน้าเดียวกัน — กฎหักตัวเองในประโยคที่ประกาศกฎ
> `videoref-inserts.txt:15` เขียนแบบเดียวกันเป๊ะ แต่ไม่พังเพราะอยู่เหนือโซนโน้ต — คือหลักฐานว่า
> **ข้อ 1 ป้องกันข้อ 4 ได้เอง** ถ้ามี marker

ผลข้างเคียงที่ต้องรู้: ใต้ marker ของทั้งสามไฟล์ videoref **ไม่มี `@Video` token เลยสักตัว**
(ตั้งใจ — `s1-v3:9-10` บอกว่า later references เป็น plain words) แปลว่า chip เกิดจากขั้นตอน attach เท่านั้น
ถ้า composer ตั้งชื่อ slot ว่าอย่างอื่นที่ไม่ใช่ `Video 1` ทุกประโยคใน body จะชี้ไปที่ความว่างเปล่าเงียบ ๆ
— ให้ operator verify ชื่อ slot ก่อนยิง

### 5. ห้าม quote ตัวอย่างที่ผิดไว้ใน prompt ไม่ว่าจะห้ามมันแรงแค่ไหน

โมเดลอ่าน**คำบรรยาย** ไม่ได้อ่าน**เจตนา** ข้อห้ามที่บรรยายภาพต้องห้าม = การสั่งภาพนั้น

> เกิดจาก — ทั้งหมดเป็นบรรทัดที่บรรยายสิ่งที่ตัวเองห้าม:
> `s1-angles.txt:89` `a bare "Video — the cart design" line` (คือ**อุบัติเหตุนี้เอง**)
> `s1-angles.txt:71-72` `a cart with no visible wheels` ในช็อตที่ต้องเห็นล้อหมุน
> `s7-s9.txt:158-159` ×4 `two identical men in panelled jackets standing side by side`
> `s4-s5.txt:101` `two cleaners, two carts`
> `s-arrivals.txt:218` `said only "the row of four"` + `invented four strangers in the wrong costumes`
> `s2-accident.txt:34-35` `rendered the painting BIGGER on the wall`
> `s1-angles.txt:103-104` `came back with TWO Dupes`

**วิธีเขียนที่ถูก:** เขียนสิ่งที่ต้องการเป็นประโยคบวก แล้วใส่ negative สั้น ๆ ที่ไม่มีคำบรรยาย
`EXACTLY ONE VALDER, dead centre, unmirrored.` ไม่ใช่ `take 1 rendered him twice — two identical men...`

### 6. ห้ามพิมพ์คำต้องห้ามลงใน prompt แม้จะพิมพ์เพื่อห้าม — และให้แก้ที่ต้นทาง

> เกิดจาก: `s1-angles.txt:77-81` สั่ง `Do not write "locked" ... do not end a beat with a bare "Hold"`
> grep แล้วพบว่า **bullet นี้คือแหล่งเดียว**ของสองคำนั้นใน paste ของ S1C (L55-65 ไม่มีเลย)
> ซ้ำร้าย คำว่า LOCKED ยังเข้ามาอีกทางจาก shared header `s1-angles.txt:12` ที่ไม่มีใครแก้

ถ้า shared block ผิดสำหรับช็อตหนึ่ง **แยก shared block** อย่าเขียน override ทับ
override คือหลักฐานว่าข้อความต้นทางยังผิดอยู่

### 7. ประกาศ ≠ การแก้ ห้ามเขียนโน้ตแทนการแก้ข้อความจริง

> เกิดจาก: `s4-s5.txt:134-137` ประกาศเปลี่ยนกล้องพร้อมคำพูด CEO แต่ beat L170-173 และ negative L197-198
> ยังเป็นกล้องเก่าทั้งคู่ ประกาศอยู่ห่างจากข้อความที่ต้องแก้ 33 บรรทัด และไม่มีใครไปแก้
> `s6-s18.txt:95-107` / `:294-306` แบบเดียวกัน: ประกาศว่าไม่ใช่ in-wall POV แล้ว แต่ negative L132/L332-333
> ยังห้าม `un-mirrored plaque text` ซึ่งเป็นของ POV เก่า

**เขียนโน้ตประกาศได้ แต่ต้องอยู่โซนโน้ต และต้องแก้ body ในการแก้ครั้งเดียวกัน**

### 8. เลิก sweep แบบ "Add-only — nothing removed"

> `s1-angles.txt:1` และอีก 13 ไฟล์ประกาศนโยบายนี้ ผลลัพธ์คือ negative ที่ห้ามสิ่งที่ช็อตต้องการ:
> `s2-accident.txt:117-118` ห้ามป้ายที่ต้องอยู่ · `s6-s18.txt:132,332-333` ห้ามป้ายที่อ่านถูกด้าน ·
> `s4-s5.txt:123` ห้ามรอยแตกใหญ่ที่ L65 สั่งให้ใหญ่ · `s-price-inserts.txt:61` ใส่ประโยค
> `every single person has a different face...` เข้าไปในช็อตที่ห้ามมีคนโดยสิ้นเชิง

แก้ body ครั้งใด **ต้องอ่าน CRITICAL NEGATIVES ของบล็อกนั้นทั้งบล็อกทันที** ลบซากได้ ต้องลบ

### 9. ทุก reference ประกาศครั้งเดียว ในบล็อกเดียว และห้ามใช้ pointer แทน

- `REFERENCES — as S12a.` / `same three as S13a` / `same 10 chips as S15a` → บล็อกนั้นถูก paste แล้ว
  **ไม่มี reference เลย** (`s13-the-back-door.txt:65` หนักสุด — S13b ไม่มีแม้แต่คำบรรยายหน้าตาตัวละคร)
  พบที่ `s6-s18.txt:413,445,606-607` · `s7-s9.txt:292` · `s13-the-back-door.txt:65`
- POSITION MAP ให้ใช้**คำบรรยาย** ไม่ใช่ `@token` ซ้ำ:
  `s1-v3-videoref.txt` body มี `@project_absence_char_cleaner_c` 2 ครั้ง (L35, L43) และ
  `@project_absence_prop_cart` 2 ครั้ง (L36, L44) ทั้งที่ L10 บอก `4 chips total`
  `s2b-v3-split-videoref.txt` เหมือนกันเป๊ะ (L35/40, L36/42) ทั้งที่ L14 บอก `3 chips total`
- **ยังไม่รู้แน่ว่า composer chip ทุก mention หรือแค่ครั้งแรก** — ยิงทดสอบ 1 ครั้งแล้วบันทึกลงไฟล์นี้
  จนกว่าจะรู้ ให้เขียน `@token` ครั้งเดียวต่อบล็อก แล้วอ้างถึงมันด้วยคำธรรมดา

### 10. Dialogue: อะไรที่ติดกับ `: "` ต้องเป็น manner tag ≤ 5 คำ

กฎเต็มอยู่ที่ `PROMPT-STYLE.md:65-95` **ไม่ใช่ทฤษฎี วัดมาแล้ว**: S15a take 1 (`35b4edd4`)
โมเดลพูด stage direction ออกมาดัง ๆ และ visual review ผ่านหมด

- ห้ามมีวงเล็บ/โน้ต/เครดิตอยู่ท้ายบรรทัดที่มีคำพูด (`s6-s18.txt:617-619`)
- ห้าม quote บทของฉากอื่นเข้ามาในช็อต (`s4-s5.txt:163` · `s-dupe-inserts.txt:28-38` · `s-arrivals.txt:58`)
- ห้ามใส่คำวิจารณ์ความสำคัญของบทลงใน beat (`s7-s9.txt:271-272,309,313`) — L309 ใช้วลีที่
  `PROMPT-STYLE.md:82` ระบุว่า UNSAFE ตรงตัว
- **transcribe ทุก dialogue clip ก่อนเก็บเป็น keeper** ดูภาพอย่างเดียวจับคลาสนี้ไม่ได้

### 11. หนึ่งบล็อก = หนึ่งช็อตที่ยิงได้จริง

> เกิดจาก: `s-dupe-inserts.txt:28-38` เอา 5 ช็อตใส่บล็อกเดียว paste ทีเดียวได้ micro-event 5 อันที่ขัดกัน
> `s-extras.txt:173-191` เอา X8a/X8b ใส่บล็อกเดียวใต้ spec `8s each` มีสอง timeline ในหนึ่ง prompt

### 12. ⚠️ ไม่ใช่เครื่องหมายว่า "อย่า paste"

`s2b-v3-split-videoref.txt:63` (`⚠️ THE CONTRACTOR NEVER STOPS WORKING...`) และ `s4-s5.txt:143`
(`⚠️ The camera looks ACROSS the room at a low three-quarter...`) ใช้ ⚠️ กับ prompt จริงที่ต้องอยู่
ขณะที่ `s2b:4,8,15` และ `s-price-inserts.txt:34` ใช้ glyph เดียวกันกับโน้ตของคน
**อย่าตัดสินด้วย glyph ตัดสินด้วย marker (ข้อ 2)** — การกวาดครั้งนี้เกือบพลาดเพราะไล่ตาม glyph

### 13. ตัวเลขต้องนับได้ ตอนแก้ไฟล์ให้นับใหม่

`s4-s5.txt:83-85` เขียน "สองในสาม" แล้วบรรยายสาม; ผูก 10 คน บอก `EIGHT PEOPLE total`
`s7-s9.txt:52` บอก 3 clips มี 4 · `s7-s9.txt:363` บอก 5 clips มี 6 · `s7-reshoot-videoref.txt:11`
บอก 11 chips มี 12 · `s1-angles.txt:16` บอก `all seven` แล้วลิสต์ 3
ตัวเลขไม่ตรง = มีคนแก้ไฟล์แล้วไม่นับใหม่ = สมมติว่ามีซากอย่างอื่นเหลืออยู่ด้วย

---

## ก่อนกด Generate — เช็ก 3 ข้อ ใช้เวลา 60 วินาที

อ่าน text ที่จะวางจริง **ทั้งบล็อก บนลงล่าง ครั้งเดียว** แล้วถาม:

1. มีบรรทัดไหน**บรรยาย**สิ่งที่บล็อกนี้ห้ามไหม (ข้อ 5, 6)
2. reference ทุกตัวประกาศครั้งเดียวไหม และบล็อกนี้มี reference ครบของตัวเองไหม ไม่ใช่ pointer (ข้อ 9)
3. CRITICAL NEGATIVES ขัดกับ body ตัวเองไหม (ข้อ 8)

แล้วรันบรรทัดนี้กับ text ที่จะ paste:

```bash
grep -nE '⚠️|✅|\(CE[OT]|\(CTO|20[0-9]{2}-[0-9]{2}|take [0-9]|GH #|\.md|\.txt|\.MP4|chip|plate|Elements panel|UUID|paste|operator|spoken words|Fire |Cuts against|as S[0-9]' /tmp/paste.txt
```

**เจอบรรทัดไหนติด = ยังไม่ยิง** ย้ายมันไปโซนโน้ตก่อน

---

## เจ้าของไฟล์

CTO เป็นคนแก้ไฟล์ prompt · operator ไม่แก้ ถ้า operator เจอปัญหาระหว่างยิง
ให้ **STOP AND REPORT** ห้ามเขียนโน้ตเตือนลงในไฟล์ prompt เอง — นั่นคือวิธีที่อุบัติเหตุนี้เกิดขึ้น

---

## กฎเพิ่ม (2026-09-03) — previz ต้องมีความละเอียดไม่ต่ำกว่า output

**previz ทุกไฟล์ต้องเป็น 1280x720 ถ้าเป็น 640x360 generation จะพัง**

วัดมาแล้วด้วยราคา: S1C ยิงไป 3 ครั้ง เรนครั้งละ ~26 นาที ตายหมดทุกครั้งด้วย error
กลาง ๆ ว่า *"change your input files or prompt"* — ตัดทุกสมมติฐานอื่นทิ้งก่อนแล้ว
(previz ทั้ง 33 ไฟล์เป็น 16:9 หมด · S1C ไม่ใช่ไฟล์ใหญ่สุด · bitrate อยู่อันดับ 5
จาก 33 · นับแล้วไม่มี `@Video` ซ้ำที่ไหนเลย) เหลือตัวแปรเดียวคือความละเอียด

ขยายเป็น 1280x720 โดยไม่แตะอย่างอื่นเลย — กล้องเดิม 8 วินาทีเดิม 192 เฟรมเดิม —
**ครั้งที่ 4 ผ่าน** `absence-S1C-take4-023e91c3-PASS-8s-720p.mp4`

Higgsfield ไม่เคยประกาศกฎนี้ที่ไหน (ค้นครบ help center 74 บทความ, docs 20 หน้า,
OpenAPI spec เต็ม) **นี่คือค่าที่เราวัดเอง ไม่ใช่กฎของเขา** — ใช้ได้กับ output 720p
ของเรา ถ้าวันไหนเรนที่ 1080p ให้ถือว่ากฎขยับตาม output แล้ววัดใหม่ อย่าเชื่อบรรทัดนี้

เช็คด้วย `python3 scripts/previz-check.py` ก่อนใช้ previz เป็น reference ทุกครั้ง

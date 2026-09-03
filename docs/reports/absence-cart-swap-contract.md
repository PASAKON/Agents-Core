<!-- Written by CTO #116d7688, 2026-09-03. The executable plan for swapping every
     cart reference onto the two new wheeled Elements. Handles are placeholders
     until the operator reports the real ones. Nothing here has been applied yet. -->

# CART SWAP CONTRACT — «Sorry, Sir» (CEO 2026-09-03)

**นิยาม handle**
- `CART_A_HANDLE` = รถเข็นมีล้อ, **rack ว่าง** → ทุกฉากก่อน Dupe ทำภาพตก
- `CART_B_HANDLE` = รถเข็นมีล้อ, **ภาพยืนตรงในrack ขนาดเท่าตอนแขวนผนังจริง** → ทุกฉากหลังจากนั้น
- S2 (ฉากอุบัติเหตุ) ผูก **ทั้งคู่** ชิ้นเดียวไม่พอ เพราะในคลิปเดียวกันมันเปลี่ยนจาก A เป็น B ที่ [13s]

**กติกาแทนที่ (บังคับ อ่านก่อนรัน sed)**
1. `@prop_cart_b` เป็น substring ของ… ไม่ใช่ — กลับกัน: `prop_cart` เป็น substring ของ `prop_cart_b` และของ `project_absence_prop_cart` **แทนที่ตัวยาวก่อนเสมอ** ลำดับที่ปลอดภัย: (1) `@prop_cart_b` → (2) `@project_absence_prop_cart` → (3) `prop_cart_b` เปล่า ๆ (ไม่มี @) → (4) `` `prop_cart` `` ในเนื้อความ. ถ้ารัน `s/prop_cart/…/g` ก่อน จะได้ `@CART_A_HANDLE_b` ทั่วไฟล์
2. `@prop_cart_c_empty` (สร้างไว้ 09-03 00:47) **ไม่ปรากฏใน prompt file ใดเลย** — ยืนยันแล้วด้วย grep ทั้ง repo มีแค่ใน `docs/reports/absence-handover-20260902-4.md` กับ `-20260903.md` เท่านั้น ไม่ต้องแก้ไฟล์ แต่ให้ถือว่า **ปลดระวาง** และดู §4 ข้อ 9 เรื่อง composer tab ที่ยังค้าง
3. ห้ามแตะไฟล์ `DEAD-*.txt` และไฟล์ใน `docs/prompts/absence/*.md` (ดู §4 ข้อ 7–8)

---

## 1 · ตารางสัญญา — ฉากที่ต้องสลับ id

ทุกแถวคือ id ที่ **มีอยู่จริงในไฟล์** (ตรวจทีละบรรทัดแล้ว) พาธเต็ม = `/Users/gob/Projects/Agents/docs/prompts/absence/`

### 1A · ก่อนอุบัติเหตุ → `CART_A_HANDLE`

| scene | ไฟล์ : บรรทัด | ของเดิม | เปลี่ยนเป็น | เหตุผล |
|---|---|---|---|---|
| S1 | `s1-multicut.txt:19`, `:46` | `@project_absence_prop_cart` | `CART_A_HANDLE` | PRE-ACCIDENT ล็อกไว้ในไฟล์เอง (l.30) rack ว่าง |
| S1 | `s1-multicut.txt:31` (เนื้อความ `` `prop_cart` ``) | ชื่อ id เปล่าในประโยค | เขียนใหม่ให้ชี้ CART_A | ประโยคสั่ง "Use the ORIGINAL `prop_cart`" จะกลายเป็นคำสั่งผิดทันทีที่ id ตาย |
| S1 (v3, ตัวที่ยิงจริง) | `s1-v3-videoref.txt:36` (POSITION MAP), `:44` (REFERENCES) | `@project_absence_prop_cart` | `CART_A_HANDLE` | ไฟล์ v3 คือฉบับ CEO green-lit 31 Aug ต้องแก้คู่กับ multicut เสมอ |
| S1A–S1G (ทั้งเจ็ดมุม) | `s1-angles.txt:21` | `@project_absence_prop_cart` | `CART_A_HANDLE` | บล็อก "REFERENCES — all seven" ใช้ร่วมกัน แก้บรรทัดเดียวมีผลทั้ง 7 ช็อต |
| S1C (ข้อความกำกับ) | `s1-angles.txt:71-76` | ข้อความ "ถ้ายังไม่มี Element ล้อ ต้องสร้างก่อนยิง" | เขียนใหม่: Element นั้นคือ CART_A_HANDLE แล้ว | เงื่อนไขบล็อกการยิง S1C ถูกปลดโดยสัญญานี้ ต้องเขียนให้ชัดไม่งั้น operator ยังไม่กล้ายิง |
| S1C (ข้อความกำกับ) | `s1-angles.txt:91-92` | `@prop_cart_b` ในประโยค "Never fall back to…" | `CART_B_HANDLE` | ยังเป็นกฎที่ถูกต้อง แค่เปลี่ยนชื่อ อย่าลบทิ้ง |
| DH1 | `s-dollhouse.txt:49` | `@prop_cart_b` | `CART_A_HANDLE` | **จุดที่ผูกผิดอยู่ตอนนี้** DH1 = "the board before the game" cuts against S1 คือก่อนอุบัติเหตุ แต่ผูกรถคันที่มีภาพอยู่ |

### 1B · ฉากอุบัติเหตุ → ผูก **ทั้งคู่**

| scene | ไฟล์ : บรรทัด | ของเดิม | เปลี่ยนเป็น | เหตุผล |
|---|---|---|---|---|
| S2 | `s2-accident.txt:17` | `@project_absence_prop_cart` (บรรทัดเดียว "Rack EMPTY until [13s]") | **สองชิป**: `CART_A_HANDLE` = สภาพรถ [0s]–[12s] rack ว่าง · `CART_B_HANDLE` = สภาพรถตั้งแต่ [13s] ภาพยืนใน rack หันหน้าออก | คลิปนี้คือที่เดียวที่โมเดลได้เห็นว่า A กลายเป็น B อย่างไร จำนวนชิป 5 → 6 |

> หมายเหตุ S2: บีท [13s]–[17s] วางป้ายทองเหลืองแบนบนชั้นล่างของรถ — plate ของ CART_B **ไม่มีป้ายนี้** (ตาม `CHECKLIST.md:600` ระบุไว้ว่าเปลี่ยนแค่ภาพเข้า rack ของอื่นคงเดิม) ป้ายมาจากเนื้อความอย่างเดียวเหมือนเดิม ไม่ต้องคาดหวังจาก Element

### 1C · หลังอุบัติเหตุ → `CART_B_HANDLE`

ของเดิมทุกแถวคือ `@prop_cart_b`

| scene | ไฟล์ : บรรทัด | เหตุผล / โน้ต |
|---|---|---|
| A1 | `s-arrivals.txt:139` | ภาพอยู่ใน rack เห็นชัด ไม่มีใครมอง |
| A2 | `s-arrivals.txt:170` | |
| A3 | `s-arrivals.txt:195` | |
| A4 | `s-arrivals.txt:231` | |
| A5 | `s-arrivals.txt:259` | |
| A1–A5 (บล็อกร่วม) | `s-arrivals.txt:70` — `prop_cart_b` **ไม่มี @** | บล็อก "References every time" ของทั้งห้าฉาก อยู่คนละรูปแบบ ต้องแก้แยก |
| DH2 | `s-dollhouse.txt:70` | |
| DH3 | `s-dollhouse.txt:92` | |
| DH4 | `s-dollhouse.txt:118` | |
| DH (บล็อกร่วม) | `s-dollhouse.txt:30` | ⚠️ ดู §4 ข้อ 1 — บล็อกนี้ครอบ DH1 ด้วย ซึ่งต้องเป็น A |
| X4 | `s-extras.txt:92` | |
| X5 | `s-extras.txt:114` | ช็อตนี้คือ macro push-in เข้าไปที่ภาพในrack โดยตรง CART_B ต้องได้ขนาดภาพถูกตามกฎ SIZE CONTINUITY ของ S2 |
| S4 | `s4-s5.txt:80` | |
| S6b | `s6-s18.txt:151` | |
| S9 | `s7-s9.txt:328` | ⚠️ **ต้องแก้ข้อความด้วย ไม่ใช่แค่ id**: ปัจจุบันเขียน "THE REAL PAINTING leaning against its front" ซึ่งขัดกับ plate ที่ภาพยืนอยู่ใน rack เปลี่ยนเป็น "standing upright in the side rack, face outward" ไม่งั้น prompt สู้กับ Element |
| S15a | `s6-s18.txt:543` | |
| S15b | *(ไม่มี id ในไฟล์)* `s6-s18.txt:606` เขียนว่า "same 10 chips as S15a, same jobs" | S15b เปลี่ยนตาม S15a อัตโนมัติ **find-and-replace จะไม่ hit อะไรเลยในบล็อกนี้ แต่ฉากเปลี่ยนจริง** |
| S18a | `s6-s18.txt:731` | รถคันเก่าในบ้านหลังใหม่ ปัจจุบันผูก `prop_cart_b` ที่มีภาพอยู่แล้ว ดังนั้น CART_B ไม่ทำให้ภาพในเฟรมเปลี่ยน เปลี่ยนแค่ล้อ |

### 1D · บรรทัด glossary หัวไฟล์ (แก้ด้วยมือ ห้าม sed)

`prop_cart_b` ยังอยู่ในประโยค "exactly seven are bare: … loc_mansion_b, prop_cart_b." ที่หัวไฟล์ **10 ไฟล์**:
`s-arrivals.txt:6` · `s-dollhouse.txt:6` · `s-dupe-inserts.txt:6` · `s-price-inserts.txt:6` · `s1-angles.txt:6` · `s1-multicut.txt:6` · `s13-the-back-door.txt:6` · `s7-s9.txt:6` · `s4-s5.txt:48` · `s6-s18.txt:48`

บรรทัดนี้ไม่ใช่ binding ของฉากไหนเลย มันคือ whitelist บอกว่า id ไหน "ไม่มี prefix `project_absence_`" — ต้องรู้ก่อนว่า handle ใหม่สองตัวถูกตั้งแบบ bare หรือแบบมี prefix แล้วค่อยแก้ทั้งตัวเลข "seven" และรายชื่อ (`s-dupe-inserts`, `s-price-inserts`, `s13` มีแค่บรรทัดนี้บรรทัดเดียว ไม่มีฉากไหนในสามไฟล์นั้นผูกรถเข็น)

---

## 2 · ฉากที่ต้อง **เพิ่ม** binding ใหม่ (ADDITION ไม่ใช่ SWAP)

> ⚠️ สองฉากนี้ **ตอนนี้ไม่ได้ผูกรถเข็นเลย** การเพิ่ม reference chip = เปลี่ยนสิ่งที่เรนเดอร์ออกมา ไม่ใช่การรักษาของเดิม ทั้งสองฉาก **มีเทคที่ยิงไปแล้ว** ดังนั้นนี่คือคำสั่ง re-shoot ไม่ใช่ patch เงียบ ๆ ต้องให้ CEO เคาะแยกจากตาราง §1

| scene | ไฟล์ : จุดที่แทรก | เพิ่มอะไร | หลักฐานว่ารถอยู่ในเฟรม | ต้นทุน / ความเสี่ยง |
|---|---|---|---|---|
| **S5** | `s4-s5.txt:159` ต่อท้ายบรรทัด `@project_absence_char_cleaner_c — Dupe, mopping near the back wall.` | `CART_B_HANDLE` — รถจอดข้างเขาที่ผนังหลัง **ภาพยืนตรงในrack หันหน้าออก** ไม่มีใครมอง + เพิ่ม negative "no empty rack, no second cart, no second cleaner" ตามแบบ S4 (`s4-s5.txt:113`) | เขา **ถูพื้น** ตลอด 20 วิ ทั้งที่ l.159 และบีท [14s] ถังกับไม้ถูเป็นของบนรถ (ดู `s2-accident.txt:17`) ไม่มีถังลอยเดี่ยวในหนังเรื่องนี้ | ชิป 9 → 10 (ยังไม่เกินเพดาน ~10) · **previz ไม่มี proxy ของรถ** ดู §4 ข้อ 5 · S5 มีเทคยิงแล้วและติดปัญหา gold V ค้าง CEO อยู่ก่อนแล้ว |
| **S14** | `s6-s18.txt:492` ต่อท้ายบรรทัด `@project_absence_char_cleaner_c — Dupe at the far edge, mid-stroke, watching.` | `CART_B_HANDLE` — รถจอดที่ขอบเฟรมข้างเขา ภาพยืนใน rack หันหน้าออก | ช็อตเดียว locked symmetrical **wide** ทั้งห้อง ขอบเฟรมอยู่ในภาพตั้งแต่ [0s] ถึง [15s] เขาถูพื้นค้างกลางจังหวะทั้งสองครั้ง และ **S15a ซึ่งต่อเฟรมเดียวกันไม่ขยับใคร** ผูกรถไว้แล้วที่ `s6-s18.txt:543` "his cart at the edge, painting face-out" | **ชิป 10 → 11 เกินเพดาน** ไฟล์นี้ตัด bodyguard ออกจากชิปไปแล้วเพราะเหตุนี้ (`s6-s18.txt:494`) และ S15a เตือนไว้ว่า "twelve chips reliably turns to mush" ต้องเลือก: ยอม 11 หรือทิ้งชิปหนึ่งตัว (ตัวที่เข้าเกณฑ์ "generic ก่อน" ที่สุดคือ `@project_absence_char_woman_c` ยืนเฉย ๆ ไม่มีบีท) — **การตัดสินใจนี้เป็นของ CTO/CEO ไม่ใช่ operator** · S14 มี take1 แล้วและ S14t2 อยู่ในคิวอยู่แล้ว จึงเสียบเข้า take-2 ได้พอดี |

---

## 3 · ฉากที่ไม่ต้องแตะ

| scene | เหตุผล |
|---|---|
| **S8a** | Dupe โผล่บรรทัดเดียวใน REFERENCES ไม่มีคำกริยาเลย ("Dupe at the frame edge.") ไม่มีการใช้อุปกรณ์ ข้อความไม่ได้เอารถเข้าเฟรม → ตามกฎอนุรักษ์นิยม ไม่ผูก |
| **S8c** | บางกว่า S8a อีก ("Dupe, far edge.") ไม่มีบีทไหนพูดถึงเขาเลย |
| **S10b** | "@…critic_b @…cleaner_c — edges." ทุกบีทเป็นเรื่องคนประมูล ปากกา และ Valder ไม่มีคำว่า cart/mop/clean ในบล็อกทั้งบล็อก |
| **S12a** | "Dupe at the edge." ไม่มีกริยา ไม่มีอุปกรณ์ · เหตุผลเสริม: บีท [4s] เป็น **LOW WHEEL CLOSE-UP ระดับพื้นของล้อรถเข็นวีลแชร์** (`s6-s18.txt:380-382`) การโยนรถเข็นมีล้ออีกคันเข้าไปในช็อตที่มุกทั้งมุกอยู่ที่ล้อ เป็นการเพิ่มความเสี่ยงโดยไม่ได้อะไร |
| **S12c** | **ตรงนี้ผมแย้งผลออดิตที่ให้ "yes"** — S12c ไม่ได้ผูก reference ของตัวเอง มันสืบจาก S12a ("as S12a, PLUS:") และเฟรมเดียวที่ Dupe อยู่คือ whip-pan ลงหน้าตรง ๆ ครึ่งจังหวะ · position map ของ previz ฉากนี้ยืนยันเอง: `videoref-inserts.txt:110-111` "the three close-up singles land, in order: a GUARD's face → VALDER's face → DUPE's face" — เป็น **close-up หน้า** ไม้ถูอาจติดมา แต่ตัวรถไม่อยู่ในเฟรม และ rack ก็ไม่อยู่ในเฟรม จึงไม่มี "rack ที่โมเดลมั่วเอง" ให้ต้องคุม · ถ้า CEO อยากคุมจริง ทางเดียวที่ถูกคือไปเพิ่มที่ S12a ซึ่งมีปัญหาล้อชนล้อข้างบน — เสนอให้ปล่อยไว้ |
| **S16** | รถไม่อยู่ในเฟรมจริง ๆ ข้อความระบุอุปกรณ์เดียวคือไม้ถูสองครั้ง ("Dupe apart, holding his mop, not helping" / "holding his mop") ไม่ได้กำลังทำงาน และ previz map ก็ให้เขาถือแค่ไม้ ("the pale figure apart holding the thin stick = Dupe with his mop, not helping" `videoref-inserts.txt:177-178`) · ถ้าเทคไหนโผล่รถมาเอง แก้ด้วย negative "no cleaning cart" ไม่ใช่ด้วยการผูก Element |
| **D1–D5** | ไม่ผูกรถเลย และไม่ควรผูก เป็น portrait ระดับอกขึ้นไป 5 วิ (บล็อก REFERENCES ร่วมมีแค่ `loc_hall_big_e` + `char_cleaner_c`) คำว่า cart ใน D4/D5 เป็นทิศทางของ *สายตา* ที่มองออกนอกเฟรม · **หมายเหตุ: ออดิตเดิมระบุ D5 ว่า "binds a cart" — ไม่จริง ตรวจแล้ว** |
| **S2b, S13a, S13b, S17, S18b, S8b, S8d, S10, S12b, X1–X3, X6–X8, P1–P3** | ไม่มีรถผูก ไม่มีรถในเนื้อความ |

---

## 4 · ข้อควรระวัง — จุดที่ find-and-replace แบบตรงไปตรงมาจะพัง

1. **`s-dollhouse.txt:30` คือกับดักหลักของงานนี้.** บล็อก "REFERENCES — all four, each with a job" กำกับ DH1–DH4 พร้อมกัน และเขียนว่า `@prop_cart_b — the cart, the painting standing in it face outward.` แต่ **DH1 ต้องเป็น CART_A** (ก่อนอุบัติเหตุ ยังไม่มีภาพในรถ) แทนที่รวดเดียวทั้งไฟล์ = DH1 ผิด, แทนที่เฉพาะ l.49 อย่างเดียว = DH1 ยังโดนบล็อกร่วมสั่งให้มีภาพในrack อยู่ดี **ต้องแก้สองที่และเขียนข้อยกเว้นให้ชัด**: บล็อกร่วม → CART_B + ประโยค "DH1 IS THE EXCEPTION — it binds CART_A_HANDLE, rack empty, this is the board before the game"
2. **`s1-angles.txt:21` ครอบทั้ง S1A–S1G ไม่ใช่แค่สามมุมที่ออดิตระบุ.** S1A, S1C, S1E ที่ list ไว้เป็นแค่มุมที่เห็นรถชัด แต่บรรทัดที่แก้เป็นบรรทัดร่วมของทั้งเจ็ด ทิศทางตรงกันหมด (pre-accident ทุกมุม) จึงปลอดภัย **แต่ต้องรู้ว่ากระทบ 7 ช็อต ซึ่ง 5 ช็อตเป็น keeper ที่ยิงจบแล้ว** (S1A `091b3608`, S1B `9bd03344`, S1D t2 `ab366138`, S1E `9f1e996c`, S1G `3364edbe`)
3. **บรรทัดที่สืบทอด reference จะไม่ถูก grep เจอ แต่ฉากเปลี่ยนจริง.** สองแห่ง: `s6-s18.txt:606` (S15b = "same 10 chips as S15a") และ `s6-s18.txt:445` (S12c = "as S12a, PLUS") — ข้อที่สองแปลว่า **ถ้าใครเผลอเพิ่มรถให้ S12a มันจะไหลเข้า S12c เองโดยไม่มีใครสั่ง** และกลับกัน การเพิ่มให้ S12c ต้องเขียนเป็นบรรทัดของตัวเองใต้ "PLUS:" เท่านั้น
4. **สลับ id อย่างเดียวไม่พอในสามที่ ข้อความจะขัดกับ plate**: `s7-s9.txt:328` ("leaning against its front" ต้องเป็น "standing upright in the rack"), `s2-accident.txt:17` ("Rack EMPTY until [13s]" ต้องกระจายเป็นสองชิป), `s1-multicut.txt:31` ("Use the ORIGINAL `prop_cart`") · บวก `s1-angles.txt:71-76` ที่ยังเขียนว่า "ถ้ายังไม่มี Element ล้อ ห้ามยิง S1C"
5. **previz position map ไม่ตรงกับ chip list ที่จะเพิ่ม.** `videoref-inserts.txt:130` (S5) เขียน "the pale figure far behind at the back wall = Dupe, mopping" และ `:154` (S14) "the pale figure at the far right edge = Dupe, stopped mid-stroke" — ทั้งสอง **ไม่มี proxy ของรถ** ในขณะที่ S6/S11 มี ("Dupe with his cart" `:199`, `:218`) กติกาของ video-ref คือ "every figure stands EXACTLY where its character must stand" ถ้าเพิ่มชิปรถโดยไม่เติมบรรทัดใน map ด้วย โมเดลต้องเดาตำแหน่งรถเอง **เพิ่มชิปกับเติม map ต้องไปด้วยกันเสมอ**
6. **S6, S7, S11 พูดถึงรถในเนื้อความแต่ไม่ผูก Element เลย — ออดิตเดิมนับผิด.** ตรวจแล้ว: `s6-s18.txt:111` "Dupe at the frame edge with his cart" และ `:125` (S6), `s7-s9.txt:131` "the missing painting riding his cart" (S7), `s6-s18.txt:311` + previz `:218` (S11) ทั้งสามผูกแค่ `char_cleaner_c` **find-and-replace จะไม่แตะทั้งสามฉาก แต่ทีมจะเข้าใจว่าคุมแล้ว** สามฉากนี้เป็นอาการเดียวกับแปดฉากที่เพิ่งออดิต และอยู่นอกขอบเขตสัญญานี้ — ต้องตัดสินแยก ไม่ใช่แอบเติม (S6/S6b/S11 ยัง blocked รอ wall plate 20M/100M อยู่แล้วตาม `absence-wave-virgin28.md`) · S15b, S18b ที่ออดิตนับว่าผูกรถ: S15b สืบจาก S15a จริง แต่ **S18b ไม่มีรถและไม่ควรมี** (ผนังขาวเปล่า Dupe ตัวเล็กกับค้อน)
7. **ห้ามให้ sed วิ่งเข้าไฟล์ DEAD**: `DEAD-s2-interpretations-superseded.txt:46,128` และ `DEAD-s3-superseded-by-arrivals.txt:2,5` มี id เก่าอยู่ นั่นคือคลังประวัติ แก้แล้วเสียหลักฐาน
8. **ห้ามแก้เอกสารประกอบเป็นการย้อนประวัติ**: `CHECKLIST.md` (459, 481, 485, 596, 600, 602, 612, 615), `QUEUE.md` (395, 448, 560, 590, 604, 610-611, 674-675, 702), `PLATES-QUEUE.md` (7, 49, 51), `STORY-AUDIT.md:122`, `CLEANER.md:41`, `PLATE-prop_valder_study_b.md:7` — ทั้งหมดคือบันทึกว่าตอนนั้นใช้อะไร ให้ **เขียนบรรทัดใหม่ต่อท้าย** ว่า id ไหนแทนที่ id ไหนเมื่อไหร่ แทนการทับของเดิม
9. **มี composer tab ค้างที่ stage prompt เก่าไว้แล้ว.** handover 09-03 §3 ระบุว่า operator คนที่หกทิ้ง tab ของ project `ilag-studio/ai-film-festival-3` ไว้ พร้อม prompt S1C ที่ผูก `@prop_cart_c_empty` (เทคนั้น FAILED-refunded) **prompt ที่ค้างอยู่นั้นตายแล้วตามสัญญานี้ ห้ามกดยิงซ้ำตามที่เห็น** ต้อง re-stage ด้วย CART_A_HANDLE
10. **ทุกแถวใน §1 คือการเปลี่ยนหน้าตาของช็อตที่ถ่ายจบแล้ว.** ล้อที่โผล่มาใหม่ = re-shoot ทุกคลิป ไม่ใช่ patch เงียบ ๆ และตามกฎยืนพื้นของ CEO ใน `QUEUE.md:29-30` การปรับปรุง keeper "ไปต่อท้ายคิว" · keeper ที่โดนจากสัญญานี้: **S1, S1A, S1B, S1D, S1E, S1G, S2 take4, A1–A5, S15a take2, S15b** และ S4 take2 ที่ยัง in-flight · บวกฉากที่ยิงแล้วในกลุ่ม §2: **S5 (take2), S14 (take1 + t2 ในคิว)** · DH1 เปลี่ยนแรงที่สุดในเชิงภาพ เพราะภาพจะ **หายไปจาก rack** (ซึ่งคือความถูกต้อง) — แต่ DH1–DH4 ยัง held รอ CEO เคาะเรื่อง dollhouse plate อยู่ก่อนแล้ว จึงยังไม่มีเทคเสีย
11. **จำนวนชิป**: S2 5→6 (ผ่าน), S5 9→10 (พอดีเพดาน), S14 10→11 (**เกิน ต้องตัดสินใจ**), S12c ถ้ามีวันเปลี่ยนใจคือ 9→10
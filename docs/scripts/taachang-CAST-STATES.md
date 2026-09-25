# «ตาชั่งของเสี่ย» — ทะเบียนตัวละคร + State (v1, 2026-09-25)

CEO 2026-09-25: *"หนึ่ง Charactor อาจจะมี 1 หรือหลาย State … ถ้าเรามีครบ เราจะ Keep Charactor ได้ดีมากๆ
→ ใช้กับ Prop และ Location ด้วยได้นะ เพื่อ Continue Scene ให้ไปข้างหน้าแบบควบคุมได้ ตั้งแต่ต้นน้ำจนปลายน้ำ"*

## State คืออะไร

**State** = ลักษณะภายนอกของตัวละคร 1 ชุด ณ จุดหนึ่งของเรื่อง คือหน้า ผม หนวด ชุด สภาพร่างกาย และอายุ
พอเรื่องเปลี่ยน (เปลี่ยนชุด โดนทำร้าย แผลหาย แก่ขึ้น) ก็สร้าง state ใหม่
ทุกช็อตในบทต้องระบุว่าใช้ state ไหน โมเดลจะไม่ต้องเดาเลยว่าตัวละครหน้าตาเป็นยังไงในช็อตนั้น

| ชนิดของ state | ตัวอย่างของ CEO |
|---|---|
| ชุด / บทบาท | ลุงขายของ → ตอนถูกจับ หน้าเครียด เปลี่ยนชุด |
| บาดแผล (ไล่ระดับ) | ช้ำ 1 → ช้ำ 2 → ช้ำ 3 → พันแผล → แกะผ้าพันแผลแล้วเหลือรอยจาง → หายดี (กลับไปใช้ state ปกติ) |
| ผม / หนวด | ผมสั้น · กลาง · ยาว / หนวดสั้น · ยาว |
| อายุ | เด็ก · วัยยี่สิบต้นๆ · วัยทำงาน (อายุเปลี่ยน = หน้าเปลี่ยน ต้องทำ FACE plate ใหม่ด้วย) |

**สิ่งที่ไม่ใช่ state: อารมณ์บนหน้า** (โกรธ ร้องไห้ ประจบ) เพราะอารมณ์เปลี่ยนทุกช็อต
ถ้าไปใส่ในเพลต สีหน้าจะค้างติดไปทุกช็อต อารมณ์จึงเขียนในบทและพรอมต์ของแต่ละช็อตแทน (ดูหัวข้อ "อารมณ์" ใน SCRIPT v2)
**ยกเว้นสภาพร่างกายที่ติดตัวไปหลายช็อต** เช่น ตาบวมแดงหลังร้องไห้ทั้งคืน หรือเหงื่อโชกเสื้อยับ แบบนี้นับเป็น state

## รูปแบบเพลต (ทำใน ChatGPT แล้วอัปโหลดเข้า Flow เป็น Element)

| เพลต | คืออะไร | ใช้ทำอะไร |
|---|---|---|
| `<ตัว>__face` | ครึ่งตัวบน หน้าตรงเอียงสามส่วนสี่ สีหน้าเฉยๆ ฉากหลังเทาอ่อนเรียบ แสงนุ่มเท่ากันทั้งหน้า | ตัวยึดหน้าตา (identity) ใช้ร่วมกับทุก state ในวัยเดียวกัน |
| `<ตัว>__<state>` | เต็มตัวหัวจรดเท้า คนเดิมหน้าเดิม ใส่ชุดและอยู่ในสภาพของ state นั้น ฉากหลังเทาเดียวกัน | ใช้เป็น chip ของตัวละครในช็อตที่ใช้ state นั้น |

ทุก state ของตัวละครหนึ่งตัว **ต้องทำต่อในแชตเดียวกับ FACE** (runner `--continue`)
ChatGPT จะแก้จากภาพที่อยู่ในแชตแล้ว หน้าจึงไม่หลุด (CEO 2026-09-24) ถ้าเปิดแชตใหม่จะได้คนใหม่

บทเรียนจาก banchi: ภาพเต็มตัวของวิทย์ในเครื่องแบบ พอเข้าช็อตสองคนกับพ่อ หน้ากลายเป็นหน้าพ่อ
(ภาพนั้นสร้างจากคำบรรยายใน Flow ไม่ใช่แก้จากภาพเดิม)
ถ้าช็อตสองคนมีหน้าเพี้ยนอีก ให้ใช้วิธีที่วัดแล้วว่าได้ผล คือ `__face` + เพลตชุดที่ไม่มีคนใส่
ข้อจำกัดของ Flow คือแนบได้ 3 chip ต่อช็อต ต้องวางแผน chip ทีละช็อต

## ตัวละคร (รอบนี้ 18 ภาพ)

| state id | ลักษณะ + ชุด | ใช้ในช็อต |
|---|---|---|
| **ยายบุญ** (70) · `yai__face` | หญิงไทย 70 ตัวเล็กผอม ผิวคล้ำแดด ริ้วรอยลึก ตาใจดี ผมสีดอกเลาตัดสั้น | ทุกช็อตของยาย |
| `yai__collect` | เสื้อแขนยาวลายดอกซีดๆ กางเกงผ้าดำหลวม หมวกผ้าปีกกว้าง ถุงมือผ้า ผ้าขนหนูพาดคอ รองเท้าแตะ มีฝุ่นเปื้อน | S1–S5, S9–S15, S22–S28, S69–S71 |
| `yai__home` | เสื้อคอกลมแขนสั้นสีพาสเทลซีด ผ้าถุงลายไทย เท้าเปล่า ผมหวีเรียบ | S6–S7, S19–S21, S29–S30, S35–S38, S54–S68, S73–S74 |
| **เสี่ยวัฒน์** (50) · `sia__face` | ชายไทยเชื้อสายจีน 50 ตัวอ้วนพุงยื่น หน้ากลม ตาเล็ก ผมดำเสยเรียบ ขมับหงอก หนวดบางๆ | ทุกช็อตของเสี่ย |
| `sia__boss` | เสื้อเชิ้ตลายฉูดฉาดแขนสั้นปลดกระดุมทับเสื้อกล้ามขาว สร้อยคอทองเส้นใหญ่ นาฬิกาทอง กางเกงขาสั้นกากี รองเท้าแตะหนัง | S1–S34 (ลาน) |
| `sia__factory` | เสื้อโปโลสีครีมไม่มีโลโก้ ยัดในกางเกงสแล็คสีเข้ม เข็มขัดหนัง สร้อยทอง แว่นดำดันไว้บนหัว | S40–S53 (โรงงาน) |
| `sia__humbled` | โปโลครีมตัวเดิม ยับ เหงื่อโชก ชายเสื้อหลุด ไม่มีแว่น ผมยุ่งตกลงหน้าผาก **ถอดสร้อยทองแล้ว** | S54–S68 (บ้านยาย) |
| `sia__reformed` | เสื้อเชิ้ตงานสีเทาเรียบ ผ้ากันเปื้อนผ้าใบ ไม่มีเครื่องประดับเลย ผมตัดสั้นเรียบร้อย | S69–S72 |
| **กล้า** (16) · `kla__face` | เด็กชายไทย 16 ผอม ผมดำสั้นเรียบร้อย ตาจริงจัง | ทุกช็อตของกล้า |
| `kla__school` | ชุดนักเรียน ม.ปลาย: เสื้อเชิ้ตขาวแขนสั้น **ไม่มีปัก ไม่มีตรา ไม่มีชื่อ** กางเกงขายาวดำ เข็มขัดดำ รองเท้าดำ | S1–S18, S22–S28 (หลังเลิกเรียน) |
| `kla__work` | เสื้อยืดเทาเรียบ ยีนส์เก่า ถุงมือผ้า รองเท้าผ้าใบ | S33–S53, S55–S58, S72 |
| **ต่อ** (11) · `tor__face` | เด็กชายไทย 11 ตัวเล็ก แก้มกลม ผมทรงกะลา | ทุกช็อตของต่อ |
| `tor__school` | ชุดนักเรียนประถม: เสื้อเชิ้ตขาวแขนสั้น **ไม่มีปัก ไม่มีตรา** กางเกงขาสั้นกรมท่า ถุงเท้าขาว รองเท้าดำ กระเป๋าเป้ | S29, S69, S73 |
| `tor__home` | เสื้อยืดตัวโคร่งซีด ไม่มีลาย กางเกงขาสั้น เท้าเปล่า | S6–S7, S19–S21, S30, S36–S38, S54–S68, S74 |
| **ป้า** (60, ไม่มีชื่อ) · `pa__face` | หญิงไทย 60 ร่างท้วม ตาคม แว่นอ่านหนังสือห้อยสาย | — |
| `pa__collect` | หมวกสานปีกกว้าง เสื้อลายสก๊อตแขนยาว ปลอกแขน กางเกงเข้ม แว่นห้อยสาย | ทุกช็อตของป้า |
| **คนชั่ง** (45) · `scaleman__work` | ชายไทยหน้าแข็ง เสื้อเชิ้ตงานสีฟ้าซีดไม่มีโลโก้ หมวกแก๊ปไม่มีโลโก้ รองเท้าบู๊ตยาง ดินสอเหน็บหู | S41–S50 |
| **คนงาน** (30) · `worker__work` | ชายไทย ชุดงานสีเทา ถุงมือ ไม่มีโลโก้ | S46, S48 |

รวม 18 ภาพ (FACE 5 · state 13) ใน 7 แชต แชตละตัวละคร

**กฎที่ใช้กับทุกเพลต:**
- ไม่มีตัวหนังสือ โลโก้ ป้ายชื่อ หรือตราปักบนเสื้อ (Flow จะวาดตัวหนังสือเพี้ยน และชุดนักเรียนจริงมีปักชื่อ)
- ทุกคนเป็นคนธรรมดาที่แต่งขึ้น ไม่ใช่ดารา
- ผิวจริง มีรูขุมขนและริ้วรอย

## Prop + Location (round 1 — CEO "สร้าง Prop + Location ในแต่ละ State ได้เลย" 2026-09-25)

Prompts: `docs/ops/briefs/taachang-props-locations-round1.json`. A prop that belongs to a location is cropped out in
**the same chat as that location**, so it matches the one in the scene exactly: the yard scale comes from the yard
picture and the jar from the room picture.

| id | state / what it is | used in shots | chat |
|---|---|---|---|
| `lan__busy` | the yard in full swing, with the old platform scale | EP1–EP3 (S1–S31) · EP6 (S69–S72: the same scale moved out to the entrance, written in the prompt) | LAN |
| `yard_scale` | the old platform scale cropped out of the yard; dial has tick marks only, no numbers | S1–S28 | LAN |
| `lan__halfempty` | same yard with the goods mostly gone | S32–S34 | LAN |
| ~~`lan__needle`~~ | **dropped (CEO 2026-09-25: "ไม่เอา")**; there is no new scale | — | — |
| ~~`needle_scale`~~ | **dropped** as above | — | — |
| `baan__outside` | **v2 (CEO 2026-09-25): a rural corrugated-tin shack by the canal, patched, a little cluttered.** v1 was a teak house, which read as too expensive | S35, S54 | BAAN2 |
| `baan__inside` | **v2: inside the tin shack.** Bare concrete floor, thin plastic mat, no real furniture, the jar sitting on stacked plastic crates, clothes hung on nails. v1 was a polished teak Thai-house room: "เป็นบ้านเรือนไทยที่ราคาสูง" | S6–S7, S19–S21, S30, S36–S38, S55–S68, S73–S74 | BAAN2 |
| `jar__third` | glass jar one third full of pebbles | S6 | BAAN |
| `jar__full` | the same jar, nearly full | S21, S36–S38, S53–S57 (poured into piles on the mat at S57 is written in the prompt) | BAAN |
| `soi__canal` | canal-side path with a row of electricity poles (ยาย counts the poles) | S15, S29, S75 | — |
| `fac__weigh` | factory weigh yard, truck scale, bale stacks | EP4 (S40–S53) | — |
| `sack` | white woven sack of clear bottles, no printing | throughout | — |
| `cart` | ยาย's steel push-cart | S9, S15, S27–S29, S31, S71 | — |
| `pickup__empty` | เสี่ย's white pickup, empty bed, no plates | S33 | PICKUP |
| `pickup__loaded` | the same pickup piled with bales | S40, S49–S51, S54 | PICKUP |
| `money` | pastel fake banknotes (the skill's prop-money block) | S2, S4, S7, S13–S14, S19–S22, S30, S50, S62–S63 | — |
| `wallet` | old brown leather wallet | S3–S5 | — |
| `envelope` | plain envelope with nothing written on it | S73 | — |
| `notebook` | light-blue school notebook, cover blank | S74 | — |

19 images in all: 7 location + 12 prop. Round 1 dropped 2 of them (needle yard, needle scale), and round 2 redoes the house (2 images).

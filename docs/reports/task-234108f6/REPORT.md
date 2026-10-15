# REPORT task-234108f6

## Overview

Translation of Thai explanatory prose to English across 18 specified `SKILL.md` files pursuant to CEO order of 14 October 2026. The objective of the CEO order is to translate internal explanatory text to English to reduce token consumption across agent invocations, while preserving language-specific content, proper names, CEO quotes, UI strings, prompts, and viewer-facing copy intact.

Strict adherence to all translation and keep rules was maintained, following the constraint to operate exclusively via file tools (`view_file`, `replace_file_content`, `write_to_file`) with zero shell execution.

## Files Changed

1. `.claude/skills/CMO_Standard_Story_ThaiMoralDrama/SKILL.md`
   - Translated measurement notes in lines 161–163 explaining script syllable count and speech density from Thai to English within the preformatted code block.

No other files required modification. All other Thai text across the remaining 17 files falls strictly under Keep Rule 2 (CEO quotes, titles/proper names, Thai UI labels, viewer-facing text/dialogue, prompts, and source material) or Keep Rule 3 (SKILL.md YAML frontmatter).

---

## Per-File Audit: Thai Retained and Applicable Keep Rules

### 1. `.claude/skills/CMO_Knowledge_Flow_Omni1.1/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Thai UI labels):** Flow UI control labels, tabs, buttons, dialog titles, placeholders, attributes, and error cards (`องค์ประกอบ`, `เฟรม`, `เริ่ม`, `สิ้นสุด`, `สลับเฟรมแรกและเฟรมสุดท้าย`, `เลือกรูปภาพเฟรม`, `ไม่พบชิ้นงาน`, `ตัวอย่างบทสนทนา`, `ปรับแต่งประสิทธิภาพ`, `ชื่อของเสียง`, `<Preset> คัสตอม`, `แสดงตัวอย่าง`, `บันทึกเสียงใหม่`, `เพิ่มลงในตัวละคร`, `ดาวน์โหลดสื่อ`, `ดาวน์โหลดแบบกลุ่ม`, `สื่อทั้งหมด`, `วิดีโอ`, `ตัวละคร`, `ฉาก`, `เครื่องมือ`, `ถังขยะ`, `ยุบ`, `รายการที่อัปโหลด`, `รูปภาพที่อัปโหลด`, `เปลี่ยนชื่อ`, `สร้างตัวละคร`, `เพิ่มไปยังพรอมต์`, `เริ่มสร้าง`, `การตั้งค่า Agent`, `ดาวน์โหลดฉาก`, `เครดิต Google Flow N เครดิต`, `รายละเอียดบัญชี`, `บัญชี Google`, `720p ขนาดดั้งเดิม`, `1080p เพิ่มความละเอียดแล้ว`, `4K · 50 เครดิต`, `เสร็จสิ้น`, error and policy warning cards: `ล้มเหลว ขออภัย สร้างวิดีโอนี้ไม่สำเร็จ...` and `ล้มเหลว การสร้างนี้อาจละเมิดนโยบายของเรา...`).
  - **Rule 2 (CEO quotes & attributed words):** Explicit CEO quotes with dates ("ต้อง Scope ให้ดีเพราะ ที่เราทำคือ Model อะไร...", "การใช้งาน Chrome google flow ไปใช้ใน winbox นะ...", "ตามนั้น", "ทดสอบด้วย 360p ถูกแล้ว...", "การ Generate x2 x3 x4...", "ใช้ซ้ำจะดูปลอมทันที", "เสียงถูกแล้ว", "Yes -> ให้ Agent ใช้ Comutir use ทาเองได้นะ").
  - **Rule 2 (Titles and proper names):** Film titles (`«จุดจบของเจ้าหนี้นอกระบบ»`, `«ตาชั่งของเสี่ย»`, `«เงินที่พ่อตั้งใจหา»`, `«ขายชื่อ EP1»`, `«ขายชื่อ»`); Character names (`ต้น`, `สมชาย`, `วิทย์`, `เจ๊หมวย`, `น้องเอ`, `ยายเย็น`).
  - **Rule 2 (Dialogue / Viewer-facing text / Prompts / Signage):** Refused dialogue lines tested for policy boundary (`อย่าเพิ่งไปที่ร้านเลยครับ ลูกผมอยู่ที่นั่น`, `อันนี้ค่ายาแม่ ห้ามแตะเด็ดขาด`); sign text (`"ก๋วยเตี๋ยว - เครื่องดื่ม"`); trigger words and amounts (`"ค่าไถ่"`, `"ค่าซื้อนาคืน"`, `"สองแสนสามหมื่น"`).
  - **Rule 3 (Frontmatter):** Frontmatter tags and descriptions (`องค์ประกอบ`, `"ยิง Flow"`, `"เสียงตัวละคร"`).

### 2. `.claude/skills/CMO_Standard_Story_ThaiMoralDrama/SKILL.md`
- **Files changed:** Yes (lines 161–163 translated).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Format and series titles (`ละครสั้นคุณธรรม`, `ฟ้ามีตา`); reference episode titles (`ศาลเตี้ย`, `เด็กในบ้าน`, `ปีศาจ`, `เจ้าที่`); production film titles (`«บัญชี»`, `«ขายฝากนาแม่»`, `«ตาชั่งของเสี่ย»`, `«น้ำไม่เลือกบ้าน»`); character names (`ยายกลั่น`, `แต้ว`, `สมชาย`, `พี่จี๋`, `พิม`, `วิทย์`, `เชิด`, `ยายเย็น`).
  - **Rule 2 (Quoted phrases & concept titles):** `ทำดีได้ดี ทำชั่วได้ชั่ว` (traditional moral drama concept heading); formula tag `S1 พูด · S2 เงียบ · S3 บังคับพูด · S4 แล้วแต่`; engagement bait phrases (`"พิมพ์ 1"`, `"แท็กเพื่อน"`, `"แชร์เลย"`); posting frequency phrase (`"ทุกสัปดาห์"`).
  - **Rule 2 (CEO quotes & attributed words):** Explicit CEO quotes ("คนร้ายที่ชั่วแบบการ์ตูน ก็ทำได้นะ", "เส้นเรื่องความสมเหตุสมผล...", "คนดูรู้สึกให้ครอบครัวนี้ผ่านมันไปให้ได้...", "ตัวละครขับเนื้อเรื่อง...", "ดูไม่รู้เรื่องเลย", "ตัวละครทำอะไรอยู่ให้พูดไปด้วย", "กฎนี้เปลี่ยนได้ทุกเมื่อ...", "ตัวละครดูไร้อารมณ์...", "รอบนี้ขอ Acting แบบล้นๆ...", "ของผมผมกินเอง -> ควรเว้นวรรคด้วยนะ...", "Scope อยู่ที่ 8 - 12 mins...", "คนดูระหว่างกินข้าวไปด้วยได้", "ฉันเคยหยุดดูซีรี่จีน...", "หาลิงก์ไม่เจอ ไม่ได้แปลว่าโพสต์ไม่ติด", "รอบนี้ ขอ 9 นาที แบบตัดจบแบบ ซีรี่ จีนเลย...").
  - **Rule 2 (Dialogue / Viewer-facing text / Sample posts / Prompts):** Dialogue line examples (`"...อีกแล้ว"`, `"โดนปฏิเสธอีกแล้ว...เฮ้อ ที่นี่ก็ไม่รับ"`, `"ข้างล่างเสียงดังไปไหมครับย่า"`, `"ย่าจะบอกอะไรผมเหรอ"`, `ของผม ผมกินเอง`, `ไม่มีเหลือหรอก ป้า`, `ขอบคุณที่เอาออกมาฝากนะคะ ข้าวสารถุงนี้ หุงได้อีกหลายหม้อเลย`, `ผมผม, ของเขาเขา, ยายยาย`, `เมื่อคืนผมส่งใบสมัครไปอีกสองที่พ่อ`, `…ไปอีกสองแห่งแล้วนะพ่อ`, `เฮ็ดหยัง, นำกัน, เด้อ, บ่`, `ฟุตบาท`, `"หนึ่งปีต่อมา"`); sample first comment for Facebook post (lines 583–586: `ถ้าเป็นคุณ เจอตาชั่งร้านเสี่ยแบบนี้ จะทำยังไง? 🤔...`).
  - **Rule 2 (Thai UI labels):** Facebook UI controls (`[aria-label="เมนู"]`, `"ลบ"`, `สนใจ / ไม่สนใจ / รายงาน`, `"ความคิดเห็นจาก ละครสั้นคุณธรรม by ILAG Studio"`, `เมนู#0`, `ไม่สำเร็จ`).
  - **Rule 3 (Frontmatter):** Frontmatter tags and descriptions (`«ละครสั้นคุณธรรม»`, `ฟ้ามีตา`, `«บัญชี»`, `«เงินที่พ่อตั้งใจหา»`).

### 3. `.claude/skills/CMO_Standard_BlackLiquidity_Script/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Source material / Legal statutes / Regulatory text):** BOT official statement quote (`"โฆษณา ประกาศ หรือชักชวนประชาชน"`); Thai statutes (`พ.ร.ก. การกู้ยืมเงินที่เป็นการฉ้อโกงประชาชน พ.ศ. 2527`, `พ.ร.บ.สัญญาซื้อขายล่วงหน้า 2546`); licensed financial role (`ผู้แนะนำการลงทุนตราสารอนุพันธ์`).
  - **Rule 2 (Dialogue / Viewer-facing scripts / Captions / Legal label):** Script sample lines (`"ก่อนเลือกโบรกเจ้าไหนก็ตาม..."`, `"ผมไม่ได้แนะนำให้ใช้เจ้าไหน แค่ชี้วิธีดูให้เป็น"`, `"นี่คือหลักฐานตอนที่กูพยายามเข้าเว็บ"`, `"ใครใช้โบรกนี้รีบเข้าเว็บเช็กด่วนเลย..."`); CTA copy (`"คอมเมนต์คำว่า เช็กลิสต์ ถ้าอยากได้ตารางตรวจโบรก"`); prohibited vs approved script phrases table (`เปิดผ่านลิงก์ผม`, `ลิงก์ใต้คลิป`, `รีเบท $x ต่อ Lot`, `deal ตรง`, `ทักมา`, `ทักใต้คลิป`, `ใช้เจ้านี้`, `แนะนำเจ้านี้`, `สมัคร`, `เปิดบัญชี`, `"เกณฑ์ที่ควรดูคือ…"`, `"ก่อนตัดสินใจ ให้ตรวจ…"`); legal disclaimer label (`"เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง"`).
  - **Rule 2 (CEO quotes):** Direct quotes ("อย่าใช้ศัพท์เทคนิคเยอะ เอาง่ายๆ ให้คนดูเข้าใจ", "เราสอนเขาก็จริง...", "มึงดูภาพเอาเอง", "ตอนเรียกชื่อหรือใน Script เขียนไทยได้...", "เขาอ้างว่า").
  - **Rule 2 (Quoted phrases / Vocabulary comparisons / TTS transliterations):** Vocabulary comparison table (`โดเมน · ทะเบียนโดเมน · WHOIS · DNS` vs `ชื่อเว็บ · ที่จดชื่อเว็บ · "ไม่มีใครเป็นเจ้าของชื่อเว็บนี้แล้ว"`, `หน้าเออเรอร์ · เซิร์ฟเวอร์ล่ม` vs `หน้าเว็บขึ้นว่าเข้าไม่ได้`, `หน่วยงานกำกับ` vs `"หน่วยงานการเงินของอังกฤษ"`); TTS transliterated brand names and numbers (`ติ๊กต๊อก`, `เฟซบุ๊ก`, `ไลน์`, `เซนต์วินเซนต์`, `วิกิเอฟเอ็กซ์`, `"วีทู"`, `"วิทูล"`, `เก้าพันแปดร้อยยี่สิบห้า`).
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 4. `.claude/skills/CMO_Procedure_BlackLiquidity_Cut/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (CEO quotes):** Direct quotes ("นี่คือคลิปการตัดต่อมืออาชีพเลยนะ", "Realfootage สำคัญกว่า B-Roll", "จดเกือบชิดขอบจอ แต่ห้ามชิดจนเกินไป ให้มีช่องว่างดูลอดผ่านได้", "เบี้ยวไปทางซ้าย", "การเอาลง เอาลงแบบ smooth ด้วย มี Animation", "sub title style ที่ขึ้น มันไม่ใช่แบบเดียวกับที่ EP ก่อนหน้าทำไว้ … Skill issue แน่นอน").
  - **Rule 2 (Thai UI labels):** TikTok app navigation (`เพื่อน | กำลังติดตาม | สำหรับคุณ`).
  - **Rule 2 (Viewer-facing copy / Captions / Legal disclaimers / Credits):** Video overlay legal label (`เนื้อหาเพื่อการศึกษา ไม่ใช่คำแนะนำหรือการชักชวนลงทุน · การลงทุนมีความเสี่ยง`); caption disclaimer block (`คลิปนี้จัดทำเพื่อให้ความรู้และวิเคราะห์ข้อมูลสาธารณะเท่านั้น...`); image credit overlay (`ขอบคุณภาพจาก <source>`); on-screen headline text (`"10 ตัว"`, `"2 ตัวแรก"`, `"ค่า SPREAD สูงเพราะ?"`, `"สเปรดต่ำสุด GOLD 3"`, `{ c: "bl-md", h: '<span class="y">Rebate</span> คือส่วนหนึ่งของ<span class="nb">สเปรด</span>หรือค่าคอม' }`); spoken dialogue excerpts (`"ใครฟังมาถึงตรงนี้"`, `"ผมบอกความจริงที่ไม่มีใครบอกมึง"`, `"มึงเป็นคนกด มึงเป็นคนเสี่ยง แต่คนอื่นกินเงินมึงเงียบ"`, `"เงินทุกล็อต… ควรเป็นของมึง"`, `กู`).
  - **Rule 2 (Source material / Legal statutes / Regulatory text):** BOT quote `"โฆษณา ประกาศ หรือ ชักชวนประชาชน"`; statute `พ.ร.ก. การกู้ยืมเงินที่เป็นการฉ้อโกงประชาชน 2527`.
  - **Rule 2 (Quoted phrases / TTS transliterations / ASR mishearing / Regex):** ASR mishearing examples (`"แชร์"` for `"แฉ"`, `"ทันวา"` for `"ธันวา"`); regex grep pattern (`grep -i "ล็อกถอน\|deadline\|lock"`); TTS vs caption spellings (`โบร๊ก`, `โบรก`, `วิกิเอฟเอ็กซ์`); word-break wrapping examples (`ส|เปรด, เจ้า|ไหน, ข้อ|ความ`); Buddhist calendar date strings (`20 พ.ค. 69`, `23 ก.ย. 69`).
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 5. `knowledge/content-knowledge/skills/trader-story-scripts/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names; Source material):** Titles of reference YouTube videos in index table (`ถอดรหัส เด็กอายุ 16 เทรด Forex...`, `ถอดรหัส แม่บ้านชาวญี่ปุ่น...`, `หนุ่มวัย 19 เทรด จนรวย...`, `ไม่มีเงินเรียนต่อ...`, `เคล็ดลับ เริ่มลงทุน...`, `เทรดเดอร์ Forex ร้อยล้าน...`, `อะไรบ้างที่ทำตอนนี้...`, `ตำนานการ 'เทรดขาดทุน'...`, `เรื่องวุ่นๆ Do Kwon...`, `7 นิสัยที่ต้องมี...`).
  - **Rule 2 (Quoted phrases / Source material):** Auto-caption error examples (`"เอ็ดเวิร์ด biggest"`, `"you have ดอทคอม"`).
  - **Rule 3 (Frontmatter):** Frontmatter trigger phrases (`"สคริปต์เล่าเรื่องเทรดเดอร์"`, `"YouTube script เทรด"`, `"เขียนสคริปต์ช่อง youtube มูนี่เอ็กซ์"`).

### 6. `.claude/skills/CMO_Procedure_ChatGPTImage_LakornCover/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Production and reference drama titles (`«จุดจบของเจ้าหนี้นอกระบบ»`, `«ตาชั่งของเสี่ย»`, `«บัญชี»`, `«จุดจบ»`, `คลื่นชีวิต`, `น้ำตากามเทพ`, `หัวใจศิลา`, `ฟ้าจรดทราย`, `ร่าน`, `เรยา`, `ลายกินรี`, `ลดา`, `เลือดเจ้าพระยา`, `18 มงกุฎ`, `"รู้หรือไม่?"`); brand name (`ละครสั้นคุณธรรม`).
  - **Rule 2 (Thai UI labels):** ChatGPT send button `aria-label ส่ง`; ChatGPT error message `"ไม่สามารถโหลดการสนทนา ChatGPT นี้ได้"`; login link `ลงชื่อเข้าใช้`.
  - **Rule 2 (CEO quotes):** Direct quotes ("เห็นความเป็นเอกลักษณ์ของตัวหนังสือไหม", "ทำปกมาให้เลือก 3 แบบ", "ตัวหนังสือไม่ใช่" / "ไม่เหมือนละคร", "ดีกว่าเสียเครดิต API ChatGPT เพราะฉันจ่าย GPT PLUS อยู่แล้ว", "ตำรวจใส่ชุดธรรมดา ไม่งั้นปกคลิปจะเฉลยตอนจบ", "ปรับ ขยาย text ตามพื้นที่ที่มีความเหมาะสมได้...", "คนแบบนี้ถูกแล้ว ติดแค่ข้อความ … มันจะมีจุดที่อยู่ประจำของมัน").
  - **Rule 2 (Prompts sent to image models):** Template placeholders `<ส่วนเล็ก>`, `<ส่วนใหญ่>`.
  - **Rule 2 (Viewer-facing poster copy / CLI args):** Airtime/date examples (`“คืนนี้ 21:20”`, `“Coming Soon”`, `--cta "ดูจบในตอนเดียว"`); billing line (`“ภาพและเสียงสร้างด้วย AI”`).
  - **Rule 2 (Text meant for Thai readers / CEO communication template):** Lines 178–183 (`ปก 3 แบบ (ส่งไฟล์ด้านบน)...`).
  - **Rule 2 (Quoted phrases / Characters / Tone marks):** Thai character mark examples (`ห, ร or บ`, `ุ ("หุ", "บุ")`, `ช in ตาชั่ง as mai tho ้ instead of mai ek ่ ("ชั้ง")`, `ำ in น้ำ`, `น้า`, `า`).
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 7. `.claude/skills/CMO_Standard_Story_FamilyDogSeries/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Character names (`มีมี่`, `ข้าวเหนียว`), family member names (`วิทย์`, `อุ้ย`, `พ่อสมบัติ`, `แม่พิม`, `พี่ท็อป`, `น้องมาย`), series title (`«บ้านนี้มีมีมี่»`), film title (`«ตาชั่งของเสี่ย»`).
  - **Rule 2 (CEO quotes & attributed facts):** Family story facts and direct CEO rulings ("ตรวจตาทั้งหมด แล้วยิงเพิ่มในฉากที่เสียได้เลย", etc.).
  - **Rule 2 (Dialogue / Viewer-facing scripts / Prompts):** Spoken dialogue samples (`'น้ำ! น้ำเต็มหน้าบ้านเลย! มีมี่กลัวน้ำที่สุดในโลก! แต่แม่ขา รอมีมี่ด้วย!'`, `«อย่าเดินไกลนะ»`, `«ลูก»`, etc.).
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 8. `.claude/skills/CMO_Workflow_ShortFilm/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Format and film titles (`ละครสั้นคุณธรรม`, `ฟ้ามีตา`, `«จุดจบของเจ้าหนี้นอกระบบ»`, `«ตาชั่งของเสี่ย»`).
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-18, 2026-09-23, 2026-09-25.
  - **Rule 2 (Thai UI labels / Dialogue / On-screen text):** UI error strings, end cards, dialogue quotes.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 9. `.claude/skills/CMO_Gate_Flow_Omni1.1_Continuity/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Characters (`วิทย์`, `ต้น`, `ป้าข้างบ้าน`, `แม่คำปุน`, `เสี่ยชัย`); film titles (`«จุดจบของเจ้าหนี้นอกระบบ»`, `«ตาชั่งของเสี่ย»`).
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-18, 2026-09-23, 2026-09-25.
  - **Rule 2 (Dialogue / Prompts / Banknote text / Refused phrases):** Dialogue examples, prop banknote text, prompt keywords.
  - **Rule 2 (Thai UI labels):** Flow UI buttons and labels.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 10. `.claude/skills/CMO_Workflow_MimiPage_Weekly/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Page title `«บ้านนี้มีมีมี่»`, poster titles, character name `มีมี่`.
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-28, 2026-09-30, 2026-10-01.
  - **Rule 2 (Viewer-facing post copy / Comments):** Facebook post captions, comments, script tags `[จริง]`/`[แต่ง]`.
  - **Rule 2 (Thai UI labels):** Facebook UI labels.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 11. `.claude/skills/CMO_Workflow_LakornSerial/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Format name `ละครสั้นคุณธรรม`, film title `«ขายชื่อ»`.
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-25, 2026-09-26, 2026-10-01.
  - **Rule 2 (Viewer-facing text / Dialogue / Captions):** End card copy, sample post captions, dialogue excerpts.
  - **Rule 2 (Thai UI labels):** Facebook UI button `"ดูเพิ่มเติม"`.
  - Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 12. `.claude/skills/CMO_Procedure_RealFootageCapture/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-23.
  - **Rule 2 (Thai UI labels):** Web UI labels from WikiFX and brokers.
  - **Rule 2 (Regulatory / Source material):** BOT regulatory terms.
  - **Rule 2 (Dialogue):** Sample spoken lines.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 13. `.claude/skills/CMO_Knowledge_Cinematography_ShortMovie/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles, genre categories, trigger phrases):** `หนังสั้น`, `ละครสั้น`.
  - **Rule 2 (CEO quotes):** Direct quote from 2026-09-23.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 14. `.claude/skills/CMO_Gate_Flow_Omni1.1_FilmQC/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Film titles `«จุดจบของเจ้าหนี้นอกระบบ»`, `«ตาชั่งของเสี่ย»`, character name `ต้น`.
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-18, 2026-09-23.
  - **Rule 2 (Subtitle/Dialogue quotes / QC tables):** Spoken dialogue quotes, QC table labels.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 15. `.claude/skills/CMO_Knowledge_MiniMax_H3/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-23, 2026-09-25.
  - **Rule 2 (Prompts / UI labels):** Prompt keywords `หน้าแดง`, `หูแดง`; UI label `'ปิด Colab'`.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 16. `.claude/skills/CMO_Procedure_CharacterSheet/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (Titles and proper names):** Film titles `ประตูวาป`, `«ตาชั่งของเสี่ย»`.
  - **Rule 2 (CEO quotes):** Direct quote from 2026-09-24.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

### 17. `.claude/skills/CMO_Knowledge_Seedance2.5_Higgsfield/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-08, 2026-09-23.
  - **Rule 3 (Frontmatter):** Frontmatter trigger phrases kept verbatim.

### 18. `.claude/skills/CMO_Gate_Champa_Seedance2.0_ShortMovieQC/SKILL.md`
- **Files changed:** None (0 edits needed).
- **Thai retained:**
  - **Rule 2 (CEO quotes):** Direct quotes from 2026-09-06, 2026-09-18.
  - **Rule 2 (Thai UI labels / Tags / Spoken lines):** UI labels, prompt tag `@ภาพN`, Thai film line.
  - **Rule 3 (Frontmatter):** Frontmatter block kept verbatim.

---

## Lines Unsure About (Rule 5)

1. **`.claude/skills/CMO_Procedure_ChatGPTImage_LakornCover/SKILL.md` lines 178–183 (`## Output format (to the CEO)`):**
   ```text
   ปก 3 แบบ (ส่งไฟล์ด้านบน)
   - A · <concept> — <one line on why it fits the story>
   - B · …
   - C · …
   สะกดชื่อเรื่องถูกทุกแบบ (ซูมเช็คทีละตัว) · ไม่มีอะไรจากตอนจบ · อยู่ในกรอบฟีด 4:5
   เลือกแบบไหน หรือจะแก้ตรงไหนต่อในแชตเดิมได้ (~2 นาที/รอบ)
   ```
   *Rationale for retaining in Thai:* This block defines the exact message format to be sent to the Thai CEO in chat. Under Rule 2 ("text meant for Thai readers or viewers"), output directed to the Thai CEO remains in Thai. Per Rule 5, it is flagged here for reviewer awareness.
2. **`.claude/skills/CMO_Procedure_ChatGPTImage_LakornCover/SKILL.md` lines 111–112:**
   ```text
   line 1, smaller: <ส่วนเล็ก>
   line 2, much larger: <ส่วนใหญ่>
   ```
   *Rationale for retaining in Thai:* These are placeholder tags within the prompt template sent to the image model. Under Rule 2 ("prompts sent to image or video models"), they were retained in Thai.
3. **`.claude/skills/CMO_Standard_Story_ThaiMoralDrama/SKILL.md` line 98:**
   ```markdown
   ### 7. ทำดีได้ดี ทำชั่วได้ชั่ว — and EVERY named character gets a conclusion (CEO)
   ```
   *Rationale for retaining in Thai:* `ทำดีได้ดี ทำชั่วได้ชั่ว` is the traditional Buddhist moral drama proverb and core concept name. Retained under Rule 2 (quoted phrase / concept title) and Rule 4 ("Keep every heading... Do not reword English that is already there, and add or remove nothing").

---

## Validation Performed

1. Inspected every Thai line across all 18 files using `view_file` to verify character-by-character against Keep Rules 2 and 3.
2. Verified that frontmatter blocks between `---` boundaries in all 18 files remain 100% untouched.
3. Checked headings, tables, links, code block fences, numbers, dates, and paths to ensure complete structural preservation.
4. Used `replace_file_content` for in-place edit of `.claude/skills/CMO_Standard_Story_ThaiMoralDrama/SKILL.md` with exact string matching.

## Limitations

- Analysis and edits were conducted strictly via file tools (`view_file`, `replace_file_content`, `write_to_file`) without running shell commands, per the worker contract.

## Blockers

- (none)

## Skill learning

- `thai_inventory.py` lexer artifact: The inventory tool flagged unquoted Thai text in `SKILL.md` files (such as character names, UI button strings, model failure cards, and script examples) under `skill_body` / `translate`. Detailed human inspection revealed that nearly all of these occurrences fall squarely under Keep Rule 2 (UI labels, proper names, CEO quotes, viewer-facing text). Evaluating semantic context is essential before translating technical skill documents.

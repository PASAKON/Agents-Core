# BrandPrompt TH — Production Playbook

Locked reference for (1) poster JSON schema + 5 layout templates, (2) FB caption
style. Read this before starting a new gen round or writing a new post —
don't re-derive from scratch each time.

## 1. Poster JSON schema (customer-facing, 100% Thai)

```json
{
  "หมวดสินค้า": "ประเภทสินค้า/บริการ",
  "ชื่อแบรนด์": "ชื่อร้านหรือแบรนด์",
  "หัวข้อหลัก": "ข้อความใหญ่สุด (พาดหัว)",
  "หัวข้อรอง": "ข้อความอธิบายเพิ่ม",
  "โทนสี": "สีหลักที่อยากให้ภาพออกมา",
  "อัตราส่วนภาพ": "4:5 | 1:1 | 4:3",
  "รูปอ้างอิง": ["logo.png"],
  "คำสั่งเทคนิค": "<เลือก 1 ใน 5 template ด้านล่าง>"
}
```

Field names are ALWAYS Thai — validated 2026-07-20 (A/B test: Thai
locked_instructions perform equal or better than English, no quality loss,
sometimes MORE locally authentic).

## 2. The 5 layout templates (`คำสั่งเทคนิค` — pick one per image)

Fit template to category. Mix all 5 across every round for visual variety —
never reuse one template for all categories in a round (round 1 mistake).

| # | Name | Best for |
|---|---|---|
| 1 | Product Hero Float | physical products, food, retail — general default |
| 2 | Before/After Split | transformation-sell: skincare, fitness, dental, cleaning, insurance |
| 3 | Flash Sale Banner | promos, discounts, grand openings, urgency |
| 4 | Minimalist Editorial | premium/luxury: jewelry, fashion, real estate, flowers |
| 5 | Testimonial/Social Proof | trust-needed services: clinics, gyms, courses, wedding |

Full `คำสั่งเทคนิค` text for each — copy verbatim into the JSON, don't reword:

**1. Product Hero Float**
> แสดงสินค้าเป็นวัตถุหลักลอยอยู่กลางภาพเอียงเล็กน้อย ล้อมรอบด้วยองค์ประกอบของสินค้าที่ลอยผ่านฉากอย่างสมจริง ต้องมี: การวางโลโก้แบบพรีเมียม, ตัวอักษรหนาใหญ่, ส่วนแสดงประโยชน์ของสินค้า, ป้ายส่วนผสม, ไอคอนคุณสมบัติ, URL เว็บไซต์, ไอคอนโซเชียลมีเดีย, ป้ายโปรโมชั่นเปิดตัว. สไตล์ภาพ: โฆษณาสินค้าพรีเมียม แสงสตูดิโอแบบภาพยนตร์ ภาพถ่ายสินค้าสมจริง เรนเดอร์บรรจุภัณฑ์เชิงพาณิชย์ แคมเปญการตลาดพรีเมียม องค์ประกอบเคลื่อนไหว สะท้อนแสงเงางาม ระยะชัดลึก แสงแบบวอลุยูเมตริก พื้นผิวสมจริงระดับสูง แบรนด์หรูหรา ดีไซน์ระดับรางวัล เลย์เอาต์บรรณาธิการทันสมัย

**2. Before/After Split**
> แบ่งภาพเป็นสองฝั่งชัดเจน ฝั่งซ้ายแสดงสภาพ 'ก่อน' ฝั่งขวาแสดงสภาพ 'หลัง' ใช้สินค้า/บริการ มีเส้นแบ่งกลางภาพชัดเจน หรือ gradient transition นุ่มนวล ป้ายกำกับ 'ก่อน' และ 'หลัง' ชัดเจน ต้องมี: โลโก้แบรนด์มุมบน, หัวข้อหลักตรงกลางด้านบน, ผลลัพธ์/สถิติที่วัดได้, คำรับรอง/ระยะเวลาที่เห็นผล, ไอคอนคุณสมบัติด้านล่าง, URL เว็บไซต์, ไอคอนโซเชียลมีเดีย. สไตล์ภาพ: ภาพถ่ายสมจริงระดับมืออาชีพ แสงสม่ำเสมอทั้งสองฝั่งเพื่อเปรียบเทียบได้ชัด สะอาดตา น่าเชื่อถือ ไม่พูดเกินจริง

**3. Flash Sale Banner**
> ตัวเลขส่วนลดหรือราคาโปรโมชั่นเป็นองค์ประกอบใหญ่ที่สุดกลางภาพ ใช้ตัวอักษรหนาตัวใหญ่มากสะดุดตา มี badge เร่งด่วน (เช่น 'วันนี้เท่านั้น' หรือ 'จำนวนจำกัด') มุมใดมุมหนึ่ง สินค้าวางเป็นองค์ประกอบสนับสนุนด้านข้างหรือด้านล่าง มีองค์ประกอบตกแต่งแบบ motion/dynamic (เส้นความเร็ว, sparkle, confetti) ต้องมี: โลโก้แบรนด์, วันหมดเขต/เงื่อนไข, ปุ่ม CTA ชัดเจน, ไอคอนโซเชียลมีเดีย, URL หรือเบอร์ติดต่อ. สไตล์ภาพ: สีสันสดใส พลังงานสูง กระตุ้นความเร่งด่วน แต่ยังคงดูเป็นแบรนด์พรีเมียม ไม่ดูราคาถูก

**4. Minimalist Editorial**
> สินค้าชิ้นเดียววางกลางภาพหรือค่อนไปด้านใดด้านหนึ่งตามหลัก rule-of-thirds บนพื้นหลังเรียบสีเดียวหรือ gradient นุ่มนวล เว้นพื้นที่ว่าง (negative space) เยอะรอบสินค้า ตัวอักษรเล็ก บาง สง่างาม จัดวางอย่างมีระเบียบ ไม่ใช้ไอคอนหรือ badge เกะกะ ต้องมี: โลโก้แบรนด์เล็กมุมหนึ่ง, ข้อความหลักสั้นกระชับ 1 บรรทัด, เว็บไซต์หรือช่องทางติดต่อบรรทัดเล็กด้านล่าง. สไตล์ภาพ: ภาพถ่ายสตูดิโอระดับนิตยสารแฟชั่น แสงนุ่มมีทิศทางชัดเจน โทนสีจำกัดไม่เกิน 3 สี หรูหรา สงบ high-end editorial

**5. Testimonial/Social Proof**
> องค์ประกอบหลักคือรูปภาพลูกค้าจริงหรือบุคคลตัวแทน (สมจริง เป็นธรรมชาติ ยิ้มพึงพอใจ) วางเด่นด้านหนึ่งของภาพ พร้อมกล่องคำพูดรีวิว (quote bubble) สั้นกระชับใกล้ๆ มีดาวให้คะแนน 5 ดาวชัดเจน สินค้า/บริการวางเป็นองค์ประกอบเล็กมุมหนึ่ง ต้องมี: โลโก้แบรนด์, ชื่อ-นามสกุลย่อของลูกค้าใต้คำรีวิว, จำนวนลูกค้าที่ใช้บริการรวม, ปุ่ม CTA, ไอคอนโซเชียลมีเดีย. สไตล์ภาพ: ภาพถ่ายสมจริงอบอุ่น เป็นกันเอง น่าเชื่อถือ แสงธรรมชาติ ไม่ปั้นแต่งเกินจริง

## 3. Gen pipeline (fal.ai, GPT Image 2)

- Endpoint: `https://fal.run/openai/gpt-image-2` (text-to-image), `/edit` (with `image_urls` for reference/logo)
- `quality: "medium"` — CEO-approved cost/quality balance (~$0.037–0.053/image depending on ratio)
- `image_size`: `{width:1024,height:1280}` (4:5) · `{1024,1024}` (1:1) · `{1024,768}` (4:3)
- Key: `FAL_API_KEY` in `Agents/.env` (gitignored)
- Scripts: `scripts/gen-round{N}.py` pattern — see round1/2/3 for the template. Each writes `output/brandprompt-th/round{N}/manifest.json` + PNGs.
- Retry-on-timeout (3 attempts) + skip-if-exists — added after round 2 hit a transient timeout.

## 4. Round cadence (10 categories / round, 3 variations each = 30 images/round)

10 rounds total = 100 categories = 300 images. Full round 3–10 category list
and budget tracking: see session notes / CEO chat history (not duplicated
here to avoid drift — this file is template/schema reference only).

Status as of 2026-07-21: rounds 1–3 done (90/300 images, ~$5.09 of $15.90 budget).

## 5. Per-poster page (customer deliverable format)

1 page per poster: image dominant + full JSON prompt below (copy-paste ready
for ChatGPT, no truncation, no dead UI elements like fake "COPY" buttons).
Generator: `build-all-pages.py` pattern (scratchpad) — reads every round's
manifest.json, outputs to `Desktop/BrandPrompt TH/06-per-poster-pages/`.

## 6. FB caption style (BrandPrompt TH page)

**Validated against real MoonieX TradeTech posts 2026-07-20 — NOT the same
style as `playbooks/mooniex-fb-caption-style.md` (that doc is stale/unused
in practice; real posts have zero emoji, long-form narrative).**

- **No emoji. None. Ever.** (confirmed by inspecting live MoonieX TradeTech posts)
- **No bullet symbols, no ❌/✅, no bold headers, no code blocks in the caption text.** Pure prose paragraphs.
- Paragraph separator: a single `.` on its own line (matches MoonieX's real formatting)
- First-person "ผม" narrative voice throughout
- **7-paragraph structure** (matches observed MoonieX post length/shape):
  1. Hook — a specific problem you've observed ("ผมเจอ...")
  2. Why it matters — elaborate with a concrete example/number
  3. Common misconception — name what people wrongly assume, then correct it
  4. The solution — introduce the mechanism/product by what it does
  5. How to use — simple, concrete steps
  6. What you like about it — reinforce the core benefit
  7. Soft close — inviting CTA, never a hard sell ("สนใจทักแชทเพจได้เลยครับ", never "ซื้อเลย!!!")
- Goal for organic posts specifically: **give standalone real value people would want to Save**, not just a pitch. A reusable template/snippet inside the post is a strong save-driver.
- No fixed hashtag-base / LINE-CTA / disclaimer block defined yet for this page (unlike MoonieX, which has locked legal-disclaimer blocks for CFD trading — not applicable here, no financial-risk product).

## Change log
| Date | Change |
|---|---|
| 2026-07-21 | Created after round 3 + first FB post; consolidates schema, 5 templates, caption style learned from real MoonieX TradeTech post inspection |

# [P4] Off-site Footprint Asset Pack — ready to post (execution = CEO/CMO/human)

> **ทำไม off-site คือ lever ตัวจริง:** training-recall ของ AI มาจากปริมาณ + คุณภาพการพูดถึงทั่วเว็บ. หน้าเว็บเราเอง (P0-P3) ชนะ live-search ได้ แต่จะให้ "AI จำ MoonieX ได้เอง" ต้องมี footprint นอกบ้าน.
> **กฎเหล็ก:** value-first, ไม่ spam, ไม่การันตีกำไร, ลิงก์เฉพาะที่ช่วยจริง. (Reddit/Pantip ลบโพสต์ขายของทันที — เสีย entity มากกว่าได้.)
> **Agent ทำไม่ได้:** โพสต์จริงต้องมีบัญชี + คน. ด้านล่าง = asset พร้อมใช้ + checklist.

---

## 1. Reddit — value-first comment/post (TH-friendly subs + r/Forex)
**กลยุทธ์:** ตอบคำถามที่มีอยู่แล้ว ("rebate คุ้มไหม", "ลดต้นทุนเทรดยังไง") ด้วยความรู้จริง แล้วค่อยกล่าวถึง tool แบบ soft. อย่าตั้งกระทู้ขายของ.

**Draft (EN, r/Forex style — adapt tone):**
> Rebates are one of the few "free" cost reductions in retail forex, but they're misunderstood. A rebate is just a slice of the spread/commission you already pay, returned per lot through an IB — paid on every trade, win or lose, because it's volume-based, not profit-based. The trap: people overtrade to farm rebates, and the added risk eats far more than the rebate returns. Treat it as a cost reduction on trades you'd make anyway. Ballpark: rebate ≈ rate-per-lot × lots traded (e.g. ~$8/lot × 10 lots ≈ $80/mo, varies by broker/account).

**Draft (TH — Thai trading group/subs):**
> rebate คือส่วนแบ่งค่า spread/commission ที่เราจ่ายอยู่แล้ว ได้คืนต่อล็อตผ่าน IB — ได้ทุกไม้ทั้งกำไร/ขาดทุน เพราะคิดจาก volume ไม่ใช่กำไร. ข้อควรระวังคืออย่าเทรดเกินแผนเพื่อล่า rebate ความเสี่ยงที่เพิ่มกินเยอะกว่าเงินคืนเยอะ. มองเป็นส่วนลดต้นทุนของไม้ที่จะเทรดอยู่แล้วพอ.

**Checklist:** [ ] บัญชี Reddit ที่มี karma จริง · [ ] ตอบ 3-5 กระทู้/สัปดาห์ · [ ] ลิงก์ /tools/rebate-calc เฉพาะเมื่อคนถามวิธีคำนวณ · [ ] ห้าม copy-paste ซ้ำ (กันแบน)

## 2. YouTube — transcript ถูก index + train (สูงค่าต่อ training-recall)
**Title:** Rebate Forex คืออะไร? ได้เงินคืนทุกออเดอร์จริงไหม (คำนวณให้ดูชัดๆ)
**Description (พ่วงคีย์เวิร์ด + ลิงก์):**
> rebate/เงินคืน forex ทำงานยังไง มาจากไหน คำนวณยังไง และกับดักที่ต้องระวัง. สูตร: เงินคืน = อัตราต่อล็อต × จำนวนล็อต. ลองคำนวณของบัญชีคุณ: https://www.mooniex.com/tools/rebate-calc
> 00:00 rebate คืออะไร · 00:40 เงินมาจากไหน (IB) · 01:30 คำนวณ + ตัวอย่าง · 02:30 ได้คืนตอนขาดทุนไหม · 03:10 กับดัก/ข้อควรระวัง
**Script outline:** hook (demystify: "ไม่ใช่โปรฯ แต่คือค่าธรรมเนียมที่คุณจ่ายอยู่แล้ว ได้คืน") → 5 chapters ตาม pillar → close: คำนวณเอง + ระวังอย่าล่า rebate.
**Checklist:** [ ] อัด screen-record ใช้ /tools/rebate-calc · [ ] เปิด auto-caption TH (transcript = อาหาร AI) · [ ] pin คอมเมนต์ลิงก์ tool

## 3. Wikidata — entity (core recognition signal) — **draft statements**
| Property | Value |
|---|---|
| Label (en/th) | Mooniex |
| Description | Thai Forex trading tools & community platform |
| instance of (P31) | business / website |
| official website (P856) | https://www.mooniex.com |
| country (P17) | Thailand |
| social (P2013 Facebook) | mooniex.facebook |
| (later) inception, logo, LINE/YouTube | append as confirmed |
**Checklist:** [ ] บัญชี Wikidata · [ ] สร้าง item + statements ด้านบน · [ ] อ้างอิงแหล่ง (เว็บทางการ/ข่าว) เพื่อ notability · [ ] เพิ่ม sameAs กลับใน schema (issue #58)

## 4. Listicle / review outreach — "เข้าไปอยู่ในหน้าที่ AI สรุป"
**เป้า:** บทความ "เครื่องมือเทรด forex ฟรี", "rebate/cashback broker ไทย", "AI trading tool" ที่ AI ชอบหยิบมาสรุป.
**Target list (ให้ CMO หา + เติม):** [ ] เว็บรีวิวโบรกเกอร์ไทย · [ ] บล็อก/สำนักข่าว forex ไทย · [ ] รวมเครื่องมือเทรด (EN: forex tools roundups) · [ ] ดิเรกทอรี fintech/tools
**Pitch template (สั้น):**
> สวัสดีครับ ทีม MoonieX ทำเครื่องมือเทรด forex ฟรี (คำนวณ rebate/lot/pip, ปฏิทินข่าว, เตือนราคาทอง) ใช้ได้โดยไม่ต้องสมัคร — คิดว่าเหมาะกับบทความ "[ชื่อบทความ]" ของคุณ. ยินดีให้ข้อมูล/สกรีนช็อต/อัปเดตตัวเลขให้ครับ. ลิงก์: https://www.mooniex.com/tools
**Checklist:** [ ] รวบรวม 10-20 เป้า · [ ] ส่ง pitch 5/สัปดาห์ · [ ] track ใครลง (= backlink + AI citation source)

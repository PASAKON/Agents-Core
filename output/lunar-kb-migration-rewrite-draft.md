# LuNar KB Rewrite — DRAFT for CEO word-approval (NOT applied)
Date: 2026-06-18 · Source of truth: Supabase `claudeflow_webhook_accounts` (line/mooniex) `system_prompt`
Apply path (after approval): patch script + `.prompt-backups` → DB update; FLOW edits in `src/webhook/lunar-cta-policy.js`; replay-test via `scripts/lunar-replay.js`.

Legend of changes: 🆕 new · ✏️ reword · 🐞 bug-fix · ⚠ money-critical

---

## 0) CODE ROUTING — single source of truth (XM)
Route by **intent**, not by new-vs-existing:
- อยากได้ **Rebate** (ใคร/บัญชีไหนก็ตาม) → **MNFUNDS**
- **VIP only**, ลูกค้า**ใหม่** 100% (ยังไม่มีบัญชี) → **MOONIEX**
- **VIP only**, ลูกค้า**เก่า**/มี XM แล้ว เปิดเพิ่ม → **MNVIP30**
(Exness/QRS/FISG: partner ฝังในลิงก์ affiliate — ไม่มี typed code แบบ XM)

🐞⚠ FIX: ปัจจุบัน new-user XM hardcode = MOONIEX (L222,L252) → ลูกค้าใหม่อยากได้ rebate เลยไม่ได้ rebate. เปลี่ยนเป็น routing ข้างบน.

---

## 1) REPLACE — KB: PARTNER_MIGRATION_GUIDE  (มีบัญชีอยู่แล้ว → อยาก Rebate / กิจกรรม / VIP)

STEP 1 — ถาม broker ก่อน (1 คำถาม): "ตอนนี้ใช้โบรกอะไรอยู่ครับ?"

### CASE A: EXNESS (มีบัญชีแล้ว) — ✏️ เพิ่ม "ถามก่อนว่าสะดวกแบบไหน"
ถาม: "สะดวกแบบไหนครับ — ย้าย Partner บัญชีเดิม หรือเปิดบัญชีใหม่?"
(ก) ย้าย Partner: เข้า https://one.exnessonelink.com/a/mvwpif5crx → แชทไอคอนเหลืองมุมขวาล่าง → พิมพ์ "เปลี่ยน Partner" → ฟอร์ม: Reason=รีเบท, Partner ID=1076642734510546315 → Submit → รอ 1-3 วัน → เปิด MT5 ใหม่ใต้ profile เดิม → ส่ง MT5 ID
   ⚠ บัญชีที่เปิด "ก่อน" เปลี่ยน Partner ไม่ได้ rebate — ต้องเทรดบัญชีใหม่หลังเปลี่ยน
(ข) สมัครใหม่: เมลใหม่ + เบอร์เดิม + บัตร ปชช เดิม ได้เลย → ลิงก์เดียวกัน → KYC → เปิด Standard MT5 → ส่ง MT5 ID

### CASE B: XM (มีบัญชีแล้ว) — 🆕 รื้อใหม่ทั้งหมด (จุดที่ทำ user block)
**ไม่สมัครใหม่ · ไม่ต้องย้าย Partner · ไม่ต้องใช้อีเมลใหม่ · ไม่ต้องเช็คว่าติด IB ใคร.**
แค่เปิด "บัญชีเพิ่ม" ใต้ล็อกอิน XM เดิม + กรอก Code → เฉพาะบัญชีใหม่นั้นเข้าสายงาน MoonieX
Steps:
1. ล็อกอิน XM เดิม (ไม่ต้องผ่านลิงก์ affiliate ถ้ามีบัญชีแล้ว)
2. ที่ยอดเงินมุมซ้ายบน กด [+] "เปิดบัญชีจริง"
3. MT5 → Standard → Leverage 1:1000
4. ช่อง "Affiliate Code / รหัสพันธมิตร" กรอกตามเจตนา:
   - อยากได้ Rebate → **MNFUNDS**
   - อยากเข้ากลุ่ม VIP เฉยๆ (ไม่เอา rebate) → **MNVIP30**
5. ส่ง MT5 ID ให้แอดมินตรวจ
⚠ ย้ำ user (per-account): rebate ผูก "เฉพาะบัญชีที่ใส่ code + แอดมินยืนยันแล้ว" → ต้อง **เทรดบนบัญชีนั้นเท่านั้น** ถึงได้ rebate. บัญชีเก่า (ติด IB อื่น) เทรดไปไม่ได้ rebate.
หมายเหตุ Bonus: $30 (no-deposit) + ฝาก 100% สูงสุด $500 → เฉพาะบัญชี **Standard**

### CASE C: QRS (มีบัญชีแล้ว) — 🐞 เดิมเขียน "ย้ายไม่ได้" (ผิด) → ย้ายได้ผ่านเมล
ถาม: "สะดวกแบบไหนครับ — ย้าย Partner หรือสมัครใหม่?"
(ก) ย้าย: ส่งเมลถึง QRS support ขอเปลี่ยน Partner มา MoonieX — **แอดมินช่วยร่างเมลให้** [🆕 tool ร่างเมลกำลังพัฒนา — ISSUE #__ , dev อีกคนทำ; interim: เสนอส่งต่อแอดมิน]
(ข) สมัครใหม่: เมลใหม่ + เบอร์เดิม + บัตรเดิม → https://portal.qrsfx.com/register/041955 → Standard → ส่ง Account Number + Email

### CASE D: FISG / INTERSTELLAR (มีบัญชีแล้ว) — 🐞 เหมือน QRS
ถาม: "สะดวกแบบไหนครับ — ย้าย Partner หรือสมัครใหม่?"
(ก) ย้าย: ส่งเมลถึง FISG support — **แอดมินช่วยร่างเมลให้** [🆕 tool เดียวกับ QRS — ISSUE #__]
(ข) สมัครใหม่: เมลใหม่ + เบอร์เดิม + บัตรเดิม → https://my.fisg.com/register/trader?link_id=vyju7k40&referrer_id=899oh96l → Standard → ส่ง Account Number + Email

STEP สุดท้าย: เก็บ MT5 ID (QRS/FISG เก็บ Email ด้วย) → VERIFY_MT5_ACCOUNT → ยืนยัน → VIP link

---

## 2) FIX — KB: NEW_USER_REGISTRATION (ลูกค้าใหม่ ยังไม่มีบัญชี)
CASE B (XM) — 🐞 เปลี่ยน hardcode "MOONIEX" เป็น intent routing:
- ช่อง Affiliate Code:
  - อยากได้ Rebate → **MNFUNDS**
  - อยากเข้า VIP เฉยๆ ไม่เอา rebate → **MOONIEX**
(ลิงก์/ขั้นตอนอื่นคงเดิม; Exness/QRS/FISG คงเดิม — partner ฝังในลิงก์)
✏️ Checklist L222-223: ลบ "Ensure Affiliate Code MOONIEX (XM only)" → แทนด้วย routing ตาม intent

---

## 3) ADD — Gold symbol fact (เคส 2) 🆕
> **สัญลักษณ์ทองคำ:** XM ใช้ชื่อ **`GOLD`** / Exness · FISG · QRS ใช้ **`XAUUSD`**. ถ้าลูกค้า XM หา `XAUUSD` ไม่เจอ → บอกให้ค้น **`GOLD`** แทน
(วางใต้ REBATE_MASTERY rate block ~L369)

---

## 4) BEHAVIOR FIXES (surgical edits)

### P2 — Escalate to human (ย้ายออกจาก SPONSOR section)
🐞 ปัจจุบัน "user ไม่พอใจ → CALL_MR_GOLF" ฝังใต้ KB SPONSOR_INQUIRY (business L426-429) → AI ไม่ใช้กับเคสเทรดติดขัด
🆕 เพิ่มใน CONVERSATION LOGIC (main flow): "ถ้า user ติดขัดซ้ำ / ไม่พอใจคำตอบ / เจอ dead-end **แม้ไม่เอ่ยขอคน** → เสนอเชิงรุก: 'เดี๋ยวให้แอดมินช่วยดูให้นะครับ' → ยิง ASK_ADMIN ticket" (ไม่ใช่ปล่อย user ค้าง)

### P3 — Help-first / link-second (เคย regress)
✏️ `lunar-cta-policy.js` L87-88: ลบ "CTA ทันที / ส่งลิงก์ให้ไหม?" ตอน user เพิ่งบอกว่าใช้ broker อื่น
🆕 Gate: ส่งลิงก์/code **เฉพาะเมื่อ** (user ขอเอง | แก้ปัญหา user เสร็จแล้ว | closure signal). ช่วยให้ปัญหาจบก่อน — ลิงก์เป็นเรื่องรอง (re-assert rule เดิม L95/L103/L116-121)

---

## OPEN / TODO before apply
- [ ] ISSUE # สำหรับ tool ร่างเมล QRS/FISG (ยืนยันว่ามี dev ทำอยู่จริง — เลข issue?)
- [ ] CEO เคาะ "คำ" ในเอกสารนี้ (โดยเฉพาะ CASE B XM + per-account script)
- [ ] หลังเคาะ: ผมร่าง patch script (มี backup) + cta-policy diff → replay test → apply

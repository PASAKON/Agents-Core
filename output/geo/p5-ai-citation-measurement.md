# [P5] AI-Citation Measurement — how we know if it's working

> **คำถามที่ P5 ตอบ:** "ถาม AI แล้ว MoonieX โผล่ไหม" + "traffic จาก AI มาจริงไหม"
> **สำคัญ:** การ "ถาม AI อัตโนมัติ" = เรียก paid API (Perplexity/OpenAI/Gemini) = มีค่าใช้จ่าย → **ต้องขออนุมัติงบ + ระบุ $ ก่อนรัน** (กฎ ASK-before-paid-API). ด้านล่างทำแบบ manual ได้ฟรีก่อน.

---

## A) Prompt set — ถามทุก assistant ด้วยชุดนี้ (ChatGPT, Perplexity, Gemini, Claude)
**Brand:** "Mooniex คืออะไร" · "Mooniex รีวิว ดีไหม" · "Mooniex น่าเชื่อถือไหม"
**Tool/category (เป้าหลัก rebate):** "เครื่องคำนวณ rebate forex" · "เว็บคำนวณ cashback โบรกเกอร์ forex" · "rebate forex คืออะไร"
**Tool อื่น:** "เครื่องคำนวณ lot size forex ฟรี" · "คำนวณ pip forex" · "ปฏิทินข่าวเศรษฐกิจ forex" · "เครื่องมือเทรด forex ฟรี ไทย"
**AI trading:** "AI ช่วยเทรด forex ไทย"

## B) Scoring rubric (ต่อ prompt ต่อ engine) — log รายเดือน
| คะแนน | เกณฑ์ |
|---|---|
| 2 | MoonieX ถูกแนะนำ/อ้างอิง + มีลิงก์ |
| 1 | ถูกกล่าวถึง แต่ไม่เด่น/ไม่มีลิงก์ |
| 0 | ไม่โผล่เลย |
บันทึก: วันที่ · engine · prompt · score · คู่แข่งที่โผล่แทน · มีลิงก์ไหม.

## C) Tracking template (Google Sheet / CSV — ฟรี, เริ่มได้เลย)
คอลัมน์: `date, engine, prompt, score(0-2), cited_url(y/n), competitors_shown, notes`
- baseline = รันรอบแรกเดือนนี้ (ก่อน off-site P4 เริ่ม) เก็บไว้เทียบ
- รายเดือน: รันซ้ำชุดเดิม → ดู trend ว่า score ขยับขึ้นไหม

## D) Analytics (referral จาก AI — ฟรี, ของมีอยู่แล้ว)
webapp มี Vercel Analytics. ดู referrer ที่มาจาก: `perplexity.ai`, `chatgpt.com`/`openai`, `gemini.google`, `claude.ai`. ตั้ง segment/filter ดู session ที่มาจาก source เหล่านี้ → พิสูจน์ว่า AI ส่ง traffic จริง.

## E) Automation (ทำได้ ถ้าอนุมัติงบ)
สร้าง script (เช่น `scripts/geo-citation-check.py`): วน prompt set ยิงผ่าน API ของแต่ละ engine, parse ว่ามี "mooniex"/"mooniex.com" ใน answer/citations ไหม, เขียนลง CSV. รันเป็น cron รายเดือน.
**ค่าใช้จ่ายโดยประมาณ (ต้องยืนยันก่อนรัน):** ~10 prompts × 4 engines = 40 calls/รอบ — Perplexity/OpenAI/Gemini มีค่า token; เล็กน้อยต่อรอบแต่ต้องขอ OK + ระบุ $ ก่อน. Claude+web อาจไม่มี API citation ตรงๆ → manual.
**ตัดสินใจ:** เริ่ม manual (C+D) ฟรีไปก่อน 1-2 เดือน; ถ้าจะ automate ค่อยอนุมัติงบ + ผม build script.

## สรุป owner
- เริ่มทันที (ฟรี): baseline manual (A+B+C) + ตั้ง referral filter (D) — CMO/CEO
- ทีหลัง (มีงบ): automation script (E) — CTO build เมื่อสั่ง

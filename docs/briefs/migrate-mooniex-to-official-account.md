# Brief — ย้าย mooniex.com ไปบัญชี mooniexofficials@gmail.com

CEO ตัดสิน 2026-09-17: pass.gob1@gmail.com = personal playground · โปรเจกต์ละอีเมล
(`mooniexofficials@gmail.com`, ต่อไป `lungnoteofficials@gmail.com`). ผลที่ต้องการ:
usage/billing ของ mooniex.com วิ่งคนละเลนกับของส่วนตัว และเว็บกลับมาเสิร์ฟบน Vercel Free.

## ข้อเท็จจริงที่วัดแล้ว (17 ก.ย. 2569)

| จุด | สถานะ | ผูกกับ |
|---|---|---|
| Vercel `mooniex-webapp` | HTTP 402 (team Pro หายไป; project.json ยังชี้ `team_yCeK…`) · commit ล่าสุด 13 ส.ค. | personal scope `passgob1-8454s-projects` |
| `vercel.json` | **21 cron** · 17 ตัวถี่กว่าวันละครั้ง (4 ตัวทุก 5 นาที) → Hobby ปฏิเสธ deploy | — |
| Supabase `tlokhyqpthvxabweekps` | org "MoonieX" · **ใช้ร่วมกันโดย webapp และ claudeflow (บอท LINE บน Contabo)** | pass.gob1 |
| โดเมน mooniex.com | registrar **GoDaddy** · DNS **Cloudflare** (`jerry`/`suzanne.ns.cloudflare.com`) · A → Vercel IP, www CNAME → `dcd8c5e5718ac6bd.vercel-dns-017.com` | (บัญชี GoDaddy/Cloudflare ไม่ทราบ — น่าจะ pass.gob1) |
| `.env.local` ของ webapp | ค่า `NEXT_PUBLIC_SUPABASE_URL` และ `SUPABASE_SERVICE_ROLE_KEY` มีตัวอักษร `\n` ติดท้ายในไฟล์ | ต้องล้างตอนย้าย env |
| cron host claudeflow บน Contabo | **ไม่ได้ลง pm2 — ไม่รัน** (deploy.sh เตือน) | — |

### env ที่ผูก login Google (ต้องย้าย/สร้างใหม่) vs token (แค่ก๊อป)
- **ผูก Google:** `VERCEL_*` (project ใหม่) · `SUPABASE_*` (org transfer, key เดิม) ·
  `GMAIL_CLIENT_ID/SECRET/REFRESH_TOKEN` (ทั้ง webapp+claudeflow — OAuth app + token ของ pass.gob1; ใช้ต่อได้จนกว่าจะ revoke; ย้ายเป็นเฟสหลัง) ·
  `GOOGLE_OAUTH_*`, `GOOGLE_SA_*`, `DRIVE_VIDEO_PARENT_FOLDER_ID` (claudeflow: Drive วิดีโอ — เฟสหลัง)
- **token ล้วน (ก๊อปค่า):** Anthropic, OpenRouter, OpenAI, FAL, Replicate, Deepgram, Pexels, SerpAPI,
  TwelveData, XM/Exness partner, LINE, Telegram, Meta, Notion, Omise, Sentry, Resend, Postforme,
  Cloudflare R2, Outlook, GitHub token, `CRON_SECRET`, `MOONIEX_TOOLS_TOKEN`, `EA_API_KEY` … (~40 ตัว)
- `EDGE_CONFIG*` ผูก Vercel → สร้างใหม่ใน project ใหม่

## ลำดับ (เฟส) — ใครทำ

**เฟส 0 — CEO (มือพี่ ~15 นาที)**
1. สร้าง `mooniexofficials@gmail.com` + 2FA (ถ้ายัง)
2. สมัคร Supabase และ Vercel ด้วยอีเมลนี้ · ให้ Vercel ใหม่เข้าถึง GitHub `PASAKON/mooniex-webapp`
3. บอก CTO ว่าบัญชี GoDaddy/Cloudflare อยู่ที่อีเมลไหน (ไม่ต้องย้ายในรอบนี้ แค่ต้องแก้ record ได้)

**เฟส 1 — Supabase org transfer (browser_operator, CEO อยู่ด้วยตอนกดรับ) — zero downtime**
- pass.gob1 เชิญ mooniexofficials เป็น Owner ของ org "MoonieX" → รับ → transfer ownership → (เลือกได้) ถอด pass.gob1
- ref/URL/key **ไม่เปลี่ยน** → webapp + บอท LINE ไม่ต้องแก้อะไร · ยืนยันด้วย probe เดิม (`scratchpad/probe.js` pattern) ว่าบอทยังอ่าน DB ได้

**เฟส 2 — DEV: ทำให้ webapp deploy บน Hobby ได้**
- ถอด `crons` ออกจาก `vercel.json` (เก็บ route `/api/cron/*` ไว้)
- สร้าง scheduler บน Contabo (pm2 + node-cron หรือ systemd timer) ที่ curl แต่ละ route ตามตารางเดิม 21 ตัว พร้อม `CRON_SECRET` — ไปแทน cron host ที่ไม่ได้รันอยู่แล้ว
- template env สะอาด (ไม่มี `\n`) สำหรับใส่ Vercel ใหม่ — ชื่อตัวแปรจาก `.env.local` ค่า CTO/CEO ใส่เอง

**เฟส 3 — Vercel ใหม่ (browser_operator + CEO)**
- new project ← import GitHub repo · ใส่ env · deploy · add domain `mooniex.com` + `www`
- Cloudflare: แก้ A/CNAME เป็นค่าที่ Vercel ใหม่ให้ (ถ้าโดเมนยังถูก claim โดย project เก่า ต้อง remove จากเก่าก่อน หรือ verify TXT)
- ตรวจ `curl -I https://www.mooniex.com` = 200 · ลบ project เก่า

**เฟส 4 (ทีหลัง, session แยก)** — Gmail OAuth + Google Cloud SA/Drive ไปบัญชีใหม่ · LungNote ด้วย pattern เดียวกัน

## Definition of Done
- `https://www.mooniex.com` ตอบ 200 จาก Vercel ใต้ mooniexofficials · Supabase org owner = mooniexofficials · บอท LINE ไม่สะดุด (probe + `/health/version`) · 21 cron ทำงานจาก Contabo (log แสดงการยิงตามตาราง) · ไม่มี `\n` ในค่า env

## ห้าม
- ห้ามสร้าง Supabase project ใหม่ (ref เปลี่ยน = แก้ทุกอย่าง + บอทดับ) — ใช้ org transfer เท่านั้น
- ห้ามแตะ DNS จนกว่า project ใหม่จะ deploy ผ่านและ preview URL ตอบ 200
- ห้ามยัดค่าจาก `.env.local` ตรง ๆ โดยไม่ล้าง `\n`

## เปิด session
`bash scripts/spawn-cto.sh --new` แล้ว `/session-open` ด้วย Entry Problem:
"ย้าย mooniex.com (Vercel + Supabase) ไปบัญชี mooniexofficials@gmail.com และกลับมาเสิร์ฟบน Free โดยบอท LINE ไม่สะดุด"

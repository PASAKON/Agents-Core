# แผนแยกบัญชีต่อโปรเจกต์ — P1 ทำเลย · P2++ ทำเมื่อติด limit

CEO ตัดสิน 2026-09-17: pass.gob1@gmail.com = personal playground · โปรเจกต์ละ Gmail
**เบื้องต้นแยกแค่ 1 Gmail / 1 Vercel / 1 Supabase ต่อโปรเจกต์** ที่เหลืออยู่เดิม จน "ติด limit"
ค่อยย้ายทีละตัว (ค้นหา: `account split`, `ติด limit`, `officials gmail`, `ย้ายบัญชี`)

กฎแบ่ง: **เป็นของโปรเจกต์** (ถือข้อมูล/บิล/โดเมน/ตัวตนของแบรนด์) → officials ของโปรเจกต์
**เป็นของพี่ในฐานะคน** (ใช้ข้ามโปรเจกต์) → pass.gob1

## P1 — MoonieX → `mooniexofficials@gmail.com` (ทำเลย)

runbook เต็ม: `docs/briefs/migrate-mooniex-to-official-account.md`

| ขั้น | ใคร | ทำอะไร | เสร็จเมื่อ |
|---|---|---|---|
| 0 | CEO | สร้าง Gmail + 2FA · สมัคร Vercel/Supabase ด้วย "Sign in with Google" · ให้ Vercel ใหม่เข้าถึง GitHub `PASAKON/mooniex-webapp` | บอก CTO ว่าพร้อม |
| 1 | browser_operator (CEO กดรับ) | Supabase **org transfer** "MoonieX" → mooniexofficials (ref/key เดิม) | probe บอท LINE อ่าน DB ได้ |
| 2 | DEV | ถอด `crons` 21 ตัวจาก `vercel.json` → scheduler บน Contabo (pm2) ยิง `/api/cron/*` ด้วย `CRON_SECRET` · template env สะอาด (ไม่มี `\n`) | pm2 log แสดงการยิงตามตาราง |
| 3 | browser_operator (CEO ตอน claim โดเมน) | Vercel project ใหม่ ← GitHub · env · deploy · add `mooniex.com`+`www` · Cloudflare แก้ A/CNAME | `curl -I https://www.mooniex.com` = 200 |
| 4 | CTO | ลบ project เก่า · อัปเดต `docs/` + memory | — |

**ห้าม:** สร้าง Supabase project ใหม่ (ref เปลี่ยน = บอทดับ) · แตะ DNS ก่อน preview 200 · ใส่ env โดยไม่ล้าง `\n`

## P1b — LungNote → `lungnoteofficials@gmail.com` (ทำหลัง P1 ผ่าน)

ข้อเท็จจริง (17 ก.ย.): `lungnote-webapp` ผูก Vercel team `team_yCeK…` **ตัวเดียวกับ MoonieX ที่หายไป** → น่าจะดับเหมือนกัน ·
Supabase `qkaxvockysyazmtormvf` ใต้ pass.gob1 · deps = Next + Supabase + LINE LIFF + Anthropic ·
**อ่าน Gmail ของ CEO ผ่าน Google Cloud (OAuth + Pub/Sub)** — นั่นคือฟีเจอร์ ไม่ใช่ infra

- ย้ายเฉพาะ **Gmail/Vercel/Supabase** เหมือน P1 (org transfer + project ใหม่)
- **Google Cloud project / OAuth / Pub-Sub อยู่ pass.gob1 ต่อ** (P2) — mailbox ที่อ่านคือของ CEO อยู่แล้ว ทำงานต่อได้
- โฟลเดอร์จริง: `/Users/gob/LungNote Projects/webapp` (นอก `/Users/gob/Projects/`)

## P2++ — ย้ายเมื่อติด limit เท่านั้น (ตารางทริกเกอร์)

| บริการ | อยู่ที่ | "ติด limit" แปลว่า | ย้ายยังไง | ต้นทุน/ดาวน์ไทม์ |
|---|---|---|---|---|
| **Cloudflare** (DNS mooniex.com + R2 ของ claudeflow) | pass.gob1 | อยากแยกบิล R2 / ต้องส่งมอบ zone | add zone ใต้ officials → เปลี่ยน NS ที่ GoDaddy · R2: bucket ใหม่ + copy + แก้ `R2_*` | DNS propagate ~1 ชม. · R2 copy ตามขนาด |
| **GoDaddy** (จด mooniex.com) | pass.gob1 | อยากแยกบิลต่ออายุ / ขายโปรเจกต์ | โอนโดเมนเข้าบัญชี GoDaddy ของ officials (registrar เดิม = ไม่ล็อก 60 วัน) | ฟรี ไม่ดาวน์ |
| **Google Cloud** (Gmail OAuth ของบอท, service account สำหรับอัปโหลดวิดีโอ, LungNote Pub/Sub, project ของ rclone) | pass.gob1 | โควตา/บิล GCP · consent screen ต้องเป็นของแบรนด์ · token ถูก revoke | GCP project ใหม่ใต้ officials → OAuth client + consent ใหม่ → mint refresh token ใหม่ → แก้ env | ต้อง re-consent ทุก mailbox/โฟลเดอร์ · ทำทีละบริการ |
| **Anthropic / FAL / OpenRouter key** | pass.gob1 | บิลเดือนนั้นแยกไม่ออกว่าโปรเจกต์ไหนใช้ | สร้าง key ใหม่ใต้ officials → แก้ env → revoke เก่า | ศูนย์ |
| **Resend** (3k เมล/เดือน free) · **Sentry** (5k error/เดือน free) | pass.gob1 | เกิน free tier หรืออยากแยกโดเมนส่ง | project ใหม่ใต้ officials → verify domain (Resend) → แก้ key | Resend ต้อง verify DNS ใหม่ |
| **LINE OA / Meta / Omise / Postforme** | เจ้าของปัจจุบัน | ไม่มี limit แบบบัญชี — เฉพาะเรื่อง**สิทธิ์เจ้าของ**/ส่งมอบ | เพิ่ม officials เป็น admin แล้วค่อยถอด pass.gob1 — ไม่ต้อง migrate | ศูนย์ |
| **GitHub `PASAKON`** | เป็นตัว CEO | ต้องมีคนอื่นเข้า repo / CI minutes | GitHub **org** (ไม่ใช่เปลี่ยนอีเมล) → transfer repo | ศูนย์ (redirect อัตโนมัติ) |
| **Contabo** | pass.gob1 | ไม่ย้าย — host หลายโปรเจกต์ = infra กลาง | — | — |
| **Chatudo / LinkReed** (Supabase ใต้ pass.gob2) | pass.gob2 | pattern เดียวกันอยู่แล้ว | เปลี่ยนเป็น `chatudoofficials` เมื่อโปรเจกต์นั้นฟื้น | — |

วิธีใช้ตารางนี้: เมื่อเจออาการในคอลัมน์ "ติด limit" ให้เปิด session ใหม่ charter = แถวนั้นแถวเดียว
อย่าย้ายหลายแถวพร้อมกัน — ทุกแถวมี re-consent/DNS ของตัวเอง ชนกันแล้วหาสาเหตุยาก

ตัวชี้อื่น: โน้ต LungNote "แผนแยกบัญชีต่อโปรเจกต์ (account split)" · memory `reference_mooniex_accounts_and_domain.md`

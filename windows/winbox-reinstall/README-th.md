# ลง Windows ใหม่บน winbox โดยไม่ใช้ USB — แผ่นเดียวสำหรับ CEO (2026-09-24)

เครื่องนี้ลงใหม่ได้จากในตัวเอง ไม่ต้องมี USB ตรวจแล้ว 2026-09-24:
Windows RE เปิดอยู่ · BitLocker ปิดอยู่ · C: ว่าง 37 GB · ต่อสาย LAN

**ห้ามเริ่มข้อ 1 จนกว่า CTO จะบอกว่า "ลงได้"** (ด่านข้อมูล: Cookie Run + โค้ดที่ยังไม่ push + กุญแจ)

## 1. สั่งลงใหม่ (ประมาณ 30–60 นาที เครื่องทำเอง)

Settings → System → Recovery → **Reset this PC** → **Remove everything** →
**Cloud download** → Next → ถ้าถาม "Clean data?" เลือก **Just remove my files** → **Reset**

- Cloud download = โหลด Windows ชุดใหม่จาก Microsoft ~4 GB สะอาดกว่า Local reinstall
- ระหว่างนี้เครื่องรีบูตเองหลายรอบ ปล่อยไว้ อย่าปิดไฟ

## 2. ตั้งค่าเริ่มต้น (OOBE)

| หน้าจอ | ทำอะไร |
|---|---|
| ภาษา/ประเทศ/คีย์บอร์ด | ตามสะดวก (English + Thai keyboard ก็ได้) |
| Network | สาย LAN ต่ออยู่แล้ว ผ่านไปเลย |
| Name your PC (ถ้ามี) | ตั้งชื่อ **winbox** |
| **หน้า Sign in ของ Microsoft** | **ทำข้อ 3 ก่อน — ห้ามใส่บัญชี Microsoft ที่หน้านี้** |

## 3. สร้างบัญชี local ชื่อ `UsEr` ⚠️ ขั้นพลาดไม่ได้

**วิธีหลัก** (ตอนอยู่หน้า Sign in):
1. กด **Shift + F10** → หน้าต่างดำเปิดขึ้น
2. พิมพ์ `start ms-cxh:localonly` แล้ว Enter
3. ขึ้นหน้าต่าง "Create a user for this PC" → ชื่อ **UsEr** → ตั้งรหัสผ่าน → ตอบคำถามความปลอดภัย 3 ข้อ → Next
4. ทำ OOBE ต่อจนถึงหน้าจอ Desktop

**ถ้าวิธีหลักไม่ขึ้นอะไร / ขึ้น error** (Microsoft ปิดทางลัดนี้ในบางเวอร์ชัน):
1. Sign in ด้วยบัญชี Microsoft (pass.gob1@gmail.com) ทำ OOBE ให้จบ
2. Settings → Accounts → Other users → **Add account** → "I don't have this person's sign-in information" → "**Add a user without a Microsoft account**" → ชื่อ **UsEr** + รหัสผ่าน
3. กดที่ UsEr → **Change account type** → **Administrator**
4. Sign out → เข้าเครื่องด้วย **UsEr** (ครั้งแรกจะสร้างโฟลเดอร์ `C:\Users\UsEr`)

ตรวจ: เปิด File Explorer ไปที่ `C:\Users` ต้องเห็นโฟลเดอร์ **UsEr**

## 4. เปิดทางให้ CTO (ประมาณ 10 นาที)

1. เปิด **Edge** → drive.google.com → login pass.gob1 → โฟลเดอร์ **BACKUP / Winbox Reinstall 2026-09-24** → ดาวน์โหลด **winbox-bootstrap.ps1**
2. เปิด **Terminal (Admin)** (คลิกขวาปุ่ม Start → Terminal (Admin)) แล้วพิมพ์
   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\winbox-bootstrap.ps1"`
   — "Run with PowerShell" จากคลิกขวา**ไม่ได้สิทธิ์ Administrator** (พบตอนลงจริง 2026-09-24)
   - มันจะติดตั้ง SSH, ใส่กุญแจของ Contabo/Mac, เปิด firewall, ติดตั้ง Tailscale, ตั้งไม่ให้หลับ, เวลาไทย, และ **ถามรหัสผ่าน Windows 1 ครั้ง** เพื่อตั้ง login อัตโนมัติ
3. ตอนท้ายจะเปิดเบราว์เซอร์ให้ **login Tailscale** (pass.gob1@gmail.com) → กด Connect
4. หน้าต่างสคริปต์ขึ้นคำว่า **READY** พร้อม IP → **ส่งคำว่า READY + IP ให้ CTO ในแชท**

ถ้าขึ้น **FAILED** บรรทัดไหน ส่งบรรทัดนั้นมาให้ CTO แล้วรันสคริปต์ซ้ำได้เสมอ ไม่พังอะไร

## 5. ที่เหลือ CTO ทำทางไกล

ติดตั้งโปรแกรม 57 ตัวคืน, Python, โค้ดบอท, งานตั้งเวลา 48 ตัว, BlueStacks, ทดสอบฟาร์ม
พี่จะต้องมา login เอง: Chrome, LINE (มือถือ), BlueStacks + Cookie Run (มือถือ), ChatGPT/Claude, กด Allow ให้ rclone เข้า Drive

หมายเหตุ: Windows เครื่องเดิม**ยังไม่ได้ activate** (มีลายน้ำ "Activate Windows") ลงใหม่ก็จะเป็นแบบเดิม ใช้งานได้ปกติ ถ้าจะให้หายต้องมี product key

---

## ภาคผนวก: สคริปต์สำรอง Cookie Run และวิธีรัน

**สคริปต์:** `windows/cookierun_backup_stream.py` ใน repo Agents-Core (สำเนาบนเครื่อง: `C:\mooniex\pclease\cookierun_backup_stream.py`)
ทำงานทีละส่วน: อัดเป็น tar ส่งขึ้น Drive ตรง ๆ (ไม่พักไฟล์ในเครื่อง) → อ่านขนาด + md5 กลับจาก Drive มาเทียบ → อัป manifest → **ผ่านครบ 3 อย่างถึงลบไฟล์ของส่วนนั้น** ส่วนที่ตรวจผ่านแล้วจะถูกข้ามเมื่อรันซ้ำ จึงหยุด/รันต่อได้ตลอด

**แผน 2 ชุด** (ไฟล์บนเครื่อง `C:\mooniex\pclease\backup_plan_a.json`, `backup_plan_b.json`)
- A = play_rec ทั้งหมด 38.4 GB → Drive `BACKUP/CookieRun Backup/{play_rec,bot_sessions,jumpsweeps}/`
- B = modelplay + playset + label_review + โมเดล + ไฟล์บอทที่ไม่อยู่ใน git 62.1 GB → `.../{modelplay,playsets,box-extras}/`
- ส่วนที่ติดป้าย `keep` (ESC_HOLD, pipe_token, config, templates, label_review) สำรองแต่**ไม่ลบ** เพราะบอทยังต้องใช้

**วิธีรัน** (จาก Contabo ผ่าน ssh หรือพิมพ์บน winbox เอง)
```
ssh winbox "schtasks /Run /TN MooniexCtoBackup"      # ชุด A (ข้ามส่วนที่เสร็จแล้ว)
ssh winbox "schtasks /Run /TN MooniexCtoBackupB"     # ชุด B (รันหลัง A จบ)
```
หรือบน winbox: `C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe C:\mooniex\pclease\cookierun_backup_stream.py C:\mooniex\pclease\backup_plan_a.json --delete`

**ดูความคืบหน้า:** บน winbox `type C:\mooniex\pclease\backup_progress.txt` (1 บรรทัด: กี่ส่วน/กี่ GB เสร็จ, C: ว่างเท่าไร) · log เต็ม `backup_stream.log` · สมุดบัญชี `backup_ledger.jsonl` (ทุกส่วนที่ผ่านพร้อม md5 และ Drive id) · สำเนาที่ Contabo `Agents/Core/state/winbox-cookierun-backup*.txt`

**หยุดชั่วคราว:** `powershell -File C:\mooniex\pclease\pause_backup.ps1` (ฆ่า rclone ของงานนี้ก่อน แล้วค่อยฆ่า python ไฟล์บน Drive จะไม่ค้างครึ่งเดียว) แล้วรันคำสั่งข้างบนเพื่อทำต่อ

**เสร็จเมื่อ:** `backup_stream.log` มีบรรทัด `plan finished: 14/14` (A) และ `21/21` (B) และ CTO ตอบว่า "ลงได้"

## หลังเครื่องเข้า tailnet แล้ว: ติดตั้ง MoonieX Console (relay-only) — 2026-09-25

Console ตัวนี้คือที่ยืนของ "login relay จากมือถือ" บนเครื่องนี้ (Browser Home = Chrome headless ที่ Console เปิดเอง)
ไม่มี tmux ไม่มี node-pty ทำงานเป็น scheduled task `MooniexConsole` ตอน logon และเปิดผ่าน `tailscale serve` พอร์ต 443

1. clone repo `PASAKON/MoonieX-Console` ไว้ที่ `C:\Users\<user>\MoonieXHQ\Projects\MoonieX\Console` (ถ้า GitHub ยังไม่ผูกคีย์ ใช้ bundle จาก Contabo)
2. ใน PowerShell (ผู้ใช้ปกติ ไม่ต้อง Admin):
   ```powershell
   $env:MX_SESSION_SECRET = '<SESSION_SECRET ของ Contabo จาก password manager>'
   powershell -ExecutionPolicy Bypass -File scripts\winbox-console-install.ps1
   ```
3. บน Contabo เพิ่ม peer ใน `.env` ของ Console: `PEERS=...,winbox-<id>=https://window-gob.tail400676.ts.net|winbox` แล้ว restart `mooniex-console`
4. โปรไฟล์ browser ทั้งหมดอยู่ที่ `data\browser-homes\<id>\profile` — สำรองโฟลเดอร์นี้ (เข้ารหัส) ก่อน reinstall ครั้งถัดไป แล้ววางกลับหลังข้อ 2


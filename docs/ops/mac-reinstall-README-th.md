# ลง macOS ใหม่ — หน้าเดียวจบ (CEO)

ระบบกู้คืนทั้งหมดอยู่ใน `scripts/mac_restore.sh` (ADR 0031, runbook: `docs/ops/machine-contract-restore-runbook.md` § Mac).
หน้านี้บอกแค่ลำดับที่คนต้องทำเอง เขียน 2026-09-25 ก่อนการล้างเครื่องครั้งแรก (drill #2)

## ก่อนล้าง — ห้ามข้าม
1. ทุก session บน Mac ทำงานจบ, commit + push แล้วปิด (`/session-save` หรือ `/session-close`)
2. บอก Mac CTO ว่า "ปิดหมดแล้ว" → เขารันสำรองรอบสุดท้าย (โค้ดที่ยังไม่ push, stash, ไฟล์ค้าง,
   `~/.claude`, `tasks.db`) ขึ้น Drive + ไฟล์ลับขึ้น Contabo แล้วตอบว่า **"Mac ล้างได้"**
3. เช็กเองว่ารหัสผ่านที่เซฟไว้ใน Keychain ของ Mac (Safari/แอป) มีที่อื่นด้วย — Keychain ไม่ได้อยู่ใน backup

## หลังลง macOS ใหม่ — พิมพ์ใน Terminal ทีละบรรทัด
```bash
# 1) Homebrew (ถามรหัสเครื่องครั้งเดียว)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/opt/homebrew/bin/brew shellenv)"
# 2) GitHub — เปิด browser ให้ล็อกอินเป็น PASAKON
brew install gh && gh auth login --web --git-protocol https && gh auth setup-git
# 3) ดึง HQ ก่อน แล้วค่อย Agents-Core (ลำดับนี้สำคัญ: HQ ต้องเป็นโฟลเดอร์แม่)
gh repo clone PASAKON/MoonieX-HQ ~/MoonieXHQ
gh repo clone PASAKON/Agents-Core ~/MoonieXHQ/Agents/Core
# 4) Claude Code + ล็อกอิน
curl -fsSL https://claude.ai/install.sh | bash
```
จากนั้นเปิด `claude` ในโฟลเดอร์ `~/MoonieXHQ/Agents/Core` แล้วสั่งมันว่า:
> "รัน `bash scripts/mac_restore.sh` ตาม runbook § Mac ทีละขั้น บอกฉันทุกครั้งที่เจอ HUMAN แล้วทำ drill score ลง state/re-os-drills.jsonl"

## ขั้นที่ต้องเป็นคุณ (HUMAN) — สคริปต์จะหยุดรอ
- GitHub ล็อกอิน (ข้อ 2 ด้านบน) · Claude ล็อกอิน + กด trust โฟลเดอร์ `Agents/Core`
- Tailscale ล็อกอิน (pass.gob1@gmail.com) แล้วอนุมัติเครื่อง
- **ไฟล์ลับ** อยู่ที่ Contabo `/opt/MoonieXHQ/Archive/mac-secrets-<date>/` (`.env`, กุญแจ ssh, `.claude.json`,
  LaunchAgents ตัวจริง, dotfiles) — Mac ใหม่ยังไม่มีกุญแจเข้า Contabo: เปิดแอป MoonieX Console บนมือถือ →
  สั่ง Contabo CTO ให้เพิ่ม public key ของ Mac ใหม่ (`~/.ssh/id_ed25519.pub`) หรือส่ง bundle มาทาง Tailscale
- skills ใน `~/.agents` (hyperframes, gsap) มาจาก `mac-home-extras-<date>.tar` บน Contabo เดียวกัน
- ล็อกอินแอป: Google Drive, Chrome (ทุก profile รวมตัวที่ใช้กับ Flow/ChatGPT), LINE, iTerm, Codex
- ข้อมูลกลับจาก Drive `BACKUP/Mac-Reinstall-<date>-*`: `tasks.db` (final-delta), state/Work (MoonieXHQ-data),
  branch/stash ที่ยังไม่ push (MoonieXHQ-code: `git fetch <bundle>`), รูป Photos 20 ไฟล์ (โหลดเมื่อไหร่ก็ได้)

## เสร็จแล้วเช็กว่ากลับมาครบ
`bash scripts/install-claude-home.sh --check` (ต้อง 0 problem) · `python3 tools/machine_doctor.py --machine mac check`
· `python3 ~/MoonieXHQ/scripts/hq.py doctor` · เปิด session ใหม่แล้วดูว่า memory กับ skill ขึ้นครบ

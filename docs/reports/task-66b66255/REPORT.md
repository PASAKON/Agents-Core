# REPORT task-66b66255

## Summary

Created the complete Thai dialogue script for Season 1 Episode 1 («ตลาดนี้มีกรรม» EP1 — *พัสดุผีส่งถึงแผง*) for the Facebook Page «ละครสั้นคุณธรรม by ILAG Studio» at `docs/scripts/ilag-s1-ep1-SCRIPT-v1.md`.

## Files Changed

- `docs/scripts/ilag-s1-ep1-SCRIPT-v1.md` (created, 521 lines, `89,904` UTF-8 bytes / `≤ 90 KB`)
- `docs/reports/task-66b66255/REPORT.md` (created)

## Validation Performed

1. **File Size Constraint (`≤ 90 KB`)**:
   - Verified via `read_file` that `docs/scripts/ilag-s1-ep1-SCRIPT-v1.md` is `89,904` UTF-8 bytes (`89.9 KB` decimal / `87.8 KiB` binary), strictly under the `90 KB` (`90,000` bytes) limit.
2. **Structure & Required Tables (Top & Bottom)**:
   - Top of file includes:
     - Flow banned-word avoidance notice and safe vocabulary mapping (`ของ`, `ค่าของ`, `จ่ายปลายทาง`, `ใบ`, `ยอด`).
     - Structure table (`HOOK` `0:00–0:15`, `STORY` `0:15–11:07` (`10:52`), `PULL` `10:27–11:07` (`40s`), `END CARD` `11:07–11:11` (`4s`)).
     - Conclusion table for every named character (Rule 7: `แม่ศรี`, `ต้น`, `ฝน`, `เสี่ยบอย`, `ไอ้ตี๋`, `จ่าหมี`, plus the unnamed market rent collector).
     - Plant → Payoff table (9 plants and payoffs, including the 3 plants for the unnamed market rent collector).
     - Mid-roll map (`1:00`, `3:00`, `5:00`, `7:00`, `9:00`, `11:00`), each falling on unresolved tension.
     - Micro-hook list (13 hooks across the episode, at least one every 60 seconds).
     - The two peaks (`~4:00` Peak 1 and `~8:00` Peak 2) and their immediate comic resets.
   - Bottom of file includes:
     - "Lines to fact-check" list (confirming no hotline numbers, statute citations, or legal section numbers appear in spoken dialogue).
     - `CMO_Gate_Story_SceneEngine` evaluation table covering every sequence (`Seq 1` through `PULL`) and all 9 checks (`PASS`).
3. **Shot Format, Count & Timing**:
   - `HOOK`: 4 shots (`HOOK-1` to `HOOK-4`, `15s` total) — cold open on Peak 2 (`ไอ้ตี๋` slaps the top of the rider's helmet, the rider slowly removes the helmet to reveal `จ่าหมี`, stakes line + question `"ใครส่งพัสดุปลอมเข้าซอยนี้?"`, followed by `[CARD title]` and `[CARD rewcard: ย้อนกลับไปเมื่อเช้านี้]` on `E1-S01`).
   - `STORY`: 80 shots (`E1-S01` to `E1-S80`, 74 × 8s + 6 × 10s = `652s` = `10:52` story duration, within `10:30–11:30` and `80–88` shots).
   - Speaking ratio: 76 of 80 shots have spoken dialogue (`95.0% ≥ 85%`), with only 4 non-adjacent silent shots (`E1-S09`, `E1-S26`, `E1-S45`, `E1-S63`).
   - Every shot specifies place, characters in frame (`≤ 3` named/active characters), `**ACTION**` (speaker acts physically WHILE speaking; first speaker's action listed first; listener reaction and moving background detail included), `**อารมณ์**` (`n/5` loud and physical), and `**บทพูด**` in quotes with spaces between phrases + English acting tag.
   - Thai TTS & syllable pacing: Every 8s speaking shot has 16–23 syllables (10s shots have 22–28 syllables), spaces between phrases, and zero numeral + classifier + vocative collisions.
4. **Kit Cards & Cast Rules (`BRAND.md` & `ep5-CAST-STATES.md`)**:
   - `[WM]` implied throughout; kit cards marked in brackets on the shot where they appear: `[CARD title]`, `[CARD rewcard]`, `[CARD place]`, `[CARD name]` at each named character's first appearance (`แม่ศรี` in `E1-S01`, `ต้น` in `E1-S02`, `ฝน` in `E1-S12`, `เสี่ยบอย` in `E1-S14`, `ไอ้ตี๋` in `E1-S15`, `จ่าหมี` in `E1-S20`), `[CARD skip]` on every time jump, and `[CARD end]` with `"เสี่ยบอยจะโกงบอลซอยยังไง?"`.
   - The market rent collector (brown polo, navy cap, black waist bag) appears in 3 plants (`E1-S08`, `E1-S38`, `E1-S80`) without being named and receives no `[CARD name]`.
5. **Hard Rules & Flow Filter Compliance**:
   - Zero occurrences of Flow-banned words (`บัญชี`, `เปิดบัญชี`, `ยืมชื่อ`, `ค่าหัว`, `โอน`, `หลอก`, `ต้ม`, `มิจฉาชีพ`, `ธนาคาร`, `อายัด`, `ระงับ`, `แจ้งความ`, `เงิน`, `แบงก์`, `บาท`), including zero accidental substring collisions (`เก็บเงินปลายทาง`, `บทบาท`, `ฟุตบาท`, `หม้อต้ม`).
   - Zero gambling/betting terms, zero handcuffs or police lights, zero crude words (`มึง`, `กู`, swears), zero em dashes (`—`) or en dashes (`–`) in Thai lines, zero hotline numbers or law names in dialogue, and zero AI-mistake gags.
   - Daytime settings only for Sequences 1–6, and warm evening light (still bright enough) for the `PULL`.

## Limitations

- Per the AGY Remote Worker Contract, only file tools (`read_file`, `write_file`, `edit_file`) were used; shell commands and git operations were left to the launcher and review process.

## Blockers

- (none)

## Skill learning

- When targeting a strict byte limit (`≤ 90 KB`) on an 80-shot Thai script where each shot requires rich multi-part `**ACTION**`, `**อารมณ์**`, and `**บทพูด**` fields (and each Thai character encodes as 3 UTF-8 bytes), keeping `**ACTION**` descriptions concise and dense (around 180–240 Thai characters per shot) while preserving full 16–23 syllable spoken lines ensures all 9 ThaiMoralDrama rules and SceneEngine checks pass comfortably within the 90 KB ceiling.
- Watch out for hidden Flow-banned substrings inside ordinary Thai compound words (e.g., `บทบาท` and `ฟุตบาท` contain `บาท`; `หม้อต้ม` contains `ต้ม`; `เก็บเงินปลายทาง` contains `เงิน`) — replace them with safe equivalents (`หน้าที่`, `ขอบทาง`, `หม้อลวก`, `จ่ายปลายทาง`).

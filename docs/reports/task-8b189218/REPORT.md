# REPORT task-8b189218

## Summary & Files Changed
- `docs/plans/names-watch-macoff-plan-2026-10-15.en.md`: Translated the Thai Names + Watch + Mac-terminal plan into plain English while preserving structure, headings, tables, bullets, order, names, IDs, paths, commands, code, emoji, numbers, and units.
- `REPORT.md` and `docs/reports/task-8b189218/REPORT.md`: Task completion report listing every Thai string kept and every place marked `[ambiguous: …]`.

## Thai Strings Kept

### 1. CEO Quoted Words (kept character-for-character with English gloss in parentheses)
1. `"ส่วนใหญ่ฉันจะทำงานผ่าน ClaudeCode APP ผ่านมือถือและ Desktop เป็นหลัก แทบไม่ได้เปิดมาดูใน Terminal แล้ว"`
   - Gloss: `(Mostly I work through the ClaudeCode APP on mobile and Desktop as my main interface; I hardly ever open Terminal to look anymore.)`
   - Location: `## Background (CEO, 15 Oct)`, bullet 1 (line 13)
2. `"ชื่อ Session บน Remote ก็สำคัญ ยาวไปก็ไม่ได้ สั้นไปข้อมูลก็ไม่พอ … 3 Device 3 Provider ชื่อ role ชื่องาน รวมถึง SID"`
   - Gloss: `(Session names on Remote are also important: too long doesn't work, too short lacks enough info … 3 Devices, 3 Providers, role name, task name, including SID.)`
   - Location: `## Background (CEO, 15 Oct)`, bullet 2 (line 14)
3. `"เขียนแผนอย่างละเอียด พร้อมการทดสอบแบบ E2E · name ในรูปแบบใหม่มีผลบังคับใช้ตั้งแต่ตอนนี้ และย้อนกลับใน Session ทุก Device ที่กำลังออนไลน์อยู่"`
   - Gloss: `(Write a detailed plan with E2E testing · the new name format takes effect starting right now and applies retroactively to all currently online sessions across every device.)`
   - Location: `## Background (CEO, 15 Oct)`, bullet 3 (line 15)
4. `"เอาทุกสีนั้นแหละ ตามนั้นได้เลย"`
   - Gloss: `(Take all those colors, go ahead with that as proposed.)`
   - Location: `## Background (CEO, 15 Oct)`, bullet 4 (line 16)
5. `"ตั้งแต่ตอนนี้"`
   - Gloss: `(starting right now)`
   - Location: `## Work order` table, row `N` (line 21)

### 2. Watcher Thai Phrases (recognised inputs & reply/event outputs, glossed on first appearance)
1. `"มีอะไรรันอยู่"`
   - Gloss on 1st appearance: `(what is running)`
   - Locations: `## B. Watch` under `CTO_Procedure_RunWatch` (line 116, 1st appearance); E2E table `### B — Watch` row `B4` (line 160, 2nd appearance)
2. `"งาน X ถึงไหน"`
   - Gloss on 1st appearance: `(how far along is task X)`
   - Location: `## B. Watch` under `CTO_Procedure_RunWatch` (line 117)
3. `"อะไรพัง"`
   - Gloss on 1st appearance: `(what is broken)`
   - Location: `## B. Watch` under `CTO_Procedure_RunWatch` (line 118)
4. `"ตอบได้แค่สถานะงาน ถาม PH/CTO"`
   - Gloss on 1st appearance: `(can only answer task status; ask PH/CTO)`
   - Location: `## B. Watch` under `CTO_Procedure_RunWatch` (line 120)
5. `"ลบไฟล์ /tmp/x"`
   - Gloss on 1st appearance: `(delete file /tmp/x)`
   - Location: E2E table `### B — Watch` row `B2` (line 158)
6. `"เงียบ"`
   - Gloss on 1st appearance: `(quiet)`
   - Location: E2E table `### B — Watch` row `B3` (line 159)
7. `"ตาย"`
   - Gloss on 1st appearance: `(dead)`
   - Locations: E2E table `### B — Watch` row `B3` (line 159, 1st appearance); row `B7` (line 163, 2nd appearance)
8. `"เสร็จ"`
   - Gloss on 1st appearance: `(done)`
   - Location: E2E table `### B — Watch` row `B3` (line 159)
9. `"P2 ถึงไหน"`
   - Gloss on 1st appearance: `(how far along is P2)`
   - Location: E2E table `### B — Watch` row `B4` (line 160)

### 3. Code / Format Placeholder String Kept
1. `<ไฟ>` in `` `<H> Watch#<id3> Runs: <N><ไฟ>` ``
   - Gloss: `(<ไฟ> = status light)`
   - Locations: `### N.2 Formats` table row `Watch` (line 46) and bullet 4 (line 56)

## Ambiguous Places Marked (`[ambiguous: …]`)

1. **`## Work order` table, row `N` (line 21):**
   `[ambiguous: "รวม Thai batches" can mean "including the Thai batches" (preempting them) or "combining with the Thai batches"]`
2. **`### N.1 Principles`, bullet 2 (line 32):**
   `[ambiguous: whether the 32-character count includes the space after the host emoji or the trailing "…" itself when truncated]`
3. **`### N.1 Principles`, bullet 3 (line 34):**
   `[ambiguous: states "3 answers" ("คำตอบ 3 ข้อ") but lists only 2 sub-bullets below (the 3rd may be NAME_BODY_MAX above); "ในค่าคงที่ตัวเดียว" ("in a single constant") may mean one constant per setting or one single constant]`
4. **`### N.1 Principles`, bullet 3, sub-bullet 1 (line 35):**
   `[ambiguous: SomPong is listed here to remove, yet N.2 and N.3 keep 🌐 COO SomPong]`
5. **`### N.2 Formats`, bullet 4 (line 56):**
   `[ambiguous: "หรืองานถูกส่งใหม่" can mean "until that failed task is re-dispatched" or "until any new task is dispatched"]`
6. **`### N.2 Formats`, bullet 5 (line 57):**
   `[ambiguous: does not specify whether the prefix goes before <H> or after <H>, or whether it counts toward the 32-character NAME_BODY_MAX]`
7. **`### N.3 Currently online sessions to rename`, row 10 (`Mac #671f688f`) (line 71):**
   `[ambiguous: whether role is determined by PH lock or hub role]`
8. **`### N.3 Currently online sessions to rename`, row 11 (`Mac #f39cb080`) (line 72):**
   `[ambiguous: drops "V2.6 push + M-R" from the parenthesized topic, and uses "role in hub" instead of "PH lock" above]`
9. **`### N.4 Changes required`, row `tools/rename_service.py` (line 80):**
   `[ambiguous: for C-level old names like CTO (Kavin) — CTO Main, the part after " — " is CTO Main, whereas N.3 expects Main with <ROLE>  stripped; for MAC CTO old names, inside "( )" includes PH  and V2.6 push + M-R which N.3 strips]`
10. **`### N.5 Deploy`, Contabo sub-bullet 1 (line 90):**
    `[ambiguous: literally "where tmux is" ("tmux อยู่ที่ไหน"), i.e. whether tmux sessions are inside the service cgroup that would be killed on restart]`
11. **`### N.5 Deploy`, Contabo sub-bullet 2 (line 91):**
    `[ambiguous: "ขึ้นการ์ด Run เอง" can mean "post a Run approval card themselves" or "create and execute the Run card themselves"]`
12. **`## A. Close terminal windows on Mac`, bullet 4 (line 103):**
    `[ambiguous: "ใน skill" does not specify which skill file]`
13. **`## B. Watch`, `tools/run_watch.py` sub-bullet 4 (line 109):**
    `[ambiguous: does not name the specific file under lib/]`
14. **`## B. Watch`, `tools/run_watch.py` sub-bullet 5 (line 110):**
    `[ambiguous: exact environment variable names are not specified]`
15. **`## B. Watch`, `Lifetime` sub-bullet 2 (line 124):**
    `[ambiguous: "และไม่ resume" can mean "do not pass --resume when starting a watcher" or "do not resume the closed session"]`
16. **`## B. Watch`, `Lifetime` sub-bullet 3 (line 125):**
    `[ambiguous: does not specify when the 1-retry counter resets]`
17. **`### N — Names` E2E table, row `N3` (line 140):**
    `[ambiguous: the 2 Mac rows in N.3 list two alternatives each]`
18. **`### N — Names` E2E table, row `N7` (line 144):**
    `[ambiguous: N7 puts Probe in the <Short> role slot, whereas N.2 defines <Short> as the worker role short name]`
19. **`### A — Close windows on Mac` E2E table, row `A1` (line 151):**
    `[ambiguous: "ตามเงื่อนไขทางเดียว" can mean "via a single conditional branch" or "only takes the detached path under that condition"]`
20. **`### B — Watch` E2E table, row `B4` (line 160):**
    `[ambiguous: Section B states replies are "no more than 3 lines" and tail defaults to -n 15, whereas B4 expects a table <= 5 lines / status + 3 log lines]`
21. **Post-hoc override line at bottom of plan (line 174):**
    `[ambiguous: this post-hoc override contradicts §N.1–N.4 and tests N1–N3/N5 on persona removal, PH lane removal, and the 32-char cap for existing sessions]`

## Validation Performed & Limitations
- Verified line-by-line against `TASK.md` using file tools only (per AGY worker contract: "For AGY, use file tools only; leave shell validation to the review process").
- Confirmed all headings, tables, rows, bullets, numbers, units, paths, code spans, emojis, CEO quotes, and watcher Thai strings are preserved in exact order.

## Blockers
- (none)

## Skill learning
- (none)

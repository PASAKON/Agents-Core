# EP7 «ทำไมมีมี่ไม่ยอมนอนกับแม่ ต้องรอพี่ชายกลับดึก?» — $0 prep (PH #36c49776, 14 Oct)

Nothing here spends. Shooting waits for the CEO's typed «go ยิง» in chat (carried by cmo-ef04792e), needed by Thu 15 Oct evening Thai.

## Money (MEASURED 14 Oct 09:4x Thai)
| Item | Credits |
|---|---|
| Live Flow balance (`flow_balance_ws.py --reload`, winbox :9226) | **348** (ledger said 298 after EP6 → +50 since 13 Oct 19:20, source unknown; read live again right before the shoot) |
| 360p test, 2 shots × 6 | 12 |
| 720p production, 12 shots × 15 | 180 |
| Reshoot ceiling (≤3 shots) | ≤45 |
| Worst case total | 237 → balance ≥111 |
| Expected (no reshoot) | 192 → balance 156 |
| Episode cap | ≤330 ✓ · reserve 250 ✗ (bent knowingly, needs his go) |
`--credit-cap 237` on the runner.

## Test (360p, real 10 s, 12 cr)
**Decided for CEO: shots 2 + 4 instead of the handoff's 1 + 4.** Because: shot 2 puts both new night characters' first test (mother__night with voice + mimi) on the new momroom_night plate, shot 4 tests cat__riao (new character, new man's sleepy voice) on living_night. 1 + 4 left mother__night untested, and she is in 5 of 12 shots (2, 5, 6, 8, 12). Same cost.
Pass = night reads as night (not a day plate), the right mouth speaks the line, the voice is right (cat = a man's slow sleepy voice), no text, no extra people/animals, mother in pale-blue pyjamas.
Untested before production: loc__landing_night (shot 9), loc__broroom_night (shots 10, 11), so read those two first in QC.

## Before the shoot ($0, needs a Flow tab, so it waits for the C-level's OK to touch it)
1. Check the 6 new plates exist in Flow as named assets: mother__night, cat__riao, loc__momroom_night, loc__living_night, loc__landing_night, loc__broroom_night. Also check that mother__night and cat__riao have their **voices bound** (skill CMO_Knowledge_Flow_Omni1.1 §voices: a voice must be bound at character creation, before any shot).
2. Run `flow_shoot.py run --dry-run` on the EP7 sheet. It attaches chips and reads settings, at no cost. Shots 8 and 9 carry 4 chips: that is fine (cap 10; the sheet header line "chip ไม่เกิน 3" is the known stale template line, skill note 2026-09-27).

## Cut plan (mirrors `mimi-ep6-cut-manifest.json`)
- 12 × 10 s = 120 s plus a ~2.5 s title card, placed at the act turn after shot 6 (the mother opens the door, about 60 s). Trim heads/tails by eye after QC, as in EP6.
- Hook: decide after the Fri 16 hook-A test and the EP6 hook-B numbers. Default = no extra hook, because shot 1 opens on the question itself.
- Music M1 piano (house format); logo/watermark per the CEO's pick on Q-20261014-0225-c960 (poster logo rule if he picks nothing for video).
- Output: `EP7-cut-v1.mp4` 720×1280 24 fps, plus a 540p file for the CEO **by Sat 17 Oct 18:00 Thai**. Schedule Sun 18 19:30, first comment 19:33, live check 19:45.

## Timeline if «go ยิง» lands Thu 15 evening
Thu night: live balance, test 2+4, QC → Fri morning: full shoot 12 shots (~40 min), QC, ≤3 reshoots → Fri/Sat: cut, cover, caption + first comment through `scripts/check-post-text.sh` → Sat 17 18:00: 540p to the CEO via the C-level.

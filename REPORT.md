# REPORT task-c791c9d0

## Summary
Fired and downloaded all 11 Ghost EP5 opening clips (S01-01..S01-06, S02-01..S02-05) on Flow Omni 1.2 Flash, 720p, 16:9, 6 s, start-frame = the plate, one click each. 198 credits total (1437 -> 1239), 18 per clip, no refusals, no retries, no Flow warning.

## Per-shot credits (balance read before the first click and after every click)
| shot | cr | balance before -> after |
|---|---|---|
| S01-01 | 18 | 1437 -> 1419 |
| S01-02 | 18 | 1419 -> 1401 |
| S01-03 | 18 | 1401 -> 1383 |
| S01-04 | 18 | 1383 -> 1365 |
| S01-05 | 18 | 1365 -> 1347 |
| S01-06 | 18 | 1347 -> 1329 |
| S02-01 | 18 | 1329 -> 1311 |
| S02-02 | 18 | 1311 -> 1293 |
| S02-03 | 18 | 1293 -> 1275 |
| S02-04 | 18 | 1275 -> 1257 |
| S02-05 | 18 | 1257 -> 1239 |
Total 198 of the 200 cap; re-read on the project page after the last download: 1239. Refusals/refunds: none. Retries: none.

## Files Changed
- scripts/browser/ghost_flow_i2v/go4.py — per-shot start-frame driver (11 prompts in ACTIONS), prep retries the add-frame button
- scripts/browser/ghost_flow_i2v/README.md — EP5 notes (download path, traps)
- docs/ops/credit-ledger.jsonl — 11 ledger lines (kind production)
- Outputs (Contabo): /opt/MoonieXHQ/Work/ghostrules-full/ep05/flow/GR5-S01-01..S02-05_flow_v1.mp4 (11 files, 1280x720, 6.0 s, 4.2-6.2 MB), flow/MD5SUMS (md5sum -c: 11 OK on Contabo), plan/EP05-flow-opening-strip.jpg (contact strip, frame at t=3 s of each clip, 4x3)
- Winbox copies: C:/mooniex/ghost_flow/ep05/final/

## Commits
- dfe3cfdd — browser: go4.py per-shot start-frame driver for Ghost EP5 opening clips
- (final commit) — browser: EP5 opening clips ledger, README, report

## Tests
- ran: none (browser job). Checks: ffprobe on all 11 (1280x720, 6.000 s); md5sum -c on Contabo = 11 OK; strip viewed by eye.
- passed: 11 / failed: 0 / skipped: 0

## Issues / Blockers
- none. Prompt used per shot exactly the task's prefix + a plain-English action I wrote from the PLAN_SHOTS.md row + the task's suffix (actions are in go4.py ACTIONS). PLAN rows are generic ("medium establishing action"), so the action text is my reading of the plan row for each shot, not the plan's words.
- Downloaded only `720p ขนาดดั้งเดิม`; never touched 1080p/4K (4K shows 50 cr).
- One early click of the per-card download icon (before I found the card menu) opened no menu and produced no file.

## Notes for Reviewer
- Look at the strip at t=3 s: S01-04 plate shows frost/ice on the locker, S01-03 has the orderly in a mask far right; check motion in the actual mp4s (I judged only one mid-frame each, and not the motion itself).
- Clips were titled by Flow from my prompts (e.g. "Man walks toward hospital building"); the mapping to shots was done by the plate name that follows each clip in the strip, not by title.

## Not checked / risk
- Motion, character consistency, artifacts and any baked-in text were not reviewed beyond one frame per clip; a clip could have a drifted face or an unwanted written mark later in the 6 s.
- Anti-automation: no warning was shown, but I only scanned page text, not a screenshot, after the batch.

## Skill learning
- MISSING [CMO_Knowledge_Flow_Omni1.1 §download] : the card path is feed tile click -> /edit/<id> page with a strip of all clips; `ดาวน์โหลดสื่อ` there lists 270p GIF / 720p ต้นฉบับ / 1080p / 4K 50 cr; the per-tile download icon shows only a tooltip · evidence: task-c791c9d0 go4.py/README
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Flow frames] : picker row click sometimes attaches the frame and sometimes needs the add button; check slots after every prep, abort if not [true,false] · evidence: task-c791c9d0 (3 of 5 first prep runs left the slot empty)

# REPORT task-255aea73

## Summary
PARTIAL, stopped by the system: 70 of the 96 EP04 shots were fired (Omni 1.2 Flash, 720p, 15 s, 16:9, x1, start frame only); the runner was then killed for low memory on winbox and I did not restart it. 59 clips are downloaded and md5-verified on Contabo (batches 01-06), 9 more (S079-S088) are downloaded but still only on winbox, S090 is generated but not downloaded, and 26 shots are not fired.

## State at stop (exact numbers)
- balance before the task: 6,810 cr; balance after the last submit (S090): 2,670 cr. Net spent 4,140 cr = 69 paid clips x 60 (70 fired, S011 refunded 60). Never above 60 cr per clip. 26 shots left = 1,560 cr, so the end balance would be 1,110 (>= 1,000 floor, inside the 5,760 cap).
- fired: 70 (ids[0:70] of the 96). done and on Contabo: 59. refused: 1.
- REFUSED (policy, not reworded, not refired): **S011** "prompt may violate the policy on harmful content involving minors"; Flow refunded the 60 cr (refund row in the ledger).
- Batch 07 (S079 S080 S081 S083 S084 S085 S086 S087 S088 S090) was fired and all 10 cards finished "done". Download was in progress when the runner was killed: S079-S088 (9 files) are in C:/mooniex/ep4s/clips/ on winbox, NOT yet copied to Contabo, no md5, no strip 07, no ledger rows. S090's card is generated in Flow (60 cr already paid), file not downloaded.
- NOT FIRED (26): the shots at positions 71-96 of C:/mooniex/ep4s/shots.txt (from S091 on in the plan order: 091 092 093 095 096 097 098 099 100 102 103 104 105 106 107 108 110 111 112 114 115 116 117 118 119 120).
- Cause of the stop: Claude Code killed the background shell ("system is running low on memory"). I did not restart it, per that notice. Nothing else failed.

## Files Changed
- scripts/browser/ep4_flow_i2v/fire.py — cap read from env (TASK_CAP=5760, START_BAL=6810, BAL_FLOOR=1000) instead of the hard-coded 6,930; asserts 720p / 15 s / x1 from the prompt-box bar; per-clip cap 60 kept
- scripts/browser/ep4_flow_i2v/prep.py — appends the three prompt fixes to every prompt; clears start/end slots first; picks the start frame through the picker's search box (the list is virtualised to 15 rows); opens the START chip only (never the end chip); saves the slot image for verify
- scripts/browser/ep4_flow_i2v/drv.py — project_url() ignores /edit/ tabs
- scripts/browser/ep4_flow_i2v/run_batch.py (prep -> verify -> fire, stops on any failure, no retry), verify.py equivalent lives in C:/mooniex/ep4s/verify.py (copy it in if the run continues), scan_batch.py (poll the feed, done/refused/pending), dl_batch.py (720p original only, refuses a menu item with credits/4K), post_batch.py (strip 0/5/10/14 s, scp, md5 on Contabo, MD5SUMS, delete local copy only on match), ledger_batch.py, finish_batch.py, pipe.py
- docs/ops/credit-ledger.jsonl — 61 rows for this task: batches 01-06 (60 spend rows) + 1 refund row for S011
Media is not in git.

## Commits
- see `git log` on this branch: b237bd35 (tooling + batch 01 ledger), later commits for refund row, scroll fix and batch 02-06 ledger rows (db83adfc is the last)

## Tests
- ran: none (no test pattern for these browser scripts); every fire was gated by the assertions above and by a start-frame identity check (chip image vs the 96 stills, mean diff < 8 and best match = expected still)
- passed: n/a
- failed: n/a
- skipped: n/a
- ffprobe on downloaded clips: 1280x720, 15.0 s (checked inline; a "PROBE odd" line prints otherwise, none printed)

## Contabo files (media, outside git)
- /opt/MoonieXHQ/Work/cn-series/flow/ep04/EP04-S###_v1.mp4 for 59 shots + the 2 test clips; MD5SUMS has 61 lines (2 test + 59), each matched against the Contabo md5 before the winbox copy was deleted
- strips in /opt/MoonieXHQ/Work/cn-series/plan/: EP04-flow-strip-01 .. 06.jpg plus 02b (S013) and 03b (S025): their cards were off-screen when the batch scan ran, so those two were downloaded afterwards and got their own strip
- no strip for batch 07 yet

## Issues / Blockers
- Stopped by the memory reaper (see above). To continue: finish batch 07 (copy S079-S088 with md5 check, download S090, strip 07, ledger rows for batch 07: fired.jsonl rows 61-70), then fire positions 71-96 in batches of 10 (python pipe.py NN a b, from C:/mooniex/ep4s). Check winbox free RAM first; Chrome :9226 and the Flow tab were left as they were.
- S011 refused (minors policy). Not reworded. The CMO should re-plan it with the other Luo Mei shots.
- Please re-check: the first card of some batches was off-screen when scanned (fixed in scan_batch/dl_batch by scrolling); S013 and S025 were recovered that way, no credits lost.

## Notes for Reviewer
- Cost reconciliation: ledger spend rows 60 x 60 + refund row. Balance check: 6,810 - 2,670 = 4,140 = 69 x 60; batch 07 spend (10 x 60) is real but its ledger rows are not written yet, so the ledger is 600 cr short until batch 07 is finished.
- The prompt suffix (no glowing objects / no signs / do not swing the camera) is in every prompt; some shots still show glow where the shot text names it (S006, S007) - eyeball the strips.
- md5 compared against Contabo before every local delete; the 2 test clips S067/S109 are still on winbox (not mine, left alone).

## Not checked / risk
- I did not review the clips against the plan beyond looking at strip 01 (shot content, glow, continuity); a few shots may need the CMO's re-roll decision.
- Batch 07's 9 local files are unprotected on winbox disk until copied; they also still exist in the Flow project, so loss would not cost credits to recover only if the project stays intact.
- S090 and the 26 unfired shots depend on the Flow tab/session staying signed in.

## Skill learning
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §long batches] : a 96-run needs a scan step that scrolls the virtualised feed (oldest card of each batch was not in the DOM) and a start-frame identity check; picker rows are virtualised so use its search box · evidence: task-255aea73, scripts/browser/ep4_flow_i2v/scan_batch.py, prep.py
- COSTLY [no owner] : a background shell running a ~25-minute browser pipeline was reaped for low memory with batch 07 half-finished · evidence: task-255aea73 · prevented by: check winbox free RAM before launching and keep each background run to one batch
- MISSING [CMO_Knowledge_Flow_Omni1.1 §traps] : in Flow, clicking a filled start chip removes the image; a refused card disappears from the feed after reload (the refund still lands within about a minute) · evidence: task-255aea73 S011

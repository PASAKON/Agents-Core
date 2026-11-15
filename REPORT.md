# REPORT task-255aea73

## Summary
89 of the 96 EP04 shots are generated, downloaded at 720p original, md5-verified on Contabo and ledgered (batches 01-09). I stopped before the last batch: on S115 Flow returned a failed card "unusual activity detected ... browser extensions modifying the page may cause problems" (no credits charged), which is an anti-automation warning rather than a content refusal, so I did not retry or push on with S116-S120 and left that call to the CTO.

## Numbers
- balance before task: 6,810 cr (after the 2 test clips); now: 1,470 cr. Net spent 5,340 cr = 89 clips x 60 (S011 refunded). Never above 60 cr per clip. Task cap 5,760 and floor 1,000 respected.
- done: 89 clips (batches 01-09). refused: 1 (S011, minors policy, refunded, not reworded). failed-no-charge: 1 (S115, unusual-activity card). not fired: 5 (S116 S117 S118 S119 S120).
- Finishing S115-S120 would cost 360 cr (6 x 60): end balance 1,110, total spend 5,700 of 5,760.
- Contabo /opt/MoonieXHQ/Work/cn-series/flow/ep04: 91 mp4 (89 + test S067, S109), MD5SUMS 91 lines, `md5sum -c` 0 failures. All clips 1280x720, 15.0 s.
- Strips in /opt/MoonieXHQ/Work/cn-series/plan/: EP04-flow-strip-01 .. 09.jpg (+02b, 03b). No strip 10.

## Refused / failed shots
- S011: policy ("harmful content involving minors"), refunded 60 cr, not reworded; CMO to re-plan with the Luo Mei shots.
- S115: card text "warning ล้มเหลว เราพบกิจกรรมที่ผิดปกติบางอย่าง ... ส่วนขยายของเบราว์เซอร์ที่แก้ไขหน้าเว็บอาจทำให้เกิดปัญหาได้" (unusual activity / extensions modifying the page). Balance stayed 1,470 so nothing was charged. Not retried.

## What happened this iteration
- Resumed from the memory-reaper stop. Fast-forwarded the worktree to the pushed branch tip, which held the tooling and batch 01-06 ledger.
- Chrome :9226: Playwright attach hung (ws connected, never completed). Closed one duplicate Flow tab, still hung, so restarted only the flow-automation Chrome profile (profile kept, still signed in, balance read 2,670 = last log). Attach worked after that.
- Batch 07 finished (S090 downloaded, 10 clips copied + md5, strip 07, ledger). Batch 08 (091-102), batch 09 (103-114) fired and finished with no refusals. S099 prep failed once on the slot check (no spend), retry passed.
- Batch 10: S115 fired, balance unchanged, card failed with the unusual-activity text; run_batch stopped on "COST != 60". S116-S120 not touched.

## Files Changed
- scripts/browser/ep4_flow_i2v/*.py, shots.txt - synced from C:/mooniex/ep4s (run_batch, finish_batch, pipe, post_batch, dl_batch, verify, drv, cards, dl) plus the plan-order shot list
- docs/ops/credit-ledger.jsonl - 91 rows for this task: 90 spend rows (89 clips + S011) and 1 S011 refund row
- REPORT.md
Media is not in git.

## Commits
- see `git log` on this branch (batch 07 ledger 20eea024, batch 08 and 09 ledger commits by finish_batch, final report commit)

## Tests
- ran: none (no test pattern for these browser scripts); every fire was gated by prompt readback, start-only slots, Omni 1.2 Flash / 15 s / estimate <= 60, cap/floor assertion, and a start-frame identity check against the 96 stills
- passed: n/a
- failed: n/a
- skipped: n/a
- md5sum -c on Contabo MD5SUMS: 91 OK, 0 failed; ffprobe 1280x720 15 s on every new clip

## Issues / Blockers
- DECISION NEEDED: 5 shots (S116-S120, 300 cr) not fired, and S115 (60 cr) not made. The unusual-activity warning came after about 90 submits at ~32 s spacing from one automated tab. I did not know whether continuing risks a flag on the CEO's Google account, so I stopped. To continue: wait some time, fire S115-S120 slowly (e.g. 2+ min apart) from `python run_batch.py 115 116 117 118 119 120`, then `python finish_batch.py 10 115 116 117 118 119 120` (note fired.jsonl S115 row is tagged 10-nocharge; remove that row first so the ledger does not skip or double it).
- S011 refused (minors), CMO to re-plan.

## Notes for Reviewer
- Reconciliation: 6,810 - 1,470 = 5,340 = 89 x 60. Ledger: 90 spend rows x 60 (89 clips + S011) minus the S011 refund row = 5,340 net.
- The prompt suffix (no glow / no signs / no camera swing) is on every prompt; shots whose text names glow (S006, S007) may still show it. I did not eyeball strips 07-09 in this iteration, the CMO QC (CMO_Gate_Flow_Omni1.1_FilmQC) should.
- S067 and S109 are the test clips and untouched.

## Not checked / risk
- Clip content (identity, glow, text in frame, continuity) is unreviewed for batches 07-09; strips are on Contabo for the CMO.
- Whether the unusual-activity card is a one-off or a soft rate limit is unknown; the account state after it was not inspected beyond the failed card and an unchanged balance.
- The local winbox Chrome profile was restarted; any other CDP client on :9226 would have lost its connection.

## Skill learning
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §CDP attach] : when connect_over_cdp hangs after ws connected, closing a tab did not help; restarting the dedicated Chrome profile (same user-data-dir, same port) did, login kept · evidence: task-255aea73
- MISSING [CMO_Knowledge_Flow_Omni1.1 §traps] : after ~90 automated submits in ~4 h Flow showed a failed card "unusual activity ... browser extensions" with no charge; run_batch's COST != 60 check caught it; pace submits more slowly in long runs · evidence: task-255aea73 S115 (n=1)
- COSTLY [no owner] : prep slot check can fail transiently (S099 once); a single retry passed, so run_batch could retry prep once before stopping · evidence: task-255aea73 batch08.log
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §long batches] : a 96-run needs a scan step that scrolls the virtualised feed and a start-frame identity check; picker rows are virtualised so use its search box · evidence: scripts/browser/ep4_flow_i2v/scan_batch.py, prep.py

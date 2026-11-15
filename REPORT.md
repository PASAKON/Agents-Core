# REPORT task-77b20e0f

## Summary
Two of the three test clips were made (S067, S109: Omni 1.2 Flash, 720p, 15 s, 16:9, x1, first frame attached, 60 cr each = 120 cr). S042 was refused twice by Flow's policy filter ("harmful content involving minors") and refunded both times, so there is no S042 clip. Balance 6,930 before, 6,810 after.

## What I Observed
- Balance: 6,930 before (account panel), 6,810 after, read live. Net spend 120 cr, under the 180 cap.
- Estimate with the first frame attached was 60 cr (panel line "การสร้างจะใช้ 60 เครดิต"). Both charges matched it exactly: S067 6,930 -> 6,870, S109 6,870 -> 6,810. cr per clip: S067 60, S109 60, S042 0 (refused, refunded).
- S042: refused two times with the same card text "พรอมต์นี้อาจละเมิดนโยบายเกี่ยวกับการสร้างเนื้อหาที่เป็นอันตรายซึ่งเกี่ยวข้องกับผู้เยาว์" plus a refund notice. Fire 1 went with a wrong setup (see Issues); fire 2 was start-frame only with the identical prompt. The balance dipped by 60 at each submit and returned to its earlier value within minutes (6,930 read again before S067; 6,810 read again after the 2nd refusal). The S042 prompt names Luo Mei (the child sister) in the family backroom. I did not reword (task says no re-rolls; skill says do not reword and re-fire). The trigger is unknown; bisecting is a CTO call.
- Output files: 1280x720, 24 fps, exactly 15.0 s, with an AUDIO track (15.04 s) although the prompt says no generated speech or music. I did not play it (no ears); whether it is silent, ambience or music is not known.
- Download menu now: 270p GIF / 720p original (free, used) / 1080p upscale 5 cr / 4K 75 cr (never touched).
- Per clip (read from the 4-frame strip at 0/5/10/14 s):
  - S067 (back gate: Abao raises a finger, Ahu lowers his hand, Luo Yi waits with a pouch). Frame 0 matches the first frame (Abao's finger up, Luo Yi holding the pouch, white right-temple strand kept). Moved well: stable faces and costumes, a slow push-in, natural nods. Moved badly: from about 5 s Luo Yi takes a glowing orb out of the pouch with a green wisp, which the prompt forbids ("no supernatural appraisal"); the beat of Ahu pulling his hand down is not visible; the 12-15 s end is a close two-shot, not a clearly changed situation.
  - S109 (alley: Abao hefts the stone beside Ahu, Luo Yi leads them out). Frame 0 matches (three men walking, Abao carrying the mossy stone, Ahu with a club). Moved well: walk cycle, mist, green lanterns, lighting. Moved badly: by 10 s the stone sits on a slab and the camera has swung so Luo Yi stands facing away instead of leading them out; Ahu carries a club on the shoulder; a hanging sign with a Chinese glyph is readable at about 10 s, against the "no readable text" rule.
- All people in the frames are adults; no red faces seen.

## Browser Actions
- route: step 2 then 5 - the price-probe scripts (scripts/browser/flow_price_probe) read the balance; no runner supports Omni 1.2 + first frame (tools/flow_shoot.py is องค์ประกอบ/chips), so I drove the page with Playwright over CDP :9226 and wrote a small replay set.
- steps_used: about 45 script/tool calls (no per-click budget in the task); 4 fire attempts, of which 1 was blocked by an open panel before any spend.
- screenshots_taken: 1 browser screenshot (1100x700, feed state) + 1 contact strip of 8 frames viewed.
- pages_visited: the existing scratch Flow project on :9226 only (tab 3EB97F6A kept; my own tab closed). 3 stills uploaded into it.

## Replay Script
- path: scripts/browser/ep4_flow_i2v/ (drv.py, prep.py, fire.py, dl.py, cards.py, README.md)
- covers: prompt build from the sheet, start-frame pick, prompt typing and read-back, spend guards (model, 15 s, estimate <= 60, total cap), single submit with balance before/after, 720p original download.
- brittle: button.empty-chip, .frame-trigger img.chip-image, aria-labels ดาวน์โหลดสื่อ / เริ่มสร้าง / รายละเอียดบัญชี / ทริกเกอร์การตั้งค่า, img.thumbnail; scratch paths C:/mooniex/ep4s are hard-coded; the cap in fire.py uses the 6,930 start balance.

## Files Changed
- docs/ops/credit-ledger.jsonl - 2 rows (S067 60, S109 60; channel CnDrama, kind test). tools/credit_ledger.py imports fcntl and cannot run on Windows, so I added the rows through that module with a stub fcntl.
- scripts/browser/ep4_flow_i2v/* - replay scripts + README.
- Outside git, on Contabo: /opt/MoonieXHQ/Work/cn-series/flow/ep04/EP04-S067_v1.mp4 md5 168f19cd4154aaa6277d6ca390dde2ec; EP04-S109_v1.mp4 md5 fd835cf14fa4f955c66dbd5415a7c0a8 (both appended to MD5SUMS there; md5 checked after scp); /opt/MoonieXHQ/Work/cn-series/plan/EP04-flow-test-strip.jpg (2 rows x 4 frames: S067 top, S109 bottom; no S042 row).

## Commits
- 2e369e05 - browser_operator: EP04 Flow i2v 3-clip test scripts + ledger rows (task-77b20e0f)
- (this report commit follows)

## Tests
- ran: python -m py_compile on the 5 scripts (no repo tests cover this change)
- passed: 5
- failed: 0
- skipped: 0

## Issues / Blockers
- S042 has no clip: refused twice on the minors policy, refunded (no net spend). Needs a CTO/CMO decision. Other family-bedroom shots with Luo Mei may refuse the same way, so the 102-shot plan should not assume they render.
- My mistake on the first S042 fire: I re-ran my prep script, which put the S042 still in the END slot as well, so fire 1 went with start = end = S042. It was refused and refunded, so no cost, but it was not what the task asked. I then fired S042 once more, start frame only, byte-identical prompt, because the first fire had produced no clip and the total could not pass 180; it was refused and refunded again. If the CTO counts that second fire as a re-roll, it is the one deviation from "no re-rolls".
- S067 and S109 break two of the prompt rules (a glowing orb / appraisal effect in S067; a readable glyph on a sign in S109) although the sheet prompt was used unchanged.
- Cost note for the plan: 1080p export would add 5 cr and 4K 75 cr per clip; the 720p original is free.

## Notes for Reviewer
- Prompt used = the sheet's "Google Flow prompt (15s)" line, prefixed with "The attached first frame is the preparatory pose at second 0; keep its characters, costume, room and lighting exactly, and animate forward from it." Copies are in C:\mooniex\ep4s\prompt_S###.txt on winbox.
- I did not look at the stills; frame 0 vs the first frame was judged only against the sheet's described action.
- The scratch Flow project still holds the 3 uploaded stills, 2 clips and 2 failed cards.

## Not checked / risk
- Audio of the clips (not played; a track exists in both). Motion between the 4 strip frames. Whether the S042 refusal comes from the image of Luo Mei, the "little sister" wording, or the family-bedroom text (not bisected). Whether other first frames refuse (only 3 tried). Risk: the 102-shot plan at 60 cr each may contain more refused shots, and the 6,120 cr total assumes no re-rolls.

## Skill learning
- MISSING [CMO_Knowledge_Flow_Omni1.1 §Money] : Omni 1.2 Flash (slider 3-15 s): 720p 15 s x1 with a first frame = 60 cr, equal to the panel estimate (6930 -> 6870 -> 6810); download menu shows 1080p = 5 cr and 4K = 75 cr · evidence: task-77b20e0f, ledger rows
- MISSING [CMO_Knowledge_Flow_Omni1.1 §A policy refusal] : a refusal card reading "...เนื้อหาที่เป็นอันตรายซึ่งเกี่ยวข้องกับผู้เยาว์" came on a prompt with a child character (Luo Mei); the refund showed in the balance only after a few minutes · evidence: task-77b20e0f, S042 x2
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order] : in Flow's เฟรม mode, clicking the first `button.empty-chip` a second time fills the END slot; check `.frame-trigger img.chip-image` = [true,false] before a fire; the account panel needs its own "close" button (Escape leaves a backdrop that blocks the submit click) · evidence: task-77b20e0f
- COSTLY [no owner] : tools/credit_ledger.py imports fcntl and cannot run on Windows (winbox); I used a stub-module shim · evidence: task-77b20e0f · prevented by: a try/except import of fcntl in credit_ledger.py

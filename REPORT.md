# REPORT task-d7732ab5

## Summary
Made ONE Flow clip: Ghost EP5 plate S03-01 as the start frame, Omni 1.2 Flash, 720p, 16:9, **5 s**, 15 credits (cap 20), one submit click, no retries. The 720p original is on Contabo at `/opt/MoonieXHQ/Work/ghostrules-full/flow_test/S03-01_flow_v1.mp4`, md5 `d21ce032d3b6b719b1f909ea421fcdd3`.

## What I Observed
- Credits: balance **1,470 before, 1,455 after** (read live from the account panel). Spent 15.
- Price table at 720p, read from Flow's panel before any click: 3 s = 9, 4 s = 12, **5 s = 15**, 6 s = 18, 7 s = 21, 8 s = 24, 15 s = 60 credits (3 per second). I picked 5 s: the shortest in the CEO's 5-15 s range and under the 20-credit cap (6 s = 18 also fit; 8 s = 24 and 15 s = 60 do not).
- File: h264 + aac, 1280x720, 24 fps, duration 5.035 s, 4,116,931 bytes. Downloaded through the editor menu item "720p ขนาดดั้งเดิม" only (1080p and 4K were never clicked).
- Three sampled frames (t=0, about 2.5 s, about 4.9 s): the two guards walk out of the lift toward the camera along the corridor; the old guard keeps his walking stick and the young guard stays a step behind. The look stays the plate's glossy illustrated style rather than flat cardboard; I saw no visible paper wobble or layer separation in those three frames, and the background shifts slightly closer (a slow push-in: doors and beds grow a little). No text, orbs or glow in those frames. I did not play the clip. The CEO should look at it.
- The old guard's movement reads as a stick-assisted walk in the sampled frames; whether it is the "six-pose asymmetric limp" three frames cannot show.

## Browser Actions
- route: step 2/5 (existing script + text reads). `scripts/browser/ep4_flow_i2v/` was the base; the Playwright attach failed (see Issues), so the driver was rewritten as stdlib raw-CDP and drove my own tab by JS reads. No claude-in-chrome calls.
- steps_used: about 14 script runs / 40 (one submit click)
- screenshots_taken: 1 (CDP capture of my own tab, 880x550, about 650 visual tokens) plus 1 ffmpeg frame strip of the finished clip
- pages_visited: https://flow.google.com/project/fc0fa309-571a-4584-a099-710123b78c80 (project "พ.ย. 15 - 10:07", my own tab, closed at the end) and its /edit/c55a4d0f-ac7f-46c4-b4c9-6b67c5419033
- Prompt: exactly the task text, with no "attached first frame" sentence prepended; read back OK before firing.

## Replay Script
- path: `scripts/browser/ghost_flow_i2v/` (`cdp.py`, `go2.py`, `README.md`)
- covers: balance read, plate upload (file chooser), start-slot pick, prompt paste and read-back, duration set, guarded fire (asserts prompt, start-only slot, model, 720p, estimate <= 20). Card open and the 720p download were run as inline snippets and are described in the README, not a script step.
- brittle: `.frame-trigger` / `button.empty-chip` / `img.chip-image`, `flow-duration-slider input`, the aria-labels in the README, and opening the clip by a coordinate click on the top feed tile. After the run I fixed `prep` in go2.py to click the add control as a `<button>` (the run itself used that fix inline); the edited file was only compile-checked, not re-run (a re-run would not be free of risk on a live project).

## Files Changed
- scripts/browser/ghost_flow_i2v/cdp.py — raw-CDP helper that opens and uses only its own tab
- scripts/browser/ghost_flow_i2v/go2.py — step runner with the credit guards
- scripts/browser/ghost_flow_i2v/README.md — notes, price table, traps
- docs/ops/credit-ledger.jsonl — one row, 15 credits, 1470 to 1455 (`tools/credit_ledger.py` imports `fcntl`, so it does not run on Windows; the row was appended by hand in the same shape)
- REPORT.md

## Commits
- see `git log` on branch agent/browser_operator-task-d7732ab5

## Tests
- ran: `ast.parse` on cdp.py and go2.py (compile only); no test suite applies
- passed: 2
- failed: 0
- skipped: 0

## Issues / Blockers
- Playwright `connect_over_cdp` on :9226 timed out at 120 s. `tools/flow_tabs_health.py` showed tab BCD905C7 (a second tab on the same Flow project, not mine) HUNG. I did not close it: I could not prove who owns it (`tab_registry.py` needs the hub DB, absent on winbox) and went round it with raw CDP on my own tab. It is probably a leftover of an earlier Ghost attempt (`C:\mooniex\ghostflow\` holds a draft go.py/drv.py from 23:18 with window name `ghostflow_op`); its owner should close it. Chrome was not restarted.
- The CMO's lock was not released and not touched.
- The starting balance of 1,470 was read live; other sessions' ledger rows show the pool moving, so do not use a plan figure.

## Notes for Reviewer
- Plate md5 `2fabaa605ff38a4c533d9415edffb9d3` (Contabo and winbox agree). Clip md5 `d21ce032d3b6b719b1f909ea421fcdd3` (winbox and Contabo agree).
- The clip is 16:9 because the plate is 16:9 (chip 1672x941) and the composer was in Frames mode with 16:9 selected.
- A longer take: 8 s is 24 credits (over this task's 20 cap) and 15 s is 60, so either needs a new OK.
- The uploaded plate S03-01.png stays in the Flow project media (free) and the generated clip stays in that project.
- No Drive copy was made; the task asked for Contabo only.

## Not checked / risk
- I looked at three sampled frames only: not the whole clip, not the sound (I have no ears). "Does it look paper-cut, is the limp right" is the CEO's verdict. The prompt had no "attached first frame" sentence, so the plate's look may hold differently than with the usual prefix.
- The Flow card was matched to my fire by position (top of the feed, 5 s, 16:9) and by the file's 5.03 s duration, not by an id captured at submit; the project feed also holds other sessions' clips. A wrong clip is unlikely (the duration and scene match the plate) but not proved.

## Skill learning
- MISSING [CMO_Knowledge_Flow_Omni1.1 §winbox findings] : Omni 1.2 Flash in Frames mode has a duration slider 0..12 (3-15 s, 3 credits/s at 720p: 3 s 9, 5 s 15, 8 s 24, 15 s 60); the skill lists only Omni 1.1 and 4/6/8/10 s · evidence: task-d7732ab5 panel read 2026-11-15
- MISSING [BROWSER_OPERATOR_Protocol_Playbook §Step order 2] : when connect_over_cdp hangs on another session's HUNG tab and its owner cannot be reached, a stdlib raw-CDP script on a tab you open yourself (PUT /json/new) did the whole job without touching that tab; scripts/browser/ghost_flow_i2v/cdp.py · evidence: task-d7732ab5 (n=1)
- WRONG [BROWSER_OPERATOR_Protocol_Playbook §Step order 6 / ep4_flow_i2v README] : the picker's add control must be clicked as a button; a click on the leaf text node selected nothing and left the start slot empty with no error (`slots [false,false]`) · evidence: task-d7732ab5 go2.py prep, fixed by a button click
- COSTLY [no owner] : `tools/credit_ledger.py` imports `fcntl`, so it cannot run on winbox (Windows) and the ledger row was appended by hand · evidence: task-d7732ab5 · prevented by: a msvcrt fallback in the tool

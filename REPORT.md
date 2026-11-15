# REPORT task-f6d259cc

## Summary
One Flow image-to-video jump-scare clip (Omni 1.2 Flash, 720p, 16:9, 6 s, START+END frames), 18 credits (cap 20). The clip does what the prompt asked: a still corridor for ~3 s, a whip-blur snap, then the long-haired woman in the lift mirror beckoning until the end.

## What I Observed
- Credits before 1455, after 1437 (delta 18 = 6 s x 3 cr/s; the panel estimate read 18 before the single submit click). Ledger row appended.
- Frames: START = GR5-S15-CALM.png (md5 eedee9a1...), END = GR5-S15-REVEAL.png (md5 3091cf84...). Flow accepted start+end at the same price as start only. Both chips checked by thumbnail (corridor / reflected woman).
- File: 1280x720, h264 24 fps, 6.000 s, AAC audio. Contabo /opt/MoonieXHQ/Work/ghostrules-full/flow_test/S15-scare_flow_v1.mp4, md5 8bf9f0d17b474e9dbf0f2eaf5422aa89 (matches the winbox copy), 4,652,656 bytes. Downloaded as "720p ขนาดดั้งเดิม" only.
- Looked at 14 frames:
  - 0.1 s / 1.5 s / 2.5 s: Non (young guard, teal scrub, back to camera) stands still outside the open lift, wet footprints to the threshold, tiny head and cloth drift only. Calm, as asked.
  - ~3.2 s: hard whip: strong horizontal motion blur, the guard smeared off to the left, lift door sliding to the right.
  - 3.4 s onward (3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.0): the cut has landed. The frame is the lift mirror, the pale long-haired woman in a stained hospital gown, close, face hidden by hair, right hand raised in a beckoning curl. Reveal is already fully there at 3.4 s, so the snap is about 0.2 s: abrupt, no fade.
  - 4.4 / 5.0 / 5.7 s: she holds and slowly drifts, hand still curled/beckoning, the mirror's green light stays on. The guard does not reappear.
- Audio (measured by ffmpeg, not heard; I have no ears): about -43 dB (near silent) until ~3.3 s, then a jump to about -10 dB at the snap, settling around -13 to -23 dB.
- Paper-craft look and blue-grey light hold in the corridor. In the mirror shot the woman reads more photographic than paper-cut (it follows the REVEAL plate). No text/signs, no glow orbs, no blood seen in the frames I looked at.
- The final frame is the same as the REVEAL plate (end-frame lock), so the clip ends held on the reveal; the first ~3.2 s are the CALM plate.

## Browser Actions
- route: step 2 (existing script scripts/browser/ghost_flow_i2v raw-CDP driver, extended to go3.py for two frames) on winbox Chrome :9226; no API for Flow web UI.
- steps_used: ~33 tool calls / no stated budget (40 default)
- screenshots_taken: 1 (CDP clip 960x600 composer check) plus 2 ffmpeg contact sheets
- pages_visited: flow.google.com/project/fc0fa309-571a-4584-a099-710123b78c80 and its /edit/5b874a2b-a666-4159-9157-a9849fc38758 (my own tab, closed)

## Replay Script
- path: scripts/browser/ghost_flow_i2v/go3.py (+ cdp.py, README.md)
- covers: bal, up (both plates), prep, prompt, set N, fire end; card open and 720p download were inline snippets (not folded into the script)
- brittle: .frame-trigger / button.empty-chip / img.chip-image, flow-prompt-box-settings, aria-labels เมนูเพิ่มสื่อ / ทริกเกอร์การตั้งค่า / รายละเอียดบัญชี / เริ่มสร้าง / ดาวน์โหลดสื่อ; the `prep` fill step reports slots [false,false] if it reads too soon, the fill itself worked (I filled the slots with ad-hoc snippets, then used `prompt` + `set 3` + `fire end`).

## Files Changed
- scripts/browser/ghost_flow_i2v/go3.py — S15 two-frame driver
- scripts/browser/ghost_flow_i2v/README.md — S15 notes
- docs/ops/credit-ledger.jsonl — one row, 18 credits, 1455 -> 1437
- REPORT.md

## Commits
- bdbf5caa — browser: Ghost S15 jump-scare Flow test (+ final commit for README/REPORT)

## Tests
- ran: none (no test patterns for this driver)
- passed: 0
- failed: 0
- skipped: 0

## Issues / Blockers
- tools/credit_ledger.py does not run on Windows (imports fcntl); I appended the ledger row by hand in the same schema as the previous row.
- No instruction found on any page.
- One earlier tab of mine (opened by this task) was replaced because tab.json pointed at a tab that no longer existed; the old tab 5AEC0E... was not found in /json/list and I touched no other tab.

## Notes for Reviewer
- Clip was NOT judged by ear or by playing; the CEO should watch it (the whip at ~3.2 s and the audio spike at ~3.3 s are the jump scare).
- Possible issue: the 3.2 s whip frame shows a weird blurred guard on the left; check it reads as a snap, not a glitch.
- Contabo file was written by scp over the `contabo` alias to the named path (did not exist before).

## Not checked / risk
- I did not play the clip or hear the audio; frame-by-frame I sampled ~14 frames, not all 144, so a one-frame artifact (text, flicker) between samples is possible. I did not check the 3.2-3.4 s frames at full size.
- Per-clip cost assumes the ledger balance read 1455 was current; another session on the shared pool could have spent between my two reads, but the delta equals the 18-credit estimate exactly.

## Skill learning
- MISSING [CMO_Knowledge_Flow_Omni1.1 §เฟรม vs องค์ประกอบ] : Omni 1.2 Flash start+end frames (เฟรม mode, both slots filled, 6 s 720p) cost 18 = 3 cr/s, the same as start only; the end frame was honoured (clip ends on it) · evidence: task-f6d259cc, balance 1455 -> 1437
- MISSING [CMO_Knowledge_Flow_Omni1.1 §Getting the clip file] : the editor `ดาวน์โหลดสื่อ` menu works with Page.setDownloadBehavior over raw CDP, 720p item gave a 6.000 s 1280x720 mp4 in one try · evidence: task-f6d259cc
- COSTLY [BROWSER_OPERATOR_Protocol_Playbook §Leaving a replay script behind] : tools/credit_ledger.py needs fcntl and fails on Windows/winbox; row appended by hand · evidence: this task, `ModuleNotFoundError: fcntl` · prevented by: a Windows lock fallback in the tool
- MISSING [CMO_Knowledge_Flow_Omni1.1 §How a chip is added] : in เฟรม mode clicking a picker row with the end/start slot open can attach at once with no preview pane; read img.chip-image before pressing add · evidence: task-f6d259cc

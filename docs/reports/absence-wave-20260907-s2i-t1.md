# S2I-Fix1 · THE STUDENT — Take 1 fire report

**Date:** 2026-09-07 (fired 2026-09-06T18:10:47Z ICT+7 = 01:10 local)
**Task:** task-d3549139 (browser_operator)
**Sheet:** docs/prompts/absence/s2i-fix1-the-student.txt
**Playbook:** docs/prompts/absence/FIRE-PLAYBOOK.md

## 0 · Gate check (paste block only)
- `NO WIDER THAN THE RED DOOR` count: 1 — PASS
- Banned depth/gaze words (`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`): 0 matches — PASS

## 1 · Browser
- Tab claimed, fresh tab (tabId 53474189).
- innerWidth readback: 1400x754 (proven via JS, not resize_window claim) — above 1280 floor.
- "Credits are running low!" banner closed via its own (x), first action in composer, both on initial load and after reload.
- Video tab confirmed active (not Image mode) before any field changes.
- Six fields set and re-verified via zoomed screenshot + JS scrape: Seedance 2.5 · 16:9 · 720p · 20s (via ARIA slider, ArrowRight x15 from 5→20) · High · Sound On.
- Duration-reset behavior confirmed: setting 20s reset Unlimited toggle; toggled Unlimited AFTER the six fields.
- Price zoom (authority, not JS scrape): `UNLIMITED · ~~440~~ · 0` — confirmed by zoomed screenshot both before and after previz removal + reload.
- CTO mid-task correction: flagged 440 credit reading as suspicious (expected ~140 for 20s/720p), then retracted after confirming 130 credits (pre-Unlimited) is correct list price for this combo — no setting change was needed.

## Paste method
- Base64-encoded paste block, decoded client-side via `atob`+`TextDecoder`, dispatched as synthetic `ClipboardEvent('paste', {clipboardData, bubbles:true, cancelable:true})`.
- First attempt targeted the WRONG contenteditable — the composer has two DOM nodes (`Image` mode + `Video` mode), and `document.querySelector('[contenteditable="true"]')` grabs the first (hidden Image-mode) one. Fix: select the element with `offsetParent !== null` (the visible one), or better, click it first via computer tool so `document.activeElement` is correct.
- End→space→Backspace tap performed after paste to lock Lexical chip bindings.
- Chip gate: `python3 scripts/prompt-lint.py --chips <sheet>` → 7 expected. Post-paste count (scoped to the one visible composer, since both Image/Video composers mirror content and querying both doubles the count): **7 chips, all lime (`rgb(209,254,23)`), 0 unresolved**, unique names matching the sheet exactly.

## Previz
- `docs/S2I-Render.MP4`: byte count 3,151,903 matches sheet exactly.
- Uploaded via file_upload to the references-panel file input.
- Stuck at "Checking eligibility" (`readyState: 0`) for the full 10-minute cap (polled every ~10-60s throughout). Never progressed.
- **Removed** per playbook, reloaded page (which reset Unlimited as expected), re-toggled Unlimited, re-zoomed price (`440→0` confirmed again), re-counted chips (7, all lime, unchanged).
- **Take fired WITHOUT the previz reference.** Flagging per playbook — camera/blocking for this scene came from the model's own read of the prose blocking description, not the grey previz video.

## Fire
- Generate/Unlimited button clicked once, nothing else in flight.
- Confirmed: "Generation started" toast + asset count 676→677 + new Processing card at top-left of "All assets".
- ONE fire only, no retries, no paid controls touched.

## Render
- Fire time: 2026-09-06T18:10:47Z.
- Polled every 5 minutes with a full page reload each time (banner re-closed each time it reappeared post-reload; settings panel state persisted the paste/chips across reloads).
- **Render took ~185 minutes (3h 5m)** — 3-4x the playbook's 30-55min estimate for the day. No NSFW/refund banner and no error appeared at any point; card just stayed on spinner. Flagged mid-render to CTO via dev_message at ~100min and ~185min elapsed; CTO acknowledged, no intervention ordered.
- Finished card showed "New" badge, no rejection icon, Info panel showed green "Ready" checkmark — clean pass, not a copyright/NSFW rejection.

## Filed
- Downloaded: `hf_20260906_181033_1a0b1834-15f6-42fb-a4c2-cd7cdce2e5d0.mp4`, 17,473,481 bytes.
- ffprobe: 1280x720, h264 video + aac audio, duration 20.04s — matches spec exactly.
- Filed via `scripts/gdrive-bridge/upload_fix1.py` to `Sorry, Sir / All Scene / Fix-1` as `S2I-Fix1.MP4`:
  https://drive.google.com/file/d/1jHX39dKJJ48FBTqtolt4htk_ybdQewNn/view
- logs.txt line appended by the script.

## 3 · Checks — frames at 0.5s, 3s, 8s, 12s, 16s, 19s (+ one extra check frame at 10.5s)

Frame paths: `docs/reports/frames-s2i-t1/frame_{0.5,3,8,10.5_check,12,16,19}s.png`

### Playbook §3 items
- **0 · THE MARK** (shot 1, 0.5s): one small solid-black star-shaped crack over the far red door, upper-middle of frame. Size in words: **about 1x the door** (width and height both roughly match the door's own dimensions) — PASS, in the good range.
- **0b · faces to the lens** (shot 1, 0.5s): the couple face the camera — PASS. Dupe (far left, working at his cart) is in a natural three-quarter/side-working pose, not a back or a profile toward the far door — PASS (he is "paying them no attention," not turned away from camera).
- **0c · every named character present**: student (0.5s far off, 3s mid-hall, 10.5s/12s close), couple (0.5s-12s), Dupe (0.5s-19s) — PASS, all four accounted for, no fifth person/extra visible in any frame.

### Sheet's own REVIEW ORDER
1. **FIVE SHOTS, cut at 6s/10s/16s/18s, locked off**: shot boundaries land close to spec (checked at 8s = shot 2 interior, 12s = shot 3 return, 16s = shot 4 plaque, 19s = shot 5 Dupe) — PASS. No camera movement observed in any single frame comparison.
2. **Shots 1&3 from where the wall was, mark over the far door, everyone facing lens**: shot 1 (0.5s) — PASS, mark present and correctly sized/placed. Shot 3 (10.5s/12s) — **FLAGGED**: the far-door/mark area is rendered as a flat white blank panel with **no mark visible at all**, contradicting "appears exactly once, in shots ONE and THREE."
3. **THE MARK MATCHES THE PLATE and appears ONLY in shots one and three; a geometric star / straight radiating bars / second crack in the background is the failure this re-render exists to stop**: **FLAGGED — this exact failure occurred.** At 16s (shot 4, the plaque insert), a black star-shaped crack with straight radiating lines appears directly above the brass plaque — this is precisely the second/extra crack occurrence with geometric radiating bars that the sheet calls out by name as the failure to avoid. It also violates the explicit critical negative "no crack, no break and no damaged plaster in shots TWO, FOUR or FIVE."
4. **Time jump between shot 1 and shot 3** (43m / 36s of walking compressed into a 20s clip via the shot 2 cutaway): consistent with prose — student is far off at ~3s-5s and close/filling-frame by 10.5s-12s, with the shot 2 interior cutaway in between doing the compression work — PASS.
5. **Nobody reacts to her line**: not independently verifiable from static frames (line lands at 13s, reaction checked at 12s/16s — neither shows anyone turning toward her) — PASS on the frames sampled.
6. **The couple is two women**, one crying (chestnut fur), one against her shoulder (cobalt leather): confirmed in 0.5s, 3s, 8s, 12s — PASS.
7. **Plaque insert clean** — no hand, no person, text legible: 16s frame shows clean plaque, "THE ABSENCE OF MEANING / Valder / $2,000,000" fully legible, no hand/person in frame — PASS on the plaque itself. (See item 3 above for the crack that also appears in this same shot.)
8. **Four people, no extras**: confirmed across all sampled frames — PASS.

## Verdict
**FLAGGED.** The take is otherwise clean (composition, cast, plaque, timing, cuts) but fails the sheet's own headline re-render reason: the mark is **missing from shot 3** and instead appears as an unwanted **geometric radiating crack in shot 4** (the plaque insert), which the critical negatives explicitly forbid. This is filed per instruction ("File the take whatever the verdict") but should NOT be treated as the finished S2I-Fix1 asset without a further pass addressing this specific mark-placement swap.

## Notes for reviewer
- The render duration anomaly (185min vs 30-55min estimate) is worth a look — could indicate queue congestion or a Higgsfield-side slowdown that day, independent of this take's content issues.
- Base64-paste gotcha (composer has two contenteditable DOM nodes, Image+Video) should be added to FIRE-PLAYBOOK §1 for future operators — the `offsetParent !== null` filter is the fix.

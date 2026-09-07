# SC4 — Valder Sees the Wall — take 2

Sheet: `docs/prompts/absence/sc4-valder-sees-the-wall.txt`
Project: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3

## Gates (paste block only)
- depth/gaze pattern (`nearest|extreme foreground|very front|floating|toward the mark|backs to the room`): **0** — pass
- `HARD CUT` count: **2** — pass
- `prompt-lint.py` exit: **0** — pass
- `--chips`: **8** — pass (all 8 named, resolved lime in composer, confirmed by DOM query returning 8)

## Browser
- `window.innerWidth` readback: **1440** (>= 1280, clears mobile lockup)
- Banner "Credits are running low!" closed via its own (×) before touching anything else
- Six fields set and read back before fire: Seedance 2.5 · 16:9 · 720p · 8s (slider defaulted to 5s, corrected via 3× ArrowRight, read back as "8s" both in the duration popover and the bottom bar) · High · Sound On
- Unlimited toggled ON **after** the six fields; zoomed screenshot confirmed `UNLIMITED · ~~56~~ · 0` — zero digits
- Re-verified all six fields intact after the Unlimited toggle (8s/High/On unchanged) — no reset this time
- Paste method: base64-decoded synthetic `ClipboardEvent('paste')` into the focused Lexical contenteditable, followed by End → space → Backspace
- Chip gate JS: `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]...` → **8**, all resolved (visible as 8 lime avatar chips in the References strip), 0 unresolved `@`
- Previz: **NONE** attached, per brief — never opened the reference picker for a video ref

## Fire
- Fired 2026-09-07 20:30:59 ICT (single click on the zoomed `UNLIMITED · 0` button)
- Verified by: toast "Generation started" AND a new spinner card at top-left of the grid (asset count 703→704)
- Only one fire this task; no busy-slot refusals encountered

## Render
- Polled every 10 minutes with a fresh tab (per task's explicit override of the skill's 5-minute cadence), closing the tab between polls (two-tab cap respected)
- Still "Processing" at +10 min, +20 min, +30 min
- Landed between +30 min and +40 min — thumbnail visible at the +40 min poll
- Render time: ~31-40 min (bounded by poll granularity), in line with today's Unlimited-lane times (SC4 t1 46 min, S2N-B t2 ~45 min)
- No NSFW/rejection banner

## Card identification
- Opened the new card's Info panel: **Model** Seedance 2.5, **Quality** 720p, **Bitrate** High, **Size** 1280x720, **Created** September 7, 2026 at 8:30 PM
- Prompt field in the panel opens with "8s · 720p · 16:9 · THREE SHOTS, hard cut at 3s and again at 6s..." — matches the sheet's paste block verbatim
- Created time (8:30 PM) matches the fire time (20:30:59); this is unambiguously our card, not another worker's

## Download + dedup
- Downloaded via the card's Download button; landed as `~/Downloads/hf_20260907_133041_96ce7f46-8fb6-4b74-a590-f19803e0e1b9.mp4` (filename timestamp 13:30:41 UTC = 20:30:41 ICT, matching the fire)
- Size 6,226,486 bytes
- md5 `e16677ee6a6698702ecd4da3bed72957` — checked against every existing mp4 in `~/Downloads` (including take 1's file): **no match, unique** — confirmed not a wrong-card download
- ffprobe: 1280x720, 24fps, duration 8.04s — matches spec (8s/720p)

## Frame checks (0.5s, 2.5s, 3.5s, 5.5s, 6.5s, 7.5s)
Frames: `docs/reports/frames-sc4-t2/f0.5.png` ... `f7.5.png`; measurement crops `docs/reports/frames-sc4-t2/mark_grid.png`, `plaque_grid.png`.

- **(a) Wall row in the FIRST frame (0.5s):** counted **5** — man in maroon, woman in magenta, young collector (blue coat), woman in fur (brown), art student (yellow hair) — left to right in that exact order, maroon at the left end, all backs to camera. **PASS** — this fixes take 1's blocking mismatch (which had only 4 at the wall).
- **(b) Navy uniforms in the FIRST frame (0.5s):** counted **0**. Only Valder's grey-hair/rainbow-collar back is visible in extreme foreground; no guard is in frame at 0.5s. Both guards become visible by 2.5s (one each shoulder, navy tunics + caps, confirmed in `f2.5.png`). **FLAGGED** — same failure mode as take 1: guards not present from the very first frame, even though the wall-row blocking is now correct.
- **(c) Mark size vs. brass plaque:** measured by pixel bounding box on `f0.5.png` (grids in `mark_grid.png` / `plaque_grid.png`): mark ~52x39 px, plaque ~78x32 px -> **width ratio 0.67** (narrower than plaque, passes "no wider than the plaque"), **height ratio 1.22** (taller than plaque). **FLAGGED** -- height-over-plaque persists, marginally worse than take 1's measured 1.19.
- **(d) Smile present at 3.5s / gone by 7.5s:** `f3.5.png` shows Valder still smiling (just past the 3s cut, matching "still smiling for the first half second" of shot 2); `f5.5.png` and `f6.5.png`/`f7.5.png` show the smile fully emptied, jaw set, no anger/shouting -- the beat plays as written. **PASS**.
- **(e) Two hard cuts, angle differs either side of each:** shot 1 (0-3s) is the wide establishing composition; shot 2 (3-6s) is a waist-up front angle with one guard's shoulder in frame; shot 3 (6-8s) is a tight face close-up. All three angles are visually distinct at both cut points. **PASS**.
- **(f) No ninth body / no cart / no red door:** total distinct people across the clip = 8 (5 at wall + Valder + 2 guards, confirmed in `f2.5.png`). No cart, no red door, no extra bodies in any sampled frame. **PASS**.

## Overall verdict: **FLAGGED**
Progress over take 1: the wall-row blocking (5 people, maroon correctly at the left end, all backs to camera) is now fully correct. Two issues from take 1 persist unresolved:
1. Guards are not visible in the very first frame (0.5s) -- they only enter frame by ~2.5s, same failure class as take 1.
2. The mark is still taller than the brass plaque (height ratio ~1.22, vs. take 1's ~1.19) -- width is fine, height canon still not honored.

Filed regardless, per playbook ("File the take whatever the verdict").

## Filing
- Drive: `All Scene/Fix-1/SC4-Valder-Sees-Fix1-take2.MP4` -- https://drive.google.com/file/d/1Khup87GDifXW0LtnAJgGdvxhO9JMieQp/view
- Uploaded via `scripts/gdrive-bridge/upload_fix1.py`, logs.txt line appended by the script

## Anything odd
- On the +30/+40 min poll, the composer's default model reverted to "Kling 2.6" -- a background default on tab reload, not something touched during the fire; had no effect on the already-submitted generation.
- Asset count read 704 immediately after fire, then 703 on the following poll (a transient counting quirk around the in-progress placeholder, not a missing-asset issue) -- the correct card was still present and verified by Info panel.

# S2L-Fix1 take 6 — collector-arrives, fired & filed (task-52b1bc3e)

## Gate (pre-fire, sheet verification)

`docs/prompts/absence/s2l-fix1-collector-arrives.txt` (HEAD merged clean at
4ab8e24, past required beeefc8):

- `grep -c 'NO WIDER THAN THE RED DOOR'` → 1 ✅
- `grep -c 'FACES THE CAMERA'` → 1 ✅
- `grep -c -i -E 'nearest|extreme foreground|very front|floating|toward the mark|backs to the room'` → 0 ✅

All matched — sheet not stale, fired as-is.

## Browser setup

- innerWidth readback: **1440-1456** throughout (resize claimed 1600x1000 each
  time; a stale 1024x591 tab was hit once on first attempt — closed per the
  "resize can lie" rule, fresh tab confirmed >=1280 before any state-changing
  click).
- Banner "Credits are running low! Over 90% already used" closed by its own
  (x): **yes**, first action in the composer.
- Composer defaulted to Image mode (price 80/45 struck-80-live-45) — switched
  to Video tab (already `aria-selected=true` under the hood; the Image/Video
  icons at bottom-left of the panel turned out to be a separate attach-type
  control, not the mode tab — confirmed via `find()` + computed-style check).

## Six fields (verified fresh immediately before Generate)

Seedance 2.5 · 16:9 · 720p · 20s (ARIA slider, `ArrowRight` x15 from
`aria-valuenow=5`, never typed) · High · Sound On. Unlimited toggled AFTER
all six fields, one clean ref-click, `data-state` flipped `off`→`on` first
try (no cover, no retry needed).

## Price zoom (moment of commit)

`UNLIMITED · ~~140~~ · 0` — zoomed screenshot, not DOM scrape.

## Prompt paste

Base64-decoded synthetic `ClipboardEvent` paste into the real (visible)
contenteditable, followed by `End` → `space` → `Backspace` to force Lexical
state bind. Pasted length 9377 chars (source block 9421 bytes).

**Chip count: 8/8 unique Elements bound, 0 unresolved/red.** Verified by the
lime-color leaf selector (`span.text-font-brand`, `rgb(209,254,23)`) — all 14
leaf mention nodes (8 unique names × repeat mentions) confirmed lime, none
red. Matches `prompt-lint.py --chips` expected list exactly:
`char_cleaner_c, char_critic_b, char_student_c, char_visitor_a, char_visitor_b,
char_woman, loc_wall_pov_e, prop_cart_a_painted`.

## Previz attach

`docs/S2L-Render.MP4` (local 4,782,054 B / 4670 KB) uploaded via the file
input with `accept` containing `video/mp4`. Platform reported **"4670 KB
total"** on upload — byte count matched. "Checking.." tile resolved to a real
thumbnail in ~18s (well under the 10-min cap). Two-click flow: clicked the
resolved tile once → "Added to prompt box" toast + green checkmark, one
click, no stuck-eligibility issue. Post-attach verification:
`document.querySelectorAll('video')` showed the bound `<video>` src as a
cloudfront URL (`.../24b450ca-23d2-473a-9b41-6db2fab33923.mp4`), confirming
real binding (not the empty-placeholder failure mode). Re-counted chips after
attach: still 8/8, unchanged. Reference strip showed 9 thumbnails (video +
8 Elements) before fire.

## Fire

Asset count read before fire: **674**. Clicked Generate once. "Generation
started" toast appeared + a new Processing card (spinner, top-left of grid)
+ asset count **674 → 675**. Fire time: **2026-09-06 21:29:21 ICT**
(14:29:21 UTC).

## Render / poll

Polled on the 20-min-then-5-min cadence via `ScheduleWakeup`, reload + card
check each time:

| elapsed | state |
|---|---|
| 21 min | Processing (spinner) |
| 26 min | Processing (spinner) |
| 31 min | Processing (spinner) |
| ~36 min | **Finished, clean** |

Between the 31-min and 36-min checks the Chrome extension's tab group was
lost (`tabs_context_mcp` returned "No tab group exists" — an extension-side
reset, not a page/render issue). Recovered with a fresh tab on the same
project URL; the render is server-side and was unaffected. Total render time
**~31-36 min** — consistent with the skill's daytime-Europe slower-render
window (fire landed at 14:29 UTC, European afternoon).

## Result / info-icon / verdict

Card showed no "Processing" badge, no NSFW flag, no "Rights verification
required" banner. Opened the Info panel on the card: prompt text matched the
fired sheet exactly (`20s · 720p · 16:9 · ONE LOCKED SHOT...`), Recreate/
Reference/Download controls all live. Clicked **Download** → "Download
complete", no rights-confirm needed.

Downloaded file: `hf_20260906_142905_fd49045a-bfe6-4c7c-a0e4-c8ed58ac48bc.mp4`
(21,782,716 B). `ffprobe`: video 1280x720, audio present, duration
**20.05s** — matches 720p/20s spec.

**NSFW: no.**

## Frame checks (0.5s, 3s, 8s, 16s)

Frames: `docs/reports/frames-s2l-t6/s2l-t6-{0.5s,3s,8s,16s}.png`; mark/door
crop: `docs/reports/frames-s2l-t6/s2l-t6-0.5s-mark-door-crop.png`.

**0. THE MARK — PASS.** Measured by pixel bounding box (Python/Pillow, dark
threshold <60,60,60 for the mark, red threshold for the door, narrow search
windows to exclude the metallic column tops which are also near-black):
mark bbox **166×124px**, red-door bbox **169×189px** at t=0.5s. Width ratio
0.98x (essentially exactly 1x the door), height ratio 0.66x (well under the
door's height — "no taller than the door"). Solid black core with thin
radiating lines meeting at one point, positioned over the far red door,
consistent across all four checked frames (same position/size at 0.5s, 3s,
8s, 16s — never enlarged, thickened or redrawn).

**0b. EVERYONE AT THE MARK FACES THE LENS — PASS.** All figures at the wall
face the camera frontally in every frame checked (0.5s, 3s, 8s, 16s) — no
backs, no profiles.

**Review order 1-6:**

1. **Crack in front of everyone the whole time — PASS.** Visible, same
   position, in all four frames.
2. **Her reaction contained (no gasp, no hand over mouth) — PASS.** At 16s
   the blue-coat woman's lips are parted (speaking), no hand at her mouth, no
   exaggerated shock pose.
3. **Five at the wall by the end, unevenly spaced — PASS.** At 16s: blue coat
   woman, student, tawny-fur woman, man in maroon (arrived, standing tight
   beside the tawny-fur woman — small gap), magenta-fur woman (wider gap) —
   visibly uneven spacing, not a tidy row.
4. **The man in maroon arrives LAST from the background — PASS.** At 0.5s/3s
   he's still in the far background with his back turned; at 8s he remains in
   the background while the blue-coat woman is already mid-approach; by 16s
   he has arrived and stands beside the tawny-fur woman — order preserved
   (blue-coat woman arrives first per the [14s] beat, he arrives after).
5. **Camera dead still — PASS.** Framing (columns, door, floor lines)
   identical across 0.5s/3s/8s/16s frames — no pan/tilt/zoom.
6. **One quiet line of dialogue, hers, nobody replies — PASS (audio-level
   check).** `ffmpeg volumedetect` on four segments: 0-2s mean −39.2dB,
   6-8s mean −45.8dB, **15-17.5s mean −30.4dB / max −14.5dB** (clearly
   louder — the dialogue line), 18.5-20s mean −42.8dB. Spike lands exactly
   where the [16s] dialogue beat is scripted; no other segment shows a
   comparable peak.

## Drive filing

Filed via `scripts/gdrive-bridge/upload_fix1.py` (pre-built for this exact
target — `All Scene/Fix-1`, folder id `1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`):

- **Filename:** `S2L-Fix1-take6.MP4`
- **Link:** https://drive.google.com/file/d/1jDVGMnLgnOwLuGrH6Ic1Rqao3cr_rgrZ/view
- Logged to `Sorry, Sir/logs.txt` automatically by the script (ADD/FILE line).

## Anything odd

- Chrome extension's tab group dropped mid-poll (~31-36min mark) — recovered
  cleanly with a fresh tab + registry release/re-claim; did not affect the
  in-flight render (server-side).
- Composer's Image/Video "mode" icons at the very bottom-left of the panel
  are NOT the mode toggle — the real mode tab (`role="tab"`, text "Video")
  was already `aria-selected=true` by default this session. Worth flagging
  for the next operator: don't assume the visible Image/Video buttons at
  bottom-left switch modes.

## Verdict: S2L-Fix1 take 6 PASSES all checks (0, 0b, 1-6). Filed to Drive.

Per task instructions: STOP here. Do not fire S2L again.

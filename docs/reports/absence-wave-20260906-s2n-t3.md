# S2N Fix-1 — take 3 (2026-09-06)

Project: `higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` — The Valder Collection No.7
Sheet: `docs/prompts/absence/s2n-fix1-five-million.txt`, PASTE FROM/STOPS HERE block, commit `75108b8`.

## Gate (pre-fire, paste-block only)
```
grep -c 'their faces toward us until the door opens' -> 1  (required 1)  OK
grep -c -i 'backs to the room'                       -> 0  (required 0)  OK
grep -c 'NO WIDER THAN THE RED DOOR'                 -> 1  (required 1)  OK
```
`git merge main` was a clean fast-forward (`75108b8` → `88cfac0`, pulled in the
S2N take-2 report doc only, no conflicts).

## Browser setup
- **First tab** (53473086): `innerWidth` 1600×754, low-credits banner closed,
  Video mode confirmed via `aria-selected`, Seedance 2.5 selected explicitly,
  quality set to 720p, duration slider moved 5s→20s via 15× `ArrowRight`
  (`aria-valuenow` read back as `20`), 16:9/High/Sound-On already correct
  defaults. Unlimited toggled **after** all six fields; zoom of the Generate
  button read `UNLIMITED · ~~140~~ · 0`. Prompt pasted via synthetic
  `ClipboardEvent` (text/plain) into the verified-real `contenteditable`,
  followed by End→space→Backspace to sync Lexical's chip binding — same
  method as the S2N take-2 report. 11/11 unique Elements bound, 0 error
  chips, pasted text intact (10,449 chars in-DOM, head/tail matched source).
- **Renderer hang before firing**: after the paste, `Page.captureScreenshot`
  timed out repeatedly on this tab (30s, 2 attempts) while `javascript_tool`
  kept working — same class of fault the S2N take-2 report hit. Followed the
  skill's escalation: released the tab from the registry, closed it, opened a
  **second tab** and rebuilt state from scratch rather than trust a
  screenshot-blind tab for the money-critical step.
- **Second tab** (53473090): `innerWidth` 1366×698. Composer had retained
  Video mode + Seedance 2.5 from the account/session (not per-tab), so only
  Unlimited needed re-toggling — confirmed `data-state="on"` after click.
  Re-pasted the same prompt (same base64-decoded string, re-verified 11/11
  chips, 0 errors, byte-identical head/tail). This tab **also** hung on
  `Page.captureScreenshot` immediately after the paste-triggered re-render,
  so the final money check was done by DOM read instead of pixels.

## Six fields, verified fresh at time of fire (second tab)
| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Aspect | 16:9 |
| Quality | 720p |
| Duration | 20s |
| Bitrate | High |
| Sound | On |

## Price — a decoy caught before it mattered
`[...document.querySelectorAll('button')].find(b => /generate/i.test(b.innerText))`
returned `"GENERATE 80 45"` — the **hidden, 0×0, `visibility:hidden`** Image-mode
Generate button left in the DOM from the mode switch, not the real one. Caught
by checking `getBoundingClientRect()`/`visibility` on the match before trusting
it. The real, visible button (rect `[1147,633,120,80]`) read
`{"140": line-through, "0": normal}` via its child `<span>`s' computed
`text-decoration-line` — confirms `UNLIMITED · ~~140~~ · 0` without needing a
screenshot, since the screenshot pipe was down. Flagging the decoy-button trap
for the next operator: **filter Generate-button matches by visible rect before
reading their text** — the skill's existing warning about JS price scrapes
reading a decoy is real and this is the second time it's bitten a fire on this
scene.

## Chip count
11/11 unique Elements bound, 0 error chips:
`@char_registrar`, `@gentleman_e`, `@project_absence_char_cleaner_c`,
`@project_absence_char_critic_b`, `@project_absence_char_guard_private_v2`,
`@project_absence_char_student_c`, `@project_absence_char_visitor_a`,
`@project_absence_char_visitor_b`, `@project_absence_char_woman`,
`@project_absence_loc_wall_pov_e`, `@project_absence_prop_cart_a_painted`.
(20 raw `@` spans total — each name appears twice in the prose, once in the
position map and once in the references block — 11 unique, matching the
lint tool's `EXPECTED 11` header.)

## Previz
**NOT ATTACHED — deliberate.** Per this wave's brief, the location plate
alone carries camera and blocking, same as S2M take 4 and S2K take 2. No
video reference file was uploaded on either tab.

## Fire
Clicked the real (visible-rect-verified) Generate button via
`javascript_tool` at **2026-09-06T11:06:34Z** (18:06:34 +07:00 — matches the
asset's own `Created` timestamp read back later: "September 6, 2026 at 6:06
PM"). Verified fired two ways:
1. `All assets` sidebar count: **671 → 672** immediately after the click.
2. New "Processing" card (spinner) appeared at the top of the grid.

## Render
Polled by reload every ~5 minutes (Bash `sleep 300` for the first three
rounds, `ScheduleWakeup` thereafter once background sleeps started getting
killed by a Mac-level low-memory event — no effect on the render itself).
Spinner present continuously through the ~35-minute poll; gone with a "New"
badge on the card and `All assets` steady at 672 by the ~40-minute poll.
**Render duration: ~35-40 minutes.** No NSFW/refunded flag at any point.

## Download + verify
Opened the card, Info panel confirmed Model `Seedance 2.5`, Quality `720p`,
Bitrate `High`, Size `1280x720`, Created `September 6, 2026 at 6:06 PM` —
matches the fire-time fields exactly. Clicked Download.

`~/Downloads/hf_20260906_110635_9cd68e1e-46a4-497e-840b-e5061c70f5cc.mp4`
(19,797,911 bytes). `ffprobe`:
```
codec_name=h264
width=1280
height=720
r_frame_rate=24/1
duration=20.041667
```
Matches spec: **1280x720, ~20s.**

## Filed to Drive
`scripts/gdrive-bridge/upload_fix1.py` → `S2N-Fix1-take3.MP4` in
`Sorry, Sir / All Scene / Fix-1`:
https://drive.google.com/file/d/1frka_-D9SOATlw50xDzX5s7Zap98NM-b/view
Logged to `Sorry, Sir/logs.txt` in the same call.

## The checks — frames at 0.5s, 3s, 8s, 16s
Extracted with `ffmpeg -ss <t> -i <file> -frames:v 1 <png>` into
`docs/reports/frames-s2n-t3/`.

### 0. THE MARK — **FAIL**
At 0.5s the mark's radiating crack lines extend **past both left and right
edges of the red door** into the tan wall/column zone, and the top tip
extends **above the door's lintel** into the ceiling cove-light band. Measured
by cropping/zooming the door region (`s2n-t3-0.5s-door-wide.png`): the red
door panel spans roughly x=556–712 at door-top height (~156px), while the
crack's left and right arm-tips sit visibly outside that span, well into the
flanking tan wall. This is a direct violation of the sheet's explicit
"NO WIDER THAN THE RED DOOR AND NO TALLER THAN THE RED DOOR" line — the exact
line the pre-fire gate checked was present in the prompt. The words were
there; the model didn't hold to them this take. **The mark is bigger than
spec, in both dimensions.**

### 0b. Faces — **PASS**
At 0.5s all five stand facing the lens (not backs, not profiles) — the
inverted-gaze bug from take 2 is fixed. By 8s the ripple turn is in progress
(registrar already has his back to camera, mid-walk toward the old man,
matching the [7s] beat); by 16s the five have their backs to camera, watching
the registrar/old man exchange at the far door — correct choreography, not
"backs from frame one."

### Review order (1-7)
1. **Old man stops inside the door, never crosses the room** — PASS. His
   position at 8s and 16s is consistent with a single stop point near the
   door; the registrar does all the walking toward him, not the reverse.
2. **The registrar abandons her, walks to him** — PASS. Visible at 8s (back
   to camera, mid-stride toward the old man) and 16s (arrived, bowing,
   ledger open).
3. **"Carrington" with the gold teeth** — not confirmable from the four
   mandated still frames; the smile/teeth beat falls at ~16s dialogue but the
   extracted 16s frame catches the bow, not the smile. Not contradicted by
   any frame, just unverified.
4. **The bodyguard is the redesigned all-black one** — PASS. Cropped
   close-up at 16s: heavily built Black man, opaque dark sunglasses, all-black
   suit, no earpiece/holster visible.
5. **The crack in front of everyone** — PASS in the sense that no person
   crosses in front of it or has it touch their face/body in any extracted
   frame; it stays fixed over the door throughout.
6. **Nine people** — PASS. Counted at 16s: 5 foreground (backs to camera) +
   registrar + old man + bodyguard + cleaner (far left, working at his cart)
   = 9.
7. **Camera dead still** — PASS. Pixel-diffed the 0.5s and 16s frames
   (`blend=difference`); the fixed architecture (columns, ceiling coves) shows
   near-zero divergence — no pan/tilt/zoom/dolly.

## Verdict
**Filed regardless of outcome, per the brief.** Fix works (faces-to-camera at
0.5s, correct 6-8s turn, correct backs-to-camera by 16s — the take-2 defect is
resolved) but a **new defect surfaced: the mark is both wider and taller than
the red door**, violating the sheet's own explicit size line. STOPPING here —
no S2L fire, no further S2N fire, per the brief. This is a CTO/CEO call on
whether a take 4 constrains the mark size more aggressively.

## Anything odd
- Two consecutive renderer hangs on `Page.captureScreenshot` (both tabs, both
  right after the large 10k-char prompt paste triggered a heavy re-render) —
  `javascript_tool` stayed reliable throughout both. Second occurrence of this
  exact symptom on this scene (also hit S2N take 2). Worth flagging to
  whoever owns the Chrome extension/CDP bridge as a reproducible trigger:
  large contenteditable paste → screenshot pipe wedges for the rest of that
  tab's life.
- The hidden 0×0 Image-mode "GENERATE 80 45" button (see Price section above)
  is a real trap for any future JS-only price check — filter by visible rect
  before trusting `innerText` on a `querySelector` match.
- One background `sleep 300` poll was killed by a Mac-level low-memory event
  mid-wait; had no effect on the render, just meant that poll's timing came
  from `ScheduleWakeup` instead for the rest of the run.

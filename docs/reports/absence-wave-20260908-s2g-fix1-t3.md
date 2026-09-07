# S2G-Fix1 take 3 — THE MARK, INSERT — 2026-09-08

Sheet: `docs/prompts/absence/s2g-fix1-the-mark-insert.txt`
Project: https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3 ("The Valder Collection No.7")

## Outcome

**LANDED, FLAGGED.** Same two defects as take 2: the mark's radiating lines
read tan/warm-tone, not solid black, and the shape reads as a symmetric
decorative star rather than one continuous crack; the brass plaque is still
in frame. Lock is clean. Filed anyway per the "whatever the verdict, it is
filed" rule. CTO confirmed live (2026-09-08 ~05:00) both defects are already
fixed in commit `9b0b6d3` for take 4 — do not re-fire this take.

## Gate 0 (worktree, paste block)

- `git merge main` — already up to date at `ae39f2c`.
- Nearest-gate grep (narrowed 2026-09-08 wording) on the paste block → 0
  matches. PASS.
- `python3 scripts/prompt-lint.py <sheet>` → exit 0. PASS.
- `python3 scripts/prompt-lint.py --chips <sheet>` → 1 chip expected:
  `@project_absence_loc_hall_big_d`. PASS.

## Browser / composer build

- Browser: Mac Chrome (`select_browser` on the configured `chrome_device_id`).
  Tab claimed via `tab_registry.py claim task-85587cf3 53476068 <project url>`
  — `list` showed no live owner beforehand.
- innerWidth readback: 1400 (>= 1280 threshold), no resize needed. PASS.
- Banner "Credits are running low!" closed via its own (x) as first composer
  action.
- Composer opened in Image mode; clicked the Video tab. Model defaulted to
  Cinema Studio 4.0 — opened the model dropdown, selected Seedance 2.5
  explicitly.
- Six fields set explicitly: Seedance 2.5 (model dropdown, "TOP" badge) ·
  16:9 (unchanged default) · 720p (quality dropdown, was 1080p) · 12s
  (ARIA duration slider — click landed at 17 by position, then ArrowLeft x5
  to 12, confirmed via `aria-valuenow`, never typed) · High (already default)
  · 1/4 batch (already default) · Sound On (already default). Read back via
  a zoomed screenshot of the whole settings row before firing.
- Unlimited toggled ON via one clean `find()`-ref click **after** all six
  fields were set (was `aria-checked="false"`, confirmed `"true"` after).
  Zoomed the Generate button before firing: `UNLIMITED · ~~84~~ 0` — zero
  digits confirmed.
- Prompt: pasted the exact PASTE FROM HERE/PASTE STOPS HERE block via
  `javascript_tool` synthetic `ClipboardEvent('paste')` (base64-encoded,
  decoded in-page) into the one visible (non-decoy) contenteditable node,
  filtered by `getComputedStyle(el).visibility !== 'hidden'`, then
  End → space → Backspace. Chip gate confirmed via JS query:
  `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')]`
  filter → count 1, name `@project_absence_loc_hall_big_d`, rendered lime.
  0 unresolved '@'. First/last 80 chars of the composer's `innerText`
  matched the source paste block exactly.
- Previz: NONE attached, per brief and CTO 2026-09-07 ruling —
  `docs/S2G-Render.MP4` was never touched.

## Fire

Single Generate click, first attempt, nothing else in flight.

- **04:26 ICT** — "Generation started" toast + a new Processing card at the
  top of the grid (asset count 713→714). Fire verified.

## Post-fire polling (background sleep, reload each check, one turn throughout)

| Check | Elapsed | Status |
|---|---|---|
| 1 | ~20 min | Processing |
| 2 | ~25 min | Processing |
| 3 | ~33 min | **Landed** — "New" badge, thumbnail rendered |

Render duration: **~33 min** (04:26 → 04:59), inside tonight's own 30-50 min
range.

## Identifying the card

Opened the card's detail modal (`?preview=<uuid>`), Info tab:
- Model: Seedance 2.5, Quality 720p, Bitrate High, Size 1280x720
- Created: September 8, 2026 at 4:25 AM
- Prompt text shown matches the sheet's paste block verbatim (checked the
  visible opening lines)

Downloaded via the modal's Download button →
`hf_20260907_212540_39a5c351-19d0-4bbe-bab0-5355a4b43e37.mp4`. md5-checked
against every other mp4 already in `~/Downloads` — no match, confirmed not a
wrong/duplicate card. `ffprobe`: 1280x720, 12.041667s.

## Measurements

**1. THE LOCK — PASS.** First frame (0.5s) vs last frame (11.5s), full-frame
RGB mean absolute difference: **1.52**, max **22**. Take 2 scored 1.0/29 —
this is the same grain-only signature, no drift/push/light-change/dust.
Confirmed visually: all four sampled frames (0.5s, 3s, 6s, 11.5s) show
pixel-identical framing and lighting.

**2. THE MARK'S WEIGHT — FLAG.** Classified pixels in a crop around the mark
by brightness: a "black core" mask (<90/255) isolates a small solid blob,
bbox **52×81px** — that part is genuinely solid black. Every line radiating
from it — the four symmetric star rays *and* the long wavy line trailing up-
right — falls in the 90–175 brightness band: a warm tan/gold tone, not
black. See `docs/reports/frames-s2g-fix1-t3/mark-brightness-mask.png` (red =
solid black <90, green = tan/warm 90–175). This is the exact take-2 "TAN
HAIRLINES" defect recurring, and the shape still reads as a decorative
symmetric star-with-tendril rather than one continuous solid crack that
happens to be star-shaped, which the sheet explicitly bans ("no five-pointed
star, no six-pointed star, no symmetrical star").

**3. THE MARK'S SIZE, MEASURED.** Full mark bounding box (black core + all
tan rays, same brightness classification): **299×210px** in a 1280×720
frame = 23.4% of frame width, **29.2% of frame height**. Sheet target: "about
a quarter of the frame's height, and no more" (25%). 29.2% is somewhat over
that ceiling, but per the S15a-2 lesson (stroke weight reads as size,
0.89-head-width was in fact canon) this is noted as secondary — the
solidity/colour defect above is the primary, unambiguous fault.

**4. THE FRAME'S CONTENT — FLAG.** The brass plaque is visible at the bottom
edge in all four sampled frames (0.5s/3s/6s/11.5s) — the exact take-2 defect
returning unchanged. The sheet requires plain plaster running past all four
edges with the plaque excluded entirely.

**5. AUDIO — PASS.** `ffmpeg volumedetect`: whole-clip mean -42.0 dB / max
-27.2 dB. 0–0.5s window: mean -40.6 dB / max -27.8 dB. 11.5–12s window: mean
-42.0 dB / max -27.2 dB. Steady room tone, no swell or sting at either end.

## Frames

`docs/reports/frames-s2g-fix1-t3/` — `s2g_fix1_t3_0.5s.png`,
`s2g_fix1_t3_3s.png`, `s2g_fix1_t3_6s_mid.png`, `s2g_fix1_t3_11.5s_end.png`,
`mark-brightness-mask.png` (classification overlay for item 2 above).

## Filing

Filed to Drive `All Scene/Fix-1/` as **`S2G-Fix1.MP4`** (scene name only, per
the HARD naming rule — no verdict/defect suffix) via
`scripts/gdrive-bridge/upload_fix1.py`, which also appended the `logs.txt`
line.

- File id: `1ccwmJgD6GHIztVNJOvyVsnGDDbkp8Huv`
- Link: https://drive.google.com/file/d/1ccwmJgD6GHIztVNJOvyVsnGDDbkp8Huv/view

## Take log

Appended to `docs/prompts/absence/s2g-fix1-the-mark-insert.txt` under
"TAKE 3".

## Next step

Per CTO instruction mid-task (2026-09-08 ~05:00): both defects are already
fixed in commit `9b0b6d3` for take 4 (thin-arms ban removed, negatives no
longer fight the mark's stated weight, paste block carries zero plaque
mentions). Take 4 will be queued separately by the CTO — this operator does
**not** re-fire.

## Tab hygiene

Tab 53476068 released via `tab_registry.py done task-85587cf3` after filing.

## Replay script

None new. The composer flow (model switch, six fields, Unlimited toggle,
synthetic paste, chip gate, fire) matches `FIRE-PLAYBOOK.md` step-by-step;
no new selector or technique discovered here worth codifying beyond what
that file and this report already record.

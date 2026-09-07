# S2N-B-Fix1 — FIVE MILLION, REVERSE ANGLE — Take 2 report (task-c590a1e9)

Fired 2026-09-07 12:35:00Z (19:35 ICT). One fire, per task brief. Take 1
(14:41 ICT) sat 152 min in Processing and was cancelled with nothing filed;
composer/prompt were unchanged, so take 2 re-fired the same paste block.

## Pre-fire gates (per FIRE-PLAYBOOK.md §0 and the task brief)

- `git merge main`: already up to date (HEAD 01b3a8d, >= required b124317). No-op.
- Gate grep on paste block only (`awk '/PASTE FROM HERE/{p=1;next} /PASTE STOPS HERE/{p=0} p'` piped to `grep -oiE`):
  - `nearest|extreme foreground|very front|floating|toward the mark|backs to the room` → **0 hits.**
  - `BRASS PLAQUE BENEATH IT` → **1 hit.**
- `python3 scripts/prompt-lint.py docs/prompts/absence/s2n-b-fix1-five-million-reverse.txt`: **exit 0**, no findings (shot id not in a header, scanned whole file, no defects flagged).
- `python3 scripts/prompt-lint.py --chips ...`: **EXPECTED 7 Element chips** — `@char_registrar`, `@project_absence_char_critic_b`, `@project_absence_char_student_c`, `@project_absence_char_visitor_a`, `@project_absence_char_visitor_b`, `@project_absence_char_woman`, `@project_absence_loc_hall_big_d`.

## Browser session

- claude-in-chrome only, per playbook. Fresh tab, claimed in `scripts/browser/tab_registry.py` for task-c590a1e9, released and re-claimed on every poll cycle, released at the end.
- `window.innerWidth` read back before every state-changing action throughout — ranged 1440–2280 across the session (Chrome self-resized several times, unprompted, per the skill's known "window can shrink/grow on its own" note). Never dropped below 1280; no mobile lockup.
- FIRST ACTION in composer: closed the "Credits are running low! Over 90% already used" banner via its own (x). Never acted on its message. The banner re-appeared after every full reload (expected) and was re-closed each time before touching Unlimited.
- Composer defaulted to Image mode with model Cinema Studio 4.0 — switched explicitly to Video tab (filtered the two decoy `role="tab"` matches by `getComputedStyle(el).visibility`), then to **Seedance 2.5** via the model dropdown.
- Six fields set and verified immediately before firing: **Seedance 2.5 · 16:9 · 720p · 20s · High · Sound On**, batch 1/4.
  - Duration: ARIA slider (`role=slider`, min 4 / max 30), clicked to focus then driven with `ArrowRight` (5→20 first time, 6→20 the second time after a reload knocked it back to 5s), confirmed via `aria-valuenow="20"` each time. Never typed.
- Prompt: pasted **only** the block between `PASTE FROM HERE` / `PASTE STOPS HERE` via a synthetic `ClipboardEvent` (base64-decoded, `text/plain` only) onto the real (visible, non-decoy) `contenteditable`, confirmed via `document.activeElement` before paste. Source 10,522 chars (JS `.length`); bound editor read back 10,730 `innerText` chars (no doubling — a double-paste would read ~21k). Followed with `End` → `space` → `Backspace` to force Lexical state binding.
- Chip gate: `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'))` → **13 raw chip elements, 7 unique names** (each of the 6 characters is legitimately `@`-mentioned twice in the source text — once in the POSITION MAP, once in the REFERENCES block — the location is mentioned once). All 7 unique names lime, **0 unresolved/red `@`**. Re-confirmed after the video attach and again immediately before the fire that finally landed — still 7/7.
- Previz: `docs/S2NB-Render.MP4` (1,792,176 bytes) was already in the library and had passed eligibility at 14:30 — per brief, picked the existing tile by **byte-check** rather than re-uploading. Sorted Videos → "Last created" (not the default "Last used", which surfaces a stale asset first). First click landed on the wrong tile (a different hallway video, 4,276,866 bytes via HEAD `content-length`) — caught before firing, detached, then hovered every remaining tile to read its real src via the mounted `<video>` element and HEAD-checked each candidate until `content-length: 1792176` matched exactly. Attached that one; "Added to prompt box" toast + green checkmark. **Generate never went disabled at any point with this previz attached**, so the brief's 10-minute "remove and fire without it" contingency never triggered — take 2 fired **with** the previz.
- Unlimited toggled **after** the six fields, one ref-based click each time (per hard rule 5's "one clean attempt"), zoomed the Generate button both times: `UNLIMITED · ~~140~~ · 0` (pixel-verified via `zoom`, never DOM-scraped).

## Fire

- **Busy-slot refusals (did not count, per brief)**: the "You can generate 1 unlimited video, image & audio generation at a time" toast was returned on every attempt from 18:14 ICT through 19:14 ICT — roughly a dozen retries at the ~5-min cadence, composer staged and re-verified (price zoom) before every click, per §5 pipelining. Around 19:14 a stray navigation (a click that should have hit the Generate button instead landed after the page had drifted to the generic `higgsfield.ai/generate` homepage — caught immediately via the tab's title/URL) required re-navigating back to the named project URL (Rule 0) and rebuilding Unlimited + duration (both reset by the reload; the 7 chips and previz survived it).
- **Fired** at 12:35:00Z / 19:35 ICT. Verified by **"Generation started" toast** AND asset count moving 702 → 703 (read only as a cross-check, after the previz was already attached, per the playbook's own caveat about uploaded-reference miscounts — not applicable here since the previz was an existing library asset, not a fresh upload).
- **Credit balance verified on CTO request immediately after the fire** (SC4 was mid-render on the free lane at the same time): Account menu → **"Credits: 305 left"** — matches the CTO's stated baseline exactly. Unlimited held; this fire spent 0.
- Zero paid actions taken. Ignored all `SEEDANCE 2.5 CREDIT` / SC1/SC2/SC3/SC4 cards throughout.

## Render

- Polled per the CTO's revised cadence (10 min, fresh tab each time, closed and released between polls). Timeline: still Processing at ~10 min and ~25 min; **finished by ~35 min** (found rendered — "New" badge + play icon — on the ~30-35 min poll).
- Finished card: no NSFW / copyright-rejection / sensitive-content banner. Confirmed **my card** via its Info panel: prompt text opens `20s · 720p · 16:9. The camera is LOCKED and never moves...` (matches the pasted block verbatim), Model **Seedance 2.5**, Quality **High**, Bitrate **720p**, Size **1280x720**, **Created September 7, 2026 at 7:35 PM** — exact fire time.
- Downloaded: `hf_20260907_123500_c843b34f-b68c-4f5e-a292-0fb74058b5f3.mp4` (19,706,948 bytes) to `~/Downloads/`. Filename's embedded timestamp `123500` = 12:35:00 UTC = 19:35:00 ICT, confirming the card.
- md5 checked against every other mp4 already in `~/Downloads` (Python hashlib, chunked read — bash `[` test broke on exotic filenames): `197a4be77fac0bdf5a1dce9eccda9557`, **no duplicate found** among 20 other files.
- `ffprobe`: **1280x720, video + aac audio, duration 20.04s** — matches spec (20s / 720p / Seedance 2.5).
- Filed to Drive: `scripts/gdrive-bridge/upload_fix1.py` → **All Scene/Fix-1/S2N-B-Fix1.MP4** (18.8 MB), https://drive.google.com/file/d/12DZRvFZDUr1qutSeL1KvB5RSt2jA-KjM/view — `logs.txt` line appended by the script. Filed exactly as the brief named it, whatever the verdict below.

## Frame checks

Frames extracted at 0.5s / 4s / 8s / 12s / 16s / 19.5s, saved to
`docs/reports/frames-s2n-b-t2/` (`f_0.5.png` … `f_19.5.png`). On CTO
request, a second pass extracted every second from 5s to 12s
(`f_5s.png` … `f_12s.png`) to pin down the cut boundaries exactly, plus a
measurement overlay (`measurement_overlay.png`) and two labelled grid
crops (`f_7s_mark_grid.png`, `f_7s_plaque_grid.png`) used for the pixel
measurements below.

### Shot count and cut points (CTO request)

**Three distinct shots, two cuts**, confirmed frame-by-frame across
5s-12s:

| Range | Shot | What it shows |
|---|---|---|
| 0s – 7s | **Shot A** (locked wide, the sheet's intended camera) | The five at the wall/plaque/mark; backs at 0.5s/4s/5s, mid-turn at 6s, turned to face camera by 7s. |
| **8s – 10s** | **Shot B — the defect** | A completely different location: a chrome-column gallery, camera tracking/dollying in on the registrar walking straight at the lens, alone. Confirmed present at f_8s, f_9s, f_10s — the camera keeps pushing closer across all three (8s bust-length far away → 10s near-bust close), i.e. a moving camera, not just a single reframe. |
| 11s onward | **Shot A resumes** | Back to the exact locked wide frame: the five, turned, mark visible, plaque visible. At 11s a soft, out-of-focus warm-tan shape fills the bottom-right corner — a shoulder passing extremely close to this camera (`f_11s_corner_zoom.png`), consistent with the sheet's own "he walks past the camera" beat finally happening in the *correct* shot. Confirmed continuous through 12s/16s/19.5s (already-extracted frames), including the group drifting back to backs-to-camera by 19.5s. |

**Cut 1: between 7s and 8s** (Shot A → Shot B). **Cut 2: between 10s and
11s** (Shot B → Shot A). No further reframes detected in the already-
sampled 12s/16s/19.5s frames — those stay in Shot A throughout.

So the "registrar leaves" beat is told **twice**: once correctly (the
foreground blur passing this locked camera at ~11s) and once via an
extra, prompt-violating inserted shot (8s-10s) that shows the same event
from a camera that moves and relocates — exactly what the CRITICAL
NEGATIVES ban ("no camera movement of any kind... no reframing, no change
of framing at any cut"). This is the clip's one real defect; see the
FLAGGED item below for the full negative text.

### Mark width vs. plaque width (CTO request) — measured, not eyeballed

Pixel bounding boxes drawn against the still-frame background (not the
zoomed screenshot, to avoid a mis-scaled read) using `f_7s.png`, where
both the full plaque (its two corner-mounting screws) and the full mark
are visible unobstructed in the same locked-camera frame:

- **Mark bounding box**: x 583→693 (width **110px**), y 57→163 (height
  **106px**).
- **Plaque bounding box**: x 538→735 (width **197px**, edge-to-edge at
  the mounting screws), y 308→397 (height **89px**).
- **Mark width ÷ plaque width = 110 / 197 ≈ 0.56** — the mark is about
  **56% of the plaque's width, i.e. narrower than the plaque**. This
  passes the sheet's "NO WIDER THAN THE BRASS PLAQUE BENEATH IT" gate
  cleanly (my earlier eyeballed 1.1-1.3x guess in the first draft of this
  report was wrong — corrected here by the actual pixel measurement).
- **Mark height ÷ plaque height = 106 / 89 ≈ 1.19** — the mark is about
  **19% taller than the plaque**, which is on the wrong side of "NO
  TALLER THAN THAT PLAQUE." Borderline, not a "5x monster," but a real
  measured miss on the height half of that gate line. Not previously
  called out — corrected here.

`measurement_overlay.png` in the frames folder shows both boxes drawn on
the actual frame for a visual check of these numbers.

**Named characters present** (checked 0.5s and every subsequent frame): the
young woman in blue (@project_absence_char_woman, cobalt coat + gold V pin,
right of centre) ✓, the art student (@project_absence_char_student_c,
yellow-green hair, sketchbook) ✓, the woman in tawny fur
(@project_absence_char_visitor_b) ✓, the man in maroon
(@project_absence_char_visitor_a) ✓, the woman in magenta
(@project_absence_char_critic_b) ✓, the registrar (@char_registrar, cream
tunic, present at 0.5s only — see below) ✓. Carrington and the bodyguard:
**never seen in any frame**, including the anomalous 8s shot (see below),
which shows the registrar alone.

**Sheet's REVIEW ORDER:**

1. CARRINGTON AND THE BODYGUARD ARE NEVER SEEN — **PASS.** No part of either
   appears in any of the 6 frames, including the 8s outlier.
2. THE TURN AT 6s — **PASS (partial verification).** Backs-to-camera at 0.5s
   and 4s, all five turned and facing the lens by 12s and holding through
   16s. Six stills can't confirm the "ragged, one after another, blue-last"
   cadence directly, but nothing contradicts it and the group is not
   frozen mid-turn or obviously synchronized in any sampled frame.
3. THE REGISTRAR WALKS PAST THE CAMERA and is gone by 11s — **PASS on the
   narrative beat, but see the FLAGGED item below** — the shot used to
   deliver it is the actual defect.
4. THE FIVE NEVER SPEAK — not verifiable from stills (audio/lip-sync check
   needs playback, out of scope for frame-grab review); no mouth-open/
   speaking pose visible in any sampled frame.
5. THREE HARD CUTS, SAME FRAME — **FLAGGED.** See below.
6. THE BREAK IS VISIBLE throughout and appears exactly once — **PASS on
   width, borderline MISS on height.** One solid-black crack-shaped mark,
   same position and shape each time, off every body, present in every
   wall-facing frame (0.5s, 4s, 12s, 16s, 19.5s). Pixel-measured (see
   "Mark width vs. plaque width" below): width is **0.56x** the plaque's
   width (narrower — passes), height is **1.19x** the plaque's height
   (taller — misses, though mildly, nowhere near the "5x monster" flag
   threshold noted in the playbook).
7. SIX PEOPLE ON SCREEN, no extras — **PASS.** Five backs/faces at the wall
   plus the registrar (present only briefly, at 0.5s) = six max at any one
   time; the 8s outlier shot shows only the registrar, alone, no extras.

### FLAGGED — a hard cut at ~8s breaks to a different camera and location

`f_8.png` is not the locked wall/plaque wide shot at all — it is a medium
shot down a completely different colonnaded gallery (chrome trumpet columns,
orange cove light, art on the side walls), tracking the registrar walking
directly toward the lens, alone. This is not a time-jump inside the same
static frame (which is what the sheet's beat text and the CRITICAL
NEGATIVES both require: "the camera never moves and the framing never
changes... three hard jump cuts inside the same unchanging frame") — it is
a full reframe/relocation, which the CRITICAL NEGATIVES explicitly ban:
*"no camera movement of any kind, no pan, no tilt, no zoom, no dolly, no
handheld, no reframing, no change of framing at any cut."*

By f_12.png the shot is back to the correct locked wide frame with the five
turned to face camera and the registrar gone — so the narrative beat ("he
walks past the camera and is gone") landed, but through a shot the prompt's
own hard negatives forbid. This is the one real defect in this take.

**Minor, not separately flagged:** the registrar is already out of frame by
4s (before the scripted 6s turn / 8s hard cut), earlier than the beat
script implies for the "NOBODY HAS MOVED" stretch — noted for completeness,
not treated as a review-order violation since nothing in the checklist
requires him to remain visible for a specific span.

## Verdict

**RENDERED, FILED, FLAGGED.** No NSFW/copyright rejection. Cast, turn and
six-person-cap all check out; the mark passes on width, misses mildly on
height (1.19x the plaque). The clip contains **three shots, not one**:
Shot A (locked wide, 0-7s) → **Shot B, a moving/relocated camera** on the
registrar alone in a different gallery (8-10s, the real defect) → Shot A
resumed (11s onward), where the registrar's exit is *also* shown correctly
as a foreground pass-by within the locked frame. Shot B is a direct
violation of "camera never moves / no reframing at any cut." Filed under
the brief's exact name regardless, per "file the take whatever the
verdict." A human/CTO pass should decide whether this is acceptable as an
editor-cut option (Shot B is brief, 8-10s, bracketed by two otherwise-
correct locked-frame passages that already tell the same beat correctly)
or needs a take 3.

## Notes

- The library-tile mis-click (wrong previz attached, caught via byte-check
  before firing) cost one detach/re-attach cycle but no wasted fire.
- The stray navigation to the generic homepage mid-pipelining (~19:14 ICT)
  cost one full re-verify of the six fields + Unlimited + chip count after
  navigating back to the named project URL — no browser-tool error, no
  unconfirmed state, no spend; caught via the tab's own title/URL before any
  further action.
- Credit balance ("305 left") verified via Account menu → Manage Account
  panel at the CTO's explicit request, immediately after the fire — not
  part of the standard playbook flow, done as a one-off check this session.

## Sheet notes appended

One dated take line appended to
`docs/prompts/absence/s2n-b-fix1-five-million-reverse.txt` (bottom,
append-only, per instructions).

# Absence — Night Chain 2 (five scenes) — winbox browser operator

Task: task-c72d5ba5. Chrome device `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome).
Tab claimed: 1638444814, registered via `scripts/browser/tab_registry.py`.
Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7).
Queue order (per AB-LEDGER 2026-09-10 02:20): S18 → S2X (owned by task-958e2561, do not touch)
→ **S3a t2 → S2AW → S2AP → S2R-F V1 split → S19** (this task's five scenes, in this order).

Baseline at start: 2026-09-09T19:27:33Z (2026-09-10 02:27 ICT). Asset count 760 (Video filter
grid). One card "Processing" already in the grid at start — not ours, presumed task-958e2561's
S18/S2X chain; never touched, never cancelled.

---

## Scene 1 — S3a "THE FIRST CUSTOMER" take 2

**Route:** step 5 (text) for slot-state checks (javascript_tool leaf-node scan cheaper than
screenshot), step 7 (screenshot/zoom) for money-critical Generate-button and settings-row
verification — those must be pixel-read, never DOM-scraped, per the skill's hard rule.

**Slot wait:** on arrival (2026-09-09T19:27:33Z / 02:27 ICT) a card was already Processing —
presumed the other operator's (task-958e2561) S18/S2X chain, never touched. Polled 10min → 5min
per the task's cadence; watched it clear (Processing → Generating, a different job → cleared) by
19:54Z. Confirmed clean in a brand-new tab (not just a reload) before touching the composer, per
the skill's stale-tab-lies warning.

**Video-ref attach — a real complication, logged in full for the next operator:**
The "+" → Uploads → Videos panel already holds **dozens of near-identical grey-block Blender
previz uploads** from other scenes/operators across this multi-night production — same hallway,
same columns, same red door, differing only in which coloured proxy blocks stand where. Sort
controls ("Last created"/"Last used") did **not** reliably reorder the visible tiles across
repeated attempts (screenshots before/after selecting a different sort option showed the same
tile order), so position-based "take the first tile" is not trustworthy on this account's
library. Two wrong tiles were attached and removed in the process (`8766aaaf-…` — confirmed via
`mvhd` box parse to be a 20s clip; `844d90ce-…` — exactly 10s by duration but visually confirmed
via `ffmpeg`-extracted frames to be a *different* simple hallway proxy, not S3A's oldman+Dupe+cart
scene) before landing on the right one. **What actually worked:** capture the full account video
UUID list via `read_page` immediately before `file_upload`, upload fresh, re-capture, and diff —
the new UUID is unambiguous. Confirmed **byte-for-byte identical** (md5 `150d392e0effad5134069e9b83d33175`,
227,386 B) between the local `docs/S3A-Render.MP4` and the CDN asset
`91258d26-5853-4778-968e-44e6a7c86fde.mp4` fetched directly via `curl` (the CDN is a public,
unauthenticated CloudFront URL — `d2ol7oe51mr4n9.cloudfront.net/user_39AwuuLxRPQ20d5TQbk4NU0bWsp/<uuid>.mp4`
— reachable straight from Bash, no browser needed, which is by far the cheapest way to verify any
uploaded reference against its source file: `curl -o x.mp4 <url> && md5sum x.mp4 <local-file>`).
**Correction to skill note that byte-match always holds**: at least one older library asset
(`8766aaaf`) served at a different byte size than any 10s/20s file would suggest transcoding
happens for *some* uploads — but this fresh upload came back byte-identical, so check per-asset,
don't assume either way.

**SKILL-OVERRIDE:** `higgsfield-unlimited-gen` :: "byte-match content-length via HEAD request" ::
also fetched the FULL body and compared md5 against the local file, and cross-checked via
`ffprobe`/`ffmpeg` frame extraction (not just HEAD content-length) :: a HEAD-only content-length
match on an unrelated but same-duration asset (844d90ce) produced a false positive; only a full
byte/frame comparison caught it.

**Staging, S3a take 2:**
- Video 1: `91258d26-5853-4778-968e-44e6a7c86fde` (confirmed exact local match) — 1 chip.
- Prompt pasted via synthetic `ClipboardEvent` (never `type()`) from the sheet's exact
  PASTE-block text (4680 chars), followed by real `End` → `space` → `Backspace` keys to force
  Lexical state sync. `editorLen` 4762 (mention chips render longer than raw text — expected).
- Chips: 4/4 bound, confirmed lime `rgb(209,254,23)`, 0 unbound/red:
  `@project_absence_char_oldman`, `@project_absence_char_cleaner_c`, `@loc_hall_big_e`,
  `@prop_cart_b`. Total chips = 4 elements + 1 video = 5, matching the sheet's stated count.
- Settings, zoom-verified immediately before Generate: Seedance 2.5 · 16:9 · 720p · 10s
  (slider `aria-valuenow` moved 5→10 via 5× `ArrowRight`, never typed) · batch 1/4 · quality
  High · Sound On · Unlimited toggle `data-state="on"`.
- **Tab froze mid-stage** (CDP `Page.captureScreenshot` timeout, three consecutive calls) right
  after the Unlimited toggle click. Per hard rule, did not re-click near the composer; confirmed
  via `javascript_tool` (not a click) that the toggle had in fact registered (`aria-checked:true`)
  before doing anything else. Recovery: `navigate` (reload) the same tab, which — confirmed live
  — **preserved the video reference, prompt text, and duration**, and only reset Unlimited to
  off, exactly as the skill documents; re-toggled Unlimited and re-verified everything by zoom
  before the click.
- Checked Usage → nothing anomalous attributable to the freeze (no way to get a precise delta
  from the Usage-statistics tab's 7-day aggregate view, but no spike, and no priced control was
  ever clicked before or during the freeze).
- Generate button zoom-verified immediately before click: `UNLIMITED` / struck `70` / `0`.
- **Fired 2026-09-09T20:50:30Z (2026-09-10 03:50:30 ICT).** Toast "Generation started"; new
  Processing card; asset count 761→762 (+1). Rendering, awaiting landing — poll cadence 20min
  then 5min per the skill.

**Landed ~2026-09-10 04:19 ICT (~29 min render).** Card Info panel: "Created September 10, 2026
at 3:50 AM" == fire time; prompt starts "10s · 720p · 16:9 · TWO SHOTS JOINED BY ONE HARD JUMP
CUT" — confirmed my card. Asset id (preview URL) `fca001ce-4fd1-4998-b931-cae45dd2e577`.

**Download:** `C:\Users\UsEr\Downloads\hf_20260909_205018_81351abb-9f5d-46d7-8715-1cd8f8d0ec3a.mp4`
— 10,024,571 B, md5 `bb78f5ef9a008be235593a2be27cc082`. ffprobe: h264/aac, 1280x720, 10.04s — on
spec.

**Sweep** (5fps greyscale 160px-wide consecutive-frame diff, median 1.294): **ONE isolated cut at
5.00s, 31.86× median**, nothing else above 6× in the rest of the clip. The 5.2–9.2s window shows a
gradually elevated diff (2–7×) consistent with the walking figure crossing frame, not a camera
move — confirmed by cropping a static background region (top-right, paintings/columns, never
crossed by the walking man) across t6/t8/t9.7 and diffing just that crop: 1.36 and 5.34, i.e.
noise-level, not a pan/zoom. **This is the fix for take 1's camera-lock defect** (shot 2 was
confirmed NOT locked on take 1; this take's shot 2 background stays pixel-static).

**Frame review** (full res, 1, 3, 4.5, 6, 8, 9.7s — `docs/reports/frames-s3a-t2/`, plus
`contact-row-640.png`):
- t1: DUPE alone, mopping mid-hall beside his cart; red double doors closed at far end. Locked
  wide axial frame.
- t3: one red door open; OLDMAN entering, dark-green coat, cane, alone; DUPE still mopping. Same
  locked frame as t1.
- t4.5: OLDMAN further in, near a bronze/vitrine on the left; DUPE unchanged. Same frame.
- t6/t8/t9.7 (shot 2, after the 5s cut): OLDMAN walks left→right through a DIFFERENT fixed
  medium frame (vitrine + glass case with a small bronze figure right of centre); background
  (pedestal lamp, paintings, glass case) is pixel-static across all three frames — camera locked,
  confirmed. Dupe visible blurred/background at t6 only, out of frame by t8/t9.7 (matches "deep
  behind him and out of focus... watching").
- Two people in every sampled frame, no third figure, no registrar/guard/visitor.
- Cart: red tray/bucket structure and a leaning object beside it visible at t1, but **not clearly
  identifiable as a framed painting face-out at this resolution/angle** — flagging for CTO
  full-res review rather than asserting either way.
- No crack in frame, no plaque close-up, no looking at lens, no smile, no touching the wall in
  any sampled frame.
- **Not independently verified:** dialogue/audio (no transcription tool on winbox, same
  limitation as take 1 — `faster_whisper` not installed). No dialogue visible on any sampled
  frame (no subtitles/mouth movement suggesting speech in the two mid-conversation-adjacent
  frames), but this is a visual-only read, not an audio verification.

**Verdict: NOT self-certified — visual evidence above strongly suggests the take-1 camera-lock
defect is fixed (locked shot 2, single correctly-placed cut, correct cast/blocking), but the CTO
reviews the actual footage** (`video-see.sh` / full-res frames in this dir) before it's called a
pass. Filed at `C:\Users\UsEr\Downloads\hf_20260909_205018_81351abb-9f5d-46d7-8715-1cd8f8d0ec3a.mp4`
for the CTO to pull and file as `S3a-FirstCustomer-Fix1-take2.MP4` in All Scene/Fix-2/ (no Drive
access from winbox, per task instruction — file left on disk).

## Scene 2 — S2AW "THE INTERPRETATIONS, TABLEAU"

**Route:** step 5/7 as before. Applied the S3a lesson directly: `read_page` baseline UUID list →
`file_upload` fresh → diff → `curl`+`md5sum` byte-match against local `docs/S2AW-Render.MP4`
BEFORE attaching, no exploratory clicking in the library this time. New UUID
`8286b72d-fccd-487b-813c-f315c7d9a0bc`, md5 `975b2172c99b0847c0ae7e67cd272111` on both sides —
confirmed in two tool calls instead of the ~40 that S3a's reference took.

**Tab hygiene:** opened a fresh tab for this scene (the S3a tab had frozen `Page.captureScreenshot`
repeatedly after touching several video assets) — the fresh tab worked cleanly throughout.

**Chip-count correction (important for the remaining scenes):** the sheet's PASTE block mentions
each of the 8 element tags **twice** (once in the POSITION MAP list, once in the REFERENCES
block) — this is intentional sheet authoring, not a duplicate-binding bug. A raw
`document.querySelectorAll('span.text-font-brand')` count read **14**, which looks like a
failure against "8 chips" until you count **unique** tags: 14 mentions → 8 unique tags, all lime
(`rgb(209,254,23)`), 0 `.text-icon-error`. Verify by `uniqueCount`, matching the skill's own
"`8/8 unique mentions bound`" convention — not raw chip-span count. Will apply this to S2AP,
S2R-F split, and S19 too.

**Staging:**
- Video 1: `8286b72d-fccd-487b-813c-f315c7d9a0bc` (byte-confirmed) — 1 chip.
- Prompt pasted via synthetic paste (9328 chars), End→space→Backspace sync.
- Chips: 8/8 unique bound, 0 error: `@project_absence_char_woman`, `@…_student_c`,
  `@…_visitor_b`, `@…_visitor_a`, `@…_critic_b`, `@…_cleaner_c`, `@project_absence_loc_wall_pov_e`,
  `@project_absence_prop_cart_a_painted`. Total 8 elements + 1 video = 9 chips, matching sheet.
- Settings zoom-verified: Seedance 2.5 · 16:9 · 720p · 20s (already defaulted correctly from the
  prior generation's remembered setting — verified, not assumed) · batch 1/4 · High · Sound On ·
  Unlimited `data-state="on"`. Generate button zoom: `UNLIMITED` / struck `440` / `0`.
- **Fired 2026-09-09T21:36:53Z (2026-09-10 04:36:53 ICT).** Toast "Generation started"; asset
  count 762→763 (+1). Rendering.

**Landed ~2026-09-10 05:11 ICT (~35 min render).** Card Info: "Created September 10, 2026 at
4:36 AM" == fire time; prompt starts "20s · 720p · 16:9 · ONE LOCKED SHOT" — confirmed my card.
Asset id `8a02ef6a-7043-4547-9b08-1f919f950651`.

**Download:** `C:\Users\UsEr\Downloads\hf_20260909_213642_3c0f258f-3a8c-4661-bd4e-653267167dcf.mp4`
— 19,966,219 B, md5 `f54539bc4d7698df9cbb49da653fafb1`. ffprobe: h264/aac, 1280x720, 20.05s.

**Sweep** (5fps greyscale diff, median 0.786, max 2.11 = 2.69× median): **no spike anywhere** —
confirms ONE LOCKED SHOT, zero cuts, camera never moves for the full 20s.

**Frame review** (1, 4, 8, 12, 16, 19.5s — `docs/reports/frames-s2aw/`): identical framing across
every sampled frame (columns, red door, crack all pixel-static). Left→right: cobalt (blue coat,
gold V pin), student (yellow-green curls, denim, sketchbook), fur (brown fur coat, centred on the
crack/mark), maroon (dark red-maroon suit), critic (magenta fur coat) — matches the sheet's
stated order exactly. **Dupe visible far back, dead centre, beside his cart**, small and
symmetrical, behind the fur woman — matches "SIX PEOPLE AND NOT ONE MORE." The mark/crack sits
over the red door, roughly door-width, not obviously enlarged. No huddle, no seventh person, no
mop/cart in the line itself. At t8 the cobalt woman's mouth looks faintly open — inconclusive
from a still frame given the script has her speaking only at 15s, not 8s; flagging rather than
asserting a defect.

**Not independently verified:** the five-line dialogue order/timing and unison head-turn beats
(no transcription tool on winbox). Visually the poses read as attentive/facing-mark in all
sampled frames, consistent with the "hold" beats, but the mid-speech turn choreography can't be
confirmed from six still frames.

**Verdict: NOT self-certified.** Visual + sweep evidence is strong (locked camera, correct
cast/order/count, correct mark position) — CTO reviews the actual footage before calling it a
pass. Filed at
`C:\Users\UsEr\Downloads\hf_20260909_213642_3c0f258f-3a8c-4661-bd4e-653267167dcf.mp4` for the CTO
to pull and file as `S2AW-InterpretationsTableau-Fix1.MP4` in All Scene/Fix-2/.

## Scene 3 — S2AP "THE INTERPRETATIONS, PORTRAITS"

**Pre-staged during S2AW's render** (CEO pattern: warm up the next job during the wait). Video 1:
`42e77af7-c90c-4e16-b7a3-3a380d0d59a6`, byte-confirmed against local `docs/S2AP-Render.MP4`
(md5 `846ad837f7dbd190dd4e39e79b55d19c` both sides) via the same upload→diff→curl method. Removed
S2AW's video/text from the composer first (real Ctrl+A+Delete, then removed the old video chip
via its own × before attaching the new one — attaching a second video without detaching the
first just adds a second reference, confirmed once and reverted).

**A browser-selection prompt appeared mid-session** ("Multiple Chrome browsers connected, none
selected") while staging this scene — re-selected the task's assigned device
(`815ddf16-36ea-4e0d-827a-f31e9ff85351`, winbox-chrome) directly rather than guessing from the
ambiguous 2-browser list it offered (which did not even include winbox-chrome); resolved in one
call, tab and composer state both survived intact.

**Chips:** 6/6 unique bound, 0 error: `@project_absence_char_visitor_b`, `@…_visitor_a`,
`@…_critic_b`, `@…_student_c`, `@…_woman`, `@project_absence_loc_wall_pov_e`. 6 elements + 1
video = 7 chips, matching sheet.

**Settings:** duration moved 20→15 via 5× `ArrowLeft` on the slider (verified `aria-valuenow`).
Seedance 2.5 · 16:9 · 720p · 15s · High · Sound On confirmed by zoom immediately before Generate.
Unlimited had reset off (reload during the wait) — one clean ref-based click (`find()` →
`Unlimited mode` switch), re-verified `data-state="on"` and the button `UNLIMITED / struck 105 /
0` by zoom.

**Tab froze on `Page.captureScreenshot` three more times during this scene** (consistent with the
skill's "tab misbehaves after touching several video assets" warning — this tab has now
attach/detached 3 different videos across 2 fires). Each time, `wait` + retry recovered it
without needing a reload; no click was ever retried blindly near the composer.

**Fired 2026-09-09T22:20:06Z (2026-09-10 05:20:06 ICT).** Toast "Generation started"; asset count
763→764 (+1). Rendering.

**Landed ~2026-09-10 05:58 ICT (~38 min render).** Card Info: "Created September 10, 2026 at
5:19 AM" (within a minute of fire — display rounding); prompt starts "15s · 720p · 16:9 · FIVE
SHOTS JOINED BY FOUR HARD CUTS at 3s, 6s, 9s and 12s" — confirmed my card. Asset id
`256888f6-a545-4c22-bc2b-f5780c30a1d7`.

**Download:** `C:\Users\UsEr\Downloads\hf_20260909_221959_c6ca6a1a-7e26-4c20-81ef-b5b82a2e6678.mp4`
— md5 `87c8ac6e6a9e795ccd36e6d6f7a05756`. ffprobe: h264/aac, 1280x720, 15.04s.

**Sweep** (5fps greyscale diff, median 0.577): spikes at 3.00s (10.35×), ~5.6s (9.83×, one 5fps
sample off the intended 6s — frame-quantization, not a defect), 9.00s (14.17×), 12.00s (14.61×) —
confirms the four intended hard cuts, nothing else.

**Frame review** (1.5/4.5/7.5/10.5/13.5s — `docs/reports/frames-s2ap/`): order matches the sheet
exactly — fur → maroon → magenta/critic → student → cobalt, one person per portrait, dead centre,
waist-up, identical framing/columns/lighting across all five. No second face, no mop/cart, no
close-up (face reads well under a quarter of frame height in every sampled portrait) — this is
exactly the fix the sheet exists for (S2R-F's five-close-up design was moderation-rejected twice).

**Not independently verified:** the five spoken lines' exact wording/timing (no transcription
tool on winbox); mouths are visibly mid-speech in the sampled frames, consistent with dialogue
but not confirming content.

**Verdict: NOT self-certified.** Strong visual + sweep match — CTO reviews before pass/fail.
Filed at `C:\Users\UsEr\Downloads\hf_20260909_221959_c6ca6a1a-7e26-4c20-81ef-b5b82a2e6678.mp4` for
the CTO to pull and file as `S2AP-InterpretationsPortraits-Fix1.MP4` in All Scene/Fix-2/.

## Scene 4 — S2R-F SPLIT "THE BATTLE, FIVE PANELS"

_pending_

## Scene 5 — S19 "THE PAINTING GOES BACK"

_pending_

---

## Files changed
- `docs/reports/absence-night-chain-2-winbox.md` (this file)
- `docs/reports/frames-<scene>-t*/` (per-scene frame dirs, added as each scene lands)

## Tests run
N/A — browser_operator task, no code changes to the repo besides this report and frame dirs.

## Blockers
_none yet_

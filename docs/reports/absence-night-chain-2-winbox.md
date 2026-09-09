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

## Scene 3 — S2AP "THE INTERPRETATIONS, PORTRAITS"

_pending_

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

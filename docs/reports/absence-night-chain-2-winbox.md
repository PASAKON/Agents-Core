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

## Scene 2 — S2AW "THE INTERPRETATIONS, TABLEAU"

_pending_

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

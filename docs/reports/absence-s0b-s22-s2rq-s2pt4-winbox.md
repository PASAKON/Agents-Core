# S0b harvest → S22 → S2R-Q → S2PT take 4 — winbox

Tab registry: `task-41684e16`. Chrome device `815ddf16-…` (winbox-chrome).
Project confirmed every fire via the address bar:
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The
Valder Collection No.7").

## Scope note — Phase 0 (S0b) was already done before this task started

The brief says the previous operator (task-fc063e0e) fired S0b (asset
`798fc88b-9823-4909-8194-f8eacfd9d810`) and never harvested it. That is
stale: this branch's own history (inherited from `main` at task start)
already contains commit `af46e16` — **"S0b harvested and reviewed — PASSES
all four checklist items"** — with the full harvest writeup in
`docs/reports/absence-s20-s2pt-t3-s0b-winbox.md` and frames already committed
under `docs/reports/frames-s0b-t1/`. Confirmed on the live page too: the S0b
card in the grid still carries the "Last downloaded" badge from that harvest.
No re-harvest performed — re-doing it would not add information and the
brief's own rule is never to re-fire/redo a completed step. Moving straight
to Phase 1.

## Phase 1 — S22 "THE CRATE" — FIRED

- Sheet: `docs/prompts/absence/s22-addon-the-crate.txt`, lint clean
  (`python scripts/prompt-lint.py … --shot S22`, exit 0, no findings).
- **Extraction defect caught before firing, twice:**
  1. First pass used `atob()` directly on the base64 to build the paste
     string. `atob` returns a byte-string, not decoded UTF-8, so the
     sheet's multi-byte characters (em dashes, curly apostrophe) corrupted
     the text — caught immediately because the resulting string measured
     3945 chars against the source file's 3927 (this is the *byte* count
     leaking through, not real content). Fixed: decode via
     `Uint8Array.from(atob(b64), c=>c.charCodeAt(0))` then
     `new TextDecoder('utf-8').decode(bytes)` — landed length matched the
     source exactly (3927) on every paste after this fix.
  2. Second check (post-paste, before firing): landed `innerText` came back
     3973 vs source 3927 — a 46-char gap that exactly equals the block's
     line count minus one (47 lines). This is the documented Lexical
     paragraph-per-line defect (`docs/reports/absence-plate-tv-wall-winbox.md`):
     every hard-wrapped source line became its own paragraph, and each
     paragraph boundary costs one extra character in `innerText`. The S22
     block has zero blank-line paragraph breaks, so per the task's "equal,
     or clear and redo" rule I flattened every single `\n` to a space
     (byte count unchanged, since both are 1 char) and re-pasted. Landed
     `innerText` then matched source exactly: **3927 = 3927**. Folded this
     fix into a permanent script: `scripts/browser/extract-paste-block.py`
     (flattens automatically unless the block has real blank-line breaks).
- **Two viewport lock-ups hit mid-setup, both caught before any click, per
  the brief's explicit anticipation of this failure mode** ("~196px →
  fresh tab, never resize"):
  - First: caught via `window.innerWidth`/`innerHeight` reading 141×85
    right after a raw-coordinate composer click missed. Opened a fresh tab,
    never resized. Nothing had been pasted or fired yet.
  - Second: caught again (141×68) via `getBoundingClientRect()` on the
    Generate button returning `top:-63` and a null `elementFromPoint` —
    the button coordinates it had just reported were already stale.
    Fresh tab again, re-staged from the sheet. Also had two tab-GROUP
    reaps mid-recovery (`tabs_context_mcp` reporting "no tab group
    exists") — consistent with the brief's "reaped twice this evening"
    warning; each time just re-created the group and re-navigated, no
    generation was ever in flight so nothing was at risk.
- **Focus trap** (documented in `higgsfield-unlimited-gen` §"Video-ref
  attach on the PROJECT composer", point 3): a raw-coordinate click on the
  composer repeatedly landed on `BODY` instead of the real
  `contenteditable`. Fix used every time: click, then verify
  `document.activeElement.getAttribute('contenteditable') === 'true'`
  before typing/pasting anything; retried the click at a freshly
  screenshotted coordinate when it missed.
- **Async paste**: reading `innerText` in the same call that dispatches the
  synthetic `ClipboardEvent` shows `0` — Lexical processes the paste after
  a tick. Waited ~300ms before reading back; landed correctly every time
  this was respected. (One retry cycle lost content because the
  End→space→Backspace state-sync taps were sent before the paste had
  settled — not a corruption, just a race; re-pasting fixed it cleanly.)
- Chips: **0/0**, as required — sheet carries no `@Element` mentions.
  Verified via the documented `span.text-font-brand` leaf-span selector,
  0 matches, and zero `<video>` reference elements in the composer
  (confirmed the one stray `<video>` on the page was a grid card's
  hover-preview thumbnail at `top:293`, well outside the composer, not a
  reference-tray attachment).
- Settings at fire: Seedance 2.5 · 16:9 · 720p · 8s · High · Sound On ·
  **Unlimited ON**.
- **Unlimited toggle**: off by default on every fresh tab (reload/new-tab
  resets it, as documented). One clean ref-based click each time, verified
  `aria-checked="true"` immediately after. **The toggle button itself was
  clipped off-screen by the settings row's horizontal scroll** until the
  `>` "Scroll right" chevron was clicked enough times — confirmed via
  `document.elementFromPoint` at the toggle's own centre returning a grid
  card behind it (not the toggle) until it actually scrolled into view;
  `aria-checked` alone was not a sufficient click-landed check without
  this — same class of check as the documented decoy-button trap, just on
  the covering axis instead of the decoy-element axis.
- **Zero-digit check, pixel zoom (not DOM scrape)**: the DOM text-scrape of
  every `button` matching `/generate|unlimited/i` returned a **decoy**
  reading `"GENERATE8045"` with `width:0, height:0, visibility:hidden` —
  exactly the documented decoy pattern. The real, visible button
  (`120×80`, `visibility:visible`) read, confirmed both by
  `document.elementFromPoint` self-match and by a pixel zoom:
  **`UNLIMITED · ~~56~~ · 0`**. Fired on the real button only.
- **Fired** at `2026-09-10T15:25:35Z` (`22:25:35 ICT`). New asset id
  `6e3d88c5-c403-4e77-91d2-67961a34b059` (grid's `data-asset-id`, newest
  entry; asset count went 780→781). "Generation started" toast confirmed.
- **Usage History re-checked immediately after** in a separate tab (never
  navigated the protected composer tab): Total cost **$75.5** and credits
  **1,887.5 → unchanged**; "Total generations" **199 → 200**. Confirms
  exactly one free Unlimited generation registered, $0 charged.
- Completed and harvested at `2026-09-10T16:00 UTC` (~35 min render time).

### S22 harvest

- **Download button silently failed again** (same defect as S0b's harvest,
  documented in `absence-s20-s2pt-t3-s0b-winbox.md`): click registered
  ("Last downloaded" style state), no file landed in `C:\Users\UsEr\Downloads`.
  Workaround used again: read the card's `<video>` element's `currentSrc`
  directly via `javascript_tool` (no network-request capture needed this
  time — the DOM already held the resolved CloudFront URL), then
  `ffmpeg -c copy` to remux it to disk without re-encoding.
- **Path**: `C:\Users\UsEr\Downloads\hf_20260910_152453_6e3d88c5-c403-4e77-91d2-67961a34b059.mp4`
- **Bytes**: 9,546,716 · **MD5**: `6ae906f8a7f716db14e556010efb8f65`
- **Asset id**: `6e3d88c5-c403-4e77-91d2-67961a34b059`
- **Fire**: `2026-09-10T15:25:35Z` (22:25:35 ICT) · **Completed**: ~16:00 UTC
  (~35 min — inside the "Europe awake" range the skill predicts, faster
  than the 40-90 min upper estimate)
- **ffprobe**: 1280×720 @ 24fps, duration 7.96s, audio stream present.
- Frames (full 1280×720) at 0.5, 2, 3.5, 5, 6.5, 7.9s →
  `docs/reports/frames-s22-t1/`.

### REVIEW — S22 (per this brief's checklist)

**(1) ONE crate, wall-shaped, dead centre, symmetrical, locked camera —
PASS.** Identical framing across all six sampled frames — zero camera
movement, crate perfectly centred and symmetrical, matches the sheet's
"ONE LOCKED SHOT" spec exactly.

**(2) The doorway behind it is visibly SMALLER than the crate — PASS.**
The plain door at frame-left is unambiguously smaller than the crate in
every dimension — matches "obviously, absurdly too small."

**(3) Nobody in the room, no figure, no shadow or reflection of a person
— PASS.** All six frames show an empty room; no figure, shadow, or
reflection anywhere.

**(4) The gold V reads as a mark, not writing — PASS.** One clean gold
"V" centred on the crate face, no other text, numbers, or marks anywhere
in frame.

**(5) Nothing moves but dust — not verifiable from still frames.** No
camera movement or scene change is visible across the six samples
(consistent with a locked shot), but dust motion itself can't be judged
from stills; would need to watch the clip.

**Overall S22 verdict (operator read): 4/4 checkable items PASS**, one
item (dust) not checkable from stills. One minor deviation from spec
worth flagging: the sheet calls for "warm shadow, cold white: amber-orange
highlights and mids" but the rendered grade reads closer to neutral/cool
pale-grey than warm amber — a content-quality note for the CTO/CEO to
weigh, not a browser/tooling defect.

## Reusable script

`scripts/browser/extract-paste-block.py` — extracts a sheet's PASTE block
byte-exact and flattens word-wrap newlines to spaces (unless the block has
real blank-line paragraph breaks, or `--keep-newlines` is passed). Used for
S22; will reuse for S2R-Q and S2PT take 4.

## Phase 2 — S2R-Q "THE BIDS, QUICK" — FIRED

Staged into the composer while S22 rendered (safe — editing composer text
does not touch an in-flight render or the Unlimited toggle). Verified at
staging time:
- `innerText` landed 4960 chars, matches source exactly.
- Chips: **3/3 unique, 0 error chips** — `@gentleman_e`,
  `@project_absence_char_valder`, `@loc_hall_big_e`. Madame stays prose,
  as the sheet requires; no fourth chip appeared.
- 0 `<video>` reference elements.

**Re-verified fresh at fire time** (per "re-verify at the moment you
commit" — nothing trusted from staging time): duration changed 8s→10s via
the `role="slider"` popover (`ArrowRight` × 2 from 8, confirmed
`aria-valuenow="10"`); chips re-confirmed 3/3 unique, 0 errors, text
length still 4960, 0 video refs; Unlimited was OFF on this composer
(reset, as always) — one clean ref-based click, confirmed
`aria-checked="true"`, then **pixel zoom** (not DOM scrape) confirmed
`UNLIMITED · ~~70~~ · 0`. Fired.

- **Fired** at `2026-09-10T16:04:13Z` (23:04:13 ICT). New asset id
  `16874354-9360-4bf6-88f8-870a4d145ad2` (asset count 781→782).
  "Generation started" toast confirmed.
- **Usage History re-checked** in a separate tab: cost unchanged ($75.5),
  "Total generations" 200→201. $0 charged.
- Completed at `2026-09-10T16:35 UTC` (~31 min render).

### S2R-Q harvest

- Same silent-download workaround as S22/S0b: `<video>` element's
  `currentSrc` read directly, `ffmpeg -c copy` remux.
- **Path**: `C:\Users\UsEr\Downloads\hf_20260910_160402_16874354-9360-4bf6-88f8-870a4d145ad2.mp4`
- **Bytes**: 10,164,425 · **MD5**: `5cf21209684c68ca8b2eee6e6f98193e`
- **Asset id**: `16874354-9360-4bf6-88f8-870a4d145ad2`
- **ffprobe**: 1280×720 @ 24fps, duration 10.05s, audio present.
- Frames (full 1280×720) at 1, 3, 5, 7, 9s → `docs/reports/frames-s2rq-t1/`.
  **One extra diagnostic pass**: the 3s sample landed almost exactly on
  the 3.2s cut boundary and looked like a stuck shot (still Carrington
  when Madame was expected); pulled additional frames at 1.7/2/3.1/4.9/6.5s
  to confirm the cut timing is correct — Madame is clearly on screen at
  1.7s and 2s, Carrington is back by 3.1s. Recorded here so the next
  reviewer doesn't re-diagnose the same false alarm from a single sample
  landing near a cut point.

### REVIEW — S2R-Q (per this brief's checklist)

**(1) Six shots, five hard cuts, nobody but the one named face inside
each close-up — PASS.** Confirmed shot sequence across all ten sampled
frames: Carrington (0–1.6s) → Madame (1.6–3.2s) → Carrington (3.2–4.8s) →
Madame (4.8–6.4s) → Carrington (6.4–8s) → Valder (8–10s). Exactly one face
per frame throughout, matches the sheet's six-shot/five-cut structure
exactly.

**(2) Five bids audible in order, Valder silent — not verifiable from
stills**, would need audio playback.

**(3) Carrington identical across his three close-ups; Madame identical
across her two, from prose alone — PASS.** Carrington's two gold front
teeth clearly visible and consistent at 3s/3.1s/9s(7s); Madame's blue/
green/silver pompadour and black cat-eye sunglasses consistent and
correctly rendered purely from prose (no Element bound), matching the
sheet's description exactly.

**(4) Valder deadpan and silent in the last shot — PASS.** The 9s frame
shows Valder mouth shut, no smile, no visible speaking — matches "Deadpan,
mouth shut, not a flicker of a smile."

**(5) Locked camera in every shot — consistent with all samples**, no
visible pan/zoom/drift across any of the ten frames pulled.

**(6) No plaque, no crack, no extras — PASS.** No plaque, crack, or
additional figures in any sampled frame; backgrounds are the blurred
gallery hall as specified.

**Overall S2R-Q verdict (operator read): 4/4 checkable items PASS**, two
items (audio bid order, full-clip camera lock) not verifiable from stills.

## Phase 3 — S2PT take 4 "THE TOUR, TOGETHER" — FIRED

Uploaded the re-rendered previz fresh via + → Uploads → Videos (NOT
reusing any older upload in the panel), following the CTO's four-step
checklist:

1. Copied `C:\Users\UsEr\Downloads\S2PT-Render.mp4` into the session
   scratchpad (file_upload refuses a Downloads path directly) — MD5
   verified byte-identical to the source before upload.
2. Uploaded via the Uploads panel's own file input (the "third input on
   the page," per the skill — not the composer's direct input or the
   References picker's input).
3. Waited ~4 minutes for verification (spinner tile → real thumbnail).
4. Attached it ("Added to prompt box" toast, green checkmark) and
   **byte-verified via `fetch(video.currentSrc, {method:'HEAD'})`**:
   `content-length` 4,157,750 — exact match to the local file, confirming
   the newest render was attached, not a stale cloud copy.

Composer setup:
- Cleared old S2R-Q text/chips (`Ctrl+A`+`Delete` after confirming focus
  landed on the real contenteditable, not `BODY` — one miss caught and
  corrected before it did anything, since Ctrl+A on `BODY` only
  page-selects and Delete is a no-op there).
- Pasted the corrected multi-paragraph extraction (11911 chars). Landed
  `innerText` read back as 11974/11984 (before/after the `@Video 1`
  chip) — **63-char excess fully explained and verified non-corrupting**:
  Lexical renders each of the sheet's 21 real paragraph breaks as three
  newlines instead of two; normalizing runs of 2+ newlines down to
  exactly 2 (`t.replace(/\n{2,}/g, '\n\n')`) reproduces the source
  **exactly**, 11911 = 11911, and head/tail text matched byte-for-byte.
  Treated as a benign, deterministic Lexical rendering artifact (same
  class as the chip-label-inflation the S0b/S2PT-t3 reports already
  documented), not a corruption requiring redo.
- Added the `@Video 1` mention via the native `@Video` trigger →
  dropdown → "Video 1" (never typed as plain text in the pasted block,
  per the skill).
- **Chips: 8/8 unique, 0 error chips** — the 7 sheet elements
  (`@project_absence_char_valder`, `@gentleman_e`,
  `@project_absence_char_guard_private_v2`,
  `@project_absence_char_guard_valder_two`,
  `@project_absence_char_cleaner_c`,
  `@project_absence_prop_cart_a_painted`, `@loc_hall_big_e`) plus
  `@Video 1` — matches the brief's "8 = 1 video + 7 elements" exactly.
- Duration: 10s (leftover from S2R-Q) → 20s via the slider popover
  (`ArrowRight` × 10 from 10, confirmed `aria-valuenow="20"`).
- Unlimited: still `true` from S2R-Q's session (same tab, no reload) —
  re-verified anyway per "re-verify at the moment you commit": **pixel
  zoom** confirmed `UNLIMITED · ~~140~~ · 0` immediately before the click.
- **Fired** at `2026-09-10T17:01:33Z` (2026-09-11 00:01:33 ICT — the
  Unlimited grant's 06:59 ICT deadline is now ~7 hours out). New asset id
  `98f51d92-9119-4147-8d42-1bb6569dee26` (asset count 782→783).
- **Usage History re-checked**: cost unchanged, "Total generations"
  201→202. $0 charged.
- Awaiting render.

## Extraction script bug found and fixed mid-task

`scripts/browser/extract-paste-block.py`'s first version flattened a
block's word-wrap newlines to spaces only when the WHOLE block had zero
blank lines. That is correct for S22/S2R-Q (one giant word-wrapped
paragraph, no blank lines at all) but wrong for S2PT's sheet, which is
genuinely multi-paragraph (one paragraph per beat, blank-line separated)
**and** each paragraph is itself hard-wrapped across several lines. The
naive rule saw a blank line anywhere in the block and skipped flattening
entirely, which would have pasted all 192 raw source lines as 192
separate Lexical paragraphs instead of the ~22 real ones — the same
`innerText`-inflation defect as the S22 fix, just ~4x larger (191 extra
chars instead of 46). Caught before any paste, by inspecting the
extracted file's line count (192) against the sheet's ~22 real
paragraphs, before trusting it for Phase 3.

**Fix**: split the block on blank-line boundaries first, flatten each
paragraph's internal newlines to spaces, then rejoin with a single blank
line between paragraphs. Re-verified all three sheets after the fix:
S22 → 3927 chars/1 line (unchanged), S2R-Q → 4960 chars/1 line
(unchanged), S2PT → 11911 chars/22 real paragraphs (21 blank-line
separators), chip mentions unchanged (13 raw / 7 unique, matching the
`prompt-lint.py --chips` expectation and the earlier take-3 report's own
count).

## Phase 3 — S2PT take 4 "THE TOUR, TOGETHER" — previz checked, one finding, not fired yet

Sheet confirmed at commit `c4b98bf` or later via `git log` — this
branch's history includes `c4b98bf` (v4 sheet) and the two follow-up
previz-only fixes `fdbfe17` and `a8b394d` (put Dupe at the cart's own
depth). Extraction re-verified above (7 unique chips, 0 stray `@Video`
mentions in the static text — the video chip is added via the composer's
upload flow, not typed).

**Previz file located**: `C:\Users\UsEr\Downloads\S2PT-Render.mp4` —
1280×720, 24fps, 20.00s exactly, matches spec. Only one file matching
`S2PT-Render*` in Downloads (no ambiguity between an old/new copy to
choose between, unlike the brief's warning about the Uploads panel
possibly showing two — that check still applies once it's uploaded).

**Finding, not treated as a blocker — reasoning recorded for the
reviewer:** sampling frames at 0.5s/5s/10s/15s/19s, Dupe's cylinder body
is **not visibly distinguishable from the background** at normal
brightness — only his floating "DUPE" text label is clearly visible, with
no cylinder underneath it. A brightness/contrast-boosted re-render of the
10s frame (`eq=brightness=0.25:contrast=2.0`) reveals a faint pale sliver
of his cylinder peeking out from directly behind/beside the cart's tall
items — he is present, but almost entirely occluded by the cart from this
flat side-on camera angle, for the whole 20s (identical across all five
sample times, consistent with the camera tracking everyone at a fixed
relative screen position).

Checked this against the actual previz source, `scripts/previz/s2pt_previz.py`
(commit `a8b394d`): DUPE sits at `x=-0.15, dy=-2.90`; the cart is built at
`x=-0.15, dy=-2.20`. Same depth (`x`) as the cart, and the cart leads him
by 0.7m in the walk direction (`dy` — cart's -2.20 is less negative than
Dupe's -2.90, and the party walks +Y, so the cart is genuinely ahead).
**This is the geometric relationship the brief's check asks for** — cart
ahead of Dupe, not Dupe ahead of cart, which was the actual bug in takes
1-3. The task's two named auto-stop conditions are "previz missing" (it
is present, right duration/resolution) or "shows Dupe ahead of the cart"
(the math says the opposite is true). Neither applies literally, so this
was **not** treated as the "wrong file attached" blocker.

What it does mean: this exact previz frame gives the video model a very
weak visual signal for where Dupe's reference should map to (his marker
region is mostly hidden behind the cart's silhouette), which is a
different, new risk than the one v4's fix targeted — the model might
still place `@project_absence_char_cleaner_c` correctly from the prompt's
explicit prose (POSITION MAP + "DUPE IS PUSHING A WHEELED CLEANING CART…
his hands are on the handle at the back") even if the video reference
alone wouldn't be enough. **Flagging this explicitly for whoever reviews
take 4's frames**: review-order item (1) already asks to crop the right
third at 7/15/19s and say where Dupe's hands are — if take 4 fails again,
check whether it inherited a wrong hand position from this occlusion
before writing a v5 prose fix, since the previz signal here is weak
specifically at Dupe's own position.

**Not fired yet** — waiting for the one Unlimited slot (S22 fired and
completed, S2R-Q fired and rendering — see above). Will upload the
re-rendered previz (below) fresh via + → Uploads → Videos when the slot
reaches this phase, confirm eligibility, and re-check the
cart-ahead-of-Dupe relationship on the freshly-attached chip before
pasting the prompt, per the brief.

### CTO cross-session message — re-render confirmed, occlusion actually FIXED

A CTO session (`bridge:session_01T2Ri4fTB7YVL8ss3M9JiX9`) messaged mid-task
with the same concern independently: don't trust the existing previz,
re-render from the fixed script and **confirm Dupe is actually visible**
before uploading. Acted on it:

1. Confirmed Blender 5.2 is installed on winbox
   (`C:\Program Files\Blender Foundation\Blender 5.2\blender.exe`).
2. `git fetch origin main` — no previz commit newer than `a8b394d` exists,
   so the repo's `scripts/previz/s2pt_previz.py` is already the fix to
   render from.
3. Ran it headless against the project's base scene:
   `blender.exe -b SorrySir_hall_v41.blend --python scripts/previz/s2pt_previz.py`
   → `C:\Users\UsEr\Downloads\S2PT-Render.mp4` (**overwriting** the file
   analysed above — the old 1,659,245-byte file no longer exists locally).
4. **Result is a completely different, much better previz than the file
   that was already sitting in Downloads.** The old file rendered as a
   bare grey block-out with no location geometry at all (matching the
   frames analysed above); this fresh render includes the real
   `SorrySir_hall_v41.blend` location — columns, chandelier, patterned
   floor, wall art — and, critically, **Dupe's cylinder is now plainly,
   unambiguously visible** standing just behind and beside the cart in
   every sampled frame (0.5s/10s/19s), not merely a faint sliver under
   contrast boost. The likely explanation: whoever produced the old file
   ran the previz script standalone (default empty scene) rather than via
   `run_s2pt.cmd`'s `-b SorrySir_hall_v41.blend` invocation, which is also
   why `Downloads\s2pt_previz.py` (a separate, STALE copy with the
   pre-fix `DUPE x=0.60` / cart `dy=-3.60` values — diffed and confirmed)
   was never actually the source of that render either; something else
   produced it.
5. **New file**: `C:\Users\UsEr\Downloads\S2PT-Render.mp4` — 4,157,750
   bytes, MD5 `db57cf109e231973e622a9c4a1140ccc`, 1280×720 @ 24fps, 20.00s.
   This is the file to upload for take 4, not the one this report
   originally analysed.

Replied to the CTO session confirming this.

## Checkpoint

`2026-09-10T15:45 UTC` (`22:45 ICT`). S22 still Processing (~20 min
elapsed, normal per the skill's queue-depth timing — 15:25 UTC fire time
is inside Europe's working day, so 40-90 min is more likely than the
20-25 min night-window figure). S2R-Q fully staged in the composer, ready
to fire the moment S22 completes and the slot frees. S2PT take 4's
prompt is extracted and verified but not yet pasted (staging it now would
mean re-verifying it twice for no benefit, since S2R-Q must fire first).

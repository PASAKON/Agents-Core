# S21 THE NEWS WALL — winbox browser operator report (task-1028bcfc)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7)
Browser: winbox-chrome (`815ddf16-…`), fresh tab id `1638445172`, claimed via tab_registry.
Other operator's tab (task-fc063e0e, id `1638445167`) never opened/touched. A "Processing" card visible in
the shared project asset grid throughout (not mine — the other operator's free/Unlimited-lane render;
never clicked, cancelled, or interacted with).

## Pre-flight

- `git fetch origin main` confirmed worktree already at commit `ccc62a3` (the branch this task started on).
- `python scripts/prompt-lint.py docs/prompts/absence/s21-addon-the-news-wall.txt` — clean, exit 0.
- Sheet already carries the fix from the prior blocker (task-01f88235): the museum/`loc_exterior` chip is
  gone; the building insert ships as prose. **Only 2 chips** in the PASTE block:
  `@project_absence_prop_tv_wall` and `@project_absence_char_valder`. No Element created, renamed, or
  deleted — `project_absence_prop_tv_wall` was already registered by the prior operator.

## Step 1 — browser + tab setup

- `select_browser` on `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome, per `config/hosts.yaml` /
  `ORG_HOST=winbox` — no ambiguity, no `list_connected_browsers` prompt needed).
- `tabs_context_mcp` returned one pre-existing empty `New Tab` (id `1638445172`), unclaimed in the
  registry (checked `state/browser-tabs/*.json` directly — not in any live task's file). Used it as my
  fresh tab and claimed it: `tab_registry.py claim task-1028bcfc 1638445172 <project URL>`.
- Navigated to the project URL. `resize_window(1600,1000)` → readback `window.innerWidth === 1920`
  (already wide; the resize call's own claim is unverified per the skill, but the JS readback proves
  desktop layout). Desktop composer confirmed present throughout (Unlimited toggle exists, no `disabled`
  Generate button, no mobile lockup).

**Tooling note for whoever inherits this task next:** `tab_registry.py list` / `owner` / `orphans` crash
on this host — `state/tasks.db` exists at `C:\Users\UsEr\mooniex\state\tasks.db` but has **no `tasks`
table** (empty schema), which the script's fail-safe branch doesn't cover (it only checks
`DB.exists()`, not whether the table exists). `claim`/`release`/`done` are unaffected (no DB read). I
did not patch the script — flagging it as a known winbox quirk rather than fixing scope I wasn't asked
to touch.

## Step 2 — stage and fire

The composer landed already set to Seedance 2.0 Fast / 16:9 / 720p / 8s / High / Sound On / batch 1/4 /
Unlimited off (apparent carry-over account-level state from a prior session) — verified every field fresh
rather than trusting that:

- Model: "Seedance 2.0 Fast" (visible label).
- Duration: real DOM slider (not the hidden decoy — two `[role="slider"]` elements exist, the decoy read
  `max=30, valuenow=5`; the real one for this model reads `min=4, max=15, valuenow=8`). Confirmed **8s**.
- 720p, 16:9 — visible labels.
- Quality: "High" (found via button-text scan, filtered to the one non-decoy match).
- Sound: "On" (`find()`).
- Unlimited: `aria-checked="false"`, `data-state="off"` — **OFF**, credit lane as required. Re-verified
  immediately before the click, not just once at setup.
- Composer was clean before pasting: 0 chips, 0 `<video>` elements, no leftover reference thumbnails
  (visual zoom of the tray + DOM check).

**Paste — byte-verified, no hand-transcription at any step:**
1. Extracted the PASTE block from the sheet to a scratchpad file with a Python script (regex between the
   sheet's own markers), never retyped by hand.
2. Base64'd that file from disk (`base64.b64encode` on the file's bytes), wrote the b64 to a second
   scratchpad file, read that file's content back for the paste — the b64 string used in the browser call
   came from the file, not from memory or re-derivation.
3. In-page: decoded the b64 → `TextDecoder('utf-8')` → dispatched a synthetic `ClipboardEvent` (`paste`,
   `text/plain` only, no `text/html`, no follow-up synthetic `input` event) into the verified-visible
   (non-decoy) `[contenteditable="true"]` node, confirmed via `document.activeElement` immediately after
   the initiating click.
4. `End` → `space` → `Backspace` (real keypresses) to force Lexical's bound state to sync.
5. **Length check**: decoded text in-browser measured **5344 chars**, matching the source file's Python
   `len()` of **5344 chars** exactly. Landed editor `innerText` normalized (collapsing contenteditable's
   doubled `\n\n` back to `\n`) also measured **5344**, and first/last 80 characters matched the source
   verbatim. No truncation, no duplication, no hand-transcription drift anywhere in the chain.

**Chip check** (selector per the skill: `span.text-font-brand` leaves starting with `@`, filtered to
non-nested):
```
2/2 bound, 0 error chips (.text-icon-error): 
  @project_absence_prop_tv_wall
  @project_absence_char_valder
```
Reference tray zoomed pixel-wise: 2 thumbnails, no prohibited/no-entry icon overlay on either — clean,
unlike the prior operator's 3-chip attempt where the museum chip carried the flag.

**Price check (pixel zoom of the Generate button, not a DOM scrape):** `GENERATE +28` — matches the
sheet's expected ≈28 credits, well under the 45-credit stop threshold. No strike-through (expected:
Unlimited is off by design on this lane, so a bare live number is correct, not a warning sign).

**Fire:** clicked Generate once. Toast "Generation started" appeared immediately, a new card entered
`Generating` state in the grid, asset count `778 → 779`. **No protected-content warning this time** — the
prior blocker (flagged `loc_exterior` chip) does not reproduce now that the chip is gone.

New asset id (from `data-asset-id` on the Generating card): **`71ccced9-2936-45b8-879c-a0c9d8469a72`**.

**Usage History confirmation** (opened in a separate tab, never navigated the composer tab away; tab
closed and released immediately after reading): top entry reads **`28 credits · Seedance 2.0 · Spent ·
Sep 10, 2026 7:03 PM`** — exact match to the price shown before the click. Fire time ≈ 2026-09-10
12:03:53Z (19:03:53 ICT).

## Render completed — ~23 min (fire 7:03:34 PM ICT → card `New` at next check ~7:23 PM ICT)

Card `71ccced9-2936-45b8-879c-a0c9d8469a72` showed `New`, no `Processing`/`Generating` text, when checked
at the first poll (~20 min after fire, per the skill's cadence). Opened its `?preview=dccc8bb8-…` modal —
different id in the URL than the card's `data-asset-id`, but content is unambiguously the same asset: the
video `currentSrc` filename is `hf_20260910_120334_71ccced9-…mp4` (the exact id), the prompt panel shows
the sheet's PASTE text verbatim starting `8s · 720p · 16:9 · ONE LOCKED SHOT…` with the
`@project_absence_prop_tv_wall` chip, and Details read Feature **Seedance 2.0 Fast**, Quality **720p**,
Bitrate **High**, Size **1280x720**, Created **September 10, 2026 at 7:03 PM** — matching the Usage
History entry exactly. **No rights-verification banner appeared** on this card (nothing to confirm).

## Harvest

- Downloaded via the preview panel's Download button → `C:\Users\UsEr\Downloads\hf_20260910_120334_71ccced9-2936-45b8-879c-a0c9d8469a72.mp4`
- **Bytes**: 10,945,410
- **MD5**: `8b89868b7d47d0aa10c6a58c061dd9cf`
- **Asset id**: `71ccced9-2936-45b8-879c-a0c9d8469a72`
- **ffprobe**: h264, 1280x720, 24 fps, aac audio, duration **8.096s**
- **Model**: Seedance 2.0 Fast · **Settings**: 720p, 16:9, High, Sound On, batch 1/4, Unlimited OFF
- **Fire time**: 2026-09-10 12:03:53Z (19:03 ICT) · click-to-Usage-entry match: `28 credits · Seedance 2.0 · Spent · Sep 10, 2026 7:03 PM`
- **Credits shown before click**: `+28` (pixel-zoomed, matches the sheet's expected ≈28, well under the 45 cap)
- **Chip count at fire**: 2/2 bound, 0 error chips
- Frames extracted at FULL resolution (1280x720) via `ffmpeg -ss <t> -frames:v 1 -q:v 2` at 0.5, 2.2, 4,
  5.5, 7.8s → `docs/reports/frames-s21-t1/s21-t1-<t>s.jpg`.

## Review — per the brief's REVIEW ORDER

**Exact prompt used** is the sheet's PASTE block verbatim (`docs/prompts/absence/s21-addon-the-news-wall.txt`,
commit `ccc62a3`, unmodified — no edits this session), reproduced in full above under "Editor gotchas /
Paste" and in the card's own Prompt panel.

1. **Shop window and sets match the registered Element — PASS.** Compared `s21-t1-0.5s.jpg` against
   `docs/reports/plate-tv-wall/variant-a.jpg` (the registered `project_absence_prop_tv_wall` source):
   same uneven second-hand TV stack and arrangement, same wooden cabinet at left, same chrome ball on a
   stalk, same red cabinet and wood drawers on the right, same wet pavement and amber fascia. No set
   added or removed, nothing rearranged (tighter framing than the source plate but the same elements in
   the same relative positions).
2. **Nobody in the room — PASS.** Checked all 5 frames: no shopper, no passer-by, no silhouette, no
   reflection of a person in the glass, at any sampled timestamp.
3. **Every screen lit, all showing the SAME broadcast, never out of sync — FAIL.** This is a real defect,
   not a close call. At 0.5s and 2.2s every screen correctly shows the same newsreader. **From 4s**,
   only a **subset** of screens (4 of ~29 at 4s, 5 of ~29 at 5.5s) switch to showing the museum-building
   insert — and by **7.8s**, screens are showing THREE different pictures simultaneously: most show the
   Valder photograph, several still show the museum building (unchanged from the 2s cue), and at least
   one screen (visible at roughly the composer's centre, e.g. `s21-t1-7.8s.jpg`) still shows the plain
   newsreader with no insert at all. The wall never re-synchronizes within the clip's 8s. This directly
   contradicts the prompt's own negative: *"the screens never show different pictures from each other,
   never go out of sync."*
4. **Insert delivery — FAIL, related to #3.** The prompt asks for the museum building and the Valder
   photograph to appear as **"a small square INSERT PICTURE"** beside the newsreader's head, with the
   newsreader still visible and talking underneath/beside it — *"small in the screen... beside his head a
   small square insert picture."* What actually rendered on the screens that did change is the insert
   image **replacing the entire screen content** (full-frame takeover, newsreader gone), not a small inset
   next to him. Combined with #3, the net effect is a wall where some screens show a full-frame building,
   some show a full-frame photograph of a man in a colourful blazer, and (briefly) some still show a
   full-frame newsreader — the opposite of the single, synchronized broadcast the shot is built around.
5. **No readable word/letter/number/logo — PASS on the samples checked.** Cropped/zoomed the lower-third
   colour band at 0.5s: a soft, blurred orange/white stripe with no resolvable text, consistent with the
   prompt's "far too small and too soft... for any word to resolve." Did not exhaustively check every
   screen at every frame for text, only the sampled crops.
6. **Camera dead locked, no push-in, no cut — PASS.** All 5 sampled frames show identical framing,
   window position, and TV-wall geometry; no visible pan/tilt/zoom/cut across 0.5s→7.8s.
7. **Audio — partial check only.** `ffprobe` confirms an AAC audio track present for the full 8.096s.
   `ffmpeg silencedetect` (threshold ‑35dB) found **no silence at 0s** (room tone/murmur present from the
   start, matching "opens mid room-tone with no intro sting"), and a short silence only in the final
   ~0.3s (7.8–8.096s), consistent with "simply stops with no tail." I did **not** verify the actual
   spoken content (the two scripted lines) — that needs a human listen; I have no transcription tool
   available in this session.

## Verdict — FLAGGED, not self-certified

Per "THE REVIEW LOOP — the operator never self-certifies a clip," I am not marking this pass/fail myself
beyond reporting what the frames show. **Items 3 and 4 are clear, verifiable defects** (out-of-sync
screens; inserts rendering as full-screen takeovers instead of a small inset beside the newsreader) —
the same failure class the skill's "duplicate character" and "wrong asset" precedents describe: technically
correct fire (right chips, right settings, right price), but the model did not follow the shot's own
explicit rules. Filing this as `-FLAGGED-inserts-out-of-sync`.

- File kept exactly as downloaded, nothing deleted, nothing re-fired (task explicitly bans firing twice).
- Frames committed below for CTO review; MP4 stays local only (`C:\Users\UsEr\Downloads\hf_20260910_120334_71ccced9-2936-45b8-879c-a0c9d8469a72.mp4`), per the brief.
- **Did not** attempt a second generation, did not touch the sheet, did not touch any Element.

## Current state

- Composer tab `1638445172` left on the project page (idle, nothing further staged — this is a single-clip
  harvest task, not a wave with a next scene to pre-stage).
- Other operator's tab (`1638445167`) never opened or touched.
- No Element created/renamed/deleted this session.

## Stop-and-ask

None of the brief's listed stop conditions were hit (no protected-content warning, price was 28 ≤ 45,
Unlimited stayed OFF throughout, chip count was correct, no viewport lock-up, no browser-tool error). The
out-of-sync/insert-delivery defect above is a **creative/model-behaviour finding for the review loop**,
not one of the brief's stop-and-ask triggers, so I did not file a `BLOCKER.md` — but I am not marking the
task complete-and-clean either; see Verdict above for what needs a CTO/CEO call (re-fire as a spare take,
adjust the prompt to state the sync/inset rule even more forcefully, or accept as-is).

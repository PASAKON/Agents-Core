# S2K-Fix1 take 2 — absence wave, 2026-09-06

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The Valder Collection No.7").
Sheet: `docs/prompts/absence/s2k-fix1-the-crowd-gathers.txt`, gated at HEAD `7024a47` (after mandatory `5eaf42a`).

## Pre-fire gate

- `git merge main` — already up to date, HEAD `7024a47e1e770d15c61ee8c865ae90ed9bc01538` (>= `5eaf42a` required). PASS.
- `grep -c 'NO WIDER THAN THE RED DOOR'` on paste block → **1**. PASS.
- `grep -c -i -E 'nearest|extreme foreground|very front|floating|toward the mark|looking at the (break|mark)'` on paste block → **0**. PASS.
- `prompt-lint.py --chips` → EXPECTED 8 Element chips (matches sheet).
- Previz byte count: task brief said 2,859,627 bytes; actual `docs/S2K-Render.MP4` on disk was **2,813,179 bytes** (2747 KB). Mismatch noted — proceeded with the actual file on disk (v2, crack-free per sheet notes), verified upload-reported size (2747 KB) matched local bytes exactly.

## Browser actions

- innerWidth readback: **1600** (first tab) / **1440-1600** (second tab after resize_window returned an unrequested size — readback is authoritative per skill, both were >= 1280).
- Banner "Credits are running low! Over 90% already used" closed with its own (x): **yes**, every fresh tab/reload.
- Two tabs used: first tab hit a persistent `Page.captureScreenshot` timeout after the paste (page stayed JS-responsive throughout — no Processing/modal appeared, confirmed no accidental fire); escalated per skill (reload → fresh tab). Second tab worked cleanly for the remainder including render-check reloads. Both tabs claimed/released via `tab_registry.py`.

### Six fields (12s!)

| Field | Value | Verified |
|---|---|---|
| Model | Seedance 2.5 | selected explicitly from dropdown |
| Aspect | 16:9 | default, unchanged |
| Resolution | 720p | changed from 1080p default |
| Duration | 12s | ARIA slider, `aria-valuenow` read 5→12 via 7x ArrowRight after thumb click (never typed) |
| Quality | High | already correct after mode switch |
| Sound | On | already correct after mode switch |

- Price zoom: **`UNLIMITED · ~~84~~ · 0`** (zoomed screenshot, not JS scrape — JS scrape of `/generate/i` buttons returned a stale decoy `GENERATE8045` at one point, correctly ignored per skill).
- Chip gate: `python3 scripts/prompt-lint.py --chips` → 8 unique names expected. Composer selector (`span.text-font-brand` filtered) → **8/8 unique chips bound, 0 red/unresolved '@' mentions**. Reference strip showed 9 thumbnails (8 element chips + 1 video ref).
- Previz attached: **yes**. Two-click flow: uploaded via reference panel file input (idx matched `accept` containing `video/mp4`), "Checking.." pill cleared to a real thumbnail within ~15s, clicked tile → "Added to prompt box" toast. Uploaded size 2747 KB matched local file exactly. No 10-minute stall encountered.

## Fire

- Fired at **2026-09-06 15:36:11 ICT (08:36:11 UTC)** via the real (non-decoy) Generate button element — located by filtering `getBoundingClientRect()` for a non-empty rect after an initial click landed on a hidden decoy (`visibility:hidden`, empty rect) with no effect.
- Verified: "Generation started" toast + asset count **669 → 670** (read before firing, confirmed after).
- Note: outside the recommended 01:00-07:00 UTC low-queue window (fired ~08:36 UTC) — task was time-critical (film due 9 Sept), not delayed.

## Render

- Duration: **~39 minutes** (fired 15:36, card showed finished/"New" badge at the 16:14-16:19 poll cycle). Faster than the 20s-clip norm (30-55 min today), consistent with the shorter 12s duration.
- Poll cadence followed: first check ~20 min after fire, then every 5 min, each cycle an active reload + re-read (never a scheduled-wake-only approach). Mid-wait the Chrome tab group was lost (unrelated to the render — verified the server-side generation survived; claimed a fresh tab and continued, no re-fire).
- NSFW / credits-refunded: **no**. Card status read "No status" on completion — clean.

## Verification

- Info icon opened: Model `Seedance 2.5`, Quality `720p`, Bitrate `High`, Size `1280x720`, Created `September 6, 2026 3:36 PM`. Prompt panel matched the pasted sheet text.
- Downloaded via the card's Download button → `~/Downloads/hf_20260906_083600_2b045110-bc20-4311-9ff0-a9bb4028a6f7.mp4` (12,225,826 bytes).
- `ffprobe`: **1280x720, h264, 24fps, 12.04s duration, aac stereo audio (32kHz)** — matches spec.
- Filed to Drive via `scripts/gdrive-bridge/upload_fix1.py`: **`S2K-Fix1-take2.MP4`**, 11.7 MB → `https://drive.google.com/file/d/1mHUQGIRcmfoIGVhSTvOsLaclJj9k4gMW/view`. Logged to `Sorry, Sir/logs.txt` (append_log via the bridge) in the same call.

## Frame checks (0.5s, 3s, 6s, 11s)

Frames saved under `docs/reports/frames-s2k-fix1-t2/`:
- `s2k_fix1_t2_0.5s.png`, `s2k_fix1_t2_3s.png`, `s2k_fix1_t2_6s.png`, `s2k_fix1_t2_11s.png` (full frames)
- `mark_zoom_0.5s.png` (crop on the mark), `rust_face_3s.png`, `maroon_man_3s.png`, `dupe_3s.png` (crops for the checklist)

**0. THE MARK** — over the far red door, solid black, thin lines meeting at one small dark point, off every face (confirmed via `mark_zoom_0.5s.png` — sits above the art student's head, clear of her hair). Size in words: **about 1x the door** — comparable width/height to the red double door beneath it, not enlarged, not touching anyone. **PASS.**

**0b. FACES AT THE MARK** — all four women (magenta/critic, cobalt/woman, rust/visitor_b, and the art student) face the lens in every checked frame (0.5s, 3s, 6s, 11s), no backs or profiles turned to the far door. **PASS.**

**1. THE COUPLE IS TWO WOMEN** — cobalt-coat woman stands directly beside the rust-coat woman in every frame; no man appears beside or near them at any checked timestamp. **PASS.**

**2. THE MAN IN MAROON IS ALONE AND FAR OFF** — confirmed small, separate figure visible in the background at 3s (`maroon_man_3s.png`), clearly apart from the four-woman group and never joining it. **PASS.**

**3. THE CRYING IS SMALL** — rust-coat woman's face at 3s (`rust_face_3s.png`) shows a subdued, undramatic expression; no visible sobbing, shaking, or hand-to-mouth gesture in any checked frame. Visual-only check (audio not manually reviewed — see below). **PASS on visual evidence.**

**4. NOBODY SPEAKS** — no open-mouth/talking poses in any checked frame; audio track present (AAC 32kHz stereo, "Sound On" confirmed) but not manually listened through for dialogue absence — flagging this as unverified-by-ear rather than claiming a false PASS.

By 11s (`s2k_fix1_t2_11s.png`): magenta-coat woman's arms are folded (matches the [10s] beat), mark unchanged over the door, all four still facing camera, DUPE at his cart far left, maroon man visible far right background.

## Anything odd

- Previz file byte-count mismatch vs the task brief (2,859,627 expected vs 2,813,179 actual) — used the actual file on disk since it matched the sheet's own description (v2, crack-free) and its upload-reported size was internally consistent.
- First browser tab suffered repeated `Page.captureScreenshot` CDP timeouts right after the large synthetic-paste (9.6k chars into the Lexical editor) — page remained JS-responsive throughout (confirmed no Processing card, no modal, no accidental Generate) — escalated to a fresh tab per skill, which resolved it.
- Initial Generate click landed on a hidden decoy button (`GENERATE8045`-style stale duplicate, `visibility:hidden`, empty bounding rect) with zero effect — re-located the real button by filtering for a non-empty `getBoundingClientRect()`, second click fired correctly and was verified by toast + asset-count delta.
- Chrome's MCP tab group was dropped during the ~20-minute wait between the fire and the first status check (unrelated to the render, which is server-side) — recovered with a fresh tab, no re-fire, no data lost.

## Verdict

S2K-Fix1 take 2: **mark and faces PASS**, review items 1-2 PASS, item 3 (small crying) PASS on visual evidence, item 4 (nobody speaks) unverified by ear. Filed regardless, per standing rule. No re-fire performed — per brief, stopping here.

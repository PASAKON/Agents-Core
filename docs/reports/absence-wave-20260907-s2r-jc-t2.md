# S2R-JC take 2 — THE BATTLE, jump-cut, previz attached — 2026-09-07

Task: task-a5de192a (browser_operator). Sheet: `docs/prompts/absence/s2r-fix1-the-battle-jumpcut.txt`.

## Route
route: step 3 (own tab, claude-in-chrome only) — task named the Higgsfield project URL directly, no API.

## Composer build
- innerWidth readback: 1440 (>= 1280 desktop threshold), confirmed on every tab used.
- Banner "Credits are running low!" closed via its own (x) on every fresh tab, before touching Unlimited.
- Six fields (final fire): Seedance 2.5 · 720p · 16:9 · 20s (ARIA slider, ArrowRight/Left, never typed) · High · Sound On.
- Paste: synthetic ClipboardEvent on the real (visible) contenteditable node, base64-encoded paste block, End→space→Backspace tap after every paste to force Lexical state sync.
- Chip gate: `python3 scripts/prompt-lint.py --chips <sheet>` → 13 expected. Composer count via
  `[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'))`
  → 13/13 unique, 0 `.text-icon-error`, every fire.
- Unlimited toggled AFTER all six fields (duration reset resets it), zoomed every time: `UNLIMITED · ~~140~~ · 0`.

## Previz — byte-check false positive found and corrected
- docs/S2R-Render.MP4 = 4,528,874 bytes locally.
- First "byte match" (session 1) was taken from a `blob:` URL captured off the **expand-preview modal**'s `<video>` element and turned out to be a **partially-buffered Blob** — matched by coincidence, not by content. A later `fetch(url, {cache:'no-store'})` against the actual cloudfront URL for that same tile returned **1,796,645 bytes**, not a match. Lesson: byte-verify the *cloudfront URL itself* (`fetch(..., {cache:'no-store'})` → `blob.size`), never a modal's `blob:` object.
- Scanned every similar "CRIT_MAN…" thumbnail in the Videos reference panel and found the real match: `.../5b7b05d6-2eda-4088-86f3-bd9af901412c.mp4`, byte-verified 4,528,874 via fresh no-cache fetch. This tile was used for every later fire attempt.
- A separate fresh upload (via `file_upload`) of the same local file also verified at 4,528,874 bytes (confirmed via its blob `<video>` element) but was removed before firing to avoid two video refs in one composer (brief: "the video is a CHIP exactly ONCE").

## Generate-disabled saga (why this took ~5 hours)
1. First tab: Generate stayed `disabled=true` with the previz attached, previz eligibility suspected (byte match looked correct at the time).
2. CTO ladder: remove tile → still `disabled=true` with **zero** video refs and 13 chips only → ruled out eligibility, matched brief §5 pipelining (S2G render in flight, account-wide Unlimited slot busy) — Higgsfield was apparently disabling the button client-side rather than only toasting on click.
3. Held (CTO instruction, 90s then 300s sleeps) while S2G / SC4 / S2N-B / SC5 cleared the queue ahead.
4. RESUME at ~21:50: fresh tab, Generate read `disabled=false` (never priced, plain "GENERATE 210→195" before Unlimited toggled) — confirmed the busy-slot hypothesis. Rebuilt composer from scratch.
5. First click at Unlimited·0 → busy-slot toast "You can generate 1 unlimited video, image & audio generation at a time" (not a fire). Composer state stayed intact.
6. Retried Generate once at the 5-min mark (no reload) → **"Generation started"** toast + new Processing card + asset count 705→706.

## Fire
- Verified by: "Generation started" toast, exactly one new Processing card at fire time, asset count 705→706.
- Fire time: **2026-09-07 22:07:13 ICT**.

## Post-fire polling
10-min fresh-tab polls, no reload of a live composer tab (none was open post-fire). Render completed between the 30-min and 40-min checks — total render time **~46 min** (fired 22:07, card showed a real thumbnail at the ~50-min check, Created timestamp confirms 22:06 PM start). Within today's observed range for the Unlimited lane once the slot actually freed.

## Identify-mine
A second Processing card appeared mid-poll (someone else's fire, not mine — asset count moved 706→707 independently). Both finished around the same window. Identified mine via the Info panel (`?preview=<uuid>` route, clicked the actual card center, not the hover icons):
- **Prompt** (in the Info panel): verbatim match to the pasted block, opening "20s · 720p · 16:9. The camera is LOCKED and never moves…".
- **Model**: Seedance 2.5. **Quality**: 720p / High. **Size**: 1280x720.
- **Created**: September 7, 2026 at 10:06 PM (22:06 ICT) — matches the 22:07:13 fire time.
- No "Rejected due to copyright restrictions" / NSFW banner. Clean render.

## Download + file
- Downloaded: `hf_20260907_150651_c1a0be1a-e8d8-4b9f-930c-2252e3e4d168.mp4` (18,110,531 bytes local), `data-asset-id=c1a0be1a-e8d8-4b9f-930c-2252e3e4d168` matched the asset id captured off the grid tile during polling — second independent confirmation this is my card.
- md5 `3bc98a8944ca06663ebda7536451e52e` — checked against every other mp4 in `~/Downloads` (80+ files), no match. Not a re-download of an earlier take.
- ffprobe: video 1280x720, duration 20.041667s; audio present, duration 19.968s. Matches spec (20s · 720p).
- Filed: Drive `All Scene/Fix-1/` as `S2R-JC-Fix1.MP4` via `scripts/gdrive-bridge/upload_fix1.py` — https://drive.google.com/file/d/1VXFdhmTGjsX0bySJ2Py38yw9ESVp6ZSz/view — `logs.txt` line appended by the script.

## Frame checks
Frames at 0.5s, 2.5s, 3.5s, 8.5s, 9.5s, 14.5s, 15.5s, 19.5s — `docs/reports/frames-s2r-jc-t2/t<seconds>.png`.

Review order — the jump-cut sheet's own addendum (items below "0"), plus the base sheet's inherited order (`s2r-fix1-the-battle.txt`, items 1-7):

| # | Item | Verdict | Notes |
|---|---|---|---|
| 0 | Three cuts at ~3s/9s/15s, frame **identical** on both sides of each cut (sheet's own explicit wording — locked camera, "same lens, same framing… only time jumps") | **PASS** | `t2.5.png` vs `t3.5.png`, `t8.5.png` vs `t9.5.png`, `t14.5.png` vs `t15.5.png` all show identical framing/composition — no pan/tilt/zoom, confirmed. |
| 1 | Valder in the middle, stays there | **PASS** | Centred (rainbow blazer) in all 8 frames, never drifts, never joins the bidding. |
| 2 | THE HEADS SWING — left/right/left/right, ragged, following whoever spoke. "That swing is the scene." | **FLAGGED** | Cropped the background-crowd strip (`crop_t2.5.png` vs `crop_t3.5.png`) and diffed pixels across every cut boundary: mean abs diff at cut boundaries (5.4-5.9) is **not distinguishably higher** than mean abs diff between two frames deep inside the same uncut span (`t3.5` vs `t8.5`, 5s apart, no cut between them: 6.07). Visually every head — Carrington, both navy guards, the registrar, background extras — is in the same orientation before and after each cut. The described head-swing choreography did not render. This is the sheet's own stated core beat of the scene and it is absent. |
| 3 | Nobody walks | **PASS** | No visible foot/stance change across any frame pair; everyone static. |
| 4 | Five bids in order, hers first, nobody else speaks | **NOT VERIFIED** | No transcription tool available in this session; audio track is present (ffprobe, 19.968s) but content not checked. |
| 5 | She never raises her voice / he starts confident, ends silent | **PASS (visual)** | Carrington: closed-mouth smile at 0.5s/2.5s/3.5s/8.5s/9.5s → mouth open, shocked/silent at 14.5s/15.5s/19.5s. Matches the described arc exactly. Audio delivery not verified (see item 4). |
| 6 | Registrar writing the whole time | **PASS** | Present in every frame, cream/orange-piped uniform, ledger + pen held consistently; can't confirm active pen motion from stills but pose/props are correct and unchanging. |
| 7 | Twelve people, no extras, no duplicate fur woman | **FLAGGED — uncertain, needs a human look** | Several partially-obscured background figures (steward-hat silhouettes between the two navy guards, a dim extra head at the far left edge behind the registrar) are visible in `t8.5.png` that don't cleanly resolve to one of the 13 named references. Could be edge-of-frame overlap of the same named cast, or could be true extras — stills at this resolution can't settle it. No duplicate chestnut-fur woman found (only one brown/tawny-fur figure spotted, partial, right of the green dress). |

**Overall: FLAGGED** — item 2 (head-swing choreography, the sheet's stated core beat) did not render; item 7 (headcount) is uncertain and needs a full-resolution human look. Filed regardless, per instruction ("File the take whatever the verdict").

## Notes for reviewer
- The take is visually strong (cast, costumes, positions, colour grade, Carrington's silent-collapse arc all correct) — the miss is specifically the jump-cut head-swing action, which barely registers as a discontinuity at all against a genuinely locked, static-looking crowd.
- Worth a full-res look at `t8.5.png` for the background headcount before deciding whether to re-shoot.
- SKILL-OVERRIDE: none — followed browser-operator, higgsfield-unlimited-gen and the task brief as written; CTO's live corrections (busy-slot hypothesis, hold/resume cadence) were followed as given mid-task.

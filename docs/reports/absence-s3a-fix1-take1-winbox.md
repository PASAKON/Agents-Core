# Absence — S3a "The First Customer", Fix1 take 1 — winbox (task-850dd3f1)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The Valder Collection No.7")
Sheet: `docs/prompts/absence/s3a-fix1-the-first-customer.txt`

## Result: FIRED AND LANDED. One camera-lock defect flagged in shot 2. Not filed to Drive (no OAuth token on winbox). Zero credits spent.

## STEP 0 probe (per task brief)
- Fresh tab on the project URL: logged in as **ilag-studio**, "The Valder Collection No.7" loaded with its Elements (Character 55, Location 41, Prop 34, Scene folders present).
- Unlimited control present in the composer.
- `window.innerWidth` = 1920 (desktop layout).
- Probe passed — proceeded to fire.

## Setup / gates
- `git merge main` — already up to date (`7851baf`, matches `origin/main`).
- `python scripts/prompt-lint.py docs/prompts/absence/s3a-fix1-the-first-customer.txt` → exit 0.
- `python scripts/prompt-lint.py --chips <sheet>` → 4 expected: `@loc_hall_big_e`, `@project_absence_char_cleaner_c`, `@project_absence_char_oldman`, `@prop_cart_b`.
- FIRE-PLAYBOOK §0/§0b gates on the flattened paste block: flagged-Element grep (word-boundary) → 0 hits; "NO WIDER THAN THE RED DOOR" → 0 (not a wall-POV sheet); extreme-foreground/floating/mark-nearest → 0 hits; weight-word (0b) matches were all non-contradictory (heavy/thick describe the two characters' own build/hair/moustache, "fine film grain" is grade language) — no antonym pair found; `reference video` count → 0 (no previz required).
- Paste block sha256-verified before dispatch: hash matched, length 3687 chars (3711 bytes UTF-8), first/last 80 chars matched the source file exactly.

## Composer
- Real (visible) vs decoy (hidden, `visibility:hidden`) contenteditable both found; focused and pasted into the visible one only.
- Cleared with real Ctrl+A + Delete (no `execCommand`).
- Paste: synthetic `ClipboardEvent` with `text/plain` only (no `text/html`), on `window.__pastePayload` (base64 → UTF-8 decoded and sha256-checked in-page before paste, matching the Bash-side hash).
- End → space → Backspace tap after paste (state-sync technique).
- Chip check: `document.querySelectorAll('[contenteditable="true"] span.text-font-brand')` filtered to leaf `@`-starting spans → **4/4 unique chips bound**, 0 stray/unbound `@` text nodes anywhere in the editor (verified with a TreeWalker over all text nodes). Zoomed the 4 reference thumbnails: no warning triangles on any.
- Duration: ARIA slider (`role=slider`, min 4 / max 30), clicked the thumb, `ArrowLeft` x10 from 20 → verified `aria-valuenow="10"`.
- Six fields verified present: Seedance 2.5, 16:9, 720p, 10s, batch 1/4, High, Sound On.
- Unlimited toggled **after** the six fields: one clean ref-based click, `aria-checked` flipped `false → true` (no stuck-toggle, no retry needed).
- Generate button zoom-verified (pixels, not DOM scrape — the DOM scrape read a stale decoy button `GENERATE8045` in the same check, confirming the skill's warning that a text scrape can be flatly wrong): `UNLIMITED` / struck-through `70` / live `0`.
- Asset count baseline: **732** (matches the sheet's prior Mac-staged note).

## Fire
- Clicked Generate once at **2026-09-09 02:33:22 ICT (2026-09-08 19:33:22 UTC)**.
- Confirmed: "Generation started" toast, new Processing card at top of grid, asset count **732 → 733 (+1)**.
- Sheet TAKE LOG updated and committed (`08a70e6`) immediately after the fire.

## Wait
- Background-timer polling, no foreground blocking sleeps: first check at ~20 min (still "Processing", asset count 733 held), second check at ~25 min (status "Generating"), landed by ~30-34 min (normal range for this project).
- One recovery mid-wait: the original composer tab's OS window collapsed to 294x49 px on its own (not a CSS breakpoint — genuinely tiny), consistent with the skill's "a window can shrink on its own" note. Since the render is server-side and already fired, opened a fresh tab instead of fighting the stale one; closed the broken tab.
- Mid-session the browser connection briefly lost its tab group and a second Windows Chrome device (`70bf3142-...`) appeared alongside the task-named one (`815ddf16-...`); re-selected the task-named device id explicitly and continued — no action taken on the other device.

## Card identification
- Opened the new card's Info panel. **Created: "September 9, 2026 at 2:33 AM"** — matches the fire time exactly.
- Prompt text starts `10s · 720p · 16:9 · TWO SHOTS JOINED BY ONE HARD JUMP CUT` — matches the required marker string exactly.
- Model Seedance 2.5, Quality 720p, Bitrate High, Size 1280x720 — matches spec.
- This is confirmed to be my card, not another worker's.

## Download
- Downloaded via the preview modal's Download button (not Rerun, not Recreate — those were visible but not clicked).
- File: `C:\Users\UsEr\Downloads\hf_20260908_193316_ab04071f-379a-474c-8d9e-e3d3ebec258d.mp4`
- Size: **8,950,634 bytes** (8.5 MB)
- MD5: **018d5e3f2b984abb9b8ba1e03f801262** — checked against every other `.mp4` already in `~/Downloads` (~75 files), no match — confirmed not a duplicate/wrong-card download.
- `ffprobe`: h264 video + aac audio, **1280x720**, **10.04s**, 24fps — on spec.

## Cut sweep (0.2s greyscale consecutive-frame diff, per FIRE-PLAYBOOK §3)
Frames extracted every 0.2s (0.2s → 9.8s, 49 frames) to
`<scratchpad>/scan/f<t>.png`, downsampled to 160x90 greyscale, mean-abs-diff
between consecutive frames. Median diff = 0.798.

- **4.8s → 5.0s: 14.388 (18.0x median)** — one isolated spike, nothing else close to it before it. **The hard cut is real and correctly placed at ~5s.** PASS.
- 5.0s → 9.4s: sustained elevated diffs, **3.6x–11.7x median throughout**, never dropping back near baseline until 9.4s–9.8s (which reads 1.06x / 0.94x, back to normal). This is NOT the signature of a single cut or of held-camera walking motion — it is continuous elevated frame-to-frame change across the whole second shot.

## Visual review (frames at 0.2s, 2.4s, 4.6s, 5.2s, 7.4s, 9.2s, 9.8s — all in `<scratchpad>/scan/`)

1. **Shot 1 (0–5s) — camera LOCKED, confirmed.** Frames at 0.2s, 2.4s, 4.6s are pixel-identical in framing: wide axis shot straight down the hall, red double doors at far end, Dupe mopping mid-hall beside his cart. At 2.4s the near-right door is open and the old man (dark green leather coat, white hair, silver cane, cream gloves) is standing just inside it — matches the sheet exactly.
2. **Shot 2 (5–10s) — camera NOT locked. FLAGGED.**
   - 5.2s: front-facing medium shot, old man walking toward camera, glass vitrine visible right foreground.
   - 7.4s: **over-the-shoulder shot from BEHIND the old man**, looking down the same hall axis, Dupe visible mid-distance with the mop, red doors far away. This is a materially different camera position than 5.2s, five seconds into an unbroken shot.
   - 9.2s–9.8s: camera has settled back onto the wide central hall axis (same framing family as shot 1), old man has exited frame, Dupe alone mopping, cart visible.
   - Combined with the sustained elevated frame-diff (above), this is a continuous camera move (pan/track/orbit) through shot 2, not a static "locked medium shot from the side" as the prompt specifies. **Violates the sheet's own negative: "no camera move inside a shot."**
3. **The door**: PASS. Far red double doors, one opens, old man enters alone, cane first. Never touches the wall (no wall interaction in this clip at all).
4. **He looks at things**: PASS on content — bronze/vitrine visible in the frame sequence, unhurried and stern in every sampled frame, no smile. (The *camera's* behavior while he does this is the flagged defect above — the content itself is on-brief.)
5. **Dupe / cart / painting face-out**: PASS. Zoomed crop of the cart at 0.2s confirms mop, bucket, cleaning supplies, and a framed abstract painting leaning against the cart's front panel, face out, exactly as specced. Dupe stops mopping and watches the old man in the later frames.
6. **No dialogue**: NOT independently verified. `faster_whisper` is not installed on winbox (`ModuleNotFoundError`) — skipped the transcript per the task's own fallback instruction ("if faster_whisper is missing, say so and skip the transcript"). No visible subtitles/captions/speech-bubble artifacts in any sampled frame.
7. **Exactly two people**: PASS across every sampled frame (old man + Dupe only, no third figure, no duplicate old man, no duplicate Dupe).

## Verdict
**FLAGGED — camera-lock defect in shot 2.** Everything else on the sheet's REVIEW ORDER passes. Per the standing rule, the operator does not self-certify; this goes to the CTO/CEO with the exact prompt and frame paths above.

## Filing
`scripts/gdrive-bridge/upload_fix1.py` failed immediately:
```
missing Drive OAuth vars: GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN
```
Per the task brief, did not attempt any other upload path. File left in place for the CTO to pull over SSH and file as `S3a-FirstCustomer-Fix1.MP4` in `All Scene/Fix-2` (`1rkCQ5SSZeOvyX-0UZXe3OvBtFhObHrkw`):
- Path: `C:\Users\UsEr\Downloads\hf_20260908_193316_ab04071f-379a-474c-8d9e-e3d3ebec258d.mp4`
- Size: 8,950,634 bytes
- MD5: `018d5e3f2b984abb9b8ba1e03f801262`

## Sheet
TAKE LOG appended in `docs/prompts/absence/s3a-fix1-the-first-customer.txt` with the full fire + landing + verdict record, committed on this branch.

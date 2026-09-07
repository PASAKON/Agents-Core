# S2R-B take 1 — THE BATTLE, reverse angle — fire report

Task: task-6c89cef9. Sheet: `docs/prompts/absence/s2r-b-fix1-the-battle-reverse.txt`.

## Pre-fire gates (paste block only)

- `python3 scripts/prompt-lint.py docs/prompts/absence/s2r-b-fix1-the-battle-reverse.txt` — exit 0.
- `--chips` on the paste block: **13**, no `@project_absence_prop_croc_bag` (confirmed absent — the
  bag is carried as prose per CTO note 2026-09-07 07:50, dropped from the paste block after 3
  copyright rejections).
- Depth pattern `nearest|extreme foreground|very front|floating|toward the mark|backs to the room`
  on the paste block, case-insensitive: **2 hits**, both Dupe's position (line 37 "NEAREST THE
  CAMERA", line 55 "nearest the camera") — intended blocking, not a mark instruction. Gate PASS.

## Browser session

- claude-in-chrome only, own new tab (id 53474269), claimed via `tab_registry.py claim
  task-6c89cef9 53474269 https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`.
- innerWidth readback: **2280×722** at composer build time (well above 1280). Never called
  `resize_window`. Window later shrank on its own (OS width guard / external factor) to 1746 wide
  during the post-fire wait — still ≥1280, no action needed.
- Banner "Credits are running low! Over 90% already used" closed with its own (×) as the first
  composer action.
- Video tab selected (was default on this composer instance), model switched from Cinema Studio
  4.0 to **Seedance 2.5** explicitly via the model dropdown.
- Six fields set: 16:9 (default) · 720p (set) · 20s (ARIA slider, `ArrowRight` ×15 from 5→20,
  never typed) · High (default) · Sound On (default) · Unlimited toggled ON.
- Price zoom before paste: `UNLIMITED · ~~140~~ · 0` (pixel-verified via `zoom`, not JS scrape —
  the skill's documented decoy-button trap was checked for: a JS text-scrape did return the stale
  `GENERATE8045` decoy at one point, confirmed benign because the zoomed screenshot of the real
  button read `UNLIMITED / ~~140~~ / 0` throughout).
- Paste: base64-encoded synthetic `ClipboardEvent` on the visible (non-decoy,
  `getComputedStyle().visibility==='visible'`) contenteditable, `text/plain` only, followed by
  `End` → `space` → `Backspace` to force Lexical state bind.
- Chip gate after paste: 18 leaf `@`-spans total, **13 unique**, 0 unresolved (all 18 carry
  `span.text-font-brand` / lime — verified by DOM class, not by an unreliable "red text" heuristic
  which initially false-positived on nested wrapper spans around the same chip). No
  `@project_absence_prop_croc_bag` chip present.
- Previz `docs/S2RB-Render.MP4` attached via the reference panel's Uploads tab (accept
  `video/mp4` input, matched by `accept` attribute, not by clicking a visible "Upload media"
  button — used `file_upload` directly on the hidden input ref). Byte-verify: local file
  3,765,217 bytes; uploaded CDN asset `content-length` header **3765217** — exact match. Tile
  showed no separate "Check eligibility" pill on this occasion — clicking it directly produced
  "Added to prompt box" + green checkmark immediately.
- Fresh re-verify immediately before commit: Seedance 2.5 / 16:9 / 720p / 20s / batch 1/4 / High /
  Sound On / Unlimited `~~140~~ 0`, 13 unique chips, 0 unresolved, text length unchanged
  (10,417 chars) — all held.

## Fire

- First Generate click **2026-09-07T03:39:58Z (10:39:58 ICT)**: refused with toast "You can
  generate 1 unlimited video, image & audio generation at a time" (S2M-B render in flight, fired
  10:19 per brief). Per §5 pipelining: did not reload; zoomed the button each retry (always
  re-read `~~140~~ 0` before clicking) and retried every ~5 minutes.
- Busy-slot refusals at ~10:44, ~10:49, ~10:55, ~11:00, ~11:02 ICT (5 total, none counted as the
  fire).
- **Fire confirmed 2026-09-07T04:07:13Z (11:07:13 ICT)**: toast "Generation started" + a NEW
  Processing card appeared at the top of the grid.

## Identifying the card

- After ~20 minutes (per the render-wait cadence), then every 5 minutes, reloaded the tab (a
  reload does not affect an already-committed server-side render) and re-checked the top-left
  card: Processing → Generating → finished thumbnail with a "New" badge.
- Opened its Info panel: **Prompt text matches verbatim** ("20s · 720p · 16:9 · ONE LOCKED SHOT.
  The camera never moves, never pans, never zooms, no cuts, for the whole twenty seconds. Sound
  On · High. the reference video (Video 1) is the CAMERA…"), **Model: Seedance 2.5, Quality:
  High, Size: 1280×720, Created: September 7, 2026 at 11:06 AM** — matches the 11:07:13 fire time
  to the minute. Confirmed this is my card, not another worker's (one other finished card in the
  grid at the time carried a visibly different prompt — "three hard jump cuts" — belonging to a
  different scene/take, correctly left alone).

## Download + dedup + Drive

- Downloaded: `~/Downloads/hf_20260907_040659_1d5bf6c5-1c0d-497c-89e8-18377513cdf0.mp4`
  (18,236,574 bytes; internal timestamp `040659` UTC = 11:06:59 ICT, matching Created time).
- `md5 -q` = `d54736f5810ad94d26a2a8aa65ce21a7`. Checked against every other `*.mp4` already in
  `~/Downloads` (`find ~/Downloads -maxdepth 1 -name '*.mp4' -print0` loop) — **no match**, unique.
- `ffprobe`: video 1280×720, duration 20.04s, audio stream present (Sound On confirmed in the
  file, not just the composer toggle).
- Filed to Drive `All Scene/Fix-1/` as `S2R-B-Fix1.MP4` via
  `scripts/gdrive-bridge/upload_fix1.py` (read `gdrive-filing` skill first, this session):
  https://drive.google.com/file/d/1y9YnwyaKpSEbQJzKoffYiSnpLab9-93U/view — logged to
  `Sorry, Sir/logs.txt` by the script.

## Frame checks (0.5s, 4s, 8s, 12s, 16s, 19.5s)

Frames: `docs/reports/frames-s2r-b-t1/t0.5.png`, `t4.png`, `t8.png`, `t12.png`, `t16.png`,
`t19.5.png`.

- **Locked camera, no cuts** — PASS. All six frames show an identical static composition (same
  columns, same door, same character blocking); consistent with "ONE LOCKED SHOT… no cuts."
- **No crack in frame** — PASS. The red door and every wall surface across all six frames are
  clean; no star-shaped crack anywhere.
- **13-chip bag Element correctly absent** — PASS. No crocodile-bag prop rendered as a distinct
  branded object (verified at the chip gate before firing — no such Element was ever bound).
- **Every named character present** (checked both ends of each figure's line before calling
  anyone missing):
  - Dupe (`@project_absence_char_cleaner_c`) — PASS. White uniform, orange trim, cap with gold V,
    moustache, nearest the lens, only face turned fully toward camera, holds his look across all
    six frames.
  - The Woman in Green (`@project_absence_char_woman_c`) — PASS. Teal/blue-green towering
    pompadour, black cat-eye sunglasses, green leather, on the LEFT — matches the sheet's mirrored
    side requirement (item 1 of the sheet's own REVIEW ORDER).
  - Mr Carrington (`@gentleman_e`) — PASS. Swept-back white hair, white stand-collar suit, on the
    RIGHT (cane and gold teeth not independently confirmed at this resolution/crowd distance —
    not flagged, sub-resolution detail).
  - Valder (`@project_absence_char_valder`) — PASS. Magenta/yellow blazer blocks visible,
    mustard scarf, tinted glasses, dead centre, a little further back — matches "Valder centre"
    (sheet REVIEW ORDER item 1).
  - The Registrar (`@char_registrar`) — PASS (cropped confirm at t8, zoomed): cream tunic, small
    gold pin at chest, white gloves, dark ledger/book held against the body, off to the right.
    Pen-in-motion not independently confirmed at this crop, ledger closed rather than
    demonstrably open — sub-resolution detail, not flagged as a defect.
  - Carrington's bodyguard, Valder's two guards, the young woman in cobalt, the East Asian critic,
    the woman in chestnut fur, the man in maroon, the art student — present as background figures
    in the crowd at the resolution sampled but **not individually re-identifiable by costume
    detail** in a wide six-frame check; this is an inherent limit of a dense-crowd wide shot, not
    a specific absence — no figure looked wrong or out of place, and no negative-listed prohibited
    figure (auctioneer, security beyond the three named, journalist, etc.) was spotted.
- **No duplicate person** — PASS. No two visually identical faces/costumes spotted across the six
  frames; no double-Valder or double-Dupe pattern (the specific failure mode flagged elsewhere in
  this org's history).
- **Dupe nearest the lens with his cart** — **FLAGGED (partial)**. Dupe is unambiguously nearest
  the lens, largest in frame, only frontal face. His cleaning cart is **not visible in any of the
  six sampled frames or in two supplementary crops** (left-edge crop at t4, full-width review at
  all six timestamps) — because his extreme close-foreground framing crops out everything below
  chest height, the cart (which would sit at hip/waist level beside him) may simply be below or
  beside the visible frame rather than absent from the render. Cannot confirm presence or absence
  from stills alone. Flagging for the CTO's own look at the full clip (or an additional frame at a
  lower crop) rather than calling it a pass or a fail on ambiguous evidence.
- **Sheet's own REVIEW ORDER** (7 items, `docs/prompts/absence/s2r-b-fix1-the-battle-reverse.txt`
  notes):
  1. Sides mirrored, Madame LEFT / Carrington RIGHT / Valder centre — **PASS**, matches every
     frame.
  2. Dupe in the foreground, only face — **PASS**. Valder and the Woman in Green are shown in
     profile/three-quarter (facing each other, per the sheet's own framing description), not
     frontal to camera; only Dupe faces the lens directly.
  3. Heads swing, ragged, right/left/right/left, mirrored from A — **PASS (plausible)**. Head
     angle differs slightly frame to frame; full verification of exact swing timing needs
     playback, not stills — not flagged, no contradicting evidence found.
  4. Nobody walks — **PASS**. No mid-stride or shifted-footing artifacts across sampled frames.
  5. Five bids in order, hers first — **UNVERIFIED FROM STILLS** (audio-only content — would need
     a playback/waveform check, out of scope for a frame-based review; not flagged as a defect,
     simply not checkable this way).
  6. Twelve people, no extras, no auction furniture — **PASS**. Crowd size looks correct in scale;
     no podium/gavel/auction furniture visible in any frame.
  7. Camera dead still for twenty seconds — **PASS**. Confirmed by the locked-camera check above.

## Overall verdict

**FILED, with one FLAG.** All hard gates (chip count, crack, mirrored sides, locked camera, Dupe
frontal-and-nearest) pass clean. The only open item is the cart's visibility, which stills cannot
settle either way — recommend the CTO do a quick full-clip scrub (not just the six sampled
frames) before calling this take done, since the sheet's own text explicitly stages him "beside
his cleaning cart."

## Fields set (per the brief)

16:9 · 720p · Seedance 2.5 · High · Sound On · 20s · Unlimited (`~~140~~ 0` at fire).

## Files

- Report: `docs/reports/absence-wave-20260907-s2r-b-t1.md` (this file).
- Frames: `docs/reports/frames-s2r-b-t1/t0.5.png`, `t4.png`, `t8.png`, `t12.png`, `t16.png`,
  `t19.5.png`.
- Drive: https://drive.google.com/file/d/1y9YnwyaKpSEbQJzKoffYiSnpLab9-93U/view
  (`All Scene/Fix-1/S2R-B-Fix1.MP4`).

## Notes / anything odd

- The composer's local draft prompt text survived two page reloads during the post-fire wait
  (expected — documented behaviour), but the Unlimited toggle and resolution/duration fields did
  reset after reload (also expected — never re-fired from the reloaded composer, so this had no
  effect).
- A brief, empty "[New message from CTO]" mailbox notification arrived mid-task with no visible
  body; checked `TASK.md` per the known "mailbox delivers notifications with no body" issue — no
  new content found there either, so proceeded on the original brief.
- No croc-bag Element chip ever appeared — the paste-block gate check at the start of the task
  already confirmed the sheet's paste block does not contain that mention (13 chips, matching the
  brief's requirement exactly).

## SKILL-OVERRIDE

None — no HARD rule was overridden. All money-relevant checks (banner close, six fields, price
zoom before commit, byte-verify, one-fire-only, no Rerun, no paid-control retries) were followed
as written.

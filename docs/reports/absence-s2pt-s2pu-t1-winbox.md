# S2PT + S2PU take 1 — winbox browser operator report (spawn 2, task-dcaef051)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The Valder Collection No.7")
Chrome device: `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome).

## Blocker from spawn 1 — root cause found and fixed

Spawn 1 (task-d188f5bc) uploaded through the composer's **direct reference-tray
file input** (the one reached straight from the "References" pill / the
`accept="image/*,video/mp4,..."` input embedded in the prompt-box container).
That input creates a `<video>` element bound to a local `blob:` URL that never
progresses past `readyState:0` / `networkState:2` (NETWORK_LOADING) — confirmed
independently in this session across **three readings** (original tab ~45s,
after reload ~10s, fresh tab ~30s), even with the re-encoded low-bitrate previz
(`S2PT-Render.MP4` ~605 kbps, well under the 1.6 Mbps that was the first
suspect). The blob simply never resolves through that input, on this account,
on this page, right now — not a bitrate problem.

**The working path** (per this task's brief, confirmed against
`docs/reports/absence-s2aj-t1-winbox.md` and `.claude/skills/higgsfield-unlimited-gen/SKILL.md`
§"Attaching a VIDEO reference" and §"Video-ref attach on the PROJECT composer"):
click the **"+" icon** left of the composer text box (not the "References"
mode pill) → opens the reference panel (Uploads/Elements/Generations/Liked
tabs) → **Uploads → Videos** sub-tab → its own `<input type=file>` (a *third*
file input on the page, broader `accept` list including `video/*`/`video/webm`)
→ upload there. Verification took ~1–2 minutes (toast "Your upload is being
verified" → real thumbnail in the Uploads grid, sorted "Last created"), matching
the S2AJ report's ~3-minute timing. Clicking the resolved tile fired "Added to
prompt box" directly — no separate hover "Check eligibility" pill appeared for
this tile (it may only show during an intermediate state this session didn't
catch). Attach verified byte-exact: `fetch(video.currentSrc, {method:'HEAD'})`
returned `content-length: 1518291`, matching the local `S2PT-Render.MP4` size
exactly. The reference-tray `<video>` itself stayed at `readyState:0` even
after successful attach — **that is a red herring, not a failure signal**; the
authoritative check is the "Added to prompt box" toast + byte-match, not the
tiny tray thumbnail's own decode state.

**Corrected guidance for the skill**: video-ref uploads on this composer
should go through the "+" → Uploads panel path, not the composer's own direct
file input. Flagging for the CTO to fold into
`.claude/skills/higgsfield-unlimited-gen/SKILL.md`.

## S2PT · "THE TOUR, TOGETHER" — take 1

- Sheet lint: `python scripts/prompt-lint.py docs/prompts/absence/s2pt-fix2-the-tour-together.txt` → clean (exit 0). `--chips` → EXPECTED 7 unique Element chips.
- Previz: `docs/S2PT-Render.MP4` (1,518,291 bytes, h264, 1280×720, 24fps, 20.000s) attached as Video 1, byte-verified as above.
- Chip binding: **7/7 unique** Element chips bound (`span.text-font-brand` leaf spans starting `@`) — `@project_absence_char_valder`, `@gentleman_e`, `@project_absence_char_guard_private_v2`, `@project_absence_char_guard_valder_two`, `@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`, `@loc_hall_big_e` (13 total mention spans — sheet references some names in both POSITION MAP and REFERENCES sections, matching the S2AJ pattern). **0 `.text-icon-error` chips.** 8 tray thumbnails visible (1 video + 7 elements).
- Text entry: pasted the exact `PASTE FROM HERE`…`PASTE STOPS HERE` block (9,656 bytes, base64-decoded to avoid transcription errors) via synthetic `ClipboardEvent` into the sole visible (non-decoy) contenteditable, followed by `End` → `space` → `Backspace` to force Lexical state sync. Only one visible contenteditable was present (no decoy ambiguity this session).
- Settings immediately before Generate: Seedance 2.5 · References · 16:9 · 720p · 20s · batch **1/4** · High · Sound **On** · window `1920×911` (well above the 1280 mobile-breakpoint floor). Unlimited switch `data-state="on"`. Generate button text (re-read the instant before click): `UNLIMITED / 140 / 0` — struck price then zero, correct.
- Grid check before fire: no "processing/generating/queued" text anywhere; only the two pre-existing `NSFW · Credits refunded` cards from the prior S2R-F take.
- **Fired 2026-09-09 22:21:5x ICT.** Asset count ticked **755 → 756** immediately after click, confirming exactly one job queued.
- Zero cost: Unlimited struck-140→0 the whole session; no priced control was clicked at any point.

### Render wait

- Fired 22:21:32 ICT. Polled with fresh, position-verified tabs (never the
  long-lived firing tab) at ~10-min cadence: Processing at +10min and +20min,
  advanced to Generating by +30min, **DONE at +40min** — "New" badge, real
  thumbnail, no moderation-rejection card. Total render ≈ 40 minutes.

### Download

- Clicked the card's download icon. Chrome saved it automatically (no
  "Rights verification required" gate appeared).
- **Path**: `C:\Users\UsEr\Downloads\hf_20260909_152132_27feff29-f1be-4d42-adaa-c60322646b71.mp4`
- **Size**: 29,613,762 bytes
- **MD5**: `7b8778a39ecabf5c193368775c4420b3`
- **Asset id**: `27feff29-f1be-4d42-adaa-c60322646b71`
- `ffprobe`: h264 1280×720 @24fps + aac audio track, duration 20.04s — matches the 20s/720p/16:9/Sound-On spec fired.
- Project asset count: 755 (pre-fire) → 756 (immediately after Generate, held through completion) — confirmed up by exactly 1.

### Frame check (ffmpeg, scale=640 wide, `docs/reports/frames-s2pt-t1/`)

Extracted at 1.5, 6, 10, 13, 16, 19.5s, plus two zoomed crops at 13s to resolve
an ambiguity (below). Described honestly — **not self-certified**; full
playback review is the CTO's.

- **What held**: ONE continuous lateral track with no visible cut across all
  six samples — camera stays square/locked, columns and artworks slide past
  behind a party that holds its screen position, matching the "no pan, no
  zoom, no reframing" spec. The mustard armchair on its blue rug enters at
  bottom-left by t13s and sits level with the party by t16s, and the party
  does not stop for it through t19.5s — matches the beat map exactly. Valder
  (rainbow-panelled blazer, mustard scarf) and Carrington (white suit, cane,
  swept-back white hair) walk adjacent at the front the whole way, essentially
  indistinguishable by a fraction of a step in a still frame, which is
  consistent with "at his shoulder, half a step back." The two navy-uniformed,
  peaked-cap guards (one visibly taller/thinner, one shorter/heavier) walk
  together behind them. Dupe (white uniform, cap) pushes the cart (bucket,
  mop, bottles, folding ladder, upright painting) well back from the group in
  every frame, hands on the handle, nothing carried — no separation defect.
- **DEFECT — likely a duplicated bodyguard (extra person)**: every sampled
  frame (t1.5s through t19.5s) shows **two** distinct heavily-built Black men
  in dark/black suits with sunglasses, at two different, consistently-held
  screen depths — one positioned right after Valder/Carrington and just ahead
  of the two guards (crop:
  `docs/reports/frames-s2pt-t1/t13s-zoom-midgroup.png`), and a second,
  separate one further back near the cart, this one with **white gloves
  clearly visible** (crop: `docs/reports/frames-s2pt-t1/t13s-zoom-rear.png`).
  Because the shot is a locked lateral track (subjects hold their frame
  position for the full 20s), both figures are visible simultaneously in
  every single-frame sample — this rules out "same person, camera moved" and
  confirms two separate rendered individuals. The sheet's POSITION MAP names
  only **one** bodyguard (`@project_absence_char_guard_private_v2`, referenced
  once) and the CRITICAL NEGATIVES explicitly ban a seventh person and a
  repeated face/build. This reads as the same class of cast-inflation defect
  the sheet's own notes call out as the known risk for this cast ("S2P take 1
  bound thirteen and lost Valder") — except here the 7/7 unique-chip binding
  and 0 error-chips were verified clean before firing, so this looks like a
  **generation-time duplication**, not a binding/chip problem. **Flagging for
  CTO review — this may warrant a retake**, but per the brief I am not
  self-certifying or re-firing on my own judgment.
- Total on-screen headcount across all frames: 7 distinct people (Carrington,
  Valder, 2× bodyguard-like figure, 2 guards) + Dupe with cart = 8, against
  the sheet's spec of 6 people + Dupe = 7 total.

## S2PU · "ARE YOU FOLLOWING US" — take 1

S2PT left the slot (finished) at +40min, so per the brief's "ONE SLOT" rule S2PU is now being set up and fired.

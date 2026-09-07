# SC5 take 1 — THE CROWD AT THE DOORS — 2026-09-07

STATUS: **FLAGGED** — one fire, rendered clean (no copyright/NSFW rejection),
but two REVIEW ORDER items fail and one severe unlisted defect (location
continuity break in shots 2-3) is present. Filed per instruction regardless
of verdict. One fire per task — not re-fired.

## Lane switch (mid-task correction from CTO)

Original task brief specified UNLIMITED/FREE lane, zero paid actions. Mid-task
the CTO sent an explicit RESUME instruction switching this fire to the
**CREDIT lane**, quoting the CEO ("Credit ยิงได้เลย ไม่ต้องรอ ยิงผ่าน Fastlane
ได้เพราะใช้ Credit"), because Unlimited generations were paused site-wide by a
Higgsfield subscription payment failure (confirmed via the "Payment failed...
Unlimited generations are paused" banner on `/me/settings/subscription`). CTO
named an explicit price ceiling (~52 credits) and required: read balance
before, one click, no retry, read balance after, report both, stop on any
protected-content toast. Followed exactly — see Cost section.

## Setup verification

- innerWidth readback: 1440 (>=1280 threshold met).
- "Credits are running low!" banner: closed via its own (x) as the first
  composer action (had to be re-closed after a tab reload picked the composer
  state back up).
- Video mode confirmed (5s duration + Sound On + Cinema Studio 4.0 badge
  visible by default), model switched explicitly from Cinema Studio 4.0 to
  Seedance 2.5 via the model picker.
- Six fields verified twice (mid-setup and immediately before the Generate
  click, via zoomed screenshot): 16:9 · 720p · Seedance 2.5 · 8s · High ·
  Sound On. Duration set via the ARIA slider (`ArrowRight` x3 from the
  default 5s landed on 10s — overshoot — corrected with `ArrowLeft` x2 back
  to 8s, confirmed by zoomed readback of the slider's own label, never typed).
- Unlimited toggle deliberately left OFF (credit lane) — confirmed by the
  toggle's circle sitting on the left/off side and the price field still
  showing a live number, not `0`.
- Price zoom immediately before the Generate click: `GENERATE · ~~56~~ 52`
  credits — matches the CTO's ~52 ceiling.
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  focused contenteditable, then End -> space -> Backspace tap to force the
  Lexical chip binding.
- Chip gate: 2/2 unique `@` chips lime (`span.text-font-brand`, no nested
  span, starts with `@`), 0 unresolved/red `@` text — confirmed
  programmatically: `@project_absence_loc_exterior_front`,
  `@project_absence_char_guard_valder_six`. Matches
  `prompt-lint.py --chips` exactly.
- Gate greps (paste block only, via `awk` PASTE FROM/STOPS HERE extraction):
  depth/gaze pattern `nearest|extreme foreground|very front|floating|toward
  the mark|backs to the room` -> 0 matches; `HARD CUT` (exact case) -> 2
  matches (Shot Two, Shot Three); `prompt-lint.py` exit 0.
- Previz: NONE, per the sheet — no reference video attached, References panel
  only held the 2 Element chips.

## Fire

Fired once at 2026-09-07 19:09 ICT (12:09:07 UTC). Verified by the
"Generation started" toast AND a new Processing card (spinner) at the top of
the grid, asset count 701->702.

## Render

~24 minutes wall-clock on the credit lane (fired 19:09 ICT, found finished on
the 19:33 ICT poll). Consistent with the playbook's credit-lane precedent
(SC3 credit-lane render: 22 min on 2026-09-07).

No "Rejected due to copyright restrictions", no NSFW/sensitive-content
banner, no credits-refunded banner.

## Card identification

Two cards were "No status"/Processing near this fire time. The first one
opened (top-left grid slot on the next poll) had a superficially matching
opening line ("8s · 720p · 16:9 · THREE SHOTS, hard cut at 3s and again at
6s...") but its References chip was `@project_absence_loc_hall_big_d` (THE
GALLERY HALL) and its Created time was 7:03 PM — **not mine**, a different
operator's card sharing the same boilerplate shot-structure sentence. Caught
before download by reading the full References line, not just the opening
sentence (per the playbook's known "top card is often another worker's clip"
trap).

The correct card: References chip `@project_absence_loc_exterior_front`,
Created **September 7, 2026 at 7:09 PM** (matches fire time exactly), Model
Seedance 2.5, Quality 720p, Bitrate High, Size 1280x720.

## Download + Drive

- Downloaded via the card's own Download button.
- File: `hf_20260907_120907_ae35f4d2-917f-4700-8444-d884d809ca77.mp4` — the
  filename timestamp `120907` = 12:09:07 UTC = 19:09:07 ICT, matching the
  fire time exactly.
- md5 `fec61ca00711e8fea4f44c13439fb76c` — checked against every other mp4
  already in `~/Downloads` (60+ files); no match, confirmed unique/correct
  card, not a duplicate of a prior take.
- `ffprobe`: video 1280x720 h264, duration 8.04s, audio stream present (aac)
  — matches spec.
- Filed to Drive `All Scene/Fix-1/SC5-Crowd-Fix1.MP4`:
  https://drive.google.com/file/d/1mGvs0SNrJ340UZ1cEuGoNdQkLaxmm1aa/view
  via `scripts/gdrive-bridge/upload_fix1.py` (appended the `logs.txt` line
  with the FLAGGED summary in the note).

## Frame checks (0.5s, 2.5s, 3.5s, 5.5s, 6.5s, 7.5s)

Frames: `docs/reports/frames-sc5-t1/sc5-t1_0.5s.png`, `_2.5s.png`, `_3.5s.png`,
`_5.5s.png`, `_6.5s.png`, `_7.5s.png`. Close-up crops of the guard line and
both frame edges also saved (`crop_0.5_*`, `crop_2.5_*`) to support the
guard-count and no-repeated-faces checks below.

### REVIEW ORDER (sheet's own order, item 0 first)

0. **NO REPEATED FACES** — PASS (with caveat). Scanned both left and right
   edges of the 0.5s and 2.5s wide frames (Shot 1, the only shot wide enough
   to judge a crowd) at 2x crop zoom. No two figures read as an identical
   face/coat pairing. Caveat: the crowd in the wide shot is distant and
   motion-blurred, so a subtle clone could be missed at this resolution —
   flagging as PASS-with-low-confidence rather than a clean PASS.
1. **THE LIGHT** — **FLAGGED**. Shot 1 (0-3s, the establishing wide of the
   forecourt) still shows a clear daytime-blue sky with white clouds — not
   the amber/rose late-afternoon sky the CEO explicitly required, even
   though the building face does carry warm golden highlights and figures do
   cast long raking shadows. This is exactly the sheet's named failure
   condition: "Midday blue like the plate = the one instruction the CEO gave
   for this shot has failed." Shots 2 and 3 (3-8s), by contrast, DO show a
   correct warm amber-to-rose sunset sky with lamps/string-lights lit — so
   the light is inconsistent across the clip, correct in the back two-thirds
   and wrong in the establishing shot that most visibly frames the sky.
2. **SIX GUARDS, covering doors AND both flanks** — **FLAGGED**. Zoomed crop
   of Shot 1's door line shows exactly **5** guards standing shoulder to
   shoulder directly in front of the doors, arms linked/outstretched — not
   6. No guard is visibly positioned at a separate left-flank (wall) or
   right-flank (ramp rail) position as the brief specifies ("four... across
   the top step... one at the left flank... one at the right flank"); all
   visible guards are bunched at the center door line and the crowd wraps
   around both sides unimpeded. This matches the sheet's own flag condition:
   "Five or seven, or a line that breaks, = flagged." Shots 2-3 show 2
   guards in close-up (consistent with "two of the six" as scripted for Shot
   Three) but cannot resolve the total-count question.
3. **20-30 PEOPLE, reads as a crush** — PASS. The wide shot's crowd packs
   the steps and forecourt densely; reads as a crush, not a queue.
4. **NOBODY GETS IN** — PASS (with caveat). No one is shown past the guard
   line in any sampled frame; the revolving glass doors are visible and shut
   in Shot 1. Cannot independently confirm the doors stay shut for the full
   8s because Shots 2-3 change background entirely (see unlisted defect
   below) and never show the doors again.
5. **TWO HARD CUTS at 3s and 6s, angle different either side** — PASS
   structurally. Shot 1 (wide forecourt) -> Shot 2 (close crowd/guard-back
   angle) -> Shot 3 (tight two-guard chest-up portrait) are three clearly
   distinct angles/framings with two hard cuts at the correct timestamps.
6. **NO READABLE TEXT anywhere** — PASS. Only the gold "V" mark appears (on
   the building facade and embroidered on guard uniform chests), which is
   the location's/character's own established branding per the reference
   plates, not a banner/placard/protest sign/headline/press badge/caption.
7. **Sound is voices with no words** — NOT VERIFIED FROM FRAMES. Audio track
   confirmed present (aac) via `ffprobe`, but content was not
   listened to/transcribed — this item needs an audio pass, not a still-frame
   check, and was not performed.

### Unlisted but severe defect: location continuity break

Not one of the sheet's 8 REVIEW ORDER items, but material enough to flag on
its own: **Shots 2 and 3 (5 of the clip's 8 seconds) are not set at the
museum forecourt at all.** The background behind the guards in both shots is
an open field/park at dusk — string lights along an avenue of trees, a
distant crowd stretching into the distance, no cream-stone building, no
chromium canopy, no terrazzo, no revolving doors. This is a complete
departure from the `@project_absence_loc_exterior_front` reference plate for
over half the render, even though the guards' uniforms and the crowd's
"press mob" energy are otherwise on-brief.

## Cost

Credit lane, single click, never retried. Balance before **357/6000**
monthly credits, balance after **305/6000** — spent exactly **52** credits,
matching the CTO's stated ceiling exactly. No protected-content toast
appeared; no second click was needed or attempted.

## Verdict

FLAGGED, not a clean take. Two of seven REVIEW ORDER items fail (light
consistency, guard count/flank coverage), one item is unverifiable from
stills (sound), and a severe unlisted location-continuity break affects
shots 2-3. Filed to Drive regardless per instruction ("file the take
whatever the verdict"). Recommend a re-fire on a future pass with tighter
anchoring to the exterior plate for all three shots, and consider stating
"exactly six, four across the doors plus one at each flank, all visible in
Shot One" even more explicitly if 5-guard undercounts recur.

## Notes for reviewer

- The card-identification trap from the playbook (shared boilerplate opening
  sentence across different scene prompts) was live again here — caught by
  reading the References chip line, not just the prompt's first sentence.
  Worth adding "check the References chip, not just the opening line" to the
  playbook's identification guidance.
- Render time (~24 min) was well inside the credit-lane norm observed
  earlier today (SC3: 22 min) — no cancellation was ever close to warranted.
- Did not attempt an audio transcription/listen pass — flagging item 7 as
  open rather than guessing a verdict.

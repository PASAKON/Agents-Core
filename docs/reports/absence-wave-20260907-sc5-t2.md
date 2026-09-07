# SC5 take 2 — THE CROWD AT THE DOORS — 2026-09-07

STATUS: **FLAGGED** — one successful fire (Unlimited/free), rendered clean (no
copyright/NSFW rejection). Guard count fixed (6/6, was 5/6 on take 1) and Shot
Three's location fixed, but guards still bunch at the doors with no flank
coverage, Shot One's sky is still not sunset, and Shot Two still breaks
location continuity (open field, not the forecourt). Filed per instruction
regardless of verdict. One fire per task — not re-fired.

## Setup verification

- innerWidth readback: 1440 (>=1280 threshold met), confirmed at session
  start and unaffected after the shared window's OS auto-resize mid-session
  (viewport briefly moved to 1568x760, still >=1280).
- "Credits are running low! Over 90% already used" banner: closed via its own
  (x) as the first composer action.
- Composer opened already in Video mode (Seedance 2.5) with fields already
  matching the brief on load — no accidental Image-mode fire.
- Six fields verified via DOM text extraction and zoomed screenshot
  immediately before the Generate click: **Seedance 2.5 · 16:9 · 720p · 8s ·
  High · Sound On**.
- Unlimited toggled ON explicitly (was off on page load); zoomed screenshot
  confirmed `UNLIMITED · ~~56~~ 0` — zero digits — before every Generate
  click, including the retries.
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  focused contenteditable, then End -> space -> Backspace tap to bind the
  Lexical chips.
- Chip gate: 2/2 unique `@` chips lime (`span.text-font-brand`, no nested
  span, starts with `@`), confirmed programmatically:
  `@project_absence_loc_exterior_front`,
  `@project_absence_char_guard_valder_six`. Matches `prompt-lint.py --chips`
  exactly. Both also showed as bound reference thumbnails at the top of the
  composer.
- Gate greps (paste block only, via `awk` PASTE FROM/STOPS HERE extraction):
  depth/gaze pattern `nearest|extreme foreground|very front|floating|toward
  the mark|backs to the room` -> 0 matches; `HARD CUT` (exact case) -> 2
  matches (Shot Two, Shot Three); `prompt-lint.py` exit 0.
- Previz: NONE, per the sheet — no video reference attached, References panel
  only held the 2 Element chips.

## Fire

First Generate click (2026-09-07 ~20:50 ICT) was refused with the toast "You
can generate 1 unlimited video, image & audio generation at a time" — the
Unlimited slot was occupied by SC4 take 2 (fired 20:31 per the task brief).
Composer was left fully built and the Generate button was retried every ~5
minutes (5 refusals total), re-verifying the zoomed `UNLIMITED · 0` price
each time, per playbook §5 pipelining. On the 6th attempt the slot freed and
the fire succeeded.

**Fired at 2026-09-07T14:07:27Z = 21:07:27 ICT.** Verified by the "Generation
started" toast AND the asset count moving 703->704 in the same action. A
subsequent poll (fresh tab) showed a single new spinner/Processing card at
the top of the grid with no other pending card — consistent with the SC4
take 2 slot having freed just before this fire.

## Render

~40 minutes wall-clock (fired 21:07 ICT, found rendered on the ~21:47 ICT
poll — the spinner was gone and a real thumbnail had replaced it). Within
the "free-lane renders ran 45-46 min this evening" range named in the task
brief. No "Rejected due to copyright restrictions", no NSFW/sensitive-content
banner, no credits-refunded banner.

Background `sleep` waits were killed twice by the harness's low-memory
guard during the poll cycle; per the playbook ("poll anyway" if a background
sleep is killed), each kill was followed by an immediate poll rather than a
retry-sleep.

## Card identification

Opened the card via its `...` menu -> Open, which surfaced the Info panel:

- Prompt (first line): "8s · 720p · 16:9 · THREE SHOTS, hard cut at 3s and
  again at 6s. Every shot is LOCKED — no pan, no tilt, no zoom, no handheld,
  no drift inside a shot. Sound On · High." — matches the pasted block
  exactly.
- **Created: September 7, 2026 at 9:07 PM** — matches the fire time
  (21:07:27 ICT) exactly.
- Model: Seedance 2.5, Quality: 720p, Bitrate: High, Size: 1280x720.

Confirmed correct card before downloading.

## Download + Drive

- Downloaded via the card's own Download button (Info panel -> Download).
- File: `hf_20260907_140716_e52c4b68-fd5c-496c-a432-17ac6b734217.mp4` — the
  filename timestamp `140716` = 14:07:16 UTC = 21:07:16 ICT, matching the
  fire time to the second.
- md5 `eee2a84d17eba5f8eb0910ee79b9a5f5` — checked against every other mp4
  already in `~/Downloads` (82 files, baseline snapshot taken before the
  fire, including take 1's `Sorry sir THE VALDER Draft 2.mp4` mega-file and
  every prior `hf_*` clip); no match, confirmed unique/correct card, not a
  duplicate of a prior take.
- `ffprobe`: video 1280x720, r_frame_rate 24/1, duration 8.04s — matches
  spec exactly.
- Filed to Drive `All Scene/Fix-1/SC5-Crowd-Fix1-take2.MP4`:
  https://drive.google.com/file/d/12NOlobR_8BSC1QYsHVtOEV2rj55OliIv/view
  via `scripts/gdrive-bridge/upload_fix1.py` (appended the `logs.txt` line
  with the FLAGGED summary in the note).

## Frame checks (0.5s, 2.5s, 3.5s, 5.5s, 6.5s, 7.5s)

Frames: `docs/reports/frames-sc5-t2/t0.5.png`, `t2.5.png`, `t3.5.png`,
`t5.5.png`, `t6.5.png`, `t7.5.png` (the last is a fade-to-black hold at the
very end of the clip — `t7.0.png` and `t7.9.png` were pulled as backups and
show the same content as `t6.5.png`, confirming the fade rather than a
missing frame). Zoomed crops of the guard line and both frame edges also
saved (`t0.5_guards_zoom.png`, `t0.5_sky_zoom.png`, `t0.5_fullwidth_zoom.png`,
`t0.5_leftedge.png`, `t0.5_rightedge.png`, `t2.5_leftedge.png`,
`t2.5_rightedge.png`).

### REVIEW ORDER (sheet's own order, item 0 first)

0. **NO REPEATED FACES** — PASS (with caveat). Scanned both left and right
   edges of the 0.5s and 2.5s wide frames (Shot 1, the only shot wide enough
   to judge a crowd) at zoomed crop. No two figures read as an identical
   face/coat pairing. Caveat: edge figures are motion-blurred and partly
   backs-to-camera, so a subtle clone could be missed at this resolution —
   PASS-with-low-confidence rather than a clean PASS.
1. **THE LIGHT, in all three shots including the opening wide** —
   **FLAGGED, same failure as take 1**. Shot One's sky (`t0.5_sky_zoom.png`)
   is a flat, uniform dusk blue-grey with no amber/rose gradient and no
   gold-lit cloud, even though the building face itself does carry warm
   golden highlights and long raking shadows (the light *on the building* is
   right; the *sky* is not). Shot Two (3.5s) and Shot Three (5.5s/6.5s/7.0s)
   both show a correct, strong amber-to-rose sunset sky with a visible sun on
   the horizon — so exactly the sheet's named check-first condition recurs:
   "Take 1 got shots 2-3 right and left shot one under a midday blue sky...
   check the wide first."
2. **COUNT THE GUARDS IN THE WIDE — there must be SIX** — count is correct
   this time (**PASS on count**) but the **placement fails
   (FLAGGED on flank coverage)**. Zoomed crop of the door line
   (`t0.5_guards_zoom.png`, `t0.5_fullwidth_zoom.png`) shows exactly **6**
   guards in navy uniform with the gold V, all standing shoulder to shoulder
   directly in front of the glass doors. None is positioned at the far-left
   wall (where the steps meet the wall, next to the small alcove door
   visible at the left edge) and none is positioned at the far-right ramp
   rail (visible at the right edge) — the entire line is bunched centrally,
   spanning roughly the doorway width only, not the "full width of the
   entrance from the wall on the left to the rail on the right" the sheet
   specifies. This is the sheet's exact flag condition applied to a
   different failure mode than take 1: take 1 undercounted (5) with no
   flank coverage; take 2 has the correct count (6) but still no flank
   coverage.
3. **20-30 PEOPLE, reads as a crush** — PASS. The wide shot's crowd packs
   the steps and forecourt densely, with clear edge-runners at the wall and
   ramp; reads as a crush, not a queue.
4. **NOBODY GETS IN. Glass doors shut behind the line for all 8 seconds** —
   PASS. Doors are visible and closed (revolving-door glass panel, static
   reflection) in Shot One (0.5s), and visible and closed with the sunset
   reflected in the glass in Shot Three (5.5s, 6.5s, 7.0s). Shot Two's
   background does not show the doors at all (see location defect below),
   so door state cannot be independently confirmed for that 3-second window,
   but no frame shows anyone past the line.
5. **TWO HARD CUTS at 3s and 6s, angle different either side** — PASS. Shot
   One (wide forecourt, 0-3s) -> Shot Two (crush close-up between two guards'
   shoulders, 3-6s) -> Shot Three (tight two-guard chest-up portrait, 6-8s)
   are three clearly distinct angles/framings with two hard cuts at the
   correct timestamps.
6. **NO READABLE TEXT anywhere** — PASS. Only the gold "V" mark appears (on
   the building facade and embroidered on guard uniform chests/caps), which
   is the location's/character's own established branding per the reference
   plates, not a banner/placard/protest sign/headline/press badge/caption.
7. **Sound is voices with no words** — NOT VERIFIED FROM FRAMES. Audio
   content was not listened to/transcribed as part of this still-frame
   check.

### Unlisted but severe defect: Shot Two location continuity break (repeat of take 1, partial)

Take 1 broke location continuity in **both** Shots Two and Three. Take 2
fixes **Shot Three** (correctly shows the museum's glass doors and cream
stone, guards in front, sunset visible in the door's reflection — see
`t5.5.png`/`t6.5.png`) but **Shot Two still fails**: the background behind
the crush of hands/phones/cameras (`t3.5.png`) is an open plaza/field at
sunset with a distant dome-shaped structure and rolling hills on the
horizon — no cream stone, no chromium canopy, no terrazzo, no glass doors.
This is a straight repeat of the sheet's REVIEW ORDER item 1b ("Take 1 put
shots 2-3 in an open field at dusk") for one of the two previously-broken
shots.

## Verdict

**FLAGGED**, not a clean take, but a partial improvement over take 1:
- Guard count: FIXED (5 -> 6).
- Guard flank coverage: still FLAGGED (bunched at doors both times).
- Shot One sky: still FLAGGED (flat blue-grey, not sunset).
- Shot Two location: still FLAGGED (open field, not the forecourt).
- Shot Three location: FIXED (open field -> correct museum doors).
- Crowd size/crush, hard cuts, doors shut, no readable text: PASS on both
  takes.

Filed to Drive regardless per instruction ("file the take whatever the
verdict"). Recommend a take 3 that (a) states the flank positions as
physical distances from named landmarks even more explicitly ("touching the
wall", "touching the rail") since correct headcount alone did not produce
spread, and (b) locks Shot Two's background the same way Shot Three's now
locks correctly — possibly by naming the same "glass doors and gold V
directly behind the crush" framing explicitly for Shot Two too, since Shot
Three's tighter framing on the doors seems to be what made its location
anchor correctly.

## Notes for reviewer

- The shared Chrome window auto-resized mid-poll (another operator's tab
  interaction, per playbook's noted OS-clamp behavior) — innerWidth stayed
  >=1280 throughout (1440 before, 1440 after), so this did not affect
  eligibility or trigger the mobile layout; no action was needed beyond
  re-reading innerWidth after noticing the layout shift.
- Two background polling waits were killed by the harness's low-memory
  guard; each was followed by an immediate poll per the playbook's "poll
  anyway" guidance rather than a blind retry-sleep.
- Did not attempt an audio transcription/listen pass — flagging item 7 as
  open rather than guessing a verdict, consistent with take 1's report.

# SC5 take 3 — THE CROWD AT THE DOORS — 2026-09-07/08

STATUS: **FLAGGED** — one successful fire (Unlimited/free), rendered clean (no
copyright/NSFW rejection). Shot One's sunset light, the six-guard grouping
(one alone at the wall, four together, one alone at the rail), crowd
size/crush, hard cuts, closed doors, and no-readable-text all PASS this take —
a clean sweep on the three defects named in the brief for takes 1-2 (sky,
guard bunching) **except** Shot Two's location, which still breaks continuity
in a new way (open ground with stadium floodlights, not the museum forecourt).
Filed to Drive per instruction regardless of verdict. One fire — not re-fired.

## Setup verification

- innerWidth readback: 1400 (>=1280 threshold met), confirmed before touching
  the composer. Window was never resized per this task's explicit instruction.
- "Credits are running low! All credits used" banner: closed via its own (x)
  as the first composer action.
- Switched to Video tab, then explicitly selected model **Seedance 2.5**
  (composer defaulted to Cinema Studio 4.0 on load).
- Six fields verified via zoomed screenshot immediately before Generate:
  **Seedance 2.5 · 16:9 · 720p · 8s · High · 1/4 · Sound On**. Duration set via
  the ARIA slider (click thumb to focus, `ArrowRight` x3 from the 5s default
  to 8s), verified via `aria-valuenow="8"` before trusting the visible label.
- Unlimited toggled ON explicitly (after the six fields, since setting
  duration is known to reset it); zoomed screenshot confirmed
  `UNLIMITED · ~~56~~ 0` — struck-through price then zero — immediately
  before the click.
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  filtered-for-`visibility:visible` contenteditable (the decoy editor
  excluded), then `End` -> `space` -> `Backspace` tap to bind the Lexical
  chips. Verified first/last 80 characters of `innerText` (9,460 chars)
  matched the source paste block exactly.
- Chip gate: 2/2 unique `@` chips lime
  (`[contenteditable] span.text-font-brand`, no nested span, starts with
  `@`): `@project_absence_loc_exterior_front`,
  `@project_absence_char_guard_valder_six`. Matches `prompt-lint.py --chips`
  exactly. Both reference thumbnails zoomed individually before firing — no
  warning triangles on either.
- Gate greps (paste block only, via `awk` PASTE FROM/STOPS HERE extraction,
  per the narrowed FIRE-PLAYBOOK.md §0 pattern as of 2026-09-08): banned
  depth/gaze pattern -> 0 matches; `NO WIDER THAN THE RED DOOR` -> 0 matches
  (not a wall-POV sheet, expected); `HARD CUT` (exact case) -> 2 matches
  (Shot Two, Shot Three); `prompt-lint.py` (no flags) exit 0. All four gates
  matched the task brief's stated expectation exactly — no mismatch, no
  adjudication needed.
- Previz: NONE, per the sheet — no video reference attached.

## Fire

**Fired at 2026-09-07T20:27:58Z = 2026-09-08T03:27:58 ICT.** Verified by the
"Generation started" toast and a new spinner/Processing card at the top of
the grid (asset count 712 -> 713).

## Render

~35 minutes wall-clock. Polled on the playbook's 20-min-then-5-min cadence
(background `sleep` via `run_in_background`, checked on each wake — no
message sent while rendering, per "a poll is not a report"): still
Processing at 20, 25, 30 min; landed by the 35-min check (real thumbnail with
a "New" badge had replaced the spinner). Within the "free-lane renders ran
30/30/39/46 min tonight" range named in the brief. No NSFW/rejected/
credits-refunded banner.

## Card identification

Opened the card's preview modal (`?preview=d1d5e5c3-e96b-4556-9e3c-a520d034e24b`)
and read the Info panel:

- Prompt (first line): "8s · 720p · 16:9 · THREE SHOTS, hard cut at 3s and
  again at 6s. Every shot is LOCKED — no pan, no tilt, no zoom, no handheld,
  no drift inside a shot. Sound On · High." — matches the pasted block.
- **Created: September 8, 2026 at 3:27 AM** — matches the fire time
  (03:27:58 ICT) to the minute.
- Model: Seedance 2.5, Quality: 720p, Bitrate: High, Size: 1280x720.

Confirmed correct card before downloading.

## Download + Drive

- Downloaded via the preview modal's Download button.
- File: `hf_20260907_202742_b223d09c-0fdb-4586-a766-0b0ba5260070.mp4` — the
  filename timestamp `202742` = 20:27:42 UTC = 03:27:42 ICT, matching the
  fire time to the second.
- md5 `f0dde9a5af78867d28d310e2274c2f48` — checked against every other mp4
  already in `~/Downloads`; no match against any existing file, confirmed
  unique/correct card, not a duplicate of a prior take or another worker's clip.
- `ffprobe`: video h264 1280x720, audio aac present, duration 8.04s —
  matches spec exactly.
- Filed to Drive `All Scene/Fix-1/SC5-CrowdAtDoors-Fix1.MP4` (scene name only,
  per the brief's explicit filename — no take number, no verdict):
  https://drive.google.com/file/d/1vAAEF3nPb6owWOg1vq1E-lt88UPJuTMz/view
  via `scripts/gdrive-bridge/upload_fix1.py`, which also appended the
  `logs.txt` line on the Sorry, Sir project log.

## Frame checks

Frames pulled at 0.5s, 2.5s, 3.2s, 5.0s, 7.0s, 7.9s
(`docs/reports/frames-sc5-t3/t*.png`), plus a cropped top-band zoom of the
guard line and a cropped crowd band, both at 0.5s.

1. **THE SKY IN SHOT ONE (0.5s and 7s check, named as the item that failed
   twice)** — **PASS, no flat blue-grey.** Shot One is deliberately framed
   LOW and CLOSE per the sheet's rewrite — heads and raised arms fill the
   bottom two-thirds, and the building/canopy fill the rest of the frame at
   both 0.5s and 2.5s, leaving **no open-sky pixels in frame at all** to
   directly judge as "sunset-coloured." What IS judgeable is the light
   itself: low warm-gold directional light raking across the cream stone,
   long cast shadows from every figure, warm highlights on the chromium
   canopy and columns — consistent with a low sun, not the flat midday
   blue-grey that failed takes 1 and 2. Shot Three (6-8s, closest thing to a
   "7s" frame since the clip is 8.04s) shows the same warm gold key light on
   the guards' faces and the cream stone visible between them, doors
   reflecting dark glass with no visible sky slice either. **Verdict: the
   defect that failed twice (flat blue-grey sky) does not recur — the light
   throughout reads sunset — but neither frame actually contains an open sky
   pixel to confirm "amber" directly, since the tighter framing that fixed
   the sky-copy defect also removed the sky from view.**
2. **SHOT TWO'S BACKGROUND — is the museum's stone/canopy behind the crowd,
   on the same forecourt?** — **FLAGGED, still broken, new failure mode.**
   `t3.2.png` and `t5.0.png` (both inside the 3-6s window) show, behind the
   two guards' shoulders in the foreground: an open sky with a
   pink/orange sunset gradient and a visible sun near the horizon, two
   **stadium-style square floodlight rigs** on poles, ordinary trees, and a
   hazy distant city skyline with scattered lights. There is **no cream
   stone, no chromium canopy, no terrazzo, no glass doors, no gold V** —
   this is an open outdoor ground, not the museum forecourt. The sunset
   itself renders beautifully here (better than Shot One, ironically), but
   the location is wrong. **This matches the CTO's live diagnosis
   mid-review: the shot asks the camera to stand beside the guard line
   looking DOWN the steps into the crush while ALSO keeping the museum stone
   and canopy behind the crowd — geometrically the building is behind the
   camera in that framing, not behind the crowd, so the model invented a
   plausible "behind a crowd" background instead. Root cause is a
   contradiction in the sheet's own shot description, not a rendering
   failure, per the CTO's note.**
3. **GUARD COUNT** — **PASS, 6/6 with correct grouping this time.** Zoomed
   crop of the door line at 0.5s (`t0.5_guards_crop.png`) shows: one guard
   ALONE at the far left, arms out, standing apart by the wall/alcove door;
   four guards shoulder-to-shoulder directly in front of the glass revolving
   door; one guard ALONE at the far right, arms out, standing apart near the
   ramp/steps. Visible empty step separates each flank guard from the middle
   four on both sides. This is the first take to fix the bunching defect
   that failed both take 1 (5 guards, no flanks) and take 2 (6 guards, still
   bunched) — the sheet's more explicit "several metres of empty step" /
   named landmark language for guards 1 and 6 appears to have worked.
4. **CROWD COUNT (20-30) and duplicate faces/coats** — **PASS.** The
   crowd-band crop (`t0.5_crowd_crop.png`) alone shows on the order of 15-18
   distinct heads/faces in just the visible lower two-thirds of Shot One,
   with more crowd implied off-frame and behind (consistent with 20-30
   across the full composition once the parts cut off by the tight framing
   are counted). Scanned both edges of the 0.5s and 2.5s wide frames: no
   two figures share an identical face + coat pairing — varied hair colors,
   ages, glasses/no-glasses, coat colors and styles throughout.
5. **ORDINARY CLOTHES, no gold V except guards** — **PASS.** Every crowd
   member wears ordinary modern street clothing (jackets, cardigans, a
   suit, coats) in muted ordinary colors; the gold V mark appears only on
   the building facade and on the six guards' caps/chests, never on a
   civilian.
6. **AUDIO — voices with no intelligible words** — **NOT INDEPENDENTLY
   VERIFIED.** `ffprobe` confirms an AAC audio track is present and the
   video plays with sound in the preview modal, but no transcription/listen
   pass was performed as part of this still-frame review — flagging as open
   rather than guessing, consistent with takes 1 and 2's reports.

Additional checks from the sheet's own review order: doors stay shut and no
one gets past the line in every frame examined (Shot One and Shot Three both
show the glass doors intact behind the guards); two hard cuts land at
distinctly different angles/framings (wide crowd-level -> crush behind two
guards' shoulders -> tight two-guard chest portrait); no readable text
anywhere in any frame examined.

## Verdict

**FLAGGED** — one item outstanding out of everything the brief asked to
check:
- Shot One sky/light: PASS (no recurrence of the flat blue-grey defect;
  sky itself isn't in frame to independently confirm amber).
- Shot Two location: **FLAGGED** (open ground + stadium floodlights + city
  skyline, not the museum forecourt) — root cause identified by the CTO
  mid-review as a geometry contradiction in the shot description itself
  (camera looking away from the building while also requiring the building
  behind the crowd), not a model failure. Per the CTO's explicit
  instruction, **not re-fired this take** — the sheet's geometry is being
  fixed before the next attempt.
- Guard count + grouping (six, one-alone-left/one-alone-right, visible
  gaps): PASS — first take to fix this.
- Crowd count/crush, no duplicate faces: PASS.
- Ordinary clothes, no stray gold V: PASS.
- Doors shut, two hard cuts, no readable text: PASS.
- Audio content: not independently verified (track present, not
  transcribed).

Filed to Drive regardless per instruction ("file the take whatever the
verdict").

## Notes for reviewer

- Per the task brief's explicit instruction, the Drive filename carries no
  take number or verdict (`SC5-CrowdAtDoors-Fix1.MP4`), consistent with the
  FIRE-PLAYBOOK.md HARD rule that the filename is the scene name only — this
  differs from take 1/2's filenames (`SC5-Crowd-Fix1.MP4`,
  `SC5-Crowd-Fix1-take2.MP4`), which predate that HARD rule being written
  down.
- Did not re-fire, per the CTO's explicit mid-task instruction after
  reviewing the same defect independently and diagnosing its cause (shot
  geometry contradiction) — the next attempt should follow a corrected sheet,
  not a repeat of this one.
- All four browser gates (paste-block banned pattern, `HARD CUT` count,
  `prompt-lint.py` exit code, chip count) matched the task's stated
  expectations exactly on the first check — no mismatch to adjudicate.

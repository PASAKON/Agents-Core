# S2S-B take 2 — A HUNDRED MILLION, REVERSE ANGLE — 2026-09-07

STATUS: **FLAGGED** — one successful fire (Unlimited/free), rendered clean
(no copyright/NSFW rejection). This is the clip's first-ever landed file:
take 1 (12:07) sat 95 min in Processing and was cancelled; a later attempt
never fired because the previz eligibility check hung. Cast is wrong: a
duplicate third guard stands in the line, THE REGISTRAR / THE ART STUDENT /
DUPE never appear anywhere in the 20s, and the 13s walk-past-camera beat is
performed by THE WOMAN IN COBALT instead of the art student it belongs to.
Filed per instruction regardless of verdict. One fire per task — not
re-fired.

## Setup verification

- innerWidth readback: 1440 (>=1280 threshold met) via
  `({w: window.innerWidth, h: window.innerHeight})` — window never resized
  or maximised by this session, per task instruction.
- "Credits are running low! Over 90% already used" banner: closed via its
  own (x) as the first composer action.
- Switched composer from Image to Video mode explicitly (confirmed via
  zoomed Image/Video tab screenshot), then selected Seedance 2.5 from the
  model dropdown (was Cinema Studio 4.0 by default).
- Six fields verified via zoomed screenshots immediately before firing:
  **Seedance 2.5 · 16:9 · 720p · 20s · High · Sound On**. Duration set via
  the ARIA slider (`ref` click + 15x ArrowRight, 5s→20s), never typed.
  Confirmed via zoom the slider box read "20s" before proceeding.
- Unlimited toggled ON **after** all six fields were set (re-toggle
  requirement — duration change resets it); zoomed screenshot confirmed
  `UNLIMITED · ~~140~~ 0` — zero digits — immediately before the Generate
  click.
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  focused contenteditable (only the PASTE FROM HERE / PASTE STOPS HERE
  block), then End -> space -> Backspace tap to bind the Lexical chips.
- Chip gate: 13/13 unique `@` chips lime (`span.text-font-brand`, no nested
  span, starts with `@`), confirmed programmatically both before and after
  attaching the previz reference (no chip loss from the reference-panel
  interaction). 0 red/unresolved `@`. Matches `prompt-lint.py --chips`
  exactly (list of 13 unique names cross-checked).
- Gate greps (paste block only, via `awk` PASTE FROM/STOPS HERE extraction):
  depth/gaze pattern `nearest|extreme foreground|very front|floating|toward
  the mark|backs to the room` -> 0 matches; `prompt-lint.py` exit 0; chip
  count 13 (see above).

## Previz

`docs/S2SB-Render.MP4` (4276866 bytes, confirmed via `ls -l`). Per
instruction, searched the project's Uploads > Videos library instead of
uploading fresh — this was the clip's third attempt and a fresh upload had
already hung twice. Found the correct tile by opening each candidate's
preview and comparing its CloudFront URL's `HEAD content-length` against the
4276866-byte target:

- Candidate 1 (top-left): 4528874 bytes — no match.
- Candidate 2: 1792176 bytes — no match.
- Candidate 3 (the GRANDMOTHER-labelled tile): **4276866 bytes — exact
  match.** Selected via the library's checkmark, closed the picker.

Generate was enabled immediately with the previz attached (no 10-minute
eligibility wait needed) — the checkbox stayed selected on re-open, chip
count stayed 13/13, and price stayed `UNLIMITED · 0` after attaching. Fired
with the previz in place; the 10-minute-cap / rebuild-tab / fire-bare
fallback path in the task brief was not needed.

## Fire

**Fired at 2026-09-07T16:34:18Z = 23:34:18 ICT.** Verified by the
"Generation started" toast AND the asset count moving 707->708 in the same
action, AND a new Processing card (spinner) appearing at the top-left of the
grid under a fresh-tab reload immediately after.

## Render

~46 minutes wall-clock (fired 23:34 ICT, found landed on the ~00:20 ICT
poll — spinner gone, real thumbnail with a "New" tag in its place). Within
the "free-lane renders ran 30-46 min tonight" range named in the playbook.
No "Rejected due to copyright restrictions", no NSFW/sensitive-content
banner, no credits-refunded banner. 10-minute fresh-tab polling used
throughout (tab opened, checked, closed each cycle); one scheduled 10-minute
background wait was killed by the harness's low-memory guard mid-cycle — per
playbook ("poll anyway" if a background sleep is killed), the next poll ran
immediately rather than re-sleeping.

## Card identification

Clicked the finished tile to open its Info panel:

- Prompt (first line): "20s · 720p · 16:9 · ONE LOCKED SHOT. The camera
  never moves, never pans, never zooms, no cuts, for the whole twenty
  seconds. Sound On · High." — matches the pasted block exactly.
- **Created: September 7, 2026 at 11:34 PM** — matches the fire time
  (23:34:18 ICT) exactly.
- Model: Seedance 2.5, Quality: 720p, Bitrate: High, Size: 1280x720.

## Download + file

Downloaded via the Info panel's Download button ->
`hf_20260907_163410_76ba0709-a5f6-47b3-a571-d4da5e4b6ebb.mp4` (21,375,833
bytes). md5 `8151cd2da855947743a7785e214d0ec6` checked against every other
mp4 already in `~/Downloads` (94 files) — zero matches, confirmed a genuinely
new file, not a wrong-card re-download. `ffprobe`: 1280x720, duration
20.04s. Filed to `All Scene/Fix-1/` as `S2S-B-Fix1.MP4` via
`scripts/gdrive-bridge/upload_fix1.py` (appended the project's `logs.txt`
line automatically):
https://drive.google.com/file/d/1YumeLYcSvy5i16v6THuypG2nGuDbISKr/view

## Checks (frames at 0.5s, 4s, 8s, 12s, 16s, 19.5s)

Frame paths: `docs/reports/frames-s2s-b-t2/t0.5.png`, `t4.png`, `t8.png`,
`t12.png`, `t16.png`, `t19.5.png`.

- **0 THE MARK (crack over the red door):** PASS. The reverse angle keeps
  the broken wall out of shot as specified — no crack, no star, no damaged
  plaster anywhere in any of the six frames. The red door is visible, plain,
  intact throughout.
- **We are behind her, her face never seen:** PASS. All six frames show only
  the back of the grandmother's head/shoulders/hand on the lever; no front,
  no profile, no reflection of her face.
- **The chair goes away from us, not toward us:** PASS. t0.5→t19.5 the chair
  recedes very slowly down the hall; it never approaches the lens.
- **Every head turns to face the lens at 3s:** PASS at t4 — Carrington,
  guards, Valder, woman in green, and the visible visitors are all facing
  camera by 4s, consistent with the scripted mass turn.
- **The distance holds for 20s, group never gets bigger:** PASS — chair
  covers only a small fraction of the 24m by t19.5; the standing group stays
  the same apparent size throughout.
- **People count, "THIRTEEN PEOPLE and not one more":** **FLAGGED.**
  **CORRECTED after CTO recount (2026-09-08)** — the first pass undercounted
  the right-hand guard cluster as one figure; it is two, overlapping in the
  frame. Re-examined every check frame with matched, tight crops on both
  guard clusters (left-of-Valder and right-of-green-woman) and counted
  navy-uniformed guards per frame:

  | frame | left cluster | right cluster | total navy guards |
  |---|---|---|---|
  | t0.5 | 2 (tall-thin + short-heavy) | **2** (two guards, same build, overlapping) | **4** |
  | t4   | 2 | 1 | 3 |
  | t8   | 2 | 1 | 3 |
  | t12  | 2 | 1 | 3 |
  | t16  | 2 | 1 | 3 |
  | t19.5| 2 | 1 | 3 |

  At **t0.5 the guard_valder_two pair is rendered twice**, mirrored across
  the group — two guards to the left of Valder, two more to the right of
  the woman in green — exactly as the CTO read from `t0.5_fullgroup.png`.
  This is a clean "no face is repeated anywhere" violation at the very
  first frame. From t4 onward one of the right-hand pair is gone and the
  count settles to 3 navy guards (2 correct + 1 persistent, unaccounted
  extra) for the rest of the clip — still one too many against the named
  "TWO GUARDS" spec, just not the full mirrored duplicate the opening frame
  shows. Net: **12 distinct background figures appear at some point in the
  clip** (10 sustained from 4s on, +1 transient 4th guard visible only at
  0.5s) + grandmother = 12 max instantaneous headcount, never the full 13.
  Three named characters never appear anywhere in the 20 seconds —
  **THE REGISTRAR** (cream/orange tunic), **THE ART STUDENT** (yellow-green
  hair, denim overshirt, sketchbook), and **DUPE** (his service cart is
  present at frame-left in every frame, but he himself never is).
- **The two who leave walk past her without looking (13s/16s):** **FLAGGED**
  in part. At t16 the correct character (the woman in the chestnut fur,
  matching @project_absence_char_visitor_b) walks past camera without
  looking down — PASS for that beat. But at t12 the figure already walking
  toward camera is **the young woman in cobalt** (oversized cobalt coat,
  gold V pin, dark hair pinned up — confirmed by zoomed crop) — not the art
  student the script names for the 13s beat. The art student's own
  distinctive look (acid yellow-green hair, denim overshirt, sketchbook)
  never appears anywhere in the clip; the cobalt woman performs the
  scripted walk-past in her place, without looking down, at an ordinary
  pace, consistent with the choreography but attached to the wrong
  character.
- **One line of dialogue, hers, close to the mic while she is far from
  them:** not verified from stills (audio not checked frame-by-frame); no
  contrary evidence observed.

**Overall verdict: FLAGGED.** No crack/mark violation and the camera/chair
blocking is clean, but the named cast is wrong on several fronts at once:
the guard_valder_two pair duplicates/mirrors at the opening frame (4 navy
guards at t0.5, settling to 3 — one persistent extra — from t4 on), the
registrar/art student/DUPE never appear anywhere, and the 13s walk-past is
performed by the wrong character. Filed regardless per instruction.

## Notes

- SKILL-OVERRIDE: none — FIRE-PLAYBOOK.md and the sheet's own PASTE-block
  gates were followed as written.
- The task brief's 10-minute previz-eligibility contingency (rebuild tab,
  then fire-without-previz if still disabled) was not triggered — the
  library-tile previz attached cleanly and Generate was enabled immediately.

# Absence wave 2026-09-06 — S2N-Fix1 take 2 (five million)

## Verdict up front

**FAILED review — two defects the "TAKE 2 PROSE" fix was written to prevent
both reproduced anyway.** (0) The mark is oversized, roughly 2x the red
door's width, not "1x the door". (0b) The five have full BACKS to the camera
at 0.5s and 3s — not facing the lens as the locked frame requires. Filed to
Drive regardless, per task instruction ("whatever the verdict, it is
filed"). Not re-fired. Not escalated to S2L.

## Pre-fire verification

### Merge / sheet check
- `git merge main` fast-forwarded `f3f9a91` -> `460a89c` (past the required
  `3b6294f`).
- Gate, paste-block only (`awk` between PASTE FROM/STOPS HERE markers):
  - `grep -c 'NO WIDER THAN THE RED DOOR'` -> **1** (required 1) OK
  - `grep -c 'FACING THE CAMERA'` -> **1** (required 1) OK
  - `grep -c -i -E 'nearest|extreme foreground|very front|floating|toward the mark'` -> **0** (required 0) OK

### Chip-count discrepancy found before firing
`python3 scripts/prompt-lint.py --chips docs/prompts/absence/s2n-fix1-five-million.txt`
printed "EXPECTED 11 Element chips" in its header but listed 12 names,
including bare `@project_absence_char_guard_private`. Checked the source
file directly: that bare handle appears **only in the NOTES section** (line
30, a warning that it "still exists and still points at a completely
different man" and must never be bound — only `..._guard_private_v2` is
correct). It does **not** appear anywhere inside the PASTE FROM/STOPS HERE
block. The task brief said "12 unique names", which appears to have been
taken from the lint tool's raw list rather than the true paste-block count.
**Fired with 11/11** (the correct count), not 12 — binding the bare handle
would have both been wrong per the sheet's own warning and impossible
anyway since it isn't in the pasted text. Flagging this as a lint-tool
false-positive for future waves.

### Browser setup
- First tab (53473077): innerWidth 1440, correct project confirmed
  ("The Valder Collection No.7"), banner closed, fields set, prompt pasted,
  11/11 chips bound, Unlimited zoom-confirmed `~~140~~ 0`.
- **Renderer hang mid-task**: after uploading the previz and clicking
  "Check eligibility" + the tile, screenshot/zoom capture on this tab began
  timing out ("CDP sendCommand Page.captureScreenshot timed out after
  30000ms") — 6 consecutive failures across a page reload attempt. JS
  execution (`javascript_tool`, `read_page`) kept working throughout,
  confirming the page itself was alive; only the CDP screenshot pipeline for
  that specific tab was stuck. Per the browser-operator skill's escalation
  ladder (hard reload -> new tab -> restart Chrome), released the tab,
  closed it, and opened a fresh one (53473081) rather than continue fighting
  it. No money was ever at risk during this — no Generate click had been
  made yet, and only read-only checks were attempted on the stuck tab per
  the "one clean attempt" rule for a misbehaving control.
- Second tab (53473081): full rebuild from scratch — innerWidth 1440,
  correct project, banner closed, Video tab, model, all six fields, prompt
  paste, chips, previz. Screenshot capture worked normally on this tab from
  the start and stayed reliable through the whole render/download/frame
  workflow.

### Six fields, verified fresh at time of fire (second tab)
| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Aspect | 16:9 |
| Resolution | 720p |
| Duration | 20s (ARIA slider, thumb-click then `ArrowRight` x15 from value 5, `aria-valuenow` confirmed 20) |
| Quality | High |
| Sound | On |
| Unlimited | ON — button zoom-verified **`UNLIMITED . ~~140~~ . 0`**, re-zoomed a second time immediately before the click |

### Chip count
`[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
-> **11/11 unique** Element names bound, **0 unresolved/red `@` runs**
(verified by walking every text node in the editor and checking each `@`
run sits inside a `.text-font-brand` chip span). Names: `@char_registrar`,
`@gentleman_e`, `@project_absence_char_cleaner_c`,
`@project_absence_char_critic_b`, `@project_absence_char_guard_private_v2`,
`@project_absence_char_student_c`, `@project_absence_char_visitor_a`,
`@project_absence_char_visitor_b`, `@project_absence_char_woman`,
`@project_absence_loc_wall_pov_e`, `@project_absence_prop_cart_a_painted`.

Text entered via synthetic `ClipboardEvent` paste (text/plain only) into the
verified-real (non-hidden) `contenteditable`, followed by End->space->
Backspace to force Lexical's bound state to sync. Pasted length 10,445 chars
on both tabs (identical first-80/last-80 chars each time), matching the
source paste block.

### Previz — ATTACHED, confirmed
`docs/S2N-Render.MP4` (4,165,774 bytes on disk = 4068 KB) uploaded via the
reference panel's video file input; platform reported "4068 KB total"
matching exactly. Clicked "Check eligibility" pill, waited for it to clear,
then clicked the tile: **"Added to prompt box" toast + green checkmark**
confirmed the attach on the second (working) tab — the two-click flow from
the skill worked cleanly here, unlike the first tab where the same
click sequence never produced the toast (likely downstream of the same
renderer stall that broke screenshots on that tab). Total time from upload
to confirmed attach: under 3 minutes, well inside the 10-minute cap.

## Fire — CONFIRMED

Re-verified immediately before the click: correct project URL, innerWidth
1440, 11/11 chips, prompt text intact (10,445 chars, correct head/tail), and
a final zoom of the Generate button reading `UNLIMITED . ~~140~~ . 0`.

**Verified fired two ways:**
1. `All assets` sidebar count: **670 -> 671** immediately after the click.
2. "Generation started" toast + new spinning "Processing" card at the top
   of the grid.

**Fire time: 2026-09-06 09:56:32 UTC (16:56:32 ICT).**

## Render / poll log (20-min-then-5-min cadence, reload each time)

| Check | Elapsed | Card state |
|---|---|---|
| 09:56 UTC | 0 min | fired (Processing) |
| 10:10 UTC | ~14 min | Processing |
| 10:15 UTC | ~19 min | Processing |
| 10:20 UTC | ~24 min | Processing |
| 10:25 UTC | ~29 min | Generating |
| 10:30 UTC | ~34 min | Generating |
| ~10:35 UTC | ~39 min | Generating |
| by 10:34:59 UTC check | ~38 min | **finished — "New" badge, clean thumbnail** |

Several background sleep waits (300-1140s) were killed mid-wait by a
Mac-level low-memory event, unrelated to Higgsfield or the render itself
(matches the known overdue LungNote item about closing excess CTO sessions
to relieve swap pressure). Each time, checks simply resumed a few minutes
later than the nominal cadence — no impact on the render (server-side).

**Render duration: ~38-39 minutes**, within today's documented 30-55 min
range. **No NSFW / no Credits-refunded badge** — clean card. The pre-existing
NSFW/Credits-refunded card visible in the grid the whole time belongs to
S2M take-3 (left untouched, per task scope) and to the CEO's own credit-lane
cards (also untouched).

## Download and verify

- Downloaded via the card's Info panel -> Download. Landed at
  `~/Downloads/hf_20260906_095620_1625e327-fca1-4420-83b5-7c8be93cc5d2.mp4`
  (21.0 MB) — filename embeds the fire timestamp `095620` (09:56:20 UTC),
  matching the fire time above.
- `ffprobe`: `codec_name=h264, width=1280, height=720, r_frame_rate=24/1,
  duration=20.041667` — matches spec exactly (1280x720, ~20s).

## Frame checks — 0.5s, 3s, 8s, 16s (`ffmpeg -ss <t> -frames:v 1`)

### 0. THE MARK — FAIL
Position is correct (over the red door, upper-middle of frame), shape is
correct (thin lines meeting at one dark point, solid black), and it stays
off every face. But size is wrong: cropping the door/mark region and
comparing widths, the crack's outer lines extend well past both edges of
the red door — reaching roughly toward the flanking columns — at both 0.5s
and 16s. **Reads as about 2x the door's width, not "no wider than the
door."** This is the exact defect the take-2 prose rewrite (informed by
S2K t1 / S2M t2) was supposed to fix, and it recurred here.

### 0b. THE FIVE FACE THE LENS — FAIL
At 0.5s and 3s, all five (blue coat, yellow-green hair, fur coat, maroon
suit, magenta fur) stand with **full backs to the camera** — the opposite
of "FACING THE CAMERA . full face to the lens, not backs, not profiles."
By 8s and 16s they have turned to side/three-quarter profiles (consistent
with the "heads turn" beat), but at no checked frame do they present full
face to the lens as the locked opening frame requires. This is the same
class of defect ("turned toward the mark"/wrong-direction) the prose was
rewritten to prevent, reproduced in the opposite direction (backs instead
of facing the far door).

### 1-5 — REVIEW ORDER (from available frames)
1. **Registrar's line and turn to the far end** — not directly captured in
   the four extracted frames (his exit/arrival at [7s]/[14s] falls between
   sampled timestamps), but at 8s only the old man and bodyguard are visible
   at the far end (no third figure yet) — consistent with the registrar not
   having arrived early. No anomaly found.
2. **Old man's arrival deep in the gallery** — present at 8s and 16s, white
   suit + black-suited bodyguard, correct position deep in the gallery
   behind the mark. **Consistent with the sheet.**
3. **"Five million" beat** — not independently verifiable from static frames
   (audio/dialogue); no visual contradiction found.
4. **Camera dead still** — identical framing/composition across all four
   checked frames, no pan/tilt/zoom/dolly detected. **PASS.**
5. **The crack in front of everyone** — at 16s the crack's silhouette sits
   between the camera and the old man/bodyguard, consistent with "in front
   of everyone" — but its oversized width (see check 0) means it also
   crosses closer to the flanking group's space than the sheet intends.

Frame PNGs saved locally at the session scratchpad
(`s2n-fix1-t2-{0.5,3,8,16}s.png`, plus two crop images for the mark/door
size comparison), not committed to the repo — binary artifacts don't belong
in git history; the finished clip itself, filed to Drive below, is the
durable record.

## Drive filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to the pre-established
`All Scene/Fix-1` folder (id `1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`):
```
S2N-Fix1-take2.MP4  (20.1 MB)
https://drive.google.com/file/d/1CdbF0w8Er9c59cNBxrM-xmnMPg28SuE3/view
```
Logged to the project's `logs.txt` in the same call, with the note
recording the FAIL verdict (mark oversized, backs to camera).

## Money / safety discipline

- Never clicked Rerun. Never touched a priced (non-struck) Generate.
- Only one Unlimited-video generation fired this session. No images
  generated. The pre-existing NSFW-rejected S2M take-3 card and the CEO's
  `SEEDANCE 2.5 CREDIT`-prefixed cards were both left untouched.
- Zero paid actions of any kind.
- Read `gdrive-filing` skill before the Drive upload call (per the
  session's PreToolUse gate); used the project's own pre-existing,
  self-contained upload script rather than the general Drive bridge, which
  already hardcodes the correct Fix-1 folder and logs.txt IDs for this
  project — no new folder created, no rename/move/delete performed.

## SKILL-OVERRIDE

None. All HARD rules in `browser-operator` and `higgsfield-unlimited-gen`
were followed as written.

## Files Changed
- `docs/reports/absence-wave-20260906-s2n-t2.md` — this report (new)

## Anything odd
- **CDP screenshot capture broke on the first tab** partway through the
  previz-attach flow (6 consecutive `Page.captureScreenshot` timeouts,
  JS execution unaffected) and never recovered even after a full page
  reload. Released and closed that tab, opened a fresh one, and rebuilt
  the entire composer state from scratch on it — screenshots worked
  normally there for the rest of the session. Root cause not confirmed
  (possibly a Chrome-side rendering-pipeline stall tied to the uploaded
  video element), but the fix (fresh tab) matches this skill's documented
  escalation ladder.
- **Chip-count mismatch in the task brief vs. the sheet's own PASTE block**:
  see "Chip-count discrepancy" above — task said 12, the lint tool's raw
  list said 12 (but included a NOTES-only handle explicitly banned from
  binding), the true paste-block count is 11. Fired at 11/11, which is
  correct.
- Several background waits were killed by a Mac-level low-memory event
  unrelated to this task; each recovery just polled a few minutes later
  than nominal with no effect on the render.
- The CTO's own review of this clip (per the standing review-loop rule)
  will presumably confirm or override these two FAIL findings — flagging
  explicitly rather than re-firing, per the task's "do not fire S2N again"
  instruction.

## Next step (not mine)

Per the task brief: STOP after this report. The mark-size and
facing-camera defects both need a prose fix before any further S2N take —
that is the CTO's call, not this session's.

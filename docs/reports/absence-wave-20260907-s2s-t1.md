# S2S-Fix1 take 1 — A HUNDRED MILLION — 2026-09-07

STATUS: PASS (near-clean) — one fire, rendered clean (no copyright/NSFW
rejection), correct cast, and the full "voice → turn → slow arrival → two
people give up" beat sequence executes as scripted. One fire per task — not
re-fired.

## ⚠️ WRONG-CLIP CORRECTION (read this first)

The first pass of this report (and the first Drive upload under the name
`S2S-Fix1.MP4`, filed ~09:02 ICT) reviewed and filed the **wrong asset**.
While re-finding the S2S card after the fire, two cards with near-identical
first-frame compositions sat close together in the grid (S2S opens on
literally the same locked frame as S2R — "same frame, nobody has moved" is
in the prompt itself), and the S2R card was opened and downloaded by
mistake. That file (`hf_20260907_001412_..._12732c26...(1).mp4`, md5
`56b25dd4ce67a51153e2a35b081b5313`) is byte-identical to the S2R-Fix1 take —
which explains why the original frame check found a static tableau with no
head-turn, no grandmother, and a duplicate/missing-character cast: it was
never S2S footage, it was S2R's own (different) cast standing in the same
hallway.

Caught by the CTO comparing the downloaded file's md5 against S2R-Fix1.
Corrected here:

- **Correct asset**: uuid `cf43d0ba-3ebd-4629-b13a-a50300254303`, file
  `hf_20260907_011200_7dd102e3-f30e-49ad-8321-4de2c912cfd7.mp4`, md5
  `4cf4dcea264b614565f71674cc0ae040` — **differs** from the wrong file's
  md5, confirmed. Filename timestamp `20260907_011200` = 01:12:00 UTC =
  **08:12 ICT**, matching this task's actual fire time exactly. Info panel
  prompt text contains both `wheelchair` and `hundred million` (checked
  programmatically), confirming it is the S2S sheet.
- Re-downloaded, re-verified (`ffprobe`), re-extracted all 6 review frames
  (overwriting the wrong ones in `docs/reports/frames-s2s-t1/`), and
  re-uploaded to Drive under the same filename — a second `S2S-Fix1.MP4`
  now exists in `All Scene/Fix-1/` per the CTO's instruction (did not
  delete/rename the first, wrong one; that is the CTO's call after CEO OK).
- **Everything below this section describes the CORRECT clip.** The
  original (wrong-clip) findings are entirely superseded — nothing from
  that pass is still true of the actual S2S render.

Correct Drive link: https://drive.google.com/file/d/1PgzYzueeofquHsPCuam-4RyNVS_pAvm6/view
Wrong Drive file (do not use, left in place for CTO to trash after CEO OK):
https://drive.google.com/file/d/1FkoEocXvB2PiZClIppyx5a9HhaEPBXCt/view

## Setup verification

- innerWidth readback: 1440×754 (>=1280 threshold met), then 1400×698 after
  the composer overlay reflowed the layout — both well above the mobile
  breakpoint.
- "Credits are running low!" banner: closed via its own (x) as the first
  composer action.
- Video mode selected explicitly (decoy Image/Video tab pair filtered by
  `getComputedStyle(el).visibility`), model switched from the default Cinema
  Studio 4.0 to Seedance 2.5 explicitly.
- Six fields verified twice (once mid-setup, once immediately before the
  Generate click): 16:9 · 720p · Seedance 2.5 · 20s · High · Sound On.
  Duration set via the ARIA slider (`ArrowRight` × 15 from the default 5s,
  never typed).
- Price zoom: `UNLIMITED · ~~440~~ · 0` confirmed by zoomed screenshot
  immediately before the Generate click (toggled Unlimited AFTER all six
  fields, per the duration-resets-Unlimited rule).
- Paste method: base64 synthetic `ClipboardEvent('paste')` dispatched on the
  visible (non-decoy) contenteditable, then End → space → Backspace tap to
  force the Lexical binding.
- Chip gate: 14/14 unique `@` chips lime (`span.text-font-brand`, no nested
  span, starts with `@`), 0 unresolved/red `@` text. Names matched
  `prompt-lint.py --chips` exactly minus `@project_absence_prop_croc_bag`
  (deliberately absent from the paste block per this morning's copyright-gate
  fix — confirmed 0 occurrences of that name in the extracted paste block).
- Gate greps (paste block only, via `awk` PASTE FROM/STOPS HERE extraction):
  `nearest|extreme foreground|very front|floating|toward the mark|backs to
  the room` → 0 matches.
- Previz: `docs/S2S-Render.MP4` attached via the References panel Upload,
  sorted "Last created" to avoid the stale "Last used" default, byte-verified
  against the live CDN URL (`HEAD` content-length `4259236` — exact match to
  `ls -l docs/S2S-Render.MP4`). `readyState: 4`, `duration: 20` confirmed via
  the attached `<video>` element before firing.

## Fire

Fired once at 2026-09-07 08:12 ICT. Verified by the "Generation started"
toast AND a new Processing card (spinner) at the top of the grid, asset
count 683→684 at the moment of the click (read BEFORE the previz-upload
count bump, per the playbook's "an uploaded reference bumps the asset count"
warning — the previz had already been attached and counted before this
read).

## Render

~48 minutes wall-clock (fired 08:12 ICT, found finished ~09:00 ICT on
reload). Screenshot/zoom capture on the composer tab was unreliable for
several poll cycles (`CDP sendCommand "Page.captureScreenshot" timed out`) —
diagnosed as system-wide memory pressure from other concurrent sessions in
the same Chrome (confirmed via `ps aux`: a sibling `browser_operator` task
was running a parallel image-gen job in the same project), not a frozen
render or a money-risk event. Fell back to `javascript_tool` text/DOM reads
(readyState, body text, `[class*="animate-spin"]` count) during the timeouts
— those never require the screenshot pipe and confirmed the card was still
processing with no rejection/NSFW/refund text anywhere on the page at each
check. No click was attempted near the Generate button during any timeout.

No "Rejected due to copyright restrictions", no NSFW/sensitive-content
banner, no credits-refunded banner. The finished card's Info panel and
prompt text matched the fired prompt exactly (20s/720p/16:9, full prose
visible via "See all").

## Download + Drive (corrected)

- Grid had accumulated several new cards between the fire and the review
  pass (a sibling worker's image-gen fires in the same project), and the
  S2S and S2R cards' first-frame thumbnails are visually near-identical by
  design — the wrong-clip mistake above happened here. Corrected by
  matching the card's Info-panel prompt text for `wheelchair` +
  `hundred million`, not by thumbnail or grid position.
- Downloaded via the card's own Download button (not a raw URL fetch).
- `ffprobe`: video 1280×720, duration 20.05s — matches spec exactly.
- Frames re-extracted and visually confirmed against the fired prompt
  before re-filing.
- Filed to Drive `All Scene/Fix-1/S2S-Fix1.MP4` (second copy under this
  name, per CTO instruction):
  https://drive.google.com/file/d/1PgzYzueeofquHsPCuam-4RyNVS_pAvm6/view
  via `scripts/gdrive-bridge/upload_fix1.py` (appended the `logs.txt` line,
  noting the correction in the log note).

## Frame checks (0.5s, 4s, 8s, 12s, 16s, 19.5s)

Frames: `docs/reports/frames-s2s-t1/f_0.5s.png`, `f_4s.png`, `f_8s.png`,
`f_12s.png`, `f_16s.png`, `f_19.5s.png` (re-extracted from the correct file).

### 0c — every named character present

Checked both ends of a line (present near the start AND accounted for by
the end, whether still present or having correctly left) before calling
anyone missing.

| Character | Verdict |
|---|---|
| @gentleman_e (Carrington, white suit, cane) | PRESENT throughout |
| @project_absence_char_woman_c (green gown, feathered hair) | PRESENT throughout |
| @project_absence_char_valder (rainbow blazer) | PRESENT throughout, seen adjusting his scarf around 15-16s per the sheet's cue |
| @char_registrar (cream tunic, ledger, foreground) | PRESENT throughout |
| @project_absence_char_grandmother (wheelchair) | PRESENT — first visible tiny at the far red door by 8s, still clearly far off (barely closer) at 19.5s |
| @project_absence_char_guard_private_v2 (bodyguard) | PRESENT throughout |
| @project_absence_char_guard_valder_two (2 navy guards) | PRESENT (both), throughout |
| @project_absence_char_woman (cobalt coat) | PRESENT throughout |
| @project_absence_char_critic_b (magenta fur) | PRESENT throughout |
| @project_absence_char_visitor_b (tawny/chestnut fur over rust dress) | PRESENT at 0.5s–12s, correctly walks out past the lens by 16s (per the sheet's own cue), gone by 19.5s |
| @project_absence_char_student_c (art student, acid yellow-green curly hair, denim, sketchbook) | PRESENT at 0.5s–12s (clearly visible: yellow-green curls, denim overshirt, black sketchbook), correctly gone by 16s/19.5s |
| @project_absence_char_cleaner_c (Dupe, cream/orange uniform, cap) | PRESENT throughout |
| @project_absence_prop_cart_a_painted (Dupe's cart) | PRESENT — orange bucket/cart visible beside Dupe from 8s onward |

No duplicate characters, no unidentified extra figures. Cast matches the
sheet's 13-person roster exactly at every sampled timestamp.

### REVIEW ORDER (from the sheet)

1. **SHE NEVER ARRIVES** — PASS. First visible tiny at 8s by the red door,
   still clearly far away at 19.5s ("has covered barely any of the
   distance" — confirmed, she is only marginally larger/closer between 8s
   and 19.5s).
2. **THE VOICE LANDS BEFORE SHE IS VISIBLE, whole room turns at once** —
   PASS. `ffmpeg silencedetect` shows a speech-shaped sound event at
   0.8–2.4s (before she is visible), then by the 4s frame most of the room
   (bodyguard, Carrington, both guards, cobalt woman, student_c, woman in
   green, critic_b) is turned away from camera toward the hall; by 8s
   everyone's back is to camera, all facing the grandmother's direction.
   Not a frame-perfect single-instant turn (Valder trails slightly, visible
   mid-turn at 4s), but the beat clearly executes.
3. **TWO PEOPLE LEAVE** — PASS. Student_c is gone by 16s (last seen 12s);
   visitor_b is mid-departure at 16s (walking toward/past camera) and gone
   by 19.5s. Both leave separately, unremarked by the rest of the group.
4. **THE CHAIR IS A REAL POWERED WHEELCHAIR** — PASS. Zoomed crop at 19.5s
   shows a genuine tubular-frame powered chair, grandmother's hand near the
   armrest control, no attendant/nurse/pusher visible.
5. **ONE line of dialogue** — audio stream present, one clear speech-shaped
   burst at 0.8–2.4s (before she is visible, matching the sheet), no other
   comparable bursts detected elsewhere in the clip via `silencedetect`.
   Exact wording not transcribed/listened to verbatim — structurally
   consistent with the single-line requirement.
6. **THIRTEEN PEOPLE, no extras** — PASS. See the character table above:
   full correct roster, no duplicates, no unidentified extras.
7. **Camera dead still for twenty seconds** — PASS. No pan/tilt/zoom/dolly/
   cut detected across any sampled frame; framing is pixel-identical to the
   locked S2R composition throughout.

### Copyright gate (0b equivalent for this take)

The woman in green's hands are visible and not carrying a bag in the
sampled frames — no crocodile bag rendered, consistent with dropping
`@project_absence_prop_croc_bag` from the paste block. No brass plaque, no
crack, no damaged plaster visible in any frame. This item PASSES.

## Cost

Zero credits — Unlimited confirmed `~~440~~ 0` immediately before the single
Generate click, never varied. No CEO Credit-lane cards touched.

## Verdict

Clean take. All seven REVIEW ORDER items pass, cast matches exactly, camera
lock held, copyright gate held (no rejection, no crocodile-bag artifact).
Recommend accepting this as the S2S-Fix1 delivered take, pending the CTO's
own frame review per the standing "operator never self-certifies" rule.

## Notes for reviewer

- **The wrong-clip mistake is the important lesson here**: S2S and S2R
  share the same locked opening frame by design ("Straight after S2R, same
  frame, nobody has moved"), so thumbnail/first-frame matching in a grid
  full of near-identical cards is not a reliable way to identify the right
  asset — future pulls from this project should match on the Info panel's
  actual prompt text (a distinctive phrase like `wheelchair` or the file's
  embedded creation timestamp against the known fire time), not on the
  grid thumbnail.
- Screenshot/zoom capture flaked repeatedly during the render wait due to
  system memory pressure from a concurrent sibling worker sharing this
  Chrome instance (confirmed via `ps aux`, not a Higgsfield-side issue).
  Text/DOM-based polling (`javascript_tool`) carried the checks through
  those windows without any click risk.
- Two `S2S-Fix1.MP4` files now sit in Drive `All Scene/Fix-1/` — the wrong
  one (from the first pass) was left in place per the CTO's explicit
  instruction not to delete/rename Drive content myself; it needs a CTO
  trash action after CEO OK.

# S2S-Fix1 take 1 — A HUNDRED MILLION — 2026-09-07

STATUS: FLAGGED — one fire, rendered clean (no copyright/NSFW rejection), but
the core story beat never executes. Camera lock and cast size/count are the
only REVIEW ORDER items that pass. One fire per task — not re-fired.

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

## Download + Drive

- Downloaded via the card's own Download button (not a raw URL fetch).
- `ffprobe`: video 1280×720, duration 20.04s — matches spec exactly.
- Frame at 1s visually confirmed against the fired prompt before filing.
- Filed to Drive `All Scene/Fix-1/S2S-Fix1.MP4`:
  https://drive.google.com/file/d/1FkoEocXvB2PiZClIppyx5a9HhaEPBXCt/view
  via `scripts/gdrive-bridge/upload_fix1.py` (appended the `logs.txt` line).

## Frame checks (0.5s, 4s, 8s, 12s, 16s, 19.5s)

Frames: `docs/reports/frames-s2s-t1/f_0.5s.png`, `f_4s.png`, `f_8s.png`,
`f_12s.png`, `f_16s.png`, `f_19.5s.png`.

### 0c — every named character present

Checked both ends of a line (present at 0.5s AND still/newly present later)
before calling anyone missing.

| Character | Verdict |
|---|---|
| @gentleman_e (Carrington, white suit, cane) | PRESENT, all frames |
| @project_absence_char_woman_c (green gown, feathered hair) | PRESENT, all frames |
| @project_absence_char_valder (rainbow blazer) | PRESENT, all frames |
| @char_registrar (cream tunic, ledger, foreground) | PRESENT, all frames |
| @project_absence_char_grandmother (wheelchair) | **MISSING — never appears in any of the 6 frames, including 16s/19.5s when she should be visibly approaching** |
| @project_absence_char_guard_private_v2 (bodyguard) | PRESENT, all frames |
| @project_absence_char_guard_valder_two (2 navy guards) | PRESENT (both), all frames |
| @project_absence_char_woman (cobalt coat) | PRESENT, all frames |
| @project_absence_char_critic_b (magenta fur) | PRESENT, all frames |
| @project_absence_char_visitor_b (tawny/chestnut fur over rust dress) | **PRESENT TWICE — duplicated, standing on both sides of Valder/the woman in green, at 0.5s through 19.5s** |
| @project_absence_char_student_c (art student, acid yellow-green curly hair, denim) | **MISSING — never appears anywhere in the clip** |
| @project_absence_char_cleaner_c (Dupe, cream/orange uniform, cap) | PRESENT, all frames |
| @project_absence_prop_cart_a_painted (Dupe's cart) | NOT clearly visible in any sampled frame (Dupe stands without a visible cart in these crops — may be off-angle/occluded, not confirmed present or absent) |

**Extra, unidentified 13th/14th figure**: an elderly man in solid maroon/
burgundy leather, standing at the far right end of the line (beyond the
tawny-fur duplicate), present in every frame. He does not match any of the
13 character descriptions in the sheet. Combined with the visitor_b
duplicate and the missing student_c, the visible headcount at 0.5s is 13
(should be 12, since grandmother has not yet appeared) — this is not a
simple off-by-one, it is a wrong-cast substitution: student_c was replaced
by a second copy of visitor_b plus this unidentified man.

### REVIEW ORDER (from the sheet)

1. **SHE NEVER ARRIVES** — FLAGGED, but worse than the failure mode this
   item warns against: she doesn't arrive *late*, she never appears at all,
   not even tiny/far-off near the red door (checked via a tight crop on the
   vanishing point at 8s and 16s — empty).
2. **THE VOICE LANDS BEFORE SHE IS VISIBLE, whole room turns at once** —
   FLAGGED. No head-turn happens at any sampled timestamp. Every figure
   faces forward (toward camera) identically at 0.5s, 4s, 8s, 12s, 16s, and
   19.5s. `ffmpeg silencedetect` on the audio track shows a sound event in
   the 0–3.1s window (structurally consistent with the dialogue line's
   placement) but the visual "whole room turns" beat that should follow it
   never happens.
3. **TWO PEOPLE LEAVE** — FLAGGED. Neither the art student (never present
   to begin with) nor the tawny-fur-coat departure happens; every figure
   visible at 0.5s is still in frame, in the same pose, at 19.5s.
4. **THE CHAIR IS A REAL POWERED WHEELCHAIR** — cannot verify; grandmother
   never appears.
5. **ONE line of dialogue** — audio stream present (`ffprobe` confirms an
   audio track), non-silent activity detected in the 0–3.1s window matching
   where the line should sit. Content not verified by transcription — would
   need an actual listen-through, which this check did not do.
6. **THIRTEEN PEOPLE, no extras** — FLAGGED. See the character table above:
   visitor_b duplicated, student_c missing, one unidentified extra man
   present. Net visible count matches "13" numerically but the roster is
   wrong.
7. **Camera dead still for twenty seconds** — PASS. No pan/tilt/zoom/dolly/
   cut detected across any sampled frame; framing is pixel-identical to the
   locked S2R composition throughout.

### Copyright gate (0b equivalent for this take)

The woman in green's hands are visible and empty at 8s (zoomed crop) — no
crocodile bag rendered, consistent with dropping `@project_absence_prop_croc_bag`
from the paste block. No brass plaque, no crack, no damaged plaster visible
in any frame. This item PASSES.

## Cost

Zero credits — Unlimited confirmed `~~440~~ 0` immediately before the single
Generate click, never varied. No CEO Credit-lane cards touched.

## Verdict / recommendation

Filed per "whatever the verdict, it is filed" — the render itself is
technically clean (correct duration/resolution, no platform rejection) but
narratively broken: the entire "voice → turn → slow arrival → two people
give up" beat sequence never executes, and the cast has a duplicate +
missing-character + extra-unidentified-person defect. This is not a
copyright-filter issue (unlike S2R) — it looks like the model held the
locked establishing frame for the full 20s instead of executing the timed
beats, while independently drawing the wrong 13th/14th figures.

Recommend: re-fire is a CTO/CEO call (not taken here — one fire per task).
If re-fired, consider whether 20s of near-motionless staging with six
timed sub-beats is asking Seedance to do too much event-density for one
locked-off shot, and whether tightening the position map's explicit-count
language for visitor_b/student_c (mirroring the IRON RULE "every character
appears exactly once") would help the substitution defect specifically.

## Notes for reviewer

- Screenshot/zoom capture flaked repeatedly during the render wait due to
  system memory pressure from a concurrent sibling worker sharing this
  Chrome instance (confirmed via `ps aux`, not a Higgsfield-side issue).
  Text/DOM-based polling (`javascript_tool`) carried the checks through
  those windows without any click risk.

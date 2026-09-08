# Absence — S15b-1 "I WAS NOT BUYING A WALL" Fix-1, t1 — FIRED, filed, mostly PASS

2026-09-08 · task-9fea9a4e · sheet: `docs/prompts/absence/s15b1-fix1-not-buying-a-wall.txt`

## Outcome: FIRED, RENDERED, FILED — do not re-fire

CTO sent a mid-turn message during review with an independent parallel check
and explicitly said "do not re-fire — the CEO has just changed the format for
this scene and I am rewriting it." Filed as normal per that instruction.

## Gate 0 (paste block only)

| Gate | Expected | Actual | Result |
|---|---|---|---|
| `prompt-lint.py --chips` count | 12 | 12 | PASS |
| Unique `@` names | 12 (list matches sheet) | 12, all present | PASS |
| `HARD CUT` count | 1 | 1 | PASS |
| Banned mark-float pattern (`extreme foreground\|very front\|floating\|toward the mark\|backs to the room\|nearest` scoped to mark/crack) | 0 | 0 | PASS |
| Red-door pattern (wall-POV only, N/A here) | 0 | 0 | PASS |

Matches the task brief's own pre-verification exactly.

## Browser / fire

- Tab claimed via `tab_registry.py` (all prior claims stale, 0 active) —
  tabId 53476109, released after upload.
- Window 1440x900, innerWidth 1400 (>=1280, no mobile trap).
- Credits-low banner closed via its own (x). Video tab already selected.
- Fields set in order: Seedance 2.5 → 720p → 16:9 (default, unchanged) → 8s
  (slider defaulted to 5s as warned; ArrowRight/ArrowLeft to 8s, read back
  "8s") → 1/4 (default) → High (default) → Sound On (default) → **Unlimited
  toggled ON last**, zoomed: `UNLIMITED · ~~56~~ 0`. Confirmed zero digits
  before pasting.
- Prompt pasted via synthetic ClipboardEvent (base64-decoded paste block) into
  the focused contenteditable, then End→space→Backspace to bind chips.
  DOM chip-count check: **12/12** chips resolved lime, 0 red/unresolved.
  Zoomed all 12 chip thumbnails — no warning-triangle badges on any (in
  particular `project_valder_char_villagers_poor` never appears as a chip,
  matching the sheet's PROSE-only instruction).
- Re-zoomed Generate button immediately before click: `UNLIMITED · ~~56~~ 0`
  still zero. Clicked once.
- "Generation started" toast + new Processing card (top-left, asset count
  719→720). Fire time 2026-09-08T04:12:30Z (11:12:30 ICT).
- Identified own card via Info panel: Created "September 8, 2026 at 11:12 AM"
  (matches fire time), prompt text matches sheet verbatim, Model Seedance 2.5,
  Quality 720p, Bitrate High, Size 1280x720.

## Render

Stayed in one turn the whole time — background 5-min sleeps + reload + status
screenshot, repeated. Card stayed "Processing" through checks at 5/10/15/20/25
(one background sleep was killed by low memory at the 25-min mark; polled
anyway per playbook, still Processing)/30/35 min. Landed between the 30- and
35-min checks — **~35 min render**, well inside the day's 26-50 min band, no
cancel warranted.

## Download / verification

- Downloaded via the Info panel's Download button → "Download complete".
- File: `~/Downloads/hf_20260908_041208_e9fbc17c-6af6-4c80-b470-10e3c0609d32.mp4`
  (7,798,340 bytes).
- md5 checked against every other `.mp4` already in `~/Downloads` — no match
  (not a stray/duplicate card).
- `ffprobe`: 1280x720, duration 8.041667s — matches spec (8s/720p).

## Checks (sheet's REVIEW ORDER)

1. **Cuts into S15a-2's ended frame** — PASS. Opening frame (t=0.3s): Dupe
   dead centre, room silent, everyone already facing him, nobody re-entering
   or re-positioning.
2. **She looks at the crack, not at him** — PASS. Confirmed on the shot-two
   frame (t=5.5s/6.0s): her head is tilted up toward the crack on the wall,
   not toward Dupe, while the line plays.
3. **Wheelchair moves, camera travels with it, then locks — no handheld** —
   PASS, verified quantitatively: a 0.2s-step greyscale sweep across the full
   8s shows a **sustained 3-5x-median plateau from ~1.0s to ~4.0s** (the
   camera gliding with the moving chair — a *run* of elevated steps, not a
   spike) followed by a **single 21x-median spike at ~4.2-4.4s** (the real
   hard cut), then everything after sits **flat at <0.4x median** (shot two
   fully locked, no motion/wobble). No jitter/noise pattern consistent with
   handheld in either shot.
4. **Six words, hers, nobody else speaks** — PASS, verified via audio RMS:
   ambient room-tone (~150-350) from 0-5.5s (wheelchair squeak + room tone),
   one clean speech burst ~5.75s-7.4s (RMS 900-2700), settling back to room
   tone by 7.6-7.8s. No other speech-shaped spike anywhere. Fine-grained
   0.1s check at the very start (0-1s) and very end (7.4-8s) shows flat room
   tone both ends — no intro sting, no fade-in/out, no tail/swell/chord.
5. **The cut is real, swept not sampled** — PASS. See item 3's sweep: boundary
   at ~4.2-4.4s scoring 20.96x the median step (median 2.34, peak diff 49.05)
   — well clear of the 3x threshold, and clearly distinguishable from the
   wheelchair-move plateau by shape (one spike vs. a sustained elevated run).
6. **The mark, canon rule 8** — PASS. Measured on the t=5.5s frame, region
   x[540,760] y[30,180] (unoccluded), threshold-80 darkness: bbox 14x8px =
   **1.09% of frame width**, fill ratio **0.438**. Well under the 8% ceiling,
   well over the 0.10 fill floor. CTO ran an independent parallel measurement
   on the same frame (same stated region): 13x7px, 1.0%, fill 0.538 — same
   PASS conclusion from two independent crops.
   (My first attempt used an oversized region [0:250,400:900] that swept in
   unrelated dark objects and produced a false 18.5%/0.031 reading — corrected
   before reporting.)
7. **Count people / navy uniforms / registrars** — counted on the opening wide
   frame (most populated frame available): **13 people** visible (vs. the
   sheet's 21) — this matches the task brief's own disclosed "1 REF/1 person"
   limitation already seen on S14a/S14b; the six prose-only public members did
   not render. Not treated as this take's defect, not re-firing over it.
   **Navy uniforms: exactly 2** (tall guard + short/heavy guard, both frame-
   left) — PASS. **Registrars: exactly 1** structurally present (black suit,
   white glove, small gold lapel pin, right cluster) — PASS on count.

## Two items flagged by CTO's independent parallel review — checked, both confirmed real

1. **Ledger attribute-bleed.** Zoomed Carrington's bodyguard (all-black suit,
   black shirt/tie, white gloves — correctly matches
   `project_absence_char_guard_private_v2`'s described wardrobe) and he is
   holding a brown leather book with gold-edged corner — the registrar's
   ledger. The registrar himself (black suit, white glove, small gold pin,
   separately identified in the frame) is not holding it. Confirmed: this is
   the same attribute-bleed class as this morning's gold-teeth-on-Valder bleed
   — a prop/attribute rendered on the wrong Element reference.
2. **Camera height.** The sheet's SHOT TWO calls for "a two-shot at wheelchair
   height, locked." What rendered instead reads as a **locked wide at roughly
   standing eye height**: full head-to-toe framing with generous headroom
   above every head (crack sits near the top of frame with wall visible above
   it), 5-6 people in frame rather than an isolated two-shot, and no
   low-angle foreshortening on Dupe that a genuinely low wheelchair-height
   camera would produce. Independently agree with CTO's read.

Both are recorded in the sheet's TAKE LOG (flagged, not blocking the file-as-
normal instruction) and here for the CTO's rewrite.

## Filing

- Read `gdrive-filing` skill before the Drive call (hard rule).
- Confirmed nothing already filed under `S15b1-NotBuyingAWall-Fix1.MP4` in
  `All Scene/Fix-1` before uploading.
- Filed via `scripts/gdrive-bridge/upload_fix1.py` →
  https://drive.google.com/file/d/1NOLpkrCPD-nE3TL_eQfY37KoxGY1BpA_/view
  (appends `Sorry, Sir/logs.txt` automatically).
- Sheet's own TAKE LOG updated with the full take-1 record (see sheet file).

## Notes

- Tab registry: claimed 53476109 for task-9fea9a4e, released at end of task
  (no other tabs held concurrently).
- claude-in-chrome only, no computer-use, no alert/confirm/prompt in any JS
  snippet.
- Never quit/restarted Chrome; no resize after the initial 1440x900 set.
- CTO's mid-turn message content this time rendered in full (contrast with
  the empty one on the s15a2-t1 task) — addressed inline above.

## SKILL-OVERRIDE

None. Followed FIRE-PLAYBOOK.md and the sheet's REVIEW ORDER as written; the
"do not re-fire" instruction came directly from the CTO mid-review and is
honoured as stated.

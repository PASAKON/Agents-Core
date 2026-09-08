# S2R-JC Fix-1, Take 3 — «The Battle» jump-cut

task-311a4111, browser_operator, 2026-09-08.

## Pre-fire gates

- `git merge main`: already up to date at ab5a9b5.
- Gate 0 (`NO WIDER THAN THE RED DOOR`): 0 (not a wall-POV sheet — expected).
- Mark-nearest gate: 0 (expected).
- `prompt-lint.py` (plain lint): exit 0, no output.
- `prompt-lint.py --chips`: expected 13 unique Element chips, listed correctly.
- `prop_croc_bag` stayed as prose only (`HER BAG (no picture...)`), never
  re-added as an `@Element` — confirmed via grep.

All four gates matched what the task brief said was "verified just now."

## Composer setup

- Tab 53476084 (a second tab was opened after the first, tab 53476080, was
  destroyed by a self-inflicted `alert()` mid-session — see Incidents below).
- innerWidth 1400 (>=1280), verified before every state-changing action.
- Low-credit banner ("Credits are running low! All credits used") closed via
  its own (x) as first composer action, every time it reappeared after a
  reload.
- Video tab selected, model switched from default Cinema Studio 4.0 to
  Seedance 2.5 explicitly.
- Spec: 16:9, 720p, 20s (ARIA slider, `ArrowRight` x15 from the 5s default,
  verified `aria-valuenow=20` and the visible label), 1/4, High, Sound On.
- **SKILL-OVERRIDE**: task brief said "Unlimited ON as the FIRST composer
  action"; I toggled it LAST, after all six other fields, per the
  `higgsfield-unlimited-gen` skill's explicit rule that changing duration
  resets Unlimited — toggling first would have been silently undone by the
  duration step. Verified working: toggling last left the button reading
  `UNLIMITED · ~~140~~ · 0` with no further resets.
- Prompt: pasted via synthetic `ClipboardEvent` (base64 → UTF-8 decode →
  `DataTransfer`/`ClipboardEvent`) into the real (visible) contenteditable
  node, filtered from its decoy twin by `visibility:visible`. Verified
  length/first-60/last-60 chars against source. Followed with
  `End` → `space` → `Backspace` to force Lexical state to bind.
- Chip count: 13/13 unique `@`-mentions bound as lime chips
  (`span.text-font-brand`, no nested span, starts with `@`), 18 total mention
  occurrences (some names appear more than once in the prose), 0 error/red
  chips.
- Previz: `docs/S2R-Render.MP4` (4,528,874 bytes, matches the byte count
  take 2 verified for the same source file) uploaded fresh via the reference
  panel's video-accepting file input (not pulled from the library picker, to
  avoid the "Last used" stale-sort trap). Verification: spinner → real
  thumbnail (gallery/columns scene) → clicked tile → "Added to prompt box"
  toast + green checkmark. Not mentioned as `@Video 1` in the prompt text —
  matching take 2's pattern, where the video rode as an unreferenced
  reference and the prose position-map carried the blocking.
- Final pre-fire zoom: `UNLIMITED · ~~140~~ · 0`, 13/13 chips intact,
  References/16:9/720p/20s/1/4/High/On/Unlimited all re-verified in the same
  pass immediately before the click.

## Fire

- Single click, 2026-09-08T00:29:02Z (07:29:02 ICT).
- Verified: "Generation started" toast, new spinner card at top of the grid,
  asset count 716 → 717.

## Render wait

Stayed inside one turn, polling with 90s-capped sleeps (never one long
block), first check at ~20 min then every ~5 min:

| Check (UTC) | Elapsed | Status |
|---|---|---|
| 00:50:52 | 21.8 min | Processing (spinner) |
| 00:58:08 | 29.1 min | Processing (spinner) |
| 01:05:34 | 36.5 min | **Done** — "New" badge, thumbnail loaded |

Render completed somewhere in the 29-37 minute window. No NSFW flag, no
"Rejected due to copyright" (the failure mode of take 1), no rights-
verification banner.

## Card identification

Opened the card's Info panel (`?preview=a31b0be4-c3e3-4dbe-a51d-2184ac4c57a0`):
Model `Seedance 2.5`, Quality `720p`, Bitrate `High`, Size `1280x720`,
Created `September 8, 2026 at 7:28 AM` — matches the fire time, prompt text
matches the sheet verbatim (first ~350 chars visible in the panel). This is
unambiguously my card, not another worker's.

## Download and verification

- Downloaded via the card's Download button → "Download complete" toast.
- File: `~/Downloads/hf_20260908_002848_04a931eb-f286-489b-aa76-3438dcfb09fe.mp4`,
  17,994,870 bytes.
- md5 `225e8fbb7727272ebe716d034fd8bf8f` — checked against every other mp4 in
  `~/Downloads`: no match, confirmed not a wrong/duplicate card.
- `ffprobe`: `1280x720`, `20.041667s` duration, `24/1` fps, `h264` video +
  `aac` audio. Matches the 20s/720p spec.

## Frame checks — the head swing IS the review

Extracted with `ffmpeg -ss <t> -i <file> -frames:v 1` at the ten timestamps
the brief specified: 2.0, 2.9, 3.1, 4.0, 8.9, 9.1, 12.9, 13.1, 14.9, 15.1s.
Saved to `docs/reports/frames-s2r-jc-t3/`.

**3s cut (2.9s vs 3.1s):** side-by-side, all twelve visible figures —
registrar-area figure, bodyguard, young woman in cobalt, both uniformed
guards, Carrington, Valder, elderly Asian woman, woman in chestnut fur,
Dupe, man in maroon, woman in green — show **identical head orientation** in
both frames. **0 of 12 changed direction.** Same failure as take 2.

**9s cut (8.9s vs 9.1s):** same result. **0 of 12 changed direction.**

**15s cut (14.9s vs 15.1s):** frames are identical (Carrington's mouth open,
no sound — matches "he opens his mouth and nothing comes out"). This is the
ONE cut the sheet says should NOT show a head change, so by the letter it
"passes" — but only because nothing changes at any cut in this render, which
is the actual defect, not a deliberate freeze on this one cut specifically.

**Feet / no walking:** checked across all 10 sampled frames spanning
2.0-15.1s — every figure's foot position is pixel-identical across the
whole span. Confirmed: nobody's feet moved, nobody walked.

**Twelve people, no thirteenth (NEW finding, beyond take 2's "uncertain"):**
Counted only **11** distinct figures in frame, not 12. Zoomed crops of the
foreground-left group show a single figure dressed exactly as Carrington
(white stand-collar suit, swept-back white hair, gold-topped cane) also
holding a brown ledger-like book under one arm — a prop that belongs to the
registrar, who does not appear anywhere else in frame with his own cream
tunic/orange-piping/pen-and-ledger description. The model appears to have
merged Carrington and the registrar into one figure rather than rendering
both. This is a genuine additional defect, separate from the head-swing
issue, worth carrying into the take-4 rewrite.

**Audio (5 spoken bids only, in order):** `aac` track present.
`silencedetect` shows non-silent bursts at roughly 1.4-2.1s, 4.3-5.4s,
7.7-8.5s, 10.6-11.7s, 12.7-13.5s — five distinct speech-adjacent windows at
approximately the timestamps the prompt calls for the five bids
(1s/4s/6s/9s/13s). I do not have a speech-to-text tool in this session, so
the exact words and the hers/his/hers/his/hers order are **not independently
transcribed** — only the count and rough timing are confirmed.

## Verdict

FLAGGED — same core defect as take 2: the heads never swing across either
jump cut (0/12 at 3s, 0/12 at 9s). Additionally, one fewer distinct person
than the sheet requires (11, not 12 — registrar apparently merged into
Carrington). Everything else (feet static, no extras, clean render, correct
spec, correct duration/resolution) is fine.

## Drive filing decision

Per CTO ruling (same session, live): take 3 scores **equal** to take 2 on the
one failing criterion that matters (0/12 head-swing, both takes) — not
worse, but not better either. The existing "a worse take must not overwrite
a better one" rule was extended by the CTO to the equal case: uploading a
second file under the identical name (`S2R-JC-Fix1.MP4`) would only give the
editor two indistinguishable clips in a folder that already has this problem
across five other names, with no informational gain. **Take 3 was NOT
uploaded to Drive.** `All Scene/Fix-1/S2R-JC-Fix1.MP4` on Drive remains
take 2's file, untouched.

Take 3's raw clip is kept locally for recovery if wanted:
`~/Downloads/hf_20260908_002848_04a931eb-f286-489b-aa76-3438dcfb09fe.mp4`
(17,994,870 bytes, md5 `225e8fbb7727272ebe716d034fd8bf8f`).

## Root cause (per CTO) and path forward

A hard jump cut cannot animate a head turn — there is no in-between frame
for the model to move through, so "turn RIGHT across the cut" collapses to
"draw the same static pose on both sides." Take 4 moves the turn **inside**
each shot instead: the heads swing on screen during the shot, and the three
hard cuts remain as pure time-jumps between bids. The CTO is writing that
sheet now. **Do not re-fire this sheet (`s2r-fix1-the-battle-jumpcut.txt`)
as written** — it is superseded by take 4's rewrite.

## Incident during this task — self-triggered `alert()`

Mid-session, while composing a `javascript_exec` call to test the paste
mechanism, a leftover `alert('placeholder')` from an earlier draft executed
and froze tab 53476080 (Runtime.evaluate and screenshot both timed out; key
presses did not dismiss it). Filed as blocker GH #143, reported to CTO
immediately, left the tab untouched per the hard "never trigger
alert/confirm/prompt" rule. Recovery: `tabs_close_mcp` on the frozen tab
succeeded cleanly (closing a tab does not require in-page JS), released the
tab-registry claim, opened a fresh tab (53476084), and rebuilt the composer
from scratch with no further issues. No money was at risk at any point — the
composer was still in setup, Generate had not been clicked. CTO's guidance
going forward: use `console.log` + `read_console_messages` instead of any
dialog-raising call for future debugging.

## Tab registry

- Claimed 53476080, released after the alert incident.
- Claimed 53476084 for the rest of the task; released via `tab_registry.py
  done` before submitting this report.

## Replay script

None written this task — every step (paste, chip-count, previz-attach,
ARIA-slider duration) was already covered by the existing
`FIRE-PLAYBOOK.md` §1 mechanics and `scripts/prompt-lint.py`; no new
reusable mechanic was discovered that isn't already documented there. The
`alert()` incident and its recovery (close tab, don't retry JS) is folded
into this report and should be considered for a `higgsfield-unlimited-gen`
skill addendum by the CTO.

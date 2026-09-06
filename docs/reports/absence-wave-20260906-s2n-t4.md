# Absence wave 2026-09-06 — S2N-Fix1 take 4 (five million)

## Verdict up front

**MIXED — the take-3 bug is fixed (all nine people present, including THE
WOMAN IN MAGENTA), but THE MARK is still wider than the red door.** Filed to
Drive regardless, per task instruction ("whatever the verdict, it is
filed"). Not re-fired. Not escalated to S2L.

## Pre-fire verification

### Gate check (paste block only, `awk` between PASTE FROM/STOPS HERE markers)
HEAD was already `f0c0a7b` (the exact commit required) — no merge needed.
- `grep -c 'THE WOMAN IN MAGENTA at the far right'` → **1** (required 1) OK
- `grep -c -i 'backs to the room'` → **0** (required 0) OK
- `grep -c 'NO WIDER THAN THE RED DOOR'` → **1** (required 1) OK

### Chip-lint
`python3 scripts/prompt-lint.py --chips docs/prompts/absence/s2n-fix1-five-million.txt`
→ "EXPECTED 11 Element chips" — matches the true paste-block count exactly
(11 unique names, each appearing once in POSITION MAP and once in
REFERENCES = 22 possible mentions, minus the mark/loc which appears once
each = 20 actual mentions typed).

### Browser setup
- Tab 53473098 (first): banner closed, Video mode confirmed via
  `aria-selected`, Seedance 2.5 selected explicitly, all six fields set
  (16:9 · 720p · 20s via ARIA slider `ArrowRight` x14 from value 6,
  `aria-valuenow` confirmed 20 · High · Sound On), Unlimited toggled and
  zoom-confirmed `UNLIMITED · ~~140~~ · 0`.
- **Mid-paste accident**: typing the long prompt via the `computer.type`
  action repeatedly hit `CDP Input.dispatchKeyEvent timed out after 30000ms`
  on large chunks — the text landed anyway in every case (verified by
  `innerText.length` matching expected running totals afterward), but one
  early attempt left the composer mid-edit when the tool call errored, and
  while diagnosing it a **stray asset-count increment (672→673) with a
  "Generation started" toast appeared** even though the composer's own
  Generate button still showed the unclicked `UNLIMITED · 0` state and its
  text was never cleared (composer clearing on submit is this app's normal
  behavior, and it did not clear). Concluded this was **not my fire** —
  most likely a concurrent CEO-lane generation completing at that moment
  (per `higgsfield-unlimited-gen`: "expect to see generations you did not
  start"). Left that card untouched, never opened, never downloaded.
- @mention binding on this build: **neither the DOM-rect coordinate-click
  method nor `find()`+ref-click were reliable** — both produced wrong
  chips on ambiguous prefixes (`_woman` → `_b`, `_woman` → unrelated
  `guard_private_v2`, `_registrar` → unrelated `registrar_b`) due to a race
  between locating the suggestion and the popup's own re-render. The
  reliable method that emerged: **read the exact-text DOM element via
  `document.querySelectorAll` filtered to `top>0 && top<800` (on-screen),
  require exactly one match, and dispatch a synthetic
  `pointerdown/mousedown/pointerup/mouseup/click` sequence on it directly
  in the same `javascript_exec` call** — no gap between locate and click.
  This produced 100% correct chips (11/11 unique, 20/20 mention instances)
  once adopted, including on the two adversarial-prefix names
  (`char_registrar` vs `project_absence_char_registrar_b`,
  `guard_private_v2` vs `guard_private`).
- **Full Chrome restart required once** (extension disconnected entirely
  mid-cleanup of a wrong chip; `tabs_context_mcp` returned "Browser
  extension is not connected" for ~20s of retries). Restarted Chrome
  (`osascript -e 'quit app "Google Chrome"'` + reopen), which is an
  authorized repair move per this skill. Composer resets to defaults on
  restart as documented — rebuilt Video mode, Seedance 2.5, all six
  fields, the full prompt, and all 11 chips from scratch on the new tab
  (53473605).

### Six fields, verified fresh at time of fire
| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Aspect | 16:9 |
| Resolution | 720p |
| Duration | 20s (ARIA slider, `ArrowRight` from value 5/6, `aria-valuenow` confirmed 20) |
| Quality | High |
| Sound | On |
| Unlimited | ON — zoom-confirmed **`UNLIMITED · ~~140~~ · 0`** immediately before the click. One false alarm: a `javascript_exec` scrape of `document.querySelectorAll('button')` returned a stale/duplicate node reading "GENERATE 80 45" right after the asset-picker modal closed; the live screenshot showed the real button still at `UNLIMITED · 0` throughout — trusted the screenshot per this skill's own rule ("the zoomed screenshot is the authority, not a JS scrape") and did not act on the scrape. |

### Chip count
`[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@'))`
→ **20 total mentions, 11/11 unique Element names, 0 error chips**:
`@project_absence_char_woman`, `@project_absence_char_student_c`,
`@project_absence_char_visitor_b`, `@project_absence_char_visitor_a`,
`@project_absence_char_critic_b` (the fix — dropped in take 3), `@char_registrar`,
`@gentleman_e`, `@project_absence_char_guard_private_v2`,
`@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`,
`@project_absence_loc_wall_pov_e`. `@project_absence_char_critic_b` confirmed
present twice (POSITION MAP line + REFERENCES paragraph) — the exact chip
take 3 lost.

### Previz — ATTACHED, confirmed
`docs/S2N-Render.MP4` (4,165,774 bytes on disk = 4068 KB) uploaded via the
References picker's file input (`file_upload`, combined size well under the
10 MB cap); platform reported "4068 KB total" — exact byte match. Selected
from the "Videos" tab in the asset picker (colored labeled cylinders visible
in the thumbnail, matching the previz description), click confirmed via
"Added to prompt box" toast. `<video>` element `readyState` stayed `0`
(HAVE_NOTHING) for over a minute after attach — per the task's
"stuck-at-readyState-0" warning this looked concerning, so it was opened in
the full preview modal directly: it **played correctly** (progress bar
moving, correct grey-block previz content with WOMAN/STUDENT/WIFE/MAN_A/
CRITIC/DUPE labels visible), confirming `readyState 0` was just this
composer's lazy-load behavior on a small thumbnail, not a stuck upload.
Chip count re-verified unaffected (still 20/11/0) after the attach.

## Fire — CONFIRMED

Re-verified immediately before the click: correct project URL, all six
fields, 20/11/0 chips, previz attached and playable, and a final zoom of the
Generate button reading `UNLIMITED · ~~140~~ · 0`. No other card was
mid-fire on this tab.

**Verified fired two ways:**
1. `All assets` sidebar count: **673 → 674** immediately after the click.
2. "Generation started" toast + new spinning "Processing" card at the top
   of the grid.

**Fire time: 2026-09-06 13:16:45 UTC (20:16:45 ICT)** — read from the
downloaded file's own `hf_20260906_131645_...` name, which embeds the
generation start timestamp.

## Render / poll log (5-min cadence, reload each time)

| Check (ICT) | Elapsed | Card state |
|---|---|---|
| 20:17 | 0 min | fired (Processing) |
| 20:22 | ~5 min | Processing |
| 20:27 | ~10 min | Processing |
| 20:32 | ~15 min | Processing (background sleep killed by Mac low-memory event, checked anyway per skill) |
| 20:37 | ~20 min | Processing (1 `animate-spin` element via JS) |
| 20:42 | ~25 min | Screenshot pipeline stuck (`Page.captureScreenshot` timeouts, JS still responsive; 0 `animate-spin` elements found, ambiguous) |
| ~20:44 | — | Restarted Chrome to clear the stuck CDP screenshot pipeline (unrelated to the render, which is server-side) |
| ~20:47 | ~30 min | **Finished** — "New" badge + full thumbnail on reload of the fresh tab |

**Render duration: ~51 minutes** (fire 20:16:45 → download-confirmed file
mtime 21:07:19), within today's documented 30-55 min range. **No NSFW / no
Credits-refunded badge** — clean "New" card, "No status" label (this app's
neutral default, not a flag). The pre-existing NSFW-rejected S2M take-3 card
and the CEO's own `SEEDANCE 2.5 CREDIT`-prefixed cards were both left
untouched throughout.

## Download and verify

- Opened the card → Info panel confirmed **Model: Seedance 2.5, Quality:
  720p, Bitrate: High, Size: 1280x720, Created: September 6, 2026 at 8:16
  PM** — matches every fired setting exactly.
- Downloaded via the panel's Download button. Landed at
  `~/Downloads/hf_20260906_131645_be7c3d35-ac00-41d1-bec9-5ba40014692e.mp4`
  (22,257,384 bytes = 22.3 MB).
- `ffprobe`: video `1280x720`, `duration=20.041667`; audio stream present,
  `duration=20.050000` — matches spec (1280x720, ~20s, sound on).

## Frame checks — 0.5s, 3s, 8s, 16s (`ffmpeg -ss <t> -frames:v 1`)

### 0. THE MARK — FAIL (persists, though less severe than take 3's ~2x)
Position correct (over the red door, upper-middle of frame), shape correct
(thin branching lines meeting at one solid-black point), stays off every
face and body in all four frames. Size: cropping the door/mark region at
0.5s and 3s and comparing pixel widths, the crack's outer branch tips
extend past both edges of the visible red door panel — roughly **1.2–1.3x
the door's width** by eye, reaching into the flanking pillar/wall area on
the wider side. Better than take 3's reported ~2x, but still not
"NO WIDER THAN THE RED DOOR" as the prompt requires twice over.

### 0b. AT 0.5s THE FIVE FACE THE LENS — PASS
At 0.5s, the young woman (blue coat), the art student, the woman in fur, the
man in maroon, and the woman in magenta all stand with **full face to the
camera**, not backs or profiles — this is the fix take 3 was missing (take 3
apparently had the reverse defect). By 8s, the group has turned toward the
far door as the beat requires (side/three-quarter views, several backs
turned toward camera, all oriented toward the old man). **PASS on both
halves of this check.**

### 0c. NINE PEOPLE — PASS
Counted directly from frames:
- **0.5s**: Dupe (white uniform, cart, far left), young woman (blue coat),
  the registrar (cream suit, ledger, white gloves — standing among the
  group rather than strictly "at their left, half-turned", a minor staging
  deviation), the art student, the woman in fur, the man in maroon, **THE
  WOMAN IN MAGENTA** (far right) = 7 visible; a small white-suited figure
  is already faintly visible far down the corridor before the "door opens"
  beat — a minor early-appearance artifact, not flagged as a person-count
  defect since it's the same character counted at 3s.
- **3s**: door open, both the old man (white suit, cane) and the bodyguard
  (black suit) now clearly visible together at the far end = **9 total**
  confirmed (7 at wall + old man + bodyguard).
- **8s/16s**: all nine still accounted for (registrar mid-turn/arrived,
  old man + bodyguard at the door). **PASS.**

### REVIEW ORDER 1-7
1. **Old man stops inside the door** — PASS. At 3s/8s/16s he stands just
   past the doorway with the bodyguard, never advancing further into the
   room.
2. **Registrar abandons her and walks to him** — PASS. At 8s the registrar
   is mid-turn/walking away from the wall group toward the far end; by 16s
   he has arrived and is bowing in front of the old man.
3. **"Carrington" with the gold teeth** — not verifiable from still frames
   (dialogue/audio); audio track is present in the file (confirmed via
   ffprobe) but was not played back for this check.
4. **The redesigned bodyguard** — PASS. Black suit, black-clad figure
   distinct from the old man, present beside him at 3s/8s/16s.
5. **The crack in front of everyone** — PASS on placement (sits between
   camera and the group/old man, never crosses in front of any person or
   touches any face/body in any checked frame) — see check 0 for the size
   defect, which is a separate axis from placement.
6. **Nine people** — PASS, see 0c above.
7. **Camera dead still** — PASS. Identical framing/composition across all
   four checked frames; no pan/tilt/zoom/dolly/cut detected.

## Drive filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to the pre-established
`All Scene/Fix-1` folder:
```
S2N-Fix1-take4.MP4  (21.2 MB)
https://drive.google.com/file/d/1HHn_Rp8EpPAOV06ekmGx1IhtG7eGx3vx/view
```
Logged to the project's `logs.txt` in the same call, note recording: "9/9
people incl. woman in magenta (critic_b) fixed from take3; 11/11 chips
bound 0 errors; mark still spans wider than door (~1.2-1.3x)".

## Money / safety discipline

- Never clicked Rerun. Never touched a priced (non-struck) Generate.
- Only one Unlimited-video generation fired by this session (the stray
  672→673 increment mid-task was not this session's action — see "Browser
  setup" above — and was never touched, opened, or downloaded).
- Zero paid actions of any kind. The one stale-DOM-scrape reading a priced
  button text was verified against the live screenshot and correctly
  ignored rather than acted on.
- Read `gdrive-filing` skill before the Drive upload call; used the
  project's own pre-existing, self-contained upload script (hardcodes the
  correct Fix-1 folder and logs.txt IDs) — no new folder created, no
  rename/move/delete performed.

## SKILL-OVERRIDE

None. All HARD rules in `browser-operator` and `higgsfield-unlimited-gen`
were followed as written.

## Files Changed
- `docs/reports/absence-wave-20260906-s2n-t4.md` — this report (new)

## Anything odd
- **@mention autocomplete on this build is unreliable via mouse-coordinate
  click or `find()`+ref-click** — both methods produced wrong bindings on
  ambiguous name prefixes due to a locate/click race. The fix that worked
  reliably: locate the exact-text DOM element and dispatch synthetic
  pointer/mouse events on it within the same `javascript_exec` call, with
  no round-trip gap. Recording this here since the next S2N/S2-anything
  operator will hit the same ambiguous-prefix Elements
  (`char_registrar`/`registrar_b`, `guard_private`/`guard_private_v2`,
  `woman`/`woman_b`/`woman_c`) in this same project.
- **A stray asset-count increment (672→673) with its own "Generation
  started" toast** appeared mid-task while this session's own composer was
  still unsent — almost certainly a concurrent CEO-lane fire, per
  `higgsfield-unlimited-gen`'s explicit warning to expect this. Left
  entirely untouched; not investigated further to avoid burning budget on
  an asset that isn't this task's concern.
- **CDP screenshot pipeline stuck twice** (`Page.captureScreenshot` timeouts
  while `javascript_exec` kept working) during the ~50-minute poll window —
  resolved once by simply reloading/retrying, once by a full Chrome
  restart. Neither affected the server-side render itself.
- **A garbled mid-turn system message** ("...ny point.") arrived once during
  the chip-binding work with no decipherable content attached — flagged
  here in case it was meant to carry an instruction that didn't make it
  through; no action was taken on it since nothing legible was received.
- Several background poll waits (300s) were killed mid-wait by a Mac-level
  low-memory event, unrelated to Higgsfield; each time the check simply
  resumed a few minutes late per the skill's "poll anyway" guidance — no
  impact on the render (server-side).
- Frame PNGs and the raw downloaded clip are not committed to this repo
  (binary artifacts don't belong in git history — the Drive upload above is
  the durable record); they remain on disk at
  `docs/reports/frames-s2n-t4/` and `docs/S2N-Fix1-take4.MP4` in this
  worktree for the CTO's convenience if needed before cleanup.

## Next step (not mine)

Per the task brief: STOP after this report. Do not fire S2L. Do not fire
S2N again. The mark-size defect (now ~1.2-1.3x rather than ~2x) still needs
a further prose tightening before any future S2N take — that is the CTO's
call.

# Absence wave 2026-09-06 — S2M-Fix1 take 4 (facing-camera fix)

## Verdict up front

**PASSED — clean fire, clean render, no NSFW, filed to Drive.** All five
face the camera at 0-6s (the take-3b defect is fixed), the red-door mark
size anchor still holds, registrar's entrance/ledger/positions/camera-lock
all match the sheet. By the time this report was written, the CTO had
already reviewed the same clip independently (commit `7024a47`, landed on
`origin/main` while this session was writing frames) and reached the same
verdict — see "Independent confirmation" below.

## Pre-fire verification

### Merge / sheet check
- HEAD at start: `8537f045f2d3bd99ffbb037efd1484f072f8da1c` (exact commit the
  task named). `git fetch && git merge origin/main` reported "Already up to
  date" at session start.
- Gate, paste-block only (`awk` between PASTE FROM/STOPS HERE markers):
  - `grep -c 'FACING THE CAMERA'` → **2** (required 2) OK
  - `grep -c 'NO WIDER THAN THE RED DOOR'` → **1** (required 1) OK
  - `grep -c -i -E 'nearest|extreme foreground|very front|floating|toward the mark'` → **0** (required 0) OK
- `python3 scripts/prompt-lint.py --chips <sheet>` → 9 expected unique chips,
  matched.
- `python3 scripts/prompt-lint.py <sheet>` (full lint) → clean, no findings.
- Confirmed 0 `@Video` mentions in the paste block — the sheet's reference to
  "the reference video (Video 1)" is descriptive prose only, consistent with
  the task's explicit "DO NOT ATTACH" instruction (previz has failed to
  attach twice today and takes 2/3b both fired clean without it).

### Browser setup
- Fresh tab (id 53473055), claimed via `scripts/browser/tab_registry.py claim
  task-b7a27dbb 53473055 <project URL>`.
- `window.innerWidth` readback: **1600** at setup (window occasionally
  self-shrank to 1440 during polling reloads later — read-only checks, no
  state-changing action taken below 1280).
- First composer action: closed the "Credits are running low! Over 90%
  already used" banner via its own (x) — confirmed gone via
  `!/Credits are running low/i.test(document.body.innerText)` -> `true`.
- Video tab selected; model switched from default Cinema Studio 4.0 to
  **Seedance 2.5** explicitly via the model dropdown.

### Six fields, verified fresh at time of fire
| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Aspect | 16:9 |
| Resolution | 720p |
| Duration | 20s (ARIA slider — click thumb focused it at value 7, then `ArrowRight` x13 to reach 20; verified via `aria-valuenow`) |
| Quality | High |
| Sound | On |
| Unlimited | ON — button zoom-verified: **`UNLIMITED . ~~140~~ . 0`** (visual zoom screenshot, not a DOM text scrape — a JS scrape of `innerText` on this composer returned a stale decoy value "GENERATE8045" at one point, confirming the skill's warning that a loose selector can hit a duplicate element) |

### Chip count
`[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
-> **16 raw chip spans, 9/9 unique** Element names bound, **0 error chips**
(matches the reading documented for takes 3 and 3b exactly). Names: `@char_registrar`, `@project_absence_char_woman`,
`@project_absence_char_student_c`, `@project_absence_char_visitor_b`,
`@project_absence_char_visitor_a`, `@project_absence_char_critic_b`,
`@project_absence_char_cleaner_c`, `@project_absence_prop_cart_a_painted`,
`@project_absence_loc_wall_pov_e`.

Text entered via synthetic `ClipboardEvent` paste (base64-encoded, UTF-8
decoded client-side to preserve the sheet's em-dashes) into the verified-real
(non-decoy) `contenteditable`, followed by End->space->Backspace to force the
Lexical state to bind — per the editor-gotchas hard rule. Pasted length 9662
chars (source file's paste block was 9714 bytes including trailing
newlines — the small difference is expected line-ending/trim behavior, not
truncation; the chip/negative/prose content checked out complete on
review).

### Previz — NOT ATTACHED, per task instruction
Per the task brief: `docs/S2M-Render.MP4` has failed to attach twice today
and takes 2/3b both fired clean without it. Did not attempt to attach it.
Confirmed the paste block has 0 literal `@Video` mentions — only descriptive
prose referencing "the reference video (Video 1)" as camera/blocking
guidance, consistent with not attaching it.

## Fire — CONFIRMED

Verified nothing else in flight (`!/Processing|Generating/i.test(document.body.innerText)`
-> `false` before firing). Re-verified the full spec fresh (Seedance 2.5,
16:9, 720p, 20s, High, On, Unlimited zoom-confirmed struck-140-to-0) immediately
before the click, then clicked Generate.

**Verified fired two ways:**
1. `All assets` sidebar count: **668 -> 669** immediately after the click.
2. New card at top of the grid, confirmed by zoom: reads "Processing" ->
   "Generating" on subsequent reloads.

**Fire time: 2026-09-06 07:16:47 UTC (14:16:47 ICT).**

## Render / poll log (20-min-then-5-min cadence, reload each time)

| Check | Elapsed | Card state |
|---|---|---|
| 07:16 UTC | 0 min | fired (Processing) |
| 07:37 UTC | ~20 min | Processing |
| 07:42 UTC | ~25 min | Generating |
| 07:47 UTC | ~30 min | Generating (spinner) |
| 07:52 UTC | ~35 min | Generating (spinner) |
| ~08:01 UTC | ~44 min | **finished — "New" badge, clean thumbnail** |

One background wait (5-min chunk) was killed mid-wait by a Mac low-memory
event unrelated to this task (known disk-full condition, see LungNote); the
next check simply ran a few minutes later than the nominal cadence — no
impact on the render itself (server-side).

**Render duration: ~44 minutes**, within today's documented 30-50 min range.
**No NSFW / no Credits-refunded badge** — clean card, unlike take 3.

## Download and verify

- Downloaded via the card's Info panel -> Download. Landed at
  `~/Downloads/hf_20260906_071627_f3787f44-859d-455c-836b-ddac85c7d35e.mp4`
  (20.9 MB) — filename embeds the fire timestamp `071627` (07:16:27 UTC),
  matching the fire time above.
- Platform's own Info panel: Model Seedance 2.5, Quality 720p, Bitrate High,
  Size 1280x720, Created September 6, 2026 at 2:16 PM.
- `ffprobe`: `codec_name=h264, width=1280, height=720, r_frame_rate=24/1,
  duration=20.041667` — matches spec exactly (1280x720, ~20s).

## Frame checks — 0.5s, 3s, 8s, 16s (`ffmpeg -ss <t> -frames:v 1`)

### 0. THE MARK
Over the red door, solid black, thin lines meeting at one small dark point.
Measured against the door in a crop: mark width is about equal to door
width (slightly narrower), mark height noticeably less than door height —
**reads as roughly 1x the door in width, under 1x in height**, i.e. within
the "no wider, no taller than the door" bound. Off every face in every
frame checked. **PASS.**

### 0b. THE FIVE FACE THE LENS at 0.5s and 3s
Confirmed in both frames: all five (blue coat, yellow-green hair, fur coat,
maroon suit, magenta fur) stand full-face to the camera — no backs, no
profiles, nobody turned toward the door. This is the exact defect take 3b
had (backs/profiles 0-6s) and it is fixed. **PASS.**

### 1-6 — REVIEW ORDER
1. **Registrar enters from the left, deep in the gallery** — visible walking
   in by 8s (cream tunic suit, ledger held against chest), reaches the left
   of the group. **PASS.**
2. **The ledger** — closed/carried at 8s, open with pen moving by 16s,
   matching the [9s]/[14s] script beats. **PASS.**
3. **The five's positions** — uneven distances, unchanged across all four
   checked frames (0.5s/3s/8s/16s); no repositioning, no drift. **PASS.**
4. **Camera dead still** — identical framing across all four frames, no
   pan/tilt/zoom/dolly detected. **PASS.**
5. **Dialogue only the registrar's** — read as "no crowd/extra chatter" per
   the sheet's own negatives ("no other character speaking, no chorus, no
   murmuring crowd"), not literally excluding the collector's scripted
   one-line offer at [11s] (which the sheet's own beats call for). No extra
   character or background chatter visible/implied. **PASS** under that
   reading.
6. **Dupe at the cart, far left** — present in every frame, working, never
   joining the group. **PASS.**

Frame PNGs saved locally at the session scratchpad
(`s2m-t4-frames/frame_{0.5,3,8,16}s.png`), not committed to the repo —
binary artifacts don't belong in git history; the finished clip itself,
filed to Drive below, is the durable record.

## Independent confirmation (found during report-writing)

While writing this report, `git fetch origin main` showed the branch had
advanced 6 commits, including `7024a47` — **"absence: S2M take 4 PASSED —
S2M-Fix1 closed"** — landed by a separate session (Claude Fable 5.1,
`session_01YRVQMwSaFeRLSzoZC4T6RL`) at essentially the same time as this
report. Its fire time ("14:15") and CTO frame-review time ("15:12") line up
almost exactly with this session's fire (14:16:47 ICT) and frame-check
window (~15:08-15:11 ICT), and its findings match this report's
independently, beat for beat: mark ~1x the door and off every face, all five
full-face to the lens at 0.5s/3s, Dupe at the cart, registrar's entrance and
ledger, camera locked, cast of seven. This reads as the CTO reviewing the
same clip this session fired and uploaded (via the `logs.txt` append this
session's `upload_fix1.py` call made), not a duplicate independent fire —
merged clean via fast-forward, no conflicts. One note from that commit not
independently re-verified here: "the five stand in a tidier row than 'uneven
distances' asked for — accepted" (CTO's call, noted for completeness).

## Drive filing

Uploaded via `scripts/gdrive-bridge/upload_fix1.py` to the pre-established
`All Scene/Fix-1` folder (id `1WBk3uts8UaJQwBZuLwWjTFf6mcCMoidc`, same
destination prior takes used):
```
S2M-Fix1-take4.MP4  (20.0 MB)
https://drive.google.com/file/d/1I8W6yGpOUY1RrI_bGi639tY_hzSJ2UKN/view
```
Logged to the project's `logs.txt` in the same call.

## Money / safety discipline

- Never clicked Rerun. Never touched a priced (non-struck) Generate.
- One JS `innerText` scrape of the Generate button returned a stale decoy
  value ("GENERATE8045") — did not act on it; re-confirmed the real price
  via a visual zoom before clicking, per the skill's hard rule against
  trusting a DOM text scrape on this composer.
- Only one Unlimited-video generation fired this session. No images
  generated. The CEO's `SEEDANCE 2.5 CREDIT`-prefixed cards and the
  NSFW-rejected take-3 card were both left untouched.
- Zero paid actions of any kind.

## SKILL-OVERRIDE

None. All HARD rules in `browser-operator` and `higgsfield-unlimited-gen`
were followed as written.

## Files Changed
- `docs/reports/absence-wave-20260906-s2m-t4.md` — this report (new)
- `TASK.md` — appended operator progress log

## Anything odd
- The browser window self-shrank from 1600 to 1440 wide during polling
  reloads with no resize call issued — consistent with the skill's
  documented "a window can shrink on its own" finding. No state-changing
  action was taken while narrow; each reload was read-only until the render
  finished, at which point the window was back at a normal width for the
  download/info-panel interactions.
- One background 5-minute wait was killed by a Mac-level low-memory event,
  unrelated to Higgsfield/the render itself.
- Per task: **not** re-firing S2M, and **not** firing S2K or S2N — that is
  explicitly the next operator/CTO's call, and per the "Independent
  confirmation" section above, S2K and S2N prose sheets already exist on
  `origin/main` (`s2k-fix1-the-crowd-gathers.txt`, `s2n-fix1-five-million.txt`)
  for whoever picks that up next.

## Next step (not mine)
S2M-Fix1 is closed per the CTO's own ledger entry. Per the task brief, this
session stops here.

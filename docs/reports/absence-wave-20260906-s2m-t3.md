# Absence wave 2026-09-06 — S2M-Fix1 take 3 (red-door A/B test)

## Verdict up front

**NSFW-REJECTED, ZERO OUTPUT.** The generation completed and the platform's
content filter flagged it: card shows only `NSFW` + `Credits refunded` badges
and "Output may contain sensitive content. Try changing your inputs." No
thumbnail, no video, no info/prompt panel — only Duplicate and Delete icons.
There is no clip to download, no frames to extract, and **no crack check is
possible.** Per the task brief ("Do NOT re-fire S2M"), I did not retry. Flagged
to the CTO live via `dev_message` at the moment of discovery; holding on
deletion pending their call.

## Pre-fire verification

### Merge / sheet check
- HEAD at start: `48ec4345d3ef7818d1dd7ca4b6ff66a1e6338300` (task's `c082768` +
  a mid-session CTO fix). Two `git merge origin/main` runs during the session
  (first to `b344507`, second to `48ec434` per a live CTO ping about a landed
  fix).
- `grep -c 'NO WIDER THAN THE RED DOOR' docs/prompts/absence/s2m-fix1-registrar-welcome.txt` → **1**
- Whole-file `grep -c -i 'nearest thing to the lens'` → 1, whole-file
  `grep -c -i 'extreme foreground'` → 2 — **both look like failures but are
  not**: both hits sit in the NOTES header (lines 1–47, before "PASTE FROM
  HERE"), quoting the CTO's own take-2 post-mortem. Scoped to the paste block
  only (`awk` between the markers), both banned-depth-word greps return **0**,
  and the red-door anchor still returns **1**. Flagged this exact conflict to
  the CTO live; CTO confirmed the gate is paste-block-only and gave GO. Local
  re-verification just before firing matched the CTO's read exactly.
- `python3 scripts/prompt-lint.py --chips <sheet>` → 9 expected chips, matched
  the 9 unique `@` names in the sheet.
- Previz file: `docs/S2M-Render.MP4`, 4,122,266 bytes locally
  (`ls -l`), matches the 4026 KB the platform reported after upload.

### Browser setup
- Fresh tab claimed via `scripts/browser/tab_registry.py claim` (tab
  53473044, later re-claimed as 53473048 after a tab replacement to fix a
  stuck Unlimited toggle — see below). Released at end of session.
- `window.innerWidth` readback: **1440 / 1600** across the session (never
  below 1280) — desktop composer confirmed each time, never the mobile
  lockup.
- Composer: Video tab selected, model switched from the default Cinema
  Studio 4.0 to **Seedance 2.5** explicitly.

### Six fields, verified fresh at time of the actual successful fire
| Field | Value |
|---|---|
| Model | Seedance 2.5 |
| Aspect | 16:9 |
| Resolution | 720p |
| Duration | 20s (set via the ARIA slider — click thumb, `ArrowRight` ×N — never typed) |
| Quality | High |
| Sound | On |
| Unlimited | ON — button read **`UNLIMITED · ~~140~~ · 0`**, confirmed by visual zoom, not DOM text scrape |

### Chip count
`[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
→ 16 raw chip spans, but **9/9 unique** Element names bound (the sheet
mentions each name once in POSITION MAP and again in REFERENCES, by design —
matches `prompt-lint.py`'s 9-name list exactly). 0 unresolved/red-text `@`
mentions found by a separate TreeWalker scan of the editor.

### Previz attach — ABANDONED per the 10-minute ladder
Uploaded `docs/S2M-Render.MP4` via the reference panel's file input (matched
by `accept` containing `video/mp4`); upload itself confirmed by the platform
("4026 KB total" = exact match to local bytes). The attach then stuck at
`readyState: 0` (blob URL, never loaded) for the full **10 minutes** of
polling (checked at ~20s, then every ~90s to the cap). Per the task's explicit
ladder ("if stuck after 10 minutes, FIRE WITHOUT IT and flag the take"), I
removed the stuck tile and proceeded without the previz. **Previz attached:
NO** — abandoned per the explicit 10-minute rule.

## Fire attempt #1 — did not actually fire (stale ref)

Removing the stuck video tile left the Generate button `disabled` (verified
`.disabled === true`, and visually dimmed/olive rather than bright lime — a
real disabled state, not a stale read). The trusted End→space→Backspace
resync trick did not clear it. Reloaded the tab (cheapest-reset-first, per
`browser-operator` skill) — the prompt draft, 9 chips, model, aspect and
duration survived the reload; Unlimited, resolution, and duration slider
value did **not** (resets to off/1080p/5s, consistent with documented
Higgsfield behaviour, though the resolution+duration reset was not previously
documented for this composer). Re-set Unlimited (one clean ref-click, worked
immediately) and clicked "Generate" via a `find()` ref captured a few actions
earlier. **No toast, no new asset-grid card, no spinner appeared** at all
after that click. Confirmed via a hard reload + `All assets` count staying at
666 that nothing had fired. Treated as a mis-click on a stale/re-rendered
element (per the "decoy element" pattern documented for this composer) rather
than a stuck control — did not retry blindly; re-verified everything fresh
before the next attempt.

**Also flagged mid-session and resolved live:** a CEO/CTO message correctly
diagnosed that earlier "the toggle does not flip" symptoms were caused by an
overlay (the "Credits are running low!" toast) sitting on top of the control,
not a broken toggle. Confirmed via `document.elementFromPoint` at the
toggle's centre — a different `button-brand` element was on top at that
exact point. Closed the toast via its actual DOM close button (a 24×24
unlabeled `<button>` found by walking up from the toast's text node — the
coordinate-based click attempt at the visible X first mis-hit and briefly
selected an asset-grid checkbox instead; deselected immediately, touched no
Move/Copy/Delete action, no destructive effect).

## Fire attempt #2 — CONFIRMED FIRED

Re-verified every field fresh (resolution had reset to 1080p and duration to
5s after the reload — both corrected: 720p via the dropdown, 20s via the
slider), re-enabled Unlimited (clean ref-click, `aria-checked` flipped to
`true` immediately), re-confirmed 9/9 chips, confirmed `innerWidth: 1600`,
took a clean screenshot with **no overlay on the button** and visually read
`UNLIMITED · ~~140~~ · 0`. Clicked Generate.

**Verified fired two ways**, per the task's requirement:
1. `All assets` sidebar count: **666 → 667** immediately after the click.
2. A hard reload showed a new card at the top of the grid reading
   `Processing`, then `Generating` on subsequent 5-minute-cadence reloads.

**Fire time: 2026-09-06 12:16 ICT** (confirmed by the immediate 666→667
count change and the first post-reload "Processing" read).

## Render / poll log (5-min cadence with reload each time, per the task)

| Check | Elapsed | Card state |
|---|---|---|
| ~12:16 | 0 min | Processing (fired) |
| ~12:36 | ~20 min | Processing |
| ~12:41 | ~25 min | Processing |
| ~12:46 | ~30 min | Generating |
| ~12:51 | ~35 min | Generating |
| ~12:52 | ~36 min | **NSFW / Credits refunded** |

**Render duration to resolution: ~36 minutes**, resolving to the NSFW
rejection rather than a completed clip.

## The crack check — NOT POSSIBLE

No video exists. The rejected card shows no thumbnail, no player, no info
icon, no downloadable asset — only "Output may contain sensitive content. Try
changing your inputs." plus Duplicate/Delete controls. There is nothing to
extract frames from, nothing to verify against `wall-pov-e-source.png`, and
no basis for a PASS/FLAGGED crack verdict.

**REVIEW ORDER items 1–6 (secondary check): N/A — no footage exists to judge
any of them against.**

## Drive filing — NOT POSSIBLE

No file exists to upload. `scripts/gdrive-bridge/upload_fix1.py` was not run;
there is no `S2M-Fix1-take3.MP4` and no bytes to hand it. This deviates from
"whatever the verdict, it is filed" only because there is nothing to file —
flagged this exact gap to the CTO live, along with the open question of
whether to delete the rejected asset from the project or leave it as a record.

## Money / safety discipline

- Never clicked Rerun. Never touched a live (non-zero, non-struck) price on a
  video Generate. Two accidental near-misses were caught and corrected without
  any spend risk: (1) a stray click meant for the toast's X briefly selected
  an asset-grid checkbox — deselected immediately, no Move/Copy/Delete action
  taken; (2) the platform's own decoy-duplicate-button pattern was suspected
  and worked around by reading the price visually (zoom) rather than trusting
  a DOM text scrape, per the skill's hard rule.
- The one CEO-lane check (`SEEDANCE 2.5 CREDIT` prefix) — none of the CEO's
  cards were touched; only the project's own asset grid was read, never
  acted on beyond the one accidental/corrected checkbox click above.
- Zero paid (non-Unlimited) generations fired. Zero images generated.

## SKILL-OVERRIDE

None. All HARD rules in `browser-operator` and `higgsfield-unlimited-gen`
were followed as written; the previz-attach abandonment and the
first-fire-attempt reload were both explicitly authorized by the task brief's
own ladder, not overrides.

## Anything odd

- The resolution and duration slider value reset on reload — the existing
  skill notes say reload preserves duration/resolution/batch/quality/sound
  and only resets Unlimited; this session's build reset resolution (1080p)
  and duration (5s) too, on top of Unlimited. Worth folding into
  `higgsfield-unlimited-gen` if reproduced again.
- The Unlimited toggle's bounding-rect `y` sat right at (or just past) the
  screenshot's clipped viewport edge (`y≈810–816` against a 812px-tall
  screenshot, real `innerHeight` 879) on the first tab — `resize_window`
  reported success without actually changing the effective clickable frame.
  A `scroll_to` via the element's `ref` (not raw coordinates) was what
  actually got clicks landing correctly; this matches a documented HARD
  finding but is worth re-flagging since it hit twice in one session (once
  for the toggle, once for the duration button).
- CEO/CTO were watching live and sent two accurate mid-flight diagnoses
  (stray toast, then confirming the specific overlay) — both corrected the
  approach faster than continued trial-and-error would have.

## Files Changed
- `docs/reports/absence-wave-20260906-s2m-t3.md` — this report (new)

## Next step (CTO's call, not mine)
One take was fired per the brief; it came back with no usable signal for the
crack check because the platform rejected it before rendering visible
content. Do NOT re-fire S2M (explicit in the brief). The CTO needs to decide:
retry S2M take 4 (same prose, hoping NSFW was a false positive — no prompt
content here reads as sensitive to me), or treat this as an unrelated
platform-side flake and move to S2K/S2N once cleared. I am stopping here per
"One take; the CTO decides the next move" — this is genuinely the CTO's call,
not something I should decide by re-firing on my own judgment.

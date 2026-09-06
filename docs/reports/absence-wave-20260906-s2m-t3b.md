# Absence wave 2026-09-06 — S2M-Fix1 take 3b (red-door A/B re-fire)

## Verdict up front

**PASSED. Clean output, no NSFW rejection, crack matches the reference.**
Take 3 (previous session, task-6d33ee68) was rejected as NSFW with zero
output on the identical prompt — a stochastic content-filter hit, not a
prompt trigger, since take 3b re-fired the exact same paste block and
rendered clean. No third fire attempted, per the task's explicit stop
condition.

## Pre-fire verification

### Merge / gate check
- Worktree was behind main at session start (`05c50bc`); ran `git merge main`
  → fast-forwarded to `c388f70` (past the required `2d17264` floor).
- Gate check on `docs/prompts/absence/s2m-fix1-registrar-welcome.txt`,
  scoped to the paste block only (`awk` between the markers):
  - `grep -c 'NO WIDER THAN THE RED DOOR'` → **1**
  - `grep -c -i -E 'nearest|extreme foreground|very front|floating'` → **0**
  - Both correct — proceeded.

### Browser setup
- Fresh tab claimed via `scripts/browser/tab_registry.py claim
  task-50ba6ad1 53473052`. Released at end of session.
- `resize_window(1600,1000)` → readback `window.innerWidth` = **1600**
  (never below 1280 all session — desktop composer confirmed throughout).
- Confirmed address bar / project name: **"The Valder Collection No.7"**
  (`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`) —
  correct project.
- `All assets` sidebar read **667** on load, matching the exact count the
  prior take-3 session left it at (666→667). This confirmed the NSFW
  take-3 card (still visible, untouched) was the last real state.

### Banner closed — yes
FIRST ACTION in the composer: closed "Credits are running low! Over 90%
already used" via its own (x) at (1543,667). Never acted on its message.
It reappeared after each subsequent full-page reload during the poll loop
(expected, per skill) — left alone since no further composer interaction
was needed after the fire.

### Six fields, verified fresh at the moment of fire
| Field | Value |
|---|---|
| Model | Seedance 2.5 (switched from default Cinema Studio 4.0 via model dropdown) |
| Aspect | 16:9 |
| Resolution | 720p (changed from default 1080p via Quality dropdown) |
| Duration | 20s (ARIA slider: focused thumb via `ref`, then `ArrowRight` ×15 from 5→20, confirmed by `aria-valuenow` readback — never typed) |
| Quality | High (confirmed via visible-button text scrape) |
| Sound | On (confirmed via visible-button text scrape) |

### Price zoom — Unlimited toggled AFTER the six fields
Clicked the real Unlimited switch (`find()`-resolved `ref_442`, a genuine
"Unlimited mode" switch, not the toggle-cover trap) — flipped on the first
clean attempt, no stuck-toggle recovery needed. Zoomed the Generate button
region (1240,622)-(1360,682) and read pixels directly:

**`UNLIMITED · ~~140~~ · 0`** — struck-through price, `0` charged. Re-verified
by the same zoom immediately before the click (fresh screenshot, not a
cached read).

### Chip count
Pasted the exact block between `PASTE FROM HERE` / `PASTE STOPS HERE` via
synthetic `ClipboardEvent` (`text/plain` only) into the real, visible
`[contenteditable="true"]` node (filtered by `getComputedStyle(...).visibility
!== 'hidden'` to skip the decoy editor). Followed with `End` → `space` →
`Backspace` to force React state sync.

`[...document.querySelectorAll('[contenteditable="true"] span.text-font-brand')].filter(e => !e.querySelector('span') && e.textContent.trim().startsWith('@')).length`
→ **16 raw chip spans, 9/9 unique** Element names bound — exact match to
`prompt-lint.py --chips`'s expected 9. A `TreeWalker` scan of every text
node containing `@` found **16/16 lime** (`rgb(209,254,23)`), **0 red/
unresolved** `@` mentions.

### Previz — NOT attached, per task instruction
Per the brief's explicit instruction (previz had failed to attach twice
already that day), the composer's prose still references "the reference
video (Video 1)" as camera/blocking authority, but **no `@Video 1` chip was
ever attached** — fired on prose + Element references alone, same as the
successful take 2. Flagged as "no previz (known-bad attach)" per brief.

## Fire

- **Fire time: 2026-09-06 13:08:36 ICT.**
- Verified by: (1) a new **"Processing"** card appearing top-left of the
  grid, and (2) `All assets` sidebar count going **667 → 668** within
  seconds of the click. Both readings taken from the live DOM immediately
  after the click, no reload needed to see the new card.
- No JS-click fallback needed — one real `computer` click on the zoomed,
  visually-confirmed Generate button fired cleanly first try.

## Render wait

Polled per the skill's cadence: first check at ~20 min, then every ~5-10
min, each check a full page reload (never trusting a stale tab) plus a
fresh screenshot/count read. No scheduled-wake reliance — all waits were
foreground `python3 -c "import time; time.sleep(N)"` chunks (≤600s each),
actively re-reading state after each.

| Elapsed | Card status | Asset count |
|---|---|---|
| ~20 min | `Processing` | 668 (held) |
| ~25 min | `Processing` | 668 |
| ~30 min | `Generating` | 668 |
| ~35 min | `Generating` | 668 |
| ~40 min | `Generating` | 668 |
| ~50 min | **`New` (finished)** | 668 |

**Render duration: ~49 minutes** (13:08 fire → ~13:57 finished), consistent
with the "European daytime" throughput note in the skill (fire time was
13:08 ICT = 06:08 UTC, inside Europe's working morning, not the
01:00-07:00 UTC quiet window).

## Result

- **NSFW: NO.** Opened the finished card (`?preview=34d69ef0-...`) — no
  NSFW badge, no "Credits refunded" badge on this card. Clean thumbnail
  showing the full 5-visitor gallery scene with the registrar entering.
- **Info icon panel** confirmed: Model `Seedance 2.5`, Quality `720p`,
  Bitrate `High`, Size `1280x720`, Created `September 6, 2026 at 1:08 PM`
  (exact match to fire time). No "Rights verification required" banner
  appeared on this card — nothing to confirm.
- **Download**: clicked Download from the info panel → "Preparing
  download" → "Download complete". File landed at
  `~/Downloads/hf_20260906_060816_e0914395-c5e9-486e-b253-c78977d08844.mp4`
  (20.8 MB / 21,801,312 bytes).
- **ffprobe verification**: `1280x720`, `h264` video / `aac` audio,
  `duration=20.050000` — matches the 1280x720/~20s spec exactly.
- **Filed to Drive**: `scripts/gdrive-bridge/upload_fix1.py` →
  `All Scene/Fix-1/S2M-Fix1-take3.MP4`
  (https://drive.google.com/file/d/1-b17aa5plFJk88mqKAxjZnXJrXER9JM8/view),
  20.8 MB. `logs.txt` line appended by the script itself (ADD/FILE entry,
  actor `AI:browser_operator-task-50ba6ad1`).

## The crack check

Extracted frames at 0.5s, 8s, 16s via `ffmpeg -ss <t> -frames:v 1`, saved to
the scratchpad:
- `/private/tmp/claude-501/-Users-gob-Projects-Agents-worktrees-mooniex-agents--browser-operator--task-50ba6ad1/ea8474bb-1ef8-4674-a5ea-fa72a0bb8191/scratchpad/s2m-t3b-0.5s.png`
- `/private/tmp/claude-501/-Users-gob-Projects-Agents-worktrees-mooniex-agents--browser-operator--task-50ba6ad1/ea8474bb-1ef8-4674-a5ea-fa72a0bb8191/scratchpad/s2m-t3b-8s.png`
- `/private/tmp/claude-501/-Users-gob-Projects-Agents-worktrees-mooniex-agents--browser-operator--task-50ba6ad1/ea8474bb-1ef8-4674-a5ea-fa72a0bb8191/scratchpad/s2m-t3b-16s.png`

**Verdict: PASS.** Compared directly against
`docs/prompts/absence/wall-pov-e-source.png` at matching door-centered
crops (same absolute crop window, image scales within ~5% of each other —
1344x752 reference vs 1280x720 render). The mark is:
- **Size: about 1x the reference door** — the crack's outermost arms reach
  to roughly the same extent (door width plus a touch onto the flanking
  columns) in both the reference and the render; no meaningfully larger
  spread in either width or height.
- **Shape**: thin lines meeting at one small solid-black central point,
  matching the reference's spider/star pattern — not a thick core, not
  radiating dead-straight lines from a single centre.
- **Placement**: over the far red door, upper-middle of frame, consistent
  across all three sampled timestamps (locked shot, camera never moved).
- **Off every face**: at 8s and 16s the nearest character (the yellow-green
  haired art student, closest figure in frame) sits well clear of the mark
  — no overlap with any face or body at any sampled timestamp.
- No second crack, no damage anywhere else on the wall/door in any frame.

## Review order 1-6 verdicts

1. **Fresh tab, claimed, maximized ≥1280, proven via innerWidth** — PASS.
   1600 read back at session start, never dropped below it.
2. **First action: close the credits banner by its own (x)** — PASS. Done
   before any other composer interaction, on the first load.
3. **Video → Seedance 2.5 → 16:9·720p·20s·High·Sound On, Unlimited toggled
   after, price zoomed** — PASS. All six fields set and re-verified fresh;
   Unlimited toggled last; button zoomed twice (once right after toggling,
   once immediately before the click) — both reads `UNLIMITED · ~~140~~ · 0`.
4. **Paste-only block, chip gate 9 unique / 0 red** — PASS. 9/9 unique
   bound, 16/16 raw mentions lime, 0 unresolved.
5. **Previz NOT attached** — PASS. Never uploaded/attached; fired on prose
   + Element references, flagged per brief.
6. **Generate as the last action, nothing else in flight, fire verified by
   card + count** — PASS. Nothing else was generating in this project at
   fire time (the only other card, take-3 NSFW, was already terminal);
   verified by both the new Processing card and 667→668.

## Two lanes

Left the CEO's `SEEDANCE 2.5 CREDIT`-prefixed cards untouched (none were
present in the visible grid this session). Left the NSFW take-3 card
exactly as found — not deleted, not touched.

## Anything odd

- The composer's model defaulted to Cinema Studio 4.0 on this fresh tab
  (not Seedance 2.5), and resolution/duration defaulted to 1080p/5s —
  all corrected explicitly before firing, per the six-field checklist.
- The settings row on this project's embedded Video composer required
  several right-chevron clicks to scroll into view (References → aspect →
  resolution → duration → batch size → quality → sound → Unlimited); once
  each field's location was known, `find()` refs were used directly for
  Quality/Sound/Unlimited to avoid further chevron-scroll guessing.
- No "Rights verification required" banner appeared on this card, so hard
  rule 3 (confirm rights) never needed to be exercised.
- `python3 -c "import time; time.sleep(N)"` foreground sleeps were used for
  the render wait (this is an interactive session, not a spawned
  subprocess DEV, so the standalone-sleep-blocked failure mode documented
  in the skill did not apply) — capped at 600s per chunk, always followed
  by a real page reload and re-read, never a scheduled-wake assumption.

## Tab hygiene

Released tab 53473052 via `scripts/browser/tab_registry.py done
task-50ba6ad1` after the last check.

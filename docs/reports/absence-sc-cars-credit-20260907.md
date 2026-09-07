# Absence — SC1/SC2 credit-lane fires + van plates, 2026-09-07

Browser: local Mac Chrome (confirmed via `list_connected_browsers` after an
accidental mid-task switch to a remote Windows browser — corrected, all real
browser work below happened on the local Mac). claude-in-chrome only, window
never resized (per task override of the general browser-operator default —
the CTO's OS width guard handles width; innerWidth checked >= 1280 throughout,
no resize call made).

## STEP 1 — museum-front plate

**Skipped entirely**, per CTO mid-task correction: the CEO confirmed a
location Element already existed — `@project_absence_loc_exterior_front`
(existing, four-panel sheet) — so no new plate was generated and nothing was
registered for STEP 1. All SC1/SC2 prompts below bind that existing Element.

## SC1 — two blocked attempts, one real fire

The scene changed twice mid-task by CEO/CTO order before firing (Carrington by
limo → Valder by limo with umbrella-doorman + two guards), each requiring a
fresh git merge and a fresh chip gate check. Full history:

| Attempt | Chips | Outcome |
|---|---|---|
| 1 (Carrington, 5 chips: exterior_front/prop_limo/gentleman_e/guard_private/guard_valder_six) | 5/5 bound | **Blocked** — "Some reference elements may contain protected content. Check eligibility or remove them to proceed." toast, before any charge. Screenshot: `docs/reports/frames-sc-cars/sc1-protected-content-dialog.png`. Credits unchanged (513). |
| 2 (Carrington, bodyguard_private_v2 swap, 4 chips) | superseded before firing — CEO changed the whole scene to Valder before this version was tried | — |
| 3 (Valder + doorman + 2 guards, 5 chips: exterior_front/prop_limo/char_valder/guard_valder_two/guard_valder_six) | 5/5 bound, 0 unresolved | **Fired for real.** |

Investigated the "eligibility" mechanism per CTO's ask: there is **no
per-Element "Check eligibility" control** anywhere in the Elements panel — the
only per-card control is a generic workflow Status picker (In progress / Needs
review / Approved), unrelated to content moderation. Eligibility is evaluated
only at Generate time, confirmed by the CTO after this finding. The flagged
reference for SC1 attempt 1 was never isolated (scene changed before a
bisection was needed); for SC2 it was (see below).

**Real fire (attempt 3) — settings & verification:**
- Video tab → Seedance 2.5 → 16:9 → 720p → 8s (ARIA slider, ArrowRight) → High
  → Sound On → Unlimited toggle **OFF**.
- Chip gate: 5/5 lime chips bound (`@project_absence_loc_exterior_front`,
  `@project_absence_prop_limo`, `@project_absence_char_valder`,
  `@project_absence_char_guard_valder_two`, `@project_absence_char_guard_valder_six`),
  0 unresolved.
- `prompt-lint.py` clean (exit 0); its `--chips` list output showed a bug
  (listed 6 names incl. a stale `@project_absence_char_guard_private_v2` from
  the NOTES zone even though the header correctly said "EXPECTED 5") — verified
  manually via `awk`+`grep` against the paste zone only, confirmed 5 real
  mentions; CTO fixed the NOTES-zone stray mention on main same session
  (commit `a1609f6`).
- Price zoomed: struck **56** / live **52** (screenshot-confirmed, not DOM
  scrape).
- Credits before: **513**. Clicked Generate **once** at
  `2026-09-07T06:18:08Z` (13:18:08 ICT).
- "Generation started" toast + new Processing card confirmed (asset count
  691→692).
- Credits after: **461** (−52, exact match).
- Card outcome: **clean** — Info panel prompt matches exactly, Created "September
  7, 2026 at 1:18 PM", Seedance 2.5, 720p, 1280x720, no NSFW/rejection flag.

## SC2 — two blocked/superseded attempts, one real fire

| Attempt | Chips | Outcome |
|---|---|---|
| 1 (original, 4 chips incl. `@project_absence_prop_car`) | 4/4 bound | **Blocked**, no toast text captured but confirmed no charge (credits unchanged, no new card, no new asset). Warning-triangle badge visually confirmed on the `@project_absence_prop_car` reference thumbnail specifically — the other 3 (exterior_front, woman_c, guard_valder_six) showed no badge. Reported the flagged chip to CTO. |
| 2 (car dropped to prose, 3 chips) | 3/3 bound, 0 unresolved | **Fired for real.** |

**Real fire (attempt 2) — settings & verification:**
- Same settings as SC1: Seedance 2.5, 16:9, 720p, 8s, High, Sound On,
  Unlimited **OFF**.
- Chip gate: 3/3 lime chips bound (`@project_absence_loc_exterior_front`,
  `@project_absence_char_woman_c`, `@project_absence_char_guard_valder_six`);
  the car is now plain prose ("HER CAR (no picture of it — build it from these
  words): ...").
- `prompt-lint.py` clean (exit 0), chip count matched.
- Price zoomed: struck **56** / live **52**.
- Credits before: **461**. Clicked Generate **once** at
  `2026-09-07T06:44:03Z` (13:44:03 ICT).
- "Generation started" toast + new Processing card confirmed (asset count
  692→693).
- Credits after: **409** (−52, exact match).
- Card outcome: **clean** — Info panel prompt matches exactly, Created "September
  7, 2026 at 1:44 PM", Seedance 2.5, 720p, 1280x720, no NSFW/rejection flag.

## Identifying and filing both cards

Both cards were located ~80+ minutes after firing (interleaved with the van
plate work below), after `Processing` badges had long since resolved and the
grid no longer showed them at the top. Identified reliably by extracting
`hf_<timestamp>` strings from thumbnail `img.src` attributes (id-diff
technique) and matching against the exact fire timestamps
(`20260907_061809`, `20260907_064404`) — both matched exactly — then confirmed
each via its Info panel (prompt text + Created time), never by eye alone.

- Downloaded both, `md5` checked against every other `.mp4` already in
  `~/Downloads` (70+ files) — no collisions, both genuinely new.
- `ffprobe`: both `1280x720`, `h264`, duration `8.041667s`.
- Frames extracted at 1s and 6s each →
  `docs/reports/frames-sc-cars/SC1-1s.png`, `SC1-6s.png`, `SC2-1s.png`,
  `SC2-6s.png`. No verdict rendered — the CEO reviews these himself, per task
  instruction.
- Filed via `scripts/gdrive-bridge/upload_fix1.py` to `All Scene/Fix-1/`:
  - `SC1-Limo-Arrival-Credit.MP4` — https://drive.google.com/file/d/1FKn7NqEA9XD8HqeP4aBs9ekAkEqYCO8Z/view
  - `SC2-Madame-Arrival-Credit.MP4` — https://drive.google.com/file/d/1d0GQ83c-yAQFuApSFCgjo76cfk2usgjz/view

## Credit summary

| Event | Credits before | Credits after | Δ |
|---|---|---|---|
| SC1 fire | 513 | 461 | −52 |
| SC2 fire | 461 | 409 | −52 |
| **Total spend this task** | | | **−104 credits** |

Every other action (van plates below) used Kling O1 Unlimited and cost 0
credits, confirmed by re-reading the balance immediately after each click.

## Extra work ordered mid-task: Carrington's van plate (3 takes, all free)

Not in the original brief; added by CEO/CTO order after SC1/SC2 fired. Free
image plates only (Kling O1, Unlimited toggle **ON**, 16:9, 1/4, one fire each,
button zoomed to bare `UNLIMITED` — zero digits — both before and after every
paste). No Element registered for any take; the CEO approves the look before
that happens.

| Take | Prompt fix | Result | Saved as |
|---|---|---|---|
| 1 | original wording ("same era as a wedge-shaped limousine") | Rendered a low wedge-shaped coupé, not a van — rejected by CTO/CEO | `generated/project_absence_prop_van_take1.png` |
| 2 | van stated first, wedge banned in negatives | Rendered a tiny cab under a roof 3x its height ("skyscraper box") — rejected | `generated/project_absence_prop_van_take2.png` |
| 3 | proportions stated in metres/ratios ("~5m long, 2m tall, roof one flat line"), high-roof explicitly banned | **Usable** — correct classic 1970s panel-van proportions, sliding door, wheels at corners | `generated/project_absence_prop_van_take3.png` |

Take 1's first click also hit a client-side "Prompt is required" refusal
(zero cost) because I skipped the mandatory End→space→Backspace Lexical-bind
tap after paste — caught immediately (asset count unchanged, no card), the tap
was applied, and the retry fired cleanly.

All three takes committed to `docs/prompts/absence/generated/`.

## Commits (this task, chronological)

- SC1/SC2 protected-content screenshot, SC1/SC2 fire record frames
- Van plate take 1, take 2, take 3
- This report

## SKILL-OVERRIDE / anomalies worth flagging

- `SKILL-OVERRIDE: browser-operator :: "restart Chrome, it is free and yours" ladder :: opened a fresh tab instead, never quit/restarted Chrome :: task ran concurrently with 2+ other live browser_operator tasks in the same window (confirmed via tab_registry.py list); a mid-session skill update (commit c2968e0) made this HARD anyway.`
- `SKILL-OVERRIDE: prompt-lint.py --chips :: trusted its printed name list :: cross-checked manually via awk+grep on the paste zone :: the tool's list-output picked up a stale @mention from the NOTES zone even though its own header count was correct — a real bug in the tool, not the sheet; flagged to CTO, fixed same session on main.`
- Mid-task the browser tool briefly connected to a remote Windows browser
  (accidental selection from an incomplete/mislabeled prompt) — caught before
  any action was taken there, corrected via `list_connected_browsers` back to
  the local Mac. No state was touched on the wrong browser.

## Tab hygiene

Every tab claimed via `scripts/browser/tab_registry.py claim` and released via
`release`/`done` before closing. No other worker's tab was touched. Final tab
closed and released before this report was written.

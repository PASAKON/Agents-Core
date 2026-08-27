# absence-cleaner (task-f4305098)

Both plates for the film's protagonist — `project_absence_char_cleaner` and
`project_absence_prop_cart` — generated, filed as Elements, downloaded,
reported. See `docs/prompts/absence/CLEANER.md` for prompts, asset ids, and
the honest per-image assessment.

## Credit balance

| Point | Paid balance |
|---|---|
| Task brief baseline | ~1,830 |
| Mid-session check (after plate 1, before plate 2) | 1,797 |
| Final check (after plate 2, session end) | 1,775 |

My own confirmed spend: **9 credits** (plate 1 = 2, plate 2 = 7), inside the
task's 10-credit cap. The rest of the ~55-credit drop from the stated
baseline is other operators' concurrent work on this same shared project —
the task brief itself warned "Other operators are holding tabs," and over
the session I repeatedly saw fresh, unrelated assets appear mid-scroll
(a corridor/hall location plate, several other character reference sheets
using an older prompt template, a man in a black leather coat) that I never
generated. Consistent with the skill's guidance on reading a shared-account
ledger: verified size (my two generations matched the button price shown
immediately before each click) and confirmed no unexplained large charge
landed in the window I was actively clicking Generate.

## Tab title

`Cinema Studio 4.0 — Direct Every Detail | Higgsfield`

## What blocked me

**Locating each generated asset in the shared grid was the single biggest
time cost this session.** The project's "All assets" grid holds 300+ items
across multiple concurrent operators and films (Absence, Valder, and what
looked like other festival entries), is virtualized (only ~10-30 tiles ever
mounted in the DOM at once), reorders unpredictably as other operators'
generations land, and gives no reliable "sort by newest" or "show only mine"
control. Visual scrolling was too slow and error-prone (I opened several
wrong cards — other operators' character sheets that happened to share a
similar prompt template). What actually worked: each thumbnail's underlying
`<img data-asset-preview>` carries a CDN URL of the form
`hf_<YYYYMMDD>_<HHMMSS>_<asset-uuid>.png` — I read these via
`querySelectorAll('[data-asset-id]')` + a small JS sort, took the newest
timestamp after my own Generate click, and opened the raw CDN URL directly
in a fresh tab to visually confirm content before touching the real asset in
the app. This is worth adding to the project's Higgsfield skill/replay notes
as a general technique: **diff by the embedded timestamp, not by scrolling.**

**Two separate rounds of severe browser/CDP instability**, matching the
`higgsfield-unlimited-gen` skill's documented traps but going further:
- The composer window's `window.innerWidth/innerHeight` silently dropped to
  `728x420` (a known "stuck mobile-viewport" bug per `absence-plates-3.md`)
  partway through plate 2's setup, and `resize_window` reported success
  without actually fixing it. Recovered per the skill's own prescribed fix:
  open a fresh tab, confirm dimensions there, close the broken one.
- Separately, `Page.captureScreenshot` timed out repeatedly (30s) on an
  otherwise-responsive tab (JS execution and `read_page` kept working fine),
  and at one point **every click stopped registering at all** — even
  ref-based clicks that had worked moments earlier on the same tab, on
  elements as basic as the "Filter" button. A hard reload of that exact tab
  resolved it. No credits were spent during any of these episodes — verified
  via the Usage/credit check before and after, per the skill's hard rule 7.

**The composer's own settings (aspect ratio / quality / resolution
dropdowns) intermittently stopped responding to clicks** — sometimes
opening on the first try, sometimes needing 3-4 attempts, and once
resetting itself back to Auto/High/2K defaults between page loads despite
having been set correctly earlier in the same session. This is the direct
cause of plate 2 costing 7 credits instead of ~2: rather than keep
retrying a flaky control, I accepted the higher-cost defaults once the
total spend was confirmed still under the 10-credit cap. Flagged in
`CLEANER.md` per-plate rather than glossed over.

**One prompt-desync failure on plate 1's first attempt** (documented
already by the `higgsfield-unlimited-gen` skill: "Prompt: Prompt is
required" even though the composer visibly held the correct text). Fixed
by a full page reload plus a real trusted keystroke (End, space,
backspace) after the paste to force the framework's bound React state to
sync — this is a new finding beyond what the skill currently documents
(the skill's existing fix was "reload and paste into a clean composer,"
which I also tried first and which did **not** fix it on its own; the
keystroke nudge is what actually worked). Worth adding to the skill.

**Real drag-and-drop for the cart's `@Image1` reference could not be made
to fire reliably.** See `CLEANER.md` plate 2 for the full explanation and
the substitution used (`@project_absence_prop_painting`, the same existing
Element, verified bound) — flagged there rather than silently worked
around.

## Not blockers, but worth recording

- The `project_absence_prop_painting` Element referenced in the task brief
  already existed from a prior session (`absence-plates-3.md`), confirmed
  via `?elements=1` and bound correctly (lime/green mention chip) on both
  the verification paste and the real generation.
- `project_absence_char_cleaner` did not previously exist; this session
  created it fresh.

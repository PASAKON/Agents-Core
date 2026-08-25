# Valder Scene 2 — eligibility clear + fire attempt (task-5c05dc3c, 2026-08-25)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/`

## Credits

- **Before: 1,974 left.**
- **After: 1,974 left.**
- Zero credits spent. Confirmed three separate times via Account menu → Credits, and via `read_network_requests` — no `generate`-pattern network call was ever observed after any Generate click (each click either did nothing server-side or was rejected client-side before any generation request was dispatched).

## JOB 1 — eligibility clear: ALL 5 PASSED

Opened a fresh tab, navigated to the project, pasted the Scene 2 prompt from
`/private/tmp/claude-501/-Users-gob-Projects-Agents/f61b5ac7-2b1a-4c8f-bbea-f692eab87266/scratchpad/s2-multicut.txt`
(14,231 bytes on disk, 14,161 chars decoded after base64 round-trip, matched
first/last 80 chars) via synthetic `ClipboardEvent` into the visible
(non-decoy) `contenteditable`. A stale/broken draft was already sitting in
the composer on page load (6 raw-UUID mentions, `hasError:true` on 5 of
them, malformed) — cleared it with a real `Cmd+A`+`Delete` via a `find()`-
resolved ref before pasting fresh.

- **7/7 distinct references bound, 0 `.text-icon-error`.** (19 total mention
  chips in the text — most `@project_valder_*` tags repeat several times
  across the 7 shots — but 7 distinct UUIDs, matching the 7 Elements.)
- Ran the per-reference **Check eligibility** control (by clicking each
  flagged reference-thumbnail chip, which opened its Element detail modal
  with the same tooltip+button, or in later cases cleared directly on
  click) on all 5 elements the task named:

| Element | Result |
|---|---|
| `char_mother` | **PASSED** |
| `char_daughter` | **PASSED** |
| `char_grandma` | **PASSED** |
| `loc_home_interior` | **PASSED** |
| `prop_plan` | **PASSED** |

No verbatim FAILED tooltip was ever seen for any of the 5. Confirmed PASS
for each via three signals: (1) reference-thumbnail badge svg count dropped
from 3 (badge + warning triangle) to 2 (badge only, same as the
never-flagged `char_father`/`char_son`), (2) a full-page text scan for
`needs an eligibility check`, `Face/IP failed`, and `may contain protected
content` returned nothing, (3) for `char_mother` specifically, opened its
Element detail modal directly and watched the "This asset needs an
eligibility check before it can be used." tooltip + "Check eligibility"
button disappear entirely after the click, with the Name/Element ID fields
in the same modal confirming the correct Element (`Mother`,
`@project_valder_char_mother`).

**Job 1 succeeded exactly as the task predicted** — this is the same
per-reference "Check eligibility" flow that cleared 8/9 in `task-8ea73ebb`.

## JOB 2 — settings verified, Generate blocked by a NEW form of the same banner

### What was verified before every attempt
Model **Seedance 2.5** (selected from the model dropdown — the composer had
defaulted to "Cinema Studio 4.0", a different template that is NOT Seedance
2.5), Mode **References** (default after switching to Seedance 2.5, not
Sequel), Duration **20s** (composer defaulted to 5s; this is a real text
input inside a small popover, NOT a hidden ARIA slider as the earlier
scripts documented for this project — typing into it moved the value in
odd increments, so it was set precisely via `ArrowRight` key presses after
triple-clicking the field), Resolution **720p** (defaulted to 1080p),
Quality **High** (default, correct), Sound **On** (default, correct),
Aspect **16:9** (default, correct), Unlimited **ON** (defaulted OFF on
page/model-switch load — flipped with **one clean `find()`-resolved ref
click**, which worked on the first attempt, `data-state` went `off`→`on`,
no second technique needed).

Confirmed via a **visibility-filtered** DOM read every time (this
project's composer renders duplicate/decoy/stale pill rows in the DOM
simultaneously with the live one — same bug family as the documented
"decoy editor" and "hidden duplicate Generate button"): `Seedance 2.5 /
References / 16:9 / 720p / 20s / High / On`, all seven pills present and
matching. Generate button read **`UNLIMITED / ~~140~~ / 0`** — struck
price resolving to 0 — confirmed both via `innerText` and a zoomed
screenshot tiebreaker, every time, immediately before each click.

### The blocker
Clicking Generate did **not** fire a generation. Instead, the exact same
banner from `task-1cbe84c8` (GH #99) reappeared: **"Some reference elements
may contain protected content. Check eligibility or remove them to
proceed."**

This happened **three times**, and each time was investigated differently:

1. **First click** (immediately after switching to Seedance 2.5, re-pasting,
   and setting duration/resolution/Unlimited): banner appeared. Checked all
   7 reference-thumbnail badges — all showed the clean 2-svg state (no
   warning triangle), full-page text scan for fail/needs-check text
   returned nothing. `read_network_requests` showed no `generat`-pattern
   call at all — only background `GET /fnf/reference-elements/<uuid>`
   polling calls (the same 4 of the 5 previously-flagged UUIDs) and
   `GET /fnf/folders/<id>/publish` calls, neither of which is a generation
   request.
2. **Second click** (after dismissing the banner toast and re-verifying
   settings fresh): same banner reappeared, network log cleared
   immediately before the click confirmed **zero** `generat`-pattern
   requests fired by the click itself either.
3. **Diagnostic**: hovered each of the 7 reference chips again in *this*
   Seedance-2.5 composer instance specifically. `char_mother` — and only
   `char_mother` — showed the "needs an eligibility check before it can be
   used." tooltip again, **despite its badge showing clean**. Ran Check
   eligibility on it again via a freshly-found ref; tooltip and warning
   disappeared. Re-hovered all 7 (including mother again) — zero tooltips
   anywhere, zero fail text, banner dismissed.
4. **Third click** (full fresh re-verification: 7/7 refs bound with 0
   errors, all settings correct, Generate button re-confirmed
   `UNLIMITED / ~~140~~ / 0` via zoomed screenshot): **banner reappeared a
   third time**, identical text, identical behavior.

**Working hypothesis, not confirmed:** switching the model from "Cinema
Studio 4.0" to "Seedance 2.5" fully resets the composer and creates a
**new** reference-element binding instance per pasted `@tag`, distinct from
the one the per-reference "Check eligibility" control operates against
under the original model. The individual-element check clearly *does*
something real (badges visibly flip states, tooltips genuinely disappear,
and it fixed `char_mother`'s tooltip specifically on the second pass) — but
the Generate-time validation appears to run a broader or differently-scoped
check that this composer instance keeps failing regardless, with no
specific element ever named as the culprit and no FAILED tooltip on any
individual reference. This is a **different symptom** from the one Job 1
anticipated (a named element failing its own check) — every element
individually reports clean, yet Generate still refuses.

## Stopped per task instructions

Per the money rules and the task's own stop condition ("If anything blocks,
leave Chrome exactly as it is and report the exact state"), no further
Generate attempts were made after the third reproduction. **Zero
generations fired, zero credits spent** (1,974 → 1,974, verified via
Account menu and via network-request absence of any `generat`-pattern
call across all three attempts).

Chrome was left with: composer holding the full 7-reference Scene 2 prompt,
all settings intact (Seedance 2.5 / References / 16:9 / 720p / 20s / High /
Sound On / Unlimited On), and the protected-content banner visible from the
third attempt (dismissed only to check the credit balance in the account
menu, which was then also closed — no navigation, no further clicks).

## What's needed to unblock

This is out of an operator's scope to resolve blind, per the standing
"scope discoveries are a C-level decision" rule. Two live options for
whoever picks this up next:

1. Try firing Take 1 **without** ever switching the model away from
   whatever default composer state is already Seedance-2.5-capable, if one
   exists, to avoid the model-switch reset entirely.
2. Have someone with Elements-panel/rights authority check whether there is
   a *composer-instance-scoped* or *generation-request-scoped* eligibility
   flag (distinct from the per-Element one this task's Job 1 successfully
   cleared) that needs a different clearing action — the banner text is
   identical to Job 1's, but Job 1's own fix did not resolve it here.

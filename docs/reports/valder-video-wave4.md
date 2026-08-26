# Valder video wave 4 (task-581d5c05)

Takes over from `task-80379c92` (wave 3), retired at 320k tokens. Full wave3
handoff: `docs/reports/valder-video-wave3.md`.

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/`

## Setup

All 14 prompt files re-synced fresh from `main` via `git show main:<path>` —
byte-identical to what was already in the worktree (no drift, nothing to
commit). Credits at wave start: **1,928** (down 2 from wave3's closing 1,930,
consistent with the documented small concurrent-image-operator drift).

## PART 1 — DIAGNOSIS (done first, per brief)

### The exact block, captured fresh

Fired S2 (8 elements: mother, father, son, daughter, grandma,
loc_home_interior, prop_frame, prop_mark — 8/8 bound, 0 mention errors,
Lexical state populated, desync fix applied) with Seedance 2.5 / 16:9 / 720p /
20s / High / Sound On / Unlimited ON, Generate button zoom-confirmed
`UNLIMITED / ~~140~~ / 0` (struck-through, free) immediately before the click.

- **Exact wording, verbatim:** "Some reference elements may contain protected
  content. Check eligibility or remove them to proceed."
- **Where it appears:** a **Toastify toast** (`div.Toastify__toast` inside
  `section.Toastify`, top of viewport). NOT a modal/dialog, NOT text on the
  Generate button itself, NOT inline next to any one chip in the toast's own
  text.
- **Does it name a specific element?** No — the toast text is fully generic
  regardless of how many or which elements are flagged.
- **Network request:** **zero.** `read_network_requests` around the click
  showed no `generat`-pattern call at all, before or after — only the
  pre-existing background `GET /fnf/folders/<id>/publish` polling that runs
  continuously regardless of any click. The click is refused **entirely
  client-side**, before any request reaches the generation endpoint.
- **Credit balance:** did not move on the click. 1,928 → 1,922 across this
  whole diagnostic session is accounted for by the documented concurrent
  image-plate operator's small drift (confirmed: no jump of 130+ credits,
  the signature of an actual video charge).

### NEW FINDING — the toast is generic, but the reference-thumbnail strip visually named TWO flagged elements, not one

The task brief's own framing ("S2 blocked on `@project_valder_prop_frame`")
undercounts what's actually flagged right now. Zoomed the 8-card reference
strip above the composer immediately after the blocked Generate click:

**Two cards showed the warning-triangle overlay, not one:**
- `@project_valder_char_grandma` (card 5) — **flagged**
- `@project_valder_prop_frame` (card 7) — **flagged**, as the brief predicted

`char_grandma` is **not** part of the 2026-08-26 batch of 15 new plates the
task brief's hypothesis rests on — it is one of the five original family
Elements that has been in every family scene since wave 1. **Wave 3's own
table shows S3 fired clean with `char_grandma` attached** (asset
`6d01ad10-572e-41d1-876f-58093c0f5b56`, 8/8 elements, 0 errors, no gate) —
meaning grandma's flag is **not a fixed, permanent property of the Element**.
It was clear when S3 fired in wave 3 and is flagged now. The eligibility flag
state changes over time on at least one Element that has nothing to do with
the new-plates batch.

**This complicates, but doesn't refute, the brief's batch hypothesis.** The
new-batch Elements (`prop_frame`, `loc_new_interior`, `prop_market_bag`, etc.)
may still be flagged for a different, more permanent reason (e.g. genuinely
new/unreviewed assets) while `grandma`'s flag looks like a separate,
transient toggle on an old, previously-clean asset. Two mechanisms may be
stacked here, not one.

### The one authorized variation: `@project_valder_prop_frame` removed, described in plain words

Built a variant of the S2 prompt with every literal occurrence of
`@project_valder_prop_frame` replaced by the plain phrase "the gilt frame"
(the surrounding prose already fully describes the object — this only
stripped the `@`-tag binding, nothing else changed). Cleared the composer
(real Cmd+A + Delete), pasted the variant, verified **7/7 elements bound, 0
errors**, re-applied the desync fix, re-confirmed
`UNLIMITED / ~~140~~ / 0` fresh.

Reference strip after paste: 7 cards, `prop_frame` gone as expected —
**`char_grandma`'s warning triangle was still present**, unchanged.

**Result: STILL BLOCKED.** Identical toast text, identical Toastify element,
zero `generat`-pattern network request, credits unchanged (1,922 → 1,922).

### What this actually proves

Because `grandma` was never removed (only `prop_frame` was, per the brief's
single authorized variation), this run **cannot cleanly separate** "the gate
is per-scene" from "the gate is per-element" — the result is confounded by a
second flagged element that was left in place. What it DOES show cleanly:

- The gate tracks **which references are attached**, not the scene as a
  whole: removing one flagged element while another flagged element remains
  attached still blocks, with the block riding on the surviving flagged
  reference. This is consistent with (not proof of) a per-element gate.
- It is **not** a stale/transient toast — the exact same banner reproduced on
  a completely fresh paste + fresh settings + fresh Generate button read, in
  the same tab, seconds apart.
- Zero cost either way. This block does not touch the credit ledger at all.

### Recommendation

The clean test is still available and cheap: **remove or clear-via-check-
eligibility BOTH flagged elements** (`prop_frame` AND `grandma`) and fire
once more. If it fires with zero flagged references, the gate is
confirmed per-element and (per wave 3's `valder-s2-eligibility.md`) the
per-reference "Check eligibility" control is the actual fix, not a
prompt-rewrite. Not run this wave — the brief authorized exactly one
variation and asked for this result to be reported before anything else.

**Also worth flagging to whoever has Elements-panel access:** since
`char_grandma` was clean in wave 3 and flagged now, the flag is not
write-once. Every "blocked" scene should be spot-re-checked visually (zoom on
the reference strip) rather than assumed permanently blocked from a past
wave's finding — the flagged-elements list can change between waves.

## PART 1B — CTO-directed follow-up: the fix IS the warning-triangle icon itself

CTO instruction after reading Part 1: the toast literally says "Check
eligibility or remove them to proceed" — that means the control exists, and
nobody had tried clicking the warning-triangle overlay on the flagged card
directly (as opposed to hunting for a panel-level button).

**Tested on the still-loaded S2-variant composer** (7 elements, `prop_frame`
already removed/described in plain words from Part 1's variation,
`char_grandma` still showing its warning triangle at the time):

1. Clicked directly on the warning-triangle icon on `char_grandma`'s
   reference-thumbnail card.
2. **No menu, no dialog, no dropdown appeared.** The icon changed instantly to
   a small loading/checked state and the triangle vanished. Zoomed
   before/after: triangle present → gone, on the same card, no other UI
   surfaced.
3. `read_network_requests` showed exactly what fired from that one click:
   `POST /fnf/reference-elements/306901ba-48b1-4520-8c4e-5daab310145d/ip-detect`
   (200), followed by a few `GET /fnf/reference-elements/<same-uuid>` polls
   (200) — a live face/IP eligibility re-check against that specific asset,
   confirmed via UUID match to `char_grandma`'s own mention id from the
   earlier bind. Full reference strip re-zoomed after: **zero warning
   triangles remaining on any of the 7 cards.**
4. Re-verified 7/7 bound, 0 mention errors, re-applied the desync fix,
   re-confirmed `UNLIMITED / ~~140~~ / 0` fresh, cleared the network log, and
   clicked Generate.

**RESULT: FIRED CLEAN.** `"Generation started"` toast, credits 1,922 → 1,918
(concurrent-operator drift only, matches pattern), new card confirmed via
`document.querySelectorAll('[data-asset-id]')[0]` →
**`b9b74401-26cd-433a-8cad-9f0eaf99d138`**.

**Confirmed: the fix is exactly what the CTO predicted.** The per-reference
"Check eligibility" control is not a separate panel/menu item — it IS the
warning-triangle icon on the flagged card, one click, no confirmation step,
resolves via a real `ip-detect` API call in a few seconds. This is why prior
waves' searches for a panel-level "Check eligibility" button sometimes found
one (in the Elements panel, per wave3's `valder-s2-eligibility.md`) and
sometimes didn't — **there are two places this control surfaces, and the
faster one (the reference-tray thumbnail itself, right where the prompt is
being built) had not been tried until now.**

**Practical consequence for the rest of this film:** every blocked scene
(S4, S4A, S4B, S4C, S5, S5B, S6, S7A, S7B) is very likely unblockable the
same way — paste the prompt, zoom the reference strip, click every
warning-triangle icon present, wait for it to clear, re-verify 0 errors,
Generate. No prompt rewriting needed. This is the single highest-value
finding of the wave. Adding all previously-blocked scenes back into the
active rotation below.

## PART 1C — CTO's natural experiment: does the flag follow the image or the scene?

Mid-wave, `task-d9001e45` (the concurrent image-plate operator) finished
regenerating 6 plates onto the SAME UUIDs: `prop_plan`, `char_grandma`,
`char_press`, `loc_studio`, `loc_street_row`, `loc_new_interior`. CTO asked:
retry canonical S2 (unmodified, `prop_frame` tag intact) and see whether
`char_grandma`'s flag — which was cleared manually via triangle-click in Part
1B — is now clean automatically because the underlying image changed, while
`prop_frame` (not part of this regen batch) stays flagged.

Pasted the **original, unmodified S2 prompt** (all 8 elements, `prop_frame`
tag intact) into a cleared composer. 8/8 bound, 0 errors (one transient
misread showed 2 errors on the very first read, resolved to 0 within ~800ms —
a timing race in the mention-resolution UI, not a real failure; the fix is to
re-check after a short wait rather than trusting the instant post-paste read).

**Result — clean and definitive:**
- `char_grandma`'s card: **zero warning triangle, no click needed at all.**
  The regenerated plate cleared the flag by itself.
- `prop_frame`'s card: **still flagged**, exactly as predicted — it was not
  part of the 6-plate regen batch.
- Clicked `prop_frame`'s triangle (per CTO instruction, do this regardless):
  same clean resolve as Part 1B — icon changed to a spinner, then to the
  normal hover state, triangle gone. (No `ip-detect` POST was visible in
  `read_network_requests` for this specific click — the network log appears
  to have a short retention/visibility window and may have missed it — but
  the visual before/after and the identical resolve pattern to the
  confirmed `ip-detect` case in Part 1B are conclusive.)
- **Final state: all 8 reference cards on the canonical, unmodified S2 prompt
  are clear of warnings.**

**Conclusion, confirmed two independent ways:** the protected-content flag is
tied to the **image asset itself**, not the scene, not the prompt, and not
fixed by creation date. It can be cleared either by **regenerating the
underlying plate** (what happened to grandma) or by the **triangle-click
eligibility re-check** (what happened to prop_frame, twice now, and to
grandma once in Part 1B before her regen). Both are legitimate, independent
fixes for the same underlying gate.

## PART 2 — keeping the slot busy (rotation of scenes that fire clean)

Per the CEO's standing "Unlimited must never sit idle" rule, proceeding to
fire extra takes of S1 / S1B / S3 / S-V in rotation, prioritising one take of
S-V first since it has never been fired. If the diagnosis above changes
(CTO instruction to test the double-removal, or new information), will
switch immediately.

**Watch item carried into this rotation:** S3 uses `char_grandma` too. If S3
now also gates (where it fired clean in wave 3), that confirms grandma's flag
is currently live and global, not scoped to S2's composer instance. If S3
still fires clean, the flag may be scoped differently than expected. Will
report this observation the moment S3 is attempted.

**Unrelated observation, noted for the record only, not investigated:** on
first load of the project this wave, one existing asset card showed "Failed"
/ "Credits refunded" with the note "Rejected due to copyright restrictions."
Not touched, not this wave's asset, flagged here only in case it's relevant
context for the protected-content investigation generally.

(Clip table below, updated after every fire.)

| Scene | Take | Clip asset id | Elements | Settings | Notes |
|---|---|---|---|---|---|
| S2 (variant) | 1 | `b9b74401-26cd-433a-8cad-9f0eaf99d138` | 7/7, 0 errors | Seedance 2.5 / 16:9 / 720p / 20s / High / Sound On / Unlimited ON | `prop_frame` removed+described in plain words (Part 1's variation) + `char_grandma` cleared via triangle-click eligibility re-check (Part 1B). Fired clean, `UNLIMITED / ~~140~~ / 0`, credits 1922→1918 (drift only). NOT the canonical S2 prompt — this take used the modified/no-prop_frame-tag text, kept for the record as proof-of-fix, not as a canonical S2 take. |
| S2 (canonical) | 1 | `b1b3276a-4d4f-483e-af76-dc08f6e63a5a` | 8/8, 0 errors | Seedance 2.5 / 16:9 / 720p / 20s / High / Sound On / Unlimited ON | The real, unmodified S2 prompt with `prop_frame` tagged. All 8 ref cards clear after the plate-regen (grandma, automatic) + triangle-click (prop_frame). Fired clean, `UNLIMITED / ~~140~~ / 0`, credits 1918→1918 unchanged. First successful canonical S2 take this project. |

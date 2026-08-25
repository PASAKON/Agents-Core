# Valder Scene 1 — Audit, Re-point, Fire Attempt (task-8ea73ebb, 2026-08-25)

## Result: BLOCKED before Generate — no video fired, zero credits spent.

## JOB 1 — Audit of the nine Elements

| Element | Found pointing at | Verdict | Action |
|---|---|---|---|
| `project_valder_loc_studio` | asset `15280a2c-2400-47a9-aa5f-2c2d4169f477` — vivid oxblood corridor, long axis, matches description exactly | Correct (visual match; ID differs from table's `c30be822-...` but content is right — see note below) | none |
| `project_valder_loc_fountain_hall` | asset `8551de74-fe87-4970-b88e-909eb09543fc` — teal+yellow concourse, chrome starburst fountain, red door, matches exactly | Correct (visual match) | none |
| `project_valder_prop_magazine` | asset `c3e9c946-46a0-4d90-846d-2f44730aed03` | Correct — **exact ID match** to table's target | none |
| `project_valder_char_valder` | asset `fb22cd96-3105-4b95-b7e3-caefea5565be` | Correct — **exact ID match** to table's target | none |
| `project_valder_char_press` | asset `8df3858b-4bc0-4f7a-b69e-a12a94c9959a` | Correct — **exact ID match** to table's target | none — **but see BLOCKER below: this asset later failed Higgsfield's own Face/IP eligibility check** |
| `project_valder_char_father` (pos 2) | asset `37ee1ae3-a97e-4988-a699-473ba46eb26d` | Correct — exact match to batch position 2 (timestamp `hf_20260824_193419`) | none |
| `project_valder_char_son` (pos 4) | was `e56817e1-...` (old-style multi-pose turnaround sheet, Aug-19 batch) | **Wrong** | **Re-pointed** → `6b754717-cbc2-42b2-9230-5236062cb5e8` (batch position 4, `hf_20260824_193728`, olive-green sweater boy) |
| `project_valder_char_guard` (pos 7) | was `9d599bc0-...` (old-style sheet, near-identical light-blue-uniformed men) | **Wrong** | **Re-pointed** → `8d2c6978-d10b-46cb-807f-1be7370981f4` (batch position 7, `hf_20260824_194214`) |
| `project_valder_char_crowd_a` (pos 9) | was `e3c4758e-...` (old-style 5-person muted-brown crowd sheet) | **Wrong** | **Re-pointed** → `62cfcd84-8b99-4b0b-b295-c99af6d0da42` (batch position 9, `hf_20260824_194515`, solid-blue-suit single figure) |

**Note on loc_studio / loc_fountain_hall ID mismatch:** the asset IDs currently pointing (embedded in the CDN filename) do not match the literal hex UUIDs given in the task table (`c30be822-...`, `1e0b8058-...`). Tested `?preview=c30be822-...` via full page navigate twice (fresh loads) — it consistently rendered the *same* oxblood-hall image already pointed by the Element, never producing a "not found" state. A parallel test with a definitely-real asset ID (`fb22cd96-...`, confirmed present in the Generations picker) via the same `?preview=` full-navigate method failed to open at all (URL param silently stripped, no modal). Conclusion: `?preview=` via full-page navigate is unreliable for verification on this project, so audit correctness was judged the way the task instructs — by visual content match against the description — not by hex-string equality. Both locations matched their description exactly, block for block (oxblood hall down its long axis; teal+yellow concourse with chrome starburst fountain and red door). Flagging this for the CTO in case the table's given target UUIDs for these two specifically need reconciling against a different ID namespace.

## Group C cross-check (position 7 = guards)

Confirmed **before** re-pointing `char_guard`: the batch-position-7 asset (`8d2c6978-...`) is a **wide group shot of six identically-uniformed men in deep teal uniforms with chrome-starburst caps, six clearly different faces, wildly different builds** (very tall/thin, short/stout, obese, thin-mustached, stout, medium) — matches the required cross-check exactly. Position-10 anchor (`c05fd4ed-...`, `project_valder_char_crowd_b`'s already-correct current pointer) also confirmed matching. Mapping validated — proceeded with re-pointing.

## Resolve test

Pasted all nine `@[name](uuid)` tags (the mention-id values, a third ID namespace distinct from both the asset-image IDs above and the CDN-filename IDs) into the composer in one synthetic paste. Read-back via `editor.querySelectorAll('[data-beautiful-mention]')`:

**All nine came back as bound chips, 1:1 exact match on both name and UUID.** No unresolved tags. Composer cleared afterward (verified `innerText.length <= 1` before proceeding).

## JOB 2 — Fire attempt

- Settings applied and verified immediately before Generate: **Seedance 2.5**, **References** mode (not Sequel), **20s**, **720p**, **16:9**, **Quality High**, **Sound On**, **Unlimited ON**.
- Full ~18,600-char prompt pasted via synthetic `ClipboardEvent`. Verified first/last 80 characters exact match to source. Normalized length delta (source 18,608 → rendered 17,806, diff −802) fully reconciled: 23 `@[name](uuid)` occurrences shrink to `@name` chip text (−920 chars, computed via regex) plus the documented small positive paragraph-break normalization (+118) — **not truncation**.
- **Reference thumbnail count: 9**, matching the 9 distinct Elements in the prompt.
- Generate button read **`Unlimited / ~~140~~ / 0`** immediately before the click — struck-through positive price with `0` actually charged, the documented "Unlimited is working" signal for a Seedance video generation (price legitimately dropped from an earlier `~~440~~` reading after I changed resolution 1080p→720p — not drift, a real recalculation).
- Clicked Generate via the documented direct-dispatch `PointerEvent`/`MouseEvent` sequence (coordinate clicks are unreliable on this composer per the existing replay script).

### Blocked — did not fire

A toast appeared: **"...reference elements may contain protected content. Check eligibility or remove them to proceed."** No generation started (button text unchanged, no "Generating" state). Ran the per-reference "Check eligibility" flow on all 9 thumbnails. **8 of 9 cleared cleanly.**

**`project_valder_char_press` failed**, with the tooltip: **"Face/IP failed — A face or protected content was detected, so this asset cannot be used. Try another."**

This is the elderly-photographer character portrait — the exact asset the audit above confirmed was *already correctly pointed* (exact ID match to the task's target). Higgsfield's own moderation is rejecting this specific reference image as containing a real face / protected likeness, independent of whether the Element points at the "right" asset per the task's own criteria.

Per the task's explicit instruction — **"If any [reference] fails, stop and report; do not fire the video."** — stopped here. **The video was not generated.** No credit-consuming action occurred.

## Credit balance

- **Before:** 1,980 (confirmed at session start, before any action).
- **After:** **1,980** (confirmed via Account menu after the blocked Generate attempt — no charge, since Generate never actually fired).

## Chrome state left as-is

Composer still holds: Seedance 2.5 / References / 20s / 720p / 16:9 / High / Sound On / Unlimited On, the full pasted prompt with all 9 chips bound, 9 reference thumbnails (8 cleared, 1 — `project_valder_char_press` — showing the Face/IP-failed icon with its tooltip visible on hover). Not navigated away, not cleared, not retried.

## Recommendation for the CTO

`project_valder_char_press`'s current reference image (asset `8df3858b-4bc0-4f7a-b69e-a12a94c9959a`) needs a new generation or a different existing asset that doesn't trip Higgsfield's face/IP detector — this is outside this task's scope (JOB 1 only authorized re-pointing to existing, already-generated assets for the 9 listed elements when wrong; it did not authorize generating a replacement). Re-pointing `char_press` was correctly **not** attempted here since the audit showed it was already pointing at the specified target asset — the failure is with that asset's content itself, not with which Element it's attached to.

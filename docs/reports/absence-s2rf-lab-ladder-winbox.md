# S2R-F cause-finding ladder — CREDIT lane — winbox spawn 2 (task-1755ef77)

Continuation of spawn 1 (task-5e0b9915, blocked on price 130 vs 140 — CEO
confirmed 130 is the correct live price today, docs/reports/absence-s2rf-lab-ladder-winbox-blocked-price.md).
CEO order 2026-09-10 11:40 ICT (verbatim in TASK.md): fire the auction scene
on the CREDIT lane, one variable at a time, stop at the first rejection.

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`
("The Valder Collection No.7"). Browser: winbox-chrome (device
`815ddf16-36ea-4e0d-827a-f51e9ff85351`), fresh tab 1638444898, claimed in
tab registry for task-1755ef77 (never touched task-0fe8ed87's tab
1638444895 or any other task's tab).

Composer settings every fire: Seedance 2.5 · 20s · 720p · 16:9 · High · 1/4 ·
Sound ON · **Unlimited toggle OFF** (credit lane) — verified fresh
immediately before each click (DOM `aria-checked`/`data-state` + pixel zoom).
Window 1920x855 throughout (well above the 1280 mobile-breakpoint floor).

## Method notes

- Prompt text extracted programmatically from each sheet's PASTE-FROM/PASTE-STOPS
  block (Python regex), base64-encoded, decoded in-page via `atob`+`TextDecoder`,
  then pasted via a single synthetic `ClipboardEvent` (`text/plain` only) into
  the real (visibility:visible) contenteditable — the 0-size decoy was present
  and correctly excluded by the visibility filter. Length and first/last-80-char
  boundary strings verified to match the source file exactly before firing each
  time (sha256 also computed in-page; the tool's own output redacted the hex
  digest as "[BLOCKED: Base64 encoded data]" on the first check, so length +
  boundary-string matching was used as the verification signal instead — both
  matched the Python-computed source values exactly on every fire).
- After every paste: `End` → space → Backspace (real trusted keystrokes) to
  force Lexical's bound state to sync, per the skill's documented fix.
- Chip count verified via
  `[contenteditable="true"] span.text-font-brand` (filtered to the one
  visibility:visible editable, leaf spans starting with `@`), de-duplicated to
  unique element names. Raw span counts run higher than the unique count
  because the sheets' own prose legitimately mentions several tags twice
  (once in the POSITION MAP, once in REFERENCES) — this is NOT the known
  0×0-decoy duplication bug (that was independently ruled out: only one
  visible contenteditable was present each time). Unique name count is what's
  reported against the task's per-step chip table.
- Real Generate button (never the `GENERATE8045` 0×0 decoy) located via
  `find()` and cross-checked by DOM rect (~120×80, visible) each time; price
  read by pixel zoom AND DOM text, both agreeing every fire.
- Per-fire credit balance: the account-wide Usage History/credit-balance
  widget was not located from inside this tab without a full navigation away
  from the protected composer (only a project-level "Usage statistics"
  aggregate — last-7-days total, not a per-transaction ledger — was found
  under Settings → Usage statistics, SPA route, no reload). Per-fire
  before/after credit balance is therefore **not** independently confirmed
  in this report; the authoritative signal used instead is each card's own
  badge (`Credits refunded` on rejection), consistent with how spawn 1 and
  prior AB-LEDGER entries recorded this. Flagged for the CTO/CEO — see Notes.

## Ladder

| step | sheet | chips (unique) | fired (UTC) | landed (UTC) | result |
|---|---|---|---|---|---|
| L0 | s2rf-fix1-the-battle-faces.txt (V2 as-is) | 13/13, 0 error | 2026-09-10T04:57:45Z | ~2026-09-10T05:03Z | **REJECTED** (expected) |
| L1 | s2rf-lab-l1-the-battle-faces.txt (no bidder chips) | 11/11, 0 error | 2026-09-10T05:06:29Z | 2026-09-10T05:25Z | **PASSED** |

### L0 — REJECTED (expected)

- Asset id `11e1da83-0120-4257-adaf-cdbe06111af3`.
- Card text verbatim: `NSFW / Credits refunded / Rejected due to copyright
  restrictions. / Delete`.
- 13/13 unique chips bound (loc_hall_big_e, gentleman_e, guard_private_v2,
  woman_c, valder, char_registrar, guard_valder_two, char_woman, critic_b,
  visitor_b, visitor_a, cleaner_c, prop_cart_a_painted), 0 error chips, 13/13
  reference thumbnails, no warning icons.
- Price at click: struck `140`, live `130` (authorized range per this task's
  brief). Not deleted (left for CTO/CEO per prior AB-LEDGER precedent on this
  exact NSFW/copyright rejection pattern).
- Per decision rule: L0 REJECTED (expected) → continue to L1.

### L1 — PASSED

- Asset id `3d33d133-a919-4477-9cf7-f74e6b3fb386`. Fired 05:06:29Z, `in_progress`
  through the full poll (checked ~05:08, ~05:10, ~05:14, ~05:18, ~05:22Z —
  all `in_progress`), landed `completed` by 05:25:24Z (~19 min render, in line
  with the credit-lane 5–15 min estimate plus platform queue variance).
- 11/11 unique chips bound (loc_hall_big_e, guard_private_v2, valder,
  char_registrar, guard_valder_two, char_woman, critic_b, visitor_b,
  visitor_a, cleaner_c, prop_cart_a_painted) — **no** `@gentleman_e`, **no**
  `@project_absence_char_woman_c` (both replaced with prose per the sheet),
  0 error chips, 11/11 reference thumbnails, no warning icons.
- Price at click: struck `140`, live `130` — this was a **passing fire**, so
  **130 credits were spent** (not refunded). Card details panel confirms
  Model Seedance 2.5 · 720p · High · 1280x720 · Created Sep 10 2026 12:06 PM
  (ICT, = 05:06 fire time) · filed in The Valder Collection No.7.
- **Download**: `hf_20260910_050627_3d33d133-a919-4477-9cf7-f74e6b3fb386.mp4`,
  19,929,436 bytes, md5 `c8774351b5c8e11ddff30c289510c7dc`, copied into
  `docs/reports/frames-s2rf-lab/L1/`. ffprobe: h264/aac, 1280x720,
  duration 20.04s — matches spec.
- Frames extracted at 1.5/4.5/7.5/10.5/13.5/16/19.5s (full resolution) +
  640-wide contact row, all in `docs/reports/frames-s2rf-lab/L1/`.
- **Honest description of the footage**: the five close-ups (1.5/4.5/7.5/
  10.5/13.5s) are clean — exactly one face per shot, Carrington's prose
  description and the woman-in-green's prose description both render
  consistently across their three/two respective close-ups (same gold teeth,
  same cream wall behind Carrington; same blue-green-silver pompadour and
  cat-eye sunglasses for the woman), no second face or shoulder intrudes in
  any close-up. **However, in the full shot (16s) Carrington does not appear
  as a separate, identifiable 13th figure.** The front-left position his
  prose said he should occupy is filled by a single cream-suited man holding
  a ledger and pen (white gloves, small gold V) — that is the REGISTRAR's
  described outfit exactly, not Carrington's (no cane, no visible gold
  teeth at this distance). The bodyguard is standing directly behind this
  same figure, i.e. positioned as if Carrington and the registrar are one
  person. This is plausibly two near-identical prose "cream/white
  stand-collar suit" descriptions merging in the model's read of the full
  shot once Carrington had no reference plate to keep him visually distinct.
  The woman in green DOES appear as a separate, correctly-dressed figure on
  the right. Not flagged as a moderation problem (the card passed), but
  flagged here as a full-shot cast-count/identity discrepancy for the CTO to
  judge — screenshots at `docs/reports/frames-s2rf-lab/L1/frame_16s.jpg`,
  `left_crop.jpg`, `mid_crop.jpg`.

## Conclusion (interim)

L0 (13 chips, both bidders bound as Elements) → REJECTED as NSFW/copyright,
as expected/reproduced. L1 (11 chips, both bidders as prose only, no
Element binding) → PASSED moderation. This points toward **the bidder
Element bindings themselves (not the close-up framing) as the likely
trigger for the rejection** — continuing to L2 to isolate which of the two
bidders (Carrington vs the woman in green) is responsible, per the ladder.
Final conclusion pending L2/L3.

## Files changed

- `docs/reports/absence-s2rf-lab-ladder-winbox.md` (this file)

## Tests

None applicable — browser_operator/data task, no code changed.
`python scripts/prompt-lint.py` run clean on all three sheets before firing
(L0, L1, L2).

## Blockers

None yet. Will update if the ladder stops early or hits a stop-and-ask
condition.

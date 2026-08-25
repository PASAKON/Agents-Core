# Valder crowd/pallor reshoot — 5 plates (task-5e0dbf26)

Higgsfield project `ai-film-festival-3`, Character folder `ae0bb5a3-9f66-4e95-8112-c2939e9de56e`.
Model: GPT Image 2 / Medium / 1K / quantity 1 throughout. All five plates image-only, no video.

**Credits: 1,974 before → 1,964 after. Total spend: 10 credits, 6 generations (well under the 15-generation stop / 30-credit ceiling).**

Sequencing note: waited for `wd-be7868a5` (Scene 1 video fires) to fully finish (task-be7868a5 → review) before touching Chrome, per brief. CTO sent a mid-task revision to Plate 1's spec (exact accessory counts) via TASK.md at 00:23 — verified via mtime before applying, then generated to the revised spec.

---

## PLATE 1 — `project_valder_char_crowd_a` — REVISED SPEC (2-3 colours/person + exact accessory counts)
- Asset id: `898f419f-f9c1-4943-a536-17b35c7afd6c`
- Attempts: 1/3 (first attempt hit the known "Prompt is required" desync bug — paste landed in the DOM but not app state; fixed with a real keystroke nudge (End, Space, Backspace) then re-clicked Generate, no re-paste needed)
- Checklist:
  - 8 distinct people, all clearly visible — PASS
  - Each wears 2-3 saturated colours in a considered combination, never one flat colour head to foot — PASS
  - Every combination different from every other — PASS
  - No patterns/prints/stripes/checks anywhere — PASS
  - All 8 carry one fashionable item, each different — PASS
  - Exactly 3 scarves (verified: purple, yellow, purple — worn by 3 of the 8, other 5 bare-necked) — PASS
  - Exactly 3 hats (black fedora, blue derby, purple hat) — PASS
  - Exactly 2 spectacles (2 of the 8) — PASS
  - 8 completely different faces/ages/builds — PASS
- **Pallor verdict: reads as an ordinary drained-human complexion, not alien.** No green/grey/blue cast on any face.
- Element re-pointed: YES (Edit Original → Generations tab → selected by matching asset id → Name/ID unchanged → Save → "Element saved.")
- Eligibility check: PASSED (no "Face/IP failed" or "needs an eligibility check" text after running Check eligibility in the video composer's References panel)

## PLATE 2 — `project_valder_char_crowd_b`
- Asset id: `6f14b6cb-4108-4ccb-bda1-62f8dc788e66`
- Attempts: 1/3
- Checklist:
  - 8 distinct people — PASS
  - One saturated coat each, clearly patterned clothes/ties visible at collar and cuffs — PASS
  - Too many accessories (pins, pocket squares, watch chains) on each — PASS
  - 8 different faces, ages, builds — PASS
  - Reads as "almost right and visibly wrong" vs Plate 1 — PASS
- **Pallor verdict: patchy/uneven, mid-transition, still reads human — not alien.**
- Element re-pointed: YES
- Eligibility check: PASSED

## PLATE 3 — `project_valder_char_guard` — reshoot for pallor only, composition unchanged
- Asset id: `ab9ca314-8a4f-4eb0-b007-717a331fd907`
- Attempts: 1/3
- Checklist:
  - 6 men, one identical teal uniform (chrome buttons, peaked cap, starburst badge) — PASS
  - 6 wildly different builds (very tall/thin, very short, enormously broad, narrow-shouldered, middle-aged heavy, young gaunt) — PASS
  - 6 completely different faces — PASS
- **Pallor verdict: ordinary pale human complexion, not alien.**
- Element re-pointed: YES (searched Elements panel by "char_guard" — two matches existed, "Guards 12" (a different, older 12-person element) and "Guard"; confirmed the exact target via Element ID `project_valder_char_guard` before editing, not by name/thumbnail alone)
- Eligibility check: PASSED

## PLATE 4 — `project_valder_char_valder` — reshoot for pallor only, wardrobe unchanged
- Asset id: `9451b1b9-f20e-488f-90ad-69e3e8a98213` (the `?preview=` URL param showed a *different* id, `4e2a3995-...` — confirmed this is a separate id namespace per prior wave notes; the media-picker `img.alt` / `data-asset-id` value is the one that matters for re-pointing, and that's `9451b1b9-...`)
- Attempts: 1/3
- Checklist:
  - 5 distinct saturated colours (oxblood, petrol teal, chrome yellow, ultramarine, forest green) in flat hard-edged panels, no gradient/print — PASS
  - Sleeves different lengths (one full-length, one cut short at elbow) — PASS
  - Gloves two different colours (teal + yellow) — PASS
  - Chrome starburst brooch at throat — PASS
  - Eyes closed — PASS
  - Very tall, very thin, long neck — PASS
- **Pallor verdict: the palest of the five, but still unmistakably an ordinary human being — not alien.**
- Element re-pointed: YES (this Element had already been through a full restyle in an earlier wave — the reshoot only needed to swap the reference asset, wardrobe/composition untouched)
- Eligibility check: PASSED

## PLATE 5 — `project_valder_char_press` — HANDLED WITH CARE (2x prior Face/IP fails)
- Asset id: `2b60c244-49bb-4b0c-a650-0877544e4653` (media-picker id; the `?preview=` URL id `ccc30c7b-...` is again a different namespace — same caveat as Plate 4)
- Attempts: **2/3**
  - Attempt 1: **flagged by the safety system** ("Content was flagged by the safety system. Try different prompts or inputs.") — did not render, cost 0 credits.
  - Attempt 2: reinforced the ordinariness/synthetic-composite framing even more explicitly than the task brief's base language (added "this face is entirely synthetic and invented... assembled from no real photograph... deliberately unremarkable, plain and forgettable... no connection whatsoever to a real person", plus matching negatives) — passed cleanly, rendered normally.
- Checklist:
  - Heavy square jaw, jowls, thinning hair, receding hairline, thick black-framed spectacles, short neck — PASS
  - Permanently/severely hunched, one shoulder visibly higher, head tilted to compensate — PASS (clearly visible, camera-weight explanation legible)
  - Deep forest-green coat, leather flashbulb harness, retrofuturist press camera w/ separate flash unit — PASS
  - Face reads generic/unremarkable, no resemblance to any recognisable public figure — PASS
- **Pallor verdict: ordinary indoor pallor, reads human — not alien.**
- Element re-pointed: YES (re-pointed to the successful attempt-2 asset, not the flagged attempt-1 one)
- **Eligibility check (per-reference "Check eligibility" in the video composer): PASSED** on the first run after re-pointing.

---

## Summary
All 5/5 plates pass on the pallor rule — every face now reads as an ordinary, blood-drained-but-human complexion, with no green/grey/blue/silver cast anywhere. All 5 Elements have been re-pointed to the new assets (Name and Element ID left untouched, no new Elements created, no duplicates). All 5 re-pointed Elements passed their post-repoint "Check eligibility" gate. No plate needed a third attempt. Credits: 1,974 → 1,964 (10 spent, 6 generations).

Chrome left on the Character folder page, composer in Video mode with `@project_valder_char_press` still attached (harmless — no Generate click pending, nothing staged to fire).

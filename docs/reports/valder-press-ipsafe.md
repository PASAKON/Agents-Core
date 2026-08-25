# Valder `project_valder_char_press` — IP-safe replate (task-5993f785, 2026-08-25)

Character folder: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/folders/ae0bb5a3-9f66-4e95-8112-c2939e9de56e`

## Result: PASS on attempt 2/3

`project_valder_char_press` now points at a plate that **passes Higgsfield's own
Face/IP eligibility check** — the Character-photographer reference no longer
blocks video generation. Element re-pointed, no video generated, no rights
modal touched.

## Credits

- **Before: 1,978 left** (Account menu → Credits). Task brief expected 1,980;
  the 2-credit gap is explained by `wd-c32c5816`'s storyboard generation
  running concurrently before I started — recorded the actual reading, not
  the expected one.
- **After: 1,974 left.**
- **Spent: 4 credits** (2 attempts × 2 credits, GPT Image 2 / Medium / 1K /
  qty 1 / 3:2) = **$0.16**, inside the 6-credit / $0.24 ceiling. Attempt 3 was
  not needed.

## Attempt 1 — asset `cd1c4b47-2084-4f75-af45-9817d3f17d66`

- Plate itself: **not safety-flagged** on generation (no `[title*="flagged"]`
  string on the card).
- Shoulder asymmetry: dramatic and immediately visible — right shoulder driven
  up near jaw level, head tilted off-vertical to compensate, camera weight
  visibly on that side.
- Re-pointed `project_valder_char_press` onto this asset (Elements → Edit →
  **Edit Original** → refresh icon → Generations tab → selected, verified by
  `img.alt === "cd1c4b47-2084-4f75-af45-9817d3f17d66"` → Save). "Element
  saved" confirmed.
- **Eligibility check: FAILED.** Pasted `@[project_valder_char_press](f17d75cc-cd5d-4e0f-a14e-fe6b181d68e9)`
  into the video composer, confirmed it bound as a reference (References
  1/50, thumbnail `img.alt === "project_valder_char_press"`), clicked the
  per-reference **Check eligibility** control. Hover tooltip after the check:
  **"Face/IP failed — A face or protected content was detected, so this asset
  cannot be used. Try another."** Identical failure to the pre-existing plate
  this task was created to fix.

## Attempt 2 — asset `3a92bf07-f3c4-4af5-b68d-8c304f7d4bd3`

Retried per procedure: same locked silhouette/wardrobe/prop language, face
section rewritten to state the "generic, computer-generated composite face
with zero basis in any real individual's likeness" requirement far more
explicitly (named it the single most important instruction, added "blend
countless unremarkable strangers", "not based on any well-known
character-actor type", explicit low-distinctiveness/forgettability language,
and matching NEGATIVES additions: no character-actor typecast face, no
distinctive or memorable face, no impression of a real person).

- Plate itself: **not safety-flagged** on generation.
- Shoulder asymmetry: visible and readable (right shoulder raised, head
  tilted, camera weight on that side) — present but slightly less extreme
  than attempt 1's version; still clearly an intentional, immediate visual
  asymmetry, not subtle.
- Re-pointed `project_valder_char_press` onto this asset (identical Edit
  Original → Generations-tab → verified-by-`img.alt` → Save flow). "Element
  saved" confirmed.
- **Eligibility check: PASSED.** Pasted the same `@[project_valder_char_press](...)`
  mention, confirmed reference bound (`img.alt === "project_valder_char_press"`),
  clicked **Check eligibility**. After the check completed: the mention chip
  resolved to a clean, properly-named `@project_valder_char_press` chip (no
  longer showing the raw UUID as on attempt 1), the reference thumbnail
  showed no warning-triangle icon and no circle-slash fail badge (contrast
  with attempt 1's persistent "🚫" overlay after its failed check), and a
  full-page text scan for `Face/IP failed|protected content|eligibility check
  before` returned **no match**. Hovering the thumbnail directly produced no
  tooltip at all — the clean, no-flag state.

## Element re-point

`project_valder_char_press` (Category: Character, used in 92 generations at
time of edit) was re-pointed **twice** in this run — once to the attempt-1
plate, then again to the attempt-2 plate once attempt 1 failed eligibility.
Both edits went through **Edit Original** (never "Duplicate & Edit"). Name
("Press") and Element ID (`project_valder_char_press`) are unchanged from
before this task. Final state: pointing at asset
`3a92bf07-f3c4-4af5-b68d-8c304f7d4bd3`, the attempt-2 (passing) plate.

## Composer left clean

References cleared to 0/50, prompt field empty, no video generated at any
point in this task (image-generation only, as briefed).

## Notes for reviewer

- The bracket-paste syntax `@[name](uuid)` initially displayed the mention
  as a raw, unresolved UUID in red text even though the underlying reference
  was correctly bound (`img.alt` matched the target Element the whole time).
  This resolved itself into a clean, properly-named chip only *after* running
  the eligibility check — don't read the red/raw-UUID display alone as a
  binding failure; verify via `img.alt` on the reference thumbnail instead.
- The reference thumbnail carries a small "🚫" (circle-slash) badge after a
  **failed** eligibility check and a clean "@"-only badge after a **passed**
  one — this is a fast, cheap way to distinguish pass/fail visually without
  re-reading the tooltip text every time, though the tooltip text remains the
  authoritative signal and is what this report relied on.

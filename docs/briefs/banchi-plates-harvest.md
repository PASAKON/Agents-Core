# «บัญชี» — harvest EVERY plate once, and create the 2 missing assets. ZERO credits.

## Why this task exists

CEO standing rule, 2026-09-18: a shot sheet may not be written until every
character, location and prop plate has actually been **looked at**, as one
montage. We have 4 of roughly 19. The rest exist only inside Flow, and the CEO's
instruction is explicit that they get downloaded **once** — not re-fetched per
shoot. One clean pass, and the script is corrected against real images instead
of against what someone remembered.

Everything in this task is **free**. Image generation and downloads have both
been measured at 0 credits, repeatedly. Read the balance at the start and at the
end and report both. Never press Submit in the video composer.

Project: **"AI Film"** in Google Flow (the project that holds `@lung_somchai`,
`@grandma_pranom`, `@noodle_shop`).

## Part 1 — create the two assets the Act 1 sheet references but that do not exist

The last run (task-36507a6a) scrolled the whole `ตัวละคร` tab twice and
confirmed **`@cop_wit` is not in the project.** The shot sheet uses it in 11
shots. A second handle, **`@side_wall`**, was not in that run's inventory either
— **verify it yourself** before creating it; if it already exists, skip it and
say so.

Create each as a **Character/Ingredient** asset, model **Nano Banana Pro**, and
rename it to exactly the handle given. Style line to prepend to both prompts:

> Contemporary Thai realist drama, shot on 35mm, desaturated colour, natural light.

**`@cop_wit`**

> a Thai man of 32, medium athletic build, short neat black hair, clean-shaven,
> calm steady eyes, in a plain dark-grey polo shirt with an open two-button
> collar and a simple steel wristwatch on his left wrist, a canvas bag still on
> his shoulder

**`@side_wall`** (only if it really is missing)

> the side exterior wall of an old Bangkok shophouse before dawn — rough grey
> concrete with peeling paint and long water stains, an air-conditioner bracket,
> a rusted pipe running down to the ground, wet pavement, a single distant
> streetlamp

Confirm the balance is unchanged after each generation, and report it. If a
generation ever shows a credit cost, stop and report instead of paying it.

## Part 2 — download every plate in the project, once

Download **one image per asset tile** in the `ตัวละคร` tab — characters,
locations and props alike, including the two you just made — to:

```
~/Desktop/banchi-plates/<handle>.png
```

Name each file for its handle, without the `@` (`lung_somchai.png`,
`noodle_shop.png`, …). One file per asset. If a tile has several generations,
take the one the tile itself displays.

The previous run's inventory, as a checklist of what to expect (it is not
authoritative — download what is actually there, and report anything on this
list you cannot find, plus anything present that is not on it):

`@grandma_pranom` · `@nong_daeng` · `@lung_somchai` · `@money_fold` ·
`@empty_pill_pack` · `@qr_sign` · `@fathers_phone` · `@bedrail_marks` ·
`@noodle_shop_thriving` · `@staircase` · `@street_front` · `@back_alley` ·
`@upstairs_bedroom` · `@staff_a` · `@jae_muay` · `@lender_cherd` ·
`@noodle_shop` · `@prop_envelope`

Skip `@test_char3` and anything else obviously left over from an unrelated test
— list what you skipped and why.

Known trap from the skill: downloading one image has taken anywhere from 25 s to
266 s, and two of them needed a fresh tab. That is normal. A hung export is
cured by a full page reload, which costs nothing.

## Budget

60 steps, 4 screenshots. **Answer in text.** Do not open any video, do not press
play, do not verify anything about the clips — this task is only about stills.

## Deliverable

`docs/reports/banchi-plates-20260918/REPORT.md` containing:
1. a table: handle → created / already existed → downloaded yes/no → file size on disk
2. anything on the checklist that does not exist, and anything present that was not on it
3. credit balance before and after
4. the wall-clock per action, appended in the skill's table format

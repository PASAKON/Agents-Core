# «Sorry, Sir» — Valder guards uniform (V-mark absence), task-962ebf8d

Project: Higgsfield "The Valder Collection No.7"
(`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3`)

## Job 1 — existing guard plate check

Element `project_valder_char_guard` (Character folder, 6 guards) opened and
zoomed at chest/collar/cap/sleeve on multiple figures. Prompt on the card:
"Six men in an identical uniform standing in a row: deep petrol teal, high
stiff collar, a vertical row of chrome buttons, peaked cap with a small
chrome starburst badge, tapered trousers." **No gold V anywhere** — only
silver/chrome buttons and a chrome starburst cap badge. Confirmed visually,
not from thumbnail.

**Verdict: V is missing → proceeded to Job 2, Route A.**

## Job 2, Route A — uniform garment study

| Field | Value |
|---|---|
| Element name | Guard Uniform Study |
| Element ID | `project_absence_prop_guard_uniform` |
| Asset ID | `4067d5a3-f798-4ed8-81e6-e9c81efa17c8` |
| Model | GPT Image 2, 1K, Medium |
| Cost | 1.5 credits (attempt 1 of 1 — succeeded first try) |
| Result | Front + back panels, deep navy uniform, mandarin collar, gold V on chest, gold V on cap, gold buttons/piping, black leather belt (black accent allowed for guards) |
| File written | `docs/plates-props/project_absence_prop_guard_uniform.webp` (repo copy) + `/Users/gob/Desktop/absence-guard-uniform.png` (task-specified path) |

Prompt used:
> A single retrofuturist guard uniform, shown alone as a garment study on a
> plain neutral studio background, front view and back view side by side. No
> person wearing it, no mannequin head, no face, no body.
>
> Deep blue uniform body matching an existing set of blue-uniformed guards.
> Structured shoulders, standing mandarin collar, clean moulded lines,
> nothing later than 1970s in style, no logos, no modern tactical gear. A
> single vertical row of buttons down the front.
>
> A clearly visible GOLD V emblem centered on the chest, rendered in gold
> metal or gold thread, unmistakable and sharply defined. If the uniform
> includes a peaked cap, place a small matching gold V or gold badge on the
> front of the cap as well.
>
> Black accents are allowed as trim, piping, belt, or boots, but the main
> body of the uniform stays blue.
>
> Sharp studio product photography, clean even lighting, high detail on
> stitching, collar, buttons, fastenings, and the gold V. No background
> clutter.

## Job 2, Route A — six-guard redress

| Field | Value |
|---|---|
| Element name | Guards Redressed Six |
| Element ID | `project_absence_char_guard_valder_six` |
| Asset ID | `db69589e-1c4a-4800-8723-0dde14ab28bb` |
| References | `@project_valder_char_guard` (original 6-guard plate) + `@project_absence_prop_guard_uniform` (uniform study), both auto-resolved from plain-text `@` mentions in the pasted prompt |
| Model | GPT Image 2, 1K, Medium |
| Cost | 1.5 credits (attempt 1 of 1 — succeeded first try) |
| Result | Same six faces, builds, heights, poses, and framing as the original; uniform swapped to the study's navy uniform with gold V on chest and cap, gold buttons, black belt |
| File written | `docs/plates-props/project_absence_char_guard_valder_six.png` (repo copy) + `/Users/gob/Desktop/absence-guard-valder-six.png` (task-specified path) |

Prompt used (both `@` tags auto-resolved to reference chips on paste, confirmed by checking tag color/chip before Generate — not left as red text):
> Using @project_valder_char_guard as the reference for the six guards' faces,
> body types, poses, and framing, and @project_absence_prop_guard_uniform as
> the reference for the uniform garment: redress all six guards in the exact
> uniform shown in the uniform reference. Deep navy blue uniform body,
> standing mandarin collar, gold buttons down the front, gold piping on the
> cuffs and trouser side-seam, black leather belt with a gold buckle, and a
> clearly visible GOLD V centered on the chest of each guard's uniform. If a
> guard wears a cap, add a small matching gold V on the front of the cap too.
>
> Change ONLY the clothing. Keep the same six faces, the same six body types
> and heights, the same poses, and the same framing, composition, lighting,
> and background as the original reference photo. Do not add, remove, or
> alter any person.

## Remaining (in progress at time of writing)

- Single-guard 4-panel plate → `project_absence_char_guard_valder_single`.

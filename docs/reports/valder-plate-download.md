# Valder Collection No.7 — Character plate download (task-598b5fa3)

Project: `The Valder Collection No.7` (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3)

**Scope note:** this task was narrowed mid-run by the CTO to `project_valder_char_*`
Elements only. `project_valder_loc_*`, `project_valder_prop_*`, and the two
`project_valder_sb1_*` (storyboard) Elements were handed to other operators and
are **not** covered by this manifest.

All 17 Character Elements found in the panel (Active + Drafts combined, via
the "All elements" status filter) were downloaded. Files were pulled with the
Elements panel's own **Download** button on each Element's detail dialog —
full resolution as served by Higgsfield, no re-encoding, no cropping.

The **Panel Name** column is the "Name" field verbatim as it appears in the
Elements panel detail dialog — separate from the Element ID / filename, at the
CTO's request. Two elements (`char_tea_circle`, `char_neighbor`) have no Name
ever set — the panel falls back to displaying the raw Element ID in that
field, which is reported here as-is rather than invented.

| Element ID | Category | Panel Name | Asset id | File written | Downloaded? |
|---|---|---|---|---|---|
| project_valder_char_valder | Character | @Valder | a713569c-0a8c-4217-9653-dcd45baedfbb | docs/plates/project_valder_char_valder.webp | Yes |
| project_valder_char_mother | Character | Mother | not captured | docs/plates/project_valder_char_mother.webp | Yes |
| project_valder_char_father | Character | Father | not captured | docs/plates/project_valder_char_father.webp | Yes |
| project_valder_char_tea_circle | Character | (none set — panel shows raw ID) | not captured | docs/plates/project_valder_char_tea_circle.webp | Yes |
| project_valder_char_neighbor | Character | (none set — panel shows raw ID) | not captured | docs/plates/project_valder_char_neighbor.webp | Yes |
| project_valder_char_guards_12 | Character | Guards 12 | not captured | docs/plates/project_valder_char_guards_12.webp | Yes |
| project_valder_char_villagers_rich | Character | Villagers Rich | not captured | docs/plates/project_valder_char_villagers_rich.webp | Yes |
| project_valder_char_guard | Character | Guard | not captured | docs/plates/project_valder_char_guard.webp | Yes |
| project_valder_char_grandma | Character | Grandma | not captured | docs/plates/project_valder_char_grandma.webp | Yes |
| project_valder_char_daughter | Character | Daughter | not captured | docs/plates/project_valder_char_daughter.webp | Yes |
| project_valder_char_son | Character | Son | not captured | docs/plates/project_valder_char_son.webp | Yes |
| project_valder_char_chase_group | Character | Chase Group | not captured | docs/plates/project_valder_char_chase_group.webp | Yes |
| project_valder_char_crowd_a | Character | Crowd A | not captured | docs/plates/project_valder_char_crowd_a.webp | Yes |
| project_valder_char_crowd_b | Character | Crowd B | not captured | docs/plates/project_valder_char_crowd_b.webp | Yes |
| project_valder_char_press | Character | Press | not captured | docs/plates/project_valder_char_press.webp | Yes |
| project_valder_char_valder_press | Character | Valder Press | not captured | docs/plates/project_valder_char_valder_press.webp | Yes |
| project_valder_char_villagers_poor | Character | Villagers Poor | not captured | docs/plates/project_valder_char_villagers_poor.webp | Yes |

**"Asset id" column note:** the panel's detail dialog exposes a UUID under
"Element details of `<uuid>`" in its header. That header text was found to be
unreliable — it is one of the fields that goes stale across quick successive
element opens (see Findings below), so it was captured reliably for only one
Element (`char_valder`, confirmed while its dialog was freshly and verifiably
open) and is marked "not captured" everywhere else rather than guessed.

17 / 17 found = 17 / 17 downloaded. Nothing in scope failed to download.

## Findings for the CTO (retrieval facts only — no image interpretation)

- **`project_valder_char_neighbor`'s asset does not depict what the name
  implies.** Re-verified via a clean page reload and a single screenshot
  showing the Element ID label and the main image together (not two separate
  reads): the panel genuinely serves a six-men-in-uniform image for this
  Element. Its "Name" field was also never set (defaults to the raw ID),
  unlike every other Character Element. This is a source-side condition, not
  a download-pairing error — cross-checked and ruled out by also re-verifying
  `char_guards_12` and `char_villagers_rich` (both correct) and by opening the
  raw bytes of `valder`, `mother`, `father`, `daughter`, `son`, and
  `tea_circle` directly (all correct).
- **`project_valder_char_tea_circle`** also has no Name field set (same
  raw-ID-as-name pattern as `neighbor`), though its image content matches its
  ID sensibly (four women at a tea table).
- **The true set of 17 Character Elements** found in the panel is:
  `char_chase_group`, `char_crowd_a`, `char_crowd_b`, `char_daughter`,
  `char_father`, `char_grandma`, `char_guard`, `char_guards_12`,
  `char_mother`, `char_neighbor`, `char_press`, `char_son`, `char_tea_circle`,
  `char_valder`, `char_valder_press`, `char_villagers_poor`,
  `char_villagers_rich`. `char_guard` and `char_guards_12` are two separate,
  distinct Elements (a lone figure vs. a lineup of twelve), as are
  `char_crowd_a`/`char_crowd_b` vs. `char_villagers_rich`/`char_villagers_poor`
  — none of these four are aliases of one another.

## Not downloaded (out of this task's scope, not a failure)

- All `project_valder_loc_*` Elements (14, including `loc_neighbor_door`) —
  assigned to another operator.
- All `project_valder_prop_*` Elements (15) — assigned to another operator.
- `project_valder_sb1_1` (Prop-categorised) and `project_valder_sb1_2`
  (Location-categorised), the two storyboard-panel Elements — assigned to
  another operator.

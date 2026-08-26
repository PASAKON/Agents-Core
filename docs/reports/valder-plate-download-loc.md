# Valder Collection No.7 — Location plate download manifest

Project: Higgsfield "The Valder Collection No.7"
(`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1`)
Scope: Locations category only (task-63d270c7).

Every row was confirmed by opening the Element's own detail panel (name +
category read there) and using that panel's own Download button, in the
same turn as the click — per the mislabelling-bug mitigation in the task
brief.

## Downloaded (15 of 15 found — 14 from brief list + 1 extra)

| Element name (panel) | Category (panel) | Asset/Element ID | File written | Downloaded |
|---|---|---|---|---|
| project_valder_loc_studio (Name: "Valder Studio") | Location | `project_valder_loc_studio` | `project_valder_loc_studio.webp` | yes |
| project_valder_loc_fountain_hall (Name: "Fountain Hall") | Location | `project_valder_loc_fountain_hall` | `project_valder_loc_fountain_hall.webp` | yes |
| project_valder_loc_home_interior (Name: "Home Interior") | Location | `project_valder_loc_home_interior` | `project_valder_loc_home_interior.webp` | yes |
| project_valder_loc_house_old (Name: "House Old") | Location | `project_valder_loc_house_old` | `project_valder_loc_house_old.webp` | yes |
| project_valder_loc_house_new (Name: "House New") | **Prop** (miscategorized — see note) | `project_valder_loc_house_new` | `project_valder_loc_house_new.webp` | yes |
| project_valder_loc_street_row (Name: "Street Row") | Location | `project_valder_loc_street_row` | `project_valder_loc_street_row.webp` | yes |
| project_valder_loc_aerial (Name: "Aerial") | Location | `project_valder_loc_aerial` | `project_valder_loc_aerial.webp` | yes |
| project_valder_loc_office_ext (Name: "Office Exterior") | Location | `project_valder_loc_office_ext` | `project_valder_loc_office_ext.webp` | yes |
| project_valder_loc_museum (Name: "Museum") | Location | `project_valder_loc_museum` | `project_valder_loc_museum.webp` | yes |
| project_valder_loc_neighbor_door (Name field clean; the panel's own "ELEMENT ID" field showed a glitched `@loc_project_valder_loc_neighbor_door` — Name field is authoritative) | Location | `project_valder_loc_neighbor_door` | `project_valder_loc_neighbor_door.webp` | yes |
| project_valder_loc_neighbor_parlour | Location | `project_valder_loc_neighbor_parlour` | `project_valder_loc_neighbor_parlour.webp` | yes |
| project_valder_loc_new_interior | Location | `project_valder_loc_new_interior` | `project_valder_loc_new_interior.webp` | yes |
| project_valder_loc_shop_ext | Location | `project_valder_loc_shop_ext` | `project_valder_loc_shop_ext.webp` | yes |
| project_valder_loc_shop_int | Location | `project_valder_loc_shop_int` | `project_valder_loc_shop_int.webp` | yes |
| **EXTRA, not on brief list** — `project_valder_sb1_2` (Name: "Storyboard Sence1B") | Location | `project_valder_sb1_2` | `project_valder_sb1_2.webp` | yes |

**Count: 15 downloaded out of 15 found (14/14 from the brief's list, plus 1 extra genuinely tagged Location).**

## Reconciliation against the brief's list

- **On brief list AND in panel:** all 14 — studio, fountain_hall, home_interior,
  house_old, house_new, street_row, aerial, office_ext, museum, neighbor_door,
  neighbor_parlour, new_interior, shop_ext, shop_int.
- **In panel but NOT on brief list:** `project_valder_sb1_2` / "Storyboard
  Sence1B" — Category = Location. Fetched anyway per instructions. A sibling
  element `project_valder_sb1_1` ("Storyboard Sence...") also exists but its
  Category is **Prop** — left alone, out of scope for this task.
- **On brief list but NOT in panel:** none — every listed name resolved to
  exactly one Element.

## Known data-quality issues found in the panel (report only, not fixed)

1. **`project_valder_loc_house_new` is filed under Category = Prop**, not
   Location, even though its name carries the `_loc_` infix and its own
   "Used in" list shows a `Location` tag. Same category-mis-detection bug the
   Location folder run before this one flagged for `neighbor_door`
   (see `scripts/browser/higgsfield-valder-neighbor-plates.js`) — this time it
   affected `house_new` instead.
2. **`project_valder_loc_neighbor_door`'s own "ELEMENT ID" field renders with
   a spurious `loc_` prefix** (`@loc_project_valder_loc_neighbor_door`) while
   its "Name" field is clean (`project_valder_loc_neighbor_door`). Treated
   Name as authoritative for the filename; flagging in case this indicates a
   deeper data issue on that Element.
3. **Cross-tab category-filter flicker**: this Chrome profile has 3 other
   operator tabs open on the same account. Repeatedly, closing a detail panel
   or switching to the "Locations" or "All" tab would silently re-render as
   "Props" a moment later (the other operator's active tab, presumably synced
   via a shared client-side store). Mitigated by re-confirming the tab state
   and the Element name in the SAME opened panel immediately before every
   Download click — never trusted a prior screenshot. One click on a
   `shop_ext`-positioned tile opened `project_valder_prop_dress_c2` instead
   mid-flicker; caught in the panel before any download and aborted, no file
   written for it.

## Credits

- Start of task (per brief): 1,932
- End of task (checked via Account menu → Credits): **1,930**
- Delta: -2. Not attributable to this task — no Generate / Rerun / Recreate
  button was ever clicked here. Consistent with the other three operators
  (one firing paid video generations) sharing this same Chrome/account.

## Spot-check

Opened 3 of the 15 downloaded files directly (not screenshots) and confirmed
the picture matches the name/panel: `project_valder_loc_neighbor_door.webp`
(teal wall, cream door, chrome starburst — matches), `project_valder_loc_shop_ext.webp`
(red wall, gold V, queue of period-dressed extras — matches), and
`project_valder_loc_house_new.webp` (modern cantilevered blue-glass house —
matches).

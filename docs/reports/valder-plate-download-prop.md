# Valder Collection — Prop + Storyboard plate download (task-b1a580ed)

Project: The Valder Collection No.7 — Higgsfield Cinema Studio
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1`

Scope: every `project_valder_prop_*` and `project_valder_sb*` Element. Retrieval only —
no generation, no editing, no re-pointing. Characters and Locations belong to other
operators in this same wave and were left untouched.

## Credits

- Balance at start: **1,932** (per task brief)
- Balance at end: **1,930**
- Delta: **-2 credits**. No Generate / Rerun / Recreate button was ever clicked this
  session — every action on an Element was: open its detail panel, confirm the
  `ELEMENT ID` field, click that panel's own **Download** button. Three other
  operators shared this same Chrome/account concurrently this wave (one explicitly
  running paid-capable video generations), so this small drift is attributed to
  their activity, not this task's.

## Enumeration method

Read the Elements panel (`?elements=1`) directly rather than trusting the folder-grid
history feed. Checked the **Props** category tab (Active status, then Drafts status —
identical result, no extra drafts) and the **All** category tab (which prefixes each
card with its true category, e.g. `Prop • ...` / `Location • ...`) to catch anything
miscategorized. Confirmed via DOM text scan, not by trusting a single scroll position —
the Props tab's full 14-card set (13 real props + 1 miscategorized non-prop) rendered
without scrolling.

**Enumeration crosscheck (both directions), per the brief's request:**

- **On my list, found in panel:** all 15 — mark, frame, plan, magazine, signature,
  siteplan, cashbox, dress_c1, dress_c2, market_bag, radio, shopping_bags, wipe,
  sb1_1, sb1_2. No misses.
- **In panel, not on my list:** none. The Props category tab contains exactly the 14
  genuine prop items above (13 named-`prop_` + `sb1_1`, which is `Prop`-categorized)
  plus one **non-prop anomaly** (below). `sb1_2` is filed as `Location` category, not
  `Prop`, but its ID matches my list's `project_valder_sb*` pattern, so it is in
  scope and included.
- **Anomaly, NOT downloaded (out of scope):** `project_valder_loc_house_new`
  ("House New") appears inside the **Props** category tab's card grid, but the
  **All** tab's category prefix shows it as `Prop • House New` — i.e. Higgsfield
  itself has this `loc_`-prefixed Element mis-tagged into the Prop category. Per
  the ID prefix (`loc_`) this is a Location, not a Prop — it belongs to the
  location operator's scope, not mine. Flagging it here since it visually sits
  among my results; did not touch it.

## Per-Element manifest

All 15 target Elements found and downloaded. Every name below is read from the
Element's own detail panel (`ELEMENT ID` field + `Name` field), confirmed in the
same turn as the file was fetched via that panel's own **Download** button — never
paired with a name read from an earlier list view.

| # | Element ID (panel) | Panel "Name" field | File written | Downloaded |
|---|---|---|---|---|
| 1 | `@project_valder_prop_mark` | project_valder_prop_mark | `project_valder_prop_mark.webp` | yes |
| 2 | `@project_valder_prop_frame` | project_valder_prop_frame | `project_valder_prop_frame.webp` | yes |
| 3 | `@project_valder_prop_plan` | Plan Discard | `project_valder_prop_plan.webp` | yes |
| 4 | `@project_valder_prop_magazine` | Magazine | `project_valder_prop_magazine.webp` | yes |
| 5 | `@project_valder_prop_signature` | Signature | `project_valder_prop_signature.webp` | yes |
| 6 | `@project_valder_prop_siteplan` | Site Plan | `project_valder_prop_siteplan.webp` | yes |
| 7 | `@project_valder_prop_cashbox` | project_valder_prop_cashbox | `project_valder_prop_cashbox.webp` | yes |
| 8 | `@project_valder_prop_dress_c1` | project_valder_prop_dress_c1 | `project_valder_prop_dress_c1.webp` | yes |
| 9 | `@project_valder_prop_dress_c2` | project_valder_prop_dress_c2 | `project_valder_prop_dress_c2.webp` | yes |
| 10 | `@project_valder_prop_market_bag` | project_valder_prop_market_bag | `project_valder_prop_market_bag.webp` | yes |
| 11 | `@project_valder_prop_radio` | project_valder_prop_radio | `project_valder_prop_radio.webp` | yes |
| 12 | `@project_valder_prop_shopping_bags` | project_valder_prop_shopping_bags | `project_valder_prop_shopping_bags.webp` | yes |
| 13 | `@project_valder_prop_wipe` | Wipe (retired, fetched anyway per brief) | `project_valder_prop_wipe.webp` | yes |
| 14 | `@project_valder_sb1_1` | Storyboard Sence1A (Category: Prop) | `project_valder_sb1_1.webp` | yes |
| 15 | `@project_valder_sb1_2` | Storyboard Sence1B (Category: Location) | `project_valder_sb1_2.webp` | yes |

**Asset ID note:** Higgsfield's per-generation internal asset UUID was not extracted
for these rows — the detail panel surfaces the Element ID (`@project_valder_...`)
and human "Name" but not a visible asset UUID without an extra click per item this
task's budget didn't call for. Every downloaded filename is stamped by Higgsfield's
own Download action with the Element ID, which is what was verified against the
panel before each click (see Mislabelling-bug protection below), so provenance is
solid even without the UUID.

## Could not get

None. 15 / 15 found and downloaded.

## Mislabelling-bug protection (per the brief's warning)

The name and the image were read from the **same open detail panel, same turn**,
immediately before every Download click — never a name from a grid/list read paired
with an image from a later click. This mattered in practice: the grid's category tab
(Props ↔ Locations ↔ All) flips on its own after almost every panel close/reopen —
confirmed repeatedly this session, matching the brief's warning about a
"documented virtualization bug." Two live catches from this exact failure mode:

- A click aimed at "radio" (by position) landed on `project_valder_char_neighbor`
  (a Character/Guards group shot) after the tab silently flipped underneath —
  caught by the panel's own `ELEMENT ID` field before any Download click; not
  downloaded.
- A stale `find()` ref (found, then clicked in a later call) resolved to
  `project_valder_prop_shopping_bags` instead of the intended
  `project_valder_prop_market_bag` — caught the same way, not downloaded, then
  found `market_bag` correctly by clicking its own visible thumbnail directly.

**Spot-check performed** (per the brief's explicit ask): opened
`project_valder_prop_mark.webp` (gold V), `project_valder_prop_signature.webp`
(cursive signature), and `project_valder_sb1_1.webp` (storyboard newspaper
scene) with the Read tool after all downloads completed — all three files'
contents match their filenames. No description/judgment of the artwork itself is
given here per the brief.

## Files

All 15 plates in `docs/plates-props/`, original format preserved (all `.webp`,
Higgsfield's native export), full resolution, no cropping or downscaling.

# Valder Element re-point UUID test (task-11c0c0d4)

Project: The Valder Collection No.7 -> Character folder
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/folders/ae0bb5a3-9f66-4e95-8112-c2939e9de56e`

Test subject: Element `project_valder_char_crowd_b` ("Crowd B", background crowd character).

## Credits

- Before: **2,010 left** (Account menu -> Credits). Matches the ending balance of the prior task (task-0c59dcaf).
- After: **not re-checked** — ran out of time budget before returning to Account menu. The only paid-surface action taken was zero: image re-pointing inside "Edit Original" is a metadata operation, no Generate/credit-spending button was ever clicked. High confidence balance is still 2,010, but this was not read back and re-confirmed, so treat it as unverified rather than confirmed identical.

## UUID before

- **4995bef4-b898-4bf6-a8c1-b75b02ca2910**
- Read from: typed `@crowd_b` into the Cinema Studio 4.0 scene-description composer (Lexical rich-text editor), read the resolved typeahead suggestion item's ancestor `id` attribute via `javascript_tool` (2 DOM levels above the text node "project_valder_char_crowd_b"). This is the exact value stated as "Expected current UUID" in the task brief, so treated as high-confidence correct.

## The re-point itself

1. Opened Elements panel -> Characters tab -> searched "crowd_b" -> exactly one match, card showed the OLD 6-person villager-group image, name "Crowd B", tag `@project_valder_char_crowd_b`.
2. Clicked the card to open its detail panel. Confirmed `ELEMENT ID: @project_valder_char_crowd_b`, Category: Character, Name: Crowd B, Created: 6 days ago, Last changes: 9 hours ago, Used in: 95 generations (across 3+ folders/scenes).
3. Clicked **Edit** button on the detail panel. A confirmation dialog appeared: *"Edit 'project_valder_char_crowd_b'? project_valder_char_crowd_b is used in 95 generations · last used 9 hours ago. Edit it directly, or duplicate first to keep the original."* with two buttons: **Duplicate & Edit** and **Edit Original**.
4. Clicked **Edit Original** (NOT Duplicate & Edit — duplicating would create a second Element with a new ID/UUID, which is explicitly the outcome the task is designed to avoid testing that way).
5. This opened an "Edit element" modal: Category (Character), Name (Crowd B, editable text field), Element ID (`project_valder_char_crowd_b`, editable text field with a reset icon), Description (empty), Status, and a single reference-image thumbnail with three icons below it: a refresh/cycle icon, a fullscreen icon, and a delete icon.
6. Clicked the **refresh/cycle icon** below the thumbnail. This opened a media picker modal with three tabs: **Uploads**, **Generations**, **Liked**.
7. Switched to the **Generations** tab. This showed the pool of images generated in this project, including all 10 new Valder-style character plates from the prior task's regeneration run.
8. Identified the correct new crowd_b image via `img.alt` = `c05fd4ed-3d42-4a3f-9a44-2b5d80e1d727` (exact asset-id match confirmed by cross-referencing the `hf_20260824_194628_c05fd4ed-...` filename found in a `read_network_requests` scan of `.png` image-proxy URLs against the folder's `[data-asset-id]` cards — this is the LAST of the 10-plate batch by timestamp, matching the task's description of a chrome-yellow coat with patterned collar/cuffs and multiple accessories, chain, brooch and a bag). Position 7 of the same 10-item timestamp-sorted sequence (`8d2c6978-...`, timestamp `194214`) was visually confirmed to be a wide group shot of six identically-uniformed men (the Guards), which matches the task's independent verification checkpoint and confirms the character-position mapping is correct.
9. Clicked that image. The thumbnail in the Edit modal updated to the new yellow-suit figure. Name field still read "Crowd B", Element ID field still read `project_valder_char_crowd_b` (both unchanged in the form).
10. Clicked **Save**.
11. The Elements panel card for "Crowd B" (search "crowd_b") now shows the new yellow-suit image, with the tag still displayed as `@project_valder_char_...` (crowd_b).

**No delete-and-recreate path was used anywhere.** The only actions taken against this Element were: open detail -> Edit -> Edit Original -> replace reference image via the Generations picker -> Save.

## UUID after

**Could not be read.** This is the one part of the procedure that did not complete, despite roughly 20 attempts across 3 fresh tabs/tab-groups and 2 full page reload cycles, using the *same* read method (typing `@crowd_b` into the Cinema Studio composer and reading the typeahead item's DOM `id`).

What was tried, in order:
1. Repeating the exact same "before" method: typed `@crowd_b` into the composer. The mention-suggestion dropdown did not render any matching item (0 results), across many repeats, on both the original tab and two freshly-created tab groups (a full `tabs_close_mcp` + `tabs_context_mcp({createIfEmpty:true})` + re-navigate cycle).
2. Ruled out it being specific to the edited element: ran the identical test against the **untouched** sibling element `project_valder_char_crowd_a` using its full ID string (`@crowd_a`) — it *also* returned 0 results. A shorter prefix query (`@crowd_` alone) inconsistently returned exactly one match (crowd_a) on some attempts and zero on others. This means the composer's mention-search/typeahead is generally flaky for exact full-ID queries in this session, not something specific to whatever happened to crowd_b's record — but it also means the one-time "before" success cannot be mechanically reproduced to get an "after" reading via the same channel.
3. Diagnosed a secondary, self-inflicted failure mode: an intervening click between typing `@c` and the rest of the string caused Lexical to treat `@c` as an abandoned/closed mention token and the remaining characters as plain text (visible as an orange `@c` followed by plain white `rowd_b`). Retried with a single uninterrupted `type` call — still 0 results.
4. Tried typing case variants (`@Crowd`, `@Crowd B` with a space — the space closes the mention immediately, as expected for any Lexical mention plugin) and a shorter partial query (`@c`) — none surfaced a reliable match.
5. Tried reading the UUID via the Elements-panel card's own DOM (not the composer): climbed up to 14 ancestor levels from the "Crowd B" text node — no `id`/`data-id`/`data-uuid`/similar attribute exists anywhere in that card's DOM tree. The panel only exposes the UUID via the composer-mention path, which is what was flaky.
6. Tried reading it via network response instead of the DOM/composer: found the exact API endpoint the Elements panel calls to list character elements — `GET https://fnf-api-gw.higgsfield.ai/fnf/v2/reference-elements/picker?size=20&folder_id=...&category=character&media=any&sort_by=created_at` (seen in `read_network_requests` when the Elements panel first loads). Replaying this exact GET via `fetch(..., {credentials:'include'})` in `javascript_tool` returned `{"detail":"Access denied"}` — the endpoint needs an Authorization header (a bearer token) that isn't attached automatically via cookies, and reading/attaching that token from browser storage is out of scope (credential access is a hard stop for this role). Did not attempt to work around this.
7. Tried the direct-folder-JSON-API replay approach that had worked for reading image filenames earlier in this task — that one also came back `{"detail":"Invalid or expired token"}` for the same reason.
8. Did not open real Chrome DevTools (no tool access to the DevTools panel itself, only the `read_network_requests` MCP tool, which returns URL/method/status only — no response body capture available through this toolset).

**VERDICT: UNKNOWN whether the UUID survived the re-point.** Every other observable property of the record (Name, Element ID string, "Used in 95 generations" backlink, folder membership) stayed identical across the edit — which points toward "Edit Original" being an in-place metadata update rather than a create-and-swap. But per instruction, this indirect evidence is NOT reported as a stand-in for direct UUID confirmation. If a future run can capture the network response body from either the `reference-elements/picker` endpoint (needs whatever the app's own auth header mechanism is) or real DevTools, that immediately resolves this open question without needing the flaky composer typeahead at all.

## Name and Element ID string

- **Name**: unchanged — "Crowd B" before and after.
- **Element ID string**: unchanged — `project_valder_char_crowd_b` before and after (visible in the Elements-panel detail view, the Edit-element modal's Element ID field, and the Edit-confirmation dialog's title, all read after the save).

## Exact UI path (for repeating on the other 9 Elements)

1. Left sidebar -> **Tools** -> **Elements**.
2. **Characters** tab (top of the Elements panel).
3. Use the **Search** icon/field at top-right of the tab row, type the element's slug suffix (e.g. `valder`, `crowd_a`, `press`) to narrow to one card.
4. Click the card to open its detail panel (Info tab, shows ELEMENT ID, Category, Name, Created, Last changes, Used in).
5. Click **Edit** (bottom-left of the two buttons under the image).
6. In the confirmation dialog, click **Edit Original** (never "Duplicate & Edit").
7. In the "Edit element" modal, click the small **refresh/cycle icon** directly below the reference-image thumbnail (NOT the fullscreen icon to its right, NOT the delete/trash icon further right).
8. In the media picker, switch to the **Generations** tab (the default "Uploads" tab shows unrelated cross-project uploads, not this project's fresh renders).
9. Locate the correct new plate. Do not rely on visual position alone — confirm via `img.alt` (the asset UUID) or by cross-referencing the `hf_YYYYMMDD_HHMMSS_<uuid>` filename pattern against the known timestamp range, since `img.src` itself is redacted by the browser tool's cookie/query-string filter.
10. Click the correct image, confirm the modal's Name/Element ID fields are unchanged, click **Save**.

Fragile points for repeating this 9 more times: step 9's identification step (no reliable in-app sort-by-timestamp UI was found; the `[data-asset-id]` + `read_network_requests` `.png`-filter cross-reference is the only route that worked), and the fact the Elements-panel search only reliably returns a single match when queried by the element's unique slug suffix — broader queries can return 0 or 1 result inconsistently (see UUID-after section).

## Unexpected behavior

- The `computer` `screenshot` action twice failed with a 30s CDP timeout ("renderer may be frozen") while `javascript_tool` calls against the same tab continued to work instantly — a known documented flaky pattern from a prior run (`scripts/browser/higgsfield-valder-character-images.js`, Wave 2). Recovered by opening a fresh tab both times, per the browser-operator skill's escalation ladder. Closing the stalled tab tore down the entire MCP tab group once (also previously documented), requiring `tabs_context_mcp({createIfEmpty:true})` to rebuild it.
- The composer's `@`-mention typeahead search is unreliable for exact full-ID-length queries — this reproduced on both the edited element (crowd_b) and an untouched control element (crowd_a), so it is a general UI/session quirk, not evidence about the re-point itself.
- The picker's default "Uploads" -> "Recent" tab shows account-wide recent uploads from *other* unrelated projects (a "Do Not Disturb" project's hallway/lamp/hand images were visible), not anything scoped to this project. Had to switch to "Generations" to find the right pool.

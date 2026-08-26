/**
 * scripts/browser/higgsfield-valder-plate-dl-loc.js
 *
 * Replay notes for downloading the LOCATIONS-category Element plates of
 * "The Valder Collection No.7" project, task-63d270c7 (2026-08-26).
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1)
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. This is a DOWNLOAD-only companion to
 * higgsfield-valder-neighbor-plates.js (which generates); read that file
 * first for the base composer/generation recipe if this project ever needs
 * new Location plates generated. This file only covers retrieval.
 *
 * Result this run: 15/15 plates confirmed+downloaded (14 from the brief's
 * list + 1 extra genuinely tagged Location: project_valder_sb1_2 /
 * "Storyboard Sence1B"). 0 credits spent (no Generate/Rerun/Recreate ever
 * clicked). Full per-plate table in docs/reports/valder-plate-download-loc.md.
 *
 * ============================================================
 * THE MISLABELLING BUG THIS FILE EXISTS TO AVOID
 * ============================================================
 * A prior operator on a sibling task wrote a file named for one Element that
 * actually contained a DIFFERENT Element's image, because the name was read
 * from a list in one pass and the image was fetched in a later pass, while
 * this panel's virtualized grid re-ordered underneath. NEVER do that.
 *
 * The only safe sequence is:
 *   1. Click a candidate tile to OPEN its detail panel.
 *   2. In that SAME panel, read "Category" and "Name" (or the "ELEMENT ID"
 *      field -- but see gotcha #2 below, Name is sometimes more reliable).
 *   3. If it matches what you wanted, click THAT PANEL'S OWN Download
 *      button. Never click Download from a different panel/turn than the
 *      one where you confirmed the name.
 *   4. Close the panel, THEN move to the next candidate.
 *
 * ============================================================
 * GOTCHA #1: cross-tab category-filter flicker
 * ============================================================
 * This Chrome profile is shared with up to 3 other operator tabs on the same
 * Higgsfield account (other categories, or a video-generation composer).
 * Observed repeatedly this run: clicking the "Locations" tab, or closing a
 * detail panel, would render correctly for a moment and then silently
 * snap to "Props" (breadcrumb AND the underlying grid content), apparently
 * because another tab's category selection is synced client-side (likely
 * localStorage + a `storage` event, or similar). This is NOT something you
 * can "fix" by waiting longer -- it can happen at any time depending on what
 * the other operator's tab is doing.
 *
 * ONE CONFIRMED INCIDENT this run: clicked the on-screen position of the
 * `shop_ext` tile (red-wall-gold-V location) and the detail panel that
 * opened was actually `project_valder_prop_dress_c2` (a Props Element) --
 * the grid had flickered to Props between the screenshot and the click.
 * Caught immediately because step 2 above was followed (checked Category:
 * Prop, Name: dress_c2) -- closed without downloading, no harm done, no
 * wasted file. This is the entire reason step 2 is mandatory, not optional.
 *
 * MITIGATION THAT WORKED: use the panel's own Search box (top of the
 * Elements list, magnifying-glass icon) instead of scrolling/clicking
 * category tabs. Searching for a specific, near-unique substring of the
 * Element's name collapses the grid to 1 (rarely 2) result(s) regardless of
 * which category tab is currently selected underneath -- the search itself
 * seems to search across ALL categories. This was far more reliable than
 * fighting the tab flicker by scrolling the "All" or "Locations" grid.
 *
 * Typing into the search box via the `computer` tool's `type` action was
 * itself unreliable this run (silently no-op'd on ~half the attempts, likely
 * because the click-to-focus and the type landed on either side of a
 * cross-tab re-render). The reliable way to set it:
 *
 *   const input = [...document.querySelectorAll('input')]
 *     .find(i => i.placeholder === 'Search');
 *   const setter = Object.getOwnPropertyDescriptor(
 *     window.HTMLInputElement.prototype, 'value').set;
 *   setter.call(input, 'YOUR_SEARCH_TERM');
 *   input.dispatchEvent(new Event('input', {bubbles:true}));
 *
 * This uses the native setter + a real `input` event so React's controlled-
 * input state actually updates (a plain `input.value = 'x'` does NOT trigger
 * React's onChange). After setting it, click the "All" tab once (it may
 * also have flickered to a filtered category) and screenshot/read before
 * clicking the resulting single card.
 *
 * ============================================================
 * GOTCHA #2: the panel's own "ELEMENT ID" field can itself be wrong
 * ============================================================
 * For `project_valder_loc_neighbor_door`, the "ELEMENT ID" field rendered as
 * `@loc_project_valder_loc_neighbor_door` (an extra spurious `loc_` prefix),
 * while the "Name" field on the same panel read the correct
 * `project_valder_loc_neighbor_door`. The download button's resulting
 * filename actually matched the glitched ID
 * (`loc_project_valder_loc_neighbor_door.webp`), so this file had to be
 * renamed on copy into the worktree. When the two fields disagree, prefer
 * "Name" for what to call the asset, and double check the actual filename
 * Chrome saved before assuming it matches.
 *
 * ============================================================
 * GOTCHA #3: some genuinely Location-category assets are filed as Prop
 * ============================================================
 * `project_valder_loc_house_new`'s own Category field says "Prop", not
 * "Location" -- yet its "Used in" section on the same panel lists a
 * `Location` tag, and its name carries the `_loc_` infix. This is an
 * occasional model mis-categorization on Element creation (also seen on a
 * sibling task for `neighbor_door`, see
 * higgsfield-valder-neighbor-plates.js finding #5) -- it is NOT systemic,
 * but you cannot assume the visible category tab (Locations/Props/etc.)
 * contains every asset that conceptually belongs to it. The Search-box
 * approach above finds these regardless of which category tab they are
 * filed under, which is another reason to prefer it over browsing tabs.
 *
 * ============================================================
 * GOTCHA #4: async multi-step scroll/click JS can hang the CDP call
 * ============================================================
 * A `javascript_tool` script that does `await new Promise(r=>setTimeout(...))`
 * loops interleaved with DOM manipulation (e.g. stepping scrollTop across an
 * entire virtualized grid) twice hit
 * `CDP sendCommand "Runtime.evaluate" timed out after 45000ms`. The page
 * itself kept working (a follow-up `tabs_context_mcp` + screenshot showed
 * the scroll had actually happened), so this looks like a harness-side
 * response timeout rather than a real page freeze -- but don't chain many
 * `await setTimeout` cycles in one javascript_tool call; do it in shorter
 * bursts across multiple tool calls instead, or use the Search box (above)
 * to avoid needing to scroll/enumerate at all.
 *
 * ============================================================
 * Per-plate loop used this run
 * ============================================================
 *   1. Set the Search box to a name fragment (JS snippet in gotcha #1).
 *   2. Click the "All" tab (breadcrumb/category may have flickered).
 *   3. Screenshot: confirm exactly one (or a small, distinguishable set of)
 *      result card(s) with a caption like "Location • <Display Name>".
 *   4. Click the card to open its detail panel.
 *   5. In that panel, read Category + Name (and ELEMENT ID, cross-checking
 *      against gotcha #2). If it is not the Location Element you wanted,
 *      close and retry -- do not download.
 *   6. Click that panel's own Download button.
 *   7. Wait ~1-2s (no reliable "Download complete" toast was visible every
 *      time this run -- ONE download silently failed to appear in
 *      ~/Downloads despite the click registering and the panel showing no
 *      error; always verify the file landed with a filesystem check before
 *      assuming success, and retry the whole panel-open+download sequence
 *      if it did not).
 *   8. Close the panel (X button, top-right of the panel).
 *   9. Copy the file from ~/Downloads into
 *      docs/plates-locations/<exact_name>.webp inside the repo, using the
 *      Name field (not necessarily the raw downloaded filename -- see
 *      gotcha #2) to name it.
 *  10. Commit every ~5-10 plates, not just at the end.
 *
 * Shared ~/Downloads directory: the other operators on this task (Characters,
 * Props) download into the SAME ~/Downloads folder on this machine. Always
 * `cp` by the specific expected filename, never a broad glob -- a plain
 * `cp ~/Downloads/*.webp` would have pulled in other operators' files too.
 */

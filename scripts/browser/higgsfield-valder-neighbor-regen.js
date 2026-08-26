/**
 * scripts/browser/higgsfield-valder-neighbor-regen.js
 *
 * Replay notes for regenerating and re-pointing the single Element
 * `project_valder_char_neighbor` (UUID e56fed30-6d22-4fcb-8e3f-c4ef9610729c),
 * task-31b49224 (2026-08-26), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Thin addendum to higgsfield-image-gen.js (base
 * paste/desync/verify recipe) and higgsfield-valder-neighbor-plates.js /
 * valder-repoint-s2.md (the re-point flow) -- read those first, this file
 * only records what was NEW or notable this run.
 *
 * Result: 1/1 attempt, no reshoot needed. 2 credits (1,932 -> 1,930).
 * New asset 77b6a8af-fc94-4329-89a2-12a32ecdfa04. Element re-pointed,
 * Name field set, UUID confirmed unchanged. No "Check eligibility" control
 * found anywhere on the Element panel (Info tab, Edit modal, More menu,
 * Status dropdown) -- second operator in a row who could not find it.
 *
 * STEP 1 -- generation (Character folder composer):
 *   1. Folder URL: .../folders/ae0bb5a3-9f66-4e95-8112-c2939e9de56e
 *      (Character folder, Valder Collection No.7).
 *   2. Fresh navigate loaded composer in VIDEO mode by default (matches
 *      prior waves) -- clicked the small "Image" icon bottom-left of the
 *      composer (above the settings pills) to switch, confirmed via
 *      button-text dump rather than a screenshot.
 *   3. Model defaulted to "Higgsfield Soul Cinema" -- opened the model
 *      picker pill, selected "GPT Image 2" from the list (also offers
 *      Seedream 5.0 Pro / 4.5, AI Cast, Cinematic Locations -- don't
 *      confuse these).
 *   4. Quality pill defaulted to High, resolution to 2K (7 credits at
 *      GPT Image 2 default). Set Quality -> Medium (3 credits @ 2K), then
 *      Resolution -> 1K (2 credits final). Quantity stepper already read
 *      1/4 (current 1, max 4) -- no change needed for qty 1.
 *   5. Paste (synthetic ClipboardEvent, text/plain only) landed correctly
 *      on the FIRST attempt this run -- normalized length matched source
 *      exactly (2464 chars) on the first read-back. (An immediate read
 *      right after the paste call showed 0 length once -- this was a
 *      transient render-lag false negative, not a real failure: a second
 *      read a moment later showed the full correct text. Don't trust a
 *      single 0-length read as proof of paste failure; re-read once before
 *      concluding it didn't land.)
 *   6. Desync fix (focus + Selection API cursor-to-end + real Space + real
 *      BackSpace) applied once, immediately before the click.
 *   7. Generate clicked via the synthetic PointerEvent sequence
 *      (pointerdown/mousedown/pointerup/mouseup/click, all bubbles+
 *      cancelable, at the button's real rect center) -- fired cleanly on
 *      the FIRST attempt, no no-op cycle this run. "Generation started"
 *      toast present, "All assets" 252 -> 253.
 *   8. Poll `[data-asset-id]` top card's `data-job-status` every ~10s.
 *      Took ~60s total (in_progress -> completed) for this GPT Image 2 /
 *      Medium / 1K single image -- much shorter than Seedance video waits,
 *      no need for the 20-min video poll cadence here.
 *   9. Visual check: zoom into the card's bounding rect (from a JS-computed
 *      screenshot-scaled region) first -- cheap, sufficient to confirm
 *      wardrobe/pose/colour-panel checklist. Opened the full detail card
 *      (`role="dialog"`, click the thumbnail near its visual center, not
 *      the top-left corner which can hit a hidden select checkbox) only to
 *      judge the face closely (skin tone, expression). This is the "New"-
 *      badge-obscures-the-face problem from a grid zoom -- the badge sits
 *      right over the face in the small thumbnail, so a face judgment
 *      needs the opened card, not just a zoom.
 *
 * STEP 2 -- re-point (Elements panel, project root ?elements=1):
 *   1. Left-sidebar "Elements" tool -> lands on whichever category tab was
 *      last active (Props, this run) -- click "Characters" explicitly, or
 *      "All" if you want the duplicate-check below.
 *   2. Search box, type the element's unique slug fragment ("neighbor").
 *      In "Characters" tab: exactly 1 match. Cross-checked in "All" tab
 *      too: 3 matches for "neighbor" total, but only 1 is Category
 *      "Character" (the other 2 are Location elements for
 *      neighbor_door -- unrelated, not a miscategorised duplicate of this
 *      element). No duplicate/orphan copy of the Character element exists.
 *   3. Click the card -> opens the detail panel directly into Info tab.
 *      Confirmed: ELEMENT ID @project_valder_char_neighbor, Category
 *      Character, Name field blank (as the task brief stated -- "has never
 *      been set"), Used in: 1 folder.
 *   4. Click "Edit" (bottom-left button under the image). NOTE: unlike the
 *      `project_valder_char_crowd_b` run (docs/reports/valder-element-
 *      repoint-test.md), which is used in 95 generations and shows an
 *      "Edit 'X'? ... Duplicate & Edit / Edit Original" confirmation
 *      dialog first, THIS element (used in only 1 folder / low usage) went
 *      straight to the "Edit element" modal with no confirmation step at
 *      all. The confirmation dialog appears to be usage-count-gated, not
 *      universal -- don't assume it will always appear, and don't assume
 *      its absence means something went wrong.
 *   5. In the Edit modal, the Name input already SHOWED the string
 *      "project_valder_char_neighbor" even though the Info panel had just
 *      shown Name as blank. This is very likely the UI falling back to
 *      display the Element ID as filler text in an empty Name field, not a
 *      real saved value -- confirmed after Save that the Info panel's Name
 *      row now reads "project_valder_char_neighbor" for real (Last changes
 *      timestamp advanced to "just now"), so the field genuinely was unset
 *      before and is genuinely set now. Left the Name field exactly as
 *      shown (didn't need to retype it) and it saved correctly as the
 *      literal string "project_valder_char_neighbor".
 *   6. Click the refresh/cycle icon directly below the reference-image
 *      thumbnail (NOT the fullscreen icon to its right, NOT the trash icon
 *      further right) -> opens the media picker (Uploads / Generations /
 *      Liked tabs). Default "Uploads" -> "Recent" tab shows cross-project
 *      unrelated uploads (a horror-project's hallway/lamp/door images were
 *      visible this run too, same as valder-element-repoint-test.md) --
 *      always switch to "Generations".
 *   7. Located the target tile by EXACT match, not by eye: queried the two
 *      open `[role="dialog"]` elements for the one whose innerText
 *      contains "Generations", then `.querySelector('[aria-label="<the
 *      new asset's UUID>"]')` inside that specific dialog. This is the
 *      same recipe as higgsfield-valder-neighbor-plates.js step 9 --
 *      worked first try, single candidate dialog match, no ambiguity
 *      (only one generation this run, so no timestamp-sorting cross-check
 *      was needed).
 *   8. Click the tile -> Edit modal's thumbnail updates to the new image.
 *      Confirmed Name/Element ID fields unchanged in the form before
 *      clicking Save.
 *   9. Click Save -> "Element saved." toast. Grid card for this Character
 *      immediately shows the new woman thumbnail.
 *
 * "Check eligibility" control -- NOT FOUND, second operator in a row:
 *   Checked every surface on the Element's own panel: the Info tab's
 *   buttons (Download / Edit / Share / More), the "More" (...) dropdown
 *   (Use / Pin / Duplicate / Move to / Copy to / Delete -- nothing
 *   eligibility-related), the "Status" pill at the bottom of the detail
 *   view (a 3-option colour-coded workflow label: In progress / Needs
 *   review / Approved -- NOT an eligibility check, left untouched at "No
 *   status"), and the full Edit modal (Category / Name / Element ID /
 *   Description / Status, same 3 options, no eligibility action). No such
 *   control exists anywhere reachable from this Element's own UI. Per the
 *   task brief: reporting this plainly rather than inventing a workaround,
 *   same as the prior operator on a different Element.
 *
 * VERIFY (mandatory fresh-reload check):
 *   Full `navigate()` back to `?elements=1` (not a soft in-app nav) ->
 *   Characters tab (or All) -> search the slug fragment again -> single
 *   card already shows the new image in the grid thumbnail before even
 *   opening it -> click to open -> waited ~3s before screenshotting (the
 *   detail dialog is a documented buggy singleton that can serve stale
 *   content from a PREVIOUSLY opened card for several seconds -- since
 *   this was the first card opened after a hard page reload there was no
 *   prior card's state to leak, but the wait was applied anyway as cheap
 *   insurance) -> single screenshot shows ELEMENT ID
 *   `@project_valder_char_neighbor` and the new woman image together,
 *   Name row = `project_valder_char_neighbor`, Last changes = "2 minutes
 *   ago". This is the mandatory verification screenshot.
 *
 * UUID-preserved check (composer @mention resolution, NOT the flaky
 * composer-typeahead-typing method from valder-element-repoint-test.md --
 * that report's "UUID after: could not be read" failure was from TYPING
 * `@crowd_b` into the composer, letter by letter, and reading the
 * autocomplete dropdown item, which reproduced as flaky even against an
 * untouched control element. This run used a full literal-string PASTE of
 * `@project_valder_char_neighbor` instead (same mechanism the neighbor-
 * plates.js recipe uses to auto-resolve @tags in a full prompt), which
 * resolves deterministically and was NOT flaky):
 *   1. Navigate to the Character folder composer (a fresh navigate loads
 *      the composer in Video mode again -- switch to Image mode via the
 *      bottom-left icon toggle if you need the settings pills correct for
 *      anything else, but for a pure UUID read the mode doesn't matter,
 *      only the presence of a live contenteditable does).
 *   2. Clear whatever's in the box (real Cmd+A + Delete works fine when
 *      there's no mention chip yet; if a mention chip is present, the
 *      `beforeinput`/`deleteContentBackward` synthetic dispatch alone did
 *      NOT clear it in this run -- only a REAL Cmd+A + Delete keypress via
 *      the driving tool cleared a chip-containing editor. Note this is the
 *      opposite of higgsfield-valder-neighbor-plates.js finding #2, where
 *      beforeinput was the FIX for dead real-keyboard input -- both
 *      techniques exist for different failure modes; try beforeinput
 *      first since it's cheaper, fall back to real keys if content
 *      persists).
 *   3. Paste (synthetic ClipboardEvent, text/plain) the literal string
 *      `@project_valder_char_neighbor` alone.
 *   4. Read `[...editor.querySelectorAll('[data-beautiful-mention]')]
 *      .map(m => m.getAttribute('data-beautiful-mention'))` -- resolved to
 *      `@e56fed30-6d22-4fcb-8e3f-c4ef9610729c` (the leading `@` in the
 *      attribute value is literal, part of how this composer stores it --
 *      strip it when comparing against a bare-UUID source). Matches the
 *      task brief's stated pre-existing UUID exactly.
 *   5. Cleared the composer again afterward (real Cmd+A + Delete required
 *      here too, per step 2's note) before leaving the tab. Generate was
 *      NEVER clicked during this verification pass.
 *
 * Credit ledger check: account avatar (top-right) -> menu shows
 * "N left" text, read via
 * `document.body.innerText.match(/[\d,]+\s*(left|credits)/i)`. Closed the
 * menu with a plain click on empty page background both times, never
 * Escape (Escape-on-avatar-menu has previously destroyed the entire MCP
 * tab group on this exact project, per higgsfield-image-gen.js Wave 4).
 */

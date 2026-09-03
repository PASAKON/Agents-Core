/**
 * scripts/browser/higgsfield-absence-elements-fetch.js
 *
 * Replay notes for downloading source plates behind named `project_absence_*`
 * Elements, task-5e5928ec (2026-09-04), same project as the Valder Collection
 * No.7 (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP, interleaved with real `computer` clicks. This run
 * reused the recipe from higgsfield-valder-plate-download.js almost
 * unchanged; the differences found this run are below.
 *
 * Result: 10/10 named Elements + 1 bodyguard-search candidate downloaded,
 * 0 credits (read-only asset retrieval, Generate never touched).
 *
 * WHAT'S THE SAME AS higgsfield-valder-plate-download.js (read that file
 * first -- this one only documents deltas):
 *   - Full navigate() reload is the reliable way to clear the stuck-dialog
 *     bug. Confirmed again this run.
 *   - After reload, wait ~2-3s, then re-click the "Characters" tab (position
 *     ~(568,103)) before searching -- it silently reverts to whatever
 *     category was last active (this run: kept landing back on "Locations").
 *   - Set the search box via the native input setter + dispatchEvent, not
 *     real typing.
 *   - VERIFY the dialog's own Element ID leaf text before ever clicking
 *     Download. Regex used this run: /^@(project_absence_)?char_/ -- widen
 *     the prefix group to match BARE ids with no project prefix (see below).
 *
 * NEW FINDINGS THIS RUN:
 *
 * 1. BARE (NO-PROJECT-PREFIX) ELEMENT IDS EXIST ALONGSIDE PREFIXED ONES.
 *    `@char_registrar` is a real, separate Element from
 *    `@project_absence_char_registrar_b` -- both exist, both are genuine,
 *    different people (cream suit holding a ledger vs. dark suit holding a
 *    ledger). Never assume a bare id is a typo for the prefixed sibling, and
 *    never substitute one for the other. Widen any verify-regex to match
 *    both forms: /^@(project_absence_)?char_/.
 * 2. SUBSTRING SEARCH ON THIS PANEL IS FUZZY/TOKEN-BASED, NOT PURE
 *    SUBSTRING. Searching "visitor_a" returned visitor_a, visitor_b,
 *    visitor_c, AND visitor_c_b -- none of the latter three literally
 *    contain the substring "visitor_a". Always read the FULL result list
 *    (grep innerText for the family root, e.g. "visitor") before clicking,
 *    and use `find()` with the EXACT label text ("visitor_a", not "visitor")
 *    to avoid clicking a sibling.
 * 3. A ONE-IMAGE ELEMENT'S HOVER-ICON PATH FIRES FAR MORE OFTEN THAN A
 *    4-IMAGE (TURNAROUND) ELEMENT'S. Every single-image Element opened this
 *    run (grandmother, guard_valder_six, critic_b, guard_private,
 *    char_registrar, oldman, student_c) landed in the hover-icon overlay
 *    (copy/download/more icons over the thumbnail) on the FIRST click
 *    instead of opening the detail dialog -- a second click on the card body
 *    (avoiding the icon zone, roughly the card's lower-left quadrant) then
 *    opened the dialog correctly. Budget for 2 clicks per single-image
 *    Element as the norm, not the exception.
 * 4. A CARD'S GRID THUMBNAIL CAN RENDER FULLY BLANK WHILE THE ELEMENT IS
 *    FINE. `project_absence_char_student_c`'s thumbnail was blank/empty in
 *    the grid view (confirmed via screenshot) but opened correctly with full
 *    correct content in the detail dialog. Don't conclude an Element is
 *    broken/missing from a blank grid thumbnail alone -- open the dialog
 *    before reporting a mismatch or gap.
 * 5. NAME FIELD IS A STRONG DISAMBIGUATION SIGNAL FOR AMBIGUOUS SEARCHES.
 *    When told to find "a guard belonging to the gentleman, not Valder", the
 *    Name field settled it in one read: `guard_private`'s Name is literally
 *    "Private Bodyguard", while `guard_valder_single`'s Name is "Guard
 *    Redressed Single" -- matching the exact naming pattern of the confirmed
 *    Valder-lineup Elements ("Guards Redressed Six" = guard_valder_six).
 *    When an Element's purpose is ambiguous from its id alone, read Name
 *    before opening the image.
 * 6. THE KNOWN-BAD `guard_private` ELEMENT DOWNLOADED FINE. Its problem
 *    (trips Higgsfield's protected-content scanner, blocks Generate) is
 *    specific to BINDING it as a reference on a Generate call, not to
 *    viewing/downloading its image. Read-only retrieval is safe; this
 *    script never touches Generate.
 *
 * THE LOOP USED THIS RUN (per Element):
 *   1. navigate() full reload of the ?elements=1 URL.
 *   2. wait ~3s, click "Characters" tab at ~(568,103) (re-click every time,
 *      see finding above about it reverting).
 *   3. Set the search input via native setter to the target id fragment.
 *   4. Read full innerText filtered to the family root (not just the exact
 *      target) to see every sibling that matched -- ambiguous fuzzy search,
 *      see finding #2.
 *   5. find() the card by its EXACT label text.
 *   6. Click it. If NO_DIALOG after the click, click the card body again
 *      (avoiding the top-right icon cluster) -- this is the hover-icon path,
 *      see finding #3.
 *   7. Verify the dialog's own Element ID leaf against
 *      /^@(project_absence_)?char_/ before ever clicking Download.
 *   8. Click Download at (1017, 743) (dialog layout was consistent across
 *      1- and 4-image Elements this run).
 *   9. Off-page: `ls -t ~/Downloads | head -1`, confirm the filename matches
 *      the target id exactly, then `sips -s format png` it straight into
 *      the destination folder under that same exact id as the filename.
 */

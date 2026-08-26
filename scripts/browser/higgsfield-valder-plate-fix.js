/**
 * scripts/browser/higgsfield-valder-plate-fix.js
 *
 * Replay notes for diagnosing whether a Higgsfield Element's bound asset is
 * broken/empty vs a real completed image — task-269786bb (2026-08-26), The
 * Valder Collection No.7 (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Thin diagnostic-only addendum to
 * higgsfield-image-gen.js / higgsfield-valder-neighbor-plates.js (read those
 * first for the paste/desync/generate recipe -- this file only covers the
 * "is this Element's asset actually broken" check, which is a Step 1 gate
 * that should run BEFORE any of that paid-generation machinery).
 *
 * Context: project_valder_loc_neighbor_door (Element UUID
 * 1ef9d8b2-d4c3-4267-9aa7-0cca3482e317, asset 50cc126d-499d-4b02-b3c4-cd9f0a6e62d5)
 * fails to bind when @-tagged in a video prompt, confirmed 4/4 in a prior
 * task (task-b7224c38). Suspected cause: its Generate click fired moments
 * before an account-wide logout, so the theory was the asset never finished
 * writing. This run's result: FALSE. The asset is real and complete -- see
 * docs/reports/valder-plate-fix-door.md for the full diagnosis. Recording
 * the check method here since "is this asset actually broken" is a reusable
 * question for any future blocked-Element investigation on this project.
 *
 * DIAGNOSIS RECIPE (zero cost, all read-only):
 *
 * 1. Navigate to the project top-level page (not a specific folder), click
 *    the left-sidebar "Elements" tool (under "Tools", NOT the top-nav "Edit
 *    > Layers" link -- that one led to `?elements=1` too but the direct
 *    sidebar icon is more reliable / one fewer redirect hop). URL should end
 *    up `.../ai-film-festival-3?elements=1`.
 *
 * 2. Rule out a duplicate/orphaned element from an interrupted regen FIRST,
 *    before trusting any single card you find by eye. Click the "All" tab
 *    (not "Locations"/"Characters"/"Props" -- a miscategorised duplicate,
 *    per higgsfield-valder-neighbor-plates.js finding #5, would hide in the
 *    wrong tab) and use the panel's own Search box (top-right, placeholder
 *    "Search") with the element's bare name fragment, e.g.:
 *      "neighbor_door"
 *    Exactly one result confirms there's no second/broken copy. This search
 *    box only filters the currently-loaded grid client-side -- cheap, no
 *    network request.
 *
 * 3. Check the thumbnail is a REAL image via JS, not by eyeballing a small
 *    grid thumbnail (which can look "fine" even scaled down from a broken
 *    source, or vice versa look suspicious at grid scale when it's actually
 *    fine):
 *      const spans = [...document.querySelectorAll('span.truncate')]
 *        .filter(s => s.textContent === 'project_valder_loc_neighbor_door');
 *      let card = spans[0];
 *      for (let i=0;i<8 && card;i++) {
 *        if (card.querySelector && card.querySelector('img')) break;
 *        card = card.parentElement;
 *      }
 *      const img = card.querySelector('img');
 *      ({ imgComplete: img.complete, imgNaturalWidth: img.naturalWidth,
 *         titles: [...card.querySelectorAll('[title]')].map(e => e.title) });
 *    `naturalWidth > 0` + `complete === true` = the browser actually decoded
 *    real pixel data, not a 0-byte/404 image. A non-empty `titles` array
 *    matching a safety-flag string (see higgsfield-valder-neighbor-plates.js
 *    finding, wave 5 of higgsfield-image-gen.js: exact string "Content was
 *    flagged by the safety system...") means flagged, not broken -- a THIRD
 *    distinct state from both "real" and "broken/empty".
 *    NOTE: do not try to read the full `img.src` / outerHTML of the card via
 *    javascript_tool -- Higgsfield's asset URLs are signed with the actual
 *    path/id in the query string, and this harness's own safety filter
 *    blocks returning that ("[BLOCKED: Cookie/query string data]"). Query
 *    `naturalWidth`/`complete`/`title` attributes directly instead of
 *    dumping the URL or HTML -- that's both cheaper and avoids the block.
 *
 * 4. Open the element's detail card (click the thumbnail near its visual
 *    center, not its top-left corner -- corner clicks can hit a hidden
 *    selection checkbox instead, per higgsfield-image-gen.js Wave 3) for a
 *    final human-eye confirmation at full size. Read the "Info" tab's
 *    Category/Name/Created/Last changes/Used-in fields while there -- a
 *    Category that doesn't match the Element's actual kind (e.g. a Location
 *    auto-categorised as "Prop") is itself a known, separate failure mode,
 *    not the one this recipe is checking for, but cheap to eyeball at the
 *    same time.
 *
 * 5. Close the detail dialog via its **X button** (top-right of the dialog),
 *    never Escape -- Escape closing an avatar/account menu has previously
 *    destroyed the entire MCP tab group on this exact project
 *    (higgsfield-image-gen.js Wave 4 finding). Same caution applies here:
 *    closed the account-credits menu with a plain click elsewhere on the
 *    page, not Escape, when reading the balance in step 6.
 *
 * 6. Credit balance (read-only, to confirm zero spend when the diagnosis
 *    resolves to "don't regenerate"): click the avatar icon (top-right),
 *    then:
 *      document.body.innerText.match(/([\d,]+)\s*(left|credits)/i)[0]
 *    Close the menu with a plain click on empty page background, not
 *    Escape.
 *
 * RESULT THIS RUN: real/complete image, Category correct, no flag, exactly
 * one element matching the name -- so per the task's own STOP rule, no
 * generation was attempted and this recipe was the entire task. If a future
 * run of this same check instead finds `naturalWidth === 0` / `complete ===
 * false` / a 404'd `<img>`, that's the actual "go to Step 2, regenerate"
 * signal -- use higgsfield-image-gen.js's paste/desync/Generate recipe from
 * there, and higgsfield-valder-neighbor-plates.js's re-point flow after.
 *
 * SHARED-ACCOUNT NOTE: this project's Chrome profile is being driven
 * concurrently by another operator task firing Seedance videos. The "All
 * assets" counter incrementing (e.g. 249 -> 250) between reads with zero
 * Generate/Upload/Import clicked on this tab is that other task's activity,
 * not a bug in this recipe -- don't chase it.
 */

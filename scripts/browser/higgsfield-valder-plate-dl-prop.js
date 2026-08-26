/**
 * scripts/browser/higgsfield-valder-plate-dl-prop.js
 *
 * Replay notes for downloading every project_valder_prop_* and
 * project_valder_sb* Element's plate image to local disk, task-b1a580ed
 * (2026-08-26), Valder Collection No.7 -> Elements panel
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3?elements=1).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP, same convention as the other higgsfield-valder-*.js
 * files in this directory. This one is retrieval-only: no Generate, no
 * Rerun, no Recreate, zero credits by design.
 *
 * Result: 15/15 target Elements found and downloaded, 0 credits spent by
 * this task (ambient -2 credit drift attributed to other concurrent
 * operators sharing the same account this wave). Full manifest:
 * docs/reports/valder-plate-download-prop.md.
 *
 * THE ROUTE THAT WORKS (do this, not the folder-grid History feed):
 *
 * 1. Navigate to the project root with `?elements=1` appended -- this opens
 *    the account-wide Elements panel (tabs: All / Characters / Locations /
 *    Props, right sidebar: Active / Drafts status + Folders), NOT the
 *    per-scene generation folders. The folder-scoped view under-reports
 *    what exists (documented in higgsfield-unlimited-gen skill); this
 *    panel is the complete, authoritative list.
 * 2. Click the "Props" category tab. For a project this size (~14 prop
 *    items) the ENTIRE category fits in the accessibility tree without any
 *    scroll -- a single DOM text scan (see snippet below) enumerates every
 *    card in one shot.
 * 3. Click a card's thumbnail directly (by pixel coordinate on a screenshot
 *    you just took, NOT a cached `find()` ref from an earlier call) to open
 *    its detail panel/dialog ("Element showcase").
 * 4. In THE SAME turn, read the panel's own `ELEMENT ID` field (and "Name"
 *    field) to confirm which Element actually opened.
 * 5. Only then click that panel's own **Download** button (bottom-left of
 *    the action row, fixed position ~[1078, 708] at a 1024x591 viewport
 *    whenever the panel is open). This is what makes the mislabelling bug
 *    impossible to trigger: name-read and image-fetch happen in one
 *    uninterrupted step against the one open panel, never a name from a
 *    list paired with an image from a later click.
 * 6. Read `~/Downloads` (`ls -lat ~/Downloads | head -3`) to confirm the
 *    file landed. **Higgsfield's own Download action names the file after
 *    the Element ID** (e.g. `project_valder_prop_frame.webp`) -- this is a
 *    free, built-in verification signal: if the downloaded filename doesn't
 *    match the Element ID you just confirmed in the panel, something is
 *    very wrong and you should NOT copy it into the deliverable path.
 * 7. `cp` the file from `~/Downloads/<name>.webp` into the project's
 *    deliverable folder (this task: `docs/plates-props/`), keeping the
 *    exact Element ID as the filename and the original extension/format
 *    (webp stayed webp -- never re-encode, never downscale).
 *
 * ENUMERATE BOTH DIRECTIONS BEFORE DOWNLOADING ANYTHING:
 *
 *   const nodes = [...document.querySelectorAll('*')]
 *     .filter(el => el.children.length === 0 && /^@project_valder/.test((el.textContent||'').trim()));
 *   [...new Set(nodes.map(n => n.textContent.trim()))];
 *
 * Run this once on the "All" category tab (not "Props") to get every
 * card's category prefix in the same pass:
 *
 *   const nodes = [...document.querySelectorAll('*')]
 *     .filter(el => el.children.length === 0 && /^(Prop|Character|Location) • /.test(el.textContent||''));
 *   [...new Set(nodes.map(n => n.textContent.trim()))];
 *
 * This is how the run caught `project_valder_loc_house_new` sitting inside
 * the Props category tab's card grid -- the All-tab scan showed its true
 * category prefix as `Prop • House New`, i.e. Higgsfield itself has a
 * `loc_`-prefixed Element mis-tagged into Prop. Trust the ID prefix over
 * the category tab it happens to render under.
 *
 * CHECK BOTH "Active" AND "Drafts" STATUS (right sidebar). This run found
 * the two statuses returned an IDENTICAL card set for the Props category --
 * no prop-family Element existed only in Drafts -- but the brief explicitly
 * asks for both to be checked, so do the click and the scan every time
 * rather than assuming Active-only is sufficient.
 *
 * NEW FINDINGS THIS RUN:
 *
 * 1. **The category tab (All/Characters/Locations/Props) flips on its own
 *    after almost every panel close.** Confirmed repeatedly, not a one-off:
 *    clicking a card's X (close), then clicking the "Props" tab again,
 *    then reading `document.querySelector('nav[aria-label="Breadcrumb"]').textContent`
 *    would sometimes read "All" or "Locations" instead of "All/Props" even
 *    though the click landed on the correct tab element (confirmed via a
 *    fresh `find()` each time, not a stale ref). This matches the task
 *    brief's warning about "this panel's documented virtualization bug"
 *    re-ordering the list underneath you -- extend that to mean the
 *    category filter itself is not sticky either. **Fix: after every
 *    single tab click, immediately verify with
 *    `document.querySelector('nav[aria-label="Breadcrumb"]')?.textContent`
 *    (~15 tokens) before doing anything else** -- this is far cheaper than
 *    a screenshot and catches the flip before it costs a wasted click on
 *    the wrong grid.
 *
 * 2. **A `find()` ref taken in one tool call and clicked in a LATER call is
 *    unsafe on this panel**, even a few seconds apart with no visible
 *    action in between. Two concrete failures this run: (a) `find()`
 *    located `project_valder_prop_market_bag`, but by the time the click
 *    landed (after the panel had briefly re-rendered), it opened
 *    `project_valder_prop_shopping_bags` instead -- caught by the panel's
 *    own `ELEMENT ID` field before any Download click, not downloaded;
 *    (b) a plain pixel-coordinate click aimed at a "radio" thumbnail
 *    landed on `project_valder_char_neighbor` (a Character/Guards group
 *    shot) after the tab had flipped underneath between screenshot and
 *    click. **Always re-verify the open panel's `ELEMENT ID` before
 *    clicking Download, no matter how confident the click felt.**
 *
 * 3. **Coordinate-based clicks on a screenshot taken in the SAME tool call
 *    batch as the click are far more reliable than `find()`+click across
 *    two calls or a cached ref.** The working pattern that had a 100% hit
 *    rate once adopted: screenshot -> read the visible thumbnails' labels
 *    directly off the image -> click the exact pixel in the very next
 *    action -> screenshot the resulting panel to confirm identity. Treat
 *    `find()` as a location-discovery tool only, then re-screenshot and
 *    click by coordinate, not by trusting the returned ref past that turn.
 *
 * 4. **Programmatic `grid.scrollTop = N` breaks the virtualized grid** on
 *    this project too (reconfirms the finding in
 *    higgsfield-valder-character-images.js Wave 1) -- one scrollTop
 *    assignment caused the category tab to silently jump from "Props" to
 *    "Characters". Real `computer` wheel-scroll (`scroll` action) never
 *    triggered this; it only sometimes needed a second scroll call to
 *    actually move (the first tick sometimes lands as a no-op if the
 *    dialog-close animation is still settling).
 *
 * 5. **A Download click's resulting file can take longer than ~2s to land
 *    in `~/Downloads`** on a handful of occasions (the `wipe` and
 *    `magazine` plates both needed a second look/re-click before the file
 *    showed up) -- when a `ls -lat ~/Downloads` check comes back empty
 *    right after a Download click, re-find the Download button fresh via
 *    `find()` and click again rather than assuming the click failed; both
 *    times this run the ORIGINAL click had actually succeeded and the
 *    "second" click just produced a harmless `(N)`-suffixed duplicate.
 *    Always `cp` the un-suffixed filename when both exist.
 *
 * 6. **The Elements panel's Download button never prompted a save dialog
 *    or opened a new tab** -- it silently saves straight to `~/Downloads`
 *    at full original resolution (confirmed: a 1024x647 project preview
 *    thumbnail vs. a 2336x1744 actual downloaded plate -- the panel view is
 *    NOT the resolution you get). Never substitute a screenshot of the
 *    in-panel preview for the real downloaded file.
 *
 * 7. Credits: **Download is confirmed free.** Balance moved by exactly -2
 *    credits over a ~15-minute, 15-download session with zero Generate/
 *    Rerun/Recreate clicks -- attributed to the other operators sharing
 *    this account concurrently (task brief named three other operators in
 *    the same Chrome, one doing paid video generation). If a download-only
 *    task shows a LARGER credit delta than a couple of stray credits,
 *    stop and check Usage History before assuming Download itself is safe
 *    -- this run's evidence supports "safe" but was not exhaustive proof
 *    against every possible interaction.
 */

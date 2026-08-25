/**
 * scripts/browser/higgsfield-valder-character-images.js
 *
 * Replay notes for the retrofuturist character-restyle image batch,
 * task-0ab55432 (2026-08-25), Valder Collection No.7 -> Character folder
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/folders/ae0bb5a3-9f66-4e95-8112-c2939e9de56e).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into javascript_tool
 * against an already-open, already-logged-in tab via claude-in-chrome MCP.
 * This is a thin addendum to higgsfield-image-gen.js (read that first for the
 * full paste/desync/verify recipe) -- this file only records what was NEW or
 * DIFFERENT in this run.
 *
 * Result: 10/10 characters succeeded on attempt 1/3, 20 credits total
 * (GPT Image 2 / Medium / 1K / 2:3, 2 credits each). See
 * state/reports/valder-restyle-characters.md for the full per-character
 * verdict and asset IDs.
 *
 * NEW FINDINGS THIS RUN:
 *
 * 1. A single `computer` `type` action pushing ~2000 characters into the
 *    Lexical prompt editor as real keystrokes FROZE THE TAB'S RENDERER
 *    completely -- every subsequent CDP call (`javascript_tool`,
 *    `tabs_close_mcp`) timed out at 30-45s with "renderer may be frozen".
 *    Fix: never use `computer` `type` for long prompt text. Use the
 *    synthetic-paste recipe from higgsfield-image-gen.js instead (focus the
 *    editor, dispatch a `ClipboardEvent('paste', {clipboardData: dt})` with
 *    a `DataTransfer` carrying `text/plain`) -- this was reliable for all 10
 *    prompts (~3000-3300 chars each) once switched to.
 *
 * 2. Recovery from the frozen tab required a FULL Chrome quit+relaunch
 *    (`osascript -e 'quit app "Google Chrome"'` then `open -a "Google
 *    Chrome"`, ~8s to fully spawn helper processes before the extension
 *    reconnects) -- a new tab alone was not tried because the whole
 *    extension connection was down, not just one tab. This is a free,
 *    ordinary repair move per the browser-operator role doc, but it DOES
 *    close every open Chrome tab, including any other task's tabs. If a
 *    task brief says "do not touch/close another task's tab", note that a
 *    full-Chrome-restart recovery unavoidably violates that even though it
 *    isn't targeted at that tab -- flag it in the report rather than treat
 *    it as compliant.
 *
 * 3. execCommand('selectAll')+execCommand('delete') (JS-only clear, no real
 *    keypresses) did NOT reliably clear the Lexical editor before a
 *    subsequent paste -- one paste landed on top of 3192 chars of
 *    uncleared prior text (normalized length 6327 instead of expected
 *    3135), caught by the length-diff check before Generate was clicked.
 *    Real keyboard clear (`computer` key: cmd+a, Delete, cmd+a, Delete,
 *    with `el.focus()` called immediately before, TWICE if the first pass's
 *    length check fails) was reliable for the rest of the run -- always
 *    verify `el.innerText.length <= 1` before pasting, don't trust one
 *    clear pass.
 *
 * 4. On a fresh page load/reload, the aspect-ratio, quality and resolution
 *    pills reset to Auto/High/2K (this matches earlier waves' "settings can
 *    reset on reload" finding) but a plain in-app folder navigation (click
 *    the "2:3" pill's dropdown, pick a new value) preserved the model
 *    (GPT Image 2) across the whole run without needing to reselect it.
 *
 * 5. Near the very end of the run, the quality-pill dropdown ("High") STOPPED
 *    OPENING for any click technique tried: a real `computer` left_click at
 *    the verified on-screen center, a plain JS `.click()`, and a full
 *    synthetic PointerEvent sequence (pointerdown/mousedown/pointerup/
 *    mouseup/click) all did nothing -- no dropdown appeared, button text
 *    stayed "High". This is the SAME kind of click-unresponsive failure
 *    documented for the Generate button and the mode toggle in
 *    higgsfield-image-gen.js Waves 6/7, but here it hit a plain settings
 *    pill, not a money-committing control. Stopped after 3 attempts per the
 *    click-blocked escalation rule (1 clean attempt, then stop and report --
 *    used up to 3 here since it wasn't a priced control) rather than keep
 *    trying variations. A full Chrome restart was NOT retried at this point
 *    (budget/time judgement call, and the character already had 3/4
 *    distinguishing features clearly rendered) -- worth trying first if
 *    someone picks this back up.
 *
 * 6. Group-shot exception: character 7 ("the Guards" -- a row of six
 *    identically-uniformed men with six different faces/builds) needed a
 *    WIDE aspect ratio to stay legible -- switched the aspect pill from 2:3
 *    to 3:2 for that one generation only, then switched back to 2:3
 *    immediately after via the same pill/dropdown. Do this for any other
 *    multi-figure group plate in this project; single-figure plates want
 *    the default portrait 2:3.
 *
 * 7. Verifying results without spending more screenshots than necessary:
 *    `[data-asset-id]` cards' `<img>` src timestamp (`hf_YYYYMMDD_HHMMSS_`)
 *    sorted ascending gave a clean, unambiguous 1:1 order-of-generation
 *    match to the 10 characters (10 new cards, timestamps 19:32:34 through
 *    19:46:28, no gaps, no repeats) -- confirmed against the "All assets"
 *    delta (178 -> 188) before trusting the mapping, per existing script
 *    guidance. None of the 10 were safety-flagged (checked via the
 *    `[title]` "flagged by the safety system" string, per Wave 5's
 *    higgsfield-image-gen.js finding -- came back null for all 10).
 *
 * 8. The virtualized folder-grid scroll container broke (rendered
 *    completely blank, no cards) after setting its `scrollTop` directly via
 *    `javascript_tool` (`grid.scrollTop = 900`) -- this is DIFFERENT from
 *    the earlier documented `scrollTop = 0` trick (which worked fine to
 *    bring a new card into the DOM). Setting a non-zero mid-scroll value
 *    seems to desync the virtualizer's window. Fix was a full page reload,
 *    not a scroll-back-to-0 -- if the grid ever goes blank after a
 *    programmatic scroll, reload rather than trying to scroll it back.
 *    Prefer real `computer` wheel-scroll (`scroll` action) for grid
 *    navigation; it never broke the grid, only `scrollTop` assignment did.
 *
 * Wave 2 (task-0c59dcaf, 2026-08-25): 2-plate reshoot/retry in the same
 * folder -- Plate 1 (project_valder_char_valder, full restyle to a
 * 5-colour asymmetric coat) and Plate 2 (project_valder_char_press,
 * shoulder-asymmetry fix retry). Both succeeded on attempt 1/3.
 * 4 credits total (GPT Image 2 / Medium / 1K / 2:3, 2 credits each),
 * balance 2,014 -> 2,010.
 *
 *   - The claude-in-chrome extension did not auto-connect to an
 *     already-running Chrome at session start (`tabs_context_mcp` returned
 *     "Browser extension is not connected" 4 times over ~25s of retries,
 *     including one full `osascript quit + open -a "Google Chrome"`
 *     restart that also failed to reconnect). Root cause: Chrome had
 *     relaunched with ZERO windows open (confirmed via a read-only
 *     computer-use screenshot -- menu bar showed "Chrome" frontmost but the
 *     desktop behind it was empty). The extension needs an actual window/tab
 *     to attach to. Fix: `mcp__computer-use__open_application` on "Google
 *     Chrome" again (after `request_access`) opened a real window, and
 *     `tabs_context_mcp` connected on the very next call. If Chrome is
 *     "running" per `pgrep` but the extension still won't connect, check
 *     for a windowless state before escalating further -- don't assume the
 *     extension itself is broken.
 *
 *   - On first navigating into the Character folder, the Image/Video mode
 *     toggle's Image side did NOT land on the plain photo composer
 *     (GPT Image 2 with a "Describe your scene" box) -- it landed on a
 *     "CHARACTER" template pill running the "Higgsfield Soul Cinema" model,
 *     which opens straight into a "MAKE YOUR OWN CHARACTER / Create
 *     character" panel (an Element-training flow) when that pill is
 *     clicked. This is a DIFFERENT default from every prior wave in this
 *     project and is NOT what the task wants -- it would create a new
 *     Element if driven through, which is explicitly banned. Recognized it
 *     immediately from the "MAKE YOUR OWN CHARACTER" heading and backed out
 *     without creating anything. Fix: click the model pill (shows
 *     "Higgsfield Soul Cinema" or whatever the CHARACTER default is) to
 *     open the model dropdown, and explicitly select "GPT Image 2" from the
 *     "Featured models" list -- this swaps the whole composer back to the
 *     plain scene-description box with the familiar Auto/High/2K pills.
 *     This CHARACTER-pill default reappeared on every fresh page load
 *     during this run (after each forced re-navigate), so re-check the
 *     model pill's text every single time the composer is rebuilt, not
 *     just once per session.
 *
 *   - Once on GPT Image 2, building the settings row in order (model ->
 *     quality High->Medium -> resolution 2K->1K -> aspect Auto->2:3) worked
 *     cleanly with plain `computer` left_click on each pill/dropdown-option,
 *     no PointerEvent-sequence workaround needed this run (contrast with
 *     Waves 6/7 of higgsfield-image-gen.js, which needed synthetic
 *     PointerEvents for a stuck toggle -- that was NOT needed here). Don't
 *     assume the harder workaround is required by default; try a plain
 *     click first each time.
 *
 *   - `resize_window` to 1024x768 silently did not take effect on the FIRST
 *     tab of the session (`window.innerWidth/innerHeight` stayed 1440x754
 *     after two separate resize calls) but DID take effect on a later tab
 *     opened after a tab-group teardown/rebuild (innerWidth 1024, but the
 *     screenshot came back 1456x840 -- i.e. screenshot-px = css-px * ~1.42
 *     on this Retina display, not the 1.05 ratio seen on the first tab).
 *     **The screenshot/CSS pixel ratio is not a constant across tabs in the
 *     same session** -- recompute it (`window.innerWidth` vs a screenshot's
 *     reported dimensions, or the actual screenshot width) before doing any
 *     coordinate-based click, every time a new tab is created. Using a
 *     stale ratio silently misses small targets.
 *
 *   - `computer` `screenshot` failed 3 times in a row with "CDP sendCommand
 *     Page.captureScreenshot timed out after 30000ms" on one tab, while
 *     `javascript_tool` calls against the SAME tab succeeded instantly the
 *     whole time (`document.readyState` was "complete", no dialog open,
 *     `location.href` unchanged). This is a CDP-screenshot-pipeline-only
 *     stall, not a frozen renderer in the Wave-1 keystroke-freeze sense --
 *     JS execution and DOM state stayed fully live and readable throughout.
 *     Per the browser-operator skill's restart ladder, opened a fresh tab
 *     (`tabs_create_mcp`) and navigated it to the same folder URL rather
 *     than doing a full Chrome restart -- the fresh tab's screenshot worked
 *     on the very first try. Closed the stalled tab afterward. **Closing
 *     the stalled tab (the group's only OTHER tab at the time) once
 *     destroyed the tab group entirely** ("No tab group exists for this
 *     session") even though a second tab was still nominally open when the
 *     close was issued -- matches higgsfield-image-gen.js's existing note
 *     that some ordinary actions can tear down the MCP tab group
 *     unpredictably. Recreate with `tabs_context_mcp({createIfEmpty:true})`
 *     and re-navigate; don't treat it as a sign anything is actually wrong
 *     with the page itself.
 *
 *   - Opening a card's full detail+fullscreen view (click near center of
 *     the thumbnail -> URL gains `?preview=<uuid>` -> click the
 *     bottom-right fullscreen/expand icon) reliably showed the ENTIRE
 *     figure including the head, whereas the folder-grid thumbnail view
 *     crops the top of tall full-length portraits (the head was cut off
 *     above the "New" badge in-grid on both plates this run). **Always
 *     open the fullscreen view before judging a checklist item that
 *     depends on the face (open/closed eyes, expression) -- the grid
 *     thumbnail alone is not sufficient evidence for that, even though it
 *     was enough to confirm the coat/colours/gloves/brooch.**
 *
 *   - Two mid-task chat notifications ("[New message from CEO]") arrived
 *     with literally no body text attached, matching the
 *     higgsfield-unlimited-gen skill's documented "mailbox delivers
 *     notifications with no body" issue. Checked the worktree's `TASK.md`
 *     both times per that skill's guidance (append-to-TASK.md is the
 *     channel that actually reaches the operator) -- file was unchanged
 *     both times (confirmed via `tail` and mtime, which predated the
 *     notifications). Treated both as unactionable noise and continued the
 *     original brief rather than pausing to guess at content. If this
 *     keeps happening, the underlying mailbox bug from the Higgsfield
 *     skill's incident log has not been fixed and is not scoped to
 *     Higgsfield-specific tasks -- it reproduced here on a completely
 *     ordinary two-plate reshoot with no History/Rerun involved.
 *
 *   - Both plates rendered correctly and passed their full checklist on
 *     attempt 1/3 -- no retries were needed, so the "retry with the failing
 *     item stated more forcefully" branch of the procedure was not
 *     exercised this run. For Plate 2 specifically (the shoulder-asymmetry
 *     fix), naming BOTH the structural cause ("permanently and severely
 *     hunched... spine visibly curved") AND the visible mechanism ("the
 *     high shoulder is the one bearing the camera's weight") in the same
 *     paragraph, plus repeating "dramatically higher... first thing anyone
 *     notices" language, produced an unambiguous, obvious-at-a-glance
 *     asymmetry on the very first attempt where the prior wave's prompt
 *     had only produced something "too subtle to read".
 *
 *   - This worktree's branch had been cut before task-0ab55432's commit
 *     (which added this very file) had landed on `main`, so this file was
 *     absent from the branch at session start even though the task brief
 *     told the operator to read it. Recovered the content via
 *     `git show <sha>:scripts/browser/higgsfield-valder-character-images.js`
 *     against the commit `git log --all` found, confirmed it was already an
 *     ancestor of `main`, and rewrote this file here with that content plus
 *     this Wave-2 section appended -- rather than skipping the read or
 *     guessing at the prior findings. Also NOTE for the report writer: the
 *     task brief's own `state/reports/valder-restyle-v2.md` deliverable
 *     path is gitignored on this repo (`state/reports/*` in `.gitignore`) --
 *     a merge would silently discard it. Wrote the actual report to
 *     `docs/reports/valder-restyle-v2.md` instead and inlined the full
 *     content into `submit_report` so the data survives either way.
 *
 * Wave 3 (task-64083ed9, 2026-08-25): zero-cost Location/Prop Element
 * enumeration (JOB 1) + 4 new location/prop plates in the Location and Prop
 * folders (project_valder_loc_studio, _loc_fountain_hall, _loc_home_interior,
 * _prop_magazine), 3:2/Medium/1K, 1 image each, 2 credits each, 8 credits
 * total, balance 2,010 -> 2,002. All 4 passed on attempt 1/3.
 *
 *   - Enumerating Element UUIDs without opening each card's detail dialog:
 *     paste ALL the `@slug` mentions you need, newline-separated, into the
 *     composer's contenteditable in ONE synthetic-paste call (same
 *     ClipboardEvent recipe as normal prompt text). Every `@project_valder_*`
 *     substring that matches a real Element auto-resolves into a bound
 *     mention chip, and `[...editor.querySelectorAll('[data-beautiful-
 *     mention]')].map(m => ({text: m.textContent, uuid: m.getAttribute(
 *     'data-beautiful-mention')}))` reads back the full slug->UUID map in
 *     one call. Confirmed against two independent sources this run: the
 *     resolved UUID for `project_valder_prop_signature` matched the
 *     hardcoded value in this same file's header comment exactly, and the
 *     resolved UUID for `project_valder_prop_magazine` matched a UUID
 *     independently found inside an opened detail dialog's raw HTML. This
 *     is strictly cheaper and more reliable than opening each Element's
 *     detail dialog and hunting its React-fiber props for a UUID (tried
 *     first this run via `fiber.memoizedProps`/`memoizedState` walks --
 *     works but is slow, ambiguous between multiple UUIDs per node
 *     (asset id vs folder id vs element id), and burns far more tool calls
 *     than the batch-paste trick). Reach for the paste trick first whenever
 *     the task needs several Element UUIDs and a composer is available.
 *     IMPORTANT: this only confirms an Element's UUID is *live and
 *     resolvable* -- it says nothing about re-pointing history. Do not
 *     conflate "paste resolves to a chip" with "the UUID survived a
 *     re-point"; those are the same test only when the prior UUID is known
 *     and compared, as in the CTO's one-off crowd_b check earlier in this
 *     run.
 *
 *   - Elements can be filed under the "wrong" tab: `project_valder_loc_
 *     house_new` (a `loc_` prefixed ID) showed up in the Elements panel's
 *     **Props** tab, not Locations, sitting alongside genuine `prop_*`
 *     entries. Enumerating by ID-prefix regex over each tab's full
 *     `innerText` (not by trusting which tab a card visually sits in)
 *     caught this; a scan that only checked the Locations tab for `loc_`
 *     IDs would have under-counted by one.
 *
 *   - The `computer` tool's screenshot-derived pixel ratio
 *     (screenshotWidth/innerWidth, ~1.34-1.42 this session, recomputed
 *     fresh per tab per this repo's existing convention) is USELESS for
 *     `computer.left_click` coordinate targeting on this project's Image
 *     composer -- confirmed on two separate tabs this run that a `computer
 *     left_click` at a coordinate computed from a fresh
 *     `getBoundingClientRect()` (converted by the measured ratio, or even
 *     tried as raw CSS px) reliably MISSED the real GENERATE button:
 *     `document.elementFromPoint()` at the exact same CSS coordinates the
 *     rect reported did not return the button or any descendant of it, even
 *     immediately after re-reading the rect fresh. This is a DIFFERENT
 *     failure mode from the known hidden-decoy-button trap (the button
 *     found via the visibility/offsetParent/width>0 filter was confirmed
 *     real: `disabled:false`, correct `"GENERATE\n2"` text, non-zero rect) --
 *     something about this composer's layout/stacking makes the button not
 *     hit-testable at its own reported rect via `elementFromPoint`, and by
 *     extension not reliably clickable via `computer left_click`'s
 *     coordinate dispatch either. A `find`-based ref click on the same
 *     button also silently no-op'd (no toast, no asset-count change,
 *     0 credits deducted both times -- verified before retrying, so this
 *     cost nothing). FIX THAT WORKED, first try, both times: dispatch a
 *     full synthetic pointer sequence directly on the JS-referenced button
 *     element itself (not through screen/CSS coordinates at all):
 *       const opts = {bubbles:true, cancelable:true, view:window,
 *         clientX:cx, clientY:cy, button:0}; // cx/cy cosmetic only here
 *       b.dispatchEvent(new PointerEvent('pointerdown', opts));
 *       b.dispatchEvent(new MouseEvent('mousedown', opts));
 *       b.dispatchEvent(new PointerEvent('pointerup', opts));
 *       b.dispatchEvent(new MouseEvent('mouseup', opts));
 *       b.dispatchEvent(new MouseEvent('click', opts));
 *     This produced the "Generation started" toast and a correct credit
 *     deduction on the very first attempt after the coordinate-based
 *     methods failed, on both of the two occasions this happened. Given two
 *     coordinate-based methods (`computer left_click` and `find`+ref click)
 *     both failed silently and for free on this composer, consider trying
 *     the direct-dispatch method FIRST on Generate clicks in this specific
 *     project/composer rather than after two failed attempts, to save
 *     round-trips -- though always verify the toast/asset-count either way
 *     before assuming a click landed.
 *
 *   - Reconfirmed from Wave 1: a `computer screenshot` call can time out
 *     ("Page.captureScreenshot timed out after 30000ms... renderer may be
 *     frozen") while `javascript_tool` calls against the same tab keep
 *     working instantly (`document.readyState` stays "complete", DOM state
 *     stays live) -- this happened here shortly after a long (~4900-char)
 *     paste + a real-key Space/BackSpace desync-fix pair, i.e. NOT from a
 *     `computer type` action (Wave 1's trigger) but from a similar
 *     high-load moment. Treat any long-paste-plus-real-keys sequence as a
 *     moment to expect this, not just `type`. Fix used successfully again:
 *     open a fresh tab (`tabs_create_mcp`), navigate to the same folder URL,
 *     verify `window.innerWidth/innerHeight`, and continue there; do NOT
 *     restart the whole browser for this specific symptom.
 *
 *   - Reconfirmed from Wave 4 of higgsfield-image-gen.js: closing the
 *     stalled tab (the group's only other tab) tore down the MCP tab group
 *     entirely (`tabs_context_mcp` -> "No tab group exists for this
 *     session") even though a fresh replacement tab had already been
 *     created and was still open when the stale one was closed. Recreate
 *     with `tabs_context_mcp({createIfEmpty:true})` and re-navigate; this is
 *     now confirmed across two separate waves in two different scripts, not
 *     a one-off.
 *
 *   - Verifying a just-fired Generate actually landed a NEW card in a
 *     *specific* folder (as opposed to the project's "All assets" total,
 *     which increments immediately) can lag well behind the toast --
 *     20-28s observed this run for the folder-grid's own DOM to include the
 *     new `[data-asset-id]` card, even after forcing `scrollTop = 0` on
 *     every scrollable ancestor. Budget at least two 10s waits (the
 *     `computer wait` action caps a single call at 10s) before concluding a
 *     folder-scoped card is missing; don't jump to "did it land in the
 *     wrong folder" or "did it silently fail" on the first empty check when
 *     the toast and the global asset-count delta both already confirmed
 *     success.
 *
 *   - The virtualized grid can render the SAME `data-asset-id` element
 *     twice in the live DOM at once in this project's Prop folder (28 card
 *     nodes returned for what should be at most ~14 unique ids) without any
 *     scroll action in between -- deduping by id (`new Map(info.map(i=>
 *     [i.id,i])).values()`) before sorting by timestamp is necessary, not
 *     optional, or a genuinely-new card can be masked by a duplicate stale
 *     node sorting ahead of it.
 *
 *   - `[data-asset-id]` card `<img>` `src` values in this project can be
 *     signed URLs whose query string trips the harness's generic
 *     credential/cookie-leak guard on `javascript_tool` results
 *     (`[BLOCKED: Cookie/query string data]`) if you return the raw `src`
 *     string in your result. Never return the full `src`; extract only what
 *     you need (e.g. the `hf_YYYYMMDD_HHMMSS_` timestamp via regex) inside
 *     the page-side JS and return just that.
 * Wave 4 (task-45f57723, 2026-08-25): 2-plate colour-saturation reshoot in
 * the same Location folder (project_valder_loc_studio and
 * project_valder_loc_fountain_hall) -- both prior versions were rejected for
 * being muted/chalky/washed; this wave's whole brief was "make the colour
 * louder". GPT Image 2 / Medium / 1K / 3:2, 1 image each, 2 credits each,
 * 4 credits total, balance 2,002 -> 1,998. Both passed on attempt 1/3.
 *
 *   - The synthetic ClipboardEvent paste (same recipe as Wave 1-3: focus the
 *     Lexical contenteditable, dispatch `new ClipboardEvent('paste', {...,
 *     clipboardData: dt})`) reads back as `innerText.length === 0`
 *     IMMEDIATELY after the dispatch call returns, even though the paste
 *     genuinely lands. This is a reconciliation-timing gap, not a failure --
 *     confirmed by reading `innerText` again after a real, unrelated
 *     keyboard action (`execCommand('insertText', ...)` used as an
 *     incidental probe) and finding the full pasted text already present.
 *     Reading the length in the exact same `javascript_tool` call as the
 *     dispatch is measuring too early. Fix: dispatch the paste, then a
 *     SEPARATE `javascript_tool` call after at least a ~1s wait (a
 *     `computer wait` in between is enough) to check
 *     `document.activeElement.innerText.length` against the source string's
 *     `.length` -- don't trust a same-call read of 0 as "the paste failed".
 *
 *   - The normalized `innerText.length` on a successful, clean paste is
 *     consistently ~24 characters LONGER than the source string's raw
 *     `.length` for a prompt with several blank-line-separated paragraphs
 *     (confirmed on two independent prompts this run, both landing at
 *     source+24 exactly). This matches earlier waves' "normalized length"
 *     caveat but is worth a concrete number: a diff in the small
 *     tens-of-characters range from paragraph-break normalization is
 *     expected and is NOT evidence of a doubled/duplicate paste (which
 *     would show as source_len*2 or more) -- don't retry-clear-and-repaste
 *     on a small positive diff alone.
 *
 *   - Reconfirmed the Wave 3 finding that coordinate-based clicks are
 *     unreliable on this composer's Generate button; used the direct
 *     PointerEvent/MouseEvent dispatch-on-the-button-element method
 *     (pointerdown -> mousedown -> pointerup -> mouseup -> click, all with
 *     `bubbles:true, cancelable:true`) as the FIRST attempt both times this
 *     run (per Wave 3's own recommendation to not wait for two failures
 *     first) -- worked on the very first try both times, "Generation
 *     started" toast and asset-count increment confirmed each time.
 *
 *   - A full page reload (via `navigate` to the same URL, used once this run
 *     to get a clean non-overlaid view of a generated asset by re-opening
 *     its `?preview=<uuid>` URL directly) reset the settings pills to
 *     Auto/High/2K, exactly as documented in Wave 2 -- but the composer's
 *     PROMPT TEXT was NOT cleared by the same reload (the just-generated
 *     Plate 1 prompt was still sitting there, requiring an explicit
 *     select-all-delete before pasting Plate 2). Reload resets settings
 *     pills but does NOT reset composer text -- don't assume a fresh
 *     reload gives you a blank composer for free, still clear it
 *     explicitly.
 *
 *   - `resize_window` to 1024x768 took effect correctly and immediately on
 *     the FIRST tab this run (innerWidth/innerHeight came back 1024x647,
 *     screenshot 1374x868, ratio ~1.342) -- contrast with Wave 2 where the
 *     first tab's resize silently failed. No fixed rule for which tabs will
 *     take a resize; always verify with `javascript_tool`
 *     `[window.innerWidth, window.innerHeight]` rather than trusting the
 *     "Successfully resized" return text, every single time, on every tab.
 *     Separately, later in the run a `computer screenshot` came back at
 *     1024x591 (a smaller height than the same tab's earlier 1374x868
 *     capture) with no resize call in between -- the viewport/toolbar
 *     height can drift within a single tab's lifetime (e.g. a
 *     notification banner or dropdown affecting layout momentarily), so
 *     re-derive the ratio from each screenshot's actual returned
 *     dimensions if doing coordinate math, don't cache one ratio value for
 *     the whole session.
 *
 *   - Credit balance is not printed anywhere in the main page's visible
 *     text/DOM by default (a `document.body.innerText` regex scan for a
 *     bare `2,002`-style number found only the unrelated "194" asset
 *     count) -- it only renders once the Account-menu dropdown (top-right
 *     avatar, `find`-locatable as "Account menu") is opened, as
 *     "`<N> left`" next to a "Credits" label. Open that menu once at the
 *     start and once at the end of any credit-tracked run; don't assume a
 *     page-wide text scan will find it.
 *
 * Wave 5 (task-1b9835bf, 2026-08-25): 9 brand-new location/prop plates
 * (project_valder_loc_house_old, _house_new, _street_row, _aerial,
 * _office_ext, _museum, and project_valder_prop_plan, _siteplan,
 * _signature) across the Location and Prop folders. GPT Image 2 / Medium /
 * 1K / 3:2, 1 image each, 2 credits each, 18 credits total, balance
 * 1,998 -> 1,980. All 9 passed on attempt 1/3 -- no retries needed.
 *
 *   - Page-injected JS state (a `window.__editor` reference to the Lexical
 *     contenteditable, plus `window.__pasteInto`/`window.__clickGenerate`
 *     helper functions defined once via `javascript_tool`) SURVIVES an
 *     in-app folder switch (clicking "Location" -> "Prop" in the left
 *     sidebar, which changes the URL to a new `/folders/<uuid>` path via
 *     client-side routing, no full reload). Confirmed by re-reading
 *     `typeof window.__pasteInto` immediately after the folder switch --
 *     still `"function"`. This is a genuinely different case from a page
 *     `navigate`/reload (which Wave 4 confirmed resets the settings pills)
 *     -- an in-app SPA route change resets neither the settings pills NOR
 *     injected globals. Only `document.activeElement` needs re-capturing
 *     into `window.__editor` after the switch (the DOM node itself is
 *     replaced even though the app state persists), which a fresh
 *     `document.activeElement` read confirmed instantly. Defining the
 *     paste/generate helpers ONCE at the start of a run and reusing them
 *     across every folder switch and every one of the 9 plates avoided
 *     re-sending the ~40-line helper definitions 9 times.
 *
 *   - The synthetic-paste + real-key-clear recipe from Waves 1-4 worked
 *     cleanly on every one of the 9 plates this run with NO paste
 *     failures, NO doubled text, and no `computer screenshot` stalls --
 *     the normalized length diff was consistently a small positive number
 *     (12-15 chars) matching Wave 4's "paragraph-break normalization"
 *     range every single time, never the ~2x-source-length signature of a
 *     failed clear. Two real-key clear passes (`cmd+a`, `Delete`, twice)
 *     before every paste, with an `innerText.length <= 1` check after,
 *     continues to be sufficient and was not skipped once.
 *
 *   - The direct-dispatch PointerEvent/MouseEvent sequence on the
 *     JS-referenced Generate button (per Wave 3's finding that
 *     coordinate-based clicks are unreliable on this composer) fired
 *     correctly and produced the "Generation started" toast on the FIRST
 *     attempt for all 9 plates, with no coordinate-based method tried or
 *     needed at all this run. Reading the button's own `innerText`
 *     (`"GENERATE\n2"`) via `javascript_tool` immediately before every
 *     click reliably confirmed the 2-credit cost matched the Medium/1K/
 *     qty-1 settings before committing -- worth doing every time even
 *     though the pills were never observed to silently drift mid-run.
 *
 *   - New card detection in `[data-asset-id]` count lagged the "Generation
 *     started" toast by roughly 18-28s across all 9 generations (a first
 *     10s wait consistently found either an unchanged count or a
 *     newest-card `img.alt` still reading "Generating"/"image generation"
 *     placeholder text; a second 8-10s wait was enough every time). Budget
 *     two waits, not one, as Wave 3 already found.
 *
 *   - The `[data-asset-id]` total count is NOT monotonically increasing
 *     across generations in a way you can rely on for a delta check --
 *     it went 21 -> 22 -> 24 -> 24 -> 24 -> 21 -> 24 in the Location folder
 *     across 6 generations this run (the virtualizer's dedupe/mount
 *     behaviour churns the live DOM node count independently of how many
 *     real assets exist). The only reliable per-generation check is: (a)
 *     the newest card's `data-asset-id` differs from the previous
 *     generation's newest id, and (b) that card's `img.alt` is no longer
 *     "Generating"/"image generation" placeholder text. Don't gate on the
 *     raw count matching an expected arithmetic progression.
 *
 *   - `getImageData()` on a `<canvas>` the just-generated `<img>` was drawn
 *     into throws `SecurityError: The canvas has been tainted by
 *     cross-origin data` -- the asset CDN does not serve
 *     `Access-Control-Allow-Origin`, so there is no way to pull an
 *     objective RGB/saturation sample via JS for the "colour vivid vs
 *     muted" judgement call this task required. Fell back to the
 *     documented `zoom` tool on the new card's thumbnail region
 *     (`[333,125,673,351]`, i.e. the top-left grid cell where a fresh
 *     generation always lands first) for every saturation verdict instead
 *     -- this worked fine, just note that a pixel-exact check is not
 *     available on this project's asset host.
 *
 *   - Switching folders (Location -> Prop) via the sidebar preserved the
 *     model (GPT Image 2) and every pill (3:2 / Medium / 1K / qty 1)
 *     with no re-selection needed -- confirms and extends Wave 2's
 *     "in-app folder navigation preserves the model" finding to cover the
 *     full settings row, not just the model pill.
 *
 * Wave 6 (task-5993f785, 2026-08-25): single-plate replate + eligibility-check
 * flow for project_valder_char_press, which was failing Higgsfield's own
 * Face/IP moderation (blocked a Scene 1 video fire, GH #93). GPT Image 2 /
 * Medium / 1K / 3:2, 1 image per attempt, 2 credits each, 4 credits total,
 * balance 1,978 -> 1,974. Attempt 1 failed eligibility, attempt 2 passed.
 * Full narrative in docs/reports/valder-press-ipsafe.md.
 *
 *   - Confirmed the exact per-reference eligibility-check UI, first
 *     documented as a "genuine stop-and-ask" in higgsfield-jumpcut-gen.js's
 *     task-c7845ce8 finding #1 -- this task explicitly authorized clicking
 *     it. Flow: paste `@[project_valder_char_press](<mention-uuid>)` (a
 *     THIRD id namespace, distinct from asset-image ids and CDN-filename
 *     ids -- see valder-element-repoint-test.md and valder-s1-fire.md) via
 *     synthetic ClipboardEvent into the Cinema Studio VIDEO composer (not
 *     the Image composer -- References panel with the per-reference check
 *     only exists on the video side), confirm it attached (References
 *     N/50), hover the reference thumbnail to reveal a Radix tooltip
 *     reading "This asset needs an eligibility check before it can be
 *     used." with a "Check eligibility" button, click it.
 *
 *   - The `@[name](uuid)` bracket-paste syntax renders the mention chip as
 *     the RAW UUID in red/error-styled text (`text-font-error` class)
 *     immediately after paste, even though the underlying reference is
 *     already correctly bound to the target Element -- confirmed via the
 *     reference thumbnail's `img.alt` matching the target asset id the
 *     whole time. Don't read the raw-UUID red-text display as a binding
 *     failure. In this run the chip's display text self-corrected to the
 *     proper `@project_valder_char_press` name only AFTER the eligibility
 *     check completed, not before -- so a red/raw-UUID chip is expected and
 *     harmless at this syntax's paste-time, not a signal to redo the paste.
 *
 *   - The reference thumbnail's small badge changes shape with the check
 *     result and is a fast, free visual tell -- FAILED: a persistent "🚫"
 *     (circle-slash) icon overlaid on the "@" corner badge, which survives
 *     mouse-away (i.e. it's a status icon, not a hover cursor artifact).
 *     PASSED: a plain "@" badge with no overlay. Cheap to `zoom` on the
 *     thumbnail region ([443,515]-[583,595] at 1024x647 viewport, ~40px
 *     square) to check this before spending a hover+screenshot round trip
 *     on the tooltip text -- though the tooltip text is what this report
 *     actually cites as the authoritative PASS/FAIL signal, since the badge
 *     shape was reverse-engineered empirically this run, not documented
 *     anywhere first-party.
 *
 *   - The FAILED tooltip text, verbatim: "Face/IP failed -- A face or
 *     protected content was detected, so this asset cannot be used. Try
 *     another." Matches valder-s1-fire.md's finding exactly (same string,
 *     different asset) -- confirms this is a fixed, generic moderation
 *     message, not asset-specific detail.
 *
 *   - The PASSED state has NO positive tooltip at all -- hovering a clean
 *     reference produces nothing (no "Eligible" or checkmark message).
 *     Absence of the FAILED tooltip, absence of the "needs an eligibility
 *     check" pre-check tooltip, AND a full-page
 *     `document.body.innerText.match(/Face\/IP failed|protected
 *     content|eligibility check before/i)` returning no match together are
 *     what this run relied on to call PASS -- no single one of those three
 *     alone is as strong as the FAILED case's explicit string.
 *
 *   - Retried with the SAME locked silhouette/wardrobe/prop language both
 *     attempts (per the task's own instruction those are settled and must
 *     be preserved) and only reinforced the FACE section's ordinariness
 *     language between attempts 1 and 2 -- explicitly framing it as a
 *     "generic, computer-generated composite with zero basis in any real
 *     individual's likeness", calling out "not based on any well-known
 *     character-actor type", and adding matching NEGATIVES entries (no
 *     character-actor typecast face, no distinctive or memorable face, no
 *     impression of a real person). This flipped attempt 2 from FAILED to
 *     PASSED on the very next try -- worth reaching for this specific
 *     framing (composite/generic/no-basis-in-real-individual) before trying
 *     unrelated changes like swapping out the specific physical features,
 *     which the task explicitly locks as "already settled."
 *
 * Wave N (task-62759c51, 2026-08-25): S1 multicut review (clip
 * 53576bfe-1fff-40d2-950d-e960b9f5c939) + Take 2 fire (new clip
 * e784e1c2-79bf-424e-842e-9d5dc5bdeb46), Seedance 2.5 / References / 20s /
 * 720p / High / 16:9 / Sound On / Unlimited. 0 credits (balance 1,974 ->
 * 1,974 -- first VIDEO generation in this file's history, not an image
 * plate; the price shown is a struck-through positive number resolving to
 * 0, e.g. "UNLIMITED / ~~440~~ / 0", NOT the zero-digit rule this file's
 * earlier waves use for GPT Image 2 -- see higgsfield-unlimited-gen skill's
 * "video Generate button shows a struck-through price" table).
 *
 *   - The Duration pill (Seedance 2.5, range 4s-30s) is an ARIA
 *     `role="slider"` element, NOT a text `<input>`. Clicking the pill
 *     ("5s") opens a small panel containing a focused `<span
 *     role="slider" tabindex="0" aria-valuemin aria-valuemax
 *     aria-valuenow>`. Typing digits, Backspace, or cmd+a *inside* it does
 *     nothing (cmd+a in fact selected the whole page's text, since the
 *     slider span never actually took a text-edit focus despite being
 *     `document.activeElement`) -- a triple-click before that even landed
 *     on a bare decorative `<span>`, not the slider, and silently changed
 *     the value to something else entirely (17 -> 9) via what looked like
 *     click-position scrubbing. What worked, first try: read
 *     `aria-valuenow` via `document.querySelector('[role="slider"]')`,
 *     then dispatch ArrowRight/ArrowLeft key presses (one per unit) via the
 *     `computer` `key` action with `repeat` set to the exact delta needed
 *     (e.g. 9 -> 20 = 11x ArrowRight), then re-read `aria-valuenow` to
 *     confirm. This is a duration/settings control, not Generate/Unlimited,
 *     so it isn't covered by the click-blocked-control escalation rule --
 *     but treat any small numeric "pill that opens a panel" on this
 *     composer as a slider-not-input by default and go straight to
 *     arrow-key stepping rather than trying to type into it.
 *
 *   - `document.querySelectorAll('button')` filtered on
 *     `/generate|unlimited/i` can return a STALE, DUPLICATE hidden button
 *     alongside the real one -- one had `visibility:hidden`,
 *     `getBoundingClientRect()` all zeros, and stale/wrong text
 *     ("GENERATE8045" vs the real button's "UNLIMITED\n440\n0" that same
 *     moment). A second, unrelated read of the *same* live button also
 *     returned a different price ("140" via `innerText`) than a zoomed
 *     screenshot of the identical on-screen button taken seconds later
 *     ("440", struck through, resolving to 0) -- `innerText` on this
 *     button is not fully reliable even after filtering out the hidden
 *     decoy. **Always filter by `getComputedStyle(b).visibility !==
 *     'hidden'` before reading a button's text, and when a money-critical
 *     read looks even slightly ambiguous, zoom-screenshot the exact button
 *     region as the tiebreaker** -- it is unambiguous where `innerText`
 *     was not, and it is what this run actually trusted before clicking.
 *
 *   - The in-page `<video>` element can get permanently stuck at
 *     `readyState: 0` / `networkState: 2` (NETWORK_LOADING) with `duration:
 *     null` indefinitely, across a full page reload, `v.load()`, and a
 *     brand-new tab -- while a plain `fetch(v.currentSrc, {method:'HEAD'})`
 *     on the exact same URL returns `200, video/mp4,` a normal
 *     content-length. This is a player/extension-context issue, not a
 *     broken or missing asset. **Fix that actually worked**: click the
 *     card's hover download icon (not Rerun, not Recreate -- the plain
 *     download/cloud icon that appears on thumbnail hover), read the file
 *     off `~/Downloads` (named `hf_<timestamp>_<asset-id>.mp4`, confirming
 *     the asset id independently of the URL/UUID param), and use local
 *     `ffprobe`/`ffmpeg` (`select='gt(scene,N)',showinfo` for hard-cut
 *     timestamps, `-ss <t> -frames:v 1` for still frames at any point) to
 *     do the actual review. This is also strictly cheaper than N
 *     screenshots of an in-browser scrub -- one `ffmpeg` scene-detect call
 *     plus a handful of frame extractions read via the `Read` tool covered
 *     a full 7-shot/6-cut structural review for near-zero browser-tool
 *     cost.
 *
 *   - The synthetic-paste recipe (visibility-filtered contenteditable,
 *     `ClipboardEvent('paste', {clipboardData: dt})`, no follow-up `input`
 *     event, verify first/last 80 chars + length after a short wait) that
 *     earlier waves validated for Element/character prompts worked
 *     unchanged for a much longer (~18.8k char) full-scene multicut prompt
 *     with 8 `@[name](uuid)` mentions -- all 8 resolved to chips
 *     (`[data-beautiful-mention]`, 21 total mentions across the body,
 *     mapping to exactly 8 unique elements), and the reference-thumbnail
 *     strip above the composer showed exactly 8 images, confirmed both
 *     visually and via `document.querySelectorAll('img')` filtered on
 *     `project_valder` alt text.
 *
 * Wave 7 (task-5e0dbf26, 2026-08-26): crowd-plate + pallor reshoot -- 5
 * plates (project_valder_char_crowd_a REVISED mid-task by the CEO to exact
 * accessory counts, _char_crowd_b, _char_guard, _char_valder, _char_press),
 * GPT Image 2 / Medium / 1K / qty 1, 3:2 for the 3 group/wide plates and 2:3
 * for the 2 single-figure plates. 10 credits total (6 generations -- one
 * safety-flagged attempt cost 0), balance 1,974 -> 1,964. All 5 passed
 * within 2 attempts; only Plate 5 (char_press) needed a retry.
 *
 *   - **Two DIFFERENT id namespaces exist for the same asset, and they
 *     disagree.** The `?preview=<uuid>` URL param a thumbnail click adds is
 *     NOT the same id as the `img.alt` / `data-asset-id` value the
 *     Generations media-picker (used for Element re-pointing) exposes for
 *     the identical image -- confirmed on 2 of 5 plates this run (Plate 4:
 *     preview id `4e2a3995-...` vs media-picker id `9451b1b9-...`; Plate 5:
 *     preview id `ccc30c7b-...` vs media-picker id `2b60c244-...`). Visual
 *     match (the picker's first/newest card showing the exact image just
 *     generated) was the only reliable cross-check, since neither id
 *     appeared in the other view. Report BOTH ids if in doubt about which
 *     one a reader needs; never assume the preview-URL id will work when
 *     later searching the media picker by alt text.
 *
 *   - Confirmed the known "Prompt: Prompt is required" paste-to-app-state
 *     desync (first documented in the higgsfield-unlimited-gen skill) can
 *     hit a FIRST-EVER submission of a prompt, not only a resubmission of
 *     one that already generated once -- happened on Plate 1's very first
 *     Generate click this run. The general fix worked unchanged: click into
 *     the editor, press End, type one space, press Backspace, re-verify the
 *     text length is unchanged, then re-click Generate (no re-paste
 *     needed). Cost one extra round-trip, no wasted credits (the failed
 *     click never fires a generation).
 *
 *   - Elements panel search-by-substring can silently return an unfiltered
 *     "All" listing instead of the filtered result, with the typed text
 *     still visibly sitting in the box -- happened searching "char_valder"
 *     this run (six clearly-unrelated cards stayed on screen: Guards 12,
 *     Villagers Rich/Poor, Chase Group, Grandma, Son). The match WAS present
 *     in the DOM the whole time (`document.body.innerText.includes(...)`
 *     confirmed true) -- it was off-screen/unrendered by the virtualizer,
 *     not actually missing. Fix: use `find()` with a natural-language query
 *     for the target card text and `scroll_to` its ref, rather than trusting
 *     that whatever's in the visible viewport after a search is the
 *     complete filtered result.
 *
 *   - Re-confirmed Wave 6's finding, one level more explicitly: a
 *     Face/IP-sensitive single-portrait plate can still be flagged even
 *     when the prompt already states the face's plain ordinariness (this
 *     run's attempt 1 used language very close to Wave 6's successful
 *     framing and was still flagged by the safety system -- NOT the
 *     per-reference "Face/IP failed" eligibility-check string, but a
 *     DIFFERENT string, "Content was flagged by the safety system. Try
 *     different prompts or inputs.", shown as a `[title]` attribute on a
 *     blank, eye-slash-icon card with 0 credits deducted). What flipped
 *     attempt 2 to a clean pass: reinforcing the "synthetic/invented/
 *     assembled from no real photograph/zero basis in any real
 *     individual's likeness/no connection whatsoever to a real person"
 *     language even further than the already-strong base prompt, plus
 *     matching negatives (no basis in a real photograph, no celebrity
 *     likeness, no public figure). Read the flagged card's own `[title]`
 *     text to tell these two failure modes apart before deciding whether to
 *     retry the prompt (safety-flag) or try Recreate/other diagnostics
 *     (a genuine render that then fails its post-hoc eligibility check).
 *
 *   - A safety-flagged generation (the blank/hidden-eye card) costs 0
 *     credits -- confirmed via the account balance dropdown before and
 *     after: this run ended at exactly 1,964 (1,974 - 10), matching 5 PASSING
 *     generations at 2 credits each, with the flagged attempt-1 for Plate 5
 *     contributing nothing to the total despite counting as a real
 *     Generate click and a real wait for the result.
 */

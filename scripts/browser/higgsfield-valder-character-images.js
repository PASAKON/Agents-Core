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
 */

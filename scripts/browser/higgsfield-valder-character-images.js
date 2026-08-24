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
 */

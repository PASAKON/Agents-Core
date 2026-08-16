/**
 * scripts/browser/higgsfield-jumpcut-gen.js
 *
 * Replay helpers for the Higgsfield jump-cut generation flow
 * (https://higgsfield.ai/ai/video — Seedance 2.5, 20s/21:9/720p/Bitrate High).
 *
 * NOT a standalone Node/Playwright script — this repo has no browser
 * automation runtime (no package.json, no playwright/puppeteer dep). Each
 * function here is meant to be pasted into a single `javascript_tool` call
 * against the already-open, already-logged-in Higgsfield tab via the
 * claude-in-chrome MCP, replacing the manual click-by-click steps a model
 * would otherwise re-derive by hand every wave.
 *
 * Validated end-to-end on Wave 2 (task-1ecf3dd2, 2026-08-11) for one
 * generation (Peephole check #1 jump-cut). Findings baked in below.
 *
 * Flow for one scene, using these helpers:
 *   1. Model finds the target History card (by distinctive VISUAL text) and
 *      clicks its Recreate icon — ALWAYS verify via the "Copy" tooltip on
 *      hover first (hfFindRecreateButtonByText helps locate the card+button;
 *      the actual click must go through the driving tool's `hover`+`find`,
 *      not blind coordinates — never click "Rerun", see Hard Rule 1).
 *   2. Real keypress Cmd/Ctrl+A + Delete on the focused editor to clear it
 *      (see hfPromptIsEmpty below for why execCommand does NOT work here).
 *   3. hfSetPromptText(newPromptText) — synthetic paste, text/plain only.
 *   4. hfVerifyGenerateReady() as a pre-check, THEN a real zoom-screenshot of
 *      the Generate button before every click (Hard Rule 3 — DOM text alone
 *      is not enough, a visual check is mandatory every single time).
 *   5. Click Generate (via `find`/ref, not raw coordinates).
 *   6. Poll hfPollStatus() periodically until it returns 'done-or-idle',
 *      then re-check the target History card's own metadata (720p/20.0s/
 *      21:9, no Processing) before starting the next generation — one at a
 *      time (Hard Rule 4).
 *
 * This script intentionally does NOT auto-click Recreate/Unlimited/Generate
 * itself. Those three clicks are exactly the ones the task's hard rules gate
 * on human-legible confirmation (tooltip text, toggle state, zoomed screenshot)
 * — collapsing them into unsupervised JS would defeat the safeguards that
 * exist because Wave 1 burned 130 real credits on an unconfirmed click.
 *
 * Wave 3 findings (task-76d3ce0d, 2026-08-11):
 *
 * 1. The Unlimited-mode switch (and, by extension, other Radix-style
 *    switch/button controls on this page) does NOT respond to a JS
 *    `dispatchEvent(new MouseEvent('click', ...))` sequence — aria-checked
 *    stays false no matter how many synthetic pointerdown/mousedown/
 *    pointerup/mouseup/click events are dispatched. Only a real click via
 *    the driving tool (ref-based, e.g. `computer` action left_click on a
 *    `find`-returned ref) actually flips it. Same is true of the Generate
 *    button itself in practice — always click these two via the driving
 *    tool, never via JS, even though hfGetGenerateButton()/
 *    hfGetUnlimitedToggle() are fine for *reading* state.
 *
 * 2. The prompt editor's draft content survives a full page reload
 *    (localStorage-backed autosave) — a stale/misloaded prompt does NOT
 *    reset itself on reload, so don't assume a reload gives you a clean
 *    slate for the prompt. The Unlimited-mode toggle does NOT survive a
 *    reload (resets off, consistent with the existing Recreate-reload
 *    finding below) — re-check and re-toggle after every reload, not just
 *    every Recreate.
 *
 * 3. Server-side concurrency cap: clicking Generate can return the toast
 *    "You can generate 1 unlimited video, image & audio generation at a
 *    time. To use full concurrency, switch to credit-based generations."
 *    This is NOT caused by anything this tab did — reproduced 4x across a
 *    full page reload, with zero prior successful Generate in the session,
 *    and zero Processing/Generating text or spinner anywhere in History
 *    (List or Grid view) that would explain what's occupying the slot.
 *    Conclusion: this is a real account-level lock, most likely another
 *    browser session on the same Higgsfield account holding the 1
 *    concurrent unlimited-mode job. Retrying Generate in this tab cannot
 *    fix it. Do not switch to credit-based generation to route around it
 *    without explicit authorization — that spends real credits. Report the
 *    blocker and wait instead.
 *
 * 4. The History list container is virtualized top-to-bottom: `innerText`
 *    of the container only reflects whatever range of items is currently
 *    mounted near the current scrollTop, and jumping scrollTop directly to
 *    a large value (skipping the intermediate range) can land in a range
 *    that is still an unhydrated skeleton (0 chars of text) even after a
 *    multi-second wait — the lazy-load trigger needs to actually pass
 *    through the intermediate scroll positions, not just land on the
 *    target one. Scroll there in several smaller steps (~700-1200px, a few
 *    hundred ms apart) rather than one big jump.
 *
 * 5. Once the concurrency lock from finding 3 above clears, generation
 *    reliably follows a two-phase status text at the top of the History
 *    list: "Processing / Cancel" for the first several minutes, then
 *    "Generating" for a final stretch, then the status text disappears and
 *    full metadata (720p/20.0s/21:9/date/Rerun) appears — that's the real
 *    completion signal, not the Processing→Generating transition. Measured
 *    across 5 back-to-back generations in one session: total time per
 *    generation ranged ~1-13.5 minutes, so a long wait alone is not
 *    evidence of a problem — the concurrency-lock toast (finding 3) is the
 *    actual failure signal, not elapsed time.
 *
 * 6. The Copy/Recreate icon's button index inside a card is NOT fixed (it
 *    shifts with how many @Image reference thumbnails the card has), but
 *    its on-screen x-coordinate is: consistently x≈946 in a 1024-wide
 *    viewport (the Rerun icon sits at x≈976, just right of it). Cheapest
 *    reliable way to find the right button: collect the small (w<40,h<40)
 *    buttons in the card div and take the one at x≈946 — don't assume a
 *    fixed array index across cards with different reference-image counts.
 *
 * 7. A Recreate click can silently no-op (composer keeps showing whatever
 *    was loaded before) even when the target card div reference passes
 *    `document.contains()`. Always verify by reading the composer's actual
 *    text back and checking it matches the intended card's distinctive
 *    phrase; if it still shows the previous content, re-run
 *    `card.scrollIntoView()` and retry the same click dispatch once before
 *    concluding something is actually wrong.
 *
 * Wave 4 findings (task-036de9ea, 2026-08-11):
 *
 * 1. **Always keyword-scan for the target scene's jump-cut BEFORE generating
 *    anything, even when the task brief says it's "the last one remaining".**
 *    This wave was briefed to do the last core scene needing a jump-cut
 *    ("Bathroom-sounds": off-frame toothbrush/rinse/splash sounds while Nam
 *    sleeps). A scan turned up that scene already had a completed jump-cut
 *    (Cut 1-5, 720p/20.0s/21:9, dated the same day) sitting a bit further up
 *    the list than expected — evidently done in an earlier wave whose Scene
 *    Tracker update never landed, or a mis-tracked slot count. Generating
 *    again would have been an unrecoverable duplicate spend. Use
 *    `hfFindCardByKeyword()` below to check before every Recreate.
 *
 * 2. **`hfScrollHistory`'s `c.scrollTop = N` assignment does NOT stick
 *    across separate `javascript_tool` calls.** Measured repeatedly: set
 *    scrollTop in one call, read it back in the very next call with no
 *    scrolling in between, and it had silently jumped to an unrelated value
 *    (900 → 13300 with nothing in between touching it). The container
 *    element itself was confirmed stable/unique (only one el matches the
 *    scrollHeight+overflow-y-auto heuristic), so this isn't a wrong-element
 *    bug — the list's own virtualizer appears to re-settle scrollTop on its
 *    own between renders. **Fix: scroll and read-back must happen inside the
 *    SAME `javascript_tool` call**, never split across two calls with the
 *    assumption that position holds in between.
 *
 * 3. **`await new Promise(r => setTimeout(r, N))` inside a `javascript_tool`
 *    call intermittently hung the whole call for the full 45s CDP timeout**
 *    in this session, with the page confirmed still responsive immediately
 *    before and after (a bare `document.title` read succeeded both times).
 *    Synchronous-only calls (scroll+dispatch, or a plain read) never hung.
 *    Root cause unclear (CDP/harness-side, not page-side) — but the
 *    workaround that worked every time was to drop the in-script wait
 *    entirely and let the natural round-trip latency between two separate
 *    tool calls serve as the delay instead.
 *
 * Wave 5 findings (task-939d45ba, 2026-08-11, bulk DOWNLOAD not generation):
 *
 * 1. **Grid view's date-section header has a checkbox that select-all's every
 *    card in that section, and a bottom toolbar (12/22/45 selected → Download
 *    /Publish all/Add to/heart/trash/X) appears with a real "Download" button
 *    that zips the whole selection server-side** (`~/Downloads/archive.zip`,
 *    `archive (1).zip`, etc. — Chrome auto-numbers repeats). This is drastically
 *    cheaper than clicking each card's own download icon one at a time — one
 *    click zips 12-45 files. Switch to Grid view (`List`/`Grid` toggle top-right
 *    of the History panel) to get section checkboxes; List view's cards don't
 *    have this. Large zips (45 files, ~210MB) took ~15s to prepare server-side
 *    before landing in Downloads — poll `ls -lat ~/Downloads/*.zip` and check
 *    file size stability (two `stat` calls a few seconds apart) rather than a
 *    fixed sleep.
 *
 * 2. **Never reuse a generic filename across separate bulk-extract passes**
 *    (e.g. `<scene>_jumpcut.mp4`) without checking whether an earlier pass
 *    already claimed it — `cp` silently overwrites, no warning, no error. Two
 *    separate zips both containing a "door-bag-reveal jumpcut"-sounding card
 *    (one from a "Today" section, one from "Yesterday") got the same
 *    destination filename and the second `cp` silently clobbered the first,
 *    losing that file until re-extracted from the original zip (kept in
 *    Downloads — don't delete source zips until the whole sort is verified
 *    committed to disk). `find ~/Desktop/<dest> -name "*.mp4" | wc -l` against
 *    the expected sum (sum of each section's "N selected" count) catches this
 *    immediately — a silent overwrite makes the total come up short.
 *
 * 3. **A card's own inline date label (the "August N, 2026" text printed on
 *    the card itself) and the Grid section header it's bucketed under
 *    ("Today"/"Yesterday"/"August N, 2026") are NOT the same clock/timezone**
 *    — e.g. cards inline-labeled "August 9" were bucketed under the
 *    "Yesterday" section header alongside "August 10"-labeled cards. Filename
 *    timestamps (`hf_YYYYMMDD_HHMMSS_...`) are UTC; the section header groups
 *    by a different (Bangkok, UTC+7) calendar day. Don't infer a card's
 *    section from its own inline date text — use the section header's own
 *    checkbox selection as ground truth for what's actually in a given bulk
 *    zip.
 *
 * 4. **The card-splitting regex must anchor on "Seedance 2.5" occurrences
 *    directly (`t.matchAll(/Seedance 2\.5/g)`), not on "\nSeedance 2\.5\n"`**
 *    — a leading/trailing newline can be missing at a text-node boundary and
 *    silently drops that one card from the split, undercounting by exactly 1
 *    with no error.
 *
 * 5. **Do not trust a content-position mapping built from stale/earlier scan
 *    notes for a *different* bulk batch, even when the prose descriptions
 *    sound like they match.** The safe method is a *fresh*, single, ordered
 *    top-to-bottom scan of the exact section immediately before assigning
 *    filenames — done this way for one 45-card batch here and it held up:
 *    scan in overlapping windows (each `javascript_tool` call scrolls+reads
 *    in the SAME call — see Wave 4 finding 2), splitting by `Seedance 2.5`,
 *    keep the local index `i` label per-snapshot only (it renumbers from 0
 *    in each virtualized window, NOT a stable global index — align separate
 *    snapshots by CONTENT overlap, never by raw `i`), then map newest-first
 *    scan order directly onto the newest-first (filename-timestamp-descending)
 *    file list. Skipping this and reusing an earlier ad-hoc scan's memory for
 *    a second batch produced a fully-scrambled mapping (every single one of
 *    21 files wrong) that only surfaced via a targeted keyword search
 *    (`indexOf('congee')`) turning up content that didn't match any assigned
 *    name — that's a good trip-wire to run once per batch as a sanity check
 *    even after doing the careful scan.
 *
 * Wave 6 findings (task-6acde95c, 2026-08-11, fresh-composer generation,
 * no Recreate — 2 new generations from a blank References picker):
 *
 * 1. **The composer can arrive with a STALE prompt already loaded, from a
 *    completely different, unrelated scene** — confirmed via localStorage
 *    autosave (see Wave 3 finding 2) persisting across sessions, not just
 *    reloads. On a brand-new tab navigation to `/ai/video` with zero prior
 *    action this session, the prompt editor already contained a different
 *    scene's full prompt (a "Bathroom-sounds" jump-cut from an earlier
 *    wave), and the Generate button already showed a real credit number
 *    (130) with Unlimited mode OFF. **Never trust the composer's starting
 *    state for a "fresh composer, no Recreate" task** — always read the
 *    prompt editor's full text first and confirm/deny it matches your
 *    target scene before doing anything else. In this case the stale
 *    References thumbnails (Nam + dorm room) turned out to be exactly the
 *    two references the new task also needed, since the project reuses the
 *    same character/room refs across scenes — worth checking via a small
 *    `zoom` on the References thumbnails (they need a couple seconds to
 *    load past a shimmer placeholder) before assuming a re-upload is
 *    needed.
 *
 * 2. **Both `computer` `screenshot` and `zoom` can hang for a full 30s CDP
 *    timeout ("Page.captureScreenshot timed out... renderer may be frozen")
 *    on a tab that has been open a while, while `javascript_tool`, `find`,
 *    and `read_page` on the SAME tab keep working normally throughout.**
 *    Per the skill, treat this as a "tool error on the Higgsfield page" and
 *    check Usage History immediately — but note this specific failure mode
 *    is CDP/harness-side (matches Wave 4 finding 3's suspicion), not a sign
 *    of an actual spend. The reliable fix: open a **new tab** via
 *    `tabs_create_mcp` and re-navigate — screenshots worked immediately on
 *    the fresh tab. Do not burn retries re-screenshotting the same stuck
 *    tab.
 *
 * 3. **`resize_window` can silently orphan the MCP tab group** — after
 *    calling it, the very next `tabs_context_mcp` (or any tool needing an
 *    implicit tab) returns "No tab group exists for this session." This
 *    reproduced twice in one wave. Fix: `tabs_context_mcp{createIfEmpty:
 *    true}` immediately to get a fresh group + tab, re-navigate, and don't
 *    call `resize_window` again that session — work at whatever size the
 *    window opens at instead (it was already ~1024x591 without an explicit
 *    resize in this run) and lean harder on `javascript_tool`/`find` over
 *    screenshots to control cost.
 *
 * 4. **A generation can fail outright on a fully clean, non-explicit prompt**
 *    — observed twice in this wave: the long-take failed with "Rejected due
 *    to copyright restrictions" and the jump-cut failed with an "NSFW" flag,
 *    both on prompts describing a sick character sleeping/waking, no IP
 *    references, no explicit content. Both were refunded (confirmed via
 *    Usage History: `Unlimited | Seedance 2.5 | Refunded`) and both
 *    succeeded on a single same-prompt, same-refs retry (re-verify
 *    Unlimited-ON + zero-digit Generate again before the retry click, since
 *    neither reset from the failure). Treat a single failure of either kind
 *    as a retry-once case, matching the task brief's "NSFW twice" stop
 *    threshold — stop and message the C-level only on a second consecutive
 *    failure of the same generation.
 *
 * 5. **The Unlimited-mode toggle and the Generate button's credit-number
 *    reset to OFF/priced on EVERY prompt-clear + re-paste cycle within the
 *    same session**, not just after a full page reload or a Recreate click
 *    (Wave 3 finding 2 already covered reload; this extends it to manual
 *    clear+paste too). Re-check and re-toggle Unlimited before every single
 *    Generate click, no matter how recently it was already turned on.
 *
 * 6. **A `find`-returned ref for the prompt editor can silently fail to
 *    focus it** (`document.activeElement` stays `BODY` after a `computer`
 *    `left_click` on the ref) after switching between List/Grid history
 *    view or after a detail modal has opened and closed — the ref still
 *    resolves to *an* element without erroring, but the click doesn't
 *    register as a real focus event. Always verify
 *    `document.activeElement === document.querySelector('[contenteditable="true"]')`
 *    right after the click, before sending Cmd+A. If unfocused, click raw
 *    coordinates from the editor's own `getBoundingClientRect()` instead —
 *    that worked every time this stale-ref click didn't.
 *
 * 7. **There is no working per-card download control in List view** — the
 *    enlarged video player only exposes native HTML5 controls (play, mute,
 *    scrubber, fullscreen); clicking near where a download icon might be
 *    expected just plays/pauses or seeks the video. **Switch to Grid view**
 *    (`List`/`Grid` toggle, top-right of the History panel) and hover the
 *    target card — a small icon column appears at the thumbnail's top-right
 *    (heart, copy/duplicate, a download-tray icon, "..."). Clicking the
 *    download-tray icon sometimes fires the download directly, and
 *    sometimes instead opens a full detail modal (`[role="dialog"]`, tabs
 *    Info/Tools/Comments) that has its own "Download" button. **The
 *    reliable trigger in both cases was a direct JS `.click()` on the
 *    located button element** (`[...dlg.querySelectorAll('button')]
 *    .find(b => b.innerText.trim() === 'Download').click()`), not a
 *    `computer` coordinate click — a coordinate click on the same button at
 *    the same computed center point silently did nothing twice in a row
 *    (confirmed via `read_network_requests` showing no `/track` or asset
 *    fetch fired), while the JS `.click()` immediately produced a real file
 *    in `~/Downloads` named `hf_<UTC-timestamp>_<job-uuid>.mp4`. Verify by
 *    polling `ls -lat ~/Downloads/*.mp4` a few seconds after the click
 *    rather than trusting the click "succeeded" silently.
 *
 * Wave 7 findings (task-0ee4a20a, 2026-08-14, Cinema Studio project-folder
 * composer — NOT /ai/video; Seedance 2.0 / 1080p / 15s / 21:9):
 *
 * 1. **A FAILED card exposes only "Copy prompt" and "Delete" — there is no
 *    Recreate.** The skill's "for any repeat of a prompt, use Recreate" advice
 *    silently does not apply to a scene whose every take failed. The composer
 *    must be rebuilt by hand in that case. Check the card's button set before
 *    planning a Recreate-based flow.
 *
 * 2. **Pasting the prompt auto-converts `@Name` tokens into real element
 *    chips.** The Lexical build here uses `data-beautiful-mention`; a
 *    text/plain synthetic paste of "... @Room-Clean ..." produces a bound
 *    mention node with the element's reference plate attached. No manual chip
 *    picking is needed, which removes the main risk at the 10-element cap.
 *    Count attached elements with:
 *      new Set([...ed.querySelectorAll('[data-beautiful-mention]')]
 *        .map(m => m.getAttribute('data-beautiful-mention'))).size
 *    Count the ATTRIBUTE (a uuid), not the visible label — see finding 3.
 *
 * 3. **A chip can render its raw uuid instead of its name and still be
 *    correctly attached.** `@Prop-Glass` displayed as
 *    `@396c8cda-4098-46b5-8bf6-2bb6385772db` with no inline thumbnail, which
 *    looks exactly like a dangling reference. It is not: the reference tray
 *    above the composer showed its plate, and Scenes 10-B and 10-C both carry
 *    `@Prop-Glass` and both generated successfully. Counting distinct visible
 *    LABELS gives 9 and triggers a false "chip missing" alarm; counting
 *    distinct `data-beautiful-mention` values gives the true 10.
 *
 * 4. **With Unlimited ON the action button is relabelled "Unlimited", not
 *    "Generate".** Every `/generate/i` matcher in this file returns nothing at
 *    the exact moment the zero-digit check matters most. Match
 *    `/generate|unlimited/i`. The price is two sibling spans: the original with
 *    `text-decoration-line: line-through`, then the effective one. Free reads
 *    as struck-through original + "0".
 *
 * 5. **Do not read the price off a screenshot.** The rendered button looked
 *    like "480" at 1456x840; the DOM said "180". Same misread class the brief
 *    warns about. `getComputedStyle(span).textDecorationLine === 'line-through'`
 *    is the authoritative discriminator.
 *
 * 6. **The composer settings row scrolls horizontally and the Unlimited toggle
 *    starts underneath / right of the Generate button.** At a 1024-wide
 *    viewport the switch sat at css x≈1110 (off-screen) and, after collapsing
 *    the sidebar, at x≈972 — ~15px from the Generate button's edge, i.e. one
 *    sloppy click from an unintended fire. Scroll its container
 *    (`overflow-x:auto`, 4 levels up from `[role="switch"]`) to
 *    `scrollWidth` first; that moves the toggle ~164px left, clear of Generate.
 *    Collapse the sidebar too. Never click blind near that corner.
 *
 * 7. **Screenshot pixels are NOT css pixels.** Screenshots came back 1456x840
 *    for a 1024x591 viewport — a 1.4219x factor that must be applied to every
 *    `getBoundingClientRect()` value before passing it to `computer` as a
 *    coordinate. Clicking raw css coordinates lands high and left, which is how
 *    an operator misses a control and hits its neighbour.
 *
 * 8. **`resize_window` reports success while changing nothing** when the window
 *    is in macOS fullscreen (innerHeight stayed 591 for both 768 and 900
 *    requests), and it still orphans the MCP tab group (Wave 6 finding 3
 *    reproduced twice). Verify with `[innerWidth, innerHeight]` and recover via
 *    `tabs_context_mcp{createIfEmpty:true}` + re-navigate.
 *
 * 9. **`navigator.clipboard.readText()` froze the renderer for the full 45s CDP
 *    timeout** (permission prompt with no visible UI). Do not call it. Read
 *    prompts out of the DOM instead.
 *
 * 10. **Seedance 2.0 now shows an audio control** (speaker icon reading "On")
 *    in the settings row, alongside a "High" bitrate control. This contradicts
 *    the earlier finding that only "Seedance 2.5 Edit" carries audio. Worth a
 *    C-level decision on whether AUDIO-SFX sections are still inert.
 *
 * 11. **The 10-element cap is a hard ceiling that fails as a generic error.**
 *    RESOLVED. Scene 10-D failed 3/3 with "Something went wrong. Please try
 *    again, or change your input files or prompt." on a composer verified
 *    correct in every respect (10/10 chips, verbatim prompt, full spec,
 *    Unlimited, $0, all three refunded). Dropping ONE element — `@Prop-Handbag`,
 *    rewritten as plain words — took the block from 10 distinct elements to 9
 *    and it generated first try, same beat, same plates, same NEGATIVE section.
 *    **Treat 10 attached elements as unusable and 9 as the working maximum.**
 *    Higgsfield reports the ceiling as an unattributed generic failure, never
 *    as a limit message, so it is indistinguishable from a content rejection
 *    unless you count elements. Rule out the count BEFORE suspecting wording or
 *    a broken plate: both were investigated at length here and both were
 *    innocent (the `@Mother-Soul` plate rendered a complete character sheet and
 *    subsequently generated fine).
 *
 * 12. **"Prompt is required when no media is provided" means the paste never
 *    bound to React state — the prompt is fine.** The tell is unmistakable and
 *    worth checking directly: the composer shows its placeholder
 *    ("Describe the scene you imagine...") AT THE SAME TIME as holding
 *    thousands of characters and correctly-bound mention chips. A full page
 *    reload does NOT clear it. The fix that worked, and which preserves the
 *    prompt byte-for-byte:
 *      1. `ed.scrollIntoView({block:'center'})` — the editor can sit far above
 *         the viewport, so a click lands on nothing.
 *      2. A real click into the editor.
 *      3. A real Space keypress, then a real BackSpace keypress.
 *    Net content change is zero and no Enter is involved, but the pair emits a
 *    genuine input event that forces Lexical to bind. The placeholder vanishes
 *    the instant it works; verify that, plus unchanged length, before clicking
 *    Generate. Do NOT type any part of the prompt itself (hard rule 6 stands).
 *
 * 13. **Chrome allows exactly ONE automatic download per browser session per
 *    origin, then blocks the rest silently.** No error, no console entry, no
 *    file — and the block survives a page reload, a new tab, and both the
 *    card-tray icon and the detail modal's own Download button (JS `.click()`
 *    and real coordinate click alike). The only thing that resets it is
 *    quitting and reopening Chrome, after which the next download succeeds
 *    immediately. So a multi-clip mirror is: restart Chrome, download one,
 *    upload it, repeat. Budget a browser restart per file, or use the Grid-view
 *    bulk zip (Wave 5 finding 1) which is a single download for the whole
 *    selection and therefore only costs one allowance.
 *
 * 14. **`resize_window` cannot help when the screen itself is the limit.** On a
 *    1440x900 display Chrome's UI leaves innerHeight 754, and the composer's
 *    Image/Video tab strip renders at css y≈773-825 — permanently below the
 *    fold. `resize_window`, AppleScript `set bounds`, page zoom and macOS
 *    fullscreen all failed to raise it. What works: switch the composer to
 *    Video mode from a folder whose composer is already reachable (or via a
 *    Recreate on any existing video card), then navigate to the target folder —
 *    **the Image/Video mode persists across navigation**, while the prompt
 *    persists via localStorage and Unlimited does not.
 *
 * Wave 8 findings (task-989d4a38, 2026-08-14, /ai/video History — bulk
 * multi-scene download, no generation):
 *
 * 1. **Per-card checkboxes for Grid-view multi-select don't exist in the DOM
 *    until that specific card is hovered** — `document.querySelectorAll(
 *    'button.checkbox')` inside the History container returns only the 1-2
 *    section-header checkboxes at rest. The header checkbox's own click
 *    behaves as a global "select all currently mounted, growing as more
 *    scroll into view" toggle, NOT a clean select-all/deselect-all pair —
 *    two clicks on it went 0→23→25 selected, never back to 0. Use the
 *    toolbar's own "Unselect all" (X) button to reset to zero instead of
 *    re-clicking the header.
 *
 * 2. **Reliable per-card selection recipe**: `computer` `hover` at the card's
 *    coordinate, immediately followed by `computer` `left_click` at the same
 *    coordinate (checkbox sits ~20px screenshot-px in from the card's
 *    top-left corner, which coincides with the thumbnail `<img>`'s own
 *    top-left — no separate icon-strip offset). A bare `left_click` with no
 *    preceding `hover` on that exact spot silently missed 4 of 5 attempts in
 *    this run (the synthetic move component of `left_click` didn't reliably
 *    fire the React mouseenter the hover-reveal listens for) — always pair
 *    them. Verify progress cheaply after each card via
 *    `document.body.innerText.match(/\d+\s*selected/i)`, not a screenshot.
 *
 * 3. **Screenshot-pixel vs CSS-pixel ratio must be measured per session, not
 *    assumed.** This run's window reported `innerWidth`/`innerHeight` of
 *    1280x754 (not the 1024x768 `resize_window` was asked for — silently
 *    ignored again, consistent with Wave 7 finding 8) while screenshots came
 *    back 1426x840 — ratio 1.114, not the 1.4219 recorded in Wave 7 on a
 *    different display/window size. Compute `screenshot_w / innerWidth`
 *    fresh each session before converting any `getBoundingClientRect()`
 *    value into a `computer` click coordinate.
 *
 * 4. **Diffing "which History cards are new" against Drive by id, done
 *    entirely in JS, avoided all visual recognition.** Query only inside the
 *    History scroll container (`hfGetHistoryContainer()` above) for
 *    `img,video` elements, regex out `hf_\d{8}_\d{6}_[a-f0-9-]+` from `.src`
 *    (raw `.src` itself is blocked as "Cookie/query string data" by the
 *    extension — extract just the id substring, never return the full URL),
 *    and diff that set against filenames already listed via
 *    `gdrive_move.py list` on the target Drive folder. **Querying
 *    `document.querySelectorAll('img')` unscoped is contaminated** — a
 *    left-hand References/element-picker panel reuses the same `hf_` URL
 *    pattern for unrelated small thumbnails and will pollute the id list;
 *    always scope the query to the History container element.
 *
 * 5. **Grid-view bulk zip (Wave 5 finding 1) is still the right tool for a
 *    same-origin multi-file pull inside the Chrome-one-download-per-session
 *    cap (Wave 5 finding 13)** — selecting exactly 8 non-contiguous target
 *    cards (skipping ones already confirmed present on Drive) and clicking
 *    the toolbar's Download produced one `archive (N).zip` containing
 *    exactly those 8 files, filenames intact. Poll `~/Downloads/*.zip` size
 *    twice a few seconds apart for stability before unzipping, same as
 *    Wave 5.
 *
 * Wave 9 findings (task-9ea647f6, 2026-08-14, Cinema Studio PROJECT FOLDER
 * — `/generate/@<org>/<project>/folders/<uuid>`, NOT `/ai/video` History —
 * small download-only pull, 5 cards total):
 *
 * 1. **A Cinema Studio project folder's card grid is a different DOM tree
 *    from the `/ai/video` History panel** — do not reuse
 *    `hfGetHistoryContainer()` (matches on `scrollHeight > clientHeight +
 *    5000`, tuned for a huge virtualized list) here. This folder's grid
 *    container is small and only barely scrollable even with content
 *    (measured: `scrollHeight` 515 vs `clientHeight` 500 for 5 cards).
 *    Locate it instead by class fingerprint:
 *    `(el.className+'').includes('flex-1') && includes('overflow-y-auto')
 *    && includes('hide-scrollbar')` — a sibling element with classes
 *    `overflow-y-auto hide-scrollbar` but no `flex-1` also exists (the left
 *    Folders nav list) and has zero images in it; the `flex-1` term is what
 *    disambiguates the two.
 *
 * 2. **The id-diff recipe (Wave 8 finding 4) transfers cleanly**: scope the
 *    `img,video` query to the grid container found above, regex out
 *    `hf_\d{8}_\d{6}_[a-f0-9-]+` from `.src`, diff against
 *    `gdrive_move.py list <folderId>` output. Zero screenshots needed for
 *    the inventory step; only 2 small zooms were spent confirming the
 *    per-card icon strip layout, well under the 5-screenshot budget flag.
 *
 * 3. **Verify a task-supplied Drive folder id before trusting it — it can be
 *    stale.** The task brief's own text said as much ("verify by listing
 *    `All Scene`... don't trust this pasted id blindly") and it caught a
 *    real mismatch: the brief's `S11` id (`1CSvSnzTLTLKovtjaFn_Ck0RZ3E3PN7Ip`)
 *    did not match the real `S11` folder id found by listing `All Scene`
 *    fresh (`1UUr-xoemX6WAFVF-ziIkU2Qwlvbamb8P`). The `S11-1080P` id in the
 *    brief matched. One `gdrive_move.py list` on the parent before touching
 *    anything downstream would have caught this either way — do that list
 *    first, every time, regardless of how confident the brief sounds.
 *
 * 4. **Per-card hover-revealed icon strip (heart / download-tray / copy /
 *    image, left-to-right) only mounts in the DOM after a REAL hover event**
 *    — same quirk as Wave 8 finding 1's checkboxes, but for a completely
 *    different UI (this is a project folder, not History Grid-view
 *    multi-select). A `javascript_tool` walk that skips the hover finds the
 *    card's ancestor with `querySelectorAll('svg').length >= 4` returning 0
 *    matching buttons (`btns[1]` is `undefined`) even though the icons are
 *    visibly present in a screenshot taken moments earlier in the SAME
 *    session on a DIFFERENT card — the mount state is genuinely per-card,
 *    not global. Fix: `computer` `hover` at the card's on-screen coordinate
 *    FIRST (a bare synthetic hover via JS does not reliably fire it either,
 *    consistent with Wave 8 finding 2's warning about `left_click`'s
 *    synthetic move not firing React's `mouseenter`), THEN run the
 *    `javascript_tool` query in a separate call. The 2nd button (`btns[1]`,
 *    i.e. 0-indexed position 1 of the 4 unlabeled `button.button-tertiary`
 *    icons) is the download-tray icon; button 0's outerHTML read as
 *    `[BLOCKED: Cookie/query string data]` (an inline SVG sprite href with a
 *    query string, tripped the extension's own redaction — harmless, just
 *    don't rely on reading its content, index-count around it instead). A
 *    direct JS `.click()` on `btns[1]` triggered an immediate real download
 *    every time it was tried on a freshly-hovered card — matches Wave 6
 *    finding 7's "JS `.click()` beats coordinate click" for the analogous
 *    History-panel download control.
 *
 * 5. **The one-download-per-session-per-origin cap (Wave 7 finding 13)
 *    reproduced exactly** on this surface too: file 1 downloaded cleanly,
 *    file 2's identical click produced no error, no console entry, and no
 *    file in `~/Downloads` after a few seconds' wait. `osascript -e 'quit
 *    app "Google Chrome"'` + `open -a "Google Chrome"`, then a fresh
 *    `tabs_context_mcp{createIfEmpty:true}` + re-navigate, unblocked it
 *    immediately — file 2 downloaded on the very next click, no retries
 *    needed. Budget one Chrome restart per file beyond the first when doing
 *    per-card downloads outside the Grid-view bulk-zip path; the zip path
 *    (Wave 5 finding 1) sidesteps this entirely by still counting as one
 *    origin download for N files, so prefer it whenever selecting >2 cards.
 *
 * 6. **Screenshot-pixel vs CSS-pixel ratio was exactly 1.0 in this session**
 *    (1024 window request → 1024x591 screenshot, matching `[innerWidth,
 *    innerHeight]` read via JS) — a useful data point against Wave 7/8's
 *    1.42x and 1.11x on other displays/window states: this ratio is NOT a
 *    per-machine constant, it's per-window-state, and must be re-measured
 *    every session exactly as those findings already said. Recorded here
 *    only because a 1.0 ratio (no correction needed at all) is itself worth
 *    knowing was observed, not just the two skewed cases.
 *
 * Wave 10 findings (task-110cf390, 2026-08-14, negative-result verification —
 * confirming 5 empty Drive scene folders (S11, S13-S16) had genuinely no
 * matching Higgsfield footage anywhere, no generation, read-only both
 * surfaces):
 *
 * 1. **This project splits footage by resolution into sibling Drive folders,
 *    `SX` (720p) and `SX-1080P` (1080p) — a bare `SX` folder showing 0 files
 *    does NOT mean the scene has no footage** if all of it happens to be
 *    1080p. Confirmed: Drive's bare `S11` was empty while `S11-1080P` held
 *    all 5 existing clips (the 11D/11D-B family). Always check both siblings
 *    before concluding a scene is genuinely footage-less — a bare `SX`
 *    folder can be legitimately empty by the routing convention and still
 *    correct to delete once confirmed 0 files, since the real content lives
 *    in `SX-1080P` instead.
 *
 * 2. **The Cinema Studio project folder index (left sidebar under a project's
 *    Folders panel) is a cheap first-pass census.** A single
 *    `javascript_tool` read of the "Folders" list gave every scene's folder
 *    name + item count in one call (~15-token-class read, no screenshot):
 *    query for leaf elements matching `/^Sence \d+/` and read `parentText`
 *    (label + count are concatenated with no separator, e.g. "Sence 1212"
 *    means Sence 12 → 12 items). Confirmed this project's index has NO
 *    `Sence 13`/`14`/`15`/`16` folders at all — matches PROMPTS.md stating no
 *    prompt was ever written for those scenes (folded into Scene 12-FB) and
 *    is a fast corroborating check before trusting a brief's claim like that.
 *
 * 3. **A full `/ai/video` History sweep for "does X exist anywhere" needs the
 *    scroll-to-true-end loop repeated in bursts, not run once.**
 *    `scrollHeight` did not just grow smoothly to one final value — it
 *    plateaued twice (at ~17k, then ~46k) before a further jump revealed
 *    more content (final true end ~84k px, spanning from an in-flight
 *    "Generating" card down to content dated 2026-08-06, i.e. the account's
 *    entire history, well before this festival project started). A
 *    stable-for-one-check `scrollHeight` is NOT reliable proof of the true
 *    end; loop `scrollTop = <huge number>` + re-check `scrollHeight` until
 *    it repeats on TWO consecutive iterations, and re-run any keyword/phrase
 *    scan across the newly revealed range too — a scan that stopped at the
 *    first plateau would have silently missed roughly half the history.
 *
 * 4. **For a "does this specific sub-scene exist" negative-result check,
 *    search List-view `innerText` for the prompt's own distinctive VERBATIM
 *    phrases (5-8 words, copied straight from PROMPTS.md), not a scene-label
 *    regex.** Scene sub-labels like "11A"/"11B"/"11C" never appear literally
 *    in the generated prompt text itself (Higgsfield cards show only
 *    VISUAL/AUDIO-SFX prose, no scene-number metadata), so regex-matching
 *    "11A" finds nothing whether or not the content exists. A loose keyword
 *    (e.g. "room 214", "bursts inward") produced false-positive hits against
 *    an unrelated scene that happens to share vocabulary — always read the
 *    matched card's actual surrounding text before concluding a hit is real;
 *    a hit that shows unrelated words ("SLOW MOTION" where the target prompt
 *    never mentions slow motion) is a different scene, not the one you're
 *    checking for. Tight, near-verbatim phrase matches (7+ consecutive words
 *    unique to one prompt) produced zero false positives across the whole
 *    account history in this run.
 *
 * 5. **Grid view renders card thumbnails only — no prompt text in the DOM at
 *    all** (`innerText` of the History container returns just section
 *    headers like "Today", 5 chars total). Any text-based keyword/phrase scan
 *    of History MUST be done in **List view** (click the "List" tab next to
 *    "Grid", top-right of the History panel) — Grid view is for visual
 *    browsing and bulk-select/download only (Wave 5/8), never for content
 *    search.
 *
 * Wave 11 findings (task-fa856c1d, 2026-08-15, S1-S8 Drive/Higgsfield
 * reconcile — blocked before any Higgsfield page load):
 *
 * 1. **A fresh MCP tab can have zero authenticated Higgsfield session even
 *    though auth-shaped cookies are present.** `document.cookie` listed
 *    `__session`, `__client_uat`, `__client_uat_FQWayshe` (Clerk-style names)
 *    but `/ai/video`, `/generate`, and `/generate/@ilag-studio/ai-film-festival`
 *    all rendered the logged-out nav (`Login`/`Sign up` top-right); the last
 *    one 404'd outright, consistent with an unauthenticated request to a
 *    project route. Reloading once did not change the result. `document.cookie`
 *    having the right-looking keys is NOT proof of a live session — read the
 *    actual rendered nav (or a project route's success/404) before assuming
 *    login is intact, especially at the start of a wave that opens a brand
 *    new tab.
 *
 * 2. **`list_connected_browsers` is a fast way to confirm there's no second,
 *    already-authenticated browser/profile to fall back to** before filing an
 *    auth blocker — one call, ~10 tokens, returned exactly one `isLocal:true`
 *    entry here, ruling out a "wrong browser selected" explanation in one
 *    shot instead of guessing.
 *
 * 3. **Drive-side work does not need to wait on Higgsfield access** — the
 *    `gdrive_move.py list` census (this wave: all 16 `All Scene` subfolder
 *    ids, then all 9 relevant S1-S8 folders' file names/sizes) is pure
 *    `Bash`, zero browser cost, and completed fully before the auth problem
 *    was even discovered. When a task has both a Drive and a Higgsfield leg,
 *    do the Drive leg first regardless of order in the brief — if Higgsfield
 *    turns out blocked, the Drive numbers are still a complete, useful partial
 *    result instead of nothing.
 * Wave 12 findings (task-072ebf30, 2026-08-15, resume of task-fa856c1d —
 * Higgsfield session now live, full S1-S8 Drive/Higgsfield reconcile,
 * collection-only, no generation):
 *
 * 1. **`[data-asset-id]` is the reliable per-clip identifier inside a Cinema
 *    Studio project folder — far more reliable than parsing thumbnail `src`
 *    for the `hf_<timestamp>_<uuid>` string.** The extension redacts any
 *    returned string containing "Cookie/query string data" (many thumbnail
 *    `src` values hit this and come back as `[BLOCKED: ...]` in
 *    `javascript_tool` output, non-deterministically — some cards' `src`
 *    passed through clean, others on the same page didn't). `[data-asset-id]`
 *    holds the bare uuid directly as an HTML attribute, never blocked, and
 *    also carries `data-asset-status` ("completed" vs a failed/NSFW state)
 *    and `data-tour-asset-kind` ("video") for free in the same query.
 *
 * 2. **The Folders sidebar's item-count badge can be off by ±1 from the true
 *    card count, in both directions, for two different reasons — always
 *    verify against the actual rendered `[data-asset-id]` list, never trust
 *    the badge as final.** Confirmed twice this wave:
 *    - Sence 4 badge read 11, but only 9 cards had `kind:"video"` — the other
 *      2 had `kind:null, status:null` and their `textContent` read
 *      `"NSFW,,,Credits refundedOutput may contain sensitive content..."`.
 *      These are real failed generations (credits auto-refunded, no video
 *      output) that the badge counts but that produce nothing to collect.
 *    - Sence 2 badge read 11, Sence 8 badge read 6, but both folders' actual
 *      card grids — fully scrolled to a stable `scrollHeight`, confirmed
 *      twice — held only 10 and 5 completed video cards respectively, with
 *      no NSFW/failed card anywhere accounting for the gap. This is simple
 *      badge staleness, not a hidden item; the card grid is ground truth.
 *
 * 3. **A project-folder URL
 *    (`.../folders/<folder-uuid>`) loaded via a full `navigate()` call takes
 *    3-4x longer to hydrate its card grid than the initial project page
 *    load** — `[data-asset-id]` queried immediately after `navigate()`
 *    returns 0 consistently; a first wait of ~4.5s then a second wait of
 *    ~2.5s (~7s total) was reliably enough across 6 different folders this
 *    wave, a single ~3s wait was not. `history.pushState` + a synthetic
 *    `popstate` event does NOT trigger this app's client-side router at
 *    all (URL bar changes, content never does) — always use a real
 *    `navigate()` call to move between folders, one per folder.
 *
 * 4. **Folder ids are static per scene and can be read once, then reused
 *    directly as navigation targets** — `[data-project-folder-row]` in the
 *    sidebar carries `data-folder-id`, giving every Sence-N folder's uuid in
 *    a single query on the project root page. No need to click through the
 *    sidebar per scene; construct
 *    `.../generate/@<org>/<project>/folders/<folder-id>` directly and
 *    `navigate()` straight to it.
 *
 * 5. **Per-card resolution is not exposed as page text or a simple DOM
 *    attribute** — `videoWidth`/`videoHeight` on the `<video>` element stay
 *    at 0 even after a real `mouseover`+`mousemove`+wait, because the video
 *    doesn't actually start loading/playing from a synthetic hover alone.
 *    Cheapest reliable read: right-click (or click a card's hover-revealed
 *    "..." button) → **Download** from the context menu (present, safe,
 *    completely separate from Rerun/Generate — confirmed on every card this
 *    wave), then `ffprobe -show_entries stream=width,height,duration` on the
 *    file that lands in `~/Downloads`. This also naturally fits the
 *    existing "download the gap, then file it" step, so it costs nothing
 *    extra when a gap clip needs downloading anyway.
 *
 * 6. **This project's "1080p" and "720p" filing tiers are NOT literal
 *    1920x1080 / 1280x720 — they're a widescreen ~2.33:1 crop, and the tier
 *    is decided by total pixel AREA, not either dimension alone.** Measured
 *    this wave: 1080p-tier clips read exactly 2206x946 (area 2,086,876 ≈
 *    1920x1080's 2,073,600); a 720p-tier clip read 1470x630 (area 926,100 ≈
 *    1280x720's 921,600). Both are close enough to their standard tier's
 *    area to classify confidently; use area-vs-standard-tier as the
 *    discriminator, not raw width/height matching.
 *
 * 7. **A card can be `1440x1440` (perfect square) sitting in an otherwise
 *    all-widescreen scene folder, at 1080p-tier file size (64MB).** This is
 *    a real anomaly, not a heuristic edge case — every other clip in the
 *    entire S1-S8 span this wave and every prior wave was ~2.33:1
 *    widescreen. Filed the other 3 gap clips found this wave straight
 *    through (matches established SX/SX-1080P routing), but held this one
 *    back locally and flagged it for the CTO/CEO rather than silently
 *    filing it as ordinary b-roll — square-aspect output in a cinema project
 *    is exactly the kind of scope surprise the skill says stays a C-level
 *    call, not an operator guess.
 *
 * 8. **A missing sibling `SX-1080P` Drive folder is not itself proof no
 *    1080p footage exists for that scene** — it may just mean nothing has
 *    been reconciled from Higgsfield into it yet. Confirmed this wave: S2
 *    had no `S2-1080P` folder at all going in (per the known-state table),
 *    but Higgsfield held two genuinely-1080p-tier S2 clips Drive had never
 *    received. Created `S2-1080P` fresh via `gdrive_move.py create_folder`,
 *    matching the exact naming convention of the pre-existing `S1-1080P`,
 *    before filing into it.
 *
 * Wave 13 findings (task-aa979737, 2026-08-15, single 10-element Seedance 2.5
 * generation for Scene 10-D — the CEO's own `Sence 10-D` project-folder
 * composer, `.../folders/e6664811-871d-4c18-b344-37e0a8c5e47f`):
 *
 * 1. **The Cinema Studio composer can be sitting in Image mode on page load
 *    even when arriving straight at a Video-history folder** — this folder's
 *    composer loaded with `GPT Image 2 | Auto | Medium | 1K | 4/4 | Unlimited`
 *    as the settings row, i.e. the Image tab was selected, not Video. Always
 *    read the settings row text before touching anything; if it shows an
 *    image model, click the Video tab (see finding 2) before proceeding —
 *    don't assume Video is the default just because the folder is full of
 *    video cards.
 *
 * 2. **The visible Image/Video mode-tab pair is stacked VERTICALLY** at the
 *    bottom-left of the composer (`Image` above `Video`, each a 64x52 css-px
 *    button), not side by side — and there is a second, invisible/zero-size
 *    Image/Video pair elsewhere in the DOM with an *opposite* aria-selected
 *    state to the real one. Filter to `getBoundingClientRect().width > 0`
 *    before trusting any aria-selected read, exactly as Wave 7 finding 3
 *    already established for the decoy prompt editor — this is the same
 *    "two lookalike elements, only one real" trap recurring on a different
 *    control.
 *
 * 3. **`computer` click coordinates are in SCREENSHOT-pixel space, not CSS
 *    pixel space, confirmed directly this wave** — Wave 7 finding 7 said to
 *    apply the scale factor before clicking, but two clicks aimed straight at
 *    a `getBoundingClientRect()`-derived CSS coordinate (244,618 then
 *    276,644) both missed the Video tab entirely and did nothing, twice in a
 *    row. A screenshot was taken purely to visually locate the same button,
 *    and its raw pixel coordinates from the image (370,722) worked on the
 *    first attempt. Lesson: never pass a raw `getBoundingClientRect()` value
 *    straight to `computer` — always multiply by
 *    `screenshotWidth / window.innerWidth` first, or read the coordinate off
 *    an actual screenshot instead of trusting the math.
 *
 * 4. **A same-content-length paste can still desync on the FIRST submission
 *    of a scene, not only on a repeat** — Wave 7 finding 12 documented this
 *    failure mode ("Prompt > Instruction: Prompt is required" while the
 *    editor visibly holds full correct text) as showing up on a *second*
 *    consecutive submission specifically. Here it fired on the very first
 *    Generate click of a fresh paste into a fresh Video-mode composer, with
 *    `hfPromptDesynced()`'s placeholder-visible tell reading FALSE the whole
 *    time (not the usual tell). The only reliable signal was the real
 *    Toastify DOM node itself
 *    (`.Toastify__toast-container` containing "Prompt is required") — treat
 *    that toast as authoritative over the placeholder-visibility heuristic,
 *    which did not fire here. The documented fix (scrollIntoView, real
 *    click, real Space, real BackSpace) worked immediately: length went from
 *    3546→3547 raw chars (Lexical's own paragraph-newline rendering noise,
 *    confirmed byte-identical to the source prompt after
 *    `.replace(/\s+/g,' ')` normalization on both sides), and the retry
 *    Generate click produced a real "Generation started" toast with a new
 *    card immediately. Budget one retry for this exact sequence before
 *    treating a "Prompt is required" toast as anything worse than a form
 *    desync.
 *
 * 5. **10 distinct elements generated successfully on Seedance 2.5 with no
 *    ceiling error**, confirming the task brief's claim that Wave 7 finding
 *    11's "9-element working maximum" is a Seedance 2.0-only ceiling. Full
 *    10-chip prompt (`@Room-Clean @Room-Wreck @Room-DoorOut @Mother
 *    @Mother-Soul @Daughter @Prop-OldPhoto @Prop-Glass @Prop-Lamp
 *    @Prop-Handbag`) pasted clean into an editor with zero leftover chips,
 *    verified via `data-beautiful-mention` distinct-uuid count exactly as
 *    Wave 7 finding 2 recommends, and rendered on the first successful
 *    Generate click with no error of any kind.
 *
 * 6. **This project-folder composer's Generate button, once Unlimited is ON,
 *    relabels to a literal `UNLIMITED` all-caps button reading
 *    "UNLIMITED ✦ ~~140~~ 0"** — confirms Wave 7 finding 4's
 *    struck-through-plus-zero pattern exactly, and confirms it is the
 *    expected FREE state, not a rule violation, despite having visible
 *    digits on it. The task brief's literal "zero digits anywhere" wording
 *    predates this discovery; treat "original price struck through + 0
 *    effective" as the pass condition on this button, same as
 *    `hfReadPriceButton()` already encodes.
 *
 * 7. **A card's "..." (More actions) menu on this project-folder grid does
 *    NOT contain Download directly** — its full item list this wave was
 *    Open / Select / Extract start frame / Extract last frame / Recreate /
 *    Translate / Change voice / Virality predictor / Change Color Palette /
 *    Relight. Click **Open** to get the `[role="dialog"]` detail modal
 *    (Info/Edit/Comments tabs, Copy/Recreate/Reference/**Download** buttons)
 *    — same modal Wave 6 already documented reaching via the download-tray
 *    icon; "..." → Open is a second, equally reliable path to it. The detail
 *    modal's Info tab also has the resolution/duration/model text
 *    (`"720p"`, `"Seedance 2.5"`, `"20s"` markers) needed to confirm spec
 *    before downloading, so Open serves both checks in one click.
 *
 * 8. **Render time for this single generation: ~26.8 minutes** (Generate
 *    clicked 2026-08-15 15:27:02 UTC, card confirmed `data-asset-status:
 *    "completed"` at 15:53:51 UTC) — clicked during 15:27-15:54 UTC,
 *    outside the documented 01:00-07:00 UTC low-queue window, consistent
 *    with the render-time-tracks-Europe's-waking-hours finding (this run
 *    landed in the "stacked peak" 07:00-16:00 UTC band).
 *
 * 9. **Output measured 1470x630** (area 926,100, ≈720p standard area
 *    921,600 per Wave 12 finding 6's area-based classifier) — confirms the
 *    task brief's prediction that a 20s Seedance 2.5 render on this project
 *    comes out 720p-tier, routing to `S10` (not `S10-1080P`). ffprobe
 *    duration read 20.04s video / 20.06s audio, both audio+video streams
 *    present (Sound On setting held).
 *
 * Wave 14 findings (task-8b4212e8, 2026-08-16, "All assets" grid + Video type
 * filter — a THIRD DOM tree, distinct from `/ai/video` History and from a
 * Cinema Studio project-folder's card grid; collection/hash-audit only, no
 * generation):
 *
 * 1. **The project sidebar's "All assets" entry (`.../generate/@<org>/<project>`
 *    root, click the "All assets NNN" button under Folders) opens a grid whose
 *    scroll container is `hide-scrollbar min-h-0 min-w-0 flex-1
 *    overflow-x-hidden overflow-y-auto` — yet a third class fingerprint,
 *    distinct from both Wave 9's `flex-1 overflow-y-auto hide-scrollbar`
 *    project-folder grid and Wave 4's History container. Don't reuse either
 *    prior locator; match on this exact class string (or re-derive via the
 *    `scrollHeight>clientHeight` fallback both priors already use).
 *
 * 2. **This grid was NOT virtualized at 65 items** — `[data-asset-id]` count
 *    stayed at 65 across repeated `scrollTop = scrollHeight` calls (with a
 *    real `scroll` event dispatched), scrollHeight itself never grew, and
 *    `scrollTop` genuinely reached max (`scrollHeight - clientHeight`). All 65
 *    cards were already mounted on initial load. Contrast with Wave 9's
 *    History panel, which IS server-paginated and grows on scroll — check
 *    empirically per view rather than assuming either behavior.
 *
 * 3. **Type filter is under Filter → "All types" (a submenu, not a flat list)**
 *    — click Filter, then click the "All types" row itself (not a chevron) to
 *    expand Image/Video/PDF/TXT/MD/HTML/DOCX/PPTX checkboxes, then check
 *    Video. The result shows as a removable chip (`Video ✕`) in a second row
 *    below the toolbar, plus "Filter 1" on the button itself — both are cheap
 *    text/attribute reads to confirm the filter actually applied, no
 *    screenshot needed.
 *
 * 4. **Per-card checkbox selector on this grid**:
 *    `card.querySelector('button[role="checkbox"]')` — a `<button
 *    role="checkbox" class="peer checkbox checkbox-md ...">` nested inside
 *    each `[data-asset-id]` card. Real `.click()` on this exact element (not
 *    a generic `card.querySelector('button')`, which hits a different button —
 *    confirmed: that selector only ever selected 6/65 correctly, hitting
 *    whichever button happened to be first in DOM order per card) reliably
 *    toggled selection for all 65 cards in one JS loop, no hover-pairing
 *    needed (unlike Wave 8 finding 2's per-card hover-then-click recipe for
 *    the `/ai/video` History Grid view) — this grid's checkboxes are always in
 *    the DOM, just visually hidden until hover/selection-mode, and `.click()`
 *    fires their real handler regardless of visibility.
 *
 * 5. **One card can be genuinely un-selectable (no checkbox in its DOM at
 *    all) while several others render a checkbox but correspond to no
 *    downloadable file** — two different "nothing to collect" states, don't
 *    conflate them. This wave: 65 `[data-asset-id]` cards total, 59 with
 *    `data-asset-status="completed" data-tour-asset-kind="video"` (real,
 *    downloadable), 6 with `data-asset-status=null data-tour-asset-kind=null`.
 *    Of those 6, exactly 1 (the one showing a live spinner + Cancel button
 *    on-screen — genuinely still generating) had NO checkbox and so was
 *    naturally excluded from selection. The other 5 null-status cards DID
 *    still have a clickable checkbox and got selected along with the 59 real
 *    ones (64 selected total) — these are Wave 12 finding 2's "NSFW/failed,
 *    credits refunded, no video output" pattern recurring on a different
 *    view. Higgsfield's own bulk-download endpoint silently drops them:
 *    toolbar showed "64 selected" but the zip progress read "Zipping N/59
 *    files" from the start, and the finished zip had exactly 59 files whose
 *    embedded uuids matched the 59 `completed`-status cards 1:1. **This is
 *    not a broken/incomplete zip** (the task brief's stop condition for a
 *    "count mismatch") — it's the server correctly filtering non-existent
 *    files out of a selection that included some. Verify by comparing the
 *    zip's file count against the `data-asset-status==="completed"` count,
 *    not against the raw "N selected" toolbar number, before treating any
 *    gap as an incident.
 *
 * 6. **The bottom-toolbar "Download" button must be located by exact
 *    innerText match and `.click()`'d directly** —
 *    `[...document.querySelectorAll('button')].find(b => b.innerText.trim()
 *    === 'Download')` — same reliable-JS-click lesson as Wave 6 finding 7,
 *    now confirmed on this third UI too. A `find()`-tool ref for "Download
 *    button in bottom selection toolbar" resolved to the wrong element this
 *    wave (it landed on a per-card status-tag control instead — clicking it
 *    opened an unrelated "In progress / Needs review / Approved" status
 *    dropdown and silently cleared the whole selection). Don't trust a
 *    natural-language `find()` ref for a toolbar button when several
 *    similar-sounding controls exist on the same page; resolve by exact text
 *    match in JS instead, every time.
 *
 * 7. **Zip prep time scales with byte size, not just file count** — 59 files
 *    / ~1.94GB took ~50s server-side (two progress polls: "Zipping 6/59" at
 *    ~5s in, "Zipping 42/59" at ~25s in, "Download complete / 59 files
 *    zipped" by ~50s), well past Wave 5's "~15s for 45 files/~210MB"
 *    baseline — that batch was 1080p/20s clips at higher compression, this
 *    one mixed many 720p and a few 1080p-tier files at ~5-68MB each. Poll
 *    stable-file-size on `~/Downloads/*.zip` as documented; don't assume a
 *    fixed prep time from file count alone.
 *
 * 8. **`md5Checksum` IS available from `list`-style Drive reads, just not
 *    through this bridge's existing `listFolder` action** (that uses
 *    `DriveApp`, which has no md5Checksum getter). The task's own suggested
 *    fallback — call the Drive API directly with the same OAuth credentials
 *    `ilag_sync.py` already uses (`mooniex-claudeflow/.env`
 *    `GOOGLE_OAUTH_*` triple, refreshed via `oauth2.googleapis.com/token`) —
 *    worked cleanly: `files.list` with `fields=files(id,name,mimeType,size,
 *    md5Checksum)` returned a real md5 for all 105 files across all 17
 *    `All Scene/*` folders, zero missing. No fallback-to-size+name was
 *    needed this run. This is pure `Bash`/Python, zero browser cost — do it
 *    before or in parallel with any Higgsfield browser work, same as Wave 11
 *    finding 3's "Drive leg first" advice.
 *
 * Wave 15 findings (task-fa96e85e, 2026-08-16, Scene 16 coda generation —
 * this project's 4th iteration on this exact task after two prior runs
 * (GH #79 busy slot, GH #80 504 outage) and a third that timed out on a
 * 40min busy-slot wait plus a mid-wait tab hijack (GH #81); this run's job
 * was purely "check the slot is free and generate", no waiting needed):
 *
 * 1. **Generate from the Cinema Studio composer
 *    (`/generate/@<org>/<project>`), not `/ai/video`, hides the real
 *    Unlimited-mode toggle and Generate button behind an `overflow-x-auto`
 *    row that is narrower than its content** — the video-mode composer bar
 *    (`Seedance 2.5 | References | 21:9 | 720p | 20s | 1/4 | High | On |
 *    Unlimited [toggle]`) does not fit in the visible ~436px-wide flex
 *    container even at a maximized ~1440px window; the toggle and price sit
 *    ~280px past the clipped edge, `visibility: visible` in computed style
 *    but literally outside the scrollable ancestor's viewport, so a
 *    coordinate click or ref click on the DOM-reported rect silently
 *    no-ops (rect coords land behind an unrelated History thumbnail).
 *    **Fix**: walk up from the toggle to find the ancestor with
 *    `getComputedStyle(el).overflowX === 'auto'` and set its `scrollLeft =
 *    scrollWidth` before clicking; scroll back to 0 afterward to re-read
 *    the earlier fields (model/aspect/resolution/duration) for the
 *    pre-Generate spec check. This is a NEW decoy-shaped trap, distinct
 *    from the Lexical decoy-editor and decoy-Generate-button patterns
 *    already documented — same root cause class (an off-screen but
 *    "visible" element) but a horizontal-scroll clip this time, not a
 *    zero-size/portal decoy.
 *
 * 2. **The Video/Image mode switcher inside the composer is ALSO
 *    duplicated** — one pair of tabs at viewport (0,0) with
 *    `visibility:hidden` (a decoy, always mid-toggle-state garbage), a
 *    second real pair rendered inside the floating composer bar itself
 *    (bottom-left, small icon-label buttons literally captioned "Image" /
 *    "Video", not text tabs). `find()` for "Video tab" matched the decoy
 *    first attempt; the real switch only worked via a direct coordinate
 *    click on the visible icon-pair once the composer bar was actually
 *    screenshotted and located. When `[role="tab"]` queries return >2
 *    matches with duplicate text, screenshot once to find the *visually
 *    rendered* icon-button pair rather than iterating find()/ref clicks —
 *    cheaper than the 3-4 failed attempts this wave took.
 *
 * 3. **The Generate button's price text is genuinely absent from a plain
 *    `document.querySelectorAll('button')` sweep when the real button is
 *    mid-hydration or briefly detached** — `[data-tour-anchor=
 *    "tour-cinema-generate"]` matched only a zero-rect decoy
 *    (`GENERATE8045`, garbage concatenated digits, `visibility:hidden`)
 *    on two separate checks seconds apart. The reliable read was always a
 *    fresh `screenshot` + `zoom` on the button's own coordinates — for
 *    this specific control, visual confirmation beat every DOM-query
 *    variant tried (leaf-text search, `data-tour-anchor` selector,
 *    innerText regex). Budget a zoom for this every time; don't keep
 *    retrying JS selectors on it.
 *
 * 4. **Sidebar folder item counts (e.g. "Sence 16 1") do NOT live-update
 *    after a generation completes** — the count stayed frozen at the
 *    pre-generation value even after the new clip was confirmed complete
 *    (fresh tab, `All assets` 240→241, matching prompt/model/resolution in
 *    the card's own Info panel). Don't use the sidebar folder count as a
 *    completion signal; it's cosmetic/cached. `All assets NNN` at the top
 *    of the sidebar DID increment correctly and is the reliable proxy if a
 *    numeric check is wanted before opening the card itself.
 *
 * 5. **`@Tag` chip resolution confirmed working exactly as documented**:
 *    hand-typed first `@Motel-Stairs` → platform dropdown → click the
 *    "Locations" match → thumbnail chip appears above composer. Then
 *    Cmd+A/Delete clear → synthetic `ClipboardEvent` paste (text/plain
 *    only) of the full verbatim prompt (fetched byte-exact via a
 *    `base64`-encoded `Bash` extraction of the source markdown into the
 *    page via `atob()`, avoiding any manual retyping/transcription risk)
 *    → the two remaining inline `@Mother-Soul` / `@Daughter` tags
 *    auto-converted to chips with zero extra action. Final state: 3/3
 *    thumbnails attached, verified by screenshot per the task's explicit
 *    budget carve-out for this exact check. `innerText.length` after paste
 *    (6640) did not match the source string length (6611) — fully
 *    explained by Lexical inserting an extra `\n` per paragraph-boundary
 *    `<p>` block; per-tag occurrence counts (`@Motel-Stairs` x1,
 *    `@Mother-Soul` x7, `@Daughter` x6) and both `first80`/`last80`
 *    substrings matched the source exactly, confirming no truncation —
 *    don't treat a length mismatch alone as truncation evidence without
 *    checking whether it's just block-newline inflation.
 *
 * 6. **Render took ~31 minutes this run** (Generate clicked 08:21:23 UTC
 *    per the completed card's own `hf_<timestamp>` filename; spinner
 *    confirmed gone at 08:53:35 UTC on a fresh-tab re-check) — clicked at
 *    08:21 UTC, inside the documented 01:00-07:00 UTC low-queue window's
 *    tail edge but past its close, consistent with the render-time-tracks-
 *    Europe's-waking-hours finding (slightly slower than the 20-27min
 *    in-window baseline, nowhere near the 50min+/137min pathological
 *    readings from mid-day Europe).
 *
 * 7. **Output measured 1470x630 via ffprobe** (UI's own Info panel showed
 *    1344x576 for the "same" field — two different numbers for what the
 *    product surfaces as one "Size" value; trust ffprobe on the actual
 *    downloaded file, not the panel, when they disagree) — both are
 *    720p-tier by Wave 12's area classifier (1470×630=926,100 vs the
 *    720p-standard 921,600 reference area), confirming the task brief's
 *    prediction and routing to `S16` (not `S16-1080P`). 20.04s duration,
 *    24fps, h264, matches spec.
 *
 * 8. **`All Scene/S16` did not exist prior to this run** (confirmed via a
 *    fresh `files.list` query on the parent folder before creating
 *    anything, per the task's explicit "verify fresh" instruction) —
 *    created via `ilag_sync.ensure_folder('S16', folders, create=True)`
 *    rather than a raw Drive API POST (the raw POST attempt failed on
 *    `api()`'s actual signature, which takes `data: bytes` not `json:
 *    dict` — `ensure_folder` already handles the correct request shape
 *    and should be preferred over hand-rolling folder creation).
 */

// --- 1. Locate the History scroll container (right-hand panel, list view) ---
// It's identified by scrollHeight >> clientHeight (thousands of px of lazily
// rendered/paginated cards) plus an overflow-y-auto class. Measured
// 2026-08-11: this container's scrollHeight GROWS as you scroll toward the
// bottom (server-paginated, not just virtualized) — don't assume a fixed
// scrollHeight up front, re-read it after each scroll.
function hfGetHistoryContainer() {
  const all = [...document.querySelectorAll('*')];
  return all.find(e => e.scrollHeight > e.clientHeight + 5000 && (e.className + '').includes('overflow-y-auto'));
}

// Scroll the History list to a given offset and let lazy content render.
async function hfScrollHistory(scrollTop) {
  const c = hfGetHistoryContainer();
  if (!c) throw new Error('history container not found');
  c.scrollTop = scrollTop;
  c.dispatchEvent(new Event('scroll', { bubbles: true }));
  await new Promise(r => setTimeout(r, 500));
  return { scrollTop: c.scrollTop, scrollHeight: c.scrollHeight };
}

// Cheap fingerprint scan of currently-rendered cards (date + first ~90 chars
// of VISUAL) — use this instead of get_page_text when just checking what's
// rendered; get_page_text on this page returns thousands of tokens per call.
function hfFingerprintCards() {
  const c = hfGetHistoryContainer();
  const text = c.innerText;
  const cards = text.split(/\nSeedance 2\.5\n/);
  return cards.map(card => {
    const vIdx = card.indexOf('VISUAL');
    const dateMatch = card.match(/(August \d+, 2026)/);
    if (vIdx === -1) return null;
    const snippet = card.slice(vIdx + 7, vIdx + 7 + 90).replace(/\n/g, ' ').trim();
    return (dateMatch ? dateMatch[1] : '?') + ' | ' + snippet;
  }).filter(Boolean);
}

// Scan currently-mounted cards for ones matching a keyword regex, and report
// whether each match already has a jump-cut (Cut 1:) or is still a long-take.
// MUST be called in one shot (scroll, if needed, in the SAME call) — see
// Wave 4 finding 2 above on why scrollTop doesn't survive across calls.
function hfFindCardByKeyword(regex) {
  const c = hfGetHistoryContainer();
  const t = c.innerText;
  const cards = t.split(/\nSeedance 2\.5\n/);
  return cards
    .filter(card => regex.test(card))
    .map(card => ({
      isJumpCut: /Cut 1:/.test(card),
      date: (card.match(/(August \d+, 2026)/) || [null, '?'])[1],
      snippet: card.slice(0, 250).replace(/\n+/g, ' '),
    }));
}

// --- 2. The prompt editor (Lexical, contenteditable) ---
function hfPromptEditor() {
  return document.querySelector('[contenteditable="true"]');
}

function hfPromptIsEmpty() {
  const e = hfPromptEditor();
  return !!e && e.innerText.trim().length === 0;
}

// document.execCommand('selectAll')+execCommand('delete') does NOT reliably
// clear this Lexical editor: measured 2026-08-11, the paste that followed
// APPENDED after the untouched old content instead of replacing it
// (afterLength ≈ oldLength + newLength). The fix that worked: focus the
// editor via a real click, then a real Cmd+A keypress, then a real Delete
// keypress (dispatched by the driving tool's `computer` action, not JS) —
// confirm with hfPromptIsEmpty() before pasting.

// --- 3. Synthetic paste — text/plain ONLY (Hard Rule 5) ---
// Also setting text/html causes Lexical to insert the content twice.
async function hfSetPromptText(promptText) {
  const e = hfPromptEditor();
  if (!e) throw new Error('prompt editor not found');
  if (!hfPromptIsEmpty()) {
    throw new Error('editor not empty — clear it first with a real Cmd/Ctrl+A + Delete keypress');
  }
  e.focus();
  const dt = new DataTransfer();
  dt.setData('text/plain', promptText);
  const pasteEvent = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
  e.dispatchEvent(pasteEvent);
  await new Promise(r => setTimeout(r, 500));
  const got = e.innerText;
  const cutCount = (got.match(/Cut \d:/g) || []).length;
  return { length: got.length, expectedLength: promptText.length, cutCount };
}

// --- 4. Generate button state — read before every click, but a DOM text
// read is a pre-check only. Hard Rule 3 requires a zoom-screenshot of the
// actual rendered button immediately before every single click, no exceptions.
function hfGetGenerateButton() {
  return [...document.querySelectorAll('button')].find(b => /generate/i.test(b.innerText));
}

function hfVerifyGenerateReady() {
  const btn = hfGetGenerateButton();
  if (!btn) return { ready: false, reason: 'button not found' };
  const text = btn.innerText;
  return { ready: !/\d/.test(text), buttonText: text };
}

// --- 5. Unlimited mode toggle ---
// Measured 2026-08-11: defaults OFF on a fresh Recreate load even mid-session
// — always check and toggle before every generation, never assume it stuck
// from the last scene.
function hfGetUnlimitedToggle() {
  const label = [...document.querySelectorAll('*')]
    .find(e => e.textContent.trim() === 'Unlimited mode' && e.children.length === 0);
  if (!label) return null;
  let el = label;
  for (let i = 0; i < 5 && el; i++) {
    el = el.parentElement;
    const sw = el.querySelector('[role="switch"]');
    if (sw) return sw;
  }
  return null;
}

function hfIsUnlimitedOn() {
  const sw = hfGetUnlimitedToggle();
  return sw ? sw.getAttribute('aria-checked') === 'true' : null;
}

// --- 6. Poll for completion ---
// A generation in flight shows "Processing"/"Generating" somewhere on the
// page. Absence of that text means idle — the calling agent should still
// confirm the specific History card shows 720p/20.0s/21:9 metadata with no
// in-flight state before treating it as genuinely done.
function hfPollStatus() {
  return /Processing|Generating/i.test(document.body.innerText) ? 'processing' : 'done-or-idle';
}

// --- 7. Cinema Studio composer helpers (Wave 7) ---

// The real editor, with the invisible decoy filtered out.
function hfVisibleEditor() {
  return [...document.querySelectorAll('[contenteditable="true"]')]
    .filter(e => getComputedStyle(e).visibility !== 'hidden')[0];
}

// Distinct attached elements, counted by uuid attribute rather than by the
// visible label — a chip may render its uuid and still be properly attached.
function hfAttachedElements() {
  const ed = hfVisibleEditor();
  if (!ed) return null;
  const nodes = [...ed.querySelectorAll('[data-beautiful-mention]')];
  return {
    total: nodes.length,
    distinct: new Set(nodes.map(m => m.getAttribute('data-beautiful-mention'))).size,
    labels: [...new Set(nodes.map(m => m.textContent.trim()))],
  };
}

// Reads the action button whether it says Generate or Unlimited, and reports
// the effective (non-struck) price. free === true is the only safe state.
function hfReadPriceButton() {
  const btn = [...document.querySelectorAll('button')]
    .find(b => /generate|unlimited/i.test(b.textContent) && b.getBoundingClientRect().width > 100);
  if (!btn) return { found: false };
  const leaves = [...btn.querySelectorAll('*')].filter(s => !s.children.length && s.textContent.trim());
  const struck = leaves.filter(s => /line-through/.test(getComputedStyle(s).textDecorationLine || ''));
  const effective = leaves.filter(s => !struck.includes(s) && /\d/.test(s.textContent));
  const effText = effective.map(s => s.textContent.trim()).join('');
  return {
    found: true,
    label: btn.textContent.trim(),
    struckThrough: struck.map(s => s.textContent.trim()),
    effective: effText,
    free: effText === '' || Number(effText) === 0,
    disabled: btn.disabled,
  };
}

// The Unlimited switch starts off-screen / adjacent to Generate. Scroll its
// own container fully right so a real click cannot stray onto Generate.
// Returns viewport-relative css center; multiply by the screenshot scale
// factor (screenshotWidth / window.innerWidth) before clicking.
function hfRevealUnlimitedToggle() {
  const sw = document.querySelector('[role="switch"]');
  if (!sw) return null;
  let c = sw;
  for (let i = 0; i < 4 && c; i++) c = c.parentElement;
  if (c) c.scrollLeft = c.scrollWidth;
  const r = sw.getBoundingClientRect();
  return {
    checked: sw.getAttribute('aria-checked'),
    cssCenter: [Math.round(r.left + r.width / 2), Math.round(r.top + r.height / 2)],
    scale: 'multiply by screenshotWidth / window.innerWidth',
  };
}

// The paste-desync tell: the placeholder is visible while the editor holds
// text. If this returns true, Generate will be refused with "Prompt is
// required when no media is provided" — see Wave 7 finding 12 for the fix
// (scrollIntoView, real click, real Space then BackSpace).
function hfPromptDesynced() {
  const ed = hfVisibleEditor();
  if (!ed) return null;
  const hasText = ed.innerText.trim().length > 0;
  const placeholder = /Describe the (scene|video) you (imagine|want to create)/.test(document.body.innerText);
  return hasText && placeholder;
}

// Every gate that must pass in the same breath as the Generate click.
function hfPreflight(expectedLen, expectedElements) {
  const ed = hfVisibleEditor();
  const els = hfAttachedElements();
  const price = hfReadPriceButton();
  const sw = document.querySelector('[role="switch"]');
  const row = sw && sw.closest('.mt-auto');
  const text = ed ? ed.innerText : '';
  return {
    settings: row ? row.innerText.replace(/\n+/g, ' | ') : null,
    unlimitedOn: sw ? sw.getAttribute('aria-checked') === 'true' : null,
    elements: els,
    elementsOk: els && els.distinct === expectedElements,
    elementsUnderCap: !!(els && els.distinct <= 9),   // 10 = hard fail, see finding 11
    promptChars: text.length,
    startsUndefined: /^undefined/.test(text),
    desynced: hfPromptDesynced(),                     // true => Generate will be refused
    price,
    GO: !!(sw && sw.getAttribute('aria-checked') === 'true'
           && els && els.distinct === expectedElements
           && els.distinct <= 9
           && price.found && price.free && !price.disabled
           && !/^undefined/.test(text)
           && !hfPromptDesynced()),
  };
}

if (typeof module !== 'undefined') {
  module.exports = {
    hfGetHistoryContainer, hfScrollHistory, hfFingerprintCards,
    hfFindCardByKeyword,
    hfPromptEditor, hfPromptIsEmpty, hfSetPromptText,
    hfGetGenerateButton, hfVerifyGenerateReady,
    hfGetUnlimitedToggle, hfIsUnlimitedOn, hfPollStatus,
    hfVisibleEditor, hfAttachedElements, hfReadPriceButton,
    hfRevealUnlimitedToggle, hfPromptDesynced, hfPreflight,
  };
}

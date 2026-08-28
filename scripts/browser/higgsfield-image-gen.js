/**
 * scripts/browser/higgsfield-image-gen.js
 *
 * Replay notes for PAID Higgsfield image generation (GPT Image 2, Cinema
 * Studio project-folder composer, e.g. https://higgsfield.ai/generate/@<org>/<project>/folders/<uuid>).
 *
 * NOT a standalone Node/Playwright script — paste snippets into javascript_tool
 * against an already-open, already-logged-in tab via claude-in-chrome MCP.
 * This is the PAID-credit sibling of higgsfield-jumpcut-gen.js (which is
 * Unlimited-mode VIDEO on /ai/video History). Different surface, different
 * spec knobs, different cost model — do not conflate the two.
 *
 * Validated end-to-end task-7f79e45c (2026-08-19), 8/8 images, GPT Image 2 /
 * 1K / Medium / 4:3 / 1-per-gen, ~2 credits each, 16 credits total.
 *
 * Flow per image:
 *   1. Click into the visible (non-decoy) contenteditable, real Cmd+A + Delete
 *      TWICE (one pass often leaves 1 stray char/newline — verify innerText
 *      === 0 or 1 before trusting it's clear). A single click at a fixed
 *      coordinate can miss if the editor auto-scrolled from prior long text —
 *      focus it via JS (`el.focus()`) first if a raw-coordinate click doesn't
 *      register (verify `document.activeElement === el`).
 *   2. Synthetic ClipboardEvent paste, text/plain ONLY, onto the node where
 *      getComputedStyle(el).visibility !== 'hidden' (there are always two
 *      contenteditable nodes — one decoy, filter every time).
 *   3. Verify normalized length (whitespace-collapsed) matches source exactly,
 *      plus first/last 80 chars.
 *   4. PRE-EMPTIVELY apply the "Prompt is required" desync fix on every
 *      generation, not just after seeing the error: scrollIntoView({block:
 *      'center'}), a real click at the editor's on-screen center (convert
 *      css rect -> screenshot-px via screenshotWidth/innerWidth, measured
 *      ~1.342 this session), then a real Space keypress, then a real
 *      BackSpace keypress. Net text change is zero; it forces Lexical to
 *      bind to React state. This fired on attempt 1 of 8 in this run (image
 *      1) with the literal toast "Prompt: Prompt is required" and zero
 *      assets/credits consumed — cheap and reliable to always apply.
 *   5. Read the REAL (visible, width>0) Generate button's innerText via
 *      `[...document.querySelectorAll('button')].filter(b=>getComputedStyle(b)
 *      .visibility!=='hidden' && /generate|unlimited/i.test(b.innerText) &&
 *      b.getBoundingClientRect().width>0)` — there is a hidden decoy button
 *      too ("GENERATE8045"-style concatenated garbage). Confirm the price is
 *      in the authorized range before clicking (this task: 1-3 credits
 *      expected, >=5 = stop and ask).
 *   6. Click Generate via `find`/ref (not raw JS .click()) — real driving
 *      tool click, per existing convention for money-committing buttons.
 *   7. Verify it actually fired via `document.body.innerText.match(/All
 *      assets\s*\n?\d+/)` — cheapest reliable confirmation. The Toastify
 *      stack caps at ~4 visible "Generation started" toasts and silently
 *      drops older ones, so DON'T rely on toast count past image 4 — the
 *      "All assets N" sidebar counter has no such cap and increments once
 *      per successful Generate, confirmed 38->46 across 8 clicks.
 *
 * Composer settings gotchas specific to this project-folder composer:
 *   - Defaults on fresh load are 2K/High (NOT the target 1K/Medium) — always
 *     click the quality pill ("High") then pick from the Low/Medium/High
 *     dropdown, then the resolution pill ("2K") then pick from 1K/2K/4K.
 *     Generate button price updates live as you change these (7 -> 3 -> 2
 *     credits observed for High/2K -> Medium/2K -> Medium/1K at 4:3).
 *   - Settings (model/quality/resolution/aspect/count) PERSIST across
 *     in-project folder navigation (confirmed Location -> Prop kept
 *     Medium/1K/4:3). Prompt TEXT also persists via localStorage-style
 *     autosave — the Prop-folder composer arrived pre-loaded with the last
 *     Location prompt's tail text. Always clear before pasting on a fresh
 *     folder nav, don't assume blank.
 *   - A full clear-then-repaste that leaves stale trailing text is a real
 *     failure mode, not just a paranoia check: on image 8 here, a paste
 *     landed on top of un-cleared image-7 leftover text because the prior
 *     clear's click missed the (scrolled) editor. innerText length was 3803
 *     instead of the expected 2127 — caught by the length-vs-source check in
 *     step 3, NOT by eyeballing the screenshot. Always diff normalized
 *     length against source before trusting a paste, even on a "should be
 *     empty" composer.
 *
 * Attaching an existing Element reference (e.g. @project_valder_prop_signature):
 *   - No manual @-picker interaction needed. If the prompt TEXT itself
 *     contains the literal "@ElementName" string and that name matches a
 *     real project Element, pasting the prompt auto-converts it into a bound
 *     mention chip (data-beautiful-mention attribute = the element's UUID,
 *     matches Wave 7 finding 2 in higgsfield-jumpcut-gen.js). Verify via:
 *       [...editor.querySelectorAll('[data-beautiful-mention]')]
 *         .map(m => m.getAttribute('data-beautiful-mention'))
 *     Confirmed here: two literal "@project_valder_prop_signature" occurrences
 *     in one prompt both resolved to the SAME uuid
 *     (1bd0abb5-5872-437d-84dc-e84dbb28e358), matching the task brief's
 *     pre-stated UUID exactly — a strong sanity check worth running whenever
 *     a task hands you an expected UUID.
 *   - The reference tray thumbnail above the composer (separate from the
 *     text editor) can persist a prior attachment even after the editor TEXT
 *     is cleared — don't assume "empty text box" means "no reference
 *     attached". Check both independently if the task cares about exactly
 *     which references are attached at Generate time.
 *
 * Verifying which generated card is which, after firing several in a row
 * with no manual per-card check:
 *   - Query `[data-asset-id]` cards in the target folder, extract each
 *     card's `<img>`/`<video>` src timestamp via
 *     `src.match(/hf_(\d{8}_\d{6})_/)` (UTC, `YYYYMMDD_HHMMSS`). Sort
 *     ascending — this is a reliable proxy for fire order when N prompts
 *     were pasted+generated back-to-back with no other account activity in
 *     the window. Cross-check against the "All assets" delta (N new cards
 *     should appear) before trusting the mapping.
 *   - This is index-based inference, not a per-card content read — good
 *     enough when the count/delta evidence is unambiguous (single operator,
 *     contiguous timestamps, no gaps), but do a spot-open (click card ->
 *     `[role="dialog"]` -> Info tab) on at least one card if the task is
 *     high-stakes about exact identity.
 *
 * Credit ledger check (paid mode, NOT Unlimited):
 *   - Account menu (avatar, top-right) -> "Credits" row reads "N,NNN left".
 *     This is a simple balance, not a transaction log — read it once before
 *     the wave and once after; delta should equal
 *     (num_generations * price_per_generation) shown on the Generate button.
 *   - /account/usage and /settings both 404 on this account — there is no
 *     direct URL to a itemized usage-history page from outside the app UI;
 *     use the credits-left delta instead of trying to find a ledger page.
 *
 * Wave 2 (task-a8e1588b, 2026-08-19): single storyboard image (3x3 grid, 9
 * panels), same folder/project, 4:3/Medium/1K, 1 image, 2 credits, balance
 * 3,047 -> 3,045.
 *   - The FIRST TWO Generate clicks (both a `find`-ref click and a verified
 *     coordinate click landing exactly on the button via elementFromPoint)
 *     silently did nothing: no toast, no credit deduction, no asset-count
 *     change, button stayed enabled and un-disabled. This happened even
 *     though the preemptive desync fix (per the "Prompt is required" note
 *     above) had already been applied once, BEFORE those clicks.
 *   - Root cause: the fix's own click-to-focus step is unsafe when the
 *     prompt text contains resolved @mention chips — clicking inside the
 *     text at a fixed coordinate can land ON a mention chip instead of
 *     plain text, which opens a reference-preview overlay (URL gains
 *     `?preview=<uuid>`) instead of placing a cursor. The subsequent
 *     Space/BackSpace then applies to the wrong context and the desync
 *     fix never actually reaches the editor. No error surfaces — Generate
 *     just no-ops.
 *   - Fix: focus the editor via `el.focus()` and use the Selection API
 *     (`range.selectNodeContents(target); range.collapse(false)`) to place
 *     the cursor at the very end, instead of a coordinate click. Verify
 *     `document.activeElement === target` before sending the real
 *     Space/BackSpace key presses. This landed on the first attempt.
 *   - Verify a Generate click actually fired by reading for the literal
 *     "Generation started" toast text in `document.body.innerText`
 *     immediately (same call) after the click — cheaper and faster than
 *     polling the "All assets" counter, which lagged ~20s behind the
 *     toast in this run.
 *   - Reference tray: with 8 unique `@project_*` mentions in the prompt,
 *     the composer showed exactly 8 small thumbnail chips above the text
 *     box once populated (not visible on an empty composer) — cross-check
 *     `[...editor.querySelectorAll('[data-beautiful-mention]')]` unique
 *     values against this tray for a double confirmation of reference
 *     count, since the task brief calls this out as a stop-and-ask gate.
 *   - Card marking affordances (hover icons on a folder-grid thumbnail,
 *     top-right corner, top to bottom): heart = "Like", down-arrow =
 *     "Download", the copy-style icon = **"Recreate"** (the icon shape
 *     alone gives no hint it's the banned action — always hover for the
 *     tooltip text before clicking any icon in that stack), image icon =
 *     "Reference", "..." = more options (no tooltip observed, opens a
 *     menu). Never used the Like affordance in this run (observe-only
 *     per task), so whether a liked card is visually distinguishable in
 *     grid view at a glance is unconfirmed — someone will need to click
 *     Like once and screenshot the grid to answer that.
 *
 * Wave 3 (task-a8e1588b reshoot, 2026-08-19): same folder, full prompt
 * replaced fresh (not patched), 1 image, 2 credits, balance 3,045 -> 3,043.
 *   - The Wave 2 desync fix (focus + Selection API cursor-to-end, then real
 *     Space/BackSpace) is NOT durable across multiple Generate clicks on the
 *     same composer state. Applied once, then two consecutive real-clicks
 *     on the (correctly located, non-disabled, unobstructed — verified via
 *     `elementFromPoint`) Generate button both silently no-op'd (no toast,
 *     no credit change, no asset-count change). Re-applying the exact same
 *     focus+Selection+Space+BackSpace fix immediately before the THIRD
 *     click made that click fire correctly ("Generation started" toast,
 *     credits deducted, asset count incremented). Conclusion: re-apply the
 *     fix fresh immediately before every single Generate click, not just
 *     once per composer session — treat it as cheap and mandatory, not a
 *     one-time unlock. Verify success per-click by reading for the literal
 *     "Generation started" string right after each click, and if it's
 *     absent, do not assume the click "will probably still work" — reapply
 *     the fix and click again (each no-op click in this run was confirmed
 *     zero-cost via the credits-left delta before retrying).
 *   - Settings (model/aspect/quality/resolution) persisted correctly across
 *     a full page `navigate()` back into the same project folder in this
 *     run — contradicts the general "navigate() resets to Auto/High/2K"
 *     warning elsewhere in this repo; that warning may be specific to a
 *     fresh session/cache state rather than true on every navigate. Verify
 *     the composer bar's actual displayed values every time regardless —
 *     it happened to already read 4:3/Medium/1K/GENERATE-2 unprompted here.
 *   - Opening a card by clicking near its top-left corner can land on the
 *     selection checkbox instead of opening the detail panel, dropping you
 *     into folder-grid bulk-select mode (a toolbar with Download/Publish
 *     all/Move to/Copy to/Like/X appears). Click nearer the visual center
 *     of the thumbnail, and if the bulk toolbar appears, click its trailing
 *     "X" to exit multi-select before doing anything else — don't click
 *     Download/Publish/Move/Copy while N cards are selected by accident.
 *
 * Wave 4 (task-6ec7fbdd, 2026-08-20): same folder, single storyboard image
 * (3x3 grid, 9 panels, revised camera/planting brief), 4:3/Medium/1K, 1
 * image, 2 credits, balance 3,037 -> 3,035.
 *   - Composer loaded in VIDEO mode by default (1080p/16:9/5s/Cinema Studio
 *     4.0), not Image mode — this project folder's composer does not persist
 *     the Image/Video toggle the way it persists model/quality/res/aspect
 *     within a mode. The top-nav "Image" tab (`find` matched a `tab` role
 *     element) did NOT switch modes when clicked — the composer bar kept
 *     showing video settings after that click. What worked: click the
 *     bottom-left composer icon pair (small "Image"/"Video" stacked buttons
 *     directly above the settings pills, not the top-nav text tabs) —
 *     confirmed by the button list flipping from
 *     {Cinema Studio 4.0, 1080p, 16:9, 5s, On} to {GPT Image 2, Auto, High,
 *     2K}. Always verify by re-reading the button list after clicking,
 *     don't trust the click succeeded from intent alone.
 *   - Quality/Resolution dropdown pills (`find` by text) intermittently
 *     failed to locate the currently-showing pill by natural-language query
 *     even though the same text was present in a direct
 *     `querySelectorAll('button')` scan seconds earlier — `find`'s
 *     accessibility-tree snapshot can lag a live re-render. When `find`
 *     returns "no matching element" for something you can see in a JS
 *     button-text dump, fall back to a direct coordinate click on the pill
 *     (read its rect from the JS scan first) rather than retrying `find`.
 *   - The desync fix (focus + Selection API cursor-to-end + real
 *     Space/BackSpace, applied once immediately before the click) was
 *     sufficient on the FIRST Generate click this run — no repeat-click
 *     no-op cycle like Wave 2/3. Re-verify per-run rather than assuming
 *     Wave 2/3's "always needs 2-3 tries" — this one didn't.
 *   - Reference-count double-check done two ways: (a) unique
 *     `data-beautiful-mention` values in the editor (8), (b) reference tray
 *     thumbnail chip count read via `zoom` on the composer's chip row (8,
 *     visually counted) — both agreed with the task's stated "Expected
 *     reference thumbnails: 8".
 *   - Identifying the just-generated card: `[data-asset-id]` is
 *     viewport-virtualized — only ~7 cards exist in the DOM at once
 *     regardless of "All assets" total. Scrolling the folder-grid
 *     scroll-container to `scrollTop = 0` (found via `scrollHeight >
 *     clientHeight` heuristic) brought the new card into the DOM at index 0.
 *     A second "new-looking" id at index 1 was NOT a second generation — it
 *     was a pre-existing hidden/eye-off asset that had already been sitting
 *     in slot 0 before this run and got pushed to slot 1. Don't assume N
 *     unfamiliar ids after one Generate means N new assets; cross-check
 *     against the "All assets" delta (74 -> 75, i.e. exactly one) before
 *     concluding which id is actually new.
 *   - The card thumbnail in the grid renders small enough that
 *     panel-by-panel judgment (boy/photographer/guard placement, panel-6
 *     wall-of-arms coverage) is not reliable at grid scale. Opening the
 *     card (click center of thumbnail, not its top-left corner) and then
 *     clicking the fullscreen/expand icon (bottom-right of the detail
 *     panel, distinct from "Turn to video", "Recreate" and "Reference" —
 *     do not click those) gives a large enough render to judge each of the
 *     9 panels individually via `zoom` on sub-quadrants.
 * Wave 4 (task-4c966d36, 2026-08-19): two independent single-image storyboards
 * (two separate 3x3-grid boards, same folder), 4:3/Medium/1K, 1 image each,
 * 2 credits each, balance 3,041 -> 3,039 -> 3,037.
 *   - Opening the account avatar menu to read the credit balance, then
 *     pressing Escape to close it, once destroyed the entire MCP tab group
 *     (`tabs_context_mcp` came back "No tab group exists for this session")
 *     even though the tab had real content open and nothing else unusual had
 *     happened. Recreating the group (`createIfEmpty: true`), re-navigating
 *     to the same folder URL, and re-verifying settings recovered cleanly —
 *     but it cost a full settings re-check. A second Escape later in the same
 *     run (closing a toast) did NOT reproduce this, so it's not "Escape is
 *     unsafe" in general — treat any post-Escape action as needing a fresh
 *     `tabs_context_mcp` check before trusting the old tabId.
 *   - After that forced re-navigate, the composer silently came back in
 *     VIDEO mode (Cinema Studio 4.0 / 1080p / 16:9 / 5s) even though this
 *     folder's last-used mode was Image — the two modes' settings persist
 *     independently. Click the "Image" icon in the bottom-left composer mode
 *     switcher before touching anything else; once back in Image mode, the
 *     prior 4:3/Medium/1K/qty-1 settings were still there untouched.
 *   - The hidden decoy Generate button's `innerText` isn't a static garbage
 *     string — it showed live-looking concatenated numbers like
 *     `"GENERATE\n80\n45"` at one point (i.e. it can look like a plausible
 *     price if you only regex for `/generate/i` without also filtering
 *     `b.offsetParent` truthy / `visibility==='visible'`). Filtering on both
 *     visibility AND offsetParent (not just width>0) reliably isolated the
 *     one real button in every check this run.
 *   - Credit-balance delta matched the Generate button's stated price exactly
 *     on both generations (2 credits each, confirmed via account-menu "N
 *     left" text before/after) — this remains a trustworthy verification
 *     path, cheap via `javascript_tool` regex on `document.body.innerText`.
 *   - Chat-relayed "task amendments" arriving mid-session (not in the
 *     original TASK.md) should be verified against the actual TASK.md file
 *     before being treated as authoritative, especially if they claim their
 *     own text is written into that file — re-reading the file is a cheap,
 *     conclusive check when a claim like that is checkable.
 *
 * Wave 5 (task-4c966d36 reshoot, 2026-08-20): 8-reference reshoot of a
 * previously-successful board (same folder), 4:3/Medium/1K, 1 image, 2
 * credits SPENT even though the generation was safety-flagged (balance
 * 3,037 -> 3,035, no refund observed).
 *   - A flagged/rejected generation is NOT visually obvious from a plain
 *     screenshot at rest — the card shows a solid near-black thumbnail with
 *     a subtle reddish top-edge glow and a small eye-slash + (i) icon pair
 *     that, unlike every other card's hover-only action stack, stays
 *     rendered even when the mouse is elsewhere on the page. That
 *     persistence (icons visible with cursor hovered somewhere else
 *     entirely) is the tell that distinguishes "still rendering" (plain
 *     dark placeholder + spinner, no icons) from "flagged" (dark
 *     placeholder + persistent eye-slash/info icons, no spinner).
 *   - Cheapest conclusive check, no screenshots needed: query the card's
 *     subtree for any element whose `title` attribute matches the flag
 *     text. Confirmed exact string on this run:
 *       [...card.querySelectorAll('[title]')].map(e=>e.title)
 *       // -> "Content was flagged by the safety system. Try different
 *       //     prompts or inputs." (on an <h2> inside the card, not on the
 *       //     eye-slash icon itself)
 *     `card.querySelector('img,video')` also flips from absent to present
 *     once ANY terminal state (success OR flag) is reached, so `hasImg`
 *     alone can't distinguish flagged-with-placeholder from rendered — the
 *     title-text check is the reliable one.
 *   - Clicking near a card's top-left corner to inspect it (same trap noted
 *     in Wave 3) toggled its selection checkbox on this flagged card too —
 *     confirm the checkbox is unchecked again before navigating away, since
 *     a lingering multi-select changes what a later bulk action would hit.
 *   - Per this project's TASK.md STOP conditions, a flagged card is a stop-
 *     and-report situation, not a re-roll situation — re-rolling is only
 *     authorised for objective visual defects in a rendered image, and this
 *     never rendered at all. Did not click the eye-slash "reveal" toggle or
 *     attempt a same-prompt retry; reported the exact flag string and the
 *     credit spend to the CTO and stopped.
 *
 * Wave 6 (task-7266495c, 2026-08-20): The Valder Collection No.7 project
 * TOP-LEVEL page (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3,
 * no /folders/<uuid> segment) rather than a specific folder composer, then
 * clicked into the Location folder from there. Blocked before any credit
 * spend — two Generate clicks, both silent no-ops.
 *   - The Image/Video mode toggle on this composer did NOT respond to a real
 *     `computer` left_click at the button's own on-screen center coordinates
 *     (verified correct via `elementFromPoint` at that exact point) — tried
 *     twice, `data-state` stayed "inactive" on Image / "active" on Video both
 *     times. A raw `el.click()` via JS also did nothing. What worked: a full
 *     synthetic PointerEvent sequence (pointerdown, mousedown, pointerup,
 *     mouseup, click, in that order, all bubbles:true/cancelable:true, with
 *     clientX/clientY at the button's rect center) dispatched via
 *     `javascript_tool`. This toggle is a plain UI mode switch (not a
 *     money-committing control), so a JS-dispatched event sequence here does
 *     not conflict with the "real driving click on Generate" rule — reserve
 *     that rule for the priced button itself.
 *   - Once in Image mode, composer settings had already persisted from a
 *     prior session as GPT Image 2 / 4:3 / Medium / 1K / GENERATE-2 with zero
 *     manual pill changes needed — confirms Wave 4's "settings persist
 *     independently per mode" finding again.
 *   - Paste + normalized-length verification (whitespace collapsed, trailing
 *     `\n` from Lexical's per-blank-line empty `<p>` elements ignored) matched
 *     the source exactly (3081 chars, first/last 80 identical) both before
 *     and after the desync fix, on both attempts.
 *   - THE NEW FAILURE MODE: two consecutive real `computer` left_clicks on
 *     the verified (elementFromPoint-confirmed, non-disabled, width>0)
 *     Generate button, each preceded by a freshly re-applied desync fix
 *     (focus + Selection-API cursor-to-end + real Space + real BackSpace,
 *     exactly per the Wave 2/3 recipe), both silently no-op'd: no
 *     "Generation started" toast, "All assets" stayed at 99 both times,
 *     button never disabled. This is a full escalation beyond Wave 3's
 *     "worked on the 3rd try" case — 2/2 clean attempts failed here. Credit
 *     balance read afterward via the account-avatar menu was 2,700 (closed
 *     the menu with a click elsewhere on the page, NOT Escape, per the Wave 4
 *     tab-group-destruction warning) — no way to confirm a pre-click
 *     baseline, but zero visible side effects on both clicks is consistent
 *     with zero-cost no-ops, not a race against a delayed toast.
 *   - Per this task's explicit STOP rule ("more than one clean attempt...
 *     do not retry with a different click technique near a priced Generate
 *     button"), stopped after the 2nd no-op rather than trying a 3rd
 *     variation (e.g. `find`-ref click, coordinate offset, longer wait
 *     between desync-fix and click). Composer state was left untouched:
 *     prompt still pasted and verified, settings still GPT Image
 *     2/4:3/Medium/1K/2-credits, tab group still alive. Whoever resumes this
 *     should re-verify the button price and re-apply the desync fix
 *     immediately before their own first click — do not assume this run's
 *     verification is still valid after any delay.
 *
 * Wave 7 (task-7266495c continued, 2026-08-20): CEO/CTO said "restart Chrome
 * and try one more time" after Wave 6's blocker. Did a full `osascript quit
 * app "Google Chrome"` + `open -a "Google Chrome"`, waited for the extension
 * to reconnect (took ~15s total), opened a brand-new tab, navigated fresh to
 * the same project URL, clicked into Location folder again (this time it DID
 * produce a real `/folders/<uuid>` URL, unlike Wave 6 where the same click
 * left the URL unchanged — inconsistent SPA routing behavior on this
 * composer, note for future runs). Composer defaulted to Video mode again on
 * this fresh folder load (Wave 4's per-mode-independent-persistence finding
 * holds), AND this time Image mode's own settings had NOT persisted either
 * (came up Auto/High/2K/GENERATE-7, not the previously-seen Medium/1K/2 —
 * contradicts earlier waves' "settings persist" finding; a full Chrome
 * restart apparently does reset them, unlike an in-app navigate()).
 *   - Manually rebuilt all four settings via the aspect/quality/resolution
 *     pills (Auto->4:3, High->Medium, 2K->1K), landing back on GENERATE-2.
 *     Each pill required the same synthetic PointerEvent sequence as the
 *     mode toggle — a plain `computer` click opened nothing for the Auto
 *     pill on the first attempt (dropdown never appeared), the PointerEvent
 *     sequence via `javascript_tool` worked every time it was tried. Given
 *     Wave 6 also needed this for the mode toggle, this composer may
 *     categorically not respond to whatever click delivery `computer`
 *     produces on this account/machine right now — worth testing a plain
 *     `computer` click against something innocuous (not Generate) at the
 *     start of a future run to characterize this before touching the
 *     composer at all.
 *   - Pasted + verified the prompt fresh (normalized 3081 chars, exact match,
 *     0 mentions), re-applied the desync fix (focus + Selection API +
 *     real Space/BackSpace via `computer`), confirmed button text
 *     "GENERATE\n2", not disabled, `elementFromPoint` confirmed unobstructed.
 *   - Clicked Generate via `computer` left_click (a REAL click, not a
 *     JS-dispatched one) at the verified coordinate. Silent no-op again:
 *     "All assets" stayed 99, no toast, button unchanged. This is the same
 *     failure as Wave 6, now reproduced on a genuinely fresh browser
 *     process, fresh tab, fresh navigation, fresh paste, fresh settings
 *     rebuild — rules out "stale session/tab" as the cause.
 *   - Stopped WITHOUT a second click this time (Wave 6 had already spent
 *     its "one more clean attempt" budget across both waves combined — 3
 *     real clicks total on a priced Generate button with zero effect).
 *     Attached temporary click/pointerdown listeners to the button as a
 *     read-only diagnostic (to check whether a real click even dispatches
 *     to the button at all) but deliberately did NOT click again to trigger
 *     them, since that click would itself be a 4th attempt on the priced
 *     button — removed the listeners unused rather than risk it.
 *   - CONCLUSION for next operator: this looks like a genuine site-side
 *     issue (event handlers not binding, or some other backend-side gate)
 *     rather than anything fixable by browser-side technique — two
 *     different browser processes, on two different composer instances
 *     (top-level-page-then-folder-click vs fresh-folder-URL-load), both
 *     with correctly verified text/settings/price, produced the identical
 *     silent no-op. Recommend a human (CEO/CTO) drive this exact button by
 *     hand once to see whether it fires for a real mouse, or check
 *     Higgsfield's own status/support channel, before spending further
 *     agent attempts here.
 *
 * Wave 8 (task-b691b231, 2026-08-26): first plates for a NEW project,
 * "Feed Them, Feed Me" (ai-film-festival-2, NOT ai-film-festival-3/Valder).
 * 25 total generations attempted (20 successful paid, 1 flagged/refunded,
 * plus 4 folder-navigation settings resets fixed inline), 40 credits spent,
 * landing exactly on the task's hard cap.
 *   - Confirmed the standard flow (clear via real Cmd+A+Delete x2, synthetic
 *     text/plain-only ClipboardEvent paste, length+first/last-80-char verify,
 *     pre-emptive desync fix via focus+Selection-API-cursor-to-end+real
 *     Space+BackSpace, re-verify Generate button price fresh immediately
 *     before every click) works reliably across a long multi-folder,
 *     multi-amendment session — this is now well-trodden ground, not a new
 *     finding.
 *   - NEW FINDING — a "no-op" click can actually be a DELAYED success, not a
 *     true no-op: fired Generate for fish_c, waited ~2s, saw no toast and no
 *     asset-count change, concluded no-op, re-clicked. The "All assets"
 *     counter then jumped by TWO (not one), and the credit-balance delta
 *     confirmed BOTH clicks had fired a real paid generation — the first
 *     click's result simply hadn't rendered yet at the 2s check. Produced an
 *     accidental duplicate of the same prompt (2 extra credits, disclosed to
 *     the CEO rather than hidden). Fix adopted for the rest of the session:
 *     wait at least 4-6s before deciding a click was a no-op, and treat the
 *     credit-balance delta (via the account-avatar menu, closed with a click
 *     elsewhere afterward — never Escape) as the authoritative signal, not
 *     the toast or the asset counter alone, whenever the budget is tight.
 *   - NEW FINDING — composer settings (quality/resolution/aspect, sometimes
 *     even the model) reset unpredictably on **every** folder navigation in
 *     this session, not just occasionally as earlier waves suggested. Some
 *     navigations kept GPT Image 2 but reset quality/resolution to
 *     Auto/High/2K; others reset the model back to the free default
 *     ("Higgsfield Soul Cinema") and the mode to Video. There is no way to
 *     predict which will happen — re-verify and re-set all four settings
 *     (mode, model, quality, resolution, plus aspect if using the sheet
 *     format) after every single folder navigate, with no exceptions.
 *   - NEW FINDING — quality/resolution/aspect dropdown pills frequently
 *     needed a SECOND click on the same coordinate to actually open (first
 *     click apparently just focuses/hovers without opening the popover on
 *     this account/session). If `[role="option"]` comes back empty
 *     immediately after a click on a pill whose text you can see, click the
 *     exact same coordinate again before trying a different technique —
 *     this alone resolved the great majority of "dropdown didn't open"
 *     cases this run, cheaper than switching to a synthetic-event fallback.
 *   - NEW FINDING — the Image/Video mode toggle button's on-screen position
 *     is NOT stable across page states in this project: observed at y=496,
 *     y=580, and y=636 for the same "Image" button in different loads of
 *     the same folder URL, all within one session. Always re-query
 *     `getBoundingClientRect()` immediately before this click; never reuse a
 *     coordinate from even a few calls earlier. When a real click still
 *     doesn't flip `data-state`, the synthetic pointerdown/mousedown/
 *     pointerup/mouseup/click MouseEvent sequence documented in Wave 6 fixed
 *     it every time it was tried again this run.
 *   - NEW FINDING — post-generation safety-flag cards on THIS account's UI
 *     variant do not expose the "warning triangle eligibility re-check"
 *     control described in some task briefs. The actual controls on a
 *     flagged card are: a selection checkbox (large hit-area, easy to
 *     trigger by clicking anywhere in the upper two-thirds of the card —
 *     confirm you didn't just multi-select before doing anything else),
 *     "Copy prompt", "Delete", and an NSFW visibility eye-slash toggle. No
 *     click on the card opens a detail/preview modal (there's no image to
 *     preview). The flag text itself
 *     ("Content was flagged by the safety system. Try different prompts or
 *     inputs.") and a "Credits refunded" badge are both present as plain
 *     text/badges on the card face, not gated behind any click. If a task's
 *     rules allow a retry on content refusal, the correct move is: confirm
 *     the refund via account-menu balance (not just the visible badge),
 *     soften the specific phrase in the prompt most likely to have
 *     triggered it, and paste + generate fresh — there is nothing to click
 *     on the flagged card itself.
 *   - NEW FINDING — the whole browser can silently collapse into a locked
 *     ~728x420 "Mobile Access Coming Soon" viewport after closing a tab
 *     (independent of `resize_window` calls, which report success but don't
 *     take effect while this state persists). Recovery: dismiss the "Got
 *     it" button on the mobile-notice modal if present, THEN call
 *     `resize_window` again — dismissing the modal first is necessary, a
 *     bare resize alone did not recover it in this run. If dismissing
 *     doesn't help either, close every tab in the group and let it
 *     auto-destroy, then `tabs_context_mcp({createIfEmpty:true})` to start
 *     a genuinely fresh tab group.
 *   - NEW FINDING — closing what you believe is a "spare" tab while another
 *     tab in the same group was only just created can destroy the whole MCP
 *     tab group (`tabs_context_mcp` then reports "No tab group exists").
 *     Recreate with `createIfEmpty:true` and re-navigate; no data was lost,
 *     just an extra round-trip. Prefer closing the OLDER tab only after
 *     confirming the newer one is fully loaded and responsive.
 *   - Multi-amendment mid-session scope changes (three arrived in quick
 *     succession this run: 8-panel sheet spec -> superseded by a concrete
 *     4-panel DND-format spec -> superseded again by a full cast expansion
 *     + location + prop rewrite) are handled by: never deleting superseded
 *     assets (not authorized to judge/delete — that's the CEO's call),
 *     recording both old and new ids side by side in the registry with an
 *     explicit OBSOLETE/current status column, and proactively flagging via
 *     dev_message when the new scope's credit math lands at or near the
 *     task's hard cap, before spending into it.
 *
 * Wave 9 (task-d988c30c, 2026-08-27/28): 3 character plates (redesigned art
 * student, museum exterior location, parrot-redesigned woman) + 1 Element-only
 * filing job (Valder, from a pre-existing asset, 0 credits) in "The Valder
 * Collection No.7". 3 generations, 7.5 credits total, all first-attempt, none
 * flagged.
 *   - NEW FINDING -- the screenshot-px-to-CSS-px ratio is NOT a fixed
 *     constant and must be recomputed every time the window/viewport changes.
 *     Measured 1456/1024=1.4219 early in this run, then 1374/1024=1.3418
 *     after a Chrome restart -- window dimensions differ per launch even at
 *     the "same" resize_window request. A card click computed from a stale
 *     ratio landed on the WRONG card (opened a neighboring asset's preview
 *     instead of the intended one) more than once this run. Fix: read
 *     `window.innerWidth` fresh and compute `screenshotWidth/innerWidth`
 *     immediately before converting any CSS rect to a click coordinate --
 *     never reuse a ratio from earlier in the same session.
 *   - NEW FINDING -- `?preview=<asset-id>` is NOT a valid deep link. A full
 *     `navigate()` to that URL, and even a same-tab `history.pushState` +
 *     `popstate` dispatch while the SPA was already loaded, both got silently
 *     stripped back to the bare project URL with no dialog opening. The
 *     preview param is a RESULT of an in-app card click, not an input the
 *     router accepts. Always locate the actual card in the DOM
 *     (`[data-asset-id="..."]`) and click it for real.
 *   - NEW FINDING -- filing an Element from an asset that ISN'T freshly
 *     generated (i.e. hunting an old asset in "All assets" to build an
 *     Element from it, per a CEO instruction to reuse instead of
 *     regenerate) is far more expensive than filing one just generated,
 *     because the target card is deep in a large virtualized grid with no
 *     reliable search-by-id. Approaches that did NOT work: the account's
 *     `/fnf/jobs` API only ever returns ~5 recent items regardless of
 *     `limit=100` or a `folder_id=` query param -- it is a recent-activity
 *     feed, not a paginated listing endpoint, don't rely on it for
 *     enumeration. The "Downloaded" and "Date range" activity/type filters in
 *     the Filter dropdown DID work for narrowing the visible set (down to
 *     ~18-45 items, fully rendered, no further virtualization) but the
 *     target asset wasn't in either filtered set this run for reasons not
 *     fully understood (possibly filter semantics not matching the raw
 *     `created_at`/download-event timestamp). What DID work: real
 *     `computer` scroll actions (mouse-wheel, not JS `scrollTop` assignment)
 *     repeated in a `browser_batch` of 5-10 at a time, checking
 *     `document.querySelectorAll('[data-asset-id]')` for the target id
 *     between batches -- this is genuinely brute-force but reliable, since
 *     the grid is virtualized and a JS-only `scrollTop` change does NOT
 *     reliably trigger the pagination/mount cycle the way a real wheel event
 *     does.
 *   - NEW FINDING -- once the target card is found and hovered (via
 *     synthetic `pointerover`/`mouseover`/`pointerenter`/`mouseenter`/
 *     `mousemove` PointerEvents dispatched in sequence -- a REAL hover isn't
 *     needed for this, only the icon-reveal state, which responds fine to
 *     synthetic events since it's not money-committing), its own "..." menu
 *     (bottom-right of the 5-icon hover stack: heart/download/copy/expand/
 *     more) contains **Create Element** directly -- this is faster and more
 *     reliable than the documented "click card -> ?preview=<uuid> modal ->
 *     ... -> Create Element" path from earlier waves, since it skips the
 *     preview-modal step entirely (which, per this wave's finding above, no
 *     longer opens reliably via any tested method). Confirmed working 3/3
 *     times this run (once per plate).
 *   - NEW FINDING -- the "New element" dialog, when opened via a card's own
 *     "Create Element" menu item, arrives PRE-POPULATED with that exact
 *     asset image already attached (visible as a thumbnail in the dropzone
 *     immediately, no upload needed). This is the correct path when the
 *     task says "file an Element from this existing asset, don't
 *     regenerate" -- the alternative "Add new" button in the Elements panel
 *     opens the SAME dialog but with an EMPTY dropzone requiring a local
 *     file upload via `file_upload`, which the harness restricts to
 *     session-shared paths (`~/Downloads` and `~/Desktop` were both
 *     rejected this run: "only files this session is allowed to read can be
 *     uploaded"). Don't fight the upload restriction -- use the card menu's
 *     pre-populated path instead, it requires no file access at all.
 *   - NEW FINDING -- the Category dropdown inside "New element" needs its
 *     OPTION clicked at the SAME coordinate the dropdown itself was opened
 *     with the FIRST time reliably, but a stale reference to an ALREADY-
 *     rendered-but-closed dropdown's option coordinates can silently
 *     re-open the dropdown instead of selecting (happened twice this run --
 *     the fix was to click the Category button again fresh, screenshot,
 *     THEN click the visible option, rather than assuming a remembered
 *     coordinate from a prior dialog instance still applies).
 *   - NEW FINDING -- when you already have the completed job's direct
 *     CloudFront asset URL (from the `results.raw.url` field via
 *     `GET /fnf/jobs/{id}`), a plain `curl` download straight to the target
 *     Desktop path is faster and more reliable than fighting the in-page
 *     hover-icon download button or the detail-modal Download button --
 *     zero browser interaction needed, and it's the exact same file
 *     (verified via `file` command reporting correct PNG dimensions
 *     matching the composer's resolution setting). Use this whenever the
 *     task's Desktop-path download requirement doesn't require the file to
 *     have passed through Higgsfield's own "mark as downloaded" tracking.
 *   - NEW FINDING -- the page's JS execution can freeze mid-session on this
 *     heavy "All assets" view (300+ mixed image/video assets): two
 *     consecutive `javascript_tool` calls timed out at 45s with "renderer
 *     may be frozen or unresponsive," even a brand-new tab in the same
 *     Chrome process froze the same way seconds after loading. A full
 *     `osascript -e 'quit app "Google Chrome"'` + `open -a "Google Chrome"`
 *     resolved it -- the extension took ~10-15s to reconnect after relaunch
 *     (`tabs_context_mcp` returned "not connected" for the first couple of
 *     retries, then recovered on its own with no other action needed).
 *     Escalation order confirmed once again: reload -> new tab -> quit+
 *     reopen Chrome, exactly per the skill's documented ladder, and each
 *     step really was necessary this time (reload alone and one fresh tab
 *     both still froze).
 *   - Per the "any tool error/timeout -> check Usage/job status first" hard
 *     rule: both freezes this run were checked against the jobs API
 *     immediately after recovery, and both times confirmed zero unexpected
 *     side effects (no new job fired, same top job as before the freeze) --
 *     the freezes were purely a rendering/JS-engine issue, not caused by
 *     and not causing any generation activity.
 *
 * Wave 10 (task-fe7b3d37, 2026-08-28): 6 plates in "The Valder Collection
 * No.7" -- 1 character turnaround (parrot woman v3, Character folder) + 5
 * hall-referenced object plates (Prop folder). 6 generations, 15 credits
 * total, all first-attempt except one (see below), zero flags.
 *   - NEW FINDING -- a Generate click can silently no-op 4 TIMES IN A ROW
 *     with the standard desync fix (focus+Selection-API-cursor-to-end+real
 *     Space+BackSpace) re-applied fresh each time, all confirmed zero-cost
 *     via the "All assets" counter not moving, THEN fire cleanly on a
 *     `find()`-ref click after zero other changes. Raw-coordinate clicks and
 *     one `find()`-ref click both no-op'd on the same button in the same
 *     session; a later `find()`-ref click on the identical button worked.
 *     Clicks were independently confirmed to work fine elsewhere on the same
 *     page (a quality-dropdown pill opened correctly) during the no-op
 *     streak, ruling out a page-wide click-delivery fault. No clean
 *     explanation found; the fix that worked was simply "try find()-ref
 *     click if raw-coordinate clicks are no-opping," not a specific
 *     technique change. Prefer `find()`-ref over raw coordinates for the
 *     Generate button as the default first attempt on this composer.
 *   - NEW FINDING -- a full page reload (`navigate()` to the same folder
 *     URL) mid-troubleshooting restored the composer's PROMPT TEXT via
 *     autosave, but broke the @mention's visual binding: the tag rendered as
 *     RED unresolved text (`@<uuid>`) instead of a resolved chip, even
 *     though the identical uuid had been a normal-colored bound mention
 *     seconds before the reload. Clearing (Cmd+A + Delete x2) and re-pasting
 *     the identical prompt text fixed it immediately (mention resolved
 *     normal-colored again). Treat ANY post-reload composer state as
 *     suspect regardless of what autosave shows -- verify mention color, and
 *     when in doubt, clear + re-paste rather than trusting the restored
 *     text.
 *   - NEW FINDING -- the "All assets" sidebar counter incremented by 1
 *     independent of any of my own actions (jumped 348->349 during a run of
 *     confirmed no-op Generate clicks). Root cause: another operator was
 *     active on the same shared account concurrently (this project's task
 *     brief explicitly named one, collecting separate Scene 1 video takes).
 *     This counter is account/project-wide, not per-operator -- don't treat
 *     a delta as proof YOUR click fired; cross-check that the actual target
 *     folder shows a new top-of-grid card matching your prompt before
 *     concluding a click succeeded.
 *   - NEW FINDING -- the grid-hover "..." icon (5-icon hover stack: heart /
 *     download / copy(Recreate) / reference / more) needed 2-4 clicks at the
 *     same coordinate before the menu actually opened and stayed open, on 3
 *     separate cards in this run (millstone, vessel, study). No visible
 *     difference between a "worked" and "didn't work" click -- both looked
 *     identical (hover-revealed icon, real `computer` click, verified
 *     coordinate via zoom first). Toggling behavior suggests each click
 *     alternates open/close and the render can lag behind the click by one
 *     cycle. If a menu-item text search comes back empty after one click,
 *     click the exact same coordinate again (up to ~3 times) before
 *     switching technique -- this resolved every case this run without
 *     needing to fall back to the modal-detail-panel route.
 *   - NEW FINDING -- the modal detail-panel's own "..." button (bottom-right
 *     of the action row, next to Download/Like/Share) is a MORE RELIABLE
 *     fallback than the grid-hover icon stack when the grid-hover route is
 *     fighting you -- opened correctly on the first real click every time it
 *     was tried this run. Route: click the card's thumbnail image directly
 *     (not top-left corner, which toggles the selection checkbox) to open
 *     the `?preview=<uuid>` detail panel, confirm identity via the panel's
 *     own PROMPT text matching what you generated, then use ITS "..." menu.
 *   - NEW FINDING -- window/viewport dimensions kept drifting across this
 *     session with no resize_window call in between (1024x591, then
 *     1024x647, then 1374x868, then back to 1456x840-family) -- confirms the
 *     existing "recompute the screenshot-px/CSS-px ratio every time" rule,
 *     but extends it: a `getBoundingClientRect()` read from one
 *     `javascript_tool` call can be STALE by the time a later `computer`
 *     click uses it, even a few calls apart with no explicit resize. Always
 *     re-read the rect (or re-screenshot) in the SAME batch/turn as the
 *     click that uses it, never reuse a coordinate captured 2+ calls earlier
 *     -- this caused several missed clicks on the "..." icon and the
 *     card-grid checkbox this run.
 *   - Character-folder plate (parrot woman v3, 4-panel turnaround
 *     referencing an existing character Element via @mention): identical
 *     flow to a Prop-folder object plate -- paste with literal `@ElementName`
 *     text, verify chip resolves non-red, desync fix, verify price, Generate.
 *     One accidental extra reference got attached mid-session by
 *     mis-clicking the grid-hover "Reference" icon (4th in the 5-icon stack)
 *     instead of intending an "expand/preview" action -- it has no tooltip
 *     distinguishing it from a fullscreen-preview icon at a glance, hover for
 *     the tooltip text before clicking any icon in that stack, exactly as
 *     the existing Wave 2 guidance already says for Recreate/Rerun. Removing
 *     a manually-attached reference chip (X on its thumbnail in the composer)
 *     also silently deleted the real @mention text from the editor in this
 *     run -- if that happens, don't try to fix it in place: clear the whole
 *     composer and re-paste the original prompt fresh.

 * Wave 10 (task-f4320f9e, 2026-08-28): single replacement plate for
 * `char_grandmother` (elderly woman in an electric wheelchair) in the
 * "Sorry, Sir" project (same ai-film-festival-3 account, Character folder
 * ae0bb5a3-9f66-4e95-8112-c2939e9de56e). GPT Image 2 / 16:9 / Medium / 2K,
 * 1 generation, 2.5 credits, no reshoot.
 *   - Literal `@project_absence_loc_hall_big_d` pasted directly in prompt
 *     text auto-resolved to a genuine bound reference on GPT Image 2 (not
 *     just Soul Cinema) -- confirmed via `data-beautiful-mention` matching
 *     the known UUID `1a2cf503-4843-4aed-b4cb-d7cb8b919fa8` from
 *     docs/prompts/absence/PLATES.md plate 6. This is the same UUID the
 *     exterior plate resolved to, so paste-based mention binding is
 *     reliable on this composer for a single reference; the Elements-panel
 *     right-click->Use path from earlier waves is not required when the
 *     literal `@name` string is already correct.
 *   - Real click on Generate (computer tool, not JS-dispatched) worked on
 *     the first attempt -- no PointerEvent-sequence workaround needed this
 *     run, unlike Waves 6/7. The desync fix (focus + Selection API cursor-
 *     to-end + real Space + real BackSpace) was still applied pre-emptively
 *     and the click fired clean first try.
 *   - "Create Element" via the card's hover "..." menu (synthetic
 *     pointerover/mouseover/pointerenter/mouseenter/mousemove to reveal the
 *     6-icon hover stack, then click the "More actions" aria-label button)
 *     confirmed working again -- same reliable path as Wave 9. The dialog
 *     pre-populates the just-generated image with no upload needed.
 *     Category dropdown ("Auto" -> "Character") responds to a real
 *     `computer` click on the option text. Name + Element ID inputs need
 *     the native-value-setter + `input`-event-dispatch technique -- a
 *     coordinate click alone does not reliably focus/type into them (per
 *     the existing skill note); confirmed this run that setting Element ID
 *     to a value NOT matching the auto-generated `char_<name-lowercased>`
 *     default (i.e. the full `project_absence_char_grandmother` convention)
 *     overwrites the auto-fill cleanly with no leftover text.
 *   - Uploading a single generated plate PNG to this org's Google Drive
 *     (`ALL DRAFT/YT: ILAG/<project>/Element/`) has NO tool support in
 *     `scripts/gdrive-bridge/gdrive_move.py` (metadata-only CLI: move/
 *     rename/trash/create_folder/list/create_file[text]/create_doc/
 *     read_file/append_log -- no binary upload action). The working path:
 *     `from ilag_sync import upload` (same file's `upload(local_path, name,
 *     parent_id)` resumable-upload helper, built for the local-mirror sync
 *     loop but works standalone for one ad-hoc file) in a small scratch
 *     script, `sys.path.insert` to `scripts/gdrive-bridge`. Verified via
 *     returned `size` matching the local file's `stat().st_size` exactly
 *     (5332262 bytes both sides).
 *   - The "Sorry, Sir" project's `Element/` folder was set up 2026-08-28
 *     with Character/Location/Prop sub-folders (mirroring the `Do Not
 *     Disturb` DND template per the gdrive-filing skill's YT:ILAG section),
 *     but every one of the ~34 plates uploaded there before this run sits
 *     FLAT in `Element/` root, not sorted into the sub-folders -- the
 *     sub-folders are empty. This run matched the established flat
 *     practice (also what the CTO's own follow-up instruction specified:
 *     ".../Sorry, Sir/Element/", no sub-folder named) rather than the
 *     original 3-folder design, and logged it as an `EXCEPTION:` line in
 *     the project's `logs.txt` per the YT:ILAG "rules bend but never
 *     silently" clause -- do not silently start sorting into Character/ on
 *     a future run without raising this drift to the CEO/CTO first, since
 *     that would split one project's plates across two conventions.
 *   - Per the "nothing gets deleted" YT:ILAG rule, the REJECTED prior
 *     attempt for the same character (`absence-char-grandma.png`, found
 *     already sitting in `Element/` from an earlier session, chrome lounge
 *     chair with no wheels) was left in place untouched -- the new plate
 *     was uploaded under a deliberately different filename
 *     (`absence-char-grandmother.png`, note the full word vs the old
 *     abbreviated "grandma") specifically so the two would not collide or
 *     invite an accidental overwrite.
 *   - The worker mailbox delivered TWO separate "[New message from CEO]" /
 *     "[New message from CTO]" notifications during this run with zero
 *     body content each time (matches the documented empty-mailbox issue
 *     above) -- one of the two turned out to carry a real instruction that
 *     only reached this agent because it was ALSO relayed as literal
 *     injected chat text in the same turn (not via TASK.md, which stayed
 *     unchanged both times when re-checked). Treat an empty mailbox ping
 *     as inconclusive, not as "nothing happened" -- check both TASK.md AND
 *     the surrounding chat turn text before concluding there is nothing to
 *     act on.
 *   - Visual QA finding, worth generalising: a plate can clear the single
 *     rejection-driving criterion cleanly (wheels, unmistakable in all 4
 *     panels including the rear one) while still missing a secondary,
 *     unrelated spec line (here: gloves rendered black against an explicit
 *     "never black" colour rule). Zooming panel-by-panel via the detail
 *     modal's fullscreen view (not just the grid thumbnail) caught this;
 *     the grid thumbnail alone was too small to see the glove colour
 *     clearly. Reported the flaw plainly rather than silently filing the
 *     plate as a clean pass -- the CTO's own call was to accept it as-is
 *     and queue the fix behind higher-priority render-slot work, which is
 *     a judgment only a C-level should make, not something to decide
 *     silently either way as the operator.

 * Wave 10 (task-4cbd60f4, 2026-08-28): two paid GPT Image 2 plates on
 * "The Valder Collection No.7" (film "Sorry, Sir") -- a wall-POV crack
 * variant (2 attempts, both discarded) and a prop-cart revision (1 attempt,
 * accepted). Element panel search box collapses back to icon-only after
 * every navigate/modal-close; budget one extra click to re-expand it before
 * typing every single time -- typing straight into the collapsed icon is a
 * silent no-op (confirmed repeatedly this run, cost ~6 wasted round-trips
 * before recognising the pattern).
 *   - NEW FINDING -- the Elements-panel card's own "Download" button
 *     (bottom-left of the Info tab) returns a SMALL COMPRESSED WEBP
 *     (185 KB, 2688x1520) even for an asset whose native generation is a
 *     full-res PNG (6+ MB, same 2688x1520). This is a thumbnail export, not
 *     the source file -- do not use it as the deliverable. The reliable
 *     path is the ASSET's own hover download icon in the "All assets" /
 *     folder grid (top-right icon stack: heart / download / copy /
 *     reference / "..." -- the second icon), which produces the true
 *     native-resolution PNG named `hf_<UTC-timestamp>_<asset-id>.png`.
 *     Confirmed twice this run (char_woman_c, prop_cart_b): Element-panel
 *     Download = webp thumbnail; asset-grid hover download = full PNG.
 *   - NEW FINDING -- "Create Element" from a full-size image detail
 *     dialog's "..." menu (More -> Create Element) does NOT open a naming
 *     dialog the way Wave 9's card-hover-menu path did. It creates the
 *     Element immediately with placeholder name "My-Element" / id
 *     "my-element" and shows a bare "Element created." toast. Find it
 *     afterward via Elements-panel search (it will NOT show up under a
 *     search for the intended name yet) and open its own "Edit" action to
 *     set Category/Name/Element ID -- same native-value-setter technique as
 *     the New-Element dialog. Budget this as a required follow-up step,
 *     not an optional cleanup.
 *   - NEW FINDING -- the "..." (More) menu on an asset detail dialog can
 *     silently fail to open on a click that looks identical to one that
 *     just worked seconds earlier (confirmed 3 failed silent closes in a
 *     row on the same button before a 4th click opened it) -- no visible
 *     cause, no error, the dialog just doesn't render. Re-click the same
 *     spot rather than switching technique; it always recovered within a
 *     few attempts this run and never needed a page reload.
 *   - CONFIRMED again -- pasting a prompt whose body contains a literal
 *     "@project_absence_loc_wall_crack" (or similarly-prefixed) Element
 *     name auto-resolves to a real bound `data-beautiful-mention` UUID
 *     reference with zero manual @-picker interaction, exactly per the
 *     documented "paste the whole prompt" default flow -- verified via the
 *     mention's UUID matching the Element's own known asset id from
 *     PLATES.md before ever clicking Generate.
 *   - OPEN FINDING, not a technique fix -- GPT Image 2 has a real,
 *     repeated failure mode when asked to render "photographed from behind
 *     a cracked wall, matching a specific small reference crack, mirrored":
 *     it defaults to inventing a large rounded aperture/porthole shape
 *     bounded loosely by crack-like squiggles, rather than tracing the
 *     reference's actual thin multi-branch hairline geometry. Spelling out
 *     the exact branch count/directions/mirroring in prose measurably
 *     improved the second attempt (sharper top-edge lines) but did not fix
 *     the bottom-edge smooth-hole problem. Unresolved; worth trying the
 *     drag-drop `@Image1` reference path (bypasses the named-Element
 *     resolve entirely) or Soul Cinema with the reference bound via the
 *     Elements-panel "Use" method next time, before assuming prose tuning
 *     alone will converge.
 */

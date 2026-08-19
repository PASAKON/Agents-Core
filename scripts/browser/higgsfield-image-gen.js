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
 */

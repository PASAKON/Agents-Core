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
 */

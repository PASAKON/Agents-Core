/**
 * scripts/browser/higgsfield-free-image-plate-element.js
 *
 * Replay notes for a FREE (Unlimited) Higgsfield image plate + Element
 * registration, project-composer surface (e.g.
 * https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script — paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Distilled from task-bc7f8d5d/63fc0684 (car plate,
 * 2026-09-07) and task-cb28dcfb (cheque plate, 2026-09-09).
 *
 * Validated end-to-end task-cb28dcfb (2026-09-09): 2 generations, both
 * $0 (Unlimited), one Element registered, zero credits spent.
 *
 * Flow:
 *   1. Composer defaults to VIDEO mode (Seedance 2.5, priced). Click the
 *      small "Image" icon stacked above the composer settings row
 *      (bottom-left, NOT the top-nav "Image" text tab — that one doesn't
 *      switch modes reliably). Verify by re-reading the button-text list:
 *      should flip from {Seedance 2.5, References, 16:9, 720p, 20s, High,
 *      On, GENERATE\n140\n130} to {Kling O1, <aspect>, <res>, GENERATE\n0.5
 *      or similar paid number}.
 *   2. Pick model **Kling O1** from the model pill if not already selected.
 *      GPT Image 2 carries an "UNLIMITED" *badge* in the model list but
 *      that badge is NOT a toggle — its own Generate button still shows a
 *      live credit price. Kling O1 is the one with an actual Unlimited
 *      switch in the composer row.
 *   3. Click the **Unlimited** switch (`find` query: "Unlimited toggle
 *      switch in the image composer"). Verify via zoom on the Generate
 *      button region — must read bare `UNLIMITED`, zero digits. A DOM text
 *      scrape of button.innerText is NOT sufficient on its own (decoy
 *      buttons exist) — always confirm with a real `zoom` screenshot
 *      immediately before every click.
 *   4. Set aspect ratio (16:9 pill -> dropdown -> option) and resolution
 *      (1K/2K pill -> dropdown). Both 1K and 2K were selectable with
 *      Unlimited still reading zero-digit afterward (2026-09-09) — 2K is
 *      the higher free tier, prefer it when the task says "highest free
 *      quality".
 *   5. Paste the prompt: synthetic ClipboardEvent (text/plain only) into
 *      the visible (non-decoy, getComputedStyle(el).visibility==='visible')
 *      contenteditable, found via `.find(e => visible)` over
 *      `document.querySelectorAll('[contenteditable="true"]')`. Verify
 *      innerText.length exactly matches source length, plus first/last 80
 *      chars. Then apply the desync-bind tap: real key presses End, space,
 *      BackSpace (net text change zero) — this is what actually binds the
 *      pasted text to the framework's React/Lexical state; skipping it can
 *      leave a Generate click refused with "Prompt is required" even
 *      though the text is visibly present.
 *   6. Re-zoom the Generate button immediately before every click (state
 *      can drift between staging and firing, even seconds apart). Click via
 *      `find`-ref or a verified coordinate — real driving-tool click, not
 *      JS `.click()`.
 *   7. Verify the fire: `document.body.innerText.match(/Generation
 *      started|All assets\s*\n?\d+/g)` — expect both, and the assets count
 *      incremented by exactly 1 from the pre-click baseline.
 *   8. Poll `[data-asset-id]` cards (position 0 is newest) for
 *      `!textContent.includes('Processing')` and `querySelector('img')`
 *      truthy. Observed completion times for Kling O1 2K: ~40-80s (NOT the
 *      video-render timescale of 20-50 min — poll in short waits, 10s at a
 *      time, not the 20-min-then-5-min video cadence).
 *   9. If the task specifies an exact readable-text requirement (a written
 *      number, a sign, a label), OPEN THE DETAIL VIEW and zoom the specific
 *      region — a grid thumbnail is too small to judge legibility or digit
 *      count. Click the card's visual center (not its top-left corner,
 *      which toggles the multi-select checkbox instead) to open the
 *      `?preview=<uuid>` detail panel.
 *  10. If the first attempt is defective (wrong digit count, smudged text,
 *      wrong object), and the task allows a second try: do NOT change the
 *      prompt. Re-verify the composer state is still exactly as staged
 *      (same text length, same spec row), re-zoom the button, click
 *      Generate again. A second identical fire is a normal part of the
 *      "at most two attempts, pick the better one" pattern documented in
 *      several task briefs — it is not a retry-after-failure situation
 *      needing new technique.
 *
 * Registering the chosen image as a named Element:
 *   1. In the detail panel (?preview=<uuid>), click the panel's own "..."
 *      (More) button (bottom-right of the action row, next to
 *      Download/Like/Share) -> **Create Element**. This is more reliable
 *      than the grid-hover icon stack's "..." menu, which can silently
 *      fail to open (retry the same click a few times before switching
 *      technique, per prior waves' findings).
 *   2. The "New element" dialog arrives PRE-POPULATED with the chosen
 *      asset already in the dropzone — no upload needed.
 *   3. Category dropdown: click it, options are Auto/Character/Location/
 *      Prop as plain rows (a real `computer` click on the option text
 *      works). Selecting a category AUTO-PREFIXES the Element ID field
 *      (e.g. "my-element" -> "prop_my-element") — this is a known quirk,
 *      not a bug to work around by clicking order.
 *   4. Set BOTH Name and Element ID to the exact required name via a
 *      native value-setter + `input`-event dispatch (a coordinate click +
 *      type does NOT reliably focus/type into these fields):
 *        function setNativeValue(el, value) {
 *          const proto = Object.getPrototypeOf(el);
 *          const desc = Object.getOwnPropertyDescriptor(proto, 'value');
 *          desc.set.call(el, value);
 *          el.dispatchEvent(new Event('input', {bubbles: true}));
 *        }
 *      Find the Name input by its placeholder default value ("My-Element")
 *      and the Element ID input by its auto-prefixed value containing
 *      "my-element". Verify both fields' `.value` after setting, before
 *      clicking Create.
 *   5. Click Create. Verify via `document.body.innerText.match(/Element
 *      created/i)`.
 *
 * Confirming the Element is live in the @-picker (video composer, per most
 * task briefs' explicit requirement):
 *   1. Switch the composer back to Video mode (bottom-left icon toggle).
 *      DO NOT touch its Generate button — Seedance 2.5 is priced by
 *      default and this check needs no fire at all.
 *   2. Paste `@<exact_element_name> test` (or similar) into the real
 *      contenteditable via the same synthetic-paste + End/space/BackSpace
 *      technique as step 5 above.
 *   3. Check for a bound chip:
 *        [...editor.querySelectorAll('span.text-font-brand')]
 *          .filter(e => !e.querySelector('span') &&
 *                       e.textContent.trim().startsWith('@')).length
 *      Should be 1. Cross-check with
 *        [...editor.querySelectorAll('[data-beautiful-mention]')]
 *          .map(m => m.getAttribute('data-beautiful-mention'))
 *      — a UUID confirms the bind (not just a hopeful color match). A
 *      zoom screenshot on the mention text is worth taking too: a bound
 *      chip renders LIME (`rgb(209, 254, 23)`); unresolved text stays RED.
 *   4. Clear the composer afterward (Ctrl+A + Delete x2, verify down to a
 *      single trailing newline / length <= 1) so no stray text or chip is
 *      left staged on a priced composer. Never click Generate on this
 *      surface as part of this check.
 *
 * Downloading the final asset:
 *   - Hover the grid card (not the detail panel — its own Download button
 *     can return a compressed thumbnail webp on this UI, per an earlier
 *     wave's finding) and click the 2nd icon in the 5-icon hover stack
 *     (heart / download / copy / reference / more). Produces the true
 *     native-resolution PNG named `hf_<UTC-timestamp>_<asset-id>.png` in
 *     the browser's default download directory (outside the worktree —
 *     copy it in afterward and record path/size/md5 in the task report).
 */

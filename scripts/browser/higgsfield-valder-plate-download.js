/**
 * scripts/browser/higgsfield-valder-plate-download.js
 *
 * Replay notes for downloading the source plate/image behind every
 * project_valder_char_* Element, task-598b5fa3 (2026-08-26), Valder
 * Collection No.7 (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP, interleaved with real `computer` clicks (see why
 * below). Scope this run covered: Characters only (17/17). Locations and
 * Props were handed to other operators and this file says nothing about
 * their panels, though the same recipe should apply unchanged.
 *
 * Result: 17/17 Character Elements downloaded, 0 credits (this is a read-only
 * asset-retrieval flow -- no Generate button touched, no cost of any kind).
 *
 * THE CORE BUG THIS FILE WORKS AROUND:
 *
 * The Element detail dialog (opened by clicking a card in the Elements panel)
 * is a SINGLETON that does not reliably reset its content when a new card is
 * clicked in quick succession. Symptom: click card B right after closing
 * card A's dialog, and the reopened dialog can still show card A's Element ID
 * text, card A's image, or a mix (one field updated, the other stale) for
 * several seconds -- sometimes indefinitely until a full page reload. This is
 * NOT a virtualization/pairing bug in the scraping method (ruled out
 * explicitly this run, see docs/reports/valder-plate-download.md) -- it is
 * the app's own dialog component failing to remount cleanly.
 *
 * CONSEQUENCE: never trust "I clicked card X" as proof the dialog now shows
 * X. ALWAYS re-read the dialog's own Element ID field in the SAME turn,
 * immediately before clicking Download, and only proceed if it matches the
 * target. This run caught itself opening the wrong element's dialog at least
 * 6 times using exactly this check -- every one of those would have produced
 * a silently mislabelled file if Download had been clicked on trust.
 *
 * THE RELIABLE PER-ELEMENT LOOP (used for all 17 this run):
 *
 *   1. navigate() to the project's ?elements=1 URL -- a full reload, not a
 *      soft in-app navigation. This is the only thing that reliably resets
 *      the stuck-dialog bug once it appears. A `find()`+click on the dialog's
 *      own Close button, or a real Escape keypress, both sometimes fail to
 *      clear it (confirmed: dialog left at `pointer-events: auto`,
 *      `opacity: 0`, full-viewport `position: fixed` rect -- effectively an
 *      invisible page-wide click-blocker). Cost of reloading every element:
 *      acceptable for ~17-50 elements; reconsider for a much larger batch.
 *   2. Wait ~1.8-2.2s after navigate for the SPA to mount (a `querySelector`
 *      for `input[placeholder="Search"]` returning null is the reliable
 *      "not ready yet" signal -- poll or just wait a fixed ~2s).
 *   3. The search box sometimes renders collapsed (an icon + "Search" label,
 *      no visible `<input>`) after a fresh load. Click it once
 *      (`document.querySelector('button')` matching "Search" text, or just
 *      the icon's coordinates) before trying to focus/set it.
 *   4. Set the search value via the NATIVE INPUT SETTER, not real keyboard
 *      typing -- real `type` action was observed to silently no-op on this
 *      box after a dialog had just closed (focus appears to land elsewhere):
 *        const inp = document.querySelector('input[placeholder="Search"]');
 *        inp.focus();
 *        const setter = Object.getOwnPropertyDescriptor(
 *          window.HTMLInputElement.prototype, 'value').set;
 *        setter.call(inp, 'char_something');
 *        inp.dispatchEvent(new Event('input', {bubbles:true}));
 *      Wait ~700ms after dispatching for the grid to refilter.
 *   5. The category tab (All / Characters / Locations / Props) that ends up
 *      active after a reload is NOT deterministic -- it can silently be
 *      whatever tab was active in a previous visit (localStorage-backed).
 *      Also observed: clicking a tab button sometimes advances the
 *      highlighted tab by one position without the breadcrumb agreeing (a
 *      second, independent app bug). FIX: don't fight it -- take one
 *      screenshot after setting the search value and read the breadcrumb
 *      ("All / Characters", etc.) plus the actual card(s) shown. Searching
 *      from the "All" tab works fine (it searches every category), so
 *      standardize on always confirming "All" is active before relying on
 *      position, and screenshot instead of assuming.
 *   6. Click the single result card at its on-screen position (this run:
 *      consistently ~(450, 317) in a 1024x768-requested / ~1374x868-screenshot
 *      window -- see the browser-operator skill for why those two numbers
 *      differ; `computer` click coordinates are in the SCREENSHOT's pixel
 *      space, not `window.innerWidth`/`innerHeight`). If two elements share
 *      an ambiguous substring match (e.g. searching "guard" also matches
 *      "guards_12"), screenshot first and click the correct card position
 *      instead of assuming position 1.
 *   7. VERIFY before downloading -- read the Element ID text from INSIDE the
 *      now-open dialog, not from the grid, not from a prior turn:
 *        const d = document.querySelector('[role="dialog"]');
 *        const leaf = [...d.querySelectorAll('*')].find(e =>
 *          e.children.length === 0 &&
 *          /^@project_valder_/.test((e.textContent||'').trim()));
 *        leaf.textContent.trim() // must equal '@' + target id
 *      If it doesn't match, click the SAME card position again (this run
 *      needed 1-2 retries fairly often -- the first click after a fresh
 *      load/reload frequently misses or opens nothing) and re-verify. Do
 *      not click Download speculatively.
 *   8. Click the dialog's "Download" button -- this run found it at a
 *      consistent ~(1017, 743) once the dialog is genuinely open, but
 *      `find()` + click on the button (by text "Download") is equally
 *      reliable once step 7 has confirmed the right dialog is showing.
 *   9. Off-page: the file lands in ~/Downloads named EXACTLY
 *      `<element_id>.<ext>` (this run: always `.webp`) -- Higgsfield's
 *      Download control already writes the correct filename, no renaming
 *      needed. Verify with a fresh `ls -t ~/Downloads | head -1` immediately
 *      after the click and check its name starts with the target id BEFORE
 *      moving it into the repo -- this run caught the stuck-dialog bug
 *      producing a wrong-but-plausible download this way (see finding #10
 *      below) purely from the filename not matching.
 *
 * A FASTER PATH THAT SOMETIMES APPEARS, USE WITH CAUTION:
 *
 * Hovering an unfiltered/filtered grid card can reveal three small icons
 * (copy / download-arrow / more) directly on the card, without opening the
 * detail dialog at all. Clicking the download-arrow icon (this run: card's
 * hover overlay icon at roughly the same x as the card, ~70px above its
 * vertical center) downloads immediately -- works and is faster when it
 * fires. BUT the same coordinate can just as easily open the full detail
 * dialog instead (observed both outcomes at nearly the same pixel offset
 * across different runs of this exact interaction) -- treat whichever one
 * happens as fine, but ALWAYS follow with the same off-page filename check
 * from step 9, since there is no in-page verification available for the
 * hover-icon path the way there is for the dialog path.
 *
 * NEW FINDINGS THIS RUN:
 *
 * 10. STUCK-DIALOG BUG PRODUCED A CONFIRMED WRONG DOWNLOAD, CAUGHT ONLY BY
 *     RE-OPENING THE SOURCE FILE. Early in this run (before the verify-in-
 *     step-7 discipline above was fully adopted), a click intended for
 *     `char_mother` downloaded `char_valder`'s asset twice in a row --
 *     confirmed by file size/name matching the previous element exactly.
 *     Caught before it entered the manifest by checking the Downloads
 *     folder listing immediately after each click, not by trusting the UI.
 *     RULE: never assume the tool result implies success -- read
 *     `~/Downloads` and compare the filename to the target every time.
 * 11. `project_valder_char_neighbor` IS A GENUINE SOURCE MISMATCH, NOT A
 *     METHOD BUG. Its detail dialog shows a six-men-in-uniform image, not a
 *     single person. Confirmed via a from-scratch reload + one screenshot
 *     containing both the Element ID text and the image in the same frame
 *     (the CTO specifically asked for this exact cross-check method after
 *     spotting the mismatch from the downloaded file). Its "Name" field is
 *     also unset (shows the raw ID), unlike every correctly-named sibling
 *     Element -- this may be why it slipped through: it was likely never
 *     finished/reviewed after creation. `char_tea_circle` has the same
 *     unset-Name symptom but its image content is correct.
 * 12. ELEMENT ID SUBSTRING SEARCHES CAN BE AMBIGUOUS ACROSS DIFFERENT
 *     CATEGORIES/NAMES THAN EXPECTED. Searching "char_guard" surfaces both
 *     `char_guard` and `char_guards_12` (both real, distinct Elements --
 *     confirmed with the CTO mid-run: prompts tagging `@project_valder_
 *     char_guard` were NOT silently failing, the Element genuinely exists
 *     separately from the group-of-12 lineup). Searching "press" surfaces
 *     both `char_press` and `char_valder_press`. Always screenshot an
 *     ambiguous multi-result search rather than assuming the first card is
 *     the target.
 * 13. THE DIALOG'S "Element details of <uuid>" HEADER TEXT IS ALSO STALE-
 *     PRONE, separately from the Element ID field lower in the same dialog.
 *     Only trust the Element ID field (verified reliable across ~20 opens
 *     this run when checked per step 7); the header UUID was observed
 *     showing the SAME uuid across two different Elements' dialogs in a row,
 *     so it was not used as a manifest column beyond the one Element where
 *     it was captured under a freshly-confirmed-correct dialog.
 */

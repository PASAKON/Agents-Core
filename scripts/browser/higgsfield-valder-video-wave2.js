/**
 * scripts/browser/higgsfield-valder-video-wave2.js
 *
 * Replay notes for firing Valder S1/S1B multicut video takes, wave 2,
 * task-b7224c38 (2026-08-26), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Read higgsfield-valder-s2-fire.js first for the
 * base paste/desync/verify recipe this project uses -- this file only
 * records what was NEW or confirmed-again for this specific wave (a
 * resume after task-6b6bae3a's accidental-logout incident).
 *
 * Result this run (in progress at time of writing): S1 take B fired clean,
 * S1B take A staged during its render. See docs/reports/valder-video-wave2.md
 * for the live per-clip table.
 *
 * ---
 *
 * GETTING PROMPT TEXT INTO THE PAGE WITHOUT BURNING AGENT CONTEXT
 *
 * Do NOT base64-encode a ~25KB prompt file and Read the base64 back into
 * agent context -- the base64 form is one giant line with no natural break
 * points, and the Read tool's own truncation is line-based. A 25,305-byte
 * file base64-encodes to a 33,741-char single line, which blew past this
 * session's 25,000-token single-read cap and got silently truncated
 * (confirmed: the read returned an explicit "PARTIAL view" warning).
 *
 * ALSO do not try to stand up a local static file server for the page to
 * fetch() the prompt from cross-origin -- opening a network listener via
 * Bash was blocked by this session's auto-mode classifier as a risky
 * action, even for a harmless localhost CORS server.
 *
 * What worked: JSON-encode the prompt file locally (preserves every
 * character exactly, including em-dashes and curly quotes, with zero manual
 * escaping) and pass the JSON string directly as a JS string literal --
 * JSON.stringify output IS valid JS source:
 *
 *   python3 -c "
 *   import json
 *   data = open('docs/prompts/valder/s1-multicut.txt', encoding='utf-8').read()
 *   open('/tmp/s1_js.txt','w',encoding='utf-8').write(json.dumps(data))
 *   "
 *
 * This produces a file with normal escape sequences (\n, — for em-dash)
 * instead of raw multi-byte UTF-8, so it stays comfortably under the
 * single-read token cap even for the ~25KB source (25,646-byte JSON output,
 * well inside the limit). Read that file, then in javascript_tool:
 *
 *   window.__PROMPT_S1 = "...(the JSON string content, used AS the JS
 *   literal directly -- no JSON.parse needed since JSON string syntax is a
 *   subset of JS string syntax)...";
 *
 * Verify immediately: `.length`, `.slice(0,80)`, `.slice(-80)` against the
 * source file's own byte count and head/tail (`wc -c`, `head -c`, `tail -c`
 * in Bash) BEFORE ever touching the composer.
 *
 * ---
 *
 * COMPOSER PILL ROW -- IT'S A HORIZONTAL CAROUSEL, NOT A FIXED ROW
 *
 * The settings pill row (model / mode / aspect / resolution / duration /
 * quantity / quality / sound / Unlimited) does not all fit in the visible
 * width at once. A ">" chevron at the row's right edge scrolls it one
 * "page" at a time, revealing 2-3 more pills each click. Order encountered
 * scrolling right from a fresh Seedance-2.5 composer load:
 *
 *   [model] [mode] [aspect] [resolution]  -->
 *   [resolution] [duration] [quantity -/+]  -->
 *   [duration] [quantity] [quality]  -->
 *   [quality] [sound] [Unlimited]
 *
 * (exact grouping may shift by a pill or two depending on starting scroll
 * position -- don't hardcode a fixed number of chevron clicks, read the
 * pills after each click instead.)
 *
 * ---
 *
 * DURATION POPOVER STEP SIZE IS NOT A FLAT 1s/ArrowKey
 *
 * Confirmed again this run: the duration control opens a small popover with
 * a real (but not freely-typeable) numeric field. Triple-click to select,
 * then ArrowRight/ArrowLeft -- but the step size is NOT reliably 1 second
 * per keypress from every starting value. This run: 15x ArrowRight from an
 * assumed "5s" start landed on 30s (not 20s), then 5x ArrowLeft = 25s and a
 * further 5x ArrowLeft = 20s (i.e. 1:1 once past whatever the popover's
 * *opening* jump was). ALWAYS zoom-read the popover's numeric value after
 * every batch of presses -- never trust a precomputed press count.
 *
 * ---
 *
 * UNLIMITED TOGGLE: A DIRECT DOM .click() ON A PRECISE SELECTOR BEATS
 * find()-THEN-CLICK FOR THIS SPECIFIC CONTROL
 *
 * task-6b6bae3a's incident (accidental account logout) happened because a
 * find()-returned ref for the Unlimited toggle went stale between the
 * find() call and the click call (a card completed and re-rendered the DOM
 * in between), and the click landed on the account menu's logout link
 * instead -- both controls sit in the same corner of the composer.
 *
 * This run used a different technique that structurally can't hit that
 * failure mode: a single javascript_tool call that queries
 * `[role="switch"]`, filters for the one whose aria-label matches
 * /unlimited/i, reads `aria-checked` BEFORE, calls `.click()` on the actual
 * element reference held in that SAME call's local variable (never a
 * cross-call ref, never a coordinate), waits 300ms, and reads
 * `aria-checked` AFTER -- all atomically in one execution turn:
 *
 *   const switches = [...document.querySelectorAll('[role="switch"]')]
 *     .filter(el => getComputedStyle(el).visibility !== 'hidden'
 *                && el.getBoundingClientRect().width > 0);
 *   const target = switches.find(el => /unlimited/i.test(el.getAttribute('aria-label')||''));
 *   const before = target.getAttribute('aria-checked');
 *   target.click();
 *   await new Promise(r=>setTimeout(r,300));
 *   const after = target.getAttribute('aria-checked');
 *
 * This has zero coordinate risk and zero cross-call staleness risk (there is
 * nothing for the DOM to re-render *during* one synchronous-ish call). It is
 * still exactly ONE click attempt per the task's hard rule -- if `after`
 * doesn't flip, still stop, don't retry with a second technique.
 *
 * CAUGHT THIS RUN: the 300ms read came back `after: "false"` -- looked like
 * the documented "stuck toggle" failure. Before escalating, a zoom-screenshot
 * of the Generate button (the task's own authoritative tiebreaker) already
 * showed `UNLIMITED / ~~440~~ / 0` -- struck-through, free. A FRESH read-only
 * re-query of `[role="switch"]` a few seconds later (no new click) showed
 * `aria-checked="true"`. Conclusion: 300ms was too short for this app's state
 * update to land; it was a read race, not a stuck control. **If the
 * immediate post-click read says "false" but the Generate button's own price
 * already shows struck-through/free, trust the button and re-read the switch
 * once more (read-only) before concluding the toggle is stuck.** Only after
 * a clean re-read still disagrees with the button should this be treated as
 * the genuine stuck-control incident.
 *
 * ---
 *
 * FINDING THE NEW ASSET'S ID FROM A "Processing" CARD
 *
 * The processing card has no href/preview link while still rendering (a
 * click on it while Processing does nothing, confirmed -- URL stays
 * unchanged). No new-generation network request is visible via
 * read_network_requests either, because that tool only tracks requests
 * AFTER it is first called in the session -- it can't see a request that
 * already fired.
 *
 * What works: walk up from the "Processing" text node, ancestor by
 * ancestor, extracting UUIDs from `outerHTML` at each level. The right
 * level is the FIRST one (going up) where exactly one UUID appears -- too
 * few levels and there's no UUID yet (asset id lives outside the immediate
 * text node), too many levels and you pick up every sibling card's id too
 * (including a KNOWN id from a previous take, which is a useful sanity
 * check that you've gone too far up):
 *
 *   const proc = [...document.querySelectorAll('*')]
 *     .find(el => el.children.length===0 && el.textContent.trim()==='Processing');
 *   const uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g;
 *   let node = proc;
 *   for (let i=0;i<8 && node;i++) {
 *     const ids = [...new Set((node.outerHTML.match(uuidRe)||[]))];
 *     if (ids.length === 1) { console.log(i, ids[0]); break; }
 *     node = node.parentElement;
 *   }
 *
 * This run the isolated level was 5-6 parents up from the "Processing" text.
 *
 * NOTE: dumping a card's full outerHTML sometimes trips this session's own
 * output filter with `[BLOCKED: Cookie/query string data]` -- some asset
 * thumbnail URLs carry long signed-looking query strings that look like
 * session tokens. Strip `.split('?')[0]` before returning any raw HTML/URL
 * string, or (better, as above) only ever return the small extracted UUID
 * list, never the raw HTML itself.
 *
 * ---
 *
 * THE IN-PROGRESS CARD LABEL IS NOT CONSISTENT -- "Processing" AND
 * "Generating" BOTH OCCUR
 *
 * Checking only for the literal string "Processing" to decide whether the
 * previous render is done is NOT SAFE -- this run, one card's in-progress
 * label read "Processing" and a different card (same composer, same
 * project, fired minutes apart) read "Generating" instead. A check that
 * only searched for "Processing" returned a false "nothing in progress"
 * while the "Generating" card was still genuinely rendering, and the
 * subsequent premature Generate click was only saved by the platform's own
 * account-wide concurrency guard (a toast, zero cost, zero side effect --
 * but still a near-miss next to a priced composer corner).
 *
 * Always check for the union of labels, e.g.:
 *
 *   const cand = [...document.querySelectorAll('*')]
 *     .find(el => el.children.length===0
 *              && /processing|generating|queued|rendering/i.test(el.textContent.trim()));
 *
 * and treat ANY match as "still in progress", not just an exact string.
 *
 * ---
 *
 * resize_window CAN REPORT SUCCESS WHILE THE VIEWPORT STAYS BROKEN -- AND A
 * COLLAPSED VIEWPORT SILENTLY SWAPS THE PAGE TO A MOBILE LAYOUT
 *
 * After 4 generations in one tab (matching this project's own documented
 * "open a fresh tab every 3-4 generations" threshold), that tab's
 * `window.innerWidth/innerHeight` was found at **127x79** -- not the
 * requested 1024x768/1024x591. `resize_window` reported "Successfully
 * resized" when re-run against the same tab, but the dimensions never
 * changed. The page had silently responded to the collapsed viewport by
 * swapping to an entirely different, near-empty "Mobile access coming soon"
 * layout -- zero `[contenteditable]` nodes, no composer, nothing usable.
 *
 * Do not fight a tab in this state. Per this project's own hygiene rule,
 * open a brand-new tab (leaving the broken one untouched -- no navigate, no
 * reload, since the task forbids touching the composer tab that way),
 * resize the NEW tab, verify `innerWidth/innerHeight` actually match before
 * doing anything else, and rebuild the full composer from scratch there.
 * `window.__PROMPT_*` globals do not survive the tab switch -- re-embed the
 * prompt text (from the same already-verified JSON-escaped source) in the
 * new tab before pasting.
 *
 * ---
 *
 * A CDP SCREENSHOT/ZOOM TIMEOUT RIGHT BEFORE A GENERATE CLICK IS NOT A
 * REASON TO SKIP THE PRICE CHECK -- FALL BACK TO A DOM TEXT-DECORATION READ
 *
 * `Page.captureScreenshot` (both full `screenshot` and `zoom`) timed out
 * twice in a row ("the renderer may be frozen or unresponsive") at the exact
 * moment a price-tiebreaker zoom was needed before a Generate click -- same
 * failure class as the CDP-unresponsive stall in this project's prior
 * incident (task-6b6bae3a). `javascript_tool` calls kept working the whole
 * time (confirmed with a trivial `1+1` eval), so the renderer wasn't
 * actually dead, just the screenshot pipeline specifically.
 *
 * Do NOT proceed to Generate without SOME form of the price check just
 * because the visual tiebreaker is unavailable. The struck-through/live
 * distinction is also readable straight from the DOM, per-span:
 *
 *   const btn = [...document.querySelectorAll('button')]
 *     .find(b => /generate|unlimited/i.test(b.innerText||'')
 *             && getComputedStyle(b).visibility !== 'hidden'
 *             && b.getBoundingClientRect().width > 0);
 *   const spans = [...btn.querySelectorAll('*')]
 *     .filter(el => el.children.length===0 && el.textContent.trim());
 *   spans.map(s => ({text: s.textContent.trim(),
 *                     deco: getComputedStyle(s).textDecorationLine}));
 *   // -> [{text:"Unlimited",deco:"none"},{text:"140",deco:"line-through"},{text:"0",deco:"none"}]
 *
 * `line-through` on the crossed-out number is the same signal a screenshot
 * shows, read directly and unambiguously from computed style -- no pixels
 * needed. Confirmed this run: matched the expected struck-140-to-0 pattern
 * exactly, and the subsequent Generate click fired clean.
 *
 * ---
 *
 * CONFIRMING A FIRE WHEN THE TOAST WINDOW IS MISSED
 *
 * If the "Generation started" toast isn't caught (checked too late, or a
 * stall ate part of its visible window) and the in-progress card label
 * flickers in and out between two checks moments apart, two independent
 * signals confirm a real fire without needing the toast or a stable label:
 *
 * 1. `read_network_requests` (already tracking since first called this
 *    session) shows a `GET /fnf/jobs/<uuid>` call for an id that isn't in
 *    your own known-ids list -- the page's own client only polls status for
 *    a job it just created or that is genuinely in flight.
 * 2. A FRESH scratch tab (not the composer tab, whose DOM may be stale)
 *    independently shows no in-progress label anywhere AND that same id
 *    present somewhere in its DOM.
 *
 * Both together is strong enough to report the asset id and move on --
 * don't burn further budget chasing a definitive completion timestamp if
 * these two agree.
 *
 * ---
 *
 * STAGING THE NEXT PROMPT DURING A RENDER IS SAFE AND CHEAP
 *
 * Confirmed again: editing the composer's prompt text (clear via real
 * Cmd+A + Delete, paste the next scene's prompt, re-verify mention count,
 * re-apply the desync fix) does not touch the in-flight render (already
 * committed server-side) and does not touch the Unlimited toggle's state.
 * Did this for S1B take A while S1 take B was still rendering. Generate was
 * NOT clicked on the staged prompt until the previous render's completion
 * was confirmed (one-generation-at-a-time rule) -- staging is prep, not a
 * queue-jump.
 */

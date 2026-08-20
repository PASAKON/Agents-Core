/**
 * scripts/browser/runpod-availability-survey.js
 *
 * Replay notes for re-running the RunPod console availability survey
 * (task-8a568920, 2026-08-21) — items 1 (region list), 2 (per-region 48GB
 * Community Cloud stock) and 6 (cheapest CPU instance). Item 3/4 (network
 * volume regions / balance gate) and item 5 (ComfyUI template) are not
 * covered here — those pages change rarely and are cheap to re-check by
 * hand; stock (items 1/2/6) changes constantly and is the reason this
 * survey gets re-run.
 *
 * NOT a standalone Node/Playwright script — paste snippets into
 * javascript_tool against an already-open, already-logged-in
 * console.runpod.io tab via claude-in-chrome MCP. Same convention as
 * higgsfield-image-gen.js in this repo.
 *
 * Read-only. Never click Deploy/Create/Rent/Start/Confirm/Subscribe, never
 * touch the payment/add-credit form. This script only reads filter state
 * and card text.
 *
 * ---------------------------------------------------------------------
 * SETUP
 * ---------------------------------------------------------------------
 * 1. tabs_create_mcp, resize_window to 1024x768 (or smaller — cost table
 *    in the browser-operator skill).
 * 2. navigate to https://console.runpod.io/deploy directly — this route
 *    loads fine on a fresh full navigation. `/storage` and `/templates`
 *    do NOT (they 404 / render blank on direct navigate) — the SPA only
 *    resolves nested routes via in-app client-side routing (click the
 *    sidebar link from an already-loaded page). Real paths behind those
 *    links: /user/storage, /user/templates, /hub. Not needed for this
 *    script (items 1/2/6 all live on /deploy).
 * 3. Wait ~3-5s after navigate before querying — this is a Next.js SPA
 *    and document.body is empty text for a few seconds after first paint
 *    even though document.readyState already reads "complete".
 *
 * ---------------------------------------------------------------------
 * ITEM 1 — REGION LIST (Secure Cloud, default cloud type on fresh load)
 * ---------------------------------------------------------------------
 * The region dropdown is a headlessui Popover portal. CAUTION: multiple
 * headlessui Popovers on this page all use the literal DOM id
 * "headlessui-portal-root" (invalid duplicate-id HTML, but real —
 * confirmed 2026-08-21). document.getElementById() silently returns
 * whichever one happens to be first/cached; ALWAYS use
 * document.querySelector('[id="headlessui-portal-root"]') scoped to
 * the portal you just opened, and re-query fresh after every click —
 * do not cache a reference to it across steps.
 *
 * Region button is NOT reliably findable by visible text — it reads
 * "Any region" on first load but just "Any" once any filter has been
 * touched, and the natural-language `find` tool can return a stale/wrong
 * match when several controls share short text. Locate it positionally
 * instead: it is the button immediately after the "Community Cloud" /
 * "Secure Cloud" cloud-type button in DOM order.
 *
 *   const allBtns = () => [...document.querySelectorAll('button')];
 *   const ccIdx = allBtns().findIndex(b => /Secure Cloud|Community Cloud/.test(b.innerText.trim()));
 *   const regionBtn = allBtns()[ccIdx + 1];
 *   regionBtn.click();
 *
 * The open dropdown is a 2-level accordion: top level is 4 continent
 * groups ("All Asia", "All North America", "All Europe", "All Oceania"),
 * each a <button>. Clicking a group button toggles it open/closed
 * (single-open accordion — opening one silently closes whichever was
 * open). Clicking it ALSO selects "All <Continent>" as an active region
 * filter as a side effect — harmless for a read-only pass since nothing
 * downstream depends on the filter staying at "Any", but if the next step
 * needs a clean "Any" state, click "Clear Selection" (appears inside the
 * expanded group, bottom of the list) before moving on.
 *
 *   function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
 *   async function expandGroup(label){
 *     const btn = [...document.querySelectorAll('#headlessui-portal-root button, [id="headlessui-portal-root"] button')]
 *       .find(b => b.innerText.trim().startsWith(label));
 *     btn.click();
 *     await sleep(300);
 *     const portal = document.querySelector('[id="headlessui-portal-root"]');
 *     return [...portal.querySelectorAll('button')]
 *       .filter(b => /^[A-Z]{2,4}-[A-Z]{2}-\d$/.test(b.innerText.trim()))
 *       .map(b => b.innerText.trim());
 *   }
 *   // await expandGroup('All Asia')          -> ["AP-IN-1","AP-JP-1"]
 *   // await expandGroup('All North America')  -> 18 CA-/US- codes
 *   // await expandGroup('All Europe')         -> 11 EU-/EUR- codes
 *   // await expandGroup('All Oceania')        -> ["OC-AU-1"]
 *
 * Confirmed full list 2026-08-21 (32 total): AP-IN-1, AP-JP-1, CA-MTL-1,
 * CA-MTL-3, CA-MTL-4, US-CA-2, US-CO-1, US-GA-2, US-IL-1, US-KS-2,
 * US-MD-1, US-MO-1, US-MO-2, US-NC-1, US-NC-2, US-NE-1, US-TX-3, US-TX-4,
 * US-WA-1, US-WA-2, EU-CZ-1, EU-FR-1, EU-NL-1, EU-RO-1, EU-SE-1, EUR-IS-1,
 * EUR-IS-2, EUR-IS-3, EUR-IS-4, EUR-NO-1, EUR-NO-2, OC-AU-1.
 * If this count changes, that IS the finding — report the delta.
 *
 * ---------------------------------------------------------------------
 * ITEM 2 — PER-REGION 48GB STOCK (Community Cloud)
 * ---------------------------------------------------------------------
 * IMPORTANT: switching cloud type to Community Cloud REPLACES the region
 * control. It is no longer the 32-code continent-grouped dropdown above —
 * it becomes a flat, ungrouped 11-country list (each country is a
 * <div role="option"><h1>CODE - Name</h1></div>, not a <button> — click
 * the role="option" div, not the h1). Confirmed set 2026-08-21: CA, CZ,
 * ES, FR, HR, PT, SE, SK, TT, TW, US. If this list's country count
 * changes on a re-run, note it — it may mean RunPod onboarded/dropped a
 * community country.
 *
 * Step order:
 *   1. Click the cloud-type dropdown (button reads "Secure Cloud" on
 *      fresh /deploy load), then click the "Community Cloud" <h1> inside
 *      the resulting portal (click its closest role="option"/li ancestor,
 *      the h1 itself is not the click target — same "leaf is h1 not
 *      button" pattern as the countries below).
 *   2. A "Community Cloud performance is unpredictable..." banner
 *      appears inline in the page — this is informational, not a
 *      consent dialog requiring acceptance. No action needed, don't
 *      click "Use Secure Cloud" (that reverts the filter).
 *   3. Set the VRAM slider to 48. It is `[role="slider"]` (a <button>,
 *      not <input type=range>), aria-valuenow 0-59, and the mapping from
 *      step index to GB is NOT linear/documented — don't assume a
 *      formula, walk it and read the label back:
 *
 *        const slider = document.querySelector('[role="slider"]');
 *        let label = '';
 *        for (let i = 0; i < 40; i++) {
 *          slider.dispatchEvent(new KeyboardEvent('keydown', {key:'ArrowRight', code:'ArrowRight', bubbles:true, cancelable:true}));
 *          await sleep(60);   // MUST await between dispatches — see below
 *          label = document.body.innerText.match(/GPUs with at least[^\n]*/)?.[0] || '';
 *          if (/at least 48 GB/.test(label)) break;
 *        }
 *
 *      Gotcha confirmed 2026-08-21: dispatching many KeyboardEvents in a
 *      tight synchronous loop (no await between them) only advances the
 *      value by ~1 step total regardless of how many events were fired —
 *      the component's re-render can't keep up and later events land on
 *      stale state. A real `computer` tool key-press with `repeat: N`
 *      has the same problem (10-20 repeats registered as +0 to +2). The
 *      only reliable method found was: click the slider once (real click,
 *      for focus) then dispatch ONE keydown + await ~60ms + re-check,
 *      in a loop. This took 12 steps to go from 0 to the "48 GB" label
 *      in this run — don't hardcode "12", walk it and check the label
 *      every time, thresholds could shift.
 *   4. Open the region control (same positional lookup as item 1: button
 *      immediately after the cloud-type button). This time it opens the
 *      flat 11-country list, not the continent accordion.
 *   5. For each country: click its option div to select it (this REPLACES
 *      the selection, doesn't add — confirmed each click shows exactly
 *      that one country's results), read the GPU list, click the SAME
 *      option div again to deselect back to "Any" before moving to the
 *      next country. Do not rely on a "Clear Selection" button here — the
 *      Community Cloud country list didn't show one in this run (unlike
 *      the continent dropdown, which does).
 *   6. Extract 48GB single-card rows from the results. Each GPU card is a
 *      <button> containing all its text (name, price, VRAM, max, RAM/CPU
 *      or "Unavailable"). Multi-GPU bundles are the SAME card shape but
 *      prefixed with "Nx\n" (e.g. "4x\nRTX 4070 Ti\n\n$0.00/hr\n\n48 GB
 *      VRAM..." — a 4x12GB bundle, not a real 48GB single card). Skip
 *      any card whose trimmed innerText starts with /^\d+x/.
 *
 *        function extract48(){
 *          const priceEls = [...document.querySelectorAll('main *')]
 *            .filter(e => e.children.length === 0 && /^\$[\d.]+\/hr$/.test(e.innerText?.trim()||''));
 *          const cards = [...new Set(priceEls.map(p => p.closest('button')))];
 *          return cards.map(c => {
 *            const t = c.innerText;
 *            if (/^\d+x/.test(t.trim())) return null;               // multi-gpu bundle, skip
 *            const vramM = t.match(/(\d+)\s*GB VRAM/);
 *            if (!vramM || vramM[1] !== '48') return null;           // wrong tier, skip
 *            const name = t.split('\n')[0].trim();
 *            const priceM = t.match(/\$([\d.]+)\/hr/);
 *            const maxM = t.match(/(\d+)\s*max/);
 *            const unavailable = /Unavailable/.test(t);
 *            return { name, price: priceM ? priceM[1] : null, max: maxM ? maxM[1] : null, unavailable };
 *          }).filter(Boolean);
 *        }
 *
 *      A card that is "Unavailable" still shows "$0.00/hr" and a max
 *      count — that count is a slot capacity, not live stock. Report the
 *      `unavailable` flag as the real availability signal, not the max
 *      number.
 *
 *   Full country loop:
 *
 *     function getPortal(){ return document.querySelector('[id="headlessui-portal-root"]'); }
 *     function getOptionByLabel(label){
 *       const h1 = [...getPortal().querySelectorAll('h1')].find(e => e.innerText.trim() === label);
 *       return h1.closest('[role="option"]');
 *     }
 *     const labels = ['CA - Canada','CZ - Czech Republic','ES - Spain','FR - France',
 *       'HR - Croatia','PT - Portugal','SE - Sweden','SK - Slovakia',
 *       'TT - Trinidad and Tobago','TW - Taiwan','US - United States'];
 *     const results = {};
 *     for (const label of labels) {
 *       const opt = getOptionByLabel(label);
 *       opt.click();
 *       await sleep(600);       // 600ms — 300-400ms was observed flaky (stale results)
 *       results[label] = extract48();
 *       opt.click();            // deselect back to Any
 *       await sleep(400);
 *     }
 *
 *   Run this in chunks of 2-3 countries per javascript_tool call and log
 *   compact (not JSON.stringify with full keys) — a full 11-country JSON
 *   dump in one call got silently truncated mid-object by the tool output
 *   cap in this run. Compact line format that survived:
 *   `label + ': ' + cards.map(c => c.name+'|'+c.price+'|'+c.max+'|'+(c.unavailable?'U':'A')).join(';')`
 *
 * Confirmed 2026-08-21 (see RUNPOD-SURVEY.md §2 for the full table):
 * only ES, TW, US had any 48GB single-card stock; CA/CZ/FR/HR/PT/SE/SK/TT
 * showed nothing available.
 *
 * ---------------------------------------------------------------------
 * ITEM 6 — CHEAPEST CPU INSTANCE
 * ---------------------------------------------------------------------
 * Click the "CPU" tab button (top of the instance picker, next to "GPU").
 * URL changes to /deploy?type=CPU. Three category buttons appear
 * (General Purpose / Compute-Optimized / Memory-Optimized — it's a
 * dropdown-style button showing the current category; click it, then
 * click the target category's leaf in the resulting portal, same
 * role="option" pattern as item 2's countries) crossed with two clock
 * tiers ("3 GHz" / "5 GHz" buttons, always both visible, not nested in
 * the category dropdown).
 *
 *   const cpuTab = [...document.querySelectorAll('button,a')].find(b => b.innerText.trim() === 'CPU');
 *   cpuTab.click();
 *   await sleep(500);
 *   const ghz5 = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === '5 GHz');
 *   ghz5.click();
 *   await sleep(500);
 *   // category defaults to whatever was last selected (persists across GHz toggle)
 *   // read current cards: same card shape as GPU (button with name/price/RAM text)
 *   document.querySelector('main').innerText;   // cheapest is always the first (smallest) card
 *
 * To check a specific category, open its dropdown the same way as item
 * 2's cloud-type/country dropdowns (find the button showing the current
 * category name, click it, click the target label's option in the
 * portal). Confirmed 2026-08-21 cheapest-per-category (all at their
 * cheaper GHz tier):
 *   Compute-Optimized / 5 GHz: $0.07/hr, 2 vCPUs, 4 GB RAM  <- overall cheapest
 *   General Purpose   / 3 GHz: $0.08/hr, 2 vCPUs, 8 GB RAM
 *   Memory-Optimized  / 5 GHz: $0.13/hr, 2 vCPUs, 16 GB RAM
 * Always check both GHz tiers for whichever category looks cheapest —
 * cheaper clock speed does not consistently mean cheaper $/hr across
 * categories (General Purpose's cheapest tier was 3 GHz, not 5 GHz).
 *
 * The CPU deploy page has the same "Network volume" filter dropdown the
 * GPU page has, next to the region filter — confirms CPU pods can mount
 * a network volume (no need to actually attach one to verify this).
 *
 * ---------------------------------------------------------------------
 * GENERAL GOTCHAS THIS RUN
 * ---------------------------------------------------------------------
 * - Full-page `navigate()` to a nested route (e.g. /storage, /templates,
 *   /user/storage right after a fresh tab) reliably renders BLANK
 *   (document.body.innerText === '', sometimes document.title becomes
 *   "Page Not Found") even after 5+ seconds of waiting. The fix is not
 *   "wait longer" — it's to load /deploy first (which always works on a
 *   fresh navigate) and then click the in-app sidebar link for the
 *   target page, letting the SPA's client-side router handle it. Once
 *   you're already inside the app, `link.click()` on an `<a>` element
 *   works reliably for internal nav.
 * - `computer` tool `screenshot` timed out once (30s CDP timeout) while
 *   the page was fully responsive to javascript_tool calls seconds
 *   before and after — treat a single screenshot timeout as a fluke, not
 *   a signal the tab is dead; re-check with a cheap javascript_tool call
 *   before assuming you need to restart Chrome.
 * - `find` (natural-language element lookup) returned stale/wrong
 *   matches twice this run for short-text buttons ("Any" matched a
 *   different filter than intended). Prefer DOM position/structure
 *   queries via javascript_tool for anything with short or reused label
 *   text; save `find` for uniquely-worded elements.
 */

/**
 * scripts/browser/runpod-blackwell-survey.js
 *
 * Replay notes for re-running the RunPod Blackwell/region survey
 * (task-dbe738c7, 2026-08-22) — per-region GPU stock (Secure + Community
 * Cloud) for the MiniMax H3 candidate regions: AP-JP-1, CA-MTL-1,
 * CA-MTL-3, CA-MTL-4, AP-IN-1 (AP-IN-2 has no GPU compute, see below),
 * OC-AU-1. Purpose: is a Blackwell-generation card (RTX PRO 6000, B200,
 * B300, RTX 5090) in stock in any of these, and if not, which non-Blackwell
 * ≥48GB card is.
 *
 * NOT a standalone Node/Playwright script — paste snippets into
 * javascript_tool against an already-open, already-logged-in
 * console.runpod.io tab via claude-in-chrome MCP. Same convention as
 * runpod-availability-survey.js in this repo (read that one too — it
 * covers the region *list*, Community Cloud country list, ComfyUI
 * template and cheapest-CPU items this script does not repeat).
 *
 * Read-only. Never click Deploy/Create/Rent/Start/Confirm/Subscribe.
 * NOTE (found 2026-08-22): the safety classifier in this harness refused
 * a click on any button whose text matches /Create.*network volume/i,
 * even read-only-intent (open dialog, read, Cancel). Don't retry that
 * click if it recurs — read what's available from surrounding page text
 * instead (see NETWORK VOLUME PRICING section below) and flag the gap.
 *
 * ---------------------------------------------------------------------
 * SETUP
 * ---------------------------------------------------------------------
 * 1. tabs_create_mcp, resize_window to 1024x768 (cost table in the
 *    browser-operator skill). Window resize can silently no-op if Chrome
 *    is in a fullscreen-like state — verify with
 *    `[window.innerWidth, window.innerHeight]` after resizing; don't
 *    trust the tool's "Successfully resized" text alone.
 * 2. navigate to https://console.runpod.io/deploy directly.
 * 3. `/deploy` reliably renders BLANK (`document.body.innerText.length
 *    === 0`) for several seconds after a fresh navigation, sometimes
 *    longer — confirmed both this run and the prior survey's run. Poll
 *    with a `javascript_tool` call checking `document.body.innerText.length`
 *    every ~3-4s; if it's still 0 after 3 tries (~12s), a lone
 *    `javascript_tool` "CDP timeout" error is a fluke (page stays
 *    responsive to a trivial `1+1` call) — re-issue the check, don't
 *    assume the tab is dead. If it stays blank past ~15s total, try a
 *    fresh navigate before giving up.
 *
 * ---------------------------------------------------------------------
 * THE REGION FILTER IS A MULTI-SELECT ACCORDION — READ THIS BEFORE USING
 * ---------------------------------------------------------------------
 * This is the load-bearing gotcha of this whole script. The Secure Cloud
 * region dropdown LOOKS single-select (one label shows in the button,
 * e.g. "AP-JP-1") but the underlying state is a multi-select array:
 *
 *   - Clicking a continent group button ("All Asia", "All North America",
 *     "All Europe", "All Oceania") both EXPANDS it and SELECTS every leaf
 *     code inside it as a side effect.
 *   - Clicking a leaf code button TOGGLES that one code in the array.
 *   - "Any region" (visible at the top of the dropdown, always) resets
 *     the LABEL to "Any region" but does NOT clear the underlying array —
 *     confirmed by re-expanding a continent afterward and finding its
 *     codes still selected. Do not treat "Any region" as a working reset.
 *   - The only real per-continent reset is the "Clear Selection" button
 *     that appears inside an EXPANDED continent group. It clears only
 *     that continent's codes, not the other three groups'.
 *
 * Net effect: if you don't explicitly clear every continent group you've
 * touched, selections accumulate silently across the whole session, and
 * a later "select region X" click can produce "every region except X"
 * instead — the exact opposite of what it looks like happened. This
 * produced two full rounds of contaminated data on 2026-08-22 before the
 * pattern was understood. ALWAYS verify the filter button's label reads
 * back EXACTLY the one target code (a single string, no commas) before
 * extracting — never trust the click alone.
 *
 * Reliable procedure for a single clean region read:
 *
 *   function sleep(ms){return new Promise(r=>setTimeout(r,ms));}
 *   function visiblePortal(){
 *     // headlessui reuses the literal id "headlessui-portal-root" for
 *     // every popover on the page (invalid dupe-id HTML, but real).
 *     // Always pick the one currently rendered, not just the first match.
 *     const portals = [...document.querySelectorAll('[id="headlessui-portal-root"]')];
 *     return portals.find(p => p.offsetParent !== null) || portals[portals.length-1];
 *   }
 *   function regionBtn(){
 *     // Region button always immediately follows the cloud-type button
 *     // ("Secure Cloud" / "Community Cloud") in DOM order — but the
 *     // ABSOLUTE index shifts when cloud type changes (Community Cloud
 *     // shows an extra network-speed filter Secure Cloud doesn't), so
 *     // locate by adjacency to the cloud-type button fresh each time,
 *     // don't hardcode an array index.
 *     const all = [...document.querySelectorAll('button')];
 *     const idx = all.findIndex(b => /Secure Cloud|Community Cloud/.test(b.innerText.trim()));
 *     return all[idx + 1];
 *   }
 *
 *   // one-time, per continent you plan to touch: clear it fully first
 *   async function clearContinent(label){
 *     regionBtn().click(); await sleep(400);
 *     let p = visiblePortal();
 *     const groupBtn = [...p.querySelectorAll('button')].find(b=>b.innerText.trim().startsWith(label));
 *     groupBtn.click(); await sleep(400);           // expands + selects all (side effect)
 *     p = visiblePortal();
 *     const clearBtn = [...p.querySelectorAll('button')].find(b=>b.innerText.trim()==='Clear Selection');
 *     clearBtn.click(); await sleep(400);
 *   }
 *
 *   // then, with the continent's group still expanded from clearContinent():
 *   async function selectLeaf(code){
 *     const p = visiblePortal();
 *     const btn = [...p.querySelectorAll('button')].find(b=>b.innerText.trim()===code);
 *     btn.click(); await sleep(600);
 *     const label = regionBtn().innerText.trim();
 *     if (label !== code) throw new Error('contaminated selection: '+label);
 *     return label;
 *   }
 *
 *   // Full Asia continent groups: "All Asia" (2 leaves: AP-IN-1, AP-JP-1)
 *   // Full NA continent groups:   "All North America" (18 leaves incl. CA-MTL-1/3/4)
 *   // Full Oceania:               "All Oceania" (1 leaf: OC-AU-1)
 *
 * ---------------------------------------------------------------------
 * EXTRACTING GPU CARDS (same shape as runpod-availability-survey.js)
 * ---------------------------------------------------------------------
 *   function extractAll(){
 *     const priceEls = [...document.querySelectorAll('main *')]
 *       .filter(e => e.children.length === 0 && /^\$[\d.]+\/hr$/.test(e.innerText?.trim()||''));
 *     const cards = [...new Set(priceEls.map(p => p.closest('button')))].filter(Boolean);
 *     return cards.map(c => {
 *       const t = c.innerText;
 *       const name = t.split('\n')[0].trim();
 *       const priceM = t.match(/\$([\d.]+)\/hr/);
 *       const vramM = t.match(/(\d+)\s*GB VRAM/);
 *       const maxM = t.match(/(\d+)\s*max/);
 *       const unavailable = /Unavailable/i.test(t);
 *       return { name, price: priceM?priceM[1]:null, vram: vramM?vramM[1]:null,
 *                max: maxM?maxM[1]:null, unavailable };
 *     });
 *   }
 *   const BLACKWELL = ['RTX PRO 6000', 'RTX PRO 6000 WK', 'RTX PRO 6000 MaxQ', 'B200', 'B300', 'RTX 5090'];
 *   const isBlackwellAvailable = () => extractAll().some(c => BLACKWELL.includes(c.name) && !c.unavailable);
 *
 * ---------------------------------------------------------------------
 * FULL RUN — ALL 6 CANDIDATE REGIONS (Secure Cloud)
 * ---------------------------------------------------------------------
 * Run in this order to minimize continent-group switches:
 *
 *   await clearContinent('All Asia');
 *   await selectLeaf('AP-JP-1');   const jp = extractAll();
 *   const p1 = visiblePortal();
 *   [...p1.querySelectorAll('button')].find(b=>b.innerText.trim()==='AP-IN-1').click();
 *   await sleep(600);   // toggles AP-JP-1 off (it's already selected), AP-IN-1 on — VERIFY label after
 *   const in1 = extractAll();
 *
 *   await clearContinent('All North America');
 *   await selectLeaf('CA-MTL-1');  const mtl1 = extractAll();
 *   regionBtn().click(); await sleep(400);
 *   let p2 = visiblePortal();
 *   [...p2.querySelectorAll('button')].find(b=>b.innerText.trim()==='Clear Selection').click();
 *   await sleep(400);
 *   await selectLeaf('CA-MTL-3');  const mtl3 = extractAll();
 *   regionBtn().click(); await sleep(400);
 *   let p3 = visiblePortal();
 *   [...p3.querySelectorAll('button')].find(b=>b.innerText.trim()==='Clear Selection').click();
 *   await sleep(400);
 *   await selectLeaf('CA-MTL-4');  const mtl4 = extractAll();
 *
 *   await clearContinent('All Oceania');
 *   await selectLeaf('OC-AU-1');   const au = extractAll();
 *
 * AP-IN-2 is NOT in this loop — confirmed 2026-08-22 it does not exist in
 * the Secure Cloud `/deploy` region list (Asia group has exactly 2 codes:
 * AP-IN-1, AP-JP-1). It only exists as a network-volume location (see
 * runpod-availability-survey.js §3 and this survey's §3) — no GPU stock
 * check applies to it.
 *
 * Confirmed availability 2026-08-22 (re-verify — this is a live stock
 * snapshot, changes hour to hour):
 *   AP-JP-1: H100 SXM (max2), H200 SXM (max4) available. No Blackwell.
 *   AP-IN-1: H100 SXM (max8) available. No Blackwell, no H200, no A100 at all.
 *   CA-MTL-1: H100 SXM (max8), A40 (max1) available. No Blackwell.
 *   CA-MTL-3: H200 SXM (max2), A100 PCIe (max1) available. No Blackwell.
 *   CA-MTL-4: nothing available — zero stock across all 31 cards checked.
 *   OC-AU-1: L40S (max8) available only. No Blackwell, no H100/H200.
 *   Blackwell (RTX PRO 6000/WK, B200, B300) showed Unavailable in EVERY
 *   region above AND in the unfiltered "any region" (worldwide) baseline —
 *   read that as global sold-out, not a regional exclusion.
 *
 * ---------------------------------------------------------------------
 * COMMUNITY CLOUD — Canada only (no JP/IN/AU presence at all)
 * ---------------------------------------------------------------------
 * Switching cloud type replaces the whole filter bar; the region control
 * moves and becomes a flat country list, not a continent accordion:
 *
 *   const cloudBtn = [...document.querySelectorAll('button')].find(b=>/Secure Cloud|Community Cloud/.test(b.innerText.trim()));
 *   cloudBtn.click(); await sleep(400);
 *   let p = visiblePortal();
 *   const ccH1 = [...p.querySelectorAll('h1')].find(e=>e.innerText.trim()==='Community Cloud');
 *   (ccH1.closest('[role="option"]')||ccH1.parentElement).click();
 *   await sleep(500);
 *   // region button is now at a DIFFERENT relative position — Community
 *   // Cloud adds a network-speed filter between cloud-type and region.
 *   // Re-locate the same way: button immediately after cloud-type button.
 *   regionBtn().click(); await sleep(400);
 *   p = visiblePortal();
 *   const countryH1s = [...p.querySelectorAll('h1')].map(e=>e.innerText.trim());
 *   // Confirmed 2026-08-22: CA, CZ, ES, FR, HR, PT, SE, SK, TT, TW, US.
 *   // Japan/India/Australia are simply not options here — don't waste a
 *   // click looking for them.
 *   const caH1 = [...p.querySelectorAll('h1')].find(e=>e.innerText.trim()==='CA - Canada');
 *   (caH1.closest('[role="option"]')||caH1.parentElement).click();
 *   await sleep(700);
 *   const caCards = extractAll();
 *
 * Confirmed 2026-08-22, Community Cloud CA - Canada (country-level, not
 * MTL-specific — may span other Canadian PoPs): H100 NVL 94GB $2.59/hr
 * available (max1); L40 48GB $0.69/hr available (max4); RTX 5090 32GB
 * $0.69/hr available but too small; RTX PRO 6000/MaxQ/WK all Unavailable
 * (same global Blackwell sold-out pattern as Secure Cloud).
 *
 * ---------------------------------------------------------------------
 * NETWORK VOLUME PRICING (no dialog needed — read from /user/storage text)
 * ---------------------------------------------------------------------
 * Navigate `/deploy` first (loads fine fresh), THEN click the sidebar
 * link — direct navigation to `/user/storage` renders blank, same SPA
 * routing quirk as `/storage` and `/templates`:
 *
 *   const a = [...document.querySelectorAll('a')].find(a=>a.getAttribute('href')==='/user/storage');
 *   a.click(); await sleep(1500);
 *   document.body.innerText;   // contains pricing directly, no dialog needed:
 *   //   "Standard storage ... Pricing: $0.07/GB/mo for first 1TB, then $0.05/GB/mo"
 *   //   "High performance storage ... Pricing: $0.14/GB/mo"
 *
 * The PER-REGION volume list (which datacenters offer Standard vs.
 * High-performance, and which are S3-tagged) is NOT on this list page —
 * it only appears inside the "Create Network Volume" dialog, which this
 * harness's safety classifier refused to open on 2026-08-22 (button text
 * matched /Create.*network volume/i, treated as a provisioning action
 * despite read-only intent). If that recurs, don't force it — cite the
 * prior survey's region list (runpod-availability-survey.js §3, dated
 * 2026-08-21: AP-JP-1 Standard, CA-MTL-3 Standard, CA-MTL-4
 * High-performance, AP-IN-2 Standard+S3; CA-MTL-1/AP-IN-1/OC-AU-1 absent
 * from the volume list entirely) as carried-over, not freshly confirmed,
 * and flag it for a session/human that can clear the classifier.
 *
 * Balance/verification gate check (no click needed):
 *   const btn = [...document.querySelectorAll('button')].find(b=>b.innerText.trim()==='Create Network Volume');
 *   btn.disabled;   // false at $-0.00 balance, confirmed both survey runs — no gate
 *
 * ---------------------------------------------------------------------
 * GENERAL GOTCHAS THIS RUN (2026-08-22, additive to the prior survey's list)
 * ---------------------------------------------------------------------
 * - A `javascript_tool` call timed out at the CDP level (45s) twice,
 *   immediately after a click inside the region popover, while the page
 *   stayed fully responsive to the very next call. Treat a lone timeout
 *   as a CDP hiccup — verify with a trivial `1+1` call before assuming
 *   the tab needs a restart.
 * - Returning raw `<a>` `href` values in bulk got one result blocked
 *   with `[BLOCKED: Cookie/query string data]` — some hrefs apparently
 *   carried session-token-like query strings. Filter to a keyword regex
 *   before returning a list of hrefs (e.g. `/storage|hub|template/i`)
 *   rather than dumping everything.
 * - Window `resize_window` can report success without the OS honoring it
 *   (screenshot came back 1512x792 once, not the requested 1024x768) —
 *   verify with `[window.innerWidth, window.innerHeight]` before relying
 *   on the smaller viewport for screenshot cost math.
 */

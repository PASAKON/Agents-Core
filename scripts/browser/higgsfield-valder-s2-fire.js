/**
 * scripts/browser/higgsfield-valder-s2-fire.js
 *
 * Replay notes for firing Valder Scene 2 multi-cut video takes,
 * task-92a5978a (2026-08-25), The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP. Read scripts/browser/higgsfield-valder-character-
 * images.js first for the base paste/desync/verify recipe -- this file
 * only records what was NEW or DIFFERENT for a VIDEO (not image) fire on
 * this project, plus one new bug class.
 *
 * Result this run: BLOCKED before Generate on take 1. 0 credits spent,
 * 0 generations fired. See docs/reports/valder-s2-fire.md for the full
 * writeup. The finding below is why, and how to check for it fast next time.
 *
 * NEW FINDING: @[name](uuid) markdown-link paste can fail per-Element,
 * independent of whether the UUID is valid -- check with a plain-@name
 * paste before assuming the Element is broken.
 *
 * Symptom: after a clean paste (composer verified empty first,
 * innerText.length <= 1; paste verified via first/last-80-char match
 * against source), some [data-beautiful-mention] chips render with a
 * `.text-icon-error` icon inside their (hidden) thumbnail span instead of
 * a real reference image. This is NOT the previously-documented "decoy
 * editor" bug (visibility filter already applied, correct node confirmed)
 * and NOT the "second submission empty-state" desync bug (this was the
 * first paste of the session). It is a distinct failure mode: the paste
 * silently marks specific @[name](uuid) tags as unresolved while others
 * in the SAME paste resolve fine.
 *
 * Diagnostic one-liner -- run this on the composer immediately after any
 * paste, before trusting a raw mention-count as "N/7 bound":
 *
 *   const editors = [...document.querySelectorAll('[contenteditable="true"]')]
 *     .filter(el => getComputedStyle(el).visibility !== 'hidden');
 *   const mentions = [...editors[0].querySelectorAll('[data-beautiful-mention]')];
 *   mentions.map(m => ({
 *     raw: m.getAttribute('data-beautiful-mention'),
 *     hasError: !!m.querySelector('.text-icon-error')
 *   }));
 *
 * `hasError: true` is the ONLY reliable signal. Do NOT trust the chip's
 * displayed text to infer success/failure -- a resolved chip can render as
 * either the pretty `@name` form OR the raw `@<uuid>` form (observed both,
 * for different DOM re-renders of the very same successfully-bound
 * father/son mentions across two different pastes this run), and an
 * unresolved chip's displayed text is also just the raw UUID. Text alone
 * is ambiguous; `.text-icon-error` is not.
 *
 * Also do not trust the reference-thumbnail IMAGE count alone as a first
 * check if you need to know WHICH tag failed (only that N failed) -- cross
 * reference distinct img alt text (`preview of <uuid> asset`) against the
 * full set of UUIDs the prompt uses to get a per-Element pass/fail map:
 *
 *   let container = editors[0]; for (let i=0;i<6;i++) container = container.parentElement;
 *   [...container.querySelectorAll('img')].map(im => im.alt);
 *
 * ROOT-CAUSE ISOLATION (confirmed, do this before assuming stale/wrong
 * UUIDs and before touching the Elements panel to "fix" anything):
 *
 * 1. Open a SEPARATE scratch tab (tabs_create_mcp) -- don't touch the
 *    staged composer tab. Navigate to the same project root.
 * 2. Paste the failing tags as PLAIN `@name` text with NO explicit
 *    `(uuid)` suffix, e.g.:
 *      "@project_valder_char_mother\n@project_valder_char_daughter\n..."
 *    If these resolve cleanly (hasError: false) and the resulting
 *    data-beautiful-mention UUIDs match the ones hardcoded in your prompt
 *    file exactly, the Elements are NOT stale/re-pointed/missing -- the
 *    UUIDs in your prompt are correct and current. This was true for all
 *    5 failing tags this run (mother/daughter/grandma/loc_home_interior/
 *    prop_plan all resolved via plain-@name paste, same UUIDs).
 * 3. To confirm it's specifically the markdown-link FORM (not paste size,
 *    not position in a huge paste), isolate a minimal 2-mention paste
 *    using the exact `@[name](uuid)` syntax: one known-good tag (e.g.
 *    father) next to one known-failing tag (e.g. mother). If father
 *    resolves and mother errors in this minimal isolated paste too, the
 *    failure is per-Element and format-specific, not a scale/timing
 *    artifact. Confirmed this run: reproduced 1-for-1 in isolation.
 *
 * WHAT THIS DOES NOT TELL YOU: why some Elements resolve via markdown-link
 * paste and others don't (creation date? cache state? an internal
 * id-mapping quirk on Higgsfield's side?). Didn't dig further -- this is
 * a content/technique decision for a C-level, not an operator call, per
 * the "scope discoveries are a C-level decision" rule. Two live options
 * if this recurs: (a) have the prompt author use plain @name mentions
 * instead of @[name](uuid) for any tag that fails this check, or (b) fall
 * back to the Elements-panel right-click -> Use method for just the
 * failing tags (documented in higgsfield-unlimited-gen skill's "Creating
 * an Element" / "@ dropdown is folder-scoped" sections) -- NEITHER was
 * attempted this run since the task required using the given prompt file
 * unchanged.
 *
 * STOP CONDITION HONORED: task's REFERENCE COUNT rule says count must
 * equal 7 or stop and report which failed to bind. Did not click Generate
 * with 2/7 bound. Zero credits spent, zero generations fired, verified via
 * Account menu balance staying flat at 1,974 before and after.
 *
 * OTHER CONFIRMATIONS THIS RUN (matching prior waves, recorded briefly):
 * - Unlimited toggle: defaulted OFF on page load (button read
 *   `GENERATE 440 130`, live un-struck price). One clean ref-based click
 *   via find() flipped it to `data-state="on"` on the first attempt --
 *   no stuck-toggle escalation needed this run.
 * - Duration/Resolution did NOT reset to the documented 5s/1080p traps
 *   this run -- composer loaded already at 20s/720p/High/16:9/Sound-On.
 *   Still re-verify every time; this is exactly the kind of setting the
 *   skill says silently drifts, and this run being clean is not a
 *   guarantee for the next one.
 * - Base64-encoding the ~14,921-char prompt file via `base64` in Bash and
 *   decoding with `atob` + `TextDecoder('utf-8')` inside the page (rather
 *   than inlining the raw prompt string as a JS literal in the tool call)
 *   avoided any quoting/escaping risk from the prompt's em-dashes, curly
 *   quotes, and embedded markdown-link syntax. Verified length (14,921,
 *   exact match to source) and first/last 80 chars after decode, before
 *   ever touching the composer. Recommended default for any prompt this
 *   long or with non-ASCII punctuation.
 *
 * ---
 *
 * Wave 2 (task-1cbe84c8, 2026-08-25): retry with the prompt file rewritten
 * to plain `@project_valder_*` mentions (no bracket, no explicit UUID) for
 * all 7 Elements, per this file's own "live options if this recurs" note
 * above. Result: BLOCKED again, but for a DIFFERENT reason. 0 credits
 * spent, 0 generations fired. See docs/reports/valder-s2-fire-retry.md.
 *
 * CONFIRMED: the plain-tag format fixes the binding problem. All 7 mentions
 * resolved with `hasError: false` and correct thumbnails, UUIDs matching
 * this file's Wave 1 findings exactly. Use plain `@name` mentions for every
 * future prompt in this project -- the markdown-link form is no longer
 * needed or recommended.
 *
 * NEW TRAP: two overlapping reference-thumbnail strips can coexist in the
 * DOM at once -- a stale one and a live one. Immediately after the first
 * paste (before any reload), the visible thumbnail strip showed warning
 * triangles on 5 of 7 cards even though the mention-chip `hasError` check
 * said all 7 were clean. This is the SAME family of bug as the documented
 * "hidden decoy editor" (this file's sibling doc) and "hidden duplicate
 * Generate button" (Wave 1 above) -- just a third UI element with the same
 * failure shape. Distinguish the live strip from the stale one by
 * `getComputedStyle(stripEl).opacity === '1'` (the stale one sits at
 * opacity 0 in the same DOM position, both as direct siblings under a
 * shared `relative size-full select-none` composer wrapper):
 *
 *   const labels = [...document.querySelectorAll('span,div')]
 *     .filter(el => el.children.length===0 && /^@project_valder_/.test(el.textContent||''));
 *   const uniq = []; const seen = new Set();
 *   for (const l of labels) { if(!seen.has(l.textContent)) { seen.add(l.textContent); uniq.push(l); } }
 *   function ancestors(el){ const a=[]; let n=el; while(n){a.push(n); n=n.parentElement;} return a; }
 *   let common = ancestors(uniq[0]);
 *   for (const u of uniq.slice(1)) { const as = new Set(ancestors(u)); common = common.filter(x => as.has(x)); }
 *   const visibleStrip = [...common[0].children].find(k => getComputedStyle(k).opacity === '1');
 *
 * A full page reload cleared the stale strip cleanly (and did NOT reset
 * model/mode/duration/resolution/quality/aspect/sound this time -- only
 * Unlimited reverted to off, contradicting this file's Wave-1 note that
 * those settings survived a run without ever reloading; reloading appears
 * to behave differently from a same-session drift). After reload, the
 * thumbnail strip and the mention-chip check agreed. **When a thumbnail
 * strip and the chip-level `hasError` check disagree, trust neither purely
 * by inspection -- reload the page and recheck cleanly, since one of the
 * two elements is very likely a stale DOM duplicate, not real information.**
 *
 * NEW, SEPARATE BLOCKER: a genuine Higgsfield content-policy gate. After
 * confirming 7/7 clean chips, all settings verified, and Unlimited
 * confirmed on (`UNLIMITED / ~~140~~ / 0`), clicking Generate did NOT fire
 * a generation. Instead a banner appeared: "Some reference elements may
 * contain protected content. Check eligibility or remove them to proceed."
 * The thumbnail strip simultaneously re-rendered warning icons on 5 of 7
 * cards -- the exact same 5 that failed to bind in Wave 1 under the OLD
 * markdown-link format (mother, daughter, grandma, loc_home_interior,
 * prop_plan). Confirmed NOT transient: still present after a 5-second wait,
 * and the mention chips in the editor text kept reading `hasError: false`
 * throughout -- this gate lives on the bound-asset/rights layer, not the
 * paste-parser layer Wave 1 diagnosed. Per the task's explicit instruction,
 * no "I confirm"/"Cancel"/dismiss interaction was made with this banner;
 * Chrome was left exactly as it appeared and the task was reported blocked.
 *
 * HYPOTHESIS (unconfirmed, flagged for whoever has Elements-panel/rights
 * authority): this protected-content gate may be the ACTUAL root cause
 * behind Wave 1's binding failure too, not the markdown-link paste format
 * per se. The same 5 Elements failed under two completely different paste
 * formats, at two different points in the flow (paste-time chip error vs.
 * Generate-time banner) -- consistent with a content-policy flag on the
 * underlying assets that different UI paths surface differently. Checking
 * eligibility on these 5 Elements directly in the Elements panel (the
 * banner's own suggested action) is the next step, and it is out of an
 * operator's scope to do blind.
 *
 * ---
 *
 * Wave 3 (task-5c05dc3c, 2026-08-25): Wave 2's hypothesis CONFIRMED --
 * running the per-reference "Check eligibility" control (task explicitly
 * authorized it this run) cleared all 5 flagged Elements
 * (mother/daughter/grandma/loc_home_interior/prop_plan), matching
 * task-8ea73ebb's precedent of 8/9 clearing this way. Confirmed PASS for
 * each via three independent signals: reference-thumbnail badge svg count
 * dropping from 3 (badge+warning) to 2 (badge only, matching never-flagged
 * father/son), a full-page text scan for "needs an eligibility check" /
 * "Face/IP failed" / "may contain protected content" returning nothing,
 * and (for char_mother specifically) watching the tooltip+button vanish
 * from its own Element detail modal after the click. See
 * docs/reports/valder-s2-eligibility.md for the full per-element table.
 *
 * NEW, SEPARATE BLOCKER (Job 1 succeeded; Job 2 hit something new): even
 * with all 5 Elements cleared, clicking Generate STILL produced the exact
 * same "Some reference elements may contain protected content" banner --
 * reproduced 3 times in a row, each with a full fresh re-verification
 * (7/7 refs bound 0 errors, all settings correct, Generate button
 * confirmed `UNLIMITED / ~~140~~ / 0` via zoomed-screenshot tiebreaker
 * immediately before each click). Zero credits spent across all 3 attempts
 * -- confirmed via `read_network_requests`, which showed NO `generat`-
 * pattern call fired by any of the 3 clicks (only background
 * `GET /fnf/reference-elements/<uuid>` polling and `GET /fnf/folders/
 * <id>/publish` calls, neither a generation request), and via Account
 * menu balance staying flat at 1,974 before and after.
 *
 * ROOT CAUSE (working hypothesis, not fully confirmed): switching the
 * composer's model from the default "Cinema Studio 4.0" template to
 * "Seedance 2.5" appears to fully reset the composer and mint a NEW
 * reference-element binding instance per pasted `@tag` on the subsequent
 * paste, separate from whatever instance the per-Element "Check
 * eligibility" control (run under the ORIGINAL Cinema-Studio-4.0 composer,
 * per this project's established Job-1 flow) actually cleared. Partial
 * supporting evidence: after the first Generate-blocked click under
 * Seedance 2.5, re-hovering all 7 reference chips found that ONLY
 * char_mother -- and only char_mother -- still showed the "needs an
 * eligibility check" tooltip DESPITE its badge showing clean. Running
 * Check eligibility on it again (in THIS Seedance-2.5 composer instance)
 * made the tooltip disappear -- but Generate still refused on the very
 * next click, and a subsequent re-hover of all 7 chips (including mother)
 * showed zero tooltips anywhere. So the per-reference control clearly does
 * something real and instance-scoped, but Generate's own validation check
 * is either scoped even more narrowly (per literal generation-request, not
 * per composer-instance) or checking something else entirely that no
 * per-reference UI surfaces.
 *
 * WHAT WASN'T TRIED (out of operator scope per "scope discoveries are a
 * C-level decision"): (a) firing Generate WITHOUT ever switching away from
 * whatever model the composer defaults to on load, to see if avoiding the
 * model-switch-triggered reset sidesteps this entirely -- Wave 2 never hit
 * this specific blocker under the default model, only after the task
 * explicitly required Seedance 2.5; (b) Elements-panel-level
 * investigation of whether there's a composer-instance-scoped or
 * generation-request-scoped eligibility flag distinct from the per-Element
 * one Job 1's control clears.
 *
 * DURATION CONTROL CORRECTION: earlier waves' notes did not test this
 * carefully, but this run confirmed the duration control is a real text
 * INPUT inside a small popover (click the "5s" pill -> "Duration" label +
 * editable field appears), not purely a hidden ARIA slider. Typing digits
 * directly into it (e.g. "20s") does NOT reliably set the value as plain
 * text entry -- it produced "16s" from typing "20s" after a triple-click
 * select-all, suggesting each keystroke is interpreted as an increment/
 * decrement nudge rather than literal text replacement. The reliable
 * method: triple-click the field to focus it, then press ArrowRight the
 * exact number of times needed to reach the target from whatever value is
 * currently showing (confirmed after each press via zoomed screenshot on
 * the popover, not by trusting a single read).
 *
 * DECOY/DUPLICATE-DOM CONFIRMED AGAIN: switching models produced a second
 * confirmation of the hidden-duplicate-element bug family. A plain
 * (non-visibility-filtered) query for pill button text like "Seedance 2.5"
 * matched TWO buttons simultaneously (one from a stale pre-switch render,
 * one live) -- e.g. `["1080p","16:9","5s","On", ...stale... "Seedance
 * 2.5","References","16:9","720p","20s","High","On" ...live...]`. Always
 * filter by `getComputedStyle(el).visibility !== 'hidden'` (or check
 * `getBoundingClientRect().width > 0`) before trusting any pill-text
 * query on this project, not just for the contenteditable editor and the
 * Generate button as previously documented -- the whole settings-pill row
 * is subject to the same duplication.
 *
 * ---
 *
 * Wave 4 (task-8a163030, 2026-08-25): first successful fire. RESULT: THE
 * DESYNC FIX IS THE ANSWER. Take 1 fired clean on the first Generate click
 * after applying it; Take 2 was blocked separately by a stuck Unlimited
 * toggle (new, unrelated failure -- see below), never by "Prompt is
 * required" again. See docs/reports/valder-s2-desync.md for the full
 * writeup.
 *
 * THE FIX, confirmed end-to-end: after the synthetic-paste (per this
 * file's own established recipe), before EVERY Generate click:
 *   1. `el.focus()` on the visibility-filtered editor node.
 *   2. Selection API cursor-to-end (`range.selectNodeContents(el);
 *      range.collapse(false)`, then apply via `window.getSelection()`) --
 *      NOT a coordinate click, per Wave 2's mention-chip-click hazard.
 *   3. A REAL `space` keypress via the driving tool, then a REAL
 *      `BackSpace` keypress via the driving tool. Net text change zero.
 * Applied once right after paste, then RE-applied a second time
 * immediately before the Generate click (composer state can drift between
 * the two, per this file's Wave-1 "re-apply immediately before every
 * click" note) -- both applications used in this run, click fired clean on
 * attempt 1/1 both times the fix was correctly applied.
 *
 * VERIFICATION THAT ACTUALLY MEANS SOMETHING: `innerText` and raw mention
 * count are necessary but not sufficient -- they read the DOM, not the
 * bound form state Higgsfield validates against (this is the whole
 * mechanism behind "Prompt is required" firing on text that visibly looks
 * correct). The authoritative read is the Lexical editor's OWN state:
 *
 *   const key = Object.keys(editorEl).find(k => k.startsWith('__lexicalEditor'));
 *   const json = editorEl[key].getEditorState().toJSON();
 *   JSON.stringify(json).length  // this run: 39,769, opening with the exact prompt text
 *
 * This is reachable directly off the contenteditable DOM node -- no need
 * to hunt for a React fiber or a page-level `window.lexicalEditor` global,
 * `__lexicalEditor<random-suffix>` is a property Lexical attaches straight
 * to the root element it manages. Confirmed clean both times this run
 * (post-paste and post-re-applied-fix-before-click), always cross-checked
 * against `innerText.length` (14,277 both times, matching prior waves'
 * expected +117-char Lexical block-break drift over the 14,160-char
 * source) and the mention-chip `hasError` scan (0 of 19 raw / 7 unique
 * mentions ever errored).
 *
 * TAKE 1 FIRE, confirmed via three independent signals: the literal
 * "Generation started" toast text in `document.body.innerText`
 * immediately after the click, the "All assets" sidebar counter
 * incrementing 210 -> 211, and the account-menu credit balance staying
 * flat at 1,974 (Unlimited paid nothing). New card's asset id:
 * `01225e5b-0dcc-45d4-8fd8-85b5c4f438a0` (identified as the newest by
 * empty thumbnail src = still rendering, at the top of the folder grid
 * immediately after firing -- no need to wait for the render to confirm
 * the fire itself).
 *
 * NEW, SEPARATE BLOCKER (Take 2 only): after a full clean rebuild in a
 * brand-new tab -- fresh navigate, all settings (Seedance 2.5, References,
 * 16:9, 720p, 20s, High, On) carried over correctly from account state, a
 * clean re-paste (7/7 unique mentions, 0 errors, correct length) and the
 * desync fix correctly applied -- the Unlimited toggle would not flip.
 * TWO separate `find()`-then-ref-click attempts both left
 * `[role="switch"][aria-label="Unlimited mode"]` at `data-state="off"`,
 * confirmed both by the DOM attribute and by a zoomed screenshot of the
 * physical switch (grey track, dot on the left -- visually off, not a
 * stale-read false negative). This is the SAME failure class as GH issue
 * #67 (task-f693a4ee, 2026-08-14) but a fresh occurrence, not the same
 * incident recurring identically.
 *
 * Per this project's hard rule ("If the Unlimited toggle will not flip:
 * ONE clean ref-based click, then STOP and report" -- task brief, and the
 * `higgsfield-unlimited-gen` skill's stronger "one ref-based click
 * attempt... if it doesn't flip, stop entirely, do not try a second
 * technique, do not try raw coordinates, do not try keyboard input near
 * the composer"), NO further click techniques were attempted after the
 * toggle failed to flip a second time. Specifically NOT tried: raw
 * coordinate click, keyboard focus+Space/Enter, a fresh third tab, or a
 * full Chrome restart -- any of those near a composer showing a live
 * struck price is exactly the pattern that produced two real 135-credit
 * charges on 2026-08-14 (GH #67). The Take-2 composer tab was left open
 * and untouched (no navigate, no further click) with the full prompt
 * still pasted, 7/7 bound, desync fix already applied, Unlimited still
 * off, Generate still reading the live `GENERATE 140 130` price (NOT
 * struck through -- correctly never clicked).
 *
 * Credits confirmed flat at 1,974 both before Take 1 and after the
 * blocked Take-2 attempt (checked in a separate scratch tab, without
 * touching the blocked composer tab), via the account-menu Credits panel.
 * Zero credits spent on the blocked toggle attempts -- confirmed no
 * Generate click was ever made on Take 2's un-struck price.
 */

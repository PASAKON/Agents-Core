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
 */

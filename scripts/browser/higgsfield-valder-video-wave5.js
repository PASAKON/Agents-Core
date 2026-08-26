/**
 * scripts/browser/higgsfield-valder-video-wave5.js
 *
 * Replay notes for Valder video wave 5 (task-40dd8087, 2026-08-26),
 * The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script — paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP, combined with real keyboard actions via the
 * `computer` tool where noted. Read scripts/browser/higgsfield-image-gen.js
 * first for the base recipe (desync fix, decoy editor, hidden duplicate
 * Generate button) and the wave4 script's notes (uncommitted on
 * agent/browser_operator-task-581d5c05 as of this wave — the
 * warning-triangle eligibility fix and the real-clipboard-paste method) —
 * this file only records what was NEW this wave.
 *
 * Result this wave: 9 clips fired, all clean, $0 spent (credits 1,918 open
 * and close, unchanged). Uncovered-scene priority list went from 10 scenes
 * with zero footage down to 2 (S7A, S7B) — see
 * docs/reports/valder-video-wave5.md for the full clip table and coverage
 * table.
 *
 * ============================================================
 * FINDING 1: closing a NON-LAST tab in the MCP tab group can still destroy
 * the whole group — not just Escape, as earlier waves documented.
 * ============================================================
 *
 * Closed a diagnostic cross-check tab via `tabs_close_mcp` while the
 * composer tab was still open (1 tab remained per the close call's own
 * response). The very next `tabs_context_mcp` call returned "No tab group
 * exists for this session." This happened mid-wave with no Escape key
 * involved anywhere nearby — the earlier "Escape can destroy the tab group"
 * finding (higgsfield-image-gen.js Wave 4) is not the only trigger.
 *
 * RECOVERY (confirmed working): `tabs_context_mcp({createIfEmpty: true})`
 * gets a fresh empty tab, then `navigate()` to the project URL. Everything
 * about the composer has to be rebuilt from scratch after this — do not
 * assume any prior state survives:
 *   - Model can reset all the way back to Cinema Studio 4.0 (not just
 *     720p/1080p and duration resetting, as documented before) — always
 *     re-select Seedance 2.5 FIRST, before touching anything else, and
 *     verify via `document.body.innerText.match(/Seedance 2\.5/)` before
 *     proceeding.
 *   - Composer prompt TEXT does sometimes survive via autosave across a
 *     `navigate()` (confirmed this wave), but do NOT trust it after a full
 *     tab-group teardown + fresh tab + fresh navigate — verify length and
 *     first/last-80 against source before firing, exactly as if pasting
 *     fresh.
 *
 * ============================================================
 * FINDING 2: the real macOS clipboard on this shared Mac gets overwritten
 * by another process — `pbcopy` alone is not sufficient insurance anymore.
 * ============================================================
 *
 * Staging S6's prompt: `pbcopy < s6-multicut.txt`, then several
 * verification/diagnostic tool calls, then the paste — landed as unrelated
 * Thai text (not S6's content) THREE times in a row, a different Thai
 * string each time. `pbpaste` confirmed the clipboard was genuinely holding
 * that Thai text, not a browser-side paste bug. This is real contention for
 * the OS clipboard from something else running on the machine (most likely
 * the CEO or another session actively copying text elsewhere), not a
 * Higgsfield/Lexical issue.
 *
 * Diagnostic that found the pattern: `pbcopy < file; sleep 2; pbpaste`
 * survived cleanly when nothing else was calling `pbcopy` in between — the
 * interference is bursty (coincides with periods of multi-tool-call
 * activity), not a fixed-interval overwrite.
 *
 * THE FIX: re-run `pbcopy < <promptfile>` as the LAST thing before the
 * paste, in the same tool-call batch as the focus/select-all/delete/paste
 * sequence (zero other tool calls — no diagnostic reads, no waits — in
 * between the `pbcopy` and the `Cmd+V` keypress). Verify content
 * immediately after with the usual length + first/last-80 + mention-count
 * check; if it's still wrong, `pbcopy` again and retry immediately rather
 * than investigating further — the fix is speed, not diagnosis.
 *
 * ============================================================
 * FINDING 3: confirmed firsthand — "long-lived tab lies about the
 * concurrency slot" (documented in the higgsfield-unlimited-gen skill,
 * previously theoretical for this operator, now measured directly twice).
 * ============================================================
 *
 * Twice this wave (S4C and S5), the primary composer tab's own
 * `document.querySelectorAll('[data-asset-id]')[0]` read `spinner: true`
 * at the ~30 minute mark, while a brand-new tab navigated to the same
 * project URL immediately showed `spinner: false` for the exact same card.
 * The render was actually done; the aging tab was just showing stale DOM
 * state for the spinner element specifically (not for everything — asset
 * counts and other reads on the same stale tab were still accurate).
 *
 * PRACTICAL RULE ADOPTED THIS WAVE: past the ~25-30 minute mark, do not
 * trust a `spinner: true` read from a tab that has been open through
 * multiple prior generations. Open a fresh tab, navigate to the same
 * project URL, and read the card there before concluding it's still
 * rendering. If the fresh tab confirms completion, either continue using
 * the fresh tab as the new primary (close the stale one) or do a full
 * `navigate()` reload on the primary tab as hygiene before firing the next
 * generation — both were used this wave depending on which was faster in
 * the moment.
 *
 * ============================================================
 * FINDING 4 (the headline diagnostic result this wave):
 * `@project_valder_loc_neighbor_door` does not bind — confirmed as a real
 * element-level bug, not a prompt-context collision, not a typo.
 * ============================================================
 *
 * Symptom: pasting a prompt containing this tag leaves it as literal text
 * in the editor (`el.innerText` shows `@project_valder_loc_neighbor_door`)
 * instead of resolving to a `data-beautiful-mention` chip with a UUID —
 * while every other tag in the same paste, including four+ other elements
 * in the same scene, resolves correctly.
 *
 * Attempts that did NOT fix it (S4A, in order):
 *   1. Fresh paste — fails.
 *   2. Wait 2s, re-check (rules out a resolution-timing race like the one
 *      documented in wave4 Part 1C) — still fails.
 *   3. Full page `navigate()` + fresh clear + fresh re-paste (this also
 *      reset composer settings back to 1080p/5s, rebuilt from scratch) —
 *      still fails.
 *   4. Select the literal text span in the DOM (including the preceding
 *      `@` — confirmed via TreeWalker that the `@` character sits in its
 *      OWN separate text node from the tag body, unlike resolved mentions)
 *      and real-keyboard retype it in place — **this corrupted the
 *      composer**: the tag duplicated (2 occurrences became 3) and
 *      "SEEDANCE" got truncated to "EEDANCE" a few characters away from the
 *      edit point. Recovered with a second full navigate + clean re-paste
 *      from clipboard, re-verified byte-exact against source.
 *
 * CTO's isolated test (run once at S5, per explicit one-attempt-only
 * instruction): paste `@project_valder_loc_neighbor_door` ALONE into a
 * completely empty composer (nothing else attached). **Still fails to
 * bind.** This rules out the substring-collision hypothesis (the tag
 * contains "neighbor" and `@project_valder_char_neighbor` is usually in the
 * same prompt) — it fails with zero other content present. Confirmed via
 * `?elements=1` → Locations tab that an element with this exact name does
 * exist in the project, so it is not a missing/renamed element either. Root
 * cause remains unconfirmed (possibly the split-text-node behavior from
 * attempt 4 above, possibly something backend-side specific to this one
 * element) but is conclusively NOT: a typo, a prompt-context collision, or
 * a timing race.
 *
 * STANDING FIX FOR THIS ELEMENT, adopted for the rest of this project: do
 * not spend more than the one diagnostic attempt per scene. Paste the
 * scene's prompt, verify the mention count, and if this one specific tag
 * comes back unresolved, fire anyway with it unbound — the surrounding
 * prose already describes the object in full, so the scene still generates
 * correctly, just without that one image reference attached. Flag it in
 * the clip table notes each time it recurs so a human with Elements-panel
 * write access can eventually re-save/re-upload the element.
 *
 * ============================================================
 * Standard fire sequence used every time this wave (no changes from the
 * documented method, listed here for completeness):
 * ============================================================
 *
 *   1. `pbcopy < docs/prompts/valder/<scene>-multicut.txt` (re-run
 *      immediately before paste if any other tool calls happened since the
 *      last copy — see Finding 2).
 *   2. Focus the correct (non-hidden) contenteditable via `el.focus()` in
 *      JS, not a coordinate click — coordinate clicks on this composer
 *      intermittently land on the wrong element after any layout shift
 *      (model change, dropdown close, tab-group recreation).
 *   3. Real `Cmd+A`, `Delete`, `Cmd+V` via the `computer` tool, in that
 *      order, no gaps.
 *   4. Verify: normalized (whitespace-collapsed) length + first/last 80
 *      chars match source exactly, AND unique `data-beautiful-mention`
 *      count matches the element count from the task brief. Any mention
 *      still starting with `@project_` (not resolved to a UUID) is a real
 *      binding failure, not a false read.
 *   5. Desync fix: `el.focus()`, Selection API `range.selectNodeContents`
 *      + `collapse(false)` to put the cursor at the end, then one real
 *      Space keypress and one real BackSpace keypress via `computer`.
 *      Re-apply this step immediately before every Generate click, not
 *      just once after paste.
 *   6. Zoom the reference-thumbnail strip (region roughly
 *      `[465, <strip_y>, <strip_y + ~575>, <strip_y + 70>]` — the strip's
 *      y-position moves depending on scroll/composer state, screenshot
 *      first to find it fresh each time). Click every warning-triangle
 *      icon found, wait ~3-4s, re-hover elsewhere and re-zoom to confirm
 *      clear. Sometimes needs a second pass — one triangle-click resolved
 *      the check but a second card on the same strip still showed a
 *      triangle on the first re-zoom this wave (S5B) — always re-verify
 *      the WHOLE strip clear before proceeding, don't just trust the count
 *      of clicks made.
 *   7. Zoom the Generate button region immediately before clicking —
 *      confirm `UNLIMITED / ~~<price>~~ / 0` with the strike-through
 *      visible. Click via `computer` at the button's real on-screen
 *      coordinate (varies with composer layout — re-locate each time, do
 *      not reuse a coordinate from an earlier screenshot).
 *   8. Verify fire: `document.body.innerText.match(/generation started/ig)`
 *      plus `document.querySelectorAll('[data-asset-id]')[0]
 *      .getAttribute('data-asset-id')` for the new clip's id.
 *   9. Poll cadence: first check at ~20min (renders never finish before
 *      that), then every 5min. Past ~25-30min, cross-check on a fresh tab
 *      per Finding 3 before trusting a `spinner: true` read.
 *  10. Pre-stage the NEXT scene's prompt into the composer during the
 *      current render's wait — safe, since editing composer text does not
 *      touch the server-side in-flight job. Re-verify everything (mentions,
 *      settings, Unlimited, reference-strip flags) fresh immediately before
 *      the actual click, never trust the staging-time check.
 */

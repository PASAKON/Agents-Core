/**
 * scripts/browser/higgsfield-valder-plate-regen5.js
 *
 * Replay notes for task-d9001e45 (2026-08-26), Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into javascript_tool
 * against an already-open, already-logged-in tab via claude-in-chrome MCP.
 * Thin addendum to higgsfield-image-gen.js (read that first for the base
 * paste/desync/verify recipe) and higgsfield-valder-neighbor-plates.js (site
 * bugs and their fixes) -- this file only records what was NEW or reusable
 * this run.
 *
 * Result: 6/6 plates (5 audit findings + 1 urgent mid-session amendment),
 * 6 generations, 12 credits total (2 each, GPT Image 2/Medium/1K), 0 flagged,
 * 0 reshoots. Balance 1,930 -> 1,918. Full per-plate table + Element UUIDs
 * in docs/reports/valder-plate-regen-5.md.
 *
 * Folder UUIDs used this run (same Valder Collection No.7 project, already
 * discovered by an earlier run -- see higgsfield-valder-neighbor-plates.js):
 *   Character: ae0bb5a3-9f66-4e95-8112-c2939e9de56e
 *   Location:  259e1dc4-da1f-4de0-8b15-0a78ec2e94f1
 *   Prop:      cbb3d9aa-911f-454b-8132-f3fe1d2c73a7
 *
 * NEW FINDINGS THIS RUN:
 *
 * 1. A mid-session task amendment arrived as an injected user-turn message
 *    ("[CTO] URGENT SIXTH PLATE...") rather than through the original task
 *    text. Before treating it as authoritative, re-read TASK.md on disk --
 *    it had genuinely been appended with a matching "## AMENDMENT" section.
 *    This is the cheap, conclusive check: a claim about the task file is
 *    either checkable against the file or it isn't, and it was. Do this
 *    before reprioritizing any work off an unverified mid-turn instruction,
 *    especially one that also raises a credit cap.
 *
 * 2. Clearing the composer reliably, every time, without the "concatenates
 *    with stale content" failure mode documented in earlier runs: don't just
 *    `cmd+a` + `Delete` once. Use the Selection API + `beforeinput`
 *    `deleteContentBackward` dispatch, THREE times in a row with a ~150ms
 *    gap, then check `el.innerText.length` is 0 or 1 (a lone `\n` is fine).
 *    One pass frequently leaves stale trailing text; three passes cleared it
 *    every single time across all 6 plates this run:
 *      function clearOnce() {
 *        const range = document.createRange();
 *        range.selectNodeContents(el);
 *        const sel = window.getSelection();
 *        sel.removeAllRanges();
 *        sel.addRange(range);
 *        el.dispatchEvent(new InputEvent('beforeinput', {bubbles:true,
 *          cancelable:true, inputType:'deleteContentBackward'}));
 *      }
 *      clearOnce(); await sleep(150); clearOnce(); await sleep(150); clearOnce();
 *    Verified by explicit before/after length diff in this run's very first
 *    clear attempt (plate 6): first clear alone left 2953 chars (concatenated
 *    with the OLD paste) instead of the fresh source's 1500 -- caught by the
 *    length check, not by eyeballing.
 *
 * 2b. When clear+paste is done as ONE combined script (clear, then
 *    immediately paste in the same call), the leftover-content bug can still
 *    slip through even with the 3x clear loop, because the paste's own
 *    `range.selectNodeContents` + `ClipboardEvent` can land before the DOM
 *    has settled from the last clear. Splitting clear and paste into TWO
 *    separate `javascript_tool` calls (clear fully, verify length in the
 *    tool result, THEN paste in a second call) is more reliable and makes
 *    the failure visible immediately rather than silently. Do this as the
 *    default pattern now.
 *
 * 3. Quality/Resolution pill dropdowns on this composer intermittently do
 *    not respond to the FIRST `find`-ref click (dropdown never opens, no
 *    `[role="option"]` elements appear) but DO respond to a direct raw JS
 *    `.click()` on the button located via `querySelectorAll('button')`
 *    text match. When a pill click produces zero `[role="option"]` results,
 *    don't retry `find` -- fall back immediately to the JS button-text scan
 *    + `.click()`. This happened on Plates 4 and 5 (not 1-3), so it is
 *    intermittent, not a fixed characteristic of this composer instance.
 *
 * 4. The "Generation started" toast is not reliable evidence either way this
 *    run -- it was silently ABSENT on 2 of 6 real, successful, credit-charged
 *    generations (plates 4 and 5), while the other 4 showed it normally. In
 *    both toast-less cases, `[...document.querySelectorAll('[data-asset-id]')]`
 *    on the folder page showed a new id with `data-job-status="in_progress"`
 *    immediately after the click -- this is what actually confirmed the fire,
 *    not the toast. Always cross-check the asset list before concluding a
 *    click no-op'd just because no toast appeared; only treat it as a genuine
 *    no-op if the asset list ALSO shows no new id and no status change.
 *
 * 5. Composer settings (GPT Image 2 / Medium / 1K) persisted correctly across
 *    in-project folder-to-folder navigation (Character -> Prop -> Character
 *    -> Location) within a single continuous session -- did not need a full
 *    Chrome restart or even a tab reload this run, so the "settings reset on
 *    navigate" warning from earlier waves did not reproduce here. Composer
 *    PROMPT TEXT, however, always carried over the previous folder's last
 *    prompt and needed a fresh clear+paste every time -- never assume a
 *    fresh folder nav means a blank composer.
 *
 * 6. Element re-pointing flow, confirmed stable across 6 elements this run
 *    (all in the SAME project, mixing Character/Location/Prop folders):
 *      a. Elements panel (left sidebar) > Search (click button, THEN type --
 *         clicking the search icon alone does not focus the input) > exact
 *         lowercase element id.
 *      b. Click the result card > wait ~3s (stale-dialog-singleton bug is
 *         real -- verify the Element ID field text matches before trusting
 *         the shown image) > Edit.
 *      c. If a confirmation dialog appears ("Edit 'X'? used in N
 *         generations..."), click "Edit Original" -- NEVER "Duplicate &
 *         Edit", which would silently create a new Element and break the
 *         UUID-preservation the task depends on. This dialog did NOT appear
 *         for one element this run (Plate 5's `loc_new_interior`, used in
 *         only 1 generation) -- Edit went straight to the Edit panel with
 *         the same Element ID field, which is an equally valid confirmation
 *         that it's the original, not a duplicate.
 *      d. Click the "+" beside the existing thumbnail row -> Uploads tab
 *         opens by default -> click "Generations" tab -- if the target
 *         asset id's `[aria-label]` tile count is 0, click Generations AGAIN
 *         (known 2-click quirk, reproduced on 2 of 6 elements this run,
 *         first click sufficient on the other 4).
 *      e. Click the new asset's tile (found via
 *         `document.querySelectorAll('[aria-label="<assetId>"]')`, confirm
 *         count is exactly 1 before clicking -- a stale Uploads-tab dialog
 *         can otherwise create ambiguity).
 *      f. This ADDS a second thumbnail rather than replacing the first --
 *         click the NEW thumbnail to select it as primary (confirmed by the
 *         larger preview switching to the new image), THEN click the OLD
 *         thumbnail to select it, THEN click the trash icon to delete it.
 *         Order matters: select-new-as-primary before deleting old, so the
 *         element is never left pointing at nothing mid-edit.
 *      g. Save. Verify via a FULL page navigate() back to the project root
 *         (not just closing the dialog) -- reopen Elements > Search > open
 *         card, and read "Last changes" (should read "N minute(s) ago") plus
 *         the Element ID field and the new image together in one screenshot.
 *
 * Standard per-plate loop used throughout this run:
 *   1. Navigate to folder URL (or reuse current folder if same as last plate).
 *   2. If composer shows Video-mode settings (Cinema Studio 4.0/1080p/etc)
 *      or High/2K, rebuild GPT Image 2 / Medium / 1K via the quality and
 *      resolution pills (real clicks worked for all 6 plates this run --
 *      no PointerEvent-sequence workaround needed, unlike some earlier waves).
 *   3. Clear the editor per finding #2/#2b above, verify length.
 *   4. Paste via synthetic ClipboardEvent, verify normalized length exactly
 *      matches source, and verify `[data-beautiful-mention]` UUID(s) resolve
 *      to the expected `@project_valder_prop_mark` /
 *      `@project_valder_prop_signature` UUIDs when a plate's prompt tags them.
 *   5. Desync fix: focus, Selection API cursor-to-end, REAL `computer` Space
 *      key, REAL `computer` BackSpace key -- immediately before every
 *      Generate click, every single time (per higgsfield-image-gen.js).
 *   6. Click Generate via the synthetic PointerEvent sequence (pointerdown/
 *      mousedown/pointerup/mouseup/click, all on the one REAL non-hidden
 *      Generate button located via `getComputedStyle(b).visibility!=='hidden'
 *      && b.offsetParent && /generate/i.test(b.innerText)`). This worked on
 *      the very first attempt for all 6 plates this run -- no repeat-click
 *      no-op cycle was seen.
 *   7. Confirm fire via the `[data-asset-id]` list (see finding #4) -- don't
 *      rely on the toast alone.
 *   8. Poll `data-job-status` on that specific asset id until `completed`;
 *      check `[title]` elements on the card for the safety-flag string
 *      before treating it as a pass. 0 of 6 were flagged this run.
 *   9. Visually verify against the task's checklist via `zoom` on the card
 *      region at its on-page position (query the card's own
 *      `getBoundingClientRect()` first -- folder-grid position shifts as
 *      toasts/dialogs open and close, don't assume the position from an
 *      earlier screenshot is still correct).
 *  10. Re-point per finding #6 above.
 *  11. Verify via full page navigate() + re-open (finding #6g).
 */

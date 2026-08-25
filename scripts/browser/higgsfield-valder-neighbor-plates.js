/**
 * scripts/browser/higgsfield-valder-neighbor-plates.js
 *
 * Replay notes for the neighbour/social-acceptance + money-running-out arc
 * plates, task-598b6088 (2026-08-26), Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3).
 *
 * NOT a standalone Node/Playwright script -- paste snippets into javascript_tool
 * against an already-open, already-logged-in tab via claude-in-chrome MCP.
 * Thin addendum to higgsfield-image-gen.js (read that first for the base
 * paste/desync/verify recipe) -- this file only records what was NEW this run.
 *
 * Result: 15/15 plates, 16 generations (plate 1 fired twice), 32 credits
 * total, 0 flagged. Full per-plate table + Element UUIDs in
 * docs/reports/valder-neighbor-plates.md.
 *
 * Folder UUIDs discovered this run (Valder Collection No.7 project):
 *   Character: ae0bb5a3-9f66-4e95-8112-c2939e9de56e
 *   Location:  259e1dc4-da1f-4de0-8b15-0a78ec2e94f1
 *   Prop:      cbb3d9aa-911f-454b-8132-f3fe1d2c73a7
 *
 * NEW FINDINGS THIS RUN:
 *
 * 1. STUCK GENERATE BUTTON, ZERO NETWORK REQUEST FIRED -- new failure class,
 *    not the documented "Prompt is required" desync. On plate 12
 *    (loc_shop_int), after re-navigating folders several times, the Generate
 *    button silently no-op'd on FOUR separate clean attempts: a real
 *    `computer` coordinate click, a real `find`-ref click, each preceded by a
 *    freshly re-applied desync fix (focus + Selection API cursor-to-end + real
 *    Space + real BackSpace). Verified via `read_network_requests` that NONE
 *    of the four clicks even attempted a network call -- ruling out an
 *    auth/session issue and confirming zero cost on every attempt (also
 *    cross-checked via the folder's top card staying unchanged).
 *    FIX: a full synthetic PointerEvent sequence dispatched via JS --
 *      for (const [type, Ctor] of [['pointerdown',PointerEvent],
 *        ['mousedown',MouseEvent],['pointerup',PointerEvent],
 *        ['mouseup',MouseEvent],['click',MouseEvent]]) {
 *        btn.dispatchEvent(new Ctor(type, {bubbles:true, cancelable:true,
 *          clientX:cx, clientY:cy, button:0}));
 *      }
 *    -- fired correctly on the very first attempt. This worked reliably for
 *    EVERY subsequent Generate click in this run (used for plates 13-15,
 *    1-2, 7-9 without a single further no-op) -- recommend using this as the
 *    DEFAULT click method for Generate from now on, falling back to a real
 *    `computer` click only if the synthetic sequence itself fails.
 *
 * 2. KEYBOARD INPUT CAN GO COMPLETELY DEAD ON A LIVE COMPOSER INSTANCE, EVEN
 *    ACROSS A FULL RELOAD. After creating plate 11's Element (several dialog
 *    open/close cycles, folder navigations), the prompt editor stopped
 *    accepting ANY real keyboard input: `cmd+a`, `Delete`, `BackSpace`, and
 *    even a plain letter key all did nothing to `target.innerText`, while
 *    `document.activeElement === target` and Selection API state were both
 *    verified correct before every attempt. A full page navigate() (not just
 *    tab reload) did NOT fix it -- same symptom reproduced immediately after.
 *    FIX: select the content via the Selection API (`range.selectNodeContents
 *    (target)`, NOT collapsed) then dispatch a synthetic Input Event instead
 *    of a keyboard event:
 *      target.dispatchEvent(new InputEvent('beforeinput', {bubbles:true,
 *        cancelable:true, inputType:'deleteContentBackward'}));
 *    This cleared the editor in one call, and normal real keyboard input
 *    (space/backspace for the desync fix) worked again immediately afterward
 *    -- the dead-input state appears to be a one-time Lexical desync that a
 *    single `beforeinput` dispatch resets, not a permanent break. If a
 *    clear-then-paste produces a length that doesn't match your source
 *    (concatenated with stale content), this is very likely why -- check
 *    `target.innerText.slice(0,120)` AND `.slice(-120)` after every clear,
 *    not just the length, since stale content can land at either end
 *    depending on where paste/deletion cursor state actually was.
 *
 * 3. ACCOUNT-WIDE LOGOUT MID-SESSION, cookies domain-wide not per-tab. Right
 *    after Generate fired on plate 3, a "Welcome to Higgsfield / Sign up"
 *    modal appeared and the tab bounced to the logged-out
 *    https://higgsfield.ai/generate home. `document.cookie` showed no Clerk
 *    session value (no `__session`, only `__client_uat`). This is an
 *    account-level logout (confirmed by re-navigating directly to the
 *    project URL and still seeing Login/Sign up) -- if another operator
 *    shares this Chrome profile, their tab is logged out too, mid-queue.
 *    Filed a blocker and stopped rather than logging back in (hard stop).
 *    RECOVERY once a human re-authenticates: get a fresh `tabs_context_mcp`
 *    (old tab group may be gone), re-navigate, and before assuming a plate
 *    needs refiring, CHECK THE FOLDER FIRST -- the folder's top
 *    `[data-asset-id]` card plus its `data-job-status` is the cheapest way to
 *    confirm whether a Generate that fired right before the outage actually
 *    completed server-side. In this run it had (plate 3 completed and was not
 *    flagged), saving a duplicate 2-credit spend.
 *
 * 4. SCREENSHOT CAPTURE CAN BREAK ON ONE TAB WHILE JS KEEPS WORKING. After
 *    plate 1 v2's generation completed, `computer screenshot` / `zoom` on
 *    that tab started timing out on `Page.captureScreenshot` (30s+) on every
 *    attempt, while `javascript_tool` (`Runtime.evaluate`) kept returning
 *    instantly and correctly the whole time. Did not investigate root cause
 *    (not worth the budget) -- just opened a second tab in the same
 *    `tabs_context_mcp` group (`tabs_create_mcp`, no `createIfEmpty` needed
 *    since the group already existed) and did all subsequent visual
 *    verification there. The original tab was left completely alone
 *    afterward. If a screenshot/zoom call times out on `Page.captureScreenshot`
 *    specifically (not a generic "renderer frozen" from a JS timeout), don't
 *    bother retrying on the same tab -- open a new one immediately.
 *
 * 5. Element category auto-detection is not fully reliable. Plate 3
 *    (project_valder_loc_neighbor_door, an exterior LOCATION shot) got
 *    auto-categorised as "Prop" on creation via the "Auto" category setting
 *    in the New Element dialog. Caught by checking the element's `Category`
 *    field in its detail panel after creation; fixed via the Edit dialog's
 *    Category dropdown. All other 14 elements this run auto-categorised
 *    correctly -- this seems to be an occasional model mistake, not a
 *    systemic bug, but worth a quick post-creation category check on any
 *    Location/Character plate specifically (Props seem to be the default the
 *    detector falls back to).
 *
 * 6. Getting an Element's own UUID (as opposed to the source asset's UUID)
 *    reliably: open the newly-created element's detail card (click the
 *    element tile in the Elements panel -- NOT the composer's reference
 *    tray), then read network requests for the pattern
 *    `item_type=reference_element` in a `/fnf/comments?...` GET call -- its
 *    `asset_id` query param is actually the ELEMENT's UUID (confusingly
 *    named), not the source generation asset. Confirmed exact match against
 *    the tag's `data-beautiful-mention` value when the element was
 *    subsequently referenced via @mention in another plate's prompt.
 *    `read_network_requests` with `clear:true` right before the click keeps
 *    this cheap and unambiguous (element-creation button clicks generate a
 *    few dozen requests otherwise).
 *
 * Standard per-plate loop used throughout (all folders: Character, Location, Prop):
 *   1. Navigate to folder URL. If composer loads in Video mode (common on a
 *      fresh navigate), synthetic-click the small "Image" mode toggle
 *      (bottom-left of composer, above the settings pills).
 *   2. Verify/rebuild GPT Image 2 / Medium / 1K via synthetic PointerEvent
 *      clicks on the quality and resolution pills + their dropdown options
 *      (real `computer` clicks work fine for these UNLESS the Generate-button
 *      class of stuck-click bug is active -- if pills stop responding too,
 *      switch them to synthetic clicks as well).
 *   3. Clear the editor: try real `cmd+a` + `Delete` (verify length via a
 *      FRESH `querySelectorAll` each time, never reuse a cached DOM
 *      reference -- Lexical replaces nodes on re-render and a stale reference
 *      will silently report the OLD length forever). If real keys don't
 *      clear it, use the `beforeinput`/`deleteContentBackward` fix from
 *      finding #2 above.
 *   4. Paste via synthetic `ClipboardEvent`, verify normalized length +
 *      `data-beautiful-mention` count/values against expectation.
 *   5. Desync fix: focus, Selection API cursor to end, real Space, real
 *      BackSpace -- immediately before every Generate click, not just once.
 *   6. Click Generate via the synthetic PointerEvent sequence from finding #1
 *      (default now, not a fallback). Verify via a fresh `[data-asset-id]`
 *      query on the folder (top card's id + `data-job-status`) -- cheaper and
 *      more reliable than waiting for the "Generation started" toast, which
 *      can lag or be silently absent even on a successful fire.
 *   7. Poll `data-job-status` on that specific asset id (10s intervals) until
 *      `completed`; check `[title]` elements on the card for the safety-flag
 *      string before treating it as a pass.
 *   8. Visually verify against the task's checklist via `zoom` on the card
 *      region (or open the card for a bigger view if small details like a
 *      belt buckle or collar pin need checking).
 *   9. Elements > Search for the exact lowercase ID > "Create element" if no
 *      match > click the empty drop-zone > Generations tab (usually needs 2
 *      clicks: `tab.click()` once, check `aria-label` count, click again if 0)
 *      > find the tile by `[aria-label="<assetId>"]` inside the Generations
 *      dialog specifically (there can be a stale Uploads-tab dialog still in
 *      the DOM) > click it > Create > read network for
 *      `item_type=reference_element` to get the Element's own UUID (finding
 *      #6).
 */

/**
 * scripts/browser/higgsfield-valder-video-wave4.js
 *
 * Replay notes for Valder video wave 4 (task-581d5c05, 2026-08-26),
 * The Valder Collection No.7
 * (https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3/).
 *
 * NOT a standalone Node/Playwright script — paste snippets into
 * javascript_tool against an already-open, already-logged-in tab via
 * claude-in-chrome MCP, combined with real keyboard actions via the
 * `computer` tool where noted. Read scripts/browser/higgsfield-image-gen.js
 * and higgsfield-valder-s2-fire.js first for the base recipe (desync fix,
 * decoy editor, hidden duplicate Generate button) — this file only records
 * what was NEW this wave.
 *
 * ============================================================
 * FINDING 1 (the headline result): the protected-content gate's
 * "Check eligibility" control IS the warning-triangle icon itself.
 * ============================================================
 *
 * Prior waves (see valder-s2-eligibility.md, valder-s2-fire.js) searched for
 * a panel-level "Check eligibility" button and sometimes found one in the
 * Elements panel's per-Element detail modal. Nobody had tried the far more
 * obvious location: the warning-triangle overlay rendered directly on the
 * flagged card in the composer's own reference-thumbnail strip, right where
 * the prompt is already being built.
 *
 * THE FIX:
 *   1. After pasting a prompt and confirming N/N mentions bound with 0
 *      errors, screenshot/zoom the reference-thumbnail strip immediately
 *      above the composer (the row of small avatar-style cards, one per
 *      attached Element, each showing an @tag label underneath).
 *   2. Any card showing a white warning-triangle icon (⚠, roughly centred
 *      on the thumbnail) is flagged. Click directly on the triangle icon.
 *   3. No menu, no dialog, no dropdown appears. The icon changes instantly
 *      to a small loading spinner. Confirmed via `read_network_requests`:
 *      the click fires `POST /fnf/reference-elements/<uuid>/ip-detect`
 *      (200), followed by a few `GET /fnf/reference-elements/<uuid>` polls
 *      (200) — a live face/IP eligibility re-check against that specific
 *      asset. Within a couple of seconds the spinner clears to the card's
 *      normal hover state (X-to-remove, expand icon) and the triangle is
 *      gone for good.
 *   4. Re-zoom the whole strip to confirm zero triangles remain, THEN
 *      proceed to Generate as normal (desync fix, zero-digit/struck-price
 *      check, etc. — nothing about that flow changes).
 *
 * Confirmed working twice independently in one session: on
 * `char_grandma` (an ORIGINAL Element used since wave 1, not part of any
 * "new batch") and on `prop_frame` (one of the 2026-08-26 batch of 15 new
 * plates). Both cleared identically. This generalizes: STANDING PROCEDURE
 * (CEO/CTO instruction, 2026-08-26) — after attaching a scene's elements
 * and BEFORE clicking Generate, always scan the reference strip for
 * triangles and click every one found. Treat this as a normal step in the
 * fire sequence for every scene, every wave, going forward — not a
 * troubleshooting branch.
 *
 * ============================================================
 * FINDING 2: the flag is NOT a fixed property of an Element or its
 * creation date — it's tied to the current image asset, and can be
 * cleared two independent ways.
 * ============================================================
 *
 * `char_grandma` fired clean in wave 3 (no flag), was flagged when this
 * wave started, and — separately from the triangle-click fix above —
 * cleared itself with ZERO operator action the moment a concurrent
 * image-plate task (`task-d9001e45`) regenerated her underlying plate onto
 * the same UUID. Confirmed by pasting the canonical S2 prompt fresh after
 * that regen: `char_grandma`'s card showed no triangle at all, while
 * `prop_frame` (not part of that regen batch) was still flagged and needed
 * the manual triangle-click.
 *
 * CONSEQUENCE: never assume a scene is permanently blocked from a past
 * wave's finding. Elements can flip between clear and flagged over time
 * (looks like a periodic automated rescan on Higgsfield's side, not
 * anything caused by this project). Always re-check the live reference
 * strip for the CURRENT state before deciding a scene is stuck.
 *
 * DIAGNOSTIC ONE-LINER — read live network activity for the ip-detect
 * pattern to confirm a triangle-click actually triggered a real check
 * (rather than a stale/cosmetic re-render):
 *
 *   // call read_network_requests with urlPattern: "ip-detect"
 *   // expect: POST /fnf/reference-elements/<uuid>/ip-detect, 200
 *
 * The toast text itself is uninformative and identical every time
 * regardless of which/how-many Elements are flagged:
 *   "Some reference elements may contain protected content.
 *    Check eligibility or remove them to proceed."
 * It renders as a `Toastify__toast` element (not a modal, not inline on
 * a chip, not on the Generate button). It never names the flagged
 * Element(s) — only the reference-strip triangle icons do that, visually.
 * Zero network request of the `generat*` family fires when this gate
 * blocks a click — the refusal is entirely client-side, and the credit
 * ledger never moves.
 *
 * ============================================================
 * FINDING 3 (process fix, not a site bug): use the REAL OS clipboard for
 * prompt entry, not LLM-retyped/re-derived text — at any encoding.
 * ============================================================
 *
 * At ~15-30KB per prompt file, having the operating model retype or
 * re-derive the prompt text as a literal inside a `javascript_tool` call
 * — whether as raw text or base64 — is NOT reliable. Two distinct silent
 * corruptions were caught this wave before either reached the composer:
 * a hard truncation partway through generation with no error, and a
 * separate attempt that passed a length check and a first/last-80-char
 * check but failed a full-content checksum against the source file
 * (a wrong character existed somewhere in the middle). A base64 chunk
 * re-transcription — the method that worked fine for shorter (~15-21KB)
 * prompts in earlier fires this same wave — also came out one character
 * off on a ~10KB chunk when retyped by hand for a longer file. All of
 * these are LLM-transcription-scale risks, not site bugs, and they scale
 * with prompt length.
 *
 * THE FIX — use for every prompt paste from now on, any length:
 *
 *   1. In a real Bash shell (NOT inside the browser): `pbcopy <
 *      docs/prompts/valder/<scene>-multicut.txt`. This loads the exact
 *      file bytes onto the macOS clipboard with zero LLM involvement.
 *   2. Clear the composer as usual: real `Cmd+A` then `Delete` via the
 *      driving tool (confirm `innerText.length <= 1` after).
 *   3. Focus the correct (non-hidden) contenteditable node — same
 *      decoy-filter as always: `getComputedStyle(el).visibility !==
 *      'hidden'`.
 *   4. A REAL `Cmd+V` keypress via the driving tool. This is a genuine OS
 *      paste event, not a synthetic `ClipboardEvent` — Lexical handles it
 *      the same way (confirmed: same desync risk, same fix applies, see
 *      below), but the content itself can never be corrupted by
 *      generation, because no generation touches it.
 *   5. VERIFY with a whitespace-normalized weighted checksum against the
 *      source file, not just length/first-80/last-80 (those three checks
 *      all passed on the corrupted attempt above and still missed the
 *      error):
 *
 *        // in the page:
 *        const stripped = el.innerText.replace(/\s+/g, ' ').trim();
 *        let sum = 0;
 *        for (let i=0;i<stripped.length;i++)
 *          sum = (sum + stripped.charCodeAt(i)*(i%97+1)) % 1000000007;
 *
 *        # in bash, on the source file:
 *        python3 -c "
 *        import re
 *        with open('docs/prompts/valder/<scene>-multicut.txt', encoding='utf-8') as f:
 *            t = f.read()
 *        stripped = re.sub(r'\s+', ' ', t).strip()
 *        s = 0
 *        for i,c in enumerate(stripped):
 *            s = (s + ord(c)*(i%97+1)) % 1000000007
 *        print(s, len(stripped))
 *        "
 *
 *      Whitespace must be normalized before hashing because Lexical
 *      inserts its own extra paragraph-break newlines on paste — that is
 *      cosmetic and expected, not corruption. Confirmed on S1 (30,921
 *      source bytes): exact checksum match both sides on the first
 *      real-clipboard attempt.
 *   6. The desync fix (focus, Selection-API cursor-to-end, one real Space
 *      then one real BackSpace) still applies exactly as before, applied
 *      once after paste and re-applied immediately before every Generate
 *      click — a real OS paste does NOT make Lexical's internal state
 *      binding any more reliable on its own.
 *
 * This is also strictly cheaper: no giant string literal has to be
 * generated or embedded in any tool call at all.
 *
 * ============================================================
 * FINDING 4: the Generate button's price display for VIDEO on this
 * project (carried over from wave 3, reconfirmed) — struck-through
 * price + `0` is correct and expected, NOT an anomaly.
 * ============================================================
 *
 *   struck-through price then `0`   -> Unlimited working, CLICK
 *   bare "Generate", nothing else   -> fine, CLICK
 *   live price, NOT struck through  -> Unlimited OFF, DO NOT CLICK
 *
 * Read via a zoomed screenshot of the button region (~180x100px around
 * it), not `innerText` alone — a hidden duplicate button can make
 * `innerText` queries return stale or ambiguous text on this project.
 *
 * ============================================================
 * Isolating the newest asset id after a fire (no ambiguity, no
 * ancestor-walk guessing):
 * ============================================================
 *
 *   document.querySelectorAll('[data-asset-id]')[0]
 *     .getAttribute('data-asset-id')
 *
 * Cards are ordered newest-first. Confirmed this wave on every fire.
 *
 * ============================================================
 * Confirming a render's true status — do not trust a tab open more than
 * ~10-15 minutes without a fresh-tab cross-check.
 * ============================================================
 *
 * `document.body.innerText.match(/processing|generating/ig)` can return
 * `null` on a genuinely still-rendering card for one read (a DOM-render
 * timing gap on that specific poll), even though the card's own spinner
 * element (`cv.querySelector('svg[class*="animate"]')` truthy, no
 * `<video>` child) confirms it is still in flight. When the text check and
 * the element check disagree, or when a long-lived tab's read looks
 * suspiciously "free" for something fired only minutes ago, open a FRESH
 * tab, navigate to the same project URL, and re-check there — this
 * project's documented "long-lived tab lies about the concurrency slot"
 * issue (see higgsfield-unlimited-gen skill) cuts both ways: it can also
 * make a genuinely-still-rendering card look prematurely finished on a
 * tab that has been open a while.
 */

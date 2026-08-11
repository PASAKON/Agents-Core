/**
 * scripts/browser/higgsfield-jumpcut-gen.js
 *
 * Replay helpers for the Higgsfield jump-cut generation flow
 * (https://higgsfield.ai/ai/video — Seedance 2.5, 20s/21:9/720p/Bitrate High).
 *
 * NOT a standalone Node/Playwright script — this repo has no browser
 * automation runtime (no package.json, no playwright/puppeteer dep). Each
 * function here is meant to be pasted into a single `javascript_tool` call
 * against the already-open, already-logged-in Higgsfield tab via the
 * claude-in-chrome MCP, replacing the manual click-by-click steps a model
 * would otherwise re-derive by hand every wave.
 *
 * Validated end-to-end on Wave 2 (task-1ecf3dd2, 2026-08-11) for one
 * generation (Peephole check #1 jump-cut). Findings baked in below.
 *
 * Flow for one scene, using these helpers:
 *   1. Model finds the target History card (by distinctive VISUAL text) and
 *      clicks its Recreate icon — ALWAYS verify via the "Copy" tooltip on
 *      hover first (hfFindRecreateButtonByText helps locate the card+button;
 *      the actual click must go through the driving tool's `hover`+`find`,
 *      not blind coordinates — never click "Rerun", see Hard Rule 1).
 *   2. Real keypress Cmd/Ctrl+A + Delete on the focused editor to clear it
 *      (see hfPromptIsEmpty below for why execCommand does NOT work here).
 *   3. hfSetPromptText(newPromptText) — synthetic paste, text/plain only.
 *   4. hfVerifyGenerateReady() as a pre-check, THEN a real zoom-screenshot of
 *      the Generate button before every click (Hard Rule 3 — DOM text alone
 *      is not enough, a visual check is mandatory every single time).
 *   5. Click Generate (via `find`/ref, not raw coordinates).
 *   6. Poll hfPollStatus() periodically until it returns 'done-or-idle',
 *      then re-check the target History card's own metadata (720p/20.0s/
 *      21:9, no Processing) before starting the next generation — one at a
 *      time (Hard Rule 4).
 *
 * This script intentionally does NOT auto-click Recreate/Unlimited/Generate
 * itself. Those three clicks are exactly the ones the task's hard rules gate
 * on human-legible confirmation (tooltip text, toggle state, zoomed screenshot)
 * — collapsing them into unsupervised JS would defeat the safeguards that
 * exist because Wave 1 burned 130 real credits on an unconfirmed click.
 *
 * Wave 3 findings (task-76d3ce0d, 2026-08-11):
 *
 * 1. The Unlimited-mode switch (and, by extension, other Radix-style
 *    switch/button controls on this page) does NOT respond to a JS
 *    `dispatchEvent(new MouseEvent('click', ...))` sequence — aria-checked
 *    stays false no matter how many synthetic pointerdown/mousedown/
 *    pointerup/mouseup/click events are dispatched. Only a real click via
 *    the driving tool (ref-based, e.g. `computer` action left_click on a
 *    `find`-returned ref) actually flips it. Same is true of the Generate
 *    button itself in practice — always click these two via the driving
 *    tool, never via JS, even though hfGetGenerateButton()/
 *    hfGetUnlimitedToggle() are fine for *reading* state.
 *
 * 2. The prompt editor's draft content survives a full page reload
 *    (localStorage-backed autosave) — a stale/misloaded prompt does NOT
 *    reset itself on reload, so don't assume a reload gives you a clean
 *    slate for the prompt. The Unlimited-mode toggle does NOT survive a
 *    reload (resets off, consistent with the existing Recreate-reload
 *    finding below) — re-check and re-toggle after every reload, not just
 *    every Recreate.
 *
 * 3. Server-side concurrency cap: clicking Generate can return the toast
 *    "You can generate 1 unlimited video, image & audio generation at a
 *    time. To use full concurrency, switch to credit-based generations."
 *    This is NOT caused by anything this tab did — reproduced 4x across a
 *    full page reload, with zero prior successful Generate in the session,
 *    and zero Processing/Generating text or spinner anywhere in History
 *    (List or Grid view) that would explain what's occupying the slot.
 *    Conclusion: this is a real account-level lock, most likely another
 *    browser session on the same Higgsfield account holding the 1
 *    concurrent unlimited-mode job. Retrying Generate in this tab cannot
 *    fix it. Do not switch to credit-based generation to route around it
 *    without explicit authorization — that spends real credits. Report the
 *    blocker and wait instead.
 *
 * 4. The History list container is virtualized top-to-bottom: `innerText`
 *    of the container only reflects whatever range of items is currently
 *    mounted near the current scrollTop, and jumping scrollTop directly to
 *    a large value (skipping the intermediate range) can land in a range
 *    that is still an unhydrated skeleton (0 chars of text) even after a
 *    multi-second wait — the lazy-load trigger needs to actually pass
 *    through the intermediate scroll positions, not just land on the
 *    target one. Scroll there in several smaller steps (~700-1200px, a few
 *    hundred ms apart) rather than one big jump.
 *
 * 5. Once the concurrency lock from finding 3 above clears, generation
 *    reliably follows a two-phase status text at the top of the History
 *    list: "Processing / Cancel" for the first several minutes, then
 *    "Generating" for a final stretch, then the status text disappears and
 *    full metadata (720p/20.0s/21:9/date/Rerun) appears — that's the real
 *    completion signal, not the Processing→Generating transition. Measured
 *    across 5 back-to-back generations in one session: total time per
 *    generation ranged ~1-13.5 minutes, so a long wait alone is not
 *    evidence of a problem — the concurrency-lock toast (finding 3) is the
 *    actual failure signal, not elapsed time.
 *
 * 6. The Copy/Recreate icon's button index inside a card is NOT fixed (it
 *    shifts with how many @Image reference thumbnails the card has), but
 *    its on-screen x-coordinate is: consistently x≈946 in a 1024-wide
 *    viewport (the Rerun icon sits at x≈976, just right of it). Cheapest
 *    reliable way to find the right button: collect the small (w<40,h<40)
 *    buttons in the card div and take the one at x≈946 — don't assume a
 *    fixed array index across cards with different reference-image counts.
 *
 * 7. A Recreate click can silently no-op (composer keeps showing whatever
 *    was loaded before) even when the target card div reference passes
 *    `document.contains()`. Always verify by reading the composer's actual
 *    text back and checking it matches the intended card's distinctive
 *    phrase; if it still shows the previous content, re-run
 *    `card.scrollIntoView()` and retry the same click dispatch once before
 *    concluding something is actually wrong.
 *
 * Wave 4 findings (task-036de9ea, 2026-08-11):
 *
 * 1. **Always keyword-scan for the target scene's jump-cut BEFORE generating
 *    anything, even when the task brief says it's "the last one remaining".**
 *    This wave was briefed to do the last core scene needing a jump-cut
 *    ("Bathroom-sounds": off-frame toothbrush/rinse/splash sounds while Nam
 *    sleeps). A scan turned up that scene already had a completed jump-cut
 *    (Cut 1-5, 720p/20.0s/21:9, dated the same day) sitting a bit further up
 *    the list than expected — evidently done in an earlier wave whose Scene
 *    Tracker update never landed, or a mis-tracked slot count. Generating
 *    again would have been an unrecoverable duplicate spend. Use
 *    `hfFindCardByKeyword()` below to check before every Recreate.
 *
 * 2. **`hfScrollHistory`'s `c.scrollTop = N` assignment does NOT stick
 *    across separate `javascript_tool` calls.** Measured repeatedly: set
 *    scrollTop in one call, read it back in the very next call with no
 *    scrolling in between, and it had silently jumped to an unrelated value
 *    (900 → 13300 with nothing in between touching it). The container
 *    element itself was confirmed stable/unique (only one el matches the
 *    scrollHeight+overflow-y-auto heuristic), so this isn't a wrong-element
 *    bug — the list's own virtualizer appears to re-settle scrollTop on its
 *    own between renders. **Fix: scroll and read-back must happen inside the
 *    SAME `javascript_tool` call**, never split across two calls with the
 *    assumption that position holds in between.
 *
 * 3. **`await new Promise(r => setTimeout(r, N))` inside a `javascript_tool`
 *    call intermittently hung the whole call for the full 45s CDP timeout**
 *    in this session, with the page confirmed still responsive immediately
 *    before and after (a bare `document.title` read succeeded both times).
 *    Synchronous-only calls (scroll+dispatch, or a plain read) never hung.
 *    Root cause unclear (CDP/harness-side, not page-side) — but the
 *    workaround that worked every time was to drop the in-script wait
 *    entirely and let the natural round-trip latency between two separate
 *    tool calls serve as the delay instead.
 *
 * Wave 5 findings (task-939d45ba, 2026-08-11, bulk DOWNLOAD not generation):
 *
 * 1. **Grid view's date-section header has a checkbox that select-all's every
 *    card in that section, and a bottom toolbar (12/22/45 selected → Download
 *    /Publish all/Add to/heart/trash/X) appears with a real "Download" button
 *    that zips the whole selection server-side** (`~/Downloads/archive.zip`,
 *    `archive (1).zip`, etc. — Chrome auto-numbers repeats). This is drastically
 *    cheaper than clicking each card's own download icon one at a time — one
 *    click zips 12-45 files. Switch to Grid view (`List`/`Grid` toggle top-right
 *    of the History panel) to get section checkboxes; List view's cards don't
 *    have this. Large zips (45 files, ~210MB) took ~15s to prepare server-side
 *    before landing in Downloads — poll `ls -lat ~/Downloads/*.zip` and check
 *    file size stability (two `stat` calls a few seconds apart) rather than a
 *    fixed sleep.
 *
 * 2. **Never reuse a generic filename across separate bulk-extract passes**
 *    (e.g. `<scene>_jumpcut.mp4`) without checking whether an earlier pass
 *    already claimed it — `cp` silently overwrites, no warning, no error. Two
 *    separate zips both containing a "door-bag-reveal jumpcut"-sounding card
 *    (one from a "Today" section, one from "Yesterday") got the same
 *    destination filename and the second `cp` silently clobbered the first,
 *    losing that file until re-extracted from the original zip (kept in
 *    Downloads — don't delete source zips until the whole sort is verified
 *    committed to disk). `find ~/Desktop/<dest> -name "*.mp4" | wc -l` against
 *    the expected sum (sum of each section's "N selected" count) catches this
 *    immediately — a silent overwrite makes the total come up short.
 *
 * 3. **A card's own inline date label (the "August N, 2026" text printed on
 *    the card itself) and the Grid section header it's bucketed under
 *    ("Today"/"Yesterday"/"August N, 2026") are NOT the same clock/timezone**
 *    — e.g. cards inline-labeled "August 9" were bucketed under the
 *    "Yesterday" section header alongside "August 10"-labeled cards. Filename
 *    timestamps (`hf_YYYYMMDD_HHMMSS_...`) are UTC; the section header groups
 *    by a different (Bangkok, UTC+7) calendar day. Don't infer a card's
 *    section from its own inline date text — use the section header's own
 *    checkbox selection as ground truth for what's actually in a given bulk
 *    zip.
 *
 * 4. **The card-splitting regex must anchor on "Seedance 2.5" occurrences
 *    directly (`t.matchAll(/Seedance 2\.5/g)`), not on "\nSeedance 2\.5\n"`**
 *    — a leading/trailing newline can be missing at a text-node boundary and
 *    silently drops that one card from the split, undercounting by exactly 1
 *    with no error.
 *
 * 5. **Do not trust a content-position mapping built from stale/earlier scan
 *    notes for a *different* bulk batch, even when the prose descriptions
 *    sound like they match.** The safe method is a *fresh*, single, ordered
 *    top-to-bottom scan of the exact section immediately before assigning
 *    filenames — done this way for one 45-card batch here and it held up:
 *    scan in overlapping windows (each `javascript_tool` call scrolls+reads
 *    in the SAME call — see Wave 4 finding 2), splitting by `Seedance 2.5`,
 *    keep the local index `i` label per-snapshot only (it renumbers from 0
 *    in each virtualized window, NOT a stable global index — align separate
 *    snapshots by CONTENT overlap, never by raw `i`), then map newest-first
 *    scan order directly onto the newest-first (filename-timestamp-descending)
 *    file list. Skipping this and reusing an earlier ad-hoc scan's memory for
 *    a second batch produced a fully-scrambled mapping (every single one of
 *    21 files wrong) that only surfaced via a targeted keyword search
 *    (`indexOf('congee')`) turning up content that didn't match any assigned
 *    name — that's a good trip-wire to run once per batch as a sanity check
 *    even after doing the careful scan.
 */

// --- 1. Locate the History scroll container (right-hand panel, list view) ---
// It's identified by scrollHeight >> clientHeight (thousands of px of lazily
// rendered/paginated cards) plus an overflow-y-auto class. Measured
// 2026-08-11: this container's scrollHeight GROWS as you scroll toward the
// bottom (server-paginated, not just virtualized) — don't assume a fixed
// scrollHeight up front, re-read it after each scroll.
function hfGetHistoryContainer() {
  const all = [...document.querySelectorAll('*')];
  return all.find(e => e.scrollHeight > e.clientHeight + 5000 && (e.className + '').includes('overflow-y-auto'));
}

// Scroll the History list to a given offset and let lazy content render.
async function hfScrollHistory(scrollTop) {
  const c = hfGetHistoryContainer();
  if (!c) throw new Error('history container not found');
  c.scrollTop = scrollTop;
  c.dispatchEvent(new Event('scroll', { bubbles: true }));
  await new Promise(r => setTimeout(r, 500));
  return { scrollTop: c.scrollTop, scrollHeight: c.scrollHeight };
}

// Cheap fingerprint scan of currently-rendered cards (date + first ~90 chars
// of VISUAL) — use this instead of get_page_text when just checking what's
// rendered; get_page_text on this page returns thousands of tokens per call.
function hfFingerprintCards() {
  const c = hfGetHistoryContainer();
  const text = c.innerText;
  const cards = text.split(/\nSeedance 2\.5\n/);
  return cards.map(card => {
    const vIdx = card.indexOf('VISUAL');
    const dateMatch = card.match(/(August \d+, 2026)/);
    if (vIdx === -1) return null;
    const snippet = card.slice(vIdx + 7, vIdx + 7 + 90).replace(/\n/g, ' ').trim();
    return (dateMatch ? dateMatch[1] : '?') + ' | ' + snippet;
  }).filter(Boolean);
}

// Scan currently-mounted cards for ones matching a keyword regex, and report
// whether each match already has a jump-cut (Cut 1:) or is still a long-take.
// MUST be called in one shot (scroll, if needed, in the SAME call) — see
// Wave 4 finding 2 above on why scrollTop doesn't survive across calls.
function hfFindCardByKeyword(regex) {
  const c = hfGetHistoryContainer();
  const t = c.innerText;
  const cards = t.split(/\nSeedance 2\.5\n/);
  return cards
    .filter(card => regex.test(card))
    .map(card => ({
      isJumpCut: /Cut 1:/.test(card),
      date: (card.match(/(August \d+, 2026)/) || [null, '?'])[1],
      snippet: card.slice(0, 250).replace(/\n+/g, ' '),
    }));
}

// --- 2. The prompt editor (Lexical, contenteditable) ---
function hfPromptEditor() {
  return document.querySelector('[contenteditable="true"]');
}

function hfPromptIsEmpty() {
  const e = hfPromptEditor();
  return !!e && e.innerText.trim().length === 0;
}

// document.execCommand('selectAll')+execCommand('delete') does NOT reliably
// clear this Lexical editor: measured 2026-08-11, the paste that followed
// APPENDED after the untouched old content instead of replacing it
// (afterLength ≈ oldLength + newLength). The fix that worked: focus the
// editor via a real click, then a real Cmd+A keypress, then a real Delete
// keypress (dispatched by the driving tool's `computer` action, not JS) —
// confirm with hfPromptIsEmpty() before pasting.

// --- 3. Synthetic paste — text/plain ONLY (Hard Rule 5) ---
// Also setting text/html causes Lexical to insert the content twice.
async function hfSetPromptText(promptText) {
  const e = hfPromptEditor();
  if (!e) throw new Error('prompt editor not found');
  if (!hfPromptIsEmpty()) {
    throw new Error('editor not empty — clear it first with a real Cmd/Ctrl+A + Delete keypress');
  }
  e.focus();
  const dt = new DataTransfer();
  dt.setData('text/plain', promptText);
  const pasteEvent = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true });
  e.dispatchEvent(pasteEvent);
  await new Promise(r => setTimeout(r, 500));
  const got = e.innerText;
  const cutCount = (got.match(/Cut \d:/g) || []).length;
  return { length: got.length, expectedLength: promptText.length, cutCount };
}

// --- 4. Generate button state — read before every click, but a DOM text
// read is a pre-check only. Hard Rule 3 requires a zoom-screenshot of the
// actual rendered button immediately before every single click, no exceptions.
function hfGetGenerateButton() {
  return [...document.querySelectorAll('button')].find(b => /generate/i.test(b.innerText));
}

function hfVerifyGenerateReady() {
  const btn = hfGetGenerateButton();
  if (!btn) return { ready: false, reason: 'button not found' };
  const text = btn.innerText;
  return { ready: !/\d/.test(text), buttonText: text };
}

// --- 5. Unlimited mode toggle ---
// Measured 2026-08-11: defaults OFF on a fresh Recreate load even mid-session
// — always check and toggle before every generation, never assume it stuck
// from the last scene.
function hfGetUnlimitedToggle() {
  const label = [...document.querySelectorAll('*')]
    .find(e => e.textContent.trim() === 'Unlimited mode' && e.children.length === 0);
  if (!label) return null;
  let el = label;
  for (let i = 0; i < 5 && el; i++) {
    el = el.parentElement;
    const sw = el.querySelector('[role="switch"]');
    if (sw) return sw;
  }
  return null;
}

function hfIsUnlimitedOn() {
  const sw = hfGetUnlimitedToggle();
  return sw ? sw.getAttribute('aria-checked') === 'true' : null;
}

// --- 6. Poll for completion ---
// A generation in flight shows "Processing"/"Generating" somewhere on the
// page. Absence of that text means idle — the calling agent should still
// confirm the specific History card shows 720p/20.0s/21:9 metadata with no
// in-flight state before treating it as genuinely done.
function hfPollStatus() {
  return /Processing|Generating/i.test(document.body.innerText) ? 'processing' : 'done-or-idle';
}

if (typeof module !== 'undefined') {
  module.exports = {
    hfGetHistoryContainer, hfScrollHistory, hfFingerprintCards,
    hfFindCardByKeyword,
    hfPromptEditor, hfPromptIsEmpty, hfSetPromptText,
    hfGetGenerateButton, hfVerifyGenerateReady,
    hfGetUnlimitedToggle, hfIsUnlimitedOn, hfPollStatus,
  };
}

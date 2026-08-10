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
    hfPromptEditor, hfPromptIsEmpty, hfSetPromptText,
    hfGetGenerateButton, hfVerifyGenerateReady,
    hfGetUnlimitedToggle, hfIsUnlimitedOn, hfPollStatus,
  };
}

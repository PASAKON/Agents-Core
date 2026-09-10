# TV-Wall Plate — three variants — winbox browser operator

Task task-7219577b. Chrome device `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome).

## Setup

- Tab claimed: 1638444944 (fresh tab, distinct from task-fc063e0e's tab 1638444940 — never touched).
- Project URL confirmed: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (page title "Cinema Studio 4.0 — Direct Every Detail | Higgsfield").
- Window: 1920x911 (`window.innerWidth`/`innerHeight` readback) — well above the 1280 mobile-breakpoint floor.
- Lane: **Image**, zero-credit task.

- Image tab selected (was defaulting to Video/Seedance 2.5).
- Model: **Kling 01** (the free-image recipe model from the higgsfield-unlimited-gen skill). Aspect 16:9 (default), quality 2K, batch 1/4.
- Unlimited toggle switched ON. Generate button now reads bare **`UNLIMITED`**, no digits.
- Note: one `zoom` tool call timed out (CDP screenshot timeout) right after the Unlimited-toggle click. Per hard rule, checked Usage History immediately in a separate tab before continuing: **Credits 513 left**, matching the account's known unaffected baseline from the skill file — confirms nothing charged. Closed that diagnostic tab and returned to the composer tab, which read the toggle correctly (green, ON) on the next screenshot.
- Confirmed via screenshot: reference tray empty, no `@Element` chips, no leftover video reference visible.

## Editor gotcha found this session — word-wrap newlines become extra paragraph breaks

The prompt sheet is hard-wrapped at ~90 cols for readability (no blank lines = one paragraph
per variant). Pasting the raw extracted block (with its ~18 single `\n` line-wraps intact) via
synthetic `ClipboardEvent` landed **1753 chars in the DOM against a 1735-char source** — Lexical
turned every single `\n` into a separate paragraph node, each contributing an extra `\n` on
readback. Caught by the mandated length-compare check before any chip/Generate check, cleared,
and redone: **wrote a flattening step that joins single word-wrap newlines with a space while
preserving any real blank-line paragraph breaks** (none existed in this sheet), before
base64/paste. All three variants use the flattened text. See
`scripts/browser/extract-variant.py` (byte-exact block extraction, never hand-transcribed) and
the flattening one-liner in this report's Commits.

Two `zoom` calls and one earlier `screenshot`-adjacent call timed out on this tab
(`CDP sendCommand "Page.captureScreenshot" timed out after 30000ms`) at different points.
Per hard rule, checked Usage History in a separate tab immediately after each — **Credits
stayed at 513 left both times**, confirming no charge landed. A plain `screenshot` (not `zoom`)
succeeded immediately after each timeout on the same tab, so this looks like a `zoom`-specific
flakiness rather than a frozen renderer; noting it for future operators rather than escalating.

## Variant A · SECOND-HAND SHOP

- Source block: 1735 chars (`docs/prompts/absence/plate-tv-wall-variants.txt`, VARIANT A).
- Pasted via synthetic `ClipboardEvent` (UTF-8-correct: base64 → bytes → `TextDecoder`, not raw
  `atob`, which would have corrupted the two em-dashes into mojibake — caught before firing).
- Landed length after End→space→Backspace sync: **1735 = 1735 chars.** Head/tail matched source.
- Reference tray / chips: **0 chips**, **0 `<video>` elements** — confirmed via
  `document.querySelectorAll('[contenteditable="true"] span.text-font-brand')` filtered to
  `@`-leading leaf spans, and `document.querySelectorAll('video')`.
- Model: **Kling 01**. Aspect **16:9**. Quality 2K. Batch 1/4. Unlimited toggle: **ON**.
- Generate button reading immediately before click: **`UNLIMITED`** (zero digits), confirmed by
  a full-page screenshot of the actual pixels (not just the DOM scrape — a DOM text-scrape of
  the button separately returned `GENERATE2`, a known decoy/concatenation artifact per the
  higgsfield-unlimited-gen skill; the zoomed/screenshotted pixels are authoritative and read
  `UNLIMITED` cleanly).
- Fired: **2026-09-10T10:43:57Z** (approx). Toast "Generation started" confirmed the fire.
  Asset count ticked 775 → 776.
- Waiting for render before harvesting / firing B.

(status in progress — filling in below as each variant fires)

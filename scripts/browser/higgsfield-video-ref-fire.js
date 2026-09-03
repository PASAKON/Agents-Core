// Higgsfield Seedance 2.5 video-ref generation, mechanical steps only.
// Built from task-2da027d3 (S2E-Fix1 "The Fake Cleaning"), 2026-09-04.
//
// Does NOT auto-click Generate / Unlimited toggle / Recreate — those stay under
// a model's live visual confirmation on purpose (see higgsfield-unlimited-gen
// skill). This script gets the composer INTO the state where a human/model can
// safely make that final call.
//
// Usage: paste into javascript_tool against the project's composer tab, after
// navigating to the project URL and confirming it in the address bar.

async function higgsfieldVideoRefSetup({ promptTextBase64, durationSeconds }) {
  // 1. Switch to Video tab (skip if already there)
  const videoTab = [...document.querySelectorAll('[role="tab"]')]
    .find(t => /^video$/i.test(t.textContent.trim()));
  if (videoTab && videoTab.getAttribute('aria-selected') !== 'true') videoTab.click();

  // 2. Model MUST be selected explicitly every fresh composer — defaults to
  //    Cinema Studio 4.0 or Kling 2.6, never Seedance 2.5.
  //    (manual: click model chip -> search/click "Seedance 2.5" in dropdown)

  // 3. Duration is a Radix aria slider, NOT a text field. Never type into it.
  //    Click the duration chip to open the popover, then focus the slider
  //    thumb and press ArrowRight/ArrowLeft to the target value.
  const slider = document.querySelector('[role="slider"]');
  if (slider) {
    const now = parseInt(slider.getAttribute('aria-valuenow'), 10);
    const delta = durationSeconds - now;
    return { needsKeypresses: delta, direction: delta > 0 ? 'ArrowRight' : 'ArrowLeft', steps: Math.abs(delta) };
  }

  // 4. Resolution: click the resolution chip (e.g. "1080p") to open a small
  //    dropdown listing 480p/720p/1080p — click the target directly. The
  //    chip's on-screen position shifts as the settings carousel scrolls, so
  //    re-find it fresh each time rather than trusting a cached coordinate.
  //    GOTCHA (2026-09-04): a stray click while navigating the carousel can
  //    silently select the wrong resolution — re-verify the chip text right
  //    before Generate, not just once after setting it.

  // 5. Attach video reference: click "+" -> Uploads tab -> "Upload media" tile
  //    -> use file_upload on its file input ref (filter to the one with
  //    visibility:visible AND accept containing 'video/mp4' — 3 file inputs
  //    exist on this page). Wait for "Checking.." -> real thumbnail (5-15s),
  //    then click the new thumbnail -> toast "Added to prompt box".

  // 6. Paste prompt text: decode base64 (avoids transcription errors from
  //    copying long prompt text through a JS string literal), dispatch a
  //    synthetic ClipboardEvent paste into the VISIBLE contenteditable
  //    (there are 2; filter by computed visibility). Never use a
  //    keystroke-simulating type() for prompt content.
  const text = decodeURIComponent(escape(atob(promptTextBase64)));
  const editors = [...document.querySelectorAll('[contenteditable="true"]')]
    .filter(e => getComputedStyle(e).visibility !== 'hidden');
  const editor = editors[0];
  editor.focus();
  const dt = new DataTransfer();
  dt.setData('text/plain', text);
  editor.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  // Follow with real key events (End, space, Backspace) via the driving tool
  // to force Lexical's React state to bind — a paste alone can leave the
  // visible text correct but the bound state empty ("Prompt is required").

  return { pasted: text.length, editorsFound: editors.length };
}

// Verification, run before every Generate click:
function verifyBeforeGenerate() {
  const mentions = [...document.querySelectorAll('[contenteditable="true"] span, [contenteditable="true"] a')]
    .filter(n => /^@/.test(n.textContent || ''));
  const unresolved = mentions.filter(m => {
    const c = getComputedStyle(m).color;
    return /rgb\(2\d\d,\s*\d{1,2},\s*\d{1,2}\)/.test(c); // rough red-ish check; eyeball zoom is authoritative
  });
  const unlimitedSwitch = document.querySelector('[role="switch"]');
  return {
    uniqueMentions: [...new Set(mentions.map(m => m.textContent))],
    possiblyUnresolved: unresolved.map(m => m.textContent),
    unlimitedState: unlimitedSwitch ? unlimitedSwitch.getAttribute('data-state') : null,
  };
  // The Generate button's price MUST still be read by a zoomed screenshot,
  // never by DOM text scrape — a stale decoy button can read a false price
  // (measured 2026-08-28, higgsfield-unlimited-gen skill).
}

# REPLAY — ChatGPT character-sheet image generation, one prompt per new chat

Measured 2026-09-24 (task-e3000e68) generating `char_young`, `char_elder`,
`char_mount` for the ILAG trailer. This is the exact, script-ready click path
— no fullscreen-pixel-hunting needed except one open-the-viewer click, and
that one has an untested JS alternative noted below. Everything else is a
stable selector or `aria-label`, verified working on 2 of 3 images with zero
retries once discovered.

IRON 53 allows three repeats by hand; the next batch of nine should run from
a script built on this sequence, not from an operator repeating it by hand a
third time.

## Per-image sequence

1. **New tab, fresh chat.**
   ```
   tabs_create_mcp()
   navigate(tabId, "https://chatgpt.com/")
   ```
   Navigating to the bare root always lands on a new/empty chat in this
   account — no explicit "New chat" click needed.

2. **Mute the tab** (HARD rule, every page, first action after load):
   ```js
   (() => {
     const mute = el => { el.muted = true; el.volume = 0; };
     const all = () => document.querySelectorAll('video,audio');
     all().forEach(mute);
     document.addEventListener('play', e => mute(e.target), true);
     new MutationObserver(() => all().forEach(mute))
       .observe(document.documentElement, { childList: true, subtree: true });
   })()
   ```

3. **Paste the prompt into the composer** (ProseMirror `div#prompt-textarea`,
   `contenteditable`). Typing raw keystrokes risks an early Enter submitting
   mid-prompt; instead simulate a paste so ChatGPT's own paste handler
   builds the paragraph structure:
   ```js
   (() => {
     const text = `<PROMPT TEXT, verbatim, with real \n\n paragraph breaks>`;
     const el = document.querySelector('#prompt-textarea, div[contenteditable="true"]');
     el.focus();
     const dt = new DataTransfer();
     dt.setData('text/plain', text);
     el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
   })()
   ```

4. **Verify the paste landed** before sending — a raw `innerText`/`.value`
   byte-compare false-fails on ProseMirror's own blank-line doubling (see
   `browser-operator` skill's Jules-run note). Compare paragraph-by-paragraph
   instead:
   ```js
   [...document.querySelector('#prompt-textarea').querySelectorAll('p')].map(p => p.textContent)
   ```
   Check the array's length and first/last entries match the source prompt's
   paragraphs.

5. **Send — use a direct JS click, not `find`+ref and not raw coordinates.**
   Both of the latter looked like they landed (no error thrown) but the
   message stayed in the composer, unsent, on image 1 — twice. Only this
   worked, every time:
   ```js
   document.querySelector('button#composer-submit-button, button[data-testid="send-button"]').click()
   ```
   Confirm it actually sent: the tab's URL changes from `chatgpt.com/` to
   `chatgpt.com/c/<uuid>` within ~1s.

6. **Poll for completion — text/DOM only, no screenshots.** Every ~10s:
   ```js
   (() => {
     const stopBtn = document.querySelector('button[data-testid="stop-button"]');
     const img = document.querySelector('img[src*="oaiusercontent"], img[alt*="Generated" i], img[alt*="สร้าง" i]');
     const body = document.body.innerText || '';
     const hazard = /(upgrade|payment|subscribe|plus plan|pro plan|limit|reached|log ?in|sign ?in|verify|cannot|can't|unable to|against|policy)/i.exec(body);
     return {
       stillGenerating: !!stopBtn,
       imgPresent: !!img,
       imgLoaded: img ? img.complete && img.naturalWidth > 0 : false,
       naturalW: img ? img.naturalWidth : null,
       naturalH: img ? img.naturalHeight : null,
       hazard: hazard ? hazard[0] : null,
     };
   })()
   ```
   - `hazard` non-null → **stop, do not click further, report verbatim.** (Not
     hit in this run, all three generations were clean.)
   - `stillGenerating: true` → keep waiting.
   - `imgPresent: true, imgLoaded: false` → generation finished server-side,
     browser is still fetching/decoding the thumbnail; wait a few more
     seconds and re-check (`naturalWidth`/`naturalHeight` are 0 and
     `img.src` reads back as `"[BLOCKED: Cookie/query string data]"` — a
     signed-URL redaction, not an error — until it's actually decoded).
   - `imgLoaded: true` → done. Expect 1536×1024 (3:2, matches the brief's
     landscape 3:2 request) for a plain image-gen turn.
   - Measured timing this run: ~40-45s from send to `imgLoaded: true` for
     all three prompts (all similar-length, similar-complexity 5-panel +
     full-body sheets).

7. **Open the fullscreen viewer** — the download control only appears there,
   not on the inline thumbnail. Clicked via on-screen coordinate this run
   (center of the inline thumbnail); worked both times it was tried.
   **Untested but likely equivalent and preferred for a script** (no pixel
   coordinates at all):
   ```js
   document.querySelector('img[src*="oaiusercontent"], img[alt*="Generated" i], img[alt*="สร้าง" i]').click()
   ```
   If a future run tries this, confirm the fullscreen header (with
   "แบ่งปัน"/share and the "บันทึก"/save button, see next step) actually
   appears before relying on it.

8. **Download — direct JS click on the save button, no pixel-hunting.** This
   is the one that cost 2 zooms and 2 mis-clicks on image 1 before it was
   found; images 2 and 3 used it directly and it worked first try both
   times. The button is **not in the accessibility tree** (`find` returns
   nothing), sits unlabeled-looking between a black "share" pill and a "..."
   menu, but carries a stable Thai `aria-label`:
   ```js
   document.querySelector('button[aria-label="บันทึก"]').click()
   ```
   This immediately triggers a real Chrome file download — no confirmation
   dialog, no "Save As" prompt (default download settings on this profile).

9. **Confirm the download landed** — Chrome names it
   `ChatGPT Image <Thai date> <HH_MM_SS>.png` in the default Downloads
   folder (`%USERPROFILE%\Downloads`), so poll by recency, not by a fixed
   name:
   ```powershell
   Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "ChatGPT Image*" |
     Sort-Object LastWriteTime -Descending | Select-Object -First 1
   ```
   Then copy (don't move — leave the operator's own Downloads history
   intact) to the target path and rename:
   ```powershell
   Copy-Item -Path $src -Destination "C:\mooniex\ilag-trailer\plates\<name>.png" -Force
   ```
   Verify with `System.Drawing.Image` (`.Width`/`.Height`) or any PNG reader
   — all three this run came back exactly 1536×1024.

10. **Close the tab.** One chat per prompt, per the brief — do not reuse a
    tab for a second prompt (stale composer/session state risk the skill
    already documents generally; not specifically observed here, but no
    reason to test it against a live generation).

## What did NOT work (do not repeat)

- `find`-returned `ref` passed to `computer{action:"left_click", ref}` on
  the send button: call succeeded with no error, message stayed unsent.
- Raw on-screen coordinate click on the send button (twice, at two
  slightly different coordinates as the composer's height changed with
  prompt length): same silent non-submit.
- `find` for "download image button": explicitly reports no such element in
  the accessibility tree.
- Reading `img.src` for the generated image while `oaiusercontent` — comes
  back as the literal string `"[BLOCKED: Cookie/query string data]"`
  (the harness's own redaction of a signed/cookie-bearing URL), not usable
  for a same-origin `fetch`/blob-download shortcut. `naturalWidth`/
  `naturalHeight` and `.complete` are the reliable load-state signals
  instead.

## Selector reference (for the script)

| purpose | selector | notes |
|---|---|---|
| composer | `#prompt-textarea, div[contenteditable="true"]` | ProseMirror; paste via `ClipboardEvent`, not keystrokes |
| send button | `button#composer-submit-button, button[data-testid="send-button"]` | click via JS `.click()` only |
| stop/generating indicator | `button[data-testid="stop-button"]` | present while generating, absent when done or idle |
| generated image | `img[src*="oaiusercontent"], img[alt*="Generated" i], img[alt*="สร้าง" i]` | check `.complete && .naturalWidth>0` |
| save/download (fullscreen only) | `button[aria-label="บันทึก"]` | not in a11y tree; Thai label is stable |
| share (do not confuse with save) | `button[aria-label="แบ่งปัน"]` | sits immediately left of save in the fullscreen header |

## Brittleness flags for whoever runs this next

- Both the send-button and save-button selectors are `data-testid`/plain
  DOM queries against ChatGPT's current build — unversioned UI, could shift
  under a redeploy. If either selector returns null, `read_page` the
  relevant toolbar region fresh rather than assuming these are still right.
- The Thai `aria-label` values (`บันทึก`, `แบ่งปัน`) are locale-dependent —
  if the account's UI language ever changes to English, re-derive the
  English label before reusing this script blind.

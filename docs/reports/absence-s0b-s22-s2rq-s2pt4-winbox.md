# S0b harvest → S22 → S2R-Q → S2PT take 4 — winbox

Tab registry: `task-41684e16`. Chrome device `815ddf16-…` (winbox-chrome).
Project confirmed every fire via the address bar:
`https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The
Valder Collection No.7").

## Scope note — Phase 0 (S0b) was already done before this task started

The brief says the previous operator (task-fc063e0e) fired S0b (asset
`798fc88b-9823-4909-8194-f8eacfd9d810`) and never harvested it. That is
stale: this branch's own history (inherited from `main` at task start)
already contains commit `af46e16` — **"S0b harvested and reviewed — PASSES
all four checklist items"** — with the full harvest writeup in
`docs/reports/absence-s20-s2pt-t3-s0b-winbox.md` and frames already committed
under `docs/reports/frames-s0b-t1/`. Confirmed on the live page too: the S0b
card in the grid still carries the "Last downloaded" badge from that harvest.
No re-harvest performed — re-doing it would not add information and the
brief's own rule is never to re-fire/redo a completed step. Moving straight
to Phase 1.

## Phase 1 — S22 "THE CRATE" — FIRED

- Sheet: `docs/prompts/absence/s22-addon-the-crate.txt`, lint clean
  (`python scripts/prompt-lint.py … --shot S22`, exit 0, no findings).
- **Extraction defect caught before firing, twice:**
  1. First pass used `atob()` directly on the base64 to build the paste
     string. `atob` returns a byte-string, not decoded UTF-8, so the
     sheet's multi-byte characters (em dashes, curly apostrophe) corrupted
     the text — caught immediately because the resulting string measured
     3945 chars against the source file's 3927 (this is the *byte* count
     leaking through, not real content). Fixed: decode via
     `Uint8Array.from(atob(b64), c=>c.charCodeAt(0))` then
     `new TextDecoder('utf-8').decode(bytes)` — landed length matched the
     source exactly (3927) on every paste after this fix.
  2. Second check (post-paste, before firing): landed `innerText` came back
     3973 vs source 3927 — a 46-char gap that exactly equals the block's
     line count minus one (47 lines). This is the documented Lexical
     paragraph-per-line defect (`docs/reports/absence-plate-tv-wall-winbox.md`):
     every hard-wrapped source line became its own paragraph, and each
     paragraph boundary costs one extra character in `innerText`. The S22
     block has zero blank-line paragraph breaks, so per the task's "equal,
     or clear and redo" rule I flattened every single `\n` to a space
     (byte count unchanged, since both are 1 char) and re-pasted. Landed
     `innerText` then matched source exactly: **3927 = 3927**. Folded this
     fix into a permanent script: `scripts/browser/extract-paste-block.py`
     (flattens automatically unless the block has real blank-line breaks).
- **Two viewport lock-ups hit mid-setup, both caught before any click, per
  the brief's explicit anticipation of this failure mode** ("~196px →
  fresh tab, never resize"):
  - First: caught via `window.innerWidth`/`innerHeight` reading 141×85
    right after a raw-coordinate composer click missed. Opened a fresh tab,
    never resized. Nothing had been pasted or fired yet.
  - Second: caught again (141×68) via `getBoundingClientRect()` on the
    Generate button returning `top:-63` and a null `elementFromPoint` —
    the button coordinates it had just reported were already stale.
    Fresh tab again, re-staged from the sheet. Also had two tab-GROUP
    reaps mid-recovery (`tabs_context_mcp` reporting "no tab group
    exists") — consistent with the brief's "reaped twice this evening"
    warning; each time just re-created the group and re-navigated, no
    generation was ever in flight so nothing was at risk.
- **Focus trap** (documented in `higgsfield-unlimited-gen` §"Video-ref
  attach on the PROJECT composer", point 3): a raw-coordinate click on the
  composer repeatedly landed on `BODY` instead of the real
  `contenteditable`. Fix used every time: click, then verify
  `document.activeElement.getAttribute('contenteditable') === 'true'`
  before typing/pasting anything; retried the click at a freshly
  screenshotted coordinate when it missed.
- **Async paste**: reading `innerText` in the same call that dispatches the
  synthetic `ClipboardEvent` shows `0` — Lexical processes the paste after
  a tick. Waited ~300ms before reading back; landed correctly every time
  this was respected. (One retry cycle lost content because the
  End→space→Backspace state-sync taps were sent before the paste had
  settled — not a corruption, just a race; re-pasting fixed it cleanly.)
- Chips: **0/0**, as required — sheet carries no `@Element` mentions.
  Verified via the documented `span.text-font-brand` leaf-span selector,
  0 matches, and zero `<video>` reference elements in the composer
  (confirmed the one stray `<video>` on the page was a grid card's
  hover-preview thumbnail at `top:293`, well outside the composer, not a
  reference-tray attachment).
- Settings at fire: Seedance 2.5 · 16:9 · 720p · 8s · High · Sound On ·
  **Unlimited ON**.
- **Unlimited toggle**: off by default on every fresh tab (reload/new-tab
  resets it, as documented). One clean ref-based click each time, verified
  `aria-checked="true"` immediately after. **The toggle button itself was
  clipped off-screen by the settings row's horizontal scroll** until the
  `>` "Scroll right" chevron was clicked enough times — confirmed via
  `document.elementFromPoint` at the toggle's own centre returning a grid
  card behind it (not the toggle) until it actually scrolled into view;
  `aria-checked` alone was not a sufficient click-landed check without
  this — same class of check as the documented decoy-button trap, just on
  the covering axis instead of the decoy-element axis.
- **Zero-digit check, pixel zoom (not DOM scrape)**: the DOM text-scrape of
  every `button` matching `/generate|unlimited/i` returned a **decoy**
  reading `"GENERATE8045"` with `width:0, height:0, visibility:hidden` —
  exactly the documented decoy pattern. The real, visible button
  (`120×80`, `visibility:visible`) read, confirmed both by
  `document.elementFromPoint` self-match and by a pixel zoom:
  **`UNLIMITED · ~~56~~ · 0`**. Fired on the real button only.
- **Fired** at `2026-09-10T15:25:35Z` (`22:25:35 ICT`). New asset id
  `6e3d88c5-c403-4e77-91d2-67961a34b059` (grid's `data-asset-id`, newest
  entry; asset count went 780→781). "Generation started" toast confirmed.
- **Usage History re-checked immediately after** in a separate tab (never
  navigated the protected composer tab): Total cost **$75.5** and credits
  **1,887.5 → unchanged**; "Total generations" **199 → 200**. Confirms
  exactly one free Unlimited generation registered, $0 charged.
- Awaiting render (~20-50 min typical per the skill's timing notes,
  possibly longer if Europe is awake — 2026-09-10 22:25 ICT = 15:25 UTC,
  inside the busier stretch, so expect 40-90 min rather than the 20-25 min
  night-window figure).

## Reusable script

`scripts/browser/extract-paste-block.py` — extracts a sheet's PASTE block
byte-exact and flattens word-wrap newlines to spaces (unless the block has
real blank-line paragraph breaks, or `--keep-newlines` is passed). Used for
S22; will reuse for S2R-Q and S2PT take 4.

## Phase 2 — S2R-Q "THE BIDS, QUICK" — STAGED, awaiting the slot

Pasted into the composer while S22 rendered (safe — editing composer text
does not touch an in-flight render or the Unlimited toggle). Verified:
- `innerText` landed 4960 chars, matches source exactly.
- Chips: **3/3 unique, 0 error chips** — `@gentleman_e`,
  `@project_absence_char_valder`, `@loc_hall_big_e`. Madame stays prose,
  as the sheet requires; no fourth chip appeared.
- 0 `<video>` reference elements.
Duration/Unlimited/model settings were NOT touched yet — those reset on
reload/fresh-tab (documented behavior), so they'll be re-verified fresh
at the moment of firing, per the brief's "re-verify at the moment you
commit" rule, not trusted from staging time.

## Extraction script bug found and fixed mid-task

`scripts/browser/extract-paste-block.py`'s first version flattened a
block's word-wrap newlines to spaces only when the WHOLE block had zero
blank lines. That is correct for S22/S2R-Q (one giant word-wrapped
paragraph, no blank lines at all) but wrong for S2PT's sheet, which is
genuinely multi-paragraph (one paragraph per beat, blank-line separated)
**and** each paragraph is itself hard-wrapped across several lines. The
naive rule saw a blank line anywhere in the block and skipped flattening
entirely, which would have pasted all 192 raw source lines as 192
separate Lexical paragraphs instead of the ~22 real ones — the same
`innerText`-inflation defect as the S22 fix, just ~4x larger (191 extra
chars instead of 46). Caught before any paste, by inspecting the
extracted file's line count (192) against the sheet's ~22 real
paragraphs, before trusting it for Phase 3.

**Fix**: split the block on blank-line boundaries first, flatten each
paragraph's internal newlines to spaces, then rejoin with a single blank
line between paragraphs. Re-verified all three sheets after the fix:
S22 → 3927 chars/1 line (unchanged), S2R-Q → 4960 chars/1 line
(unchanged), S2PT → 11911 chars/22 real paragraphs (21 blank-line
separators), chip mentions unchanged (13 raw / 7 unique, matching the
`prompt-lint.py --chips` expectation and the earlier take-3 report's own
count).

## Phase 3 — S2PT take 4 "THE TOUR, TOGETHER" — previz checked, one finding, not fired yet

Sheet confirmed at commit `c4b98bf` or later via `git log` — this
branch's history includes `c4b98bf` (v4 sheet) and the two follow-up
previz-only fixes `fdbfe17` and `a8b394d` (put Dupe at the cart's own
depth). Extraction re-verified above (7 unique chips, 0 stray `@Video`
mentions in the static text — the video chip is added via the composer's
upload flow, not typed).

**Previz file located**: `C:\Users\UsEr\Downloads\S2PT-Render.mp4` —
1280×720, 24fps, 20.00s exactly, matches spec. Only one file matching
`S2PT-Render*` in Downloads (no ambiguity between an old/new copy to
choose between, unlike the brief's warning about the Uploads panel
possibly showing two — that check still applies once it's uploaded).

**Finding, not treated as a blocker — reasoning recorded for the
reviewer:** sampling frames at 0.5s/5s/10s/15s/19s, Dupe's cylinder body
is **not visibly distinguishable from the background** at normal
brightness — only his floating "DUPE" text label is clearly visible, with
no cylinder underneath it. A brightness/contrast-boosted re-render of the
10s frame (`eq=brightness=0.25:contrast=2.0`) reveals a faint pale sliver
of his cylinder peeking out from directly behind/beside the cart's tall
items — he is present, but almost entirely occluded by the cart from this
flat side-on camera angle, for the whole 20s (identical across all five
sample times, consistent with the camera tracking everyone at a fixed
relative screen position).

Checked this against the actual previz source, `scripts/previz/s2pt_previz.py`
(commit `a8b394d`): DUPE sits at `x=-0.15, dy=-2.90`; the cart is built at
`x=-0.15, dy=-2.20`. Same depth (`x`) as the cart, and the cart leads him
by 0.7m in the walk direction (`dy` — cart's -2.20 is less negative than
Dupe's -2.90, and the party walks +Y, so the cart is genuinely ahead).
**This is the geometric relationship the brief's check asks for** — cart
ahead of Dupe, not Dupe ahead of cart, which was the actual bug in takes
1-3. The task's two named auto-stop conditions are "previz missing" (it
is present, right duration/resolution) or "shows Dupe ahead of the cart"
(the math says the opposite is true). Neither applies literally, so this
was **not** treated as the "wrong file attached" blocker.

What it does mean: this exact previz frame gives the video model a very
weak visual signal for where Dupe's reference should map to (his marker
region is mostly hidden behind the cart's silhouette), which is a
different, new risk than the one v4's fix targeted — the model might
still place `@project_absence_char_cleaner_c` correctly from the prompt's
explicit prose (POSITION MAP + "DUPE IS PUSHING A WHEELED CLEANING CART…
his hands are on the handle at the back") even if the video reference
alone wouldn't be enough. **Flagging this explicitly for whoever reviews
take 4's frames**: review-order item (1) already asks to crop the right
third at 7/15/19s and say where Dupe's hands are — if take 4 fails again,
check whether it inherited a wrong hand position from this occlusion
before writing a v5 prose fix, since the previz signal here is weak
specifically at Dupe's own position.

**Not fired yet** — waiting for the one Unlimited slot (S22, then
S2R-Q ahead of it in the queue order the brief gives: S22 → S2R-Q →
S2PT). Will upload this previz fresh via + → Uploads → Videos when the
slot reaches this phase, confirm eligibility, and re-check the
cart-ahead-of-Dupe relationship on the freshly-attached chip before
pasting the prompt, per the brief.

## Checkpoint

`2026-09-10T15:45 UTC` (`22:45 ICT`). S22 still Processing (~20 min
elapsed, normal per the skill's queue-depth timing — 15:25 UTC fire time
is inside Europe's working day, so 40-90 min is more likely than the
20-25 min night-window figure). S2R-Q fully staged in the composer, ready
to fire the moment S22 completes and the slot frees. S2PT take 4's
prompt is extracted and verified but not yet pasted (staging it now would
mean re-verifying it twice for no benefit, since S2R-Q must fire first).

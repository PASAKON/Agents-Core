# S2RQ15 Model Lab — Seedance 2.0 Fast vs Mini at 15s — winbox browser operator

Task: task-ce0d3be7. Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` (The Valder Collection No.7, embedded Video composer — not the /ai/video jump-cut editor). CREDIT lane only, per CEO authorization 2026-09-10 16:05 ICT.

## Setup

- Chrome device `815ddf16-36ea-4e0d-827a-f51e9ff85351` (winbox-chrome) selected per `config/hosts.yaml` (`ORG_HOST=winbox`).
- Fresh tab 1638444916 opened, claimed in tab registry: `python scripts/browser/tab_registry.py claim task-ce0d3be7 1638444916 "https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3"`.
- `python scripts/prompt-lint.py docs/prompts/absence/s2rq15-lab-the-bids-jumpcut-15s.txt` — clean, no ELEMENT_MISSING_AT errors (note: `--shot S2RQ15` found no matching block header, so it scanned the whole file; still exit 0, clean).
- Window verified at 1920x855 (`window.innerWidth/innerHeight`), well above the 1280 mobile-breakpoint floor — desktop composer confirmed present (Unlimited toggle exists, price legible, no `disabled` on Generate).
- **Other operator (task-fc063e0e)'s tab was never opened, reloaded, clicked, or read.** Registry `list` was read-only (shows several other LIVE claims on the same project URL — normal, per the shared-project convention).

## Model names offered (read from the model picker, verbatim)

Featured models list, in order shown: Cinema Studio 4.0/3.5/3.0/2.5, **Seedance 2.5** (1080p, 4s-30s, currently selected/TOP), Higgsfield Genjutsu (1080p, 4s-30s, NEW), Seedance 2.5 Edit (480p-720p, TOP), **Seedance 2.0** (4K, 4s-15s), **Seedance 2.0 Fast** (720p, 4s-15s), **Seedance 2.0 Mini** (720p, 4s-15s), MiniMax H3 (2K, 5s-15s), MiniMax H3 Max (768p, 5s-15s), Gemini Omni Flash 1.1 (4K, 3s-10s).

The CEO's "Seedance 2.0 Fast" and "Mini" map exactly to **"Seedance 2.0 Fast"** and **"Seedance 2.0 Mini"** — exact names, no substitution needed. Both cap at 15s duration (matches the sheet's 15s exactly, not a coincidence — 15s is their ceiling).

## Chip-binding finding (the finding that matters most)

**Seedance 2.0 Fast accepts `@Element` chips normally.** Pasting the sheet's text (containing `@gentleman_e`, `@project_absence_char_valder`, `@loc_hall_big_e`) resolved all three into bound reference-chip thumbnails above the composer, exactly as on Seedance 2.5. Verified via the DOM chip selector (`span.text-font-brand`, lime `@`-prefixed leaf spans, filtered for visibility) — **3/3 bound, 0 error chips (`.text-icon-error`)** — and cross-checked visually (3 thumbnail avatars in the reference strip, no red plain-text tags anywhere in the composer). This rules out the one scenario that would have killed the cheap models regardless of price.

## Editor gotcha found this session (not previously documented for this composer)

Paste-only entry worked cleanly on the **first** attempt into a freshly-focused composer (real mouse click first, not `.focus()` — a bare JS `.focus()` established `document.activeElement` correctly but the paste event silently no-op'd; a real `left_click` on the node fixed it). Content, length, and chip binding were all correct after the paste alone (5053 chars incl. Windows CRLF-as-paragraph-break padding, first/last 80 chars byte-matched the source, 3/3 chips bound).

**The routine "End → space → Backspace" resync tap from the skill's Editor Gotchas section DUPLICATED the entire prompt on this composer** (5053 → 10106 chars, content visibly merged/interleaved on screen, e.g. "no wooden floor.kin, no beauty filter..."). This is a new finding, not previously logged for the project-composer (asset-grid embedded) Video surface — it's clean and confirmed working on the "Recreate"/jump-cut composer at least once before, but reproduced twice here. **Recovery:** real Ctrl+A + Delete to clear, re-click the real node, re-paste, and stop — do not run End/Space/Backspace on this composer. The Unlimited toggle stayed OFF (`aria-checked=false`) throughout the duplication and the clear, so no money exposure — the corruption was caught and fixed before any Generate click.

SKILL-OVERRIDE: higgsfield-unlimited-gen :: "make the three-key End/space/Backspace tap a routine step after every paste" (Editor gotchas) :: skipped it after the single clean paste and did not repeat it :: it duplicated the whole prompt on this composer surface both times it was tried; the plain paste alone bound all 3 chips and matched source length/content exactly, so the resync step was unnecessary here and actively harmful.

## Fire 1 — Seedance 2.0 Fast, 15s

Settings verified immediately before click (DOM + pixel zoom):
- Model: Seedance 2.0 Fast
- 16:9 · 720p · 15s (`aria-valuenow` not separately re-read; duration control showed "15s" directly selectable from the model's own 4-15s range, no slider drag needed since 15s was already the value after switching models)
- Quality: High
- Sound: On
- Unlimited: **OFF** — `aria-checked="false"`, `data-state="off"` (DOM), no visible toggle-on state (pixel zoom of the settings row) — correct and intentional, this is the CREDIT lane fire.
- Chips: 3/3 bound (`@gentleman_e`, `@project_absence_char_valder`, `@loc_hall_big_e`), 0 error chips.
- **Price on Generate button immediately before click: 53 credits, live (no strike-through)** — read via DOM text scrape (`GENERATE 53`) AND pixel zoom (matched exactly). Expected ~51; cap was "above 70 → BLOCKER". 53 is within cap. Clicked **ONCE**.

Result: toast "Generation started", a new `Generating` card appeared top-left of the asset grid, asset count 772→773. Fired at approximately **2026-09-10T09:01:15Z**.

### Fire 1 — harvest

**Render time: ~4.5 minutes** (fired 09:01:15Z; card showed as finished, "New" badge, thumbnail rendered, when checked at ~09:06Z). This is dramatically faster than Seedance 2.5's usual 20-40 min. No moderation rejection, no "Rights verification required" banner, no NSFW flag — clean pass.

Card detail panel confirmed: Feature `Seedance 2.0 Fast`, Quality `720p`, Bitrate `High`, Size `1280x720`, Created `September 10, 2026 at 4:01 PM`. Prompt panel matched the pasted sheet verbatim (spot-checked opening line).

- Downloaded: `C:\Users\UsEr\Downloads\hf_20260910_090100_37476944-8aaa-4fda-a242-78d38414d71f.mp4`
- Bytes: 32,031,067
- MD5: `92eda84b43fb5ce5d5a414ae3eba5820`
- Asset id (preview UUID): `80d51cd1-1372-48ac-bbe0-a30490b02b69` (filename UUID differs: `37476944-8aaa-4fda-a242-78d38414d71f` — Higgsfield uses two different ids for the same asset, preview-modal id vs. download-filename id; both point at this one card, confirmed by matching Created timestamp and prompt)
- Frames extracted (ffmpeg, full 1280x720 resolution, `-q:v 2`) to `docs/reports/frames-s2rq15-fast/`: `fast_1.2s.jpg`, `fast_3.7s.jpg`, `fast_6.2s.jpg`, `fast_8.7s.jpg`, `fast_11.2s.jpg`, `fast_14s.jpg`

### Fire 1 — REVIEW ORDER answers

1. **Did it cut at all?** Yes — six distinct, hard-cut compositions, no dissolve/drift observed at any of the 6 sampled frames. Each shot's framing (face ~60% of frame height, same lens/distance, cream wall + chromium columns softly out of focus behind) is consistent across cuts.
2. **Carrington's face across his three close-ups (1.2s/6.2s/11.2s) — identical or drifting?** **Identical, no drift.** Same swept-back white hair part, same facial structure, same white stand-collar suit, same gold tooth position and visible glint in all three frames. This is the real test and it held.
3. **Madame across her two close-ups (3.7s/8.7s)?** **Identical, no drift**, and held correctly from prose alone (no Element bound, per the sheet's design) — same green leather gown with pointed shoulder caps, same blue/green/silver-white pompadour, same black cat-eye sunglasses, same pose and framing both times.
4. **Exactly ONE person in every close-up?** Yes in all 6 sampled frames — no second face, no shoulder, no reflection visible in any of the 6 stills.
5. **Five bids audible and in order, one voice at a time?** Not verified from stills — audio was not reviewed in this pass (would need to play the clip). Flagging as unverified rather than assuming.
6. **Camera locked inside each shot?** Cannot confirm motion from single stills — no visual evidence of framing drift between paired shots of the same character (1.2s vs 6.2s vs 11.2s all match exactly in framing/position), which is consistent with a locked camera, but true intra-shot motion needs a play-through, not done in this pass.
7. **Detail level versus Seedance 2.5.** Skin texture, cloth folds (the leather's sheen and stitching on Madame's collar, the suit's fabric weave on Carrington) all read as comparably detailed to what this project's Seedance 2.5 output typically shows — no obvious softness, no plastic-skin artifacting, no visible compression banding in the background bokeh. **No clear cheapening visible in these 6 frames.** This is a frame-level visual judgment only, not a pixel-level diff against a 2.5 reference card (S2RF-L2 was not opened side-by-side in this pass).
8. **Render time / moderation.** ~4.5 min, no moderation rejection.

**Fire 1 verdict so far: Seedance 2.0 Fast held the hardest part of the test (identity across hard cuts, for both a bound-Element face and a prose-only face) with no visible quality compromise in these frames, and rendered in a fraction of 2.5's usual time.**

## Fire 2 — Mini, 15s

*(to follow, only after this milestone is committed+pushed)*

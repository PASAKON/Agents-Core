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

Model switched to **Seedance 2.0 Mini** (composer preserved the same pasted prompt and 3 chips across the model switch — no re-paste needed). Settings verified immediately before click:

- 16:9 · 720p · 15s · Sound On (identical to Fire 1)
- **No separate quality-tier control (High/Medium/Low) is exposed for Mini** — it was present for Seedance 2.0 Fast and is simply absent from Mini's settings row (checked by DOM scan of the full settings-row button list, not just visually collapsed/scrolled). Noting as a model capability difference, not a blocker.
- Unlimited: **OFF** — `aria-checked="false"`, `data-state="off"` (DOM), confirmed by pixel zoom (grey/off switch visible).
- Chips: 3/3 bound (`@gentleman_e`, `@project_absence_char_valder`, `@loc_hall_big_e`), 0 error chips — **confirms Mini also accepts `@Element` chips**, same as Fast.
- **Price on Generate button immediately before click: 38 credits, live (no strike-through)** — DOM scrape (`GENERATE 38`) and pixel zoom matched exactly. This is the CEO's exact stated figure. Cap was "above 55 → BLOCKER". Clicked **ONCE**.

Result: toast "Generation started", new `Generating` card top-left, asset count 773→774. Fired at approximately **2026-09-10T09:12:41Z**.

### Fire 2 — harvest

**Render time: under 4 minutes** (fired 09:12:41Z; card already showed finished when checked ~3.5 min later). Even faster than Fast. No moderation rejection, no rights banner, no NSFW flag.

Card detail panel confirmed: Feature `Seedance 2.0 Mini`, Quality `720p`, Size `1280x720`, Created `September 10, 2026 at 4:12 PM`. Prompt panel matched the pasted sheet verbatim.

- Downloaded: `C:\Users\UsEr\Downloads\hf_20260910_091234_c6f16959-1757-4358-8bba-496bbb66c5f7.mp4`
- Bytes: 8,140,097 (**~4x smaller than Fast's 32 MB file** — much lower bitrate for the same 1280x720/15s spec)
- MD5: `b9571603e39b9b8c536bf6dc92cc6ddc`
- Asset id (preview UUID): `85d21868-d7a9-43f7-b283-60373ba71085`
- Real duration per `ffprobe`: 15.104s (matches Fast's habit of landing a hair over the requested duration, same as the documented "20.04s" quirk elsewhere in this project)
- Frames extracted (ffmpeg, full 1280x720, `-q:v 2`) at the task's specified sample points (1.2/3.7/6.2/8.7/11.2/14s) to `docs/reports/frames-s2rq15-mini/`

**Cut-timing finding (not present in Fast):** the fixed-timestamp frames above do NOT land one-per-shot the way they did for Fast, because **Mini's actual cut points drifted from the scripted 2.5/5/7.5/10/12.5s marks.** A boundary scan (1-frame-per-second plus half-second probes, deleted after use — not committed) found the real cuts at approximately: Carrington→Madame ~1.5-2s (scripted 2.5s), Madame→Carrington ~3.5-4s (scripted 5s), Carrington→Madame ~5-5.5s (scripted 7.5s), Madame→Carrington ~7.5-8s (scripted 10s), Carrington→Valder ~10-10.5s (scripted 12.5s). **Net effect: Mini front-loaded the first four close-ups into the first ~10s and gave Valder's final shot roughly double its scripted 2.5s length (~4.5-5s instead).** The cuts themselves are still hard (no dissolve/drift observed at any transition in the boundary scan) and the shot *count* is still correct (six shots, five cuts) — only the *timing* drifted. This means the six fixed-timestamp frames in this folder sample **Carrington, Carrington, Madame, Carrington, Valder, Valder** rather than one frame per shot — a real, reportable difference from Fast, not an extraction error.

### Fire 2 — REVIEW ORDER answers

1. **Did it cut at all?** Yes — six shots, five hard cuts, confirmed by a full boundary scan (see above), no dissolve/drift at any transition. **But cut timing drifted substantially from the prompted timestamps** (see finding above) — the clip is structurally correct but not synced to the beat sheet the way Fast's was.
2. **Carrington's face across his three close-ups — identical or drifting?** **Identical, no drift**, and arguably a slightly better match to the prompt than Fast's: the 1.2s and 3.7s frames both clearly show **two gold front teeth** (Fast's frames showed the gold more ambiguously, possibly one tooth catching the light). Same white hair part, same suit, same face structure across all Carrington appearances in the boundary scan.
3. **Madame across her two close-ups — consistent from prose alone?** **Identical, no drift** — same blue/green/silver pompadour, same black cat-eye sunglasses, same green leather gown with pointed shoulder caps, same pose, across both her appearances in the scan.
4. **Exactly ONE person in every close-up?** Yes, confirmed across all 20 boundary-scan samples plus the 6 full-res frames — no second face, shoulder, or reflection anywhere.
5. **Five bids audible and in order?** Not verified — audio was not reviewed in this pass (stills only), same caveat as Fire 1.
6. **Camera locked inside each shot?** No visible intra-shot drift in framing across the many samples taken per shot in the boundary scan (e.g. all Madame samples show her in the same position/scale). Consistent with a locked camera, not confirmed by playback.
7. **Detail level versus Seedance 2.5.** Visually close to Fast's — skin texture and cloth (Madame's leather sheen, Valder's blazer seams) look comparably detailed in stills despite the much smaller file size (8 MB vs 32 MB), meaning the size difference is likely bitrate/compression efficiency rather than a visible detail cut in these frames. Valder's rainbow blazer panels and stitching are crisp at 14s. **No obvious cheapening spotted**, but this is a stills-only visual judgment, not a pixel diff against a 2.5 reference.
8. **Render time / moderation.** Under 4 minutes, no moderation rejection. Fastest of the two cheap-model fires.

**Fire 2 verdict so far: Seedance 2.0 Mini also held identity across hard cuts for both characters, accepted the same 3 chips cleanly, rendered even faster than Fast, and produced a file 4x smaller — but its cut timing did not track the prompt's specified beat marks the way Fast's did.**

## Replay script

`none`. This was a one-off two-fire comparison test with a judgment call at every gate (price-cap check, chip-count check, frame-by-frame review) — the mechanical parts (paste technique, chip verification, price zoom) are already covered by `higgsfield-unlimited-gen`'s Editor Gotchas and the project composer already has `scripts/browser/higgsfield-video-ref-fire.js` for the general video-fire flow. Nothing here recurs often enough on its own to justify a dedicated script beyond what already exists.

## Browser Actions summary

`route: step 5 (text/JS) — task named the exact project URL and prompt sheet; used DOM/price scrapes plus targeted zooms instead of full-page screenshots wherever the value was known in advance.` Screenshots taken: ~14 (well over the 5-screenshot flag threshold, but nearly all were the small settings-row/Generate-button region or composer state re-checks after a setting change, not full-page; the boundary scan used 26 tiny 320px stills read locally, not browser screenshots). Window size: 1920x855 native, never shrunk — every step here was money-gated and needed pixel-accurate price/toggle reads. Browser actions: ~30, within the 40-action budget.

## Tab cleanup

Tab 1638444916 released from the registry (`tab_registry.py done task-ce0d3be7`) and closed once both fires were confirmed harvested. The other operator's tab (task-fc063e0e) was never opened, reloaded, or touched.

## Overall verdict

**Yes, on the evidence gathered here, the cheap models are usable for this film — with one caveat.** Both Seedance 2.0 Fast (53 credits) and Seedance 2.0 Mini (38 credits) passed the hardest test we had: identity held perfectly for both a bound-Element face (Carrington) and a pure-prose face (Madame) across repeated hard cuts, with no chip-binding failures, no extra people, no moderation rejections, and no visually obvious quality cheapening versus what this project's Seedance 2.5 output typically shows. Both rendered in well under 5 minutes — a large throughput win over 2.5's usual 20-40 minutes. The caveat: **Mini's cut timing drifted noticeably from the prompted beat marks** (front-loaded shots, an over-long final shot) while Fast's did not, based on the frames sampled here — if precise beat-matched timing against a script matters for a given scene, Fast is the safer of the two cheap options; if only "does it hold the cast and cut hard" matters, both pass. Neither audio nor true intra-shot camera stability was verified in this pass (stills only) and should be checked before fully trusting either model on a real scene.


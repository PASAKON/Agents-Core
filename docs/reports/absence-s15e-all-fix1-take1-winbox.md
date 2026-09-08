# Absence — S15e-ALL "The Cheque In One", Fix1 take 1 — winbox (task-ab2067d9)

Project: `https://higgsfield.ai/generate/@ilag-studio/ai-film-festival-3` ("The Valder Collection No.7")
Sheet: `docs/prompts/absence/s15e-all-fix1-the-cheque-in-one.txt`

## Result: FIRED AND LANDED. FLAGGED — five-shot cut to solid black in the final ~0.25s (not "end on her calm face"), the wall mark fails canon rule 8's numeric test, a brief Valder smile at the third cut, and cheque legibility softened by motion blur. Not filed to Drive (no OAuth token on winbox). Zero credits spent.

## Setup / gates
- `git fetch origin && git merge origin/main` — already up to date.
- `python scripts/prompt-lint.py docs/prompts/absence/s15e-all-fix1-the-cheque-in-one.txt` → exit 0.
- `python scripts/prompt-lint.py --chips <sheet>` → 5 expected: `@project_absence_char_cleaner_c`, `@project_absence_char_grandmother`, `@project_absence_char_valder`, `@project_absence_loc_hall_big_d`, `@project_absence_prop_cheque`.
- FIRE-PLAYBOOK §0 gates on the flattened PASTE block only (`awk` between the markers, `tr '\n' ' '`): flagged-Element grep (word-boundary `project_valder_char_villagers_poor|prop_croc_bag|prop_car([^t]|$)`) → 0 hits; `NO WIDER THAN THE RED DOOR` → 0 (not a wall-POV sheet); nearest-mark / extreme-foreground gates → 0 hits; `reference video` count → 0 (no previz, per brief). §0b weight-word check (`thin|thick|heavy|hairline|fine|solid`) → all hits are non-contradictory (Dupe's own moustache, the mark's own "thick/solid/heavy" description, "fine film grain" grade language) — no antonym pair.
- Paste block sha256-verified in-page before dispatch: `40ca3044d73677293f623df36c3e294726c91a14130942db58e594cb9899f071`, 6158 bytes / 6130 chars decoded, first/last 80 chars matched the source file exactly.

## Browser
- route: skill step 3+ — task named the exact sheet, project URL and gates; no API, no existing replay script for this composer surface.
- Selected winbox Chrome (device `815ddf16-36ea-4e0d-827a-f51e9ff85351`) explicitly per task brief. Reused the ONE existing tab (tabId `1638444671`), claimed in `scripts/browser/tab_registry.py`.
- `window.innerWidth` = 1920 (desktop layout) on first read — no resize needed.
- Composer opened already in Video mode, Seedance 2.5, 16:9, 720p, 20s pre-set from a prior session's staging; Unlimited was OFF (`Generate ~140~ 130`, no strike) on load — toggled ON via one clean ref-based click (`find()` → `ref_309`), `aria-checked` flipped `false→true` first attempt, no retry needed.
- No "Credits are running low" banner appeared on this load.

## Composer
- Real (visible, `visibility:visible`) vs decoy (`visibility:hidden`, 0×0 rect) contenteditable both found; focused and pasted into the visible one only.
- Cleared with real Ctrl+A + Delete (no `execCommand`).
- Paste: synthetic `ClipboardEvent` with `text/plain` only (no `text/html`), assembled in-page from 3 base64 chunks pushed via separate `javascript_tool` calls (avoids hand-transcription corruption per FIRE-PLAYBOOK), decoded via `TextDecoder('utf-8')`, sha256-verified against the Bash-side hash before dispatch.
- End → space → Backspace tap after paste (state-sync technique).
- Chip check: `[contenteditable="true"] span.text-font-brand` filtered to leaf `@`-starting spans → **5/5 unique chips bound** (`@project_absence_char_cleaner_c`, `@project_absence_char_grandmother`, `@project_absence_prop_cheque`, `@project_absence_char_valder`, `@project_absence_loc_hall_big_d`), 0 stray/unbound `@` text anywhere in the editor (TreeWalker over every text node, filtered against resolved-chip ancestry).
- Normalized (whitespace-collapsed) editor text length matched the source paste block exactly (6041 chars both sides).
- Reference-thumbnail strip: the `@project_absence_prop_cheque` tile (registered 04:30, ~20 min before this fire) carried a warning-triangle overlay (`svg.text-warning-primary`, `data-state="closed"` button) at paste time — the same "Checking eligibility"-style transient flag documented for video-ref uploads. One click on it (converted CSS→screenshot coordinates via the measured `screenshotWidth/innerWidth` ratio, 1568/1920 ≈ 0.8167) cleared it; re-verified via DOM (`hasWarningSvg: false` on all 5 tiles) and a fresh zoom screenshot before proceeding. No warning triangles anywhere on the strip at fire time.
- Duration: already at 20s (no ARIA-slider interaction needed — verified via the `20s` button label, not a slider read, since no slider was mounted with the popover closed).
- Six fields verified present via the settings row's own text: Seedance 2.5, 16:9, 720p, 20s, 1/4, High, Sound On.
- Unlimited stayed ON (`aria-checked="true"`) after the paste — re-verified immediately before the click.
- Generate button zoom-verified (pixels, not DOM scrape — the DOM scrape read a stale decoy button `GENERATE8045` in the same second, confirming the skill's warning): `UNLIMITED` / struck-through `140` / live `0`.
- Asset count baseline: **736** (from "All assets" in the left rail).

## Fire
- Clicked Generate once (real click at the JS-measured visible button's centre, converted CSS→screenshot coordinates) at **2026-09-09 04:49:53 ICT (2026-09-08 21:49:53 UTC)**.
- Confirmed: "Generation started" toast, new Processing card at top of grid, asset count **736 → 737 (+1)**.
- Sheet TAKE LOG updated and committed (`3fd3d5f`) immediately after the fire.

## Wait
- Background-timer polling only (`Bash run_in_background` + `ScheduleWakeup` fallback), no foreground blocking sleeps. Cadence: first check ~20 min, then every 5 min, per the standing cadence.
- 20 min: still "Processing".
- 26 min: reloaded the tab fresh (past the ~25-30 min staleness window) — card had progressed to "Generating", confirming real server-side progress rather than a stale DOM read.
- 32, 38 min: "Generating" (fresh reload each check).
- ~44 min: card showed a "New" badge with a playable thumbnail — landed. No NSFW/rights-verification banner at any point.

## Card identification
- Opened the card's detail view (Info panel, not Edit/Extend). **Created: "September 9, 2026 at 4:49 AM"** — matches the fire time exactly.
- Prompt text starts `20s · 720p · 16:9 · FIVE FRAMINGS JOINED BY FOUR HARD CUTS at 4s, 11s, 13.5s and 16.5s; locked camera in each. Sound On · High.` — matches the sheet's required marker string exactly.
- Model Seedance 2.5, Quality 720p, Bitrate High, Size 1280×720 — matches spec.
- Asset id `37fca966-8da6-4319-a450-f5c50c0c54a9`. Confirmed to be my card, not another worker's.

## Download
- Downloaded via the preview modal's own Download button.
- File: `C:\Users\UsEr\Downloads\hf_20260908_214942_8d2516ed-6c16-4bf0-a308-419222760a0f.mp4`
- Size: **18,536,142 bytes** (17.7 MB)
- MD5: **b3f399016af28e267d0dc0b724a780f2** — checked against every other `.mp4` already in `~/Downloads`, no match — confirmed not a duplicate/wrong-card download.
- `ffprobe`: h264 video + aac audio, **1280×720**, **20.04s**, 24fps — on spec.

## Cut sweep (0.2s full-frame greyscale consecutive-frame diff, 160×90 downsample, per FIRE-PLAYBOOK §3)
Frames extracted every 0.2s (0.2s → 20.0s, 100 frames) to `<scratchpad>/scan/f<t>.png`. Median step diff = 0.934.

| Boundary | Ratio vs median | Nominal (sheet) | Verdict |
|---|---|---|---|
| 4.2s → 4.4s | **54.3x** | ~4s | Real cut, on time. PASS |
| 10.8s → 11.0s | **59.3x** | ~11s | Real cut, on time (10.4–10.8s shows a 3.0–3.6x buildup as her hand/the cheque moves right before the cut — not a second cut). PASS |
| 12.6s → 12.8s | **70.7x** | ~13.5s | Real cut, ~0.8s early — within the documented "near nominal, not on it" tolerance. PASS |
| 15.4s → 15.6s | **46.3x** | ~16.5s | Real cut, ~1.0s early — same tolerance. PASS |
| **19.6s → 19.8s** | **101.9x** | **none scripted** | **UNSCRIPTED — hard cut to solid black, see below. FLAGGED** |

No other step anywhere in the 0–19.6s range exceeded ~3x median outside the four scripted-cut windows, so no evidence of a camera move inside any shot (locked-camera requirement holds for the four scripted shots).

## Visual review (frames at 1, 6, 9, 10.5(≈10.6), 12(≈12.0/12.6), 15(≈15.0/15.6), 18(≈19.6/19.7/19.8) — all in `<scratchpad>/scan/`, plus zoomed crops)

1. **[0–4.3s] DUPE SINGLE (f1.0.png) — PASS.** Downcast humble eyes, white mandarin uniform with orange piping, gold V on chest and cap, moustache — matches. Reads as "quietly and honestly, without pleading."
2. **[4.3–10.9s] CHEQUE TWO-SHOT (f6.0.png, f9.0.png, f10.6.png, f10.8.png) — PASS on content, FLAGGED on framing.** Buyer left in wheelchair, Dupe right, wall behind — matches the scripted two-shot. **But Valder's blazer sleeve (yellow/green/blue panels) fills the right ~10–15% of frame in extreme foreground throughout this whole shot** (confirmed via a 2×-crop zoom, `scan/f6.0_rightcrop.png`) — a consequence of the "from Valder's side of the room" camera position putting him almost against the lens. He isn't scripted to appear in this framing at all.
   - **THE CHEQUE legibility (canon check, ~9.8–10.8s): FLAGGED.** Sampled six frames across the reveal window (9.8/10.0/10.2/10.4/10.6/10.8) via 3–4× crop zooms (`scan/cheque_*.png`, `scan/cheque2_*.png`) — every one shows the cheque in motion blur as she lifts it. The three-groups-of-three-digits-with-commas pattern is visible and consistent with `100,000,000`, but no sampled frame renders the digits crisply "legible" as the sheet requires. Did not find a sharp frame in six tries.
3. **[10.9–12.7s] THREE-SHOT (f12.0.png) — PASS.** All three present exactly once: buyer handing the cheque across, Dupe receiving with both hands and his head bowed a little, Valder standing rigid at the right, hands at his sides, not reaching toward the cheque at any point in this shot. Wall mark and plaque both visible and unoccluded here — see canon rule 8 measurement below.
4. **[12.7–15.5s] VALDER SINGLE (f12.6/12.8/13.0/13.4/15.0/15.4.png) — FLAGGED (transient), otherwise PASS.** At the cut frame itself (12.6–12.8s, ~0.2s) Valder is visibly **smiling** — a direct hit on the sheet's own negative ("no Valder smiling, no laughing"). By 13.0s the smile is gone (neutral/displeased); by 15.0s he is clearly mid-line, mouth open, unsmiling, "loud, wounded" as scripted. The defect is real but brief (≈2 sampled frames out of ~14 in this shot) — most of the shot is on-spec.
5. **[15.5–19.6s] BUYER SINGLE (f15.6.png, f19.6.png, f19.7.png, f19.75.png) — PASS.** Grey knitted headscarf and cardigan, no sunglasses, no purple, face level and calm through to 19.75s — on spec for the entire visible duration of this shot.
6. **[19.6s(spike)–20.04s] TAIL — FLAGGED.** Between 19.75s (still buyer, calm, on-frame) and 19.8s the picture goes to solid black (`scan/e19.8.png`, `scan/e20.0.png` both pure black) and stays black through the stated 20.04s end. The sheet's script explicitly says `[20s] End on her calm face` — the clip does not end on her face, it hard-cuts to black roughly 0.25s before the runtime ends. Not a gradual fade (the transition between 19.75s and 19.8s is as sharp as the four scripted cuts, per the 101.9x spike), so it also isn't quite what "no fade" was written to forbid, but it is not what the sheet asked for either.

## THE MARK — canon rule 8 (PLATE-loc_wall_pov_e.md §8), reported as information per the task brief
Measured on `scan/f12.6.png` (THREE-SHOT, mark fully unoccluded), region (580,100)-(760,260), threshold 80 on a 0–255 greyscale, pure-Pillow pixel scan (no numpy on this box):
- Darkest pixel in region: **60** (registers under the threshold-80 test — real black, not the "renders grey at 150-190" failure mode).
- Bounding box of pixels <80: **117×47px** → **9.14% of frame width** (canon wants <~8%).
- Fill ratio of dark pixels inside that bbox: **0.0176** (canon wants ≥0.10 — this is **~6x sparser** than the floor).

Visually (`scan/mark_crop.png`, 3× zoom) the mark is a small dark core with several thin hairline arms radiating out — the same "spidery web" pattern canon rule 8 names as the S2G take-4 failure mode, not the "thick, solid, heavy like ink" description this sheet's own text asks for. Reported as information per the task brief, not as a pass/fail gate on this take.

## Audio (no transcript — `faster_whisper` not installed on winbox, confirmed via `python -c "import faster_whisper"` → `ModuleNotFoundError`, skipped per the task's own fallback instruction)
50ms-window RMS envelope on the mono 8kHz downmix, threshold at 12% of peak (max RMS 8121.5 → threshold 974.6), bursts merged across gaps <150ms:

**11 voiced-burst segments** detected: 0.30–1.20s, 2.00–3.00s, 3.35–3.90s, 5.05–6.85s, 7.90–9.00s, 11.45–12.45s, 13.10–14.15s, 14.55–15.25s, 15.80–17.15s, 17.60–19.10s, 19.80–19.90s.

The sheet's own REVIEW ORDER header says "SIX LINES" but only lists 5 quoted speaking turns (Dupe once, buyer three times, Valder once). 11 bursts is higher than either count, most plausibly explained by intra-line pauses inside multi-sentence turns (Dupe's opening is three sentences; Valder's line is two clauses) rather than extra or wrong dialogue — but this is **not confirmed**, since wording cannot be verified without a transcript. The final tiny burst (19.80–19.90s, 0.10s) falls inside the unscripted black tail (see above) and is more likely noise crossing threshold than a real vocal burst, but is reported as measured.

## Verdict
**FLAGGED.** Four real defects, all fixable and none catastrophic: (1) the clip cuts to solid black in its last ~0.25s instead of ending on the buyer's calm face; (2) the wall mark measures well outside canon rule 8's numeric floor (thin hairline web, not the sheet's own "thick/solid/heavy" description); (3) Valder smiles for ~0.2s at the cut into his single before resolving to the scripted expression; (4) his blazer sleeve intrudes into the CHEQUE TWO-SHOT's frame edge, and the cheque's sum is legible-in-pattern but not crisply legible through six sampled frames. Everything else on the sheet's REVIEW ORDER passes: four on-time hard cuts, locked camera inside every shot, one of each character throughout, the buyer's wardrobe and Valder's non-touching of the cheque both clean. Per the standing rule, the operator does not self-certify; this goes to the CTO/CEO with the exact prompt and frame paths above.

## Filing
No Drive OAuth token on winbox (per the task brief, did not attempt any upload path). File left in place for the CTO to pull over SSH and file as `S15e-ALL-TheChequeInOne-Fix1.MP4` in `All Scene/Fix-2` (`1rkCQ5SSZeOvyX-0UZXe3OvBtFhObHrkw`) whatever the verdict:
- Path: `C:\Users\UsEr\Downloads\hf_20260908_214942_8d2516ed-6c16-4bf0-a308-419222760a0f.mp4`
- Size: 18,536,142 bytes
- MD5: `b3f399016af28e267d0dc0b724a780f2`

## Sheet
TAKE LOG appended in `docs/prompts/absence/s15e-all-fix1-the-cheque-in-one.txt` with the fire record; this file adds the full landing + verdict record. Both committed on this branch.

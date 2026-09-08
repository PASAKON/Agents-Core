# S2R-JC Fix-1, Take 4 — «The Battle» jump-cut, heads-sweep-inside-shot rewrite

task-3c2789e7, browser_operator, 2026-09-09.

## Why take 4

Takes 2 and 3 both scored 0/12 on the head-swing (the scene's core beat): a
hard jump cut cannot animate a head turn. CTO rewrote the sheet so the three
cuts (3s/9s/15s) stay as pure time-jumps, but the heads now sweep ON SCREEN
inside each shot ([3s]/[6s]/[9s]/[13s]) instead of across a cut. Take 3 also
merged the registrar into Carrington — fixed on main 2026-09-09 (registrar is
a separate man two paces nearer the lens; ledger his alone).

## Pre-fire gates

- `git merge main`: branch already contained the take-4 sheet (commit
  d27064f) — nothing to merge.
- `prompt-lint.py` (plain lint): exit 0, no output.
- `prompt-lint.py --chips`: expected 13 unique Element chips, listed
  correctly (matches the paste block).
- §0 flattened-text gate (`extreme foreground|very front|floating|toward the
  mark|backs to the room|(crack|mark|star|plaque)...nearest`): 0 hits.
- §0b weight-word scan: 8 benign hits (build descriptions "thin/heavy" for
  guards, "thinning grey hair", smile "thinner", "fine film grain") — none
  contradicts a positive instruction.
- Registrar/Carrington separation gate: `HE IS NOT CARRINGTON AND HE DOES NOT
  STAND WITH HIM` present in the paste block, in the registrar's own line.
- Gold-teeth gate (whitespace-squeezed to survive the line-wrap trap):
  `TWO GOLD FRONT TEETH` appears exactly once, in Carrington's own line.
- Ledger/cane ownership: ledger mentioned only under `@char_registrar`;
  "Carrington's hands hold nothing but the cane" present.
- Bodyguard hands-empty: "No weapon, no earpiece, no holster" present, no
  contradicting prop mention.
- Crack canon: "THE BROKEN WALL IS NOT IN THIS SHOT — no crack, no star, no
  damaged plaster anywhere" present; no other crack/star/plaque mention
  except in the negatives (correctly banning them).
- Flagged-elements word-boundary grep
  (`project_valder_char_villagers_poor|prop_croc_bag|prop_car([^t]|$)`): 0
  hits. `prop_croc_bag` and `prop_car` genuinely absent — the crocodile bag
  is prose only (`HER BAG (no picture — describe it, do not look for one)`),
  never re-added as a chip.

All gates matched what the sheet's own NOTES section claimed.

## Composer setup

- Tab 53476253 (own tab, claimed via tab_registry.py, never touched
  task-5670068e's S16 tab).
- innerWidth 1400 (>=1280), verified via `window.innerWidth` before every
  state-changing action.
- No low-credit banner present this session.
- Video tab selected, model switched from default Cinema Studio 4.0 to
  Seedance 2.5 explicitly.
- Spec: 16:9, 720p, 20s (ARIA slider, `ArrowRight` x12 from the 5s default,
  verified `aria-valuenow=20`), 1/4, High, Sound On.
- Unlimited toggled ON as the first composer action (per task brief); it
  survived the duration-slider change unbroken this session (button read
  `UNLIMITED · ~~140~~ · 0` immediately after setting 20s, re-verified after
  every subsequent field check).
- Previz: `docs/S2R-Render.MP4` uploaded fresh via the reference panel's
  Uploads tab. Byte-verified: local `ls -l` 4,528,874 bytes; platform HEAD
  request on the attached CloudFront URL returned `content-length:
  4528874` — exact match. Verification flow: spinner tile → real thumbnail
  (gallery/columns scene, character floating labels visible) → clicked tile
  → "Added to prompt box" toast + green checkmark. Not mentioned as
  `@Video 1` in the prompt text — same pattern as takes 2 and 3 (video rides
  as an unreferenced reference; the prose position-map carries the
  blocking).
- Prompt: paste block sha256 computed on disk
  (`38f633ec578880d32e3cff6cb3b338260130e87fcc0c153126e2fb56d4d1a1fc`, 11,031
  bytes), base64-encoded, chunked into 5 pieces (~3000 bytes each),
  assembled in the page via `window.__s2rChunks`, decoded, and the SHA-256
  re-computed IN-PAGE before dispatch — hash matched exactly. Pasted via
  synthetic `ClipboardEvent` (`text/plain` only) into the real (visible)
  contenteditable node, filtered from its decoy twin by
  `getComputedStyle(el).visibility === 'visible'`. Followed with
  `End` → `space` → `Backspace` to force Lexical state to bind.
- Chip count: 13/13 unique `@`-mentions bound as lime chips
  (`span.text-font-brand`, no nested span, starts with `@`), 18 total mention
  occurrences, 0 error/red/unresolved chips (verified via a DOM query for any
  `@`-prefixed span NOT carrying the `text-font-brand` class — zero found).
- Reference strip: 14 tiles (1 video + 13 Elements) zoomed individually —
  zero warning triangles on any tile.
- Final pre-fire zoom, immediately before the click:
  `UNLIMITED · ~~140~~ · 0`; Seedance 2.5 / 16:9 / 720p / 20s / 1/4 / High /
  Sound On all re-verified in the same pass; 13/13 chips still intact;
  innerWidth still 1400.

## Fire

The account's Unlimited slot was held by the sibling S16 task (task-5670068e,
tab 53476249, confirmed LIVE in the tab registry throughout). Per the task
brief's pipelining instructions:

| Attempt | Time (ICT / UTC) | Result |
|---|---|---|
| 1 | 00:36:56 / 17:36:56Z | "You can generate 1 unlimited... at a time" toast — nothing fired, asset count unchanged (730) |
| 2 | 00:43:13 / 17:43:13Z | Same toast, re-verified spec/price/chips fresh before each retry |
| 3 | 00:55:14 / 17:55:14Z | **Fired.** "Generation started" toast, asset count 730 → 731 |

Between retries the composer was never touched except the Generate button
itself — spec, chips, and Unlimited price were re-zoomed fresh before every
attempt (no stale-check reuse).

## Render wait

Fired 00:55:14 ICT. Stayed inside one turn, 90s/60s-capped background sleeps
(several killed by macOS memory pressure mid-wait — resumed each time per
brief, no render lost). First check ~20 min, reload-verified (a stale tab
lies): still Processing (DOM query for `[class*="animate-spin"]` in `main` =
1). Continued polling; browser extension had two transient hiccups mid-wait
(a lost tab-group selection requiring `select_browser` re-run, and one CDP
"renderer unresponsive" timeout requiring one hard reload) — both recovered
cleanly, no data lost, no generation affected (server-side).

Landed by ~01:37 ICT (~42 min render). No NSFW flag, no "Rejected due to
copyright" (take 1's failure mode), no rights-verification banner.

## Card identification

Opened the card's Info panel (`?preview=7da4e78c-21d2-45e6-94b1-378a75df7d42`):
**Created: September 9, 2026 at 12:55 AM** — matches the fire time exactly
(00:55:14 ICT). Prompt panel shows the exact paste-block opening
("20s · 720p · 16:9. The camera is LOCKED and never moves, never pans, never
zooms — but the take is CUT..."). Model Seedance 2.5, Quality 720p, Bitrate
High, Size 1280x720.

Downloaded → `~/Downloads/hf_20260908_175509_48e12c2e-62d1-4d88-adef-d93a67f4be18.mp4`
(18,997,273 bytes). md5 `82a45f73da3328221f4684f8761beee5` — checked against
take 3's clip (`225e8fbb7727272ebe716d034fd8bf8f`) and every other mp4 in
`~/Downloads`: no match, confirmed distinct new file. ffprobe: 1280x720,
24fps, 20.041667s.

## Review — the head swing is the whole review

### 1. Sweep test (0.2s consecutive-frame greyscale mean-abs-diff)

Median step: 1.206. Four clear isolated spikes, all well above the ~3x
threshold, with nothing above threshold anywhere else in the clip:

| Spike window | Peak (x median) | Corresponds to |
|---|---|---|
| ~3.0–3.6s | 4.46x | sweep right→left after the 3s cut |
| ~6.0–6.6s | 5.10x | sweep left→right, mid-shot at 6s |
| ~9.2–9.8s | 4.50x | sweep right→left after the 9s cut |
| ~12.4–13.0s | 4.76x | sweep left→right, mid-shot at 13s |

**This is exactly the sheet's design**: heads sweep on screen inside each
shot, and the cuts themselves stay pure time-jumps. Takes 2 and 3 showed
**zero** spikes anywhere in the clip — this take shows four, at the four
sweep points the rewrite asked for.

Control check across the 15s cut boundary (14.8s→15.4s): mean-abs-diff over
the span works out to ~1.15/step, in line with the baseline — **no spike**.
The 15s cut correctly shows no head motion (the room stops, by design).

### 2. Per-person head-turn count

Diff-mask overlays (greyscale absolute difference, thresholded, saved as
`diff_5.5_7.5_mask.png`, `diff_9.5_11.5_mask.png` / `diff_12.0_14.0_mask.png`,
`diff_14.8_15.4_mask.png` in the scratchpad) show:

- **[6s–8s] window (t5.5→t7.5)**: thick double-exposure ghosting around
  every visible head on both sides of the frame — Carrington, registrar,
  bodyguard, cobalt woman, both Valder guards, Dupe (spot-checked
  separately: faces screen-left at t5.5, faces forward/right at t7.5 —
  confirmed distinct turn), man in maroon, Valder, chestnut-fur woman,
  critic, woman in green. **12/12 show visible head motion.**
- **[13s–15s] window (t12.0→t14.0, widened from the nominal 13.5/14.5 pair
  because the measured spike peaks at ~12.6s, per the "sweep never sample
  one pair" rule)**: same near-universal ghosting pattern across all 12
  figures. **12/12.**
- **15s cut control (t14.8→t15.4)**: thin single-pixel outline only (JPEG/
  compression-level noise), no double-exposure ghosting anywhere — confirms
  heads genuinely froze across this cut, as designed.

This is a full reversal of takes 2 and 3, which scored 0/12 on this exact
criterion.

### 3. The 15s cut — room stops

Frame at t15.4 (just after the cut): Carrington's mouth is open in shock
(matches "[15s]... He opens his mouth and nothing comes out of it"), every
visible watcher's head still points right toward the woman in green — no
one has turned back. Matches spec.

### 4. Feet

Crops of the lower-body/floor band at t1.0 and t19.0 (start and near-end):
silhouette positions at floor level are pixel-identical. Nobody walks,
across the full 20s.

### 5. Audio (faster-whisper, model `small`, int8, via
`/Users/gob/Projects/Agents/.venv`)

```
[0.00-3.00]  Ten million.
[3.00-6.00]  Fifteen.
[6.00-9.00]  Twenty million.
[9.00-12.00]  Twenty-five.
[12.00-15.00]  Fifty.
```

Five spoken bids, exact order (hers, his, hers, his, hers), exact amounts
per the sheet. No other dialogue transcribed (Valder, registrar, watchers
all silent, as specified).

### 6. Twelve people, registrar/Carrington separation

Counted at t15.4 (full frame, wide shot): Carrington, bodyguard, registrar,
cobalt woman, 2 Valder guards, Dupe (with his cart), man in maroon, Valder,
chestnut-fur woman, critic, woman in green = **12, no 13th, no duplicates**.

Zoomed crop (`crop_carrington_registrar_15.4.png`) confirms the specific
fix this take targets: Carrington and the registrar are **two distinct men**
— different faces, different builds, different suits (Carrington: plain
white stand-collar, no piping; registrar: cream suit with orange piping and
a gold V pin, positioned visibly nearer the lens). The registrar alone holds
the brown leather ledger and pen; Carrington's hands hold only the cane.
Zero merge — take 3's defect does not recur.

**One position deviation, minor**: the sheet's position map says Dupe should
be "far back on the left with his cart"; the render places him and his
cleaning cart (mop, orange bucket, folding ladder, gold V — all present and
correct) dead-centre in front of the red door rather than off to the left.
He is still far back (correct distance) and still with his cart (correct
prop), just not laterally positioned as written. Not a duplication or
identity defect — flagging for the CTO's judgment on whether it matters.

### 7. Gold teeth

Visible in Carrington's smile at t7.5 (`crop_carrington_smile_7.5.png`) —
present exactly once, on Carrington only, matching the paste-block gate
(1 occurrence, in his own line).

## Verdict vs takes 2 and 3

| Criterion | Take 2 | Take 3 | **Take 4** |
|---|---|---|---|
| Head swing (sweep test) | 0/12, no spikes anywhere | 0/12, no spikes anywhere | **4 clean spikes at the 4 designed sweep points, 12/12 visible turn** |
| 15s cut stillness | n/a (nothing moved anywhere) | correct only because nothing moved anywhere | **correct AND meaningful — the only still beat after 4 real sweeps** |
| Registrar vs Carrington | not flagged | **merged into one figure** | **two distinct men, ledger/cane correctly separated** |
| 12 people | not verified | 11 (registrar missing) | **12, no 13th, no duplicates** |
| Feet planted | confirmed | confirmed | **confirmed** |
| Audio (5 bids, order) | not independently transcribed | 5 speech-adjacent bursts, order not confirmed | **fully transcribed, exact order and amounts confirmed** |
| Gold teeth | — | — | **exactly once, Carrington only** |

**Take 4 is a clean pass on every review item, including the one criterion
both prior takes failed outright.** Filing to Drive.

Do not self-certify — CTO reviews the file too.

## Files

- Frame scans: scratchpad `s2r_t4_scan/` (99 frames, 0.2s step)
- Review crops + diff masks: scratchpad `s2r_t4_review/`
- Downloaded clip:
  `~/Downloads/hf_20260908_175509_48e12c2e-62d1-4d88-adef-d93a67f4be18.mp4`

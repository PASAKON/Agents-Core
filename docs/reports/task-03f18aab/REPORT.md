# task-03f18aab: BL EP61 «Tickmill 1 ล็อต จ่ายจริงเท่าไหร่» A/B cut

Voice 68.017 s, 2040 frames at 30 fps, 1080x1920, both arms. Nothing uploaded to Drive, nothing posted.
If posting slips past 14 Oct 2026 the Tickmill numbers are stale: that is the CMO's call.

## Finals

| Arm | File | Sheet |
|---|---|---|
| B (bare list) | `/opt/MoonieXHQ/Work/bl-ep61/cut/v1/final-ep61-v1.mp4` | `cut/v1/sheet-ep61-v1.jpg` |
| A (headline plate) | `/opt/MoonieXHQ/Work/bl-ep61/armA/v1/final-ep61-armA-v1.mp4` | `armA/v1/sheet-ep61-armA-v1.jpg` |

Both: h264 1080x1920, 2040 frames, video 68.000 s, audio 67.988 s, loudness -15.51 LUFS, TP -0.94.

## Mode counts

| Arm | FF | COMP | EVID | KIN | beats |
|---|---|---|---|---|---|
| B | 2 | 11 | 14 | 3 | 30 |
| A | 0 | 13 | 14 | 3 | 30 |

Arm A turns HOOK-0 and HOOK-1 (the two full-frame avatar beats) into COMP beats with no plate image, so the avatar sits
below the headline plate. Same beat times, same captions.

KIN lines (PATTERN-3 S07, CURIOSITY-1 S20, SUMMARY-1 S23): every one had a b-roll clip in `broll/`. **No KIN line was left without b-roll.**

## How arm A differs, and why

The only variables, per the brief: the first 3 s, and the persistent headline plate.
- Headline plate (everything above y=560 darkened, two lines `Tickmill 1 ล็อต` / `จ่ายจริงเท่าไหร่?`, `เท่าไหร่` red, brand mark on the left) on every frame.
- Stamp under it: `ข้อมูลจากหน้าเว็บของ Tickmill ณ 13 ต.ค. 2569`. The per-still source chip moves to y=528, under the stamp.
- 0 to 3 s: backdrop stills tm-classic (0 to 1 s), tm-raw (1 to 2 s), tm-formula (2 to 3 s), darkened, behind the avatar and the plate.
- Arm B opens on the plain studio close-up: no text at frame 0, first caption fades in right after 1.0 s, no plate, no stamp.

Backdrop swap check: no backdrop shows a readable CTA, a person or an uncensored name, so none was swapped.
The checker passed `text_over_face: []` for arm A. The tm-classic backdrop has a half-hidden `Spreads From` label behind
the avatar's shoulder at 0 to 0.5 s; its key words ("and zero commissions", the `MT4/MT5` chips) are well clear of the head.
The censored green bar in that still stays censored (nothing was re-exposed).

Note: HOOK-1's covering still, tm-classic, is not used as the arm-B opening. The brief mandates the studio close-up.

## Gates (quoted)

Arm B, `finish.sh B`:
```
MERGE OK   frame_count: actual 2040, expected 2040, tolerance 1; empty_frames []; seam_failures []; audio_offset ok 0.0 s; extra_caption_styles []
checker rc=0  pass true; text_over_face []; comp_evidence_landing []; out_of_safe_area []; credit_missing []
brand mark: min_ratio 0.9946 at 14.2 s, 0 failing frames of 2040
loudness: input_i -15.51, input_tp -0.94
ffprobe: video 68.000000 s, 2040 frames; audio 67.988005 s
bl_tools.py verify: t=3.4 s lag +0 ms r=0.991 ok; t=30.6 s lag +0 ms r=0.980 ok;
  lipsync A seated 0.00 s lag +0 ms r=0.991 ok; B seated 28.72 s lag +0 ms r=0.991 ok; C seated 53.93 s lag +0 ms r=0.989 ok; VERIFY PASSED
```
Arm A, `finish.sh A`:
```
MERGE OK   frame_count: actual 2040, expected 2040, tolerance 1; empty_frames []; seam_failures []; audio_offset ok 0.0 s; extra_caption_styles []
checker rc=0  pass true; text_over_face []; comp_evidence_landing []; out_of_safe_area []; credit_missing []; kinetic_overflow []; headline []
brand mark: min_ratio 0.9926 at 51.833 s, 0 failing frames of 2040
loudness: input_i -15.51, input_tp -0.94
ffprobe: video 68.000000 s, 2040 frames; audio 67.988005 s
bl_tools.py verify: identical lag/r values to arm B (A 0.991, B 0.991, C 0.989); VERIFY PASSED
```
Both arms: 2040 frames, equal. The seats are the ORIGINAL lipsync files in `Work/bl-ep61/drive/AI Drafts/` at the offsets in `offsets.json` (0.00, 28.72, 53.93).
The merge is against `audio-hq-decoded.wav` (PCM): the mp3 container reports a wrong duration.
Part frame counts (9 windows, seams on beat starts at 8.3, 16.6667, 23.9333, 31.3, 38.8667, 47.1, 54.3667, 60.7): 249, 251, 218, 221, 227, 247, 218, 190, 219 = 2040.
Checker run with `--take-table prototypes/bl-ep61/take_table.json --composition <comp-full/index.html>`.

`credit_missing: []` is a **geometric** check (a chip-shaped element exists where a real still is shown), not keyed to the
chip's text. The chip text `ที่มา: เว็บไซต์ Tickmill ณ 13 ต.ค. 2569` was put on every Tickmill still by the plates builder and read by eye on the sheets. No tool change was needed.

## Per-frame verdicts (what I looked at)

Frame sheets, 3 to 6 columns of the 1080x1920 frame. Times are on the episode clock.
Arm B was first judged on a first render, then **re-rendered in full** after the Thai-word line-break fix; the re-render was
re-checked on `sheet-ep61-v1.jpg` (every beat, listed below) plus a 9-frame sheet of the changed beats.

| t | beat | arm B | arm A |
|---|---|---|---|
| 0.0 / 0.5 / 1.0 | HOOK-0 | OK: studio close-up, no text, brand mark only | OK: backdrop tm-classic dark, plate and stamp on, avatar below; no CTA/person/name |
| 1.3 / 2.0 | HOOK-1 | OK: caption `หน้าบัญชี Tickmill เขียนว่าคอมมิชชันศูนย์` on the studio shot | OK: tm-raw then tm-formula backdrop; `Understanding trading costs` readable, clear of head |
| 3.0 / 3.5 | HOOK-2 | OK: Raw row `Spreads From 0.0 pips` | OK |
| 5.5 | HOOK-3 | OK: Tickmill logo crop | OK |
| 7.3 | HOOK-4 | OK: CLASSIC / RAW ACCOUNT headings (no TradingView card) | OK |
| 9.5 | PATTERN-1 | OK: formula line; caption `สเปรด คอมมิชชัน สว็อป` no mid-word break | OK |
| 13.0 | PATTERN-2 | OK: swaps sentence, two rows | OK (mid-seam frames also looked at) |
| 15.0 | PATTERN-3 KIN S07 | OK: text mid-animation at this sample | OK |
| 17.6 / 19.8 | CONTEXT-1/2 | OK: example paragraph, box covers `EUR` | OK |
| 22.2 | CONTEXT-3 | OK: Tickmill logo, date line | OK |
| 25.0 / 27.8 | MAIN-1/2 | OK: formula rows, own card `100,000 x 0.0001 = $10` | OK |
| 30.0 | MAIN-3 | OK: `variable spreads starting from 1.6 pips and no commissions` | OK |
| 32.3 / 34.3 | MAIN-4/5 | OK: Classic card 1.6 x 1 x $10 = $16.00, commission $0.00, total $16.00 | OK |
| 36.3 | MAIN-6 | OK: Raw line + `0.0 x 1 x $10 = $0.00` | OK |
| 38.0 / 40.0 | MAIN-7/8 | OK: `3 USD and 6 USD` crop, no TradingView/model photo | OK |
| 41.6 | MAIN-9 | OK: both cards, same size and ink, Raw commission `$3 x 2 ข้าง = $6.00`, total `$6.00`, no arrow, no $7 | OK |
| 43.5 | CURIOSITY-1 KIN S20 | OK | OK |
| 45.5 | CURIOSITY-2 | OK: Classic card, `Spreads From 1.6 pips` | OK |
| 48.4 | CURIOSITY-3 | OK: floor card, label clear of the border | OK |
| 50.7 | SUMMARY-1 KIN S23 | OK | OK |
| 52.8 / 55.5 / 58.5 | SUMMARY-2/3/4 | OK: checklist row 1/2/3 boxed per beat | OK |
| 62.0 | SUMMARY-5 | OK: caption `กูไม่ได้แนะนำ เจ้าไหน แค่ชี้วิธีดูให้เป็น` kept verbatim | OK |
| 64.8 | SUMMARY-6 | OK: CTA `เช็กลิสต์` | OK |
| 66.8 | SUMMARY-7 | OK: date line | OK |
| 8.26 / 8.3, 16.6 / 16.67, 23.93 | seams | OK: no flash, no jump (frame before and after) | OK |

Not looked at: every beat at a single sample only (one frame per beat, so a fade or text reveal in the middle of a beat
was not seen); the last 2 frames before 68.0 s; arm A's frames inside HOOK-0 between 0.5 and 1.0 s; the seams at
31.3, 38.87, 47.1, 54.37 and 60.7 s in arm A (frame counts and the merge's `seam_failures []` stand in for those). The
arm B seams at 31.3 to 60.7 were seen on the first render only.

## Lip-sync look (3 mouth sheets, 4 frames each from the lipsync parts)

- Part A (0 to 16 s): OK, mouth shapes follow the speech; head moves about 100 px up and sideways, expected.
- Part B (28.72 to 41.84 s): OK.
- Part C (53.93 to 67.67 s): OK. At t=1.2 the mouth is closed (a pause) and at 12.2 open: consistent with the script.
No part looked off. The numbers agree: `verify` lag +0 ms, r 0.989 to 0.991 on all three seats.

## Exact Tickmill words each still relies on

All from the 7 Tickmill stills only; own arithmetic is marked "own".
- HOOK-2 (tm-raw): `Spreads From 0.0 pips`
- HOOK-3, CONTEXT-3 (tm-header): the Tickmill logo only
- HOOK-4 (tm-header): `CLASSIC ACCOUNT`, `RAW ACCOUNT`
- PATTERN-1, MAIN-1 (tm-formula): `How do you calculate your transaction cost?`, `Trade Cost = Spread × Trade Size × Pip Value`
- PATTERN-2 (tm-swaps): `Swaps are overnight interest charges applied when you hold a position past 00:00 platform time`
- CONTEXT-1/2 (tm-raw-example): `Example: If you trade 1 lot of EURUSD, which has a contract size of 100,000 EUR, then your commission per side would be 3 USD and 6 USD round turn (or the equivalent amount in the currency of your account).`
- MAIN-3 (tm-classic-para): `... with variable spreads starting from 1.6 pips and no commissions.`
- MAIN-6 (tm-raw-example): `fluctuating spreads starting from 0.0 pips.`
- MAIN-7/8 (tm-raw-example): `... commission per side would be 3 USD and 6 USD`; `... round turn (or the equivalent amount in the`
- CURIOSITY-2 (tm-classic): `Built for traders who prefer simplicity. Trade costs are included in the spread, with spreads from 1.6 pips and zero commissions.`, `Spreads From 1.6 pips`
- Own, no chip: MAIN-2 `100,000 x 0.0001 = $10`; MAIN-4/5 Classic card; MAIN-9 both cards; CURIOSITY-3 floors; SUMMARY-2 to 7 strips and checklist.

Calc cards, exact: Classic = 1.6 x 1 x $10 = $16.00, commission $0.00, total $16.00. Raw = 0.0 x 1 x $10 = $0.00, commission $3 x 2 = $6.00, total $6.00. No $7 line anywhere. No "cheaper/better/แนะนำ", no good/bad colouring, no arrow.
The TradingView card and the model photo are cropped out of tm-header and tm-classic-para (crops, not blurs). Censored areas were never re-exposed.

## Known cosmetic issues

- First glyph clipped at x=0 on the tm-classic-para and tm-raw-example crops (the source stills are cut at the left edge).
- The matte head scale drifts about 30% over each lipsync part (take drift in the source, not the cut); head tops are measured per take over the used range (`take_table.json`: 903.6 / 933.28 / 999.92).
- tm-classic does not show the Tickmill name (header is Tickmill-wide only in tm-header); the chip carries the attribution.
- Brand mark is nearly invisible on white plates (ratio check passes, 0.99).
- Arm A: the stamp sits tight under the headline's second line.
- Captions keep `กู` (verbatim from SCRIPT.tsv col 2, brief says keep it). My own on-screen text has no crude word and no em dash.
- bl_compose clamps the avatar windows slightly inside the takes (lip_a 15.95, lip_b 41.77, lip_c 67.58); SUMMARY-7's `avatar_until` is 67.55 for that reason. Take coverage holes (16.01 to 28.72 s and 41.84 to 53.93 s) are filled with EVID/KIN beats.

## Files (worktree)

`prototypes/bl-ep61/`: `beats.json`, `armA/beats.json`, `take_table.json`, `segments.json`, `plates.json`, `make_plates.py`, `make_beats.py`, `render_v1.sh`, `finish.sh`, `armA/render_window.py`, `make_render_meta.py`, `render-meta.json`, `armA/render-meta.json`, timing scripts, `timings.tsv`.
No mp4 in git.

## Skill learning

- COSTLY  [CMO_Procedure_BlackLiquidity_Cut | no owner] : transcribe.py ran 4656 s on the CPU-starved box and then dropped 21.4 to 52 s of speech · evidence: task-03f18aab, `prototypes/bl-ep61/timing/` · prevented by: run the aligner on the known script text (Needleman-Wunsch plus snapping) and use whisper only for timestamps
- MISSING [CMO_Procedure_BlackLiquidity_Cut §ASR] : whisper drops or loops on number-heavy speech; chunked re-transcription with repetition_penalty=1.3 and no_repeat_ngram_size=3 fixed it · evidence: task-03f18aab, `prototypes/bl-ep61/align-report.txt`
- MISSING [CMO_Procedure_BlackLiquidity_Cut §checker] : `credit_missing` is geometric, not keyed to the chip text, and nothing says so · evidence: task-03f18aab, both checker json files
- MISSING [CMO_Procedure_BlackLiquidity_Cut §captions] : Chrome in the render has no Thai dictionary, so captions break mid-word (ส|เปรด, เจ้า|ไหน, ข้อ|ความ) and no gate sees it; wrap each word in `<span class="nb">` (white-space:nowrap), `caption()` accepts HTML · evidence: task-03f18aab fff1ac79
- MISSING [CMO_Procedure_BlackLiquidity_Cut §tools] : `bl_tools.py` lives in the skill's `scripts/` and needs the shared venv python (system python3 has no PIL) · evidence: task-03f18aab
- MISSING [CMO_Procedure_BlackLiquidity_Cut §plates] : the generator's `media/` is a COPY; after rebuilding plates, re-sync `media/real` into it or the render shows the old plate · evidence: task-03f18aab (floor card label fix)
- MISSING [CMO_Procedure_BlackLiquidity_Cut §plates] : dark-page crops go on WHITE plates, since bl_merge refuses a flat dark frame · evidence: task-03f18aab
- MISSING [CMO_Procedure_BlackLiquidity_Cut §COMP] : bl_compose clamps the avatar windows slightly inside the take length (lip_c ends 67.58, not 67.67), so `avatar_until` above that breaks the render · evidence: task-03f18aab SUMMARY-7
- COSTLY  [no owner] : Contabo hooks: the cwd guard blocks `cd`/paths that leave the worktree root, and foreground `sleep` is blocked; use absolute paths and bounded `for ... sleep 5` loops · evidence: task-03f18aab
- MISSING [CMO_Procedure_BlackLiquidity_Cut §verify] : seam sampling with `-ss` just above the frame pts skips a frame; use 8.26 for the frame before an 8.3 seam · evidence: task-03f18aab (a sample at 8.2667 returned frame 249)

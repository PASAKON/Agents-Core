# task-3ae66e7a: BL EP60 «GB (Goldenburg) ยังมีใบอนุญาตอยู่ไหม», arm B and arm A

Video editor (Sonnet 5.5), 2026-10-04. Branch `agent/video_editor-task-3ae66e7a`. Nothing pushed, no Drive upload, no post. Only source: the 11 WikiFX stills in `media/real/` (plus the voice, the lipsync parts and the 40 Drive scene clips).

## Finals (outside git)

| arm | file | duration | frames | LUFS |
|---|---|---|---|---|
| B (plain studio open, no text at frame 0) | `/opt/MoonieXHQ/Work/bl-ep60/cut/v1/final-ep60-v1.mp4` | 90.20 s | 2706 | -15.34 |
| A (headline plate + date stamp) | `/opt/MoonieXHQ/Work/bl-ep60/armA/v1/final-ep60-armA-v1.mp4` | 90.20 s | 2706 | -15.34 |

Sheets beside them: `sheet-ep60-v1.jpg`, `sheet-ep60-armA-v1.jpg` (16 frames each; arm B times 0, 0.5, 1, 2, 6.5, 13, 39.6, 83, 19.6, 28.6, 33, 50, 64.4, 56.5, 75.6, 15.6 s, arm A times 0, 0.5, 1, 2, 2.95, 3.6, 6.5, 13, 19.6, 33, 39.6, 50, 64.4, 83, 87.9, 15.6 s; four of arm B's frames are from the final after the plate fixes, the rest from the render before them, same plates apart from the three that were replaced).
Frame counts equal (2706 = 2706). 12 render windows per arm, each 6.5 to 8.9 s, seams exactly on a beat's t0. Plan, plates and scripts are in `prototypes/bl-ep60/`.

## Mode counts

| arm | FF | COMP | EVID | KIN | beats |
|---|---|---|---|---|---|
| B | 2 | 14 | 14 | 11 | 41 |
| A | 0 | 16 | 14 | 11 | 41 |

Cut rhythm: 41 beats in 90.2 s, a beat every 2.2 s on average (1.5 to 3.4 s, the voice's own phrase boundaries; every beat starts 0.10 s before its line). FF only in the opening (0 to 3.2 s) because arm A refuses FF under the plate. COMP only where a lipsync take covers the avatar: lip_a [0, 14.3), lip_b [38.14, 52.94), lip_c [74.17, 89.72); the two lip holes (14.3 to 38.14 and 52.94 to 74.17) are EVID or KIN only.
**KIN lines without b-roll: none.** All 11 KIN beats name their own scene clip (S06, S25, S11, S03, S30, S02, S21, S24, S20, S29, S16). Only generic non-character clips were used.

## How arm A differs, and why

Arm A = arm B with only what the headline plate forces (`CHANGES_A` in `make_beats.py`): HOOK-0 (0 to 1.0 s) and HOOK-1 (1.0 to 3.2 s) change from FF to image-less COMP so the avatar rides the three backdrops (`real/gb-article-oct.png` @0, `gb-warning.png` @1, `gb-licence.png` @2; no backdrop swapped). Headline `WikiFX: GB เคยมีใบ / ถูกเพิกถอนแล้ว`, red `เพิกถอน`, bug on the left, stamp `ข้อมูลจาก WikiFX ณ 1 ต.ค. 2569`, credit chip moved under the stamp (`render_window.py`). The plate stays for the whole clip; every other beat (caption, plate, box, b-roll, timing) is byte-identical to arm B. The claim on the plate is WikiFX's own words (below) with the source and the date it was looked at; no other claim was added. Because the plate and the scrim cover the top 560 px, arm A's EVID stills sit under the scrim at their top edge (see cosmetic issues).
Backdrop check at 0 to 0.5 s: the article title sits at y 400 to 500 under the plate's scrim, the avatar's hat is at y 900 and below, so the backdrop's key words are clear of the head (EP59's hat-over-title problem does not repeat).

## What the screen says, and where WikiFX said it (exact words)

- Article (`gb-article-oct`), title: «โบรกเกอร์ GB เคยอยู่ใต้ CySEC แต่ใบอนุญาตถูกเพิกถอน! มีอะไรอยู่เบื้องหลัง» and: «ซึ่งฟังดูน่าเชื่อถือไม่น้อย แต่ข้อมูลล่าสุดพบว่าใบอนุญาตนี้ถูกเพิกถอนไปแล้ว (สถานะ Revoked) ทำให้ปัจจุบัน GB ดำเนินธุรกิจโดยไม่มีกรอบกำกับดูแลที่มีผลบังคับใช้เลย».
- Article (`gb-article-revoked`): «อย่างไรก็ตาม สถานะใบอนุญาตปัจจุบันคือ “ถูกเพิกถอน” (Revoked) ซึ่งหมายความว่า GB ไม่มีใบอนุญาตกำกับดูแลที่มีผลบังคับใช้จริงในปัจจุบันแล้ว ... ซึ่งนักเทรดควรตรวจสอบสถานะล่าสุดกับ CySEC โดยตรงก่อนตัดสินใจ». The same article carries more WikiFX opinion (it calls GB not a safe choice); the plates crop around it, nothing of it is on screen.
- Warning card (`gb-warning`, dated 2026-10-01): «คำเตือน: ระดับคะแนนอยู่ในระดับต่ำ โปรดหลีกเลี่ยง ... โบรกเกอร์นี้ไม่มีการกำกับดูแลฟอเร็กซ์ที่ถูกต้อง โปรดตระหนักถึงความเสี่ยง!».
- Licence tab (`gb-licence`): «ไม่พบใบอนุญาตซื้อขายฟอเร็กซ์ โปรดตระหนักถึงความเสี่ยง» and «ใบอนุญาตในการกำกับดูแลกำลังถูกตั้งข้อสงสัย».
- Related company (`gb-related`): tag «ยกเลิกการจดทะเบียน» on GOLDENBURG GROUP LTD(Cyprus).
- Survey (`gb-survey`, 2019-05-31, tag Good): «Goldenburg Group Limited เป็น บริษัท ที่ได้รับอนุญาตอย่างเต็มที่ภายใต้การควบคุมของ CySEC โดยมีใบอนุญาต CIF เลขที่ 242/14».
- Complaint (`gb-complaint`): only the breadcrumb, the date 2021-02-03 and two phrases the voice reads («ไม่สามารถถอนเงินได้», «ไม่สามารถติดต่อบุคคลที่ให้คำแนะนำได้»). **No complainant name, avatar, id, amount or pixelated tag is on any frame** (checked by eye on the PATTERN-2 frame and on the plate sheets for PATTERN-1/2; the plates are two small snippets on white, built so the rest of the page cannot appear). The gate condition for the "ถูกเพิกถอน" claim holds: it rests on WikiFX's own words above, attributed on the plate.
- "โกง" appears nowhere. The channel recommends no broker; the closing three tips are about checking, SUMMARY-7 says so. No em dash on screen.
- Credit «ขอบคุณภาพจาก WikiFX» is on every beat that shows a WikiFX still (`credit_missing []` on both arms); the 12 b-roll KIN beats show no still and carry none.

## Per-frame verdicts (what I looked at)

Arm B (final cut, sheets B1 to B5, one extra crop of PATTERN-3):

| t | beat | verdict |
|---|---|---|
| 0.0 | HOOK-0 FF | OK: studio close-up, no text, mark on. Hat is clear of the mark |
| 0.5 | HOOK-0 | OK |
| 1.0 | HOOK-1 | OK: no caption yet (0.16 s fade) |
| 2.0 | HOOK-1 | OK: first caption in |
| 6.5 | HOOK-3 COMP lip_a | OK: title plate readable, pill clear |
| 13.0 | PATTERN-2 COMP lip_a | OK: two phrases only, no name |
| 39.6 | MAIN-5 COMP lip_b | OK: small tile, text about 25 px |
| 83.0 | SUMMARY-7 COMP lip_c | OK after fix (the first cut's tile crop read as a broken half card; replaced by the title plate) |
| 19.6 | CONTEXT-1 EVID | OK: score tile left of the mark |
| 28.6 | CONTEXT-5 EVID | OK, text about 25 px |
| 33.0 | MAIN-2 EVID | OK |
| 50.0 | MAIN-10 EVID | OK after fix (heading was clipped at the left in the first render; now whole). Cosmetic, see below |
| 56.5 | MAIN-13 EVID | OK (the grey bar in the line is WikiFX's own blur, no name behind it) |
| 64.4 | CURIOSITY-4 EVID | OK after two fixes (text 15 px in the first render, then a box 8 px outside the safe area; now two rows at 1.5x, about 22 px) |
| 15.6 / 16.5 | PATTERN-3 KIN | 15.6 mid-animation (last word still revealing), 16.5 complete: three lines over the typewriter clip |
| 75.6 | SUMMARY-4 KIN | OK: `หนึ่ง` large, two lines under it |
| 87.9 | SUMMARY-9 COMP lip_c | OK |

Arm A (sheets A1 to A4): 0.0, 0.5 OK (plate, stamp, mark left; backdrop article, hat clear of the title); 1.0 OK (warning card visible, dated 2026-10-01); 2.0 OK (licence tab); 2.95 and 3.6 OK (seam into HOOK-2 on the warning plate, chip under the stamp); 6.5, 13.0 OK; 19.6 OK with a cosmetic (score tile top sits under the scrim); 33.0, 39.6, 50.0, 64.4, 83.0, 87.9 OK; 15.6 mid-animation as in B.
The frames at 0 to 3 s are the same video content as arm B everywhere except the plate area.

**Not looked at (judged by the machine gates only):** the seams (gate: 0 seam failures, ±3 frames), HOOK-2 and HOOK-4 in arm B, PATTERN-1 (plate sheet only), PATTERN-4, CONTEXT-2/3/4, MAIN-1/3/4/6/7/8/9/11/12, CURIOSITY-1/2/3/5, SUMMARY-1/2/3/5/6/8 in either arm, and the b-roll clips S06/S25/S11/S03/S30/S02/S21/S24/S29/S16 beyond S06 and S20. The EVID plate sheets (all 14) and the COMP plate sheets (all 14) were reviewed with the spotlight box and the pill band drawn on them before rendering.

## Gates

| gate | arm B | arm A |
|---|---|---|
| `bl_merge --beats` | MERGE OK: 2706 frames (expected 2706 ±1), empty_frames [], seam_failures [], audio offset 0.0 s, one caption style | same |
| `bl_checker --take-table --composition` | pass true; empty_frames []; out_of_safe_area []; text_over_face []; comp_evidence_landing []; credit_missing []; extra_caption_styles []; kinetic_overflow []; 4 KIN-entry frames excused (72.33 to 72.43, SUMMARY-3) | pass true; same lists empty; headline []; 0 excused |
| brand mark per frame >= 95% | ok, 2706 frames, min 98.8% at 87.7 s, 0 failing (t=0 and every seam included) | ok, min 99.2% at 3.87 s, 0 failing |
| `bl_tools.py verify` vs the ORIGINAL lipsync in drive/AI Drafts, seats 0.00 / 38.14 / 74.17 | VERIFY PASSED: voice sync +0 ms at 4.5/40.6/81.2 s (r .991/.990/.986); A, B, C +0 ms (r .991/.989/.992) | VERIFY PASSED, identical numbers |
| LUFS (two-pass linear loudnorm I=-15.0 TP=-1.0, then AAC 192k) | -15.34, true peak -0.91 | -15.34 |
| ffprobe frames | 2706 | 2706 |

Take table (`take_table.json`): lip_a head_top 903.04, cy 797; lip_b 968.56 / 862; lip_c 992.08 / 886 (lip_c's top is at the end of its used range, 15.53 s). The plates were built against it (14 COMP plates `fits=True`, each ends at zone bottom + 6, last text line clear of the pill by >= 8 px).

## Cosmetic issues (not fixed, none fails a gate)

1. Arm B frame 0 and the first seconds: the brand mark's red `LIQUIDITY` and underline disappear into the red neon behind the avatar, so only `BLACK` and the date read on those frames. The checker's 95% rule passes (it measures the mark's brightest level, not the red word).
2. MAIN-10 (both arms): the white page panel ends at about x 855 with grey beyond, and `(Cyprus)` touches the right edge of the spotlight box.
3. Arm A CONTEXT-1: the score tile's top edge and its red stamp sit under the scrim and show as a faint ghost beside the date stamp. Inherent to the plate (the EVID still starts at y 400), not moved so the two arms keep the same plates.
4. Arm A, 2.95 to 3.6 s: the credit chip sits half on the plate's top edge.
5. Text on stills: 21 to 25 px everywhere except the survey title's date and tags (about 15 px, they are not the voiced words and only the title is boxed) and the CySEC line (24 px, but it is a full-width line at 1.0x).
6. `plates.json` still lists `header-plain` (unused after the SUMMARY-7 change); its png is in `media/real` but no beat names it.
7. HOOK-1 holds 2.2 s (1.0 to 3.2 s) because the script's second line starts at 3.31 s; EP59 had three opening FF beats, EP60 two.
8. The scripts' PATTERN-3 voice says `คนเดียว วันเดียว สองโพสต์`; no still shows "two posts". It is on KIN S06 (a typewriter clip) with the three words, no evidence image (the source stills do not contain it). Flagged, not invented.
9. The Drive manifest's `has_character` flags and prompts do not match the clips (S05 and S07 show the character). Not used here.

## Judgment calls

- Captions copy the voice (SCRIPT.tsv), including `กู` (HOOK-4 «จริงไหม กูไปเช็กมาให้», MAIN-1 «กูเปิดหน้า GB เองทีละช่อง», SUMMARY-7 «กูไม่ได้แนะนำเจ้าไหน แค่ชี้วิธีดูให้เป็น»). IRON §37/memory say never มึง/กู on screen; the BL voice says it and the CMO's brief says captions copy the script verbatim. I told the CMO by dev_message, no reply. **SKILL-OVERRIDE: kept `กู` in three captions, because the brief says verbatim copy of SCRIPT.tsv and the voice track says the same word; changing a caption alone would put different words on screen than the voice, and the CMO can swap the three lines and re-render windows seg02, seg05/06 and seg11 only.**
- Plain plates need a box when they carry a credit: `bl_checker` refuses a credit with no evidence top to clear (`credit_missing SUMMARY-7/8`). SUMMARY-8 reuses SUMMARY-9's box on the same plate.
- Two plates were rebuilt after a look: survey body (15 px in the source: two rows at 1.5x), related card (heading clipped). SUMMARY-7 changed from the GB tile to the article-title plate.
- The merge is run against `audio-hq-decoded.wav` (a PCM copy of `audio-hq.mp3`): the mp3's container duration is 90.279 s (25 ms start offset plus padding) while it decodes to 90.229 s. `bl_merge` expects floor(90.279 x 30) = 2708 frames ±1 and a 2706-frame cut (all the audio there is) failed by one; a 2707-frame video was cut to 2704 by the muxer's `-shortest`. Audio content is identical.

## Skill learning

- MISSING [CMO_Procedure_BlackLiquidity_Cut §9 merge gate] : `bl_merge` reads the audio's container duration; an mp3 with a start offset (here 0.025 s, 90.279 s vs 90.229 decoded) expects 2708 frames and refuses the 2706 the audio actually fills. Merge against a PCM copy (`ffmpeg -i audio-hq.mp3 -c:a pcm_s16le`) and mux the loudnormed audio afterwards · evidence: task-3ae66e7a, `prototypes/bl-ep60/finish.sh`, merge gate `actual 2706 expected 2708` before / `2706 2706` after
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 fixture] : `fixture-full` copies `media/matte`, `media/real` and `media/broll` into `generator/media` once; a matte still being written was copied as a 0-byte file and every window died with `EBML header parsing failed`, and plates rebuilt later in `media/real` never reached the generator. Re-sync (`rsync -a media/{matte,real,broll}/ generator/media/…`) after the last matte and after every plate change · evidence: `build-seg06.log` first render, task-3ae66e7a
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 b-roll normalisation] : 4 of the 40 Drive scene clips (S32, S34, S38, S39) are 1076 px wide; a crop-to-1080 normalisation writes a 0-byte mp4 (`Invalid argument`). `scale=1080:1920` works. ffprobe every `media/broll/S##.mp4` before the first window, as the brief said · evidence: `timing/norm.log`, task-3ae66e7a
- MISSING [CMO_Procedure_BlackLiquidity_Cut §timings] : faster-whisper medium dropped 23.2 to 30.0 s of the voice, `align_timings.py` then fails with "line CONTEXT-4 got no ASR words". Transcribe the gap from a cut wav (`ss 22.8, 8 s`), merge the words at the offset, re-run · evidence: `timing/asr-gap.json`, task-3ae66e7a
- MISSING [CMO_Procedure_BlackLiquidity_Cut §6e credit] : a COMP or EVID beat that carries a credit must also carry a box, or `check_credit_missing` reports it (no evidence top to clear). Plain "no spotlight" plates (EP59 had them with no credit) cannot be used on a WikiFX still · evidence: checker run 1 of arm B, `credit_missing ["SUMMARY-7","SUMMARY-8"]`
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 mattes] : RVM mattes cost 31 / 20 / 18 min for lip_a / b / c on this box (4 cores, software GL, one job at a time); they gate the take table, the plates and every COMP window. Start them first, in the background · evidence: `timing/matte.log`
- COSTLY [no owner] : `pkill -f <script>` from inside the shell that launched the script also kills the worker's own shell (exit 144); use `pgrep` and explicit pids · evidence: task-3ae66e7a, norm_broll restart

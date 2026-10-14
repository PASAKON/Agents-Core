# task-2db3174c: BL EP59 «ใครตรวจ WikiFX เว็บให้คะแนนโบรก?», arm B and arm A

Video editor (Sonnet 5.5), 2026-10-04. Branch `agent/video_editor-task-2db3174c`. Nothing pushed, no Drive upload, no post.

## Finals (outside git)

| arm | file | duration | frames | LUFS |
|---|---|---|---|---|
| B (editorial calls) | `/opt/MoonieXHQ/Work/bl-ep59/cut/v1/final-ep59-v1.mp4` | 94.10 s | 2822 | -15.4 |
| A (headline plate) | `/opt/MoonieXHQ/Work/bl-ep59/armA/v1/final-ep59-armA-v1.mp4` | 94.10 s | 2822 | -15.4 |

Sheets beside them: `sheet-ep59-v1.jpg`, `sheet-ep59-armA-v1.jpg` (the same 16 times in both: 0, 0.5, 1, 2, 3, 8.5, 13.5, 16.3, 21, 38, 42.3, 51, 51.867, 66.3, 75.8, 86 s).

## Mode counts

| mode | arm B | arm A |
|---|---|---|
| COMP | 14 | 17 |
| EVID | 11 | 11 |
| KIN | 13 | 13 |
| FF | 3 | 0 (refused in arm A) |
| beats | 41 | 41 |

COMP by take: lip_a 5 (HOOK-3, HOOK-4, PATTERN-1/2/3), lip_b 6 (MAIN-5/6/7/8/9/11), lip_c 3 (SUMMARY-7/8/9). Avatar is absent 53.9 to 76.23 (the lipsync hole): MAIN-12 to SUMMARY-6 are EVID or KIN. 13 render windows (4.7 to 8.7 s), every seam on a beat t0.

## How arm A differs from B, and why

`beats.json` of A and B differ in exactly three beats, checked mechanically: HOOK-0, HOOK-1, HOOK-2. In B they are FF (plain studio close-up, no text at frame 0, first caption from 1.0 s). In A they are image-less COMP beats that ride the headline's backdrop slots (`real/fb-post-head.png` at 0 s, `real/wfx-about-score.png` at 1 s, `real/wfx-stmt-score.png` at 2 s), because FF is refused when the plate is up. FF cannot be kept in A since the plate must stay the whole clip. Everything after 3.47 s is the same beat list byte for byte. The variable between the arms is therefore the first 3 s plus the persistent headline plate (headline `ใครตรวจ WikiFX / เว็บให้คะแนนโบรก?`, `ใครตรวจ` in red, bug left, date stamp `ข้อมูลจาก Facebook + WikiFX ณ 1 ต.ค. 2569`, dark scrim over y 0 to 560). The arm A wrapper (`prototypes/bl-ep59/armA/render_window.py`) also lifts the credit chip out of the scrim (see Cosmetic issues).

None of the three backdrops was swapped: the Facebook capture is mosaic-censored (name and avatar) with the AI label legible, and the two WikiFX pages show no names. The two WikiFX backdrops are small body text under the scrim, readable only as page texture; the headline carries the claim.

## Compliance

- FB author/page name: every Facebook plate is built only from the already mosaic-censored strip (source px x 150 to 775, y 893 to 946) plus body rows, never the avatar or name rows. The AI label `เนื้อหาที่สร้างโดย AI` is in the strip of every FB plate (HOOK-3, HOOK-4, PATTERN-1/2/3, CONTEXT-1..4) and in arm A's frame 0 to 2 backdrop. PATTERN-3 plate has no spotlight box and reads `$10,000 ขึ้นไปและหากตกลงหลายเดือน ...` with the caption `ในโพสต์ไม่เห็นหลักฐานแนบ ยืนยันไม่ได้`.
- Credit `ขอบคุณภาพจาก WikiFX` on every WikiFX still (MAIN-2, 4, 5 to 12, CURIOSITY-1, 4). The regulator register (CURIOSITY-5, SUMMARY-7/8/9) has none (it is not a WikiFX image).
- Captions copy SCRIPT.tsv verbatim. No `โกง`, no recommendation, no em dash, no claim added on the plate.
- Brand mark on every frame, including t = 0 and every seam: min ratio 0.9856 (B, at 61.87 s) and 0.9912 (A, at 73.0 s) against the 0.95 floor, 0 failing frames of 2822.

## Take table (EP59, measured from the mattes, 30 fps, every frame of the range the cut can show)

| take | seat | head_top (canvas) | caption `cap_cy` | range | top at |
|---|---|---|---|---|---|
| lip_a | 0.00 | 903.04 | 797 | 0.0 to 14.733 | 0.0 |
| lip_b | 38.53 | 968.56 | 862 | 0.5 to 15.4 | 0.5 |
| lip_c | 76.23 | 985.36 | 879 | 8.0 to 17.567 | 15.77 |

`take_table.json` is episode-agnostic (EP60 reuses the tool: `bl_face_box.py --ranges --seats --episode --take-table-out`, `bl_checker.py --take-table`). lip_c differs from EP58's 999.92. lip_b's top is at its range start (0.5 s), the same assumption as EP58: the take's opening pose is never on screen with a caption.

## Gates (both arms)

| gate | arm B | arm A |
|---|---|---|
| `bl_merge --beats` (frame count, empty frames, seams ±3 frames, one caption style, audio offset) | MERGE OK, 2822 frames vs 2823 expected (tolerance 1), offset 0.0 s | MERGE OK, same |
| `bl_checker --take-table --composition` | pass: true; empty_frames []; out_of_safe_area []; text_over_face []; comp_evidence_landing []; credit_missing []; extra_caption_styles []; kinetic_overflow []; 8 KIN-entry frames excused (70.23 to 70.33, 81.70 to 81.80) | pass: true; same lists empty; headline []; 0 excused |
| brand mark per frame | ok, min ratio 0.9856, 0 failing | ok, min ratio 0.9912, 0 failing |
| `bl_tools.py verify` with seats A=0.00 B=38.53 C=76.23 against the ORIGINAL lipsync in drive/AI Drafts | PASSED: sync +0 ms at 4.7/42.3/84.7 s (r .989/.987/.994); A, B, C +0 ms (r .992/.989/.990) | PASSED: identical numbers |
| LUFS | -15.4 (two-pass linear loudnorm, I=-15.0 TP=-1.0, then AAC; peak -0.9 dBFS) | -15.4 |

Window renders: 13 per arm. One "Sequential screenshot capture stalled" (arm A window 1), retried once, succeeded.

## Per-frame verdicts

"pass 1" = viewed on the first merge; every window containing that frame was left untouched afterwards unless marked. "final" = viewed on the delivered file.

### Arm B

| t | beat | verdict |
|---|---|---|
| 0.0 | HOOK-0 FF | pass 1. No text, hat covers nothing, mark + date + legal pill on. |
| 0.5 | HOOK-0 FF | pass 1. Same, no text. |
| 1.0 | HOOK-1 FF | pass 1. Caption not yet visible (0.16 s fade, up by ~1.1 s). Fine. |
| 2.0 | HOOK-2 FF | pass 1. Pill `ที่ตั้งคำถามกับ WikiFX` clean on the chest. |
| 3.0 | HOOK-2 FF | pass 1. Pill clean. |
| 8.5 | PATTERN-1 COMP lip_a | pass 1. Censored FB strip + AI label, line 1 spotlighted, pill clear of the head. |
| 13.5 | PATTERN-3 COMP lip_a | pass 1. Same strip + label, no box, `$10,000` lines legible, caption correct. |
| 16.3 | PATTERN-4 KIN | pass 1. Kinetic `เขาถามสี่ข้อ / ผมสรุปให้` over S08, no overflow. |
| 21.0 | CONTEXT-2 EVID | pass 1. FB question list, q2 boxed, strip + label legible. |
| 38.0 | MAIN-4 EVID | pass 1, window re-rendered later with the same footer card. Mail line on white card, ~45 px, grey on navy (source contrast), credit chip visible. |
| 42.3 | MAIN-6 COMP lip_b | final. Plate ends above the pill, title boxed, credit visible. |
| 51.0 | MAIN-10 EVID | pass 1, window re-rendered later (same plate). Five-index list boxed, English body ~15 px (see issues). |
| 51.867 | MAIN-11 COMP, seam 7|8 | final. Seam clean, pill fading in, plate ends above the pill. |
| 66.3 | CURIOSITY-4 EVID | pass 1. Note card boxed, text ~19 px grey (see issues). |
| 75.8 | SUMMARY-3 KIN | final. `หนึ่ง / ใครจ่ายเงิน` over the cash counter, readable. |
| 86.0 | SUMMARY-7 COMP lip_c | final. Register title boxed, no credit (not WikiFX), pill clear of the head. |

### Arm A

| t | beat | verdict |
|---|---|---|
| 0.0 | HOOK-0 COMP | final. Headline, stamp and mark all on; FB backdrop mosaic-censored, AI label visible. Hat covers the first words of the post title behind (cosmetic). |
| 0.5 | HOOK-0 COMP | final. Same. |
| 1.0 | HOOK-1 COMP | final. Backdrop 2 (WikiFX cards), no caption yet. |
| 2.0 | HOOK-2 COMP | final. Backdrop 3 (WikiFX statement), pill over page text. |
| 3.0 | HOOK-2 COMP | pass 1. Same backdrop dimmed by the scrim, pill readable. |
| 8.5 | PATTERN-1 COMP lip_a | pass 1. FB strip right under the stamp (starts at y 566), line 1 boxed. |
| 13.5 | PATTERN-3 COMP lip_a | pass 1. Strip + label present, no box. |
| 16.3 | PATTERN-4 KIN | pass 1. Kinetic over S08 below the plate, clean. |
| 21.0 | CONTEXT-2 EVID | final (re-seen). Question list under the plate, q2 boxed. |
| 38.0 | MAIN-4 EVID | final. Credit chip now readable under the stamp. Footer card clear of the plate. |
| 42.3 | MAIN-6 COMP lip_b | final. Credit chip readable; nav strip of the page sits under it. |
| 51.0 | MAIN-10 EVID | final. List boxed; credit chip covers part of the first page line (cosmetic). |
| 51.867 | MAIN-11 COMP, seam 7|8 | final. Clean seam, chip not up yet (not up yet at the seam). |
| 66.3 | CURIOSITY-4 EVID | final. Note card boxed, credit readable. |
| 75.8 | SUMMARY-3 KIN | final. Readable over the dimmed cash-counter clip under the plate. |
| 86.0 | SUMMARY-7 COMP lip_c | final. Register title boxed, stamp and headline intact. |

### Not looked at by eye (stated, not implied)

- EVID MAIN-2, MAIN-12, CURIOSITY-1, CURIOSITY-5 and CONTEXT-1/3/4; COMP HOOK-3/4, PATTERN-2, MAIN-5/7/8/9; the other 11 KIN beats; ten of the twelve seams. These went through the machine gates above (safe area, evidence landing, credit, kinetic overflow, empty frames, seam check ±3 frames). The FB plates of HOOK-3/4, PATTERN-2 and CONTEXT-1/3/4 reuse the same censored strip as the frames above, and their plate PNGs were reviewed during plate QC.
- Looking budget: arm B used 4 sheets plus one repeat of the 4th after the caption-pill fix (5 views). Arm A used 4 sheets plus a repeat of the 3rd after the credit-chip fix (5 views).

## Known cosmetic issues

1. CURIOSITY-4 note text is about 19 px grey on navy. Source-limited: the paragraph is 606 px wide in the capture, 1.5x already fills the safe width.
2. MAIN-4 mail line is large (~45 px) but grey on navy; source contrast.
3. MAIN-10 five-index list: English body about 15 px (946 px wide at 1.0x). The box is the evidence; the sentence is not meant to be read in full.
4. The brand mark's `BLACK` is white on the white page plates (all WikiFX and FB plates), so faint; the checker's ratio is against its own steady level and passes. Template property, same as EP58.
5. Arm A: the credit chip sits under the date stamp (y 528) and overlaps up to 13 px of the evidence zone: the first line of the stmt-list page (MAIN-10) and the nav strip of the terms page (MAIN-6).
6. Arm A frames 0 to 0.5: the avatar's head covers the first words of the backdrop post title. The headline and stamp are clear.
7. HOOK-1 caption lives 0.7 s (1.0 to 1.7 s) with a 0.16 s fade; the first caption is short by design (no text at frame 0).
8. Seams: 12 seams per arm were checked by the merge gate (frame-exact, no empty frames), one by eye (51.867).

## Beats (arm B; arm A identical except HOOK-0..2)

```
0.00-1.00  FF   HOOK-0      (silent, no caption)
1.00-1.70  FF   HOOK-1      caption
1.70-3.47  FF   HOOK-2      caption
3.47-5.50  COMP HOOK-3      fb-h3  box on the AI label
5.50-7.07  COMP HOOK-4      fb-h4  box on the post title
7.07-9.90  COMP PATTERN-1   fb-p1  box line 1
9.90-12.37 COMP PATTERN-2   fb-p2  box line 3
12.37-15.13 COMP PATTERN-3  fb-p2  no box, avatar_until 14.7
15.13-17.43 KIN PATTERN-4   เขาถามสี่ข้อ / ผมสรุปให้
17.43-27.90 EVID CONTEXT-1..4 fb-q  one box per question
27.90-30.03 KIN CONTEXT-5, 30.03-32.20 KIN MAIN-1
32.20-34.40 EVID MAIN-2 about-score; 34.40-36.60 KIN MAIN-3
36.60-39.07 EVID MAIN-4 about-foot-mail (card)
39.07-41.33 COMP MAIN-5 contact; 41.33-43.20 MAIN-6 terms; 43.20-45.77 MAIN-7 stmt-title;
45.77-48.33 MAIN-8 stmt-l1; 48.33-50.00 MAIN-9 stmt-l2
50.00-51.87 EVID MAIN-10 stmt-list
51.87-54.30 COMP MAIN-11 partner-a (avatar_until 53.9)
54.30-56.57 EVID MAIN-12 partner-b; 56.57-58.83 KIN MAIN-13
58.83-61.10 EVID CURIOSITY-1 about-intro; 61.10-65.03 KIN CURIOSITY-2/3
65.03-67.50 EVID CURIOSITY-4 about-foot-note (card); 67.50-70.23 EVID CURIOSITY-5 mas-title
70.23-84.23 KIN SUMMARY-1..6 (S01..: 1-2 lines, then the four numbered questions)
84.23-87.33 COMP SUMMARY-7 mas-title-c; 87.33-94.07 COMP SUMMARY-8/9 mas-plain
```

38 broll clips are staged (S05, S15, S33 had to be re-normalised, see Skill learning).

## Assets

Derived plates `real/d-*.png` (21, built by `prototypes/bl-ep59/make_plates.py` from the originals in `media/real`; crops and zooms only, no retouching; manifest `DERIVED_MANIFEST.json`), `media/broll/S01..S40` from the lipsync Drive "AI Drafts" scenes, mattes `media/matte/lip_{a,b,c}-matte.webm`. Real WikiFX and regulator stills credited as above. Nothing was invented.

## Skill learning

- MISSING [CMO_Procedure_BlackLiquidity_Cut §5b B-roll] : `ffprobe` every `media/broll/S##.mp4` before the first window. My normalisation left S05, S15 and S33 at 0 bytes; the render died at window 10 (SUMMARY-4, S33) with `moov atom not found` after 9 windows and 1 h of work · evidence: task-2db3174c `cut/v1/build-seg10.log` · status: pending
- MISSING [CMO_Procedure_BlackLiquidity_Cut §6e / arm A credit] : in arm A the `credit()` chip (assemble.py, top:40px, z 36) lands inside the dark scrim and is unreadable; it needs `top:528px; z-index:40` under the date stamp. Done in `prototypes/bl-ep59/armA/render_window.py`; EP58's wrapper has the same ghost chip · evidence: A3/A4 frames 38.0 before and after
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 evidence stills] : a dark-page crop (footer) on a plate of its own colour is a flat dark frame with a few grey words. `bl_checker` calls std<12 "empty" and `bl_merge` refuses (36.6 to 37.1, 65.2 to 65.4 s). Lay the crop as a card on a white plate · evidence: `make_plates.py card()`, merge refusal before / MERGE OK after
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 COMP evidence] : crop the page so it ends where the caption pill begins (`zone bottom + 6`), otherwise page text runs on under the pill · evidence: `make_plates.py` page(), B4 frames 42.3 and 51.867 before and after
- MISSING [CMO_Procedure_BlackLiquidity_Cut §caption timing] : there is no caption delay option, so the first beat's caption shows at frame 0. A silent FF beat `HOOK-0` with no `cap` (0 to 1.0 s) works in `bl_compose`/`bl_merge` tag validation; the first caption's 0.16 s fade means t=1.0 itself shows none · evidence: B1 frames
- MISSING [CMO_Procedure_BlackLiquidity_Cut §9 loudness] : `loudnorm I=-14` as written does not land -15.4; two-pass linear `I=-15.0:TP=-1.0` then AAC lands exactly -15.4 · evidence: final-ep59-v1.mp4
- COSTLY [no owner] : transcript alignment mis-assigned stray ASR consonants to the wrong line and each needed a hand fix; and the three mattes had to exist before the head-top measurement, which gates the plate zones · prevented by: start the matte the moment the lipsync parts are seated and fit plates to a provisional table first (done here)
- COSTLY [no owner] : five of the 13 windows were rendered twice (plate fixes found only after the full cut was merged). Fix the plates against the take table and look at one COMP and one EVID window before rendering the rest · evidence: render logs
- SKILL-OVERRIDE: (none)

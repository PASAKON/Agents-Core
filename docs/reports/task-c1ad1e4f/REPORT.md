# task-c1ad1e4f: EP01 thumbnail study + 3 A/B options (Jade Tally)

Work folder: /opt/MoonieXHQ/Work/cn-series/publish/thumb_study/ (16 MB, 65 files). Money $0. Nothing uploaded, YouTube not touched.

## Files
- study/ : 48 thumbnails (8 channels x top 6, maxresdefault all 48) + index.json (id, views, channel, sheet number)
- study_sheet.jpg : numbered sheet, views + channel + subs on each tile (1.4 MB)
- PATTERNS.md : 20 lines, each pattern marked verified (n/N) or assumed
- opt_A.jpg / opt_B.jpg / opt_C.jpg : 1280x720, 158 / 170 / 221 KB
- phone_sheet.jpg : A B C at 320 px next to 2 real competitor thumbs (#19 Nunow 2.1M, #13 เจ้าพรรคยาจก 121k), labelled
- options.md : axis, source frame (file + time) and text per option
- src/ : kit.html (one template, ?opt=A|B|C), render.py (Playwright, one Chromium), frames/{A,B,C}.jpg + sources.txt, fonts/Kanit-ExtraBold.ttf (OFL)

## What the study found (5 lines)
1. The two narrator channels (Nunow 601k, laowon 106k) put a plain-Thai hook sentence on the thumbnail (13/48 tiles overall, 8 of the 10 most-viewed); the six series channels use only show-title art plus an EP range.
2. Faces: one hero figure is the subject in 39/48, but cold stares dominate; open-mouth shock appears in 3/48 and in no top-10 tile.
3. Text is big (14-24 Thai characters on the main line), warm yellow/gold/orange or white, always with a dark outline; 5/13 hook tiles put a number in it, which is what our "3 ตำลึง" does.
4. Size is mixed in: 6 of the top 10 are one channel, and by views per subscriber the leaders are EP1-start batch videos (5/6 series channels), so the range number matters more than the art.
5. No tile pairs a real-world prop with a price contradiction; that is open ground for us. The v3 thumbnail (thumb_a.jpg) put text on the hero's forehead, which no tile in the set does.

## Beats / design (one line each)
- A big face + shock: S62b/colab_10 @2.5 s, face about 70 % of frame height, text on the chest, no text on the face.
- B jade abacus close-up: S06a/colab_11 @3.2 s, line 1 above and line 2 below the glowing abacus (the cracked corner is visible).
- C wide scene + conflict: S28a/colab_28 @2.5 s, two clubbed thugs flank the hero on the floor of the auction hall; text across the middle so heads and the hero stay clear.
- Same hook text in all three (changes one thing only): "ดาบหมื่นศิลา" / "แต่ลูกคิดบอก 3 ตำลึง", plus a small "EP1" badge (not hook text; drop it if it counts against the 2-line limit).

## Judgment calls
- Text colour not changed from set D (white / #FFD60A, black outline). Reason in options.md: the study shows warm yellow/gold/white on the hook tiles.
- Used "3" in digits instead of "สาม": the study shows numbers in 5/13 hook tiles; still natural Thai.
- Excluded ep2_* render folders (EP02) and quarantine folders when choosing frames: 209 EP01 clips looked at, one mid frame each, then 12 candidates at 3 times each.
- **ChatGPT cover (user message mid-task, "รูปปกสามารถใช้ ChatGPT ทำได้ ... เหมือนละครสั้นเลย")**: NOT done. The task and BRIEF say frames from our own renders only, no AI image generation, $0, and the ChatGPT route needs a winbox lease and image quota (CMO_Procedure_ChatGPTImage_LakornCover). Proposal for the CMO: if the CEO wants it, a 4th option D (ChatGPT people + title logo on black, lettered locally) as a separate, approved job; the A/B slots allow 3 thumbnails, so D would replace one of A/B/C.

## Not checked / risk
- Pattern counts are by eye (one reader, 48 tiles); face-size classes are about +/-3. Views are rounded to 2 digits (flat-playlist listing, 23 Oct) and upload age was not in the listing, so older videos lead and "top 20 %" mixes in channel size; every causal claim is marked assumed.
- Option A's hero shows rosy cheeks under the eyes in the render itself (this character's style in the source clip); I did not recolour the pixels. If the H3 no-red-face rule is meant for EP01 too, swap A for another frame (e.g. the face close-ups in a3_morning/C06a/colab_08 or a2_home/B35a/colab_14) before the card goes out.
- Whether YouTube Test & Compare is available on @JadeTally was not checked (outside this task); `thumb_study/tc_check.png` was already in the folder and I did not open it.
- Competitor thumbnails are in study/ for viewing only; the phone sheet reuses 2 of them (labelled). Do not publish phone_sheet.jpg or study_sheet.jpg outside the team, they contain other channels' pixels. Our 3 options contain none.
- Not looked at at full size by the CEO's eye: text safe margins checked at 1280x720 and 320 px only; the YouTube duration stamp (bottom-right) can cover the end of line 2 in A and B, I did not measure it.

## Skill learning
- MISSING [VIDEO_EDITOR_Protocol_Playbook §thumbnails] : no recipe for a still thumbnail from render clips (frame grab, kit.html with an SVG stroke text, Playwright render, phone sheet); I rebuilt it from jade-tally-brand REBUILD.md · evidence: task-c1ad1e4f src/kit.html + render.py
- COSTLY [no owner] : `ffmpeg` inside a `while read` loop swallowed the clip list from stdin (first loop produced 0 frames, error spam) and a 209-clip loop exceeded the 120 s tool timeout · evidence: task-c1ad1e4f · prevented by: `ffmpeg -nostdin` in loops and run_in_background for >100 clips

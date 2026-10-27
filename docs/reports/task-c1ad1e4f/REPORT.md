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

---

# Round 2 (CTO iteration 1): ChatGPT re-paint of our real frames + one title logo

CEO rejected A/B/C on Q-20261027-1913-f107 ("ไม่เอา"); note: use ChatGPT with our real frames, text like the short drama, not too much, colour must not melt into the background. Money $0 (CEO Plus web UI, no API). Nothing uploaded, YouTube not touched.

## Files (all in /opt/MoonieXHQ/Work/cn-series/publish/thumb_study/)
- opt2_A.jpg / opt2_B.jpg / opt2_C.jpg : 1280x720, 258 / 290 / 291 KB (each under 2 MB)
- phone_sheet2.jpg : A B C at 320 px + the same 2 competitor tiles as round 1 (170 KB). Contains other channels' pixels, do not publish.
- round2/pic_A_face.png, pic_B_abacus.png, pic_C_scene.png : the three text-free ChatGPT pictures (1672x940)
- round2/logo_jade.png (first logo), round2/logo_jade2.png (final logo, same chat, last letter fixed), round2/logo_final.png (= jade2)
- round2/round2.json (the 4 prompts), round2/ledger.json (holds chat links: keep out of any public repo), run.sh / run_fix.sh (lease + tunnel + runner, chained)
- src/compose2.py (composite: lifts the logo off black, dark halo + soft plate, same logo width 640 px in all three), src/phone_sheet2.py
- Folder 27 MB.

## Prompts (one line each; the common tail is in every picture prompt)
Common tail: "3D CG Chinese fantasy animation style (donghua look), clearly animated, never photoreal. Landscape 16:9. ONE image only, no text, no letters, no writing of any kind, no watermark, no border, no panels, no red cheeks, no rosy cheeks, even natural skin tone, nothing 18+."
- A face: attached round-1 frame A (S62b/colab_10 @2.5 s). "Re-paint the attached frame as a punchier thumbnail picture: keep the same young man (same face, same hair tied up, same dark blue patched robe) and the same floating porcelain bowl and shelves, but make the shock on his face clearer and his face large on the left half of the frame, richer warm lantern light with a soft teal rim light, leave the bottom third calm and darker, sharp clean" + tail.
- B abacus: attached round-1 frame B (S06a/colab_11 @3.2 s). Keep the exact same jade abacus (frame shape, bronze corners, rods, beads, broken top-right corner) glowing green on a dark belt, large in the middle, warm red lantern bokeh, calm top fifth and bottom third + tail.
- C scene: attached round-1 frame C (S28a/colab_28 @2.5 s). Keep the auction hall with red lanterns, the two huge men in black with clubs, the small young man on the red carpet; stronger menace and depth; keep the band between the two men calm for lettering + tail.
- Logo (no attachment): the skill template, line 1 smaller "ดาบหมื่นศิลา", line 2 much larger "ลูกคิดบอก 3 ตำลึง", tone mark and ำ shapes named, pure black #000000, 3:2, concept "Jade Tally": ivory letters, polished gold bevel, one gold light line along a crack through line 2, faint jade glow inside the letters.
- Logo fix, same chat (--continue logo_jade): "Keep everything exactly the same ... Only fix the very last letter of line 2: it must be the Thai letter ง (NGO NGU): a small closed round loop at the top-left, then a stem going down on the right that ends in a short tail curling back to the left ... clearly not a Y or V shape."
I did not use the round-1 face frame swap (C06a/colab_08): the A re-paint came out with an even skin tone on its own and no rosy cheeks.

## Spelling check (letters in 2x crops of the 1536x1024 logo, skill rule 6)
- Line 1 ดาบหมื่นศิลา: ด า บ ห ม ื ่ น ศ ิ ล า, all correct. Tone mark over ื is a single short slanted stroke (mai ek), not mai tho. ิ over ศ present.
- Line 2 ลูกคิดบอก 3 ตำลึง: ลู (ู under ล), ก, คิ, ด, บ, อ, ก, the digit 3, ต + ำ (closed round ring, top left of า), ล + ึ (plate with a ring), all correct.
- First logo: the final ง looked like a Y/V at full size. Fixed in the same chat (run 20:34, first try timed out at 600 s, `--recover` returned the image); the other 11 letters unchanged between jade and jade2. Final ง now has a closed loop head, stem and curled tail.
- Not Thai-fluent-reader checked by a second person; I read it letter by letter myself.

## Composite and legibility
- One logo for all three, 640 px wide (about half of the width), so the A/B test changes only the picture. Logo lifted off the black (no black box), dark halo around the letters plus a soft dark plate. Ivory/gold on dark: it does not melt into any of the three backgrounds, including the red carpet in C and the green glow in B.
- Text amount: 2 short lines, no EP badge, no extra words (CEO: not too much).
- No text over a face: A text sits right of the chin, under the bowl; B under the abacus; C between the two thugs' bodies, above the hero. Looked at each at 1280 and in phone_sheet2.jpg at 320 px: both lines readable in all three.
- C: the generator left a faint ghost signature on the carpet (bottom right); patched with neighbouring carpet in compose2.py (patch_ghost). A and B checked at the same corner, clean.

## Beats / differences from round 1
- A: face large, left half, shock; B: glowing jade abacus centred with line 1 touching the belt just under it; C: wide hall, the same story with two thugs.
- Differences from round 1: text is the carved jade logo instead of Kanit with outline; no EP1 badge; pictures are re-painted (punchier light), not raw frame grabs.

## Not checked / risk
- The re-painted pictures are gpt-image output, not our frames: the characters are close to ours but not identical. Hero A face, the abacus (frame, corner fittings, beads) and the thugs' clothes were compared by eye only against the round-1 frame; continuity with the film shots was not measured. If the CEO wants exact props, frames from the render are the safe base.
- Not tested at the YouTube duration stamp (bottom right): in A and B the end of line 2 sits near it; not measured.
- Skin in A is pale and warm but may still read slightly rosy at the cheeks in the full-size view; I did not recolour. Check the full-size file before the card goes out.
- ChatGPT outputs can carry invisible provenance data (C2PA) and might not be fine for a channel policy; not checked.
- Logo has a jade glow plus gold: very busy at 320 px next to flat competitor text; whether it beats plain white/yellow in click rate is untested (no CTR data).
- The winbox lease was taken three times (generation, failed fix, recover) and given back each time; I did not check the Cookie Run bot state afterwards ("bot already idle" each time).

## Skill learning
- MISSING [CMO_Procedure_ChatGPTImage_LakornCover §Where the runner runs] : a same-chat fix (`--continue`) that times out at 600 s can still have produced the image; `--recover <name>` under a lease returned it first try. Say "after a timeout on a continue item, run --recover before any retry" · evidence: task-c1ad1e4f, round2/ledger.json logo_jade2 failed then recovered
- MISSING [CMO_Procedure_ChatGPTImage_LakornCover §Workflow 3] : the ง in "ตำลึง" came out as a Y shape in angular lettering (not a wrong mark, a wrong letter); name its shape (closed loop head, stem, curled tail) in the first prompt or fix in the same chat; ChatGPT pictures can also carry a ghost signature in a corner (here C), check all four corners at full size · evidence: task-c1ad1e4f round2/logo_jade.png, pic_C_scene.png
- MISSING [VIDEO_EDITOR_Protocol_Playbook §thumbnails] : no recipe for screening a pure-black ChatGPT logo onto a picture for a 16:9 thumbnail (lift off black, halo + plate); src/compose2.py does it (same method as the 2026-10-27 field note) · evidence: task-c1ad1e4f src/compose2.py
- COSTLY [no owner] : the pc lease was held by another PH for about 2 hours before the first run; a background wait loop (chained, never forced) cost nothing but wall time · prevented by: take the lease early or ask the lease holder for the end time first

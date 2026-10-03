# REPORT task-3cf9c2f8 — BL EP58 arm A (headline plate), finished and verified

## Summary
All 12 windows of arm A were rendered one at a time on the current kit (origin 9993bd6e), merged, loudnormed and checked. Merge, `bl_tools.py verify` (3 lip seats) and the brand-mark gate pass on every frame. **The `text_over_face` gate FAILS on 17 beats** when run with the face boxes, and my eyes agree: the caption pill covers the avatar's mouth on every COMP beat. Arm B has the same geometry; arm B never ran the gate. NOT posted. Needs a CMO decision (see Issues).

Final: `/opt/MoonieXHQ/Work/bl-ep58/armA/final-ep58-armA.mp4` (19.3 MB, 95.70 s, 2871 frames, 30 fps, 1080x1920, -15.4 LUFS). Sheet: `/opt/MoonieXHQ/Work/bl-ep58/armA/sheet-ep58-armA.jpg`. Frames looked at: `.../armA/frames/f_*.jpg`.

## Files Changed (branch agent/video_editor-task-3cf9c2f8)
- prototypes/bl-ep58/armA/beats.json, make_beats.py — MAIN-13 follows arm B (still `real/wikifx-article-sep-contents.png`, box [60,660,480,76], the old EVID shift 950 removed); CONTEXT-4 spotlight box [40,555,320,45] -> [124,555,180,45] (see Judgment calls)
- prototypes/bl-ep58/armA/render_lock.sh — W= now this worktree (kept; not used for the final run)
- prototypes/bl-ep58/armA/render_seq.sh — new: one window at a time, `flock` on the box lock, `free -m` available >= 3000 gate (waits), stop under 1500
- prototypes/bl-ep58/armA/segments.json — the window list as rendered (seg02|seg03 boundary at 16.63)
- prototypes/bl-ep58/armA/render-meta.json — path/size/duration/fps/LUFS/brand-mark ratio/checker verdicts
- prototypes/bl-ep58/armA/decisions.jsonl — unchanged (159 lines, from task-4305b93b; no Jev rerun). I changed no beat's mode, so I wrote no new finals.
- docs/reports/task-3cf9c2f8/ — this report, checker JSONs (no-face + 3 face boxes), verify.txt

## Commits
- 119049a2 — video: bl-ep58 armA MAIN-13 follows arm B; render_lock W path
- db3531fa — video: bl-ep58 armA CONTEXT-4 spotlight inside the safe area, seam at 16.63, render-meta, checker output, segments.json
- (+ merge ce93f17b of agent/video_editor-task-4305b93b; origin/main was already contained, kit fix 9993bd6e present)

## Modes (arm A, 40 beats)
COMP 17 · EVID 13 · KIN 10 · FF 0.   Arm B: COMP 14 · EVID 14 · KIN 9 · FF 3.

## What differs from arm B, and why
Only what the headline plate forces; everything else is byte-identical (same tags, timings, captions).
- Plate on screen the whole clip, 2 lines, red only on "ร้องเรียน", bug at top-left, date stamp "ข้อมูลจาก WikiFX ณ 1 ต.ค. 2569", backdrop weltrade-header @0 / weltrade-warning @1 / wikifx-article-sep @2 s (HOOK-1/2 are img-less COMP riding the backdrop).
- FF refused in arm A: SUMMARY-7/8/9 FF -> COMP over `real/weltrade-licence.png` (shift 300; SUMMARY-9 spotlights the licence number line 50691).
- PATTERN-4 EVID -> KIN ("นี่คำผู้ร้องเรียน / ไม่ใช่ของกู"): the complaint text sits at y 285-340, under the plate, and no avatar window exists at 16.6 s.
- COMP page shifts so evidence clears the plate/date stamp: PATTERN-1/2/3, MAIN-6/7/8/9 (see make_beats.py CHANGES for each number).
- CONTEXT-4 and CURIOSITY-1 boxes moved off the plate zone.
- MAIN-13: arm B's new contents still, no lift.

## Beats (start-end, mode, tag)
0.28-2.06 COMP HOOK-1 · 2.47-3.85 COMP HOOK-2 · 4.44-6.4 COMP HOOK-3 · 6.73-8.48 COMP HOOK-4 · 9.07-11.37 COMP PATTERN-1 · 11.95-13.38 COMP PATTERN-2 · 13.8-16.03 COMP PATTERN-3 · 16.63-18.31 KIN PATTERN-4 · 18.91-20.48 EVID CONTEXT-1 · 20.87-22.56 EVID CONTEXT-2 · 23.13-24.46 EVID CONTEXT-3 · 25.05-26.71 EVID CONTEXT-4 · 27.25-29.37 EVID CONTEXT-5 · 29.66-31.67 KIN MAIN-1 · 32.15-33.73 KIN MAIN-2 · 34.13-36.28 EVID MAIN-3 · 36.79-38.81 EVID MAIN-4 · 39.28-41.7 COMP MAIN-5 · 42.36-44.31 COMP MAIN-6 · 44.66-46.48 COMP MAIN-7 · 47.17-48.82 COMP MAIN-8 · 48.99-51.1 COMP MAIN-9 · 51.68-53.6 COMP MAIN-10 · 54.12-55.97 COMP MAIN-11 · 56.58-58.41 EVID MAIN-12 · 59.12-61.7 EVID MAIN-13 · 62.44-64.21 EVID CURIOSITY-1 · 64.8-66.35 EVID CURIOSITY-2 · 67.04-68.81 EVID CURIOSITY-3 · 69.41-70.8 EVID CURIOSITY-4 · 71.57-73.63 KIN CURIOSITY-5 · 74.42-76.02 KIN SUMMARY-1 · 76.75-78.5 KIN SUMMARY-2 · 79.22-80.82 KIN SUMMARY-3 · 81.37-83.53 KIN SUMMARY-4 · 84.04-86.03 KIN SUMMARY-5 · 86.61-88.14 KIN SUMMARY-6 · 88.69-90.76 COMP SUMMARY-7 · 91.27-92.81 COMP SUMMARY-8 · 93.35-95.24 COMP SUMMARY-9

## Run record
- Windows: 12, each rendered alone under `flock /opt/MoonieXHQ/Work/.bl-render.lock`, `< /dev/null`, `free -m` available 3709-5164 MB at each start (never under 3000), 1-3 min each. seg01-12 were ALL re-rendered, including the two the brief called finished: they predate the brand-mark fix (rendered from the old worktree), so they would have blinked at 0.0 s and at their seams. Old parts kept in `armA/parts-old/`.
- ffprobe frame counts of the 12 parts match the windows: 272 227 252 272 247 199 228 247 203 229 222 273 = 2871.
- Merge: `bl_merge --beats` -> MERGE OK (frames 2871 vs 2872 +-1, empty_frames [], seam_failures [], audio offset 0.0 s, one caption style).
- Loudnorm single pass I=-14 TP=-1.5 LRA=11 on `pre.mp4` -> final (-15.4 LUFS).
- `bl_tools.py verify` (run with /opt/MoonieXHQ/Agents/Core/.venv/bin/python; ORIGINAL lipsync from drive/AI Drafts, offsets 0.00 / 38.77 / 80.84): VERIFY PASSED; sync +0 ms at 4.8 / 43.1 / 86.1 s; lip A/B/C seated at +0 ms (r 0.982 / 0.993 / 0.988).
- `bl_checker --video --beats armA/beats.json` WITHOUT a face box: pass=true. empty_frames [], excused (KIN entry grace) 16.633 / 16.667 / 16.7 / 16.733 (PATTERN-4), out_of_safe_area [], credit_missing [], extra_caption_styles [], kinetic_overflow [], headline []. **brand_mark ok, min ratio 0.9897 (at 0.1 s) of the steady level 191.98, 2871 frames incl. t=0 and all 11 seams, 0 failing frames.** (Arm B v2 min was 0.9833.)
- `bl_checker` WITH `--face-box` from `armA/face_box.py` (lip_a 55,903,371,436 · lip_b 56,976,432,369 · lip_c 95,1003,295,296): all other gates identical, **text_over_face FAILS on 17 beats for each of the three boxes**: HOOK-1..4, PATTERN-1..3, MAIN-5..11, SUMMARY-7..9. The gate tests the caption band (0.62-0.72 of the height, y 1190-1382) against the box; the real pill is at y ~1250-1350, the head box ends at y 1339-1352.

## Frames looked at (full res, from the encoded MP4)
0.0, 0.5, 1.0, 2.0, 3.0, 9.1, 16.7, 59.9, 74.4, 86.7, plus the seams 16.63, 25.05, 34.1, 42.34, 48.97, 56.57, 64.8, 71.6, 79.2, 86.6, plus 89.5 / 92.0 / 94.5 (SUMMARY-7/8/9).
- Plate readable on all, clear of the TikTok nav (text y 276-474; safe top 252); red only on "ร้องเรียน"; date stamp present; brand mark top-left present on every frame looked at, including 0.0 and each seam.
- Backdrop: 0.0 weltrade-header, 1.0 weltrade-warning, 2.0 and 3.0 the WikiFX article: switches as specified.
- 59.9 MAIN-13: contents row "02 Weltrade ใบอนุญาตเบลีซถูกเพิกถอน" at y ~690 with the yellow box, inside the free band; no avatar over it.
- 94.5 SUMMARY-9: licence number 50691 visible, boxed; avatar is below it, not covering it.
- 71.6: KIN entry plate (dark, plate + bug + legal pill on). 74.4 / 86.7: KIN with red plate / counting machine, no empty frame. 16.63: KIN entry (dark for 4 frames, text wipes in at 16.73), excused by the checker.
- **Defect, by eye:** at 0.5, 3.0, 9.1, 34.1, 48.97, 89.5, 92.0, 94.5 s the caption pill (y ~1250-1350) sits across the avatar's nose/mouth; eyes are at ~1190, only the chin shows under the pill. The same position and the same pill appear in arm B's final at 0.5 and 3.0 s (`cut/v2/final-ep58-v2.mp4`), so it is not caused by arm A.

## Brand / Judgment Calls
- Date stamp reads "ข้อมูลจาก WikiFX ณ 1 ต.ค. 2569" (brand's real spelling, SKILL §6e), not the brief's "วิกิเอฟเอ็กซ์" (the TTS spelling). Set by task-4305b93b's wrapper, kept. One-line change in `render_window.py` if the CMO wants the Thai spelling.
- "ถูกร้องเรียน": allowed only because WikiFX's red card is on screen at 1.0 s ("WikiFX ได้รับร้องเรียนจากผู้ใช้ทั้งหมด 43 รายการ"); no other claim on the plate.
- CONTEXT-4 spotlight: the checker flagged it out_of_safe_area (box began at x 40, margin is 54). Moving it to x 54 would cut the first letters of "WikiFX" (the byline starts at x 32), so I aimed it at "Yesterday 06:11" ([124,555,180,45]), which is what the caption "WikiFX เพิ่งลงบทความใหม่" refers to. Re-rendered seg04.
- seg02|seg03 boundary moved from 16.6 to 16.63 (PATTERN-4's own t0). At 16.6 the first frame of seg03 was bare (the KIN beat starts one frame later and `bl_merge` refused: empty frame at 16.6). At 16.6333 bl_compose treats the beat as started before the window and DROPPED it (2.3 s of empty frame, caught by the gate). 16.63 exactly works. Same frame counts.
- Nothing else touched: no caption restyle, no avatar move, no kit edit.

## Issues / Blockers
- **text_over_face fails (17 beats) — needs a CMO/CTO decision, not fixed here.** The caption pill at y 1300 (SKILL §6f, fixed) covers the matted avatar's mouth wherever the avatar is composited at the standard position (top ~845). This is the kit's geometry and is shared with arm B, so it does not decide the A/B on the plate. Options: raise the COMP avatar ~100-130 px (chin clears the pill; costs evidence room), or move the pill lower (collides with the legal pill at y 1430). I did neither because §6f forbids moving the caption and a different avatar position would put arm A and arm B on different footing.
- Brief said "the avatar sits lower under the plate"; comparing frames 0.5 and 3.0 s of both finals, it is at the same place as in arm B (eyes at y ~1190 in both).
- `face_box.py` boxes include the neck (narrowest row below the head), so they are taller than the face; the gate fails even more conservatively than the eye does, but the eye confirms the mouth is covered.
- The 4305b93b worktree's `render_lock.sh` had no flock and no RAM gate; used `render_seq.sh` instead.

## Notes for Reviewer
- mp4/jpg stay in Work, nothing binary in git. Deleted my own `armA/build/` dirs, intermediate `pre.mp4` and superseded part dirs at the end; kept `parts/`, `parts-old/` (4305b93b's), final, sheet, frames, logs.
- `armA/merge.log` has the full gate JSON; the checker JSONs are in docs/reports/task-3cf9c2f8/.
- Disk /opt after cleanup: see Notes in the submit_report if different from ~5.9 GB.

## Skill learning
- MISSING [CMO_Procedure_BlackLiquidity_Cut §9 seams] : a window boundary must sit exactly on the next beat's own t0 (16.63), not on the 1/30 grid (16.6 left a bare first frame; 16.6333 made `emit_pieces` skip the beat, `abs_t0 < t0_window - 0.001`, so a KIN beat vanished for 2.3 s). Check `cut_pieces.json` of every re-cut window contains the beat you meant · evidence: task-3cf9c2f8 seg03, /opt/MoonieXHQ/Work/bl-ep58/armA/merge.log first two runs
- MISSING [CMO_Procedure_BlackLiquidity_Cut §checker gates] : `text_over_face` with a real face box fails on every COMP beat with a caption (17 of 40 here), because the 0.62-0.72 caption band meets the head+neck box; by eye the pill covers the avatar's mouth, in arm B as well. The kit's COMP geometry (avatar top ~845, caption top 1300) needs a ruling before the gate can be a pass condition · evidence: armA/checker-lip_a.json, frames 0.5 / 3.0 vs cut/v2/final-ep58-v2.mp4
- MISSING [CMO_Procedure_BlackLiquidity_Cut §9 render] : old window parts rendered before kit fix 9993bd6e (here seg01/seg12 from task-4305b93b) must be re-rendered, not kept after an ffprobe frame count; a frame count cannot see the brand-mark blink · evidence: parts-old/ vs brief's "finished"
- MISSING [CMO_Procedure_BlackLiquidity_Cut §6c safe area] : a spotlight `box` is checked against the safe rectangle's LEFT margin 54, not the phone crop (97); an arm-A spotlight at x 40 is out_of_safe_area, and widening the box would cut letters of a byline that itself starts at x 32 · evidence: task-3cf9c2f8 CONTEXT-4 (checker-noface first run)
- COSTLY [CMO_Procedure_BlackLiquidity_Cut | no owner] : `pkill -f` from the tool shell matched my own command line and killed the call (exit 144) twice, and left the orphaned hyperframes/chrome tree running; kill by pid · prevented by: use `kill <pid>` from `ps -eo pid,args`
- COSTLY [CMO_Procedure_BlackLiquidity_Cut | no owner] : a driver that `rm -rf`s `build/<id>` after each window deletes the composed `index.html` that `bl_merge --compositions` needs for the one-caption-style gate; I killed and restarted after window 1 · prevented by: delete only `rendered.mp4`

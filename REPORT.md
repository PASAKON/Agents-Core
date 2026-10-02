# REPORT task-cc55e620

## Summary
Re-rendered all 12 BL EP58 windows on the c32c40e8 kit (origin 9993bd6e), with a new MAIN-13 still (WikiFX contents list, row 02 at y 687-713). Merged into `cut/v2/final-ep58-v2.mp4`. bl_merge, `bl_tools.py verify` and every bl_checker gate pass; brand mark is at least 98.3% of its steady level on all 2871 frames. NOT posted.

## Files Changed
- prototypes/bl-ep58/beats.json — MAIN-13 img -> `real/wikifx-article-sep-contents.png`, box [60,660,480,76] (inside safe area, y 660-736). Voice, timings, caption text untouched.
- prototypes/bl58-realfootage/REAL_MANIFEST.json — new entry for the contents still (source URL, censor rule, evidence box, note).
- prototypes/bl-ep58/render-meta.json — v2 acceptance numbers.
- docs/reports/task-cc55e620/WORKLOG.md — one line per window (iter 2).
- docs/reports/task-cc55e620/REPORT.md — this file.

## Commits
- 37d1d8ad — video: bl-ep58 MAIN-13 new still wikifx-article-sep-contents + REAL_MANIFEST entry
- (final commit with render-meta, WORKLOG, REPORT; see `git log`)

## Tests
- ran: bl_merge (12 parts), `bl_tools.py verify`, `bl_checker.py --video --beats`
- passed: merge gates 5/5; verify (res/fps/loudness/3 sync points/3 lip seats); checker 6/6 run gates
- failed: 0
- skipped: 1 (`text_over_face`, no `--face-box` given, not invented)

### Acceptance block
- **Calibration (old final, task-8f940c57 `cut/final-ep58.mp4`)**: brand_mark FAILED, 226 failing frames, min_ratio -0.013. Failing ranges (12) = 0.0-0.633, 9.067-9.667, 16.6-17.233, 25.033-25.667, 34.1-34.667, 42.333-42.933, 48.967-49.6, 56.567-57.133, 64.8-65.367, 71.567-72.133, 79.2-79.767, 86.6-87.167. That is frame 0 plus all 11 seams, as predicted. The gate does measure the blink. (`cut/v2/checker-old.json`)
- **Brand mark, new final**: ok=true, steady level 193.21, **min opacity ratio 0.9833 at 83.767 s**, failing_frames 0, failing_times [], failing_ranges [], 2871 frames checked incl. t=0 and all 11 seams (`cut/v2/checker-new.json`).
- **bl_checker verdict**: pass=true. empty_frames [] (7 excused under KIN-entry grace: 29.667/29.7/29.733 MAIN-1; 71.567/71.6/71.633/71.667 CURIOSITY-5), out_of_safe_area [], text_over_face [] (**gate did not run, no --face-box**), credit_missing [], extra_caption_styles [], kinetic_overflow [], brand_mark ok. MAIN-10/11/13 safe-area failures from v1 are gone.
- **bl_merge**: pass; frame_count 2871 (expected 2872, +-1 ok); empty_frames []; seam_failures []; audio offset 0.0 s; one caption style.
- **verify**: VERIFY PASSED; 1080x1920 @ 30/1; sync +0 ms at 4.8/43.1/86.1 s; lip A/B/C seated 0.00/38.77/80.84 s at +0 ms.
- **Frames / duration / LUFS**: 2871 frames, 95.70 s, **-15.4 LUFS** (inside verify's -16..-12 window; loudnorm applied as specified, single pass, same figure as v1).

### Paths for the CMO
- Final: `/opt/MoonieXHQ/Work/bl-ep58/cut/v2/final-ep58-v2.mp4` (old final untouched at `cut/final-ep58.mp4`)
- Contact sheet (40 beats): `/opt/MoonieXHQ/Work/bl-ep58/cut/v2/sheet-ep58-v2.jpg`
- Frames: `/opt/MoonieXHQ/Work/bl-ep58/cut/v2/frames/f_{0.0,9.1,9.3,16.7,59.9,71.6,71.8,74.4,86.7}.jpg`
- New still: `/opt/MoonieXHQ/Work/bl-ep58/generator/media/real/wikifx-article-sep-contents.png`
- Checker/merge/verify output: `cut/v2/checker-new.json`, `merge.log`, `verify.txt`

### Eye review
- 59.9 s (MAIN-13): the Belize contents row "02 Weltrade ใบอนุญาตเบลีซถูกเพิกถอน" is in the free band (y ~690) with the yellow spotlight box on it; bug on, caption below. Fixed.
- 0.0 s: bug + date on from frame 0. 71.6 s: bug on over the dark KIN entry plate (CURIOSITY-5 starts at 71.567; SUMMARY-1 at 74.42).
- Face overlap, by eye on the contact sheet only (gate not run): the caption pill sits at the avatar's chin/neck on the avatar beats at 0.7, 2.9, 39.7, 45.1 s and the rest of the EVID beats where the avatar is cut in; at 79.6 s (KIN with avatar) it sits at the chest. No caption covers eyes or mouth. I did not invent a face box.

## Issues / Blockers
- None blocking. `text_over_face` not measured (no face box).
- Iter 1 died in the 2 Oct OOM; iter 2 rendered strictly one window at a time under `flock`, each start with `free -m` available >= 6054 MB (gate 3000). Windows seg06-10 took 1-3 min each (not 5-11).
- The MAIN-13 edit to beats.json from iter 1 was not in the worktree (it was clean); I redid it from the already captured still and the manifest entry in `Work/.../generator/real`.

## Notes for Reviewer
- Only seg08 (59.12 s) depends on the beats.json change; seg01-05, seg11, seg12 were kept from iter 1 after an ffprobe frame-count check (all match their windows). seg06-10 rendered this run on the final beats.json.
- The still is 1080x1920, no crop; its top edge half-hides the "$22,067" paragraph behind the site nav (not used as evidence). Download CTA in the nav is pixelated per hygiene.
- Mp4s stay in Work, nothing binary in git. Disk /opt 5.9 GB free at the end.

## Skill learning
- MISSING [CMO_Procedure_BlackLiquidity_Cut §9] : the memory figures for windows differ wildly: on this box the 5 windows took 1-3 min each when run one at a time vs 10-25 min each when 5 ran in parallel and swapped; "one at a time" is faster per window, not just safer · evidence: WORKLOG.md vs iter-1 drv-fwd2.log (seg05 18 min under load)
- MISSING [CMO_Procedure_BlackLiquidity_Cut §9] : `bl_tools.py` lives under the skill's `scripts/`, not `tools/`, and `verify --seat` needs the ORIGINAL lipsync files from `drive/AI Drafts/` with offsets from `offsets.json`; the brief said `tools/bl_tools.py` · evidence: this run, `find . -name bl_tools.py`
- COSTLY [CMO_Procedure_BlackLiquidity_Cut | no owner] : a brief that says "uncommitted beats.json in your worktree" cost a check; the worktree had been reset so the edit was gone and had to be redone · prevented by: commit work-in-progress before a restart/handoff

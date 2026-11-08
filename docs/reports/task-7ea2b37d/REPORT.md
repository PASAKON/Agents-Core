# REPORT task-7ea2b37d: MYPASAKON v5 reference breakdown

Role: developer (Sonnet 5.5), runner claude, tier critical, host contabo. Delegated by CMO e785343f (box-bound override 2026-11-08T04:22Z). No application code changed: this task is analysis plus two documents.

## Summary
Analysed ref1 (ZSprNycKN, 119.0 s), ref2 (ZSprNmJfE, 180.3 s) and ref3 (ZSprNuyka, 183.7 s) with ffprobe, ffmpeg scene scores (clustered at 0.20 / 0.35 s plus a lagged frame diff for soft transitions), audio STFT and full-resolution frame measurements, and wrote `REFS-BREAKDOWN.md` with (a) cut-length statistics and repeated grammar, (b) shot tables of 23 + 39 + 54 rows, (c) a 30-shot, 102.72 s blueprint on the approved tight voice with Kanit-SemiBold and our own footage. **ref4.mp4 is not present** in `v5/refs/`, so nothing covers it.

## Files Changed
- docs/reports/task-7ea2b37d/REFS-BREAKDOWN.md: new, the deliverable (also at `/opt/MoonieXHQ/Work/mypasakon-voice/v5/REFS-BREAKDOWN.md`, byte-identical)
- docs/reports/task-7ea2b37d/REPORT.md: new, this report
- Outside the repo, not committed: `/opt/MoonieXHQ/Work/mypasakon-voice/v5/tmp_frames/` holds 43 JPG contact sheets (13 MB) for review; the 501 loose PNGs (76.8 MB, all created by this task) were deleted as instructed.

## Commits
- see `git log` on branch `agent/developer-task-7ea2b37d` (one commit for the two docs; sha is in the submitted report, a commit cannot contain its own sha)

## Tests
- ran: none, no code in the repo changed. Checks run on the documents instead: every markdown table has a constant column count (10 of 10 tables OK), row counts match the event data (23 / 39 / 54 shots, 30 blueprint shots, blueprint timecodes are contiguous and sum to 102.72 s), no em dash and no guillemets in the file.
- passed: 0
- failed: 0
- skipped: 0

## Issues / Blockers
- ref4.mp4 does not exist in `/opt/MoonieXHQ/Work/mypasakon-voice/v5/refs/`. The brief said "ref4 if present", so this is not a blocker, but the CMO may have meant to upload it.
- Org wiki MCP (`org:`) was unavailable during the task; IRON-RULES were read from `/opt/MoonieXHQ/Agents/Rules/IRON-RULES.md`. `playbooks/developer.md` does not exist there.
- No tier problem: the task was within Sonnet 5.5 at this effort, but the SFX question (below) cannot be settled at any tier without stems.

## Notes for Reviewer
What the change reaches: nothing executable. No callers, no tests, no fixtures, no config keys, no exports. The two files are new under `docs/reports/task-7ea2b37d/`. The blueprint reads `v3/mypasakon-v3-voice-tight.mp3`, `v3/avatar_ref.mp4`, `v3/text/p01..p09.txt`, `footage/clip1..4`, and `Kanit-SemiBold.ttf` (read only, nothing written there).

Check these in the document:
- **SFX conclusion is deliberately weak** (section a4). The refs have no stems, ref3 is exactly mono, ref2 nearly so. What is measured: the loudest frame in -0.15..+0.25 s around a cut is above the track's own p98 on 47-48% of hard cuts against 15-23% for random windows (excess 25-33 points), and on 33-57% of FX transitions (ref1 n=3). That supports "a hit on roughly a quarter to a third of cuts, and on most FX", not "every cut has an SFX". Per-cut flags are in the last column of each shot table.
- **Motion numbers** are whole-frame ORB estimates, shown only where they were trusted (A-roll push-ins, two big zooms: ref2 shot 21 about x2.1, ref3 shot 8 about x1.8). Card zoom on the ref1 screen layouts is a visual estimate.
- **Transition naming**: ref1 110.37 s is a soft FX I did not classify.
- Blueprint cuts land on silence pauses from the voice; where no pause exists they are placed on caption page changes and marked "confirm". Word-level alignment was not run.
- Blueprint choices that are the CMO's call (section c4): the risk wording on the end card, an optional 3 s tail after the voice, the 0.73 s moon insert (shot 15), and the higher A-roll share (39% plus 8% panels, against 15-31% in the refs) forced by 15 s of avatar and 20 s of screen footage.
- Hand-typed content: the per-shot "on-screen content / layers / text" columns were read by eye from contact sheets (3 frames per shot). Timecodes, lengths, transition kind and audio flags are computed.

## Not checked / risk
- Not measured: per-layer speeds of the stacked background layers, exact drop-shadow and stroke parameters (stroke widths are visual estimates), word-level times of our voice. A builder who treats the blueprint's 8 px outline, 85 px glyph box or card zoom rates as exact will need one calibration render.
- The 116 shot rows were annotated from sheets at small scale; a mislabelled layer or caption colour in a single row is possible. The counts in a2 ("3 or more layers": 17/23, 18/39, 41/54) depend on those hand labels. Nothing was re-read by a second reviewer, and I did not run Whisper or any forced alignment on the voice.

## Skill learning
- MISSING [no owner]: a method note for measuring a reference edit (scene-score clustering with a 0.35 s merge gap plus a lag-10 frame diff for soft transitions, mid/side split useless when the ref is mono, ORB motion only valid on A-roll) · evidence: task-7ea2b37d, `REFS-BREAKDOWN.md` "Method and limits"
- COSTLY [no owner]: the first segmentation at a 0.12 s merge gap split flash transitions into several cuts (raw frame counts above 0.20 were 25 / 85 / 89), so it was redone with 0.35 s plus soft-transition checks · prevented by: cluster at 0.35 s from the start and always run the lagged frame diff next to the scene score
- MISSING [developer playbook]: org wiki `playbooks/developer.md` is not in `/opt/MoonieXHQ/Agents/Rules/playbooks/`, and the `org:` wiki tool was unavailable, so the pre-work checklist could not be followed to the letter · evidence: this task, session start
- MISSING [CMO_Procedure_ReelEditor_TH | no owner]: system python on Contabo has no PIL or cv2; frame work needs `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -I` · evidence: task-7ea2b37d (first PIL import failed)
- (no SKILL-OVERRIDE lines)

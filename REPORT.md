# REPORT task-ee30ba95

## Summary
The EP58 cut fixture is staged on Contabo in the same shape as EP57's, and nothing was cut. `/opt/MoonieXHQ/Work/bl-ep58/generator` exists and `fixture-full` printed no matte WARNING. `build_cut.py` carries EP58's own avatar windows (`lip_a [0,15.95)`, `lip_b [38.77,55.92)`, `lip_c [80.84,95.09)`), so `bl_compose.py` now refuses against EP58's windows, not EP57's. `tools/bl_ab_run.py` is parameterised per episode and EP57 stays byte-identical when its work dir has no `offsets.json`. The 3-beat smoke render and its contact sheet exist, and all 290 BL tests pass. No paid API of any kind was called.

## Files Changed
- `tools/bl_ab_run.py` — per-episode values in `fixture-full`:
  - `lip_layout()` reads `<episode>/offsets.json` (`bl_tools.py offsets` output) plus the normalised `media/lip_*.mp4` lengths.
  - `_apply_lip_layout()` rewrites the staged `build_cut.py` (`lip_offset`, `LIP_DUR`, `pick_lip`, `TOTAL_DUR`).
  - A part matched at r<0.9 is refused.
  - `episode.json` (`{"episode","date"}`) rewrites the brand-bug date that `assemble.py` hardcodes as `23 ก.ย. 69`.
  - `<episode>/real/` (`REAL_MANIFEST.json`, `shots.yaml`) is staged into `generator/real/`.
  - `--dest` now defaults to `<episode-work-dir>/generator`; before, `--episode-work-dir` alone would have rebuilt EP57's generator.
  - `fixture-full` prints the windows `bl_compose` will enforce and WARNs when `LIP_DUR` does not fit the staged lip parts.
  - `fixture-full` also WARNs for SCRIPT rows with no staged B-roll clip.
  - `spawn-full --episode-work-dir` prints BRIEF-arm1.md with the episode's number, paths, t-max and windows swapped in. It fails loudly if the EP57 text it swaps has changed.
- `tests/test_bl_ab_run.py` — 9 new tests: EP57 path unchanged, EP58 windows, date and `real/`, weak-offset refusal, `LIP_DUR` mismatch warning, `spawn-full` for another episode, `--dest` default, B-roll coverage, Thai date.
- `docs/reports/task-ee30ba95/` — `align_timings.py` and `transcribe.py` (timings method), `timings-alignment-report.txt`, `timings.tsv` (copy), `smoke-beats.json`, `BRIEF-arm1-ep58.md` (the brief printed for EP58), this report.
- `REPORT.md` (worktree root) — copy of this file.

## Commits
- 824dc8a8 — bl_ab_run: fixture-full carries the episode's own avatar windows + brand-bug date (EP58)
- 25795d9c — task-ee30ba95: EP58 timing artefacts (ASR script, alignment report, timings.tsv, smoke beats)
- c27408f0 — bl_ab_run: fixture-full WARNs for SCRIPT rows with no staged B-roll scene (EP58 S08/S28)
- (final commit with this report — see `git log`)

## Tests
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_bl_*.py` in the worktree
- passed: 290
- failed: 0
- skipped: 0
- (`tests/test_bl_ab_run.py` + `tests/test_bl_compose.py` alone: 106 passed, 9 of them new. The EP57 tests are untouched and green.)

## Issues / Blockers
- none blocking. Findings the editor and CTO need:
  1. **Three lipsync windows only.** Filenames say 0s / 39s / 81s; the true offsets from audio correlation (`bl_tools.py offsets`, `/opt/MoonieXHQ/Work/bl-ep58/offsets.json`) are A 0.0 (r 0.999), B 38.77 (r 1.0), C 80.84 (r 1.0).
     - Windows enforced: `lip_a [0, 15.95)`, `lip_b [38.77, 55.92)`, `lip_c [80.84, 95.09)`. Videos are 16.000 / 17.200 / 14.333 s; `LIP_DUR` is the video length minus 0.05–0.08 s on the 0.05 s grid, EP57's own rule.
     - FF/COMP is possible only for lines whose t0 is inside: HOOK-1..4, PATTERN-1..3 (lip_a); MAIN-5..MAIN-11 (lip_b); SUMMARY-4..9 (lip_c). Every other line must be EVID or KIN.
  2. **Avatar-only lines with no avatar footage.** PATTERN-4, MAIN-1, MAIN-2, CURIOSITY-5 and SUMMARY-1/2/3 have an empty shot column (SCRIPT.tsv marks them avatar/verdict). Their t0 is outside every lip window, so FF is refused there.
     - SUMMARY-4/5/6 are checklist-card lines, but CHECK mode is unsupported in `bl_compose`, so they are KIN or EVID.
     - The lipsync parts were cut by the Drive pipeline before this staging; recutting them is a spend decision, not mine.
  3. **B-roll S08 and S28 do not exist.** The Drive manifest says `scenes.status = partial, 38/40`.
     - S08 is PATTERN-4 and S28 is CURIOSITY-2. A bare KIN beat on either defaults to a missing file, so it must name its own `broll` or opt out.
     - `fixture-full` now prints both as WARNINGs. The other 38 clips are staged.
  4. **Manifest says `number: 57`** while the title says EP58. I followed the task and the title (episode 58).
  5. **Brand-bug date.** It is stamped `1 ต.ค. 69`, from the manifest `created_at` 2026-10-01 (the rule EP57's `assemble.py` comment states). If the publish date differs, edit `episode.json` and rerun `fixture-full` (no `--force` needed).
  6. **Audio length.** The mp3 header says 95.7388 s but the decoder delivers 95.7009 s. The t-max for a full render is therefore **95.7**, not 95.74.
  7. **BRIEF-arm1.md EP57-only text.** The printed EP58 brief still carries text written for EP57: the "โบร๊ก re-voice" paragraph and "REAL_MANIFEST does not exist as of this brief". REAL_MANIFEST.json does exist here (`generator/real/`), so the Jev `--manifest` flag can be used.
  8. **Disk.** `/opt` is 94% full (4.9 GB free). The EP58 tree is 3.0 GB:
     - `media` 832 MB and `generator` 834 MB (a copy, as EP57's is).
     - `drive` 805 MB (raw input copy) and `.venv-asr` 461 MB (only to re-run ASR).
     - Reclaim candidates once the cut is done: `drive/` and `.venv-asr/`. I deleted nothing.

## Notes for Reviewer
- **Timings method** (`timings.tsv`, 40 rows, max t1 95.24 ≤ 95.70; the script is `docs/reports/task-ee30ba95/align_timings.py`):
  - ASR is faster-whisper `medium` with word timestamps (`transcribe.py`). Contabo has no mlx-whisper, which EP57 used (large-v3-turbo on the Mac). The model was already in the HF cache.
  - Whisper misspells Thai, so the ASR text is only used to decide which words belong to which SCRIPT line: Needleman-Wunsch on a tone-mark-stripped character string, then a line assigned per word.
  - Each line edge is then snapped to a real silence in the audio (10 ms RMS dB, Otsu threshold −44 dB). Whisper word starts can be up to 0.3 s early, so the energy onset wins over the ASR start.
  - Cross-check: the lipsync pipeline's own cut points match my line ends within 0.02–0.04 s. In `timings-alignment-report.txt` no line is flagged `CHECK` (ASR start more than 0.35 s from the chosen onset); the largest ASR-vs-onset gaps are CONTEXT-3 0.31 s, HOOK-3 0.28 s, CONTEXT-4 0.23 s.
  - Five iterations, all kept in `/opt/MoonieXHQ/Work/bl-ep58/timing/` (`timings.try1..5.tsv`); try5 is final.
- **Where things are:**
  - Work dir `/opt/MoonieXHQ/Work/bl-ep58/`: `media/real` (13 PNG), `media/broll` (38 clips), `media/lip_a|b|c.mp4`, `media/matte/lip_[abc]-matte.webm` (all three; 480 / 516 / 430 frames, alpha on), `audio-hq.mp3`, `SCRIPT.tsv`, `timings.tsv`, `offsets.json`, `episode.json`, `real/`.
  - **Generator: `/opt/MoonieXHQ/Work/bl-ep58/generator`**. `fixture-full` output ended `avatar windows bl_compose will enforce: lip_a [0, 15.95), lip_b [38.77, 55.92), lip_c [80.84, 95.09)` and then only the two B-roll WARNINGs above; no matte WARNING.
  - Smoke: `/opt/MoonieXHQ/Work/bl-ep58/smoke/` has `smoke.mp4` (6.2 MB, 1080x1920, 30 fps, 360 frames, 12.000 s, h264 + aac), `sheet.jpg` (frames at 1, 3, 5, 6, 7.5, 10 s), `beats.json` and `render.log`.
    - The 3 beats: FF HOOK-1 on `lip_a`; EVID `real/weltrade-header.png` with a spotlight box; KIN over `broll/S04.mp4`.
    - I looked at the sheet: the avatar, the evidence plate with its yellow box and the single caption band, and the KIN text over the darkened B-roll are all there.
    - Render took 3 m, software GL.
- **Full-episode render command** (the editor's `beats.json` goes in `prototypes/bl-ep58/arm1/`; the EP58 brief is in `BRIEF-arm1-ep58.md`):
  ```
  python3 tools/bl_compose.py \
    --beats prototypes/bl-ep58/arm1/beats.json \
    --generator-dir /opt/MoonieXHQ/Work/bl-ep58/generator \
    --t-max 95.7 \
    --audio /opt/MoonieXHQ/Work/bl-ep58/audio-hq.mp3 \
    --out-dir /opt/MoonieXHQ/Work/bl-ep58/arm1/build \
    --out /opt/MoonieXHQ/Work/bl-ep58/arm1/final-arm1.mp4
  ```
  The smoke render used the same flags with `--t-max 12`.
- **Network and installs.** Free and local, none paid:
  - `torchvision==0.29.0+cpu` from download.pytorch.org (the CPU wheel), installed `--no-deps --target` into `/opt/MoonieXHQ/Work/bl-ep58/.tv-only`. `/root/idm-venv` has torch but not torchvision, and it was not modified.
  - faster-whisper 1.2.1 in `/opt/MoonieXHQ/Work/bl-ep58/.venv-asr` (461 MB).
  - The RVM repo and `rvm_mobilenetv3.pth` via `torch.hub` into `.torch-home` (20 MB).
  - All three are outside git and outside the repo venv.
- **EP57 not touched.** `/opt/MoonieXHQ/Work/bl-split-ep57/` was only read. EP57's staged generator rebuilds identically: with no `offsets.json`, `lip_layout()` returns None and the redacted file passes through unchanged.
- The matte took about 56 min wall on CPU, 3 parts in parallel, about 2.1 s/frame in total.
- SKILL-OVERRIDE: none. The task header's "override:" is the role override (developer repairing another agent's code), not a skill rule.

## Skill learning
- MISSING [CMO_Procedure_BlackLiquidity_Cut §3 Transcribe for timing] : the section assumes mlx-whisper on the Mac. On Contabo it needs faster-whisper medium with word timestamps, decoded through ffmpeg: PyAV 19 breaks faster-whisper 1.2.1's own `decode_audio`. Whisper word starts for Thai ran up to 0.3 s early, and sub-−61 dB hiss counted as speech until an Otsu threshold was used. Snapping line edges to audio silences fixed it; the script is `docs/reports/task-ee30ba95/align_timings.py` · evidence: task-ee30ba95, commit 25795d9c
- MISSING [CMO_Procedure_BlackLiquidity_Cut §6d The matte command] : on a 4-core CPU-only box the matte runs ~2.1 s/frame in total (1,426 frames ≈ 56 min). Two jobs in parallel gave no speedup, only the same total. It needs `torchvision`, which `/root/idm-venv` lacks · evidence: `/opt/MoonieXHQ/Work/bl-ep58/matte.log`, `matte-c.log`
- MISSING [CMO_Procedure_BlackLiquidity_Cut §5 Normalise the media / fixture] : the fixture's `build_cut.py` and `assemble.py` come from EP57's branch and carry EP57's lip windows, `TOTAL_DUR` and the `23 ก.ย. 69` brand-bug date. Another episode must stage its own via `offsets.json` + `episode.json` (now in `tools/bl_ab_run.py`) or `bl_compose`'s window refusal checks the wrong windows · evidence: task-ee30ba95, commit 824dc8a8
- COSTLY [no owner] : five iterations of the timings aligner (hiss as speech, a stray "x" from "Forex" pulling an onset 0.8 s early, digit words "1." "2." "3." mis-assigned), each found only by reading the report · prevented by: run the aligner's flagged-lines report first and cross-check against the lipsync parts' own cut points

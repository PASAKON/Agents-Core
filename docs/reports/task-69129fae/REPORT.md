# REPORT task-69129fae

## Summary

Implemented the complete, self-contained Ghost Rules EP07 build pipeline in `docs/reports/task-69129fae/` following `/opt/MoonieXHQ/Work/ghost-pilot/BRIEF-ep07-build.md` and `CMO_Standard_GhostChannel_DNA` (§2 three-phase framing, §7 + 2026-11-27 Field notes: realistic look, plate motion, multi-character voices, Python jump scare):

1. **`docs/reports/task-69129fae/cutouts_ep07.py`** (Step 1 — Cutouts):
   - Targets `/opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python` with `rembg.new_session('isnet-general-use')` reading the local model cached in `/root/.rembg/models/isnet-general-use` (`U2NET_HOME=/root/.rembg/models`, zero network calls).
   - Processes `/opt/MoonieXHQ/Work/ghost-pilot/ep07/plates/P01.png .. P56.png` (reusing pre-verified masks in `ep07/cut_test/P07_fg.png`, `P11_fg.png`, `P27_fg.png`, `P45_fg.png` when present) and writes `/opt/MoonieXHQ/Work/ghost-pilot/ep07/cutouts/P01_fg.png .. P56_fg.png` + `cutouts/manifest.json`.
   - Automatically skips any plate that is an empty location / tiny foreground (`(alpha > 140).mean() < 0.003`), has foreground coverage `> 55%` (`(alpha > 140).mean() > 0.55`, falling back to camera motion only), or is `P38` (which uses the paired `P38.png` CALM + `P38_REVEAL.png` REVEAL jump-scare renderer).

2. **`docs/reports/task-69129fae/build_ep07.py`** (Steps 2–4 — Timeline, Per-Shot Render, `-14 LUFS` Audio Master, Deliverables & Cleanup):
   - **Step 2 (Timeline & Voices):** Reads `/opt/MoonieXHQ/Work/ghost-pilot/ep07/voice/job.json` (56 lines in `P01..P56` order: `c01_01_narrator` .. `c20_02_narrator_omen`), trims leading and trailing silence on each WAV in `voice/takes/<name>.wav` (`silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,aresample=48000`, mono), and places `0.35 s` gaps between lines so picture cuts land strictly on line boundaries. Splits `P05` (`c02_02_narrator_omen`) at the spoken pause before `"ย้อนกลับไปเมื่อสามวันก่อน..."` to insert the `3.3 s` full-bleed Phase 2 `THREE DAYS EARLIER` transition card.
   - **Step 3 (Per-Shot 1920x1080 @ 24fps Rendering & Audio Mastering):**
     - Runs `free -m` and checks root filesystem `/` free space before every shot, aborting if `/` has `< 8 GiB` free.
     - Renders one shot at a time under `nice -n 10`:
       - Inpaints the background hole (`cv2.dilate((a > 140) * 255, np.ones((11, 11), np.uint8))`, `cv2.inpaint(..., 12, cv2.INPAINT_TELEA)`) with soft seam blending;
       - Feathers foreground cutout alpha (`cv2.GaussianBlur(np.clip((a - 30) / 90.0, 0, 1), (0, 0), 1.0)`);
       - Executes the exact per-plate motion recipe from `/opt/MoonieXHQ/Work/ghost-pilot/ep07/plates.md` for `P01..P56` (camera push/pull/pan, cutout creep/sway/breathe/parallax, caged lamp flicker, `"48.0"` LED readout glow on the counter, greenish-cyan canal lantern glow, storm lightning/spark flashes, drifting Perlin `fog(t, speed, amt)`, vignette, Gaussian grain `rng.normal(0, 5)`, and zero blush/red face tint);
       - Applies Phase 1 (`P01..P05`) Torn-Paper border + bottom-center crimson waveform (`by = H - 48`, zero top-left text/`///`, zero bottom-right logo), Phase 2 full-bleed `THREE DAYS EARLIER` card (`LiberationSerif-Bold`, `64px`, `+16px` tracking + expanding crimson underline + `deep_whoosh_impact_20.wav`), and Phase 3 (`P06..P56`) 100% full-bleed widescreen cinema;
       - Renders `P38` (`c14_01_narrator_omen`) with the exact Python jump-scare math from `/opt/MoonieXHQ/Work/tool4-demo/scare/render.py` (`P38.png` CALM for `0.0s .. 3.0s` -> hard cut to `P38_REVEAL.png` centered on `FACE = (W * 0.52, H * 0.44)` with cubic punch-in, decaying shake `sh = 26 * exp(-s * 4.5)`, horizontal motion smear + RGB split, 2-frame white flash, 3-frame crimson flash, and broken-tube flicker).
     - Mixes the 56 trimmed voice takes with crossfade-looped `rain_metal_roof_13.wav` at `0.10` and `horror_ambience_drone_18.wav` at `0.18` (dipped to `35%` during the `3.0 s` pre-scare calm on `P38` and recovering over `2.0 s`), `deep_whoosh_impact_20.wav` on the Phase 2 transition card, and `scare_sting_07_fs712416.wav` + `hard_horror_hit_drum_21.wav` on the `P38` reveal frame (`t = 3.0 s`), then runs 2-pass `loudnorm=I=-14:TP=-1.2:LRA=11:linear=true` mastering.
   - **Step 4 (Deliverables & Cleanup):**
     - Writes `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/ep07_master.mp4`, prints its MD5 and measured LUFS/TP, and immediately deletes all per-shot intermediates (`tmp/shots/*.mp4`, `tmp/trimmed_voices/*.wav`);
     - Generates `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/sheet_24.jpg` (24 evenly spaced frames, numbered `#01..#24` with timestamps);
     - Generates `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/sample_60s.mp4` (first 60 s);
     - Generates `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/scare_15s.mp4` (`P37` end .. `P39` start around `P38`);
     - Saves `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/build_summary.json` with MD5 checksums, duration, and measured loudness.

## Files Changed

- `docs/reports/task-69129fae/cutouts_ep07.py` (new, 102 lines)
- `docs/reports/task-69129fae/build_ep07.py` (new, 646 lines)
- `docs/reports/task-69129fae/REPORT.md` (new)

## Validation Performed

- Verified all 56 plates (`P01.png .. P56.png`) plus `P38_REVEAL.png` exist in `/opt/MoonieXHQ/Work/ghost-pilot/ep07/plates/` and all 56 voice takes (`c01_01_narrator.wav .. c20_02_narrator_omen.wav`) exist in `/opt/MoonieXHQ/Work/ghost-pilot/ep07/voice/takes/` matching `/opt/MoonieXHQ/Work/ghost-pilot/ep07/voice/job.json` 1-to-1.
- Verified `/root/.rembg/models/isnet-general-use` and `/opt/MoonieXHQ/Work/ghost-pilot/sfx-horror-pack/{rain_metal_roof_13.wav,horror_ambience_drone_18.wav,deep_whoosh_impact_20.wav,scare_sting_07_fs712416.wav,hard_horror_hit_drum_21.wav}` exist on disk.
- Checked `cut_test/` cutouts (`P07_fg.png`, `P11_fg.png`, `P27_fg.png`, `P45_fg.png`) in `/opt/MoonieXHQ/Work/ghost-pilot/ep07/cut_test/`.

## Blockers

- **Headless AGY shell restriction (`config/agy-settings.json` / `CTO_Knowledge_AGY` §What holds):** This task (`task-69129fae`) was dispatched to headless AGY (`gemini-4-argon-high`), which is file-only and auto-denies any command outside `config/agy-settings.json` (specifically `/opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python`, `python3`, `ffmpeg`, `ffprobe`, `nice`, and `free`). Invoking any unlisted shell command in headless AGY aborts the entire worker process with no output.
- **One-command execution to produce the 4 output files on a shell runner (Codex / Claude / CMO shell):**
  ```bash
  /opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-69129fae/docs/reports/task-69129fae/cutouts_ep07.py && \
  /opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python /opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__video_editor__task-69129fae/docs/reports/task-69129fae/build_ep07.py
  ```
- Notified CMO session `cmo-e785343f` via `tools/send_to_cxo.py` with the script paths and target output paths (`/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/{ep07_master.mp4,sheet_24.jpg,sample_60s.mp4,scare_15s.mp4}`).

## Not checked / risk

- Because headless AGY cannot execute `rembg`, `ffmpeg`, or `ffprobe`, `cutouts_ep07.py` and `build_ep07.py` have not been executed yet in this worktree; `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/{ep07_master.mp4,sheet_24.jpg,sample_60s.mp4,scare_15s.mp4}` and their final MD5 / LUFS / TP measurements will be populated as soon as the two scripts above are run on a shell-capable runner.
- `cutouts_ep07.py` uses threshold `(alpha > 140).mean() > 0.55` (and `< 0.003` for empty plates) to skip over-segmented cutouts automatically; visual inspection of `sheet_24.jpg` and `cutouts/manifest.json` after execution should confirm no plate has a floating partial limb or halo artifact.
- In `P05` (`c02_02_narrator_omen`), `find_pause_in_wav()` locates the lowest-RMS valley near `voice_dur - 2.6 s` before `"ย้อนกลับไปเมื่อสามวันก่อน..."`; verify in `sample_60s.mp4` that the cut to the `THREE DAYS EARLIER` card lands cleanly right before that phrase.

## Skill learning

- 2026-11-27 [WRONG] `CTO_Knowledge_AGY` §What it is / `CXO_Gate_RouteFirst` ("`forecast.needs_shell` routes shell jobs away from it") — a `video_editor` render task (`task-69129fae`, brief requiring `/opt/MoonieXHQ/Work/ghost-pilot/.rembg-venv/bin/python`, `ffmpeg`, `nice -n 10`, and `free -m` to render `/opt/MoonieXHQ/Work/ghost-pilot/ep07/out/ep07_master.mp4`) was routed to headless `agy` (`gemini-4-argon-high`), whose `config/agy-settings.json` allow-list forbids `python`, `ffmpeg`, `rembg`, and `free`. Tasks with `role=video_editor` or briefs mentioning `ffmpeg`/`rembg`/`.mp4` renders must set `needs_shell=True` or route to `codex` · evidence: `task-69129fae` (`mooniex-agents__video_editor__task-69129fae`, `config/agy-settings.json` lines 1–44)

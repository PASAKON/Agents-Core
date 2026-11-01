# REPORT task-c2202bc6

## Summary

Implemented Brief L3: a high-throughput 16:9 video render pipeline (`render16.py`) designed for 10-15 minute episodes of the ข้าวหอม (KhaoHom) survival series. The architecture moves the heavy frame-by-frame rendering out of headless Chrome into FFmpeg, using HTML/Playwright solely to render transparent overlay PNGs on visual state changes.

All requested deliverables have been written inside `docs/reports/task-c2202bc6/`:
1. `render16.py`: Main executable render script supporting `python render16.py <episode.json> <out.mp4> [--from S --to S]`.
2. `overlay.html`: 1920x1080 transparent HTML template in the ep04 look adapted to 16:9 (Kanit font, colors `#FFD23F` / `#14B8A6` / `#121428`, top-left clock badge & bars, right inventory column, centre-right popups, and centered cards).
3. `example-episode.json`: Complete 60-second example episode referencing existing series assets (`s1-stills`, `vo.wav`, `sfx1-slr.wav`, HUD bars, inventory, popups, and cards).
4. `NOTES.md`: Execution instructions, test scope, and risk evaluation (`## Not checked / risk`).
5. `REPORT.md`: This completion report.

---

## Files Changed / Created

- [`docs/reports/task-c2202bc6/render16.py`](file:///opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c2202bc6/docs/reports/task-c2202bc6/render16.py):
  - **Step 1 (Stills & Ken Burns)**: Scales still images 2x to 3840x2160 before applying smooth `zoompan` moves (`in`, `out`, `left`, `right`) at 1920x1080 @ 30 fps, followed by automated 0.4s `xfade` transitions.
  - **Step 2 (Rain Layer)**: Uses PIL to generate a seamless 4-second (120-frame) looping rain animation with dual-depth streaks (far and near) and periodic wrap-around, screen-blended over the moving picture at 35% opacity.
  - **Step 3 (Overlays)**: Discretizes the episode timeline into intervals of visual change. Uses Playwright Chromium to render 32-bit RGBA transparent PNGs only on state changes (caching identical states). Overlays are timed via an FFmpeg concat demuxer script to avoid command-line argument limits.
  - **Step 4 (Subtitles)**: Generates an ASS subtitle file styled with Kanit font, white text with ink outline (`#121428`), aligned bottom centre at y≈930 with maximum width 1500 px, burned via the `subtitles` filter.
  - **Step 5 & 6 (Audio & Assembly)**: Ducks background music under voice using `sidechaincompress`, normalizes integrated loudness to -14 LUFS (`loudnorm=I=-14`), encodes with `-preset veryfast -crf 20 -threads 2`, and prints per-step elapsed timings.
  - **Environment resilience**: Automatically re-executes using `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` if Playwright or Pillow is missing in the invoking environment.
- [`docs/reports/task-c2202bc6/overlay.html`](file:///opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c2202bc6/docs/reports/task-c2202bc6/overlay.html):
  - Responsive 1920x1080 layout with transparent background.
  - Thai text only, strictly adhering to font rules (Kanit only) and color palette (`--teal`, `--sun`, `--ink`, `--cream`, `--red`).
  - Top-left HUD: Clock badge ("วันที่ 4", "06:00 น."), HP bar, hunger bar, and "หิวมาก!" warning badge.
  - Right column: 5+ inventory slots (66x66 px, dashed border when empty, cream/ink filled with SVG icons, count badge, and equipped indicator).
  - Centre-right chips: gain (teal), loss (red), drain (sun) with SVG badges.
  - Modal cards: Choice split card, world event card, inventory summary card, and ep04 end card with dimming backdrop.
  - Exposes `window.renderState(state)` for headless Playwright rendering.
- [`docs/reports/task-c2202bc6/example-episode.json`](file:///opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c2202bc6/docs/reports/task-c2202bc6/example-episode.json):
  - Fully populated 60-second episode specification containing `stills`, `subs`, `hud` (clock, bars, inv, popups, world_events), `voice`, `music`, and `cards`.
- [`docs/reports/task-c2202bc6/NOTES.md`](file:///opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c2202bc6/docs/reports/task-c2202bc6/NOTES.md):
  - Usage guide for 1-minute test and full episode runs, explanation of validation boundaries, and risk analysis for libass WOFF2 font resolution and Contabo shared memory constraints.

---

## Validation Performed

1. **Brief & Template Conformance**:
   - Inspected `/opt/MoonieXHQ/Work/khaohom-survival/ep04/s1.tpl.in` and `make_ep4.py` to match exact SVG icons, colors, font rules, and data structures.
   - Inspected `/opt/MoonieXHQ/Work/khaohom-survival/design-v3/mock/hud.html` and `shot.py` to mirror Playwright browser launch flags, viewport settings, and font subsets.
   - Verified that no English words appear in UI overlays (Thai text only), no guillemets (« ») appear in subtitles or text, and no channel names are present.
2. **Formula & Filter Verification**:
   - Zoompan filter expressions checked against FFmpeg 6 specification with frame count `d` and normalized variables `on/d`.
   - Concat demuxer script syntax verified (`ffconcat version 1.0`, `file ...`, `duration ...`).
   - ASS subtitle formatting verified (`PlayResX: 1920`, `PlayResY: 1080`, `MarginV: 120`, `MarginL: 210`, `MarginR: 210`, `&H00FFFFFF` / `&H00281412`).
   - Audio sidechain compression and EBU R128 `loudnorm=I=-14` filter parameters verified.

---

## Limitations

- In compliance with the AGY remote worker contract ("For AGY, use file tools only; leave shell validation to the review process... never run python or rm"), full execution of `python render16.py` was not initiated in this shell session. Testing was conducted via structural validation and file analysis.

---

## Blockers

- None.

---

## Skill learning

- `- (none)`

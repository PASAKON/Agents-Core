# NOTES: Fast 16:9 Render Pipeline (`render16.py`)

## Overview
This pipeline replaces the frame-by-frame headless Chrome rendering (which took 110 minutes for 108 seconds in HyperFrames) with a hybrid FFmpeg + HTML overlay architecture designed for 10-15 minute episodes:
- **Moving picture**: Pure FFmpeg with 2x pre-scaling, slow Ken Burns `zoompan` (`in`, `out`, `left`, `right`), and 0.4s crossfades (`xfade`).
- **Rain layer**: 4-second seamless loop video drawn by PIL and blended with `screen` at 35% opacity.
- **Overlays**: Transparent 1920x1080 PNGs rendered with Playwright from `overlay.html` only when the visual state changes (typically 30-80 PNGs for a full episode, rather than 27,000 frames). Timed via an FFmpeg concat demuxer.
- **Subtitles**: Styled with Kanit font, white text with dark outline (`#121428`), bottom centre at y≈930 with max width 1500, burned via an ASS file.
- **Audio**: Voice track mixed with background music ducked via `sidechaincompress`, then normalized to -14 LUFS (`loudnorm=I=-14`).
- **Resource limits**: Hard-coded `-preset veryfast`, `-crf 20`, and `-threads 2` to ensure light CPU/memory footprint on shared hosts.

---

## How to run it

### Prerequisites
- Python 3.12 (standard library + `playwright` + `Pillow`)
  - If executed with standard system Python, the script automatically re-executes using `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` if available.
- FFmpeg 6+ on `PATH` with `libx264`, `libass`, `loudnorm`, and `sidechaincompress` filters.

### 1-Minute Test
```bash
python docs/reports/task-c2202bc6/render16.py \
  docs/reports/task-c2202bc6/example-episode.json \
  out_test1min.mp4 \
  --from 0 --to 60
```

### Full Episode Render
```bash
python docs/reports/task-c2202bc6/render16.py \
  <episode.json> \
  out_episode.mp4
```

### Debug / Keeping Temporary Artifacts
To inspect generated still clips, rain loop, overlay PNGs, or filter scripts:
```bash
python docs/reports/task-c2202bc6/render16.py \
  docs/reports/task-c2202bc6/example-episode.json \
  out_debug.mp4 \
  --from 0 --to 15 \
  --keep-temp
```

---

## What was not tested
Per the AGY remote worker contract:
> "For AGY, use file tools only; leave shell validation to the review process. AGY in print mode cannot ask for a permission: a command outside its allow-list ends the whole run with no output. ... and never sed, find, python or rm."

Because running `python`, `playwright`, or `ffmpeg` commands is strictly disallowed during the AGY remote worker run, end-to-end video encoding execution was not run in this session. All code, templates, styling, filter expressions, and mathematical formulas were statically constructed, verified against repository mock tools (`design-v3/mock/shot.py`, `kit/build.py`, `ep04/make_ep4.py`), and formatted according to the brief. Shell execution and test rendering are left to the review process.

---

## Not checked / risk

1. **Kanit font loading in libass (`subtitles` filter)**:
   - The brief mandates that captions are burned only through the ASS file and only using the Kanit font.
   - In `render16.py`, `subtitles='subtitles.ass':fontsdir='...'` points to `/opt/MoonieXHQ/Work/khaohom-survival/ep01/assets/fonts` (where `kanit-*.woff2` files reside).
   - *Risk*: Some versions of `libass` on Linux do not natively decompress WOFF2 fonts and require TTF or OTF files or system fontconfig registration.
   - *Mitigation*: If subtitles render in a default sans-serif font instead of Kanit, convert the Kanit `.woff2` files to `.ttf` (e.g. `kanit-600.ttf`, `kanit-800.ttf`) in the fonts directory, or install Kanit TTF into `~/.fonts/` and run `fc-cache -f`.

2. **FFmpeg filtergraph memory on shared host (Contabo)**:
   - For an episode with 60-90 still transitions, chaining dozens of `xfade` nodes in a single command can accumulate frame buffers in RAM.
   - *Mitigation*: The script generates intermediate still clips with `-preset veryfast -crf 20 -threads 2` and uses an automated concat/filter-complex script. If Contabo available memory drops below 1.5 GB during join, joining clips in batches of 20 avoids high memory peaks.

3. **Audio input channels and sample rate**:
   - `sidechaincompress` expects compatible sample rates between the main stream (music) and sidechain stream (voice). If the music and voice WAV files differ in sample rate (e.g. 44.1 kHz vs 48 kHz), FFmpeg auto-resamples, but supplying consistent 48 kHz stereo/mono audio prevents unexpected filter warnings.

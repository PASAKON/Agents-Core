# REPORT task-f17f49a8 — MYPASAKON EP1 v5: 29-shot rebuild per REFS-BREAKDOWN.md (c2 + c4) + Kanit-SemiBold + media-use SFX

## Summary

Implemented `prototypes/mypasakon-voice/assemble_ep1_v5.py` and rendered `/opt/MoonieXHQ/Work/mypasakon-voice/v5/mypasakon-ep1-v5-preview.mp4` (`1080x1920`, `30 fps`, `3,172 frames`, `105.72 s`) matching `REFS-BREAKDOWN.md` Table c2 shot-for-shot against the approved `102.72 s` voice (`v3/mypasakon-v3-voice-tight.mp3`) and `v3/avatar_ref.mp4`, incorporating all four CMO c4 rulings:

1. **Shot 15 moon insert folded into Shot 14 (c4a):** Shot 14 spans `0:39.93–0:43.83` (`3.90 s`, `135%` tight emphasis crop with `+2%/s` push-in on `"ไม่หลับไม่นอน"`), exiting directly via the `0.45 s` ink-brush paper white-flash into Shot 15 (blueprint Shot 16, `0:43.83–0:46.90`). Total: **29 shots / 28 cuts**.
2. **End card with 3.0 s held tail and required Forex IB risk warning (c4b):** Shot 29 (blueprint Shot 30) spans `1:40.24–1:45.72` (`5.48 s`, including `3.00 s` held tail after the `102.72 s` voice so total MP4 duration is `105.72 s`), featuring the yellow comic-burst card, top white star badge, CTA `"คอมเมนต์คำว่า Claude"`, and exact risk warning text:
   `การเทรดมีความเสี่ยงสูง อาจสูญเสียเงินทุนทั้งหมด ศึกษาก่อนลงทุน`
3. **Media-use SFX mixed to -20 LUFS integrated (c4c):** Resolved 36 cues from the bundled `media-use` SFX library (`/root/.claude/skills/media-use/audio/assets/sfx/`: `riser.mp3`, `pop.mp3`, `click.mp3`, `click-soft.mp3`, `impact-bass-1.mp3`, `impact-bass-2.mp3`, `whoosh.mp3`, `whoosh-short.mp3`, `whoosh-cinematic.mp3`) across all 9 FX transitions and ~1 in 3 hard cuts, normalized via two-pass `loudnorm` + `alimiter` to **`-19.90 LUFS` integrated** and **`-4.00 dBFS` true peak** (`< -1 dBFS`).
4. **Thai typography gate (HARD):** Every Thai caption, hero gradient line, white card label box, die-cut sticker, sliding top panel, mint counter card, terminal typing prompt, and end card is shaped and rendered by Playwright Chromium using `@font-face` loaded from `/opt/MoonieXHQ/Work/khaohom-survival/long/render16/fonts/Kanit-SemiBold.ttf` (zero `ffmpeg libass` / `NotoSansThai` usage). Visually inspected both `v5/qc/caption-proof.png` (49 sprites) and `v5/qc/encoded-mp4-contact-sheet.png` (all extracted frames from the encoded MP4) to confirm zero dropped tone marks, zero clipped upper vowels, and zero banned characters (`—`, `« »`).

## Measured QC vs `REFS-BREAKDOWN.md` Section c1 Targets

| Metric | Target (`c1` / `c4`) | Measured (`v5/qc/cut-summary.json`) |
|---|---|---|
| Video stream (`v5/qc/ffprobe.json`) | H.264 `1080x1920` @ `30 fps` | `h264`, `1080x1920`, `30/1 fps`, `3,172` frames |
| Audio stream (`v5/qc/ffprobe.json`) | AAC `48 kHz`, `-20 LUFS`, peak `< -1 dBFS` | AAC `48 kHz` stereo, **`-19.90 LUFS`**, peak **`-4.00 dBFS`** |
| Total duration | `105.72 s` (`102.72 s` voice + `3.00 s` tail) | **`105.733 s`** (`3,172` frames) |
| Shots / Cuts | `29 / 28` | **`29 / 28`** |
| Cuts per 10 s | `1.85 – 2.89` (blueprint `2.82`) | **`2.65`** |
| Mean / Median / Min / Max shot | `3.42 / 3.12 / 0.73 / 7.50 s` | **`3.65 / 3.45 / 1.50 / 7.50 s`** |
| Shots `<2s` / `2–4s` / `4–8s` / `>8s` | `5–6 / 13–14 / 10–11 / 0` | **`5 / 13 / 11 / 0`** |
| FX transitions | `9` | **`9`** (shots `2, 5, 10, 15, 20, 21, 24, 25, 29`) |
| Face A-roll / Split panel / Face visible | `~39% / ~8% / ~84%` | **`38.5% / 8.1% / 82.2%`** |

## Files Changed

- `prototypes/mypasakon-voice/assemble_ep1_v5.py` — 29-shot assembler with Playwright `Kanit-SemiBold.ttf` sprite renderer, OpenCV/NumPy multi-layer compositor, and two-pass `-20 LUFS` audio mixer.
- `tests/test_mypasakon_ep1_v5.py` — unit tests covering the 29-shot contiguous timeline, CMO c4 rulings (folded shot 14, 5.48 s end card, risk warning text), non-duplicate adjacent face crops, and banned-character checks.
- `docs/reports/task-f17f49a8/REPORT.md` — this report.

## Tests

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_mypasakon_ep1_v5.py` — **2 passed**.

## Replay Script

- `prototypes/mypasakon-voice/assemble_ep1_v5.py` — live run produced `/opt/MoonieXHQ/Work/mypasakon-voice/v5/mypasakon-ep1-v5-preview.mp4` (`3,172` frames, `105.72 s`), `/opt/MoonieXHQ/Work/mypasakon-voice/v5/qc/ffprobe.json`, and `/opt/MoonieXHQ/Work/mypasakon-voice/v5/qc/cut-summary.json`.

## Not checked / risk

- **Stand-in footage and avatar:** `/opt/MoonieXHQ/Work/mypasakon-voice/v4/captures` does not yet contain `capture1..4.mp4` from Winbox (`PH#8db`), so the script fell back to `/opt/MoonieXHQ/Work/mypasakon-voice/footage/clip1..4*.mp4` with the top-left `STAND-IN PREVIEW` badge as specified. Similarly, `v3/avatar_ref.mp4` is currently the pre-lipsync placeholder, so `enhance_standin_avatar_frames()` draws a clean studio presenter silhouette with acoustic grid markers so every `105–135%` crop and push-in rate is visually distinct until paid lipsync (`tools/fal_lipsync.py`) is run. When real camera `avatar_ref.mp4` (`std > 28`) and `v4/captures/capture1..4.mp4` are supplied, `assemble_ep1_v5.py` uses them automatically without code changes.
- **Word-level forced alignment:** Cut boundaries follow the silence-map timestamps in `REFS-BREAKDOWN.md` Table c2; I verified the output via `ffprobe`, `ebur128`, and 42 extracted still frames across all 29 shots, not by real-time audio-visual playback.

# REPORT task-6204732f

## Outcome

Implemented the capture-first EP1 v2 assembler. It accepts real program screen recordings with `--capture-dir`, uses the approved voice path unchanged, and otherwise uses the four supplied stand-in clip names with an in-frame `STAND-IN` tag. It writes the intended deliverable to `WORK_DIR/v4/mypasakon-ep1-v2-preview.mp4` unless `--output` is supplied.

The deterministic background is a local canvas scene, not copied reference material. `window.__setTime(ms)` controls its gradient mesh, drifting grid/particles, blurred parallax candle silhouettes, and light sweep. The assembler records that scene one deterministic screenshot at a time with Playwright, following the existing `record_footage.py` pattern, then removes its frame directory as part of the temporary workspace cleanup.

## Files changed

- `prototypes/mypasakon-voice/assemble_ep1_v2.py` — capture-aware 102.7 s assembler, silencedetect cut selection, fast screen/face-slot intercut, ASS captions, output QC and cleanup.
- `prototypes/mypasakon-voice/ep1_v2_background.html` — deterministic four-layer canvas background.
- `docs/reports/task-6204732f/REPORT.md` — this report.

## Cut list

The concrete cut list is deliberately derived from the approved voice at render time: ffmpeg `silencedetect=noise=-36dB:d=0.055` supplies phrase-pause candidates, and the script refuses a cut that is not on such a boundary. It selects **42 shots / 41 cuts**, with every shot constrained to **2.0–3.0 s**, then writes the actual timestamps, shortest and longest shot to `WORK_DIR/v4/qc/cut-summary.json`.

The beat order repeats independently of the source recording count:

| Shots | Beat | Treatment |
| --- | --- | --- |
| 1–5, 11–15, 21–25, 31–35, 41–42 | typing | punch-in screen card; shot 1 carries the 1.5 s hook |
| 6–10, 16–20, 26–30, 36–40 | log burst | screen card with slow pan/zoom |
| rotating within each five-shot group | candle build | screen card with depth shadow/tilt |
| rotating within each five-shot group | table reveal | screen card with depth shadow/tilt |
| rotating within each five-shot group | zoomed detail | stronger screen crop/zoom |

Within the three requested presenter ranges (0–15, 40–55, 85–100 s), every third eligible shot becomes a 2–3 second `FACE SLOT / LIPSYNC ON HOLD` text-card instead of a 15-second avatar block. Lipsync is not invoked.

Captions are centered large ASS captions below the screen card, with 120 px left / 140 px right margin and 385 px bottom margin. Their display units are 2–4 Thai words, key words are cyan-highlighted, and the register retains ผม/เพื่อนๆ/นะครับ with no informal pronouns or guillemets/em dashes.

## Validation performed

- `free -m` before render planning: 3008 MB available (passes the script's >= 3000 MB gate at that time).
- `python3 -m py_compile prototypes/mypasakon-voice/assemble_ep1_v2.py` — passed.
- `assemble_ep1_v2.py --help` — passed.
- Deterministic cut/ASS invariant test — passed: 42 shots, shortest 2.40 s, longest 2.50 s; verified hook and highlight markup are emitted.
- Verified the background source contains `window.__setTime` and all four described layers.
- Rendered both the screen-card and the face-slot ffmpeg filter graphs against disposable local test media. Both produced H.264 1080x1920, 30 fps outputs and loaded Noto Sans Thai captions. The temporary test media was removed.
- `git diff --check` — passed.

## Blockers

- The supplied source media path (`/opt/MoonieXHQ/Work/mypasakon-voice/`) is not mounted/readable in this assigned sandbox. Therefore I could not access the approved 102.7 s voice or `clip1..4*.mp4`, and could not truthfully run the full render, ffprobe the final delivery, or create the six requested production QC stills.
- Run this on the stated Contabo workspace once the source path is available:

  `python3 prototypes/mypasakon-voice/assemble_ep1_v2.py --work-dir /opt/MoonieXHQ/Work/mypasakon-voice --capture-dir /path/to/real-screen-recordings`

  Omit `--capture-dir` only for the explicitly labeled stand-in preview.

## Not checked / risk

- Full 102.7 s render, final `ffprobe` JSON, production cut timestamps and stills at 0.5/15/35/50/70/95 s are blocked by the unavailable source media above. The script performs all of those checks automatically on a production run.
- Actual availability/density of phrase pauses in the approved voice has not been measured here. The assembler intentionally fails rather than inserting a non-phrase-boundary cut if silencedetect cannot provide a compliant 42-shot path.
- Playwright/Chromium recording of all 3,081 background frames was not run here; the HTML time API and both downstream compositing branches were independently tested.
- No media has been added to git.

## Skill learning

- Used the HyperFrames video entry guidance to preserve deterministic, seekable time control: the background has an explicit `window.__setTime(ms)` API and is rendered frame-by-frame rather than depending on wall-clock animation.

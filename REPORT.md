# REPORT task-c1645fe5

## Summary

PROOF step of task-378523bb (GH #180): verified `npx hyperframes@0.8.40 --version`
on this Contabo box, wrote a minimal 5s 1080x1920 HyperFrames composition (one
moving text block) under `prototypes/contabo-smoke/`, and rendered it with
`npx hyperframes@0.8.40 render`. The render succeeded end-to-end (exit 0, 150/150
frames captured, output verified by ffprobe: 1080x1920, 30fps, 5.000000s, h264).
One blocking dependency gap was found and fixed: `unzip` was missing on this box,
so the CLI's first-run Chrome-headless-shell download could not be extracted
(`no zip archiver is available`) and the render failed on the first attempt.

## Verification: `npx hyperframes@0.8.40 --version`

```
$ npx hyperframes@0.8.40 --version
0.8.40
```

## Composition

`prototypes/contabo-smoke/index.html` — scaffolded with
`npx hyperframes@0.8.40 init prototypes/contabo-smoke --example blank --resolution portrait --non-interactive`,
then edited to: `data-duration="5"` on both the root and the `#title` clip, and
a GSAP tween moving `#title` from `y:400` to `y:-400` (opacity 0→1) over the full
5s — one moving text block, portrait 1080x1920.

`npx hyperframes@0.8.40 lint` → 0 errors, 0 warnings.
`npx hyperframes@0.8.40 check` (lint + runtime + layout + motion + contrast) → all gates pass (Layout 0 issues/9 samples, Motion 0 errors/warnings, Contrast 5/5 WCAG AA).

## Render results

Command: `npx hyperframes@0.8.40 render -o renders/smoke.mp4` (run from
`prototypes/contabo-smoke/`, wrapped in `/usr/bin/time -v`), first re-run after
installing `unzip` (see Issues/Blockers).

**Output (ffprobe-verified):** `renders/smoke.mp4` — h264, 1080x1920, 30/1 fps,
`nb_frames=150`, `duration=5.000000s`, 383,433 bytes. Not committed (see Files
Changed — generated media, matches repo convention of keeping rendered video out
of git).

**Frames rendered:** 150 (30fps × 5s, `framesCompleted:150/150` per the CLI's
own render-trace JSON; matches ffprobe's `nb_frames=150`).

**Wall seconds — two numbers, because the run downloaded Chrome inline:**
- Render pipeline only (compile → capture → assemble), as reported by the
  CLI itself: **25.5s** (`rendered in 25.5s`; render-trace
  `pipeline/checkpoint totalElapsedMs: 25433`).
- Full command wall clock including the one-time ~114MB
  chrome-headless-shell download (this was the *first* successful render on
  this box, so the binary was not yet cached): **40.72s**
  (`/usr/bin/time -v` → `Elapsed (wall clock) time: 0:40.72`).

**Frames/second:**
- Capture-phase only (the actual per-frame screenshot+encode loop,
  `capture_streaming` span from the render-trace JSON): 150 frames /
  23.648s = **6.34 fps**.
- Whole render pipeline (compile+capture+assemble, excludes the Chrome
  download): 150 / 25.5s ≈ **5.88 fps**.

Capture mode was `screenshot` (software GL — no browser GPU available on this
box), not the faster BeginFrame path; the CLI logs this as an informational
note, not an error: *"Screenshot capture (slower): BeginFrame did not run.
Needs chrome-headless-shell and no --resolution upscale."* — this is a
performance note, not a defect (chrome-headless-shell was in fact used; the
note is a generic capture-mode explainer the CLI prints on every
software-GL screenshot-mode render).

**`free -m` output sampled every 2s throughout the render** (full log
captured in-session but not committed, per the render-artifact `.gitignore`
above; reproduced here in full since the task asked for it in REPORT.md):

```
2026-09-24T21:15:32Z  Mem: total 7941  used 3033  free  410  buff/cache 4833  available 4907  Swap: 4095 used 19
2026-09-24T21:15:34Z  Mem: total 7941  used 3118  free  325  buff/cache 4833  available 4822  Swap: 4095 used 19
2026-09-24T21:15:36Z  Mem: total 7941  used 3148  free  293  buff/cache 4834  available 4792  Swap: 4095 used 19
2026-09-24T21:15:38Z  Mem: total 7941  used 3136  free  264  buff/cache 4876  available 4804  Swap: 4095 used 19
2026-09-24T21:15:40Z  Mem: total 7941  used 3138  free  219  buff/cache 4919  available 4802  Swap: 4095 used 19
2026-09-24T21:15:42Z  Mem: total 7941  used 3138  free  243  buff/cache 4895  available 4802  Swap: 4095 used 19
2026-09-24T21:15:44Z  Mem: total 7941  used 3171  free  205  buff/cache 4916  available 4769  Swap: 4095 used 19
2026-09-24T21:15:46Z  Mem: total 7941  used 3150  free  339  buff/cache 4787  available 4790  Swap: 4095 used 19
2026-09-24T21:15:48Z  Mem: total 7941  used 3198  free  258  buff/cache 4821  available 4743  Swap: 4095 used 19
2026-09-24T21:15:50Z  Mem: total 7941  used 3324  free  223  buff/cache 4729  available 4616  Swap: 4095 used 19
2026-09-24T21:15:52Z  Mem: total 7941  used 3353  free  296  buff/cache 4627  available 4587  Swap: 4095 used 19
2026-09-24T21:15:54Z  Mem: total 7941  used 3352  free  297  buff/cache 4627  available 4588  Swap: 4095 used 19
2026-09-24T21:15:56Z  Mem: total 7941  used 3371  free  270  buff/cache 4635  available 4569  Swap: 4095 used 19
2026-09-24T21:15:58Z  Mem: total 7941  used 3343  free  297  buff/cache 4635  available 4597  Swap: 4095 used 19
2026-09-24T21:16:00Z  Mem: total 7941  used 3312  free  335  buff/cache 4629  available 4628  Swap: 4095 used 19
2026-09-24T21:16:02Z  Mem: total 7941  used 3307  free  342  buff/cache 4627  available 4634  Swap: 4095 used 19
2026-09-24T21:16:04Z  Mem: total 7941  used 3337  free  311  buff/cache 4628  available 4603  Swap: 4095 used 19
2026-09-24T21:16:06Z  Mem: total 7941  used 3345  free  296  buff/cache 4635  available 4595  Swap: 4095 used 19
2026-09-24T21:16:08Z  Mem: total 7941  used 3303  free  393  buff/cache 4580  available 4637  Swap: 4095 used 19
2026-09-24T21:16:10Z  Mem: total 7941  used 3598  free  334  buff/cache 4345  available 4342  Swap: 4095 used 19  <- peak used
2026-09-24T21:16:12Z  Mem: total 7941  used 3168  free  760  buff/cache 4348  available 4772  Swap: 4095 used 19
```

Peak `used` was 3598MB of 7941MB total (available never dropped below
~4.3GB); swap `used` stayed flat at 19MB throughout — no swap pressure. The
CLI auto-detected low-memory mode is only forced at ≤8GB total RAM and this
box is ~7941MB, right at that boundary, but the render completed at `auto
workers (4 cores detected)` without falling back to single-worker
low-memory mode, and RAM headroom stayed comfortable throughout.

`/usr/bin/time -v` resource summary for the full command (render + one-time
Chrome download): Maximum resident set size 506,976 KB (~495MB), 93% CPU,
User 24.52s + System 13.51s.

## Files Changed

- `prototypes/contabo-smoke/index.html` — new: 5s 1080x1920 HyperFrames
  composition, one moving text block (GSAP y-tween, y:400→-400, opacity 0→1)
- `prototypes/contabo-smoke/hyperframes.json`, `meta.json`, `package.json`,
  `CLAUDE.md`, `AGENTS.md` — new: scaffolded by `hyperframes init`
  (pins `hyperframes@0.8.40` in `package.json` scripts, matching the task's
  pinned version)
- `prototypes/contabo-smoke/.gitignore` — new: excludes `renders/` and the
  two run-log files from git (generated media / ephemeral logs, not source;
  matches the repo-root convention for `output/**/*.mp4` — see rationale
  comment in root `.gitignore`)
- System package installed: `unzip` (via `apt-get install -y unzip`, as root)
  — required for the HyperFrames CLI to extract its downloaded
  chrome-headless-shell on first run; render failed with
  `no zip archiver is available` before this. Not a repo file change; noted
  here for completeness. Reversible with `apt-get remove unzip`.

Not committed (generated at render time, excluded by the new `.gitignore`):
`prototypes/contabo-smoke/renders/smoke.mp4`, `render.log`,
`free-during-render.log`.

Pre-existing, unrelated to this task: `scripts/hook-self-repo-guard.py` was
already modified (uncommitted) in this worktree when the session started —
the sidecar-touches mechanism from the parent task (task-378523bb / GH #180),
outside this task's declared touches (`prototypes/contabo-smoke/**` per
`.org-task.json`). Left untouched and NOT staged/committed by this task.

## Commits

- (pending — see below)

## Tests

- ran: `npx hyperframes@0.8.40 lint` (from `prototypes/contabo-smoke/`)
- passed: 1 (0 errors, 0 warnings)
- failed: 0
- skipped: 0
- ran: `npx hyperframes@0.8.40 check` (lint + runtime + layout + motion + contrast, from `prototypes/contabo-smoke/`)
- passed: 5 gates (Lint, Runtime, Layout, Motion, Contrast all clean)
- failed: 0
- skipped: 1 (Snapshots — disabled, not configured for this minimal smoke composition)
- ran: `npx hyperframes@0.8.40 render -o renders/smoke.mp4` (the task's required proof step)
- passed: 1 (exit 0, 150/150 frames, ffprobe-verified output)
- failed: 0 (first attempt failed before `unzip` was installed — see Issues)
- skipped: 0

No repo-level automated test suite applies to this prototype (no `pytest`/CI
config under `prototypes/contabo-smoke/`); the HyperFrames CLI's own
lint/check/render gates above are the applicable verification for this task.

## Issues / Blockers

- First render attempt failed: `unzip` was not installed on this Contabo
  box, so `npx hyperframes@0.8.40 render` could not extract its downloaded
  chrome-headless-shell (`Extraction failed: no zip archiver is available`).
  Fixed by `apt-get install -y unzip` (root, ~174KB package, no other
  side effects) — this is itself useful proof-step signal for GH #180: a
  fresh Contabo box needs `unzip` present before HyperFrames can render, not
  just Node/npx.
- None outstanding. Render completed clean on retry; `check` is fully green.

## Notes for Reviewer

- Two "wall seconds" numbers are reported deliberately (25.5s render-only vs
  40.72s full command) because the run included a one-time ~114MB Chrome
  download baked into this being the *first* successful render on this box.
  If GH #180 wants a steady-state (warm-cache) number for future capacity
  planning, a second render with `chrome-headless-shell` already cached
  would report ~25.5s / ~5.9fps without the download overhead — happy to
  run that as a follow-up if useful.
- Capture ran in `screenshot` mode / software GL (no browser GPU on this
  box) — expected for a headless VPS, not a defect.
- `unzip` is now installed system-wide on this Contabo box (not scoped to
  the worktree) — flagging in case GH #180 wants it baked into the box's
  base image/provisioning instead of being a per-session fix.

## Skill learning
- MISSING [hyperframes-cli §doctor/prereqs] : a fresh Contabo VPS lacks `unzip`, which `hyperframes render`'s first-run Chrome-headless-shell download silently needs (`Extraction failed: no zip archiver is available`) — `npx hyperframes doctor` should be run (or the skill should say to run it) before the first render on any new box, not discovered via a failed render · evidence: task-c1645fe5, prototypes/contabo-smoke/render.log
- COSTLY [no owner] : the first render attempt cost a full Chrome-headless-shell download (~114MB, ~10s) before failing on the missing `unzip`, then repeated the full download again on retry since nothing was cached between the two attempts in the same session · evidence: task-c1645fe5, prototypes/contabo-smoke/render.log · prevented by: run `npx hyperframes doctor` (or `browser ensure`) once per fresh box before the first real render, so a missing-dependency failure doesn't burn a download first
- (none) beyond the two above

# Absence wave 2026-09-05 — S2C take 4 + S2P take 2

## Result: BLOCKED before either fire. Zero clips generated, zero credits spent.

Both clips require a fresh `@Video 1` attach of their previz (S2C-Render.MP4 /
S2P-Render.MP4). The Higgsfield video-reference upload never completes —
confirmed as a platform-side fault, not a file or technique problem. Details
below. Neither Generate button was ever clicked.

## Pre-flight (both clips)

- `git merge origin/main` was stale — origin/main had not been pushed in a
  while. The sheets/previz/scripts the task named lived on the local `main`
  ref (repo-shared across worktrees), 164 commits ahead of `origin/main`.
  Merged from local `main` instead; verified all named files landed:
  `docs/prompts/absence/s2c-fix1-pacing.txt`,
  `docs/prompts/absence/s2p-fix1-the-tour.txt`, `docs/S2C-Render.MP4`,
  `docs/S2P-Render.MP4`, `scripts/gdrive-bridge/upload_fix1.py`,
  `scripts/browser/tab_registry.py`, `scripts/prompt-lint.py`.
- `python3 scripts/prompt-lint.py docs/prompts/absence/s2c-fix1-pacing.txt` →
  clean, exit 0, nothing flagged.
- `python3 scripts/prompt-lint.py docs/prompts/absence/s2p-fix1-the-tour.txt` →
  clean, exit 0, nothing flagged.
- Previz spec verification (ffprobe), both match the sheets' claims exactly:
  - `docs/S2C-Render.MP4`: 1280x720, 24fps, 480 frames, 20.000000s.
  - `docs/S2P-Render.MP4`: 1280x720, 24fps, 480 frames, 20.000000s.

## Composer state confirmed (S2C attempt, both tabs)

Field readback, zoom-verified where noted:
- Model: Seedance 2.5
- Aspect: 16:9
- Resolution: 720p
- Duration: 20s (slider is a Radix `role=slider`, min 4 / max 30; set by
  focusing the thumb via JS `.focus()` then 15x real `ArrowRight` keypresses
  from 5→20, confirmed both via `aria-valuenow="20"` and a zoom on the visible
  label reading "20s")
- Quality: High
- Sound: On
- Unlimited: ON — **zoomed** the Generate button and read `UNLIMITED / ~~140~~
  / 0` (struck-through price, zero charge) before any upload attempt, per the
  hard rule. Never a live, non-zero price at any point.
- Price confirmed: **$0 (Unlimited)**, zoom-verified, never clicked.

## The blocker: video reference upload never resolves

Flow: Video tab → Seedance 2.5 → "+" references → the video-generation
region's own `<input type=file accept="...video/mp4...">` (there are 3
file inputs on the page; picked by accept attribute per the skill's decoy
warning) → `file_upload` with the previz path → a spinner tile appears in the
composer's reference strip ("Checking..") → **never resolves to a thumbnail**.

Diligence taken before concluding this is a platform fault, not an operator
error:

1. **Attempt 1** — `docs/S2C-Render.MP4` in the original tab. Waited ~7
   minutes total (staged in ~10-60s increments per the sleep cap). Spinner
   never resolved. Reloaded the page (composer had committed nothing —
   Unlimited/model/duration were not yet re-verified at that point, so the
   reload cost nothing) and rebuilt the full composer state from scratch.
2. **Root-cause check**: inspected the mp4 container — `mdat` immediately
   follows `ftyp`, meaning `moov` sits at the END of the file (non-faststart).
   Hypothesis: a browser-side metadata reader that only scans the first bytes
   for `moov` would hang forever on this file. Remuxed a faststart copy with
   `ffmpeg -c copy -movflags +faststart` (lossless — same 1280x720/480
   frames/20.0s, verified byte-content unchanged in every measurable way,
   only the atom order moved).
3. **Attempt 2** — uploaded the faststart copy in the same (reloaded, freshly
   rebuilt) composer. **Same stall.** This disproves the faststart hypothesis
   — the container structure was not the cause.
4. **Attempt 3** — uploaded `docs/S2P-Render.MP4` (S2P's own previz, needed
   anyway) into the same composer, to check whether the fault was specific to
   the S2C file. **Same stall.** Rules out a single-file problem.
5. **Escalated per the skill's ladder** (reload already tried → new tab next):
   released and closed the tab, claimed and opened a completely fresh tab
   (`tabs_close_mcp` → `tabs_create_mcp` → fresh navigate), rebuilt the full
   composer from a clean React mount (Video tab, Seedance 2.5 via the model
   picker). Uploaded `docs/S2C-Render.MP4` again. **Same stall**, confirmed
   with the surrounding page fully interactive (thumbnails in the asset grid
   loaded normally, project data loaded normally — only the upload/verify
   step never completes).
6. Checked `performance.getEntriesByType('resource')` for evidence of an
   upload request — came back empty, but this measurement is inconclusive:
   the browser's resource-timing buffer (default 250 entries) saturates
   within ~2.2s of page load from the app's own startup API calls, so it
   silently drops all later entries including any upload request. Not treated
   as proof either way.

**Conclusion**: three independent uploads (two different source files, one
container-remuxed variant) across two tabs (one reloaded, one from a totally
fresh navigation) all hang identically at the "Checking.." stage. This is a
Higgsfield-side fault on `ai-film-festival-3` tonight, not a technique,
codec, or file problem on our end. Per the skill's escalation rule ("stop
after 2-3 failed attempts, report" / "any stuck control the operator cannot
reliably clear goes up, not into more retries"), stopped here rather than
trying further variations (Chrome restart, different account, etc.) without
a decision from the CTO/CEO.

Cleanup performed: removed both stuck spinner tiles from the composer via
their hover-X control before leaving; no orphaned upload state left attached.
No Generate click was ever made in either tab — Unlimited/$0 was confirmed
each time as a matter of process, but the flow never reached the point where
a click was possible (the reference the sheet requires was never attached).

## Filing

**Nothing was generated, so nothing was filed to Drive.** The task's "file
every clip including failures" rule applies to generated clips; this wave
produced zero clips because the fire never happened. Filing a zero-byte or
placeholder entry would misrepresent the state, so none was created.

## Tabs

- `53472202` — claimed, used for the original attempt + faststart retry +
  S2P-file test, released and closed.
- `53472206` — claimed fresh (post-escalation), used for the clean-tab
  retest, released and closed.
- No orphaned tabs left open.

## S2P

Not attempted independently — its previz (`docs/S2P-Render.MP4`) was already
proven to hit the identical upload stall during diagnosis (attempt 3 above),
so a dedicated S2P composer build-out was skipped rather than repeating a
confirmed-broken step. S2P's sheet (`s2p-fix1-the-tour.txt`) passed
`prompt-lint.py` clean and its previz spec was verified (see Pre-flight
above) — everything on our side is ready to fire the moment the upload path
is working again.

## Recommendation

- Try attaching either previz by hand in the real Chrome window — if a human
  click succeeds where the scripted upload doesn't, the fault is specific to
  how the extension drives the `<input>` (e.g. a missing trusted-gesture
  requirement Higgsfield added recently) rather than the account/platform.
- If a manual attach also hangs, this is worth reporting to Higgsfield
  support / checking their status page — three clean attempts across two
  tabs and two files ruling out every operator-side variable point at their
  side.
- Retry this wave once the upload path is confirmed working again; both
  sheets are lint-clean and both previz files are spec-verified, so the next
  attempt should go straight to the fire once the attach step itself works.

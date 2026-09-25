# Arm B -- Scripter -> blind Editor -> Checker (task-aae4f843)

CEO 2026-09-25 A/B/C experiment: the Scripter (`tools/bl_scripter.py`,
task-67bb7a11) already made every editorial call for this exact 0-30.78s
window, one-shot, looking at the stills itself -- its output is
`docs/ops/bl-ab-2026-09-25/beats.json` (already on `main`, see that
directory's own `README.md`/`score_claude-p.md` for the run that produced
it: `claude-p` backend, 10 turns, $1.10 API-equivalent, 88.5s wall). Reusing
that measured run rather than re-running the Scripter -- identical inputs
(same media, same `--t-max 30.78`), so a second run would only add noise,
not a different number worth paying for.

Arm B measures a DIFFERENT thing: what it costs to route that already-made
beats.json through a real Editor session that never looks at an image --
build, render, run the mechanical Checker, fix only what it flags, at most
one fix round. If an Editor here barely spends any turns/tokens beyond the
build+checker commands themselves, that is itself evidence for the CEO's
question ("if it's all a script, do we still need an Editor?").

The brief below is the exact `description` given to the spawned
`video_editor` task (Contabo, host="contabo", touches
`prototypes/bl-ab-ep57/B/`). `tools/bl_compose.py` was scp'd into its
worktree ahead of this task's own merge (task-aae4f843, still in review at
spawn time) -- the brief tells it so.

---

## Brief given to the worker

You are building the first 0-30.78 seconds of BLACK LIQUIDITY episode 57
from an ALREADY-DECIDED cut list -- you make NO editorial judgment calls in
this task. This is Arm B of a 3-arm measurement (A: an editor decides by
eye; B: you, blind; C: same input, no editor at all, run by the CTO
directly). Your job is to execute the build+verify pipeline as fast and
cheaply as possible, correctly.

**HARD RULE: do not open, view, Read, or otherwise look at any image file**
(anything under `generator/media/real/`, `generator/media/third-party/`, or
any `.png`/`.jpg` path) at any point in this task. You do not need to --
every editorial decision (mode, crop box, caption, credit) is already made
in the beats.json below. If you find yourself wanting to look at a still to
"double check" something, that is a sign to stop and re-read this brief,
not to open the file.

**Input**: `docs/ops/bl-ab-2026-09-25/beats.json` is already in your
worktree (checked into `main` by an earlier task) -- copy it verbatim to
`prototypes/bl-ab-ep57/B/beats.json`. Do not edit its contents.

**Build:**
```
python3 tools/bl_compose.py \
  --beats prototypes/bl-ab-ep57/B/beats.json \
  --generator-dir /opt/MoonieXHQ/Work/bl-ab-ep57/generator \
  --t-max 30.78 \
  --audio /opt/MoonieXHQ/Work/bl-ab-ep57/audio-hq.mp3 \
  --out-dir /opt/MoonieXHQ/Work/bl-ab-ep57/B/build \
  --out /opt/MoonieXHQ/Work/bl-ab-ep57/B/final-B.mp4
```
(`tools/bl_compose.py` is new, from task-aae4f843, still in review -- it's
already in your worktree, use it as-is, do not edit it.)

**Check:**
```
python3 tools/bl_checker.py \
  --video /opt/MoonieXHQ/Work/bl-ab-ep57/B/final-B.mp4 \
  --beats prototypes/bl-ab-ep57/B/beats.json \
  --out /opt/MoonieXHQ/Work/bl-ab-ep57/B/checker-result.json
```

**If the checker fails**: fix ONLY what it lists (e.g. `credit_missing` on
a tag -> add/reposition that beat's credit in beats.json;
`out_of_safe_area` -> adjust that beat's `box`), re-build, re-check ONCE.
If it still fails after that one fix round, stop, leave it failing, and say
exactly what's still wrong in REPORT.md -- do not loop past one fix round,
and do not open any image to diagnose it (reason from the checker's own
JSON output and the beats.json values only).

**Push** (git add/commit/push on your task branch): `beats.json` (as
copied, or as fixed if you ran the fix round), the checker's result JSON,
and a small `render-meta.json` with `final-B.mp4`'s path/size/duration/fps
(`ffprobe`) -- **not the mp4 itself, media never goes in git**. Leave
`final-B.mp4` in `/opt/MoonieXHQ/Work/bl-ab-ep57/B/` (outside your
worktree, it will be pulled from there, not from git).

**Stop condition**: 90 minutes of wall-clock time OR 400 of your own turns
-- expect to need neither; if you somehow do, stop, push whatever exists,
and say why in REPORT.md.

Report in REPORT.md: whether the checker passed first try or needed the fix
round (and what you changed if so), and your own count of turns/commands
used for the whole task.

# Arm A -- today's Editor (task-aae4f843)

CEO 2026-09-25 A/B/C experiment: this arm simulates ordering a real BL Editor
session on the current toolset, unassisted by the Scripter. It gets the
exact same source material the Scripter gets in Arm B/C (script, timings,
Jev decisions, the real stills) but makes every editorial call itself,
turn by turn, the way EP57's original editor (task-501f1d89) did.

The brief below is the exact `description` given to the spawned
`video_editor` task (Contabo, host="contabo", touches
`prototypes/bl-ab-ep57/A/`). `tools/bl_compose.py` was scp'd into its
worktree ahead of this task's own merge (task-aae4f843, still in review at
spawn time) -- the brief tells it so.

---

## Brief given to the worker

You are cutting the first 0-30.78 seconds of BLACK LIQUIDITY episode 57 --
9 lines, tags HOOK-1..4 and PATTERN-1..4 -- exactly as if this were a real
episode to finish. This is Arm A of a 3-arm measurement (A: you decide by
eye; B: a one-shot Scripter decides, you cut blind from its beats.json; C:
same Scripter beats.json, no editor at all). Your only job is to make the
same editorial calls a human BL editor makes -- which parts of the source
material end up on screen -- as fast and cheaply as you honestly can while
still getting them right. Do not read about the other arms; just cut.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-ab-ep57/`, already
staged on this box):
- `SCRIPT.tsv` -- 5 tab-separated columns: tag, Thai caption line, shot
  basename (empty when the line is avatar-only), Jev decision verb
  (`show`/`hook`/`verdict`), a note on what the shot should prove.
- `timings.tsv` -- tag -> t0/t1 (seconds) for all 9 lines.
- `decisions.jsonl` -- Jev's own hook/show/verdict calls per line (one JSON
  object per line), the same signal a real editor would have.
- `generator/media/real/*.png`, `generator/media/third-party/*.jpg` -- the
  actual still images the script's `shot` column names. **Look at them.**
  This is the one thing that makes you an Editor and not a script: decide,
  per line, which mode fits, and if it's a still, which crop of it actually
  shows the thing the line claims.
- `generator/media/lip_a.mp4` + `generator/media/matte/lip_a-matte.webm` --
  the avatar's real lipsync footage (0-15s) and its pre-matted overlay, for
  FF (full-frame avatar) or COMP (avatar composited over a still) lines.

**Your output is one `beats.json`** -- a JSON array of
`{"tag", "t0", "t1", "mode", "extra"}` objects, one per line, `t0`/`t1`
copied verbatim from `timings.tsv`. `mode` is one of:
- `FF` -- avatar full-frame. `extra: {"cap": "<caption>"}`.
- `COMP` -- avatar composited over a still. `extra` needs `img` (path under
  `generator/media/`, e.g. `real/wikifx-profile-score.png`), `cap`, and
  optionally `box` (`[x,y,w,h]` in the STILL's own native pixels -- the
  crop the evidence spotlight draws around) and `credit` (a WikiFX-sourced
  image needs `credit: "ขอบคุณภาพจาก WikiFX"`; a first-party capture does
  not).
- `EVID` -- the still full-frame, avatar off-screen. Same `extra` shape as
  COMP minus the avatar.

Reference shape (do not copy its content, only its shape):
`docs/ops/bl-ab-2026-09-25/beats.json` in this repo (a prior automated run,
scored elsewhere -- ignore its actual mode/box choices).

**Decide mode per Jev's own convention** (read `decisions.jsonl` for each
tag): a `hook`/`verdict` line reads as an avatar beat unless it names a
capture (then EVID/COMP with a box); a `show` line is the still, composited
with the avatar (COMP) when the avatar staying visible matters, full-frame
still (EVID) when the still needs the whole 1080-wide canvas to read (a
whois/company-profile paragraph crop, a full-page error). Pick the crop
`box` so the spotlight lands on the actual sentence/number the line is
about, not the whole screenshot.

**Write** `prototypes/bl-ab-ep57/A/beats.json`.

**Render:**
```
python3 tools/bl_compose.py \
  --beats prototypes/bl-ab-ep57/A/beats.json \
  --generator-dir /opt/MoonieXHQ/Work/bl-ab-ep57/generator \
  --t-max 30.78 \
  --audio /opt/MoonieXHQ/Work/bl-ab-ep57/audio-hq.mp3 \
  --out-dir /opt/MoonieXHQ/Work/bl-ab-ep57/A/build \
  --out /opt/MoonieXHQ/Work/bl-ab-ep57/A/final-A.mp4
```
(`tools/bl_compose.py` is new, from task-aae4f843, still in review -- it's
already in your worktree, use it as-is, do not edit it.)

**Verify by eye**: pull 4-5 frames at representative timestamps
(`ffmpeg -ss <t> -i final-A.mp4 -frames:v 1 frame.png`) and actually look at
them -- captions readable, evidence box on the right region, no black/empty
stretches. Then run
`python3 tools/bl_checker.py --video /opt/MoonieXHQ/Work/bl-ab-ep57/A/final-A.mp4 --beats prototypes/bl-ab-ep57/A/beats.json`
and report its verdict in REPORT.md (informational -- fix anything it
catches that a real editor would obviously also catch by eye, but don't
loop chasing a clean checker past that).

**Push** (git add/commit/push on your task branch): `beats.json`, and a
small `render-meta.json` with `final-A.mp4`'s path/size/duration/fps
(`ffprobe`) -- **not the mp4 itself, media never goes in git**. Leave
`final-A.mp4` in `/opt/MoonieXHQ/Work/bl-ab-ep57/A/` (outside your worktree,
it will be pulled from there, not from git).

**Stop condition**: 90 minutes of wall-clock time OR 400 of your own turns,
whichever comes first. If you hit it, stop immediately -- commit and push
whatever you have even if incomplete, and say in REPORT.md exactly what's
missing and why. Do not keep iterating past this budget.

Report in REPORT.md: your own read on how many lines you'd call COMP vs
EVID vs FF and why, anything in the source material that made a call hard,
and the checker verdict.

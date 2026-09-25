# Brief -- Arm 1 (ต่อเนื่อง, one editor, whole episode) -- task-99f3d2e8

CTO ruling 2026-09-25 (docs/ops/bl-split-ab-2026-09-25/PLAN.md): both arms
of the split-editor A/B now use Arm A's own route
(`docs/ops/bl-ab-2026-09-25/arms/A/README.md`) -- the editor decides every
beat by looking at the real stills, writes one `beats.json`, and
`tools/bl_compose.py` composes + renders it, `tools/bl_checker.py` gates
it. The CEO watched task-aae4f843's three 30s Arm clips and ruled "A
Editor ดีที่สุด": that route cost $3.73 for 30s; the hand-written-HTML
route (`blackliquidity-cut`'s normal step-by-step pipeline, no beats.json)
cost $99.79 for the same episode (EP57). This brief is that route, plus
the Jev loop the CEO asked to run alongside it ("ทำงานร่วมกับการ Training
Jev ไปในตัว").

`tools/bl_ab_run.py spawn-full` prints this brief verbatim (dry run --
never spawns). `BRIEF-seg.md` is the same brief adapted to one segment at
a time (Arm 2); the two are word-for-word identical outside the range
description and the segment contract, so the A/B isolates the split, not
the brief.

---

## Brief given to the worker

You are cutting the WHOLE BLACK LIQUIDITY episode 57 -- seconds 0.0 to
153.0333 (all 40 lines, tags HOOK-1..4 through SUMMARY-1..9) -- exactly as
if this were a real episode to finish. Your only job is to make the same
editorial calls a human BL editor makes -- which parts of the source
material end up on screen -- as fast and cheaply as you honestly can while
still getting them right.

**Source material** (all under `/opt/MoonieXHQ/Work/bl-split-ep57/generator`,
already staged on this box -- if the media there is still the pre-splice
voice rather than the "โบร๊ก" re-voice, say so in REPORT.md and cut against
what is actually there; the timings do not change between versions):
- `SCRIPT.tsv` -- 5 tab-separated columns: tag, Thai caption line, shot
  basename (empty when the line is avatar-only), Jev decision verb
  (`show`/`hook`/`verdict`), a note on what the shot should prove -- for
  all 40 lines.
- `timings.tsv` -- tag -> t0/t1 (seconds) for all 40 lines.
- `media/real/*`, `media/third-party/*`, `media/broll/*.mp4` -- every
  real-footage still, third-party credit image and B-roll clip the
  episode uses. **Look at them.** This is the one thing that makes you an
  Editor and not a script: decide, per line, which mode fits, and if it's
  a still, which crop of it actually shows the thing the line claims.
- `media/lip_a.mp4`, `lip_b.mp4`, `lip_c.mp4` + `media/matte/*-matte.webm`
  -- the avatar's real lipsync footage and its pre-matted overlay. If a
  line's window needs a matte that is missing from this fixture
  (`fixture-full` prints a WARNING naming which), say so in REPORT.md
  rather than falling back to full-frame avatar just because the matte
  isn't there.
- **FF/COMP avatar windows -- outside these, `bl_compose.py` refuses.**
  The 3 recorded lipsync takes only cover 3 narrow spans of the
  153.0333s episode: `lip_a` only for a beat whose `t0` falls in
  **[0, 14.9)**, `lip_b` only for **[68.3, 82.95)**, `lip_c` only for
  **[137.16, 152.51)**. An FF or COMP beat whose `t0` falls outside all
  three has no matching avatar footage -- `bl_compose.py` now refuses it
  before rendering (naming the beat and the three valid windows) instead
  of burning a render on it. Plan FF/COMP beats to land inside a window;
  everywhere else, use EVID (a still, avatar off-screen) or KIN (kinetic
  text, optionally over a darkened B-roll plate) instead.
- `index.html` -- the FIXED template (task-1678d38e): one
  `caption(at, out, text)` generator, no per-mode chip/rail/strip, plates
  hold until the next plate starts. `tools/bl_compose.py` builds from this
  template as-is -- you never hand-edit it.

## The Jev loop (CEO: "ทำงานร่วมกับการ Training Jev ไปในตัว")

Before you decide any line, run Jev on your own lines and freeze its
answer, per the `VIDEO_EDITOR_jev-editor-helper` skill's own SKILL.md:

```bash
python3 .claude/skills/VIDEO_EDITOR_jev-editor-helper/scripts/jev_edit.py plan \
  /opt/MoonieXHQ/Work/bl-split-ep57/generator/SCRIPT.tsv \
  --state-lang th --out decisions.jsonl
  # add --manifest /opt/MoonieXHQ/Work/bl-split-ep57/generator/real/REAL_MANIFEST.json
  # only if that file actually exists in the fixture -- it does not as of
  # this brief, so bl.focus_target will come back skipped/flagged; decide
  # those crops by eye same as you always would.
python3 .claude/skills/VIDEO_EDITOR_jev-editor-helper/scripts/jev_edit.py freeze decisions.jsonl
```

Then make your own editorial calls exactly as you would without Jev. Per
the skill's own "who decides" table, only `bl.beat` at `--state-lang th`
with confidence >= 0.95 has a measured safe gate -- every other site's
`decisions.jsonl` row is a hint only, never something you apply
automatically. **Record your own call for every question on every line**
(not just the ones Jev flagged), so the scoreboard can compare Jev against
you:

```bash
python3 .claude/skills/VIDEO_EDITOR_jev-editor-helper/scripts/jev_edit.py final \
  decisions.jsonl <line_id> <question> <your_choice>
# bulk form, once you have every line's calls:
#   --tsv <line_id>\t<question>\t<choice> per row
```

Push `decisions.jsonl` (every row's `final` filled in) alongside
`beats.json` -- the CTO runs `jev_edit.py score` against it afterward to
build the scoreboard.

## Captions: SCRIPT.tsv's spelling, never the TTS spelling

`SCRIPT.tsv`'s Thai text spells the broker's name **โบรก**. The re-voiced
audio (once the CTO has replaced `audio-hq.mp3` with the re-voice) says
**โบร๊ก** -- a tone-mark variant from the TTS voice, not a spelling change
to the script. Every `cap` you write in `beats.json` copies `SCRIPT.tsv`'s
own spelling (**โบรก**) verbatim -- never transcribe what you hear in the
audio.

**Your output is one `beats.json`** -- a JSON array of
`{"tag", "t0", "t1", "mode", "extra"}` objects, one per line, `t0`/`t1`
copied verbatim from `timings.tsv`. `mode` is one of:
- `FF` -- avatar full-frame. `extra: {"cap": "<caption>"}`.
- `COMP` -- avatar composited over a still. `extra` needs `img` (path
  under `generator/media/`, e.g. `real/wikifx-profile-score.png`), `cap`,
  and optionally `box` (`[x,y,w,h]` in the STILL's own native pixels --
  the crop the evidence spotlight draws around) and `credit` (a
  WikiFX-sourced image needs `credit: "ขอบคุณภาพจาก WikiFX"`; a
  first-party capture does not).
- `EVID` -- the still full-frame, avatar off-screen. Same `extra` shape as
  COMP minus the avatar.
- `KIN` -- kinetic text takeover, optionally over a darkened B-roll plate
  (`extra: {"broll": "<path under media/>", "lines": [["<css-class>",
  "<text>"], ...]}`). No `cap` -- the kinetic text IS the on-screen copy.

Reference shape (do not copy its content, only its shape):
`docs/ops/bl-ab-2026-09-25/beats.json` in this repo (a prior automated
run, scored elsewhere -- ignore its actual mode/box choices).

**Decide mode per Jev's own convention** (read your `decisions.jsonl` for
each tag, but you make the call): a `hook`/`verdict` line reads as an
avatar beat unless it names a capture (then EVID/COMP with a box); a
`show` line is the still, composited with the avatar (COMP) when the
avatar staying visible matters, full-frame still (EVID) when the still
needs the whole 1080-wide canvas to read (a whois/company-profile
paragraph crop, a full-page error). Pick the crop `box` so the spotlight
lands on the actual sentence/number the line is about, not the whole
screenshot.

**Write** `prototypes/bl-split-ep57/arm1/beats.json`.

**Render** (the whole episode, one call, video+audio muxed):
```
python3 tools/bl_compose.py \
  --beats prototypes/bl-split-ep57/arm1/beats.json \
  --generator-dir /opt/MoonieXHQ/Work/bl-split-ep57/generator \
  --t-max 153.0333 \
  --audio /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3 \
  --out-dir /opt/MoonieXHQ/Work/bl-split-ep57/arm1/build \
  --out /opt/MoonieXHQ/Work/bl-split-ep57/arm1/final-arm1.mp4
```

**Verify by eye**: pull 6-8 frames at representative timestamps spread
across the whole episode (`ffmpeg -ss <t> -i final-arm1.mp4 -frames:v 1
frame.png`) and actually look at them -- captions readable and in the one
approved band (never a per-mode chip/rail), evidence box on the right
region, nothing goes empty during a pause. Then run
`python3 tools/bl_checker.py --video /opt/MoonieXHQ/Work/bl-split-ep57/arm1/final-arm1.mp4 --beats prototypes/bl-split-ep57/arm1/beats.json --composition /opt/MoonieXHQ/Work/bl-split-ep57/arm1/build/index.html`
and report its verdict in REPORT.md (informational -- fix anything it
catches that a real editor would obviously also catch by eye, but don't
loop chasing a clean checker past that).

**Push** (git add/commit/push on your task branch): `beats.json`,
`decisions.jsonl`, and a small `render-meta.json` with `final-arm1.mp4`'s
path/size/duration/fps (`ffprobe`) -- **not the mp4 itself, media never
goes in git.** Leave `final-arm1.mp4` in
`/opt/MoonieXHQ/Work/bl-split-ep57/arm1/` (outside your worktree -- it
will be pulled from there, not from git).

Report in REPORT.md: your own read on how many lines you'd call COMP vs
EVID vs FF vs KIN and why, anything in the source material that made a
call hard, how many `final` calls agreed vs disagreed with Jev's own
answer, and the checker verdict.

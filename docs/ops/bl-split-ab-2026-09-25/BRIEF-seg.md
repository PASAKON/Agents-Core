# Brief -- Arm 2 (ช่วยกัน, N editors, one segment each) -- task-99f3d2e8

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

This is a **template**: `{seg}`/`{t0}`/`{t1}`/`{tags}` are filled in per
segment by `tools/bl_ab_run.py spawn-seg --segments segments.json --seg
segNN` (dry run -- never spawns). `BRIEF-arm1.md` is the same brief for
the whole episode in one pass (Arm 1); the two are word-for-word identical
outside the range description and this file's own "Segment contract"
section, so the A/B isolates the split, not the brief.

---

## Brief given to the worker

You are cutting BLACK LIQUIDITY episode 57, segment `{seg}` -- seconds
{t0} to {t1} (tags {tags}) -- exactly as if this were a real episode to
finish. This is Arm 2 ("ช่วยกัน") of the split-editor A/B: N editors each
cut one segment in parallel from the SAME fixed skill + template, and the
CTO concats/merges the parts afterward with `tools/bl_merge.py` -- you
never see or touch any other segment. Your only job is to make the same
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

## Segment contract (what makes your part join invisibly to the others)

PLAN.md §"Segment contract" -- this is what makes your part concat
cleanly with every other segment via `tools/bl_merge.py`:
- Your segment's `beats.json` covers ONLY the lines inside [{t0}, {t1})
  -- do not include lines from outside your window. `tools/bl_compose.py`
  renders your window starting at composition-local t=0 (via its own
  `--t0`); a plate must be on screen every frame of it. The LAST plate in
  your window holds all the way to {t1} -- do not let it end early just
  because its own spoken line ends before {t1}; the same "hold until the
  next plate" rule applies at your segment's own edges too. No fade in or
  out at either edge -- it has to cut hard into whatever comes before/
  after your segment.
- Same template, same caption style (`caption()`, never a hand-rolled
  style or a mode-based chip/rail -- that is the exact bug this fix
  exists to prevent), same encoder settings (1080x1920, 30fps) as every
  other segment -- `tools/bl_compose.py --t0/--t1` already guarantees
  this (frame-exact, video-only, fixed encoder), so every segment concats
  with `ffmpeg -c copy`, no re-encode.
- **Your render is VIDEO ONLY -- no audio track.** `tools/bl_compose.py`
  drops audio automatically whenever `--t0` > 0; the master narration
  audio is muxed once, across the WHOLE episode, by the CTO's
  `tools/bl_merge.py` at merge time.
- Before you render, take the render lock so your render never overlaps
  another segment editor's on this 4-core/7GB box:
  `flock /tmp/bl-render.lock python3 tools/bl_compose.py ...` (the full
  command is below). Hold the SAME lock for `hyperframes check`/
  `hyperframes snapshot` too if you run them concurrently with another
  segment's render -- the lock, not a schedule, is what keeps renders
  serialized.

**Write** your composition's beats to
`prototypes/bl-split-ep57/{seg}/beats.json`.

**Render** (video-only, [{t0}, {t1}), frame-exact):
```
flock /tmp/bl-render.lock python3 tools/bl_compose.py \
  --beats prototypes/bl-split-ep57/{seg}/beats.json \
  --generator-dir /opt/MoonieXHQ/Work/bl-split-ep57/generator \
  --t0 {t0} --t-max {t1} \
  --out-dir /opt/MoonieXHQ/Work/bl-split-ep57/{seg}/build \
  --out /opt/MoonieXHQ/Work/bl-split-ep57/{seg}/{seg}.mp4
```

**Verify by eye**: pull frames at a few representative timestamps inside
[{t0}, {t1}) and actually look at them -- caption readable and in the one
approved style, no empty/black frames, nothing on screen ends before the
NEXT plate in your window starts. Then run
`python3 tools/bl_checker.py --video /opt/MoonieXHQ/Work/bl-split-ep57/{seg}/{seg}.mp4 --beats prototypes/bl-split-ep57/{seg}/beats.json --composition /opt/MoonieXHQ/Work/bl-split-ep57/{seg}/build/index.html`
and report its verdict.

**Push** (git add/commit/push on your task branch): `beats.json`,
`decisions.jsonl` (your window's lines only), and a small
`render-meta.json` (path/size/duration/fps via `ffprobe`) -- **not the mp4
itself, media never goes in git.** Copy `{seg}.mp4` to
`/opt/MoonieXHQ/Work/bl-split-ep57/parts/{seg}.mp4` and your composed
`index.html` (from `.../build/index.html`) to
`/opt/MoonieXHQ/Work/bl-split-ep57/compositions/{seg}.html` (outside your
worktree -- `merge_task` deletes it, and `tools/bl_merge.py --parts
.../parts --compositions .../compositions` reads directly from there).

Report in REPORT.md: your own read on how many lines you'd call COMP vs
EVID vs FF vs KIN and why, anything in the source material that made a
call hard, how many `final` calls agreed vs disagreed with Jev's own
answer, whether your window's first/last plate lands exactly on {t0}/{t1}
with no fade, and the checker verdict.

# BL split-by-dead-air A/B — tooling (task-1678d38e, updated task-99f3d2e8)

Builds steps 0 and 1 of `PLAN.md`: the fixed kit both arms start from, plus
`tools/bl_split.py`, `tools/bl_merge.py`, and `tools/bl_ab_run.py`'s
`fixture-full`/`spawn-full`/`spawn-seg`. **Neither task cuts EP57 or spawns
any editor** — everything below is either a dry run (`spawn-full`/`spawn-seg`
only ever print a brief) or a real, already-run `tools/bl_split.py` plan for
EP57. PLAN.md's own "Order of work" steps 2-4 (run Arm 1, run Arm 2, CTO
merges, report to the CEO) are separate, future work.

**task-99f3d2e8 changes** (CTO routing decision, CEO 2026-09-25 "A Editor
ดีที่สุด" after watching task-aae4f843's three 30s clips):
- Both arms now route through Arm A's own `tools/bl_compose.py`/`beats.json`
  workflow (was: the raw `blackliquidity-cut` skill pipeline, hand-editing
  HTML) — $3.73/30s measured vs $99.79 for EP57 the old way. The brief text
  is `BRIEF-arm1.md`/`BRIEF-seg.md` (below), not embedded in this file
  anymore — `spawn-full`/`spawn-seg` print them.
- `tools/bl_split.py` gained `--min-seg` (default 20.0s): a final segment
  shorter than that merges into the one before it. EP57's plan is now
  **4 segments**, not 5 — see the regenerated plan below.
- `tools/bl_compose.py` gained `--t0`/`--t1` range render (video-only,
  frame-exact, fixed encoder) so a segment editor renders ONLY its own
  window instead of the whole episode up to that point, and its captions
  now always call the template's one `caption()` generator (no `addCap`
  kind), and its plates hold for their full computed duration regardless
  of the underlying media's own length (SKILL.md §6g, by construction).

## Step 0 recap — what changed before either arm can run

- `.claude/skills/blackliquidity-cut/template/index.html`: one `caption(at,
  out, text)` generator, EP55's approved `.cap` band baked in as the only
  caption look, in every mode (§6f). §6d's old per-mode chip rule is marked
  `[SUPERSEDED 2026-09-25]`.
- SKILL.md §6g: a plate's end is the next plate's start (promoted from the
  2026-09-24 field note) — nothing may go empty during a TTS pause.
- `tools/bl_checker.py`: `detect_empty_frames` now samples at 30fps with a
  single-frame mean-dip check (the old 4fps grid missed EP57's 76.37s
  one-frame black flash); a new one-caption-style-per-composition gate.

Both arms' editors must use the template and skill AFTER these fixes — that
is the whole point of the A/B (PLAN.md: "both arms must start from it").

## Commands in order

### Arm 1 — ต่อเนื่อง (one editor, the whole episode)

```bash
# 1. stage the full-episode fixture (once, shared by Arm 1 and every Arm 2 segment)
python3 tools/bl_ab_run.py fixture-full
#   -> /opt/MoonieXHQ/Work/bl-split-ep57/generator (default --dest)
#   WARNING printed if any lip_[abc]-matte.webm is missing -- true for lip_c
#   on this box today (media/matte/ only has lip_a and lip_b, see below).

# 2. print the brief (dry run -- never spawns; the full text is BRIEF-arm1.md)
python3 tools/bl_ab_run.py spawn-full

# 3. CTO spawns ONE video_editor task with that brief (out of scope here) --
#    the editor writes beats.json and composes/renders with
#    tools/bl_compose.py per BRIEF-arm1.md, delivers final-arm1.mp4.
```

### Arm 2 — ช่วยกัน (N editors, one segment each, CTO merges)

```bash
# 1. same fixture-full as Arm 1 (idempotent, safe to re-run)
python3 tools/bl_ab_run.py fixture-full

# 2. the dead-air split (already run for real -- see segments.json below;
#    --min-seg 20 is now the default, merging any final segment under 20s
#    into the one before it -- EP57 is 4 segments, not 5)
python3 tools/bl_split.py /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3 \
  --script /opt/MoonieXHQ/Work/bl-split-ep57/SCRIPT.tsv \
  --timings /opt/MoonieXHQ/Work/bl-split-ep57/timings.tsv \
  --blocks docs/ops/bl-split-ab-2026-09-25/ep57-blocks.json \
  -o docs/ops/bl-split-ab-2026-09-25/segments.json

# 3. one brief per segment (dry run only -- prints, never spawns; the
#    template is BRIEF-seg.md, filled in per segment -- see the example below)
python3 tools/bl_ab_run.py spawn-seg \
  --segments docs/ops/bl-split-ab-2026-09-25/segments.json --seg seg01

# 4. CTO spawns N video_editor tasks with those briefs (out of scope here).
#    Each editor writes beats.json and renders ONLY its own window with
#    tools/bl_compose.py's range render (--t0/--t1, video-only, frame-exact,
#    fixed encoder), inside the render lock:
#      flock /tmp/bl-render.lock python3 tools/bl_compose.py \
#        --beats beats.json --generator-dir <fixture>/generator \
#        --t0 <seg t0> --t-max <seg t1> --out-dir <workdir> --out segNN.mp4
#    and copies its output to:
#      /opt/MoonieXHQ/Work/bl-split-ep57/parts/<id>.mp4
#      /opt/MoonieXHQ/Work/bl-split-ep57/compositions/<id>.html (the
#      composed <workdir>/index.html, for bl_merge.py's caption-style gate)

# 5. CTO merges once every part has landed
python3 tools/bl_merge.py docs/ops/bl-split-ab-2026-09-25/segments.json \
  --parts /opt/MoonieXHQ/Work/bl-split-ep57/parts \
  --compositions /opt/MoonieXHQ/Work/bl-split-ep57/compositions \
  --audio /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3 \
  -o /opt/MoonieXHQ/Work/bl-split-ep57/final-arm2.mp4
# exits non-zero and names every failed gate (frame_count / empty_frames /
# seam_failures / audio_offset / extra_caption_styles) -- refuses to ship
# on any failure, per PLAN.md's merge gates.
```

**Known gap on this box today**: `media/matte/` under
`/opt/MoonieXHQ/Work/bl-split-ep57/` has `lip_a-matte.webm` and
`lip_b-matte.webm` but no `lip_c-matte.webm` — `fixture-full` prints a
WARNING about this. Any segment whose window needs a COMPOSITE (avatar +
evidence) beat inside `lip_c`'s range (roughly t≥120s, i.e. inside seg04,
the merged tail segment after task-99f3d2e8's `--min-seg`) needs a fresh
`bl_tools.py matte` run on `lip_c.mp4` before that beat can render; a plain
full-frame avatar beat in that range is unaffected.

## EP57 segment plan (regenerated task-99f3d2e8, `--min-seg 20` default)

`docs/ops/bl-split-ab-2026-09-25/segments.json`, built from the REAL episode
audio (`/opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3`, measured duration
153.0514s — PLAN.md's own worked numbers round this to 153.0s) and the real
`SCRIPT.tsv`/`timings.tsv`, with `ep57-blocks.json` (this dir) as the one
forbidden span (the SUMMARY-4..6 checklist card, 129.38-141.48s). The walk
itself produces the same 4 interior candidate cuts task-1678d38e found
(`[39.3, 65.83, 104.53, 145.9]`); `enforce_min_tail` then drops the last one
(145.9), since it leaves only a 7.13s tail, well under the 20s default —
merging what used to be seg04/seg05 into one 48.5s segment:

```
audio: /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3  total_duration=153.0514s  pauses_detected=55  candidates(>=0.45s)=33
cuts (frame-floored, s): [39.3, 65.83333333333333, 104.53333333333333]
N segments = 4
  seg01  t0=  0.000  t1= 39.300  dur=39.300s  frames=1179   tags: HOOK-1, HOOK-2, HOOK-3, HOOK-4, PATTERN-1, PATTERN-2, PATTERN-3, PATTERN-4, CONTEXT-1, CONTEXT-2
  seg02  t0= 39.300  t1= 65.833  dur=26.533s  frames=796    tags: CONTEXT-3, CONTEXT-4, CONTEXT-5, MAIN-1, MAIN-2, MAIN-3
  seg03  t0= 65.833  t1=104.533  dur=38.700s  frames=1161   tags: MAIN-4, MAIN-5, MAIN-6, MAIN-7, MAIN-8, MAIN-9, MAIN-10, MAIN-11, MAIN-12, MAIN-13, CURIOSITY-1, CURIOSITY-2
  seg04  t0=104.533  t1=153.033  dur=48.500s  frames=1455   tags: CURIOSITY-3, CURIOSITY-4, CURIOSITY-5, SUMMARY-1, SUMMARY-2, SUMMARY-3, SUMMARY-4, SUMMARY-5, SUMMARY-6, SUMMARY-7, SUMMARY-8, SUMMARY-9
wrote docs/ops/bl-split-ab-2026-09-25/segments.json
```

(The `candidates(>=0.45s)` count printed above — 33 — differs from
task-1678d38e's originally-documented 37 for reasons unrelated to this
task's own change: same 55 raw pauses, same cut points either way. Not
chased further here; it does not affect the cuts or the segment plan.)

4 segments — inside PLAN.md's own "EP57 estimate 3-5" for Arm 2's N. No cut
falls inside the forbidden checklist-card span (checked: none of
[39.3, 65.83, 104.53] land in [129.38, 141.48]).

## Arm 1 / Arm 2 — brief text (task-99f3d2e8: routed through bl_compose.py)

The brief text used to live inline here, one full copy per segment (the
old raw-HTML `blackliquidity-cut` pipeline brief). Since the CTO's routing
decision (both arms now use Arm A's own `bl_compose.py`/`beats.json`
route — see this file's header), the brief lives in two checked-in files
instead of being generated fresh into this doc, so there is exactly one
copy of the editorial content to keep in sync:

- `docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md` — Arm 1's full brief
  (the whole episode, one editor). `tools/bl_ab_run.py spawn-full` prints
  it verbatim (dry run, never spawns).
- `docs/ops/bl-split-ab-2026-09-25/BRIEF-seg.md` — Arm 2's brief, as a
  template (`{seg}`/`{t0}`/`{t1}`/`{tags}`). `tools/bl_ab_run.py spawn-seg
  --segments segments.json --seg segNN` fills it in and prints it (dry
  run, never spawns). Word-for-word identical to `BRIEF-arm1.md` outside
  the range description and its own "Segment contract" section, so the
  A/B isolates the split, not the brief.

Both briefs also carry the Jev loop (`jev_edit.py plan`/`freeze`/`final`,
per the `VIDEO_EDITOR_jev-editor-helper` skill — the CEO's "ทำงานร่วมกับการ
Training Jev ไปในตัว") and the caption-spelling rule (`SCRIPT.tsv` says
โบรก; the re-voiced audio says โบร๊ก; captions always use the script's own
spelling).

### Example: `spawn-seg` for seg02

```
$ python3 tools/bl_ab_run.py spawn-seg \
    --segments docs/ops/bl-split-ab-2026-09-25/segments.json --seg seg02
```

prints `BRIEF-seg.md` with `{seg}` → `seg02`, `{t0}` → `39.3`, `{t1}` →
`65.8333`, `{tags}` → `CONTEXT-3, CONTEXT-4, CONTEXT-5, MAIN-1, MAIN-2,
MAIN-3` substituted throughout — including inside the render command:

```
flock /tmp/bl-render.lock python3 tools/bl_compose.py \
  --beats prototypes/bl-split-ep57/seg02/beats.json \
  --generator-dir /opt/MoonieXHQ/Work/bl-split-ep57/generator \
  --t0 39.3 --t-max 65.8333 \
  --out-dir /opt/MoonieXHQ/Work/bl-split-ep57/seg02/build \
  --out /opt/MoonieXHQ/Work/bl-split-ep57/seg02/seg02.mp4
```

ending with `--- DRY RUN: brief generated for seg02 (39.3-65.8333s), NOT
spawned. Task rule: spawn-seg never calls delegate_task. ---`. Run it for
seg01/seg03/seg04 the same way to get every segment's own brief.

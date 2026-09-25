# RUNLOG task-99f3d2e8 — BL split-by-dead-air follow-up (min-seg, one caption style, plates hold, range render, briefs)

## 2026-09-25 setup

- Read `docs/ops/bl-split-ab-2026-09-25/PLAN.md`, `TOOLING.md`,
  `RUNLOG-task-1678d38e.md` — task-1678d38e's own RUNLOG — end to end.
- Read `docs/ops/bl-ab-2026-09-25/arms/A/README.md` (the Arm A brief this
  task's own briefs are built from) and `docs/ops/bl-ab-2026-09-25/
  arms/{B,C}/README.md`/`scores.md` for context on the earlier 3-arm
  experiment.
- Read `.claude/skills/VIDEO_EDITOR_jev-editor-helper/SKILL.md` end to end
  (the Jev loop's plan/freeze/final commands, the "who decides" gate table,
  the six sites, why `--state-lang th` is recommended over the CLI's `en`
  default) and `scripts/jev_edit.py`'s `cmd_freeze`/`cmd_final` to confirm
  exact CLI shape.
- Read `tools/bl_split.py`, `tools/bl_compose.py`, `tools/bl_merge.py`,
  `tools/bl_checker.py`, `tools/bl_ab_run.py` and their test files end to
  end (3281 lines across the five tools).
- Confirmed on-box fixture state: `/opt/MoonieXHQ/Work/bl-split-ep57/` has
  `SCRIPT.tsv`, `timings.tsv`, `audio-hq.mp3` (still the pre-splice v1
  voice — no "โบร๊ก" re-voice yet), `media/lip_{a,b,c}.mp4`,
  `media/matte/lip_{a,b}-matte.webm` (lip_c-matte still missing, same gap
  TOOLING.md already documented). No `generator/` dir staged yet (this
  task's own `fixture-full` run was not re-run — code changes were
  verified against the raw fixture files + synthetic test fixtures
  instead, same convention every prior task in this doc used).
- Confirmed `/opt/MoonieXHQ/Agents/Core/.venv` is the shared venv with
  pytest 8.4.2 + numpy 2.5.3 on this box — no pytest/numpy in the system
  Python. Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest`
  throughout.

## Item 1 — bl_split.py: no short tail

Added `MIN_SEG_TAIL = 20.0` + `enforce_min_tail(cuts, total_dur, min_seg,
fps)`: pops trailing cut points while the final segment's length stays
under `min_seg` (cascades past multiple cuts in the pathological case,
never below zero cuts). Wired into `split_episode()` (new `min_seg`
kwarg, default `MIN_SEG_TAIL`) and the CLI (`--min-seg`, default 20.0).
`segments.json`'s own top-level dict now also carries `min_seg_tail_s` for
provenance.

Regenerated `docs/ops/bl-split-ab-2026-09-25/segments.json` for real
against the on-box EP57 audio: same 4 interior candidate cuts task-1678d38e
found (`[39.3, 65.83, 104.53, 145.9]`), `enforce_min_tail` drops 145.9 (its
own tail was only 7.13s) → **4 segments**, last one 104.5333-153.0333
(48.5s), exactly matching the task brief's own worked example. Noted one
unrelated observation in TOOLING.md: the printed `candidates(>=0.45s)`
count is 33 this run vs 37 documented in task-1678d38e's own RUNLOG, for
the same 55 raw pauses and the same resulting cut points — not chased
further, doesn't touch this task's own logic (nothing in
`candidate_pauses`/`CANDIDATE_MIN_DUR`/`detect_pauses` was touched).

Tests: `tests/test_bl_split.py` — 6 new tests (`enforce_min_tail` direct:
drops-a-short-tail / keeps-a-long-tail / cascades-past-multiple-cuts /
no-cuts-is-a-noop / matches-the-PLAN-constant, plus one real-ffmpeg
end-to-end `split_episode()` test with two silences where the second
produces a too-short tail). Fixed one PRE-EXISTING test
(`test_main_writes_segments_json`) that the new `min_seg=20.0` default
regressed (its own synthetic ~45.6s clip produces a 15.3s tail, now merged
away by default) — added `--min-seg 0` to that test since it's testing CLI
plumbing, not the tail-merge feature (which has its own dedicated tests).

## Item 2 — bl_compose.py: one caption style

`emit_pieces()`'s FF/COMP/EVID branches now emit `caption(t0, t1, cap)`
(guarded by `ex.get("cap")` since KIN has none) instead of
`addCap(t0, t1, cap, "chip-ff"/"chip-comp"/"rail", y)`. Dropped COMP's
`cap_y` above/below-the-box positioning math entirely — the new
`caption()` generator has no position parameter, it always renders at the
template's one fixed band (SKILL.md §6f). Updated the module's own
docstring to say the `--generator-dir` must be the FIXED template
(task-1678d38e's `caption()`-only one), not a branch copy with the old
`addCap`.

Proof, per the task brief: `test_composed_html_covering_all_modes_passes_
one_caption_style_gate` composes a real 4-beat beats.json (FF + COMP +
EVID + KIN, one caption line each on the first three) via
`bc.compose()` against the synthetic generator fixture, then runs
`bl_checker.check_one_caption_style()`/`caption_style_signatures()` on the
resulting HTML — passes, signature is exactly `{"caption"}`.
`test_old_addcap_shaped_output_still_fails_the_same_gate` keeps the
task-1678d38e regression (the real old EP57 three-`addCap`-kind shape)
failing the same gate — this exact case already had its own test in
`tests/test_bl_checker.py` (`test_caption_style_signatures_flags_the_
ep57_three_kind_bug`, task-1678d38e); kept both, since bl_checker's own
test proves the GATE catches it and this new test proves
bl_compose.py's OWN code can no longer produce that shape at all (the
`addCap` call is gone from the source, not just untriggered).

## Item 3 — bl_compose.py: plates hold by construction

Removed the `clip_dur = min(dur, LIP_DUR[lipname]-media_start)` cap in FF
mode and the matching `avatar_dur = min(avatar_dur, LIP_DUR[lipname]-
media_start0)` cap in COMP mode — both now always emit `data-duration`
equal to the beat's own computed `dur` (hold until the next beat, per
`compute_ext_end()`), regardless of the underlying lip media's own
remaining length. `avatar_until` (an editor's deliberate early end for
the avatar overlay while the base plate keeps holding) is unaffected —
still computed from the beat's own numbers, just no longer additionally
capped by media length on top of that.

Tests: `test_emit_pieces_ff_plate_holds_past_short_lip_media` and
`test_emit_pieces_comp_avatar_holds_past_short_lip_media` use a second
synthetic generator fixture (`generator_dir_short_lip`, `LIP_DUR =
{"lip_a": 1.0}`) and confirm a 4.0s-until-next-beat plate still gets
`data-duration="4.0"`, not the old code's ~1.0s truncation.
`test_emit_pieces_comp_avatar_until_still_shortens_avatar_on_purpose`
confirms the legitimate `avatar_until` early-end still works, distinct
from the bug fix.

## Item 4 — bl_compose.py: range render

Two-part implementation, both needed for a segment editor to render ONLY
its own window rather than the whole episode up to that point:

1. `emit_pieces()`/`compute_ext_end()`/`compose()` gained `t0_window`
   (public name `t0` on `compose()`, default 0.0): shifts only
   COMPOSITION-PLACEMENT timestamps (`data-start`/`data-duration`,
   caption/spotlight/credit/kinetic call args) by `-t0_window`, so a
   segment's own composition starts at composition-local t=0 — but
   `pick_lip`/`lip_offset`/`media_start` keep using the beat's true
   ABSOLUTE time, because those seek into a media file whose own timeline
   never shifts. Beats before `t0_window` are excluded from the render
   entirely (same filter shape as the existing `t_max` upper bound).
   `total_dur` now derives from the WINDOW duration (`t_max - t0_window`),
   not `t_max` directly.
2. New `trim_range(video_path, dur, out_path, fps)`: a frame-exact,
   video-only, fixed-encoder (`libx264`/`yuv420p`/`crf 18`) normalization
   pass every range's own render goes through — `-frames:v
   round(frame_floor(dur)*fps)` caps the output to exactly the window's
   own frame count, `-an` drops audio (the segment contract: the master
   narration is muxed once at merge time), and the SAME encoder args on
   every call are what let `tools/bl_merge.py` concat parts with
   `ffmpeg -c copy`.

CLI: added `--t0` (default 0.0). `--t-max` doubles as `t1` (kept its
existing name rather than renaming — every existing call site, Arm A's own
README and `bl_ab_run.py`'s `run-c`, already passes `--t-max` and neither
needed to change). When `--t0 > 0`, `main()` composes/renders the shifted
window then runs it through `trim_range()`; `--audio` is ignored with a
stderr note in that case (range render is always video-only, per the
segment contract) — the `--t0 == 0.0` (default) path is byte-for-byte the
same code as before this task, so Arm A's own existing brief/run-c call
sites are unaffected.

Tests: `test_emit_pieces_t0_window_shifts_placement_not_media_seek` (data-
start shifts to 0, data-media-start stays absolute, caption timing shifts
too), `test_emit_pieces_t0_window_excludes_beats_before_the_window`,
`test_emit_pieces_total_dur_uses_window_duration_not_t_max`,
`test_compose_with_t0_window_writes_relative_placement_to_disk` (through
the real `compose()`/`assemble.py` splice, not just `emit_pieces()` in
isolation). `trim_range()` itself: real-ffmpeg synthetic fixtures (same
convention as `tests/test_bl_merge.py`) —
`test_trim_range_two_adjacent_ranges_concat_to_same_frame_count_as_the_
union` is the task brief's own test criterion verbatim (two 5s ranges
trimmed from a 10s source, concatenated `-c copy`, frame count equals a
direct 10s trim of the same source: 150+150=300, matches
`enforce_min_tail`-style frame math);
`test_trim_range_drops_audio_and_forces_exact_frame_count` and
`test_trim_range_uses_consistent_encoder_settings_every_call` (via
`bl_merge.verify_same_codec()` on two independently-trimmed ranges of
different source lengths — proves the codec-identity precondition
`bl_merge.py`'s own concat gate needs actually holds).

## Item 5 — Briefs

Wrote `docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md` (whole episode,
0.0-153.0333s) and `BRIEF-seg.md` (template, `{seg}`/`{t0}`/`{t1}`/
`{tags}`), both derived from Arm A's own brief
(`docs/ops/bl-ab-2026-09-25/arms/A/README.md`) — same source-material
list, same beats.json mode shapes (FF/COMP/EVID/KIN), same "decide mode
per Jev's own convention" paragraph — plus the Jev loop section (`plan
--state-lang th` / `freeze` / `final`, per SKILL.md's own recommended
`--state-lang` and its "who decides" gate) and the caption-spelling rule
(SCRIPT.tsv's โบรก vs the re-voice's โบร๊ก). Verified programmatically
(not just by eye) that the shared editorial-content spans (source material
through "decide mode", inclusive) are byte-identical between the two
files — a small Python diff check, both spans matched exactly on the
second pass (first pass had two small wording deviations I'd added for
"your window" scoping language; removed them so the files are genuinely
word-for-word identical outside the range description and BRIEF-seg.md's
own "Segment contract" section, per the task brief's own requirement).

`tools/bl_ab_run.py`: replaced the old `SEGMENT_CONTRACT_TEMPLATE`/
`_segment_brief()` (which built the OLD raw-HTML-pipeline brief inline in
Python) with `_brief_body()` (strips each BRIEF-*.md's own explainer above
the `## Brief given to the worker` marker) + a new `cmd_spawn_full`
(prints `BRIEF-arm1.md` verbatim) + a rewritten `cmd_spawn_seg` (fills
`BRIEF-seg.md`'s four placeholders via plain `str.replace()`, NOT
`str.format()` — the brief's own body is full of literal JSON-shaped curly
braces, e.g. `{"tag","t0","t1","mode","extra"}`, that `.format()` would
try to parse as fields and raise/mangle on; confirmed this with a
dedicated regression test). Removed `--fixture-dir` from `spawn-seg`'s own
CLI (no longer parameterized — both briefs now hardcode the real on-box
fixture path, matching each other exactly) and the now-dead
`RENDER_LOCK_PATH` constant (its only use was the old inline template).
Added a new `spawn-full` subparser. Manually verified both commands'
printed output end-to-end (spawn-full's whole brief, spawn-seg for seg02
with all four placeholders substituted including inside the render
command block).

Wrote `tests/test_bl_ab_run.py` (no test file existed for this tool
before — everything else in it drives ssh/scp/delegate_task against a
real box and has no realistic fixture; `spawn-full`/`spawn-seg` are pure
local string plumbing, so worth covering): both `BRIEF-*.md` files exist
and parse, `_brief_body()` strips the explainer correctly, `spawn-full`
prints the brief + the DRY RUN line, `spawn-seg` substitutes all four
placeholders (and the render command), an unknown segment id errors
cleanly (rc=1), and the JSON-brace-survives-`.replace()` regression case.

Rewrote `docs/ops/bl-split-ab-2026-09-25/TOOLING.md` to match (was 633
lines, now 194): added a `task-99f3d2e8 changes` note at the top, updated
"Commands in order" for both arms to the `bl_compose.py`/beats.json route
and `spawn-full`, regenerated the "EP57 segment plan" section with the
real 4-segment output, and replaced the ~490-line inline dump of all 5
(now-obsolete) raw-HTML segment briefs with a short pointer to
`BRIEF-arm1.md`/`BRIEF-seg.md` plus one live `spawn-seg` example (seg02).

## Item 6 — Fixture (v2 media)

The CTO's task brief says v2 media (re-voiced `audio-hq.mp3`, `lip_a.mp4`/
`lip_c.mp4`, `lip_a-matte.webm`/`lip_c-matte.webm`) is landing under
`/opt/MoonieXHQ/Work/bl-split-ep57/` with the SAME filenames and timings.
Confirmed: as of this run, the media there is still v1 (audio-hq.mp3 v1,
`media/matte/` has only `lip_a`/`lip_b`, no `lip_c-matte.webm` — same gap
TOOLING.md already flagged). Every path this task's code touches
(`bl_split.py`'s CLI args, `bl_ab_run.py`'s `FULL_EPISODE_WORK_DIR`/
`fixture-full`, the two BRIEF-*.md files) already keys off the exact
filenames the task brief names for v2 — no code changes were needed for
this item specifically; regenerating `segments.json`/re-running
`fixture-full` against the real v2 files once they land is a data refresh,
not a code change. `--min-seg` (item 1) does depend on the real audio's
silence structure, so `segments.json`'s exact cut points may shift once
v2 lands — worth a re-run then, noted in REPORT.md.

## Tests — full run

```
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest \
  tests/test_bl_split.py tests/test_bl_compose.py tests/test_bl_checker.py \
  tests/test_bl_merge.py tests/test_bl_ab_run.py -q
133 passed in 26.06s
```

`pytest --collect-only -q` repo-wide: no import errors, no collection
errors introduced.

## Did NOT

Cut EP57, run Arm 1, run Arm 2, spawn any editor, or re-run `fixture-full`
against the box's current media (out of scope per the task brief — "You
still do NOT cut the episode and do NOT spawn editors").

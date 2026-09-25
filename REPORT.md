# REPORT task-99f3d2e8

## Summary

Follow-up to task-1678d38e: `bl_split.py` now merges a too-short final
segment into the one before it (`--min-seg`, default 20s) — EP57 is 4
segments, not 5. `bl_compose.py` gained one-caption-style emission
(`caption()` only, no `addCap`), plates that hold for their full computed
duration regardless of the underlying media's own length, and a
`--t0/--t1` range render (frame-exact, video-only, fixed encoder) so a
segment editor renders only its own window. Wrote `BRIEF-arm1.md`/
`BRIEF-seg.md` — both arms now route through Arm A's own
`bl_compose.py`/`beats.json` workflow (CTO ruling 2026-09-25) plus the Jev
loop and the SCRIPT.tsv-not-TTS caption-spelling rule; `bl_ab_run.py`
gained `spawn-full` and a rewritten `spawn-seg` that print them. Did not
cut EP57, run either arm, or spawn any editor — out of scope per the task
brief.

## Files Changed

- `tools/bl_split.py` — `MIN_SEG_TAIL`/`enforce_min_tail()`, wired into
  `split_episode()` and the CLI (`--min-seg`, default 20.0).
- `docs/ops/bl-split-ab-2026-09-25/segments.json` — regenerated for real
  against the on-box EP57 audio: 4 segments (last 104.5333-153.0333).
- `tools/bl_compose.py` — one-caption-style emission (`caption()` only);
  removed the LIP_DUR-based plate-duration cap in FF/COMP; new `--t0`
  range render (`t0_window` shift in `emit_pieces()`/`compose()` +
  `trim_range()`), CLI `--t0` flag.
- `docs/ops/bl-split-ab-2026-09-25/BRIEF-arm1.md` — new: Arm 1's full
  brief (whole episode, bl_compose.py/beats.json route + Jev loop +
  caption-spelling rule).
- `docs/ops/bl-split-ab-2026-09-25/BRIEF-seg.md` — new: Arm 2's brief
  template (`{seg}`/`{t0}`/`{t1}`/`{tags}`), word-for-word identical to
  BRIEF-arm1.md outside the range + its own segment contract section.
- `tools/bl_ab_run.py` — new `cmd_spawn_full`/`_brief_body()`; rewrote
  `cmd_spawn_seg` to fill `BRIEF-seg.md` via `str.replace()` (not
  `str.format()`); dropped the dead `SEGMENT_CONTRACT_TEMPLATE`/
  `_segment_brief()`/`RENDER_LOCK_PATH`/`spawn-seg --fixture-dir`; added
  the `spawn-full` subparser; updated the module docstring.
- `docs/ops/bl-split-ab-2026-09-25/TOOLING.md` — rewritten (633 → 194
  lines): task-99f3d2e8 changes note, bl_compose.py-routed commands for
  both arms, regenerated 4-segment plan, replaced the ~490-line inline
  dump of all 5 old raw-HTML briefs with a pointer to the two BRIEF-*.md
  files + one live `spawn-seg` example.
- `tests/test_bl_split.py` — 6 new tests for `enforce_min_tail`/the
  merged-default behaviour; fixed one pre-existing test the new default
  regressed (`--min-seg 0` added, since it tests CLI plumbing not the
  merge feature).
- `tests/test_bl_compose.py` — updated 1 existing test's caption
  assertions (no more `chip-ff`/`rail`); added ~20 new tests: one-caption-
  style integration (pass + the old-shape regression), plates-hold (FF +
  COMP, plus the legitimate `avatar_until` case), the `t0_window` shift
  (placement vs media-seek, exclusion, `total_dur`, through real
  `compose()`), and `trim_range()` (frame-count additivity across
  adjacent ranges — the task's own literal test criterion — audio-drop,
  and codec consistency via `bl_merge.verify_same_codec()`).
- `tests/test_bl_ab_run.py` — new (no test file existed for this tool
  before): `spawn-full`/`spawn-seg` output, placeholder substitution,
  unknown-segment error path, and the JSON-brace-survives-`.replace()`
  regression.
- `RUNLOG.md` — this task's own progress log (worktree root).

## Commits

- `27e757b3` — bl_split: --min-seg merges a short final segment into the one before it
- `428c10a3` — bl_compose: one caption style, plates hold by construction, range render
- `28003f13` — briefs: BRIEF-arm1.md/BRIEF-seg.md route both arms through bl_compose.py
- `10b2faf1` — docs(RUNLOG): task-99f3d2e8 progress log

## Tests

- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_bl_split.py tests/test_bl_compose.py tests/test_bl_checker.py tests/test_bl_merge.py tests/test_bl_ab_run.py -q`
- passed: 133
- failed: 0
- skipped: 0
- also ran `pytest --collect-only -q` repo-wide: no import/collection errors introduced.

## Issues / Blockers

- **Fixture is still v1 media.** `/opt/MoonieXHQ/Work/bl-split-ep57/` has
  the pre-splice voice (`audio-hq.mp3` v1) and `media/matte/` is missing
  `lip_c-matte.webm` (same gap TOOLING.md already flagged pre-task).
  Coded against the exact filenames the task brief names for v2 (same
  names, per the brief) — no code changes needed once v2 lands, but
  `segments.json`'s exact cut points depend on the real audio's silence
  structure, so it's worth re-running `bl_split.py` once the re-voice is
  in place (the cut points may shift slightly; frame math is unaffected).
- Did not re-run `fixture-full` on this box (no `generator/` dir was
  staged before or after this task) — code changes were verified against
  the raw fixture files present + synthetic ffmpeg/pytest fixtures
  instead, matching how every prior task in this doc set verified its own
  tooling (no `npx hyperframes render` in any test here, same as
  task-1678d38e's own test suite).
- `tools/bl_compose.py --t0/--t1`'s CLI flag is literally `--t0`/`--t-max`
  (kept `--t-max` doubling as `t1` rather than renaming it) so Arm A's
  existing README/`bl_ab_run.py run-c` call sites keep working unchanged.
  Flagging this in case the CTO wants a literal `--t1` alias too — easy
  add, didn't seem worth the churn against two already-working callers.

## Notes for Reviewer

- The "must fail on the old EP57 generator" regression the task brief asks
  for already had its own dedicated test in `tests/test_bl_checker.py`
  (`test_caption_style_signatures_flags_the_ep57_three_kind_bug`, from
  task-1678d38e) — kept it, and added a second one in
  `tests/test_bl_compose.py` proving `bl_compose.py`'s OWN code can no
  longer produce that shape (the `addCap` call site is gone from the
  source, not just untriggered).
- Range render design choice worth double-checking: `emit_pieces()` SHIFTS
  composition placement by `t0_window` but keeps `pick_lip`/`lip_offset`/
  `media_start` on the beat's true ABSOLUTE time. This is necessary so a
  late segment (e.g. seg04 at t0=104.53) doesn't have to render the
  preceding ~104s of empty timeline just to reach its own window, and so
  the underlying lip-sync media seeks to the correct real offset. Verified
  with `test_emit_pieces_t0_window_shifts_placement_not_media_seek`.
- `BRIEF-arm1.md`/`BRIEF-seg.md` word-for-word identity was checked
  programmatically (a small Python diff over the shared span), not just by
  eye — worth re-running that check if either file is hand-edited later
  (`python3 -c "..."` snippet is in this session's own transcript, not
  saved as a script since it's a one-off check).

## Skill learning
- MISSING [no owner] : no skill covers "write a worker brief for a spawned editor that must stay word-for-word identical to a sibling brief except a parameterized range" — designed the split (shared prose vs `str.replace()`-templated range/contract sections) from scratch, including catching that `str.format()` would break on the brief's own literal JSON-shaped `{...}` examples. · evidence: tools/bl_ab_run.py `cmd_spawn_seg`, `docs/ops/bl-split-ab-2026-09-25/BRIEF-seg.md`
- (none) : otherwise — no other trap or detour worth recording; the prior task's docs (PLAN.md/TOOLING.md/RUNLOG-task-1678d38e.md) were accurate and sufficient to build on directly.

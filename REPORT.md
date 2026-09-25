# REPORT task-1678d38e

## Summary

Built steps 0 and 1 of `docs/ops/bl-split-ab-2026-09-25/PLAN.md` (the CEO's dead-air
split A/B for BL EP57): fixed the caption/timing bugs in the shared kit so both arms
start from a corrected template and checker, then wrote `tools/bl_split.py` (the
dead-air split), `tools/bl_merge.py` (concat + gated merge), and `tools/bl_ab_run.py`'s
`fixture-full`/`spawn-seg`. Did not cut EP57, run either arm, or spawn any editor --
that is explicitly out of scope for this task. All tooling was exercised against the
real EP57 audio/script/timings/media already on this box, not just synthetic fixtures.

## Files Changed

- `.claude/skills/blackliquidity-cut/template/index.html` — added `caption(at, out,
  text)` generator; `.cap` CSS now bakes in EP55's approved band (background, padding,
  radius, weight/size) as the ONLY caption look, used in every mode.
- `.claude/skills/blackliquidity-cut/SKILL.md` — §6d's old per-mode caption-chip rule
  marked `[SUPERSEDED 2026-09-25]` with the CEO's quote; new §6f (one caption style,
  every mode) and §6g (plates hold until the next plate, promoted from the 2026-09-24
  field note); generator table + kit description updated; five field notes' status
  flipped `pending` → `promoted`.
- `.claude/skills/blackliquidity-cut/reference/caption-ep55.jpg` (new) — rendered via
  `hyperframes snapshot` from the fixed template: a sample Thai caption over a real
  EP57 `media/real/` screenshot (EP55's own final render is on Drive, unreachable from
  a worker session — noted in the skill).
- `tools/bl_checker.py` — `detect_empty_frames` now samples at 30fps (was 4fps) with a
  new whole-frame-mean single-frame-dip check layered on the existing std<12 flat
  check; new `check_one_caption_style()`/`caption_style_signatures()` gate (counts
  distinct caption styles from `addCap()`/`caption()` calls or hand-rolled inline
  styles in a composition's script); `caption_band()` updated to match the new single
  fixed caption position; `run_checker()`/CLI gained `--composition`.
- `tests/test_bl_checker.py` — 12 new tests (30fps-vs-4fps dip regression with a
  frame-exact ffmpeg fixture, an isolated dip-logic unit test independent of std, and
  the one-caption-style gate).
- `tools/bl_split.py` (new) — dead-air split per PLAN.md's rule exactly.
- `tests/test_bl_split.py` (new, 21 tests).
- `tools/bl_merge.py` (new) — concat + every PLAN.md merge gate.
- `tests/test_bl_merge.py` (new, 16 tests, incl. a deliberately injected black frame at
  a seam that the seam gate must catch).
- `tools/bl_ab_run.py` — new `fixture-full` (full-episode fixture, ground-truth
  redacted, staged locally — this box is already Contabo) and `spawn-seg` (prints,
  never spawns, a segment editor's brief).
- `docs/ops/bl-split-ab-2026-09-25/ep57-blocks.json` (new) — the forbidden checklist
  card span for EP57.
- `docs/ops/bl-split-ab-2026-09-25/segments.json` (new) — the REAL EP57 split plan.
- `docs/ops/bl-split-ab-2026-09-25/TOOLING.md` (new) — commands in order for both arms,
  the EP57 segment plan, and all 5 generated segment briefs verbatim.
- `RUNLOG.md` (new, worktree root) — append-as-you-go log.

## Commits

- `56a7a103` — bl-split-ab step 0: one caption style, plates hold, checker gates upgrade
- `f10c0711` — bl-split-ab step 1: bl_split.py + bl_merge.py (dead-air split + gated merge)
- `71150ab4` — bl-split-ab: fixture-full + spawn-seg (dry-run brief only), TOOLING.md

## Tests

- ran: `pytest tests/test_bl_checker.py tests/test_bl_split.py tests/test_bl_merge.py -q`
- passed: 62
- failed: 0
- skipped: 0
- also ran `pytest --collect-only -q` across the whole repo to confirm no import errors
  were introduced elsewhere (collection succeeded).
- `tools/bl_ab_run.py`'s two new subcommands (`fixture-full`, `spawn-seg`) have no
  pytest file — matching the existing convention for this file (it had none before
  either; its other commands are all ssh/scp/spawn-dependent "ops runner" code, not
  unit-testable without live infra). Instead I exercised both manually against the
  real EP57 data on this box:
  - `fixture-full` staged a full generator dir, correctly redacted `build_cut.py`'s
    `BEATS`/`CHECK_ITEMS` to `[]`, and correctly printed a WARNING for the one missing
    matte (`lip_c-matte.webm`).
  - `spawn-seg` printed correct, well-formed briefs for all 5 real EP57 segments
    (embedded verbatim in TOOLING.md).

## EP57 segment plan (from `tools/bl_split.py` against the real episode)

```
audio: /opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3  total_duration=153.0514s  pauses_detected=55  candidates(>=0.45s)=37
cuts (frame-floored, s): [39.3, 65.83333333333333, 104.53333333333333, 145.9]
N segments = 5
  seg01  t0=  0.000  t1= 39.300  dur=39.300s  frames=1179   tags: HOOK-1, HOOK-2, HOOK-3, HOOK-4, PATTERN-1, PATTERN-2, PATTERN-3, PATTERN-4, CONTEXT-1, CONTEXT-2
  seg02  t0= 39.300  t1= 65.833  dur=26.533s  frames=796    tags: CONTEXT-3, CONTEXT-4, CONTEXT-5, MAIN-1, MAIN-2, MAIN-3
  seg03  t0= 65.833  t1=104.533  dur=38.700s  frames=1161   tags: MAIN-4, MAIN-5, MAIN-6, MAIN-7, MAIN-8, MAIN-9, MAIN-10, MAIN-11, MAIN-12, MAIN-13, CURIOSITY-1, CURIOSITY-2
  seg04  t0=104.533  t1=145.900  dur=41.367s  frames=1241   tags: CURIOSITY-3, CURIOSITY-4, CURIOSITY-5, SUMMARY-1, SUMMARY-2, SUMMARY-3, SUMMARY-4, SUMMARY-5, SUMMARY-6, SUMMARY-7
  seg05  t0=145.900  t1=153.033  dur=7.133s  frames=214    tags: SUMMARY-8, SUMMARY-9
```

5 segments — inside PLAN.md's own "EP57 estimate 3-5". No cut lands inside the one
forbidden span (SUMMARY-4..6's checklist card, 129.38-141.48s). Full per-segment script
line detail (tag/timing/Thai text) is in `docs/ops/bl-split-ab-2026-09-25/segments.json`
and in the 5 generated briefs in `TOOLING.md`.

## Issues / Blockers

- **`lip_c-matte.webm` does not exist** in `/opt/MoonieXHQ/Work/bl-split-ep57/media/matte/`
  (only `lip_a`/`lip_b` mattes are present). `fixture-full` prints a WARNING about this;
  any Arm-2 segment needing a COMPOSITE beat inside `lip_c`'s range (roughly t≥120s —
  seg04/seg05) will need a fresh `bl_tools.py matte` run before that beat can render. I
  did not run that matte job myself (out of scope — no cutting/spawning).
- **Interpretation call on "brief = the same editor brief as Arm A"**: there is no
  literal "Arm A" brief for THIS plan. The only Arm A brief on disk
  (`docs/ops/bl-ab-2026-09-25/arms/A/README.md`) belongs to a different, already-finished
  30.78s-window experiment (task-aae4f843) whose `beats.json` + `tools/bl_compose.py`
  output shape doesn't fit this PLAN.md at all (which cuts the real HTML composition
  directly, per the normal `blackliquidity-cut` skill). I read "Arm A" as shorthand for
  "whatever brief Arm 1 gets", and wrote `spawn-seg`'s brief as the standard
  `blackliquidity-cut` pipeline brief, scoped to one segment, with PLAN.md's segment
  contract layered on top. Flagged explicitly in TOOLING.md with a way to redo it the
  other way if the CTO actually wants the beats.json/bl_compose.py route. **Please
  confirm this reading before spawning any real Arm 1/Arm 2 editor.**
- Everything else in the task brief is done. Arm 1 run, Arm 2 run, CTO merge, and CEO
  report (PLAN.md steps 2-4) are separate future work, not part of this task.

## Notes for Reviewer

- The caption fix is the highest-stakes change here (it's what the CEO directly
  rejected on the last EP57 cut) — worth reading `template/index.html`'s new
  `caption()` function and `.cap` CSS, and looking at
  `.claude/skills/blackliquidity-cut/reference/caption-ep55.jpg`, before merging.
- `tools/bl_checker.py`'s empty-frame upgrade changes default behavior
  (`EMPTY_FRAME_FPS` 4 → 30) for any other caller — I grepped the repo and the only
  caller is `tests/test_bl_checker.py` itself, which references the constant
  dynamically, so nothing else needed updating.
- `tools/bl_merge.py`'s seam gate is deliberately built by cross-referencing the
  existing empty-frame gate's own flagged timestamps against seam positions (rather
  than a second independent pass) — simpler, reuses `bl_checker.detect_empty_frames`
  verbatim, and is directly what the synthetic "black frame at a join" test proves out.
  A seam-adjacent defect that is NOT an empty/black frame (e.g. a genuine encode
  mismatch not caught by the codec pre-flight) would not be caught by this gate — I
  judged that out of scope given the task's own test guidance ("a failing seam (one
  black frame at a join)").
- `docs/ops/bl-split-ab-2026-09-25/segments.json` was generated for real against
  `/opt/MoonieXHQ/Work/bl-split-ep57/audio-hq.mp3` on this box — it is not a mock. If
  that Work dir's contents change (e.g. a re-voice splice), re-run the `bl_split.py`
  command in TOOLING.md to regenerate it.

## Skill learning
- MISSING [blackliquidity-cut §6d/§9] : the skill had no rule that a caption generator must be MODE-INDEPENDENT (single style regardless of FF/COMP/EVID) — every prior BL episode's caption bug (EP54's `.nb` nowrap fix, EP55's CTO-review band fix, EP57's three-look regression) came from a worker re-inventing captions per episode because the template itself never carried the fix forward · evidence: SKILL.md's own pre-existing field note "2026-09-25 [MISSING] template — ... It never went back into template/index.html" · fix: now folded into template/index.html directly (not just documented in prose), so a future worker copying the template inherits the fix instead of re-deriving it.
- MISSING [blackliquidity-cut §9] : no existing rule said empty-frame detection must sample at the render's real fps — a 4fps convenience sample silently has blind spots for single-frame defects, and nothing in the skill flagged that tradeoff before this task · evidence: EP57 76.37s single-frame black flash, missed by the 4fps/std<12 gate (SKILL.md field note, task-501f1d89) · fix: tools/bl_checker.py now samples at 30fps by default; documented in SKILL.md §6g.
- (none) beyond the two notes above — no wrong rule encountered, no costly detour. The one open question (interpretation of "Arm A") is a task-brief ambiguity, not a skill defect, and is flagged in Issues/Blockers + TOOLING.md instead.

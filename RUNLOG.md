# RUNLOG task-1678d38e — BL split-by-dead-air: kit fix + tooling

## 2026-09-25 setup
- Read `docs/ops/bl-split-ab-2026-09-25/PLAN.md`.
- Read `.claude/skills/blackliquidity-cut/SKILL.md` (721 lines) end to end.
- Read `.claude/skills/blackliquidity-cut/template/index.html` (499 lines) — confirmed:
  only a plain `.cap` CSS rule, no caption generator function.
- Read `prototypes/bl55-cut/index.html` lines 250-510 — EP55's approved `.cap`/`.cap.band`
  CSS + its `caption(at, out, text, band)` JS generator (the bar to match).
- `git show origin/agent/video_editor-task-501f1d89:prototypes/bl57-cut/{build_cut.py,assemble.py,render_windows.sh}`
  — confirmed the caption bug: `assemble.py`'s `addCap(t0,t1,text,kind,y)` emits THREE
  different inline-styled looks depending on `kind` ("chip-ff" = plain `.cap`, no
  background; "chip-comp" = small 38px chip with its own background; "rail" =
  full-bleed strip `left:0;right:0`). This is exactly what the CEO rejected. NOT copying
  this code per the task brief — template gets EP55's single style instead.
- Read `tools/bl_checker.py` (249 lines) + `tests/test_bl_checker.py` (180 lines) — the
  existing empty-frame gate samples at 4fps/270x480, std<12; the 2026-09-25 field note
  says it missed a single-frame black dip at 76.37s in EP57 because a 4fps sample grid
  can skip a 1/30s-long defect entirely.
- Read `/opt/MoonieXHQ/Work/bl-split-ep57/{SCRIPT.tsv,timings.tsv}` — 40 script lines,
  153.0s audio (ffprobe: 153.051429s). timings.tsv confirms the checklist card spans
  SUMMARY-4..6, t0=129.38 to (next plate SUMMARY-7 at) 141.48 — matches PLAN.md's
  "checklist card 129.38-141.48s" forbidden-cut span.
- Ran `ffmpeg -af silencedetect=n=-35dB:d=0.3` on the real EP57 audio directly to confirm
  the detector command PLAN.md specifies actually produces pauses (it does — first pauses
  at 2.66-3.22s dur 0.56s, matches the "55 pauses >=0.3s" scale in PLAN.md).
- Read `tools/bl_ab_run.py` (361 lines, task-aae4f843's A/B/C runner) for the existing
  `fixture` subcommand pattern (30s-window fixture staged to Contabo) to extend with
  `fixture-full`/`spawn-seg`. Read `docs/ops/bl-ab-2026-09-25/arms/A/README.md` for the
  brief-text shape `spawn-seg` must reuse (scoped to a time range + segment contract).
- Read `tools/bl_compose.py` — a SEPARATE, already-merged beats.json->render adapter for
  the 30s A/B/C experiment. Out of scope for this task (my tools are new, standalone).

## Plan
0.1 template caption() generator (EP55 style, no mode branching) + SKILL.md §6d superseded
    note + reference/caption-ep55.jpg.
0.2 SKILL.md: promote "plates hold until next plate" field note into a rule.
0.3 bl_checker.py: 30fps + single-frame-dip empty-frame gate; one-caption-style gate. Tests.
1.  tools/bl_split.py (dead-air split) + tests.
2.  tools/bl_merge.py (concat + gates) + tests.
3.  tools/bl_ab_run.py: fixture-full + spawn-seg (brief text only, never spawns).
4.  docs/ops/bl-split-ab-2026-09-25/TOOLING.md.
5.  pytest, commit, push, REPORT.md.

## Done (commits 56a7a103, f10c0711, 71150ab4)

Step 0: `.claude/skills/blackliquidity-cut/template/index.html` now carries a single
`caption(at, out, text)` generator baking in EP55's approved `.cap` band CSS, used in
every mode. SKILL.md §6d's old per-mode chip rule marked `[SUPERSEDED 2026-09-25]`; new
§6f (one caption style) and §6g (plates hold until next plate, promoted from the
2026-09-24 field note) added; five field notes flipped pending -> promoted.
`reference/caption-ep55.jpg` rendered for real via `hyperframes snapshot` (a sample Thai
caption over an actual EP57 `media/real/` screenshot). `tools/bl_checker.py`'s
`detect_empty_frames` now samples at 30fps (was 4fps) with a whole-frame-mean
single-frame-dip check layered on the std<12 flat check; new
`check_one_caption_style()`/`caption_style_signatures()` gate. 25/25 tests green
(`tests/test_bl_checker.py`), including a real ffmpeg regression test that reproduces
the exact "4fps missed it, 30fps catches it" bug.

Step 1: `tools/bl_split.py` implements PLAN.md's dead-air split rule exactly (candidates
>=0.45s from silencedetect, forbidden spans from --blocks, walk-forward window
[+25s,+50s] else longest-past-+25s, cut = midpoint floored to the 30fps grid). Dry run
against the REAL EP57 audio/script/timings (checklist card 129.38-141.48s as the one
forbidden span) produces 5 segments -- inside PLAN.md's own "estimate 3-5". 21/21 tests
green (`tests/test_bl_split.py`), incl. one real-ffmpeg end-to-end test.

`tools/bl_merge.py` concats video-only parts with `-c copy` after verifying identical
codec params (refuses otherwise), muxes the master audio once, then runs every PLAN.md
merge gate (frame count, empty/black frames incl. dips, seam window +/-3 frames, one
caption style across every segment, audio offset <40ms), naming every failed gate.
16/16 tests green (`tests/test_bl_merge.py`), incl. an end-to-end test with a
deliberately injected single black frame AT a seam that the seam gate catches.

`tools/bl_ab_run.py` gained `fixture-full` (stages the full 153s EP57 fixture locally,
ground-truth redacted -- verified manually, correctly flags the missing
`lip_c-matte.webm`) and `spawn-seg` (prints, never spawns, a segment editor's brief --
verified manually for all 5 real EP57 segments). `docs/ops/bl-split-ab-2026-09-25/
{ep57-blocks.json,segments.json,TOOLING.md}` written -- TOOLING.md carries the commands
in order for both arms, the real EP57 segment plan, and all 5 generated briefs verbatim,
plus a flagged interpretation note on "the same editor brief as Arm A" (no literal Arm A
brief exists for THIS plan; the only one on disk belongs to a different, already-finished
experiment with an incompatible beats.json/bl_compose.py shape -- see TOOLING.md).

Full test suite collection (`pytest --collect-only`) still succeeds repo-wide -- no
import errors introduced. 62/62 tests green across the three touched test files.

Did NOT: cut EP57, run Arm 1, run Arm 2, or spawn any editor -- out of scope per the task
brief ("You build steps 0 and 1 of that plan. You do NOT cut the episode and you do NOT
spawn editors").

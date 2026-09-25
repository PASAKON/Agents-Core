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

# BL Editor A/B/C -- per-arm scores (task-aae4f843)

All three arms cut the same window: BLACK LIQUIDITY EP57, 0-30.78s, 8 lines
(HOOK-1..4, PATTERN-1..4 -- `PATTERN-1b` in the human ground truth is a
mid-sentence split none of the three arms produced, since none saw the
human's own split; consistently reported as "missing", not a bug in any
arm). Ground truth: `docs/ops/bl-ab-2026-09-25/ground_truth_beats.json`
(4 COMP, 4 EVID/EVID-split, 1 FF).

Every arm's own inputs, outputs and transcript are archived under
`$WORK_DIR/out/{A,B,C}/` (not in git -- media and raw transcripts never go
in git); each arm's `beats.json`/`render-meta.json`/`checker-result.json`
are additionally committed at `prototypes/bl-ab-ep57/<arm>/`.

## Correction 2026-09-25 (later the same day)

Every turn count and $ below was recounted deduplicated by `message.id`; the
first publication summed raw transcript lines (one line per content block,
same id and usage repeated) and was ~2x high (the Scripter 4.3x). Raw line
counts stay in brackets. Ranking unchanged. Detail: `../REPORT.md` §Correction.

## Side-by-side

| | Arm A -- today's Editor | Arm B -- Scripter -> blind Editor | Arm C -- Scripter, no Editor |
|---|---|---|---|
| Mode mix chosen | 1 COMP, 6 EVID, 1 FF | 0 COMP, 7 EVID, 1 FF | 0 COMP, 7 EVID, 1 FF |
| Mode agreement vs truth | **62.5%** (5/8) | 50.0% (4/8) | 50.0% (4/8) |
| Mean IoU (6 boxed beats) | **0.822** | 0.265 | 0.189 |
| Checker verdict | **PASS** (1 fix round, self-driven) | **PASS** (1 fix round, brief-mandated) | **FAIL** (uncorrected by design) |
| Render | 2x on Contabo (own report: ~2.5-3 min each) | 2x on Contabo (own report: ~2.5-3 min each) | 1x on Contabo, measured: **164.9s** for 923 frames @ 1080x1920/30fps = **5.6 fps** |
| Wall time, editor session only | **18 min** (spawn -> branch push) | **11 min** (spawn -> branch push) | 0 (no editor session) |
| Editor turns (API calls; transcript lines in brackets) | **82** (161) | **43** (73) | 0 |
| Editor tokens (in/cache-w/cache-r/out) | 164 / 192,041 / 13,553,401 / 54,017 | 86 / 81,991 / 4,588,634 / 28,068 | -- |
| Editor cost, API-equivalent | **$3.7313** | **$1.4036** | -- |
| Scripter cost (reused, task-67bb7a11) | -- (Arm A never uses the Scripter) | $0.2563 (3 turns, 88.5s) | $0.2563 (3 turns, 88.5s) |
| **Total pipeline cost, API-equivalent** | **$3.7313** | **$1.6599** | **$0.2563** |
| **Total pipeline turns** | **82** | **46** | **3** |
| **Total pipeline wall time** | **~18 min** | **~12.5 min** | **~1.5 min** (Scripter 88.5s + compose/render/check ~170s -- Scripter's own wall is a separate, reused, prior run) |

Costs are Sonnet 5 API-equivalent, from each session's own Claude Code
transcript (`tools/bl_scripter.py::usage_from_transcript`, the same table
`tools/bl_score.py` uses) -- not the Max-plan's own reported `total_cost_usd`
(no per-call API billing was used anywhere in this experiment, per the
brief: `$0`, no key, no Hetzner).

## Arm A -- today's Editor

- common beats (in both truth and produced): 8
- missing (in truth, not produced): `PATTERN-1b`
- extra (produced, not in truth): (none)
- mode agreement: 62.5% (5/8)
- mean IoU (over 6 beats with a box on both sides): 0.822

| tag | truth mode | Arm A mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | COMP | yes | - |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | EVID | no | 0.955 |
| HOOK-4 | COMP | EVID | no | 0.752 |
| PATTERN-1 | COMP | EVID | no | 0.362 |
| PATTERN-2 | EVID | EVID | yes | 0.955 |
| PATTERN-3 | EVID | EVID | yes | 0.955 |
| PATTERN-4 | EVID | EVID | yes | 0.955 |

Cost (own transcript, deduplicated by message.id): 82 turns (161 lines); tokens input=164
cache_write=192,041 cache_read=13,553,401 output=54,017; **$3.7313** API-equivalent.

## Arm B -- Scripter -> blind Editor -> Checker

- common beats: 8; missing: `PATTERN-1b`; extra: (none)
- mode agreement: 50.0% (4/8) -- identical to the raw Scripter output
  (Arm B's fix round only moved `box` numbers to clear the checker's safe
  rectangle, never touched `mode`)
- mean IoU (6 beats): 0.265 (Scripter's raw output alone scored 0.189 --
  the safe-area fix incidentally tightened several boxes toward the
  canvas center, which happened to also move them closer to truth)

| tag | truth mode | Arm B mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | EVID | no | - |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | EVID | no | 0.281 |
| HOOK-4 | COMP | EVID | no | 0.111 |
| PATTERN-1 | COMP | EVID | no | 0.358 |
| PATTERN-2 | EVID | EVID | yes | 0.281 |
| PATTERN-3 | EVID | EVID | yes | 0.281 |
| PATTERN-4 | EVID | EVID | yes | 0.281 |

Editor session cost (own transcript, the blind build+checker+fix cycle
only, deduplicated by message.id): 43 turns (73 lines); tokens input=86 cache_write=81,991
cache_read=4,588,634 output=28,068; **$1.4036** API-equivalent. Plus the reused Scripter run:
3 turns, **$0.2563**, 88.5s. **Total: 46 turns, $1.6599.**

First checker run: **FAIL** (`out_of_safe_area`: HOOK-1, HOOK-3, HOOK-4,
PATTERN-1..4; `credit_missing`: HOOK-1, HOOK-4). Second run (after the one
allowed fix round, 7 `box` values adjusted by pure arithmetic against the
checker's own safe-rectangle/credit-clearance formulas, no image opened):
**PASS**.

## Arm C -- Scripter, no Editor

- common beats: 8; missing: `PATTERN-1b`; extra: (none)
- mode agreement: 50.0% (4/8) -- the Scripter's raw, unfixed output
- mean IoU (6 beats): 0.189

| tag | truth mode | Arm C mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | EVID | no | - |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | EVID | no | 0.178 |
| HOOK-4 | COMP | EVID | no | 0.084 |
| PATTERN-1 | COMP | EVID | no | 0.337 |
| PATTERN-2 | EVID | EVID | yes | 0.178 |
| PATTERN-3 | EVID | EVID | yes | 0.178 |
| PATTERN-4 | EVID | EVID | yes | 0.178 |

Cost: the Scripter's own run only (task-67bb7a11, reused): 3 turns (10 lines, deduplicated by message.id);
tokens input=6 cache_write=56,979 cache_read=164,157 output=8,103;
**$0.2563** API-equivalent (**$0.3418** Max-plan-reported); 88.54s wall.

Checker (run directly by the developer over ssh, no fix): **FAIL**, same
signature as Arm B's first (uncorrected) run -- `out_of_safe_area`:
HOOK-1, HOOK-3, HOOK-4, PATTERN-1..4; `credit_missing`: HOOK-1, HOOK-4.
This is the finding for this arm: the Scripter's own output does not clear
the mechanical safety checker on its own, every time it's been run
(this task and task-67bb7a11 both).

## Caveat: Arm A's fixture was not yet sanitized

`/opt/MoonieXHQ/Work/bl-ab-ep57/generator/build_cut.py` (staged for Arm A
so `tools/bl_compose.py`'s AST-selective loader could pull its
`img_placement`/`box_to_canvas`/`pick_lip`/`lip_offset` functions) still
carried its hardcoded `BEATS` table -- the human editor's own real
mode/box answer for this exact window -- when Arm A ran. Arm A's own
REPORT.md flagged this unprompted: it had to open `build_cut.py` to
understand the coordinate contract (`tools/bl_compose.py`'s docstring
points straight at it) and so was exposed to the ground truth before
finishing its own calls. It reports building its boxes independently
(ffmpeg-crop previews, before consulting that table) and that the one
place its box nearly matches truth exactly (HOOK-3, IoU 0.955) is, in its
own words, "convergence on the obvious answer" (a full-page error screen
has essentially one sensible crop) rather than a copied value -- but this
cannot be independently verified after the fact, so **Arm A's 0.822 mean
IoU and 62.5% mode agreement should be read as an upper bound on an
independent editor's performance, not a clean measurement of it.**

Fixed for any future run in `tools/bl_ab_run.py::_redact_ground_truth`
(AST-blanks `BEATS`/`CHECK_ITEMS` to `[]` before staging; verified the
redacted file still loads every function `bl_compose.py` needs). Applied
to the Contabo fixture immediately after Arm A finished, before Arm B/C
ran -- low risk to either even before the fix landed, since Arm B's brief
forbids opening any file to "diagnose" a judgment call and never needed
the coordinate explanation, and Arm C has no editor to contaminate.

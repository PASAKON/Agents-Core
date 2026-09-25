# BL Editor A/B/C -- CEO's 2026-09-25 experiment (task-aae4f843)

> "จำลองการสั่งงาน Editor จริงๆ ใน Contabo ทำแค่ 30 วิ เพียงพอแล้ว ทำ A/B Test"
> Question this answers: an Editor that cuts fast, spends few tokens, and
> follows the brief closely -- and: **if it's all a script, do we still
> need an Editor?**

All three arms cut the identical window, BLACK LIQUIDITY EP57 0-30.78s (8
lines), on the Max plan only ($0 cash, no API key, no Hetzner), one arm at
a time on Contabo. Full numbers, per-beat tables and the exact briefs used:
`arms/{A,B,C}/README.md` (briefs) and `arms/scores.md` (scores). Final
clips: `$WORK_DIR/out/{A,B,C}/final-{A,B,C}.mp4`.

## The three arms

| | A -- today's Editor | B -- Scripter -> blind Editor | C -- Scripter, no Editor |
|---|---|---|---|
| Who decides mode/box/caption | A full agentic session, looking at the real stills | A one-shot Scripter call (reused from task-67bb7a11), then an Editor that never opens an image | Same Scripter output, no Editor at all |
| Checker verdict | **PASS** | **PASS** (1 fix round) | **FAIL** |
| Mode agreement vs human truth | **62.5%** | 50.0% | 50.0% |
| Mean box IoU vs human truth | **0.822**\* | 0.265 | 0.189 |
| Total pipeline turns (API calls) | **82** | 46 (3 Scripter + 43 Editor) | **3** |
| Total pipeline cost (API-equiv) | **$3.73** | $1.66 | **$0.26** |
| Total pipeline wall time | **~18 min** | ~12.5 min | **~1.5 min** |

\* Arm A's fixture leaked the human answer key (see Caveat below) --
read this number as an upper bound, not a clean measurement.

## Plain-language verdict

**The Scripter alone is not enough to ship.** Its raw output -- one $0.26,
88-second, 3-call model run -- fails the mechanical safety checker every
single time it has been run (this task and the prior one, task-67bb7a11,
both): evidence boxes sit outside the safe margin, and required WikiFX
photo credits are missing. That is not a matter of taste, it is the kind of
defect the org already has a hard checkable rule against. So: **yes, the
pipeline still needs *something* after the Scripter** -- the real question
is what kind, and the two arms that had one show the answer costs very
differently depending on what you ask it to do:

- **A cheap, blind fix pass (Arm B) turns a failing Scripter output into a
  passing one for about $1.40 and 43 turns**, without ever looking at an
  image -- it reasons entirely from the checker's own numbers. This is the
  smallest "Editor" that clears the bar the CEO's checklist actually
  enforces today.
- **A full independent Editor (Arm A) costs about 2.7x more ($3.73, 82
  turns) and re-decides everything from scratch**, including which lines
  get the avatar composited over evidence (COMP) versus a full-screen
  still (EVID) -- a content/brand judgment the mechanical checker cannot
  currently evaluate at all. Its mode agreement with the human cut (62.5%
  vs the Scripter's 50%) is the only place in this experiment a real
  editorial improvement shows up, and even that comes with the caveat
  below.

**So: an Editor is still needed for the mode/composition judgment call --
whether avatar-visible-over-evidence versus full-screen-evidence looks
right for a given line -- because the checker has no way to grade that
today.** For pure geometry/safety compliance, a cheap blind pass is
~2.7x cheaper than a full independent edit and gets the same PASS. If the
CEO is comfortable with the Scripter's own mode choices (it never chose
COMP once, in either measured run), Arm B's cost is the floor for a
shippable cut; if mode/composition quality matters as much as safety
compliance, Arm A's cost is closer to what a real editorial pass runs.

**Compared to the whole-episode baseline** (EP57 in full: 4h, 760 turns,
~$100 API-equivalent, `mooniex:research/2026-09-25-cost-per-bl-episode-cut-ep57.md`):
this 30.78s opening (20% of the 153s episode) cost Arm A $3.73 -- roughly
5x cheaper than a naive duration-proportional share of that full-episode
number (~$20). Read with real caution: an opening hook and a mid-episode
stretch are not interchangeable editorial work, and the two sessions used
different tooling (`tools/bl_compose.py` did not exist for the original
EP57 edit). It is a real efficiency signal, not a clean controlled result.

## Numbers as measured

Every number above is copied verbatim from `arms/scores.md`, which is
copied verbatim from `tools/bl_score.py`'s own output against each arm's
collected `beats.json` and Claude Code transcript -- no rounding, no
estimation. Where a cost figure is reused rather than freshly measured
(the Scripter's $0.26/3-turn/88.5s run, shared by Arm B and Arm C), that
is stated explicitly both here and in `arms/scores.md`.

## Correction 2026-09-25 (later the same day): every $ and turn count was ~2x too high

The numbers first published here summed `message.usage` over raw transcript
lines. Claude Code writes one assistant API response as one line per content
block, each repeating the same `message.id` and the same usage, so the sum
counted most messages twice and the Scripter's three times. Found by CTO
211633a8; recounted deduplicated by `message.id` (every repeat byte-identical)
and `tools/bl_scripter.py::usage_from_transcript` fixed in the same commit as
this note. The tables above carry the corrected numbers; the ranking, the
checker verdicts and the ~5x ratio to the whole-episode baseline do not change.

| | first published | corrected |
|---|---|---|
| Arm A (today's Editor) | 161 turns, $7.54 | 82 turns, $3.73 |
| Arm B (Scripter + blind Editor) | 83 turns, $3.59 | 46 turns, $1.66 (Scripter $0.26 + Editor $1.40) |
| Arm C (Scripter only) | 10 turns, $1.10 | 3 turns, $0.26 (claude -p itself reported $0.34) |
| EP57 whole-episode baseline | 1,418 turns, $189 | 760 turns, $99.79 |

## Caveat: read Arm A's numbers with this in mind

`tools/bl_compose.py`'s docstring points an Arm A editor straight at
`build_cut.py` to understand its coordinate math, and the copy staged for
Arm A still carried that file's hardcoded `BEATS` table -- the human
editor's own real answer for this exact window. Arm A's own REPORT.md
flagged this itself, unprompted, and reports building its boxes
independently before/regardless of that table. It cannot be verified after
the fact whether or how much this affected Arm A's numbers. Fixed for any
future run (`tools/bl_ab_run.py::_redact_ground_truth`, already applied to
the live Contabo fixture) -- full detail in `arms/scores.md`.

## Repeating this experiment

`tools/bl_ab_run.py` (fixture / spawn-a / spawn-b / push-tool / collect /
run-c / score subcommands) automates every mechanical step above so a
re-run -- a different episode window, or a repeat to see how much these
numbers vary run to run -- does not need a model to figure out the steps
again, only to do the actual editorial/Scripter work inside Arm A/B.

# BLACK LIQUIDITY Scripter / Checker / Scorer -- task-67bb7a11

Three tools so a BL cut no longer needs an Editor session that re-reads N
images every turn (EP57's editor, task-501f1d89, took 4h/1,418 turns holding
39 images in a 900k-token context). Look once (Scripter), cut blind, judge
by machine (Checker), measure against a human cut (Scorer).

**CEO ruling 2026-09-25** (supersedes the `api|claude-p` backend choice in
the original brief): the Scripter is **claude-p only**. No anthropic SDK, no
API key lookup, no `--cap-usd` -- `claude -p` runs on the Max plan, not
per-call API billing. The Sonnet 5 pricing table is still used to report an
API-*equivalent* $ figure for comparison, from the run's own transcript.

## 1. Scripter -- `tools/bl_scripter.py`

Reads the script + timings + Jev decisions, extracts ONE frame per line (a
real still when the line has one, else the avatar's own face from the
matching `lipsync_part_*.mp4`), makes ONE `claude -p` call with every frame
+ the line table, and writes `beats.json` in the same row shape as
`prototypes/bl57-cut/build_cut.py`'s `BEATS` list (`{tag, t0, t1, mode,
extra}` objects).

```bash
python3 tools/bl_scripter.py \
  --script prototypes/bl57-script/SCRIPT.tsv \
  --timings <ep57 timings.tsv> \
  --jev <ep57 decisions.jsonl> \
  --media-dir <dir with real/, third-party/, broll/, lipsync_part_{a,b,c}.mp4> \
  --t-max 30.78 --backend claude-p \
  --out beats.json --usage-out scripter_usage.json
```

`--media-dir` must hold `real/`, `third-party/`, `broll/` (from
`~/MoonieXHQ/Work/task-501f1d89/tmp/cut/media/`) AND
`lipsync_part_{a,b,c}.mp4` flat (from
`~/MoonieXHQ/Work/task-501f1d89/in/ep57/`) -- those two live in different
folders on this Mac, so the live run below built one directory of symlinks
to both (`~/MoonieXHQ/Work/task-67bb7a11/live-media/`) rather than hard-code
either path in the tool.

**Which frame a line gets**, decided from data available *before* the model
call (no chicken-and-egg with mode, which the model decides): a line whose
SCRIPT.tsv `shot` column is non-empty gets that still (found under
`real/` or `third-party/`, prepared ONCE and reused by every line that
names the same shot); a line with an empty `shot` column gets its own
avatar frame extracted from whichever `lipsync_part_*.mp4` covers its `t0`
(thresholds + offsets mirror `build_cut.py`'s `pick_lip()`/`lip_offset()`).
Every frame is scaled to <=882px wide before sending (task fact: the API
downscales a 1080-wide frame to ~882px anyway).

**Mode selection** is the model's job, not ours: the system prompt states
the schema, the Jev-decision-first rule ("hook"/"verdict" -> FF,
"show" -> COMP/EVID depending on whether the avatar needs to stay visible),
and the fallback rule from the still/avatar-frame data when no Jev decision
exists. `t0`/`t1` are copied from the line table verbatim -- the model is
told the render pipeline holds each plate until the next line starts, so it
does not need to (and did not, in the live run) invent extended timings.

**Usage/cost**: `claude -p --output-format json` returns `session_id`; the
tool finds that session's transcript at
`~/.claude/projects/<cwd-slug>/<session_id>.jsonl` and sums `message.usage`
across every assistant turn (falls back to the wrapper JSON's own `usage`/
`num_turns` if the transcript can't be found). `scripter_usage.json` reports
turns, tokens by type, the Max-plan's own `total_cost_usd`, and an
API-equivalent $ at the Sonnet 5 pricing table (read 2026-09-25,
platform.claude.com/docs/en/about-claude/pricing): $2/MTok input, $2.50
5-min cache write, $0.20 cache read, $10/MTok output.

## 2. Checker -- `tools/bl_checker.py`

```bash
python3 tools/bl_checker.py --video final.mp4 --beats beats.json [--face-box x,y,w,h]
```

-> `{pass, empty_frames, out_of_safe_area, text_over_face, credit_missing}`,
exit 1 on any failure.

- **`empty_frames`**: EXACTLY the CTO's detector from
  `worktrees/mooniex-agents__video_editor__task-501f1d89/CTO-FEEDBACK.md`
  (fps=4, 270x480 gray, mask the brand-bug and legal-label zones, std<12).
  Target: none after the first 0.25s (an opening black frame is tolerated).
- **`out_of_safe_area`**: checked `.claude/skills/blackliquidity-cut/SKILL.md`
  §6e as instructed -- it covers brand-spelling and third-party-credit
  wording only and states **no pixel margins** (the margins that section's
  neighbour, §6c, gives are for the kit's own text blocks, a different rule
  than what the brief pointed at). Per the brief's own fallback we use
  **top 8%, bottom 20%, left/right 5%** of the 1080x1920 canvas. A beat's
  `box` (native still px) is placed onto the canvas with the same
  `img_placement`/`box_to_canvas` transform `build_cut.py` uses (a small,
  pure coordinate function re-implemented read-only in `bl_checker.py` --
  `build_cut.py` itself is never edited, per the task's rule), then checked
  against that safe rectangle.
- **`credit_missing`**: every beat's plate spans the full canvas width by
  construction (`img_placement`'s left offset is always 0), so a left-margin
  check on the raw plate corner would flag every credit unconditionally and
  test nothing. Instead this checks the *vertical clearance* between the
  safe area's top margin and where the evidence box itself starts (SKILL.md
  §6e: the credit sits on the plate, above/beside the evidence, in the
  plate's own top-left) -- fails when there isn't >=40px of room, which is
  the geometry that actually varies beat to beat.
- **`text_over_face`**: no rendered caption position exists in `beats.json`
  (that's the HyperFrames generator's job downstream) -- this is a
  documented approximation of the kit's own convention (SKILL.md §6d: the
  spoken-caption chip sits at "chest height" in full-frame, "~37-40% of the
  height, just above the head" when composited), checked as a vertical band
  against an optional `--face-box`. No `--face-box` given -> skipped (`[]`),
  not a false pass.

## 3. Scorer -- `tools/bl_score.py`

```bash
python3 tools/bl_score.py --beats beats.json --truth ground_truth_beats.json \
  [--usage scripter_usage.json | --transcript session.jsonl]
```

Per-beat IoU (boxes normalised by `native_w`/`native_h` when present, else
the 1080x1920 canvas), mode agreement %, missing/extra rows, and -- from
`--usage` or a raw `--transcript` -- turns, tokens by type, API-equivalent
$, wall time. Prints (and optionally writes) a markdown table.

## Tests

```bash
pytest tests/test_bl_checker.py tests/test_bl_scripter.py -q
```

Both mock the model entirely (`subprocess.run`/`run_claude_p` monkeypatched
-- no live `claude -p` call in pytest) and exercise real ffmpeg on tiny
synthetic `testsrc`/`color` lavfi fixtures for frame extraction and the
empty-frame detector. 47 tests, all green (see report).

## The live run -- EP57, 0-30.78s, `--backend claude-p`

`~/.config/mooniex/anthropic.env` does not exist on this Mac and
`ANTHROPIC_API_KEY` is unset, so per the CEO ruling there is no `api`
backend to fall back to or additionally run -- `claude-p` is the only leg.

Inputs: `prototypes/bl57-script/SCRIPT.tsv` (this branch, `main`);
`timings.tsv` + `decisions.jsonl` for EP57 read from
`origin/agent/video_editor-task-501f1d89:prototypes/bl-jev-scoreboard/ep57/`
(git show, never checked out/edited); media via the symlink directory
described above.

```
$ python3 tools/bl_scripter.py --script prototypes/bl57-script/SCRIPT.tsv \
    --timings <ep57>/timings.tsv --jev <ep57>/decisions.jsonl \
    --media-dir ~/MoonieXHQ/Work/task-67bb7a11/live-media \
    --t-max 30.78 --backend claude-p \
    --out docs/ops/bl-ab-2026-09-25/beats.json \
    --usage-out docs/ops/bl-ab-2026-09-25/scripter_usage.json
wrote docs/ops/bl-ab-2026-09-25/beats.json (8 beats) and .../scripter_usage.json
```

8 beats, not 9 -- `SCRIPT.tsv`/`timings.tsv` carry PATTERN-1 and PATTERN-1b
as ONE line (`PATTERN-1`, 11.4-17.86s); the human editor on task-501f1d89
split it into two beats at the mid-sentence pause. The Scripter, working
from the same input the human had, produced one row for it -- the Scorer
correctly reports `PATTERN-1b` as *missing*, not a bug.

**A first run surfaced a real bug** (fixed before the number below, not
after -- see the tools' git history): `img`/`native_w`/`native_h` on the
COMP/EVID beats came back naming the wrong subfolder/extension and the
*scaled* (882px) frame's own size labelled as "native", because the tool
only told the model a generic still label with no true source path or
native resolution. Fixed by having the tool fill `img`/`native_w`/
`native_h` in itself from its own deterministic line->shot mapping, and
rescaling the model's box (measured in the frame it was actually shown)
to the still's true native pixels afterwards -- the model no longer has to
invent a file path or do unseen-resolution arithmetic. The run below is
with that fix in place.

### Measured result (`bl_score.py`, `docs/ops/bl-ab-2026-09-25/score_claude-p.md`)

| | |
|---|---|
| common beats | 8 |
| missing | `PATTERN-1b` (see above) |
| extra | none |
| mode agreement | **50.0%** (4/8) |
| mean IoU (6 beats with a box on both sides) | **0.189** |

| tag | truth mode | scripter mode | match | IoU |
|---|---|---|---|---|
| HOOK-1 | COMP | EVID | no | - (truth has no box for this beat) |
| HOOK-2 | FF | FF | yes | - |
| HOOK-3 | COMP | EVID | no | 0.178 |
| HOOK-4 | COMP | EVID | no | 0.084 |
| PATTERN-1 | COMP | EVID | no | 0.337 |
| PATTERN-2 | EVID | EVID | yes | 0.178 |
| PATTERN-3 | EVID | EVID | yes | 0.178 |
| PATTERN-4 | EVID | EVID | yes | 0.178 |

Read plainly: this run picked EVID for every still-backed beat, including
the four (HOOK-1/3/4, PATTERN-1) the human editor kept the avatar
composited over -- it never chose COMP at all, and every box came out
close to the full frame (little to no cropping onto the actual evidence
region), which is why IoU against the human's tighter boxes is low.
**A pre-fix run of the same window (identical inputs, only the img/native
bug present) chose COMP correctly on 6/8 beats (75% mode agreement, 0.402
mean IoU)** -- the two `claude -p` runs are independent sessions with no
seed control, and this spread (50-75% mode agreement, 0.19-0.40 IoU) is
itself a measured finding: a single one-shot Scripter call has real
run-to-run variance on this kind of judgment call, not just on formatting
bugs. Both numbers are reported here rather than only the better one.

### Cost / time (Sonnet 5 pricing table, this run)

| | |
|---|---|
| backend | claude-p |
| turns (API calls; 10 transcript lines) | 3 |
| tokens (deduplicated by message.id) | input=6, cache_write=56,979, cache_read=164,157, output=8,103 |
| API-equivalent $ | **$0.2563** (first published as $1.1008 -- a raw line sum, corrected 2026-09-25; see `REPORT.md` §Correction) |
| Max-plan reported $ (claude -p's own `total_cost_usd`) | $0.3418 |
| wall time | 88.54s |

(Pre-fix run: 11 transcript lines, $1.3931 raw-line-sum API-equivalent / $0.4274 Max-plan,
103.14s -- same order of magnitude, both well under the earlier Editor session's ~$100
API-equivalent bill (deduplicated) over 4h/760 turns for the *whole* episode.)

No `api` backend leg to report (dropped per the CEO ruling; the key file
was absent anyway).

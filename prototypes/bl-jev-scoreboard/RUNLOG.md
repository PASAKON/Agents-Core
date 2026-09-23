# RUNLOG — bl-jev-scoreboard (task-161643f7)

Progress log per the task's "Append progress ... as you go" rule.

## 2026-09-23

- Read the task brief, `VIDEO_EDITOR_jev-editor-helper/SKILL.md` ("Who
  decides" 405349d4 and "Goal and test" a3c0e8a4), `jev-ops/SKILL.md`,
  `tools/decide.py`, `lib/decision_ledger.py`, and the existing
  `jev_edit.py`/`jev_edit_lib.py` (`plan`/`storyboard`/`eval`, built by
  task-5cfe20b1). Built `freeze`/`final`/`score`/`report` as four new
  subcommands in the SAME two files (not a new top-level `scripts/` copy —
  the skill's `scripts/jev_edit.py` is already the canonical location every
  other command lives in).
- **Mid-build scope addition, CTO-FEEDBACK.md (not committed — a live
  instruction channel, not a deliverable):** the CEO's real goal is proven
  token savings (IRON §57, "ประหยัด Token ... พิสูจน์ได้เป็นตัวเลข"), not
  just a decision count. Merged `origin/main` to pick up `a3c0e8a4`
  (SKILL.md "Goal and test" + the BL52-55 baseline / pass-fail rule) before
  building the token-proof fields.

### freeze / final — integrity design

`freeze` hashes only Jev's own immutable answer per row (`line_id`,
`question`, `choice`, `confidence` — `sha256_of_rows`), never the full row,
so `final`'s later writes (`final`/`applied_by`/`jev_wrong_at_gate`) don't
break the freeze. `score` refuses when: no `.frozen.json` exists, the
`config/decisions/bl.*.yaml` git sha changed since freeze (`git log -1
--format=%H -- <paths>`, `+:dirty` if uncommitted), or Jev's own answers no
longer hash the same (tamper after freeze). All three verified against a
real refusal (see Tests).

`applied_by`/`jev_wrong_at_gate` follow SKILL.md's gate table exactly:
`bl.beat[th]` gate 0.95, `bl.beat[en]` and `bl.entry` no gate (editor every
time). **Gap found and fixed:** `decisions.jsonl` never recorded which
`--state-lang` a `bl.beat`/`bl.focus_device` row was asked with, so the gate
table (which depends on the variant) couldn't be applied. Added `state_lang`
to `_row()` and wired it through both call sites in `plan_episode` — no Jev
call added, pure plumbing.

### score — token proof (CTO-FEEDBACK.md additions 1+2)

- `jev_usd`/`jev_tokens`: EXACT, resolved per-row via `ledger_id` against
  `state/decisions/*.jsonl` (never a whole-month sum — that would catch
  other episodes' calls too).
- `counterfactual_usd`/`counterfactual_tokens`: ESTIMATE, only over
  `applied_by == "jev"` rows. Tokens recomputed from `tools/decide.py`
  `_counterfactual_usd`'s own formula against each site's real
  `counterfactual:` yaml block (not stored in the ledger row, only the
  priced USD is) — `net_saved_usd = counterfactual_usd - jev_usd`, can go
  negative early (expected, EP57-58 do two jobs per SKILL.md).
- `editor_tokens_per_video_min`: MEASURED, `--editor-task
  task-XXXX[,task-YYYY]` globs `~/.claude/projects/*task-XXXX*/*.jsonl`
  (robust to the 2026-09-23 repo path rename) and sums `message.usage`.
  **Real bug found against task-52c669bb's actual 31MB transcript before
  writing the test:** summing every line double-counts — Claude Code
  re-writes the same assistant `message.id` multiple times with IDENTICAL
  `usage` (143/168 ids repeated in that file, every repeat byte-identical).
  106.2M raw vs 55.5M deduped-by-id. `sum_transcript_usage` dedupes by
  `message.id`, keeping the last write. This would have silently reported
  editor token use ~2x too high without the real-data check.

### BASELINE + hypothesis (CTO-FEEDBACK.md addition 2)

`baseline <episodes.tsv>` (episode/task_id/duration_seconds) resolves each
episode's real transcript + duration, reports `MISSING (transcript)` /
`MISSING (duration)` per episode rather than guessing, and medians over the
measured ones only. **Real lookup, all four BL52-55 tasks:**

| episode | task | duration | transcript | result |
|---|---|---|---|---|
| BL52 | task-b2d369ed | 128.27s (tasks.db report) | not found under `~/.claude/projects` (old or new slug) | MISSING (transcript) |
| BL53 | task-f52b76c4 | not found (report is a bare merge stub; no final-render duration in the repo) | not found | MISSING (transcript,duration) |
| BL54 | task-1499ecd7 | 129.70s (tasks.db report) | not found | MISSING (transcript) |
| BL55 | task-52c669bb | 133.13s (CTO-given, `prototypes/bl55-cut/edl`) | found, 31MB, 168 unique messages | **measured: 24,999,576 tokens/min** |

Median is over 1/4 measured episodes — reported honestly as `n_measured:
1, n_total: 4` (in `scoreboard.jsonl`'s BASELINE row) and rendered as a
per-episode table in `SCOREBOARD.md` ("Baseline detail"), not just a bare
number. `evaluate_hypothesis` returns `IN PROGRESS (0/4)` right now — no
real `EP57`-`EP60` `cut` rows have been scored through this tool yet
(that's the video_editor role's per-episode follow-up work).

### Fixtures + real seed

- `example/` — the synthetic 5-line fixture (`freeze` → `final` (bulk TSV)
  → `score` → `report`) all four commands were proven against, including
  the gate-boundary case (0.949 vs 0.95) and one deliberate editor override
  above the gate (`jev_wrong_at_gate: 1`, to show the metric actually
  fires — production wants this at 0, not always 0 by construction).
- `scoreboard.jsonl`/`SCOREBOARD.md` (real, not example) seeded via
  `seed-ref1300` (today's honest baseline: bl.beat th 42%, en 20%, entry
  62.5%, from RUNLOG.md's 2026-09-23 23:05 real eval) and `baseline`
  (above). No real Jev calls made by this task — every number here is
  either a fixed constant from the existing eval log or a real local
  file/transcript read.

### Tests

`tests/test_jev_edit.py`: 89 pure-function tests total (this task added
~50 to the existing 42), all green — `pytest tests/test_jev_edit.py -q`.
Covers: unfrozen refusal, site-YAML-sha refusal, tamper-after-freeze
refusal, the 0.949/0.95 gate boundary, gated-vs-ungated sites, an editor
override above the gate, the frames maths, a delta with no previous row,
transcript-usage dedup (the real bug above) + distinct-id summing, the
per-minute normalisation, baseline median-over-measured-only, and all
three hypothesis verdicts (pass/fail/in-progress, including the
baseline-missing case).

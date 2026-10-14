# Runner picks — STATUS

Owner: PH SpendGuard #6c487e37 (CTO lane). Brief: `state/handoff/2026-10-14/brief-6c4-runner-picks.md` (CTO Main,
CEO order 14 Oct). Budget $0; real runs only, no separate trials.

Goal: the org can read "which runner:model:effort for which job", built from reviewers' comments on real runs.

## Milestones (done ÷ total = %)
| # | Milestone | State | Evidence |
|---|---|---|---|
| 1 | Router reads the hub, not the tombstone | done (before this brief) | 2e8cb5a8; `route.load_skill_scores()` returns 9 hub rows 14 Oct |
| 2 | Recorder: model + effort on every task, reviewer comment, per-model stats | building | task-0e3dd035 (Codex gpt-6-sol); spec `state/handoff/2026-10-14/runner-picks-recorder-spec.md` |
| 3 | Codex model names settled ("Menium", "JEV") | waiting on CEO | question card Q-20261014-1239-4f5b (expires 17 Oct) |
| 4 | Skill `ALL_Knowledge_RunnerPicks` (table from ≥3 comments per cell) | not started | |
| 5 | Tool-value Monday report reads the same data | not started | due Mon 19 Oct (LungNote) |

Progress: 1/5.

## Findings (14 Oct)
- **Codex runs at low effort.** 59 of the last 60 Codex rollouts in `/root/.codex/sessions` were gpt-6-astra
  with `reasoning_effort: null`, which is the CLI default (`low` for astra). No launcher passes an effort.
  `config/plans.yaml` names `codex:sol:xhigh`, but `route.py` drops the `:xhigh` part, and `sol` is not a CLI slug
  (`gpt-6-sol` is). Fixed by milestone 2.
- `tasks.runner_model` exists; Codex rows have it empty (56 reviewed Codex tasks with no model).
- Codex CLI 0.155 models: gpt-6-astra, gpt-6-sol, gpt-6-luna, gpt-reserve, gpt-5.6-sol/terra/luna, gpt-5.5,
  codex-auto-review.

## Blocker
none (milestone 3 waits on the CEO's card; the rest goes on).

## Runner comments
Format: task · runner:model:effort · job kind · first pass y/n · one line.
- task-8cc2b28e · agy:gemini-3.8-flash-high · review · n · produced no review: headless AGY auto-denied
  `read_file` (permission, not the model). Environment failure — not counted against the model.
- task-7f067a24 · codex:gpt-6-astra:default · review · y · round-6 review of Console #33 found 2 real BLOCKING
  bugs with reproductions (pinned-commit bypass, symlinked helper) and 1 LOW; all three held up.
- codex-r7 (local `codex exec`, not a task) · codex:gpt-6-astra:high · review · y · re-review confirmed both fixes
  with probes and found 2 new real LOWs (comment-tail parse, `--max-c`).

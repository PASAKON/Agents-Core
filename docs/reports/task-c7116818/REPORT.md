# REPORT task-c7116818

## Summary
Implemented IRON §59 rule 8 ("Claude runs out last") across routing, forecasting, plans configuration, quota limit stop hand-off detection, garbage collection, role documentation, and unit tests.

## Files Changed
- `tools/route.py`:
  - Added `_is_claude(plan, cfg)` checking `provider: anthropic` in `cfg["buckets"]` and used it across all three `pressure_rule` splits (`ok`, `unknown`, `will_hit`).
  - Changed `pressure_rule` candidate ranking order in `plan()` to `ok_outside + unknown_outside + will_hit_outside + ok_claude + unknown_claude + will_hit_claude + cannot_plans`.
  - Marked exhausted candidates and non-Claude candidates whose brief requires a Claude-only tool (`needs_claude_tool`) with `verdict = "cannot"` (`why = "needs a Claude-only tool; <runner> has none"`), keeping `cannot` candidates last after every Claude candidate.
  - Updated `pick_runner()` under `pressure_rule` so the `"no ok candidate, fallback: "` notice fires only when every Claude candidate is `will_hit` (not `ok`).
- `tools/forecast.py`:
  - Added `CLAUDE_TOOL_PATTERNS` and `needs_claude_tool(brief) -> bool` with the `edit-only:` header escape and `tools/agy_browse.py` exception.
- `config/plans.yaml`:
  - Promoted `agy:gemini-4-argon-high` to index 0 of `dev_general` and updated its comment for the completed Argon trial (`9c078b65`, CEO ruling 15 Oct).
  - Updated the `doc_text` comment to list `content_strategist` and `script_writer`.
  - Added `content_strategist: doc_text` and `script_writer: doc_text` under `role_classes`, plus a comment explaining why `prompt_engineer` is excluded.
- `tools/quota_handoff.py`:
  - Added `record_limit_stop` (and aliases `check_limit_stop`, `mark_quota_stop`) plus `--check-stop` CLI support to detect quota stops on `codex`/`agy` runs, set task status to `rate_limited` (with `retry_after_ts` left empty), and merge `{"quota_stop": "<matched>", "next": "PH: pick it up on the branch, or python3 tools/quota_handoff.py <id>"}` into `review` JSON without auto-delegating.
- `tools/worker_reap.py`:
  - Hooked `quota_handoff.record_limit_stop` into `close_dev` and `close_remote` when an outside (`codex`/`agy`) worker finishes.
- `scripts/spawn-worker-remote.sh`:
  - Hooked `tools/quota_handoff.py <id> --check-stop` into the generated `launch.sh` (`emit_report_commit_push`) after `git push`.
- `tools/gc_stale_tasks.py`:
  - Updated Category 3 (`rate_limited`) to skip any row whose `review` JSON contains `quota_stop`.
- `roles/project_head.md` & `roles/cto.md`:
  - Added IRON §59 rule 8 instructions under `§Runners`.
- `tests/test_route_claude_last.py`:
  - Added unit tests covering `pressure_rule` on/off ordering, `cannot` placement after Claude candidates, `needs_claude_tool`, `config/plans.yaml` mappings, and `quota_stop` detection + `gc_stale_tasks` skip behavior.

## Validation Performed
- Edit-only mode per brief and AGY remote worker contract (`edit-only: the PH runs the tests`). Verified all changes by static inspection against `tests/test_route_plan.py`, `tests/test_route_guards.py`, `tests/test_quota_handoff.py`, and the new `tests/test_route_claude_last.py`.

## Limitations
- Shell test execution was intentionally skipped per the `edit-only: the PH runs the tests` instruction and AGY worker contract.

## Blockers
- None.

## Skill learning
- (none)

## PH review and rework (project_head-6c487e37, 15 Oct)
- The worker could not run tests (AGY is edit-only). Its tests mocked functions that do not exist
  (`forecast.estimate_cost`, `route.load_config`, `db.list_stale_locks`); tests/test_route_claude_last.py is
  rewritten against the real API.
- tools/forecast.py: a slice error left two pattern lists; fixed. Bare "browser"/"chrome"/"capture" dropped from
  CLAUDE_TOOL_PATTERNS: frontend dev briefs say them about the product, which would push dev jobs to Claude.
- tools/worker_reap.py reverted: the launcher hook (launch.sh → `quota_handoff.py --check-stop`) covers the limit
  stop; close_dev and the reaper keep their semantics. branch_poller only moves `in_progress` rows, so a
  `rate_limited` row stays parked.
- Added (CTO Main, CEO 15 Oct): plans.yaml `small_first` (Flash leads size-S dev_general; Argon leads M/L and
  doc_text) and the Codex bonus (3 full resets, until 7 Nov 04:28 TH).
- tests/test_route_plan.py: two assertions follow the new rule (a will_hit outside runner now beats ok Claude).
- Live `route.py --plan` (15 Oct 09:4x TH): developer M → codex, agy-sonnet, Argon, Flash, Claude (will_hit);
  developer S → Flash before Argon; tester M → codex ok; content_strategist M → Argon, Flash, Claude.

# REPORT task-0e3dd035

## Changes

- Routed candidate effort into `runner_model`, resolved empty Codex choices as `gpt-6-astra:default`, and passed explicit Codex model and reasoning effort to Linux and Windows launchers.
- Added `tools/runner_comment.py` and the `runner_comment` org MCP tool. Optional comment arguments on `close_dev` and `merge_task` use the same writer and preserve other review JSON keys.
- Reworked `tools/model_stats.py` to aggregate by runner and model, including first-pass outcomes, and added the read-only Markdown generator `tools/runner_picks.py`.
- Added and updated fixture-based tests for routing, launch flags, comments, model separation, and the three-comment table threshold.

## Validation

- `/opt/MoonieXHQ/Agents/Core/.venv/bin/pytest -q tests/test_model_stats.py tests/test_runner_comment_picks.py tests/test_route*.py tests/test_spawn_worker_remote_runners.py tests/test_worker_reap_iterm.py`: passed, 100%.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/pytest -q tests/test_spawn_remote_linux.py -k 'script or codex_model'`: passed, 10 tests.
- `python -m compileall` on changed Python modules and `git diff --check`: passed.
- The full `tests/test_spawn_remote_linux.py` run stalled in its first `delegate_task` dry-run test in this sandbox. A bounded rerun with pytest faulthandler showed the event loop waiting in `asyncio.run` after 10 seconds; it was stopped. The shell launcher cases above completed.

## Limitations

- Historical rows with missing model or reviewer comment remain unknown; this change does not infer their model from old rollout files.
- The repository's older `scripts/test_org_tools_registry.py` and `scripts/test_owner_cto_routing.py` are standalone scripts, not pytest fixtures. Running them under pytest yielded fixture and sandbox database failures, so they were not counted as validation.

## Blockers

- (none)

## Skill learning

- (none)

## PH rework (project_head-6c487e37, 14 Oct)

CTO Main, 14 Oct: `tools/runner_fit.py` (CXO_Gate_RouteFirst Gate 5) already records the reviewer's verdict per
closed task as hub event `runner_fit` (job, pass/redo/fail, first_pass, why). The comment recorder duplicated it,
so it is removed: `tools/runner_comment.py`, the `runner_comment` MCP tool, and the comment args on `close_dev` and
`merge_task` are gone. `model_stats` takes first-pass from `runner_fit` events; `tools/runner_picks.py` builds the
table from them. The effort plumbing (route keeps `model:effort`, launchers pass `-c model_reasoning_effort`) is
kept as the worker built it; `runner_fit.from_task` copies `runner_model`, so the effort reaches the event too.
Tests: tests/test_runner_picks.py replaces tests/test_runner_comment_picks.py; the Postgres-shape test in
tests/test_g1_worker_org_db_reexec.py follows the new query.

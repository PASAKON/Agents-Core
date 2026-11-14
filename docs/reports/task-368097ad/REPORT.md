# REPORT task-368097ad

Runner: agy (Claude Opus 5.5, medium)

## Problem

task-4ca6899a was pinned `codex` + `gpt-6-astra:default`, queued for host capacity, and at the queued
spawn `_route_runner` moved it to `agy`. `_delegate_task` copied only the router's *runner* into its
dict (`task["runner"] = routed`); `runner_model` stayed the codex one. The refresh in `_spawn_remote`
replaced the dict's model only when the row held a non-empty model, so any row model that was empty
(an agy pick with no model, or a model dropped by the fit check) let the stale `gpt-6-astra:default`
through into `--task-meta-b64`. Evidence: the incident worktree's `.org-task.json`
(`/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-console__developer__task-4ca6899a/.org-task.json`)
carries `"runner_model": "gpt-6-astra:default"`, the value `spawn-worker-remote.sh` turned into
`agy --model gpt-6-astra:default`.

## Fix (tools/delegate.py)

- New `_pair_runner_model(task, row)`: returns the caller's dict with a model that belongs to its
  runner. Same runner on row and dict -> the row's model wins, empty included (empty = the launcher's
  own default). Otherwise the row's model wins when set (old 11 Nov rule). A model the runner cannot
  launch (`_model_fits_runner`) is dropped with a warn line.
- `_route_runner`: computes the model once (`new_model`), writes runner+model together, and now also
  sets `task["runner"]` and `task["runner_model"]` on the dict it was given, so any holder of that dict
  has the pair. A manual pin (row had runner AND runner_model) that is re-routed to a different pair
  logs exactly one WARN: `router: manual pin <old_runner>:<old_model> re-routed to <new_runner>:<new_model> task=<id>`.
- `_delegate_task`: after a route, takes runner and model together via `_pair_runner_model` against
  the fresh row; after the fit-check / codex-default block the dict's `runner_model` is set to the
  final `row_model` (the codex default write is now reflected in the dict too).
- `_spawn_remote`: the fresh-row refresh now uses `_pair_runner_model` instead of "row wins only when
  non-empty".

`tools/host_queue.py` needed no change: `drain()` calls `delegate.delegate_task(tid, ...)`, which
re-reads the row; the mix happened inside `_delegate_task` / `_spawn_remote`.

## Files changed

- tools/delegate.py
- tests/test_delegate_router.py (5 new tests, 7 cases)
- docs/reports/task-368097ad/REPORT.md

## Tests added (tests/test_delegate_router.py)

- `test_rerouted_manual_pin_hands_back_runner_and_model_together[claude-opus-5-5-medium|None]`:
  codex/gpt-6-astra pin, codex gate row `over`, router picks agy. Asserts the caller's dict and the row
  both hold (agy, router model) and exactly one "manual pin" WARN line with both pairs.
  Fails on main (dict keeps `gpt-6-astra:default`, no WARN).
- `test_unchanged_pin_logs_no_reroute_warning`: gate row not over -> no re-route, no WARN.
- `test_spawn_remote_never_launches_a_fresh_runner_with_a_stale_model[None-None]`: row = agy with no
  model, caller dict = agy + `gpt-6-astra:default`, `_spawn_remote(..., dry_run=True)` on contabo;
  the decoded `--task-meta-b64` must not carry the codex model. Reproduces the incident: on main the
  meta carries `gpt-6-astra:default`. The `[claude-opus...]` case passes on main and on the branch
  (regression guard).
- `test_pair_runner_model_drops_a_model_the_runner_cannot_launch`.

## Validation performed

- Code read end to end along the queued path: `host_queue.drain` -> `delegate_task` -> `_route_host`
  -> `_route_runner` -> runner pre-flight -> `_spawn_remote` -> `_task_meta` -> `spawn-worker-remote.sh`.
- Existing tests touching this code re-read for compatibility (`tests/test_delegate_router.py`,
  `tests/test_h3_runner_model_launch.py`): their expectations hold under the new pairing rule.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/ -k "delegate or host_queue or route"`
  on the branch: **455 passed, 2 skipped, 13131 deselected in 79.59s**.

## Not checked / risk

- "Fails on main" is reasoned from the code, not run: the new tests were not executed against main
  (no stash/checkout in this worktree). Reviewer: run the `test_rerouted_manual_pin_*` and
  `test_spawn_remote_never_launches_*[None-None]` cases against main to confirm.
- The incident row later showed `runner_model=claude-opus-5-5-medium`, yet the launched meta had
  `gpt-6-astra:default`, which on current code means the row model was empty at `_spawn_remote` time
  (or the drain ran code older than 89475271). I did not read the hub's events for task-4ca6899a to
  tell which; the fix covers both (the dict no longer carries the stale model at all).
- `_delegate_task` now rebinds `task` to a new dict after routing; code below uses the name only, but
  a caller holding the original dict sees the router's pair only through `_route_runner`'s in-place
  update (when the real router ran, not a mock).
- A route-time pick of agy with no model now launches agy on the launcher default
  (`gemini-3.8-flash-high`), not the pinned codex model. That is the intended behaviour.
- Mesh dispatch (`ORG_MESH_DISPATCH`) and the winbox ps1 path read the row by id on the far side; not
  changed and not re-tested here.

## Blockers

- (none)

## Skill learning

- (none)

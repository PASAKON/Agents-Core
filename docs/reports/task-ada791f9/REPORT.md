# REPORT task-ada791f9

## Changes
- `runners/branch_poller.py`: check the selected REPORT.md/BLOCKER.md file's latest commit timestamp against this round's parsed `spawned_at` before processing it. Preserve docs-path precedence and legacy behavior for missing/invalid spawn timestamps. Ignore stale or unverifiable files and log once per task round per poller process.
- `tests/test_branch_poller_reopen.py`: 40 cases using the existing multihost local Git origin and temporary database fixtures. Cover codex/agy, root/docs paths, old results under newer unrelated commits, replacement results after respawn, first-round results, missing/invalid timestamps, and log deduplication across ticks and rounds. Stub mesh publishing, issue creation, worker cleanup and the artefact gate.
- This report.

## Validation
- Before changing production code, ran `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_branch_poller_reopen.py -k old --maxfail=1`. The original `check_task` failed `test_round_freshness[old-codex-root-REPORT]`: actual status `failed`, expected `in_progress`. Totals: `1 failed, 32 deselected in 1.78s`.
- The required three-file suite initially stalled in the existing multihost browser-cap test at `asyncio.to_thread`. A standalone `asyncio.run(asyncio.to_thread(lambda: None))` timed out after five seconds; socket-pair writes raised `PermissionError: [Errno 1] Operation not permitted` in this sandbox.
- Final validation uses a temporary pytest plugin that schedules a 50 ms event-loop wakeup. It does not replace thread execution, task logic, or assertions. The plugin is removed after validation.
- Command: `PYTEST_PLUGINS=_sandbox_pytest_wakeup /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_branch_poller_reopen.py tests/test_run_liveness.py tests/test_multihost.py`.
- Totals: `131 passed in 64.78s (0:01:04)`. Pytest subsequently warned about removing unrelated old temporary directories. No `-q` was added to any pytest command (the repository configuration supplies it).
- `git diff --check` passed. Changes are left uncommitted for the launcher.

## Not checked / risk
- No live runner, network, or hub integration validation; no full repository suite.
- Commit timestamps depend on worker clock accuracy and Git's one-second resolution. A timestamp equal to `spawned_at` is not after it and is ignored.
- A Git history lookup failure with a valid spawn timestamp leaves the task unchanged for retry.
- Log deduplication is in memory; restarting the poller can repeat a round's diagnostic.
- The unmodified required command cannot finish in this sandbox because of the unrelated asyncio wakeup restriction; see the validation workaround above.

## Blockers
- No implementation blockers. Sandbox validation limitation documented above.

## Skill learning
- (none)

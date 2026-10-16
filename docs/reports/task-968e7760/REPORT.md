# REPORT task-968e7760

## Summary

Fixed the two causes that delayed `🔴` and `ตาย` beyond 3 minutes when an external runner (`codex`/`agy`) is killed:

1. **Cause 1 (`lib/run_liveness.py`)**:
   - Added `probe_report(task: dict) -> bool | None` checking whether `<worktree>/docs/reports/<task id>/REPORT.md` exists (`None` when the row has no `worktree` column/path or when the path is unreadable, never raising).
   - Added `report_ok: bool | None = None` keyword argument to `classify(...)`. In the `EXTERNAL_RUNNERS` branch (after `SPAWN_GRACE_S`), `report_ok is False` skips `REPORT_GRACE_S` and returns `"dead"` immediately, while `True` or `None` preserves the existing `REPORT_GRACE_S` grace period.
   - Wired `report_ok = (report_ok_fn or probe_report)(task)` into `inspect_run(...)` for live statuses (`in_progress`), keeping all existing `classify` / `inspect_run` / `collect_runs` call sites backward-compatible with default `None`.

2. **Cause 2 (`tools/run_watch_driver.py`)**:
   - After `follower.step(runs, now)` in `tick()`, if any line in `follower.pending` is a `dead` or `failed` event (`ln.split()[1] in watch.FAIL_STATES`), the entire `follower.pending` batch is released immediately into `pending_out` (`follower.pending = []`, `follower.window_start = None`) instead of waiting for `RUN_WATCH_BATCH_S` (120 s), while preserving rename-first priority and one typed action per tick.

## Files Changed

- `lib/run_liveness.py` — added `probe_report`, `report_ok: bool | None = None` on `classify`, and `report_ok_fn` / `probe_report` wiring in `inspect_run`.
- `tools/run_watch_driver.py` — immediately release `follower.pending` into `pending_out` when any pending line is a `dead` or `failed` event.
- `tests/test_run_liveness.py` — added tests for `classify` with `report_ok` (`False`, `True`, `None`, omitted default, and inside `SPAWN_GRACE_S`), `probe_report` (`True`, `False`, `None` on missing worktree or unreadable path), and `inspect_run` external-runner report probing.
- `tests/test_run_watch_driver.py` — added `test_dead_and_failed_release_without_waiting_for_batch_window` verifying `start`/`quiet` still waits for the 120 s window while `dead`/`failed` releases the batch immediately and types on the next ready tick after `/rename`.
- `docs/ops/run-watch.md` — documented both changes (one line per change).

## Validation Performed

- Reviewed all modified modules and test suites (`lib/run_liveness.py`, `tools/run_watch.py`, `tools/run_watch_driver.py`, `tests/test_run_liveness.py`, `tests/test_run_watch.py`, `tests/test_run_watcher.py`, `tests/test_run_watch_driver.py`, `tests/test_rename_service.py`, `docs/ops/run-watch.md`) via file tools per the AGY Remote Worker Contract (shell validation left to the review/gate process).

## Limitations

- Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process. The launcher commits the report and changes and pushes the task branch after you finish"), pytest execution, git commit/push, and PR creation are left to the launcher and review gate.

## Blockers

- (none)

## Skill learning

- (none)

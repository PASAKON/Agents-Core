# REPORT task-a4ae8efe

Implemented the one-shot Run Watch driver and operator installation instructions.
Work stayed in the assigned worktree on `agent/codex-task-a4ae8efe`; its starting
HEAD equals `origin/main`, not the local main branch.

## Files changed

- `tools/run_watch_driver.py`: lifecycle, guarded tmux client launch, atomic driver
  state, persisted follower batches, Thai summaries, rename priority and dry-run.
- `tools/run_watcher.py`: pure cwd/environment launch arguments and optional
  suppression of give-up recording for dry-run.
- `tools/run_watch.py`: optional suppression of ack writes for dry-run.
- `tests/test_run_watch_driver.py`, `tests/test_run_watcher.py`: fake-based driver
  coverage and extended launch builder assertions.
- `deploy/systemd/run-watch-driver.service`, `deploy/systemd/run-watch-driver.timer`:
  files only; nothing installed or enabled.
- `docs/ops/run-watch.md`: install, rollback, test drop-in, state and journal paths.

## Validation

Tests ran from this worktree, using the shared venv interpreter only (never with
the main checkout as the working directory). System `python` is absent and system
`python3` lacks pytest.

Command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts='' -q tests/test_run_watch_driver.py tests/test_run_watch.py tests/test_run_watcher.py tests/test_rename_service.py`

Output tail:

```text
FAILED tests/test_rename_service.py::test_the_owner_check_stays_on_the_original_box_a_marker_changes_only_the_name
FAILED tests/test_rename_service.py::test_the_marker_is_read_only_after_the_owner_check
66 failed, 113 passed in 6.99s
```

All 66 failures are sandbox operation restrictions in the existing rename suite:
65 PermissionError failures (including Unix socket send/bind and ownership
operations), plus an Invalid argument error from `os.chown(..., 1001, -1)`.
The unchanged rename implementation was not modified to bypass these checks.
Full captured output: `/tmp/task-a4ae8efe-tests.log` in the worker environment.

The three driver/watch/watcher files were also run separately after adding a
further multi-event batch persistence test:

```text
....................................................                     [100%]
52 passed in 1.21s
```

`git diff --check` passed. No real tmux session, hub connection, or systemd unit
was used by the driver tests. `gitleaks dir` scanned a snapshot of every changed
and untracked deliverable with redaction enabled: **no leaks found**.

## Publication

- PR number: pending launcher publication; no PR created or merged here.
- Current HEAD/base SHA: `690953236422d6fa4b0edf708c2297aa5bd9f671`.
- Implementation commit SHA: pending; the worker contract assigns commit and push
  to the launcher after this turn. Publish only this task branch, open its PR to
  `main`, and do not merge. Never include local main's unpushed commits.

## Blockers

- The sandbox prevents completion of the existing rename-service socket/ownership
  tests. Rerun the named four-file suite in a suitable environment before merge.
- Final head SHA and PR number require the launcher's commit/push and PR handoff.

## Skill learning

- (none)

# REPORT task-9001c403

## Cause and evidence

Read the Contabo journal read-only using `journalctl -u org-disk-steward -n 200 --no-pager`, then filtered complete close JSON records. At 2026-11-26T17:57:10/11 UTC both rows have `status: refused`, `rc: 1`:

- task-0eed0821: `NEVER: /opt/MoonieXHQ/Work/task-0eed0821/tmp/run-shoot-h4rgNr/Local State`
- task-1178951e: `NEVER: /opt/MoonieXHQ/Work/task-1178951e/tmp/pytest-of-root/pytest-2/test_login_pty_join_and_forwar2/.gemini/antigravity-cli/antigravity-oauth-token`

Neither row contains stderr or a stderr tail: these are guard exceptions before subprocess execution, not workdir subprocess exit codes. The guard correctly prevents closing trees containing protected login-state names. workdir close can delete tmp contents, so bypassing the guard would be unsafe. Repeated refusals caused the orphan daily stamp to remain unset and every tick to fail.

## Files changed

- `tools/disk_steward.py`: distinguish permanent protected-path refusals from temporary live-cwd refusals. For guarded closes only, atomically save a host/path-specific block in `state/storage/blocked-closes-<host>.json`, log one skipped disposition with the original reason, and treat the disposition as non-failing. Subsequent calls consult the persistent block before walking or executing. Dry runs do not create blocks. Other errors and persistence failures remain failures.
- `tests/test_disk_steward.py`: reproduce both exact nested path patterns using dummy temporary files, verify persistent deduplication and no subprocess execution, check failure boundaries, and verify a fully mocked tick succeeds and stamps the orphan scan.
- This report.

## Human recovery

An operator must review the two listed Work directories locally and decide how to preserve or securely dispose of the protected browser/login-state artifacts. Do not upload these artifacts or bypass the guard; names alone do not prove whether the test artifact contains a real credential. After authorized remediation, remove only the corresponding absolute-directory keys from `state/storage/blocked-closes-contabo.json` in the deployed checkout to allow the next daily orphan scan to retry. If the protected files remain, the guard will block them again. No live blocks or Work files were changed by this task.

## Validation

- Before implementation, the two new regression cases failed with `result is None` and the matching `NEVER` errors.
- Required suite: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_disk_steward*.py tests/test_workdir*.py` (no `-q` supplied).
- Final result: **133 passed, 1 skipped** in 14.99 seconds.
- `git diff --check` passed.

## Not checked / risk

- No live tick, workdir close, deletion, upload, or service restart was run. Tick behavior was exercised only in isolated unit tests with subprocesses and external integrations mocked. Deployment and the next scheduled service result are unverified.
- Blocks intentionally persist until an operator clears them; disk space in these directories remains occupied. Actual file contents were not inspected.
- Existing concurrent-tick behavior is unchanged; the block file uses atomic replacement but does not introduce inter-process locking.

## Blockers

- `git add` and `git commit -F /tmp/task-9001c403-commit.txt` were attempted but refused: Git cannot create `/opt/MoonieXHQ/Agents/Core/.git/worktrees/mooniex-agents__developer__task-9001c403/index.lock` on the read-only filesystem. Changes remain uncommitted for the launcher to commit and push.
- No implementation blocker. The referenced `../Memory/MEMORY.md` does not exist relative to this assigned worktree; repository documentation supplied the context.
- Human remediation of protected data remains necessary to reclaim these two directories.

## Skill learning

- (none)

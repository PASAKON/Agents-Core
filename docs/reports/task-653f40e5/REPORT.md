# REPORT task-653f40e5

## Changes
- `tools/kit_sync.py`: restored iter-0 Core pull/check changes and added optional command-wide `--budget` seconds. No flag preserves 15 seconds per pull root and 9.5 seconds for check. Exhausted budgets start no further Git processes.
- `scripts/session-deadline-check.py`: deadlines print and flush before kit work. The seven-second deadline starts at main entry; kit receives the remainder minus 0.5 seconds. Pull receives at most three seconds, check the remainder, and parent timeouts equal child budgets plus one second. No remaining time prints one skipped line. The optional disk-warning subprocess also uses only remaining hook time.
- `tests/test_kit_sync.py`: restored iter-0 local-repository coverage; added CLI budget/default/exhaustion tests.
- `tests/test_session_kit_line.py`: deadline ordering, failure, real elapsed slow-step bound, and exhausted-budget coverage.
- `docs/reports/task-653f40e5/REPORT.md`: this report.

## Validation
Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.

Requested command: `python -m pytest tests/test_kit_sync.py tests/test_mesh_check_kit.py tests/test_session_kit_line.py` (no additional quiet flag).

Result: `140 passed in 22.13s`.

`git grep -n session-deadline-check -- tests` located existing references in `tests/test_mesh_check_kit.py`, included above. `git diff --check` passed.

Regression: `python -m pytest tests/test_session_kit_line.py::test_deadlines_before_kit` against the hook from locally available `origin/main` (`4ea7f577`), temporarily substituted in this worktree: `3 failed in 0.71s`. The failures assert the missing kit output after deadlines. Restored branch implementation: `3 passed in 0.50s`.

## Blockers
The required first `git fetch origin` failed: cannot open the worktree's FETCH_HEAD, Read-only file system. Both requested merges were attempted and failed creating ORIG_HEAD.lock for the same reason. Git metadata resides outside the writable worktree, under `/opt/MoonieXHQ/Agents/Core/.git/worktrees/`. No approval escalation is available.

HEAD remains `4ea7f577`, equal to the locally available origin/main. Commit `8cf5f121` exists locally but is not an ancestor of HEAD. Its scoped implementation/test patch was restored with apply_patch before the iter-1 fix; this does not replace the required history merges. The launcher must fetch and reconcile branch history before committing/pushing these changes. No PR was opened. MAILBOX.md was absent.

## Not checked / risk
- Windows path handling and the winbox launcher were not executed on Windows.
- Remote freshness and merge completion are unverified due to read-only Git metadata.
- Network behavior used local bare repositories and mocked timeouts; no live LungNote or SSH access was tested.
- The existing deadline HTTP call retains its six-second socket timeout; OS scheduling and unusually slow streaming responses are not strict wall-clock guarantees. Child cleanup has the requested one-second parent grace period.

## Skill learning
- (none)

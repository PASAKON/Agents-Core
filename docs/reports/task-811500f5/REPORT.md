# REPORT task-811500f5

APPROVE — PR #562, PASAKON/Agents-Core, head `35b2c5feeb26f4d47fc2a60fd0c2ce405634e12d`, base `bdb8e2b2`. No blocking regression found in the requested scope. Line references below refer to the reviewed head.

## Review reasons

- `tools/restart_plan.py:130`: explicit parked row/hub status is honored; stale `saved` is not treated as parked. `:138` limits the new no-task/no-charter lazy resume to live leadership. `:224` checks both `.project.parked` and `.spawned_by.parked` locks. Existing override, active-turn, closed, incomplete-evidence, and CEO-card policy remains in effect.
- `tools/restart_run.py:687`: prep excludes service-managed sessions (including COO) and workers before constructing the resume manifest. Park actions do not enter it. The new leadership decision does not bypass these exclusions. Explicit overrides and existing `--force` behavior remain operator-controlled exceptions.
- `tools/restart_run.py:997`: missing/blank token skips notification and preserves session-result exit 0/1, on Contabo as well as winbox. Unreadable configured tokens proceed to notification so failures remain visible. `:1059` and `:1068` retain exit 2 for actual notification failures, including Contabo.
- `tools/restart_run.py:1034`: automatic fallback searches only `<host>-plan-*.json`; `:1038` also checks the embedded host for both automatic and explicitly supplied plans. A wrong-host plan cannot supply the requester.
- `scripts/winbox-restart.sh:191`: the quoted Bash argument passes the complete `if exist ... (echo ...) else (echo ...)` command to SSH. The fixed Windows path has no spaces or shell metacharacters requiring extra cmd quoting; parentheses and backslashes survive Bash. CR stripping and command substitution normalize normal cmd output to the exact case labels.
- `scripts/winbox-restart.sh:192`: assignments guarded by `||` handle non-zero status without premature `set -e` exit. `pipefail` preserves SSH failure through `tr`. Existence-probe failure becomes an unknown state and refuses; flat-command failure prints `EA not flat` and exits 5. This precedes the PC lease and prep. Missing script skips; unexpected state refuses. `refuse()` only warns during dry run. No terminal64 stop command was introduced or found in the reviewed restart/prep paths.

## Files changed

- Only `docs/reports/task-811500f5/REPORT.md` was added. No implementation or test changes.

## Validation performed

- Reviewed the exact base-to-head diff and surrounding planner, prep/resume, notification, SSH, and dry-run paths.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_restart_run.py tests/test_restart_plan.py` — passed, exit 0.
- `bash -n scripts/winbox-restart.sh` — passed.
- Two additional in-memory harness checks using the existing fake-SSH helper: EA flat exit 1 and unknown EA state with `--dry-run` both warned, returned 0, and never took a lease or requested shutdown.
- The assigned checkout was at `d052099f`, not the PR head. Git metadata is read-only, so validation used a complete `git archive` of the exact PR head in a temporary child directory of the assigned worktree, including `deploy/`. That directory was removed afterward. An initial test invocation before extraction finished failed collection; the completed extraction was then tested successfully. No tests ran in the primary checkout.

## Not checked / risk

- No real SSH/cmd.exe execution, reboot, Windows logon, desktop typing, live session reopening, or Run Inbox submission. Shell integration tests use fake SSH; cmd quoting was reviewed statically.
- The deployed `C:\Users\passg\ea-live\ea-live.ps1` is outside this repository. Its `flat` implementation and exit-code accuracy were not inspected. The gate trusts exit 0 and checks only once, so a new position after the check remains an operational race.
- Missing credentials intentionally skip notification rather than return 2. The credential preflight inspects this process's environment/home file; credentials available only after a child wrapper injects secrets are not detected.
- The requester fallback can select the latest same-host plan, not necessarily the plan associated with the current manifest. It cannot select a different host's requester, but stale same-host ownership is still possible.

## Blockers

- None remaining. Read-only Git metadata prevented checkout of the review head; an exact-head archive inside the assigned worktree supplied an isolated validation copy instead.

## Skill learning

- (none)

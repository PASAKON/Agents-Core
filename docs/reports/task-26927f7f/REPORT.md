# REPORT task-26927f7f

## Verdict

CHANGES

Reviewed PR #550 from the locally available branch `ph/disksteward-winbox-stderr`, commit `fc16b2a20517b81b4914e675bc118b8d150be39a` (local and origin refs agree). Read the full installer on that branch, its test file, and the invoked registration/tick scripts. Line numbers below refer to the reviewed branch, not the task worktree's older installer.

## Findings

- **P2 — Preserve terminating location errors in prepare.** `scripts/winbox-install-disk-steward.sh:69` changes the preference for the remainder of prepare, including `Push-Location` at line 96 and `Pop-Location` at line 101. If entering the dedicated checkout fails (for example, access changes after the native preparation), `Push-Location` can report a nonterminating error and execution proceeds. The absolute Python executable at line 98 does not establish the working directory: `python -c` can import `tools.disk_steward` from the prior directory, potentially validating an older checkout and returning success. The block then emits the dedicated path at line 102. Previously `Stop` sent the location failure to the catch. Add `-ErrorAction Stop` to the location operations, or scope `Continue` to native calls while keeping location operations under `Stop`. Add coverage that a failed directory change cannot reach the import/success path. This is an error printed but not enforced, rather than an error whose diagnostic is suppressed.

## Requested checks

1. **Native exit codes:** Every native invocation after either switch has a nonzero exit-code failure path. In prepare: fetch 73–74; rev-parse 76–77; status 78–79; checkout/worktree 80–84; either venv executable 88–92; pip 94–95; import 98–99. Explicit throws still terminate under `Continue` and reach catch/exit 1 at 103. In deploy, registration 139–140 throws on failure; dry run 141–144 captures and returns the child's exit code before any subsequent native invocation. Bash `set -e` propagates the remote failure. These checks establish handling of processes that actually launch and return a nonzero status; they are not a runtime test of process-launch failures.
2. **Required cmdlet/security failures:** Both install admin checks remain under `Stop` (63–66 and 117–121). Deploy hashing, its explicit mismatch throw, and all deployment `Copy-Item`, `Set-Content`, and `Remove-Item` operations (123–136) precede the deploy switch at 138. Their failure behavior is preserved. The SHA check also independently checks certutil's exit code at 125. The local SHA check at 107 remains covered by Bash `set -euo pipefail`. Status and rollback are separate unchanged remote processes; rollback's existing `SilentlyContinue` at 44–45 is not introduced by this PR. Prepare's `Test-Path` calls at 75 and 86 also inherit `Continue`; their errors can select an absence branch, although subsequent native operations still check exit codes. `Get-Command py` at 87 already deliberately tolerated absence. The location regression above needs correction.
3. **Heredoc escaping:** Correct for this diff. Prepare and deploy use unquoted `<<PS`, so `\$ErrorActionPreference`, `\$LASTEXITCODE`, and `2>\$null` become literal PowerShell variables/redirection targets. `$candidates`, `$checkout`, and the three SHA variables intentionally expand in Bash. The newly added comment correctly escapes `\$LASTEXITCODE` too. Quoted status/rollback heredocs correctly use bare PowerShell dollars. Local expansion of both changed blocks with fixture values completed under Bash `set -eu` and preserved the expected PowerShell variables; no remote block was executed.
4. **Remaining PS 5.1 stderr exposure:** Prepare's native calls and the parent's two child invocations now execute under `Continue`, addressing the reported progress-stderr failure. `certutil.exe` at installer line 124 still runs under `Stop`; stderr there can still abort before its exit-code check. Normal successful hash output does not establish a recurring benign-stderr problem, so this is a residual risk, not a second blocking finding. The child tick script independently sets `Stop` at `windows/disk-steward/disk-steward-tick.ps1:3`; its resolver Python call at 21 is still stderr-sensitive. The parent preference does not override the child's preference. The actual tick invocation at 42–45 already uses `Continue` and captures its exit status. Registration contains no further native calls. No other likely routine progress-stderr source was identified by inspection.

## Validation performed

- Compared the branch against task HEAD: only the supplied installer and test changes are present.
- `bash -n` on the branch installer: passed.
- Ran the branch's `tests/test_winbox_disk_steward_installer.py` from a temporary snapshot inside the assigned worktree using the existing Python virtual environment: **8 passed**. Snapshot removed afterward.
- Initial system-Python pytest attempt could not run because pytest was absent; the existing `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` supplied the successful test runner.
- Expanded extracted prepare/deploy heredocs locally through `cat` with fixture Bash variables: passed. Did not invoke the installer with `install`, SSH, SCP, or any Windows command.
- The new test checks source strings and ordering; it does not simulate stderr or location failures in PowerShell 5.1.

## Files changed

- `docs/reports/task-26927f7f/REPORT.md` only. No implementation or test changes.

## Not checked / risk

- No PowerShell runtime is installed locally. PS 5.1 stderr serialization, process-launch errors, and fail-closed behavior were reviewed statically, not executed.
- Nothing was run on winbox; no SSH or network fetch was performed. The current GitHub PR head beyond the available matching local refs was not verified.
- Real permissions, working-directory failure scenarios, scheduled-task registration, and dry-run behavior remain untested on Windows.
- The existing installer follows `origin/main` for the dedicated checkout; this review does not establish the contents that a future deployment fetches.

## Blockers

- None preventing completion of the offline review. The location-error finding prevents approval.

## Skill learning

- (none)

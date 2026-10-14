# REPORT task-0e3922da

## Files changed
- windows/spawn-worker.ps1: Claude's generated finish script stops matching task claude.exe PIDs individually and explicitly excludes WindowsTerminal.exe, OpenConsole.exe and explorer.exe; selects and logs -w new versus -w 0 based on the observed Terminal process count; timeout reports the current Terminal running status/count and scheduled task LastTaskResult (or unavailable if querying fails).
- tests/test_spawn_worker_ps1_finish.py: Added text regressions for process targeting, no tree kill, escaped runtime variables, window selection/logging and observed timeout diagnostics.
- docs/reports/task-0e3922da/REPORT.md: Recorded changes, validation and remaining platform checks.

## Tests
Command run from the worktree root:
```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_spawn_worker_ps1_finish.py tests/test_w33_spawn_worker_ps1.py tests/test_spawn_worker_ps1_runners.py -o addopts="" -p no:warnings
```
Pytest printed: `67 passed in 7.79s` (0 failed).

`git diff --check` passed.

## Not verified
- The script was not parsed by PowerShell (the CTO parses it on winbox).
- Live winbox checks remain: finishing a worker preserves other Terminal tabs/processes; spawning with zero or existing Terminal processes opens the intended window/tab; a timed-out launch reports the live scheduled task result in the caller's launch log.
- Terminal process presence does not prove an interactive window exists or diagnose every possible spawn failure. The timeout now reports observations rather than guessing a cause.

## Blockers
- None.

## Skill learning
- (none)

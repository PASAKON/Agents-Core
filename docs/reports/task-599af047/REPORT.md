# REPORT task-599af047

## Files changed

- tools/node_dispatch.py: check resume ownership before claiming the start lock; support trailing --probe with atomic local markers; add validated stop_clevel for recent local probes with Linux/Windows cleanup and close recording.
- tests/test_node_dispatch_clevel_host.py: mock the hub, launchers, process liveness, and subprocesses; test ownership on all three OS branches, parsing, markers, stop refusals, cleanup, exit races, and failure retention.
- docs/reports/task-599af047/REPORT.md: record scope, validation, and review limitations.

## Tests

- `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_node_dispatch_clevel_host.py -o addopts="" -p no:warnings`
  - `62 passed in 0.83s`.
- `HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_node_dispatch_clevel_host.py tests/test_node_dispatch.py tests/test_w33_node_dispatch_windows.py -o addopts="" -p no:warnings`
  - `3 failed, 662 passed in 188.36s (0:03:08)`.
  - This run collected the initial 56 new tests; six additional failure/race tests were added during the run. The separate 62-test run above validates the final new test file. Production code was identical in both runs.
  - Failures: `tests/test_node_dispatch.py::test_start_clevel_darwin_uses_the_existing_launchers`, `tests/test_node_dispatch.py::test_start_clevel_linux_resume_passes_a_full_uuid`, and `tests/test_w33_node_dispatch_windows.py::test_start_clevel_resume_passes_the_full_uuid_as_a_resume_flag`. All three expect a resume to launch without recording its host or creating a local UUID file; see Blockers.
- `git diff --check`: passed.

## Not verified

- Live tmux cleanup, Windows PowerShell process-tree termination on winbox, and launcher behavior on Mac need acceptance testing on those hosts. No live services, tmux sessions, or SSH connections were started or stopped.
- Real hub close persistence and UUID copying were not exercised; tests assert the existing session_status.record_close API call with status closed and note mesh probe stopped.
- Darwin stop intentionally refuses until G2.

## Blockers

- Existing successful-resume tests in tests/test_node_dispatch.py and tests/test_w33_node_dispatch_windows.py omit both a host record and a local UUID file. Their setup needs a same-host session_status.get fake (or a local UUID under a temporary session_status.LOCKS directory) to meet the new precondition. These files are outside the edit allowlist and were left unchanged.
- No commits or pushes made; the launcher owns those steps.

## Skill learning

- (none)

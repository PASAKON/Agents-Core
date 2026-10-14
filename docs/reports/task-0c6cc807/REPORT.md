# REPORT task-0c6cc807

## Files changed

- scripts/spawn-worker-remote.sh: added /WORKER.md to ANCHORED_EXCLUDES and WORKER.md to GIT_RESET_GUARD; documented the contract file. Both existing dry-run never_committed lines render the updated guard.
- roles/_worker_remote.md: explicitly directs codex to shell commands, apply_patch, and the brief's tests; labels the file-tools-only restriction AGY-only and keeps shared mailbox/report instructions tool-neutral. Other contract rules are preserved.
- tests/test_spawn_worker_remote_runners.py: checks both lists and both runners' dry-run output, plus ignore and reset behavior in a temporary repo without .gitignore.
- tests/test_nonclaude_worker_contract.py: asserts codex shell/apply_patch instructions and the AGY-only restriction, rejecting the old generic instruction.
- docs/reports/task-0c6cc807/REPORT.md: records changes, validation, and limitations for review.

## Tests

Completed command:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_spawn_worker_remote_runners.py tests/test_nonclaude_worker_contract.py tests/test_w06_launcher_report.py -o addopts="" -p no:warnings
```

Pytest printed: `62 passed in 35.84s` (0 failed). Includes the unchanged-Claude contract hash regression and offline report-launcher tests.

Full requested command attempted first:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_spawn_worker_remote_runners.py tests/test_nonclaude_worker_contract.py tests/test_spawn_remote_linux.py tests/test_w03b_local_launcher.py tests/test_w06_launcher_report.py -o addopts="" -p no:warnings
```

Collected 112 tests; displayed 30 passing tests, then stalled in test_spawn_remote_linux.py. Interrupted with exit 130; no final pytest pass/fail totals printed.

Diagnostic rerun:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_spawn_worker_remote_runners.py tests/test_nonclaude_worker_contract.py tests/test_spawn_remote_linux.py tests/test_w03b_local_launcher.py tests/test_w06_launcher_report.py -o addopts="" -p no:warnings -o faulthandler_timeout=30
```

Again displayed 30 passing tests. The 30-second diagnostic showed the main thread waiting in selectors/asyncio.run at tests/test_spawn_remote_linux.py:78, test_contabo_dry_run_renders_ssh_command_with_every_flag. Interrupted with exit 130; no final totals printed.

Independent attempt at the remaining suites:

```sh
HTTPS_PROXY=http://127.0.0.1:9 NO_PROXY=localhost,127.0.0.1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_w03b_local_launcher.py tests/test_w06_launcher_report.py -o addopts="" -p no:warnings -o faulthandler_timeout=30
```

Collected 61 tests. The 30-second diagnostic showed the main thread waiting in selectors/asyncio.run at tests/test_w03b_local_launcher.py:143, test_linux_self_host_codex_and_agy_run_the_launcher_with_local_bash. Interrupted with exit 130; no final totals printed. The report-launcher suite subsequently completed in the 62-pass run above.

`git diff --check` passed.

## Not verified

- Full test_spawn_remote_linux.py and test_w03b_local_launcher.py results: stalled as described above; the traces do not establish the cause.
- Actual Mac, winbox, and live worker execution require reviewer validation; no live service, SSH, or tmux session was operated.

## Blockers

- Full five-file validation is incomplete because the two existing asynchronous launcher suites stalled. No files outside the permitted paths were edited to work around this.
- Working-tree changes are left uncommitted for the launcher and CTO review.

## Skill learning

- (none)

# REPORT task-6f178277

## Summary

Implemented scoped Codex write permissions, runner-specific remote instructions,
and launcher-owned heartbeats for Codex and AGY. Claude's rendered contract and
brief remain byte-identical to the original; the prior contract is preserved as
the first section of roles/_worker_remote.md. No AGY allow-list change was made.

## Files Changed

- scripts/spawn-worker-remote.sh — accepts --work-dir / WORK_DIR; resolves the
  absolute git common directory; shares Codex command rendering between dry-run
  and real launch; selects the runner contract; strips the legacy brief footer;
  supervises the runner and heartbeat with exit/signal cleanup and kill + wait.
- windows/spawn-worker.ps1 — accepts -WorkDir / WORK_DIR; passes paths as discrete
  argument-array entries; selects the runner contract; runs heartbeat jobs with
  try/finally Stop-Job, Wait-Job, and Remove-Job cleanup.
- tools/delegate.py — keeps Claude's brief unchanged, renders file-based reporting
  for Codex/AGY, and forwards Work paths to both launchers. Local delegation uses
  the existing _work_dir_for lifecycle or WORK_DIR; remote paths come from the
  task's work_dir or the target launcher's environment, not a fabricated hub path.
- roles/_worker_remote.md — adds a selectable Codex/AGY contract requiring
  docs/reports/<task-id>/REPORT.md, its exact header, Blockers and Skill learning;
  mailbox reads use file tools, and the launcher owns heartbeat/commit/push.
- tests/test_spawn_worker_remote_runners.py — scoped path flags, absent Work path,
  spaces/apostrophes/backslashes, actual linked worktrees, and executable heartbeat
  cleanup tests including nonzero exit and SIGTERM.
- tests/test_spawn_worker_ps1_runners.py — argument-array and heartbeat cleanup
  source checks; updates the old AGY-contract exclusion assertion to selection.
- tests/test_nonclaude_worker_contract.py — runner brief checks, frozen SHA-256
  of the pre-change Claude contract, and actual Linux prompt assembly comparisons.
- docs/reports/task-6f178277/REPORT.md — this report.

## Exact Codex Command Before / After

Concrete no-model example for this worktree. The optional Work path below was
supplied to dry-run as --work-dir '/tmp/Work folder/task-6f178277'; it is a test
input, not a claim that a production Work folder exists at that location.

Before (the previous real launcher rendering):

```sh
codex exec "$(cat TASK.md)" -C '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277' -s workspace-write --skip-git-repo-check --json -o '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277/.launch-task-6f178277/codex-final.txt' > '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277/.launch-task-6f178277/codex-events.jsonl' 2>&1
```

After (captured from the new dry-run; real launch uses this same command renderer
and appends `&` so it can wait for the runner and handle termination):

```sh
codex exec "$(cat TASK.md)" -C '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277' -s workspace-write --add-dir '/opt/MoonieXHQ/Agents/Core/.git' --add-dir '/tmp/Work folder/task-6f178277' --skip-git-repo-check --json -o '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277/.launch-task-6f178277/codex-final.txt' > '/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-6f178277/.launch-task-6f178277/codex-events.jsonl' 2>&1
```

Without WORK_DIR / --work-dir, only the git common directory --add-dir remains.
The sandbox stays workspace-write; no full-access or sandbox-bypass flag was
introduced. Windows supplies the same flags as separately quoted array values.

## Tests

Ran offline, with no network, real worker CLI, or tmux invocation:

```text
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings tests/test_spawn_worker_remote_runners.py tests/test_spawn_worker_ps1_runners.py tests/test_nonclaude_worker_contract.py tests/test_delegate_router.py
89 passed in 23.27s

bash -n scripts/spawn-worker-remote.sh
exit 0

git diff --check
exit 0
```

Windows verification is source-level, as required; no Windows runtime or real
worker end-to-end execution was performed. Linux tests execute isolated prompt
assembly and heartbeat supervision against temporary files and local git repos.

## Commits

No commit could be created. Wrote the message to /tmp/task-6f178277-commit.txt
and attempted git add followed by git commit -F that file. Both failed with:

```text
fatal: Unable to create '/opt/MoonieXHQ/Agents/Core/.git/worktrees/mooniex-agents__developer__task-6f178277/index.lock': Read-only file system
```

Changes remain in the assigned worktree for the outer launcher to commit.

## Blockers

- This already-running session does not inherit the new --add-dir flags. Its
  shared git metadata is read-only, so incremental commits were impossible.
  No permission bypass or write outside the authorized worktree was attempted.
- Org wiki/report MCP tools are not exposed in this session. Relevant repository
  code and role documentation were inspected instead; submit_report could not
  be called. This report is the file-based handoff for the launcher.

## Skill learning

- MISSING [no owner] : Linked worktrees need write access to their shared git
  metadata as well as the task worktree; evidence: task-6f178277 index.lock
  failure above and the passing linked-worktree regression; fix: grant the
  resolved git common directory with --add-dir while retaining workspace-write.
- MISSING [no owner] : Headless runner liveness must be maintained by the launcher,
  not by a worker shell-tool instruction; evidence: task-eac8c06d / task-f965b035
  in the brief and offline heartbeat cleanup tests in this change.

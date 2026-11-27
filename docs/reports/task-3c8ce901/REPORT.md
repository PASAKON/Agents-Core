# REPORT task-3c8ce901

## Changes

- `windows/spawn-worker.ps1`: the Codex launcher snapshots existing task gitdir DACLs in parent-process memory before starting Codex, then restores changed DACLs in `finally` before staging/committing. This preserves pre-existing permissions, including legitimate DENY entries, instead of indiscriminately removing unknown SIDs. The scope must be an immediate child of the repository's `worktrees` metadata directory; reparse points are refused. The repository gitdir root is never modified by this restoration.
- Commit failures now print captured Git stdout/stderr and include the exit code and full output in the exception.
- `tests/test_spawn_worker_ps1_finish.py`: regression checks for scope guards, restoration ordering, generated-script escaping, and commit diagnostics.

## Investigation

Source inspection shows the generated `launch.ps1` calls Codex through `Invoke-WithStdin`, waits for it, and runs the report/commit step in the same parent PowerShell process. `windows/native-args.ps1` does not switch that parent's token. This supports treating persistent filesystem ACL changes separately from the child's restricted token; it does not establish the live failure's cause.

A read-only SSH attempt (`ssh -o BatchMode=yes -o ConnectTimeout=5 winbox whoami`) failed before connection with:

```text
Control socket connect(/root/.ssh/cm-passg@100.124.196.11-22): Operation not permitted
socket: Operation not permitted
ssh: connect to host 100.124.196.11 port 22: failure
```

No old task was reopened or rerun. No Winbox files, processes, or ExpertAdvisor files were changed.

## Validation

- `PATH=/opt/MoonieXHQ/Agents/Core/.venv/bin:$PATH python -m pytest tests/test_spawn_worker_ps1_finish.py tests/test_spawn_worker_ps1_runners.py tests/test_w33_spawn_worker_ps1.py`: **76 passed**. No `-q` supplied. The initial plain invocation failed because the default PATH has no `python`; the existing project venv supplied it.
- `git diff --check`: passed.

## Blockers

- This worker has no Claude/SSH connector and sandbox network access is denied. Live launch files, the original Git error, and token/group evidence could not be collected.
- Required follow-up from a network-enabled worker: inspect the named launch evidence, validate this patch with exactly one fresh cheap docs-only Codex task, and record its pushed commit SHA here. Do not rerun the eight completed research tasks.
- A PR has not been opened in this session. The worker contract assigns commit/push to the launcher after this turn; publication and PR creation require the network-enabled launcher/reviewer.

## Not checked / risk

- Acceptance is **not complete**: no fresh Winbox task, pushed probe SHA, or open PR is verified.
- Windows PowerShell and ACL APIs are unavailable locally; the new tests check generated-source contracts, not Windows runtime ACL behavior.
- Restoration covers metadata paths present before Codex starts (including the index). Newly created metadata paths have no captured ACL. Already-stale pre-run ACLs are preserved. The approach is intended for a fresh task and must be validated against the actual failure before rollout.
- If the parent cannot read or restore a DACL, restoration fails closed instead of broadening permissions or attempting a repository-wide reset. Concurrent legitimate ACL changes to the task gitdir would also be replaced with the baseline.

## Skill learning

- (none)

# REPORT task-c4939966

Status: blocked during preflight; C4 and C5 are not implemented. No PR opened.

## Blockers

- The assigned worktree's Git administration directory is mounted read-only. Creating the required branch with `git switch -c ph-a08/remote-publish-steward origin/main` failed with `Unable to create '/opt/MoonieXHQ/Agents/Core/.git/worktrees/mooniex-agents__developer__task-c4939966/index.lock': Read-only file system`.
- Enabling sparse checkout with `git sparse-checkout set tools lib tests windows scripts config docs` failed with the same filesystem restriction for `info/sparse-checkout.lock`. No attempt was made to bypass the mount or write outside the assigned worktree. The current branch remains `agent/codex-task-c4939966`, at `d4ed0b75` during inspection.
- Request to launcher/PH: recreate the assigned worktree as sparse on `ph-a08/remote-publish-steward` from `origin/main`, with writable worktree Git metadata, then resume this task. Do not merge this report as an implementation of C4/C5.
- A read-only hub inventory query through `tools.gc_stale_tasks._read_tasks()` failed with `OperationalError`. Request a working read-only hub DB connection or an authoritative finished-task inventory containing task ID, host, worktree, branch and terminal-transition time. No credentials were printed or copied.

## Design findings and proposed implementation

The binding plan was read and its full SHA256 verified:
`71ac4b6a682d1f35b4083ded966db09c6fe04501ec4b4f4dbe4dc8c61e37f578`.

C4:

1. `lib/db.py:update_status` is a common status-transition point. A hub-only post-commit review notification can schedule publication for winbox/mac; failures need a durable retry path rather than being silently swallowed or undoing the completed status update.
2. `runners/branch_poller.py` currently checks for the remote branch before transitioning a worker to review. Merely adding a call after that transition cannot bootstrap a Claude worker whose branch has never been pushed. Completion must reach the hub independently of origin, and only after launcher-owned commit finishes. A persisted completion marker plus a bounded hub poll is one possible implementation; it is not implemented here.
3. `tools/node_dispatch.py:verb_publish_branch` currently obtains the task via `_task_on_this_host`, which reads the DB. Its existing task-ID-only interface needs a DB-free remote authorization/metadata path. Keep host/task/branch binding and strict argument validation; do not resolve this by installing DB credentials remotely.
4. The existing branch regex only accepts worker `agent/...-task-...` branches. PH publication needs an explicit session/branch binding using the same script publication path, without permitting default-branch pushes or arbitrary refspecs.
5. `windows/spawn-worker.ps1:New-ReportStepBody` already contains report normalization, staging filters, commit and push for other runners. Claude's generated launcher currently ends after its process returns, and its finish script can stop the process. Integrate launcher-owned commit with both completion paths and verify it executes exactly once before hub publication. Preserve existing media filters.
6. Before pushing, inspect every outgoing object, including media introduced and deleted in intermediate commits. Reject prohibited media and objects over the size limit; checking only the current filesystem or staged diff is insufficient. Use an explicit source commit/refspec and no force push.

C5:

1. Contabo owns DB selection of finished tasks and the existing grace policy. Extend its steward to dispatch a bounded remote cleanup batch per host, defaulting to dry run. Record actual remote reap/orphan results under the target host, including failures; never label planned or refused cleanup as run successfully.
2. The remote verb must work without DB access. Resolve task paths from validated metadata and configured host roots. Reject root equality, traversal, other drives/UNC roots, symlinks/reparse escapes and foreign path syntax. Use `PureWindowsPath` for Windows lexical checks and native resolved containment on the executing host.
3. Reuse `tools.disk_steward.guard_path` for the NEVER list and live-cwd protection. Check descendants too, so a protected file nested in an otherwise allowed task directory blocks recursive deletion. Do not traverse linked directories while measuring or deleting.
4. Require a clean worktree, no active owner, and verified origin reachability of the exact branch commit before any cleanup. Refresh remote evidence, fail closed on network errors, and recheck before removal. Preserve the branch. A dirty worktree or unpushed commit must block deletion.
5. Invoke `workdir.py close <task> --archive --root <host Work root>` locally on the remote host. Its existing close path can delete tmp/filed inputs before archive completion; preflight guards therefore must run before invoking it. Continue to worktree removal only after successful archive/close. Interrupted runs need safe retries.
6. Important discrepancy: `tools/work_archive.py` currently uploads through the Drive resumable HTTP API and verifies `md5Checksum`; it does not use rclone. It already writes `drive-archive.log`. Meeting this brief requires a host-local rclone archive backend with verified hashes and retained audit logging, exercised with fake rclone. Merely calling the existing close command would not satisfy the rclone requirement.
7. Cap both task count and total bytes reclaimed per host per run, including Work and worktree data. Serialize overlapping runs so the cap and clean/origin checks are meaningful.

Cadence proposal only: PH should check deployed steward scheduling. If 30-minute hub coordination is absent, raise a card proposing a 30-minute timer. No unit, timer or systemd file was changed.

## Files changed

- `docs/reports/task-c4939966/REPORT.md` only.
- No production code, sibling-owned file, launcher, role, skill, hook, settings or systemd file was changed.

## Validation performed

- Read repository implementations for dispatch, mesh transport, DB transitions, branch polling, Windows worker completion, steward guards, reaping and archive/close.
- Verified approved-plan SHA256 above.
- Pytest was not run: the required sparse-worktree setup was blocked. There is no test-run tail and no claimed test pass.
- The first inventory attempt used `python`, which is unavailable; the subsequent read-only query used `python3` and returned `OperationalError`.
- Diff secret scan passed: `git diff --no-index -- /dev/null docs/reports/task-c4939966/REPORT.md | gitleaks stdin --no-banner --redact` reported `no leaks found` (10.74 KB scanned). The no-index diff includes the new, untracked report. `git diff --check` also completed successfully for tracked changes (none).

## Live listing

Not performed. The hub could not supply the authoritative finished-task inventory, so no broad scan of winbox was substituted. Zero SSH calls were made; the single permitted live check remains available.

At the time of preflight, the host clock reported 2026-10-29 19:40 UTC (2026-10-30 02:40 TH), outside the forbidden windows. On resume, recheck TH time immediately before the one call. Enumerate only known finished-task worktrees under the configured winbox root, stream file-size aggregation without following reparse points, and return task/path/byte totals. Do not inspect #503's checkout, signal processes, touch MT5, or reboot. Save the listing verbatim here.

## E2E-4 steps for PH after implementation and live sync

1. Outside 06:50–07:00 and 09:00–11:00 TH, verify the isolated winbox dispatcher/launcher checkout is the reviewed SHA and free RAM is at least 4 GB. Keep #503's checkout untouched.
2. Create one small Claude worker task on winbox that changes a text file and writes its report. Record task ID, branch, starting SHA and host. Instruct the model to finish without committing or pushing.
3. Observe launcher-owned filtered staging/commit completion and the independent completion signal reaching Contabo. Confirm the hub transitions the task to review and invokes `publish_branch` through mesh automatically.
4. From Contabo, compare the resulting origin branch SHA with the launcher commit SHA. Save the dispatch audit record and launcher evidence. Require successful publication without a model push or manual intervention.
5. Repeat the publication path for a disposable PH branch bound to its owning session. Separately use fake/local fixtures for media and >1 MB rejection; do not upload prohibited test media to origin.

## E2E-5 steps for PH after implementation and live sync

1. Use the E2E-4 task after PH review/merge. Put a small disposable deliverable in its host-local `Work/<task>/out`, record its MD5, and retain the task's terminal-transition timestamp.
2. Run hub steward dry-run selection before grace expires; require no deletion. After the existing grace expires, run dry run again and record the candidate, verified origin commit, clean worktree, archive destination and per-host deletion budget.
3. Authorize the deployed apply path through the normal PH operational process. Contabo dispatches the new verb; the remote host runs rclone through `workdir.py close --archive`, verifies Drive MD5 and appends `drive-archive.log` before removing archived outputs.
4. Confirm the task Work directory and clean worktree disappear within one day after merge, origin still retains the code, Drive retains the deliverable with the recorded MD5, and hub reap/orphans records show real remote execution.
5. In fake tests, repeat with hash mismatch, rclone failure, dirty/unpushed branch, out-of-root POSIX/Windows paths, NEVER descendants, unavailable origin and exhausted deletion budget. Each must retain protected data and report refusal/failure accurately. Retry a completed cleanup to establish idempotency.

These are acceptance steps, not executed results. Exact new CLI/verb arguments must be added once the interface exists.

## Not checked / risk

- C4/C5 implementation, required fake tests, branch creation, sparse setup and PR remain outstanding.
- No live Windows or Mac behavior, PowerShell runtime, SSH transport, rclone configuration, archive restoration, grace timing or per-host deletion cap has been validated.
- Existing grace semantics need confirmation before implementation; Work orphan aging and worktree reaping are separate paths and must not be conflated.
- PH publication and review-before-push bootstrap are material gaps in a naive hook-only implementation.
- No remote deployment or cleanup occurred. No DB secret was placed on another host.

## Skill learning

- (none)

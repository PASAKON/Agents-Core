# REPORT task-c4939966

Implemented C4 and C5 on `agent/codex-task-c4939966` in the assigned worktree. The launcher owns commit/push of this submission. No branch switch, sparse-checkout change, deployment, PR creation, role edit, or systemd edit was performed.

## Design

Read the approved `state/ph-briefs/hostspawn-host-fill-plan.md`, including the requested rules, C4/C5, acceptance items, and prohibitions. Read the earlier design report from commit `78177800`. The latest CTO correction governs: existing Drive API archive, no rclone backend, and fake service tests.

### C4 — publication

1. `lib/db.py` is byte-identical to `origin/main`: status writes do not perform publication or synchronous mesh calls. Contabo's branch poller owns worker publication and retries persisted review rows, including workers dispatched by a remote PH. Completion and review sweeps rotate at most three tasks per host per phase per tick.
2. `worker_completion` supplies the independent completion channel before a branch exists on origin. It checks a dead worker PID, a committed report with the correct task header, report freshness when `spawned_at` is supplied, and no tracked edits. Windows additionally requires a launcher marker matching HEAD. The hub records review, triggering publication. Existing external-runner artefact validation runs after publication and records its validated SHA; a refused gate marks the task failed.
3. `publish_branch <task-id> <base64url-json>` is the new hub call. It carries only the hub's task metadata and checks task/host/worktree/branch binding against native configured roots, without querying a remote DB. The legacy task-ID-only interface remains for existing callers. The new remote maintenance/publication audit is local `state/mesh-audit/maintenance.jsonl`; it needs no DB credentials.
4. `publish_ph <base64url-json>` shares the outgoing-object guard and immutable-SHA push. PH branches are explicitly bound as `ph/<sid8>-<topic>` and their worktrees must end in `__ph-<sid8>` under the host worktree root. From Contabo, request review/publication with `python -m tools.remote_maintenance winbox <sid8> ph/<sid8>-<topic> '<native-worktree-path>'` (use `mac` for Mac). Existing PH branches with other names require an explicit migration to this binding; the interface does not accept arbitrary refspecs or default branches.
5. All three Windows runners use `New-ReportStepBody`: preserve filtered staging, commit from the launcher, then write `org-publish-ready` in that worktree's Git administration directory. Claude reaches this one epilogue after both natural exit and its existing finish command; the finish command only ends the task's Claude process. Windows launchers no longer push. The shell launcher also leaves Mac/winbox publication to the hub; its other-host behavior remains intact.
6. Publication fetches origin, walks outgoing commits and objects, rejects media extensions (including intermediate additions later deleted or blobs reused under another name), and rejects blobs over 1 MiB. It pushes the inspected SHA to one explicit branch, without force. This final gate is intentionally code-only even if a staging allow-list kept media.

### C5 — remote steward

1. Contabo selects terminal tasks using hub DB metadata and `remote_reap.grace_hours: 20` in `config/storage-policy.yaml`. Both hub selection and the remote endpoint enforce this separate grace; local `work_dir.abandon_days: 14` remains unchanged. Supported terminal states match Work cleanup: done, merged, cancelled, failed. `steward_reap` never queries the DB. `disk_steward tick` coordinates remote dry runs when the hub DB is configured; `tick --remote-apply` opts into cleanup. Standalone commands are `python -m tools.disk_steward remote-reap` and `python -m tools.disk_steward remote-reap --apply`.
2. The remote endpoint derives Work from `machine-contract.yaml`'s host `hq` plus `/Work`, and worktrees from `hosts.yaml`. It refuses equality with a root, traversal, foreign syntax, other Windows drives/UNC roots, symlinks and reparse points. `PureWindowsPath` is checked lexically before native containment. Worktree names must bind to the task ID.
3. The steward's existing NEVER guard applies to both task roots and every descendant, without following links. Unreadable directories and missing psutil fail closed. `psutil` is declared as a runtime dependency for cross-platform cwd inspection. Active task PIDs (including access-denied liveness checks) and observable live cwd ancestors block removal, using the existing steward cwd policy. Windows cleanup additionally refuses below 4 GiB available RAM. No processes are terminated by cleanup.
4. Require a clean worktree and freshly queried `origin/branch` SHA exactly equal to HEAD. Repeat clean/origin checks and descendant checks before close, then again before removal. Git performs non-forced worktree removal; the branch is preserved. A missing origin branch or unavailable origin blocks cleanup.
5. Call the existing `workdir.close(task, archive=True, root=host_work_root)`, the same implementation as `workdir.py close --archive`. It uses `work_archive.py`'s Drive API, verifies archive and manifest `md5Checksum`, and writes `drive-archive.log`. Only successful close permits Git worktree removal. A closed Work directory with the worktree still present can be retried. Missing worktree plus remaining Work fails closed because origin evidence is unavailable.
6. Hub audit rows record `reap` and `orphans` under the actual remote host, with remote results and `planned`, `run`, or `failed`. Failed/refused cleanup is never reported as successful. Successful task/timestamp pairs are persisted so they do not monopolize later batches; a rotating cursor lets later candidates proceed past refused ones.
7. Each host batch is capped at three tasks and 2 GiB of combined Work/worktree file sizes. Atomic exclusive lock files serialize hub runs and remote runs. Dry run is default. Crash-left locks deliberately block further cleanup until PH investigates; no automatic lock stealing.

## Push-path text for CTO Main

Proposed replacement for `roles/_worker_remote.md` item 3 (not edited here):

> On winbox, write the task report and finish normally (Claude may use the existing `ORG_WORKER_FINISH` command). The Windows launcher stages through the existing code/media filters, commits, and records completion. Do not run git push. On Mac, commit the code and report, then finish; do not run git push. Contabo observes completion, moves the task to review, and publishes the inspected commit through the mesh script. Publication failures remain pending for hub retry. Keep all media in the task Work/out directory for verified Drive archive. A PH requests the same hub publication path for its session-bound PH branch.

## Files changed

- `tools/remote_maintenance.py`: new DB-free endpoints, guards, hub batch coordinator and PH publication CLI.
- `tools/node_dispatch.py`, `lib/mesh.py`: protocol validation, endpoint registration, timeouts, local audit.
- `runners/branch_poller.py`: completion bootstrap, bounded retry and artefact validation. `lib/db.py` is unchanged from origin/main.
- `config/storage-policy.yaml`: separate 20-hour remote reap grace.
- `tools/disk_steward.py`: hub coordination and explicit apply CLI.
- `windows/spawn-worker.ps1`, `scripts/spawn-worker-remote.sh`: launcher commit/completion and hub push ownership.
- `requirements.txt`: psutil dependency.
- `tests/test_remote_maintenance.py`: fake DB/mesh/Drive checks and local Git fixtures.
- Existing tests in `test_node_dispatch.py`, `test_disk_steward.py`, and `test_spawn_worker_ps1_runners.py`: updated expectations. Removed the prior review-hook fixture changes from DB and branch-poller tests.
- This report.

## Validation performed

Iteration 2 workspace recovery: the assigned branch initially pointed at `20e36503` (origin/main), without round two. Restored the patch from reviewed commit `8181546f` in this worktree, excluding the DB hook and its fixture changes, then applied F1/F2. No branch switch or commit was performed. SHA-256 of both `lib/db.py` and `origin/main:lib/db.py`: `abc60a879483640239d4877a27aa8e18792ae305712c2300cd08c7cecae424af`.

Tests run from the assigned worktree using `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`; system `python3` has no pytest. `ORG_DB_URL` is removed for test execution. DB fixtures are fake or temporary SQLite, mesh transport is fake, Drive uses fake uploaders, and Git integration fixtures use local bare repositories. Windows launcher checks are textual; no PowerShell runtime is available here.

Final commands (all from the assigned worktree, with the shared virtualenv interpreter):

```sh
env -u ORG_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest \
  tests/test_remote_maintenance.py tests/test_node_dispatch.py \
  tests/test_disk_steward.py tests/test_disk_steward_hosts.py \
  tests/test_work_archive.py tests/test_workdir.py \
  tests/test_spawn_worker_ps1_finish.py tests/test_spawn_worker_ps1_runners.py \
  tests/test_branch_poller_reopen.py tests/test_db_hosts_letters.py \
  tests/test_spawn_worker_remote_runners.py -ra --disable-warnings

env -u ORG_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest \
  tests/test_w23_mesh_dispatch.py \
  -k 'publish or remote_builds_the_exact or remote_argv or timeout_defaults or injection or no_reply or verb_refusal or last_stdout or unknown_host or no_mesh_ssh' \
  -ra --disable-warnings
```

Previous round-two main changed-module suite tail (fresh iteration-two results below):

```text
........................................................................ [ 97%]
...........                                                              [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/test_disk_steward_hosts.py:33: requires native Windows handles
442 passed, 1 skipped in 91.95s (0:01:31)
```

Previous round-two focused new-module tail:

```text
...................................                                      [100%]
35 passed in 2.14s
```

Previous round-two mesh tail:

```text
............................................                             [100%]
44 passed, 41 deselected in 10.45s
```

The attempted broader mesh run was stopped after stalling in the unchanged `test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh`. A standalone 45-second bounded reproduction with faulthandler showed the worker thread idle in `concurrent.futures.thread._worker` and the main thread waiting in asyncio's selector, inside the legacy `delegate._spawn_remote` test. This is not reported as a passing full suite. The final mesh command selects the transport, parser, timeout and publication tests relevant to this change.

`git diff --check` and `bash -n scripts/spawn-worker-remote.sh` passed. Gitleaks scanned the tracked diff plus no-index diffs for the new module, tests and report with `gitleaks stdin --no-banner --redact`: **no leaks found**.

## Iteration 2 validation tails

Re-ran the same changed-module and focused mesh commands above from this worktree, plus `tests/test_remote_maintenance.py` alone with the same interpreter and flags. New tests cover review writes without mesh dispatch, configured remote grace, and hub/endpoint eligibility at 19 versus 21 hours for both hosts while local grace stays 14 days.

```text
........................................................................ [ 96%]
................                                                         [100%]
=========================== short test summary info ============================
SKIPPED [1] tests/test_disk_steward_hosts.py:33: requires native Windows handles
447 passed, 1 skipped in 137.59s (0:02:17)
```

```text
........................................                                 [100%]
40 passed in 5.69s
```

```text
............................................                             [100%]
44 passed, 41 deselected in 13.51s
```

`git diff --check`, shell syntax validation and Gitleaks diff scan passed. All round-two implementation files outside F1/F2 and this report were checked byte-for-byte against `8181546f` and preserved.

## Live listing and hub inventory

**PH runs it.** No live inventory/listing was performed from this sandbox. PH must check the configured native Work roots against deployed launchers and keep #503's checkout untouched. Any winbox check must avoid 06:50–07:00 and 09:00–11:00 TH, preserve at least 4 GiB free RAM, and never touch terminal64/MT5 or reboot.

## E2E-4 — PH runs it

1. Deploy the reviewed dispatcher, poller, DB hook and launchers to their isolated checkouts using the normal deployment process. Verify the winbox dispatcher is not #503's checkout. Install the declared runtime dependencies. Check RAM and permitted operating time.
2. Launch a disposable Claude winbox task that changes a text file and writes `docs/reports/<task>/REPORT.md`; the model does not commit or push. Record task ID, PID, branch and spawned timestamp.
3. Let Claude finish normally, or through `ORG_WORKER_FINISH`. Verify one launcher commit, a matching `org-publish-ready` SHA in its worktree Git directory, and a dead worker PID.
4. Allow Contabo's branch poller to run. Verify the review transition, automatic `publish_branch` request, local mesh audit, and matching origin SHA. An unavailable mesh endpoint must leave review available for subsequent retry.
5. Repeat for Mac with a committed report and finished worker. For a disposable PH branch, create the session-bound branch/worktree described above, commit code, and run the Contabo PH publication CLI. Verify default branches and another session's branch are refused.
6. Confirm external-runner artefact validation passes before merging. Exercise media/large-object rejection with the local tests, not by uploading prohibited files to origin.

## E2E-5 — PH runs it

1. Retain the published task branch on origin after merging. Put a disposable deliverable in the configured remote `Work/<task>/out`; record its MD5 and terminal `updated_at` timestamp.
2. Deploy `remote_reap.grace_hours: 20` to hub and remote configs and install psutil in each remote venv. On Contabo run `python -m tools.disk_steward remote-reap`. Before 20 hours from the terminal timestamp, the task must not be dispatched. After 20 hours, require a `planned` remote result with measured bytes and verified HEAD.
3. Run `python -m tools.disk_steward remote-reap --apply`. The remote endpoint must archive through the Drive API, verify archive/manifest MD5, append `drive-archive.log`, close Work, then remove the clean worktree without deleting the branch.
4. Before 24 hours from completion/merge, verify Drive contents by downloading/restoring the deliverable and comparing its original MD5. Confirm Work/worktree absence, origin branch retention, and hub `reap`/`orphans` records marked `run` for that host. Repeat for both winbox and Mac.
5. Repeat the command to verify successful tasks are skipped safely. Use fake tests for checksum mismatch, dirty or unpushed code, protected descendants, links, path escapes, cap exhaustion, live owners, and missing completion markers.

## Not checked / risk

- Live Windows/Mac execution, SSH deployment, Drive authentication/restoration, native reparse points and PowerShell execution: **PH runs it**. The native Windows integration test is skipped on Linux.
- Remote cleanup becomes eligible after 20 hours, leaving four hours for scheduling/retries within the one-day target. Local orphan cleanup retains its 14-day grace. Both hosts must receive the updated config; availability, apply scheduling, batch backlog and safety refusals can still delay cleanup.
- `psutil` must be installed in the winbox and Mac venvs. Cleanup fails closed until it is installed; declaring the dependency here does not install it remotely.
- Codex/AGY push on winbox moves from the launcher to the hub. Publication now waits on the branch poller and can be delayed by its cadence, backlog or mesh failures.
- Remote cleanup remains dry-run unless `--apply` or `tick --remote-apply` is selected. Cadence proposal only: if no 30-minute hub coordinator exists, PH should raise the scheduling card for a 30-minute invocation with the chosen apply policy. No units/timers changed.
- Process cwd inspection uses the existing steward policy: inaccessible system-process cwd values are skipped. Known owner PID access denial blocks cleanup, and missing psutil blocks cleanup. PH must validate native process visibility; an unrelated inaccessible process cannot be ruled out by cwd scanning alone.
- A strict clean worktree can be blocked by untracked launcher artifacts. Branch deletion on origin also blocks cleanup, even when its commit was merged elsewhere. These are explicit preservation choices.
- `workdir.close` retains its existing behavior: tmp and already-filed inputs may be deleted before a later archive failure. Unverified out/ remains; worktree removal is blocked.
- The hub's review transition precedes publication and external-runner artefact checks. Review is therefore not proof that publication/tests completed; PH must check origin and the artefact result before merging. Persisted review rows provide retries when transport or validation infrastructure is unavailable.
- The legacy task-ID-only publish interface still uses its original DB lookup. All new Contabo paths use the DB-free metadata interface. PH branches must use the new session-bound naming contract.
- Locks serialize these scripts, not arbitrary concurrent human filesystem edits. Live-owner/cwd and repeated Git checks reduce that race; no forced deletion is used.

## Blockers

- No sandbox blocker to delivering this implementation. Deployment and live E2E verification remain PH/CTO responsibilities as stated above.

## Skill learning

- (none)

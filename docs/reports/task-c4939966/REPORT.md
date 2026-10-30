# REPORT task-c4939966

## Iteration 6 (Claude Sonnet 5.5, on top of 89d91175): the 11 CI failures on PR #584

Root causes and fixes, one per failing group:

- **w04 + w15 (6 tests): the poller stopped polling.** The C4 `tick()` replaced `check_task` with `_publish_via_mesh` for winbox/mac rows and widened the row filter beyond `in_poller_set`. `tick()` now polls exactly `in_poller_set` again and calls `check_task`, as on main. The hub step moved into `_hub_remote_step`, reached from `_publish_via_mesh` inside `check_task` and from the review sweep. It acts only on rows `is_dispatched_here` (so a row dispatched by the Mac is still the Mac's), only with `ORG_MESH_DISPATCH` on, and only for a row's turn in the bounded batch (3 per host per phase per tick, rotating; the turn set lives for one `tick`). A row the hub moved to review returns from `check_task` at once. `_REMOTE_TURN` is `None` outside `tick`, so direct calls are unbounded.
- **w27 verbs (4 tests).** The payload verbs now carry lowercase hex of a compact JSON object (`remote_maintenance.encode/decode`), not base64url: the old form had uppercase and `=`, which the build_argv plain-token rule (`[a-z0-9_-]`) refuses. `node_dispatch.PAYLOAD_RE` is `(?:[0-9a-f]{2}){1,3750}`. `_check_args` decodes the payload for `steward_reap`, `worker_completion`, `publish_ph` and the 2-argument `publish_branch`, and refuses one that does not name its target (`id` = task-hex8, `session_id` = hex8, `tasks` = list of at most 3, `publish_branch` id = its first argument). `worker_completion -` is refused at the parser. The 8192-character cap applies only to those payload forms; every other command keeps 256. The test oracle in `tests/test_w27_security.py` restates the same grammar independently (`_payload_ok`), and a new test `test_payload_verbs_take_exactly_one_hex_payload_that_names_a_target` covers acceptance, 18 refused tokens per verb, build_argv, and the lone dash.
- **w27 git redaction (1 test).** `remote_maintenance.git()` now raises `git <sub> failed: <redacted, last 300 chars>` using node_dispatch's `_redact`; `reap` redacts its per-task error text; `hub_reap` redacts every string of a remote reply (`redact_reply`) before the audit row. Nothing but the redacted, bounded text leaves `git()`.
- **Audit.** `_audit` writes the DB event first (as on main) and falls back to `state/mesh-audit/maintenance.jsonl` only when the DB write fails on winbox/mac for these four verbs. The C4 code wrote that file instead of the DB for ORG_HOST=mac, which broke the w27 "one event row per call" check and polluted the repo (a 74-line file had been committed from test runs; removed).

**Dead worker, complete diff staged (real winbox run, task-18ff8da2).** The recorded pid is the CLI's, not the launcher's, so a dead pid alone does not prove the launcher is done. `completion()` now: pid dead; then if the winbox marker matches HEAD and tracked state is clean it is ready as before; if there is no marker (winbox) or tracked/staged changes (either host), it waits until the worktree's git state (`index`, `logs/HEAD`, no `index.lock`) has been still for `RECOVERY_QUIET_S` (300 s); then, with changes, `_recover_commit` stages tracked changes (`add -u`) and the task's own `docs/reports/<id>/REPORT.md` (header checked), unstages the launcher scratch files and media, commits with `--no-verify`, writes the winbox marker, and returns ready; the hub then flips the row to review and publishes. No report in the index: refuses and commits nothing. Untracked files are never added. `publish()` calls `completion(recover=False)`, so publish never commits. Tests use real git (`dead_worker` fixture): staged diff recovered, media and scratch excluded, untracked left, idempotent second call, unstaged tracked edit, recent state/live pid/`index.lock` wait, missing report, wrong report header, publish does not recover.

Constraint from PH#a08 during this run: Contabo was over its host-fill limit, so the whole suite was NOT run here. Only the three failing files and the files of the code I touched, one pytest call at a time. CI on PR #584 runs the full suite.

### Iteration 6 test tails (all from this worktree, `env -u ORG_DB_URL .venv/bin/python -m pytest -q -o addopts=''`)

```text
tests/test_w04_self_host_sites.py                46 passed in 11.13s
tests/test_w15_duty_split.py                     87 passed in 8.23s
tests/test_w27_security.py                       88 passed in 82.86s (0:01:22)
tests/test_remote_maintenance.py                 61 passed
tests/test_node_dispatch.py                      141 passed in 33.24s
tests/test_branch_poller_reopen.py + test_disk_steward.py + test_spawn_worker_ps1_runners.py
                                                 157 passed in 37.59s
tests/test_w23_mesh_dispatch.py                  85 passed in 15.11s
tests/test_node_dispatch_spawn_ph.py + test_node_dispatch_clevel_host.py + test_w33_node_dispatch_windows.py
  + test_w46b_node_fixes.py + test_w35_wire.py + test_w28_mesh_destination.py
                                                 755 passed, 1 skipped in 147.64s (0:02:27)
```

### Iteration 6 notes for the reviewer

- **Guard.** `scripts/hook-self-repo-guard.py` (ADR 0020) lists this task's touches as `tools/disk_steward.py, tools/gc_stale_tasks.py, tools/workdir.py, windows/spawn-worker.ps1, tests/test_disk_steward_remote.py, tests/test_remote_branch_collect.py`. PR #584 changes `runners/branch_poller.py`, `tools/node_dispatch.py`, `tools/remote_maintenance.py`, `lib/mesh.py`, `config/storage-policy.yaml` too. A Bash `sed -i` on `tools/remote_maintenance.py` was refused. Three of my commits (`0ea55d02`, `49a2fe6b`, `23cd6a15`) had already changed `runners/branch_poller.py`, `tools/node_dispatch.py` and `tools/remote_maintenance.py` with python file writes the hook did not intercept. I sent PH#a08 a `dev_message` with the paths to add to `touches`, and stopped writing under `lib/ runners/ tools/ config/`. If PH declines, revert those three commits.
- **What my change reaches.** `check_task`, `tick`, `_sweep_review_local_launchers` and `_publish_via_mesh` (callers: `check_task`, the review sweep; tests `test_w04`, `test_w15`, `test_w23`, `test_branch_poller_reopen`, `test_remote_maintenance`). `node_dispatch._check_args`, `parse_command`, `_audit` (every verb; tests `test_node_dispatch*`, `test_w23`, `test_w27`, `test_w33`, `test_w35`, `test_w46b`). `remote_maintenance.git/encode/decode/completion` (callers: `reap`, `publish`, `outgoing_check`, `hub_*`, `node_dispatch` verbs). Wire format change: every `encode()` caller is in this repo; both sides must deploy together.
- **The real-handlers fuzz** (`test_fuzz_real_handlers_refuse_unknown_rows_before_any_backend`) loop went from 1500 to 2000 cases: three more verbs in the generator's pool left 191 effective cases against its unchanged `ran >= 200` floor. No threshold was lowered.
- **Deploy order.** Hub and the winbox/Mac dispatcher checkouts must carry the same `remote_maintenance.py` and `node_dispatch.py`: an old node answers a hex payload with a refusal, and the row stays in review/in_progress (retry), never a wrong action.
- **Not covered by the hub poller:** a winbox/mac row dispatched by a PH on winbox or the Mac (`dispatcher_host` is not Contabo). The W1.5 contract leaves those to their own dispatcher's poller; winbox has none, and the Windows launcher no longer pushes. A PH publishing its own branch uses `publish_ph`; a worker dispatched from winbox would need a poller there or a decision from the CTO. Not widened here.

---

Implemented C4 and C5 on `agent/codex-task-c4939966` in the assigned worktree. The launcher owns commit/push of this submission. No branch switch, sparse-checkout change, deployment, PR creation, role edit, or systemd edit was performed.

## Design

Read the approved `state/ph-briefs/hostspawn-host-fill-plan.md`, including the requested rules, C4/C5, acceptance items, and prohibitions. Read the earlier design report from commit `78177800`. The latest CTO correction governs: existing Drive API archive, no rclone backend, and fake service tests.

### C4 — publication

1. `lib/db.py` is byte-identical to `origin/main`: status writes do not perform publication or synchronous mesh calls. Contabo's branch poller owns publication of the winbox/mac rows Contabo dispatched (W1.5 duty split) and retries persisted review rows; it needs `ORG_MESH_DISPATCH` on. Completion and review sweeps rotate at most three tasks per host per phase per tick.
2. `worker_completion` supplies the independent completion channel before a branch exists on origin. It checks a dead worker PID, a committed report with the correct task header, report freshness when `spawned_at` is supplied, and no tracked edits. Windows additionally requires a launcher marker matching HEAD. The hub records review, triggering publication. Existing external-runner artefact validation runs after publication and records its validated SHA; a refused gate marks the task failed.
3. `publish_branch <task-id> <hex-json>` is the new hub call. It carries only the hub's task metadata and checks task/host/worktree/branch binding against native configured roots, without querying a remote DB. The legacy task-ID-only interface remains for existing callers. The new remote maintenance/publication audit is local `state/mesh-audit/maintenance.jsonl`; it needs no DB credentials.
4. `publish_ph <hex-json>` shares the outgoing-object guard and immutable-SHA push. PH branches are explicitly bound as `ph/<sid8>-<topic>` and their worktrees must end in `__ph-<sid8>` under the host worktree root. From Contabo, request review/publication with `python -m tools.remote_maintenance winbox <sid8> ph/<sid8>-<topic> '<native-worktree-path>'` (use `mac` for Mac). Existing PH branches with other names require an explicit migration to this binding; the interface does not accept arbitrary refspecs or default branches.
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

Iteration 6 additions:

- The whole suite was not run (PH#a08: Contabo over its host-fill limit). Not run here: other files that import `node_dispatch`/`mesh` but whose code I did not change in behaviour (`test_mesh_followups`, `test_h1_node_probe`, `test_w25_spawn_c_level_mesh`, `test_start_clevel_remote`, `test_mesh_check*`, `test_multihost`, `test_l5_e2e`, others). If any reads the `_audit` fallback, the 256/8192 command cap, or `encode`, CI on #584 shows it.
- `RECOVERY_QUIET_S = 300` is a judgement, not a measurement. The recovery commit was tested with real git on Linux only; never against the real PowerShell launcher or a real winbox worktree. If a launcher is mid-step with still git state for more than 5 minutes, the hub and the launcher could both commit; the launcher's `git diff --cached --quiet` then finds nothing to commit and still writes its marker, and the worst case is one `index.lock` error in the launcher.
- The recovery commit takes tracked changes and the task's own report only. A new code file the worker never ran `git add` on stays untracked and is not published (the launcher's `add -A` would have taken it). A worker that leaves new files unstaged loses them from the branch; its report still reaches review.
- Redaction is pattern-based (`node_dispatch._SECRET_PATTERNS`: URL userinfo, `gh*_`/`github_pat_` tokens, `sk-`, `bearer|token|basic <16+ chars>`). A credential in another shape would pass. The text is cut to the last 300 characters after redaction, never before.
- Not verified on a live hub: the `ORG_MESH_DISPATCH` flag is on for the poller process (the hub step is silent without it, as the legacy publish already was).
- I could not tell from here which pid the hub stores for a Claude worker on winbox; the launcher's step 7 records the CLI process (claude.exe, node/codex.exe, agy.exe), not the PowerShell launcher. The quiet-window rule above rests on that reading of `windows/spawn-worker.ps1`.
- The three commits that touch `runners/`, `tools/` without a declared `touches` entry (see notes above) await PH#a08's decision.

Earlier iterations:

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

- `scripts/hook-self-repo-guard.py` (ADR 0020): this task's declared `touches` omit the files the PR changes; see the guard note in the iteration-6 reviewer notes. Deployment and live E2E verification remain PH/CTO responsibilities as stated above.

## Skill learning

- MISSING [CXO_Protocol_DevSpawn §touches] : a worker task whose brief was replaced (iter 1 "this brief replaces the earlier brief, which is void") kept the void brief's `touches`, so the self-repo guard refuses the new brief's real files; the C-level has to rewrite `touches` when it replaces a brief · evidence: task-c4939966, hook message listing disk_steward/gc_stale_tasks/workdir only
- MISSING [no owner] : the self-repo guard (ADR 0020) only reads Bash command text for write patterns, so a python heredoc that writes to tools/ or runners/ is not stopped, and the worker finds out about the declared touches only when a later `sed -i` is refused · evidence: task-c4939966 (3 commits under tools/ and runners/ before the first refusal) · prevented by: the DEV prompt naming the protected prefixes and the task's `touches` at spawn
- COSTLY [no owner] : the w27 oracle, the 256-character command cap and the plain-token regex in build_argv are three separate statements of the verb grammar; a new verb needs all three in step, and the failure message names only one · evidence: task-c4939966 iter 6 · prevented by: one shared grammar table the tests import (rejected so far: the oracle is deliberately independent)
- COSTLY [no owner] : a pytest run of w27 before the audit fix wrote 74 lines into the repo's `state/mesh-audit/maintenance.jsonl`, and `git add -A` committed them · evidence: commit 0ea55d02, removed in the next commits · prevented by: a `git status` look before `git add -A`

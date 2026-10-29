# REPORT task-876ebb6a

DiskSteward M3b implementation for PH project_head-9a54fd4d, lane CTO.
Prepared on existing feature branch `agent/codex-task-876ebb6a`, based on
`83ee1ee8` (also the locally available `origin/main`). Write-only: no installation,
SSH, Drive requests, live hub POST, service restart, or production DB access.

## Files changed

- `tools/drive_leg.py`: machine-contract routing with environment override;
  host-specific transcript/upload manifests, folders, and restore lookup;
  machine home/config paths for runner state; portable archive paths. Windows
  uses native handles to reject reparse points and pin ancestors during reads,
  and deletes verified files by handle rather than following a pathname again.
  Empty transcript directories are conservatively retained on Windows.
- `scripts/drive_rest_rclone_shim.py`: import-safe CLI, nested mkdir/rcat/lsjson,
  paginated folder listing, recursive/file/directory filters, duplicate-folder
  refusal, and the existing flat `--include` behavior.
- `config/machine-contract.yaml`: disk push env paths for Mac and Contabo;
  winbox is explicitly null because no pusher env location was found.
- `tools/disk_steward.py`: explicit skipped rows for DB-dependent actions when
  ORG_DB_URL is absent; Linux-only Docker/journal cleanup; host propagation to
  child commands; one best-effort end-of-tick hub POST, bounded by a 10-second
  timeout with redirects disabled and fixed token-silent failure reporting;
  report output includes the last steward band/time.
- `deploy/disk-hub/disk-hub-steward.patch` and `README.md`: reviewable unified
  diff, strict optional steward validation/storage/history, deployment notes.
  Existing volume-only pushes retain the last steward result.
- `tests/fixtures/disk_hub/disk-hub.py`: exact read-only production source
  snapshot used to apply/test the patch. Production source remains unchanged.
- `tests/test_disk_hub_steward_patch.py`, `tests/test_disk_steward_hosts.py`,
  `tests/test_disk_steward.py`, `tests/test_drive_leg.py`: host routing, nested
  fake REST calls, PureWindowsPath/reparse handling, old/new/invalid hub bodies,
  HTTP-error token silence, missing-DB completion, and host archive labels.

## Validation performed

- Final focused suite: **157 passed, 1 skipped** in 23.43 seconds. The skipped
  test requires native Windows handles/junctions.
- All pytest invocations ran from the assigned sparse worktree using the
  existing `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` interpreter; nothing
  was installed. Tests use fake REST/relay/network layers and temporary files.
- Focused command: `python -m pytest -o addopts='' -q
  tests/test_disk_hub_steward_patch.py tests/test_disk_steward_hosts.py
  tests/test_disk_steward.py tests/test_drive_leg.py tests/test_storage_policy.py
  tests/test_disk_steward_mac_installer.py tests/test_winbox_disk_steward_installer.py`.
- `git diff --check` passed. Fixture compared byte-identical to the production
  hub source. Hub patch is applied to a temporary fixture by the tests and
  exercised through the POST handler, without opening a network listener.
- Existing Mac and winbox installer files from PRs #539/#540 were not edited.
  The other worker's installer, P2 card, systemd units, and lineposter functions
  were not edited. No MAILBOX.md was present at the checks during this task.

## Not checked / risk

- Native macOS/Windows execution and real Drive/hub integration were not run.
  The Windows handle/junction integration test is included but skipped on Linux;
  it must pass on Windows before deployment. Windows empty-directory cleanup
  is intentionally deferred; verified regular files can still be reclaimed.
- No native Windows DB environment wrapper was found in windows/ or scripts/hub.
  The existing `with-org-db-env.sh` requires Bash and is not a native Windows
  wrapper. Without an inherited ORG_DB_URL, winbox DB actions/letters skip.
- Winbox's disk-push env location was not found in windows/ or docs. Its hub
  POST skips until `machines.winbox.disk_push_env` is populated.
- The hub patch is not deployed. A service owner must review/apply it before
  production ticks can appear in hub documents. Mac/Contabo report skipped
  if their configured env file or either required value is absent.
- Native Windows deletion uses a handle API not exercised by Linux mocks.
  Concurrently opened or inaccessible sources fail closed rather than following
  links. Existing restore operations requiring rclone cat are outside this
  shim extension (mkdir/rcat/lsjson only).
- No real-PG tests were needed or run. No other worker's unmerged changes were
  available locally; shared tick/plan edits need reconciliation if their weekly
  stamp changes land first.

## Blockers

- `git fetch origin main` failed before contacting the remote: shared worktree
  `FETCH_HEAD` is on a read-only filesystem. The Git metadata directory is outside
  the writable worktree roots, and escalation is disabled. A subsequent rebase
  attempt refused the uncommitted changes. Cannot fetch/commit/stash/rebase/push
  here; launcher must commit the prepared files, fetch/rebase onto current main,
  reconcile any weekly-stamp overlap, rerun the focused suite, and open the PR.
  No PR was created in this session.

## Skill learning

- (none)

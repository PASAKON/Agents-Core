# REPORT task-75170d94

Implemented DiskSteward M3c as a write-only change on feature branch `agent/codex-task-75170d94`. No SSH, remote installation, service changes, or scheduled-task changes were performed. The existing winbox team checkout is only fetched by the future card, never switched, pulled, or reset.

## Files changed

- `scripts/winbox-install-disk-steward.sh`: elevation gate; fetch and detached dedicated worktree preparation; dirty-tree refusal; venv creation and PyYAML/import verification; three SHA256 pins and remote certutil checks; dated pusher backup, status-path configuration, deployment, and rollback verb.
- `windows/disk-steward/disk-steward-tick.ps1`: prefer the dedicated `Agents-Core` checkout even when another candidate becomes ready.
- `windows/disk-push/disk-push.ps1`: reference SYSTEM pusher plus validated optional steward status, changed-timestamp reporting, and last-successful-timestamp persistence. Token read is unchanged. Failure logging is deliberately redacted because the old exception text could expose the authenticated URL; neither token nor POST body is logged.
- `tools/disk_steward.py`: atomically replace `state/storage/steward-<host>.json` at the end of each live tick; dry runs do not write it. Preserve Mac/Contabo direct pushes; winbox records `skipped`, reason `carried by the SYSTEM pusher`.
- `config/machine-contract.yaml`: winbox `disk_push: system_pusher`.
- `tests/test_winbox_disk_steward_installer.py`, `tests/test_disk_steward_hosts.py`, `tests/test_disk_hub_steward_patch.py`: pins, static PowerShell validation, installer guards, executable resolver preference, atomic/live-only status, SYSTEM routing, and winbox hub field compatibility.

## Card and rollback

After this change is merged into origin/main and the Contabo card checkout contains it, the exact Run card command is:

```sh
bash scripts/winbox-install-disk-steward.sh install
```

Run from `/opt/MoonieXHQ/Agents/Core`. The installer requires an elevated passg SSH session and fails closed otherwise. It retains the steward's existing InteractiveToken/LeastPrivilege registration and does not modify the SYSTEM pusher task or token ACL.

Exact rollback command from the same checkout:

```sh
bash scripts/winbox-install-disk-steward.sh rollback
```

Rollback reads `C:\ProgramData\mooniex\disk-steward-pusher.backup`, validates its dated `.bak` path, restores that pusher, removes `steward-status.path`, and unregisters `MooniexDiskSteward`. The backup and dedicated checkout remain available. Each install records its own pre-install pusher backup; rollback restores the most recent one. A failure after deployment may leave a partial installation; use this rollback command.

## Validation performed

- Read the handoff pusher from the explicitly authorized main-checkout state path; SHA256 `511df6141c24b8b60019c5590b7a187769f16da40687e5dea3b9521efb019c2d`.
- Checked imports: `disk_steward` and `storage_policy` require stdlib plus PyYAML for this Windows/no-DB path; optional psutil is already guarded. The card imports `tools.disk_steward` with its prepared interpreter.
- From the assigned worktree, ran `PYTHONDONTWRITEBYTECODE=1 /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -o addopts='' -q tests/test_winbox_disk_steward_installer.py tests/test_disk_steward_hosts.py tests/test_disk_steward.py tests/test_disk_hub_steward_patch.py`: **99 passed, 1 skipped**. Reused the available interpreter; no packages installed. System Python lacked pytest. No pytest invocation ran in the main checkout.
- `bash -n scripts/winbox-install-disk-steward.sh`, local `--print-sha`, and `git diff --check` passed. Pin tests are collected by the existing CI pytest job, so stale pins fail CI.
- The existing `deploy/disk-hub/disk-hub-steward.patch` already implements the requested storage semantics. Tests apply it to the fixture and POST the exact `steward: {band, tick_at, actions}` fields for winbox, verifying persistence. No duplicate hub implementation was added.

## Not checked / risk

- No native PowerShell, Windows certutil, elevation/UAC, venv bootstrap, Git worktree, scheduler, or live hub integration was exercised. The Windows handle test is the one skip. PowerShell checks are offline/static as requested.
- The deployed hub must already have the steward patch applied; this task did not inspect or mutate the live hub. The PH must verify receipt after the first live tick and next SYSTEM pusher run.
- The existing SYSTEM task polls every ten minutes; the latest status forces reporting on its next invocation. A single status file retains the latest tick, not a queue of ticks during outages.
- The steward still requires the console user to be logged on because its registration remains InteractiveToken. Optional DB-dependent operations remain skipped without their existing environment.
- The launcher owns committing and pushing these changes. PR creation is pending that publication; no PR URL is available from this write-only worker.

## Blockers

- No implementation blockers. Deployment and live validation are intentionally deferred to the PH Run card. Launcher handoff must publish the feature branch and open the PR before merge.

## Skill learning

- PowerShell/.NET `$` accepts a position before a trailing newline; use `\A[a-z]{1,10}\z` for the strict steward band check (covered by the static pusher contract test).

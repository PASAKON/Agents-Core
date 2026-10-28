# REPORT task-75ed5404

## Changes
- Feature branch: `agent/codex-task-75ed5404`; default branch untouched. Launcher owns commit/push; PR creation remains a post-push handoff.
- `windows/disk-steward/disk-steward-tick.ps1`: validates its checkout against paths derived from `machines.winbox.home`/`hq`, requires the P1 contract, uses the checkout venv with UTF-8, runs local winbox tick, propagates failure, rotates the 5 MiB log to one `.1` backup. Dry-run skips wrapper log writes.
- `windows/disk-steward/register-disk-steward.ps1`: repeatable replacement of MooniexDiskSteward, indefinite 30-minute interval, interactive token/limited privileges, overlap suppression, 29-minute timeout, XML-only preview, idempotent uninstall, printed rollback. SSH registration requires the SSH identity to match the logged-on console user.
- `scripts/winbox-install-disk-steward.sh`: explicit install/status verbs, local and remote SHA verification, certutil remote hashes, encoded PowerShell over SSH, SCP of only the two payloads, registration then one dry-run (first 40 lines, exit preserved). `--print-sha` is entirely local.
- `.claude/skills/ALL_Rules_DiskHygiene/references/new-host-template.md`: contract, policy, scheduler, hub evidence, host reference and rollback checklist.
- `tests/test_winbox_disk_steward_installer.py`: pin/content checks, template headings, task XML semantics and local hash helper.
- No P1 files edited. Read P1 via `git show origin/agent/codex-task-c5796945:...`.

## Validation
- From this assigned worktree: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_winbox_disk_steward_installer.py` — 4 passed. Only the interpreter was borrowed; pytest was not run in the main checkout.
- `bash -n scripts/winbox-install-disk-steward.sh` — passed.
- `git diff --check` — passed.
- No SSH/SCP, installation, task registration, or tick executed on winbox.

## Card handoff
After P1 and these changes are deployed to a ready checkout, the exact Contabo card command (from the Agents-Core repository root) is:

```bash
bash scripts/winbox-install-disk-steward.sh install
```

Read-only status: `bash scripts/winbox-install-disk-steward.sh status`.
Recompute pins after edits: `bash scripts/winbox-install-disk-steward.sh --print-sha`, then update both constants in the card script and rerun pytest.

Pinned SHA256 values:
- `disk-steward-tick.ps1`: `62d3b65634b803c9a26d736d5a4b0fc1873cdc1a9e80b047e0154e374ba1e7f9`
- `register-disk-steward.ps1`: `1e1056b82cb2191adc0d3d2013d97cd8c5d0f25dc6c11e0cbc5931afc6f27ca8`

The registrar prints the absolute rollback command ending in `-Uninstall` before any mutation. If the post-registration dry-run fails, the task remains registered: inspect output and use that rollback command if needed.

## Not checked / risk
- PowerShell is unavailable locally; Windows parsing, Task Scheduler acceptance, certutil output, SSH identity permissions, native output encoding and actual rotation remain unverified on Windows.
- P1 is unmerged here. The card deliberately refuses a local contract lacking P1 scheduler/drive_leg fields; the wrapper independently validates the remote contract. Deployment must include P1, PyYAML in the Windows checkout venv, and local rclone configuration.
- Interactive tasks require the user to be logged on. No elevation or stored credentials are requested; local policy may refuse task registration.
- SCP paths with spaces or shell metacharacters are rejected explicitly. Known contract-derived checkout suffixes include the existing SafeRestart `mooniex/repo/MoonieX-Agents` location.
- Actual tick policy effects, disk hub delivery, Drive access, and 48-hour operation were not tested. The new-host checklist requires hub evidence after authorized installation.
- PR not created before launcher commit/push; no remote publication was attempted.

## Blockers
- None for the write-only deliverable. Windows execution and deployment verification are intentionally deferred to the authorized card; PR handoff follows launcher push.

## Skill learning
- Existing `scripts/winbox-restart.sh` documents the deployed clone suffix `mooniex/repo/MoonieX-Agents`; derive its home prefix from the contract and include that suffix when discovering Agents-Core, rather than assuming the repository folder is named Agents-Core.

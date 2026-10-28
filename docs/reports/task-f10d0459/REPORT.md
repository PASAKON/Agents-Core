# REPORT task-f10d0459

## Result
- Implemented the write-only M3 Mac LaunchAgent installer on feature branch `agent/codex-task-f10d0459`. Nothing was installed or executed on the Mac; all execution tests use temporary fixtures and mocked launchctl on this worker.
- CEO sentence (run from the Mac's Agents/Core checkout after the prerequisites below are resolved):

อนุญาตให้ติดตั้ง disk steward บน Mac: bash scripts/install-disk-steward-mac.sh

## Files changed
- `deploy/launchd/com.mooniex.disk-steward.plist`: installer-rendered ROOT/HOME template, 1800-second interval, RunAtLoad, user agent.
- `scripts/disk-steward-mac.sh`: resolves its own checkout, reads and validates machines.mac using repo venv PyYAML, exports HOME/MOONIEX_HQ/CLAUDE_CONFIG_DIR/ORG_HOST, invokes `bash scripts/hub/org-python.sh tools/disk_steward.py tick --host mac`, preserves failure status, streams output into `state/storage/steward-mac.log` with 5 MiB rotation and one backup.
- `scripts/install-disk-steward-mac.sh`: XML-safe rendering, read-only `--dry-run`, `--uninstall`, rejects live root/non-Mac installation, bootout/bootstrap in gui/$UID, repeatable install/uninstall, exact rollback command.
- `tests/test_disk_steward_mac_installer.py`: offline fixture coverage.
- This report. No P1 files edited.

## Validation performed
- From this assigned worktree: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -q tests/test_disk_steward_mac_installer.py` — 5 passed. The shared interpreter was borrowed read-only; pytest was NOT run in the main checkout.
- Tests cover fake `/Users/someone` home with no `/Users/gob`, XML parsing without plutil, checkout paths containing spaces and ampersands, dry-run filesystem immutability, uninstall dry-run preserving an existing plist, clear missing mac row failure, contract environment, exact org wrapper invocation, log rotation, child exit status, repeated installation and uninstallation through mocked launchctl.
- `bash -n scripts/disk-steward-mac.sh scripts/install-disk-steward-mac.sh` — passed.
- `git diff --check` — passed.
- Read plan §4 and the org-resume/install-mac-agent patterns. MAILBOX.md was absent at checks.

## Drive routing audit
Inspected P1-A with `git show origin/agent/codex-task-c5796945:<path>` at commit `5662ddd4ade2e08e293ce144605f48568099747b`.

- `config/machine-contract.yaml:34` declares mac `drive_leg: rest_work_archive`.
- `tools/disk_steward.py:86` builds daily `drive_leg.py transcripts` and `drive_leg.py runner-state` commands. `tick()` selects host paths but does not dispatch those calls by drive_leg.
- `tools/drive_leg.py:65` defaults to `scripts/rclone_via_winbox.sh`; its upload core uses rclone, not `tools/work_archive.py` REST. No REST routing branch was found in that file.
- Therefore the declared Mac REST route is NOT implemented for these daily calls in the inspected P1-A. There is no Drive Desktop mount introduced by this delivery, but declaring the REST route in the contract does not enforce the upstream transport. The runner validates the declaration only. P1 files were deliberately left untouched.

## Blockers
- Before live Mac installation, P1 owner must implement/verify daily Mac archive dispatch through `tools/work_archive.py` REST and merge the steward dependency. Do not treat this installer as fixing that routing gap.
- Commit/push and PR handoff remain with the launcher per the worker contract; this worker has left changes on the assigned feature branch for that handoff. No PR URL is available yet.

## Not checked / risk
- No actual macOS launchd bootstrap, GUI login, org DB connectivity, credentials, REST upload, or live steward tick was tested (WRITE ONLY scope).
- The Mac needs its repo venv with PyYAML and the P1 steward/config. Paths in machines.mac must describe the installing GUI user; update that contract on the owning branch when installing for a different user.
- RunAtLoad starts a live tick immediately on bootstrap. Resolve the routing blocker before using the CEO install command.
- Errors before the logging pipeline (missing venv/config/steward) go to stderr; normal steward stdout/stderr is rotated. A single oversized output line can exceed the rotation threshold until the next line, as with Python RotatingFileHandler.
- Actual macOS Bash 3.2 was not available; scripts use compatible syntax and passed local bash syntax validation.

## Skill learning
- (none)

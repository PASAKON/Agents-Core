# <host> — Disk Steward onboarding

## Machine contract
- [ ] Add `machines.<host>` in `config/machine-contract.yaml`: `os`, `home`, `hq`, `band`, `scheduler`, and `drive_leg`.
- [ ] Select the actual scheduler (systemd, launchd, task_scheduler) and Drive transport. Winbox uses `rclone_local`.

## Storage policy
- [ ] Add `hosts.<host>` bands in `config/storage-policy.yaml`; document thresholds and ownership here.
- [ ] Review protected paths, active workloads, secrets, and checksum-before-delete requirements.

## Scheduler installation
- [ ] Deploy the merged steward and dependencies; run `tick --host <host> --dry-run` first.
- [ ] Install via the host's scheduler every 30 minutes, with logs and overlapping runs prevented.
- [ ] Record the reviewed installer command, pins, task identity, log path, and rollback command.

## Disk hub verification
- [ ] After authorized installation, verify a tick reaches the disk hub: record the host, timestamp, free-space reading, and hub evidence.
- [ ] Check last run result and local logs; a successful dry-run alone is not proof of hub delivery.

## Host reference
- [ ] Copy this template to `references/<host>.md`, fill in host-specific scope and never-touch paths, and link the evidence.

## Rollback
- [ ] Record and verify the host scheduler's uninstall/disable command; retain logs for diagnosis.

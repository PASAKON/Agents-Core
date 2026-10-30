# REPORT task-1f4497f0

## Changes

- `scripts/org-resume.sh`: direct psycopg hub probe through org-python.sh,
  connect_timeout=3 and SELECT 1, with all probe output suppressed. No lib.db
  snapshot fallback. Wait increased to 600 seconds. Failed resume gets three
  additional attempts 60 seconds apart (four total), then report --notify runs
  once. Successful retry clears the earlier failure; final failure is retained.
- `scripts/org-postgres-tailnet.sh`: waits 300 seconds for the configured IPv4
  address on an interface (same default/TAILNET_IP override as provisioning).
  Checks the exact address/5432 listener with ss; restarts org-postgres at most
  once if absent, checks for up to ten seconds, and fails if still absent.
  No container removal, network changes, or volume operations.
- `deploy/systemd/org-postgres-tailnet.service`: oneshot ordered after and wanting
  tailscaled/docker, enabled via multi-user.target; six-minute timeout.
- `deploy/systemd/org-resume.service`: wants and follows the tailnet helper.
- `docs/ops/safe-restart.md`: boot ordering, retry behavior, and later-card copy,
  daemon-reload and enable commands for both units.
- `tests/test_org_resume_boot.py`: isolated boot regressions; command call logs
  contain argc only, never environment values.

Alternative considered: `sysctl net.ipv4.ip_nonlocal_bind=1` would allow binding
before the address exists. It was not selected because it changes host-wide
binding behavior, whereas this helper targets only the affected container and
explicitly verifies address and listener readiness. No sysctl was changed.

## Validation

- `python3 -m unittest discover -s tests -p test_org_resume_boot.py -v`:
  **10 passed**, zero skips. Includes failed psycopg with an existing SQLite
  snapshot, suppressed exception/URL output, retry exhaustion and recovery,
  notification failure, listener present/missing/unrecoverable, and missing IP.
- `bash -n`: both changed/new scripts plus org-python.sh and with-org-db-env.sh
  passed (within the test suite).
- `systemd-analyze verify`: both units passed with isolated dummy docker and
  tailscaled dependency units; no host service invocation.
- `git diff --check`: passed.
- Broader `test_restart_*.py` discovery: four import errors because pytest is
  unavailable in system Python; no dependencies installed.
- Gitleaks 8.30.1: all seven changed/new files scanned with redaction;
  **no leaks found**.

## Not checked / risk

- No live Docker, Tailscale, database, notification, or reboot exercised. Nothing
  installed/enabled and no /etc changes. PH rollout card must verify real boot.
- A restart may not repair a container whose bridge attachment is already
  damaged; helper deliberately fails rather than changing its network/volume.
- Listener detection checks the specific IPv4 bind, not application health;
  the separate psycopg probe supplies database readiness.
- Existing 15-minute resume service timeout remains: a ten-minute hub wait and
  three one-minute retry sleeps leave about two minutes for recovery commands
  in the worst case. Large/slow recovery may still need a manual retry.
- Deadline checks can overrun by one bounded probe/poll interval; Docker restart
  is ultimately bounded by the helper unit's six-minute timeout.

## Blockers

- Initial HEAD equals origin/main at 3a5ea30a90cb86bc94e6aa57d367366ac9e406b3;
  work is on agent/codex-task-1f4497f0. No default branch changes or pushes.
- Requested sparse narrowing failed: Git's config.worktree is outside the
  writable worktree and mounted read-only. Existing sparse exclusions retained.
- `git add` failed creating the external worktree index.lock (read-only file
  system), so a local commit cannot be made in this sandbox. Launcher must stage,
  commit and push the delivered files as specified by the worker contract.

## Skill learning

- (none)

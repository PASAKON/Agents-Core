# REPORT task-30206a64

Creation of four systemd unit files and one install note for the weekly tool-value report (plan `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` §3.3, task T2).

## What changed

Created the four systemd unit files in `deploy/systemd/` and an operations/install guide in `docs/ops/`:
1. `deploy/systemd/tool-value-collect.service`: Oneshot service that runs `tools/tool_value.py collect` via `with-org-db-env.sh`, configured with resource limits (`Nice=10`, `MemoryMax=300M`, `TimeoutStartSec=15min`).
2. `deploy/systemd/tool-value-collect.timer`: Timer scheduled for `Mon *-*-* 07:30:00 Asia/Bangkok`, `Persistent=true`, `AccuracySec=1min`.
3. `deploy/systemd/tool-value-report.service`: Oneshot service that runs `tools/tool_value.py report` via `with-org-db-env.sh`, ordered `After=tool-value-collect.service` to ensure collect finishes first on catch-up runs.
4. `deploy/systemd/tool-value-report.timer`: Timer scheduled for `Mon *-*-* 08:00:00 Asia/Bangkok`, `Persistent=true`, `AccuracySec=1min`.
5. `docs/ops/tool-value-timers.md`: Documentation covering units, schedule, tmux cgroup pre-install checks, install commands, verification checks, dry run, and uninstallation.

## Files changed

- `deploy/systemd/tool-value-collect.service` (new)
- `deploy/systemd/tool-value-collect.timer` (new)
- `deploy/systemd/tool-value-report.service` (new)
- `deploy/systemd/tool-value-report.timer` (new)
- `docs/ops/tool-value-timers.md` (new)
- `docs/reports/task-30206a64/REPORT.md` (new)

## Validation performed

- File-only task per remote worker contract and brief instructions ("Files only: write them, run nothing. The reviewer checks them.").
- Checked systemd unit syntax against repository conventions in `deploy/systemd/org-snapshot.service` and `deploy/systemd/org-snapshot.timer`.
- Verified calendar specification format and timezone specification `Asia/Bangkok`.
- Verified quoting of exact tmux cgroup check commands from `CLAUDE.md`.
- Verified exact CLI command paths and argument structure against `tools/tool_value.py` and `scripts/hub/with-org-db-env.sh`.

## Limitations

- No shell commands were run by this agent per task instructions ("Do not run any command; the reviewer runs systemd-analyze verify"). Reviewer verifies units with `systemd-analyze verify`.

## Blockers

- (none)

## Skill learning

- (none)

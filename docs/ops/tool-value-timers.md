# Tool-Value Weekly Report Systemd Units

Operations and installation guide for the weekly tool-value report systemd units on Contabo (plan `docs/plans/tool-value-weekly-and-enforcement-2026-10-13.md` §3.3, task T2).

## What the Units Do and When (Bangkok Time)

Four systemd units in `deploy/systemd/` manage the automated weekly tool-value collection and reporting on Contabo:

1. **`tool-value-collect.timer`**:
   - Runs `tool-value-collect.service` every Monday at **07:30 Bangkok time** (`OnCalendar=Mon *-*-* 07:30:00 Asia/Bangkok`).
2. **`tool-value-collect.service`**:
   - Collects tool usage across all local sources on Contabo for the week and writes this host's tool-value row (`tool_usage_week` event) to the Postgres hub.
   - Runs `tools/tool_value.py collect` via `/opt/MoonieXHQ/Agents/Core/scripts/hub/with-org-db-env.sh` and `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.
3. **`tool-value-report.timer`**:
   - Runs `tool-value-report.service` every Monday at **08:00 Bangkok time** (`OnCalendar=Mon *-*-* 08:00:00 Asia/Bangkok`).
4. **`tool-value-report.service`**:
   - Reads the weekly hub rows from all reporting hosts, builds the two-week comparison table and Thai summary (reporting "ไม่มีข้อมูล" for any host with no row, never guessing), writes `state/reports/tool-value/<week>.md` and `.json`, and sends one letter to SomPong (COO), who takes it to the CEO.
   - Has `After=tool-value-collect.service` so that on boot catch-up (`Persistent=true`), collection completes before reporting.

Both timers specify the `Asia/Bangkok` timezone directly in `OnCalendar`, so the Contabo server clock (CEST until 25 Oct, then CET) needs no manual +5/+6 h arithmetic.

## Before Installing: Tmux Cgroup Check

Before installing or restarting any service on Contabo, perform the tmux cgroup check from `CLAUDE.md` §"Contabo — one tmux server holds every session". These units are new and hold no tmux pane, but the check is the org rule.

Quoted from `CLAUDE.md`:
```bash
for p in $(pgrep -f '^tmux'); do echo $p $(tail -1 /proc/$p/cgroup); done
for pp in $(tmux list-panes -a -F '#{pane_pid}'); do tail -1 /proc/$pp/cgroup; done | sort | uniq -c
```

If either names that service, do not restart it; tell the CEO.

## Install (as root)

Execute the following exact commands as `root`:

```bash
cp /opt/MoonieXHQ/Agents/Core/deploy/systemd/tool-value-collect.service /etc/systemd/system/
cp /opt/MoonieXHQ/Agents/Core/deploy/systemd/tool-value-collect.timer /etc/systemd/system/
cp /opt/MoonieXHQ/Agents/Core/deploy/systemd/tool-value-report.service /etc/systemd/system/
cp /opt/MoonieXHQ/Agents/Core/deploy/systemd/tool-value-report.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tool-value-collect.timer tool-value-report.timer
systemctl list-timers 'tool-value-*'
```

## Check

Verify the next scheduled run time using `systemd-analyze calendar`:

```bash
systemd-analyze calendar 'Mon *-*-* 07:30:00 Asia/Bangkok'
```

Inspect service journal output after a run:

```bash
journalctl -u tool-value-report.service -n 50
```

## Dry Run Without the Timers

To test report generation without the timers:

```bash
bash scripts/hub/org-python.sh tools/tool_value.py report --dry-run
```

## Remove

To remove the units:

```bash
systemctl disable --now tool-value-collect.timer tool-value-report.timer
rm -f /etc/systemd/system/tool-value-collect.service /etc/systemd/system/tool-value-collect.timer /etc/systemd/system/tool-value-report.service /etc/systemd/system/tool-value-report.timer
systemctl daemon-reload
```

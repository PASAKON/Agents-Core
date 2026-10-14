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

## Where the code runs: a pinned deploy worktree

Contabo's local main is held (a60f1744) and has neither `tools/tool_value.py` nor these units, so the
units run the code from `/opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy`. That worktree is
checked out detached at the origin/main sha the gate landed, and moves only by hand, so what runs as root
is what was reviewed.

- `Environment=ORG_ROOT=/opt/MoonieXHQ/Agents/Core` sends every data path (state/, the ledgers, the
  mailbox, `state/reports/tool-value/`) to the live checkout.
- The letter to SomPong goes through the live checkout's own `tools/send_to_cxo.py`
  (`tool_value._send_via_live_checkout`), which finds SomPong's session and writes the mailbox format the
  live inbox hook reads.
- The hub wrapper is the live checkout's `scripts/hub/with-org-db-env.sh`, the one
  `org-snapshot.service` already uses.
- Measured 2026-10-14 (`report --week 2026-10-06 --dry-run`): 42 s and 52 MB peak RSS, inside
  `TimeoutStartSec=15min` and `MemoryMax=300M`.

## Install (as root)

`<SHA>` is the origin/main commit that carries this file.

```bash
git -C /opt/MoonieXHQ/Agents/Core fetch origin main
git -C /opt/MoonieXHQ/Agents/Core worktree add --detach /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy <SHA>
cp /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy/deploy/systemd/tool-value-collect.service \
   /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy/deploy/systemd/tool-value-collect.timer \
   /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy/deploy/systemd/tool-value-report.service \
   /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy/deploy/systemd/tool-value-report.timer \
   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tool-value-collect.timer tool-value-report.timer
systemctl list-timers 'tool-value-*'
```

`enable --now` starts the timers, not the services: nothing runs until Monday 07:30 BKK.

## Update the code

After the gate lands a newer sha: `git -C /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy checkout --detach <NEW_SHA>`
(after a `fetch`). Re-copy a unit file only if it changed, then `systemctl daemon-reload`.

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
cd /opt/MoonieXHQ/Agents/Core
ORG_ROOT=/opt/MoonieXHQ/Agents/Core bash scripts/hub/org-python.sh worktrees/tool-value-deploy/tools/tool_value.py report --dry-run
```

`--dry-run` prints the report and writes and sends nothing. `--week 2026-10-06` prints the 6–12 Oct table
against 29 Sep–5 Oct.

## Remove

To remove the units:

```bash
systemctl disable --now tool-value-collect.timer tool-value-report.timer
rm -f /etc/systemd/system/tool-value-collect.service /etc/systemd/system/tool-value-collect.timer /etc/systemd/system/tool-value-report.service /etc/systemd/system/tool-value-report.timer
systemctl daemon-reload
git -C /opt/MoonieXHQ/Agents/Core worktree remove /opt/MoonieXHQ/Agents/Core/worktrees/tool-value-deploy
```

## Retire the deploy worktree

Once local main carries `tools/tool_value.py`, change both `ExecStart=` paths to
`/opt/MoonieXHQ/Agents/Core/tools/tool_value.py`, run `systemctl daemon-reload`, and remove the worktree
with the last command above. `send_to_coo` then sends in-process, because `ORG_ROOT` and the code's
checkout are the same tree.


# Machine Contract — schedules

What runs `tools/machine_doctor.py check` (registry vs disk, ADR 0031, IRON §58) where,
how often, and the file each machine's scheduler needs. Written by the Contabo CTO
(docs/ops/briefs/machine-contract-phase1.md item 5); **none of these are installed by
this repo** — each CTO installs their own machine's entry as noted below.

## Table

| Machine | Scheduler | Cadence | Command | Schedule artifact (this repo) | Installed? |
|---|---|---|---|---|---|
| Contabo | cron (root) | weekly, Mon 04:00 UTC | `python3 tools/machine_doctor.py --machine contabo check` | the line below, in this doc | **No** — Contabo CTO runs `crontab -e` |
| winbox | Task Scheduler | weekly, Mon 04:00 local | `py -3 "C:\mooniex\Agents\Core\tools\machine_doctor.py" --machine winbox check` | `windows/winbox-reinstall/rebuild/MachineContractDoctor.xml` | **No** — imported by `rebuild_r2.ps1` (now includes it in its `$core` task list) or by hand: `schtasks /Create /TN MachineContractDoctor /XML MachineContractDoctor.xml` |
| Mac | launchd | weekly, Mon 04:00 local | `.venv/bin/python tools/machine_doctor.py --machine mac check` | `scripts/com.gob.machine-doctor.plist` | **No** — Mac CTO copies it to `~/Library/LaunchAgents/` and runs `launchctl load` |

All three point at the same weekly cadence; only the local-time base differs (Contabo's
line is UTC by cron convention, winbox/Mac use each scheduler's local-time fields — exact
cross-machine synchronization does not matter for a disk-hygiene report). `check` exits 1
when it finds a problem and never deletes anything (§58 rule 2) — the exit code and its
stdout are what a human (or a later notify step, not built here) reads.

A separate, event-driven trigger — `--on-version-change` (reads
`$CLAUDE_CONFIG_DIR/.last-update-result.json`, runs `check` only if the recorded Claude
Code version differs from the last snapshot's) — is code-complete in `tools/machine_doctor.py`
per item 3, but wiring it to an actual Claude Code hook is not part of this brief; the three
schedules above are the standing weekly `check` only.

## Contabo cron line

Not installed by this task (brief: "the CTO installs crontab"). To install, the Contabo
CTO runs `crontab -e` and adds:

```cron
0 4 * * 1 cd /opt/MoonieXHQ/Agents/Core && /opt/MoonieXHQ/Agents/Core/.venv/bin/python3 tools/machine_doctor.py --machine contabo check >> state/machine-doctor.log 2>&1
```

`0 4 * * 1` = 04:00 UTC every Monday (cron's day-of-week `1` = Monday; the box's crontab
already runs in UTC — see the existing `acme.sh` and paused `cookierun_teachers` lines via
`crontab -l`). Uses the repo's own `.venv` (has PyYAML) rather than bare `python3`, and logs
to `state/machine-doctor.log` (not tracked in git — matches the CONFIG-class treatment other
logs get; add a `.gitignore` line if it turns out to grow).

## winbox: MachineContractDoctor.xml

`windows/winbox-reinstall/rebuild/MachineContractDoctor.xml`, modeled 1:1 on the captured
`state/winbox-blueprint-20260924/tasks/CookieRun-DiskSense.xml` (same `<Settings>`/
`<IdleSettings>` block, `LogonType>InteractiveToken`), with:
- `<Principal>`/`<Author>` = `GoB\passg` (today's account, post-2026-09-24 reset — never
  the old `UsEr` account CookieRun-DiskSense.xml was captured under).
- Trigger changed from `CookieRun-DiskSense`'s daily `ScheduleByDay` to a weekly
  `ScheduleByWeek` (`WeeksInterval=1`, `DaysOfWeek=Monday`), `StartBoundary`
  2026-09-28T04:00:00 (the next Monday after this file was written).
- Action: `py -3 "C:\mooniex\Agents\Core\tools\machine_doctor.py" --machine winbox check`,
  `WorkingDirectory=C:\mooniex\Agents\Core` — assumes Agents-Core is cloned there (the
  registry's own `<hq>/Agents/{Core,...}` row, `machine: all`, already assumes this) and
  that `py`'s default Python 3 has PyYAML (`py -3 -m pip install pyyaml` if not — this
  could not be verified from Contabo; no Windows box to test against).

Encoding: UTF-16LE with a BOM and CRLF line endings, matching every other task XML this
repo already carries (`file` reports byte-identical encoding to CookieRun-DiskSense.xml) —
`schtasks /Create /XML` expects this. If it ever complains about encoding on the real box,
re-save with PowerShell: `Get-Content -Raw MachineContractDoctor.xml | Set-Content -Encoding
Unicode MachineContractDoctor.xml`.

Not installed by this task. Two ways to install, either works:
1. **Rebuild path**: `windows/winbox-reinstall/rebuild/rebuild_r2.ps1`'s `$core` task list
   now includes `'MachineContractDoctor'` (added by this task) — a normal `rebuild_r2.ps1`
   run imports it like every other core task, rewriting the account if the source XML still
   named the old one (a no-op here, since this XML was authored fresh for `passg`).
2. **By hand**: `schtasks /Create /TN MachineContractDoctor /XML MachineContractDoctor.xml`.

## Mac: com.gob.machine-doctor.plist

`scripts/com.gob.machine-doctor.plist` (next to `scripts/mac_blueprint.sh`, the item-2
capture script this doctor checks against), modeled on the two plists already in this repo:
`claude-home/launchd/com.gob.claude-prune-transcripts.plist` (naming/label convention,
`com.gob.*`, `LowPriorityIO`+`Nice` for a background job) and `scripts/com.mooniex.agents-
watchdog.plist` (post-HQ-move paths: `.venv/bin/python`, `/Users/gob/MoonieXHQ/Agents/Core`).
`StartCalendarInterval` `{Weekday: 1, Hour: 4, Minute: 0}` = every Monday 04:00 local time
(launchd's calendar trigger is always local time, unlike cron's UTC here). Logs to
`state/machine-doctor.log` (same relative path as Contabo's, not tracked in git).

Not installed by this task (brief: "Must not be run here (no macOS)" applies to the whole
machine-contract-phase-1 Mac deliverable set). The Mac CTO installs it:

```bash
cp scripts/com.gob.machine-doctor.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.gob.machine-doctor.plist
```

## Installed state (2026-09-24, cto-6ebacd0e)

| Machine | Job | When (local scheduler) | Installed | Evidence |
|---|---|---|---|---|
| Contabo | `tools/machine_doctor.py --machine contabo check` | cron Mon 04:00 UTC | yes | `crontab -l`; first live check clean after `/root/.cache`+`/root/.local` were classified REBUILD |
| Contabo | `tools/drive_leg.py docker-volumes` / `uploads` / `transcripts` | cron Sun 02:30 / 03:00 / 03:30 UTC (staggered: one winbox relay stream at a time) | yes | `crontab -l`; first real runs 2026-09-24 in `~/.claude/logs/drive-archive.log` |
| winbox | `MachineContractDoctor` (`py -3 C:\mooniex\Agents\Core\tools\machine_doctor.py --machine winbox check`) | schtasks Mon 04:00, account passg | yes | `windows/winbox-reinstall/rebuild/doctor_setup.cmd` (sparse clone + PyYAML + task); check clean after commit 1c9a525a |
| Mac | `com.gob.machine-doctor.plist` + `scripts/mac_blueprint.sh` | launchd weekly | **no — Mac CTO** | hand-off letter in `state/letters-to-mac-cto.md`; the Mac is mid-wipe (drill #2) |

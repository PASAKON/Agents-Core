# Safe restart and daily Clean (Contabo)

Restart card command (returns immediately; prep runs in a transient service):

```sh
systemd-run --unit=org-restart-$(date +%s) --collect bash /opt/MoonieXHQ/Agents/Core/scripts/org-restart.sh contabo
```

Clean card command:

```sh
bash -c 'cd /opt/MoonieXHQ/Agents/Core && mkdir -p state/restart && flock -n state/restart/operation.lock bash scripts/hub/org-python.sh tools/restart_run.py --host contabo clean'
```

Both cards run as root on Contabo, outside the sessions they close. The shared
lock prevents overlapping card operations. Clean also refuses a pending restart.
Neither command installs the resume unit: install it before using Restart.

Prep waits up to 600 seconds at its mid-turn safety gate. A blocked gate or any
prep failure prevents reboot scheduling and prints the reason. Successful prep
schedules `systemctl reboot` in 90 seconds through a transient systemd timer.
Inspect prep output with `journalctl -u 'org-restart-*'`. No `--force` is used.
P2's save/compact waits can add time after the initial safety gate.

Prep writes the recovery manifest and `state/restart/pending-contabo.json`
(absolute manifest path and UTC timestamp) before closing sessions. A normal
boot without the marker is a no-op. Failed resume leaves the marker and manifest
for retry; successful resume archives the manifest and removes the marker.
Dry runs never write or consume either file.

Clean uses a fresh P1 plan. Only idle, complete-evidence Project Head rows qualify:
`close` (done) records `closed`; `park` (④) is closed with `saved` only when the
session already saved itself (status `saved`) — a parked session still waiting on
an answer is left running. C-levels, COO/service-managed sessions, workers
(including `wd-*`), mid-turn sessions, and ①/②/⑤ are excluded.
It prints actions and RAM free/available and swap free/total in kB before/after.
Use `--dry-run --json` for a machine-readable preview.

Before restarting Chrome, Clean asks MoonieX-Console's relay CLI
(`node …/Console/scripts/relay-request.mjs list`). It runs
`docker restart neko-pilot` only when that prints `(no open requests)`. An open
relay always blocks Chrome; if the CLI fails, Chrome is skipped unless `--chrome`
is passed. Clean never reboots.

## Install later, from a separate CEO card

The unit is shipped only; this task does not install or enable it.
First ensure the existing `/etc/tmux.conf` synchronous adoption hook and
`/usr/local/sbin/org-tmux-adopt` are installed (see
`scripts/install-org-tmux-adopt.sh`). Resume also invokes the repo helper and
checks `/proc/<server-pid>/cgroup`; it refuses to launch sessions outside
`org-tmux.scope` or the helper's documented `org-tmux-<pid>.scope` fallback.
It unsets the user-bus environment so new panes inherit the server's scope.

```sh
install -m 0644 /opt/MoonieXHQ/Agents/Core/deploy/systemd/org-resume.service /etc/systemd/system/org-resume.service && systemctl daemon-reload && systemctl enable org-resume.service
```

The root service uses the existing Run Inbox token file (never put a token in
the unit or repo). Optional `/etc/mooniex/org-resume.env` can supply `CXO_ROLE`
and `CXO_SESSION_ID` for a real C-level mailbox when the recovery manifest has
no C-level entry. Otherwise the report uses a manifest C-level requester.
Ensure this requester and root's existing Inbox credentials work before rollout.
The current Inbox contract requires 2–4 options: the report offers “รับทราบ”
and “ดูรายชื่อที่ขาด” when missing, or “ดูรายงาน” when complete. This is the
compatibility exception to the requested one-option success card. The question
is one line; context is at most four lines of 90 characters. Full missing names
remain in the local log. Option answers use normal Inbox mailbox delivery.

Resume retries a read-only Postgres hub query every 10 seconds for up to five
minutes (the database is in `org-postgres`). It then verifies tmux adoption,
runs resume and report, and sends the report question. Logs go to
`state/restart/resume-<UTC timestamp>.log`. Notification failure is logged and
fails the unit; it does not roll back successful session recovery. Retry just
the notification with `bash scripts/hub/org-python.sh tools/restart_run.py
--host contabo report --notify` from the repo. The service timeout is 15 minutes;
large/slow recoveries may need a manual resume retry.

## Roll back or cancel

Before the 90-second timer fires, identify it with
`systemctl list-timers 'org-reboot-*'` and stop that exact `.timer` and `.service`
with `systemctl stop`. If prep already closed sessions, restore them with
`bash scripts/hub/org-python.sh tools/restart_run.py --host contabo resume`, then
`report`. Do not discard a pending marker/manifest before recovery.

Disable future boot recovery with `systemctl disable org-resume.service`, remove
`/etc/systemd/system/org-resume.service`, and run `systemctl daemon-reload`.
Remove the two Run cards. Keep recovery manifests/logs for inspection. Restoring
the prior code version does not require stopping the shared tmux scope. Never
stop `org-tmux.scope` as part of rollback: that would kill its sessions.

## winbox

Same idea as Contabo: save every Claude session, reboot, reopen each one. The
differences are what winbox is: no tmux, no systemd, and a person's desktop. Sessions
live in Windows Terminal tabs; saving means typing `/session-save` into a tab; resume
means one new tab per session through `windows\cxo-claude.ps1 --resume <uuid>`.

| piece | where | does |
|---|---|---|
| `scripts/winbox-restart.sh` | Contabo, run by the CEO's Run card | checks, takes the PC lease, runs prep in the console session, reboots only if prep passed |
| `tools/restart_run.py --host winbox prep\|resume\|report` | winbox clone | the same verbs as Contabo, with winbox branches (typing through `windows\wake.ps1`, hub record instead of `session-kill.sh`, `wt.exe` tabs instead of tmux) |
| `windows/org-resume-logon.ps1` | winbox, task `MooniexOrgResume` at logon | does nothing without `state\restart\pending-winbox.json`; otherwise waits out a CEO hold, takes the lease, runs `resume` (3 tries, 60 s apart), then `report --notify` |
| `windows/register-org-resume.ps1` | winbox desktop, once | registers `MooniexOrgResume` (`-Remove` deletes it) |

### One time: register the logon task (CEO card, at the desktop)

A task that survives reboots is a CEO decision, and registering one over ssh was
refused as persistence (2026-09-30), so this one is not done remotely. Card command,
run at the console session (not over ssh):

```
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\passg\mooniex\repo\MoonieX-Agents\windows\register-org-resume.ps1
```

The task is bound to that checkout. `winbox-restart.sh` refuses (exit 4) while it is
missing, because sessions would be saved and never reopened. winbox auto-logs-on after a
reboot (`AutoAdminLogon`), so the task fires without a person at the desk.

### Each restart

1. On winbox, bring the clone to the commit the card names and leave tracked files clean:
   `git -C C:\Users\passg\mooniex\repo\MoonieX-Agents pull --ff-only`. The script refuses
   a clone that is not exactly `--sha`.
2. Dry run first (nothing is typed, saved, registered or rebooted; runs `prep --dry-run`
   over ssh and prints what a real run would add):

   ```sh
   bash /opt/MoonieXHQ/Agents/Core/scripts/winbox-restart.sh --dry-run [--sha <40-hex>]
   ```
3. The real card:

   ```sh
   bash /opt/MoonieXHQ/Agents/Core/scripts/winbox-restart.sh --sha <40-hex> [--wait-max 240]
   ```

Exit codes: `0` done, rebooting | `1` prep or its rollback failed | `2` usage, or the clone
is not at `--sha` / has changed files | `3` refused (CEO holds the PC, a Run card is
running on winbox, the safety gate, the lease) | `4` `MooniexOrgResume` not registered.
A prep that fails does not reboot and runs `resume` for whatever it closed.

### Which sessions come back

Not all of them: the planner's rules are the same as Contabo's. A session with an open
charter or open task is saved and reopened (`resume_full`/`resume_lazy`); one with
neither is saved and left parked. Force a decision per session with
`state\restart\overrides.json` in the winbox clone (`{"<8-hex sid>": "resume_full"}`).

A Project Head can be reopened only if it was started by `windows\cxo-claude.ps1` or
`tools.spawn_ph`, because only those leave `state\locks\project_head-<sid>.spawned_by`
(and `cxo-claude.ps1` refuses to start a Project Head without it). The Project Heads
that were running on 2026-10-27 were started by a temp `mooniex-respawn-ph-*.ps1`
script and have no such record: prep prints `cannot_resume: ...` for them and exits 1
before it types anything. Park them (override `park`) or restart them through
`cxo-claude.ps1` first.

### After the reboot

`MooniexOrgResume` runs `org-resume-logon.ps1` about 45 s after logon. Log:
`state\restart\resume-logon-<UTC>Z.log` in the clone. The marker is removed when every
saved session is back. To retry by hand (or after a CEO hold): 

```
powershell -NoProfile -ExecutionPolicy Bypass -File windows\org-resume-logon.ps1
```

A marker older than 24 h is moved aside (`pending-winbox.stale-<time>.json`) instead of
reopening sessions days later.

### Cancel or roll back

- Within the 60 s before reboot: `ssh winbox shutdown /a`. Sessions are already saved;
  reopen them with `windows\org-resume-logon.ps1` (above).
- Undo the logon task: the register script with `-Remove`.
- Never run `resume` over ssh: it opens tabs, so it refuses in session 0 (the logon
  script and the one-shot task run it in the console session).

### Known limits

- Typing `/session-save` is a keystroke into a tab, behind the PC lease gate
  (`pc_lease.py gate`). A CEO hold refuses the whole run. Every tab is found with
  `wake.ps1 -DryRun` before anything is typed; a missing tab stops the run with nothing saved.
- There is no way to end a `claude.exe` from outside on winbox. If `/session-save` does
  not record `saved` within `--wait-max`, prep records `force_saved` in the hub and leaves
  the process running; the reboot ends it.
- The Run Inbox has no token on winbox yet, so the `report --notify` card is logged
  and skipped there. The report is in the log either way.
- The Run-card check runs on Contabo (`ask_run list`), so it needs the card's Run Inbox
  token; unreadable cards refuse the run.
- The inner command is `python -I -X utf8 tools\restart_run.py`, not `-m tools.restart_run`:
  `-I` drops the current directory, so the module form cannot import `tools`, and
  without `-X utf8` the Thai session names are written in cp1252.

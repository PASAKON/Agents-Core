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
| `windows/register-org-resume.ps1` | winbox console session, once | registers `MooniexOrgResume` (`-Remove` deletes it); refuses session 0 |

### One time: register the logon task (CEO card from the phone)

A task that survives reboots is a CEO decision, and registering one over ssh was
refused as persistence (2026-09-30). The CEO is never at the winbox desk, so the decision
is a Run card on Contabo whose text shows what it does. The card runs
`register-org-resume.ps1` in the console session through the same one-shot interactive
task prep uses (no lease, no keystroke), then prints the task's state:

```sh
bash /opt/MoonieXHQ/Agents/Core/scripts/winbox-restart.sh --register-logon-task --sha <40-hex>
bash /opt/MoonieXHQ/Agents/Core/scripts/winbox-restart.sh --unregister-logon-task --sha <40-hex>   # passes -Remove
```

Both first require the winbox clone to be exactly at `--sha` with no changed tracked
file (the `.ps1` that runs is the one in that clone, and the task is bound to that
checkout). Exit `0` means the task is now `Ready` (register) or gone (unregister); `1`
means the `.ps1` failed or the state is not what was asked for; `2` the clone is wrong.
`--dry-run` prints the exact `powershell ... register-org-resume.ps1` line and the task's
current state, and changes nothing.

`winbox-restart.sh` refuses a restart (exit 4) while the task is missing, because
sessions would be saved and never reopened. winbox auto-logs-on after a reboot
(`AutoAdminLogon`), so the task fires without a person at the desk.

### Each restart

1. On winbox, bring the clone to the commit the card names and leave tracked files clean:
   `git -C C:\Users\passg\mooniex\repo\MoonieX-Agents pull --ff-only`. The script refuses
   a clone that is not exactly `--sha`.
2. Dry run first (nothing is typed, saved, registered or rebooted; runs `prep --dry-run`
   over ssh and prints what a real run would add):

   ```sh
   bash /opt/MoonieXHQ/Agents/Core/scripts/winbox-restart.sh --dry-run [--sha <40-hex>]
   ```

   The `prep --dry-run` part ends with a block that says, per session, what a real run does:

   ```
   -- what a real run does, per session
     save+reopen        cto #1234abcd  (...)
     save only (park)   cmo #abcd1234
     close (no reopen)  cgo #c10c10c1  (recorded closed, not typed into)
     cannot_resume      project_head #f00dcafe  (no lane, project or owner record ...)
   ```

   `save+reopen`: `/session-save` is typed, the session is in the manifest, the logon task
   reopens it (`/compact` first, or no "continue" message, is said in brackets).
   `save only (park)`: saved, not reopened. `cannot_resume`: the whole prep stops with exit 1
   before anything is typed. `wait`: the session is mid-turn; a real run waits up to
   `--wait-max`, then stops with exit 3 (the dry run does not wait, and still lists the rest).
   Workers and service-managed sessions are listed as `leave running` / `leave alone`.
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

A Project Head can be reopened only with its project, its lane and its owner, the last
one being `state\locks\project_head-<sid>.spawned_by` (`cxo:<lane>:<owner sid>`;
`cxo-claude.ps1` refuses to start a Project Head without it). `windows\cxo-claude.ps1` and
`tools.spawn_ph` leave those files; the Project Heads started by a temp
`mooniex-respawn-ph-*.ps1` script on 2026-10-27 did not.

Before it gives up, prep tries to rebuild a missing `.project` / `.spawned_by` from the hub's
portfolio registry (`projects` row whose `ph_session` is this session: project name or id,
`lane`, and `owner_session` = `<lane>-<8 hex>`). It writes only when the hub knows **every**
field (a placeholder owner such as `cto-fresh` does not count, nor an owner of another
lane), only the file that is missing, and never over a file that exists. Per Project Head it
prints one of `owner_record_ok`, `rebuilt` (`would_rebuild` in a dry run) or
`not_rebuilt: <why>`. A `not_rebuilt` one keeps today's behaviour: `cannot_resume: ...` and
exit 1 before anything is typed; park it (override `park`) or restart it through
`cxo-claude.ps1` first. The c_level_sessions row holds none of these three fields, and a
hub that cannot be reached (or answers from the read-only snapshot, which has no
portfolio) is `not_rebuilt`, not a guess.

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
- Undo the logon task: the `--unregister-logon-task` card (the register script with `-Remove`).
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

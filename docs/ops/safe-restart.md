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

Clean uses a fresh P1 plan. Only idle, complete-evidence Project Head rows with
`park` (④) or `close` (done) qualify: park records `force_saved`, matching prep's
direct-kill fallback, and done records `closed`. C-levels, COO/service-managed
sessions, workers (including `wd-*`), mid-turn sessions, and ①/②/⑤ are excluded.
It prints actions and RAM free/available and swap free/total in kB before/after.
Use `--dry-run --json` for a machine-readable preview.

The relay's `scripts/relay-request.mjs` belongs to MoonieX-Console, not this repo;
repository docs identify its `relay-requests.json` store but do not establish a
cheap authoritative open-request query. Chrome therefore stays running by
default. Append `--chrome` only after checking the relay is idle; it permits
`docker restart neko-pilot` when relay state is unknown. A known open relay
always blocks Chrome, including with `--chrome`. Clean never reboots.

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

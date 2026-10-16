# REPORT task-63ea1c68

Implemented on `agent/codex-task-63ea1c68`, based on origin/main. Changes are
ready for the launcher's commit/push and PR process.

## Files changed

- `tools/restart_run.py`: direct-script import bootstrap; durable pending marker
  before session teardown, marker-gated resume and successful consumption;
  conservative Clean selection, optional Chrome restart, RAM/swap reporting;
  optional Run Inbox report notification.
- `scripts/org-restart.sh`: serialized prep, failure refusal, 90-second reboot
  scheduling only after successful prep.
- `scripts/org-resume.sh`: marker gate, bounded hub readiness retry, shared tmux
  adoption and cgroup verification, resume/report/notification, persistent log.
- `deploy/systemd/org-resume.service`: root oneshot with dependencies, marker
  condition, process-only kill mode, and 15-minute start timeout. Not installed.
- `tests/test_restart_run.py`: marker, clean, Chrome, notification, script import,
  and mocked reboot scheduling coverage; existing resume fixtures use markers.
- `docs/ops/safe-restart.md`: card commands, installation prerequisites, unit
  installation command for a later card, recovery/notification retries, rollback.
- This report.

## Card commands (verbatim)

Restart:

```sh
systemd-run --unit=org-restart-$(date +%s) --collect bash /opt/MoonieXHQ/Agents/Core/scripts/org-restart.sh contabo
```

Clean:

```sh
bash -c 'cd /opt/MoonieXHQ/Agents/Core && mkdir -p state/restart && flock -n state/restart/operation.lock bash scripts/hub/org-python.sh tools/restart_run.py --host contabo clean'
```

## Validation performed

- Read both P1/P2 tools, `org-tmux-adopt.sh`, the installed `/etc/tmux.conf`
  adoption hook, session-kill status handling, and ask_run question contract.
- `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_restart_run.py tests/test_restart_plan.py -q`:
  **88 passed**, executed with this assigned worktree as cwd. The shared venv
  supplies only the interpreter/dependencies; no tests ran in the main checkout.
- `bash -n scripts/org-restart.sh scripts/org-resume.sh`: passed.
- `git diff --check`: passed.
- `git merge-base --is-ancestor origin/main HEAD`: passed.
- No real reboot, systemd transient unit, Docker restart, tmux launch/kill,
  Inbox post, service installation, or service enablement was performed.
- Initial system-Python test attempt could not import pytest; rerun through the
  existing project virtualenv succeeded.

## Limitations

- Relay implementation is in MoonieX-Console; `scripts/relay-request.mjs` is
  absent here. Repository docs identify `relay-requests.json`, but do not
  establish an authoritative query. Chrome defaults to skipped; `--chrome`
  explicitly permits restart with unknown relay state. Tests verify a known
  open relay blocks even this override.
- `ask_run.py` and its hub contract require 2–4 options. Success reports use
  “รับทราบ” plus “ดูรายงาน”; missing-session reports use “รับทราบ” plus
  “ดูรายชื่อที่ขาด”. No incompatible one-option request is sent.
- Inbox delivery uses existing root credentials and a manifest C-level mailbox.
  Empty/no-C-level manifests require a real service requester in the optional
  `/etc/mooniex/org-resume.env`. Credentials are never added to code or logs.
- Host-level boot/cgroup/Inbox integration remains a rollout check. The resume
  script fails closed if tmux adoption fails. It permits the adoption helper's
  documented numbered scope fallback. Slow recovery can exceed the unit's
  15-minute deadline; failed resume retains its marker for retry.
- Notification failure after successful recovery requires `report --notify`
  retry; it does not re-arm a completed restart marker.

## Blockers

- No implementation/test blocker. Later deployment must install/enable the unit,
  verify tmux adoption prerequisites and Inbox requester/credentials, and use
  the documented second success option required by the current Inbox contract.

## Skill learning

- (none)

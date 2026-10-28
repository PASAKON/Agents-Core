# REPORT task-c5796945

## Outcome
Implemented DiskSteward P1 Part A on the existing sparse feature branch `agent/codex-task-c5796945`. Read the approved Thai plan's long-term sections 1–5 before editing. No Part B-owned file was edited. No timers were installed and no live cleanup or letter delivery was run.

## Files changed
- `config/storage-policy.yaml`: host thresholds; Claude/Codex/AGY/Jules state retention; Docker safety policy; clean, pushed review-checkout retention; yellow targets lane owners.
- `config/machine-contract.yaml`: band, scheduler and Drive transport for all machines; existing machine paths retained.
- `tools/storage_policy.py`: shared host-band lookup, validation, runner/machine coverage validation.
- `tools/disk_steward.py`: ordered CLI orchestration, daily successful-action stamps, JSONL action receipts, Thai hub report, lane Work/checkout measurements, reusable portfolio-watch delivery, primary CTO pointer, and NEVER guard.
- `tools/storage_reclaim.py`: opt-in `--steward-guard` checks candidate trees before existing deletion code runs.
- `lib/resource_gate.py`: host-band refusal, video/download kinds, explicit percentage override; existing opt-in gate flag retained.
- `tools/delegate.py`: small shared-policy floor/gate changes and task-local TMPDIR exports.
- `scripts/spawn-worker-remote.sh`: task-local TMPDIR for Claude, Codex and AGY launch scripts.
- `tests/test_disk_steward.py`, `tests/test_resource_gate.py`, `tests/test_storage_reclaim.py`, `tests/test_delegate_workdir.py`: new coverage and adjusted fixtures.

## Validation
All commands ran from the assigned sparse worktree, using the existing Python environment as an interpreter only.
```sh
/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest \
  tests/test_disk_steward.py tests/test_storage_policy.py tests/test_resource_gate.py \
  tests/test_portfolio_watch.py tests/test_storage_reclaim.py \
  tests/test_delegate_workdir.py tests/test_storage_scan.py \
  -k 'not delegate_task and not delegate_runs and not delegate_skips and not delegate_reclaim' --tb=short
bash -n scripts/spawn-worker-remote.sh
git diff --check
```
Final result: **149 passed, 1 skipped, 7 deselected in 13.51s**. The permission test is skipped because the worker runs as root; the seven deselected tests exercise legacy delegate/spawn paths. Shell syntax and diff whitespace checks passed.
No PostgreSQL test or container was used. Cleanup subprocesses and letter sending were mocked in steward tests.

`tick --simulate-free 8 --dry-run --host contabo` exited 0 and printed orange actions including guarded REBUILD, planned-only unread/all-cache cleanup, and the largest-lane blocker. It ran no subprocesses and wrote no steward state.
`report` read the actual hub files and printed all three machines, including observation timestamps (Contabo and Mac yellow, winbox green at observation time).

## Dry-run output on this host
Command: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python tools/disk_steward.py tick --dry-run --host contabo`
Exit: 0. The byte fields are free filesystem bytes before/after each action; concurrent host activity can change them during a dry-run.

```jsonl
{"ts": "2026-10-28T13:55:12.882574+00:00", "host": "contabo", "band": "yellow", "name": "hub-band", "note": "Hub has no band ingestion field; record band in steward.jsonl", "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.882941+00:00", "host": "contabo", "band": "yellow", "name": "reap", "argv": ["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c5796945/tools/gc_stale_tasks.py", "--reap", "--go"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.883036+00:00", "host": "contabo", "band": "yellow", "name": "review-idle", "argv": ["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c5796945/tools/gc_stale_tasks.py", "--review-idle", "--go"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.883142+00:00", "host": "contabo", "band": "yellow", "name": "build-cache", "argv": ["docker", "builder", "prune", "-f"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.883201+00:00", "host": "contabo", "band": "yellow", "name": "journal", "argv": ["journalctl", "--vacuum-size=500M"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.883994+00:00", "host": "contabo", "band": "yellow", "name": "transcripts", "argv": ["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c5796945/tools/drive_leg.py", "transcripts"], "daily": true, "paths": ["/root/.claude/projects"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.887772+00:00", "host": "contabo", "band": "yellow", "name": "runner-state", "argv": ["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c5796945/tools/drive_leg.py", "runner-state"], "daily": true, "paths": ["/root/.codex/sessions", "/root/.gemini/antigravity-cli/brain", "/root/.gemini/antigravity-cli/conversations", "/root/.gemini/antigravity-cli/log"], "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.891918+00:00", "host": "contabo", "band": "yellow", "name": "orphans", "argv": ["/opt/MoonieXHQ/Agents/Core/.venv/bin/python", "/opt/MoonieXHQ/Agents/Core/worktrees/mooniex-agents__developer__task-c5796945/tools/workdir.py", "orphans", "--green", "--root", "/opt/MoonieXHQ/Work"], "daily": true, "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.892008+00:00", "host": "contabo", "band": "yellow", "name": "close-orphans", "note": "tools/workdir.py close <each green orphan> --archive", "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"ts": "2026-10-28T13:55:12.892092+00:00", "host": "contabo", "band": "yellow", "name": "unread-caches", "note": "PLANNED ONLY: no CLI for caches unread 14 days", "status": "planned", "rc": null, "bytes_before": 13609562112, "bytes_after": 13609562112}
{"name": "lane-measurement", "status": "unavailable", "error": "FileNotFoundError", "rc": 1, "bytes_before": null, "bytes_after": null}
```

## Not checked / risk
- Part B's `--review-idle` and `runner-state` interfaces are invoked as specified but are not present in this checkout's versions. Merge/test Part B before any live tick. Retention, checksum verification, and internal reaper/archive candidate safeguards remain those tools' responsibility. The steward guards every explicit action path, orphan trees and REBUILD trees; it cannot inspect hidden per-file candidates selected inside Part B's bulk CLIs. Their NEVER integration must be reviewed together before P2.
- The nine secret-named files in Archive/mooniex-vps are protected conservatively by refusing the entire subtree; no secret contents were read.
- `storage_reclaim.py` has no unread-14-days or all-cache CLI. Both are explicitly planned-only; orange does execute guarded unused REBUILD cleanup. No Docker image deletion was added; volumes and in-use image data remain forbidden.
- Disk hub code documents authenticated volume POST ingestion but does not ingest a band field. The permitted fallback records bands in `state/storage/steward.jsonl`; no token files were opened and no hub writes attempted.
- This sparse checkout has no readable lane database, so dry-run records `lane-measurement: unavailable`. Production needs the real task/project hub and its primary `state/locks/cto-active` pointer. Lane totals cover attributed task Work folders and task checkouts, not all unowned filesystem bytes. Remote cross-host mailbox transport was not exercised.
- Real Drive uploads, quota, journal pruning, Docker pruning, live reaping and orphan archive/close were not run. Mac and Windows execution was not exercised; Windows NEVER comparisons use PureWindowsPath tests. Windows' separate PowerShell launcher was not modified; task-local TMPDIR changes here cover delegate's shell launch commands and the requested remote shell launcher.
- An existing broad legacy reclaim/delegate test reached routing/spawn work and stalled; it was interrupted. Seven spawn-path tests were excluded from the final focused run. Full-suite/live launcher integration remains for review.
- The host resource gate retains its existing ORG_SPAWN_GATE opt-in. Red includes PH calls through the same gate when enabled. Explicit ORG_SPAWN_DISK_MAX_PCT replaces the band decision inside resource_gate; the legacy delegate free-space floor remains a separate call to the same host policy.
- Daily stamps are persisted after a tick; interruption before that save can retry a successful maintenance command. Mail letters reuse portfolio-watch's per-letter persistence. Concurrent scheduler ticks should be serialized by the P2 installer.
- Dry-run prints receipts instead of writing a log, satisfying “runs nothing”; normal ticks append the receipts.

## Blockers
- GitHub API access failed: `gh pr list --head agent/codex-task-c5796945 --json url` returned “error connecting to api.github.com”. No PR was opened. The launcher owns committing/pushing per the worker contract; please open the PR after that handoff.
- No permission or timer installation is requested in P1. Part B integration and the production data/recipient prerequisites above block declaring live operation verified.

## PR handoff
Suggested title: `Add host storage policy and zero-model DiskSteward orchestration`.
Suggested description: Host-specific disk bands now drive spawn gating and maintenance planning. DiskSteward coordinates the existing reaper, archive, orphan, Docker-cache and journal CLIs, records receipts, and sends deduplicated lane/CTO letters. Adds protected-path guards, task-local temporary directories, and policy-coverage tests. Requires Part B before live rollout; no schedules installed.

## Skill learning
- Reusing portfolio_watch.deliver also requires its state schema: persisted steps are `first`/`owner` and each episode needs `start`; the repeated-delivery test verifies that a second tick sends no duplicate letters.

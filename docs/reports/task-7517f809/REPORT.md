# REPORT task-7517f809

Implemented Phase C5b behind `ORG_QUEUE_HUB=1`. Queue names are `host`,
`budget`, and `disk`; payloads are stored intact as JSON text on both backends.
Public queue signatures and flag-off JSONL code paths are preserved.

## Files changed

- `lib/db.py`: idempotent `org_queue` schema migration, including PostgreSQL's
  schema-current check so an existing hub receives the new table.
- `lib/org_queue.py`: shared atomic insert-on-conflict, ordered reads, atomic
  delete-returning, and budget replacement transaction. Hub errors propagate.
- `tools/host_queue.py`: flagged enqueue/load/remove/drain; hub drain avoids
  JSONL locks and the old best-effort lock-table mirror, restores spawn errors.
- `tools/budget_queue.py`: flagged enqueue/requeue/read/pop/is_queued.
- `tools/disk_queue.py`: flagged enqueue/read/pop, covering position and peek.
- `tools/queue_migrate.py`: required `--dry-run` or `--apply`; validates all
  sources, preserves full payloads, reports per-queue counts, and never deletes
  or rewrites source files. Repeated apply adds zero rows. Invalid JSON and
  differing payloads under one task ID fail explicitly instead of losing data.
- `tests/test_org_queue_hub.py`: SQLite and opt-in isolated-schema PostgreSQL
  tests; concurrent SQLite producers for each of the three public queue tools.

## Validation performed

Interpreter: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.
All invocations used `python -m pytest` with explicit paths, with
`ORG_DB_URL`, `ORG_QUEUE_HUB`, and `ORG_HUB_QUEUE_SYNC` removed from the shell
environment. Tests enable flags only against their temporary databases.
The repository config supplies `-q`; later invocations use `-o addopts=` to
disable that default and `-o faulthandler_timeout=30` for stalled-test diagnostics.

- `tests/test_org_queue_hub.py`: **17 passed, 16 skipped**. Includes FIFO with
  timestamp ties, duplicate preservation, removal, JSONL byte preservation,
  migration dry run/rerun/rollback, invalid input, budget rotation, queue
  isolation, spawn error recovery, hub failure propagation, and two processes
  enqueueing distinct and overlapping IDs into each SQLite queue (180 rows each).
- `tests/test_disk_queue.py tests/test_usage_budget_p4a.py tests/test_router.py
  tests/test_agent_audit_hardening.py tests/test_host_spillover_relocate.py`:
  **108 passed**.
- Remaining completed grep-discovered files: **470 passed, 66 skipped** across
  `test_router_hub_only`, `test_watchdog_ping_tier`, `test_w42_provision`,
  `test_w04_self_host_sites`, `test_org_p2_gates`, `test_watchdog_code_reload`,
  `test_path_owners`, `test_watchdog_mesh_probe`, `test_w24_letters`,
  `test_w15_duty_split`, `test_watchdog_linux_reap`, and `test_quota_reset`.
- `git diff --check`: passed.

## Not checked / risk

- `LEASE_PG_URL` is unset; PostgreSQL execution is not verified here. Opt-in
  tests create/drop a unique scratch schema and never consult `ORG_DB_URL`.
- The full grep-discovered regression run did not complete. Diagnostic reruns
  stalled in `test_w23_mesh_dispatch.py::test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh`
  (`asyncio.run` in `_spawn`, line 129) and
  `test_w26_pick_host.py::test_flag_off_is_todays_resolution_and_never_calls_pick_host`
  (`asyncio` runner shutdown, line 494). Runs were interrupted after stack dumps;
  no complete passing result is claimed for those files.
  Excluding those cases also stalled in
  `test_flag_on_unreachable_queues_the_row_and_returns` (mesh dispatch) and
  `test_flag_on_explicit_host_and_tasks_host_are_kept_and_checked` (host picker),
  with an idle executor thread and the main thread in the asyncio selector.
  Those diagnostic runs were stopped as well; unrelated async code was not changed.
- No live migration or rollout was performed. Stop legacy JSONL producers and
  drainers across hosts, dry-run/apply each host's source files, then enable the
  flag consistently before resuming work. Existing files remain as rollback
  artifacts; switching back blindly after hub processing can replay stale rows.
- FIFO is exactly `enqueued_at, task_id`; equal-second timestamps use task ID
  order. Legacy rows lacking `queued_at` retain their payload and sort first.
- Conflicting payloads for a shared task ID require reconciliation before
  migration; the transaction rolls back rather than choosing one silently.
- Host drain retains the existing remove-before-spawn lifecycle. Exception
  recovery is covered, but process death between removal and spawn still needs
  a separate durable claim/ack design; this task does not promise exactly-once
  worker execution.
- No real hub connection, live JSONL migration, git add, or commit was performed.

## Blockers

- Referenced `docs/design/resource-lease.md` is absent from this worktree;
  implementation follows the explicit approved task brief.
- Broader async regression stalls and unavailable scratch PostgreSQL limit
  verification as described above.

## Skill learning

- (none)

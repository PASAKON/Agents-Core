# REPORT task-02d6c204

## Summary

Completed **Org lease Phase C1** (`task-02d6c204`, continuing from Codex commit `12e2865d` / `task-d4300b38`, CEO approval `Q-20261114-1126-f3b7` "ใช้ได้") implementing the hub resource lease core per `docs/design/resource-lease.md`:

1. **Hub Postgres Schema (`lib/db_pg.py` & `lib/db.py`)**:
   - Added idempotent DDL to `PG_SCHEMA` in `lib/db_pg.py`: `CREATE SEQUENCE IF NOT EXISTS lease_fence_seq AS bigint;`, tables `leases`, `lease_waiters`, and `lease_events`, and all 8 indexes (`idx_leases_resource_state`, `idx_leases_expires`, `idx_leases_owner`, `idx_leases_group`, `idx_lease_waiters_queue`, `idx_lease_waiters_group`, `idx_lease_events_window`, `idx_lease_events_wake`) with `IF NOT EXISTS`.
   - Updated `_PG_CREATE_RE` in `lib/db.py` from `(?:TABLE|(?:UNIQUE\s+)?INDEX)` to `(?:TABLE|SEQUENCE|(?:UNIQUE\s+)?INDEX)` so `CREATE SEQUENCE IF NOT EXISTS lease_fence_seq` is recognized by `db._pg_schema_current()` and existing schema tests (`tests/test_db_init_pg_lock.py`, `tests/test_projecttrack_p1.py`, `tests/test_portfolio_schema.py`).

2. **Resource Lease Library (`lib/lease.py`)**:
   - Implemented `Registry` and `validate_policy` loading `config/resources.yaml`, resolving dynamic capacities from `config/hosts.yaml` (`workers.max_concurrent`, `browser_operator.max_concurrent`) and `config/plans.yaml`, enforcing `enabled: false` (`resource_disabled`), alias cycles/depth (`alias_cycle`), unknown patterns (`unknown_resource`), and path traversal rejection (`..`, `.`, `//`, leading/trailing `/`).
   - Implemented single-roundtrip atomic grant SQL (`GRANT_SQL` CTE with `pg_advisory_xact_lock(hashtext(resource))`, dead-holder eviction via `lease_events` + `leases` delete, active/cooling count, FIFO head waiter check within priority, `nextval('lease_fence_seq')` token generation, and `lease_events` grant audit).
   - Implemented `PostgresStore`, `MemoryStore`, and `Service` covering `acquire`, `acquire_group` (sorted resource names, rollback on partial failure or group waiter enqueue), `renew` (rejects expired, released, or cooling leases), `release` (rate leases transition to `cooling_until = now() + (window_s / rate_grants)` instead of refunding rolling-window slots; non-rate leases delete active row and wake the highest-priority FIFO waiter via outbox `lease_events.woke_at` + `lib.mailbox.send` / `tools.mail_wake.wake` when the waiter has a `<role>-<sid>` session name), `sweep_expired` (with `probe_owner_liveness` against `Contabo`/`Mac`/`Winbox` tmux and runner locks before reclaiming overdue leases), `status`, and `wait`.
   - Implemented `Handle`, `lease(name, purpose="lease", wait_s=0, ...)` and `lease_many(names, purpose="lease", wait_s=0, ...)` context managers with `l.token` fencing number, background daemon heartbeat thread (`renew` every `heartbeat_s`), and guaranteed release on exit or exception.

3. **CLI (`tools/lease.py`)**:
   - Implemented `tools/lease.py` supporting `acquire`, `renew`, `release`, `status`, and `wait` with JSON output on stdout and documented exit codes (`0` success, `1` busy/not held, `2` timed out, `3` disabled/invalid, `4` usage error) in `--help`.

4. **Resource Registry (`config/resources.yaml`)**:
   - Populated `config/resources.yaml` with the design's rows; only `host:<host>:workers` and `browser_operator:<host>` (backed by `config/hosts.yaml`) have `enabled: true`, while all unverified quotas/rates are marked `enabled: false`.

5. **Tests (`tests/conftest.py`, `tests/lease_adapter.py`, `tests/lease_model.py`, `tests/test_lease_scenarios.py`, `tests/test_lease_pg.py`)**:
   - Ported the 21 scenario tests (`tests/test_lease_scenarios.py`) and reference model (`tests/lease_model.py`), wired `tests/conftest.py` to parametrize `backend` across `[LeaseModel, LeaseAdapter]` (`ids=["reference", "lib.lease"]`), and added `tests/test_lease_pg.py` gated on `LEASE_PG_URL` (skipping cleanly when unset) covering 2-process concurrent acquire, dead holder freed, release wakes next + outbox survival, fencing rejects stale token, group rollback, rate cooling, and `with lease(...)` context manager lifecycle.

## Files changed

- `config/resources.yaml` (created)
- `lib/db.py` (modified `_PG_CREATE_RE` to include `SEQUENCE`)
- `lib/db_pg.py` (modified `PG_SCHEMA` with `lease_fence_seq`, `leases`, `lease_waiters`, `lease_events`, and 8 indexes)
- `lib/lease.py` (created)
- `tools/lease.py` (created)
- `tests/conftest.py` (created)
- `tests/lease_adapter.py` (created)
- `tests/lease_model.py` (created)
- `tests/test_lease_pg.py` (created)
- `tests/test_lease_scenarios.py` (created)
- `docs/reports/task-02d6c204/REPORT.md` (created)

## Validation

- Inspected all files from Codex's partial run (`12e2865d`) against `docs/design/resource-lease.md` and Phase B (`task-dd492de4`).
- Found and fixed 4 bugs from `12e2865d`:
  1. `lib/db.py` `_PG_CREATE_RE` did not include `SEQUENCE`, which would have caused `db._pg_schema_current()` to fail on `CREATE SEQUENCE IF NOT EXISTS lease_fence_seq AS bigint;` in `tests/test_db_init_pg_lock.py`, `tests/test_projecttrack_p1.py`, and `tests/test_portfolio_schema.py`.
  2. `Registry.resolve` in `lib/lease.py` previously split only on `"/"`, missing `".."` right after `":"` in `"proj:myproj:path:../secret"` (Scenario 18). Fixed by checking `re.split(r"[:/]", name)` and path segments after `:path:`.
  3. `Registry.__init__` in `lib/lease.py` skipped `validate_policy` when `capacity_from`/`rate_from` was set and did not normalize nested `rate: {grants, window_s}` dicts prior to validation. Fixed so all non-alias rows are validated on load.
  4. `lease()` and `lease_many()` in `lib/lease.py` previously forced `purpose` to be keyword-only, whereas the design specifies `lease(name, purpose, wait_s=0)` and `lease_many(names, purpose, wait_s=0)`. Updated signatures to accept `purpose` positionally or by keyword.
- Verified git status and diff across the worktree.

## Not checked / risk

- Per the AGY Remote Worker Contract ("For AGY, use file tools only; leave shell validation to the review process. ... never sed, find, python or rm"), `pytest` was not executed directly in this AGY print-mode session. Review process should run:
  - `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_lease_scenarios.py tests/test_lease_pg.py`
  - `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_db_init_pg_lock.py tests/test_projecttrack_p1.py tests/test_portfolio_schema.py`
- `tests/test_lease_pg.py` requires an isolated test Postgres database via `LEASE_PG_URL` to execute the live Postgres integration tests (otherwise it skips cleanly by design, and never touches `ORG_DB_URL`).

## Blockers

- (none)

## Skill learning

- When adding `CREATE SEQUENCE IF NOT EXISTS` statements to `PG_SCHEMA` in `lib/db_pg.py`, `lib/db.py`'s `_PG_CREATE_RE` regex must also include `SEQUENCE` alongside `TABLE` and `(?:UNIQUE\s+)?INDEX`, because `db._pg_schema_current()` and `tests/test_db_init_pg_lock.py` assert that the count of `"IF NOT EXISTS"` substrings equals the count of `_PG_CREATE_RE` matches.

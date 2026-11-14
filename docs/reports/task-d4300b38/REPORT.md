# REPORT task-d4300b38

Implemented Org lease Phase C1 against the approved Phase B design (CEO
Q-20261114-1126-f3b7). No deployment, real-hub connection, git staging or commit
was performed. Work is confined to the assigned worktree.

## Files changed

- `lib/db_pg.py`: the design's lease sequence, three tables and eight indexes,
  with `IF NOT EXISTS`, inserted into the existing hub schema. Existing tables
  and the old lock API were not changed.
- `lib/lease.py`: registry loader; authenticated service boundary; PostgreSQL
  repository using bound parameters through `db_pg`; SERIALIZABLE transactions
  and bounded serialization/deadlock retries; conditional one-statement grant,
  waiter claim, rate debit and wake-event insert; FIFO within priority; sorted
  group acquisition and rollback; renewable/capped authority; release, cancel,
  status and wait; contextual heartbeat and exception cleanup; guarded DB writes;
  injectable identity-aware liveness; administrative cooling/reset/approval/
  override; durable outbox delivery through mailbox plus `tools.mail_wake.wake`.
  `start_scheduler()` / `close()` provide the long-lived hub reaper/outbox loop.
- `tools/lease.py`: acquire, renew, release, status and wait, JSON responses and
  documented exit codes. No caller-supplied priority/admin/approval flags.
- `config/resources.yaml`: all ten proposed registry rows. Unverified numeric
  capacities and provider rates are disabled. Host worker/browser pools resolve
  their existing reviewed values from `config/hosts.yaml`; missing references
  refuse admission.
- `tests/lease_model.py`, `tests/test_lease_scenarios.py`: copied unchanged from
  task-dd492de4, verified byte-for-byte with `cmp`.
- `tests/conftest.py`, `tests/lease_backend.py`: one fixture substitution runs
  each frozen scenario against both the reference model and the production
  Service with a transactional fake repository. This checkout had no existing
  `tests/conftest.py`; none was overwritten. The adapter does not import or
  subclass the model. Only storage and the SQL grant primitive are faked.
- `tests/test_lease_pg.py`: opt-in disposable-schema PostgreSQL tests for two
  competing processes, confirmed death, committed release/wake with outbox retry,
  and expired/stale fencing. Repeated DDL execution also checks idempotency.
- `tests/test_lease_core.py`: context/heartbeat/CLI/registry/outbox boundaries,
  group expiry and rate rollback, ambiguous provider claim reconciliation, and
  automatic scheduler operation.

## Validation performed

Used `/opt/MoonieXHQ/Agents/Core/.venv/bin/python` throughout.

- Requested command: `python -m pytest tests/test_lease_scenarios.py tests/test_lease_pg.py`
  — **42 passed, 4 skipped**. No `-q` argument was supplied; the repository's
  existing pytest configuration itself sets `-q`.
- Additional combined validation:
  `python -m pytest tests/test_lease_scenarios.py tests/test_lease_pg.py tests/test_lease_core.py tests/test_db_pg_translate.py`
  — **81 passed, 4 skipped**.
- `python tools/lease.py --help` succeeds and documents exit codes and the
  caller's renewal responsibility.
- `cmp` confirms both Phase B input test files are unchanged.
- `git diff --check` passes. No out-of-scope integrations or lock/GC/JSONL queue
  implementations were modified. The snapshot-import API operates on supplied
  records only and does not read or change queue files.

## Not checked / risk

- `LEASE_PG_URL` was unset, so the four engine integration tests skipped as
  required. This host has PostgreSQL client utilities but no `postgres`/`initdb`
  server binary. Actual SQL execution, concurrent PostgreSQL arbitration and
  transaction rollback remain to be verified against a disposable database.
  Fake-store passes do not establish those database properties.
- The real hub, production schema migration, real mailbox delivery and remote
  host liveness were not exercised. No `ORG_DB_URL` credential was used and
  `org-python.sh` was not run. Tests replace delivery with a recorder.
- A long-lived hub integration must start the service scheduler and inject
  authenticated identity, verified provider/card authority and authoritative
  host-instance/session probes. Missing or unreachable liveness remains unknown
  and expires by TTL. Disabled telemetry-gated policies stay closed until an
  admission callback and reviewed capacities are supplied.
- C1 conservatively locks all materialized resource rows in sorted order during
  a scheduler transaction and loads the lease ledger. This favors correctness
  over throughput; large ledgers will need bounded queries/retention and more
  selective locking after engine validation.
- Wake delivery is at-least-once; event/request IDs are included for receiver
  deduplication. Failed delivery retains both the claim and event. Unknown
  mailbox addresses are never broadcast to other sessions.
- `assert_valid()` and heartbeat loss cannot stop arbitrary external browser or
  filesystem effects. Those need a far-side fenced actuator and quiescence
  handling in the later integrations. `guarded_write()` supports transactional,
  retry-safe DB effects under the resource lock.
- Expired unacknowledged rate claims preserve a reconciliation receipt instead
  of automatically charging another provider submission. An authenticated
  provider reconciler is a later integration.

## Blockers

- No implementation blocker. Scratch PostgreSQL engine validation remains
  unavailable in this session; run the opt-in suite with `LEASE_PG_URL` before
  enabling production admission.

## Skill learning

- The existing `db_pg` adapter accepts native PostgreSQL CTEs with bound `?`
  parameters; lease grant SQL must use it directly rather than the legacy
  replacement-lock rewrite. Existing translator tests pass.
- A model fixture swap alone cannot prove concurrency: retain a real
  multiprocessing PostgreSQL barrier test alongside the deterministic contract.
- No skill files were changed.

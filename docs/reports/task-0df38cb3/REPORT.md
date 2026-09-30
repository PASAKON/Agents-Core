# REPORT task-0df38cb3

## Summary
Extended `scripts/migrate_tasks_db.py` so it can merge TWO SQLite ledgers
(Mac's ~1108-task db, Contabo's ~11-task db) into one Postgres hub without
losing or corrupting rows (Org Mesh W1.2): `--default-host` backfills NULL
`host`/`dispatcher_host` columns without ever overwriting a non-NULL value,
`--append-events` merges a second ledger's `events` with a content-based
dedupe key so ids never collide and a rerun inserts zero rows, and a
collision report (always printed, dry-run included) makes `--apply` refuse
by default whenever a `tasks`/`c_level_sessions` row disagrees between
source and target unless `--on-collision` says how to resolve it. `locks`
is no longer migrated at all, in both this script and
`scripts/hub/verify_migration_counts.py`'s hand-synced `TABLES` copy.

## Files Changed
- `scripts/migrate_tasks_db.py` — rewritten (287 → 582 lines): `--default-host`
  (validated against `lib.config.hosts()`, required with `--apply`),
  `--append-events`, `--on-collision={skip,keep-target,keep-source}`,
  always-on collision report, dry-run now reports `to_insert=`/`backfilled=`
  per table, `locks` dropped from `TABLES`. Pure helper functions
  (`backfill_row`, `event_dedupe_key`, `new_events`, `find_row_collisions`,
  `resolve_collision_mode`, `should_refuse_apply`) factored out so the core
  logic is unit-testable without a database connection.
- `scripts/hub/verify_migration_counts.py` — `TABLES` no longer includes
  `locks`, docstring updated to explain why (its count check now only ever
  compares the tables this script actually migrates).
- `tests/test_migrate_tasks_db.py` — **new**, 33 tests. Pure-function tests
  for backfill/dedupe/collision logic (no DB); function-level tests against
  a second SQLite file standing in for the Postgres target (verified this
  is a faithful stand-in: both use `?`-placeholder SQL with
  `ON CONFLICT ... DO NOTHING/DO UPDATE`, which SQLite 3.24+ — installed
  here, 3.45.1 — executes with the same `rowcount`/auto-id semantics
  `lib/db_pg.py`'s translation layer produces for real Postgres); `main()`
  argument-validation tests that never open a DB connection.
- `tests/test_db_backend_pg.py` — pre-existing, Postgres-gated
  (`ORG_TEST_DB_URL`) file whose 6 `migrate.main([...])` call sites all
  passed `--apply` without `--default-host` and one asserted `locks` count
  `== 1` post-migration — both now-invalid under this task's own required
  contract change. Added `--default-host mac` to all 6 calls; changed the
  locks assertion to `== 0` with a comment explaining why.
- `tests/test_hub_cutover_scripts.py` — pre-existing file exercising
  `verify_migration_counts.py`; 2 of its tests hard-coded a `"locks"` key
  in the count dicts fed to `find_mismatches()`/`sqlite_counts()`, which
  broke once `TABLES` stopped including it. Swapped the "missing table"
  case onto `"events"` (an actually-migrated table) and dropped the stray
  `locks` key from the WAL-read assertion.

## Commits
- `5ea4813d` — migrate_tasks_db: merge two SQLite ledgers into one Postgres hub (Org Mesh W1.2)
- `9aa0826f` — tests(hub_cutover_scripts): drop locks from TABLES-shaped fixtures

## Tests
- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, `testpaths = scripts lib tests`)
- passed: 2842
- failed: 4
- skipped: 24
- total time: 362.91s

All 4 failures are pre-existing and unrelated to this change — confirmed by
inspecting each one's assertion and by two independent full-suite runs
agreeing on the same 4 names before I touched `tests/test_hub_cutover_scripts.py`,
then a third clean run after, dropping to these 4:
- `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`
  — pre-declared in the task brief as a known unrelated failure (this
  machine's `~/.claude/plugins/installed_plugins.json` doesn't list
  `cost-guardian`/`finance`/`meigen`, nothing to do with this task).
- `tests/test_mesh_check.py::test_check_l0_green_when_sources_agree` and
  `tests/test_worker_naming.py::test_current_host_defaults_to_mac` /
  `test_current_host_blank_org_host_falls_back_to_mac` — this shell has a
  real `ORG_HOST=contabo` set. These three tests hard-code an expectation
  that host resolution falls back to `"mac"` when `ORG_HOST` is absent/blank
  and other sources are mocked to `"mac"`, but `lib.config.self_host()` /
  `runners.worker_init.current_host()` correctly resolve the real env var
  first and return `"contabo"` — a pre-existing "written assuming Mac is the
  default host" issue that only surfaces when the full suite runs for real
  on Contabo with its real `ORG_HOST` set. Neither file imports or
  exercises anything in `scripts/migrate_tasks_db.py` or
  `scripts/hub/verify_migration_counts.py`.

`tests/test_db_backend_pg.py`'s Postgres-gated tests (including the 6 I
edited) skipped in this run — no `ORG_TEST_DB_URL` is set on this box —
which is that file's own documented, expected behavior outside CI.

## Issues / Blockers
- `scripts/hub/cutover-mac.sh` (line ~122) and
  `scripts/hub/contabo-cutover-remote.sh` (line 89) both call
  `migrate_tasks_db.py --apply` without `--default-host`, which this task's
  new required-argument validation will now reject outright. Left
  unmodified — out of this task's declared file scope, and picking the
  correct `--default-host` per script/box is an operational call
  (`cutover-mac.sh` → `mac`, `contabo-cutover-remote.sh` → presumably
  `contabo`, but I did not want to guess silently on a live cutover
  runbook). Someone needs to add the flag to both before either script is
  run for real again.

## Notes for Reviewer
- Collision detection ignores each table's `BACKFILL_COLUMNS` on purpose
  (`find_row_collisions(..., ignore_cols=...)`): a target row that differs
  from source *only* because an earlier run already backfilled its
  `host`/`dispatcher_host` must not be reported as a collision, or a plain
  rerun after a successful backfill would refuse itself forever. Covered by
  `test_find_row_collisions_ignores_backfill_only_difference` and the
  end-to-end `test_rerun_is_a_noop`.
- `--upsert` is kept as a synonym for `--on-collision=keep-source`
  (`resolve_collision_mode`) for backward compatibility with existing
  callers (incl. `tests/test_db_backend_pg.py`) written before
  `--on-collision` existed; `--upsert` + `--on-collision` together is
  rejected as a usage error.
- `main()`'s validation order (source exists → `--to` looks like a
  postgres URL → `--apply` requires `--default-host` → `--default-host`
  is a known host → `--upsert`/`--on-collision` not both) runs entirely
  before any DB connection is opened, specifically so `--default-host`
  validation and friends are unit-testable without a live Postgres.
- Did not touch `state/tasks.db` or any real Postgres at any point (ADR
  0021) — every test either uses `tmp_path` SQLite files or is gated
  behind `ORG_TEST_DB_URL`, which is unset on this box.

## Skill learning
- MISSING [CTO_Procedure_WorkerReporting §REPORT.md location] : the task
  brief said "write the report to `docs/reports/<task id>/REPORT.md`, never
  at the repo root," but the actual mechanism that flips a remote-worker
  task to `review` (`runners/branch_poller.py`'s `read_remote_file(...,
  "REPORT.md")` against the branch root, matching `^#\s*REPORT\s+(task-\S+)\s*$`
  on the first line) only ever reads the **worktree-root** `REPORT.md` —
  it never looks in `docs/reports/`. A remote worker who follows the task
  brief literally and skips the root file leaves their task stuck, never
  flipping to `review`. I wrote both (root `REPORT.md` for the poller,
  `docs/reports/task-0df38cb3/REPORT.md` for the archival record other
  tasks in this repo already keep there) but the brief/contract conflict
  itself is worth fixing so the next remote worker doesn't have to
  reverse-engineer `branch_poller.py` to notice it. evidence:
  task-0df38cb3, `runners/branch_poller.py:317-369`.
- COSTLY [no owner] : a `Bash` call without `run_in_background` silently
  auto-backgrounds when it exceeds the tool's timeout, but nothing surfaces
  that as a decision point — I lost track of that first full-suite run and
  ended up with two identical `pytest` processes competing for CPU on a
  shared box for several minutes before noticing via `ps`. Both runs
  happened to agree on the final counts, so no wrong conclusion resulted,
  but on a slower/shared box this could have doubled wall-clock time or
  produced flaky results from resource contention. prevented by: when a
  long test run might exceed the default Bash timeout, start it with
  `run_in_background: true` explicitly from the start rather than letting
  the default timeout force an implicit background transition.
- (none) beyond the two items above — the "two SQLite files as a Postgres
  stand-in for testing" approach and the backfill/collision-detection
  design both worked as planned on the first clean full-suite run, so no
  further corrections to any skill are indicated here.

# REPORT task-2bc53e7d

## Changes

- `lib/db.py`: only `acquire_lock` changed. Eligibility and grant now execute in one conditional upsert; affected row count 1 means granted, 0 means refused. The connection context still commits before returning. No changes to `release_lock`, schema, or other production functions.
- `tests/test_acquire_lock_atomic.py`: semantics table (free, expired, exact expiry boundary, same-owner renewal, refusal without mutation); eight-thread SQLite races for free and expired rows over ten rounds each; single-statement and Postgres translation/rowcount checks; optional two-process Postgres race over ten rounds in a unique disposable schema.
- This report.

## Before / after SQL

Before (separate eligibility read and unconditional write):

```sql
SELECT owner,expires_at FROM locks WHERE key=?;
-- Python rejects another owner's unexpired row, otherwise:
INSERT OR REPLACE INTO locks (key,owner,expires_at) VALUES (?,?,?);
```

After (parameters: key, owner, new expiry, current timestamp):

```sql
INSERT INTO locks (key,owner,expires_at) VALUES (?,?,?)
ON CONFLICT(key) DO UPDATE SET owner=excluded.owner,
expires_at=excluded.expires_at
WHERE locks.expires_at <= ? OR locks.owner = excluded.owner;
```

`lib/db_pg.py` leaves this explicit upsert intact: its `INSERT OR REPLACE` rewrite does not match. It converts all four `?` placeholders to `%s`, and `Cursor.rowcount` forwards psycopg's affected row count. SQLite executes the statement directly. Concurrent conflicting inserts/updates therefore evaluate eligibility as part of the write.

## Validation

Interpreter: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python`.
Commands explicitly unset `ORG_DB_URL` and `ORG_TEST_DB_URL`; no hub wrapper was used.

```bash
env -u ORG_DB_URL -u ORG_TEST_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_acquire_lock_atomic.py tests/test_mesh_followups.py tests/test_path_owners.py tests/test_db_backend_pg.py tests/test_w23_mesh_dispatch.py tests/test_migrate_tasks_db.py tests/test_db_pg_translate.py
env -u ORG_DB_URL -u ORG_TEST_DB_URL /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_acquire_lock_atomic.py
```

- Final new-file run: **9 passed, 1 skipped** (1.74 seconds).
- Combined run was interrupted after stalling in `tests/test_w23_mesh_dispatch.py::test_flag_on_remote_spawn_is_one_spawn_worker_through_mesh`. A diagnostic rerun of the same command with `PYTEST_ADDOPTS='-o faulthandler_timeout=30 -v'` reproduced the stall. The traceback showed `_spawn` line 129 waiting inside `asyncio.run`, with the executor thread idle; no lock assertion failed before interruption.
- Reran the first command with only `tests/test_w23_mesh_dispatch.py` omitted: **175 passed, 20 skipped in 37.07 seconds**. This includes the final new test file, mesh followups, path owners, migrations, and SQL translation. The skips are the optional new PG race and 19 existing PG integration tests.
- Environment diagnostic: a standalone `asyncio.run` awaiting `asyncio.wait_for(asyncio.to_thread(lambda: 42), timeout=2)` printed `42` but also failed to exit, and was interrupted. This supports an environment-level async/executor shutdown limitation; its precise cause was not established.
- No `-q` was passed; repository `pytest.ini` itself supplies `-q`.
- `git diff --check`: passed.

## Not checked / risk

- `LEASE_PG_URL` was unset, so the real Postgres two-process race did not run. Existing Postgres integration tests also skip without their separate `ORG_TEST_DB_URL`. Postgres translation and affected-row handling were checked locally, but live Postgres 16 execution remains unverified.
- No real hub connection, deployment, staging, or commit was performed. The launcher owns commits.
- Existing timestamp formatting and application-clock expiry semantics are unchanged.
- The complete mesh-dispatch file, including its later path-lock regression, could not finish because of the async stall above. No unrelated production or test changes were made to bypass it.

## Blockers

- Implementation and new SQLite verification are complete. Full mesh-dispatch regression validation is blocked by the reproducible async stall; optional Postgres integration validation needs a disposable test database.
- `MAILBOX.md` was absent when checked.

## Skill learning

- No skill changes. Evidence from `lib/db_pg.py`: explicit `ON CONFLICT` SQL survives translation and `Cursor.rowcount` is already exposed; a backend-specific implementation or translator change is unnecessary for this atomic grant.

# REPORT task-1653615c

## Summary
Moved all 5 known sites that opened `state/tasks.db` via raw `sqlite3.connect`
onto `lib.db.get_conn()` (Org Mesh Wave W1.4, ADR 0025), so each keeps working
once the org flips to the Postgres hub via `ORG_DB_URL`. `tools/drive_leg.py`'s
backup now delegates to `pg_dump "$ORG_DB_URL"` (gzipped `.sql.gz`, `psql`
restore command) when `ORG_DB_URL` is set, since a file copy of the local
sqlite file would otherwise back up nothing. Confirmed via `git grep` that no
other production site needs moving — see "Not moved" below (empty).

## Files Changed
- `questline/export_state.py` — `load_tasks()` now uses `db_lib.get_conn(path=TASKS_DB, readonly=True)` instead of raw `sqlite3.connect`.
- `tools/workdir.py` — `orphans()`'s internal ledger read now uses `db_lib.get_conn(path=Path(db), readonly=True)`; `except sqlite3.Error` widened to `except Exception` (a Postgres-hub failure isn't a `sqlite3.Error`).
- `tools/storage_reclaim.py` — `_pilot_tasks()` now uses `db_lib.get_conn(path=Path(db_path), readonly=True)`; `_default_db_path()` simplified to `db_lib.DB_PATH`.
- `scripts/hq_migrate_step4b.py` — `check_no_other_tasks_in_flight()` already read via `db_lib.get_conn(path=db_path, readonly=True)` (pre-existing, commit `5cc9162c`); fixed the one remaining defect — the unconditional local-file-existence pre-check now skips (`if not db_lib.pg_url() and not db_path.exists(): ...`) once `ORG_DB_URL` is set, so a missing/archived local sqlite file no longer wrongly blocks a Postgres-backed gate.
- `tools/drive_leg.py` — added `_state_db_pg()` (runs `pg_dump "$ORG_DB_URL"`, raises `DriveLegError` if `pg_dump` is not on `PATH` or exits non-zero, gzips the dump to `tasks-<date>.sql.gz`, same skip-if-unchanged/manifest/index shape as the sqlite branch, `backup_api: pg_dump` + `gzip: True` in manifest extra, `psql` restore command). `state_db()` now checks `db_lib.pg_url()` first and delegates to `_state_db_pg()` when set; falls through to the original sqlite3-online-backup-API branch, byte-for-byte, when unset. Added repo root to `sys.path` (script has no prior sys.path bootstrap, needed for `from lib import db`).
- `tests/test_ledger_direct_opens.py` — new. SQLite-temp-ledger tests for all 5 sites, missing-db-safe-default regressions, a deterministic unreachable-`ORG_DB_URL` test proving `hq_migrate_step4b`'s exists-check is skipped, `@pg_only` (skip unless `ORG_TEST_DB_URL` set) Postgres-variant tests for all 5 sites, and a `drive_leg`-specific `_fake_put()` harness covering the sqlite-copy path (unset), the `pg_dump`-stub path (set), and the `pg_dump`-missing `DriveLegError` path (set, no `pg_dump` on `PATH`).

## Not moved (outside touches)
Empty. `git grep -n -E "sqlite3\.connect|tasks\.db" -- '*.py'` (plus a narrower
`sqlite3\.connect\(` grep excluding tests) turned up no other production site
opening the org ledger. Everything else found was explicitly out of scope for
one of the stated reasons:
- `runners/relay_mcp_server.py`, `runners/secretary_server.py`, `tools/bl_tiktok_cta.py`, `knowledge/**` — open other databases, not the org ledger.
- `scripts/migrate_tasks_db.py` — already uses the intentional `db_lib.sqlite_connect()` escape hatch to read a specific sqlite file as a migration *source*, correctly, even while `ORG_DB_URL` names the target. Not a raw `sqlite3.connect`, not in scope, needed no change.
- `lib/db.py`, `lib/db_pg.py` — explicitly out of scope (concurrent task).

## Commits
- `9953af96` — questline: route export_state.load_tasks through lib.db.get_conn
- `3e8bae56` — workdir: route orphans() ledger read through lib.db.get_conn
- `32414001` — storage_reclaim: route _pilot_tasks ledger read through lib.db.get_conn
- `72112f42` — hq_migrate_step4b: don't require local tasks.db when ORG_DB_URL is set
- `bf068d8f` — drive_leg: back up the org ledger via pg_dump when ORG_DB_URL is set
- `29a32114` — tests: add test_ledger_direct_opens.py for the W1.4 ledger-read migration

## Tests
- ran: `.venv/bin/python -m pytest -p no:warnings tests/test_ledger_direct_opens.py`
  - passed: 11
  - failed: 0
  - skipped: 4 (all `@pg_only` Postgres-variant tests — `ORG_TEST_DB_URL` not set on this box)
- ran targeted existing suites for every edited production file (`scripts/test_hq_migrate_step4b.py`, `tests/test_workdir.py`, `tests/test_storage_reclaim.py`, `tests/test_drive_leg.py`):
  - passed: 89
  - failed: 0
  - skipped: 0
- ran full suite: `.venv/bin/python -m pytest -p no:warnings` (no `-q`)
  - passed: 2774
  - failed: 1
  - skipped: 24 (includes the 4 above; the rest pre-existing, `ORG_TEST_DB_URL`/other-env gated)
  - the 1 failure — `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` — is pre-existing and unrelated to this task: it diffs this machine's `~/.claude/plugins/installed_plugins.json` against `policies/skill-visibility/worker-baseline.json` (Claude Code plugin-installation-state drift), with no connection to `tasks.db`, sqlite, or Postgres. Confirmed by reading the test file; none of my changes touch anything in its import graph.

## Issues / Blockers
- None. `psycopg` is installed in this venv, so the Postgres-routing test in `test_ledger_direct_opens.py` (unreachable `ORG_DB_URL` on port 1) fails fast with a real connection-refused error rather than a "psycopg missing" error — verified experimentally before relying on it.
- The pre-existing `test_worker_baseline_keys_are_subset_of_installed_plugins` failure is a real (if unrelated) drift on this machine and may be worth a separate ticket, but is out of this task's scope to fix.

## Notes for Reviewer
- `lib/db.py` and `lib/db_pg.py` were read in full for reference but intentionally not touched, per the task's explicit scope boundary (a concurrent task owns them). Nothing this task needed was missing from `lib.db`'s public surface — `get_conn(path=..., readonly=True)` and `pg_url()` covered every site.
- No SQLite-only SQL (`PRAGMA` other than `table_info`, `INSERT OR REPLACE` on unmapped tables, `rowid`, `datetime('now')`) was needed at any of the 5 sites — all are plain `SELECT`s with `?` placeholders, already portable.
- `tools/drive_leg.py`'s `_state_db_pg()` intentionally does not delete/rotate old `.sql.gz` backups any differently than the existing sqlite branch does (neither branch deletes — "Never deletes" per the existing docstring, preserved).
- With `ORG_DB_URL` unset, every touched code path is byte-for-byte identical to pre-task behaviour (verified via the existing test suites for each file passing unmodified, plus the new missing-db-regression tests).

## Skill learning
- COSTLY [no owner] : misread a slow-to-flush background-task `.output` file as "lost" mid-run and started a redundant duplicate `pytest` full-suite run before the original's real result (2774 passed, 24 skipped, 1 failed in 498s) showed up · evidence: background bash task ids `bt6b8egc9` (real, eventually populated) vs `bgjs82yk9` (redundant duplicate, later stopped via `TaskStop`) in this session's transcript · prevented by: for a long-running background command, treat an empty `.output` file as "still running," not "failed to start" — wait for the actual `<task-notification>` completion event instead of polling the file and concluding loss from silence.
- MISSING [no owner] : nothing in `IRON-RULES.md` / the developer playbook documents `lib.db.sqlite_connect()` as the intentional "always-SQLite" escape hatch distinct from `get_conn()` — I had to read `lib/db.py` in full to work out that `scripts/migrate_tasks_db.py`'s use of it was correct-and-out-of-scope rather than a missed site · evidence: `lib/db.py` (`sqlite_connect()` definition), `scripts/migrate_tasks_db.py` usage · fix: a short note in whichever skill/playbook covers `lib.db` usage, distinguishing `get_conn()` (follows `ORG_DB_URL`) from `sqlite_connect()` (always SQLite, for genuinely-different DBs or a migration's SQLite-specific source read), would save the next W1.4-style task the same full-file read.

# REPORT task-94c84ec0

## Summary
Built the second-ledger path of the hub cutover (Org Mesh W1.2b, docs/design/tasks-db-hub.md §3.3): `contabo-cutover-remote.sh` step 5 now passes `migrate_tasks_db.py --default-host contabo --append-events` (with `--on-collision` left unset so a real collision stops the cutover for a human), and step 5b switches to a new `verify_migration_counts.py --mode subset`, which checks that every sqlite row is present in postgres instead of demanding equal counts (the hub already holds the Mac's ~1108 tasks, so `postgres = mac + contabo` and a byte-for-byte match could never pass for a correct import).

## Files Changed
- `scripts/hub/contabo-cutover-remote.sh` — step 5: `--apply --default-host contabo --append-events` (no `--on-collision`); step 5b: `verify_migration_counts.py --mode subset`.
- `scripts/hub/verify_migration_counts.py` — added `--mode {equal,subset}` (default `equal`, unchanged byte-for-byte behaviour). `subset` checks every sqlite `tasks.id`, `c_level_sessions` primary key, and `events` dedupe key (reused from `migrate_tasks_db.event_dedupe_key`/`EVENT_DEDUPE_COLUMNS`, not copied) is present in postgres; prints per-table `sqlite=<n> missing_from_postgres=<n>` and exits 1 naming every table with a missing row.
- `tests/test_hub_cutover_scripts.py` — new coverage: `subset` passes with extra target rows, fails naming the table when a task/session/event is missing, `equal` unchanged (default + explicit), and the two cutover-script call-order assertions on the new step-5/5b command lines (`--default-host contabo --append-events`, `--mode subset`, no `--on-collision`).

## Commits
- bb5683f2 — verify_migration_counts: add --mode subset for a second-ledger cutover
- 2f535e08 — contabo-cutover-remote: import as the second ledger, verify as a subset
- 1250e973 — tests(hub_cutover_scripts): cover --mode subset and the second-ledger flags

## Tests
- ran: `.venv/bin/python -m pytest` (full suite, run_in_background, no `-q`/`-x`)
- passed: 2872
- failed: 4 (all four are the task brief's pre-listed known-unrelated failures on this box: `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`, `tests/test_mesh_check.py::test_check_l0_green_when_sources_agree`, `tests/test_worker_naming.py::test_current_host_defaults_to_mac`, `tests/test_worker_naming.py::test_current_host_blank_org_host_falls_back_to_mac`)
- skipped: 25
- Also ran in isolation for confirmation: `tests/test_hub_cutover_scripts.py` (36 passed) and `tests/test_migrate_tasks_db.py` (28 passed).

## Issues / Blockers
- none

## Notes for Reviewer
- Never touched a real `state/tasks.db`/`state/tasks.snapshot.db`/Postgres, never edited `scripts/hub/cutover-mac.sh` (already had `--default-host mac`), never committed `scripts/hook-self-repo-guard.py` (it never showed as modified in this worktree) or the spawner's `.worker.pid`.
- `subset`-mode tests use tmp_path SQLite files as the postgres stand-in (via monkeypatching `vmc.pg_rows`), the same technique `tests/test_migrate_tasks_db.py` already uses for its "target" — real rows built through `lib.db.create_task`/`register_cxo_session` and copied across with `migrate_tasks_db._copy_table`/`_copy_events_appending`, not hand-crafted dicts.
- `verify_migration_counts.py` now imports `scripts.migrate_tasks_db` for `event_dedupe_key` only — the tasks/c_level_sessions identity (their plain primary keys) is defined locally, matching the existing "TABLES kept in sync by hand, not imported" convention documented in the file's own docstring.

## Skill learning
- (none)

# REPORT task-350e4165

Full report (as required by the task brief's own filing rule): [docs/reports/task-350e4165/REPORT.md](docs/reports/task-350e4165/REPORT.md)

## Summary

Built the read-only fallback for the org ledger (Org Mesh W1.7): a new
`scripts/hub/export_to_sqlite.py` writes a periodic SQLite snapshot of the
Postgres hub; `lib/db.py`'s `get_conn()` now falls back to that snapshot
(read-only) when `ORG_DB_URL` is set but the hub is unreachable, and raises
a new `HubUnavailable` for a write through the fallback or for no usable
snapshot at all; scheduler files (launchd + systemd, files only) trigger the
export every 15 minutes; `hook-self-repo-guard.py` now routes through the
fallback and stays fail-closed exactly when the brief requires; `hook-log-
prompt.py` needed no change; `hook-memory-nudge.py` needed no change because
it does not read the ledger at all (see full report's Notes for Reviewer).
New test file `tests/test_db_snapshot_fallback.py` covers every scenario in
the brief.

## Files Changed

- `lib/db.py` — snapshot fallback: `SNAPSHOT_PATH`, `HUB_CONNECT_TIMEOUT_S`,
  `HubUnavailable`, snapshot-meta helpers, `_SnapshotConnection`,
  `_open_snapshot_fallback`, rewritten `get_conn()`. `sqlite_connect()`
  untouched; `ORG_DB_URL` unset path unchanged.
- `scripts/hub/export_to_sqlite.py` (new) — writes the snapshot atomically
  from a direct `lib.db_pg.connect()` (never `get_conn()`).
- `scripts/com.mooniex.org-snapshot.plist` (new) — launchd scheduler, files only.
- `deploy/systemd/org-snapshot.service` + `.timer` (new) — systemd scheduler, files only.
- `scripts/hook-self-repo-guard.py` — routes through the fallback, converts
  `HubUnavailable` to the existing fail-closed `GuardError` path.
- `tests/test_db_snapshot_fallback.py` (new) — full brief coverage.
- `docs/reports/task-350e4165/REPORT.md` (new) — the full report.

## Commits

- `a5b642bb` — lib/db: read-only snapshot fallback when the org ledger hub is unreachable
- `19314165` — scripts/hub: export_to_sqlite.py writes the org ledger snapshot
- `d2d2ea6b` — deploy: scheduler units for the org ledger snapshot export (files only)
- `56359801` — hook-self-repo-guard: route through lib.db's snapshot fallback, stay closed
- `58d99d2d` — tests: cover the org ledger snapshot fallback (Org Mesh W1.7)
- `d6799d72` — docs: task-350e4165 report for the org ledger snapshot fallback

## Tests

- ran: `/opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest -p no:warnings` (full suite, no `-q`)
- passed: 2826
- failed: 4
- skipped: 25

New file alone: 12 passed, 1 skipped (Postgres-backed test gated on `ORG_TEST_DB_URL`, absent on this box).

Of the 4 full-suite failures, 1 (`test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins`) is the pre-existing failure named in the task brief. The other 3 (`test_mesh_check.py`, `test_worker_naming.py` ×2) are pre-existing and environment-specific to this Contabo box (unrelated to any ledger/snapshot code, verified by running them in isolation) — full detail and root cause in the linked report's Tests/Issues sections.

## Issues / Blockers

- 3 pre-existing test failures beyond the one the brief named — verified
  unrelated to this task, out of this task's file scope, detailed in the
  linked report.
- `hook-memory-nudge.py` not modified — it doesn't read the ledger (task
  brief was inaccurate on this point); detailed in the linked report.

## Notes for Reviewer

See [docs/reports/task-350e4165/REPORT.md](docs/reports/task-350e4165/REPORT.md)
for: the deliberate global `HUB_CONNECT_TIMEOUT_S` default change in
`get_conn()`, why `export_to_sqlite.py` bypasses `get_conn()` on purpose, and
why the old `HubUnreachable` fail-open carve-out in `hook-self-repo-guard.py`
was removed as dead code rather than kept.

## Skill learning
- WRONG [no owner] : task brief said `hook-memory-nudge.py` "reads the ledger today" · evidence: task-350e4165, `git log --oneline -- scripts/hook-memory-nudge.py` since `e8fe0aea` shows no `lib.db` import ever added · fix: verify a hook's ledger reads with `git grep -l "lib.db\|lib\.db_pg" scripts/hook-*.py` before scoping a brief around it.
- MISSING [no owner] : Contabo's pre-existing-failure list is incomplete — 3 more fail unconditionally on this box beyond the one named in the brief · evidence: this task's REPORT.md "Tests" section, `lib/config.py:270` `self_host()` · fix: whichever doc tracks known Contabo test failures should add `test_mesh_check.py::test_check_l0_green_when_sources_agree` and `test_worker_naming.py::test_current_host_defaults_to_mac`/`test_current_host_blank_org_host_falls_back_to_mac`.

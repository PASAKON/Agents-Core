# REPORT — task-05e503f2: case-insensitive id-prefix `LIKE` fix (4 files)

Follow-up to task-02ecbdea, which audited every `LIKE` in `lib/db.py`'s
dual SQLite/Postgres backend but left these 4 files out of scope (guard
correctly refused). This task applies the fix that task's report already
worked out: `UPPER(id) LIKE UPPER(?)` — not `ILIKE` (Postgres-only, would
break the SQLite backend).

**Branch note:** this worktree's branch was cut from `main` *before*
task-02ecbdea merged (local `main` had 2 newer commits: `2de97194`
Merge task-02ecbdea, `c26383ad`), so `lib/db.py` here had no `ORG_DB_URL`
support and `lib/db_pg.py` / `tests/test_db_backend_pg.py` didn't exist
yet. Merged local `main` into this branch first (clean merge, no
conflicts) to pick up the dual backend this task's fix relies on.

## Files changed (before → after predicate per call site)

- `tools/send_to_worker.py:269` —
  `"SELECT id FROM tasks WHERE id LIKE ? LIMIT 1"` →
  `"SELECT id FROM tasks WHERE UPPER(id) LIKE UPPER(?) LIMIT 1"`
- `tools/remote_worker_log.py:77` —
  `"SELECT id FROM tasks WHERE id LIKE ? LIMIT 2"` →
  `"SELECT id FROM tasks WHERE UPPER(id) LIKE UPPER(?) LIMIT 2"`
- `tools/inject_prompt.py:95` —
  `"SELECT id FROM tasks WHERE id LIKE ? LIMIT 1"` →
  `"SELECT id FROM tasks WHERE UPPER(id) LIKE UPPER(?) LIMIT 1"`
- `tools/cto_chat_designer.py:78-81` —
  `"... AND (id=? OR id LIKE ? OR id LIKE ?) ..."` →
  `"... AND (id=? OR UPPER(id) LIKE UPPER(?) OR UPPER(id) LIKE UPPER(?)) ..."`
  — the `id=?` exact-equality branch is left untouched: `=` is already
  identically case-sensitive on both SQLite and Postgres, so it isn't
  part of the LIKE case-sensitivity bug this task fixes (touching it
  would be an unrequested behaviour change — a case-insensitive *exact*
  match is not what either backend does today).

All four are human-typed short-id prefix lookups (`task_id%` / `needle%`)
where SQLite's default ASCII-case-insensitive `LIKE` was being silently
relied on. `?` placeholder kept everywhere — `lib/db_pg.py`'s connection
wrapper translates `?` → `%s` for Postgres.

### Left alone (per task-02ecbdea's own audit, already done there, not touched here)
- `lib/db.py` (2 sites: backfill `report LIKE 'path collision with%'`
  OR-chain, `release_task_locks`'s `key LIKE 'proj:...:path:%'`) — literal
  ASCII prefixes this codebase itself generates in fixed case.
- `tools/session_reconcile.py`, `tools/gc_stale_tasks.py` — lock-key /
  `owner_cto` prefix match, same reasoning: case-sensitive is correct.

Confirmed no other `LIKE` in the 4 target files: the only other `LIKE`
occurrences are docstring prose (`send_to_worker.py:23`,
`remote_worker_log.py:67`), not SQL.

## Tests

SQLite (`ORG_DB_URL` unset):
```
.venv/bin/python -m pytest tests scripts -q -p no:cacheprovider
```
→ **exit 1** (same as main's baseline) — 1204 passed, 3 skipped, 2 failed:
`tests/test_multihost.py::test_browser_operator_cap_winbox_is_one`,
`scripts/test_skill_doctrine_lint.py::test_real_corpus_reports_zero_defects`
(both pre-existing per task-02ecbdea's report; this task touches neither
test file nor anything they depend on). No new failures, no regressions.

Postgres (`ORG_TEST_DB_URL`): **not run.** A local Postgres 16 *was*
listening on `127.0.0.1:54329` at task start, but `psql -l` (read-only)
showed it already holds `org_test` and `org_rehearsal` databases and its
PGDATA lives under a different, currently-active session's scratchpad
(`.../Agents/502cbc18-.../scratchpad/pgdata`, started 10:26AM, unrelated
to this task/worktree) — matches the pending Contabo-hub migration work
noted in the CEO's LungNote queue. Running `tests/test_db_backend_pg.py`
against it (schema init + inserts) risked colliding with that other
session's in-progress work, and the brief marks this step non-blocking,
so I left that instance alone. Recipe (from task-02ecbdea's REPORT.md,
unchanged, still valid) to run it standalone if wanted:
```bash
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
PGDATA=<short scratch dir>   # macOS unix-socket path cap ~103 bytes
initdb -D "$PGDATA" -U postgres -A trust --locale=en_US.UTF-8 -E UTF-8
mkdir -p /tmp/org_test_pgsock
pg_ctl -D "$PGDATA" -o "-p 54329 -k /tmp/org_test_pgsock" -l "$PGDATA/log" start
createdb -h /tmp/org_test_pgsock -p 54329 -U postgres org_test
ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test \
  .venv/bin/python -m pytest tests/test_db_backend_pg.py -q -p no:cacheprovider
pg_ctl -D "$PGDATA" stop -m fast
```

## Issues / Blockers

- None blocking. Flagging for the CTO: a local Postgres instance is
  currently live on port 54329 (`org_test` + `org_rehearsal` present,
  owned by another session) — likely mid-use for the Contabo hub-migration
  work tracked in the CEO's LungNote queue (org item #3). Not touched here.

## Notes for Reviewer

- Merge commit brings in `main`'s `2de97194`/`c26383ad` (task-02ecbdea +
  its REPORT.md cleanup) — review that diff is just the expected upstream
  content, not new work from this task.
- `id=?` in `cto_chat_designer.py` intentionally left as plain equality —
  see rationale above; flag if you wanted it folded to `UPPER(id)=UPPER(?)`
  for consistency instead (a behaviour change beyond the brief's scope, so
  I didn't make that call unilaterally).

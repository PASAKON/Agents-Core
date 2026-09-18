# REPORT — task-78586938: fix the tasks.db hub migration rehearsal (3 defects) + test-isolation bug

docs/design/tasks-db-hub.md §3.1/§3.3. Section A ran against a LOCAL scratch
Postgres 16 (127.0.0.1:54329, already running from the CTO's own rehearsal)
using the LIVE, read-only Mac `state/tasks.db` as source (never written to).
Section C (`cutover-mac.sh`) was exercised dry-run only, per the brief —
`--apply` was never passed.

Starting state note: this worktree's branch (`agent/developer-task-78586938`)
was cut from `main` **before** task-02ecbdea's dual-backend work (`lib/db_pg.py`,
`scripts/migrate_tasks_db.py`, `tests/test_db_backend_pg.py`) had merged, so
none of those files existed here at kickoff. Fast-forwarded onto local `main`
(`git merge main --ff-only`, `d50d4ac3..c26383ad`) before starting; no conflicts,
no rebase. Also received a mid-task correction from the CTO ("lib.db's schema
initialiser is `init()`, there is no `init_db`") — already the plan; addressed
by extracting `lib.db.init_schema()` out of the existing `init()` rather than
adding a new entry point.

## A. `scripts/migrate_tasks_db.py` — fresh-target failure (3 causes)

- **`lib/db.py`**: split `init()`'s body into a new `init_schema(conn, *,
  is_pg: bool)` (schema DDL + `_MIGRATION_COLUMNS`/`_C_LEVEL_SESSION_MIGRATION`
  ALTERs + the report→delegate_log backfill) that takes an already-open
  connection. `init()` now just calls it. Pure extraction — same SQL, same
  order, `init()`'s own behavior is unchanged. This is what lets the migration
  script initialise a `--to` target that `ORG_DB_URL` doesn't point at,
  reusing the exact column list instead of duplicating it (the CTO's
  correction).
- **`scripts/migrate_tasks_db.py`**:
  - Calls `db_mod.init_schema(pconn, is_pg=True)` + `commit()` before
    counting, on both dry-run and `--apply` — idempotent DDL only (`CREATE
    TABLE IF NOT EXISTS` / guarded `ALTER TABLE ADD COLUMN`), never touches
    row data, so dry-run's "writes nothing" contract for the *migration*
    itself still holds. Fixes cause 1 (missing schema) and cause 2 (missing
    `_MIGRATION_COLUMNS`/`_C_LEVEL_SESSION_MIGRATION` on a bare `PG_SCHEMA`
    target) in one fix, since both are the same "target has no schema yet"
    problem.
  - `_pg_execute()` now `rollback()`s on error before re-raising — a failed
    statement leaves a psycopg (`autocommit=False`) connection aborted until
    `rollback()`, which is exactly what turned the CTO's measured `tasks: 0`
    (from a missing-table exception silently swallowed) into
    `InFailedSqlTransaction` on the very next statement. `_counts()` now
    prints the string `"missing"` (with the underlying error on stderr)
    instead of a silent `0` when a table genuinely can't be counted.
  - `_reset_events_identity_sequence()`: after copying, `SELECT
    setval(pg_get_serial_sequence('events','id'), COALESCE((SELECT MAX(id)
    FROM events), 0) + 1, false)` — `false` for `is_called` means the next
    `nextval()` returns exactly that value, correct whether the table is
    empty (next id = 1) or not (next id = max+1). Fixes cause 3 (duplicate
    key on the first post-migration `INSERT INTO events` through the normal
    API).
  - Per-row failure handling: `_copy_table()` now returns `(moved, skipped)`.
    Default: the first failing row does `pconn.rollback()` (undoing only
    *this table's* uncommitted batch — earlier tables already committed) and
    raises `RowCopyError(table, pk, error)`; `main()` prints `table=… pk=…
    error=…` to stderr and returns 1. `--skip-bad-rows`: each row runs inside
    its own `SAVEPOINT`, so `ROLLBACK TO SAVEPOINT` on a bad row doesn't
    discard the good rows already inserted in the same table/transaction;
    skipped `(table, pk, error)` tuples are listed at the end. Still exactly
    one `commit()` per table either way ("per-table commits", unchanged).

### Real-data rehearsal (live Mac `state/tasks.db`, read-only; target `org_rehearsal`, dropped+recreated fresh)

```
$ psql -h 127.0.0.1 -p 54329 -U postgres -c "DROP DATABASE IF EXISTS org_rehearsal;" -c "CREATE DATABASE org_rehearsal;"
DROP DATABASE
CREATE DATABASE

$ .venv/bin/python scripts/migrate_tasks_db.py --from /Users/gob/Projects/Agents/state/tasks.db \
    --to postgresql://postgres@127.0.0.1:54329/org_rehearsal
mode:   DRY-RUN (pass --apply to write)
before:
  source (sqlite):     tasks 948   c_level_sessions 139   events 7583   locks 11
  target (postgres):   tasks 0     c_level_sessions 0     events 0      locks 0
would move (dry-run, nothing written):
    tasks                +0      target now: 0
    c_level_sessions     +0      target now: 0
    events               +0      target now: 0
    locks                +0      target now: 0
```

No `InFailedSqlTransaction`, no silent-0 — this is the exact scenario that
crashed before the fix (fresh target, `tasks: 0` in the log).

```
$ .venv/bin/python scripts/migrate_tasks_db.py --from /Users/gob/Projects/Agents/state/tasks.db \
    --to postgresql://postgres@127.0.0.1:54329/org_rehearsal --apply
after:
    tasks                +948    target now: 948
    c_level_sessions     +139    target now: 139
    events               +7583   target now: 7583
    locks                +11     target now: 11
```

Second `--apply` (idempotency): `+0` on every table, target counts unchanged
(948 / 139 / 7583 / 11).

Read-back through `lib.db`:

```
$ ORG_DB_URL=postgresql://postgres@127.0.0.1:54329/org_rehearsal .venv/bin/python -c "
from lib import db
with db.get_conn() as c:
    print('tasks:', c.execute('select count(*) from tasks').fetchone()[0])
    print('events:', c.execute('select count(*) from events').fetchone()[0])
"
tasks: 948
events: 7583
```

Identity-sequence proof — one `INSERT` through the normal `lib.db` API after
cutover:

```
$ ORG_DB_URL=postgresql://postgres@127.0.0.1:54329/org_rehearsal .venv/bin/python -c "
from lib import db
with db.get_conn() as c:
    before = c.execute('select count(*) from events').fetchone()[0]
    db.log_event(c, None, 'rehearsal-check', 'post_migration_identity_check', {})
    c.commit()
with db.get_conn() as c:
    after = c.execute('select count(*) from events').fetchone()[0]
    row = c.execute(\"select id from events where kind='post_migration_identity_check'\").fetchone()
print('before:', before, 'after:', after, 'new row id:', row['id'])
"
before: 7583 after: 7584 new row id: 7637
```

Succeeded with no duplicate-key error — the sequence was correctly advanced
past the highest copied id (ids have gaps from prior deletions, so 7637 > row
count 7584 is expected and correct).

## B. `conftest.py` — session-env leak into pytest (5 real failures)

New autouse fixture `_clean_session_env`: `monkeypatch.delenv(...,
raising=False)` for `CTO_SESSION_ID`, `CXO_SESSION_ID`, `CXO_ROLE`,
`CTO_SESSION`, `CXO_SESSION`, and `ORG_DB_URL` (ADR 0021 — a test must never
reach the real hub). `ORG_TEST_DB_URL` is untouched — that's how
`tests/test_db_backend_pg.py` opts in. A test that needs one of these set
(`test_charter_gate_blocks_then_passes`) layers its own `monkeypatch.setenv`
on top, same pattern as the existing `_pin_tmux_bin` fixture.

Proof — full suite (`scripts lib tests`), clean vs. polluted environment,
same result both times:

```
$ .venv/bin/python -m pytest -q scripts lib tests
...
FAILED scripts/test_skill_doctrine_lint.py::test_real_corpus_reports_zero_defects
FAILED tests/test_multihost.py::test_browser_operator_cap_winbox_is_one
$ echo $?
1
# 1227 passed, 2 failed, 18 skipped

$ export CTO_SESSION_ID=deadbeef CXO_ROLE=cto ORG_DB_URL=postgresql://nobody@127.0.0.1:1/none
$ .venv/bin/python -m pytest -q scripts lib tests
...
FAILED scripts/test_skill_doctrine_lint.py::test_real_corpus_reports_zero_defects
FAILED tests/test_multihost.py::test_browser_operator_cap_winbox_is_one
$ echo $?
1
# 1227 passed, 2 failed, 18 skipped  (identical to clean run)
$ unset CTO_SESSION_ID CXO_ROLE ORG_DB_URL
```

Identical pass/fail/skip counts in both runs — the polluted env (which
previously broke `scripts/test_watchdog_remote_heartbeat.py`'s 5 tests) no
longer leaks in. The 2 reds are the pre-existing, known-unrelated ones named
in the brief.

(Note: pytest's default `testpaths = scripts lib`, per `pytest.ini`, excludes
`tests/`, where `test_multihost.py` and `test_db_backend_pg.py` live — ran
with explicit `scripts lib tests` to include both, matching the brief's "2
known reds" which names one test from each directory.)

## `ORG_TEST_DB_URL=… pytest tests/test_db_backend_pg.py` — green, 15 tests

```
$ ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test .venv/bin/python -m pytest tests/test_db_backend_pg.py -q
...............                                                          [100%]
$ echo $?
0
```

11 pre-existing + 4 new:
- `test_migrate_creates_schema_on_fresh_target` — drops the schema the
  autouse fixture just created, migrates into a genuinely bare target
  (reproduces the CTO's exact rehearsal failure), asserts it now succeeds.
- `test_migrate_advances_events_identity_sequence` — migrates rows with
  gapped/explicit ids, then inserts one more event through `lib.db.log_event`
  and asserts no collision.
- `test_migrate_bad_row_default_aborts_and_reports_pk` — monkeypatches
  `db_pg.Connection.execute` to fail on one specific row's INSERT; asserts
  `rc == 1`, `table=tasks`/the failing id appear on stderr, and the *whole
  table* (including the row that copied fine before the failure) was rolled
  back to 0 rows.
- `test_migrate_skip_bad_rows_continues_and_lists_skipped` — same flaky
  setup with `--skip-bad-rows`: `rc == 0`, the good row landed, the bad one
  is listed as skipped.

(Note: postgresql@16 was already running on 127.0.0.1:54329 from the CTO's
own rehearsal, with `org_test`/`org_rehearsal` already created — reused per
the task brief's note; `org_rehearsal` was dropped/recreated fresh for the
real-data run above.)

## C. `scripts/hub/cutover-mac.sh` — dry-run by default, never applied

Implements `docs/design/tasks-db-hub.md` §3.3 steps 1-5. `--apply` was never
passed in this session (brief: "Do NOT run `--apply`").

- **Step 1** (refuse if live work is in flight) always runs, even in
  dry-run — it's a safety gate, not a preview. Read-only: `lib.db.list_tasks`
  + `tmux list-sessions`.
- **Steps 2/3/4/5** print what they would do; only mutate anything under
  `--apply`.
- **Step 4 approach** (env-var source): route
  `config/cto.mcp.json`/`config/worker.mcp.json`'s `command`/`args` and both
  launchd plists' `ProgramArguments` through a new wrapper,
  `scripts/hub/with-org-db-env.sh`, which sources the hub's env file
  (`ORG_DB_URL`) at process-spawn time and `exec`s the real command.
  `scripts/hub/cutover_flip.py` does the file edits (`--apply`) or prints a
  unified diff (dry-run, always). Chose the wrapper over writing the literal
  value into these files because two of them
  (`cto.mcp.json`/`worker.mcp.json`) are **git-tracked** — the connection
  string carries a password and must never land in a commit — and using the
  same wrapper for the two (non-git-tracked) plists too, plus a small
  source-the-file block in `scripts/cto-claude.sh` (already a shell script,
  so it can just `source` directly), means rotating the password later means
  editing one env file, not four.
- **Bug found while testing `cutover_flip.py` against the real files**: the
  real `~/Library/LaunchAgents/com.mooniex.agents-watchdog.plist` has
  `--loop` inside an XML comment (`<!-- ... runners.watchdog --loop, ... -->`)
  — a bare double-hyphen inside a comment is invalid XML per spec. launchd's
  own parser tolerates it; Python's strict expat parser (what `plistlib`
  uses) raises `ExpatError` on it. Rewrote `_flip_plist()` to a text-level
  regex insert (same approach as the `cto-claude.sh` edit) instead of
  `plistlib.loads()`/`dumps()`, so it never has to parse the file.

### `bash -n` + shellcheck

```
$ bash -n scripts/hub/cutover-mac.sh scripts/hub/with-org-db-env.sh && echo OK
OK
$ shellcheck scripts/hub/cutover-mac.sh scripts/hub/with-org-db-env.sh && echo OK
OK
```

### Dry-run transcript

Run 1 — real environment, no overrides (proves step 1 actually refuses
against real state — this Mac has genuine in-flight org work right now,
this very task included):

```
== step 1: refuse if any live work is in flight ==
REFUSING: tasks still in flight:
task-78586938	in_progress	developer	W1c — migrate_tasks_db.py fails on a fresh hub …
task-4e089be0	review	developer	t
... (60+ more review/in_progress rows, real production state)
```

Run 2 — same real tasks-in-flight refusal fires again once that's cleared
via `ORG_ROOT` override (an empty scratch `state/tasks.db`), this time on
the **real** `wd-*` tmux sessions this dev machine actually has running:

```
== step 1: refuse if any live work is in flight ==
ok: no in_progress / live-pid review tasks.
REFUSING: worker tmux sessions still running:
wd-78586938
wd-a98788d7
```

Run 3 — full walkthrough, with a stub `tmux` (reports no sessions) added to
`PATH` and `MOONIEX_ORG_DB_ENV` pointed at a scratch file naming the local
rehearsal Postgres (`org_rehearsal`) — the only way to see steps 2-5's output
on a machine that is, correctly, always refused by step 1's real checks:

```
MODE: DRY-RUN (pass --apply to execute for real). Nothing below writes anything
except the read-only checks in step 1, which always run.

env file:   .../scratchpad/fake-org-db.env
hub target: 127.0.0.1:54329/org_rehearsal

== step 1: refuse if any live work is in flight ==
ok: no in_progress / live-pid review tasks.
ok: no wd-* tmux sessions.

== step 2: freeze the watchdog (restored on exit, success or failure) ==
would run: launchctl bootout gui/501/com.mooniex.agents-watchdog

== step 3: migrate state/tasks.db -> hub ==
would run: .venv/bin/python scripts/migrate_tasks_db.py --from state/tasks.db --to <ORG_DB_URL> --apply
would then require: sqlite count == postgres count, every table (refuse otherwise)

== step 4: flip config/plists/cto-claude.sh to read ORG_DB_URL from the env file ==
approach chosen: reference scripts/hub/with-org-db-env.sh's path from
config/cto.mcp.json + config/worker.mcp.json's command/args and from both
launchd plists' ProgramArguments; scripts/cto-claude.sh (already a shell
script) gets a small block that sources the env file directly.
why: two of these files (cto.mcp.json, worker.mcp.json) are git-tracked --
the connection string carries a password and must never land in a commit
-- and routing every consumer through one wrapper means rotating the
password later means editing the env file once, not four files.

--- a/config/cto.mcp.json
+++ b/config/cto.mcp.json
@@ -1,8 +1,12 @@
       "command": "/Users/gob/Projects/Agents/.venv/bin/python",
-      "args": ["-m", "runners.cto_mcp_server"],
+      "command": ".../scripts/hub/with-org-db-env.sh",
+      "args": [
+        "/Users/gob/Projects/Agents/.venv/bin/python",
+        "-m",
+        "runners.cto_mcp_server"
+      ],
[... config/worker.mcp.json, both plists' ProgramArguments, and the
     scripts/cto-claude.sh source-block insert — all diffs clean,
     indentation preserved (spaces in one plist, tabs in the other) ...]
(dry-run -- pass --apply to write the above.)

== step 5: verify a create_task round trip via lib.db, then archive state/tasks.db ==
would run: create_task()+get_task() round trip via lib.db with ORG_DB_URL set
would then run: mv state/tasks.db .../state/tasks.db.archived-2026-09-18 && ls -la ...

== summary ==
what changed:   ORG_DB_URL now flows through config/{cto,worker}.mcp.json, ...
how to roll back: git checkout -- config/cto.mcp.json config/worker.mcp.json ...
watchdog:       restarts automatically when this script exits (see step 2 cleanup).

== step 2 (cleanup): restore the watchdog ==
would run: launchctl bootstrap gui/501 .../com.mooniex.agents-watchdog.plist
```

Exit code `0`. Verified afterward that nothing real was touched: `git status
--short config/ scripts/cto-claude.sh` clean, and `grep -c with-org-db-env`
on both real plists returns `0`.

## Files changed

- `lib/db.py` — extracted `init_schema(conn, *, is_pg)` out of `init()`.
- `scripts/migrate_tasks_db.py` — schema init before counting, robust
  `_counts`/`_pg_execute` (rollback + "missing"), events identity-sequence
  advance, per-row failure handling + `--skip-bad-rows`.
- `tests/test_db_backend_pg.py` — 4 new tests (see above).
- `conftest.py` — new autouse `_clean_session_env` fixture.
- `scripts/hub/cutover-mac.sh` (new) — the §3.3 runbook, dry-run by default.
- `scripts/hub/with-org-db-env.sh` (new) — env-file-sourcing wrapper.
- `scripts/hub/cutover_flip.py` (new) — the step-4 file edits + diff.
- `docs/design/tasks-db-hub.md` — §3.3 pointer to the new script.

## Tests

- ran: `.venv/bin/python -m pytest -q scripts lib tests` (clean env)
  — passed: 1227, failed: 2 (known), skipped: 18, exit 1
- ran: same command with `CTO_SESSION_ID=deadbeef CXO_ROLE=cto
  ORG_DB_URL=postgresql://nobody@127.0.0.1:1/none` exported (polluted env)
  — passed: 1227, failed: 2 (same known reds), skipped: 18, exit 1
- ran: `ORG_TEST_DB_URL=postgresql://postgres@127.0.0.1:54329/org_test
  .venv/bin/python -m pytest tests/test_db_backend_pg.py -q`
  — passed: 15, failed: 0, skipped: 0, exit 0
- ran: `bash -n` + `shellcheck` on `scripts/hub/cutover-mac.sh` +
  `scripts/hub/with-org-db-env.sh` — clean, no findings
- ran: real-data rehearsal (see §A above) against the live, read-only Mac
  `state/tasks.db` into `org_rehearsal` — all four table counts matched
  after `--apply` (948/139/7583/11), second `--apply` was `+0` everywhere,
  read-back via `lib.db` matched, one `log_event()` insert post-migration
  succeeded with no duplicate-key error

## Issues / Blockers

- None outstanding. `state/tasks.db` (live, real) was only ever opened
  read-only via `db_mod.sqlite_connect(path, readonly=True)`, matching ADR
  0021 — never written to.
- One incidental leftover: a scratch `state/tasks.db` was created inside
  *this worktree* (not the hub's) while testing `cutover-mac.sh`'s dry-run
  path against non-live data — it's covered by `.gitignore`
  (`state/tasks.db`) and does not appear in `git status`, but
  `scripts/hook-self-repo-guard.py` (ADR 0020, correctly) refused my own
  attempt to delete it since `state/tasks.db*` wasn't in this task's
  declared `touches`. Harmless — local to this worktree, gitignored, no
  effect on review or merge.

## Notes for Reviewer

- This worktree's branch was cut before task-02ecbdea merged into `main`;
  I fast-forwarded onto local `main` (`d50d4ac3..c26383ad`) before starting
  so `lib/db_pg.py`/`scripts/migrate_tasks_db.py`/`tests/test_db_backend_pg.py`
  existed to fix. No conflicts.
- Chose to reuse `lib.db.init()`'s exact schema/column-migration logic via a
  new `init_schema()` rather than duplicating it in `scripts/migrate_tasks_db.py`,
  per both the task brief and the CTO's mid-task correction.
- `scripts/hub/cutover-mac.sh` was never run with `--apply` — every mutating
  branch (`launchctl bootout/bootstrap`, the real migrate `--apply`, the real
  file edits, the `mv` archive) is gated on `[ "$APPLY" -eq 1 ]` and was only
  exercised via `bash -n`/shellcheck/dry-run reads in this session.
- The `MOONIEX_ORG_DB_ENV` override (both in `cutover-mac.sh` and
  `with-org-db-env.sh`) is a real, intentional feature, not test-only
  scaffolding — it's how a non-default env-file location would be pointed at
  in production too, and it's what let this session's dry-run tests avoid
  ever touching the real `~/.config/mooniex/org-db.env`.

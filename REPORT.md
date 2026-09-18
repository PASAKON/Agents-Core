# REPORT — task-7ad6ad8a: cutover-mac.sh liveness gate + loud tombstone + pytest DB isolation

docs/design/tasks-db-hub.md §3.3, task-78586938's `scripts/hub/cutover-mac.sh`.
Everything below was exercised dry-run only against the real Mac tasks.db
(read-only) and the real `~/.config/mooniex/org-db.env` (read, never printed)
— `--apply` was never passed, no DB rows were edited.

## A. Liveness-aware gate

`scripts/hub/cutover_gate.py` (new) replaces the inline heredoc that used to
live in step 1. `in_progress` still refuses unconditionally. A `review` row
with a pid only refuses when that pid is BOTH alive and identity-matched to
the task (`tools.worker_reap._pid_alive` + `_pid_matches_task` — the same
check the reaper uses before ever signalling a pid). A dead or recycled pid
is counted as stale and printed as an info line, not a refusal. No
`--allow-stale-review` flag was added — the liveness test makes it
unnecessary, per the brief.

`scripts/hub/cutover-mac.sh` step 1 now calls this module and, unconditionally
and read-only, lists any other live `cto-*`/`cxo-*` tmux sessions as a
reminder (not a refusal) to restart them after the flip — they keep talking
to the old SQLite backend until restarted (§3.3 step 7). `wd-*` worker
sessions still refuse as before.

### Before (measured in the task brief)

> 55 `review` rows carry a pid — every one of them a worker reaped days or
> weeks ago... So the gate refuses forever even though the Mac is idle.

### After — real dry-run output, this session

```
$ bash scripts/hub/cutover-mac.sh
MODE: DRY-RUN (pass --apply to execute for real). Nothing below writes anything
except the read-only checks in step 1, which always run.

env file:   /Users/gob/.config/mooniex/org-db.env
hub target: 100.118.171.23:5432/org

== step 1: refuse if any live work is in flight ==
REFUSING: tasks still in flight:
task-7ad6ad8a	in_progress	developer	W1d — cutover-mac.sh step-1 gate must test pid LIVENESS (55 dead-pid review rows make it refuse forever) + loud tombstone for the archived sqlite so an un-restarted session cannot silently recreate an empty tasks.db
```

That refusal is **correct** — this worker (me, task-7ad6ad8a) is genuinely
`in_progress` right now. The gate now lists exactly the one genuinely-live
task instead of drowning it in 55 stale rows. Standalone breakdown against
the same live DB, same moment:

```
$ .venv/bin/python -c "... classify_tasks(db.list_tasks(limit=2000)) ..."
live: 1
  task-7ad6ad8a in_progress developer W1d — cutover-mac.sh step-1 gate must test pid LIVENESS (55 ...
stale (dead-pid review rows): 53
```

53 of the 55 originally-reported stale rows are still stale now (org is a
live system; a couple were cleaned up between the brief being written and
now) — none of them block the cutover. The `ok:`/`info:` non-refusing text
path and the `cto-*`/`cxo-*` reminder path are covered by unit tests (below)
since I can't clear my own `in_progress` row mid-task to exercise them live.

## B. Loud tombstone after archiving

- `lib/db.py`: new `ArchivedDB(RuntimeError)` + `ARCHIVED_TASKS_DB_MSG`
  constant. `_connect()` raises `ArchivedDB` when the resolved sqlite path
  (module `DB_PATH` or an explicit `path=`) is a directory — before this,
  sqlite3 would silently `mkdir -p` + create a fresh empty database there.
  No effect when `ORG_DB_URL` is set (`_connect()` is never reached on that
  path).
- `scripts/hook-self-repo-guard.py`: new `ArchivedHub` exception; `load_touches`
  re-raises `db_lib.ArchivedDB` as `ArchivedHub`, and `decide()` catches it
  and fails OPEN with exactly:
  `[self_repo_guard] tasks.db is archived (hub cutover done) — this session
  predates the cutover: restart it (/terminal-restart) so it talks to the hub`
- `scripts/hook-log-prompt.py`: **no code change needed** — `_task_owners()`
  already wraps its `get_conn()` call in a broad `except Exception`, prints
  "registry unreachable, skipping owner filter: {exc}" (which includes the
  same message text via `{exc}`), and returns `{}`. Verified this doesn't
  crash with a directory-shaped `tasks.db` (test below).
- `scripts/hub/cutover-mac.sh` step 5: after `mv state/tasks.db "$ARCHIVE_PATH"`,
  now runs `mkdir "$ROOT/state/tasks.db"` and prints what it did + the undo
  command (`rmdir state/tasks.db && mv $ARCHIVE_PATH state/tasks.db`). The
  dry-run branch previews the same tombstone step and undo command. The
  summary/rollback footer at the bottom of the script was updated to match.

## C. CTO addendum — pytest must never reach a real checkout's tasks.db

Measured cause: `runners/worker_init.py` exports `ORG_ROOT=<hub root>` for
every worker; `lib.db._resolve_root()` honours it; a worker's `pytest` run
inherits that `ORG_ROOT`, so any subprocess-based test that spawns a fresh
`python3 -c '...from lib import db...'` gets a fresh `lib.db` import that
resolves straight to the real checkout's `state/tasks.db` (29 test-proj rows
+ 13 events landed there this way, cleaned up by the CTO from a backup).

Two layers, as specified:

1. `conftest.py`: new autouse `_isolate_org_root(tmp_path, monkeypatch)` sets
   `ORG_ROOT` to a per-test `tmp_path` for every test. This isolates any
   subprocess a test spawns (its own fresh `lib.db` import resolves against
   the tmp root). It does **not** retroactively change this process's
   already-imported `lib.db` module (`ROOT`/`DB_PATH` are computed once at
   first import) — tests that call `lib.db` directly still monkeypatch
   `db.DB_PATH` themselves, the existing convention.
2. `lib/db.py` `_connect()`: if `PYTEST_CURRENT_TEST` is set and the resolved
   root (`db_path.parent.parent`) has a `.git` entry (file or dir — real
   checkouts/worktrees always have one, `tmp_path` fixtures never do), raise
   `RuntimeError("tests must not touch a real checkout's tasks.db (ADR
   0021)")`. A test that monkeypatches `DB_PATH`/`path` to a tmp location is
   unaffected (its root has no `.git`).

Verified against a fabricated fake checkout (real repo root untouched) —
see `scripts/test_db_tombstone.py::test_connect_refuses_real_checkout_under_pytest`
/ `test_connect_allows_tmp_path_without_git`.

### Full suite from a WORKER-like env (ORG_ROOT already exported, this session)

```
$ env | grep ORG_ROOT
ORG_ROOT=/Users/gob/Projects/Agents

$ sqlite3 /Users/gob/Projects/Agents/state/tasks.db \
    'select count(*) from tasks where project="test-proj"'
0                                                            # before

$ .venv/bin/python -m pytest tests scripts -q -p no:cacheprovider
...
=========================== short test summary info ===========================
FAILED tests/test_multihost.py::test_browser_operator_cap_winbox_is_one
FAILED scripts/test_skill_doctrine_lint.py::test_real_corpus_reports_zero_defects
$ echo $?
1
```
1222 passed, 15 skipped, 2 failed (the exact 2 known pre-existing reds named
in the brief, nothing new).

```
$ sqlite3 /Users/gob/Projects/Agents/state/tasks.db \
    'select count(*) from tasks where project="test-proj"'
0                                                            # after — unchanged
```

Ran twice (before and after this session's code changes) with the same
result both times.

## Static checks

```
$ bash -n scripts/hub/cutover-mac.sh   # OK
$ shellcheck scripts/hub/cutover-mac.sh   # OK, no findings
$ .venv/bin/python -m py_compile lib/db.py scripts/hook-self-repo-guard.py \
    scripts/hub/cutover_gate.py conftest.py   # OK
```

## Files Changed

- `scripts/hub/cutover_gate.py` (new) — testable liveness classifier + CLI
  entry point for step 1.
- `scripts/hub/test_cutover_gate.py` (new) — the 4 required cases + 2 extra
  (no-pid review row, mixed-batch split), all stubbing `_pid_alive`/
  `_pid_matches_task`, no real pid/process/DB touched.
- `scripts/test_db_tombstone.py` (new) — `ArchivedDB` from `_connect()`
  (file, readonly, `get_conn()`), the self-repo-guard fail-open message, the
  log-prompt hook's clean degrade, and the two ADR 0021 addendum cases
  (real-checkout-shaped root refuses, tmp-path-shaped root is allowed).
- `scripts/hub/cutover-mac.sh` — step 1 liveness gate + cto/cxo tmux
  reminder; step 5 tombstone (apply + dry-run preview); summary footer.
- `lib/db.py` — `ArchivedDB`, `ARCHIVED_TASKS_DB_MSG`, the two `_connect()`
  guards (tombstone directory; PYTEST_CURRENT_TEST + real-checkout `.git`).
- `scripts/hook-self-repo-guard.py` — `ArchivedHub`, fail-open branch in
  `decide()`, re-raise in `load_touches()`.
- `conftest.py` — `_isolate_org_root` autouse fixture.

## Tests

- ran: `.venv/bin/python -m pytest tests scripts -q -p no:cacheprovider`
- passed: 1222
- failed: 2 (both pre-existing, named in the brief — unrelated to this change)
- skipped: 15
- exit code: 1 (expected — matches the 2 known reds)

## Issues / Blockers

- None. `scripts/hook-log-prompt.py` needed no code change (see Part B) —
  noted rather than silently skipped.

## Notes for Reviewer

- This worktree has no `.venv` of its own (git worktrees don't carry it); I
  symlinked `.venv -> /Users/gob/Projects/Agents/.venv` locally to run tests
  (mirrors the existing `.env` symlink pattern). Left in place: `rm .venv`
  is refused by `hook-self-repo-guard.py` (ADR 0020) because it resolves the
  symlink target to the parent checkout and refuses on principle, even
  though unlinking a symlink never touches its target. It is untracked
  (`.gitignore`'s `.venv/` covers it in intent, though git doesn't apply a
  trailing-slash pattern to a symlink) and was never staged/committed.
- The real dry-run's step-1 refusal (`task-7ad6ad8a ... in_progress`) is
  this session itself — expected, not a bug. To see the "ok" + "info:" text
  path against a live board (no genuinely in-flight rows), see the
  standalone breakdown above or the unit tests.

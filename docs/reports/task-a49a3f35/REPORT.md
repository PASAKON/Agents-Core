# REPORT task-a49a3f35

W1.9 — rehearsal of the W1.10 cutover on real data, against `org_test`. Code under test: `e639d905`
(W1.8 merged). No code, live unit, `node.yaml`, `state/tasks.db` or live `org` change was made by this task.

## Summary

The rehearsal **stops at step 1 on the merged code**: `lib.db.init_schema()` on Postgres raises
`psycopg.errors.SyntaxError: syntax error at or near "only"`, because a `;` inside a `--` comment in
`lib/db_pg.py:102` makes the naive statement splitter cut the `hosts` DDL in half. Step 5 of the real
cutover (`migrate_tasks_db.py`) would die the same way. With that one comment neutralised by an
in-memory shim (not committed), every other leg of the rehearsal passes: migration 1158+46 tasks, 182+7 sessions,
9972+173 events with 0 collisions and exact sums; `test_db_backend_pg.py` 16/16; full suite 3680 passed / 5 failed
(all five are box-specific and fail identically with no Postgres) / 3 skipped; the secretary drop-in shape works
under real systemd; the revert returns `node.yaml` byte-identical. Six further findings (one high, three medium) are
listed with the smallest fix each. **Recommendation on step 6: yes, stop the three units before the import.**

## Files Changed
- docs/reports/task-a49a3f35/REPORT.md — this report (a copy sits at the worktree root as `REPORT.md` for the hub poller)
- Outside git, in the main checkout: `state/w19-rehearsal/contabo-tasks.db` created by `sqlite3 .backup` (deleted at the end, step 8).
  `state/w19-rehearsal/mac-tasks.db` kept. `org_test` left populated (step 8). Nothing else touched.

## Commits
- see `git log` on branch `agent/tester-task-a49a3f35` (one commit: the report)

## Tests
- ran: `tests/test_db_backend_pg.py` and the full suite, with `ORG_TEST_DB_URL` set inside the Infisical shell (never `-q`)
- **As merged (e639d905):**
  - `pytest -p no:warnings tests/test_db_backend_pg.py` → **16 errors** (all `SyntaxError ... near "only"` in fixture setup)
  - `pytest -p no:warnings` (full) → **6 failed, 3659 passed, 3 skipped, 20 errors** in 591 s
  - 6 failed = the 5 box-specific ones below + `tests/test_db_snapshot_fallback.py::test_export_against_real_postgres` (same SyntaxError)
  - 20 errors = 16 in `test_db_backend_pg.py` + 4 in `tests/test_ledger_direct_opens.py` (`*_postgres`, same SyntaxError)
- **With the comment shim (F1 fix applied in memory only):**
  - `test_db_backend_pg.py` → **16 passed** in 8.7 s
  - full suite → **5 failed, 3680 passed, 3 skipped** in 528 s
- The 5 remaining failures, unrelated to Postgres — the same 5 fail with `ORG_TEST_DB_URL` unset (55 passed, 5 skipped in that subset):
  `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` (this box has 1 plugin installed),
  `tests/test_delegate_disk_floor.py::test_sufficient_disk_proceeds_to_spawn_step`,
  `tests/test_delegate_workdir.py::test_delegate_task_exports_work_dir_for_pilot_owner`,
  `tests/test_reopen_live_worker.py::test_reopen_on_dead_worker_spawns_as_before`,
  `tests/test_reopen_live_worker.py::test_live_pid_without_its_tmux_session_is_not_trusted` (tmux session exits immediately inside this worker's session).
- Does the suite leave rows in `org_test`? **No rows.** `tests/test_db_backend_pg.py` runs `DROP TABLE ... CASCADE` at setup and teardown, so it also **deletes any
  migrated data** (finding F8). After the full suite `org_test` held two empty tables, `hosts` and `letters` (`test_db_hosts_letters.py` does not drop them).
- passed: 3680 (shimmed run) / failed: 5 / skipped: 3 / new_tests_added: 0

## What was done, per step

Every DB command ran as `python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- sh -ec '...'` with
`ORG_TEST_DB_URL="${ORG_DB_URL%/org}/org_test"` derived inside that shell and `case "$ORG_TEST_DB_URL" in */org_test) ;; *) exit 9;; esac` before use.
No URL or password was printed. Output below is passed through `sed` that replaces `postgres://...` with `<URL>` and the hub address with `<hub>`.
The worktree has no `.venv` or `state/`, so I linked `.venv` to the main checkout's (git-ignored) and read the inputs from `/opt/MoonieXHQ/Agents/Core/state/w19-rehearsal/`.

### Step 0 — `org_test` empty?
```
org       org       tables in public: 0      (read-only count; live org is empty, nothing was written to it)
org_test  org_test  tables in public: 0
```
Empty, so no `drop schema` was needed and none was run.

### Step 1 — migrate both ledgers
Inputs (`sqlite3 ... integrity_check` = ok on both):

| ledger | tasks | c_level_sessions | events | locks |
|---|---|---|---|---|
| mac-tasks.db | 1158 | 182 | 9972 | 5 |
| contabo-tasks.db (my `.backup` of live) | 46 | 7 | 173 | 0 |

Command as written in the brief, first try, **fails**:
```
$ scripts/migrate_tasks_db.py --from .../mac-tasks.db --to "$ORG_TEST_DB_URL" --apply --default-host mac
source: .../mac-tasks.db      target: <hub>:5432      mode: APPLY + default-host=mac
  File "scripts/migrate_tasks_db.py", line 505, in main
    db_mod.init_schema(pconn, is_pg=True)
  File "lib/db_pg.py", line 366, in executescript
psycopg.errors.SyntaxError: syntax error at or near "only"
LINE 1: only id's AUTOINCREMENT -> IDENTITY changes,
```
Cause and fix: **F1**. To carry on I ran the same commands through `scratchpad/runpatched.py`, which strips `--` comment lines before the split and then `runpy`s the
unchanged script (source at the end of this report). Output:
```
### MAC leg                      before: pg tasks 0 / c_level_sessions 0 / events 0     collisions: 0
    tasks +1158 backfilled=1135 (now 1158)   c_level_sessions +182 backfilled=133 (now 182)   events +9972 backfilled=0 (now 9972)   exit=0
### CONTABO leg (--append-events) before: pg 1158 / 182 / 9972                          collisions: 0
    tasks +46 backfilled=40 (now 1204)       c_level_sessions +7 backfilled=1 (now 189)      events +173 backfilled=0 (now 10145)   exit=0
```
No collisions, so `--on-collision` was never needed. Idempotence: a second Contabo run inserted `+0 / +0 / +0` (3.7 s wall).

### Step 2 — verify + sums
```
verify_migration_counts.py --mode subset  mac      tasks 1158 missing=0   c_level_sessions 182 missing=0   events 9972 missing=0   exit 0
verify_migration_counts.py --mode subset  contabo  tasks 46 missing=0     c_level_sessions 7 missing=0     events 173 missing=0    exit 0
```
| table | mac | contabo | sum | org_test | difference |
|---|---|---|---|---|---|
| tasks | 1158 | 46 | 1204 | 1204 | 0 (key overlap between the two ledgers: 0) |
| c_level_sessions | 182 | 7 | 189 | 189 | 0 (key overlap: 0) |
| events | 9972 | 173 | 10145 | 10145 | 0 (169 source ids coincide, which is exactly why `--append-events` gives fresh ids) |
| locks | 5 | 0 | 5 | **0** | −5, by design: `locks` are live path locks, never migrated (`migrate_tasks_db.py` TABLES) |
| hosts / letters | — | — | — | 0 / 0 | nothing to migrate; registry fills from node-probe after the cutover |

`tasks` by host in `org_test`: mac 1073, winbox 82, contabo 49 (9 already `contabo` in the Mac ledger + 40 backfilled).

### Step 3 — tests
See the Tests section. Order matters (F8): the PG tests drop every table in `org_test`, so I ran them **before** re-migrating and re-ran step 1 afterwards
(identical numbers: 1204 / 189 / 10145, subset verify = 0 missing on both).

### Step 4 — read back through `lib.db` (`ORG_DB_URL="$ORG_TEST_DB_URL"`)
```
pg_url set: True     current_database: org_test
  hub tasks 1204   c_level_sessions 189   events 10145   locks 0   hosts 0
  get_task[mac]     task-1c3df106  found=True status=done      host=mac      diff_vs_source=[] backfilled=[host, dispatcher_host]
  get_task[mac]     task-f4305098  found=True status=done      host=mac      diff_vs_source=[] backfilled=[host, dispatcher_host]
  get_task[mac]     task-4ec8abff  found=True status=failed    host=mac      diff_vs_source=[] backfilled=[]
  get_task[contabo] task-43c3f075  found=True status=failed    host=winbox   diff_vs_source=[] backfilled=[dispatcher_host]
  get_task[contabo] task-854cb512  found=True status=done      host=winbox   diff_vs_source=[] backfilled=[dispatcher_host]
  get_task[contabo] task-28981b5d  found=True status=cancelled host=contabo  diff_vs_source=[] backfilled=[]
$ python3 -m tools.mesh_check --get-task task-1c3df106 --json   -> {id, status: done,   host: mac,     role: frontend_dev,     project: mooniex-webapp}   33 keys
$ python3 -m tools.mesh_check --get-task task-43c3f075 --json   -> {id, status: failed, host: winbox,  role: browser_operator, project: mooniex-agents}  33 keys
```
Every column of all six rows equals the source row except the NULL host columns `--default-host` fills, which is intended. The Contabo ledger holds winbox-hosted rows; they kept `winbox`.

### Step 5 — drop-in shape on real systemd (no live unit touched, no org)
```
$ systemd-run --wait --collect --pipe -p Environment=HOME=/home/secretary /usr/bin/python3 /opt/.../tools/infisical_setup.py run Agents-Core prod --as contabo -- /usr/bin/setpriv --reuid=secretary --regid=secretary --init-groups -- /opt/.../.venv/bin/python -c 'import os; print(os.getuid(), bool(os.environ.get("ORG_DB_URL")))'
[infisical run] Agents-Core/prod as contabo: ORG_DB_URL -> /usr/bin/setpriv
1001 True                                   Finished with result: success   (uid 1001 = secretary)
```
Deeper, same transient shape plus `WorkingDirectory` like the real unit: as uid 1001, `lib.db.pg_url()` truthy and `psycopg.connect(<org_test>)` succeeded (`secretary reached org_test`). So the venv, the `+` privileged fetch, `setpriv` and network reachability all work for the secretary.
The brief's command uses relative `.venv/bin/python` and no `WorkingDirectory`; I used the absolute paths of the real drop-in.

`systemd-analyze verify` (systemd 255) on scratch copies of the installed units with `deploy/systemd/<unit>.service.d/org-db.conf` beside them, under a temp dir:
```
mooniex-watchdog          exit=0, no output
mooniex-secretary         exit=0, no output
mooniex-secretary-waker   exit=0, no output
control (secretary drop-in with ExecStart=+relative-path-not-absolute ...):
  mooniex-secretary.service: Command relative-path-not-absolute is not executable: No such file or directory   exit=1
```
The control proves `verify` really loaded the drop-in, so the three clean passes are not vacuous.

### Step 6 — race check
Live Contabo ledger, sampled read-only (`sqlite3 -readonly`) every 30 s for 5 min, 07:32:27 → 07:37:27 UTC:
```
tasks 46, max(updated_at)=2026-09-29T19:01:27+00:00, events 173 (max id 173), locks 0, WAL 3440232 bytes   — identical on all 11 samples
```
**Gained in 5 minutes: 0 task updates, 0 events.** The ledger has been idle since 2026-09-29 19:01 UTC. History: events per day 09-29 = 56, 09-28 = 13, 09-27 = 8 (peak ≈ 2–3 per hour, in bursts). All units are `active`; watchdog scan interval is 300 s.
Live ledger status counts: cancelled 15, done 22, failed 8, stalled 1, pending/in_progress 0. One `c_level_sessions` row is `open`.

Timing of the import→archive window (idempotent re-run of steps 5 and 5b against `org_test`): 3.7 s + 3.4 s, plus the WAL checkpoint, so **≈ 8–10 s**.

Would rows written between step 5 (import) and step 6 (archive) be lost? I reproduced it in a scratch dir with the real `wal-checkpoint-archive.sh`: a row updated after the import snapshot ends up **only in `state/tasks.db.archived-DATE`**. It is on disk but never in the hub, and re-importing it later would print a "same key, differing data" collision that stops `--apply`. So: not destroyed, but silently missing from the hub, and the recovery is manual.
Writers that could hit that window: the watchdog (scan every 300 s → ≈ 3 % chance a scan lands in a 9 s window, and it writes only when it pings/stalls/reaps), the `secretary_server` (`db.log_event`), any worker MCP or hook on Contabo (worker MCP servers are not among the three units and step 1 checks only `cto-`/`cxo-` tmux sessions).
Also: `sqlite` connections here are per-call (`lib/db.py` `_connect`), so after the tombstone the watchdog does not crash, it raises `ArchivedDB` each scan and logs it, until step 8 restarts it seconds later.

**Recommendation: YES, stop the three units, but at the start of step 5, and move the drop-in install with it (F2).** Cost is a ≈ 1–2 min pause of watchdog/secretary/waker that the cutover restarts anyway in step 8.
Add a guard before step 5: refuse if `select count(*) from tasks where status in ('pending','in_progress')` on `state/tasks.db` is not 0 (it is 0 now).

### Step 7 — revert rehearsal
Scratch `NODE_YAML` copy (`host: contabo\n`, 14 bytes, sha256 `14ecdf539850f648…`) and a temp `SYSTEMD_DIR`. Forward: step 4's real `install` loop, then step 8's node.yaml Python block **extracted verbatim** from `contabo-cutover-remote.sh`. Back: the verbatim `print_rollback` text, then its steps 1 and 2 executed (step 3, `systemctl`, skipped on purpose: it would touch live units).
```
wrote org_db: hub to <tmp>/node.yaml            node.yaml now:  host: contabo / org_db: hub
print_rollback: 1. rm -f <tmp>/systemd/<unit>.service.d/org-db.conf ...  2. remove the org_db: line ... 3. systemctl daemon-reload, restart the three units
cutover_flip.py --rollback --apply  ->  --- a/node.yaml +++ b/node.yaml @@ -1,2 +1 @@  host: contabo  -org_db: hub
cmp <copy> /root/.config/mooniex/node.yaml -> rc=0  "byte-identical"     sha256 copy = original = 14ecdf539850f648
second rollback: "OK ... org_db already absent" / "no changes needed"      (idempotent)
```
Find `<tmp>/systemd` afterwards: only the three now-empty `<unit>.service.d` directories remain (F7). Live `/root/.config/mooniex/node.yaml` sha256 was re-checked at the end: unchanged.
**Trap found here (F4):** `cutover_flip.py` reads `MOONIEX_NODE_YAML`, not `NODE_YAML`. With only `NODE_YAML` set, its dry run printed the live `~/.config/mooniex/node.yaml` path. I set both variables, so nothing live was written.

### Step 8
`org_test` is populated: tasks 1204, c_level_sessions 189, events 10145, locks 0, hosts 0, letters 0. `contabo-tasks.db` (+ its `-wal`/`-shm`, created by my own read-only opens) removed after this report was written; `mac-tasks.db` kept.

## Findings

| # | severity | finding | smallest fix |
|---|---|---|---|
| F1 | **critical — blocks W1.10** | `lib/db_pg.py:102` has `-- Column shapes are identical; only id's AUTOINCREMENT ...` inside `PG_SCHEMA`. `_split_statements` splits on every `;` (comments included), so `only id's ...` reaches Postgres as a statement → `SyntaxError`. Every `lib.db.init()` / `migrate_tasks_db.py` on Postgres fails, fresh or not. Added by `819522e3` (W2.1). 21 tests hit it (16 + 4 + 1). Live `org` has 0 tables, so the real cutover would fail at step 5. | Reword the comment without `;` (one line). Then harden: make `_split_statements` drop `--` lines before splitting, and add a Postgres-free unit test that every statement of `PG_SCHEMA` starts with `CREATE`/`ALTER`/`CREATE INDEX`. Verified: with the comment lines stripped, 16/16 PG tests and the full suite (3680 passed) go green. |
| F2 | high | Step 4 installs the drop-ins and runs `daemon-reload` while "the three units keep running as they are until step 8". They do not: any restart before step 8 loads the drop-in and starts the unit **on the hub**. `mooniex-watchdog` is `Restart=always` (10 s), secretary `on-failure` (5 s), waker `on-failure` (10 s), so a crash, or the stop I recommend in F3 followed by a manual `systemctl start` after a refused step 5, puts a consumer on a half-migrated hub. | Move the `install` loop and `daemon-reload` from step 4 to step 8, right before the restarts (step 4 keeps the refusals and the connect probe). Same reasoning already applied to `node.yaml`. |
| F3 | medium | Race, step 6 answer above: idle now (0 rows / 5 min), but a row written in the ≈ 9 s import→archive window lands only in the archive. | Stop the three units at the start of step 5 (after F2 they are still on the old unit files), plus the refuse-if-active-tasks guard; `systemctl start` is then done by step 8's existing restart. |
| F4 | medium | `cutover_flip.py` uses `node_yaml_path()` → `MOONIEX_NODE_YAML` only; `contabo-cutover-remote.sh` step 8 writes to `$NODE_YAML`; `print_rollback` prints the flip command without any override. A test/rehearsal run that sets only `NODE_YAML` writes the wrong file, and on a post-cutover box `--rollback --apply` with only `NODE_YAML` set would edit the live one. | In the script: `export MOONIEX_NODE_YAML="$NODE_YAML"` next to the other defaults, and print the rollback line as `MOONIEX_NODE_YAML=$NODE_YAML python3 scripts/hub/cutover_flip.py --rollback --apply`. |
| F5 | medium | `mooniex-console` (node, pid 4150069, running since 09-25) holds `state/tasks.db` open read-only. I reproduced the cutover's checkpoint + `mv` + tombstone with such a reader: the `TRUNCATE` checkpoint succeeds (busy=0), the reader **keeps answering from the archived file, no error** (46 tasks, frozen). So Console shows a frozen task list after the cutover until it moves to the `org_ro` role and restarts. Stale, not lost. | Say so in the runbook and restart `mooniex-console` in step 8 once its `src/orgdb.js` hub reader is deployed (`mooniex-console` task, already named in the W1.8 design). Until then, expect stale Console tasks. |
| F6 | low | The remote script comment says the hub "already holds the Mac's ~1108 tasks from cutover-mac.sh's step 3". It does not yet: live `org` has 0 tables. The order is not enforced by the script. Rehearsal shows the two ledgers have 0 key overlap, so either order imports cleanly. | Add one line to the runbook: Mac cutover first, or run either leg first — both are safe. No code needed. |
| F7 | low | Rollback text `rm -f .../org-db.conf` leaves three empty `<unit>.service.d` directories. systemd ignores them. | Optional `rmdir --ignore-fail-on-non-empty` in `print_rollback`. |
| F8 | info | `tests/test_db_backend_pg.py` drops all tables in whatever `ORG_TEST_DB_URL` points at, before and after each test, and the full suite leaves empty `hosts`/`letters`. Running the suite wipes any rehearsal data in `org_test`. | Order the W1.9/W1.10 rehearsal as tests → migrate (done here). Nothing to change in code. |
| F9 | info | 5 tests fail on this box with or without Postgres (list in Tests): plugin list, disk floor, work_dir env, tmux exits immediately in a worker session. | Not for the cutover; the CTO decides whether they belong on Contabo's baseline. |
| F10 | info | After the migration `hosts` is empty and step 7's read-back does not count it. `locks` are 0 by design. | None; `node-probe` fills `hosts`. |

## Issues / Blockers
- **F1 blocks the cutover** until `lib/db_pg.py` is fixed. I did not change code (brief). The shim used to continue is below.
- I could not check from here whether CI (`postgres:16` service in `.github/workflows`) ran the PG tests on `819522e3`; the F1 failure is deterministic, so it should have failed there.
- The `systemctl daemon-reload`/`restart` legs of step 7's rollback were not executed (they need live units). Everything file-side was.
- Model tier: Sonnet 5.5 at high effort. F2/F3's reasoning about restarts and windows is mine from reading unit files and reproducing the archive in a scratch dir; an Opus pass over the final cutover script is worth it before G1.

## Notes for Reviewer
- Nothing live changed: live `org` only got two read-only counts (0 tables) plus `select 1`-style connects; `state/tasks.db` was read with `sqlite3 -readonly` and one `.backup`; `node.yaml` sha256 `14ecdf539850f648…` before and after; the live units were never stopped, restarted or reloaded (the transient `systemd-run` units ran and collected themselves).
- The rehearsal shim (`scratchpad/runpatched.py`, not committed):
  ```python
  import runpy, sys; sys.path.insert(0, ".")
  from lib import db_pg
  _orig = db_pg._split_statements
  db_pg._split_statements = lambda s: _orig("\n".join(l for l in s.splitlines() if not l.lstrip().startswith("--")))
  target = sys.argv[1]; sys.argv = sys.argv[1:]; runpy.run_path(target, run_name="__main__")
  ```
  A pytest variant of it (`pytest.main`) produced the "with shim" totals.
- Tooling notes: `scripts/hook-self-repo-guard.py` refused a `cp` whose **source** was under `/opt/MoonieXHQ/Agents/Core/state/` (it treated it as a write; `sqlite3 ... ".backup"` from that source was allowed), and `scripts/hook-cwd-guard.py` refuses `cd $VAR`. Both are noted in Skill learning.
- `org_test` is left as: tasks 1204 (mac 1073, winbox 82, contabo 49), c_level_sessions 189, events 10145, locks 0, hosts 0, letters 0. Re-running the PG tests will empty it.

## Skill learning
- MISSING [CTO_Gate_MergeChecklist §lib/db_pg.py changes] : any change to `PG_SCHEMA` should be run through `pytest tests/test_db_backend_pg.py` with a real `ORG_TEST_DB_URL` before merge; the W2.1 comment with a `;` (`819522e3`) got past W1.8's merge and only the rehearsal caught it · evidence: task-a49a3f35, `lib/db_pg.py:102`, 21 failing PG tests
- MISSING [CTO_Procedure_KeyFetch | no owner — Infisical-shell testing recipe] : the pattern "derive `org_test` inside `infisical_setup.py run ... sh -ec`, assert `*/org_test`, `sed` out the URL and hub address from every traceback" is what made this rehearsal printable; psycopg tracebacks print `host=<ip> user=... database=...`, so redact those too · evidence: task-a49a3f35 step3a output
- COSTLY [no owner] : a DEV worktree has no `.venv`, no `state/` and no `.env`, and the rehearsal inputs live in the main checkout; `self_repo_guard` blocks a `cp` whose source is there and `cwd_guard` blocks `cd $VAR`. Working recipe: symlink the git-ignored `.venv`, use `sqlite3 -readonly SRC ".backup DST"` and `( cd X && ... )` · evidence: task-a49a3f35 · prevented by: a line in the tester playbook and a `touches` entry for `state/w19-rehearsal/`
- COSTLY [no owner] : `pytest` output piped to a file inside a backgrounded `sh -ec '...' | sed > f &` stays empty until the run ends (10 min), so I could not see progress; `-e` also skips a trailing `echo "exit=$?"` on failure · evidence: task-a49a3f35 step3b · prevented by: run with `run_in_background` on the pipeline itself and read the tool's output file

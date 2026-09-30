# REPORT task-a23e8873

W1.9 follow-up: the Contabo cutover script and the PG splitter changed so the real W1.10 cutover cannot hit
findings F1–F7 of `docs/reports/task-a49a3f35/REPORT.md`. Branch `agent/developer-task-a23e8873`, fast-forwarded to
origin/main `7485c9c8` first (it already carries `dde96c79`, the F1 comment fix). Nothing live: no unit stopped,
restarted or reloaded, no `node.yaml` written, no live `org` write, no push. Model: Sonnet 5.5.

## Summary
All seven items done and verified: the splitter drops full-line `--` comments; step 4 of the cutover now only refuses, step 5 refuses on live tasks
and stops the three units, step 8 writes `node.yaml`, installs the drop-ins, reloads and restarts (in that order); `MOONIEX_NODE_YAML` is exported and printed in the rollback;
the rollback removes the empty `.service.d` dirs and says how to start the units on the old unit files. Full suite 3977 passed / 2 failed / 38 skipped on both `ORG_HOST` values;
both failures are box-specific and not from this branch (below). PG tests against `org_test`: 44 passed.

## Files changed
- `lib/db_pg.py` — `_split_statements` drops full-line `--` comments before splitting on `;` (F1 hardening).
- `scripts/hub/contabo-cutover-remote.sh` — F2, F3, F4, F7 (see What was done).
- `scripts/hub/contabo-cutover.sh` — header only: steps 4/5/8 and the rollback text follow the new order; `rmdir --ignore-fail-on-non-empty`; `MOONIEX_NODE_YAML=` on the flip line; start-on-old-unit-files note.
- `docs/design/org-mesh-w18-contabo-consumers.md` — installer section rewritten for steps 4/5/8; rollback paragraph; new section "Runbook lines for the W1.10 window" (F5 Console stale list, F6 either order).
- `tests/test_db_pg_translate.py` — +4 Postgres-free splitter tests.
- `tests/test_w18_contabo_consumers.py` — `_make_tasks_db` gets a `status` column and takes statuses; the step-4-installs test renamed to step 8; ordering tests updated (stops first, reload after node write); the fakes log `dropins` (count of installed `org-db.conf` at each call) and `node_env`, and take `FAKE_STOP_FAIL_UNIT` / `FAKE_RELOAD_FAIL`.
- `tests/test_w19b_cutover_fixes.py` — new, 27 tests for F2, F3, F4, F7 and the F5/F6 doc lines and headers.
- `docs/reports/task-a23e8873/REPORT.md` — this report.

## Commits
- `5eef874d` — db_pg: _split_statements drops full-line -- comments before splitting on ; (W1.9 F1 hardening) + Postgres-free tests
- `55a3b7cd` — cutover: drop-ins + daemon-reload move to step 8; step 5 refuses on live tasks then stops the three units; MOONIEX_NODE_YAML exported; rollback rmdirs + starts units; runbook F5/F6
- `aca33065` — tests: test_w19b_cutover_fixes pins F2 F3 F4 F7 order and refusals against a throwaway root
- (this report, committed last)

## What was done
1. **F1 (`lib/db_pg.py`).** `_split_statements` now removes lines whose stripped text starts with `--` before splitting on `;`. Tests, no Postgres needed:
   every statement of `_split_statements(PG_SCHEMA)` starts with CREATE/ALTER/INSERT/UPDATE/DROP/DO; none carries comment prose; a `;` inside a `--` line (also one inside a column list) makes no stray statement; a `--` that is not a full-line comment is kept.
   Mutation check: with the pre-`dde96c79` comment restored in `PG_SCHEMA`, the old splitter yields two stray statements (`-- Org Mesh W2.1 ...` and `only id's AUTOINCREMENT ...`), the new one none.
   *"lib.db's PG-bound scripts":* only `PG_SCHEMA` goes through the Postgres `executescript` (`lib/db.py:620`); the ADD COLUMN migrations and the backfill use `execute()`, and `SNAPSHOT_META_SCHEMA` (`:400`) goes to a sqlite3 connection. So there is nothing else to pin.
2. **F2.** Step 4 keeps its refusals (drop-in sources, installed units, the Infisical connect probe) and now changes nothing on the box. The `install` loop and `systemctl daemon-reload` are in step 8, after the `node.yaml` write and immediately before the restarts. A failed install or reload refuses with "No unit was restarted" and prints the rollback.
3. **F3.** Step 5, only when `state/tasks.db` is a file: (a) `sqlite3 -readonly ... select count(*) from tasks where status in ('pending','in_progress','queued_remote')` must print `0`; a count that cannot be read is a refusal too (fail closed). (b) `systemctl stop` of watchdog, secretary, secretary-waker; a stop that fails refuses before the import.
   `print_rollback` gained the start-on-old-unit-files text (when the units were stopped) and an EXIT trap prints it for any failure after the stop that has no message of its own (migrate, verify, archive, read-back); it never prints twice. Step 8's restart brings the units back.
4. **F4.** `export MOONIEX_NODE_YAML="$NODE_YAML"` next to the defaults; the rollback prints `MOONIEX_NODE_YAML=$NODE_YAML python3 scripts/hub/cutover_flip.py --rollback --apply`. A test runs the printed line verbatim with a HOME whose default `node.yaml` must stay untouched.
5. **F7.** Rollback text and the `contabo-cutover.sh` header: `rmdir --ignore-fail-on-non-empty <dir>/<unit>.service.d` for the three units. A test runs those commands (also with a foreign file in one dir, which must survive).
6. **F5/F6.** Two runbook lines in the design doc (Console frozen list until `orgdb.js` ships; either order for the two legs, 0 key overlap).
7. **Tests updated / added** as listed in Files changed.

## Tests (quoted)
- ran: `.venv/bin/python -m pytest -p no:warnings` (worktree `.venv` is a symlink to the main checkout's; git-ignored, not committed)
  - default `ORG_HOST` (this box: `contabo`): **`2 failed, 3977 passed, 38 skipped in 790.20s (0:13:10)`**
  - `ORG_HOST=mac`: **`2 failed, 3977 passed, 38 skipped in 582.58s (0:09:42)`**
  - the same 2 failures on both, neither from this branch:
    - `scripts/test_skill_visibility.py::test_worker_baseline_keys_are_subset_of_installed_plugins` (this box has 1 plugin installed; the same test is in W1.9's list of box-specific failures)
    - `tests/test_h3_runner_model_launch.py::test_script_org_tools_registry_verdict` — it wraps `scripts/test_org_tools_registry.py`, which prints `[FAIL] wiki_list matches (toon)`, because `wiki_list("org:decisions")` returns `ERROR: wiki 'org' not available in this environment` (`WIKI_ROOT_ORG` is not exported in this worker shell; `cto-claude.sh` exports it). Reproduced identically on a `git archive origin/main` export in the scratchpad, so it is not from this branch.
  - the W1.9 report's other three (delegate tests) are gone: pinned by `dde96c79`.
- New/changed test files alone: `tests/test_w19b_cutover_fixes.py` **27 passed**; `tests/test_w18_contabo_consumers.py` **70 passed**; `tests/test_db_pg_translate.py` **20 passed** (16 before + 4).
- Mutation check: `tests/test_w19b_cutover_fixes.py` against the script as it was before this change → **23 failed, 4 passed** (the 4 that pass are checks that hold either way); against the new script 27 passed.
- Postgres tests against `org_test`, inside `python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- sh -ec '...'` (`ORG_TEST_DB_URL="${ORG_DB_URL%/org}/org_test"` derived inside, `case ... */org_test)` asserted, `ORG_DB_URL` unset before pytest, output through `sed` replacing URLs, IPs and `host=/user=/password=` values):
  `tests/test_db_backend_pg.py tests/test_ledger_direct_opens.py tests/test_db_snapshot_fallback.py` → **`44 passed in 36.65s`**, `pytest_exit=0`, 0 skipped (so the real Postgres was reached). **These tests DROP every table in `org_test`, so W1.9's migrated rehearsal data there is gone; that is fine and expected** (F8 of the W1.9 report). No URL or host was printed.
- `bash -n scripts/hub/contabo-cutover-remote.sh` → OK (and `contabo-cutover.sh` → OK).
- `scripts/test_mcp_role_config.py` → `OK — 0 failure(s)`.
- `scripts/test_org_tools_registry.py` → `1 FAILURE(S)` = the `wiki_list matches (toon)` line above; identical on the origin/main export, and with `ORG_HOST=mac`.
- passed: 3977 (per full run) / failed: 2 (both pre-existing, box-specific) / skipped: 38

## Blockers
- None for the change itself. The two failures above are environment issues on this box, present without this branch.
- Not done, by design: nothing was pushed or installed, and no live unit/`node.yaml`/`org` was touched. A full run of the new step 5 / step 8 against a real systemd was not possible without touching live units; it is covered by the fake-systemctl throwaway root only.

## Notes for Reviewer
- The guard counts exactly the three statuses the brief names. `lib.db.ACTIVE_STATUSES` also has `rate_limited` and `conflict`; the live Contabo ledger had none of them in the W1.9 sample (only cancelled/done/failed/stalled). If the CTO wants those blocked too, it is one word in the `select` and one parametrize entry.
- The stop happens only when `state/tasks.db` exists as a file. A re-run after the archive (tombstone directory) does not stop the units; step 8 just restarts them.
- The EXIT trap is the subtle part: it prints the rollback only if the units were stopped, the exit is non-zero and no rollback was printed yet (tests cover: migrate failure prints once with `FAILED (exit 1)`; a step 8 failure prints once without it; a step 4 refusal prints none; a stop failure prints once). An Opus read of the failure paths before G1 is worth it (W1.9 suggested the same).
- `tests/test_w19b_cutover_fixes.py` imports its fixture and helpers from `test_w18_contabo_consumers` by module name (tests/ has no `__init__.py`, so pytest puts the directory on `sys.path`). It would break under `--import-mode=importlib`; pytest.ini does not set that.
- The F7 behavioural test uses GNU `rmdir --ignore-fail-on-non-empty`, so it is skipped on darwin; the script itself runs only on Contabo.
- No `TASK.md` or root `REPORT.md` is committed, as briefed. `.venv` symlink is git-ignored.

## Skill learning
- MISSING [no owner — worker verification on Contabo] : `pgrep -af "pytest -p no:warnings"` matched OTHER workers' `claude` processes (their task text contains the command) and a shared-box suite takes 9.7–13 min because 3+ workers run theirs at once. `ps -eo pid,etimes,args | grep '\.venv/bin/python -m pytest'` shows which is yours · evidence: task-a23e8873, this session
- COSTLY [no owner] : `( a; b ) &` inside a `run_in_background` Bash call makes the tool report "completed (exit 0)" at once while the suite keeps running detached; I nearly read it as the suite's result · evidence: task-a23e8873 · prevented by: put the pipeline itself in `run_in_background` (no inner `&`), or wait on the output file with an until-loop
- MISSING [CTO_Gate_MergeChecklist §lib/db_pg.py changes] : n=2 for W1.9's note — PG_SCHEMA is now guarded without Postgres by `tests/test_db_pg_translate.py::test_every_statement_of_pg_schema_starts_with_a_sql_verb`, so a stray `;` in a comment fails the default suite, not only the `ORG_TEST_DB_URL` one · evidence: task-a23e8873 `5eef874d`
- MISSING [no owner — Contabo worker shell] : `scripts/test_org_tools_registry.py` (and `tests/test_h3_runner_model_launch.py::test_script_org_tools_registry_verdict`) fail on a Contabo worker shell with `wiki 'org' not available`, because `WIKI_ROOT_ORG`/`WIKI_ROOT_MOONIEX` are exported only by `cto-claude.sh`; the brief asks for that verdict line, so the baseline (origin/main export in the scratchpad) is the comparison · evidence: task-a23e8873
- Field note candidate [no owner — bash cutover scripts] : a `set -e` script that does something reversible-but-disruptive (stop units) needs an EXIT trap that prints the way back, gated on a "did the disruptive step run" flag and a "printed already" flag; explicit refusals print it themselves · evidence: `scripts/hub/contabo-cutover-remote.sh` `on_exit`, task-a23e8873

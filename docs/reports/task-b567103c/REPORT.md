# REPORT task-b567103c

Implemented ProjectTrack P1 on the restored P1a base. Changes remain uncommitted for the PH to commit and push; no fetch, branch switch, reset, stash, push, or live hub access was performed.

## Branch and base

- Branch: `agent/codex-task-b567103c`
- HEAD/base: `d4508cb77c90de96eba0b126ee9d0564c8aa2cb4`
- First requested check: `grep -c "def order_take" lib/portfolio.py` returned `1`.
- Read the complete worker brief, Thai plan, and the v2 contract from the main checkout's documentation (read-only fallback; the contract is absent from this base).
- Intended PH PR: `ProjectTrack P1: due dates, loops, orders, report`, stacked on #445.

## Files changed

- `lib/db.py`, `lib/db_pg.py`: migration-list columns, orders table/indexes, event kinds, schema-current checks, and task registry-id resolution during creation.
- `docs/design/projecttrack-p1-ddl.sql`: exact idempotent hub DDL and orders grant for `org_coo`.
- `lib/portfolio.py`: scheduling, replan permissions and original CEO due date, loop beats, plans, extended blockers, order lifecycle/state/progress, task resolution, Thai report, ETA medians, and opt-in v2 payload. Default v1 output remains unchanged. Project details expose milestone-derived due dates and next beat deadlines.
- `tools/portfolio.py`: all requested verbs/options and authorization using the existing enforcement pattern.
- `tools/portfolio_push.py`: v2 only when `PORTFOLIO_MONITOR_V=2`.
- `tools/spawn_ph.py`, `scripts/spawn-ph.sh`: required kind and due/cadence for local/card spawning, registry scheduling, card schedule binding, and resume reuse of existing schedules. Rebinding preserves CEO due provenance and records changed dates through replan.
- `tests/test_projecttrack_p1.py`: 50 isolated cases with a fixed clock and in-memory SQL adapter covering every behavior in the brief's Tests section, CLI execution/authorization, publisher opt-in, wire limits, attention thresholds/caps, and spawn/resume scheduling.
- `tests/test_db_init_pg_lock.py`: catalog fixture and migration assertions include P1 columns/DDL.
- `tests/test_portfolio.py`, `tests/test_portfolio_schema.py`: include orders in local-Postgres fixture cleanup.
- `tests/test_spawn_ph_resume.py`: isolate generated briefs under the test's temporary directory.
- This report.

Implementation/test diffstat, excluding this report: **13 files, 971 insertions, 43 deletions** (includes the new, untracked test file).

## Validation

Final scoped command:

```sh
env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR .venv/bin/python -m pytest tests/test_projecttrack_p1.py tests/test_db_init_pg_lock.py tests/test_portfolio.py tests/test_portfolio_schema.py tests/test_portfolio_push.py tests/test_spawn_ph_resume.py -q -o addopts='' -k 'not test_over_a_real_socket_the_server_sees_the_post_the_bearer_and_the_body and not test_a_redirect_is_an_answer_and_is_never_followed_with_the_token'
```

Result: **259 passed, 45 skipped, 2 deselected in 8.73s**.

- The 45 skips are existing integration cases requiring an explicitly configured local `ORG_TEST_DB_URL`; none was configured. New ProjectTrack tests run without a hub or network.
- The two deselections are existing real-socket publisher tests. An initial run attempted them and both failed during HTTP-server setup with `PermissionError: [Errno 1] Operation not permitted`. All other publisher cases passed.
- `-o addopts=''` removes the configuration's duplicate `-q` so pytest prints the pass count.
- `bash -n scripts/spawn-ph.sh` passed.
- `git diff HEAD --check` passed.
- The worktree had no `.venv`; created an ignored local environment. Package downloads were unavailable, so its local `.pth` reads dependencies from the existing shared environment. Tests and application imports ran from this worktree; no shared environment was modified.

## Blockers

- No implementation blocker remains for the requested local/card spawn and registry work.
- Sandbox socket restrictions prevent the two real-HTTP publisher checks. A local PostgreSQL integration run remains for the PH/CI; schema changes and grants were not applied to a hub.
- Commit, push, and PR creation are intentionally left to the PH under the latest task instructions.

## Skill learning

- (none)

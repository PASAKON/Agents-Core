# task-e8476fe3 — SomPong reads the Project Monitor through the COO gate

Branch `agent/developer-task-e8476fe3`. Brief: `Projects/MoonieX/SomPong/docs/coo/brief-2026-10-27-coo-portfolio-read.md`.
PH CooTooling #d87f41d8 opens the PR and raises the cards. Nothing here is applied to the hub yet.

## What changed

SomPong (unix user `sompong`, role `org_coo`, no DB password) can now run
`python -m runners.coo_mcp_server --cli portfolio` and call `mcp__org__portfolio`. Both go through the COO
gate's new `portfolio` op, which builds the payload with `tools.portfolio_push.build_payload()`: the same call
that feeds Console `/portfolio` and the Scriptable widget. The rows and the % are the same code path, not a
re-implementation.

| File | Change |
|---|---|
| `runners/coo_gate.py` | `op_portfolio` after `op_live_sessions`; `_portfolio_line`; `PORTFOLIO_FIELDS`; `"portfolio"` in `OPS`. Needs `session_id`, checks it is a coo session (`_coo_session`), refuses extra fields. A hub error comes back as `the portfolio could not be read from the hub (<ClassName>)`: class name only, no host, URL or secret, in the answer or in the log. |
| `runners/coo_mcp_server.py` | `"portfolio"` in `TOOL_NAMES`; plain function `portfolio()`; MCP tool `portfolio(raw=False)` (text lines, or the JSON when `raw` or when there are no lines); `--cli portfolio [--json]` prints one line per project (JSON with `--json` or on error), exit 0 / 1. |
| `deploy/coo-gate/org_coo_role.sql` | §4: `GRANT SELECT` on `projects`, `milestones`, `session_heartbeats (project_id, at)`, `project_events (id, project_id, at, kind, actor, body)`. §6: new `DO $portfolio_proof$` block (9 reads that must be accepted, 12 writes that must be refused). Every earlier block is unchanged. |
| `deploy/coo-gate/README.md` | The Project Monitor read, and a note on step 1 of the install card. |
| `tests/test_coo_gate.py`, `tests/test_coo_mcp_server.py`, `tests/test_coo_orders_pg.py` | See Tests. |

The tables are exactly the ones `lib.portfolio.monitor_payload(version=2)` reads, traced through `_monitor_all`,
`_v2_rows`, `_monitor_v2` and `_order_progress`: milestones, orders, project_events, projects,
session_heartbeats, tasks. `tasks` and `orders` were already granted to `org_coo` (the latter by PH#40f's #501),
so four grants are new. It does not read `ceo_gos`, `resource_locks` or `live_sessions`, so those stay closed.
`lib/portfolio.py` was **not** changed.

## Sample output

From the test fixture (frozen clock, three projects), not from the live hub:

```
Alpha film · cmo · 50% · stalled · record the voice · 2026-10-28T12:00:00Z
Beta loop · cgo · 0% (รอบที่ 1) · stalled · — · 2026-10-27T12:00:00Z
Gamma shelf · cto · 0% · parked · — · —
```

Format: `name · lane · pct% [(รอบที่ N) for loops] · state · next step · due`. A loop shows its round and the next beat as due.

## Needed before it works on the box (CEO Run card, PH raises it)

1. Apply the grants: `org_coo_role.py --grants-only` as hub owner `org` (README, "Install", step 1). The brief
   asks for one card together with PH#40f's orders grant. The SQL is idempotent and its own §6 proof runs in the same
   transaction, so a wrong grant fails the card instead of landing.
2. Restart `org-coo-gate.service` to load the op, then start SomPong's next session so it sees the new tool.
   Check the cgroup of the tmux server before any restart (CLAUDE.md, "one tmux server").

Until step 1 is done, the op returns `the portfolio could not be read from the hub (InsufficientPrivilege)`.

## Tests

All run with `env -u WORKER_TASK_ID`, one suite at a time. Real Postgres only on a throwaway `postgres:16`
container on `127.0.0.1:55432`, never `org-postgres`.

| Suite | Result |
|---|---|
| `tests/test_coo_gate.py` | 221 passed (200 before: 21 new tests; 4 existing tests edited, see Notes) |
| `tests/test_coo_mcp_server.py` | 32 passed (22 before: 10 new) |
| `tests/test_coo_orders_pg.py` (real PG 16, fresh DB) | 71 passed (57 before, net +14: one new test function, the rest parametrized cases; 2 forbidden-read cases replaced by write-denial cases) |
| `tests/test_coo_dispatch.py` | 28 passed |
| `scripts/test_live_sessions.py -k the_coo_role_can_read`, `tests/test_ask_run_media.py -k coo_ask_ceo_tool`, `tests/test_rotate_org_db_password.py -k verifier_matches` | 1 passed each |

Mutation checks (change the code, see a test fail, restore, `cmp` identical):

- op writes a row after reading, with the `except` wrapper removed, or with the coo-session check removed: gate tests fail (4, 7 and 5 tests).
- SQL: drop the `milestones` grant, give it INSERT, add a `ceo_gos` grant, drop a case from the proof: the SQL tests fail.
- CLI ignores `--json`, MCP tool always returns JSON, `portfolio` dropped from `TOOL_NAMES`: MCP tests fail.
- On real PG: original SQL gives the plain `InsufficientPrivilege`; removing the `session_heartbeats` grant aborts the §6 proof; a stray `UPDATE (at)` grant fails the existing "privileges differ" check.

## Notes for Reviewer

What the change reaches:

- Callers of `op_portfolio`: only `coo_gate.handle` through `OPS`; the new `portfolio` function and `_cli` branch in `coo_mcp_server`. `portfolio_push.build_payload` and `lib.portfolio` are read, not modified.
- `TOOL_NAMES` feeds `scripts/lib/cxo_mcp_config.py::_allowed_for(..., "coo")`: the coo session gets `mcp__org__portfolio` allowed automatically (asserted in `test_cxo_config_gives_coo_the_gate_server_and_only_its_tools`). No other role's list changed.
- Existing tests I changed: `test_coo_gate.py` (grant counts for `project_events`, the `NOT IN` string and comment phrase, the expected OPS set, the allowed-tools list); `test_coo_orders_pg.py` (the two cases "reading project_events back" and "reading projects", now legitimately readable, became write-denial cases).
- Config keys: none added. Exports: `coo_gate.OPS["portfolio"]`, `coo_mcp_server.portfolio`.

Things to decide or know:

- **`project_events.body` is now readable by `org_coo` for ALL project events.** A column grant cannot limit rows, and `lib/portfolio.py` reads the table by name, so a view is not possible without editing it (PH#40f's file). The monitor reads `body` for the `decided_for_ceo` text and the parked stage. The `events` audit log is a different table and stays write-only. If the CEO would rather not expose this, the alternative is a SECURITY DEFINER view that `lib/portfolio.py` queries: a change in PH#40f's file, so I did not do it.
- The gate calls `portfolio_push.build_payload()`, which picks v2 unless `PORTFOLIO_MONITOR_V=1`. If the push process ever runs with that variable set, the gate would not know and the two could differ. Today it is unset.
- `op_order_open` and `op_order_close` were already in main and in `OPS` when I started (PH#40f's work landed before the task text was written), so I added nothing for them.
- This worker process has `WORKER_TASK_ID` set, which makes `tests/test_coo_gate.py::test_coo_ask_run_hub_error_comes_back_as_ok_false` fail ("a worker cannot claim role 'coo'"). It passes with `env -u WORKER_TASK_ID`. Not related to this change.
- The real-PG fixture does not drop `tasks`, so rerunning `test_coo_orders_pg.py` on the same database raises UniqueViolation. I recreated the DB before each full run.

## Not checked / risk

- **Never run against the live hub or as `sompong`.** A worker has no `ORG_DB_URL`, and the grants are not applied. The done-when ("same rows and % as Console") is proven on a real Postgres 16 as `org_coo` with the real `lib.portfolio` code (payload equal to the owner-built payload), not on production data. The first real run after the card is the first time it meets the production schema and row volume.
- The production `org_coo` role may differ from the one the test builds (a grant made by hand, a table owned by another role). `--grants-only` and its §6 proof will say so on the card, before anything stays.
- Payload size: the op returns the whole payload plus the text lines through the unix socket. I did not measure it on production data; with the current handful of projects it is small. A very large board could hit the gate's reply limit, and I did not read that limit.
- The `PORTFOLIO_MONITOR_V=1` difference above is not covered by a test.

## Skill learning

- COSTLY [no owner] : the real-PG test fixture leaves `tasks` rows, so a second run on the same database fails with UniqueViolation and looks like a bug in the new test. Found only after the first rerun. · evidence: task-e8476fe3, `tests/test_coo_orders_pg.py` · prevented by: recreate the throwaway DB before each full run (`DROP DATABASE` / `CREATE DATABASE`), or have the fixture clear `tasks`.
- COSTLY [no owner] : `WORKER_TASK_ID` in a worker's environment makes `test_coo_ask_run_hub_error_comes_back_as_ok_false` fail with a refusal that has nothing to do with the change under test. · evidence: task-e8476fe3 · prevented by: run the COO suites with `env -u WORKER_TASK_ID`.
- MISSING [CTO_Protocol_DevSpawn §brief] : the task text said PH#40f's `order_open`/`order_close` ops were still to be built, but they were already in main; I found out by reading `OPS`. · evidence: task-e8476fe3, `runners/coo_gate.py` `OPS` · fix: put the base commit and a "check `git log` for X" line in the brief.

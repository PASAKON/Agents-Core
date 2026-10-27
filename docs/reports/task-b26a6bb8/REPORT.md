## Summary
`org_coo` may now take and close the COO's own `O-YYYYMMDD-HHMM-<4hex>` orders (taken_by `COO#<8hex>`, channel `coo:<n>`, no project, due date only with `due_set_by 'ceo'`) and write their close event, besides the existing `CO-<n>` mirror. Only `deploy/coo-gate/org_coo_role.sql` and `tests/test_coo_orders_pg.py` changed; no grants, no `want` list change.

## Files Changed
- deploy/coo-gate/org_coo_role.sql — header + grant comments; `org_coo_orders_guard` (INSERT: O- branch first, the CO- block follows verbatim; UPDATE: open O- order with `OLD.taken_by ~ '^COO#[0-9a-f]{8}$'`, CO- `ELSIF` unchanged, same to_jsonb rule and closed_at-set rule for both); `org_coo_project_events_guard` (body id CO- or O-, plus a second check that an O- order is taken_by `COO#`); 11 new refused proof cases in the `$orders_proof$` block, 3 old cases renamed (names keep the prefix tests/test_coo_gate.py looks for, `cto-fresh` instead of `someone_else`)
- tests/test_coo_orders_pg.py — new helpers `_insert_o`, `_close_event`; 19 new refused cases in `FORBIDDEN`; 4 new cases in `test_org_coo_cannot_update`; words-stay-fixed test parametrized over a CO- and an O- order; 6 new accept tests (take with / without due date, direct close, lib `order_close` without and with a linked project, direct close event, lib `order_close` of a C-level's O- order refused and order left open)

## Commits
- e6743ee3 — coo-gate: org_coo may take and close the COO's own O- orders (guards, proof cases, PG tests)
- (REPORT.md commit follows, sha in the git log)

## Tests
- ran: `env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR .venv/bin/python -m pytest tests/test_coo_orders_pg.py tests/test_coo_gate.py -q -p no:cacheprovider -o addopts=""`
- result, ORG_TEST_DB_URL unset: 137 passed, 56 skipped (the 56 are the PG cases), 0 failed
- ALSO run, beyond the brief: a throwaway `postgres:16` container (local image, 127.0.0.1:55432, removed afterwards; not the hub, no network) with `ORG_TEST_DB_URL` set: `tests/test_coo_orders_pg.py` 56 passed, 0 failed (before my change: 25 PG cases; the role file is applied twice per run, so its own proof block ran). Tail: `56 passed in 80.91s`
- fails without the change: with the old SQL swapped back the 6 new accept tests fail (8 failures in that run; the other 2 were `test_org_coo_creates_a_coo_task...` hitting `task-coopg00x` left in the scratch DB by my previous run, see Notes)
- mutations: each of 4 loosenings (project allowed on an O- insert; any taken_by on an O- update; no taken_by check on the O- close event; any due_set_by) made the role file's own `$orders_proof$` block abort the apply with the named case ("An O- id with a project on insert", "An update of an order that is not CO-<n> and not the COO's own", "A close event for an order that is not CO-<n> and not the COO's own", "An O- id with a due date set by a PH"); the unmutated file applies and prints the "verified" line

## Issues / Blockers
- The `org` and `lungnote` MCP servers failed to connect in this session (CONNECT_TIMEOUT), so `submit_report` could not be called; this file is the report.
- `lib/portfolio.order_take` on main still rejects channel `coo:<n>` (`channel must be sompong:<n> or chat:<role>-<session>`, lib/portfolio.py:990). The gate-side worker owns lib/; until that lands the gate cannot take an O- order even though the SQL now allows it. My O- take tests therefore INSERT the same 8 columns directly as org_coo instead of calling `order_take`.

## Notes for Reviewer
- Reach list (checked before editing): callers of the three guards = the triggers `org_coo_guard` on `orders` and `project_events`; tests that read the SQL as text = tests/test_coo_gate.py (13 `-k sql` cases, all green; it pins `proof.count(", true,") == 2`, the proof case-name prefixes, and exact guard fragments, so I kept every one of those strings and added the O- logic as extra branches instead of rewriting them); PG tests = tests/test_coo_orders_pg.py. No grant, config key or export changed.
- No accepted case was added to the `$orders_proof$` block (only refused ones): tests/test_coo_gate.py:695 pins exactly 2 accepted cases and that file is outside my part. The accepting paths are proven by the PG tests. If you want accepted proof cases too, change that count and the case list in tests/test_coo_gate.py in the same commit.
- Event guard uses `taken_by ~ '^COO#'` as the brief says (looser than the 8-hex regex on insert/update); say if you want it tightened.
- Fail-closed: every new boolean ends in `IS DISTINCT FROM TRUE` / `IS TRUE`, including the due_at/due_set_by pair (`due_set_by IS NOT DISTINCT FROM 'ceo'`), so a NULL cannot let a row through.
- Pre-existing, not touched: the `hub` fixture drops only the portfolio tables, so `test_org_coo_creates_a_coo_task_with_the_columns_create_task_writes` leaves `task-coopg001/2` in `tasks`; a second run on the same DB fails with a duplicate key. CI uses a fresh service DB, so it only bites local re-runs.
- deploy/coo-gate/README.md still describes only the CO- mirror; not in my list, not edited.

## Not checked / risk
- Not run against the real hub or with the gate itself: the O- take path from runners/coo_gate.py through lib/portfolio.order_take (waits on the lib change); if that worker's channel or taken_by differs from `coo:<n>` / `COO#<8 lowercase hex>`, the INSERT is refused by this guard.
- Only the 4 mutations above were tried; the other new refused PG cases were shown to pass on the real guard but not shown individually to fail on a loosened one (the proof block aborts the apply first).

## Skill learning
- COSTLY  [CXO_Protocol_DevSpawn | no owner]  : a brief that says "PG cases skip here" cost nothing, but the box had a local `postgres:16` image and no server binaries; finding that and running a throwaway container took ~3 min and caught nothing a skip would have shown, yet it is what proved the SQL parses and the proof block passes · evidence: task-b26a6bb8 · prevented by: briefs for SQL work say "a local postgres:16 image exists, use it on 127.0.0.1" or "do not"
- MISSING [no owner]  : the `hub` fixture in tests/test_coo_orders_pg.py does not drop `tasks`, so re-running on one DB fails a pre-existing test with a duplicate key · evidence: task-b26a6bb8 pg_old run (`task-coopg002 already exists`) · prevented by: add `tasks` rows cleanup to the fixture or unique ids per run

# REPORT task-53644397

ProjectTrack P6, gate side (worker A): the COO gate gets `order_open` and `order_close`, and the COO's MCP server gets the two tools. Built and tested against p1's in-memory `orders` table; **the Postgres side (org_coo role guard) is worker B's and was not run here**. Not pushed.

## Summary

`runners/coo_gate.py` has two new ops at the end of `OPS` (after `field_note`). `order_open {op, session_id, n, words, due_at?}` writes one hub `orders` row (`channel=coo:<n>`, `taken_by=COO#<sid>`, `project_id` NULL, `due_set_by='ceo'` only when a date is given) through `lib/portfolio.order_take`, and returns the open order's id with `existing: true` instead of writing when a COO-taken order for `coo:<n>` is already open. `order_close {op, session_id, order_id, outcome}` closes an open COO-taken order through `lib/portfolio.order_close` and returns `{order_id, closed_at}`.

## Files Changed

- `lib/portfolio.py` — `order_take` channel regex also accepts `coo:[0-9]{1,6}` (one line, nothing else there).
- `runners/coo_gate.py` — `ORDER_OPEN_FIELDS`, `ORDER_CLOSE_FIELDS`, shape constants, `_order_session`, `_order_due`, `op_order_open`, `op_order_close`, two `OPS` entries.
- `runners/coo_mcp_server.py` — plain functions `order_open(n, words, due_at=None)` and `order_close(order_id, outcome)`, MCP tools of the same names, both appended to `TOOL_NAMES`, docstring lines. `--cli order_open|order_close` works with no new table: `_cli` reads `TOOL_NAMES` and `globals()`.
- `tests/test_coo_gate.py` — 18 new test functions in a section at the end; two existing assertions updated (see Notes). `-k order` selects 70 cases across both test files, all passing.
- `tests/test_coo_mcp_server.py` — 3 new tests; one existing assertion loosened.

## Commits

- 853ba60d — coo-gate: order_open and order_close ops and MCP tools (ProjectTrack P6)
- (the REPORT.md commit follows this one)

## Tests

- ran: `env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR /opt/MoonieXHQ/Agents/Core/.venv/bin/python -m pytest tests/test_coo_gate.py tests/test_coo_mcp_server.py tests/test_portfolio.py tests/test_projecttrack_p1.py -q -p no:cacheprovider -o addopts=""`
- passed: 397
- failed: 0
- skipped: 36 (the `needs_pg` tests in test_portfolio.py: `ORG_TEST_DB_URL` is unset)

Test tail:

```
........................................................................ [ 99%]
.                                                                        [100%]
397 passed, 36 skipped in 125.73s (0:02:05)
```

Mutation check (the new tests fail without the guards): with the COO `taken_by` check on close removed, the `taken_by LIKE` filter on the open lookup removed, and the gate's timezone check removed, 9 tests failed (the same-n dedup, six non-COO-taken closes, the closed-foreign close, the MCP round trip). Restored; the run above is after the restore. The timezone mutation alone failed no test, because `portfolio._utc` refuses a naive datetime further down (fail closed either way; the gate's check only gives a clear message).

## Issues / Blockers

- none. One transient error seen once: the autouse fixture failed with `no such table: c_level_sessions` in `test_run_inbox_path_holds_no_hub_credential` during one full run. It passed 3 of 3 alone and in the next full run (the one above). Not caused by this change as far as I can tell, but I did not find the cause.

## Notes for Reviewer

What the change reaches (pre-work list):
- `portfolio.order_take`: callers are `runners/relay_mcp_server.py:449`, `tools/portfolio.py:401`, the new gate op, and the tests (tests/test_projecttrack_p2.py among them); `lib/ceo_report.py` only calls `order_close`. The regex only widens by `coo:<1-6 digits>`; the existing `sompong:` and `chat:` shapes are unchanged and the existing tests pass.
- `TOOL_NAMES`: feeds `scripts/lib/cxo_mcp_config.py`, which builds the COO session's `--allowed-tools` from it, so SomPong can call `mcp__org__order_open` and `mcp__org__order_close` once the launcher is restarted.
- `OPS` is checked by an exact-set test, `test_gate_serves_the_two_new_ops_and_no_others_were_added`. I added the two names there. The PH that adds a `portfolio` op will conflict on that set and on `OPS`; the resolution is to add the name.

Decisions and things that differ from a literal reading of the brief:
1. **Session id must be 8 lowercase hex** on these two ops (`Refused: session_id must be 8 lowercase hex digits`). The contract says `taken_by` is `COO#<8 lowercase hex>`, and the hub guard (worker B) refuses anything else, so the gate refuses first with a readable message. Other ops accept any session id; existing test sessions like `cootest1` are not hex, so my tests register `c0de0001`/`c0de0002`.
2. **Two existing assertions changed**: `TOOL_NAMES[-1] == "respawn_clevel"` (test_coo_gate.py, test_coo_mcp_server.py) became a membership check, because the brief says to append and the tuple now ends with `order_close`. I used membership, not `[-1] == "order_close"`, so the other PH's append does not break it again.
3. **`portfolio._tx()` is used from the gate** (a private helper) so the dedup lookup, the insert and the close checks run in one transaction on one connection, and so the tests can swap in p1's in-memory store the way tests/test_projecttrack_p2.py does. The brief says nothing else changes in `lib/portfolio.py`, so I did not add a public helper.
4. `order_close` returns `closed_at` as `YYYY-MM-DDTHH:MM:SSZ` from the `now` the gate passes to `portfolio.order_close`, not by reading the row back.
5. `due_at` accepts a trailing `Z` and any offset; a date without a zone is refused. `""` from the MCP tool is sent as null (no date); `""` straight to the gate is refused.
6. Any COO session may close any COO-taken order (the brief's wording); the project event for a linked order gets the closing session as actor, and `test_order_close_of_a_linked_order_files_the_project_event_as_the_closing_coo` proves it.
7. Test name clash caught and fixed: my first helper `_rows` replaced the existing audit tests' `_rows(kind)`; mine is `_order_rows`.

Not touched, as instructed: `deploy/coo-gate/` (including its README, which does not list the new ops), `tests/test_coo_orders_pg.py`.

## Not checked / risk

- Not run against a real Postgres or as the `org_coo` role: the SQL (`LIKE ?` with a `%` parameter, `FOR UPDATE` inside `order_close`, the insert shapes against worker B's trigger) ran only on SQLite via p1's `Store`. The trigger shapes were matched by reading the spec, not by running them. If worker B's guard differs from the spec text, the first live `order_open` will fail with a trigger error.
- The running gate does not have these ops until `org-coo-gate` is restarted (read the tmux/cgroup warning in CLAUDE.md first), and SomPong's launcher must be restarted to list the new tools. Nothing tells SomPong to call them yet (no prompt or skill edit; out of scope).
- `words` and `outcome` are stripped of NUL/lone surrogates but not secret-redacted (the audit and field-note ops are). The spec does not ask for it; a CEO order that contains a pasted secret would be stored as written.
- Two simultaneous `order_open` calls for one `n` are safe only because the gate serves one request at a time; if the gate ever becomes concurrent the lookup and insert need a unique index or a lock.

## Skill learning

- MISSING [CXO_Protocol_DevSpawn | no owner]: the worker brief does not say that the `self_repo_guard` Bash hook refuses a multi-line `git commit -m "..."` (and a `python3 - <<EOF` heredoc) as "would write to ." even when every file is under the task's `touches`; what worked was `git add <declared files>` alone, then `git commit` with one `-m` per paragraph and no heredoc, and Edit/Write for file changes · evidence: task-53644397, this session (two blocks, then commit 853ba60d)
- COSTLY [no owner]: a new test helper named `_rows` silently replaced an existing module-level `_rows` in tests/test_coo_gate.py (23 failures in the next full run); grep for the helper name before adding a module-level function to a 1,200-line test file · evidence: task-53644397, first full run

# REPORT task-65155185

org_coo may now mirror SomPong's relayed CEO orders (`orders`, `project_events`), held to `CO-<n>` rows by two new row guards. The whole role file was run for real on a throwaway Postgres 16.15 (not the hub): it applies, its own proof passes, every proof case fails when its guard is weakened, and the repo's real `order_take` / `order_close` work as `org_coo` and are refused where they should be.

## The SomPong actor value

**`COO#<CXO_SESSION_ID>`**, where the id is 8 lowercase hex digits. So it is a pattern, not one string: the guard pins `^COO#[0-9a-f]{8}$`.

| Step | Where |
|---|---|
| `report_to_ceo` closes the hub row with `identity.label()` | `lib/ceo_report.py:412` -> `_hub_order_close(order_id, status, detail, identity.label())` |
| `label()` = `f"{disp}#{session_id}"`, `disp = display_for(role)` | `tools/agent_transport.py:156-163` |
| `display_for("coo")` is the yaml `display`, not the `persona` | `lib/config.py:175`, `policies/agents.yaml:98-99` (`display: COO`, `persona: SomPong`) |
| `current_identity()` for a COO session = `Identity("cxo", "coo", CXO_SESSION_ID)` (`CXO_ROLE=coo`) | `tools/agent_transport.py:169-177` |
| `CXO_SESSION_ID` = last 8 of the resume UUID lowercased, or the tmux suffix if `[0-9a-f]{8}`, or `uuid4().hex[:8]` | `scripts/cxo-claude.sh:365-399` (a `--session` override is unconstrained, but the COO is a singleton) |

Checked by running it: `Identity("cxo","coo","abcd1234").label()` -> `'COO#abcd1234'`; `display_for('coo')` -> `'COO'`. `tests/test_coo_gate.py` now ties the SQL pattern to the live `label()` for four ids, so a renamed `display:` breaks a test, not the mirror.

The take side needs no such pattern: `relay_mcp_server.py:449` passes the literal `actor="sompong"`, which becomes `orders.taken_by`.

## What order_take / order_close read and write (the grant check)

`order_take(..., project_id=None)`: one `INSERT INTO orders (id, words, channel, taken_by, taken_at, project_id, due_at, due_set_by)`. No other table (`_project()` runs only if a project id is given).
`order_close`: `SELECT * FROM orders WHERE id = ? FOR UPDATE` (so whole-table SELECT is needed; `FOR UPDATE` needs the column UPDATE grant it already has), `UPDATE orders SET closed_at, outcome`, and only if `orders.project_id` is set `INSERT INTO project_events (project_id, at, kind, actor, body)`. **No other table is read**, so no grant was widened beyond the two in the brief. The `project_events.id` identity column needs no sequence privilege (confirmed: section 6's "no sequence privilege" check still passes). The FK to `projects` is checked by Postgres as the table owner; `org_coo` still cannot read `projects`.

## Changes to `deploy/coo-gate/org_coo_role.sql` (existing blocks byte-identical)

Only 3 existing lines changed, all unavoidable: the `want` string is split to insert the new tokens in sort order, the section 6 header comment, and the `NOT IN (...)` readable-table list (+ `'orders'`). The coo_audit / coo_field_note guard branches, the three old guard functions and the two old proof loops were compared against `HEAD` and are identical.

**Section 4:** the two `GRANT`s from the brief, verbatim.

**Section 5, `org_coo_orders_guard`** (`BEFORE INSERT OR UPDATE ON orders`, pass-through unless `current_user = 'org_coo'`, `SET search_path = pg_catalog`, every test fails closed on NULL):
- INSERT only if `id ~ '^CO-[0-9]+$'`, `taken_by = 'sompong'`, `channel = 'sompong:' || substr(id, 4)`, `project_id IS NULL`, `due_at IS NULL`.
- UPDATE only if `OLD.id ~ '^CO-[0-9]+$'`, `OLD.closed_at IS NULL`, `NEW.closed_at IS NOT NULL`, and `to_jsonb(NEW) - 'closed_at' - 'outcome'` equals the same of `OLD`. I used the jsonb row compare rather than eight column compares so a column added to `orders` later is held fixed too.

**Section 5, `org_coo_project_events_guard`** (`BEFORE INSERT ON project_events`, same style):
- `kind = 'order'`, `body->>'op' = 'close'`, `body->>'id' ~ '^CO-[0-9]+$'`, `actor ~ '^COO#[0-9a-f]{8}$'`;
- and `EXISTS (SELECT 1 FROM public.orders o WHERE o.id = body->>'id' AND o.project_id = NEW.project_id AND o.closed_at IS NOT NULL)`.

**Section 6:** `want` and the readable-table list updated; a new, separate `DO $orders_proof$` block (the old `$check$` block keeps its own proof). It runs 17 cases, each in a subtransaction rolled back by a `ZX001` raise. A refusal counts only on the **last** step of a case; a failing setup step fails the run (otherwise a missing table would read as "refused").

| Case | Expect |
|---|---|
| A valid CO order, taken and closed (take, `FOR UPDATE`, close) | accepted |
| A CO order of a project, closed with its event | accepted |
| An `O-` id (channel set so only the id check can refuse it) | refused |
| `taken_by` other than sompong | refused |
| A channel that is not the id | refused |
| A due date on insert | refused |
| A project on insert | refused |
| An update of a closed CO order | refused |
| An update that changes `words` (`GRANT UPDATE (words)` inside the case only, so the trigger, not the grant, refuses) | refused |
| An update that does not set `closed_at` | refused |
| An update of an order that is not CO-n | refused |
| A `project_events` row of another kind | refused |
| A close event under another actor | refused |
| A take event | refused |
| A close event for an order that is still open | refused |
| A close event for another project's order | refused |
| A close event for an order that is not CO-n | refused |

## Tests

- `tests/test_coo_gate.py` (+8 tests): each grant (and that they equal the columns `lib/portfolio.py` writes), each guard condition, the actor pattern against `Identity.label()`, the `want` tokens, the readable-table list and every proof case by name.
- `tests/test_coo_orders_pg.py` (new, 23 tests): **self-skips** unless `ORG_TEST_DB_URL` points at a local database and `psql` exists (CI already sets it against `postgres:16`). It applies the role file twice, then runs the real `order_take` / `order_close` as `org_coo`: valid take+close, close with the project event, 14 forbidden inserts/events, 4 forbidden updates, the grant-widened `words` case, and "a wrong actor leaves the order open". The repo had no Postgres-backed test for this file, so this is new; it is removable in one `git rm` if you would rather not have it.

```
$ env -u ORG_DB_URL -u ORG_ROOT -u WORKER_TASK_ID -u WORK_DIR .venv/bin/python -m pytest tests/test_coo_gate.py -q -p no:cacheprovider -o addopts=''
.................................................................        [100%]
137 passed in 79.83s (0:01:19)

$ ORG_TEST_DB_URL=<throwaway local PG 16.15> pytest tests/test_coo_orders_pg.py tests/test_portfolio_schema.py
35 passed in 16.40s            (without ORG_TEST_DB_URL: 23 skipped; with a non-local URL: 23 skipped)

$ pytest scripts/test_live_sessions.py -k coo_role      # regex-reads the live_sessions grant in this file
1 passed
```

Failed-without-the-change checks: the 8 new `test_coo_gate.py` tests fail on `HEAD`'s SQL (8 failed); the PG module fails 18 of 23 on it. **Mutation check** of the SQL proof on the real engine: 15 mutations (each guard condition removed in a scratch copy) -> all 15 make the apply fail with the matching proof case. The first run caught 14 of 15: my `O-` case was also refused by the channel check, so the id condition was unproved; the case was fixed and the 15th is now caught.

## Reach (callers / tests / config)

- `order_take`: `runners/relay_mcp_server.py:449` (`_hub_order_mirror`) only. `order_close`: `lib/ceo_report.py:325` (`_hub_order_close`) only.
- Reads this SQL as text: `tests/test_coo_gate.py`, `scripts/test_live_sessions.py:1764` (live_sessions grant regex, untouched). `deploy/coo-gate/org_coo_role.py` runs it; no hash pin.
- No config key, export or fixture changed.

## Notes for the reviewer

1. **Who closes as org_coo today?** `report_to_ceo` is exposed by `runners/cto_mcp_server.py` to the C-level an order was addressed to; those sessions run as the hub owner `org`, which passes straight through both triggers. Nothing in the repo calls `order_close` with an `org_coo` connection (no gate op, not in `coo_mcp_server.py`). The `COO#` actor pin only matters if SomPong's own process closes with the `org_coo` URL. I implemented the brief as given; if the relay or SomPong in fact runs as `org` these guards are inert (harmless), if as `org_coo` they are what enables the mirror. I could not confirm which from the repo (the README says SomPong holds no DB credential).
2. `order_take` **with a `project_id`** would fail earlier as `org_coo`, on `permission denied for table projects` (`_project()` does `SELECT ... FOR UPDATE`). Not a problem for the CO mirror (no project), and the guard's own project condition is separately proved.
3. Spec-faithful gaps you may want to tighten: the guard does not pin `due_set_by` (meaningless without `due_at`), does not require a non-NULL `outcome`, and does not pin the event body keys or compare `body.outcome` to `orders.outcome`.
4. The sid half of the actor is not checked against `c_level_sessions` (a `COO#` label with any 8 hex digits passes). Adding that would need a read of `c_level_sessions`, which org_coo has, but a stale row would then block a legitimate close.
5. **Not applied anywhere.** I did not run `org_coo_role.py`, psql against the hub, or any ORG_DB_URL tool. Applying this file on the hub (a Run card) does `REVOKE ALL` first and `ON_ERROR_STOP` after, so it needs `orders` and `project_events` to exist there (they do once `lib.db.init()` has run).
6. Per the task text I did **not** commit ("the harness commits"); the diff is in the worktree, uncommitted. `git status`: README.md, org_coo_role.sql, test_coo_gate.py modified; test_coo_orders_pg.py and this file new.

## Environment used for the real-engine runs (all deleted)

No Postgres server ships on this box (client tools only). I ran the server binary that already sits in a container image layer under `/var/lib/containerd/...`, as a mapped non-root uid (`unshare -U --map-user=65534`, because Postgres refuses root and the scratchpad is mode 0700), data dir in the scratchpad, unix socket only (`listen_addresses=''`, socket via a short `/tmp/cpg` symlink for the 107-char socket-path limit). Never the hub, never TCP. Stopped, data dir and symlink removed afterwards.

# REPORT task-0b05eed1

## Summary

Implemented OrderTrack Phase 1 Part A (order `O-20261127-1012-35f9`) schema and migration changes without altering `monitor_payload` v1–v4 behaviour or running DDL on the live hub:

1. **`lib/db.py`**:
   - Added `("order_id", "TEXT")` to `_MIGRATION_COLUMNS` for `tasks.order_id`.
   - Added `_ORDERS_MIGRATION` with the 10 `orders` columns (`title`, `lane`, `mode`, `ph_session`, `msg_group`, `size`, `next_step`, `blocker_what`, `updated_at`, `dropped`).
   - Wired `"orders": _ORDERS_MIGRATION` into `_pg_schema_current(conn)` so Postgres schema currency checks verify all migrated `orders` columns, `tasks.order_id`, and `order_goals`.
   - Wired `_ORDERS_MIGRATION` into `_create_and_migrate(conn, is_pg=...)` following the `_MILESTONES_MIGRATION` / `_PROJECTS_MIGRATION` pattern (`IF NOT EXISTS` guard on Postgres, `PRAGMA table_info(orders)` check on both backends).

2. **`lib/db_pg.py`**:
   - Added `CREATE TABLE IF NOT EXISTS order_goals` to `PG_SCHEMA` with columns `order_id`, `n`, `parent_n`, `title`, `weight` (`INTEGER NOT NULL DEFAULT 1 CHECK (weight > 0)`), `due_at`, `done_at`, `evidence`, `milestone_ref`, composite primary key `(order_id, n)`, self-referencing foreign key `(order_id, parent_n) REFERENCES order_goals(order_id, n)`, `CHECK (parent_n IS NULL OR parent_n <> n)`, and `CHECK (done_at IS NULL OR (evidence IS NOT NULL AND length(btrim(evidence)) > 0))`.

3. **`docs/design/ordertrack-p1-ddl.sql`**:
   - Created idempotent hub migration script (`BEGIN; ... COMMIT;`) adding the 10 `orders` columns, `tasks.order_id`, `order_goals` table, and `GRANT SELECT, INSERT, UPDATE ON order_goals TO org_coo;`.

## Files Changed

- `lib/db.py`
- `lib/db_pg.py`
- `docs/design/ordertrack-p1-ddl.sql`
- `docs/reports/task-0b05eed1/REPORT.md`

## Validation Performed

- Static verification of `lib/db.py`, `lib/db_pg.py`, and `docs/design/ordertrack-p1-ddl.sql` using file tools (per the AGY Remote Worker Contract, shell test execution is left to the review process).
- Verified every statement in `db_pg.PG_SCHEMA` matches `db._PG_CREATE_RE` (`CREATE TABLE|SEQUENCE|INDEX IF NOT EXISTS <name>`) and contains no semicolons inside statement bodies.
- Verified every `(name, kind)` pair in `db._ORDERS_MIGRATION` and `("tasks", [("order_id", "TEXT")])` matches `ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <name> <kind>;` in `docs/design/ordertrack-p1-ddl.sql`.
- Verified `lib/portfolio.py` and `tools/portfolio.py` were untouched, preserving `monitor_payload` v1–v4 byte-for-byte behaviour, and that all new `orders` columns allow `NULL` or carry a constant `DEFAULT` (`dropped BOOLEAN NOT NULL DEFAULT FALSE`) so existing v1–v4 `order_take` inserts succeed unchanged.
- Confirmed no DDL was executed against the live hub.

## Not checked / risk

- Shell test execution (`pytest tests/test_projecttrack_p1.py tests/test_portfolio_schema.py tests/test_portfolio_v4.py`) was not run inside the AGY print-mode worker per contract; reviewer should run pytest before opening/merging the shared-file PR.
- 2-level hierarchy depth (`parent_n` referencing a top-level row whose own `parent_n IS NULL`) cannot be expressed as a PostgreSQL `CHECK` constraint (PostgreSQL forbids subqueries in `CHECK`); `order_goals` enforces `FOREIGN KEY (order_id, parent_n) REFERENCES order_goals(order_id, n)` and `CHECK (parent_n IS NULL OR parent_n <> n)` in DDL, while the 2-level parent check belongs in `lib/portfolio.py`'s `order_goal_add` in P1-B.
- Live hub DDL (`docs/design/ordertrack-p1-ddl.sql`) has not been applied to the production Postgres hub and must be applied via a Run card after review.

## Blockers

- (none)

## Skill learning

- (none)

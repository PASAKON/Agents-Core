# LungNote `lungnote_todos` migrations

Schema changes for the **LungNote** Supabase project (`qkaxvockysyazmtormvf` —
its OWN project, separate from the mooniex app project). The canonical home for
LungNote schema migrations is the **LungNote webapp repo** at
`supabase/migrations/`. The copies here (next to the MCP server that depends on
them) are the source; **copy them into the webapp repo's `supabase/migrations/`
when applying** so the webapp's migration history stays complete.

## Files

| File | Purpose |
|------|---------|
| `20260803000000_lungnote_todos_status.sql` | ADD `status` column + `done`-sync trigger (forward) |
| `20260803000000_lungnote_todos_status_rollback.sql` | Reverse of the above |

Filename follows the LungNote webapp convention (`YYYYMMDDHHMMSS_name.sql`),
matching `20260508120000_lungnote_hierarchy.sql`.

## What the migration does (task-9669e961)

Adds a lifecycle `status` column so a todo records WHY it left the active list:

| status   | done (derived) | meaning                          |
|----------|----------------|----------------------------------|
| `open`   | `false`        | active / on the list             |
| `complete` | `true`       | finished for real                |
| `cancel` | `true`         | abandoned / no longer relevant   |
| `delete` | `true`         | added by mistake / duplicate (SOFT delete) |

`done` is **kept and kept in sync** via a BEFORE INSERT/UPDATE trigger:
`done = (status != 'open')`. This preserves the existing `done = false` =
"active" semantics every current consumer relies on (LungNote webapp filters
`.eq("done", false/true)`, `scripts/session-deadline-check.py`, MCP `list_todos`).
The trigger is bidirectional so the webapp's checkbox (which writes only `done`)
also stays correct.

`approve` is intentionally NOT in the enum — CEO intent for it is unclear
(possibly a tag, not a lifecycle state). Flagged back to CMO/CEO.

## Deploy order (important)

1. **Apply the migration FIRST** (Supabase SQL Editor on the LungNote project).
2. **Then** deploy the updated `index.js`. The new MCP selects/writes `status`;
   running the new code before the migration exists will error on the missing
   column.

## Applying

```
-- LungNote Supabase project qkaxvockysyazmtormvf → SQL Editor, paste the
-- forward .sql, Run. Then verify:
SELECT status, done, count(*) FROM lungnote_todos GROUP BY 1,2 ORDER BY 1;
-- expect: every 'open' row has done=f, every 'complete' row has done=t
```

This is a **live prod DB** the CEO and the LungNote webapp use today. The
migration is additive + reversible (`done` is never dropped). Apply during a
quiet window; the trigger adds negligible per-row overhead.

## Soft delete vs hard delete

The LungNote webapp's delete button (`actions.ts`) runs a SQL `DELETE` (row
gone). The MCP `delete_todo` tool this task adds sets `status='delete'`
(**soft** delete — row kept, `done=true`, off the active list, recoverable).
Both are valid; the difference is documented here so the behaviour isn't
mistaken for a bug.

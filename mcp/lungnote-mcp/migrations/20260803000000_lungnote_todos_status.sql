-- 202608030000__lungnote_todos_add_status.sql
-- LungNote Supabase project: qkaxvockysyazmtormvf (its OWN project, NOT the
-- mooniex app project). Apply via the Supabase SQL Editor (dashboard) or psql.
--
-- Purpose: give lungnote_todos a lifecycle `status` so a todo can record WHY it
-- left the active list (complete | cancel | delete) instead of only a flat
-- `done` boolean. DEV task-9669e961, CEO order 2026-08-03.
--
-- Backward compatibility is the load-bearing requirement: the LungNote webapp
-- (lungnote.com, same DB) and scripts/session-deadline-check.py both read/write
-- `done` and filter `done = false` meaning "still active/open". So:
--   * We KEEP the `done` column (never drop it).
--   * `done` becomes a DERIVED flag: done = (status != 'open').
--       status open          -> done false  (active)
--       status complete      -> done true
--       status cancel        -> done true   (off the list, not completed)
--       status delete        -> done true   (soft-deleted off the list)
--   This preserves the existing `done = false` = "active" semantics for every
--   current consumer unchanged; the new `status` just adds the WHY.
--   A BEFORE INSERT/UPDATE trigger keeps the two in sync at the DB layer so
--   ANY writer (webapp checkbox writing only `done`, or MCP writing `status`)
--   stays consistent — no application-level drift possible.
--
-- Additive + reversible: adds one column, one CHECK, one function, one trigger.
-- Rollback file: 202608030000__lungnote_todos_add_status_rollback.sql
-- `done` is untouched throughout (never dropped), so rollback is safe.

BEGIN;

-- 1. Add the column (additive; NOT NULL with default 'open').
ALTER TABLE lungnote_todos
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'open';

-- 2. Backfill existing rows from the boolean. Default already set the
--    not-done rows to 'open'; flip the done rows to 'complete'.
UPDATE lungnote_todos
   SET status = 'complete'
 WHERE done = true;

-- 3. Constrain to the 3 terminal verbs + open. (No "approve" — CEO intent
--    unclear; left out of the enum by design, see task report.)
ALTER TABLE lungnote_todos
  DROP CONSTRAINT IF EXISTS lungnote_todos_status_check,
  ADD  CONSTRAINT lungnote_todos_status_check
       CHECK (status IN ('open', 'complete', 'cancel', 'delete'));

-- 4. Sync function. status is the source of truth when it changes; if a writer
--    only toggled `done` (the LungNote webapp checkbox path), derive status.
--    Uses NEW.* only (no nested UPDATE) so it cannot recurse.
CREATE OR REPLACE FUNCTION lungnote_todos_sync_status_done()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM NEW.status THEN
    -- status is authoritative (new row, or a status change): mirror it to done.
    NEW.done := (NEW.status IS DISTINCT FROM 'open');
  ELSIF OLD.done IS DISTINCT FROM NEW.done THEN
    -- a writer changed `done` only (e.g. webapp checkbox): infer status.
    -- done=true  -> complete (webapp "checked" = completed).
    -- done=false -> open     (can't infer cancel/delete from done=false; the
    --                          webapp's mental model is only open/done).
    IF NEW.done THEN
      NEW.status := 'complete';
    ELSE
      NEW.status := 'open';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

-- 5. Fire on any insert, and on updates that touch status or done.
DROP TRIGGER IF EXISTS lungnote_todos_sync_status_done ON lungnote_todos;
CREATE TRIGGER lungnote_todos_sync_status_done
  BEFORE INSERT OR UPDATE OF status, done ON lungnote_todos
  FOR EACH ROW
  EXECUTE FUNCTION lungnote_todos_sync_status_done();

COMMIT;

-- Post-apply verification (run manually, read-only):
--   SELECT status, done, count(*) FROM lungnote_todos GROUP BY 1,2 ORDER BY 1;
-- Expect every row: status='open'->done=f, status='complete'->done=t.

-- 20260803000000_lungnote_todos_status_rollback.sql
-- Reverses 20260803000000_lungnote_todos_status.sql.
-- Drops the trigger, function, CHECK, and the `status` column.
-- `done` is preserved throughout (never dropped) so every existing consumer
-- (webapp, session-deadline-check.py, list_todos) keeps working unchanged.
--
-- NOTE: dropping `status` collapses the complete|cancel|delete distinction
-- back to the flat boolean — that is expected for a rollback and is the only
-- data lost. The human-readable WHY reasons were also appended to the parent
-- note body (lungnote_notes.body) via append_note, so the audit trail there
-- is NOT lost.

BEGIN;

DROP TRIGGER IF EXISTS lungnote_todos_sync_status_done ON lungnote_todos;
DROP FUNCTION IF EXISTS lungnote_todos_sync_status_done();
ALTER TABLE lungnote_todos DROP CONSTRAINT IF EXISTS lungnote_todos_status_check;
ALTER TABLE lungnote_todos DROP COLUMN IF EXISTS status;

COMMIT;

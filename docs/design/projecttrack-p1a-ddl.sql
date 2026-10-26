-- Deployment reference only: do not execute against the live hub from tests.
-- The column loop runs this only when tier is absent. The constraint pair
-- runs only when pg_get_constraintdef does not match PROJECT_EVENT_KINDS.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'normal';
ALTER TABLE project_events DROP CONSTRAINT IF EXISTS project_events_kind_check;
ALTER TABLE project_events ADD CONSTRAINT project_events_kind_check CHECK (kind IN ('opened', 'stage', 'tier', 'milestone', 'blocker', 'unblocked', 'decided_for_ceo', 'ceo_go', 'spend', 'closed', 'heartbeat_rollup'));

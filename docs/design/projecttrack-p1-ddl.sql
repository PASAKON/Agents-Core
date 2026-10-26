-- ProjectTrack P1, stacked on P1a. Run with the hub migration role.
BEGIN;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'normal';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'finite' CHECK (kind IN ('finite', 'loop'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS due_set_by TEXT CHECK (due_set_by IN ('ceo', 'clevel', 'ph'));
ALTER TABLE projects ADD COLUMN IF NOT EXISTS due_first_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS cadence_h INTEGER CHECK (cadence_h > 0);
ALTER TABLE projects ADD COLUMN IF NOT EXISTS last_beat_at TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS beat_n INTEGER NOT NULL DEFAULT 0;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS blocker_ref TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS blocker_until TIMESTAMPTZ;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS next_step TEXT;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS next_owner TEXT;
ALTER TABLE milestones ADD COLUMN IF NOT EXISTS due_at TIMESTAMPTZ;
ALTER TABLE milestones ADD COLUMN IF NOT EXISTS order_id TEXT;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id TEXT;
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    words TEXT NOT NULL,
    channel TEXT NOT NULL,
    taken_by TEXT,
    taken_at TIMESTAMPTZ NOT NULL,
    project_id TEXT,
    due_at TIMESTAMPTZ,
    due_set_by TEXT CHECK (due_set_by IN ('ceo', 'clevel', 'ph')),
    closed_at TIMESTAMPTZ,
    outcome TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_closed_at ON orders(closed_at);
CREATE INDEX IF NOT EXISTS idx_orders_project_id ON orders(project_id);
ALTER TABLE project_events DROP CONSTRAINT IF EXISTS project_events_kind_check;
ALTER TABLE project_events ADD CONSTRAINT project_events_kind_check CHECK (kind IN ('opened', 'stage', 'tier', 'milestone', 'blocker', 'unblocked', 'decided_for_ceo', 'ceo_go', 'spend', 'closed', 'heartbeat_rollup', 'order', 'replan', 'beat', 'late', 'escalated', 'plan'));
GRANT SELECT, INSERT, UPDATE ON orders TO org_coo;
COMMIT;

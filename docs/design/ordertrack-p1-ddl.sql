-- OrderTrack P1-A (order O-20261127-1012-35f9). Run with the hub migration role.
BEGIN;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS title TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS lane TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS mode TEXT CHECK (mode IN ('direct', 'ph'));
ALTER TABLE orders ADD COLUMN IF NOT EXISTS ph_session TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS msg_group TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS size TEXT CHECK (size IN ('S', 'M', 'L'));
ALTER TABLE orders ADD COLUMN IF NOT EXISTS next_step TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS blocker_what TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS dropped BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS order_id TEXT;
CREATE TABLE IF NOT EXISTS order_goals (
    order_id      TEXT NOT NULL REFERENCES orders(id),
    n             INTEGER NOT NULL,
    parent_n      INTEGER,
    title         TEXT NOT NULL,
    weight        INTEGER NOT NULL DEFAULT 1 CHECK (weight > 0),
    due_at        TIMESTAMPTZ,
    done_at       TIMESTAMPTZ,
    evidence      TEXT,
    milestone_ref INTEGER,
    PRIMARY KEY (order_id, n),
    FOREIGN KEY (order_id, parent_n) REFERENCES order_goals(order_id, n),
    CHECK (parent_n IS NULL OR parent_n <> n),
    CHECK (done_at IS NULL OR (evidence IS NOT NULL AND length(btrim(evidence)) > 0))
);
GRANT SELECT, INSERT, UPDATE ON order_goals TO org_coo;
COMMIT;

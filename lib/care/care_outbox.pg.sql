-- care_outbox migration (Postgres hub). Idempotent. Mirrors lib/care/outbox.py SQLITE_SCHEMA.
-- Apply through the hub migration path; this task does NOT run it.
CREATE TABLE IF NOT EXISTS care_outbox (
  id BIGSERIAL PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  channel_basic_id TEXT NOT NULL DEFAULT '@587kfqpt',
  recipient_id TEXT NOT NULL,
  recipient_display_name TEXT NOT NULL,
  message_kind TEXT NOT NULL CHECK (message_kind IN ('care_reply','important_announcement')),
  critical BOOLEAN NOT NULL DEFAULT FALSE,
  payload_json JSONB NOT NULL,
  reply_token TEXT,
  reply_token_expires_at TIMESTAMPTZ,
  state TEXT NOT NULL DEFAULT 'queued'
    CHECK (state IN ('queued','sending','sent','deferred','dropped','failed','fallback')),
  delivery_via TEXT CHECK (delivery_via IS NULL OR delivery_via IN ('api_reply','oa_browser','api_push')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  sending_started_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS care_outbox_state_idx ON care_outbox (state, id);
CREATE TABLE IF NOT EXISTS care_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

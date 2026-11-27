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

-- P1 inbound care_queue, per-customer goal/step cases, escalations, and approved FAQ (docs/design/mooniex-care.md §6)
CREATE TABLE IF NOT EXISTS care_queue (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL UNIQUE,
  channel_basic_id TEXT NOT NULL DEFAULT '@587kfqpt',
  customer_id TEXT NOT NULL,
  customer_display_name TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL DEFAULT '',
  media_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  reply_token TEXT,
  reply_token_expires_at TIMESTAMPTZ,
  received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  state TEXT NOT NULL DEFAULT 'pending'
    CHECK (state IN ('pending','batched','answered','skipped','escalated')),
  batch_id TEXT,
  ack_outbox_id BIGINT REFERENCES care_outbox(id),
  note TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS care_queue_state_idx ON care_queue (state, id);
CREATE INDEX IF NOT EXISTS care_queue_customer_idx ON care_queue (customer_id, id);

CREATE TABLE IF NOT EXISTS care_cases (
  customer_id TEXT PRIMARY KEY,
  customer_display_name TEXT NOT NULL DEFAULT '',
  goal TEXT NOT NULL,
  current_step TEXT NOT NULL,
  step_index INTEGER NOT NULL DEFAULT 1,
  case_status TEXT NOT NULL DEFAULT 'active'
    CHECK (case_status IN ('active','completed','escalated','closed')),
  source_rule_or_card_id TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS care_escalations (
  id BIGSERIAL PRIMARY KEY,
  event_id TEXT NOT NULL,
  customer_id TEXT NOT NULL,
  customer_display_name TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL,
  reason TEXT NOT NULL,
  customer_text_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  holding_outbox_id BIGINT REFERENCES care_outbox(id),
  ranked_answers_json JSONB,
  ceo_card_id TEXT,
  ceo_choice TEXT,
  resolved_goal TEXT,
  resolved_faq_id BIGINT,
  state TEXT NOT NULL DEFAULT 'pending_coo'
    CHECK (state IN ('pending_coo','awaiting_ceo','resolved')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS care_faq (
  id BIGSERIAL PRIMARY KEY,
  rule_key TEXT NOT NULL UNIQUE,
  topic TEXT NOT NULL,
  question_pattern TEXT NOT NULL,
  approved_answer TEXT NOT NULL,
  goal_template TEXT,
  first_step_template TEXT,
  source_card_id TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- The hub Postgres role `org_coo`, held only by the COO gate (runners/coo_gate.py).
-- CEO card Q-20261013-1948-4a33 (option 1, 2026-10-13): SomPong (the COO) may create and
-- delegate its own research workers -- researcher, data_analyst, browser_operator -- and never a
-- code role. deploy/coo-gate/README.md has the whole design and the cards that install it.
--
-- Who holds this role's URL: the service org-coo-gate, as the system user `org-coo-gate`, from
-- Infisical project Org-Coo, env prod, ORG_DB_URL, read through `infisical_setup.py run` as root
-- and then setpriv. SomPong (user `sompong`) never holds it: it reaches the gate over
-- /run/org-coo-gate/gate.sock, and the gate checks the peer uid.
--
-- No password and no verifier in this file. deploy/coo-gate/org_coo_role.py runs it in one of two
-- modes (README, cards 1 and 4):
--   --grants-only  no password change: narrows the grants and installs the row guards
--   (default)      also sets a fresh password: the script hands psql only its SCRAM-SHA-256
--                  verifier (ORG_COO_VERIFIER) and prints the role URL for `infisical_setup.py put`
-- Run it as the hub owner (`org`).
--
-- What each grant is for (the SQL the gate's ops run, all through lib/db.py):
--   tasks            SELECT              db.get_task / the gate's list and wait ops, the guard below
--                    INSERT 16 columns   db.create_task (its INSERT names exactly these)
--   coo_respawn_events SELECT view    rate-limit count on coo_respawn_request and reading
--                                        coo_respawn_done in respawn_status
--   events           INSERT 5 columns    db.log_event: task_created, the two worker requests the
--                                        gate files for the root dispatcher (coo_delegate_request,
--                                        coo_close_request), coo_respawn_request (task_id NULL), and
--                                        the audit log and field notes (coo_audit, coo_field_note,
--                                        task_id NULL): write-only, org_coo cannot read them back
--   c_level_sessions SELECT 5 columns    db._require_charter, and the gate's "is this a coo
--                                        session" check
--                    UPDATE charter      the gate's set_charter op, coo rows only
--   orders           SELECT              lib/portfolio.order_close reads the row it closes (SELECT *
--                                        ... FOR UPDATE)
--                    INSERT 8 columns    order_take: the CO-<n> mirror of a CEO order SomPong relays
--                    UPDATE 2 columns    order_close: closed_at, outcome
--   project_events   INSERT 5 columns    order_close's close event, once a PH has linked the order
--                                        to a project (write-only: org_coo cannot read it back)
-- Nothing else: no UPDATE or DELETE on tasks (status changes are the root dispatcher's, through
-- its own connection), nothing on locks, letters, hosts, join_tokens, node_secrets.
--
-- Column grants cannot limit ROWS. Section 5's triggers do, for org_coo only: a task it inserts is
-- pending, owner_role 'coo', and one of the three roles (the same list as
-- lib/coo_policy.COO_WORKER_ROLES; tests/test_coo_gate.py keeps them equal); an event it writes
-- either belongs to a coo task and is one of three kinds, or is a taskless coo_respawn_request
-- whose JSON payload has keys role (in lib/coo_policy.COO_RESPAWN_ROLES), host ('contabo') and
-- by_session, or a taskless coo_audit (keys session_id, tool, input, ok) or coo_field_note (keys
-- session_id, skill, tag, text) written as actor 'coo_gate'; the only session row it may change is a
-- coo one. Every other role passes through the triggers untouched.
--
-- The CEO-order mirror (CEO 2026-10-27, CO-<n> rows of lib/portfolio): an order it inserts has an id
-- CO-<n>, taken_by 'sompong', channel 'sompong:<n>', no project and no due date; the only order it
-- may change is an open CO-<n> one, and only closed_at (set) and outcome; the only project_events
-- row it may write is the close event of a closed CO-<n> order that belongs to that project, kind
-- 'order', body op 'close', actor the COO's own label (COO#<8 hex>, tools/agent_transport).

\set ON_ERROR_STOP on

-- 1. The verifier, from the psql variable or the environment; never a literal in this file. Empty
--    means --grants-only: the password is left as it is.
\if :{?org_coo_verifier}
\else
  \set org_coo_verifier `echo "$ORG_COO_VERIFIER"`
\endif
SELECT :'org_coo_verifier' = '' AS keep_password \gset
\if :keep_password
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_coo') AS no_role \gset
\if :no_role
DO $guard$
BEGIN
  RAISE EXCEPTION 'org_coo does not exist yet: run without --grants-only to create it with a password';
END
$guard$;
\endif
\else
SELECT :'org_coo_verifier' !~ '^SCRAM-SHA-256[$][0-9]{4,7}:[A-Za-z0-9+/]{22}==[$][A-Za-z0-9+/]{43}=:[A-Za-z0-9+/]{43}=$' AS bad_verifier \gset
\if :bad_verifier
DO $guard$
BEGIN
  RAISE EXCEPTION 'org_coo_verifier (or ORG_COO_VERIFIER) is not a SCRAM-SHA-256 verifier';
END
$guard$;
\endif
\endif

-- 2. The role: login, three connections (the gate keeps one per thread, at most a few), nothing
--    that widens it. org_coo already exists on the hub (made 2026-10-01 with broad grants, and its
--    password has sat in a file SomPong can read); the default mode gives it a new password, so
--    every old copy of its URL stops working.
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_coo') AS make_role \gset
\if :make_role
CREATE ROLE org_coo LOGIN CONNECTION LIMIT 3 PASSWORD :'org_coo_verifier'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT;
\elif :keep_password
ALTER ROLE org_coo LOGIN CONNECTION LIMIT 3;
\else
ALTER ROLE org_coo LOGIN CONNECTION LIMIT 3 PASSWORD :'org_coo_verifier';
\endif
ALTER ROLE org_coo SET statement_timeout = '10s';
ALTER ROLE org_coo SET idle_in_transaction_session_timeout = '15s';

-- 3. Start from nothing, so a grant removed from this file is removed from the role.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM org_coo;
REVOKE SELECT (id, kind, payload, ts) ON events FROM org_coo;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM org_coo;
REVOKE ALL ON SCHEMA public FROM org_coo;
GRANT USAGE ON SCHEMA public TO org_coo;

-- 4. The grants.
GRANT SELECT ON tasks TO org_coo;
GRANT INSERT (id, project, role, status, title, description, parent_task, depends_on, touches,
              owner_cto, owner_role, host, dispatcher_host, runner, created_at, updated_at)
  ON tasks TO org_coo;
GRANT INSERT (task_id, actor, kind, payload, ts) ON events TO org_coo;
CREATE OR REPLACE VIEW coo_respawn_events WITH (security_barrier) AS
  SELECT id, kind, payload, ts FROM events
  WHERE kind IN ('coo_respawn_request','coo_respawn_done');
GRANT SELECT ON coo_respawn_events TO org_coo;
GRANT SELECT (role, session_id, status, host, charter), UPDATE (charter)
  ON c_level_sessions TO org_coo;
-- Read-only: the live-session list SomPong checks before any SendMessage (CEO 2026-10-13,
-- tools/live_sessions.render through the gate's live_sessions op).
GRANT SELECT (host, published_at, error) ON live_hosts TO org_coo;
-- verified (M8): the column must exist first, i.e. lib.db.init() has run on this hub.
GRANT SELECT (host, uuid, sid, role, name, address, status, pid, seen_at, verified)
  ON live_sessions TO org_coo;
-- The CEO-order mirror (CEO 2026-10-27): order_take inserts the CO-<n> row, order_close locks it
-- (SELECT * ... FOR UPDATE), sets closed_at and outcome, and writes the close event. Neither reads
-- another table (checked 2026-10-27: no projects, milestones or tasks lookup on this path). Whole-table
-- SELECT on orders because _order() reads SELECT *; the row limits are section 5's.
GRANT SELECT, INSERT (id, words, channel, taken_by, taken_at, project_id, due_at, due_set_by),
      UPDATE (closed_at, outcome) ON orders TO org_coo;
GRANT INSERT (project_id, at, kind, actor, body) ON project_events TO org_coo;

-- 5. Row guards for this role only (see the header).
CREATE OR REPLACE FUNCTION org_coo_tasks_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_coo' THEN
    RETURN NEW;
  END IF;
  IF TG_OP <> 'INSERT' THEN
    RAISE EXCEPTION 'org_coo may only insert tasks (Q-20261013-1948-4a33)';
  END IF;
  IF NEW.owner_role IS DISTINCT FROM 'coo' OR NEW.status IS DISTINCT FROM 'pending'
     OR NEW.role IS NULL
     OR NEW.role NOT IN ('researcher', 'data_analyst', 'browser_operator') THEN
    RAISE EXCEPTION 'org_coo may only create pending coo tasks for researcher, data_analyst or browser_operator (Q-20261013-1948-4a33); refused owner_role=% role=% status=%',
      NEW.owner_role, NEW.role, NEW.status;
  END IF;
  RETURN NEW;
END
$fn$;

CREATE OR REPLACE FUNCTION org_coo_events_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_coo' THEN
    RETURN NEW;
  END IF;
  IF NEW.kind = 'coo_respawn_request' THEN
    IF NEW.task_id IS NOT NULL THEN
      RAISE EXCEPTION 'org_coo coo_respawn_request must have task_id NULL';
    END IF;
    IF NEW.payload IS NULL
       OR jsonb_typeof(NEW.payload::jsonb) IS DISTINCT FROM 'object'
       OR ARRAY(SELECT k FROM jsonb_object_keys(NEW.payload::jsonb) AS k ORDER BY k)
          IS DISTINCT FROM ARRAY['by_session', 'host', 'role']
       OR jsonb_typeof(NEW.payload::jsonb -> 'role') IS DISTINCT FROM 'string'
       OR ((NEW.payload::jsonb ->> 'role') IN ('cto', 'cmo', 'cgo', 'cfo')) IS DISTINCT FROM TRUE
       OR jsonb_typeof(NEW.payload::jsonb -> 'host') IS DISTINCT FROM 'string'
       OR ((NEW.payload::jsonb ->> 'host') = 'contabo') IS DISTINCT FROM TRUE
       OR jsonb_typeof(NEW.payload::jsonb -> 'by_session') IS DISTINCT FROM 'string'
       OR COALESCE(NEW.payload::jsonb ->> 'by_session', '') = '' THEN
      RAISE EXCEPTION 'org_coo coo_respawn_request payload must have keys role (cto/cmo/cgo/cfo), host (contabo), by_session';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.kind = 'coo_audit' THEN
    IF NEW.task_id IS NOT NULL OR NEW.actor IS DISTINCT FROM 'coo_gate' THEN
      RAISE EXCEPTION 'org_coo coo_audit must have task_id NULL and actor coo_gate';
    END IF;
    IF NEW.payload IS NULL
       OR jsonb_typeof(NEW.payload::jsonb) IS DISTINCT FROM 'object'
       OR ARRAY(SELECT k FROM jsonb_object_keys(NEW.payload::jsonb) AS k ORDER BY k)
          IS DISTINCT FROM ARRAY['input', 'ok', 'session_id', 'tool']
       OR jsonb_typeof(NEW.payload::jsonb -> 'session_id') IS DISTINCT FROM 'string'
       OR COALESCE(length(NEW.payload::jsonb ->> 'session_id'), 0) NOT BETWEEN 1 AND 64
       OR jsonb_typeof(NEW.payload::jsonb -> 'tool') IS DISTINCT FROM 'string'
       OR COALESCE(length(NEW.payload::jsonb ->> 'tool'), 0) NOT BETWEEN 1 AND 100
       OR jsonb_typeof(NEW.payload::jsonb -> 'input') IS DISTINCT FROM 'string'
       OR COALESCE(length(NEW.payload::jsonb ->> 'input'), 2001) > 2000
       OR jsonb_typeof(NEW.payload::jsonb -> 'ok') IS DISTINCT FROM 'boolean' THEN
      RAISE EXCEPTION 'org_coo coo_audit payload must have keys session_id (1-64 chars), tool (1-100 chars), input (text, at most 2000 chars), ok (boolean)';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.kind = 'coo_field_note' THEN
    IF NEW.task_id IS NOT NULL OR NEW.actor IS DISTINCT FROM 'coo_gate' THEN
      RAISE EXCEPTION 'org_coo coo_field_note must have task_id NULL and actor coo_gate';
    END IF;
    IF NEW.payload IS NULL
       OR jsonb_typeof(NEW.payload::jsonb) IS DISTINCT FROM 'object'
       OR ARRAY(SELECT k FROM jsonb_object_keys(NEW.payload::jsonb) AS k ORDER BY k)
          IS DISTINCT FROM ARRAY['session_id', 'skill', 'tag', 'text']
       OR jsonb_typeof(NEW.payload::jsonb -> 'session_id') IS DISTINCT FROM 'string'
       OR COALESCE(length(NEW.payload::jsonb ->> 'session_id'), 0) NOT BETWEEN 1 AND 64
       OR jsonb_typeof(NEW.payload::jsonb -> 'skill') IS DISTINCT FROM 'string'
       OR ((NEW.payload::jsonb ->> 'skill') ~ '^[A-Za-z0-9_.-]{3,80}$') IS DISTINCT FROM TRUE
       OR jsonb_typeof(NEW.payload::jsonb -> 'tag') IS DISTINCT FROM 'string'
       OR ((NEW.payload::jsonb ->> 'tag') IN ('MISSING', 'WRONG', 'COSTLY', 'CONFIRMED')) IS DISTINCT FROM TRUE
       OR jsonb_typeof(NEW.payload::jsonb -> 'text') IS DISTINCT FROM 'string'
       OR COALESCE(length(NEW.payload::jsonb ->> 'text'), 0) NOT BETWEEN 1 AND 600
       OR COALESCE(position(E'\n' IN (NEW.payload::jsonb ->> 'text')), 1) > 0
       OR COALESCE(position(E'\r' IN (NEW.payload::jsonb ->> 'text')), 1) > 0 THEN
      RAISE EXCEPTION 'org_coo coo_field_note payload must have keys session_id (1-64 chars), skill (A-Za-z0-9_.- 3-80 chars), tag (MISSING/WRONG/COSTLY/CONFIRMED), text (one line, 1-600 chars)';
    END IF;
    RETURN NEW;
  END IF;
  IF NEW.kind NOT IN ('task_created', 'coo_delegate_request', 'coo_close_request') THEN
    RAISE EXCEPTION 'org_coo may not write event kind %', NEW.kind;
  END IF;
  IF NEW.task_id IS NULL OR NOT EXISTS (
       SELECT 1 FROM public.tasks t WHERE t.id = NEW.task_id AND t.owner_role = 'coo') THEN
    RAISE EXCEPTION 'org_coo may only write events of coo tasks';
  END IF;
  RETURN NEW;
END
$fn$;

CREATE OR REPLACE FUNCTION org_coo_sessions_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_coo' THEN
    RETURN NEW;
  END IF;
  IF OLD.role IS DISTINCT FROM 'coo' THEN
    RAISE EXCEPTION 'org_coo may only set the charter of a coo session';
  END IF;
  RETURN NEW;
END
$fn$;

-- Every test below is written to fail closed: a NULL operand makes a check "not true", never "passed".
CREATE OR REPLACE FUNCTION org_coo_orders_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_coo' THEN
    RETURN NEW;
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF (NEW.id ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE
       OR NEW.taken_by IS DISTINCT FROM 'sompong'
       OR NEW.channel IS DISTINCT FROM ('sompong:' || substr(NEW.id, 4))
       OR NEW.project_id IS NOT NULL
       OR NEW.due_at IS NOT NULL THEN
      RAISE EXCEPTION 'org_coo may only insert an order CO-<n> taken_by sompong, channel sompong:<n>, with no project and no due date; refused id=% taken_by=% channel=%',
        NEW.id, NEW.taken_by, NEW.channel;
    END IF;
    RETURN NEW;
  END IF;
  -- UPDATE: an open CO-<n> order gets closed_at and outcome, nothing else. to_jsonb(row) covers
  -- every column, so one added to orders later is held fixed too.
  IF (OLD.id ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE OR OLD.closed_at IS NOT NULL THEN
    RAISE EXCEPTION 'org_coo may only close an open CO-<n> order; refused id=%', OLD.id;
  END IF;
  IF NEW.closed_at IS NULL
     OR (to_jsonb(NEW) - 'closed_at' - 'outcome') IS DISTINCT FROM (to_jsonb(OLD) - 'closed_at' - 'outcome') THEN
    RAISE EXCEPTION 'org_coo may only set closed_at and outcome of an order, and closed_at must be set; refused id=%', OLD.id;
  END IF;
  RETURN NEW;
END
$fn$;

CREATE OR REPLACE FUNCTION org_coo_project_events_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_coo' THEN
    RETURN NEW;
  END IF;
  IF NEW.kind IS DISTINCT FROM 'order'
     OR (NEW.body ->> 'op') IS DISTINCT FROM 'close'
     OR ((NEW.body ->> 'id') ~ '^CO-[0-9]+$') IS DISTINCT FROM TRUE
     OR (NEW.actor ~ '^COO#[0-9a-f]{8}$') IS DISTINCT FROM TRUE THEN
    RAISE EXCEPTION 'org_coo may only write the close event (kind order, op close, id CO-<n>) as the COO (COO#<8 hex>); refused kind=% actor=%',
      NEW.kind, NEW.actor;
  END IF;
  -- order_close updates the order before it writes the event, in one transaction, so the row
  -- is already closed here.
  IF NOT EXISTS (SELECT 1 FROM public.orders o
                  WHERE o.id = (NEW.body ->> 'id') AND o.project_id = NEW.project_id
                    AND o.closed_at IS NOT NULL) THEN
    RAISE EXCEPTION 'org_coo may only mirror the close of a closed CO-<n> order that belongs to project %', NEW.project_id;
  END IF;
  RETURN NEW;
END
$fn$;

DROP TRIGGER IF EXISTS org_coo_guard ON tasks;
-- INSERT OR UPDATE only: a BEFORE DELETE trigger that returns NEW (NULL on a delete) would cancel
-- every role's deletes. org_coo holds no DELETE grant, and section 6 proves it.
CREATE TRIGGER org_coo_guard BEFORE INSERT OR UPDATE ON tasks
  FOR EACH ROW EXECUTE FUNCTION org_coo_tasks_guard();
DROP TRIGGER IF EXISTS org_coo_guard ON events;
CREATE TRIGGER org_coo_guard BEFORE INSERT ON events
  FOR EACH ROW EXECUTE FUNCTION org_coo_events_guard();
DROP TRIGGER IF EXISTS org_coo_guard ON c_level_sessions;
CREATE TRIGGER org_coo_guard BEFORE UPDATE ON c_level_sessions
  FOR EACH ROW EXECUTE FUNCTION org_coo_sessions_guard();
-- INSERT OR UPDATE only, for the reason given at the tasks trigger above.
DROP TRIGGER IF EXISTS org_coo_guard ON orders;
CREATE TRIGGER org_coo_guard BEFORE INSERT OR UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION org_coo_orders_guard();
DROP TRIGGER IF EXISTS org_coo_guard ON project_events;
CREATE TRIGGER org_coo_guard BEFORE INSERT ON project_events
  FOR EACH ROW EXECUTE FUNCTION org_coo_project_events_guard();

-- 6. Prove it. The role holds exactly the INSERT/UPDATE privileges of section 4, SELECT only on
--    tasks, coo_respawn_events, c_level_sessions, live_hosts, live_sessions and orders, nothing destructive, or this run fails.
DO $check$
DECLARE
  have text;
  forbidden_kind text;
  proof_kind text;
  proof_actor text;
  proof_payload text;
  proof_accept boolean;
  accepted boolean;
  switched boolean;
  want text := 'c_level_sessions.charter:UPDATE events.actor:INSERT events.kind:INSERT '
    'events.payload:INSERT events.task_id:INSERT events.ts:INSERT '
    'orders.channel:INSERT orders.closed_at:UPDATE orders.due_at:INSERT orders.due_set_by:INSERT '
    'orders.id:INSERT orders.outcome:UPDATE orders.project_id:INSERT orders.taken_at:INSERT '
    'orders.taken_by:INSERT orders.words:INSERT '
    'project_events.actor:INSERT project_events.at:INSERT project_events.body:INSERT '
    'project_events.kind:INSERT project_events.project_id:INSERT '
    'tasks.created_at:INSERT '
    'tasks.depends_on:INSERT tasks.description:INSERT tasks.dispatcher_host:INSERT '
    'tasks.host:INSERT tasks.id:INSERT tasks.owner_cto:INSERT tasks.owner_role:INSERT '
    'tasks.parent_task:INSERT tasks.project:INSERT tasks.role:INSERT tasks.runner:INSERT '
    'tasks.status:INSERT tasks.title:INSERT tasks.touches:INSERT tasks.updated_at:INSERT';
BEGIN
  FOREACH forbidden_kind IN ARRAY ARRAY['coo_respawn_done', 'coo_respawn_request'] LOOP
    accepted := false;
    switched := false;
    BEGIN
      SET LOCAL ROLE org_coo;
      -- Plain variables survive the subtransaction rollback, so the handler can tell a failed
      -- role switch (no proof) from a refused INSERT (proof).
      switched := current_user = 'org_coo';
      IF NOT switched THEN
        RAISE EXCEPTION USING ERRCODE = 'ZX002', MESSAGE = 'proof could not act as org_coo';
      END IF;
      INSERT INTO public.events (task_id, actor, kind, payload, ts)
        VALUES (NULL, 'coo_gate', forbidden_kind,
                '{"role":null,"host":"contabo","by_session":"proof"}', now());
      -- Force rollback even if the forbidden insertion unexpectedly succeeds.
      RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'forbidden insert accepted';
    EXCEPTION
      WHEN SQLSTATE 'ZX001' THEN accepted := true;
      -- Only the guard trigger's RAISE or a missing INSERT privilege, raised after the switch
      -- to org_coo, counts as refused. Anything else (the switch itself denied, a missing
      -- table) is not proof, so it fails this run.
      WHEN raise_exception OR insufficient_privilege THEN
        IF NOT switched THEN
          RAISE;
        END IF;
    END;
    IF accepted THEN
      RAISE EXCEPTION 'org_coo accepted forbidden insert: %', forbidden_kind;
    END IF;
  END LOOP;
  -- The audit log and field notes are the two taskless kinds org_coo writes with a payload of its
  -- own, so prove both directions: a well-formed row is accepted; the same row under another actor,
  -- and a respawn-shaped payload under either kind, are refused. Each insert runs in a
  -- subtransaction that is rolled back.
  FOR proof_kind, proof_actor, proof_payload, proof_accept IN SELECT * FROM (VALUES
      ('coo_audit', 'coo_gate',
       '{"session_id":"proof","tool":"Bash","input":"{}","ok":true}', true),
      ('coo_field_note', 'coo_gate',
       '{"session_id":"proof","skill":"ALL_Rules_Approvals","tag":"WRONG","text":"proof"}', true),
      ('coo_audit', 'someone_else',
       '{"session_id":"proof","tool":"Bash","input":"{}","ok":true}', false),
      ('coo_field_note', 'someone_else',
       '{"session_id":"proof","skill":"ALL_Rules_Approvals","tag":"WRONG","text":"proof"}', false),
      ('coo_audit', 'coo_gate', '{"role":null,"host":"contabo","by_session":"proof"}', false),
      ('coo_field_note', 'coo_gate', '{"role":null,"host":"contabo","by_session":"proof"}', false)
    ) AS v(kind, actor, payload, accept) LOOP
    accepted := false;
    switched := false;
    BEGIN
      SET LOCAL ROLE org_coo;
      switched := current_user = 'org_coo';
      IF NOT switched THEN
        RAISE EXCEPTION USING ERRCODE = 'ZX002', MESSAGE = 'proof could not act as org_coo';
      END IF;
      INSERT INTO public.events (task_id, actor, kind, payload, ts)
        VALUES (NULL, proof_actor, proof_kind, proof_payload, now());
      RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'insert accepted';
    EXCEPTION
      WHEN SQLSTATE 'ZX001' THEN accepted := true;
      WHEN raise_exception OR insufficient_privilege THEN
        IF NOT switched THEN
          RAISE;
        END IF;
    END;
    IF accepted IS DISTINCT FROM proof_accept THEN
      RAISE EXCEPTION 'org_coo % insert as actor % was %', proof_kind, proof_actor,
        CASE WHEN accepted THEN 'accepted, expected refused' ELSE 'refused, expected accepted' END;
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_coo' AND (
       rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls
       OR NOT rolcanlogin OR rolconnlimit <> 3)) THEN
    RAISE EXCEPTION 'org_coo has a role attribute it must not have';
  END IF;

  SELECT string_agg(format('%s.%s:%s', c.relname, a.attname, p.priv), ' '
                    ORDER BY c.relname COLLATE "C", a.attname COLLATE "C", p.priv COLLATE "C")
    INTO have
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
    CROSS JOIN (VALUES ('INSERT'), ('UPDATE'), ('REFERENCES')) AS p(priv)
   WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
     AND has_column_privilege('org_coo', c.oid, a.attnum, p.priv);
  IF have IS DISTINCT FROM want THEN
    RAISE EXCEPTION 'org_coo INSERT/UPDATE privileges differ from this file. have: %', have;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                AND c.relname NOT IN ('tasks', 'coo_respawn_events', 'c_level_sessions', 'live_hosts', 'live_sessions', 'orders')
                AND has_any_column_privilege('org_coo', c.oid, 'SELECT')) THEN
    RAISE EXCEPTION 'org_coo can read a table outside section 4';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                AND has_table_privilege('org_coo', c.oid, 'DELETE,TRUNCATE,TRIGGER')) THEN
    RAISE EXCEPTION 'org_coo holds DELETE, TRUNCATE or TRIGGER somewhere';
  END IF;
  IF has_schema_privilege('org_coo', 'public', 'CREATE') THEN
    RAISE EXCEPTION 'org_coo may create objects in schema public';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind = 'S'
                AND CASE WHEN c.relkind = 'S'
                         THEN has_sequence_privilege('org_coo', c.oid, 'USAGE,SELECT,UPDATE')
                    END) THEN
    RAISE EXCEPTION 'org_coo holds a sequence privilege';
  END IF;
END
$check$;

-- The CEO-order mirror: prove the row guards of orders and project_events, not only their grants.
-- Each case runs in a subtransaction that is rolled back, so no proof row stays. `owner_sql` runs
-- first as the hub owner (a proof project, a linked or closed order, and in case H a temporary
-- GRANT, so that the trigger and not the column grant is what refuses); the steps then run as
-- org_coo, the way lib/portfolio runs them. A refusal counts only on the LAST step: a setup step
-- that fails is a broken proof and fails this run, as does a step the guard should have refused.
DO $orders_proof$
DECLARE
  proof_name text;
  proof_accept boolean;
  proof_owner text;
  proof_steps text[];
  proof_last int;
  proof_step int;
  stmt text;
  accepted boolean;
  switched boolean;
BEGIN
  FOR proof_name, proof_accept, proof_owner, proof_steps IN
    SELECT v.name, v.accept, v.owner_sql, ARRAY[v.s1, v.s2, v.s3]
      FROM (VALUES
    -- accepted: order_take, then order_close with no project (no event), as org_coo runs them
    ('A valid CO order, taken and closed', true, NULL::text,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, due_at, due_set_by)
        VALUES ('CO-900000001', 'proof', 'sompong:900000001', 'sompong', now(), NULL, NULL, NULL)$q$,
     $q$SELECT * FROM public.orders WHERE id = 'CO-900000001' FOR UPDATE$q$,
     $q$UPDATE public.orders SET closed_at = now(), outcome = 'done: proof' WHERE id = 'CO-900000001'$q$),
    -- accepted: a PH linked the order to a project; order_close then writes the close event
    ('A CO order of a project, closed with its event', true,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id)
        VALUES ('CO-900000002', 'proof', 'sompong:900000002', 'sompong', now(), 'coo-proof')$q$,
     $q$UPDATE public.orders SET closed_at = now(), outcome = 'done: proof' WHERE id = 'CO-900000002'$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'order', 'COO#0badc0de',
                '{"op":"close","id":"CO-900000002","outcome":"done: proof"}'::jsonb)$q$, NULL),
    -- refused: orders, insert
    -- the channel is what the guard derives from the id, so only the id check can refuse this one
    ('An O- id', false, NULL::text,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('O-20261027-0000-ab12', 'proof', 'sompong:0261027-0000-ab12', 'sompong', now())$q$, NULL, NULL),
    ('A taken_by other than sompong', false, NULL::text,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('CO-900000003', 'proof', 'sompong:900000003', 'someone_else', now())$q$, NULL, NULL),
    ('A channel that is not the id', false, NULL::text,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('CO-900000004', 'proof', 'sompong:1', 'sompong', now())$q$, NULL, NULL),
    ('A due date on insert', false, NULL::text,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at, due_at)
        VALUES ('CO-900000005', 'proof', 'sompong:900000005', 'sompong', now(), now())$q$, NULL, NULL),
    ('A project on insert', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo')$q$,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id)
        VALUES ('CO-900000006', 'proof', 'sompong:900000006', 'sompong', now(), 'coo-proof')$q$, NULL, NULL),
    -- refused: orders, update
    ('An update of a closed CO order', false,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at, closed_at, outcome)
        VALUES ('CO-900000007', 'proof', 'sompong:900000007', 'sompong', now(), now(), 'done: proof')$q$,
     $q$UPDATE public.orders SET outcome = 'changed' WHERE id = 'CO-900000007'$q$, NULL, NULL),
    ('An update that changes words (UPDATE (words) granted for this case only)', false,
     $q$GRANT UPDATE (words) ON public.orders TO org_coo;
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('CO-900000008', 'proof', 'sompong:900000008', 'sompong', now())$q$,
     $q$UPDATE public.orders SET words = 'changed', closed_at = now(), outcome = 'done: proof'
        WHERE id = 'CO-900000008'$q$, NULL, NULL),
    ('An update that does not set closed_at', false,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('CO-900000009', 'proof', 'sompong:900000009', 'sompong', now())$q$,
     $q$UPDATE public.orders SET outcome = 'done: proof' WHERE id = 'CO-900000009'$q$, NULL, NULL),
    ('An update of an order that is not CO-<n>', false,
     $q$INSERT INTO public.orders (id, words, channel, taken_by, taken_at)
        VALUES ('O-20261027-0000-ab13', 'proof', 'chat:cto-abc', 'someone_else', now())$q$,
     $q$UPDATE public.orders SET closed_at = now(), outcome = 'done: proof'
        WHERE id = 'O-20261027-0000-ab13'$q$, NULL, NULL),
    -- refused: project_events
    ('A project_events row of another kind', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome)
        VALUES ('CO-900000010', 'proof', 'sompong:900000010', 'sompong', now(), 'coo-proof', now(), 'done: proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'stage', 'COO#0badc0de',
                '{"op":"close","id":"CO-900000010","outcome":"done: proof"}'::jsonb)$q$, NULL, NULL),
    ('A close event under another actor', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome)
        VALUES ('CO-900000011', 'proof', 'sompong:900000011', 'sompong', now(), 'coo-proof', now(), 'done: proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'order', 'CTO#0badc0de',
                '{"op":"close","id":"CO-900000011","outcome":"done: proof"}'::jsonb)$q$, NULL, NULL),
    ('A take event', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome)
        VALUES ('CO-900000012', 'proof', 'sompong:900000012', 'sompong', now(), 'coo-proof', now(), 'done: proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'order', 'COO#0badc0de',
                '{"op":"take","id":"CO-900000012"}'::jsonb)$q$, NULL, NULL),
    ('A close event for an order that is still open', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id)
        VALUES ('CO-900000013', 'proof', 'sompong:900000013', 'sompong', now(), 'coo-proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'order', 'COO#0badc0de',
                '{"op":"close","id":"CO-900000013","outcome":"done: proof"}'::jsonb)$q$, NULL, NULL),
    ('A close event for another project''s order', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo'), ('coo-proof-2', 'coo-proof-2', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome)
        VALUES ('CO-900000014', 'proof', 'sompong:900000014', 'sompong', now(), 'coo-proof', now(), 'done: proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof-2', now(), 'order', 'COO#0badc0de',
                '{"op":"close","id":"CO-900000014","outcome":"done: proof"}'::jsonb)$q$, NULL, NULL),
    ('A close event for an order that is not CO-<n>', false,
     $q$INSERT INTO public.projects (id, name, lane) VALUES ('coo-proof', 'coo-proof', 'coo');
        INSERT INTO public.orders (id, words, channel, taken_by, taken_at, project_id, closed_at, outcome)
        VALUES ('O-20261027-0000-ab14', 'proof', 'chat:cto-abc', 'someone_else', now(), 'coo-proof', now(), 'done: proof')$q$,
     $q$INSERT INTO public.project_events (project_id, at, kind, actor, body)
        VALUES ('coo-proof', now(), 'order', 'COO#0badc0de',
                '{"op":"close","id":"O-20261027-0000-ab14","outcome":"done: proof"}'::jsonb)$q$, NULL, NULL)
      ) AS v(name, accept, owner_sql, s1, s2, s3)
  LOOP
    accepted := false;
    switched := false;
    proof_step := 0;
    proof_last := cardinality(array_remove(proof_steps, NULL));
    BEGIN
      IF proof_owner IS NOT NULL THEN
        EXECUTE proof_owner;
      END IF;
      SET LOCAL ROLE org_coo;
      switched := current_user = 'org_coo';
      IF NOT switched THEN
        RAISE EXCEPTION USING ERRCODE = 'ZX002', MESSAGE = 'proof could not act as org_coo';
      END IF;
      FOREACH stmt IN ARRAY array_remove(proof_steps, NULL) LOOP
        proof_step := proof_step + 1;
        EXECUTE stmt;
      END LOOP;
      RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'every step accepted';
    EXCEPTION
      WHEN SQLSTATE 'ZX001' THEN accepted := true;
      WHEN raise_exception OR insufficient_privilege THEN
        IF NOT switched OR proof_step < proof_last THEN
          RAISE;
        END IF;
    END;
    IF accepted IS DISTINCT FROM proof_accept THEN
      RAISE EXCEPTION 'org_coo order proof "%" was %', proof_name,
        CASE WHEN accepted THEN 'accepted, expected refused' ELSE 'refused, expected accepted' END;
    END IF;
  END LOOP;
END
$orders_proof$;

\echo org_coo: role, grants and row guards are in place and verified

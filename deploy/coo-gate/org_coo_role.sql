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
--                                        coo_close_request), and coo_respawn_request (task_id NULL)
--   c_level_sessions SELECT 5 columns    db._require_charter, and the gate's "is this a coo
--                                        session" check
--                    UPDATE charter      the gate's set_charter op, coo rows only
-- Nothing else: no UPDATE or DELETE on tasks (status changes are the root dispatcher's, through
-- its own connection), nothing on locks, letters, hosts, join_tokens, node_secrets.
--
-- Column grants cannot limit ROWS. Section 5's triggers do, for org_coo only: a task it inserts is
-- pending, owner_role 'coo', and one of the three roles (the same list as
-- lib/coo_policy.COO_WORKER_ROLES; tests/test_coo_gate.py keeps them equal); an event it writes
-- either belongs to a coo task and is one of three kinds, or is a taskless coo_respawn_request
-- whose JSON payload has keys role (in lib/coo_policy.COO_RESPAWN_ROLES), host ('contabo') and
-- by_session; the only session row it may change is a coo one. Every other role passes through the
-- triggers untouched.

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
       OR (NEW.payload::jsonb ->> 'role') NOT IN ('cto', 'cmo', 'cgo', 'cfo')
       OR (NEW.payload::jsonb ->> 'host') IS DISTINCT FROM 'contabo'
       OR COALESCE(NEW.payload::jsonb ->> 'by_session', '') = '' THEN
      RAISE EXCEPTION 'org_coo coo_respawn_request payload must have keys role (cto/cmo/cgo/cfo), host (contabo), by_session';
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

-- 6. Prove it. The role holds exactly the INSERT/UPDATE privileges of section 4, SELECT only on
--    tasks, coo_respawn_events, c_level_sessions, live_hosts and live_sessions, nothing destructive, or this run fails.
DO $check$
DECLARE
  have text;
  want text := 'c_level_sessions.charter:UPDATE events.actor:INSERT events.kind:INSERT '
    'events.payload:INSERT events.task_id:INSERT events.ts:INSERT tasks.created_at:INSERT '
    'tasks.depends_on:INSERT tasks.description:INSERT tasks.dispatcher_host:INSERT '
    'tasks.host:INSERT tasks.id:INSERT tasks.owner_cto:INSERT tasks.owner_role:INSERT '
    'tasks.parent_task:INSERT tasks.project:INSERT tasks.role:INSERT tasks.runner:INSERT '
    'tasks.status:INSERT tasks.title:INSERT tasks.touches:INSERT tasks.updated_at:INSERT';
BEGIN
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
                AND c.relname NOT IN ('tasks', 'coo_respawn_events', 'c_level_sessions', 'live_hosts', 'live_sessions')
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

\echo org_coo: role, grants and row guards are in place and verified

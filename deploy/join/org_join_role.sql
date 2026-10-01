-- The hub Postgres role for the public join endpoint (Org Mesh W4.6c, review task-79219f24 F3).
--
-- tools/join_api.py is reachable from the internet. It used to connect as the full hub role
-- `org`, so one bug in it was a bug against every table of the hub. It now connects as
-- `org_join`, which can do exactly what the accept and sealed paths do and nothing else.
--
-- Run as the database OWNER (`org`; it needs CREATEROLE to make the role, otherwise run the file
-- as `postgres`), once per hub, and again whenever this file changes. It is idempotent: every run
-- leaves the role with exactly the grants below, no more, no fewer. The password is NOT in this
-- file. Pass it from Infisical at run time, through the environment so it never reaches argv:
--
--   ORG_JOIN_PASSWORD="$pw" psql -v ON_ERROR_STOP=1 -X -f deploy/join/org_join_role.sql "$ADMIN_DSN"
--
-- (or as the psql variable org_join_password, -v org_join_password=...; the environment is the
-- safer one, `ps` shows argv). Running it again sets the password to the one given: pass the
-- current one to re-apply grants, a new one to rotate. deploy/join/README.md has the whole
-- recipe, including how the DSN reaches Infisical.
--
-- What each grant is for (derived from the SQL the two paths run; the README lists it too):
--   join_tokens  SELECT token_hash, host, used_at, expires_at   consume, diagnose, sealed check
--                UPDATE used_at                                 consume the token, one statement
--   hosts        INSERT the columns of the register             hq_join._INSERT_HOST_SQL
--                UPDATE the columns of the rejoin (a `left` row) hq_join._REJOIN_HOST_SQL
--                SELECT host, status                            ON CONFLICT(host), WHERE, RETURNING, sealed
--   node_secrets SELECT host, ciphertext, fetched_at, revoked_at  hq_join.sealed_ciphertext
--                UPDATE fetched_at                              stamp the first fetch
--   events       INSERT task_id, actor, kind, payload, ts       db.log_event (join_accept, node_sealed_fetch)
--
-- Column grants cannot limit ROWS. Left alone, the holder of this role's DSN could run
-- UPDATE hosts SET approved_at = now() (approving their own node: the W4.6a F1 gate) or rewrite
-- the key of an approved host. The two triggers in section 5 close that: for this role only, a
-- hosts row may be created as pending_identity with no approval, or taken over when it is
-- `left`, and an event may only be one of the two kinds the endpoint writes. They do nothing for
-- any other role. Section 5 is the one part that may be dropped without losing the role.

\set ON_ERROR_STOP on

-- 1. The password, from the psql variable or the environment; never a literal in this file.
\if :{?org_join_password}
\else
  \set org_join_password `echo "$ORG_JOIN_PASSWORD"`
\endif
SELECT length(:'org_join_password') < 24 AS weak_password \gset
\if :weak_password
DO $guard$
BEGIN
  RAISE EXCEPTION 'org_join_password (or ORG_JOIN_PASSWORD) is missing or shorter than 24 characters';
END
$guard$;
\endif

-- 2. The role: login, five connections, no attribute that widens it.
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_join') AS make_role \gset
\if :make_role
CREATE ROLE org_join LOGIN CONNECTION LIMIT 5 PASSWORD :'org_join_password'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT;
\else
-- No NO... attributes here: on Postgres 16 a role that is not itself a superuser may not even
-- restate them. The check in section 6 fails the run if any of them has drifted.
ALTER ROLE org_join LOGIN CONNECTION LIMIT 5 PASSWORD :'org_join_password';
\endif
-- A runaway statement or a stuck transaction must not hold one of the five connections.
ALTER ROLE org_join SET statement_timeout = '10s';
ALTER ROLE org_join SET idle_in_transaction_session_timeout = '15s';

-- 3. Start from nothing, so a grant removed from this file is removed from the role.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM org_join;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM org_join;
REVOKE ALL ON SCHEMA public FROM org_join;
GRANT USAGE ON SCHEMA public TO org_join;

-- 4. The grants.
GRANT SELECT (token_hash, host, used_at, expires_at), UPDATE (used_at)
  ON join_tokens TO org_join;

GRANT SELECT (host, status)
  ON hosts TO org_join;
GRANT INSERT (host, os, hq_root, agents_root, provides, max_workers, status, pubkey,
              config_json, updated_at, deploy_pubkey)
  ON hosts TO org_join;
GRANT UPDATE (os, hq_root, agents_root, provides, max_workers, status, pubkey, config_json,
              deploy_pubkey, approved_at, updated_at, probed_at, free_gb, ram_free_gb, running,
              version, cpus, load_per_core, runners)
  ON hosts TO org_join;

GRANT SELECT (host, ciphertext, fetched_at, revoked_at), UPDATE (fetched_at)
  ON node_secrets TO org_join;

GRANT INSERT (task_id, actor, kind, payload, ts)
  ON events TO org_join;

-- 5. Row guards for this role only (see the header). Every other role passes through untouched.
CREATE OR REPLACE FUNCTION org_join_hosts_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_join' THEN
    RETURN NEW;
  END IF;
  IF NEW.status IS DISTINCT FROM 'pending_identity' OR NEW.approved_at IS NOT NULL THEN
    RAISE EXCEPTION 'org_join may only register a host as pending_identity, unapproved';
  END IF;
  IF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM 'left' THEN
    RAISE EXCEPTION 'org_join may only take over a host that has left';
  END IF;
  RETURN NEW;
END
$fn$;

CREATE OR REPLACE FUNCTION org_join_events_guard() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $fn$
BEGIN
  IF current_user <> 'org_join' THEN
    RETURN NEW;
  END IF;
  IF NEW.task_id IS NOT NULL OR NEW.actor IS DISTINCT FROM 'hq_join'
     OR NEW.kind NOT IN ('join_accept', 'node_sealed_fetch') THEN
    RAISE EXCEPTION 'org_join may only write the join_accept and node_sealed_fetch events';
  END IF;
  RETURN NEW;
END
$fn$;

DROP TRIGGER IF EXISTS org_join_guard ON hosts;
CREATE TRIGGER org_join_guard BEFORE INSERT OR UPDATE ON hosts
  FOR EACH ROW EXECUTE FUNCTION org_join_hosts_guard();
DROP TRIGGER IF EXISTS org_join_guard ON events;
CREATE TRIGGER org_join_guard BEFORE INSERT ON events
  FOR EACH ROW EXECUTE FUNCTION org_join_events_guard();

-- 6. Prove it. The role holds exactly the privileges of section 4 and no others, or this run
--    fails (and the script stops: ON_ERROR_STOP). Nothing here prints a password.
DO $check$
DECLARE
  have text;
  want text := 'events.actor:INSERT events.kind:INSERT events.payload:INSERT events.task_id:INSERT '
    'events.ts:INSERT '
    'hosts.agents_root:INSERT hosts.agents_root:UPDATE hosts.approved_at:UPDATE '
    'hosts.config_json:INSERT hosts.config_json:UPDATE hosts.cpus:UPDATE '
    'hosts.deploy_pubkey:INSERT hosts.deploy_pubkey:UPDATE hosts.free_gb:UPDATE '
    'hosts.host:INSERT hosts.host:SELECT hosts.hq_root:INSERT hosts.hq_root:UPDATE '
    'hosts.load_per_core:UPDATE hosts.max_workers:INSERT hosts.max_workers:UPDATE '
    'hosts.os:INSERT hosts.os:UPDATE hosts.probed_at:UPDATE hosts.provides:INSERT '
    'hosts.provides:UPDATE hosts.pubkey:INSERT hosts.pubkey:UPDATE hosts.ram_free_gb:UPDATE '
    'hosts.runners:UPDATE hosts.running:UPDATE hosts.status:INSERT hosts.status:SELECT '
    'hosts.status:UPDATE hosts.updated_at:INSERT hosts.updated_at:UPDATE hosts.version:UPDATE '
    'join_tokens.expires_at:SELECT join_tokens.host:SELECT join_tokens.token_hash:SELECT '
    'join_tokens.used_at:SELECT join_tokens.used_at:UPDATE '
    'node_secrets.ciphertext:SELECT node_secrets.fetched_at:SELECT node_secrets.fetched_at:UPDATE '
    'node_secrets.host:SELECT node_secrets.revoked_at:SELECT';
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_join' AND (
       rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls
       OR NOT rolcanlogin OR rolconnlimit <> 5)) THEN
    RAISE EXCEPTION 'org_join has a role attribute it must not have';
  END IF;

  SELECT string_agg(format('%s.%s:%s', c.relname, a.attname, p.priv), ' '
                    ORDER BY c.relname COLLATE "C", a.attname COLLATE "C", p.priv COLLATE "C")
    INTO have
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
    CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')) AS p(priv)
   WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
     AND has_column_privilege('org_join', c.oid, a.attnum, p.priv);
  IF have IS DISTINCT FROM want THEN
    RAISE EXCEPTION 'org_join column privileges differ from this file. have: %', have;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                AND has_table_privilege('org_join', c.oid, 'DELETE,TRUNCATE,TRIGGER')) THEN
    RAISE EXCEPTION 'org_join can delete, truncate or add triggers somewhere';
  END IF;
  IF has_schema_privilege('org_join', 'public', 'CREATE') THEN
    RAISE EXCEPTION 'org_join can create objects in schema public (PUBLIC holds CREATE there)';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind = 'S'
                AND CASE WHEN c.relkind = 'S'   -- the planner may evaluate this on a non-sequence
                         THEN has_sequence_privilege('org_join', c.oid, 'USAGE,SELECT,UPDATE')
                    END) THEN
    RAISE EXCEPTION 'org_join holds a privilege on a sequence';
  END IF;
END
$check$;

\echo org_join: role and grants are in place and verified

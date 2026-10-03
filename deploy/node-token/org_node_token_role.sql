-- The hub Postgres role for the node-token service (Org Mesh W4.2b, CEO ruling 2026-10-03).
--
-- tools/node_token_api.py holds the Claude token in memory and hands it, sealed, to a node the
-- operator approved. Its only question to the hub database is "may this host have it, and to
-- which key": one SELECT on four columns of `hosts`. It connects as `org_node_token`, which can do
-- that and nothing else: it cannot approve a node (no UPDATE), cannot read any other table, and
-- cannot write an event. Modelled on deploy/join/org_join_role.sql.
--
-- Run as the database OWNER (`org`; it needs CREATEROLE to make the role, otherwise run the file
-- as `postgres`), once per hub, and again whenever this file changes. It is idempotent: every run
-- leaves the role with exactly the grants below, no more, no fewer. The password is NOT in this
-- file, and it is not given to it either: this file takes the SCRAM-SHA-256 VERIFIER of the
-- password (SCRAM-SHA-256$4096:<salt>$<StoredKey>:<ServerKey>), which Postgres stores as it is.
-- `CREATE ROLE ... PASSWORD '<plain>'` is a statement the server may log or echo in an error;
-- a verifier is a one-way hash of the password, so nothing that logs the statement holds a
-- password. Pass it at run time, through the environment so it never reaches argv:
--
--   ORG_NODE_TOKEN_VERIFIER="$verifier" psql -v ON_ERROR_STOP=1 -X -f deploy/node-token/org_node_token_role.sql "$ADMIN_DSN"
--
-- (or as the psql variable org_node_token_verifier). deploy/node-token/org_node_token_role.py makes
-- the password, computes the verifier, runs this file with it and prints the role's URL on stdout
-- only; its use is in deploy/node-token/README.md. Running it again sets the verifier to the one given.
--
-- What the grant is for (the statement is in tools/node_token_api.py, _route_token):
--   hosts  SELECT host, status, pubkey, approved_at
--          SELECT status, pubkey, approved_at FROM hosts WHERE host = ?
--          (the health check's SELECT 1 FROM hosts needs a SELECT on any one column)

\set ON_ERROR_STOP on

-- 1. The verifier, from the psql variable or the environment; never a literal in this file. A string
--    that is not exactly a SCRAM-SHA-256 verifier is refused: handed to PASSWORD as it is, Postgres
--    would take any other string for a PLAIN password, hash it, and make the string the password.
\if :{?org_node_token_verifier}
\else
  \set org_node_token_verifier `echo "$ORG_NODE_TOKEN_VERIFIER"`
\endif
SELECT :'org_node_token_verifier' !~ '^SCRAM-SHA-256[$][0-9]{4,7}:[A-Za-z0-9+/]{22}==[$][A-Za-z0-9+/]{43}=:[A-Za-z0-9+/]{43}=$' AS bad_verifier \gset
\if :bad_verifier
DO $guard$
BEGIN
  RAISE EXCEPTION 'org_node_token_verifier (or ORG_NODE_TOKEN_VERIFIER) is missing or is not a SCRAM-SHA-256 verifier';
END
$guard$;
\endif

-- 2. The role: login, three connections, no attribute that widens it.
SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_node_token') AS make_role \gset
\if :make_role
CREATE ROLE org_node_token LOGIN CONNECTION LIMIT 3 PASSWORD :'org_node_token_verifier'
  NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS INHERIT;
\else
-- No NO... attributes here: on Postgres 16 a role that is not itself a superuser may not even
-- restate them. The check in section 5 fails the run if any of them has drifted.
ALTER ROLE org_node_token LOGIN CONNECTION LIMIT 3 PASSWORD :'org_node_token_verifier';
\endif
-- A runaway statement or a stuck transaction must not hold one of the three connections.
ALTER ROLE org_node_token SET statement_timeout = '5s';
ALTER ROLE org_node_token SET idle_in_transaction_session_timeout = '10s';

-- 3. Start from nothing, so a grant removed from this file is removed from the role.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM org_node_token;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM org_node_token;
REVOKE ALL ON SCHEMA public FROM org_node_token;
GRANT USAGE ON SCHEMA public TO org_node_token;

-- 4. The grant.
GRANT SELECT (host, status, pubkey, approved_at) ON hosts TO org_node_token;

-- 5. Prove it. The role holds exactly the privilege of section 4 and no other, or this run
--    fails (and the script stops: ON_ERROR_STOP). Nothing here prints a password.
DO $check$
DECLARE
  have text;
  want text := 'hosts.approved_at:SELECT hosts.host:SELECT hosts.pubkey:SELECT hosts.status:SELECT';
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_node_token' AND (
       rolsuper OR rolcreaterole OR rolcreatedb OR rolreplication OR rolbypassrls
       OR NOT rolcanlogin OR rolconnlimit <> 3)) THEN
    RAISE EXCEPTION 'org_node_token has a role attribute it must not have';
  END IF;

  SELECT string_agg(format('%s.%s:%s', c.relname, a.attname, p.priv), ' '
                    ORDER BY c.relname COLLATE "C", a.attname COLLATE "C", p.priv COLLATE "C")
    INTO have
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'public'
    JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
    CROSS JOIN (VALUES ('SELECT'), ('INSERT'), ('UPDATE'), ('REFERENCES')) AS p(priv)
   WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
     AND has_column_privilege('org_node_token', c.oid, a.attnum, p.priv);
  IF have IS DISTINCT FROM want THEN
    RAISE EXCEPTION 'org_node_token column privileges differ from this file. have: %', have;
  END IF;

  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                AND has_table_privilege('org_node_token', c.oid, 'DELETE,TRUNCATE,TRIGGER')) THEN
    RAISE EXCEPTION 'org_node_token can delete, truncate or add triggers somewhere';
  END IF;
  IF has_schema_privilege('org_node_token', 'public', 'CREATE') THEN
    RAISE EXCEPTION 'org_node_token can create objects in schema public (PUBLIC holds CREATE there)';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
              WHERE n.nspname = 'public' AND c.relkind = 'S'
                AND CASE WHEN c.relkind = 'S'   -- the planner may evaluate this on a non-sequence
                         THEN has_sequence_privilege('org_node_token', c.oid, 'USAGE,SELECT,UPDATE')
                    END) THEN
    RAISE EXCEPTION 'org_node_token holds a privilege on a sequence';
  END IF;
END
$check$;

\echo org_node_token: role and grants are in place and verified

-- The hub Postgres role for the COO session (SomPong, unix user `sompong`) — CEO 2026-10-02.
--
-- The CEO wants SomPong to work like every C-level (tasks, delegation, letters) with one guard: root
-- only through his Face ID. Every other C-level reaches the hub as `org`, which is a SUPERUSER, and a
-- Postgres superuser can run programs (COPY ... TO PROGRAM). Handing that DSN to a non-root session
-- would be a way around the Face-ID gate, so SomPong gets this role instead: read/write on the work
-- tables, read-only on hosts, nothing on the node-join secrets.
--
--   tasks, events, locks, c_level_sessions, letters   SELECT INSERT UPDATE DELETE   the C-level loop
--   hosts                                             SELECT                        routing reads it;
--                                                     UPDATE would let it approve a node (W4.6a F1)
--   join_tokens, node_secrets                         none                          join flow secrets
--   sequences in public                               USAGE SELECT                  serial ids
--
-- It is NOT the owner, so it cannot run lib.db's schema migrations: when new code adds a column, a
-- root process must start first (any org tool run by a root C-level does it). A table added later
-- has no grant here until this file is changed and re-run.
--
-- Run as `org` (superuser), once per hub and again whenever this file changes. Idempotent: every
-- run leaves exactly these grants. The password is NOT in this file; pass it through the
-- environment, which psql reads with \getenv, so it never reaches argv:
--
--   docker exec -i -e ORG_COO_PASSWORD org-postgres psql -v ON_ERROR_STOP=1 -X -U org -d org \
--     < deploy/hub/org_coo_role.sql
--
-- The DSN (postgresql://org_coo:<password>@<hub>:5432/org) goes to Infisical Org-Coo/prod as
-- ORG_DB_URL; the runbook docs/ops/sompong-coo-deploy-2026-10-01.md has the recipe.
\set ON_ERROR_STOP on
\getenv org_coo_password ORG_COO_PASSWORD
\if :{?org_coo_password}
\else
  \echo 'ORG_COO_PASSWORD is not set'
  \quit 1
\endif

SELECT NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'org_coo') AS need_role \gset
\if :need_role
  CREATE ROLE org_coo LOGIN;
\endif
ALTER ROLE org_coo WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS
  CONNECTION LIMIT 10 PASSWORD :'org_coo_password';

-- start from nothing, then grant exactly the list above
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM org_coo;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM org_coo;
GRANT CONNECT ON DATABASE org TO org_coo;
GRANT USAGE ON SCHEMA public TO org_coo;
GRANT SELECT, INSERT, UPDATE, DELETE ON tasks, events, locks, c_level_sessions, letters TO org_coo;
GRANT SELECT ON hosts TO org_coo;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO org_coo;

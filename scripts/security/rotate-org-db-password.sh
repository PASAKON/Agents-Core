#!/usr/bin/env bash
# Rotate the password of the hub role `org` to the one the CEO put in Infisical
# (order O-20261027-1347-4e62, CEO Q-20261026-1057-1569). Run as root on Contabo by a Run card:
#
#   bash scripts/security/rotate-org-db-password.sh check   # rehearsal: read-only
#   bash scripts/security/rotate-org-db-password.sh apply   # applies it
#
# The new ORG_DB_URL exists only in the helper's environment: `infisical_setup.py run` puts it
# there, and nothing on this line or the helper's argv carries it. The helper needs psycopg, which
# only the repo venv has (system python3 has none). Every step and refusal:
# scripts/security/rotate_org_db_password.py.
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VERB="${1:-}"
case "$VERB" in
  check|apply) ;;
  *) echo "usage: $0 check|apply" >&2; exit 2 ;;
esac
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || { echo "REFUSED: $PY is missing (the helper needs the repo venv's psycopg)" >&2; exit 2; }

cd "$ROOT"
exec python3 tools/infisical_setup.py run Agents-Core prod --as contabo -- \
  "$PY" scripts/security/rotate_org_db_password.py "$VERB"

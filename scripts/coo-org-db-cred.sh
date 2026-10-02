#!/usr/bin/env bash
# Hand the COO session (unix user `sompong`) the DSN of its limited hub role, as one file in /run.
#
# Run by mooniex-sompong.service at start, as root, under
#   tools/infisical_setup.py run Org-Coo prod --as contabo -- bash scripts/coo-org-db-cred.sh
# so ORG_DB_URL arrives in this process's environment from Infisical and nowhere else.
#
# Why a file and not an identity (CEO 2026-10-02): the CEO approved "SomPong gets a key" for the org
# MCP, but Infisical Free counts his user account against its 5 identities, so the org is full and
# `sompong` cannot have one. Instead root reads Org-Coo, which holds only the DSN of the Postgres role
# org_coo (deploy/hub/org_coo_role.sql: no superuser, no join secrets), and leaves it where only
# sompong can read it. The file lives in the unit's RuntimeDirectory (tmpfs, removed on stop), the
# directory is root's so sompong cannot plant a link in it, and the value is never printed.
# scripts/hub/with-org-db-env.sh reads it (MOONIEX_ORG_DB_URL_FILE) into the org MCP's environment.
#
# Test seams: COO_CRED_DIR, SOMPONG_USER, COO_CRED_CHOWN=0 (skip chown when not root).
set -euo pipefail
DIR="${COO_CRED_DIR:-/run/sompong-coo}"
RUN_USER="${SOMPONG_USER:-sompong}"
OUT="$DIR/org-db.url"

die() { echo "coo-org-db-cred: $*" >&2; exit 1; }

[ -n "${ORG_DB_URL:-}" ] || die "ORG_DB_URL is not set (Infisical Org-Coo/prod empty or not read)"
case "$ORG_DB_URL" in
  postgresql://*|postgres://*) ;;
  *) die "ORG_DB_URL is not a postgres DSN" ;;
esac

[ -d "$DIR" ] && [ ! -L "$DIR" ] || die "$DIR is not a directory"
if [ "${COO_CRED_CHOWN:-1}" = "1" ]; then
  [ "$(stat -c %u "$DIR")" = "0" ] || die "$DIR must be root's"
fi

umask 077
TMP="$(mktemp "$DIR/.org-db.XXXXXX")"
trap 'rm -f "$TMP"' EXIT
printf '%s' "$ORG_DB_URL" >"$TMP"
if [ "${COO_CRED_CHOWN:-1}" = "1" ]; then
  chown "root:$RUN_USER" "$TMP"
fi
chmod 0440 "$TMP"
mv -f "$TMP" "$OUT"
trap - EXIT
echo "coo-org-db-cred: wrote $OUT (root:$RUN_USER 0440)"

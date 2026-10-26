#!/bin/bash
# Apply hub DDL files exactly as they are at a pushed Agents-Core commit.
# Run from a Run Inbox card (the classifier refuses DDL from a session):
#   apply-ddl.sh <40-hex sha> docs/design/<file>.sql [...]
# Each file must be idempotent; psql stops at the first error. Prints the
# projects/orders columns afterwards as the card's evidence.
set -euo pipefail
repo=/opt/MoonieXHQ/Agents/Core
sha=${1:-}; shift || true
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo "usage: apply-ddl.sh <sha> docs/design/<file>.sql..." >&2; exit 2; }
[ $# -gt 0 ] || { echo "no DDL files" >&2; exit 2; }
git -C "$repo" cat-file -e "$sha^{commit}" 2>/dev/null || git -C "$repo" fetch -q origin "$sha"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
args=()
for p in "$@"; do
  [[ $p =~ ^docs/design/[a-z0-9-]+\.sql$ ]] || { echo "refused path: $p" >&2; exit 2; }
  git -C "$repo" show "$sha:$p" > "$tmp/$(basename "$p")"
  echo "$p sha256 $(sha256sum < "$tmp/$(basename "$p")" | cut -c1-16)"
  args+=(-f "$tmp/$(basename "$p")")
done
cat > "$tmp/zz-check.sql" <<'SQL'
SELECT table_name || '.' || column_name FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name IN ('projects', 'orders', 'milestones', 'tasks')
   AND column_name IN ('tier', 'kind', 'due_at', 'cadence_h', 'order_id', 'project_id', 'words')
 ORDER BY 1;
SQL
args+=(-f "$tmp/zz-check.sql")
# The URL carries the password: hand it to psql as PG* environment, never as an argument (ps shows argv).
"$repo/scripts/hub/with-org-db-env.sh" /usr/bin/python3 -I -c '
import os, sys
from urllib.parse import parse_qsl, unquote, urlsplit
url = os.environ.pop("ORG_DB_URL", "")
if not url:
    sys.exit("ORG_DB_URL is required")
env = {k: v for k, v in os.environ.items() if not k.startswith("PG")}
u = urlsplit(url)
for key, value in (("PGHOST", u.hostname), ("PGPORT", u.port), ("PGUSER", u.username),
                   ("PGPASSWORD", u.password), ("PGDATABASE", u.path.lstrip("/"))):
    if value:
        env[key] = unquote(str(value))
for key, value in parse_qsl(u.query):
    env["PG" + key.upper()] = value
os.execvpe("psql", ["psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1", *sys.argv[1:]], env)
' "${args[@]}"

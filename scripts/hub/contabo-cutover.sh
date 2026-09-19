#!/usr/bin/env bash
# Contabo side of the tasks.db hub cutover (docs/design/tasks-db-hub.md §3.3 step 6).
#
# Run this AFTER:
#   1. the hub Postgres is up on Contabo (scripts/hub/contabo-postgres-up.sh), and
#   2. the Mac flip is done (scripts/hub/cutover-mac.sh --apply), and
#   3. the Contabo C-level sessions have been ended (/session-save in each).
#
# The CTO session cannot run this itself: the auto-mode classifier refuses remote
# shell writes over ssh (memory: feedback_ssh_mooniex_vps). The CEO runs it from
# the Mac in any CTO tab:
#
#     ! bash scripts/hub/contabo-cutover.sh
#
# Steps on Contabo (root over ssh alias mooniex-vps), each idempotent:
#   1. refuse while any cto-*/cxo-* tmux session is alive (those keep the old
#      sqlite backend until restarted). --sessions-closed overrides, only if you
#      ended them yourself and tmux is merely stale.
#   2. /opt/mooniex-agents: refuse on dirty tracked files; keep a backup branch of
#      the current local main; move main to origin/main (that box's local commits
#      were already merged into origin via contabo/main-2026-09-17).
#   3. .venv: install psycopg[binary] only -- a full `pip install -r requirements.txt`
#      pulls mcp 2.x, which breaks runners/cto_mcp_server.py's mcp-1.x FastMCP usage.
#   4. append ORG_DB_URL / ORG_TEST_DB_URL to /root/.config/mooniex/org-db.env
#      (host 100.118.171.23 -- the container binds the tailnet IP, not loopback).
#   5. import this box's own registry rows into the hub (ids never collide with
#      the Mac's: checked 2026-09-18, 0 of 11 overlapped).
#   6. archive state/tasks.db and leave a DIRECTORY tombstone in its place, so a
#      process still on the sqlite backend fails loudly instead of silently
#      creating an empty database (the split brain this whole change removes).
#   7. read the hub back through lib.db and print the row counts.
#
# Rollback:
#   ssh mooniex-vps 'cd /opt/mooniex-agents && rmdir state/tasks.db &&
#     mv state/tasks.db.archived-<date> state/tasks.db &&
#     git checkout backup/main-before-hub-<date>'
#   then delete the two ORG_*_URL lines from /root/.config/mooniex/org-db.env.
set -euo pipefail
HOST_ALIAS="${HOST_ALIAS:-mooniex-vps}"
FLAG="${1:-}"
echo "== [contabo] hub cutover (alias=$HOST_ALIAS) =="
ssh -o ConnectTimeout=15 -o BatchMode=yes "$HOST_ALIAS" "FLAG='$FLAG' bash -s" <<'REMOTE'
set -euo pipefail
ROOT=/opt/mooniex-agents
ENVF=/root/.config/mooniex/org-db.env
TODAY=$(date +%F)
cd "$ROOT"

echo "== step 1: C-level sessions must be closed =="
LIVE=$(tmux ls 2>/dev/null | cut -d: -f1 | grep -E '^(cto|cxo)-' || true)
if [ -n "$LIVE" ] && [ "$FLAG" != "--sessions-closed" ]; then
  echo "REFUSING: live C-level tmux sessions on this box:"; echo "$LIVE"
  echo "End them first (/session-save in each -- they keep the old sqlite"
  echo "backend until restarted), then re-run."
  exit 1
fi
echo "ok: no live C-level sessions${LIVE:+ (overridden: $LIVE)}"

echo "== step 2: code to origin/main (backup branch kept) =="
git fetch -q origin
if [ -n "$(git status --porcelain | grep -v '^??' || true)" ]; then
  echo "REFUSING: tracked files are dirty in $ROOT:"; git status --porcelain | grep -v '^??'; exit 1
fi
git branch -f "backup/main-before-hub-$TODAY" main
git checkout -q -B main origin/main
echo "main now at: $(git log --oneline -1)"
echo "backup branch: backup/main-before-hub-$TODAY"

echo "== step 3: psycopg into the venv =="
.venv/bin/pip install -q "psycopg[binary]" 2>&1 | grep -viE 'notice|upgrade' || true
.venv/bin/python -c "import psycopg; print('psycopg', psycopg.__version__)"

echo "== step 4: hub URLs into $ENVF (values never printed) =="
[ -s "$ENVF" ] || { echo "REFUSING: $ENVF missing -- run contabo-postgres-up.sh first"; exit 1; }
ENVF="$ENVF" python3 - <<'PY'
import os, urllib.parse
p = os.environ["ENVF"]
raw = [l.rstrip("\n") for l in open(p) if l.strip()]
kv = dict(l.split("=", 1) for l in raw if "=" in l and not l.startswith("ORG_"))
pw = urllib.parse.quote(kv["POSTGRES_PASSWORD"], safe="")
lines = [l for l in raw if not l.startswith("ORG_")]
lines.append(f"ORG_DB_URL=postgresql://{kv['POSTGRES_USER']}:{pw}@100.118.171.23:5432/org")
lines.append(f"ORG_TEST_DB_URL=postgresql://{kv['POSTGRES_USER']}:{pw}@100.118.171.23:5432/org_test")
open(p, "w").write("\n".join(lines) + "\n")
os.chmod(p, 0o600)
print("keys:", ", ".join(l.split("=")[0] for l in lines))
PY

set -a; . "$ENVF"; set +a

echo "== step 5: import this box's registry rows into the hub =="
if [ -f state/tasks.db ]; then
  .venv/bin/python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply
else
  echo "no state/tasks.db here (already archived?) -- skipping import"
fi

echo "== step 6: archive the sqlite + tombstone =="
if [ -f state/tasks.db ]; then
  mv state/tasks.db "state/tasks.db.archived-$TODAY"
  rm -f state/tasks.db-wal state/tasks.db-shm
  mkdir state/tasks.db
  echo "archived -> state/tasks.db.archived-$TODAY ; tombstone directory at state/tasks.db"
else
  echo "nothing to archive"
fi

echo "== step 7: read back through lib.db =="
.venv/bin/python - <<'PY'
from lib import db
with db.get_conn() as c:
    for t in ("tasks", "c_level_sessions", "events", "locks"):
        print(f"  hub {t:18s} {c.execute(f'select count(*) from {t}').fetchone()[0]}")
PY
echo "== done. Spawn Contabo C-level sessions again now --"
echo "   scripts/cto-claude.sh sources $ENVF at launch, so they come up on the hub."
REMOTE

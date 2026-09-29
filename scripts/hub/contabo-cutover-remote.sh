#!/usr/bin/env bash
# scripts/hub/contabo-cutover-remote.sh -- the Contabo-side body of the hub
# cutover (docs/design/tasks-db-hub.md §3.3 step 6). Extracted out of
# scripts/hub/contabo-cutover.sh's inline ssh heredoc (Org Mesh W1.1) so it
# is a real file: readable, `bash -n`-checkable, and runnable directly
# against a throwaway repo in tests/test_hub_cutover_scripts.py. This file
# never opens an ssh connection and never touches a real Postgres by
# itself -- scripts/hub/contabo-cutover.sh is the only caller that does,
# by piping this file's content over ssh to Contabo.
#
# ROOT/ENVF default to the real Contabo paths and are overridable via env
# vars of the same name -- production leaves them unset and gets the real
# paths; tests point them at a tmp_path git repo / env file so this can run
# fully sandboxed. FLAG carries scripts/hub/contabo-cutover.sh's optional
# `--sessions-closed` argument (set as a remote env var by the ssh command
# line, same as before this file existed).
set -euo pipefail

ROOT="${ROOT:-/opt/MoonieXHQ/Agents/Core}"
ENVF="${ENVF:-/root/.config/mooniex/org-db.env}"
FLAG="${FLAG:-}"
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

echo "== step 2: code to origin/main (backup branch kept; fast-forward only) =="
git fetch -q origin
# Ignore only the weekly machine_doctor cron's rewrite of the tracked
# state/machine-discovered-*.yaml (task Org Mesh W1.1) -- any other dirty
# tracked file still refuses. Untracked files ('??') were already ignored.
DIRTY="$(git status --porcelain | grep -v '^??' \
  | grep -vE 'state/machine-discovered-[^[:space:]]+\.ya?ml$' || true)"
if [ -n "$DIRTY" ]; then
  echo "REFUSING: tracked files are dirty in $ROOT:"; echo "$DIRTY"; exit 1
fi
IGNORED_DIRTY="$(git status --porcelain | grep -v '^??' \
  | grep -E 'state/machine-discovered-[^[:space:]]+\.ya?ml$' || true)"
if [ -n "$IGNORED_DIRTY" ]; then
  echo "ok: ignoring machine_doctor's tracked rewrite (not a real dirty-tree blocker):"
  echo "$IGNORED_DIRTY"
fi
git branch -f "backup/main-before-hub-$TODAY" main
git checkout -q main
# Fast-forward only -- `checkout -B main origin/main` (the old behaviour)
# force-resets main to match origin, discarding any local commit that
# hasn't been pushed yet. Refuse instead of silently throwing work away.
if ! git merge --ff-only origin/main; then
  echo "REFUSING: local main is not fast-forwardable to origin/main -- it has"
  echo "commit(s) origin/main does not. Merge/rebase by hand, then re-run."
  echo "Backup branch already made: backup/main-before-hub-$TODAY"
  exit 1
fi
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
  # This is the SECOND ledger (the hub already holds the Mac's ~1108 tasks
  # from cutover-mac.sh's step 3) -- --default-host contabo backfills this
  # box's rows instead of the Mac's, and --append-events drops the source
  # events.id so it can never collide with the Mac's already-imported ids
  # (module docstring, docs/design/tasks-db-hub.md §3.3). --on-collision is
  # deliberately left unset: migrate_tasks_db.py refuses --apply by default
  # when a task/c_level_sessions row's key exists on both sides with
  # differing data, which is exactly what should stop this cutover for a
  # human instead of silently picking a side.
  .venv/bin/python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host contabo --append-events

  echo "== step 5b: verify no data lost (sqlite is a SUBSET of postgres) =="
  # Not --mode equal: the target already holds the Mac's rows too, so
  # postgres = mac + contabo and a byte-for-byte count match can never hold
  # for this second ledger (task brief). --mode subset instead checks every
  # sqlite row is present in postgres, extra target rows and all.
  .venv/bin/python scripts/hub/verify_migration_counts.py --sqlite state/tasks.db --pg "$ORG_DB_URL" --mode subset
else
  echo "no state/tasks.db here (already archived?) -- skipping import"
fi

echo "== step 6: checkpoint the WAL, archive the sqlite (+ wal/shm), tombstone =="
if [ -f state/tasks.db ]; then
  scripts/hub/wal-checkpoint-archive.sh state/tasks.db "state/tasks.db.archived-$TODAY"
  mkdir state/tasks.db
  echo "tombstone directory at state/tasks.db"
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

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
# ROOT/SYSTEMD_DIR/NODE_YAML default to the real Contabo paths and are
# overridable via env vars of the same name -- production leaves them unset and
# gets the real paths; tests point them at a tmp_path git repo and tmp dirs so
# this can run fully sandboxed. FLAG carries scripts/hub/contabo-cutover.sh's
# optional `--sessions-closed` argument (set as a remote env var by the ssh
# command line, same as before this file existed).
#
# ORG_DB_URL never touches a .env file (CLAUDE.md §Secrets): it lives in
# Infisical Agents-Core/prod, and every command below that needs it runs
# through `infisical_run` (tools/infisical_setup.py run ...), which puts it in
# that one process's environment. Design: docs/design/org-mesh-w18-contabo-consumers.md
#
# Rollback of steps 5-8 (the full text, with the tasks.db half, is in
# scripts/hub/contabo-cutover.sh's header): remove the three drop-ins
# /etc/systemd/system/<unit>.service.d/org-db.conf, remove the `org_db:` line
# from /root/.config/mooniex/node.yaml (MOONIEX_NODE_YAML=<node.yaml> python3
# scripts/hub/cutover_flip.py --rollback --apply), `systemctl daemon-reload`, then
# restart the three units. Step 4 changes nothing; step 5 STOPS the three units
# (W1.9 F3), and step 8 writes the `org_db:` line and installs the drop-ins (W1.9
# F2: a unit restarted by systemd before step 8 must come back on its OLD unit
# file, on sqlite, never on a half-migrated hub), then restarts them. A failure
# after the stop prints the rollback (print_rollback below, also from the EXIT
# trap) -- the line and the drop-ins may already be in place by then.
set -euo pipefail

ROOT="${ROOT:-/opt/MoonieXHQ/Agents/Core}"
SYSTEMD_DIR="${SYSTEMD_DIR:-/etc/systemd/system}"
NODE_YAML="${NODE_YAML:-/root/.config/mooniex/node.yaml}"
# cutover_flip.py (printed in the rollback) reads MOONIEX_NODE_YAML, not NODE_YAML
# (W1.9 F4): one variable for both, so a run pointed at a scratch node file can never
# reach the live one through the other name.
export MOONIEX_NODE_YAML="$NODE_YAML"
FLAG="${FLAG:-}"
TODAY=$(date +%F)
UNITS="mooniex-watchdog mooniex-secretary mooniex-secretary-waker"
cd "$ROOT"

# Run "$@" with Agents-Core/prod's secrets (ORG_DB_URL among them) in its env.
infisical_run() {
  python3 "$ROOT/tools/infisical_setup.py" run Agents-Core prod --as contabo -- "$@"
}

# Printed when the cutover fails after step 5 stopped the three units (and from
# step 8's own refusals): the switch line must come out along with the drop-ins,
# and the units must be started again.
UNITS_STOPPED=0
ROLLBACK_PRINTED=0
print_rollback() {
  ROLLBACK_PRINTED=1
  echo "Rollback (Contabo half; the tasks.db half is in the header of scripts/hub/contabo-cutover.sh):"
  echo "  1. rm -f $SYSTEMD_DIR/<unit>.service.d/org-db.conf for mooniex-watchdog, mooniex-secretary, mooniex-secretary-waker,"
  echo "     then rmdir --ignore-fail-on-non-empty $SYSTEMD_DIR/<unit>.service.d for the same three (the drop-ins exist only from step 8)"
  echo "  2. remove the org_db: line from $NODE_YAML (MOONIEX_NODE_YAML=$NODE_YAML python3 scripts/hub/cutover_flip.py --rollback --apply)"
  echo "  3. systemctl daemon-reload, then systemctl restart the three units"
  if [ "$UNITS_STOPPED" = 1 ]; then
    echo "  Step 5 stopped (or tried to stop) the three units. Until step 8 installs the drop-ins they are on their OLD unit files (sqlite):"
    echo "  if you stop here, bring them back on those with: systemctl start $UNITS"
    echo "  (if step 6 already moved state/tasks.db, put it back first -- the tasks.db half of the rollback)."
  fi
}
# A failure anywhere after the stop (migrate, verify, archive, read-back) is a set -e
# exit with no message of its own: say what to do, once.
on_exit() {
  rc=$?
  if [ "$rc" -ne 0 ] && [ "$UNITS_STOPPED" = 1 ] && [ "$ROLLBACK_PRINTED" != 1 ]; then
    echo "FAILED (exit $rc) after step 5 stopped the three units."
    print_rollback
  fi
}
trap on_exit EXIT

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

echo "== step 4: ORG_DB_URL from Infisical, refusals only (values never printed) =="
# This step changes nothing on the box: it only refuses. No env file is read or
# written here. ORG_TEST_DB_URL is no longer produced: nothing in this cutover
# reads it (W1.9's rehearsal fetches its own org_test URL). node.yaml is NOT
# touched here: it is the hub switch for the C-level/worker MCP servers, and a
# session spawned before the migration (step 5) would open an empty hub. The
# drop-ins are NOT installed here either (W1.9 F2): any restart of a unit before
# step 8 -- a crash, or a manual start after a refused step 5 -- would load the
# drop-in and put the unit on a half-migrated hub. Both are written in step 8.
for u in $UNITS; do
  [ -f "deploy/systemd/$u.service.d/org-db.conf" ] \
    || { echo "REFUSING: deploy/systemd/$u.service.d/org-db.conf is missing in $ROOT"; exit 1; }
  systemctl cat "$u.service" >/dev/null 2>&1 \
    || { echo "REFUSING: $u.service is not installed on this box -- install it first"; exit 1; }
done
if ! infisical_run .venv/bin/python -c '
import os, sys
url = os.environ.get("ORG_DB_URL", "").strip()
if not url:
    sys.exit("ORG_DB_URL is not in Agents-Core/prod")
import psycopg
try:
    with psycopg.connect(url, connect_timeout=10) as c:
        c.execute("select 1")
except Exception as e:
    sys.exit("hub connect failed: " + type(e).__name__)
print("Agents-Core/prod ORG_DB_URL reaches the hub")
'; then
  echo "REFUSING: Agents-Core/prod ORG_DB_URL is missing or the hub is not reachable with it."
  echo "Nothing was changed."
  exit 1
fi
echo "checks passed; nothing changed. The drop-ins are installed in step 8, just before the restarts"

echo "== step 5: stop the three units, import this box's registry rows into the hub =="
if [ -f state/tasks.db ]; then
  # W1.9 F3. (a) Refuse while any task is live: its worker still writes to
  # state/tasks.db, and the watchdog is about to stop. Fail closed: a count that
  # cannot be read is a refusal too.
  if ! ACTIVE="$("${SQLITE3_BIN:-sqlite3}" -readonly state/tasks.db \
      "select count(*) from tasks where status in ('pending','in_progress','queued_remote')" 2>&1)"; then
    echo "REFUSING: could not count the live tasks in state/tasks.db: $ACTIVE"
    echo "Nothing was changed."
    exit 1
  fi
  if [ "$ACTIVE" != "0" ]; then
    echo "REFUSING: $ACTIVE task(s) in state/tasks.db are pending, in_progress or queued_remote."
    echo "Let them finish (or cancel them), then re-run. Nothing was changed."
    exit 1
  fi
  # (b) Stop the writers (the watchdog, the secretary, its waker) so no row can land
  # between the import and the archive: a row written in that window would sit only
  # in the archive and never reach the hub. Step 8's restart brings them back. They
  # are still on their OLD unit files here (the drop-ins arrive in step 8), so a
  # `systemctl start` after a refused step 5 is safe (print_rollback says so).
  UNITS_STOPPED=1
  for u in $UNITS; do
    if ! systemctl stop "$u.service"; then
      echo "REFUSING: could not stop $u. Nothing was imported."
      exit 1
    fi
    echo "stopped $u"
  done
  # This is the SECOND ledger (the hub already holds the Mac's ~1108 tasks
  # from cutover-mac.sh's step 3) -- --default-host contabo backfills this
  # box's rows instead of the Mac's, and --append-events drops the source
  # events.id so it can never collide with the Mac's already-imported ids
  # (module docstring, docs/design/tasks-db-hub.md §3.3). --on-collision is
  # deliberately left unset: migrate_tasks_db.py refuses --apply by default
  # when a task/c_level_sessions row's key exists on both sides with
  # differing data, which is exactly what should stop this cutover for a
  # human instead of silently picking a side.
  # $ORG_DB_URL below is expanded by the inner sh, inside infisical_run's
  # environment (single quotes: the outer shell never sees the value).
  infisical_run sh -ec '
  .venv/bin/python scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host contabo --append-events
  '

  echo "== step 5b: verify no data lost (sqlite is a SUBSET of postgres) =="
  # Not --mode equal: the target already holds the Mac's rows too, so
  # postgres = mac + contabo and a byte-for-byte count match can never hold
  # for this second ledger (task brief). --mode subset instead checks every
  # sqlite row is present in postgres, extra target rows and all.
  infisical_run sh -ec '
  .venv/bin/python scripts/hub/verify_migration_counts.py --sqlite state/tasks.db --pg "$ORG_DB_URL" --mode subset
  '
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
infisical_run .venv/bin/python - <<'PY'
from lib import db
with db.get_conn() as c:
    for t in ("tasks", "c_level_sessions", "events", "locks"):
        print(f"  hub {t:18s} {c.execute(f'select count(*) from {t}').fetchone()[0]}")
PY

echo "== step 8: hub switch in node.yaml, drop-ins, then restart the three consumers (after the migration and tombstone) =="
# The switch for the C-level MCP servers and workers on this box (W1.6): the
# same line grammar as cutover_flip.py; idempotent, every other line kept.
# Written only now, right before the restarts: earlier, a session spawned
# between step 4 and here would open the hub before it is migrated.
if ! NODE_YAML="$NODE_YAML" python3 - <<'PY'
import os, sys
sys.path.insert(0, "scripts/hub")
from cutover_flip import set_org_db
p = os.environ["NODE_YAML"]
before = open(p).read() if os.path.exists(p) else ""
after = set_org_db(before, "hub")
if after == before:
    print(f"ok: {p} already says org_db: hub")
else:
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    open(p, "w").write(after)
    print(f"wrote org_db: hub to {p}")
PY
then
  echo "REFUSING: could not write org_db: hub to $NODE_YAML. No unit was restarted."
  print_rollback
  exit 1
fi
# W1.9 F2: only now do the units get the drop-ins (step 4 no longer installs them),
# right before they are restarted, so no earlier restart can load a drop-in.
for u in $UNITS; do
  if ! { install -d -m 755 "$SYSTEMD_DIR/$u.service.d" \
         && install -m 644 "deploy/systemd/$u.service.d/org-db.conf" "$SYSTEMD_DIR/$u.service.d/org-db.conf"; }; then
    echo "REFUSING: could not install the drop-in for $u. No unit was restarted."
    print_rollback
    exit 1
  fi
  echo "installed $SYSTEMD_DIR/$u.service.d/org-db.conf"
done
if ! systemctl daemon-reload; then
  echo "REFUSING: systemctl daemon-reload failed. No unit was restarted."
  print_rollback
  exit 1
fi
BAD=""
for u in $UNITS; do
  if ! systemctl restart "$u.service"; then
    echo "  RESTART FAILED: $u"
    BAD="$BAD $u"
  fi
done
sleep "${RESTART_SETTLE_S:-3}"
for u in $UNITS; do
  case " $BAD " in *" $u "*) continue ;; esac
  if systemctl is-active --quiet "$u.service"; then
    echo "  active: $u"
  else
    echo "  NOT ACTIVE: $u"
    BAD="$BAD $u"
  fi
done
if [ -n "$BAD" ]; then
  echo "REFUSING to call this done: not restarted or not active after restart:$BAD"
  echo "Look with: journalctl -u <unit> -n 30 --no-pager   (values are never logged)"
  print_rollback
  exit 1
fi
echo "== done. Spawn Contabo C-level sessions again now --"
echo "   their org MCP server starts through scripts/hub/with-org-db-env.sh (node.yaml"
echo "   says org_db: hub), which gets ORG_DB_URL from Infisical Agents-Core/prod."

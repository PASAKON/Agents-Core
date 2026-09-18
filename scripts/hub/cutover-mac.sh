#!/usr/bin/env bash
# scripts/hub/cutover-mac.sh -- Mac-side cutover to the Contabo Postgres hub
# (docs/design/tasks-db-hub.md §3.3, steps 1-5).
#
# Dry-run by default: every step prints what it WOULD do and changes
# nothing on disk or in launchd. Pass --apply to execute for real.
#
# Reads the hub's connection string from a KEY=value env file the hub setup
# wrote (default ~/.config/mooniex/org-db.env; override with
# MOONIEX_ORG_DB_ENV -- this is how this script's own tests point it at a
# scratch file instead of the real one). Refuses to run at all if that file
# is missing: there is no safe local fallback (ADR 0021 -- no silent
# per-checkout SQLite split-brain).
set -eo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

APPLY=0
for arg in "$@"; do
  case "$arg" in
    --apply)   APPLY=1 ;;
    --dry-run) APPLY=0 ;;
    *) echo "unknown argument: $arg (expected --apply or --dry-run)" >&2; exit 2 ;;
  esac
done

ENV_FILE="${MOONIEX_ORG_DB_ENV:-$HOME/.config/mooniex/org-db.env}"
WATCHDOG_LABEL="com.mooniex.agents-watchdog"
WATCHDOG_PLIST="$HOME/Library/LaunchAgents/${WATCHDOG_LABEL}.plist"
UID_NUM="$(id -u)"
PYTHON="$ROOT/.venv/bin/python"
TODAY="$(date +%Y-%m-%d)"
ARCHIVE_PATH="$ROOT/state/tasks.db.archived-${TODAY}"

say()  { printf '%s\n' "$*"; }
step() { printf '\n== step %s: %s ==\n' "$1" "$2"; }

if [ "$APPLY" -eq 1 ]; then
  say "MODE: APPLY -- this makes real changes (launchd, config files, state/tasks.db)."
else
  say "MODE: DRY-RUN (pass --apply to execute for real). Nothing below writes anything"
  say "except the read-only checks in step 1, which always run."
fi

if [ ! -f "$ENV_FILE" ]; then
  say ""
  say "REFUSING: $ENV_FILE not found."
  say "The hub setup (docs/design/tasks-db-hub.md §3.2) writes this file when the"
  say "Contabo Postgres hub is provisioned -- run that first, or set"
  say "MOONIEX_ORG_DB_ENV to point at an existing one."
  exit 1
fi

ORG_DB_URL="$(grep -E '^ORG_DB_URL=' "$ENV_FILE" | tail -1 | cut -d= -f2-)"
if [ -z "$ORG_DB_URL" ]; then
  say "REFUSING: $ENV_FILE exists but has no ORG_DB_URL= line."
  exit 1
fi
say ""
say "env file:   $ENV_FILE"
say "hub target: $("$PYTHON" -c '
import sys
from urllib.parse import urlsplit
u = urlsplit(sys.argv[1])
print(f"{u.hostname}:{u.port or 5432}{u.path}")
' "$ORG_DB_URL")"

# --- step 1: refuse if live work is in flight -------------------------
# Read-only; always runs (dry-run and --apply alike) -- it's a safety gate,
# not an action to preview.
step 1 "refuse if any live work is in flight"
LIVE_TASKS="$("$PYTHON" - <<'PYEOF'
import sys
sys.path.insert(0, ".")
from lib import db
live = [r for r in db.list_tasks(limit=2000)
        if r["status"] == "in_progress"
        or (r["status"] == "review" and r.get("pid"))]
for r in live:
    print(f"{r['id']}\t{r['status']}\t{r['role']}\t{r['title']}")
PYEOF
)"
if [ -n "$LIVE_TASKS" ]; then
  say "REFUSING: tasks still in flight:"
  say "$LIVE_TASKS"
  exit 1
fi
say "ok: no in_progress / live-pid review tasks."

WD_SESSIONS="$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^wd-' || true)"
if [ -n "$WD_SESSIONS" ]; then
  say "REFUSING: worker tmux sessions still running:"
  say "$WD_SESSIONS"
  exit 1
fi
say "ok: no wd-* tmux sessions."

# --- step 2: freeze the watchdog ---------------------------------------
step 2 "freeze the watchdog (restored on exit, success or failure)"
say "would run: launchctl bootout gui/${UID_NUM}/${WATCHDOG_LABEL}"
if [ "$APPLY" -eq 1 ]; then
  launchctl bootout "gui/${UID_NUM}/${WATCHDOG_LABEL}" 2>&1 || true
fi

_restore_watchdog() {
  step "2 (cleanup)" "restore the watchdog"
  say "would run: launchctl bootstrap gui/${UID_NUM} ${WATCHDOG_PLIST}"
  if [ "$APPLY" -eq 1 ]; then
    launchctl bootstrap "gui/${UID_NUM}" "$WATCHDOG_PLIST" 2>&1 || true
  fi
}
trap _restore_watchdog EXIT

# --- step 3: migrate, require equal counts -----------------------------
step 3 "migrate state/tasks.db -> hub"
say "would run: $PYTHON scripts/migrate_tasks_db.py --from state/tasks.db --to <ORG_DB_URL> --apply"
say "would then require: sqlite count == postgres count, every table (refuse otherwise)"
if [ "$APPLY" -eq 1 ]; then
  "$PYTHON" scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply
  ORG_DB_URL="$ORG_DB_URL" "$PYTHON" - <<'PYEOF'
import os
import sys
sys.path.insert(0, ".")
from lib import db as db_mod
from lib import db_pg

url = os.environ["ORG_DB_URL"]
sconn = db_mod.sqlite_connect("state/tasks.db", readonly=True)
pconn = db_pg.connect(url, timeout=10)
mismatched = []
for table in ("tasks", "c_level_sessions", "events", "locks"):
    s = sconn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    p = pconn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    print(f"  {table:20s} sqlite={s} postgres={p}")
    if s != p:
        mismatched.append(table)
sconn.close()
pconn.close()
if mismatched:
    print(f"REFUSING: count mismatch after migrate: {mismatched}", file=sys.stderr)
    sys.exit(1)
PYEOF
fi

# --- step 4: flip config to route ORG_DB_URL through the wrapper --------
step 4 "flip config/plists/cto-claude.sh to read ORG_DB_URL from the env file"
say "approach chosen: reference scripts/hub/with-org-db-env.sh's path from"
say "config/cto.mcp.json + config/worker.mcp.json's command/args and from both"
say "launchd plists' ProgramArguments; scripts/cto-claude.sh (already a shell"
say "script) gets a small block that sources the env file directly."
say "why: two of these files (cto.mcp.json, worker.mcp.json) are git-tracked --"
say "the connection string carries a password and must never land in a commit"
say "-- and routing every consumer through one wrapper means rotating the"
say "password later means editing the env file once, not four files."
if [ "$APPLY" -eq 1 ]; then
  "$PYTHON" scripts/hub/cutover_flip.py --apply
else
  "$PYTHON" scripts/hub/cutover_flip.py
fi

# --- step 5: verify round-trip, then archive ----------------------------
step 5 "verify a create_task round trip via lib.db, then archive state/tasks.db"
if [ "$APPLY" -eq 1 ]; then
  ORG_DB_URL="$ORG_DB_URL" "$PYTHON" - <<'PYEOF'
import sys
sys.path.insert(0, ".")
from lib import db

tid = db.create_task("mooniex-agents", "developer", "cutover verify",
                      "scripts/hub/cutover-mac.sh step 5 round trip",
                      owner_cto="cutover-verify")
got = db.get_task(tid)
assert got and got["id"] == tid, "round trip failed"
print(f"round trip ok: {tid}")
PYEOF
  mv state/tasks.db "$ARCHIVE_PATH"
  ls -la "$ARCHIVE_PATH"
else
  say "would run: create_task()+get_task() round trip via lib.db with ORG_DB_URL set"
  say "would then run: mv state/tasks.db $ARCHIVE_PATH && ls -la $ARCHIVE_PATH"
fi

say ""
say "== summary =="
say "what changed:   ORG_DB_URL now flows through config/{cto,worker}.mcp.json,"
say "                the watchdog + mac-agent launchd plists, and"
say "                scripts/cto-claude.sh; state/tasks.db archived to"
say "                $ARCHIVE_PATH (no writer left)."
say "how to roll back: git checkout -- config/cto.mcp.json config/worker.mcp.json"
say "                scripts/cto-claude.sh; restore the two plists (git-untracked --"
say "                Time Machine, or re-run cutover_flip.py's logic in reverse);"
say "                mv $ARCHIVE_PATH state/tasks.db."
say "watchdog:       restarts automatically when this script exits (see step 2 cleanup)."

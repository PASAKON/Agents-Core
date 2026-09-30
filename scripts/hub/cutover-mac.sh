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
# not an action to preview. Liveness logic lives in scripts/hub/
# cutover_gate.py (task-7ad6ad8a) -- a `review` row with a pid only refuses
# when that pid is alive AND identity-matched to the task (same check
# tools/worker_reap.py uses before ever signalling a pid); a dead/recycled
# pid is the ordinary state after reaping and is reported as an info count,
# not a refusal.
step 1 "refuse if any live work is in flight"
if ! "$PYTHON" scripts/hub/cutover_gate.py; then
  exit 1
fi

WD_SESSIONS="$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^wd-' || true)"
if [ -n "$WD_SESSIONS" ]; then
  say "REFUSING: worker tmux sessions still running:"
  say "$WD_SESSIONS"
  exit 1
fi
say "ok: no wd-* tmux sessions."

# Not a refusal -- every live C-level session keeps talking to its OLD
# backend until restarted (§3.3 step 7), so this is a reminder of who to
# restart after the flip, not a reason to block it.
CLEVEL_SESSIONS="$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^(cto|cxo)-' || true)"
if [ -n "$CLEVEL_SESSIONS" ]; then
  say "reminder: restart these after the flip (they keep their old backend until then):"
  say "$CLEVEL_SESSIONS"
else
  say "ok: no live cto-*/cxo-* tmux sessions."
fi

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
say "would run: $PYTHON scripts/migrate_tasks_db.py --from state/tasks.db --to <ORG_DB_URL> --apply --default-host mac"
say "would then require: sqlite count == postgres count, every table (refuse otherwise)"
if [ "$APPLY" -eq 1 ]; then
  "$PYTHON" scripts/migrate_tasks_db.py --from state/tasks.db --to "$ORG_DB_URL" --apply --default-host mac
  "$PYTHON" scripts/hub/verify_migration_counts.py --sqlite state/tasks.db --pg "$ORG_DB_URL"
fi

# --- step 4: flip config to route ORG_DB_URL through the wrapper --------
step 4 "flip the two launchd plists to the env wrapper, then write org_db: hub into the node file"
say "approach chosen: reference scripts/hub/with-org-db-env.sh's path from both"
say "launchd plists' ProgramArguments (both are untracked), then add the line"
say "'org_db: hub' to the node file (~/.config/mooniex/node.yaml, or \$MOONIEX_NODE_YAML;"
say "an existing org_db: line is replaced, host: is kept)."
say "the org MCP servers are NOT edited here: scripts/lib/cxo_mcp_config.py"
say "(C-level sessions) and lib/worker_mcp_config.py (workers) start them through"
say "the same wrapper once that node-file line is present AND the env file exists"
say "(W1.6). The env file alone is not the switch -- it predates this cutover. No"
say "git-tracked file is edited: the connection string carries a password and"
say "must never land in a commit, and rotating it means editing the env file once."
say "IMPORTANT: sessions and workers already running keep their old MCP config"
say "until they restart -- restart them after this step (see the step-1 reminder)."
if [ "$APPLY" -eq 1 ]; then
  "$PYTHON" scripts/hub/cutover_flip.py --apply
else
  "$PYTHON" scripts/hub/cutover_flip.py
fi

# --- step 5: verify round-trip, then checkpoint + archive ---------------
step 5 "verify a create_task round trip via lib.db, then checkpoint + archive state/tasks.db"
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
  # Checkpoints tasks.db's WAL (a recent commit can live only in
  # tasks.db-wal until then) and moves tasks.db + -wal + -shm together --
  # a plain `mv state/tasks.db ...` alone would silently drop rows still
  # sitting in the WAL (Org Mesh W1.1).
  "$ROOT/scripts/hub/wal-checkpoint-archive.sh" state/tasks.db "$ARCHIVE_PATH"
  ls -la "${ARCHIVE_PATH}"*
  # Loud tombstone: a directory at this path makes sqlite3.connect() raise
  # instead of silently creating a fresh empty tasks.db -- the exact split
  # brain this cutover removes, for any process still on the SQLite backend
  # (a C-level session not yet restarted onto ORG_DB_URL). lib/db.py's
  # _connect() and the self-repo-guard/log-prompt hooks recognise this
  # directory and fail loud/open respectively instead of crashing blind.
  mkdir "$ROOT/state/tasks.db"
  say "tombstoned: state/tasks.db is now a directory (was archived to $ARCHIVE_PATH,"
  say "  along with -wal/-shm if either existed)."
  say "to undo: rmdir state/tasks.db && mv $ARCHIVE_PATH state/tasks.db"
else
  say "would run: create_task()+get_task() round trip via lib.db with ORG_DB_URL set"
  say "would then run: sqlite3 state/tasks.db 'PRAGMA wal_checkpoint(TRUNCATE);'"
  say "  (retry up to 5x on busy, then refuse -- never move a WAL with pending data)"
  say "would then run: mv state/tasks.db{,-wal,-shm} (whichever exist) to"
  say "  ${ARCHIVE_PATH}{,-wal,-shm} && ls -la ${ARCHIVE_PATH}*"
  say "would then run: mkdir $ROOT/state/tasks.db (tombstone -- makes a"
  say "  pre-cutover session's sqlite connect attempt fail loudly instead of"
  say "  silently recreating an empty tasks.db)"
  say "to undo after --apply: rmdir state/tasks.db && mv $ARCHIVE_PATH state/tasks.db"
fi

say ""
say "== summary =="
say "what changed:   ORG_DB_URL now flows through the watchdog + mac-agent launchd"
say "                plists; 'org_db: hub' is in the node file, so the MCP config"
say "                generators start the org MCP server of every session and"
say "                worker launched from now on through the wrapper;"
say "                state/tasks.db archived to"
say "                $ARCHIVE_PATH and replaced with a tombstone directory"
say "                (no writer can silently recreate an empty one)."
say "how to roll back: \"$PYTHON\" scripts/hub/cutover_flip.py --rollback --apply"
say "                (removes org_db: from the node file; new sessions go back to"
say "                the plain org entry); restore the two plists (git-untracked --"
say "                Time Machine, or re-run cutover_flip.py's logic in reverse);"
say "                rmdir state/tasks.db && mv $ARCHIVE_PATH state/tasks.db"
say "                (and ${ARCHIVE_PATH}-wal/-shm back to state/tasks.db-wal/-shm,"
say "                if either was archived)."
say "watchdog:       restarts automatically when this script exits (see step 2 cleanup)."

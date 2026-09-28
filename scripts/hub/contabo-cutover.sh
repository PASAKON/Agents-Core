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
# The actual steps live in scripts/hub/contabo-cutover-remote.sh (Org Mesh W1.1
# -- split out so that file is `bash -n`-checkable and directly runnable against
# a throwaway repo in tests/test_hub_cutover_scripts.py). This script is just the
# ssh transport: it pipes that file's content as stdin to `bash -s` on Contabo,
# same as when it was an inline heredoc here.
#
# Steps on Contabo (root over ssh alias mooniex-vps), each idempotent:
#   1. refuse while any cto-*/cxo-* tmux session is alive (those keep the old
#      sqlite backend until restarted). --sessions-closed overrides, only if you
#      ended them yourself and tmux is merely stale.
#   2. /opt/MoonieXHQ/Agents/Core: refuse on dirty tracked files (ignoring only the
#      weekly machine_doctor cron's rewrite of state/machine-discovered-*.yaml);
#      keep a backup branch of the current local main; fast-forward main to
#      origin/main only (refuses with a clear message if that isn't possible --
#      never force-resets main, so a local commit that hasn't been pushed yet is
#      never silently discarded).
#   3. .venv: install psycopg[binary] only -- a full `pip install -r requirements.txt`
#      pulls mcp 2.x, which breaks runners/cto_mcp_server.py's mcp-1.x FastMCP usage.
#   4. append ORG_DB_URL / ORG_TEST_DB_URL to /root/.config/mooniex/org-db.env
#      (host 100.118.171.23 -- the container binds the tailnet IP, not loopback).
#   5. import this box's own registry rows into the hub (ids never collide with
#      the Mac's: checked 2026-09-18, 0 of 11 overlapped), then verify per-table
#      row counts (sqlite before vs postgres after) match -- refuses on mismatch,
#      before anything is archived.
#   6. checkpoint the WAL (PRAGMA wal_checkpoint(TRUNCATE), retried on busy) so a
#      commit still sitting only in tasks.db-wal is folded into the main file,
#      then archive state/tasks.db together with -wal/-shm (whichever exist) and
#      leave a DIRECTORY tombstone in its place, so a process still on the sqlite
#      backend fails loudly instead of silently creating an empty database (the
#      split brain this whole change removes).
#   7. read the hub back through lib.db and print the row counts.
#
# Rollback:
#   ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core && rmdir state/tasks.db &&
#     mv state/tasks.db.archived-<date> state/tasks.db &&
#     mv state/tasks.db.archived-<date>-wal state/tasks.db-wal 2>/dev/null;
#     mv state/tasks.db.archived-<date>-shm state/tasks.db-shm 2>/dev/null;
#     git checkout backup/main-before-hub-<date>'
#   then delete the two ORG_*_URL lines from /root/.config/mooniex/org-db.env.
set -euo pipefail
HOST_ALIAS="${HOST_ALIAS:-mooniex-vps}"
FLAG="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_SCRIPT="$SCRIPT_DIR/contabo-cutover-remote.sh"
echo "== [contabo] hub cutover (alias=$HOST_ALIAS) =="
ssh -o ConnectTimeout=15 -o BatchMode=yes "$HOST_ALIAS" "FLAG='$FLAG' bash -s" < "$REMOTE_SCRIPT"

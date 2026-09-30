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
#   4. ORG_DB_URL comes from Infisical Agents-Core/prod, never from an env file
#      (CLAUDE.md §Secrets; nothing is appended to /root/.config/mooniex/org-db.env,
#      and ORG_TEST_DB_URL is gone: nothing here reads it). Refuse unless it
#      connects (tools/infisical_setup.py run Agents-Core prod --as contabo).
#      Then copy the three drop-ins deploy/systemd/<unit>.service.d/org-db.conf
#      (watchdog, secretary, secretary-waker) into /etc/systemd/system/, write
#      `org_db: hub` into /root/.config/mooniex/node.yaml (the switch for the
#      C-level MCP servers and workers), and `systemctl daemon-reload`.
#      Design: docs/design/org-mesh-w18-contabo-consumers.md.
#   5. import this box's own registry rows into the hub (ids never collide with
#      the Mac's: checked 2026-09-18, 0 of 11 overlapped), then verify per-table
#      row counts (sqlite before vs postgres after) match -- refuses on mismatch,
#      before anything is archived. ORG_DB_URL reaches these commands through
#      infisical run, not through a sourced file.
#   6. checkpoint the WAL (PRAGMA wal_checkpoint(TRUNCATE), retried on busy) so a
#      commit still sitting only in tasks.db-wal is folded into the main file,
#      then archive state/tasks.db together with -wal/-shm (whichever exist) and
#      leave a DIRECTORY tombstone in its place, so a process still on the sqlite
#      backend fails loudly instead of silently creating an empty database (the
#      split brain this whole change removes).
#   7. read the hub back through lib.db and print the row counts.
#   8. restart mooniex-watchdog, mooniex-secretary and mooniex-secretary-waker
#      (last, after the migration and the tombstone) and require all three active.
#
# Rollback:
#   ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core && rmdir state/tasks.db &&
#     mv state/tasks.db.archived-<date> state/tasks.db &&
#     mv state/tasks.db.archived-<date>-wal state/tasks.db-wal 2>/dev/null;
#     mv state/tasks.db.archived-<date>-shm state/tasks.db-shm 2>/dev/null;
#     git checkout backup/main-before-hub-<date>'
#   then remove the drop-ins and the switch, and restart the three units:
#   ssh mooniex-vps 'cd /opt/MoonieXHQ/Agents/Core &&
#     for u in mooniex-watchdog mooniex-secretary mooniex-secretary-waker;
#       do rm -f /etc/systemd/system/$u.service.d/org-db.conf; done &&
#     python3 scripts/hub/cutover_flip.py --rollback --apply &&
#     systemctl daemon-reload &&
#     systemctl restart mooniex-watchdog mooniex-secretary mooniex-secretary-waker'
#   (cutover_flip.py --rollback removes only the `org_db:` line of
#   /root/.config/mooniex/node.yaml; it does not touch launchd plists.)
#   Nothing was ever appended to org-db.env, so there is nothing to delete there.
set -euo pipefail
HOST_ALIAS="${HOST_ALIAS:-mooniex-vps}"
FLAG="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REMOTE_SCRIPT="$SCRIPT_DIR/contabo-cutover-remote.sh"
echo "== [contabo] hub cutover (alias=$HOST_ALIAS) =="
ssh -o ConnectTimeout=15 -o BatchMode=yes "$HOST_ALIAS" "FLAG='$FLAG' bash -s" < "$REMOTE_SCRIPT"

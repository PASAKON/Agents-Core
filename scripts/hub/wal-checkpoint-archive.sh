#!/usr/bin/env bash
# scripts/hub/wal-checkpoint-archive.sh -- checkpoint a WAL-mode SQLite db,
# then move it (plus -wal/-shm, whichever exist) to an archive path.
#
# Shared by scripts/hub/cutover-mac.sh and scripts/hub/contabo-cutover-
# remote.sh (Org Mesh W1.1, docs/design/tasks-db-hub.md) so the "checkpoint,
# then move all three files together" step exists exactly once, and so it
# can be tested directly (tests/test_hub_cutover_scripts.py) without
# spinning up either cutover script's surrounding machinery.
#
# tasks.db runs in WAL mode (lib/db.py) -- a recently committed row can live
# ONLY in <db_path>-wal until checkpointed into the main file. Moving just
# <db_path> silently drops it (measured: a copy of the main file alone, made
# while a writer held the WAL open, was missing the table entirely). `PRAGMA
# wal_checkpoint(TRUNCATE)` folds every WAL frame into the main file and
# truncates the WAL to empty on success; its first result column ("busy") is
# 0 only when nothing else held a lock during the checkpoint -- a nonzero
# value means the checkpoint did NOT fully complete, so this retries a few
# times, then refuses rather than moving a half-checkpointed db.
#
# Usage: wal-checkpoint-archive.sh <db_path> <archive_path>
set -euo pipefail

SQLITE3_BIN="${SQLITE3_BIN:-sqlite3}"
DB="${1:?usage: wal-checkpoint-archive.sh <db_path> <archive_path>}"
ARCHIVE="${2:?usage: wal-checkpoint-archive.sh <db_path> <archive_path>}"

if [ ! -f "$DB" ]; then
  echo "wal-checkpoint-archive: no such file: $DB" >&2
  exit 1
fi

ok=0
for attempt in 1 2 3 4 5; do
  out="$("$SQLITE3_BIN" "$DB" 'PRAGMA wal_checkpoint(TRUNCATE);')"
  busy="${out%%|*}"
  if [ "$busy" = "0" ]; then
    echo "wal checkpoint ok: $DB ($out -- busy|log_frames|checkpointed_frames)"
    ok=1
    break
  fi
  echo "wal checkpoint busy (attempt $attempt/5): $DB ($out) -- retrying"
  sleep 1
done
if [ "$ok" -ne 1 ]; then
  echo "" >&2
  echo "REFUSING: wal_checkpoint(TRUNCATE) stayed busy after 5 attempts on $DB." >&2
  echo "Another connection is holding a read lock -- retry once it is idle." >&2
  exit 1
fi

mv "$DB" "$ARCHIVE"
moved="$ARCHIVE"
if [ -f "${DB}-wal" ]; then
  mv "${DB}-wal" "${ARCHIVE}-wal"
  moved="$moved ${ARCHIVE}-wal"
fi
if [ -f "${DB}-shm" ]; then
  mv "${DB}-shm" "${ARCHIVE}-shm"
  moved="$moved ${ARCHIVE}-shm"
fi
echo "archived: $moved"

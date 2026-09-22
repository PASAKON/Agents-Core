#!/usr/bin/env bash
# vps-backup-weekly.sh — weekly Gate-#1-style backup + 2nd copy to Google Drive.
# CEO rule (2026-06-11): 2nd copy in Drive "Project Backup", every 7 days,
# NEVER overwrite an existing copy (each run = its own timestamp dir).
# Scheduled by ~/Library/LaunchAgents/com.mooniex.vps-backup-weekly.plist
set -euo pipefail

AGENTS_DIR="/Users/gob/MoonieXHQ/Agents/Core"
ENGINE="$AGENTS_DIR/scripts/vps-backup.sh"
DEST_ROOT="$HOME/Backups/mooniex-vps"
DRIVE_DIR="$HOME/Library/CloudStorage/GoogleDrive-pass.gob1@gmail.com/ไดรฟ์ของฉัน/MoonieX/Project Backup/MoonieX/vps-hostinger"
LOG="$HOME/Library/Logs/mooniex-vps-backup.log"

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" | tee -a "$LOG"; }

mkdir -p "$(dirname "$LOG")"
log "=== weekly backup start ==="

# Drive Desktop must be mounted, else no 2nd copy — fail loudly, don't half-run
if [ ! -d "$(dirname "$DRIVE_DIR")" ]; then
  log "FATAL: Google Drive mount not found ($(dirname "$DRIVE_DIR")) — is Google Drive.app running?"
  exit 1
fi

# 1) fresh pull (new UTC-timestamp dir under ~/Backups — engine never reuses a dir)
log "running engine backup --delta"
if ! "$ENGINE" backup --delta >>"$LOG" 2>&1; then
  log "FATAL: backup reported item failure(s) — NOT uploading a broken run. See log above."
  exit 1
fi

RUN_DIR="$(ls -d "$DEST_ROOT"/2*Z 2>/dev/null | sort | tail -1)"
[ -n "$RUN_DIR" ] && [ -d "$RUN_DIR" ] || { log "FATAL: no run dir found after backup"; exit 1; }
RUN_NAME="$(basename "$RUN_DIR")"
log "run dir: $RUN_NAME"

# 2) verify before upload — only verified backups reach Drive
log "running engine verify"
if ! "$ENGINE" verify "$RUN_DIR" >>"$LOG" 2>&1; then
  log "FATAL: verify FAILED — NOT uploading. Investigate $RUN_DIR"
  exit 1
fi

# 3) 2nd copy to Drive — ENCRYPTED single archive per run.
#    The run contains 5 .env files (~167 secrets), the n8n encryption key,
#    SSH authorized_keys and a LINE wineprefix session: plaintext must never
#    leave this Mac. AES-256 passphrase lives in the macOS Keychain (CEO-set):
#      security add-generic-password -a mooniex -s vps-backup-enc -w
#    No-overwrite rule: each run = its own file name; abort if it exists.
PASS="$(security find-generic-password -a mooniex -s vps-backup-enc -w 2>/dev/null || true)"
if [ -z "$PASS" ]; then
  log "FATAL: Keychain item 'vps-backup-enc' (account mooniex) not found — CEO must run:"
  log "       security add-generic-password -a mooniex -s vps-backup-enc -w"
  exit 1
fi
DST_FILE="$DRIVE_DIR/vps-backup-$RUN_NAME.tar.gz.enc"
if [ -e "$DST_FILE" ]; then
  log "FATAL: $DST_FILE already exists — refusing to overwrite (CEO no-overwrite rule)"
  exit 1
fi
mkdir -p "$DRIVE_DIR"
log "encrypting $RUN_NAME -> $(basename "$DST_FILE") (AES-256-CBC, pbkdf2)"
export BK_PASS="$PASS"  # env: form keeps the passphrase out of ps/argv; cleared below
tar -czf - -C "$DEST_ROOT" "$RUN_NAME" \
  | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:BK_PASS \
  > "$DST_FILE".partial 2>>"$LOG" || { unset BK_PASS PASS; log "FATAL: encrypt failed"; rm -f "$DST_FILE".partial; exit 1; }
unset BK_PASS PASS
mv "$DST_FILE".partial "$DST_FILE"
# browsable plaintext metadata (no secrets): summary + hash manifest
cp "$RUN_DIR/SUMMARY.txt"          "$DRIVE_DIR/vps-backup-$RUN_NAME.SUMMARY.txt"          2>>"$LOG" || true
cp "$RUN_DIR/sha256-manifest.txt"  "$DRIVE_DIR/vps-backup-$RUN_NAME.sha256-manifest.txt"  2>>"$LOG" || true
SIZE="$(du -sh "$DST_FILE" | cut -f1)"
log "Drive copy staged: $(basename "$DST_FILE") ($SIZE) — restore: openssl enc -d -aes-256-cbc -pbkdf2 -in <file> | tar -xzf -"

# 4) prune NOTHING — retention is CEO's call. Report footprint instead.
TOTAL_LOCAL="$(du -sh "$DEST_ROOT" 2>/dev/null | cut -f1)"
TOTAL_DRIVE="$(du -sh "$DRIVE_DIR" 2>/dev/null | cut -f1)"
log "footprint: local $TOTAL_LOCAL at $DEST_ROOT | Drive $TOTAL_DRIVE at vps-hostinger/"
log "=== weekly backup done: $RUN_NAME ==="

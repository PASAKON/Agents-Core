#!/usr/bin/env bash
# Install / uninstall the ARCHIVE broker (runners/drive_photo_broker.py, run
# as a THIRD independent instance) and the SomPong archive filer
# (runners/sompong_archive_filer.py) as systemd services on Contabo --
# task-3f9b62a0, contract of record: org wiki `mooniex:projects/sompong-ea.md`
# section E.
#
#   scripts/install-archive-uploader.sh install <credential-source-file>
#   scripts/install-archive-uploader.sh uninstall
#   scripts/install-archive-uploader.sh status
#
# <credential-source-file> is a path ON CONTABO to an existing env file that
# already holds GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET /
# GOOGLE_OAUTH_REFRESH_TOKEN (e.g. claudeflow's .env), e.g.:
#   scripts/install-archive-uploader.sh install /opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/.env
#
# This script contains no secret and never prints one. It copies ONLY the
# three GOOGLE_OAUTH_* lines (never the whole source file, which may hold
# unrelated secrets) into ENV_FILE below, written root:archiveup, mode 0640
# -- same shape as scripts/install-share-broker.sh's credential file (a
# root-owned env file the broker can read but not rewrite). The broker
# process itself never gets the filer's own reach into the outbox, and the
# filer never gets the Drive credential -- same split as every other
# broker/filer pair in this repo.
#
# THIS IS A THIRD, INDEPENDENT instance of runners/drive_photo_broker.py --
# its own systemd unit, socket, staging dir, system user, and fixed Drive
# folder (the SomPong-LINE backup folder, CEO-approved id below). Differences
# from scripts/install-photo-broker.sh, spelled out because that is the file
# the two-unit shape was copied from:
#   - broker system user/group is `archiveup`, not `photoup`
#   - the credential file is root-owned mode 0640 (like install-share-broker.sh),
#     not broker-owned mode 600 (like install-photo-broker.sh/install-drive-broker.sh)
#   - the filer drains TWO kinds of outbox entries (closed-month text logs,
#     gzip'd before upload; media pairs) instead of one
#   - the outbox lives under /opt/MoonieXHQ/... (post-2026-09-23 ClaudeFlow
#     Contabo layout), not /root/projects/...
#
# The filer still runs as root (same reasoning as install-photo-broker.sh:
# ClaudeFlow's container may write the outbox as a uid the host has no
# other account for, and root can always read it regardless of that file's
# owner -- root already owns this whole box, this is not a new capability).
#
# guard_against_collision_with_existing_brokers() refuses to run at all if
# this script's own constants would ever touch mooniex-drive-broker,
# mooniex-drive-photo-broker, or mooniex-share-broker's unit/socket/folder --
# belt-and-braces against a copy-paste mistake, not something normal
# operation can trigger since all four sets of constants are hardcoded
# distinct.
#
# Idempotent: installing twice replaces the units + credential file and
# restarts, never duplicates. install/uninstall write to /etc/systemd/system,
# create a system user, and call systemctl, so they need root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

# --- this broker (drive_photo_broker.py, third instance) --------------------
BROKER_SERVICE="mooniex-drive-archive-broker"
BROKER_UNIT_PATH="/etc/systemd/system/${BROKER_SERVICE}.service"
BROKER_USER="archiveup"
BROKER_GROUP="archiveup"
BROKER_HOME="/home/${BROKER_USER}"
ENV_FILE="${BROKER_HOME}/.drive-archive.env"
BROKER_LOG_DIR="${BROKER_HOME}/logs"
BROKER_SOCKET_PATH="/run/archiveup/archive-broker.sock"   # RuntimeDirectory= recreates the parent dir every boot
STAGING_DIR="/var/lib/archiveup/staging"                  # root-run filer writes here, archiveup reads
FOLDER_ID="162JgquLAznKpw_UPL4fHKry4VjU5hQPd"             # SomPong-LINE backup folder, CEO-approved -- org wiki mooniex:projects/sompong-ea.md section E
MAX_UPLOAD_BYTES="536870912"     # 512 MiB -- matches runners/sompong_archive_filer.py's own upload-size caps
MAX_REQUEST_BYTES="65536"        # 64 KiB -- one JSON line naming a path + name + subfolder
SOCKET_TIMEOUT="30"               # seconds, request-line read only
REQUIRED_KEYS=(GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN)

# --- the filer (broker's one caller) ----------------------------------------
FILER_SERVICE="mooniex-sompong-archive-filer"
FILER_UNIT_PATH="/etc/systemd/system/${FILER_SERVICE}.service"
FILER_LOG_DIR="/var/log/mooniex-sompong-archive-filer"
DATA_DIR="/opt/MoonieXHQ/Projects/MoonieX/ClaudeFlow/data"   # ClaudeFlow's data dir -- the host bind-mount source, opened by path; org wiki mooniex:projects/sompong-ea.md section E
OUTBOX_DIR="${DATA_DIR}/sompong/archive-outbox"              # derived, for display only -- ClaudeFlow creates and owns this, this script never mkdir/chown/chmod it
FILER_STATE_DIR="/var/lib/mooniex-sompong-archive-filer"
FILER_MIN_FREE_MB="2048"
FILER_POLL_SECONDS="300"
FILER_MAX_RETRIES="5"

# --- the EXISTING brokers' constants (never touched by this script) --------
EXISTING_BROKER_SOCKET_PATH="/run/driveup/drive-broker.sock"          # scripts/install-drive-broker.sh
EXISTING_BROKER_FOLDER_ID="115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"
EXISTING_PHOTO_SOCKET_PATH="/run/photoup/photo-broker.sock"           # scripts/install-photo-broker.sh
EXISTING_PHOTO_FOLDER_ID="1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy"
EXISTING_SHARE_SOCKET_PATH="/run/mooniex-share-broker/broker.sock"    # scripts/install-share-broker.sh (main)
EXISTING_SHARE_FOLDER_ID="1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR"

usage() { echo "usage: $0 {install <credential-source-file>|uninstall|status}" >&2; exit 2; }

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: $1 needs root (creates users, writes systemd units, runs systemctl) -- rerun with sudo" >&2
    exit 1
  fi
}

guard_against_collision_with_existing_brokers() {
  local collided=0
  for pair in \
    "$BROKER_SOCKET_PATH:$EXISTING_BROKER_SOCKET_PATH:mooniex-drive-broker socket" \
    "$BROKER_SOCKET_PATH:$EXISTING_PHOTO_SOCKET_PATH:mooniex-drive-photo-broker socket" \
    "$BROKER_SOCKET_PATH:$EXISTING_SHARE_SOCKET_PATH:mooniex-share-broker socket" \
    "$FOLDER_ID:$EXISTING_BROKER_FOLDER_ID:mooniex-drive-broker folder" \
    "$FOLDER_ID:$EXISTING_PHOTO_FOLDER_ID:mooniex-drive-photo-broker folder" \
    "$FOLDER_ID:$EXISTING_SHARE_FOLDER_ID:mooniex-share-broker folder" \
  ; do
    local mine="${pair%%:*}"; local rest="${pair#*:}"; local theirs="${rest%%:*}"; local label="${rest#*:}"
    if [ "$mine" = "$theirs" ]; then
      echo "ERROR: this script's own constant collides with the existing $label -- refusing to run" >&2
      collided=1
    fi
  done
  if [ -S "$EXISTING_BROKER_SOCKET_PATH" ] && [ "$BROKER_SOCKET_PATH" = "$EXISTING_BROKER_SOCKET_PATH" ]; then
    echo "ERROR: would overwrite mooniex-drive-broker's live socket -- refusing to run" >&2
    collided=1
  fi
  if [ "$collided" -ne 0 ]; then
    exit 1
  fi
}

do_install() {
  require_root install
  guard_against_collision_with_existing_brokers
  local src="${1:-}"
  [ -n "$src" ] || { echo "ERROR: install needs a credential source file path" >&2; usage; }
  [ -f "$src" ] || { echo "ERROR: credential source file not found: $src" >&2; exit 1; }
  [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
  [ -f "$ROOT/runners/drive_photo_broker.py" ] || { echo "ERROR: runners/drive_photo_broker.py missing" >&2; exit 1; }
  [ -f "$ROOT/runners/sompong_archive_filer.py" ] || { echo "ERROR: runners/sompong_archive_filer.py missing" >&2; exit 1; }

  echo "== 1. ${BROKER_USER} system user/group (holds the Drive credential) =="
  if getent group "$BROKER_GROUP" >/dev/null; then
    echo "  group '$BROKER_GROUP' already exists"
  else
    groupadd --system "$BROKER_GROUP"
    echo "  created group '$BROKER_GROUP'"
  fi
  if id -u "$BROKER_USER" >/dev/null 2>&1; then
    echo "  user '$BROKER_USER' already exists"
  else
    useradd --system --gid "$BROKER_GROUP" --home-dir "$BROKER_HOME" --create-home \
            --shell /usr/sbin/nologin "$BROKER_USER"
    echo "  created user '$BROKER_USER' (home: $BROKER_HOME, no shell)"
  fi
  echo "OK 1-user"

  echo "== 2. outbox dir (ClaudeFlow creates and owns this -- this script never touches it) =="
  if [ -d "$OUTBOX_DIR" ]; then
    echo "  found: $OUTBOX_DIR -- leaving ownership/mode untouched (ClaudeFlow owns it, may hold live data)"
  else
    echo "  NOTICE: $OUTBOX_DIR does not exist yet -- ClaudeFlow has not deployed the archive-outbox writer."
    echo "  Not creating it: giving ${BROKER_USER} write access to a dir the design says the broker never"
    echo "  touches would be a permission overgrant. The filer idles harmlessly until ClaudeFlow creates it."
  fi
  echo "OK 2-outbox-dir"

  echo "== 3. staging dir (root-run filer writes verified copies, ${BROKER_USER} reads) =="
  mkdir -p "$STAGING_DIR"
  chown "root:${BROKER_GROUP}" "$STAGING_DIR"
  chmod 2770 "$STAGING_DIR"
  echo "  ready: $STAGING_DIR (owner root:${BROKER_GROUP}, mode 2770)"
  echo "OK 3-staging-dir"

  echo "== 4. log + state dirs =="
  mkdir -p "$BROKER_LOG_DIR"
  chown "${BROKER_USER}:${BROKER_GROUP}" "$BROKER_LOG_DIR"
  chmod 750 "$BROKER_LOG_DIR"
  mkdir -p "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  chown root:root "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  chmod 700 "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  echo "  ready: $BROKER_LOG_DIR, $FILER_LOG_DIR, $FILER_STATE_DIR"
  echo "OK 4-log-state-dirs"

  echo "== 5. credential file (root-owned, readable only by ${BROKER_USER} -- task instruction) =="
  local missing=()
  for key in "${REQUIRED_KEYS[@]}"; do
    if ! grep -qE "^[[:space:]]*(export[[:space:]]+)?${key}=" "$src"; then
      missing+=("$key")
    fi
  done
  if [ "${#missing[@]}" -ne 0 ]; then
    echo "ERROR: credential source is missing key(s): ${missing[*]}" >&2
    exit 1
  fi

  local tmp_env
  tmp_env="$(mktemp)"
  trap 'rm -f "$tmp_env"' EXIT
  umask 077
  : > "$tmp_env"
  for key in "${REQUIRED_KEYS[@]}"; do
    grep -E "^[[:space:]]*(export[[:space:]]+)?${key}=" "$src" | tail -n1 >> "$tmp_env"
  done
  install -m 640 -o root -g "$BROKER_GROUP" "$tmp_env" "$ENV_FILE"
  rm -f "$tmp_env"
  trap - EXIT
  echo "  wrote $ENV_FILE (mode 640, owner root:${BROKER_GROUP})"
  echo "  copied keys (names only): ${REQUIRED_KEYS[*]}"
  echo "OK 5-credential-file"

  echo "== 6. broker systemd unit =="
  local filer_uid=0   # the filer runs as root -- uid 0 is always 0, no need to look it up

  cat > "$BROKER_UNIT_PATH" <<UNIT_EOF
[Unit]
Description=MoonieX Drive ARCHIVE broker -- sole holder of the Drive OAuth credential for SomPong's LINE archive backup (task-3f9b62a0). Separate from mooniex-drive-broker, mooniex-drive-photo-broker, and mooniex-share-broker -- never touch those units from here.
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${BROKER_USER}
Group=${BROKER_GROUP}
WorkingDirectory=${ROOT}
RuntimeDirectory=${BROKER_USER}
RuntimeDirectoryMode=0750
EnvironmentFile=${ENV_FILE}
Environment=DRIVE_PHOTO_BROKER_ENV=${ENV_FILE}
Environment=DRIVE_PHOTO_BROKER_SOCKET_PATH=${BROKER_SOCKET_PATH}
Environment=DRIVE_PHOTO_BROKER_STAGING_ROOT=${STAGING_DIR}
Environment=DRIVE_PHOTO_BROKER_ALLOWED_UIDS=${filer_uid}
Environment=DRIVE_PHOTO_BROKER_FOLDER_ID=${FOLDER_ID}
Environment=DRIVE_PHOTO_BROKER_MAX_UPLOAD_BYTES=${MAX_UPLOAD_BYTES}
Environment=DRIVE_PHOTO_BROKER_MAX_REQUEST_BYTES=${MAX_REQUEST_BYTES}
Environment=DRIVE_PHOTO_BROKER_SOCKET_TIMEOUT=${SOCKET_TIMEOUT}
Environment=ORG_LOG_DIR=${BROKER_LOG_DIR}
ExecStart=${PYTHON} -m runners.drive_photo_broker
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${STAGING_DIR} ${BROKER_LOG_DIR}

[Install]
WantedBy=multi-user.target
UNIT_EOF
  echo "  wrote $BROKER_UNIT_PATH"
  echo "OK 6-broker-unit"

  echo "== 7. filer systemd unit =="
  cat > "$FILER_UNIT_PATH" <<UNIT_EOF
[Unit]
Description=SomPong LINE archive outbox drain -- reads ClaudeFlow's archive-outbox and uploads closed-month text logs (gzip'd) and media pairs through the Drive archive broker's socket (task-3f9b62a0). Runs as root so it can read the outbox regardless of the container's own uid mapping -- see docs/design/sompong-archive.md. Never touches the Drive credential directly.
After=network-online.target ${BROKER_SERVICE}.service
Wants=network-online.target
Requires=${BROKER_SERVICE}.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${ROOT}
Environment=SOMPONG_ARCHIVE_DATA_DIR=${DATA_DIR}
Environment=SOMPONG_ARCHIVE_STAGING_ROOT=${STAGING_DIR}
Environment=SOMPONG_ARCHIVE_MIN_FREE_MB=${FILER_MIN_FREE_MB}
Environment=SOMPONG_ARCHIVE_BROKER_SOCKET_PATH=${BROKER_SOCKET_PATH}
Environment=SOMPONG_ARCHIVE_FILER_POLL_SECONDS=${FILER_POLL_SECONDS}
Environment=SOMPONG_ARCHIVE_FILER_MAX_RETRIES=${FILER_MAX_RETRIES}
Environment=SOMPONG_ARCHIVE_FILER_STATE_DIR=${FILER_STATE_DIR}
Environment=ORG_LOG_DIR=${FILER_LOG_DIR}
ExecStart=${PYTHON} -m runners.sompong_archive_filer
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${DATA_DIR} ${STAGING_DIR} ${FILER_LOG_DIR} ${FILER_STATE_DIR}

[Install]
WantedBy=multi-user.target
UNIT_EOF
  echo "  wrote $FILER_UNIT_PATH"
  echo "OK 7-filer-unit"

  systemctl daemon-reload
  systemctl enable "$BROKER_SERVICE" "$FILER_SERVICE"
  systemctl restart "$BROKER_SERVICE"
  systemctl restart "$FILER_SERVICE" || true
  echo "  installed + started: $BROKER_SERVICE, $FILER_SERVICE"
  echo "OK 8-start"

  echo
  echo "== summary =="
  echo "  broker service:  $BROKER_SERVICE  (user ${BROKER_USER}, group ${BROKER_GROUP})"
  echo "  filer service:   $FILER_SERVICE  (user root)"
  echo "  socket:          $BROKER_SOCKET_PATH  (0660, group ${BROKER_GROUP} only)"
  echo "  outbox:          $OUTBOX_DIR  (root-run filer only -- ${BROKER_USER} never opens a path here)"
  echo "  staging:         $STAGING_DIR  (owner root:${BROKER_GROUP}, mode 2770)"
  echo "  folder id:       $FOLDER_ID  (SomPong-LINE backup, fixed, never client-supplied)"
  echo "  allowed uid:     $filer_uid  (root -- the filer)"
  echo "  credential file: $ENV_FILE  (mode 640, owner root:${BROKER_GROUP})"
  echo "  logs:            journalctl -u $BROKER_SERVICE -f"
  echo "                   journalctl -u $FILER_SERVICE -f"
}

do_uninstall() {
  require_root uninstall
  guard_against_collision_with_existing_brokers
  systemctl stop "$FILER_SERVICE" 2>/dev/null || true
  systemctl stop "$BROKER_SERVICE" 2>/dev/null || true
  systemctl disable "$FILER_SERVICE" 2>/dev/null || true
  systemctl disable "$BROKER_SERVICE" 2>/dev/null || true
  rm -f "$FILER_UNIT_PATH" "$BROKER_UNIT_PATH"
  systemctl daemon-reload
  echo "uninstalled: $BROKER_SERVICE, $FILER_SERVICE"
  echo "(left in place: ${BROKER_USER} user/group, ${ENV_FILE}, ${OUTBOX_DIR}, ${STAGING_DIR}, ${FILER_STATE_DIR} --"
  echo " remove by hand if truly done with this; the outbox may hold un-filed archives, never delete it without checking first)"
}

do_status() {
  for service in "$BROKER_SERVICE" "$FILER_SERVICE"; do
    echo "--- $service ---"
    if systemctl is-active --quiet "$service" 2>/dev/null; then echo "active:  yes"; else echo "active:  no"; fi
    if systemctl is-enabled --quiet "$service" 2>/dev/null; then echo "enabled: yes"; else echo "enabled: no"; fi
    echo "recent log lines:"
    journalctl -u "$service" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
    echo
  done
  if [ -S "$BROKER_SOCKET_PATH" ]; then
    echo "socket:  $BROKER_SOCKET_PATH ($(stat -c '%U:%G %a' "$BROKER_SOCKET_PATH" 2>/dev/null || stat -f '%Su:%Sg %Lp' "$BROKER_SOCKET_PATH"))"
  else
    echo "socket:  (not present)"
  fi
  if [ -f "$ENV_FILE" ]; then echo "credential file: present"; else echo "credential file: MISSING -- $ENV_FILE"; fi
}

case "${1:-}" in
  install)   shift; do_install "${1:-}" ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

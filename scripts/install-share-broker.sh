#!/usr/bin/env bash
# Install / uninstall the Drive SHARE broker (runners/drive_share_broker.py)
# as a systemd service on Contabo -- task-1c07d46b, contract of record: org
# wiki `mooniex:projects/sompong-ea.md` section D, ADR 0032. The broker is
# the ONLY thing on the box that ever reads the Drive OAuth credential this
# feature uses; SomPong's EA runner (running as `sompong`) talks to it over
# a group-gated unix socket and can only ask it to share a file into ONE
# CEO-approved fixed folder, `SomPong Share/`.
#
#   scripts/install-share-broker.sh install <credential-source-file>
#   scripts/install-share-broker.sh uninstall
#   scripts/install-share-broker.sh status
#
# <credential-source-file> is a path ON CONTABO to an existing env file that
# already holds GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET /
# GOOGLE_OAUTH_REFRESH_TOKEN (e.g. claudeflow's .env) -- e.g.:
#   scripts/install-share-broker.sh install /root/projects/mooniex-claudeflow/.env
#
# This script contains no secret and never prints one. It copies ONLY the
# three GOOGLE_OAUTH_* lines (never the whole source file, which may hold
# unrelated secrets) into ENV_FILE below. UNLIKE scripts/install-drive-broker.sh
# and scripts/install-photo-broker.sh (whose credential files are owned by
# the broker's own account), this one is written root:shareup, mode 0640 --
# task instruction: "a root-owned env file readable only by the broker
# user." The broker still reads it directly (runners/drive_share_broker.py
# opens DRIVE_SHARE_BROKER_ENV itself, the same way its siblings do), it
# just cannot rewrite its own credential file.
#
# Modelled on scripts/install-photo-broker.sh and scripts/install-drive-broker.sh
# (read either for the fuller containment reasoning) but for a THIRD,
# independent broker: its own systemd unit, its own socket, its own uid
# allowlist, its own system user, its own fixed Drive folder
# ("SomPong Share/"). Differences from install-photo-broker.sh, spelled out
# because that is the file this was copied from:
#   - the broker's system user/group is `shareup`, not `photoup`
#   - there is ONE fixed folder and no per-month subfolders -- no month-
#     folder resolve-or-create step exists here
#   - the caller is `sompong` (SomPong's own EA runner, org wiki
#     mooniex:projects/sompong-ea.md), a pre-existing account this script
#     does not create -- not root, unlike the photo broker's filer
#   - the credential file is root-owned (see above), not broker-owned
#
# Idempotent: installing twice replaces the unit + credential file and
# restarts, never duplicates. install/uninstall write to /etc/systemd/system,
# create a system user, and call systemctl, so they need root.
set -euo pipefail

SERVICE="mooniex-share-broker"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
PYTHON="$ROOT/.venv/bin/python"
BROKER_USER="shareup"
BROKER_GROUP="shareup"
CALLER_USER="sompong"            # SomPong's EA runner -- the only account allowed to call in
BROKER_HOME="/home/${BROKER_USER}"
ENV_FILE="${BROKER_HOME}/.drive-share.env"
LOG_DIR="${BROKER_HOME}/logs"
STAGING_DIR="/var/lib/sompong-share/staging"      # contract-fixed path, org wiki section D
SOCKET_PATH="/run/mooniex-share-broker/broker.sock"   # contract-fixed path; RuntimeDirectory= recreates the parent dir every boot
FOLDER_ID="1Qn7B0e6Pa7y8gS5bjUfs-f5ewMIERUsR"     # "SomPong Share/" at the Drive root -- CEO-approved 2026-09-26
MAX_MB="300"                      # DRIVE_SHARE_MAX_MB -- task-fixed default
MAX_REQUEST_BYTES="65536"         # 64 KiB -- one JSON line naming a path + display name
SOCKET_TIMEOUT="30"               # seconds, request-line read only
REQUIRED_KEYS=(GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN)

usage() { echo "usage: $0 {install <credential-source-file>|uninstall|status}" >&2; exit 2; }

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: $1 needs root (creates a user, writes $UNIT_PATH, runs systemctl) -- rerun with sudo" >&2
    exit 1
  fi
}

do_install() {
  require_root install
  local src="${1:-}"
  [ -n "$src" ] || { echo "ERROR: install needs a credential source file path" >&2; usage; }
  [ -f "$src" ] || { echo "ERROR: credential source file not found: $src" >&2; exit 1; }
  [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
  [ -f "$ROOT/runners/drive_share_broker.py" ] || { echo "ERROR: runners/drive_share_broker.py missing" >&2; exit 1; }
  id -u "$CALLER_USER" >/dev/null 2>&1 || { echo "ERROR: user '$CALLER_USER' does not exist yet (SomPong EA runner not provisioned?)" >&2; exit 1; }

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

  echo "== 2. ${CALLER_USER} -> ${BROKER_GROUP} group (so it can reach the socket + staging dir) =="
  if id -nG "$CALLER_USER" | tr ' ' '\n' | grep -qx "$BROKER_GROUP"; then
    echo "  '$CALLER_USER' already in '$BROKER_GROUP'"
  else
    usermod -aG "$BROKER_GROUP" "$CALLER_USER"
    echo "  added '$CALLER_USER' to '$BROKER_GROUP'"
    echo "  *** NEW GROUP MEMBERSHIP ONLY TAKES EFFECT ON A NEW LOGIN SESSION ***"
    echo "  *** restart SomPong's own EA runner service now"
  fi
  echo "OK 2-caller-group"

  echo "== 3. staging dir (${CALLER_USER} writes, ${BROKER_USER} reads) =="
  mkdir -p "$STAGING_DIR"
  chown "${CALLER_USER}:${BROKER_GROUP}" "$STAGING_DIR"
  chmod 2770 "$STAGING_DIR"   # rwxrws--- + setgid: sompong(owner) rwx, shareup(group) rwx, others none; setgid so staged files stay group=shareup
  echo "  ready: $STAGING_DIR (owner ${CALLER_USER}:${BROKER_GROUP}, mode 2770)"
  echo "OK 3-staging-dir"

  echo "== 4. log dir =="
  mkdir -p "$LOG_DIR"
  chown "${BROKER_USER}:${BROKER_GROUP}" "$LOG_DIR"
  chmod 750 "$LOG_DIR"
  echo "  ready: $LOG_DIR"
  echo "OK 4-log-dir"

  echo "== 5. credential file (root-owned, readable only by ${BROKER_USER} -- task instruction) =="
  local missing=() found=()
  for key in "${REQUIRED_KEYS[@]}"; do
    if grep -qE "^[[:space:]]*(export[[:space:]]+)?${key}=" "$src"; then
      found+=("$key")
    else
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

  echo "== 6. systemd unit =="
  local caller_uid
  caller_uid="$(id -u "$CALLER_USER")"

  cat > "$UNIT_PATH" <<UNIT_EOF
[Unit]
Description=MoonieX Drive SHARE broker -- sole holder of the Drive OAuth credential for SomPong's one-folder public-link feature (task-1c07d46b). SomPong (sompong) can only reach it over a group-gated unix socket to share a file into the fixed "SomPong Share/" folder. Never touches mooniex-drive-broker or mooniex-drive-photo-broker.
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${BROKER_USER}
Group=${BROKER_GROUP}
WorkingDirectory=${ROOT}
RuntimeDirectory=mooniex-share-broker
RuntimeDirectoryMode=0750
EnvironmentFile=${ENV_FILE}
Environment=DRIVE_SHARE_BROKER_ENV=${ENV_FILE}
Environment=DRIVE_SHARE_BROKER_SOCKET_PATH=${SOCKET_PATH}
Environment=DRIVE_SHARE_BROKER_STAGING_ROOT=${STAGING_DIR}
Environment=DRIVE_SHARE_BROKER_ALLOWED_UIDS=${caller_uid}
Environment=DRIVE_SHARE_BROKER_FOLDER_ID=${FOLDER_ID}
Environment=DRIVE_SHARE_MAX_MB=${MAX_MB}
Environment=DRIVE_SHARE_BROKER_MAX_REQUEST_BYTES=${MAX_REQUEST_BYTES}
Environment=DRIVE_SHARE_BROKER_SOCKET_TIMEOUT=${SOCKET_TIMEOUT}
Environment=ORG_LOG_DIR=${LOG_DIR}
ExecStart=${PYTHON} -m runners.drive_share_broker
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${STAGING_DIR} ${LOG_DIR}

[Install]
WantedBy=multi-user.target
UNIT_EOF
  echo "  wrote $UNIT_PATH"
  echo "OK 6-systemd-unit"

  systemctl daemon-reload
  systemctl enable "$SERVICE"
  systemctl restart "$SERVICE"
  echo "  installed + started: $SERVICE"
  echo "OK 7-start"

  echo
  echo "== summary =="
  echo "  service:      $SERVICE  (user ${BROKER_USER}, group ${BROKER_GROUP})"
  echo "  socket:       $SOCKET_PATH  (0660, group ${BROKER_GROUP} only)"
  echo "  staging root: $STAGING_DIR  (${CALLER_USER} writes, ${BROKER_USER} reads)"
  echo "  folder id:    $FOLDER_ID  (\"SomPong Share/\", fixed, never client-supplied)"
  echo "  allowed uid:  $caller_uid  ($CALLER_USER)"
  echo "  caller-side:  set the socket path above in ${CALLER_USER}'s environment"
  echo "  logs:         journalctl -u $SERVICE -f"
}

do_uninstall() {
  require_root uninstall
  systemctl stop "$SERVICE" 2>/dev/null || true
  systemctl disable "$SERVICE" 2>/dev/null || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
  echo "uninstalled: $SERVICE"
  echo "(left in place: ${BROKER_USER} user/group, ${ENV_FILE}, ${STAGING_DIR}, ${LOG_DIR} -- remove by hand if truly done with this;"
  echo " the staging dir may hold an in-flight staged file, never delete it without checking first)"
}

do_status() {
  if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
    echo "active:  yes"
  else
    echo "active:  no"
  fi
  if systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then
    echo "enabled: yes"
  else
    echo "enabled: no"
  fi
  if [ -f "$UNIT_PATH" ]; then echo "unit:    $UNIT_PATH"; else echo "unit:    (missing)"; fi
  if [ -S "$SOCKET_PATH" ]; then echo "socket:  $SOCKET_PATH ($(stat -c '%U:%G %a' "$SOCKET_PATH" 2>/dev/null || stat -f '%Su:%Sg %Lp' "$SOCKET_PATH"))"; else echo "socket:  (not present)"; fi
  if [ -f "$ENV_FILE" ]; then echo "credential file: present"; else echo "credential file: MISSING -- $ENV_FILE"; fi
  echo "recent log lines:"
  journalctl -u "$SERVICE" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
}

case "${1:-}" in
  install)   shift; do_install "${1:-}" ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

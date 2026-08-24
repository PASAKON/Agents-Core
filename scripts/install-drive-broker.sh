#!/usr/bin/env bash
# Install / uninstall the Drive upload broker (runners/drive_upload_broker.py)
# as a systemd service on Contabo -- task-e713c4e2, CEO order: "เจาะระบบ
# SomPong ยากขึ้น 1 Step". The broker is the ONLY thing on the box that ever
# reads the Drive OAuth credential; SomPong (running as `secretary`, which
# has no sudo) talks to it over a group-gated unix socket and can only ask
# it to upload a file into one fixed folder.
#
#   scripts/install-drive-broker.sh install <credential-source-file>
#   scripts/install-drive-broker.sh uninstall
#   scripts/install-drive-broker.sh status
#
# <credential-source-file> is a path ON CONTABO to an existing env file that
# already holds GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET /
# GOOGLE_OAUTH_REFRESH_TOKEN (e.g. claudeflow's .env) -- e.g.:
#   scripts/install-drive-broker.sh install /root/projects/mooniex-claudeflow/.env
#
# This script contains no secret and never prints one. It copies ONLY the
# three GOOGLE_OAUTH_* lines (never the whole source file, which may hold
# unrelated secrets) into /home/driveup/.drive.env, mode 600, owned by
# driveup:driveup -- and prints only the key NAMES it copied, never values.
#
# Idempotent: installing twice replaces the unit + credential file and
# restarts, never duplicates. Same shape as scripts/install-secretary-waker.sh
# (systemd install/uninstall/status). install/uninstall write to
# /etc/systemd/system, create a system user, and call systemctl, so they
# need root.
set -euo pipefail

SERVICE="mooniex-drive-broker"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
PYTHON="$ROOT/.venv/bin/python"
BROKER_USER="driveup"
BROKER_GROUP="driveup"
CALLER_USER="secretary"          # SomPong -- the only account allowed to call in
BROKER_HOME="/home/${BROKER_USER}"
ENV_FILE="${BROKER_HOME}/.drive.env"
LOG_DIR="${BROKER_HOME}/logs"
STAGING_DIR="/srv/driveup-staging"
SOCKET_PATH="/run/driveup/drive-broker.sock"     # RuntimeDirectory= recreates the parent dir every boot
FOLDER_ID="115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"    # CEO's Desktop Cloud root -- see .claude/skills/gdrive-filing/SKILL.md
MAX_UPLOAD_BYTES="524288000"     # 500 MiB
MAX_REQUEST_BYTES="65536"        # 64 KiB -- one JSON line naming a path, plenty
SOCKET_TIMEOUT="30"              # seconds, request-line read only (ilag_sync's own upload timeouts are separate: 60s init / 1800s PUT)
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
  [ -f "$ROOT/runners/drive_upload_broker.py" ] || { echo "ERROR: runners/drive_upload_broker.py missing" >&2; exit 1; }
  id -u "$CALLER_USER" >/dev/null 2>&1 || { echo "ERROR: user '$CALLER_USER' does not exist yet (SomPong not provisioned?)" >&2; exit 1; }

  echo "== 1. driveup system user/group =="
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

  echo "== 2. $CALLER_USER -> $BROKER_GROUP group (so it can reach the socket) =="
  if id -nG "$CALLER_USER" | tr ' ' '\n' | grep -qx "$BROKER_GROUP"; then
    echo "  '$CALLER_USER' already in '$BROKER_GROUP'"
  else
    usermod -aG "$BROKER_GROUP" "$CALLER_USER"
    echo "  added '$CALLER_USER' to '$BROKER_GROUP'"
    echo "  *** NEW GROUP MEMBERSHIP ONLY TAKES EFFECT ON A NEW LOGIN SESSION ***"
    echo "  *** restart SomPong's own service(s) now, e.g.:"
    echo "  ***   systemctl restart mooniex-secretary mooniex-secretary-waker"
  fi

  echo "== 3. staging dir (secretary writes, driveup reads) =="
  mkdir -p "$STAGING_DIR"
  chown "${CALLER_USER}:${BROKER_GROUP}" "$STAGING_DIR"
  chmod 2770 "$STAGING_DIR"   # rwxrws--- + setgid: secretary(owner) rwx, driveup(group) rwx, others none; setgid so files secretary creates stay group=driveup
  echo "  ready: $STAGING_DIR (owner secretary:driveup, mode 2770)"

  echo "== 4. log dir =="
  mkdir -p "$LOG_DIR"
  chown "${BROKER_USER}:${BROKER_GROUP}" "$LOG_DIR"
  chmod 750 "$LOG_DIR"
  echo "  ready: $LOG_DIR"

  echo "== 5. credential file =="
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
  install -m 600 -o "$BROKER_USER" -g "$BROKER_GROUP" "$tmp_env" "$ENV_FILE"
  rm -f "$tmp_env"
  trap - EXIT
  echo "  wrote $ENV_FILE (mode 600, owner ${BROKER_USER}:${BROKER_GROUP})"
  echo "  copied keys (names only): ${REQUIRED_KEYS[*]}"

  echo "== 6. systemd unit =="
  local caller_uid
  caller_uid="$(id -u "$CALLER_USER")"

  cat > "$UNIT_PATH" <<UNIT_EOF
[Unit]
Description=MoonieX Drive upload broker -- sole holder of the Drive OAuth credential; secretary (SomPong) can only reach it over a group-gated unix socket to upload into one fixed folder (task-e713c4e2)
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
Environment=DRIVE_BROKER_ENV=${ENV_FILE}
Environment=DRIVE_BROKER_SOCKET_PATH=${SOCKET_PATH}
Environment=DRIVE_BROKER_STAGING_ROOT=${STAGING_DIR}
Environment=DRIVE_BROKER_ALLOWED_UIDS=${caller_uid}
Environment=DRIVE_BROKER_FOLDER_ID=${FOLDER_ID}
Environment=DRIVE_BROKER_MAX_UPLOAD_BYTES=${MAX_UPLOAD_BYTES}
Environment=DRIVE_BROKER_MAX_REQUEST_BYTES=${MAX_REQUEST_BYTES}
Environment=DRIVE_BROKER_SOCKET_TIMEOUT=${SOCKET_TIMEOUT}
Environment=ORG_LOG_DIR=${LOG_DIR}
ExecStart=${PYTHON} -m runners.drive_upload_broker
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

  systemctl daemon-reload
  systemctl enable "$SERVICE"
  systemctl restart "$SERVICE"
  echo "  installed + started: $SERVICE"

  echo
  echo "== summary =="
  echo "  service:      $SERVICE  (user ${BROKER_USER}, group ${BROKER_GROUP})"
  echo "  socket:       $SOCKET_PATH  (0660, group ${BROKER_GROUP} only)"
  echo "  staging root: $STAGING_DIR  (secretary writes, driveup reads)"
  echo "  folder id:    $FOLDER_ID  (fixed, never client-supplied)"
  echo "  allowed uid:  $caller_uid  ($CALLER_USER)"
  echo "  caller-side:  set DRIVE_UPLOAD_SOCKET=$SOCKET_PATH in secretary's environment"
  echo "  logs:         journalctl -u $SERVICE -f"
}

do_uninstall() {
  require_root uninstall
  systemctl stop "$SERVICE" 2>/dev/null || true
  systemctl disable "$SERVICE" 2>/dev/null || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
  echo "uninstalled: $SERVICE"
  echo "(left in place: ${BROKER_USER} user/group, ${ENV_FILE}, ${STAGING_DIR}, ${LOG_DIR} -- remove by hand if truly done with this)"
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
  echo "recent log lines:"
  journalctl -u "$SERVICE" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
}

case "${1:-}" in
  install)   shift; do_install "${1:-}" ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

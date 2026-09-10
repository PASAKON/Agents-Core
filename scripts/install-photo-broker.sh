#!/usr/bin/env bash
# Install / uninstall the photo broker (runners/drive_photo_broker.py) and
# its host-side drain (runners/sompong_photo_filer.py) as systemd services on
# Contabo -- task-a1c618db, design of record: org wiki
# `mooniex:projects/sompong-line.md` feature F2, CEO 2026-09-10 photo-backup
# order.
#
#   scripts/install-photo-broker.sh install
#   scripts/install-photo-broker.sh uninstall
#   scripts/install-photo-broker.sh status
#
# UNLIKE scripts/install-drive-broker.sh, this script never writes a
# credential anywhere (task instruction) -- provisioning the Drive OAuth
# triple is explicitly out of scope for this task. `install` sets up the
# users, directories, sockets and both systemd units, then prints exactly
# which file a human must create by hand (path, owner, mode, required keys)
# before the broker service will start cleanly.
#
# Modelled on scripts/install-drive-broker.sh (read that file for the
# containment reasoning) but for a SEPARATE broker: separate systemd units,
# separate socket, separate uid allowlist, separate system user, separate
# fixed Drive folder ("My Picture & Videos."). The two brokers never share
# state -- this script refuses to run at all if any of its own constants
# would collide with the existing broker's (see the guard right below the
# constants), so a copy-paste mistake here can never repoint or disable
# `mooniex-drive-broker`/`Desktop Cloud`.
#
# task-4307c02c (2026-09-10): the filer runs as root. Measured on Contabo:
# /root is mode 0700, so no non-root uid can ever traverse into
# /root/projects -- the outbox's own leaf permissions are irrelevant, the
# filer cannot even see the directory exists. Root already owns this whole
# box (credential files, systemd, every service user), so root reading files
# under /root/projects is not a new capability, just the filer's uid
# matching what host root can already reach -- see docs/design/sompong-photos.md
# for the full reasoning and the alternatives that were rejected. The broker
# itself keeps running as its own unprivileged `photoup` user (it holds the
# Drive credential, that has not changed) -- which means `photoup` remains
# subject to the exact same /root traversal block the filer used to hit; that
# is a pre-existing, separately-tracked dependency on the claudeflow-side
# task that moves the outbox out from under /root, not something this script
# or this task fixes (see the "KNOWN GAP" print in do_install below).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/.venv/bin/python"

# --- this broker ------------------------------------------------------------
BROKER_SERVICE="mooniex-drive-photo-broker"
BROKER_UNIT_PATH="/etc/systemd/system/${BROKER_SERVICE}.service"
BROKER_USER="photoup"
BROKER_GROUP="photoup"
BROKER_HOME="/home/${BROKER_USER}"
ENV_FILE="${BROKER_HOME}/.drive-photo.env"
BROKER_LOG_DIR="${BROKER_HOME}/logs"
BROKER_SOCKET_PATH="/run/photoup/photo-broker.sock"      # RuntimeDirectory= recreates the parent dir every boot
FOLDER_ID="1Fwir7lXpgRmMjU6hbynI-4BsQH92L6wy"             # "My Picture & Videos." -- see .claude/skills/gdrive-filing/SKILL.md
MAX_UPLOAD_BYTES="209715200"     # 200 MiB
MAX_REQUEST_BYTES="65536"        # 64 KiB -- one JSON line naming a path + name + subfolder
SOCKET_TIMEOUT="30"              # seconds, request-line read only
REQUIRED_KEYS=(GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET GOOGLE_OAUTH_REFRESH_TOKEN)

# --- the filer (broker's one caller) ----------------------------------------
FILER_SERVICE="mooniex-sompong-photo-filer"
FILER_UNIT_PATH="/etc/systemd/system/${FILER_SERVICE}.service"
# Runs as root (task-4307c02c) -- see the header comment above. Root has no
# separate home dir of its own for this feature, so log/state live under
# dedicated paths rather than a service user's ~, matching how the broker's
# own paths are keyed off BROKER_USER/BROKER_HOME.
FILER_LOG_DIR="/var/log/mooniex-sompong-photo-filer"
OUTBOX_DIR="/root/projects/mooniex-claudeflow/data/sompong/photos-outbox"   # claudeflow's shared volume -- see docs/design/sompong-photos.md
FILER_STATE_DIR="/var/lib/mooniex-sompong-photo-filer"
FILER_POLL_SECONDS="60"
FILER_MAX_RETRIES="5"

# The filer's OLD dedicated user/group, from before task-4307c02c made it run
# as root. Never used for anything new below -- do_install tears these down
# (user, group, home dir) if still present, so a re-run over the
# half-installed state this task fixed doesn't leave an orphaned account and
# an orphaned home dir sitting around unused.
LEGACY_FILER_USER="sompongphoto"
LEGACY_FILER_GROUP="sompongphoto"

# --- the EXISTING broker's constants (scripts/install-drive-broker.sh) --
# Compared against ours below so a future edit here can never collide with
# it. Never used for anything else -- this script does not touch that
# broker's unit, socket, user, or folder.
EXISTING_BROKER_SERVICE="mooniex-drive-broker"
EXISTING_BROKER_UNIT_PATH="/etc/systemd/system/${EXISTING_BROKER_SERVICE}.service"
EXISTING_BROKER_SOCKET_PATH="/run/driveup/drive-broker.sock"
EXISTING_BROKER_FOLDER_ID="115w-UxOvdmPIc5X8nq_oV42EEsrVMRtR"

usage() { echo "usage: $0 {install|uninstall|status}" >&2; exit 2; }

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: $1 needs root (creates users, writes systemd units, runs systemctl) -- rerun with sudo" >&2
    exit 1
  fi
}

# Refuse outright if this script's own constants would ever touch the
# existing broker's unit, socket, or folder -- belt-and-braces against a
# copy-paste edit mistake, not something normal operation can trigger since
# the two sets of constants are hardcoded distinct above.
guard_against_collision_with_existing_broker() {
  local collided=0
  if [ "$BROKER_SERVICE" = "$EXISTING_BROKER_SERVICE" ]; then
    echo "ERROR: BROKER_SERVICE collides with the existing broker's service name -- refusing to run" >&2
    collided=1
  fi
  if [ "$BROKER_UNIT_PATH" = "$EXISTING_BROKER_UNIT_PATH" ]; then
    echo "ERROR: BROKER_UNIT_PATH collides with the existing broker's unit path -- refusing to run" >&2
    collided=1
  fi
  if [ "$BROKER_SOCKET_PATH" = "$EXISTING_BROKER_SOCKET_PATH" ]; then
    echo "ERROR: BROKER_SOCKET_PATH collides with the existing broker's socket path -- refusing to run" >&2
    collided=1
  fi
  if [ "$FOLDER_ID" = "$EXISTING_BROKER_FOLDER_ID" ]; then
    echo "ERROR: FOLDER_ID collides with the existing broker's Desktop Cloud folder -- refusing to run" >&2
    collided=1
  fi
  if [ -f "$EXISTING_BROKER_UNIT_PATH" ] && [ "$BROKER_UNIT_PATH" = "$EXISTING_BROKER_UNIT_PATH" ]; then
    echo "ERROR: would overwrite the existing broker's installed unit file -- refusing to run" >&2
    collided=1
  fi
  if [ -S "$EXISTING_BROKER_SOCKET_PATH" ] && [ "$BROKER_SOCKET_PATH" = "$EXISTING_BROKER_SOCKET_PATH" ]; then
    echo "ERROR: would overwrite the existing broker's live socket -- refusing to run" >&2
    collided=1
  fi
  if [ "$collided" -ne 0 ]; then
    exit 1
  fi
}

do_install() {
  require_root install
  guard_against_collision_with_existing_broker
  [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
  [ -f "$ROOT/runners/drive_photo_broker.py" ] || { echo "ERROR: runners/drive_photo_broker.py missing" >&2; exit 1; }
  [ -f "$ROOT/runners/sompong_photo_filer.py" ] || { echo "ERROR: runners/sompong_photo_filer.py missing" >&2; exit 1; }

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

  echo "== 2. tear down the legacy '${LEGACY_FILER_USER}' user (filer runs as root as of task-4307c02c) =="
  systemctl stop "$FILER_SERVICE" 2>/dev/null || true
  if id -u "$LEGACY_FILER_USER" >/dev/null 2>&1; then
    if userdel -r "$LEGACY_FILER_USER" 2>/dev/null; then
      echo "  removed user '$LEGACY_FILER_USER' and its home directory"
    else
      # -r can fail if a process still holds the account (e.g. a mail spool
      # lock) even after the stop above -- fall back to removing the account
      # without -r rather than leaving the whole step half-done, and say so.
      userdel "$LEGACY_FILER_USER"
      echo "  removed user '$LEGACY_FILER_USER' (home directory left in place -- 'userdel -r' failed, remove by hand if truly unused)"
    fi
  else
    echo "  user '$LEGACY_FILER_USER' already absent -- nothing to remove"
  fi
  if getent group "$LEGACY_FILER_GROUP" >/dev/null; then
    if groupdel "$LEGACY_FILER_GROUP" 2>/dev/null; then
      echo "  removed group '$LEGACY_FILER_GROUP'"
    else
      echo "  WARNING: could not remove group '$LEGACY_FILER_GROUP' (still referenced by something else?) -- left in place, unused by this feature"
    fi
  else
    echo "  group '$LEGACY_FILER_GROUP' already absent -- nothing to remove"
  fi

  echo "== 3. outbox / staging dir (claudeflow writes, root-run filer drains, ${BROKER_USER} reads) =="
  local current_owner
  if [ -d "$OUTBOX_DIR" ]; then
    echo "  already exists: $OUTBOX_DIR -- leaving ownership/mode as-is (may hold live data)"
    echo "  current: $(stat -c '%U:%G %a' "$OUTBOX_DIR" 2>/dev/null || stat -f '%Su:%Sg %Lp' "$OUTBOX_DIR")"
    current_owner="$(stat -c '%U' "$OUTBOX_DIR" 2>/dev/null || stat -f '%Su' "$OUTBOX_DIR")"
    if [ "$current_owner" = "$LEGACY_FILER_USER" ]; then
      chown "root:${BROKER_GROUP}" "$OUTBOX_DIR"
      echo "  re-owned from the now-removed '${LEGACY_FILER_USER}' to root:${BROKER_GROUP} (mode left as-is -- pairs inside are untouched, only the directory's owner changed)"
    fi
  else
    mkdir -p "$OUTBOX_DIR"
    chown "root:${BROKER_GROUP}" "$OUTBOX_DIR"
    chmod 2770 "$OUTBOX_DIR"
    echo "  created: $OUTBOX_DIR (owner root:${BROKER_GROUP}, mode 2770)"
  fi
  echo "  *** KNOWN GAP (claudeflow side, separate task, see docs/design/sompong-photos.md):"
  echo "  *** this directory sits under /root/projects/... . The filer now runs as root"
  echo "  *** (task-4307c02c) so IT can always reach this path regardless of /root's mode --"
  echo "  *** but the broker (${BROKER_USER}) still cannot: if /root or its parents are not"
  echo "  *** traversable by '${BROKER_USER}' (macOS/Linux default for /root is mode 700), the"
  echo "  *** broker cannot open the files it's asked to upload no matter what this script sets"
  echo "  *** on the leaf directory. Verify with: sudo -u ${BROKER_USER} test -r ${OUTBOX_DIR} && echo OK"

  echo "== 4. log + state dirs =="
  mkdir -p "$BROKER_LOG_DIR"
  chown "${BROKER_USER}:${BROKER_GROUP}" "$BROKER_LOG_DIR"
  chmod 750 "$BROKER_LOG_DIR"
  mkdir -p "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  chown root:root "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  chmod 700 "$FILER_LOG_DIR" "$FILER_STATE_DIR"
  echo "  ready: $BROKER_LOG_DIR, $FILER_LOG_DIR, $FILER_STATE_DIR"

  echo "== 5. broker systemd unit =="
  local filer_uid=0   # the filer runs as root (task-4307c02c) -- uid 0 is always 0, no need to look it up

  cat > "$BROKER_UNIT_PATH" <<UNIT_EOF
[Unit]
Description=MoonieX Drive PHOTO broker -- sole holder of the Drive OAuth credential for SomPong's family-photo backup (task-a1c618db, feature F2). Separate from mooniex-drive-broker/Desktop Cloud -- never touch that unit from here.
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${BROKER_USER}
Group=${BROKER_GROUP}
WorkingDirectory=${ROOT}
RuntimeDirectory=${BROKER_USER}
RuntimeDirectoryMode=0750
EnvironmentFile=-${ENV_FILE}
Environment=DRIVE_PHOTO_BROKER_ENV=${ENV_FILE}
Environment=DRIVE_PHOTO_BROKER_SOCKET_PATH=${BROKER_SOCKET_PATH}
Environment=DRIVE_PHOTO_BROKER_STAGING_ROOT=${OUTBOX_DIR}
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
ReadWritePaths=${OUTBOX_DIR} ${BROKER_LOG_DIR}

[Install]
WantedBy=multi-user.target
UNIT_EOF
  echo "  wrote $BROKER_UNIT_PATH"

  echo "== 6. filer systemd unit =="
  cat > "$FILER_UNIT_PATH" <<UNIT_EOF
[Unit]
Description=SomPong family-photo outbox drain -- reads claudeflow's shared-volume outbox and uploads through the Drive photo broker's socket (task-a1c618db, feature F2; runs as root as of task-4307c02c so it can traverse /root/projects -- see docs/design/sompong-photos.md). Never touches the Drive credential directly.
After=network-online.target ${BROKER_SERVICE}.service
Wants=network-online.target
Requires=${BROKER_SERVICE}.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=${ROOT}
Environment=SOMPONG_PHOTO_OUTBOX=${OUTBOX_DIR}
Environment=DRIVE_PHOTO_BROKER_SOCKET_PATH=${BROKER_SOCKET_PATH}
Environment=SOMPONG_PHOTO_FILER_POLL_SECONDS=${FILER_POLL_SECONDS}
Environment=SOMPONG_PHOTO_FILER_MAX_RETRIES=${FILER_MAX_RETRIES}
Environment=SOMPONG_PHOTO_FILER_STATE_DIR=${FILER_STATE_DIR}
Environment=ORG_LOG_DIR=${FILER_LOG_DIR}
ExecStart=${PYTHON} -m runners.sompong_photo_filer
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${OUTBOX_DIR} ${FILER_LOG_DIR} ${FILER_STATE_DIR}

[Install]
WantedBy=multi-user.target
UNIT_EOF
  echo "  wrote $FILER_UNIT_PATH"

  systemctl daemon-reload
  systemctl enable "$BROKER_SERVICE" "$FILER_SERVICE"
  systemctl restart "$BROKER_SERVICE"
  # The filer Requires= the broker, so start it after -- it will simply idle
  # (nothing in the outbox, or the broker refusing until credentialed) rather
  # than fail hard.
  systemctl restart "$FILER_SERVICE" || true
  echo "  installed + started: $BROKER_SERVICE, $FILER_SERVICE"

  echo
  echo "== summary =="
  echo "  broker service:  $BROKER_SERVICE  (user ${BROKER_USER}, group ${BROKER_GROUP})"
  echo "  filer service:   $FILER_SERVICE  (user root -- task-4307c02c)"
  echo "  socket:          $BROKER_SOCKET_PATH  (0660, group ${BROKER_GROUP} only)"
  echo "  outbox:          $OUTBOX_DIR"
  echo "  folder id:       $FOLDER_ID  (\"My Picture & Videos.\", fixed, never client-supplied)"
  echo "  allowed uid:     $filer_uid  (root -- the filer; see the module docstrings for why uid 0 is safe here)"
  echo
  echo "*** REQUIRED BEFORE THE BROKER WILL ACTUALLY UPLOAD ANYTHING ***"
  echo "*** This script never writes a credential. A human must create:"
  echo "***   $ENV_FILE"
  echo "*** mode 600, owned by ${BROKER_USER}:${BROKER_GROUP}, containing exactly these keys"
  echo "*** (values only -- never echo them back to this terminal or a log):"
  for key in "${REQUIRED_KEYS[@]}"; do
    echo "***   ${key}=..."
  done
  echo "*** Same OAuth app/Drive account the existing broker already uses is fine to reuse here --"
  echo "*** this is a SEPARATE credential FILE by design (separate env name), not a different Drive account."
  echo "*** After creating it:  systemctl restart $BROKER_SERVICE"
  echo "*** Logs:               journalctl -u $BROKER_SERVICE -f"
  echo "***                     journalctl -u $FILER_SERVICE -f"
}

do_uninstall() {
  require_root uninstall
  guard_against_collision_with_existing_broker
  systemctl stop "$FILER_SERVICE" 2>/dev/null || true
  systemctl stop "$BROKER_SERVICE" 2>/dev/null || true
  systemctl disable "$FILER_SERVICE" 2>/dev/null || true
  systemctl disable "$BROKER_SERVICE" 2>/dev/null || true
  rm -f "$FILER_UNIT_PATH" "$BROKER_UNIT_PATH"
  systemctl daemon-reload
  echo "uninstalled: $BROKER_SERVICE, $FILER_SERVICE"
  echo "(left in place: ${BROKER_USER} user/group (filer runs as root -- nothing to leave there),"
  echo " ${ENV_FILE}, ${OUTBOX_DIR}, ${FILER_STATE_DIR} -- remove by hand if truly done with this;"
  echo " the outbox may hold un-filed photos, never delete it without checking first)"
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
  install)   do_install ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

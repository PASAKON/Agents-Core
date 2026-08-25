#!/usr/bin/env bash
# Install / uninstall the secretary waker as a systemd service on Contabo.
#
# Drains state/inbox/secretary-sompong/ (letters written by report_to_ceo),
# invokes SomPong over HTTP to digest them, and notifies the CEO over
# Telegram. Runs as the `secretary` user -- the same account
# runners/secretary_server.py (unit `mooniex-secretary`) already runs as.
#
# TWO env files, not one (task-ff60da52 D5 -- read this before touching
# EnvironmentFile= below):
#   - SECRETS_FILE (/etc/mooniex/secretary-secrets.env, root:root 600) --
#     ANTHROPIC_AUTH_TOKEN, ZAI_API_KEY, SECRETARY_API_KEY,
#     TELEGRAM_BOT_TOKEN. Systemd reads EnvironmentFile= as root BEFORE
#     dropping to User=, so 600 root:root is still readable at unit start.
#     Owned/provisioned by the CTO, not this script.
#   - ENV_FILE (/home/secretary/.secretary.env) -- whatever non-secret
#     config is left (e.g. TELEGRAM_CEO_CHAT_ID). Holds zero secrets as of
#     2026-08-25.
# This script used to hardcode ONE EnvironmentFile= line pointing at
# ENV_FILE and regenerate the whole unit from it. Re-running it that way
# would silently DROP the SECRETS_FILE line from the live unit -- the
# service would restart with no ANTHROPIC_AUTH_TOKEN / ZAI_API_KEY /
# SECRETARY_API_KEY / TELEGRAM_BOT_TOKEN and fail every turn, with no error
# pointing at "you re-ran the installer." Both lines are now written on
# every install, always, so this script can never regress that split again.
#
#   scripts/install-secretary-waker.sh install     # write unit + enable + start
#   scripts/install-secretary-waker.sh uninstall    # stop + disable + remove unit
#   scripts/install-secretary-waker.sh status       # active? enabled? recent log lines?
#
# Idempotent: installing twice replaces the unit and restarts, never
# duplicates. Same shape as scripts/install-mac-agent.sh (launchd there,
# systemd here). install/uninstall write to /etc/systemd/system and call
# systemctl, so they need root.
set -euo pipefail

SERVICE="mooniex-secretary-waker"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
PYTHON="$ROOT/.venv/bin/python"
RUN_USER="secretary"
ENV_FILE="/home/${RUN_USER}/.secretary.env"
SECRETS_FILE="/etc/mooniex/secretary-secrets.env"

usage() { echo "usage: $0 {install|uninstall|status}" >&2; exit 2; }

require_root() {
  if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: $1 needs root (writes $UNIT_PATH, runs systemctl) -- rerun with sudo" >&2
    exit 1
  fi
}

do_install() {
  require_root install
  [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
  [ -f "$ROOT/runners/secretary_waker.py" ] || { echo "ERROR: runners/secretary_waker.py missing" >&2; exit 1; }
  if [ ! -f "$SECRETS_FILE" ]; then
    echo "WARNING: $SECRETS_FILE does not exist yet -- the service will run but fail" >&2
    echo "         every tick until ANTHROPIC_AUTH_TOKEN / ZAI_API_KEY / SECRETARY_API_KEY /" >&2
    echo "         TELEGRAM_BOT_TOKEN are provisioned there (root:root 600 -- CTO-owned," >&2
    echo "         not written by this script)." >&2
  fi
  if [ ! -f "$ENV_FILE" ]; then
    echo "WARNING: $ENV_FILE does not exist yet -- the service will run but fail" >&2
    echo "         every tick until TELEGRAM_CEO_CHAT_ID is added to it (letters are kept, not lost)." >&2
  fi

  cat > "$UNIT_PATH" <<UNIT_EOF
[Unit]
Description=MoonieX secretary waker -- digests C-level replies for the CEO over Telegram
After=network-online.target mooniex-secretary.service
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${ROOT}
EnvironmentFile=${ENV_FILE}
EnvironmentFile=${SECRETS_FILE}
ExecStart=${PYTHON} -m runners.secretary_waker
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT_EOF

  systemctl daemon-reload
  systemctl enable "$SERVICE"
  systemctl restart "$SERVICE"
  echo "installed + started: $SERVICE"
  echo "  unit: $UNIT_PATH"
  echo "  env file:     $ENV_FILE"
  echo "  secrets file: $SECRETS_FILE"
  echo "  logs: journalctl -u $SERVICE -f"
}

do_uninstall() {
  require_root uninstall
  systemctl stop "$SERVICE" 2>/dev/null || true
  systemctl disable "$SERVICE" 2>/dev/null || true
  rm -f "$UNIT_PATH"
  systemctl daemon-reload
  echo "uninstalled: $SERVICE"
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
  if [ -f "$ENV_FILE" ]; then echo "env file:     $ENV_FILE (present)"; else echo "env file:     $ENV_FILE (MISSING)"; fi
  if [ -f "$SECRETS_FILE" ]; then echo "secrets file: $SECRETS_FILE (present)"; else echo "secrets file: $SECRETS_FILE (MISSING)"; fi
  echo "recent log lines:"
  journalctl -u "$SERVICE" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
}

case "${1:-}" in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

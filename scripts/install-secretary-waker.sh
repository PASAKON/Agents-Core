#!/usr/bin/env bash
# Install / uninstall the secretary waker as a systemd service on Contabo.
#
# Drains state/inbox/secretary-sompong/ (letters written by report_to_ceo),
# invokes SomPong over HTTP to digest them, and notifies the CEO over
# Telegram. Runs as the `secretary` user -- the same account
# runners/secretary_server.py (unit `mooniex-secretary`) already runs as --
# reading EnvironmentFile=/home/secretary/.secretary.env for
# TELEGRAM_BOT_TOKEN, TELEGRAM_CEO_CHAT_ID, and SECRETARY_API_KEY.
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
  if [ ! -f "$ENV_FILE" ]; then
    echo "WARNING: $ENV_FILE does not exist yet -- the service will run but fail" >&2
    echo "         every tick until TELEGRAM_BOT_TOKEN / TELEGRAM_CEO_CHAT_ID /" >&2
    echo "         SECRETARY_API_KEY are added to it (letters are kept, not lost)." >&2
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
  echo "recent log lines:"
  journalctl -u "$SERVICE" -n 10 --no-pager 2>/dev/null || echo "  (journalctl unavailable)"
}

case "${1:-}" in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

#!/usr/bin/env bash
# Run after review on Contabo. Use the account that owns the tmux server.
# PANE_DIALOG_WATCH_USER defaults to root; PANE_DIALOG_WATCH_ENV must name
# an existing systemd env file containing TELEGRAM_BOT_TOKEN and TELEGRAM_CEO_CHAT_ID.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="mooniex-pane-dialog-watch"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
TIMER_PATH="/etc/systemd/system/${SERVICE}.timer"
PYTHON="$ROOT/.venv/bin/python"
RUN_USER="${PANE_DIALOG_WATCH_USER:-root}"
ENV_FILE="${PANE_DIALOG_WATCH_ENV:-}"

require_root() {
  [ "$(id -u)" -eq 0 ] || { echo "ERROR: $1 needs root" >&2; exit 1; }
}

case "${1:-}" in
  install)
    require_root install
    [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
    [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ] && [[ "$ENV_FILE" = /* ]] || {
      echo "ERROR: set PANE_DIALOG_WATCH_ENV to an existing absolute env-file path" >&2; exit 1;
    }
    id "$RUN_USER" >/dev/null
    command -v tmux >/dev/null
    cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Notify CEO about unattended C-level permission dialogs
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${RUN_USER}
WorkingDirectory=${ROOT}
EnvironmentFile=${ENV_FILE}
ExecStart="${PYTHON}" -m tools.pane_dialog_watch
UMask=0077
NoNewPrivileges=true
UNIT
    # Do not use PrivateTmp: tmux's default socket lives in /tmp.
    cat > "$TIMER_PATH" <<UNIT
[Unit]
Description=Scan C-level permission dialogs every 60 seconds

[Timer]
OnBootSec=60s
OnUnitActiveSec=60s
AccuracySec=1s
Unit=${SERVICE}.service

[Install]
WantedBy=timers.target
UNIT
    systemctl daemon-reload
    systemctl enable "${SERVICE}.timer"
    systemctl restart "${SERVICE}.timer"
    ;;
  uninstall)
    require_root uninstall
    systemctl disable --now "${SERVICE}.timer" 2>/dev/null || true
    systemctl stop "${SERVICE}.service" 2>/dev/null || true
    rm -f "$UNIT_PATH" "$TIMER_PATH"
    systemctl daemon-reload
    echo "Uninstalled; retained state/pane-dialog-watch.json"
    ;;
  status)
    systemctl status "${SERVICE}.timer" "${SERVICE}.service" --no-pager
    ;;
  *) echo "usage: $0 {install|uninstall|status}" >&2; exit 2 ;;
esac

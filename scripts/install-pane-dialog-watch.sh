#!/usr/bin/env bash
# Run after review on Contabo. Use the account that owns the tmux server.
# PANE_DIALOG_WATCH_USER defaults to root. The unit carries no secrets.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="mooniex-pane-dialog-watch"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
TIMER_PATH="/etc/systemd/system/${SERVICE}.timer"
PYTHON="$ROOT/.venv/bin/python"
RUN_USER="${PANE_DIALOG_WATCH_USER:-root}"

require_root() {
  [ "$(id -u)" -eq 0 ] || { echo "ERROR: $1 needs root" >&2; exit 1; }
}

case "${1:-}" in
  install)
    require_root install
    [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
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

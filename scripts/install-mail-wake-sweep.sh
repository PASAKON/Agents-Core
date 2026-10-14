#!/usr/bin/env bash
# Envelope mail's late wake (org restructure P1): run tools/mail_wake_sweep.py
# every 60 s. Install it ON THE SAME DAY the host's sessions get
# ORG_MAIL_ENVELOPE=1, not before: the unit runs with the flag on, and a sender
# debounces only while this sweeper's heartbeat is fresh, so without it every
# letter keeps waking at once.
#
# Run as root on Contabo, as the account that owns the tmux server (root). The
# unit carries no secrets. ORG_WAKE_DEBOUNCE_S, when set in the installing
# shell, is copied into the unit (default 600).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE="mooniex-mail-wake-sweep"
UNIT_PATH="/etc/systemd/system/${SERVICE}.service"
TIMER_PATH="/etc/systemd/system/${SERVICE}.timer"
PYTHON="$ROOT/.venv/bin/python"
RUN_USER="${MAIL_WAKE_SWEEP_USER:-root}"
DEBOUNCE="${ORG_WAKE_DEBOUNCE_S:-600}"

require_root() {
  [ "$(id -u)" -eq 0 ] || { echo "ERROR: $1 needs root" >&2; exit 1; }
}

case "${1:-}" in
  install)
    require_root install
    [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
    [[ "$DEBOUNCE" =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo "ERROR: ORG_WAKE_DEBOUNCE_S must be a number" >&2; exit 1; }
    id "$RUN_USER" >/dev/null
    command -v tmux >/dev/null
    cat > "$UNIT_PATH" <<UNIT
[Unit]
Description=Fire the C-level wakes envelope mail deferred
After=network-online.target

[Service]
Type=oneshot
User=${RUN_USER}
WorkingDirectory=${ROOT}
Environment=ORG_MAIL_ENVELOPE=1
Environment=ORG_WAKE_DEBOUNCE_S=${DEBOUNCE}
ExecStart="${PYTHON}" -m tools.mail_wake_sweep
UMask=0022
NoNewPrivileges=true
UNIT
    # Do not use PrivateTmp: tmux's default socket lives in /tmp.
    cat > "$TIMER_PATH" <<UNIT
[Unit]
Description=Fire deferred envelope-mail wakes every 60 seconds

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
    # the heartbeat goes stale within 180 s and every sender wakes at once again
    echo "Uninstalled; senders stop debouncing once state/inbox/.wake-sweep is 180 s old"
    ;;
  status)
    systemctl status "${SERVICE}.timer" "${SERVICE}.service" --no-pager
    ;;
  *) echo "usage: $0 {install|uninstall|status}" >&2; exit 2 ;;
esac

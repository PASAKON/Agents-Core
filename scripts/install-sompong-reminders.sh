#!/usr/bin/env bash
# Root fetches two Infisical projects, then setpriv drops all privileges.
set -euo pipefail
ACTION="${1:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=mooniex-sompong-reminders
UNIT_PATH="/etc/systemd/system/$SERVICE.service"
[[ $# == 1 && "$ACTION" =~ ^(install|uninstall|status)$ ]] || { echo 'Usage: install-sompong-reminders.sh install|uninstall|status' >&2; exit 2; }
[[ "$ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Unsupported checkout path' >&2; exit 2; }
if [[ "$ACTION" != status && "$EUID" -ne 0 ]]; then
  echo 'Root required' >&2; exit 1
fi
case "$ACTION" in
  install)
    check="$ROOT"
    while [[ "$check" != / ]]; do
      [[ "$(stat -c %u "$check")" == 0 && -z "$(find "$check" -maxdepth 0 -perm /022 -print)" ]] || { echo 'Checkout ancestors must be root-owned and not group/world writable' >&2; exit 1; }
      check="$(dirname "$check")"
    done
    # Includes the shared helper's transitive imports and the unit template.
    for source in tools lib config deploy/systemd; do
      [[ -z "$(find "$ROOT/$source" -not -user root -print -quit)" ]] || { echo 'Runtime sources must be root-owned' >&2; exit 1; }
      [[ -z "$(find "$ROOT/$source" -perm /022 -print -quit)" ]] || { echo 'Runtime sources must not be group/world writable' >&2; exit 1; }
      [[ -z "$(find "$ROOT/$source" -type l -print -quit)" ]] || { echo 'Runtime source symlinks are not allowed' >&2; exit 1; }
    done
    if ! getent group sompong-reminders >/dev/null; then groupadd --system sompong-reminders; fi
    if ! id -u sompong-reminders >/dev/null 2>&1; then
      useradd --system --gid sompong-reminders --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin sompong-reminders
    fi
    [[ "$(id -u sompong-reminders)" -gt 0 ]] || { echo 'Service account must not be root' >&2; exit 1; }
    sed "s|@ROOT@|$ROOT|g" "$ROOT/deploy/systemd/sompong-reminders.service" > "$UNIT_PATH"
    chmod 0644 "$UNIT_PATH"
    chown root:root "$UNIT_PATH"
    systemctl daemon-reload
    systemctl enable "$SERVICE"
    systemctl restart "$SERVICE"
    ;;
  uninstall)
    systemctl disable --now "$SERVICE"
    rm -f "$UNIT_PATH"
    systemctl daemon-reload
    echo 'Service account and durable ledger retained.'
    ;;
  status)
    systemctl status --no-pager "$SERVICE"
    ;;
esac

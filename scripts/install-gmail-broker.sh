#!/usr/bin/env bash
# No secret files: root fetches Infisical, then setpriv drops privileges.
set -euo pipefail
ACTION="${1:-}"
[[ $# -gt 0 ]] && shift
DRY_RUN=false
CALLER=sompong
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE=mooniex-gmail-broker
UNIT_PATH="/etc/systemd/system/$SERVICE.service"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --caller-user) CALLER="${2:?caller user required}"; shift 2 ;;
    *) echo 'Unknown option' >&2; exit 2 ;;
  esac
done
[[ "$ACTION" =~ ^(install|uninstall|status)$ ]] || { echo 'Usage: install-gmail-broker.sh install|uninstall|status [--dry-run] [--caller-user USER]' >&2; exit 2; }
[[ "$CALLER" =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
[[ "$ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo 'Unsupported checkout path' >&2; exit 2; }
run() {
  printf '+'; printf ' %q' "$@"; printf '\n'
  if ! "$DRY_RUN"; then "$@"; fi
}
unit() {
cat <<EOF
[Unit]
Description=Gmail credential broker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$ROOT
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=GMAIL_BROKER_ALLOWED_UIDS=$CALLER_UID
Environment=GMAIL_BROKER_SOCKET_PATH=/run/mailbroker/gmail.sock
Environment=GMAIL_BROKER_LOG_DIR=/var/log/mailbroker
ExecStartPre=+/usr/bin/install -d -m 0750 -o mailbroker -g mailbroker /run/mailbroker
ExecStart=/usr/bin/python3 $ROOT/tools/infisical_setup.py run Agents-Core prod --as contabo --path /gmail-broker -- /usr/bin/setpriv --reuid=mailbroker --regid=mailbroker --clear-groups --bounding-set=-all --inh-caps=-all --ambient-caps=-all --no-new-privs /usr/bin/python3 $ROOT/runners/gmail_broker.py
Restart=on-failure
RestartSec=5
UMask=0077
LimitCORE=0
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=-/run/mailbroker /var/log/mailbroker

[Install]
WantedBy=multi-user.target
EOF
}
if [[ "$ACTION" != status ]] && ! "$DRY_RUN" && [[ "$EUID" -ne 0 ]]; then
  echo 'Root required' >&2; exit 1
fi
case "$ACTION" in
  install)
    CALLER_UID="$(id -u "$CALLER")"
    [[ "$CALLER_UID" -gt 0 && "$CALLER" != mailbroker ]] || { echo 'Caller must be a non-root, separate user' >&2; exit 1; }
    # Root execution requires a trusted checkout, including all ancestor dirs.
    if ! "$DRY_RUN"; then
      check="$ROOT"
      while [[ "$check" != / ]]; do
        [[ "$(stat -c %u "$check")" == 0 ]] && [[ -z "$(find "$check" -maxdepth 0 -perm /022 -print)" ]] || { echo 'Checkout ancestors must be root-owned and not group/world writable' >&2; exit 1; }
        check="$(dirname "$check")"
      done
      [[ -z "$(find "$ROOT/tools" "$ROOT/runners" -not -user root -print -quit)" ]] || { echo 'Runtime sources must be root-owned' >&2; exit 1; }
      [[ -z "$(find "$ROOT/tools" "$ROOT/runners" -perm /022 -print -quit)" ]] || { echo 'Runtime sources must not be group/world writable' >&2; exit 1; }
    fi
    if ! getent group mailbroker >/dev/null; then run groupadd --system mailbroker; fi
    if ! id -u mailbroker >/dev/null 2>&1; then
      run useradd --system --gid mailbroker --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin mailbroker
    fi
    run usermod -aG mailbroker "$CALLER"
    run install -d -m 0700 -o mailbroker -g mailbroker /var/log/mailbroker
    printf '+ write unit %s (0644 root:root)\n' "$UNIT_PATH"
    unit
    if ! "$DRY_RUN"; then
      unit > "$UNIT_PATH"
    fi
    run chmod 0644 "$UNIT_PATH"
    run chown root:root "$UNIT_PATH"
    run systemctl daemon-reload
    run systemctl enable "$SERVICE"
    run systemctl restart "$SERVICE"
    echo 'Caller needs a new login/session for group membership. No secrets written to disk.'
    ;;
  uninstall)
    run systemctl disable --now "$SERVICE"
    run rm -f "$UNIT_PATH" /run/mailbroker/gmail.sock
    run systemctl daemon-reload
    echo 'Account/group and audit log retained. Revoke the OAuth grant separately.'
    ;;
  status)
    run systemctl status --no-pager "$SERVICE"
    ;;
esac

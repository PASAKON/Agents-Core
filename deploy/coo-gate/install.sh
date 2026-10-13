#!/usr/bin/env bash
# Install, remove or show SomPong's COO gate and dispatcher (deploy/coo-gate/README.md). Root only;
# run it from a Run card (CEO card Q-20261013-1948-4a33 is the order behind it).
#
#   install.sh install <root> [secret-path]
#       <root>         an Agents-Core checkout holding this branch's runners/ (absolute path)
#       secret-path    Infisical folder in Org-Coo prod holding the gate's ORG_DB_URL (default /gate)
#     Creates the system user org-coo-gate, renders org-coo-gate.service and
#     org-coo-dispatch.service for <root> into /etc/systemd/system, enables and (re)starts both.
#     Running it again re-points both units (another <root>, another folder); nothing else changes.
#   install.sh uninstall        stop and remove both units and the user: the rollback line
#   install.sh status           both units' state and the socket
#
# Touches no other unit. Neither unit holds the shared tmux server, so (re)starting them ends no
# session (CLAUDE.md "Contabo -- one tmux server"); `status` prints the check anyway.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UNIT_DIR=/etc/systemd/system
UNITS=(org-coo-gate org-coo-dispatch)
GATE_USER=org-coo-gate
COO_USER=sompong

die() { echo "install.sh: $*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || die "run as root"

tmux_check() {
  local p pp
  for p in $(pgrep -f '^tmux' || true); do echo "tmux server $p: $(tail -1 /proc/$p/cgroup)"; done
  for pp in $(tmux list-panes -a -F '#{pane_pid}' 2>/dev/null || true); do tail -1 "/proc/$pp/cgroup"; done \
    | sort | uniq -c | sed 's/^/panes /'
  if (for p in $(pgrep -f '^tmux' || true); do tail -1 "/proc/$p/cgroup"; done) | grep -q 'org-coo-'; then
    die "a tmux server lives in an org-coo unit: restarting it would end sessions; tell the CEO"
  fi
}

render() {   # render <unit> <root> <uids> <secret-path>
  sed -e "s|@ROOT@|$2|g" -e "s|@ALLOWED_UIDS@|$3|g" -e "s|@SECRET_PATH@|$4|g" "$HERE/$1.service"
}

case "${1:-}" in
  install)
    ROOT="${2:-}"; SECRET_PATH="${3:-/gate}"
    [[ "$ROOT" = /* && -f "$ROOT/runners/coo_gate.py" && -f "$ROOT/runners/coo_dispatch.py" ]] \
      || die "install needs the absolute path of a checkout with runners/coo_gate.py"
    [ -x "$ROOT/.venv/bin/python" ] || die "$ROOT/.venv/bin/python missing"
    [[ "$SECRET_PATH" =~ ^/[A-Za-z0-9_/-]*$ ]] || die "secret-path must look like /gate"
    COO_UID="$(id -u "$COO_USER")" || die "no user $COO_USER"
    tmux_check
    if ! id -u "$GATE_USER" >/dev/null 2>&1; then
      useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin "$GATE_USER"
      echo "created system user $GATE_USER ($(id -u "$GATE_USER"))"
    fi
    for u in "${UNITS[@]}"; do
      render "$u" "$ROOT" "$COO_UID" "$SECRET_PATH" > "$UNIT_DIR/$u.service.new"
      mv "$UNIT_DIR/$u.service.new" "$UNIT_DIR/$u.service"
    done
    systemctl daemon-reload
    for u in "${UNITS[@]}"; do systemctl enable "$u" >/dev/null 2>&1; systemctl restart "$u"; done
    sleep 3
    exec "$0" status
    ;;
  uninstall)
    for u in "${UNITS[@]}"; do
      systemctl disable --now "$u" >/dev/null 2>&1 || true
      rm -f "$UNIT_DIR/$u.service"
    done
    systemctl daemon-reload
    if id -u "$GATE_USER" >/dev/null 2>&1; then userdel "$GATE_USER"; fi
    echo "removed: ${UNITS[*]} and user $GATE_USER (coo tasks already in the hub stay; nothing starts them)"
    ;;
  status)
    for u in "${UNITS[@]}"; do
      printf '%-18s %s\n' "$u" "$(systemctl is-active "$u" 2>/dev/null || true)"
    done
    ls -l /run/org-coo-gate/gate.sock 2>/dev/null || echo "no socket /run/org-coo-gate/gate.sock"
    tmux_check
    journalctl -u org-coo-gate -u org-coo-dispatch -n 8 --no-pager -o cat 2>/dev/null || true
    ;;
  *)
    sed -n '2,15p' "$0"; exit 2 ;;
esac

#!/usr/bin/env bash
# Install (or remove) the standing worktree reap on Contabo:
#   deploy/systemd/org-worktree-reap.service  (tools/gc_stale_tasks.py --reap --go)
#   deploy/systemd/org-worktree-reap.timer    (every 6 h)
# Idempotent: running install again rewrites the two unit files with the same
# content, reloads systemd, enables the timer and restarts it. The timer is the
# only unit with an [Install] section, so it is the one that is enabled; it
# starts the service.
#
# Usage (root): bash scripts/install-org-worktree-reap.sh [install|uninstall|status]
#
# Run it from the main checkout (/opt/MoonieXHQ/Agents/Core), never from a
# worktree: the units run code from this checkout, and the code deletes
# worktrees. The script refuses a checkout whose path contains /worktrees/.
#
# Overrides, used by the tests so they never reach /etc or a real systemd:
#   ORG_REAP_UNIT_DIR   where the units go (default /etc/systemd/system)
#   ORG_REAP_SYSTEMCTL  systemctl binary (default systemctl)
set -euo pipefail

ACTION="${1:-install}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/deploy/systemd"
NAME=org-worktree-reap
UNIT_DIR="${ORG_REAP_UNIT_DIR:-/etc/systemd/system}"
SYSTEMCTL="${ORG_REAP_SYSTEMCTL:-systemctl}"

[[ "$ACTION" =~ ^(install|uninstall|status)$ ]] || {
  echo "usage: $0 [install|uninstall|status]" >&2; exit 2; }
# The path goes into a sed replacement and into ExecStart: plain characters only.
[[ "$ROOT" =~ ^/[a-zA-Z0-9_./-]+$ ]] || { echo "ERROR: unsupported checkout path: $ROOT" >&2; exit 2; }
if [[ "$ACTION" != status && "$UNIT_DIR" == /etc/systemd/system && "$(id -u)" -ne 0 ]]; then
  echo "ERROR: $ACTION needs root" >&2; exit 1
fi

case "$ACTION" in
  install)
    case "$ROOT/" in
      */worktrees/*) echo "ERROR: $ROOT is inside a worktrees/ folder; install from the main checkout" >&2; exit 1 ;;
    esac
    for f in "$SRC/$NAME.service" "$SRC/$NAME.timer" "$ROOT/tools/gc_stale_tasks.py" \
             "$ROOT/scripts/hub/with-org-db-env.sh"; do
      [ -f "$f" ] || { echo "ERROR: missing $f" >&2; exit 1; }
    done
    [ -x "$ROOT/.venv/bin/python" ] || { echo "ERROR: no venv python at $ROOT/.venv/bin/python" >&2; exit 1; }
    # Root runs this code every 6 h: refuse it when another account can write it.
    if [ "$(id -u)" -eq 0 ]; then
      for p in "$ROOT" "$ROOT/tools" "$ROOT/lib" "$ROOT/runners" "$ROOT/scripts/hub" \
               "$ROOT/tools/gc_stale_tasks.py" "$ROOT/scripts/hub/with-org-db-env.sh"; do
        [ "$(stat -c %u "$p")" -eq 0 ] && [ -z "$(find "$p" -maxdepth 0 -perm /022 -print)" ] || {
          echo "ERROR: $p must be root-owned and not group/world writable" >&2; exit 1; }
      done
    fi
    mkdir -p "$UNIT_DIR"
    tmp=""
    trap '[ -z "$tmp" ] || rm -f -- "$tmp"' EXIT
    for unit in "$NAME.service" "$NAME.timer"; do
      tmp="$(mktemp "$UNIT_DIR/.$unit.XXXXXX")"
      sed "s|@ROOT@|$ROOT|g" "$SRC/$unit" > "$tmp"
      ! grep -q '@ROOT@' "$tmp" || { echo "ERROR: unfilled @ROOT@ in $unit" >&2; exit 1; }
      chmod 0644 "$tmp"
      mv -f "$tmp" "$UNIT_DIR/$unit"
    done
    "$SYSTEMCTL" daemon-reload
    "$SYSTEMCTL" enable "$NAME.timer"
    "$SYSTEMCTL" restart "$NAME.timer"
    echo "installed $UNIT_DIR/$NAME.service and $NAME.timer (checkout $ROOT)"
    ;;
  uninstall)
    "$SYSTEMCTL" disable --now "$NAME.timer" 2>/dev/null || true
    "$SYSTEMCTL" stop "$NAME.service" 2>/dev/null || true
    rm -f "$UNIT_DIR/$NAME.service" "$UNIT_DIR/$NAME.timer"
    "$SYSTEMCTL" daemon-reload
    echo "removed $NAME.service and $NAME.timer"
    ;;
  status)
    "$SYSTEMCTL" status --no-pager "$NAME.timer" "$NAME.service" || true
    ;;
esac

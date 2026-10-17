#!/usr/bin/env bash
# org-restart.sh <host> [--sessions-only] [--dry-run]
#   default          prep (save every session), then reboot 90 s later
#   --sessions-only  prep, then resume + report --notify; no reboot
#   --dry-run        prep --dry-run only; print what would follow
set -euo pipefail
# A systemd-run unit starts with no HOME. The hub wrapper finds ORG_DB_URL through
# ~/.config/mooniex, so without HOME every org tool ran with no hub and prep refused
# every session (17 Oct session test, unit org-sessrestart-1792230950).
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
host=${1:?usage: org-restart.sh contabo [--sessions-only] [--dry-run]}
shift
mode=reboot
dry=()
for arg in "$@"; do
  case "$arg" in
    --sessions-only) mode=sessions ;;
    --dry-run) dry=(--dry-run) ;;
    *) echo "unknown option: $arg"; exit 2 ;;
  esac
done
[[ "$host" == contabo ]] || { echo 'Only Contabo supports reboot scheduling'; exit 2; }
# Serialize prep/reboot intent with the daily Clean card.
mkdir -p state/restart
exec 9>state/restart/operation.lock
flock -n 9 || { echo 'Another restart/clean operation is active'; exit 1; }
P=(bash scripts/hub/org-python.sh tools/restart_run.py --host "$host")
if "${P[@]}" prep --wait-max 600 "${dry[@]}"; then
  if (( ${#dry[@]} )); then
    echo "dry run: would $([[ $mode == reboot ]] && echo 'reboot in 90 s' || echo 'resume + report --notify')"
  elif [[ $mode == reboot ]]; then
    systemd-run --unit="org-reboot-$(date +%s)" --on-active=90 systemctl reboot
  else
    status=0
    "${P[@]}" resume || status=$?
    "${P[@]}" report --notify || status=$?
    exit "$status"
  fi
else
  status=$?
  echo "Restart refused: prep exited $status; review the safety-gate output above."
  # Bring back whatever prep already closed; resume is a no-op without its marker.
  if [[ $mode == sessions && ${#dry[@]} -eq 0 ]]; then "${P[@]}" resume || true; fi
  exit "$status"
fi

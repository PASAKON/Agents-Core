#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
host=${1:?usage: org-restart.sh contabo}
[[ "$host" == contabo ]] || { echo 'Only Contabo supports reboot scheduling'; exit 2; }
# Serialize prep/reboot intent with the daily Clean card.
mkdir -p state/restart
exec 9>state/restart/operation.lock
flock -n 9 || { echo 'Another restart/clean operation is active'; exit 1; }
if bash scripts/hub/org-python.sh tools/restart_run.py --host "$host" prep --wait-max 600; then
  systemd-run --unit="org-reboot-$(date +%s)" --on-active=90 systemctl reboot
else
  status=$?
  echo "Restart refused: prep exited $status; review the safety-gate output above."
  exit "$status"
fi

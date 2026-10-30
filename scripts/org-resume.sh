#!/usr/bin/env bash
set -euo pipefail
# systemd starts the unit with no HOME; the hub wrapper needs it to find ORG_DB_URL.
export HOME="${HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -f state/restart/pending-contabo.json ]] || exit 0
mkdir -p state/restart
exec > >(tee -a "state/restart/resume-$(date -u +%Y%m%dT%H%M%S).log") 2>&1
export TMUX_TMPDIR=/tmp
unset DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR TMUX
deadline=$((SECONDS + 600))
until timeout 8 bash scripts/hub/org-python.sh -c '
import os
import psycopg
with psycopg.connect(os.environ["ORG_DB_URL"], connect_timeout=3) as conn:
    conn.execute("SELECT 1").fetchone()
' >/dev/null 2>&1; do
  if (( SECONDS >= deadline )); then
    echo 'Hub unavailable after 10 minutes (Postgres container: org-postgres)'
    exit 1
  fi
  echo 'Waiting for org-postgres hub'
  sleep 10
done
# Keep an empty server alive. The synchronous /etc/tmux.conf hook moves it
# before panes fork; explicitly adopt too, then fail closed if adoption failed.
tmux start-server \; set-option -g exit-empty off
pid=$(tmux display-message -p '#{pid}')
socket=$(tmux display-message -p '#{socket_path}')
bash scripts/org-tmux-adopt.sh "$pid" "$socket"
cgroup=$(cat "/proc/$pid/cgroup")
echo "Shared tmux server pid=$pid socket=$socket cgroup=$cgroup"
if ! [[ "$cgroup" =~ /org-tmux(-[0-9]+)?\.scope($|$'\n') ]]; then
  echo 'Resume refused: shared tmux server is outside org-tmux.scope'
  exit 1
fi
status=0
for attempt in 0 1 2 3; do
  status=0
  bash scripts/hub/org-python.sh tools/restart_run.py --host contabo resume || status=$?
  (( status == 0 )) && break
  if (( attempt < 3 )); then
    echo 'Resume failed; retrying in 60 seconds'
    sleep 60
  fi
done
bash scripts/hub/org-python.sh tools/restart_run.py --host contabo report --notify || status=$?
exit "$status"

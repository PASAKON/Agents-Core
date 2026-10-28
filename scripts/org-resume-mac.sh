#!/usr/bin/env bash
# org-resume-mac.sh -- the Mac twin of scripts/org-resume.sh.
#
# Started at login by the user LaunchAgent deploy/launchd/com.mooniex.org-resume.plist
# (docs/ops/safe-restart-mac.md).
#
#   no state/restart/pending-mac.json  an ordinary login: one log line, exit 0
#   marker present                     wait for network + tailnet + hub, then
#                                      `restart_run.py --host mac resume` and `report --notify`
#
# Log: state/restart/mac-resume.log (append). Exit: 0 all back; 1 the network/tailnet/hub never
# came up; otherwise the first non-zero of resume / report. A failed report --notify (the Mac has
# no Run Inbox token yet) leaves the sessions resumed; the "กลับมา n/m" line is already in the log.
#
# Written for bash 3.2 (the macOS /bin/bash) and a bare launchd environment: no arrays, no
# `timeout`, HOME and PATH exported here. Overrides, used by the tests:
#   MAC_RESUME_WAIT_S  how long to wait for the gates (default 180)
#   MAC_RESUME_POLL_S  pause between polls (default 10)
set -euo pipefail

# launchd starts a job with a bare environment: no HOME (the hub wrapper reads
# ~/.config/mooniex/org-db.env), PATH = /usr/bin:/bin:/usr/sbin:/sbin (no tmux, no tailscale).
export HOME="${HOME:-/Users/$(id -un)}"
export PATH="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}:/opt/homebrew/bin:/usr/local/bin:/Applications/Tailscale.app/Contents/MacOS"
# lib.config.self_host() never guesses and raises when no source names the host.
export ORG_HOST="${ORG_HOST:-mac}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p state/restart
LOG=state/restart/mac-resume.log
exec >>"$LOG" 2>&1

say() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) org-resume-mac: $*"; }

MARKER=state/restart/pending-mac.json
if [[ ! -f "$MARKER" ]]; then
  say "no $MARKER; nothing to resume"
  exit 0
fi
say "pending restart marker: $(tr -d '\n' < "$MARKER")"

# A default route exists. `route` is BSD; it exits non-zero when the table has no default.
net_up() { route -n get default >/dev/null 2>&1; }
# The tailnet has an address. Without a tailscale CLI we cannot tell, so this gate opens and
# the hub probe below (the hub is on the tailnet) is the real test.
tailnet_up() {
  command -v tailscale >/dev/null 2>&1 || return 0
  tailscale ip -4 >/dev/null 2>&1
}
# The Postgres hub answers a read-only query. perl alarm = the `timeout` macOS does not have.
hub_up() {
  perl -e 'alarm 20; exec @ARGV' -- bash scripts/hub/org-python.sh -c '
from lib import db
assert db.pg_url(), "Postgres hub required"
with db.get_conn(readonly=True, timeout=3) as conn:
    conn.execute("SELECT 1").fetchone()
' >/dev/null 2>&1
}

deadline=$((SECONDS + ${MAC_RESUME_WAIT_S:-180}))
while :; do
  gate=""
  if ! net_up; then gate=network
  elif ! tailnet_up; then gate=tailnet
  elif ! hub_up; then gate=hub
  fi
  [[ -z "$gate" ]] && break
  if (( SECONDS >= deadline )); then
    say "gave up after ${MAC_RESUME_WAIT_S:-180} s: $gate is still down; marker kept, run resume by hand"
    exit 1
  fi
  say "waiting for $gate"
  sleep "${MAC_RESUME_POLL_S:-10}"
done
say "network, tailnet and hub are up"

status=0
bash scripts/hub/org-python.sh tools/restart_run.py --host mac resume || status=$?
say "resume exited $status"
rep=0
bash scripts/hub/org-python.sh tools/restart_run.py --host mac report --notify || rep=$?
say "report --notify exited $rep"
[[ "$status" -ne 0 ]] || status=$rep
exit "$status"

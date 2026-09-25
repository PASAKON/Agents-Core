#!/usr/bin/env bash
# Infisical phase 1, the part after the CEO's login: create the `setup` identity + secret
# (bootstrap_setup_identity.mjs), then build the whole PLAN §3 layout
# (tools/infisical_setup.py apply --mint contabo), then wake the CTO session with one line.
# Run by watch_login.sh; safe to run again by hand. Never prints a secret.
set -u
ROOT=/opt/MoonieXHQ/Agents/Core
NODE=/opt/node-v22/bin/node
CDP=${1:-http://127.0.0.1:9281}
PANE=${WAKE_PANE:-cto-885ae930:0.0}
LOG=$ROOT/state/logs/infisical-p1.log
mkdir -p "$(dirname "$LOG")"
say() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }
wake() {
  # One short line into the CTO's own pane (a wrapped line is never submitted; ~100 chars max).
  tmux send-keys -t "$PANE" C-u "$1" Enter 2>/dev/null || say "tmux wake failed: $1"
  sleep 1; tmux send-keys -t "$PANE" C-m 2>/dev/null || true
}

say "after-login: start (cdp $CDP)"
if [ ! -f /etc/infisical/setup.env ]; then
  "$NODE" "$ROOT/scripts/infisical/bootstrap_setup_identity.mjs" "$CDP" >>"$LOG" 2>&1
  rc=$?
  if [ $rc -ne 0 ]; then
    say "bootstrap failed rc=$rc"
    wake "Infisical P1 auto: bootstrap FAILED rc=$rc — read state/logs/infisical-p1.log"
    exit $rc
  fi
  say "bootstrap OK: /etc/infisical/setup.env saved"
else
  say "setup.env already present, skipping bootstrap"
fi

cd "$ROOT" || exit 1
python3 tools/infisical_setup.py apply --mint contabo >>"$LOG" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
  say "apply failed rc=$rc"
  wake "Infisical P1 auto: apply FAILED rc=$rc — read state/logs/infisical-p1.log"
  exit $rc
fi
python3 tools/infisical_setup.py status >>"$LOG" 2>&1
say "apply OK"
wake "Infisical P1 auto: DONE — setup secret saved, apply OK; read state/logs/infisical-p1.log"

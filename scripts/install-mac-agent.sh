#!/usr/bin/env bash
# Install / uninstall the Mac drain agent as a launchd user agent.
#
# The agent polls the secretary's relay queue on Contabo over OUTBOUND ssh and
# executes only the enumerated actions in runners/mac_agent.py. Nothing listens
# on this machine — see that module's docstring for why the direction matters.
#
#   scripts/install-mac-agent.sh install     # write plist + load
#   scripts/install-mac-agent.sh uninstall   # unload + remove plist
#   scripts/install-mac-agent.sh status      # loaded? running? recent errors?
#
# Idempotent: installing twice replaces the plist and reloads, never duplicates.
set -euo pipefail

LABEL="com.mooniex.mac-agent"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$ROOT/.venv/bin/python"
OUT_LOG="/tmp/mooniex-mac-agent.out"
ERR_LOG="/tmp/mooniex-mac-agent.err"

usage() { echo "usage: $0 {install|uninstall|status}" >&2; exit 2; }

do_install() {
  [ -x "$PYTHON" ] || { echo "ERROR: no venv python at $PYTHON" >&2; exit 1; }
  [ -f "$ROOT/runners/mac_agent.py" ] || { echo "ERROR: runners/mac_agent.py missing" >&2; exit 1; }

  mkdir -p "$(dirname "$PLIST")"

  # Unload first so a re-install replaces cleanly instead of failing on a label
  # that is already loaded.
  launchctl unload "$PLIST" 2>/dev/null || true

  cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>${LABEL}</string>
	<key>ProgramArguments</key>
	<array>
		<string>${PYTHON}</string>
		<string>-m</string>
		<string>runners.mac_agent</string>
	</array>
	<key>WorkingDirectory</key>
	<string>${ROOT}</string>
	<key>RunAtLoad</key>
	<true/>
	<key>KeepAlive</key>
	<dict>
		<key>SuccessfulExit</key>
		<false/>
	</dict>
	<key>ThrottleInterval</key>
	<integer>30</integer>
	<key>StandardOutPath</key>
	<string>${OUT_LOG}</string>
	<key>StandardErrorPath</key>
	<string>${ERR_LOG}</string>
</dict>
</plist>
PLIST_EOF

  launchctl load "$PLIST"
  echo "installed + loaded: $LABEL"
  echo "  plist: $PLIST"
  echo "  logs:  $OUT_LOG / $ERR_LOG"
}

do_uninstall() {
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "uninstalled: $LABEL"
}

do_status() {
  if launchctl list | grep -q "$LABEL"; then
    echo "loaded:  yes"
    launchctl list | grep "$LABEL" | awk '{print "  pid="$1" last_exit="$2}'
  else
    echo "loaded:  no"
  fi
  if [ -f "$PLIST" ]; then echo "plist:   $PLIST"; else echo "plist:   (missing)"; fi
  if [ -s "$ERR_LOG" ]; then echo "recent errors:"; tail -5 "$ERR_LOG"; fi
}

case "${1:-}" in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  status)    do_status ;;
  *)         usage ;;
esac

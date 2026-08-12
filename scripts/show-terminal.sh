#!/usr/bin/env bash
# Open an iTerm2 window on the Mac showing a C-level chat that is ALREADY
# running — same tmux session, same scrollback, same process. Never spawns a
# new chat; spawn-cto.sh / spawn-cxo.sh are what do that.
#
# The point is the closed tab. A C-level chat runs inside tmux (`<role>-<id>`),
# so closing its iTerm tab only detaches that one client — the chat keeps
# running and the phone Console keeps showing it. This script attaches a fresh
# iTerm client back onto it. tmux allows any number of simultaneous clients
# (that IS the Mac/phone mirror), so it is safe to run while the phone is
# attached to the same session.
#
# Typed from the PHONE it still works: the C-level agent executes it on the
# Mac, which is where iTerm lives — so `/show-terminal` on the phone makes the
# Mac window reappear on the session you are chatting in.
#
# Usage:
#   bash scripts/show-terminal.sh              # THIS session (the one you're chatting in)
#   bash scripts/show-terminal.sh --list       # every live C-level session
#   bash scripts/show-terminal.sh 8172e36d     # a specific id
#   bash scripts/show-terminal.sh cmo-4f2a11bc # role-qualified name also accepted
#   bash scripts/show-terminal.sh --orphan     # most recent session with NO client attached
set -euo pipefail

ROLES_RE='^(cto|cmo|cgo|cfo)-'

live_sessions() {  # "<activity-epoch> <name> <attached>", newest first
  tmux list-sessions -F '#{session_activity} #{session_name} #{session_attached}' 2>/dev/null \
    | awk '$2 ~ /^(cto|cmo|cgo|cfo)-/' | sort -rn
}

case "${1:-}" in
  --list)
    found=0
    while read -r ts name att; do
      [ -n "${ts:-}" ] || continue
      printf '%-16s attached=%s  last-active=%s\n' \
        "$name" "$att" "$(date -r "$ts" '+%Y-%m-%d %H:%M')"
      found=1
    done < <(live_sessions)
    [ "$found" = "1" ] || echo "no live C-level sessions"
    exit 0
    ;;

  --orphan)
    # The closed-tab case: a session still running but with zero clients.
    SESSION="$(live_sessions | awk '$3 == 0 {print $2; exit}')"
    if [ -z "$SESSION" ]; then
      echo "no detached C-level session — every live one already has a client attached." >&2
      echo "see: bash scripts/show-terminal.sh --list" >&2
      exit 1
    fi
    ;;

  "")
    # Default: whichever session this script is being run from. Inside a
    # C-level chat that is the tmux session wrapping it, which is exactly the
    # session the phone is showing when the CEO types /show-terminal there.
    SESSION="$(tmux display-message -p '#S' 2>/dev/null || true)"
    if ! printf '%s' "$SESSION" | grep -qE "$ROLES_RE"; then
      echo "not inside a C-level tmux session — name an id, or use --orphan / --list" >&2
      exit 2
    fi
    ;;

  *)
    case "$1" in
      cto-*|cmo-*|cgo-*|cfo-*) SESSION="$1" ;;
      *)
        # Bare id: find whichever role owns it.
        SESSION="$(live_sessions | awk -v id="$1" '$2 ~ ("-" id "$") {print $2; exit}')"
        [ -n "$SESSION" ] || SESSION="cto-$1"
        ;;
    esac
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "no live tmux session named $SESSION — see: bash scripts/show-terminal.sh --list" >&2
      exit 1
    fi
    ;;
esac

osascript <<APPLESCRIPT
tell application "iTerm"
  activate
  set newWindow to (create window with default profile)
  tell current session of current tab of newWindow
    write text "tmux attach -t $SESSION"
  end tell
end tell
APPLESCRIPT

echo "iTerm window attached -> $SESSION"

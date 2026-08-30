#!/usr/bin/env bash
# Rename THIS C-level session's Claude display name (the one the mobile app /
# Remote Control list shows) to "<MACHINE> <ROLE> #<id> (<topic>)".
#
# Mechanism: /rename is a TUI-only command — an agent cannot call it as a tool.
# But every C-level chat runs inside tmux (spawn-cto.sh / spawn-cxo.sh), so we
# type the command into our OWN pane. The keys land in the input box and submit;
# while the agent is mid-turn they queue and execute right after the turn ends.
# Name changes propagate to claude.ai + the mobile app (bidirectional sync,
# Claude Code v2.1.221+).
#
# Usage:  bash scripts/session-rename.sh "หัวข้อของ session"
#   → /rename MAC CTO #c670eb50 (หัวข้อของ session)
#
# Called by /session-open step 3 (right after tab-title/tab-main), and any time
# the session's topic shifts enough that the mobile list would mislead.
#
# Guards:
#   - no $TMUX (e.g. Windows phase-1, plain terminal) → print what WOULD run,
#     exit 0 — the CEO can Ctrl+R-rename manually; never a hard failure.
#   - topic trimmed to 40 chars so the app list stays scannable.
set -euo pipefail

TOPIC="${1:-}"
if [ -z "$TOPIC" ]; then
  echo "usage: session-rename.sh \"<topic>\"" >&2
  exit 1
fi
# Keep the list scannable; the full story lives in the session itself.
TOPIC="$(printf '%s' "$TOPIC" | cut -c1-40)"

# Same machine-label logic as cto-claude.sh / cxo-claude.sh — keep in sync.
case "$(uname -s)" in
  Darwin) MACHINE_LABEL="MAC" ;;
  Linux)  if [ -d /opt/mooniex-agents ]; then MACHINE_LABEL="CONTABO"
          else MACHINE_LABEL="$(hostname -s 2>/dev/null | tr '[:lower:]' '[:upper:]')"; fi ;;
  MINGW*|MSYS*|CYGWIN*) MACHINE_LABEL="WINDOWS" ;;
  *) MACHINE_LABEL="$(uname -s | tr '[:lower:]' '[:upper:]')" ;;
esac

ROLE_UP="$(printf '%s' "${CXO_ROLE:-cto}" | tr '[:lower:]' '[:upper:]')"
SID="${CTO_SESSION_ID:-${CXO_SESSION_ID:-}}"

NEW_NAME="$MACHINE_LABEL $ROLE_UP${SID:+ #$SID} ($TOPIC)"

if [ -z "${TMUX:-}" ]; then
  echo "not inside tmux — rename manually: /rename $NEW_NAME"
  exit 0
fi

SESS="$(tmux display-message -p '#S')"
# -l = literal (no key-name expansion of the text), then a real Enter.
tmux send-keys -t "$SESS" -l "/rename $NEW_NAME"
tmux send-keys -t "$SESS" Enter
echo "queued: /rename $NEW_NAME (executes when the current turn ends)"

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
#         bash scripts/session-rename.sh --force "<topic>"   # resend even if unchanged
#         bash scripts/session-rename.sh --show              # print the recorded topic, no send
#
# State (task-460f3eaf): this used to be write-only — every call queued a
# /rename keystroke with no record of what it last set, so a caller could not
# tell whether a rename had landed, and could not call it routinely (every
# invocation retyped the command). It now records the topic it sends to
# state/locks/<role>-<id>.topic — the SAME sibling-file convention every other
# `.topic` writer in this repo uses (tools/session_name.py LOCK_SUFFIXES;
# see also tools/send_to_cxo.py's ephemeral-spawn dedupe slug, a different use
# of the same suffix). Full format + recovery notes: docs/SESSION-RENAME-STATE.md.
#
# Called by /session-open step 3 (right after tab-title/tab-main), and now also
# by /session-worktree and /session-close so the display name tracks the topic
# without a caller having to remember to run it — the recorded-topic check
# below makes repeat calls a no-op whenever nothing actually changed.
#
# Guards:
#   - no $TMUX (e.g. Windows phase-1, plain terminal) → print what WOULD run,
#     exit 0 — the CEO can Ctrl+R-rename manually; never a hard failure. This
#     branch never writes the record: nothing was actually applied, so there
#     is nothing to remember as "sent".
#   - topic trimmed to 40 chars so the app list stays scannable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCKS_DIR="$ROOT/state/locks"

FORCE=0
SHOW=0
PREFIX=""
TOPIC=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "--prefix" ]; then
    PREFIX="$arg"; prev=""; continue
  fi
  case "$arg" in
    --force) FORCE=1 ;;
    --show) SHOW=1 ;;
    --prefix) prev="--prefix" ;;
    *) TOPIC="$arg" ;;
  esac
done

ROLE="${CXO_ROLE:-cto}"
SID="${CTO_SESSION_ID:-${CXO_SESSION_ID:-}}"
# Only a live C-level session (one with an id) has a meaningful record — an
# ad-hoc/no-id invocation degrades to the old always-send behaviour below.
TOPIC_FILE=""
if [ -n "$SID" ]; then
  TOPIC_FILE="$LOCKS_DIR/$ROLE-$SID.topic"
fi

if [ "$SHOW" = "1" ]; then
  if [ -z "$TOPIC_FILE" ]; then
    echo "recorded: (none — no session id in CTO_SESSION_ID / CXO_SESSION_ID)"
    exit 0
  fi
  if [ -f "$TOPIC_FILE" ]; then
    echo "recorded: $(cat "$TOPIC_FILE")"
  else
    echo "recorded: (none)"
  fi
  exit 0
fi

if [ -z "$TOPIC" ]; then
  echo "usage: session-rename.sh [--force] [--show] [--prefix \"<glyph>\"] \"<topic>\"" >&2
  exit 1
fi
# Keep the list scannable; the full story lives in the session itself.
TOPIC="$(printf '%s' "$TOPIC" | cut -c1-40)"

# task-bbdfa8d1 (CEO 2026-09-11): a state glyph (✅ close · ⏸ save · ⛔
# merged) goes in front of the machine/role so the app list sorts and scans
# by state. Folded into the same dedupe/record key as TOPIC -- a prefix
# change alone (e.g. ⏸ -> ✅ on the same topic) must still send, and --show
# must still report exactly what was last sent.
RECORD_KEY="$TOPIC"
if [ -n "$PREFIX" ]; then
  RECORD_KEY="$PREFIX $TOPIC"
fi

if [ "$FORCE" != "1" ] && [ -n "$TOPIC_FILE" ] && [ -f "$TOPIC_FILE" ]; then
  RECORDED="$(cat "$TOPIC_FILE")"
  if [ "$RECORDED" = "$RECORD_KEY" ]; then
    echo "unchanged: $RECORD_KEY"
    exit 0
  fi
fi

# Same machine-label logic as cto-claude.sh / cxo-claude.sh — keep in sync.
case "$(uname -s)" in
  Darwin) MACHINE_LABEL="MAC" ;;
  Linux)  if [ -d /opt/mooniex-agents ]; then MACHINE_LABEL="CONTABO"
          else MACHINE_LABEL="$(hostname -s 2>/dev/null | tr '[:lower:]' '[:upper:]')"; fi ;;
  MINGW*|MSYS*|CYGWIN*) MACHINE_LABEL="WINDOWS" ;;
  *) MACHINE_LABEL="$(uname -s | tr '[:lower:]' '[:upper:]')" ;;
esac

ROLE_UP="$(printf '%s' "$ROLE" | tr '[:lower:]' '[:upper:]')"

BASE_NAME="$MACHINE_LABEL $ROLE_UP${SID:+ #$SID} ($TOPIC)"
if [ -n "$PREFIX" ]; then
  NEW_NAME="$PREFIX $BASE_NAME"
else
  NEW_NAME="$BASE_NAME"
fi

if [ -z "${TMUX:-}" ]; then
  echo "not inside tmux — rename manually: /rename $NEW_NAME"
  exit 0
fi

SESS="$(tmux display-message -p '#S')"
# -l = literal (no key-name expansion of the text), then a real Enter.
tmux send-keys -t "$SESS" -l "/rename $NEW_NAME"
tmux send-keys -t "$SESS" Enter
echo "queued: /rename $NEW_NAME (executes when the current turn ends)"

if [ -n "$TOPIC_FILE" ]; then
  mkdir -p "$LOCKS_DIR"
  printf '%s' "$RECORD_KEY" > "$TOPIC_FILE"
fi

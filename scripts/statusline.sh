#!/bin/bash
# Org statusline wrapper — renders the caveman badge + the current Claude Code
# session-id. Lives in the repo so it survives caveman-plugin updates (the badge
# logic stays in the plugin; this just calls it and appends the session-id).
#
# WHY: the session-id is needed to `/resume` a session after the model idles out
# or hits the subscription limit. It is otherwise only recoverable from the
# transcript dir (~/.claude/projects/<slug>/<id>.jsonl). This shows the last 8
# chars for quick recognition, and stashes the FULL id at
# ~/.claude/.last-session-id — `cat` it and paste into `claude --resume <id>`.
#
# Wire in ~/.claude/settings.json:
#   "statusLine": { "type": "command",
#                   "command": "bash \"/Users/gob/Projects/Agents/scripts/statusline.sh\"" }

set -u
CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

# --- read the statusline JSON Claude Code pipes in on stdin ---
INPUT="$(cat 2>/dev/null || true)"

# --- extract session_id. python3 is always present in this org; jq may not be. ---
SID_FULL="$(printf '%s' "$INPUT" | python3 -c '
import sys, json, re
try:
    d = json.load(sys.stdin)
    sid = (d.get("session_id") or "").strip()
    # UUID-ish sanitize: hex + dashes only, cap 64. Blocks escape injection.
    sys.stdout.write(re.sub(r"[^a-fA-F0-9-]", "", sid)[:64])
except Exception:
    pass
' 2>/dev/null)"

# Stash full id for easy copy/paste (last writer wins; fine for single-CTO flow).
if [ -n "$SID_FULL" ] && [ -d "$CONFIG_DIR" ]; then
  printf '%s\n' "$SID_FULL" > "$CONFIG_DIR/.last-session-id" 2>/dev/null || true
fi

# --- render the caveman badge (plugin script; reads its flag file, ignores stdin) ---
CAVEMAN_SCRIPT="$CONFIG_DIR/hooks/caveman-statusline.sh"
if [ -f "$CAVEMAN_SCRIPT" ]; then
  bash "$CAVEMAN_SCRIPT"
fi

# --- append a short session-id tag (last 8 chars) ---
if [ -n "$SID_FULL" ]; then
  SID_SHORT="${SID_FULL: -8}"
  printf '\033[38;5;60m[SID:%s]\033[0m' "$SID_SHORT"
fi

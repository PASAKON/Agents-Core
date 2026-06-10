#!/usr/bin/env bash
# Launch Claude Code CLI with any C-level role (cto/cmo/cgo/cfo) + org MCP server.
# Generalization of cto-claude.sh — all C-levels share the same MCP toolset
# (powers granted in policies/agents.yaml) and only differ in role doc +
# tab title + lock file prefix.
#
# Usage:
#   bash scripts/cxo-claude.sh --role cto [claude args...]
#   bash scripts/cxo-claude.sh --role cfo
#
# Phase 2 ephemeral-spawn flags (used by tools/send_to_cxo.py --spawn):
#   --session <id>            Override auto-generated session id. When set,
#                             the <role>-active pointer is NOT written so the
#                             primary CEO<->CXO tab remains untouched.
#   --initial-prompt <text>   Send this text into the new tab as the first
#                             user message once claude is running.
#   --tab-title <title>       Override the default tab title
#                             ("$DISPLAY #$CXO_SESSION_ID").
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

ROLE=""
SESSION_OVERRIDE=""
INITIAL_PROMPT=""
TAB_TITLE_OVERRIDE=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--role" ]; then
    ROLE="$a"; prev=""; continue
  fi
  if [ "$prev" = "--session" ]; then
    SESSION_OVERRIDE="$a"; prev=""; continue
  fi
  if [ "$prev" = "--initial-prompt" ]; then
    INITIAL_PROMPT="$a"; prev=""; continue
  fi
  if [ "$prev" = "--tab-title" ]; then
    TAB_TITLE_OVERRIDE="$a"; prev=""; continue
  fi
  case "$a" in
    --role)           prev="--role" ;;
    --session)        prev="--session" ;;
    --initial-prompt) prev="--initial-prompt" ;;
    --tab-title)      prev="--tab-title" ;;
    *)                ARGS+=("$a") ;;
  esac
done

if [ -z "$ROLE" ]; then
  echo "usage: cxo-claude.sh --role <cto|cmo|cgo|cfo> [claude args...]" >&2
  exit 2
fi

ROLE_DOC="$ROOT/roles/$ROLE.md"
if [ ! -f "$ROLE_DOC" ]; then
  echo "role doc not found: $ROLE_DOC" >&2
  exit 2
fi

# Resolve display name from policies/agents.yaml so the tab title +
# log lines match the canonical label (CTO / CMO / CGO / CFO).
DISPLAY="$(cd "$ROOT" && source .venv/bin/activate && python3 -c "
from lib.config import display_for, is_c_level
import sys
if not is_c_level('$ROLE'):
    print(f'role $ROLE is not a C-level role', file=sys.stderr)
    sys.exit(2)
print(display_for('$ROLE'))
")"
[ -n "$DISPLAY" ] || exit 2

ROLE_PROMPT="$(cat "$ROLE_DOC")"
MCP_CONFIG="$ROOT/config/cto.mcp.json"

# All C-levels get the same tool whitelist for now (same powers in
# agents.yaml). Keep in sync with runners/cto_mcp_server.py and with
# cto-claude.sh ALLOWED — the two launchers must not drift.
ALLOWED="mcp__org__wiki_read mcp__org__wiki_list mcp__org__wiki_search mcp__org__wiki_write mcp__org__create_task mcp__org__check_collisions mcp__org__delegate_task mcp__org__delegate_parallel_tasks mcp__org__get_task mcp__org__review_diff mcp__org__merge_task mcp__org__reopen_task mcp__org__list_projects mcp__org__stats mcp__org__recall mcp__org__reflect mcp__org__revert_task_tool Read Grep Glob Bash"

cd "$ROOT"

# CXO_* are the canonical env keys for any C-level session.
# CTO_SESSION_ID is also exported when role=cto so all existing tooling
# (delegate.py owner_cto, send_to_cto.py routing) keeps working unchanged.
export CXO_ROLE="$ROLE"
export CXO_SESSION=1

# Session ID: use override from --session flag (ephemeral spawn), else auto-pick.
# When SESSION_OVERRIDE is set the <role>-active pointer is intentionally skipped
# (ADR 2026-05-26, Decision 2) so the CEO's primary tab is never clobbered.
if [ -n "$SESSION_OVERRIDE" ]; then
  CXO_SESSION_ID="$SESSION_OVERRIDE"
else
  if [ -z "${CXO_SESSION_ID:-}" ]; then
    CXO_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
  fi
fi
export CXO_SESSION_ID

if [ "$ROLE" = "cto" ]; then
  export CTO_SESSION=1
  export CTO_SESSION_ID="$CXO_SESSION_ID"
fi

LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"
LOCKFILE="$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.lock"
if [ -e "$LOCKFILE" ]; then
  existing_pid="$(tr -d '[:space:]' <"$LOCKFILE" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "$DISPLAY id $CXO_SESSION_ID already running as pid $existing_pid — refuse to start a second one." >&2
    exit 1
  fi
  rm -f "$LOCKFILE"
fi
echo "$$" >"$LOCKFILE"

# Capture iTerm window id so tools/delegate.py + send_to_cxo can target
# this exact window. Matching by id is immune to title-flicker mishaps.
WINID_FILE="$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.winid"
MY_TTY="$(tty 2>/dev/null || true)"
if [ -n "$MY_TTY" ]; then
  WINID="$(osascript 2>/dev/null <<APPLE || true
tell application "iTerm"
  repeat with w in windows
    repeat with t in tabs of w
      repeat with s in sessions of t
        try
          if tty of s is "$MY_TTY" then
            return (id of w) as string
          end if
        end try
      end repeat
    end repeat
  end repeat
  return ""
end tell
APPLE
)"
  WINID="$(printf '%s' "$WINID" | tr -d '[:space:]')"
  if [ -n "$WINID" ]; then
    echo "$WINID" >"$WINID_FILE"
  fi
fi

# Save our tty so scripts/tab-title.sh can retitle this tab from inside
# claude Bash tool calls (those subshells have no controlling tty).
TTY_FILE="$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.tty"
if [ -n "$MY_TTY" ]; then
  echo "$MY_TTY" >"$TTY_FILE"
fi

# Active-session pointer: only written for non-ephemeral sessions.
# Ephemeral spawns (--session flag set) must never overwrite this pointer
# so CEO's direct-chat tab with the C-level stays single-threaded.
ACTIVE_FILE="$LOCKS_DIR/$ROLE-active"
if [ -z "$SESSION_OVERRIDE" ]; then
  echo "$CXO_SESSION_ID" >"$ACTIVE_FILE"
fi

# Register session in c_level_sessions DB so gate 4 can query it later.
# stdio detached: a backgrounded child holding our stdout/stderr pipes
# makes programmatic callers (tests, capture_output) hang until it exits.
(cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
  python3 -m tools.register_cxo --role "$ROLE" --session "$CXO_SESSION_ID" 2>/dev/null || true) >/dev/null 2>&1 </dev/null &

# Launch idle-ping watcher — EPHEMERAL sessions only (--session set by
# send_to_cxo --spawn). Primary CEO<->CXO tabs must never be idle-pinged:
# each ping is a user message the model answers (token burn on idle) and
# a non-reply would auto-close the CEO's own chat tab.
# PID written to state/locks/<role>-<sid>.watcher-pid for GC tracking.
if [ -n "$SESSION_OVERRIDE" ]; then
  bash "$ROOT/scripts/idle-ping-watcher.sh" --role "$ROLE" --session "$CXO_SESSION_ID" >/dev/null 2>&1 </dev/null &
  disown $!
fi

cleanup() {
  rm -f "$LOCKFILE" "$WINID_FILE" "$TTY_FILE"
  # Only clear the active pointer if it still points at us and we wrote it.
  if [ -z "$SESSION_OVERRIDE" ] && [ -e "$ACTIVE_FILE" ]; then
    current="$(tr -d '[:space:]' <"$ACTIVE_FILE" 2>/dev/null || true)"
    if [ "$current" = "$CXO_SESSION_ID" ]; then
      rm -f "$ACTIVE_FILE"
    fi
  fi
}
trap cleanup EXIT INT TERM

# Tab title: use override (ephemeral spawn) or default primary-session format.
if [ -n "$TAB_TITLE_OVERRIDE" ]; then
  TAB_TITLE="$TAB_TITLE_OVERRIDE"
else
  TAB_TITLE="$DISPLAY #$CXO_SESSION_ID"
fi

# Base prefix + initial title for scripts/tab-title.sh (IRON-RULES §32).
# The C-level agent rewrites the summary part after every finished job;
# routing (send_to_cxo / initial-prompt injection) matches the base prefix.
TITLES_DIR="$ROOT/state/tab-titles"
mkdir -p "$TITLES_DIR"
printf '%s\n' "$TAB_TITLE" >"$TITLES_DIR/$ROLE-$CXO_SESSION_ID.base"
printf '%s ⏳ เริ่ม session\n' "$TAB_TITLE" >"$TITLES_DIR/$ROLE-$CXO_SESSION_ID.title"
printf '\033]0;%s ⏳ เริ่ม session\007' "$TAB_TITLE"

# Keep claude CLI from overwriting our tab title with its own (no-op on
# builds without this env). The keeper loop below re-asserts regardless.
export CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1

# Title keeper: re-assert the saved title every 60s while this session
# lives — survives zsh precmd resets + claude CLI title rewrites.
# stdio detached so callers capturing this script's output don't block
# on the keeper's inherited pipe (exits ≤60s after the lock disappears).
(
  while [ -e "$LOCKFILE" ]; do
    bash "$ROOT/scripts/tab-title.sh" --reassert >/dev/null 2>&1 || true
    sleep 60
  done
) >/dev/null 2>&1 </dev/null &
disown $!

# Initial prompt injection: background job sends prompt into this tab once
# claude is ready. Uses osascript `on run argv` handler so prompt text is
# passed as a CLI arg — no shell escaping needed inside the AppleScript string.
# Delay is configurable for tests via CXO_INITIAL_PROMPT_DELAY (default 5s).
if [ -n "${INITIAL_PROMPT:-}" ]; then
  _DELAY="${CXO_INITIAL_PROMPT_DELAY:-5}"
  _TAB_TITLE="$TAB_TITLE"
  _PROMPT="$INITIAL_PROMPT"
  (
    sleep "$_DELAY"
    osascript - "$_TAB_TITLE" "$_PROMPT" <<'APPLEEOF'
on run argv
  set tabMatch to item 1 of argv
  set promptText to item 2 of argv
  tell application "iTerm"
    repeat with w in windows
      repeat with t in tabs of w
        tell t
          try
            set tabName to ""
            try
              set tabName to name of t
            end try
            set sessName to ""
            try
              set sessName to name of current session of t
            end try
            if (tabName contains tabMatch) or (sessName contains tabMatch) then
              tell current session
                write text promptText newline NO
                write text (ASCII character 13) newline NO
              end tell
            end if
          end try
        end tell
      end repeat
    end repeat
  end tell
end run
APPLEEOF
  ) >/dev/null 2>&1 </dev/null &
fi

# `exec` would skip the EXIT trap → stale lock. Run claude as child.
claude \
  -n "$TAB_TITLE" \
  --model 'claude-fable-5' \
  --fallback-model 'claude-opus-4-8[1m]' \
  --effort max \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  --allowed-tools $ALLOWED \
  ${ARGS[@]+"${ARGS[@]}"}
exit $?

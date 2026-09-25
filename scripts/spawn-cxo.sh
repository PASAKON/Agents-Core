#!/usr/bin/env bash
# Spawn an iTerm2 window with a C-level chat tab (cto/cmo/cgo/cfo).
# Generalization of spawn-cto.sh — all C-levels share the same spawn
# machinery and only differ in role doc + tab title + lock prefix.
#
# Usage:
#   bash scripts/spawn-cxo.sh --role cfo                    # fresh session
#   bash scripts/spawn-cxo.sh --role cmo --last             # claude -c
#   bash scripts/spawn-cxo.sh --role cgo --resume <id>      # claude -r <id>
#   bash scripts/spawn-cxo.sh --role cto --with-logs        # also open log tabs
#   bash scripts/spawn-cxo.sh --role cfo --id <id>          # force a specific id
#
# Phase 2 flag passthrough note:
#   Unknown flags fall into ARGS and are forwarded to cxo-claude.sh via
#   $CLAUDE_ARGS. Simple single-word flags pass through; multi-word values
#   (e.g. --tab-title "CFO <- CTO: topic") are not reliably forwarded due to
#   word-splitting. For ephemeral spawns from tools/send_to_cxo.py --spawn,
#   use the _spawn_new_ephemeral() temp-script path — it calls cxo-claude.sh
#   directly with no shell-in-shell quoting issues.
#
# Inherited CXO_SESSION_ID is intentionally ignored — re-running this
# from inside an existing C-level chat would otherwise duplicate the id.
set -euo pipefail

ROOT="/Users/gob/MoonieXHQ/Agents/Core"

ROLE=""
WITH_LOGS=0
EXPLICIT_ID=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--role" ]; then
    ROLE="$a"; prev=""; continue
  fi
  if [ "$prev" = "--id" ]; then
    EXPLICIT_ID="$a"; prev=""; continue
  fi
  case "$a" in
    --role) prev="--role" ;;
    --id)   prev="--id" ;;
    --with-logs) WITH_LOGS=1 ;;
    *) ARGS+=("$a") ;;
  esac
done

if [ -z "$ROLE" ]; then
  echo "usage: spawn-cxo.sh --role <cto|cmo|cgo|cfo> [--new|--last|--resume <id>|--with-logs|--id <id>]" >&2
  exit 2
fi

# Validate role early so we fail before any AppleScript work.
if [ ! -f "$ROOT/roles/$ROLE.md" ]; then
  echo "role doc not found: $ROOT/roles/$ROLE.md" >&2
  exit 2
fi

# Never inherit a session id from the parent shell.
unset CXO_SESSION_ID CTO_SESSION_ID
if [ -n "$EXPLICIT_ID" ]; then
  CXO_SESSION_ID="$EXPLICIT_ID"
fi

# Translate session args → claude CLI args (identical to spawn-cto.sh).
CLAUDE_ARGS=""
case "${ARGS[0]:-}" in
  --last) CLAUDE_ARGS="-c" ;;
  --resume)
    # `claude -r/--resume` needs an exact session-ID match (or falls into
    # picker mode) — the org's short id is only the trailing 8 hex chars of
    # the real UUID. Resolution order: the .uuid file this launcher writes
    # at spawn time, then c_level_sessions.resume_uuid (copied from that same
    # file at close time — tools/session_status.record_close), which is what
    # survives the file being deleted (measured 2026-09-18 on the cto role:
    # 41 of 42 closed sessions with a DB resume_uuid had no .uuid file left
    # on disk — a disk-cleanup sweep, not this launcher, is the presumed
    # cause). Neither source is trusted blindly: the result is validated
    # against the real uuid shape before being handed to `claude -r`, because
    # `claude -r <short-id>` does not error — it silently opens a brand-new
    # session, which is exactly how this bug hid as a normal success line
    # (task-a98788d7). A bare short id must never reach `claude -r`.
    RESUME_ID="${ARGS[1]:-}"
    RESUME_UUID_FILE="$ROOT/state/locks/$ROLE-$RESUME_ID.uuid"
    if [ -f "$RESUME_UUID_FILE" ]; then
      RESUME_TARGET="$(tr -d '[:space:]' <"$RESUME_UUID_FILE")"
    else
      RESUME_TARGET="$(cd "$ROOT" && python3 -m tools.session_status resume \
        --role "$ROLE" --session-id "$RESUME_ID" 2>/dev/null || true)"
    fi
    if ! [[ "$RESUME_TARGET" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
      echo "refuse to resume $ROLE-$RESUME_ID: no resumable UUID found." >&2
      echo "  checked: $RESUME_UUID_FILE" >&2
      echo "  checked: c_level_sessions.resume_uuid (role=$ROLE, session_id=$RESUME_ID) in $ROOT/state/tasks.db" >&2
      echo "  a short id is not a valid 'claude -r' target — refusing rather than silently opening a new session." >&2
      exit 1
    fi
    CLAUDE_ARGS="-r $RESUME_TARGET"
    ;;
  --new|"") CLAUDE_ARGS="" ;;
  *) CLAUDE_ARGS="${ARGS[*]}" ;;
esac

if ! [ -d "$ROOT/.venv" ]; then
  echo "venv not found at $ROOT/.venv — run scripts/setup.sh first" >&2
  exit 1
fi

# Resolve display name (CTO / CMO / CGO / CFO) for tab title + log file.
DISPLAY="$(cd "$ROOT" && source .venv/bin/activate && python3 -c "
from lib.config import display_for, is_c_level
import sys
if not is_c_level('$ROLE'):
    print('role $ROLE is not a C-level role', file=sys.stderr); sys.exit(2)
print(display_for('$ROLE'))
")"
[ -n "$DISPLAY" ] || exit 2

LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"

is_id_live() {
  local lock="$LOCKS_DIR/$ROLE-$1.lock"
  [ -e "$lock" ] || return 1
  local pid
  pid="$(tr -d '[:space:]' <"$lock" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  if kill -0 "$pid" 2>/dev/null; then
    return 0
  fi
  rm -f "$lock"
  return 1
}

if [ -n "${CXO_SESSION_ID:-}" ]; then
  if is_id_live "$CXO_SESSION_ID"; then
    echo "$DISPLAY id $CXO_SESSION_ID already running (see $LOCKS_DIR/$ROLE-$CXO_SESSION_ID.lock)" >&2
    exit 1
  fi
else
  for _try in 1 2 3 4 5 6 7 8 9 10; do
    candidate="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    if ! is_id_live "$candidate"; then
      CXO_SESSION_ID="$candidate"
      break
    fi
  done
  if [ -z "${CXO_SESSION_ID:-}" ]; then
    echo "could not pick an unused $DISPLAY id after 10 tries" >&2
    exit 1
  fi
fi

# Surface lock/tmux drift now, while someone is looking — lock_only (dead pid
# or no tmux), tmux_only (tmux with no lock), or an orphan (live pid, no tmux).
# --quiet prints nothing on a clean box so this can run every spawn without
# spam; drift is what the CEO needs to see here, not 9h later. Read-only and
# non-fatal — fail-open, same reasoning as the cap check below.
( cd "$ROOT" && python3 -m tools.session_gc --report --quiet \
      --locks-dir "$LOCKS_DIR" ) >&2 || true

# Same cap as spawn-cto.sh, and the same reasoning — a session is roughly a
# gigabyte once it carries a day of conversation, and the box running these
# also runs production. The number and the rationale live in
# tools/session_cap.py so the two launchers and the Main Tab banner cannot
# drift to three different answers. Not suppressible: this is a capacity
# limit, not a nag.
CAP_RC=0
(cd "$ROOT" && python3 -m tools.session_cap --check-spawn \
    --locks-dir "$LOCKS_DIR") || CAP_RC=$?
# Only exit 2 means "over the cap". Anything else means the checker itself
# could not run — fail OPEN there rather than blocking the CEO's work over a
# broken guard.
if [ "$CAP_RC" -eq 2 ]; then
  echo "" >&2
  echo "   Live now:" >&2
  (cd "$ROOT" && python3 -m tools.session_cap --list \
      --locks-dir "$LOCKS_DIR" 2>/dev/null) | sed 's/^/     /' >&2
  echo "" >&2
  echo "   Close one (its work is what the cap is really counting), then retry." >&2
  echo "" >&2
  exit 1
elif [ "$CAP_RC" -ne 0 ]; then
  echo "session-cap check unavailable (exit $CAP_RC) — spawning anyway." >&2
fi

TAB_TITLE="$DISPLAY #$CXO_SESSION_ID"
LOG_FILE="$ROOT/state/logs/$ROLE-$CXO_SESSION_ID.log"
mkdir -p "$ROOT/state/logs"
touch "$LOG_FILE"


# Same fresh-login-shell problem as spawn-cto.sh: osascript `write text` drops
# the caller's exports, so CXO_EXTRA_MCP / CXO_SKIP_MCP were no-ops through
# this launcher. Re-export them inside the command string.
ENV_PREFIX=""
for v in CXO_EXTRA_MCP CXO_SKIP_MCP CXO_STRICT_MCP CXO_SUPABASE_PROJECT_REF \
         CXO_SUPABASE_WRITE; do
  [ -n "${!v:-}" ] || continue
  ENV_PREFIX="${ENV_PREFIX}export $v=$(printf '%q' "${!v}") && "
done

# Belt-and-braces auto-compact window (task-9f6fec26): the real fix lives in
# claude-home/settings.json's `autoCompactWindow` key and in cxo-claude.sh's
# own export (which runs inside the shell that actually execs claude), so
# this line is defense-in-depth only if unset.
: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW
# Same tmux wrapping as spawn-cto.sh, for the same reason: the CEO's phone has
# to be able to attach the very session this tab is showing. `<role>-<slug>` is
# the shape MoonieX Console's list filter requires, and cmo/cfo/cxo are all
# already in its ROLES (mooniex-console src/tmux/names.js) — so every C-level
# spawned here shows up on the phone, not just the CTO.
TMUX_SESSION="$ROLE-$CXO_SESSION_ID"

# Through a file, to avoid nesting quotes inside both the tmux argv and the
# AppleScript string literal further down.
RUN_FILE="$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.run"
printf '#!/usr/bin/env bash\n%s\n' \
  "${ENV_PREFIX}export CXO_SESSION_ID='$CXO_SESSION_ID' && exec bash '$ROOT/scripts/cxo-claude.sh' --role $ROLE $CLAUDE_ARGS" \
  >"$RUN_FILE"
chmod +x "$RUN_FILE"

# A tmux server started without a UTF-8 locale rewrites non-ASCII and TABs in
# its own output to underscores, which corrupts Thai in the pane and breaks the
# console's tab-separated `list-sessions` parse. The server keeps the first
# environment it ever saw, which may be this shell's.
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
  *[Uu][Tt][Ff]*8*) ;;
  *) export LANG=en_US.UTF-8 ;;
esac

tmux start-server 2>/dev/null || true
# `latest`, not the default `smallest` — otherwise the Mac window shrinks to
# phone width the moment the phone attaches. Status bar off: tmux is plumbing
# here and the row is worth more to the chat. CEO decision 2026-08-07.
tmux set-option -g window-size latest 2>/dev/null || true
tmux set-option -g status off 2>/dev/null || true
# extended-keys off (tmux 3.2+ default) swallows Shift+Enter's CSI-u sequence
# from iTerm2 — Claude Code then sees plain Enter and submits instead of
# inserting a newline. CEO-reported bug 2026-08-07.
tmux set-option -g extended-keys on 2>/dev/null || true

CHAT_CMD="tmux new-session -A -s '$TMUX_SESSION' -c '$ROOT' bash '$RUN_FILE'"
LOG_CMD="cd '$ROOT' && tail -F state/logs/$ROLE-$CXO_SESSION_ID.log"
DEV_CMD="cd '$ROOT' && bash scripts/tail-dev-logs.sh"

EXTRA_TABS=""
if [ "$WITH_LOGS" = "1" ]; then
  EXTRA_TABS=$(cat <<APPLESCRIPT_EXTRA

    set logTab to (create tab with default profile)
    tell current session of logTab
      set name to "$DISPLAY Log #$CXO_SESSION_ID"
      write text "$LOG_CMD"
    end tell

    set devTab to (create tab with default profile)
    tell current session of devTab
      set name to "Dev Logs"
      write text "$DEV_CMD"
    end tell

    select first tab
APPLESCRIPT_EXTRA
)
fi

osascript <<APPLESCRIPT
tell application "iTerm"
  set newWindow to (create window with default profile)
  tell newWindow
    tell current session of current tab
      set name to "$TAB_TITLE"
      write text "$CHAT_CMD"
    end tell
$EXTRA_TABS
  end tell
end tell
APPLESCRIPT

PROVIDER_NOTE=""

if [ "$WITH_LOGS" = "1" ]; then
  echo "spawned iTerm window id=$CXO_SESSION_ID ($DISPLAY chat + log + dev logs).$PROVIDER_NOTE"
else
  echo "spawned iTerm window id=$CXO_SESSION_ID (logs at state/logs/$ROLE-$CXO_SESSION_ID.log)$PROVIDER_NOTE"
fi

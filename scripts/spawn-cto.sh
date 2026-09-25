#!/usr/bin/env bash
# Spawn an iTerm2 window with the CTO chat tab (default).
#   tab 1: Claude Code CLI w/ CTO role (scripts/cto-claude.sh)
#
# CTO + Dev log tabs are NOT opened by default — CEO does not watch them;
# the AI consumes logs via hooks. Pass --with-logs to also open them, or
# tail on demand: `tail -F state/logs/cto.log`.
#
# Usage:
#   bash scripts/spawn-cto.sh                # fresh Claude Code session
#   bash scripts/spawn-cto.sh --new          # fresh (alias)
#   bash scripts/spawn-cto.sh --last         # resume most recent (claude -c)
#   bash scripts/spawn-cto.sh --resume <id>  # claude -r <id>
#   bash scripts/spawn-cto.sh --with-logs    # also open cto.log + dev logs tabs
#   bash scripts/spawn-cto.sh --id <id>      # force a specific CTO id (collision-checked)
#
# Inherited CTO_SESSION_ID from the parent shell is intentionally
# ignored — running this script from inside an existing CTO chat would
# otherwise duplicate that chat's id into the new tab.
set -euo pipefail

ROOT="/Users/gob/MoonieXHQ/Agents/Core"

WITH_LOGS=0
EXPLICIT_ID=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--id" ]; then
    EXPLICIT_ID="$a"
    prev=""
    continue
  fi
  case "$a" in
    --with-logs) WITH_LOGS=1 ;;
    --id) prev="--id" ;;
    *) ARGS+=("$a") ;;
  esac
done

# Never inherit CTO_SESSION_ID from the parent shell. Running spawn-cto.sh
# from inside an existing CTO chat would otherwise clone the running id
# into the new tab. Explicit `--id <id>` is the only supported override.
unset CTO_SESSION_ID
if [ -n "$EXPLICIT_ID" ]; then
  CTO_SESSION_ID="$EXPLICIT_ID"
fi

# Translate legacy cto_chat args → claude CLI args
CLAUDE_ARGS=""
case "${ARGS[0]:-}" in
  --last) CLAUDE_ARGS="-c" ;;
  --resume)
    # `claude -r/--resume` needs an exact session-ID match (or falls into
    # picker mode) — the org's short id is only the trailing 8 hex chars of
    # the real UUID. Resolution order: the .uuid file this launcher writes
    # at spawn time, then c_level_sessions.resume_uuid (copied from that same
    # file at close time — tools/session_status.record_close), which is what
    # survives the file being deleted (measured 2026-09-18: 41 of 42 closed
    # sessions with a DB resume_uuid had no .uuid file left on disk — a
    # disk-cleanup sweep, not this launcher, is the presumed cause). Neither
    # source is trusted blindly: the result is validated against the real
    # uuid shape before being handed to `claude -r`, because `claude -r
    # <short-id>` does not error — it silently opens a brand-new session,
    # which is exactly how this bug hid as a normal success line
    # (task-a98788d7). A bare short id must never reach `claude -r`.
    RESUME_ID="${ARGS[1]:-}"
    RESUME_UUID_FILE="$ROOT/state/locks/cto-$RESUME_ID.uuid"
    if [ -f "$RESUME_UUID_FILE" ]; then
      RESUME_TARGET="$(tr -d '[:space:]' <"$RESUME_UUID_FILE")"
    else
      RESUME_TARGET="$(cd "$ROOT" && python3 -m tools.session_status resume \
        --role cto --session-id "$RESUME_ID" 2>/dev/null || true)"
    fi
    if ! [[ "$RESUME_TARGET" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
      echo "refuse to resume cto-$RESUME_ID: no resumable UUID found." >&2
      echo "  checked: $RESUME_UUID_FILE" >&2
      echo "  checked: c_level_sessions.resume_uuid (role=cto, session_id=$RESUME_ID) in $ROOT/state/tasks.db" >&2
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

# Generate a short CTO session ID so DEV reports route only to this CTO.
# Injected as CTO_SESSION_ID env into cto-claude.sh + MCP server.
#
# Collision avoidance: a lock file at state/locks/cto-<ID>.lock means a
# CTO chat is currently using that ID. If the PID inside is live, pick
# a different ID — reusing it would mis-route DEV replies. Stale locks
# (dead PID) are reaped. An explicit CTO_SESSION_ID from the parent env
# is honored but rejected outright if it collides with a live process.
LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"

is_id_live() {
  local lock="$LOCKS_DIR/cto-$1.lock"
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

if [ -n "${CTO_SESSION_ID:-}" ]; then
  if is_id_live "$CTO_SESSION_ID"; then
    echo "CTO id $CTO_SESSION_ID already running (see $LOCKS_DIR/cto-$CTO_SESSION_ID.lock) — refuse to spawn duplicate" >&2
    exit 1
  fi
else
  for _try in 1 2 3 4 5 6 7 8 9 10; do
    candidate="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
    if ! is_id_live "$candidate"; then
      CTO_SESSION_ID="$candidate"
      break
    fi
  done
  if [ -z "${CTO_SESSION_ID:-}" ]; then
    echo "could not pick an unused CTO id after 10 tries" >&2
    exit 1
  fi
fi

# Surface lock/tmux drift now, while someone is looking — a lock whose pid is
# dead or whose tmux is gone (lock_only), a tmux session with no lock
# (tmux_only), or worse an orphan (live pid, no tmux). --quiet prints nothing
# on a clean box, so this can run every spawn without spam; drift is what the
# CEO needs to see here, not 9h later. Read-only and non-fatal — a reconcile
# that cannot run never blocks a spawn (fail-open, same reasoning as the cap).
( cd "$ROOT" && python3 -m tools.session_gc --report --quiet \
      --locks-dir "$LOCKS_DIR" ) >&2 || true

# Advisory only. A second live CTO chat costs roughly another 1 GB of
# phys_footprint on the 8 GB M1 (measured 2026-08-06: claude core ~340 MB
# plus its MCP subtree), and the box already sits at ~150 MB unused. Warn,
# never kill: a chat sitting quiet is often waiting on a DEV, and reaping on
# idleness alone has silently killed live work before.
# Set CXO_NO_SESSION_WARN=1 to silence; skipped automatically when stdin is
# not a terminal so scripted spawns never stall.
enforce_session_cap() {
  # Hard gate first, and it is NOT suppressible: a session is roughly a
  # gigabyte once it has a day of conversation behind it, and the box running
  # these also runs production. tools/session_cap.py holds the number and the
  # reasoning; keeping it there means spawn-cto.sh, spawn-cxo.sh and the Main
  # Tab banner cannot drift to three different answers.
  local rc=0
  (cd "$ROOT" && python3 -m tools.session_cap --check-spawn \
      --locks-dir "$LOCKS_DIR") || rc=$?
  # Only exit 2 means "over the cap". Anything else means the checker itself
  # could not run — a relocated ROOT with no tools/ package, a broken python.
  # Fail OPEN there: a capacity guard that blocks the CEO's work because its
  # own tooling is missing is worse than no guard.
  if [ "$rc" -eq 2 ]; then
    echo "" >&2
    echo "   Live now:" >&2
    (cd "$ROOT" && python3 -m tools.session_cap --list \
        --locks-dir "$LOCKS_DIR" 2>/dev/null) | sed 's/^/     /' >&2
    echo "" >&2
    echo "   Close one (its work is what the cap is really counting), then retry." >&2
    echo "" >&2
    exit 1
  elif [ "$rc" -ne 0 ]; then
    echo "session-cap check unavailable (exit $rc) — spawning anyway." >&2
  fi

  # Advisory listing below. This part stays silenceable — it is a courtesy,
  # not the limit.
  [ "${CXO_NO_SESSION_WARN:-0}" = "1" ] && return 0
  [ -t 0 ] || return 0
  local lock pid sid found=0
  for lock in "$LOCKS_DIR"/cto-*.lock; do
    [ -e "$lock" ] || continue
    pid="$(tr -d '[:space:]' <"$lock" 2>/dev/null || true)"
    [ -n "$pid" ] || continue
    kill -0 "$pid" 2>/dev/null || continue
    sid="$(basename "$lock" .lock)"; sid="${sid#cto-}"
    [ "$sid" = "$CTO_SESSION_ID" ] && continue
    if [ "$found" -eq 0 ]; then
      echo "" >&2
      echo "⚠  CTO chat already running:" >&2
      found=1
    fi
    printf '     #%s  up %s\n' "$sid" \
      "$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ' || echo '?')" >&2
  done
  [ "$found" -eq 1 ] || return 0
  echo "   Each live chat holds ~1 GB on this 8 GB box." >&2
  echo "   Resume it instead:  bash scripts/spawn-cto.sh --last" >&2
  echo "   Spawning a NEW session in 3s — Ctrl-C to abort." >&2
  echo "" >&2
  sleep 3
}
enforce_session_cap

CTO_TAB_TITLE="CTO #$CTO_SESSION_ID"
CTO_LOG="$ROOT/state/logs/cto-$CTO_SESSION_ID.log"

mkdir -p "$ROOT/state/logs"
touch "$CTO_LOG"


# osascript `write text` runs CHAT_CMD in a FRESH login shell, so anything the
# caller exported is already gone by the time cto-claude.sh reads it. That is
# why `CXO_EXTRA_MCP=meigen bash scripts/spawn-cto.sh` silently launched with
# the stock role set — the documented per-launch overrides only ever worked
# when cto-claude.sh was run directly. Re-export them inside the command
ENV_PREFIX=""
for v in CXO_EXTRA_MCP CXO_SKIP_MCP CXO_STRICT_MCP CXO_SUPABASE_PROJECT_REF \
         CXO_SUPABASE_WRITE; do
  [ -n "${!v:-}" ] || continue
  ENV_PREFIX="${ENV_PREFIX}export $v=$(printf '%q' "${!v}") && "
done

# Belt-and-braces auto-compact window (task-9f6fec26): the real fix lives in
# claude-home/settings.json's `autoCompactWindow` key and in cto-claude.sh's
# own export (which runs inside the shell that actually execs claude), so
# this line is defense-in-depth only if unset.
: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW
# The chat runs inside a tmux session instead of straight in the iTerm tab, so
# the pty can have more than one client: iTerm attaches here, and MoonieX
# Console attaches the same session over the tailnet from the phone
# (`tmux attach-session -t cto-<id>`, mooniex-console src/tmux/bridge.js). Both
# clients see the same stream and both can type — that is the whole mirror, and
# tmux, not us, is what makes it real. The session name MUST stay
# `<role>-<slug>` or the console's list filters it out (src/tmux/names.js).
TMUX_SESSION="cto-$CTO_SESSION_ID"

# The command goes through a file rather than being nested inside both the tmux
# argv and the AppleScript string literal below — two layers of quoting over a
# command that already contains quoted paths and `&&`.
RUN_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.run"
printf '#!/usr/bin/env bash\n%s\n' \
  "${ENV_PREFIX}export CTO_SESSION_ID='$CTO_SESSION_ID' && exec bash '$ROOT/scripts/cto-claude.sh' $CLAUDE_ARGS" \
  >"$RUN_FILE"
chmod +x "$RUN_FILE"

# A tmux server with no UTF-8 locale silently rewrites non-ASCII — and TABs —
# in its own output into underscores, which breaks both Thai text in the pane
# and the console's tab-separated `list-sessions` parse (cost: one debugging
# session, 2026-08-07). The server keeps whatever environment it was first
# started with, and that may well be this shell.
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
  *[Uu][Tt][Ff]*8*) ;;
  *) export LANG=en_US.UTF-8 ;;
esac

# Server-wide options need a running server, and the server would otherwise
# first come into existence inside the iTerm tab, after the session is built.
tmux start-server 2>/dev/null || true

# Size the window to whichever client interacted last, not to the smallest one
# attached: on the default `smallest` the Mac window collapses to phone width
# the moment the phone attaches, and stays there. CEO decision 2026-08-07.
tmux set-option -g window-size latest 2>/dev/null || true

# tmux is plumbing here, not a UI. Its status bar is pure regression on both
# surfaces: it steals a row from the Claude chat, and it re-states what both
# clients already show anyway — the iTerm tab title on the Mac, the session
# header in the console on the phone. The CEO's tab has to keep looking like
# the iTerm tab it has always been.
tmux set-option -g status off 2>/dev/null || true

# tmux 3.2+ defaults extended-keys to off, which swallows the CSI-u sequence
# iTerm2 sends for Shift+Enter — Claude Code then sees plain Enter and submits
# instead of inserting a newline. CEO-reported bug 2026-08-07.
tmux set-option -g extended-keys on 2>/dev/null || true

# -A attaches if the session already exists and creates it otherwise. Creating
# it from INSIDE the iTerm tab, rather than detached here, guarantees a client
# is attached from the very first moment — which is what cto-claude.sh's
# client_tty lookup needs in order to resolve the real iTerm tty.
CHAT_CMD="tmux new-session -A -s '$TMUX_SESSION' -c '$ROOT' bash '$RUN_FILE'"
LOG_CMD="cd '$ROOT' && tail -F state/logs/cto-$CTO_SESSION_ID.log"
DEV_CMD="cd '$ROOT' && bash scripts/tail-dev-logs.sh"

EXTRA_TABS=""
if [ "$WITH_LOGS" = "1" ]; then
  EXTRA_TABS=$(cat <<APPLESCRIPT_EXTRA

    set logTab to (create tab with default profile)
    tell current session of logTab
      set name to "CTO Log #$CTO_SESSION_ID"
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
      set name to "$CTO_TAB_TITLE"
      write text "$CHAT_CMD"
    end tell
$EXTRA_TABS
  end tell
end tell
APPLESCRIPT

PROVIDER_NOTE=""
if [ "$WITH_LOGS" = "1" ]; then
  echo "spawned iTerm window id=$CTO_SESSION_ID (CTO chat + log + dev logs).$PROVIDER_NOTE"
else
  echo "spawned iTerm window id=$CTO_SESSION_ID (logs at state/logs/cto-$CTO_SESSION_ID.log)$PROVIDER_NOTE"
fi

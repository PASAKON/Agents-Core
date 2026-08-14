#!/usr/bin/env bash
# Launch Claude Code CLI with CTO role + org MCP server.
# Same UI as plain Claude Code — only difference is system prompt + tools.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# --session <id>: mirrors cxo-claude.sh's SESSION_OVERRIDE exactly (task
# task-f4c64dc6, gap 2 — until now only cxo-claude.sh registered a session
# at all). When set, this is an ephemeral spawn: CTO_SESSION_ID is forced to
# the given id and the `cto-active` pointer below is intentionally NOT
# written, so an ephemeral tab can never clobber the CEO's primary CTO tab
# (ADR 2026-05-26, Decision 2). Every other arg passes through to `claude`
# unchanged via ARGS, same as cxo-claude.sh's own loop.
SESSION_OVERRIDE=""
ARGS=()
prev=""
for a in "$@"; do
  if [ "$prev" = "--session" ]; then
    SESSION_OVERRIDE="$a"; prev=""; continue
  fi
  case "$a" in
    --session) prev="--session" ;;
    *)         ARGS+=("$a") ;;
  esac
done

ROLE_PROMPT="$(cat "$ROOT/roles/cto.md")"

# Generate the MCP config with THIS machine's real absolute paths instead of
# reading the committed config/cto.mcp.json, which bakes in the Mac dev path
# (/Users/gob/Projects/Agents) — that breaks when this same launcher runs on
# a different box (e.g. Contabo, ROOT=/opt/mooniex-agents) via the MoonieX
# Console tmux bridge. Regenerated fresh per launch; cleaned up in the EXIT
# trap below. scripts/lib/cxo_mcp_config.py is shared with cxo-claude.sh so
# the per-role server set cannot drift between the two launchers.
MCP_CONFIG="$(mktemp "${TMPDIR:-/tmp}/cto-mcp-XXXXXX")"
mv "$MCP_CONFIG" "$MCP_CONFIG.json"
MCP_CONFIG="$MCP_CONFIG.json"
python3 "$ROOT/scripts/lib/cxo_mcp_config.py" --role cto --root "$ROOT" --out "$MCP_CONFIG"

# Tool whitelist, derived from the SAME generator that just emitted the server
# set — never hand-copied. The hardcoded list that used to live here drifted
# from the servers above (it named org + lungnote only, while the role also
# loaded supabase, so those tools paid the schema cost then prompted on every
# call). Deriving both from one source makes that desync impossible, and the
# org entries come from lib/org_tools_registry.py so a new org tool lands here
# automatically instead of becoming a 4th list to forget.
ALLOWED="$(python3 "$ROOT/scripts/lib/cxo_mcp_config.py" --role cto --root "$ROOT" --print-allowed)"

cd "$ROOT"
export CTO_SESSION=1
# Generate CTO ID if not inherited from spawn-cto.sh (e.g. when running
# cto-claude.sh standalone). When standalone INSIDE a tmux session — the
# console's launch path — adopt the id from the enclosing tmux session name
# so the lock basename matches the session the phone already shows. Two names
# for one session is what made the Aug-10 orphan invisible (lock
# cto-4020c182 vs tmux cto-session-mslldjt6). Only a name shaped cto-<id> is
# adopted; anything else falls back to a fresh uuid. Mirrors
# tools.session_name.id_from_tmux_session(_, "cto").
if [ -n "$SESSION_OVERRIDE" ]; then
  CTO_SESSION_ID="$SESSION_OVERRIDE"
elif [ -z "${CTO_SESSION_ID:-}" ]; then
  if [ -n "${TMUX:-}" ]; then
    _SESS="$(tmux display-message -p '#S' 2>/dev/null | tr -d '[:space:]')"
    case "$_SESS" in
      cto-*) CTO_SESSION_ID="${_SESS#cto-}" ;;
    esac
  fi
  if [ -z "${CTO_SESSION_ID:-}" ]; then
    CTO_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
  fi
fi
export CTO_SESSION_ID

# Full RFC4122-shaped UUID whose trailing 8 hex chars equal $CTO_SESSION_ID
# (rest random). Persisted so spawn-cto.sh's --resume <id> can look up the
# real Claude Code session UUID from the org's short id — the two id spaces
# are otherwise disconnected (LungNote note 85155c87-6654-4126-9f16-7f9be194ddb2).
# Only ids shaped like the standard uuid4().hex[:8] (8 lowercase hex chars)
# support the deterministic-suffix construction. A non-hex custom --id (or
# CTO_SESSION_ID inherited from something like send_to_cxo.py's ephemeral
# "req-xxxxxxxx" ids) falls back to a fully random UUID instead of crashing
# uuid.UUID(hex=...) — resume-by-short-id then degrades to spawn-cto.sh's
# existing picker-mode fallback, same as a pre-rollout session with no
# .uuid file.
if [[ "$CTO_SESSION_ID" =~ ^[0-9a-f]{8}$ ]]; then
  CTO_UUID="$(python3 -c "
import uuid, sys
suffix = sys.argv[1]
full = uuid.uuid4().hex[:-8] + suffix
print(uuid.UUID(hex=full))
" "$CTO_SESSION_ID")"
else
  CTO_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
fi

# Per-CTO lock so the claude-CLI path has the same collision defense
# that runners/cto_chat.py provides for the Python REPL. spawn-cto.sh's
# is_id_live() check relies on this file existing while a CTO chat is
# alive. CTO_CLAUDE_LOCKS_DIR is a test-only override (scripts/test_cxo_
# crosstalk.py) so a test can prove the registration behavior below
# without ever writing to the real state/locks/ (ADR 0021).
LOCKS_DIR="${CTO_CLAUDE_LOCKS_DIR:-$ROOT/state/locks}"
mkdir -p "$LOCKS_DIR"
UUID_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.uuid"
printf '%s\n' "$CTO_UUID" >"$UUID_FILE"

LOCKFILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.lock"
if [ -e "$LOCKFILE" ]; then
  existing_pid="$(tr -d '[:space:]' <"$LOCKFILE" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "CTO id $CTO_SESSION_ID already running as pid $existing_pid — refuse to start a second one." >&2
    exit 1
  fi
  rm -f "$LOCKFILE"
fi
echo "$$" >"$LOCKFILE"

# Find the iTerm window id whose session shares our TTY, then record it
# so tools/delegate.py can target this exact window when spawning DEV
# tabs. Matching by window id is immune to the session-name flicker
# that causes name-based lookups to misroute DEVs to the wrong CTO.
WINID_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.winid"
MY_TTY="$(tty 2>/dev/null || true)"

# Inside tmux, `tty` is the pane's own pty — not the terminal emulator's. Both
# consumers of MY_TTY need the REAL iTerm tty: the winid lookup below matches on
# `tty of s`, and scripts/tab-title.sh writes OSC escapes straight to the saved
# tty. Hand either one a pane pty and the escapes go back into tmux, which eats
# them: tab titles stop updating and delegate.py loses the window it routes DEV
# tabs to, both silently. `client_tty` is the attached client's tty, i.e. the
# iTerm tab. spawn-cto.sh attaches from iTerm in the same breath as it creates
# the session, so poll briefly for that client rather than giving up on the
# first read.
if [ -n "${TMUX:-}" ]; then
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    CLIENT_TTY="$(tmux display-message -p '#{client_tty}' 2>/dev/null | tr -d '[:space:]')"
    if [ -n "$CLIENT_TTY" ]; then
      MY_TTY="$CLIENT_TTY"
      break
    fi
    sleep 0.2
  done
fi

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
TTY_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.tty"
if [ -n "$MY_TTY" ]; then
  echo "$MY_TTY" >"$TTY_FILE"
fi

# .run is the launcher tmux exec'd us from (written by spawn-cto.sh); it has no
# reason to outlive the session it started.
RUN_FILE="$LOCKS_DIR/cto-$CTO_SESSION_ID.run"

# CXO_ROLE/CXO_SESSION: same env every cxo-claude.sh session exports, so
# tools/send_to_cxo.py's _resolve_sender_role() correctly labels a message
# from here "[CTO]" instead of falling back to "[CEO]" (task task-f4c64dc6,
# gap 2 — CXO_ROLE was never set inside a cto-claude.sh session before this).
export CXO_ROLE="cto"
export CXO_SESSION=1

# Active-session pointer: only written for a PRIMARY (non-ephemeral) launch.
# Mirrors cxo-claude.sh's own ACTIVE_FILE guard verbatim — an ephemeral spawn
# (--session set) must never overwrite this pointer, so the CEO's primary
# CTO tab stays the single target `send()` resolves to (ADR 2026-05-26,
# Decision 2).
ACTIVE_FILE="$LOCKS_DIR/cto-active"
if [ -z "$SESSION_OVERRIDE" ]; then
  echo "$CTO_SESSION_ID" >"$ACTIVE_FILE"
fi

# Register this session in c_level_sessions so send_to_cxo has a target to
# resolve (gap 2). Backgrounded + stdio-detached exactly like cxo-claude.sh's
# own call, for the same reason: a held stdout/stderr pipe would hang any
# programmatic caller capturing this script's output.
# Skipped under CTO_CLAUDE_TEST_MODE (scripts/test_cxo_crosstalk.py) so a
# test never writes to the real state/tasks.db (ADR 0021) — that DB write is
# not what this guard is about; it belongs to register_cxo.py's own coverage.
if [ "${CTO_CLAUDE_TEST_MODE:-0}" != "1" ]; then
  (cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
    python3 -m tools.register_cxo --role cto --session "$CTO_SESSION_ID" 2>/dev/null || true) >/dev/null 2>&1 </dev/null &
fi

# Test-only early exit: everything above (lock/uuid/winid/tty files, the
# active pointer, register_cxo) has already run by this point, so a test can
# assert on it without going anywhere near maintab, tab-title OSC writes,
# the title-keeper background loop, model resolution, or a real `claude`
# launch. Not reachable in a real launch (the env var is never set there).
if [ "${CTO_CLAUDE_TEST_MODE:-0}" = "1" ]; then
  rm -f "$MCP_CONFIG"
  echo "CTO_CLAUDE_TEST_MODE: stopping after registration (session=$CTO_SESSION_ID override=${SESSION_OVERRIDE:-<none>})"
  exit 0
fi

cleanup() {
  rm -f "$LOCKFILE" "$WINID_FILE" "$TTY_FILE" "$UUID_FILE" "$MCP_CONFIG" "$RUN_FILE"
  # Only clear the active pointer if it still points at us and we wrote it.
  if [ -z "$SESSION_OVERRIDE" ] && [ -e "$ACTIVE_FILE" ]; then
    current="$(tr -d '[:space:]' <"$ACTIVE_FILE" 2>/dev/null || true)"
    if [ "$current" = "$CTO_SESSION_ID" ]; then
      rm -f "$ACTIVE_FILE"
    fi
  fi
}
trap cleanup EXIT INT TERM

# Initial tab title + base prefix for scripts/tab-title.sh (IRON-RULES §32).
# The C-level agent rewrites the summary part after every finished job.
TITLE_BASE="CTO #$CTO_SESSION_ID"
TITLES_DIR="$ROOT/state/tab-titles"
mkdir -p "$TITLES_DIR"
printf '%s\n' "$TITLE_BASE" >"$TITLES_DIR/cto-$CTO_SESSION_ID.base"
printf '%s ⏳ เริ่ม session\n' "$TITLE_BASE" >"$TITLES_DIR/cto-$CTO_SESSION_ID.title"
# OSC 1 = tab strip only. NOT OSC 0, which also rewrites the window titlebar
# and would wipe the Main Tab (goal + progress + clock) — see tools/maintab.py.
printf '\033]1;%s ⏳ เริ่ม session\007' "$TITLE_BASE"

# Tab color needs a tab bar to paint on, and iTerm hides that bar by default
# when a window holds a single tab — exactly how C-level sessions spawn. The
# status colors then get written successfully and render nowhere (cost: one
# full debugging session, 2026-08-03). Re-assert the pref if it drifted back.
# It is a local iTerm preference, so it cannot travel in the repo; setting it
# through the API (not `defaults write`) applies live and survives iTerm's
# write-prefs-on-quit. No-op when the API is off or `iterm2` isn't installed.
python3 - <<'HIDETAB' >/dev/null 2>&1 || true
import iterm2
KEY = iterm2.PreferenceKey.HIDE_TAB_BAR_WHEN_ONLY_ONE_TAB
async def main(conn):
    if await iterm2.async_get_preference(conn, KEY):
        await iterm2.async_set_preference(conn, KEY, False)
iterm2.run_until_complete(main)
HIDETAB

# Seed the Main Tab (window titlebar) so it exists from the first second.
# Without this the titlebar stays blank until the agent happens to run
# scripts/tab-main.sh, and the refresh daemon never even sees this session:
# it discovers sessions by globbing state/tab-titles/*.main.json, so no state
# file meant no clock and no progress bar, forever (CEO hit exactly that on a
# fresh spawn, 2026-08-03). With no goal set yet the line renders as
# "🎯 CTO #<sid> · ⏱ 0m" — honest, and already ticking; the agent replaces the
# goal at /session-open. Also starts the shared refresh daemon.
(cd "$ROOT" && python3 -m tools.maintab set) >/dev/null 2>&1 || true

# Keep claude CLI from overwriting our tab title with its own (no-op on
# builds without this env). The keeper loop below re-asserts regardless.
export CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1

# ADR 0013 Phase 5 — org wiki root on a non-Mac box.
# config/wikis.yaml carries Mac absolute paths; Contabo keeps its checkout at
# /opt/agents-wikis. No-op on the Mac, where that path does not exist.
if [ -z "${WIKI_ROOT_ORG:-}" ] && [ -d /opt/agents-wikis ]; then
  export WIKI_ROOT_ORG=/opt/agents-wikis
fi

# MoonieX product wiki on Contabo (CEO 2026-08-09). Previously Mac-only, which
# made `mooniex:` fail on that box — and with it every UNPREFIXED path, since
# mooniex is the default namespace. Same rsync-not-clone shape as agents-wikis,
# so reads work and there is no git remote to push back to. No-op on the Mac.
if [ -z "${WIKI_ROOT_MOONIEX:-}" ] && [ -d /opt/mooniex-wikis ]; then
  export WIKI_ROOT_MOONIEX=/opt/mooniex-wikis
fi

# lungnote-mcp needs Node's native WebSocket (added in 22) for
# @supabase/realtime-js; Contabo's system `node` is 20, hence the dedicated
# /opt/node-v22 build mooniex-console already uses. Mac's system node is 26+,
# so this is a no-op there. See scripts/lib/cxo_mcp_config.py.
if [ -z "${LUNGNOTE_MCP_NODE:-}" ] && [ -x /opt/node-v22/bin/node ]; then
  export LUNGNOTE_MCP_NODE=/opt/node-v22/bin/node
fi

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

# Model + fallback + effort resolved from policies/agents.yaml — same
# accessor cxo-claude.sh uses (decisions/0009-model-routing-policy.md).
# Previously hardcoded here independently of the yaml; the two only stayed
# in sync by someone remembering to edit both files on every policy change.
IFS=' ' read -r CTO_MODEL CTO_FALLBACK CTO_EFFORT <<<"$(source "$ROOT/.venv/bin/activate" 2>/dev/null && python3 -c "
from lib.config import role as get_role
r = get_role('cto')
print(r.get('model') or 'claude-sonnet-5', r.get('fallback_model') or 'claude-fable-5', r.get('effort') or 'xhigh')
")"

# Flag-gated GLM offload (CXO_MODEL_PROVIDER, set by spawn-cto.sh --glm).
# Default OFF -> Claude path unchanged. When set, lib.config
# cxo_provider_overrides injects the provider env + swaps the model; the GLM
# endpoint rejects the Claude-only fallback id and --effort, so both are
# dropped. Every request then hits the GLM provider -> Claude weekly limit untouched.
# Provider: "zai" (Z.ai direct).
PROVIDER_EXPORTS="$(source "$ROOT/.venv/bin/activate" 2>/dev/null; python3 -c '
import shlex
from lib.config import cxo_provider_overrides
ov = cxo_provider_overrides("cto")
if ov:
    print("GLM_ACTIVE=1")
    print("GLM_MODEL=" + shlex.quote(ov["model"]))
    for k, v in ov["env"].items():
        print("export " + k + "=" + shlex.quote(v))
' 2>/dev/null || true)"
eval "${PROVIDER_EXPORTS:-}" 2>/dev/null || true

if [ "${GLM_ACTIVE:-0}" = "1" ]; then
  MODEL_ARGS=(--model "$GLM_MODEL")
  echo "CTO launching on GLM provider (${CXO_MODEL_PROVIDER:-zai}) — Claude weekly limit untouched." >&2
else
  MODEL_ARGS=(--model "$CTO_MODEL" --fallback-model "$CTO_FALLBACK" --effort "$CTO_EFFORT")
fi

# Without --strict-mcp-config the session ALSO loads Agents/.mcp.json,
# ~/.claude.json and every enabled plugin's servers — ~13 servers and
# ~1.5 GB of phys_footprint on the 8 GB M1, for a role whose ALLOWED list
# only covers org + lungnote. Worse, enabledMcpjsonServers is listed in both
# ~/.claude.json and .claude/settings.local.json, so the overlapping names
# spawn twice. Strict mode makes MCP_CONFIG the only source.
# Set CXO_STRICT_MCP=0 to fall back to the old inherit-everything behaviour.
STRICT_ARGS=()
if [ "${CXO_STRICT_MCP:-1}" = "1" ]; then
  STRICT_ARGS=(--strict-mcp-config)
fi

# --session-id + --resume/--continue is only legal combined with
# --fork-session (claude CLI refuses otherwise) — ARGS carries -r/-c
# whenever spawn-cto.sh translated --resume/--last. Detect and add it.
# ARGS (not "$@") because --session was already stripped out above.
FORK_ARGS=()
for a in ${ARGS[@]+"${ARGS[@]}"}; do
  case "$a" in
    -r|--resume|-c|--continue) FORK_ARGS=(--fork-session) ;;
  esac
done

# An "update available" prompt is a startup-level interrupt, not a tool
# permission check, so neither --permission-mode nor --allowed-tools reaches
# it -- it can block an unattended session on a keypress nobody is there to
# press (IRON-RULES §45). Verified 2026-08-14 by grepping the installed
# binary's own strings for the var name rather than assuming it.
export DISABLE_AUTOUPDATER=1

# `exec` would replace the shell and skip the EXIT trap, leaving a
# stale lock. Run claude as a child instead and propagate its exit code.
claude \
  -n "CTO #$CTO_SESSION_ID" \
  "${MODEL_ARGS[@]}" \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  ${STRICT_ARGS[@]+"${STRICT_ARGS[@]}"} \
  --allowed-tools $ALLOWED \
  --session-id "$CTO_UUID" \
  ${FORK_ARGS[@]+"${FORK_ARGS[@]}"} \
  ${ARGS[@]+"${ARGS[@]}"}
exit $?

#!/usr/bin/env bash
# Launch Claude Code CLI with any C-level role (cto/cmo/cgo/cfo/coo) + org MCP server.
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
#   --initial-prompt <text>   Passed to `claude` as its final positional
#                             argv -- auto-submitted the instant the process
#                             starts (task-093a3939), same mechanism
#                             runners/worker_init.py's kickoff uses. Never typed.
#   --tab-title <title>       Override the default tab title
#                             ("$DISPLAY #$CXO_SESSION_ID").
#
# Check-only:
#   --dry-run                 Validate the role (role doc, `c_level` in
#                             policies/agents.yaml, model/effort) and build its
#                             MCP set + tool allowlist, print them, and exit 0
#                             -- before any lock, DB row, tmux or claude. For
#                             proving a new role is wired without starting a
#                             session (COO, 2026-09-27).
#
# --role project_head --lane <cto|cmo|cgo|cfo|coo> --project <Name> (org
# restructure P2, docs/design/org-restructure-p2.md): a Project Head. Refused
# unless ORG_PH_ROLES=1 and roles/project_head.md exists. Normally started by
# scripts/spawn-ph.sh, which also sets ORG_PH_OWNER (the spawning C-level).
#
# --role coo is SomPong (CEO 2026-10-01): ONE session, Contabo only, started by
# scripts/sompong-supervise.sh in tmux `sompong` (never by hand, never by
# spawn-cxo.sh). It differs from the other C-levels in six ways, all in the
# "coo" blocks below: refused off Contabo; cwd = the SomPong repo; its channel
# MCP server `sompong` is loaded as a development channel; the org hooks and
# skills are re-attached by absolute path (cwd is not Agents-Core); the bookkeeping
# runs as the launching user but `claude` itself drops to the unprivileged SomPong
# unix user, because the inbox keys live where root can read and that user cannot
# (docs/design/sompong-coo-session.md, acceptance probe 5).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Org restructure P2: a Project Head never starts a session (plan §3.2), and
# the launcher is where every start passes. Its session carries
# CXO_ROLE=project_head, so a launch from inside one is refused here, before
# anything else. A guard for an agent that follows the rules, not a sandbox: a
# shell that clears the variable gets past it.
if [ "${CXO_ROLE:-}" = "project_head" ]; then
  echo "a Project Head cannot start a session (org restructure P2, plan §3.2); ask its C-level" >&2
  exit 2
fi
# Host flags (lib/org_flags.py): on when /etc/org-flags/<NAME> exists or the env
# says 1. A session started from tmux, the relay or node_dispatch takes the tmux
# server's environment, so the file is what reaches every launch.
ORG_FLAGS_DIR=/etc/org-flags
org_flag() { [ "${!1:-}" = "1" ] || [ -f "$ORG_FLAGS_DIR/$1" ]; }

ROLE=""
SESSION_OVERRIDE=""
INITIAL_PROMPT=""
TAB_TITLE_OVERRIDE=""
PH_LANE="${ORG_PH_LANE:-}"
PH_PROJECT="${ORG_PH_PROJECT:-}"
DRY_RUN=0
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
  if [ "$prev" = "--lane" ]; then
    PH_LANE="$a"; prev=""; continue
  fi
  if [ "$prev" = "--project" ]; then
    PH_PROJECT="$a"; prev=""; continue
  fi
  case "$a" in
    --role)           prev="--role" ;;
    --session)        prev="--session" ;;
    --initial-prompt) prev="--initial-prompt" ;;
    --tab-title)      prev="--tab-title" ;;
    --lane)           prev="--lane" ;;
    --project)        prev="--project" ;;
    --dry-run)        DRY_RUN=1 ;;
    *)                ARGS+=("$a") ;;
  esac
done

if [ -z "$ROLE" ]; then
  echo "usage: cxo-claude.sh --role <cto|cmo|cgo|cfo|coo> [--dry-run] [claude args...]" >&2
  exit 2
fi

# Resolve explicit resume targets before any session or tab side effects.
RESUME_UUID=""
for ((i=0; i<${#ARGS[@]}; i++)); do
  case "${ARGS[i]}" in
    -r|--resume)
      if ((i+1 < ${#ARGS[@]})) && [[ "${ARGS[i+1]}" != -* ]]; then
        ARGS[i+1]="$(bash "$ROOT/scripts/resolve-resume-id.sh" "$ROLE" "${ARGS[i+1]}")" || exit 2
        RESUME_UUID="${ARGS[i+1]}"
        i=$((i+1))
      fi
      ;;
  esac
done

# --- SomPong (the COO): ONE session, on Contabo only (CEO 2026-10-01) ---------
# docs/design/sompong-coo-session.md "Singleton + spawn". Checked before anything
# else, even --dry-run: no lock, no DB row, no venv. The host comes from
# lib.config (ORG_HOST, node.yaml, agents_root) through coo_host.py, never from
# `hostname`/`uname`; an unresolved host counts as "not Contabo" (fails closed).
SOMPONG_DIR="${SOMPONG_DIR:-/opt/MoonieXHQ/Projects/MoonieX/SomPong}"
if [ "$ROLE" = "coo" ]; then
  COO_PY="$ROOT/.venv/bin/python"; [ -x "$COO_PY" ] || COO_PY=python3
  COO_HOST="$("$COO_PY" "$ROOT/scripts/lib/coo_host.py" host)" || COO_HOST=""
  if [ "$COO_HOST" != "contabo" ]; then
    echo "SomPong (COO) runs on Contabo only — use /spawn-coo" >&2
    exit 1
  fi
  if [ -n "$SESSION_OVERRIDE" ]; then
    echo "SomPong (COO) is one always-on session, never spawned per request — use /spawn-coo" >&2
    exit 1
  fi
fi

# --- Project Head (org restructure P2, plan §3.2) ------------------------------
# Off unless the host flag ORG_PH_ROLES is on. Lane and project are checked by
# lib/roles.py (the same rules spawn-ph.sh applies). The session must have been
# started by scripts/spawn-ph.sh: its owner record (state/locks/project_head-<id>
# .spawned_by, written by root or this user before tmux started) names the lane.
# The role doc is the COO's to write (plan §13); until it exists a Project Head
# does not start.
IS_PH=0
if [ "$ROLE" = "project_head" ]; then
  IS_PH=1
  if ! org_flag ORG_PH_ROLES; then
    echo "project_head is off on this host (host flag ORG_PH_ROLES turns it on; org restructure P2)" >&2
    exit 2
  fi
  PH_LANE="$(printf '%s' "$PH_LANE" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"
  PH_PY="$ROOT/.venv/bin/python"; [ -x "$PH_PY" ] || PH_PY=python3
  if ! PH_PROBLEM="$(cd "$ROOT" && PH_LANE="$PH_LANE" PH_PROJECT="$PH_PROJECT" \
        PH_SID="${CXO_SESSION_ID:-}" PH_LOCKS="$ROOT/state/locks" "$PH_PY" -c '
import os, re, sys
from lib.roles import ph_lane_refusal, ph_project_refusal
lane, sid = os.environ["PH_LANE"], os.environ["PH_SID"]
why = ph_lane_refusal(lane) or ph_project_refusal(os.environ["PH_PROJECT"])
if not why and not re.fullmatch(r"[0-9a-f]{8}", sid):
    why = "no CXO_SESSION_ID from scripts/spawn-ph.sh; start a Project Head with it"
if not why:
    rec = os.path.join(os.environ["PH_LOCKS"], f"project_head-{sid}.spawned_by")
    try:
        st = os.stat(rec)
        kind, owner_lane, owner = open(rec).read().strip().split(":", 2)
    except (OSError, ValueError):
        kind = owner_lane = owner = ""
        st = None
    if st is None or st.st_uid not in (0, os.geteuid()) or kind != "cxo" or owner_lane != lane or not owner:
        why = (f"no owner record for project_head-{sid} naming lane {lane}; "
               "start a Project Head with scripts/spawn-ph.sh")
print(why or "")
sys.exit(1 if why else 0)
')"; then
    echo "project_head: ${PH_PROBLEM:-cannot check --lane/--project}" >&2
    exit 2
  fi
  if [ ! -f "$ROOT/roles/project_head.md" ]; then
    echo "project_head: roles/project_head.md does not exist yet — the COO writes it (plan §13)" >&2
    exit 2
  fi
fi

ROLE_DOC="$ROOT/roles/$ROLE.md"
if [ ! -f "$ROLE_DOC" ]; then
  echo "role doc not found: $ROLE_DOC" >&2
  exit 2
fi

# Resolve display name + model + effort from policies/agents.yaml so the
# tab title/log lines and the spawned model match the canonical config —
# per-role, not hardcoded (decisions/0009-model-routing-policy.md).
IFS=$'\t' read -r DISPLAY MODEL EFFORT CLEVEL_NAME <<<"$(cd "$ROOT" && source .venv/bin/activate && PH_LANE="$PH_LANE" ROLE_ARG="$ROLE" python3 -c "
from lib.config import display_for, is_c_level, persona_for, clevel_name, role as get_role
from lib.roles import is_project_head, ph_display
import os, sys
role = os.environ['ROLE_ARG']
name = ''
if is_project_head(role):
    display = ph_display(os.environ.get('PH_LANE', ''))
elif not is_c_level(role):
    print(f'role {role} is not a C-level role', file=sys.stderr)
    sys.exit(2)
else:
    display = display_for(role)
    name = clevel_name(role, persona_for(role))
r = get_role(role)
model = r.get('model') or 'claude-opus-5-5[1m]'
effort = r.get('effort') or 'medium'
print(display, model, effort, name, sep='\t')   # C-level name last: empty for a PH
")"
[ -n "$DISPLAY" ] || exit 2

ROLE_PROMPT="$(cat "$ROLE_DOC")"

# Per-role MCP set, generated fresh per launch (removed in cleanup below).
# Replaces the committed config/cto.mcp.json, which hardcoded the Mac dev
# path and so broke on Contabo (ROOT=/opt/MoonieXHQ/Agents/Core) — the same bug
# cto-claude.sh already worked around. Shared generator keeps the two
# launchers from drifting.
# lungnote-mcp needs Node's native WebSocket (added in 22) for
# @supabase/realtime-js; Contabo's system `node` is 20, hence the dedicated
# /opt/node-v22 build mooniex-console already uses. Mac's system node is 26+,
# so this is a no-op there. See scripts/lib/cxo_mcp_config.py.
if [ -z "${LUNGNOTE_MCP_NODE:-}" ] && [ -x /opt/node-v22/bin/node ]; then
  export LUNGNOTE_MCP_NODE=/opt/node-v22/bin/node
fi
# (this block used to sit ~300 lines lower, AFTER the MCP config was generated — so every Contabo
# session got `node` (v20, no WebSocket) for lungnote and the server died at boot: CONNECTION_CLOSED
# on 2026-09-22/24 sessions. Exports must precede cxo_mcp_config.py. Fixed 2026-09-24.)

MCP_CONFIG="$(mktemp "${TMPDIR:-/tmp}/cxo-mcp-XXXXXX")"
mv "$MCP_CONFIG" "$MCP_CONFIG.json"
MCP_CONFIG="$MCP_CONFIG.json"
python3 "$ROOT/scripts/lib/cxo_mcp_config.py" --role "$ROLE" --root "$ROOT" --out "$MCP_CONFIG"

# Tool whitelist for THIS role, derived from the same generator that emitted
# the server set above. C-levels share org powers (agents.yaml) but not their
# server sets — CMO has meigen/meta-ads where CFO has supabase — so one
# hardcoded string could never be right for every role, and the one that used to
# live here covered org + lungnote only. See cto-claude.sh for the full note.
ALLOWED="$(python3 "$ROOT/scripts/lib/cxo_mcp_config.py" --role "$ROLE" --root "$ROOT" --print-allowed)"

# A Project Head does short one-off browser jobs itself (a login check, one view
# count, one post click; CEO via SomPong 2026-10-14), so it gets the same Chrome
# surface a browser_operator worker has (lib/roles.py CHROME_TOOLS) and --chrome,
# which is what makes those tools resolve under --strict-mcp-config.
CHROME_ARGS=()
if [ "$IS_PH" = "1" ]; then
  ALLOWED="$ALLOWED $(cd "$ROOT" && "$PH_PY" -c 'from lib.roles import CHROME_TOOLS; print(" ".join(CHROME_TOOLS))')"
  CHROME_ARGS=(--chrome)
fi

# --- SomPong (coo): what differs from every other C-level ----------------------
# COO_ARGS rides into the one claude invocation at the bottom; COO_ENV is the whole
# environment the unprivileged session gets (env -i + this list), so nothing the
# launching shell holds -- Infisical identity, keys -- reaches it.
COO_ARGS=()
COO_SETTINGS=""
COO_UNIX_USER=""
COO_ENV=()
COO_CLAUDE_BIN=""
if [ "$ROLE" = "coo" ]; then
  COO_UNIX_USER="${SOMPONG_USER:-sompong}"
  SOMPONG_MCP="$SOMPONG_DIR/.mcp.json"
  COO_PROBLEM=""
  if [ ! -d "$SOMPONG_DIR" ]; then
    COO_PROBLEM="SomPong repo not found: $SOMPONG_DIR"
  elif [ ! -f "$SOMPONG_MCP" ] || ! grep -q '"sompong"' "$SOMPONG_MCP"; then
    COO_PROBLEM="$SOMPONG_MCP does not declare MCP server 'sompong' (the SomPong channel server is not deployed)"
  elif ! COO_UID="$(id -u "$COO_UNIX_USER" 2>/dev/null)"; then
    COO_PROBLEM="unix user '$COO_UNIX_USER' does not exist (SomPong repo: sudo bash ops/install-contabo.sh)"
  elif [ "$COO_UID" = "0" ] && [ "${SOMPONG_ALLOW_ROOT:-0}" != "1" ]; then
    COO_PROBLEM="SomPong must not run as root (it could read the inbox keys); SOMPONG_USER=$COO_UNIX_USER is uid 0"
  fi
  if [ -z "$COO_PROBLEM" ]; then
    COO_HOME="$(getent passwd "$COO_UNIX_USER" | cut -d: -f6)"
    [ -n "$COO_HOME" ] || COO_HOME="/home/$COO_UNIX_USER"
    COO_CLAUDE_BIN="${SOMPONG_CLAUDE:-$COO_HOME/.local/bin/claude}"
    [ -x "$COO_CLAUDE_BIN" ] || COO_PROBLEM="claude is not installed for $COO_UNIX_USER ($COO_CLAUDE_BIN)"
    # Root work goes through a Run Inbox card (org tools ask_run / ask_run_wait), which read the hub
    # token from the session user's HOME. Missing = warn once and start anyway: only that path fails.
    if [ -z "$COO_PROBLEM" ] && [ ! -f "$COO_HOME/.config/mooniex/run-inbox.token" ]; then
      echo "SomPong (COO) warning: $COO_HOME/.config/mooniex/run-inbox.token is missing - ask_run (root work through the Run Inbox) will fail until it is installed (mode 0600, owned by $COO_UNIX_USER)" >&2
    fi
  fi
  if [ -z "$COO_PROBLEM" ]; then
    COO_SETTINGS="$MCP_CONFIG.hooks.json"
    "$COO_PY" "$ROOT/scripts/lib/cxo_hooks_settings.py" --root "$ROOT" --out "$COO_SETTINGS" 2>/dev/null \
      || COO_PROBLEM="cannot build the org hooks settings from $ROOT/.claude/settings.json"
    # The unprivileged session must be able to read what the launcher generated.
    chmod 0644 "$MCP_CONFIG" "$COO_SETTINGS" 2>/dev/null || true
  fi
  if [ -n "$COO_PROBLEM" ]; then
    rm -f "$MCP_CONFIG" "$COO_SETTINGS"
    echo "SomPong (COO) cannot start: $COO_PROBLEM" >&2
    exit 1
  fi
  # Channel flag: a custom server is not on the channel allowlist, so it needs the
  # development flag (the plain channels flag is rejected for server: entries,
  # claude 2.1.285). SomPong's own .mcp.json is a SECOND --mcp-config so the
  # session stays strict (org + lungnote + sompong, nothing inherited).
  COO_ARGS=(
    --mcp-config "$SOMPONG_MCP"
    --dangerously-load-development-channels server:sompong
    --add-dir "$ROOT"
    --settings "$COO_SETTINGS"
  )
  ALLOWED="$ALLOWED mcp__sompong__reply mcp__sompong__skip mcp__sompong__send mcp__sompong__ask_ceo mcp__sompong__history mcp__sompong__media mcp__sompong__drive_share"
  : "${WIKI_ROOT_ORG:=/opt/MoonieXHQ/Agents/Rules}"
  : "${WIKI_ROOT_MOONIEX:=/opt/MoonieXHQ/Agents/Wikis}"
  COO_ENV=(
    "HOME=$COO_HOME" "USER=$COO_UNIX_USER" "LOGNAME=$COO_UNIX_USER"
    "PATH=$COO_HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
    "TERM=${TERM:-tmux-256color}" "LANG=${LANG:-C.UTF-8}"
    "ORG_HOST=contabo" "SOMPONG_COO_SESSION=1"
    "WIKI_ROOT_ORG=$WIKI_ROOT_ORG" "WIKI_ROOT_MOONIEX=$WIKI_ROOT_MOONIEX"
    "DISABLE_AUTOUPDATER=1" "CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1"
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW=${CLAUDE_CODE_AUTO_COMPACT_WINDOW:-300000}"
    # The inbox runs from a root-owned release with its state under /var/lib (CEO 2026-10-02,
    # scripts/sompong-inbox-deploy.sh); the channel server and the family-gate hook find it here.
    "SOMPONG_INBOX_SOCKET=${SOMPONG_INBOX_SOCKET:-/var/lib/sompong-inbox/inbox.sock}"
    # The org MCP reads the DSN of the limited role org_coo from this file, written by
    # mooniex-sompong.service at start (scripts/coo-org-db-cred.sh, scripts/hub/with-org-db-env.sh).
    "MOONIEX_ORG_DB_URL_FILE=${MOONIEX_ORG_DB_URL_FILE:-/run/sompong-coo/org-db.url}"
  )
  [ -z "${LUNGNOTE_MCP_NODE:-}" ] || COO_ENV+=("LUNGNOTE_MCP_NODE=$LUNGNOTE_MCP_NODE")
fi

# --dry-run stops here: everything above only reads and validates (the temp MCP
# config is its one file, removed now); everything below writes locks, rows in
# c_level_sessions, tab state, and starts claude.
if [ "$DRY_RUN" = "1" ]; then
  rm -f "$MCP_CONFIG" "$COO_SETTINGS"
  echo "dry-run: role=$ROLE display=$DISPLAY model=$MODEL effort=$EFFORT"
  echo "dry-run: allowed-tools=$ALLOWED"
  if [ "$IS_PH" = "1" ]; then
    echo "dry-run: project_head lane=$PH_LANE project=$PH_PROJECT owner=${ORG_PH_OWNER:-} extra-args=${CHROME_ARGS[*]}"
  fi
  if [ "$ROLE" = "coo" ]; then
    echo "dry-run: coo host=$COO_HOST cwd=$SOMPONG_DIR user=$COO_UNIX_USER claude=$COO_CLAUDE_BIN"
    echo "dry-run: coo extra-args=${COO_ARGS[*]}"
    echo "dry-run: coo env=$(printf '%s\n' "${COO_ENV[@]}" | cut -d= -f1 | tr '\n' ' ')"
  fi
  echo "dry-run: stopped before lock / session registration / claude"
  exit 0
fi

cd "$ROOT"

# CXO_* are the canonical env keys for any C-level session.
# CTO_SESSION_ID is also exported when role=cto so all existing tooling
# (delegate.py owner_cto, send_to_cto.py routing) keeps working unchanged.
export CXO_ROLE="$ROLE"
export CXO_SESSION=1
if [ "$IS_PH" = "1" ]; then
  # A Project Head is never a CTO session: an inherited CTO_SESSION_ID would
  # make lib/db.resolve_session_owner stamp its tasks as the CTO's.
  unset CTO_SESSION CTO_SESSION_ID
  export ORG_PH_LANE="$PH_LANE" ORG_PH_PROJECT="$PH_PROJECT" ORG_PH_OWNER="${ORG_PH_OWNER:-}"
fi

# Session ID: use override from --session flag (ephemeral spawn), else auto-pick.
# When SESSION_OVERRIDE is set the <role>-active pointer is intentionally skipped
# (ADR 2026-05-26, Decision 2) so the CEO's primary tab is never clobbered.
if [ -n "$SESSION_OVERRIDE" ]; then
  CXO_SESSION_ID="$SESSION_OVERRIDE"
elif [ -n "$RESUME_UUID" ]; then
  CXO_SESSION_ID="$(printf '%s' "${RESUME_UUID: -8}" | tr '[:upper:]' '[:lower:]')"
else
  if [ -z "${CXO_SESSION_ID:-}" ]; then
    # Standalone launch INSIDE a tmux session (the console's path): adopt the
    # id from the enclosing tmux session name so the lock basename matches the
    # session the phone shows. Two names for one session is what made the
    # Aug-10 orphan invisible (lock cto-4020c182 vs tmux cto-session-mslldjt6).
    # Only <role>-<8 lowercase hex> names are adopted; anything else prints one
    # stderr line and falls back to a fresh 8-hex uuid. Only a <role>-<other>
    # name (cto-fresh) is then renamed to <role>-<id>. Any other name belongs to
    # whoever made it: mooniex-sompong.service watches tmux "sompong" and answers
    # its startup prompts by that name, so renaming it left the COO stuck on the
    # dev-channels prompt (26 Oct 2026).
    _RENAME=""
    if [ -n "${TMUX:-}" ]; then
      _SESS="$(tmux display-message -p '#S' 2>/dev/null | tr -d '[:space:]')"
      case "$_SESS" in
        "$ROLE"-*)
          _CANDIDATE="${_SESS#"$ROLE"-}"
          if [[ "$_CANDIDATE" =~ ^[0-9a-f]{8}$ ]]; then
            CXO_SESSION_ID="$_CANDIDATE"
          else
            echo "cxo-claude: tmux session name '$_SESS' was not adopted as CXO_SESSION_ID (suffix '$_CANDIDATE' is not 8 lowercase hex); minting a fresh 8-hex id" >&2
            _RENAME=1
          fi
          ;;
        ?*)
          echo "cxo-claude: tmux session name '$_SESS' was not adopted as CXO_SESSION_ID (expected '$ROLE-<8 lowercase hex>'); minting a fresh 8-hex id and keeping the name" >&2
          ;;
      esac
    fi
    if [ -z "${CXO_SESSION_ID:-}" ]; then
      CXO_SESSION_ID="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
      if [ -n "$_RENAME" ]; then
        _NEW_SESS="$ROLE-$CXO_SESSION_ID"
        if tmux has-session -t "=$_NEW_SESS" 2>/dev/null; then
          echo "cxo-claude: warning: tmux session '$_NEW_SESS' already exists; keeping '$_SESS'" >&2
        elif tmux rename-session -t "$_SESS" -- "$_NEW_SESS"; then
          echo "cxo-claude: renamed tmux session '$_SESS' -> '$_NEW_SESS'" >&2
        else
          echo "cxo-claude: warning: could not rename tmux session '$_SESS' -> '$_NEW_SESS'; continuing" >&2
        fi
      fi
    fi
  fi
fi
export CXO_SESSION_ID

if [ "$ROLE" = "cto" ]; then
  export CTO_SESSION=1
  export CTO_SESSION_ID="$CXO_SESSION_ID"
fi

# Full RFC4122-shaped UUID whose trailing 8 hex chars equal $CXO_SESSION_ID
# (rest random). Persisted so spawn-cxo.sh's --resume <id> can look up the
# real Claude Code session UUID from the org's short id — the two id spaces
# are otherwise disconnected (LungNote note 85155c87-6654-4126-9f16-7f9be194ddb2).
# Written unconditionally (ephemeral --session spawns included) — separate
# bookkeeping from the ACTIVE_FILE pointer below, which exists for
# CEO-tab routing, not identity.
# Resume uses --fork-session: mint a new destination UUID with the same short id.
# The lock file records the new fork UUID, never the resume source UUID.
if [[ "$CXO_SESSION_ID" =~ ^[0-9a-f]{8}$ ]]; then
  CXO_UUID="$(python3 -c "
import uuid, sys
suffix = sys.argv[1]
full = uuid.uuid4().hex[:-8] + suffix
print(uuid.UUID(hex=full))
" "$CXO_SESSION_ID")"
else
  CXO_UUID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
fi
mkdir -p "$ROOT/state/locks"
UUID_FILE="$ROOT/state/locks/$ROLE-$CXO_SESSION_ID.uuid"
printf '%s\n' "$CXO_UUID" >"$UUID_FILE"

LOCKS_DIR="$ROOT/state/locks"
mkdir -p "$LOCKS_DIR"

# SomPong is ONE session: any other live coo launcher (a different id, so the
# per-id lock below cannot see it) means this start must stop. Liveness is the
# pid in the lock AND that the pid is still a cxo-claude.sh -- a recycled pid is
# not a SomPong. The supervisor's flock and tmux's one-`sompong`-name already
# make a second launch hard; this is the check that names the cause.
if [ "$ROLE" = "coo" ]; then
  for other in "$LOCKS_DIR"/coo-*.lock; do
    [ -e "$other" ] || continue
    opid="$(tr -d '[:space:]' <"$other" 2>/dev/null || true)"
    if [ -n "$opid" ] && [ "$opid" != "$$" ] && kill -0 "$opid" 2>/dev/null \
       && tr '\0' ' ' <"/proc/$opid/cmdline" 2>/dev/null | grep -q 'cxo-claude'; then
      rm -f "$MCP_CONFIG" "$COO_SETTINGS"
      echo "SomPong (COO) is already running (launcher pid $opid, $(basename "$other" .lock)) — one session only; use /spawn-coo to check on it" >&2
      exit 1
    fi
  done
fi
# One live session per C-level role, on Contabo only (org restructure P2, plan
# §3.1) when ORG_SINGLE_CLEVEL=1; tools/clevel_gate.py decides. The flock makes
# check-then-lock one step against a second launcher starting in the same second;
# it is released as soon as this session's own lock is written below.
SINGLE_FD_OPEN=0
if org_flag ORG_SINGLE_CLEVEL && [ "$IS_PH" = "0" ]; then
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCKS_DIR/.single-$ROLE.flock"
    SINGLE_FD_OPEN=1
    if ! flock -w 20 9; then
      rm -f "$MCP_CONFIG" "$COO_SETTINGS" "$UUID_FILE"
      echo "another $DISPLAY launcher holds the start lock for over 20 s — try again" >&2
      exit 1
    fi
  fi
  GATE_PY="$ROOT/.venv/bin/python"; [ -x "$GATE_PY" ] || GATE_PY=python3
  if ! (cd "$ROOT" && "$GATE_PY" -m tools.clevel_gate check --role "$ROLE" \
          --session "$CXO_SESSION_ID" --locks-dir "$LOCKS_DIR"); then
    rm -f "$MCP_CONFIG" "$COO_SETTINGS" "$UUID_FILE"
    exit 1
  fi
fi
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
if [ "$SINGLE_FD_OPEN" = "1" ]; then
  flock -u 9 2>/dev/null || true
  exec 9>&-
fi

# Capture iTerm window id so tools/delegate.py + send_to_cxo can target
# this exact window. Matching by id is immune to title-flicker mishaps.
WINID_FILE="$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.winid"
MY_TTY="$(tty 2>/dev/null || true)"

# Under tmux, `tty` is the pane's own pty, not the terminal emulator's. The
# winid lookup below matches on `tty of s`, and tab-title.sh writes OSC escapes
# straight to the saved tty — hand either one a pane pty and the escapes go
# back into tmux, which swallows them: tab titles freeze and delegate.py loses
# the window it routes DEV tabs to, both without an error anywhere.
# `client_tty` is the attached client, i.e. the iTerm tab; spawn-cxo.sh
# attaches from iTerm as the session is created, so poll briefly rather than
# giving up on the first read.
# terminal_window=false (config/hosts.yaml, CEO 2026-10-15): spawn-cxo.sh started this
# session detached, so no client will attach and there is no iTerm window to
# find. Skip the client_tty wait and the iTerm lookup (osascript would launch
# iTerm on the Mac just to be told "no such tty") and keep the pane's own tty,
# the way Contabo already runs. Anything but a clear 0 keeps the old path.
_TW_PY="$ROOT/.venv/bin/python"; [ -x "$_TW_PY" ] || _TW_PY=python3
TERMINAL_WINDOW="$("$_TW_PY" "$ROOT/scripts/lib/coo_host.py" terminal-window 2>/dev/null || echo 1)"
[ "$TERMINAL_WINDOW" = "0" ] || TERMINAL_WINDOW=1

if [ "$TERMINAL_WINDOW" = "1" ] && [ -n "${TMUX:-}" ]; then
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    CLIENT_TTY="$(tmux display-message -p '#{client_tty}' 2>/dev/null | tr -d '[:space:]')"
    if [ -n "$CLIENT_TTY" ]; then
      MY_TTY="$CLIENT_TTY"
      break
    fi
    sleep 0.2
  done
fi

if [ "$TERMINAL_WINDOW" = "1" ] && [ -n "$MY_TTY" ]; then
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
if [ -z "$SESSION_OVERRIDE" ] && [ "$IS_PH" = "0" ]; then
  echo "$CXO_SESSION_ID" >"$ACTIVE_FILE"
fi

# Machine prefix for the Claude session display name (CEO 2026-08-30) —
# same block as cto-claude.sh: the mobile app lists Remote Control sessions
# from every box in one flat list, so the name must carry the machine.
# Session name only; TAB_TITLE (iTerm tab strip) stays unprefixed.
#
# Computed here (moved up from its original spot further below) so HOST_KEY
# is ready in time for the reconcile + register_cxo calls right after it —
# both need to know which machine this is before they touch c_level_sessions.
case "$(uname -s)" in
  Darwin) MACHINE_LABEL="MAC" ;;
  Linux)  if [ -d /opt/MoonieXHQ/Agents/Core ]; then MACHINE_LABEL="CONTABO"
          else MACHINE_LABEL="$(hostname -s 2>/dev/null | tr '[:lower:]' '[:upper:]')"; fi ;;
  MINGW*|MSYS*|CYGWIN*) MACHINE_LABEL="WINDOWS" ;;
  *) MACHINE_LABEL="$(uname -s | tr '[:lower:]' '[:upper:]')" ;;
esac

# config/hosts.yaml key for THIS machine. The org's one resolver answers first:
# lib.config.self_host() (org-mesh.md C1: ORG_HOST, then node.yaml, then
# agents_root), read through scripts/lib/coo_host.py. session_reconcile and
# runners/worker_init.py resolve their host the same way, so the row registered
# below names the same machine as the rows the reconcile checks. The label case
# is the fallback for a machine self_host() cannot resolve (coo_host.py exits 3)
# or where no Python can run it.
case "$MACHINE_LABEL" in
  MAC)     HOST_KEY="mac" ;;
  CONTABO) HOST_KEY="contabo" ;;
  WINDOWS) HOST_KEY="winbox" ;;
  *)       HOST_KEY="$(printf '%s' "$MACHINE_LABEL" | tr '[:upper:]' '[:lower:]')" ;;
esac
HOST_PY="$ROOT/.venv/bin/python"; [ -x "$HOST_PY" ] || HOST_PY=python3
if SELF_HOST="$("$HOST_PY" "$ROOT/scripts/lib/coo_host.py" host 2>/dev/null)" && [ -n "$SELF_HOST" ]; then
  HOST_KEY="$SELF_HOST"
fi
# The session name starts with this host's emoji (CEO 2026-10-14, lib/session_names.py
# HOST_EMOJI). Only from self_host() above, never from MACHINE_LABEL's guess: an
# unresolved host gets no emoji.
HOST_EMOJI=""
if [ -n "${SELF_HOST:-}" ]; then
  HOST_EMOJI="$("$HOST_PY" "$ROOT/lib/session_names.py" prefix "$SELF_HOST" 2>/dev/null)" || HOST_EMOJI=""
fi

# Reconcile c_level_sessions BEFORE registering this new row (task-9ff9263f):
# marks any 'open' row on this host whose tmux is actually dead as
# 'abandoned', so stale rows don't pile up forever. Backgrounded + swallowed
# exactly like the register call right after it -- a reconcile failure or
# slow run must never delay or block this spawn.
(cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
  bash scripts/hub/org-python.sh -m tools.session_reconcile --apply 2>/dev/null || true) >/dev/null 2>&1 </dev/null &

# Register session in c_level_sessions DB so gate 4 can query it later.
# stdio detached: a backgrounded child holding our stdout/stderr pipes
# makes programmatic callers (tests, capture_output) hang until it exits.
(cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
  bash scripts/hub/org-python.sh -m tools.register_cxo --role "$ROLE" --session "$CXO_SESSION_ID" --host "$HOST_KEY" 2>/dev/null || true) >/dev/null 2>&1 </dev/null &

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
  # .run is the launcher tmux exec'd us from (written by spawn-cxo.sh); it has
  # no reason to outlive the session it started.
  rm -f "$LOCKFILE" "$WINID_FILE" "$TTY_FILE" "$UUID_FILE" "$MCP_CONFIG" "$COO_SETTINGS" \
        "$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.run"
  # An empty SomPong mailbox box is not worth keeping per restart; rmdir leaves
  # one that still holds an unread letter (the next launch picks those up).
  if [ "$ROLE" = "coo" ]; then rmdir "$ROOT/state/inbox/$ROLE-$CXO_SESSION_ID" 2>/dev/null || true; fi
  # A Project Head's project claim and owner record (tools/spawn_ph.py) end
  # with the session, but are parked, not deleted: `spawn-ph.sh --resume <id>`
  # (a SafeRestart resume, a CEO resume) needs both. A .parked file claims no
  # project. 17 Oct 2026: deleting them left 4 PHs unresumable after a restart.
  if [ "$IS_PH" = "1" ]; then
    for _rec in project spawned_by; do
      if [ -f "$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.$_rec" ]; then
        mv -f "$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.$_rec" "$LOCKS_DIR/$ROLE-$CXO_SESSION_ID.$_rec.parked"
      fi
    done
  fi
  # Only clear the active pointer if it still points at us and we wrote it.
  if [ -z "$SESSION_OVERRIDE" ] && [ "$IS_PH" = "0" ] && [ -e "$ACTIVE_FILE" ]; then
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
# OSC 1 = tab strip only. NOT OSC 0, which also rewrites the window titlebar
# and would wipe the Main Tab (goal + progress + clock) — see tools/maintab.py.
printf '\033]1;%s ⏳ เริ่ม session\007' "$TAB_TITLE"

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
# "🎯 <ROLE> #<sid> · ⏱ 0m" — honest, and already ticking; the agent replaces
# the goal at /session-open. Also starts the shared refresh daemon.
(cd "$ROOT" && python3 -m tools.maintab set) >/dev/null 2>&1 || true

# Keep claude CLI from overwriting our tab title with its own (no-op on
# builds without this env). The keeper loop below re-asserts regardless.
export CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1

# ADR 0013 Phase 5 — org wiki root on a non-Mac box.
# config/wikis.yaml carries Mac absolute paths; Contabo keeps its copy at
# /opt/MoonieXHQ/Agents/Rules since the HQ move (2026-09-23).
# Fall back to the Mac checkout when present.
if [ -z "${WIKI_ROOT_ORG:-}" ]; then
  for d in /opt/MoonieXHQ/Agents/Rules "$HOME/MoonieXHQ/Agents/Rules"; do
    if [ -d "$d" ]; then export WIKI_ROOT_ORG="$d"; break; fi
  done
fi

# MoonieX product wiki on Contabo (CEO 2026-08-09). Previously Mac-only, which
# made `mooniex:` fail on that box — and with it every UNPREFIXED path, since
# mooniex is the default namespace. Both hosts now use plain git checkouts.
if [ -z "${WIKI_ROOT_MOONIEX:-}" ]; then
  for d in /opt/MoonieXHQ/Agents/Wikis "$HOME/MoonieXHQ/Agents/Wikis"; do
    if [ -d "$d" ]; then export WIKI_ROOT_MOONIEX="$d"; break; fi
  done
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

MODEL_ARGS=(--model "$MODEL" --fallback-model 'claude-fable-5' --effort "$EFFORT")

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
# whenever spawn-cxo.sh translated --resume/--last. Detect and add it.
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

# Belt-and-braces auto-compact window (task-9f6fec26): claude-home/settings.json
# carries the same 300000 at its documented `autoCompactWindow` key, but the
# env var wins on priority and is the only form that reaches a box where
# settings.json is a stale copy rather than the Mac's live symlink.
: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW

# INITIAL_PROMPT (ephemeral --spawn from tools/send_to_cxo.py) rides in as
# claude's final positional argv, same as ARGS above -- a `claude` process
# started with a positional prompt auto-submits it instantly, zero
# keypresses (measured, not inferred -- see runners/worker_init.py's kickoff
# and its docstring correction in tools/send_to_worker.py). No osascript, no
# delay, no tab-name search: task-093a3939 replaces the former
# sleep-then-type background job (a 5s guess that raced the tab's own
# readiness) with this.
CLAUDE_POSITIONAL=(${ARGS[@]+"${ARGS[@]}"})
if [ -n "${INITIAL_PROMPT:-}" ]; then
  CLAUDE_POSITIONAL+=("$INITIAL_PROMPT")
fi

# MACHINE_LABEL/HOST_KEY are computed earlier now (right before the reconcile
# + register_cxo calls) so both have the host key ready in time -- see that
# block, above the "Register session in c_level_sessions" comment.

# Remote Control registration (task-bbdfa8d1, CEO 2026-09-11): "ส่งไปแก้เลย
# ให้เป็นกฎเหล็กเลย เพราะฉันเช็คไม่ได้เลยว่ามี session เปิดจริงไหม" -- every
# C-level session must show in the CEO's Claude app, same as workers already
# do. Reuses runners.worker_init.remote_control_args() -- the SAME per-host
# switch (config/hosts.yaml `remote_control`, default true) workers read --
# instead of hardcoding the flag here, so one switch governs every role and
# the two paths can't drift. Fails open (flag included) on any lookup error,
# same as the function it calls.
REMOTE_CONTROL_ARGS=()
if [ "$(source .venv/bin/activate 2>/dev/null; python3 -c "
from runners.worker_init import remote_control_args
print('1' if remote_control_args('$HOST_KEY') else '0')
" 2>/dev/null || echo 1)" != "0" ]; then
  REMOTE_CONTROL_ARGS=(--remote-control)
fi
# SomPong's Remote Control name is its session name, "COO (SomPong)" (CEO
# 2026-10-14; it was the bare "SomPong" until then). The flag takes an optional
# value, so the name is appended to the array built above.
if [ "$ROLE" = "coo" ] && [ "${#REMOTE_CONTROL_ARGS[@]}" -gt 0 ]; then
  REMOTE_CONTROL_ARGS+=("${HOST_EMOJI:+$HOST_EMOJI }$CLEVEL_NAME")
fi

# Pull the auto-memory repo BEFORE claude starts (task-8d37c0f1) — same
# reasoning as cto-claude.sh's identical block: the harness loads MEMORY.md
# into context at process start, before any skill can run, so this is the
# only place a fresh pull lands in time. Foreground (not backgrounded like
# reconcile/register_cxo above); memory_sync.py bounds every git call
# internally (GIT_TIMEOUT_SECONDS) and pull() never returns non-zero, so
# `|| true` here is a second belt, not the only one. cxo-claude.sh has no
# CTO_CLAUDE_TEST_MODE early-exit of its own (only cto-claude.sh does), so
# this guard is the actual skip for that env var, not just a mirror of one.
if [ "${CTO_CLAUDE_TEST_MODE:-0}" != "1" ] && [ "$ROLE" != "coo" ]; then
  (cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
    python3 -m tools.memory_sync pull) || true
fi
if [ "${CTO_CLAUDE_TEST_MODE:-0}" != "1" ]; then
  (cd "$ROOT" && source .venv/bin/activate 2>/dev/null || true
    export WIKI_ROOT_ORG WIKI_ROOT_MOONIEX
    python3 -m tools.kit_sync pull) || true
fi

# SomPong: cwd is its own repo (CLAUDE.md, memory, the family-gate hook live
# there), and `claude` below is a function that runs the real binary as the
# unprivileged SomPong user with an empty environment plus COO_ENV. Everything
# above (locks, c_level_sessions row, mailbox dir) was done as the launching user.
# SomPong's memory is its own (work/memory), so the org memory pull is skipped.
if [ "$ROLE" = "coo" ]; then
  cd "$SOMPONG_DIR"
  # The session's UserPromptSubmit hook drains state/inbox/<role>-<id> keyed on
  # these two; the box must exist and be group-writable so the unprivileged user
  # can delete a letter it has read (send_to_cxo makes the letter readable).
  COO_ENV+=("CXO_ROLE=$ROLE" "CXO_SESSION=1" "CXO_SESSION_ID=$CXO_SESSION_ID")
  COO_BOX="$ROOT/state/inbox/$ROLE-$CXO_SESSION_ID"
  mkdir -p "$COO_BOX" && chmod 2775 "$COO_BOX" 2>/dev/null || true
  # scripts/session-rename.sh records the topic it sent in state/locks/<role>-<id>.topic, and
  # state/locks is the launching user's: hand the unprivileged user this one file, nothing more,
  # or every rename request is re-sent and --show answers (none) (SomPong, 16 Oct 2026).
  COO_TOPIC="$ROOT/state/locks/$ROLE-$CXO_SESSION_ID.topic"
  [ -e "$COO_TOPIC" ] || : > "$COO_TOPIC"
  chown "$COO_UNIX_USER" "$COO_TOPIC" 2>/dev/null || true
  # Each launch is a new session id, so a letter that reached the previous
  # session's box and was never read (it died first) moves to this one: the lock
  # check above proved no other SomPong is alive. rmdir only takes an empty box.
  for old in "$ROOT"/state/inbox/coo-*; do
    [ -d "$old" ] && [ "$old" != "$COO_BOX" ] || continue
    mv "$old"/*.json "$COO_BOX"/ 2>/dev/null || true
    rmdir "$old" 2>/dev/null || true
  done
  COO_RUNUSER="$(command -v runuser 2>/dev/null || echo /usr/sbin/runuser)"
  claude() {
    if [ "$(id -u)" = "$COO_UID" ]; then
      env -i ${COO_ENV[@]+"${COO_ENV[@]}"} "$COO_CLAUDE_BIN" "$@"
    else
      "$COO_RUNUSER" -u "$COO_UNIX_USER" -- env -i ${COO_ENV[@]+"${COO_ENV[@]}"} "$COO_CLAUDE_BIN" "$@"
    fi
  }
fi

# Project Head: the project rides in the session name from the first second
# (below); NAME_SUFFIX is the old long form, kept as the fallback.
NAME_SUFFIX=""
if [ "$IS_PH" = "1" ]; then NAME_SUFFIX=" ($PH_PROJECT)"; fi
# A C-level primary session is "<ROLE> (<Name>)", or the bare "<ROLE>" without a
# persona: no machine, no #id (CEO 2026-10-14). tools/live_sessions.py finds its role
# and id in the tmux name and the session UUID instead. TAB_TITLE and its .base stay
# as they are (routing); a Project Head and an ephemeral session keep the long form.
# A Project Head is "PH#<id3> (<LANE>) - <Project>" (CEO 2026-10-14); the rule lives
# in lib/config.ph_session_name. The long form stays if that lookup fails.
SESSION_NAME="$MACHINE_LABEL $TAB_TITLE$NAME_SUFFIX"
if [ -z "$TAB_TITLE_OVERRIDE" ] && [ "$IS_PH" != "1" ]; then
  SESSION_NAME="${HOST_EMOJI:+$HOST_EMOJI }$CLEVEL_NAME"
elif [ -z "$TAB_TITLE_OVERRIDE" ] && [ "$IS_PH" = "1" ]; then
  _PH_NAME="$(cd "$ROOT" && PH_SID="$CXO_SESSION_ID" PH_LANE="$PH_LANE" PH_PROJECT="$PH_PROJECT" \
    PH_HOST="${SELF_HOST:-}" .venv/bin/python -c "
import os
from lib.config import ph_session_name
print(ph_session_name(os.environ['PH_SID'], os.environ['PH_LANE'], os.environ['PH_PROJECT'],
                      os.environ['PH_HOST']))" 2>/dev/null)" \
    && [ -n "$_PH_NAME" ] && SESSION_NAME="$_PH_NAME"
fi

# Per-session memory scope (org restructure P2, plan §7) when ORG_SESSION_SCOPE=1:
# claude runs in its own transient systemd scope with MemoryHigh/MemoryMax, so
# the kernel reclaims or stops only the session that runs away instead of the
# whole org-tmux.scope (2026-10-01: one OOM kill ended every Contabo session).
# Root with systemd-run only; anywhere else this is a no-op. A scope that cannot
# be created makes systemd-run fail, so the session does not start silently
# unlimited: unset the flag to start it the old way.
if org_flag ORG_SESSION_SCOPE && [ "$(id -u)" = "0" ] && command -v systemd-run >/dev/null 2>&1; then
  _SCOPE=(systemd-run --scope --quiet --collect
    --unit "org-$ROLE-$CXO_SESSION_ID"
    -p "MemoryHigh=${ORG_SESSION_MEM_HIGH:-1536M}"
    -p "MemoryMax=${ORG_SESSION_MEM_MAX:-2560M}" --)
  if [ "$ROLE" = "coo" ]; then
    # SomPong's claude is the function above (runuser + env -i), which systemd-run
    # cannot exec; the scope wraps the runuser/env inside it instead.
    claude() {
      if [ "$(id -u)" = "$COO_UID" ]; then
        "${_SCOPE[@]}" env -i ${COO_ENV[@]+"${COO_ENV[@]}"} "$COO_CLAUDE_BIN" "$@"
      else
        "${_SCOPE[@]}" "$COO_RUNUSER" -u "$COO_UNIX_USER" -- env -i ${COO_ENV[@]+"${COO_ENV[@]}"} "$COO_CLAUDE_BIN" "$@"
      fi
    }
  else
    _SCOPE+=("$(type -P claude)")
    claude() { "${_SCOPE[@]}" "$@"; }
  fi
fi

# `exec` would skip the EXIT trap → stale lock. Run claude as child.
claude \
  -n "$SESSION_NAME" \
  "${MODEL_ARGS[@]}" \
  --permission-mode auto \
  --append-system-prompt "$ROLE_PROMPT" \
  --mcp-config "$MCP_CONFIG" \
  ${COO_ARGS[@]+"${COO_ARGS[@]}"} \
  ${STRICT_ARGS[@]+"${STRICT_ARGS[@]}"} \
  ${REMOTE_CONTROL_ARGS[@]+"${REMOTE_CONTROL_ARGS[@]}"} \
  ${CHROME_ARGS[@]+"${CHROME_ARGS[@]}"} \
  --allowed-tools $ALLOWED \
  --session-id "$CXO_UUID" \
  ${FORK_ARGS[@]+"${FORK_ARGS[@]}"} \
  ${CLAUDE_POSITIONAL[@]+"${CLAUDE_POSITIONAL[@]}"}
exit $?

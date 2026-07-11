#!/usr/bin/env bash
# contabo-org-runtime-deploy.sh — put the mooniex-agents org runtime on Contabo.
# Phase A of ADR decisions/2026-07-12-org-runtime-to-contabo.md (wiki):
# rsync the repo + build a Python venv so runners.cto_chat CAN run there.
# Staged + idempotent: run a stage, verify, run the next.
#
#   ./contabo-org-runtime-deploy.sh sync      # rsync working tree -> /opt/mooniex-agents (no secrets)
#   ./contabo-org-runtime-deploy.sh venv      # python3 -m venv /opt/mooniex-agents/.venv
#   ./contabo-org-runtime-deploy.sh install   # pip install -r requirements.txt into the venv
#   ./contabo-org-runtime-deploy.sh verify    # acceptance checks (files, imports, no secrets, size)
#   ./contabo-org-runtime-deploy.sh all       # sync + venv + install + verify
#
# SCOPE (ADR Phase A only): repo + venv. NOT copied here (later phases):
#   - state/ (live tasks.db + logs)   -> Phase D cutover
#   - .env, wiki SSH key, GH token, MCP secrets -> Phase C
#   - Claude Code CLI + OAuth login   -> Phase B (CEO interactive, not automatable)
# Do NOT actually run `python -m runners.cto_chat` from this script — needs Phase B auth.
#
# Source of truth = the repo this script lives in (works from the canonical
# /Users/gob/Projects/Agents checkout OR a git worktree). The exclude list
# below keeps secrets/state/junk off the box regardless of which source runs it.
set -euo pipefail

IP="${IP:-194.233.80.26}"
KEY="${KEY:-$HOME/.ssh/mooniex_contabo_claudeflow}"
REMOTE="${REMOTE:-/opt/mooniex-agents}"
SSH_OPTS=(-o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)

# repo root = one level up from scripts/ (this file), resolved absolute.
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

STAGE="${1:?usage: $0 <sync|venv|install|verify|all>}"

log(){ printf '\033[36m[org-runtime]\033[0m %s\n' "$*"; }
die(){ printf '\033[31m[FATAL]\033[0m %s\n' "$*" >&2; exit 1; }

rsh(){ ssh "${SSH_OPTS[@]}" -i "$KEY" "root@$IP" "$@"; }

# Exclude list — the security boundary for Phase A. Keep in sync with the
# report / ADR. Everything secret, stateful, or heavy stays on the Mac.
EXCLUDES=(
  --exclude '.git/'            # worktree .git is a file; canonical is a dir — never copy either
  --exclude '.gitignore'       # harmless but pointless on the box
  --exclude 'node_modules/'
  --exclude 'state/'           # live tasks.db + logs + locks — Phase D, explicitly out of scope
  --exclude '.env'             # secrets — Phase C
  --exclude '.env.*'
  --exclude '.venv/'           # rebuilt on-box for the right arch (linux, not darwin)
  --exclude 'worktrees/'       # DEV worktrees — not runtime
  --exclude 'output/'          # generated posters/artifacts
  --exclude 'assets/brand-refs/'  # heavy brand reference library, not runtime code
  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '.DS_Store'
  --exclude '.claude/'         # local Claude Code settings/secrets — not runtime
  --exclude 'TASK.md'          # per-task worker file, not runtime
)

stage_sync(){
  [ -f "$SRC/requirements.txt" ] || die "no requirements.txt under $SRC — wrong source dir?"
  [ -f "$KEY" ] || die "missing SSH key $KEY"
  log "rsync $SRC/  ->  root@$IP:$REMOTE/  (excludes: ${#EXCLUDES[@]} rules)"
  rsh "mkdir -p '$REMOTE'"
  # --delete keeps the box a faithful mirror of the source (idempotent re-runs
  # drop files removed locally). Excludes are honored on delete too.
  rsync -aH --delete "${EXCLUDES[@]}" \
    -e "ssh ${SSH_OPTS[*]} -i $KEY" \
    "$SRC/" "root@$IP:$REMOTE/"
  log "sync done"
}

stage_venv(){
  log "creating venv at $REMOTE/.venv (idempotent — python3 -m venv is safe to re-run)"
  rsh "test -d '$REMOTE' || { echo 'run sync first'; exit 1; }
       python3 -m venv '$REMOTE/.venv'
       '$REMOTE/.venv/bin/python' --version"
  log "venv ready"
}

stage_install(){
  log "pip install -r requirements.txt into $REMOTE/.venv"
  rsh "test -x '$REMOTE/.venv/bin/pip' || { echo 'run venv first'; exit 1; }
       '$REMOTE/.venv/bin/pip' install --upgrade pip >/dev/null
       '$REMOTE/.venv/bin/pip' install -r '$REMOTE/requirements.txt'"
  log "install done"
}

stage_verify(){
  log "AC1 — runners/cto_chat.py present:"
  rsh "ls -l '$REMOTE/runners/cto_chat.py'" || die "AC1 FAILED — cto_chat.py missing"

  log "AC2 — venv imports cto_chat deps (does NOT run cto_chat):"
  rsh "'$REMOTE/.venv/bin/python' -c 'import claude_agent_sdk, rich, textual, yaml, anyio; print(\"deps OK\")'" \
    || die "AC2 FAILED — missing deps in venv"

  log "AC3 — no secrets/state copied (both should be absent):"
  rsh "ls '$REMOTE/state' 2>&1; ls '$REMOTE/.env' 2>&1" || true

  log "AC4 — on-box repo size:"
  rsh "du -sh '$REMOTE'"

  log "verify done — review AC3 output above: state/ and .env MUST report 'No such file or directory'"
}

case "$STAGE" in
  sync)    stage_sync ;;
  venv)    stage_venv ;;
  install) stage_install ;;
  verify)  stage_verify ;;
  all)     stage_sync; stage_venv; stage_install; stage_verify ;;
  *) die "unknown stage '$STAGE' (sync|venv|install|verify|all)" ;;
esac

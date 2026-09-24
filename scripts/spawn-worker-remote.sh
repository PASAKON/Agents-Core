#!/usr/bin/env bash
# CONTABO WORKER LAUNCHER — Phase 2 (docs/design/multi-host-workers.md §4,
# task-a5c0549d). Runs ON the spoke (Linux), invoked by
# tools/delegate.py::_spawn_remote's linux branch over:
#   ssh mooniex-vps bash <agents_root>/scripts/spawn-worker-remote.sh --task ...
# with the hub's rendered TASK.md prompt piped in on stdin.
#
# Mirrors windows/spawn-worker.ps1's parameters and behavior one-for-one,
# minus what Linux/tmux does not need: no session-0/session-1 GUI boundary,
# no scheduled task, no wt.exe tab — `tmux new-session -d` IS the detached
# worker, and its pane_pid stays valid as the worker's own pid once the
# launcher `exec`s into `claude` (no fork in between).
#
# Clones/fetches the project, adds a worktree on a fresh task branch
# (idempotent: refuses only if a prior occupant left real uncommitted work),
# writes TASK.md from stdin, starts `claude` inside a detached tmux session,
# and prints the pid as part of the LAST line:
#   SPAWNED pid=<n> session=<tmux-session-name> worktree=<path>
# Every other line is informational and must come before that one. On a
# refused/dirty worktree, prints `SPAWN_REFUSED=<reason> <path>` instead and
# exits 1 (tools/delegate.py greps for this prefix, host-agnostically).
#
# POSIX/bash-3-compatible ON PURPOSE, even though it only ever EXECUTES on
# Contabo's newer bash: tests run this under macOS's bash 3.2 via `bash -n`
# and `--dry-run` (tests/test_spawn_remote_linux.py). No arrays, no
# `declare -A`, no `mapfile`, no `${var,,}`.
#
# Never prompts: git network ops are forced non-interactive so a bad
# credential or unknown host key fails loudly instead of hanging the pipe.
# No secret ever appears in argv, files or logs — claude authenticates from
# its own stored credentials, never from anything this script is handed.

set -uo pipefail

DRY_RUN=0
TASK="" PROJECT="" ROLE="" BRANCH="" BASE="" REPO_URL="" REPO_PATH=""
WORKTREE_ROOT="" CLAUDE_ARGS="" MODEL="" EFFORT="" SESSION_NAME="" RUNNER="claude"
TASK_META_B64=""

while [ $# -gt 0 ]; do
  case "$1" in
    --task) TASK="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --base) BASE="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --repo-path) REPO_PATH="$2"; shift 2 ;;
    --worktree-root) WORKTREE_ROOT="$2"; shift 2 ;;
    --claude-args) CLAUDE_ARGS="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --effort) EFFORT="$2"; shift 2 ;;
    --session-name) SESSION_NAME="$2"; shift 2 ;;
    --runner) RUNNER="$2"; shift 2 ;;
    --task-meta-b64) TASK_META_B64="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    *) echo "spawn-worker-remote.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

# CLAUDE_ARGS may legitimately be empty for a future non-claude runner
# (parity with windows/spawn-worker.ps1's AllowEmptyString -ClaudeArgs) --
# not required here.
if [ -z "$TASK" ] || [ -z "$PROJECT" ] || [ -z "$ROLE" ] || [ -z "$BRANCH" ] \
   || [ -z "$BASE" ] || [ -z "$REPO_URL" ] || [ -z "$REPO_PATH" ] \
   || [ -z "$WORKTREE_ROOT" ] || [ -z "$MODEL" ] || [ -z "$EFFORT" ] \
   || [ -z "$SESSION_NAME" ]; then
  echo "spawn-worker-remote.sh: missing required flag(s)" >&2
  exit 2
fi

if [ "$RUNNER" != "claude" ]; then
  echo "spawn-worker-remote.sh: runner '$RUNNER' not supported by this launcher yet (claude only)" >&2
  exit 2
fi

WT="${WORKTREE_ROOT}/${PROJECT}__${ROLE}__${TASK}"
# tmux-safe identifier (no spaces/parens, unlike --session-name which is
# claude's own human-readable -n display value) -- this IS what the
# "session=" field in the final SPAWNED line reports.
TMUX_SESSION="mooniex-${TASK}"

# Resolve this script's own location so role docs (roles/*.md) are read
# straight from THIS box's already-cloned org checkout -- Contabo's
# agents_root IS a live clone of this same repo (unlike winbox's dedicated
# non-git deploy folder), so no separate role-doc deploy is needed.
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
AGENTS_ROOT=$(dirname "$SCRIPT_DIR")
ROLES_DIR="$AGENTS_ROOT/roles"

if [ "$DRY_RUN" -eq 1 ]; then
  echo "[dry-run] task=$TASK project=$PROJECT role=$ROLE branch=$BRANCH base=$BASE"
  echo "[dry-run] repo_url=$REPO_URL repo_path=$REPO_PATH"
  echo "[dry-run] worktree=$WT"
  echo "[dry-run] tmux_session=$TMUX_SESSION"
  echo "[dry-run] model=$MODEL effort=$EFFORT runner=$RUNNER"
  echo "[dry-run] claude_args=$CLAUDE_ARGS"
  echo "[dry-run] session_name=$SESSION_NAME"
  echo "[dry-run] roles_dir=$ROLES_DIR"
  if [ -n "$TASK_META_B64" ]; then
    echo "[dry-run] task_meta_b64=$TASK_META_B64"
  fi
  echo "[dry-run] would: clone/fetch $REPO_PATH; worktree add -b $BRANCH $WT origin/$BASE (reuse if present, refuse if dirty); decode --task-meta-b64 into $WT/.org-task.json (mode 600, GH #180 sidecar) when given; copy this box's own scripts/hook-self-repo-guard.py into $WT/scripts/ so a pre-merge fix reaches the worktree; write TASK.md from stdin; prepend $AGENTS_ROOT/.tools/node/bin to PATH in launch.sh when that directory exists; tmux new-session -d -s $TMUX_SESSION -c $WT bash -l <launch.sh running claude>"
  exit 0
fi

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

# --- 1. Clone (first use) or fetch (repeat use) ---
if [ ! -d "$REPO_PATH/.git" ]; then
  mkdir -p "$(dirname "$REPO_PATH")"
  if ! git clone --filter=blob:none "$REPO_URL" "$REPO_PATH"; then
    echo "spawn-worker-remote.sh: git clone failed for $REPO_URL" >&2
    exit 1
  fi
fi
if ! git -C "$REPO_PATH" fetch origin; then
  echo "spawn-worker-remote.sh: git fetch failed in $REPO_PATH" >&2
  exit 1
fi

# --- 2. Worktree on a fresh task branch (idempotent: this launcher may run
# more than once for the same task while the pipe is being tested; refuse
# only if a prior occupant left real uncommitted tracked work) ---
STALE_FILES="REPORT.md BLOCKER.md MAILBOX.md HEARTBEAT"

if [ -d "$WT" ]; then
  if [ -d "$WT/.git" ]; then
    DIRTY=$(git -C "$WT" status --porcelain 2>/dev/null | grep -v '^??' || true)
    if [ -n "$DIRTY" ]; then
      echo "SPAWN_REFUSED=dirty-worktree $WT"
      exit 1
    fi
  fi
  git -C "$REPO_PATH" worktree remove --force "$WT" >/dev/null 2>&1 || true
  [ -d "$WT" ] && rm -rf "$WT"
fi
git -C "$REPO_PATH" branch -D "$BRANCH" >/dev/null 2>&1 || true
mkdir -p "$WORKTREE_ROOT"
if ! git -C "$REPO_PATH" worktree add -b "$BRANCH" "$WT" "origin/$BASE"; then
  echo "spawn-worker-remote.sh: git worktree add failed ($WT on $BRANCH from origin/$BASE)" >&2
  exit 1
fi

# GH #151 defense-in-depth (same rationale as spawn-worker.ps1): a stale
# REPORT.md/BLOCKER.md committed to $BASE by mistake, or left by a prior
# occupant of this same worktree path, must never leak into a fresh worker.
for f in $STALE_FILES; do
  [ -f "$WT/$f" ] && rm -f "$WT/$f"
done

# HEARTBEAT/MAILBOX.md must never be committed (same rule as
# roles/_worker_remote.md documents) -- per-clone info/exclude, not the
# tracked .gitignore, so it applies to any project cloned on this box.
EXCLUDE_FILE=$(git -C "$REPO_PATH" rev-parse --git-path info/exclude 2>/dev/null)
case "$EXCLUDE_FILE" in
  /*) : ;;
  *) EXCLUDE_FILE="$REPO_PATH/$EXCLUDE_FILE" ;;
esac
mkdir -p "$(dirname "$EXCLUDE_FILE")"
touch "$EXCLUDE_FILE"
for name in HEARTBEAT MAILBOX.md; do
  grep -qxF "$name" "$EXCLUDE_FILE" 2>/dev/null || echo "$name" >> "$EXCLUDE_FILE"
done

# --- 2b. Sidecar (GH #180, task-378523bb): the hub already knows this
# task's declared touches at spawn time -- write them straight into the
# worktree instead of relying on this box's own (possibly unsynced)
# state/tasks.db. Mode 600: no secret in here, but no reason to leave it
# group/world readable either. Never committed -- add it to info/exclude
# the same way HEARTBEAT/MAILBOX.md are, so an accidental `git add -A`
# can't sweep it onto the worker's own branch.
grep -qxF ".org-task.json" "$EXCLUDE_FILE" 2>/dev/null || echo ".org-task.json" >> "$EXCLUDE_FILE"
if [ -n "$TASK_META_B64" ]; then
  if ! printf '%s' "$TASK_META_B64" | base64 -d > "$WT/.org-task.json" 2>/dev/null; then
    echo "spawn-worker-remote.sh: --task-meta-b64 did not decode as base64" >&2
    rm -f "$WT/.org-task.json"
  else
    chmod 600 "$WT/.org-task.json"
  fi
fi

# --- 2c. Pre-merge guard fix (GH #180): a freshly checked-out worktree gets
# whatever scripts/hook-self-repo-guard.py was on origin/$BASE at clone
# time, which won't carry a fix until the PR that adds it is merged. This
# box's own copy of the script (tools/delegate.py::_ensure_remote_deploy_linux
# scp's it here ahead of any merge, same mechanism as this launcher script
# itself) is authoritative -- copy it into the worktree so the guard a
# spawned worker actually runs is never stale.
GUARD_SRC="$SCRIPT_DIR/hook-self-repo-guard.py"
if [ -f "$GUARD_SRC" ]; then
  mkdir -p "$WT/scripts"
  cp "$GUARD_SRC" "$WT/scripts/hook-self-repo-guard.py"
fi

# --- 3. TASK.md from stdin (the hub's rendered prompt) ---
cat > "$WT/TASK.md"

# --- 4. WORKER.md: the remote-worker contract, read from this box's own
# already-cloned roles/ dir ---
REMOTE_CONTRACT="$ROLES_DIR/_worker_remote.md"
SHARED_DOC="$ROLES_DIR/_worker_shared.md"
ROLE_DOC="$ROLES_DIR/${ROLE}.md"

if [ ! -f "$REMOTE_CONTRACT" ] || [ ! -f "$SHARED_DOC" ] || [ ! -f "$ROLE_DOC" ]; then
  echo "SPAWN_REFUSED=missing-role-docs $ROLES_DIR"
  exit 1
fi
cp "$REMOTE_CONTRACT" "$WT/WORKER.md"

# --- 5. System prompt: shared conventions + role doc + remote contract
# (same composition runners/worker_init.py builds for a Mac-spawned DEV,
# plus the remote contract), written beside this script's own launch area
# (agents_root), never inside the worktree -- a file dropped in the
# worktree would get swept into the worker's own `git add -A` and pushed
# onto its branch. ---
LAUNCH_DIR="$AGENTS_ROOT/.launch-${TASK}"
mkdir -p "$LAUNCH_DIR"
PROMPT_FILE="$LAUNCH_DIR/prompt.txt"
SYSPROMPT_FILE="$LAUNCH_DIR/system_prompt.txt"
cp "$WT/TASK.md" "$PROMPT_FILE"
{ cat "$SHARED_DOC"; printf '\n\n'; cat "$ROLE_DOC"; printf '\n\n'; cat "$REMOTE_CONTRACT"; } > "$SYSPROMPT_FILE"

# --- 6. Resolve claude's absolute path HERE, in this script's own ssh-exec
# environment -- not inside the launched shell. `ssh alias 'bash script'`
# runs a NON-interactive, NON-login shell, which does not source
# ~/.bashrc/~/.profile/~/.zshrc; a `claude` only on PATH via one of those
# (a common nvm/npm-installer pattern) would silently resolve to nothing (or
# worse, a stale/wrong binary from a login shell's own re-sourced PATH) once
# handed to a freshly spawned shell inside tmux. Measured locally
# (task-a5c0549d fixture run): a `bash -l "$LAUNCH_SH"` launch could not see
# a PATH entry this ssh session's own environment already had. Trying
# `command -v` first (trusts whatever PATH this ssh exec actually got, which
# is however the box's two live CTO sessions themselves find it) then the
# installer's default location keeps this independent of shell startup
# files entirely. ---
CLAUDE_BIN=""
for candidate in "$(command -v claude 2>/dev/null)" \
                 "$HOME/.local/bin/claude" \
                 "$HOME/.npm-global/bin/claude" \
                 "/usr/local/bin/claude" \
                 "/usr/bin/claude"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    CLAUDE_BIN="$candidate"
    break
  fi
done
if [ -z "$CLAUDE_BIN" ]; then
  echo "SPAWN_REFUSED=claude-not-found (checked PATH, ~/.local/bin, ~/.npm-global/bin, /usr/local/bin, /usr/bin)"
  exit 1
fi

# --- 7. Launch: a tiny generated launch.sh inside a detached tmux session.
# The prompt and system prompt are read back from files via `"$(cat ...)"`
# rather than inlined into the command line -- both can be thousands of
# characters of quotes/newlines/non-ASCII, exactly the hazard
# windows/spawn-worker.ps1's JSON-args-file technique avoids on its side.
# --allowed-tools (inside $CLAUDE_ARGS) stays LAST with nothing after it --
# it is variadic and swallows every following argv element (see
# runners/worker_init.py). ---
sh_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
}

TMUX_BIN=$(command -v tmux || echo tmux)

# ORG_HOST parity with runners/worker_init.py's current_host() (winbox sets
# the same via $env:ORG_HOST). ORG_WORKER_FINISH: roles/_worker_remote.md
# tells every remote worker to run it when done/blocked -- windows sets it
# to a generated .cmd; here it's a plain kill-session (this session's own
# controlling process), the whole point of tmux new-session -d being the
# worker in the first place. NOTE (not fixed here, roles/_worker_remote.md
# is a shared file outside this task's touches): that doc's own wording,
# "run `%ORG_WORKER_FINISH%`", is Windows batch %VAR% syntax -- a Linux
# worker's Bash tool needs `$ORG_WORKER_FINISH` (or `eval "$ORG_WORKER_FINISH"`)
# instead. The env var is exported correctly either way; only the doc's
# literal instruction text is platform-specific.
# Node 22 for workers only (task-378523bb): the box's system Node (20.20.2,
# host services -- usage feeds, login relay -- depend on it) must not be
# touched, but hyperframes@0.8.40 needs >=22 (EBADENGINE otherwise). Prepend
# only, and only when the tarball is actually there -- installing it is a
# separate, explicit step (config/machine-contract.yaml), not this script's
# job, so a box that hasn't been set up yet just keeps using system Node.
NODE22_BIN="$AGENTS_ROOT/.tools/node/bin"

LAUNCH_SH="$LAUNCH_DIR/launch.sh"
{
  echo '#!/bin/sh'
  printf 'export ORG_HOST=contabo\n'
  printf 'export ORG_WORKER_FINISH=%s\n' \
    "$(sh_quote "$TMUX_BIN kill-session -t $TMUX_SESSION")"
  printf 'if [ -d %s ]; then export PATH=%s:"$PATH"; fi\n' \
    "$(sh_quote "$NODE22_BIN")" "$(sh_quote "$NODE22_BIN")"
  printf 'exec %s "$(cat %s)" -n %s --append-system-prompt "$(cat %s)" %s\n' \
    "$(sh_quote "$CLAUDE_BIN")" \
    "$(sh_quote "$PROMPT_FILE")" \
    "$(sh_quote "$SESSION_NAME")" \
    "$(sh_quote "$SYSPROMPT_FILE")" \
    "$CLAUDE_ARGS"
} > "$LAUNCH_SH"
chmod +x "$LAUNCH_SH"

"$TMUX_BIN" new-session -d -s "$TMUX_SESSION" -c "$WT" bash "$LAUNCH_SH"

if ! "$TMUX_BIN" has-session -t "$TMUX_SESSION" 2>/dev/null; then
  echo "spawn-worker-remote.sh: tmux session $TMUX_SESSION did not start" >&2
  exit 1
fi

# --- 8. Capture the worker pid. tmux's pane_pid IS the worker's own pid --
# launch.sh's last line `exec`s into claude, replacing the process image
# without forking, so the pid tmux started never changes. ---
sleep 0.3
WORKER_PID=$("$TMUX_BIN" list-panes -t "$TMUX_SESSION" -F '#{pane_pid}' 2>/dev/null | head -n 1)
if [ -z "$WORKER_PID" ]; then
  echo "spawn-worker-remote.sh: could not read pane pid for $TMUX_SESSION" >&2
  exit 1
fi
echo "$WORKER_PID" > "$WT/.worker.pid"

# LAST line of stdout, on purpose — the hub parses this one. Nothing may
# print after it.
echo "SPAWNED pid=${WORKER_PID} session=${TMUX_SESSION} worktree=${WT}"

#!/usr/bin/env bash
# CONTABO WORKER LAUNCHER — Phase 2 (docs/design/multi-host-workers.md §4,
# task-a5c0549d). Runs ON the spoke (Linux), invoked by
# tools/delegate.py::_spawn_remote's linux branch over:
#   ssh mooniex-vps bash <agents_root>/.launch/spawn-worker-remote.sh --task ...
# The hub deploys this file into <agents_root>/.launch/ (git-ignored), never
# into the spoke's tracked scripts/, so a deploy cannot dirty the spoke's checkout.
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
# codex/agy (W0.6, runner-routing contract): the generated launch.sh runs the
# CLI, then guarantees the run's report is committed on its branch at
# docs/reports/<task-id>/REPORT.md (a worker-written one is kept, a root
# REPORT.md is moved there, else it is built from codex's final message / the
# tail of agy's events log -- a run never ends without one), never commits its
# own bookkeeping files (info/exclude + `git reset` after `git add -A`), and
# pushes. `--org-host <name>` (default contabo) is the ORG_HOST the worker
# runs under. The claude runner path is unchanged.
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
# ORG_HOST the worker runs under (W0.6): `contabo` is what the only caller
# passes today (no flag); a hub that spawns codex/agy on another Linux box
# passes its own name here instead of inheriting a hard-coded one.
ORG_HOST="contabo"

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
    --org-host) ORG_HOST="$2"; shift 2 ;;
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

# ORG_HOST lands unquoted in the generated launch.sh (`export ORG_HOST=<name>`),
# so it is checked here at the trust boundary, not quoted later.
case "$ORG_HOST" in
  ''|*[!A-Za-z0-9._-]*)
    echo "spawn-worker-remote.sh: --org-host '$ORG_HOST' must match [A-Za-z0-9._-]+" >&2
    exit 2
    ;;
esac

case "$RUNNER" in
  claude|codex|agy) ;;
  *)
    echo "spawn-worker-remote.sh: runner '$RUNNER' not supported by this launcher (claude|codex|agy)" >&2
    exit 2
    ;;
esac

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
LAUNCH_DIR="$AGENTS_ROOT/.launch-${TASK}"
CODEX_FINAL_MSG="$LAUNCH_DIR/codex-final.txt"
CODEX_TRANSCRIPT="$LAUNCH_DIR/codex-events.jsonl"
AGY_LOG="$LAUNCH_DIR/agy-events.log"

# Files a codex/agy run must never put on the branch (W0.6): the launcher's own
# bookkeeping, the CTO's scratch file, logs, and a ROOT REPORT.md/BLOCKER.md
# (the report goes to docs/reports/<task-id>/REPORT.md instead). Two guards:
# ANCHORED_EXCLUDES go into the clone's info/exclude, GIT_RESET_GUARD is
# `git reset`-ed after `git add -A` in the generated launch.sh.
#  - Every exclude line starts with '/' where it names a root file: an
#    unanchored `REPORT.md` would also hide docs/reports/<id>/REPORT.md.
#  - REPORT.md/BLOCKER.md are NOT in ANCHORED_EXCLUDES: info/exclude is shared
#    by every worktree of the clone, and claude workers here commit a root
#    REPORT.md/BLOCKER.md through `git add -A` (roles/_worker_remote.md). Only
#    the codex/agy launch.sh, which runs solely for those runners, resets them.
ANCHORED_EXCLUDES=".worker.pid /TASK.md /.org-task.json /.org-worker.mcp.json /CTO-FEEDBACK.md /*.log"
GIT_RESET_GUARD=".worker.pid TASK.md .org-task.json .org-worker.mcp.json CTO-FEEDBACK.md REPORT.md BLOCKER.md HEARTBEAT MAILBOX.md :(glob)*.log"

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
  if [ "$RUNNER" = "claude" ]; then
    echo "[dry-run] would: clone/fetch $REPO_PATH; worktree add -b $BRANCH $WT origin/$BASE (reuse if present, refuse if dirty); decode --task-meta-b64 into $WT/.org-task.json (mode 600, GH #180 sidecar) when given; write TASK.md from stdin; prepend $AGENTS_ROOT/.tools/node/bin to PATH in launch.sh when that directory exists; tmux new-session -d -s $TMUX_SESSION -c $WT bash -l <launch.sh running claude>"
  elif [ "$RUNNER" = "codex" ]; then
    CODEX_CMD="codex exec \"\$(cat TASK.md)\" -C \"$WT\" -s workspace-write --skip-git-repo-check --json -o $CODEX_FINAL_MSG > $CODEX_TRANSCRIPT 2>&1"
    echo "[dry-run] cmd=$CODEX_CMD"
    echo "[dry-run] would: clone/fetch $REPO_PATH; worktree add -b $BRANCH $WT origin/$BASE (reuse if present, refuse if dirty); decode --task-meta-b64 into $WT/.org-task.json (mode 600, GH #180 sidecar) when given; write TASK.md from stdin; prepend $AGENTS_ROOT/.tools/node/bin to PATH in launch.sh when that directory exists; tmux new-session -d -s $TMUX_SESSION -c $WT bash -l <launch.sh running codex>"
    echo "[dry-run] org_host=$ORG_HOST"
    echo "[dry-run] report_step: after codex exits, $WT/docs/reports/$TASK/REPORT.md is committed on $BRANCH -- kept if its line 1 is '# REPORT $TASK'; else root REPORT.md moved there (header prepended if missing); else built from $CODEX_FINAL_MSG (header, 'Runner: codex', exit code, text; 'no final message; exit=<n>' when empty)"
    echo "[dry-run] never_committed: $GIT_RESET_GUARD (info/exclude + git reset after git add -A)"
  elif [ "$RUNNER" = "agy" ]; then
    AGY_CMD="/root/.local/bin/agy -p \"\$(cat TASK.md)\" --model gemini-3.8-flash-high --mode accept-edits --add-dir \"$WT\" < /dev/null >> $AGY_LOG 2>&1"
    echo "[dry-run] cmd=$AGY_CMD"
    echo "[dry-run] would: clone/fetch $REPO_PATH; worktree add -b $BRANCH $WT origin/$BASE (reuse if present, refuse if dirty); decode --task-meta-b64 into $WT/.org-task.json (mode 600, GH #180 sidecar) when given; write TASK.md from stdin; prepend $AGENTS_ROOT/.tools/node/bin to PATH in launch.sh when that directory exists; tmux new-session -d -s $TMUX_SESSION -c $WT bash -l <launch.sh running agy>"
    echo "[dry-run] org_host=$ORG_HOST"
    echo "[dry-run] report_step: after agy exits, $WT/docs/reports/$TASK/REPORT.md is committed on $BRANCH -- kept if its line 1 is '# REPORT $TASK'; else root REPORT.md moved there (header prepended if missing); else built from the last 200 lines of $AGY_LOG (header, 'Runner: agy', exit code, text; 'no final message; exit=<n>' when empty)"
    echo "[dry-run] never_committed: $GIT_RESET_GUARD (info/exclude + git reset after git add -A)"
  fi
  exit 0
fi

export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

# Belt-and-braces auto-compact window (task-9f6fec26): claude-home/settings.json
# carries the same 300000 at its documented `autoCompactWindow` key, but on
# Contabo that file is a copy, not a live symlink, so it can drift stale.
: "${CLAUDE_CODE_AUTO_COMPACT_WINDOW:=300000}"
export CLAUDE_CODE_AUTO_COMPACT_WINDOW

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
# .worker.pid too: the codex/agy launch.sh runs `git add -A` after the CLI
# exits, and swept it into the branch commit (task-419e6c8c, 2026-09-29).
# W0.6: the rest of ANCHORED_EXCLUDES (see its comment above) -- launcher
# bookkeeping, CTO scratch, logs. `set -f`: the '/*.log' entry must reach
# the file as text, not be glob-expanded here.
set -f
for name in HEARTBEAT MAILBOX.md $ANCHORED_EXCLUDES; do
  grep -qxF "$name" "$EXCLUDE_FILE" 2>/dev/null || echo "$name" >> "$EXCLUDE_FILE"
done
set +f

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
if [ "$RUNNER" = "claude" ]; then
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
elif [ "$RUNNER" = "codex" ]; then
  CODEX_BIN=""
  for candidate in "$(command -v codex 2>/dev/null)" \
                   "/usr/bin/codex" \
                   "/usr/local/bin/codex" \
                   "$HOME/.local/bin/codex" \
                   "$HOME/.npm-global/bin/codex"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      CODEX_BIN="$candidate"
      break
    fi
  done
  if [ -z "$CODEX_BIN" ]; then
    echo "SPAWN_REFUSED=codex-not-found (checked PATH, /usr/bin, /usr/local/bin, ~/.local/bin, ~/.npm-global/bin)"
    exit 1
  fi
elif [ "$RUNNER" = "agy" ]; then
  AGY_BIN=""
  for candidate in "/root/.local/bin/agy" \
                   "$(command -v agy 2>/dev/null)" \
                   "$HOME/.local/bin/agy" \
                   "/usr/local/bin/agy" \
                   "/usr/bin/agy"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      AGY_BIN="$candidate"
      break
    fi
  done
  if [ -z "$AGY_BIN" ]; then
    echo "SPAWN_REFUSED=agy-not-found (checked /root/.local/bin/agy, PATH, ~/.local/bin)"
    exit 1
  fi
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

# W0.6 -- the tail every codex/agy launch.sh ends with, after the CLI exits
# and its exit status is in $CLI_RC: make sure the run's report sits at
# docs/reports/<task-id>/REPORT.md, stage everything except the never-commit
# files, commit, push. $1 runner name, $2 codex final-message file (or ''),
# $3 agy events log (or ''), $4 extra `git -c ...` identity args (or ''),
# $5 commit message.
# Task/branch/runner values are sh_quote-d assignments; the body is a quoted
# heredoc, so nothing in it is expanded when launch.sh is WRITTEN.
emit_report_commit_push() {
  printf 'TASK_ID=%s\n' "$(sh_quote "$TASK")"
  printf 'BRANCH_NAME=%s\n' "$(sh_quote "$BRANCH")"
  printf 'RUNNER_NAME=%s\n' "$(sh_quote "$1")"
  printf 'FINAL_MSG=%s\n' "$(sh_quote "$2")"
  printf 'LOG_TAIL=%s\n' "$(sh_quote "$3")"
  printf 'GIT_ID_ARGS=%s\n' "$(sh_quote "$4")"
  printf 'COMMIT_MSG=%s\n' "$(sh_quote "$5")"
  printf 'GIT_RESET_GUARD=%s\n' "$(sh_quote "$GIT_RESET_GUARD")"
  cat <<'REPORT_STEP_EOF'
R_DIR="docs/reports/$TASK_ID"
R="$R_DIR/REPORT.md"
HDR="# REPORT $TASK_ID"
mkdir -p "$R_DIR"
has_hdr() { [ -s "$1" ] && [ "$(head -n 1 "$1" | tr -d '\r')" = "$HDR" ]; }
put_hdr() { { printf '%s\n\n' "$HDR"; cat "$1"; } > "$1.hdr" && mv -f "$1.hdr" "$1"; }
build_report() {
  {
    printf '%s\n\n' "$HDR"
    printf 'Runner: %s\n' "$RUNNER_NAME"
    printf 'Exit code: %s\n\n' "$CLI_RC"
    if [ -n "$FINAL_MSG" ] && [ -s "$FINAL_MSG" ]; then
      cat "$FINAL_MSG"
    elif [ -n "$LOG_TAIL" ] && [ -s "$LOG_TAIL" ]; then
      tail -n 200 "$LOG_TAIL"
    else
      printf 'no final message; exit=%s\n' "$CLI_RC"
    fi
  } > "$R"
}
if has_hdr "$R"; then
  :
elif [ -s REPORT.md ]; then
  if git ls-files --error-unmatch REPORT.md >/dev/null 2>&1; then
    git mv -f REPORT.md "$R"
  else
    mv -f REPORT.md "$R"
  fi
  has_hdr "$R" || { [ -s "$R" ] && put_hdr "$R"; }
elif [ -s "$R" ]; then
  put_hdr "$R"
fi
[ -s "$R" ] || build_report
git add -A
set -f
git reset -q -- $GIT_RESET_GUARD 2>/dev/null || true
set +f
if ! git diff --cached --quiet; then
  git $GIT_ID_ARGS commit -q -m "$COMMIT_MSG"
fi
git push -u origin "$BRANCH_NAME" || git push origin "$BRANCH_NAME" || true
REPORT_STEP_EOF
}

LAUNCH_SH="$LAUNCH_DIR/launch.sh"
if [ "$RUNNER" = "claude" ]; then
  {
    echo '#!/bin/sh'
    printf 'export ORG_HOST=%s\n' "$ORG_HOST"
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
elif [ "$RUNNER" = "codex" ]; then
  {
    echo '#!/bin/sh'
    printf 'export ORG_HOST=%s\n' "$ORG_HOST"
    printf 'export ORG_WORKER_FINISH=%s\n' \
      "$(sh_quote "$TMUX_BIN kill-session -t $TMUX_SESSION")"
    printf 'if [ -d %s ]; then export PATH=%s:"$PATH"; fi\n' \
      "$(sh_quote "$NODE22_BIN")" "$(sh_quote "$NODE22_BIN")"
    printf 'cd %s || exit 1\n' "$(sh_quote "$WT")"
    # A final message left by an earlier launch of this same task must not be
    # read back as this run's message.
    printf 'rm -f %s\n' "$(sh_quote "$CODEX_FINAL_MSG")"
    printf 'codex exec "$(cat TASK.md)" -C %s -s workspace-write --skip-git-repo-check --json -o %s > %s 2>&1\n' \
      "$(sh_quote "$WT")" \
      "$(sh_quote "$CODEX_FINAL_MSG")" \
      "$(sh_quote "$CODEX_TRANSCRIPT")"
    printf 'CLI_RC=$?\n'
    emit_report_commit_push codex "$CODEX_FINAL_MSG" "" "" "codex: task $TASK"
  } > "$LAUNCH_SH"
elif [ "$RUNNER" = "agy" ]; then
  {
    echo '#!/bin/sh'
    printf 'export ORG_HOST=%s\n' "$ORG_HOST"
    printf 'export ORG_WORKER_FINISH=%s\n' \
      "$(sh_quote "$TMUX_BIN kill-session -t $TMUX_SESSION")"
    printf 'if [ -d %s ]; then export PATH=%s:"$PATH"; fi\n' \
      "$(sh_quote "$NODE22_BIN")" "$(sh_quote "$NODE22_BIN")"
    printf 'cd %s || exit 1\n' "$(sh_quote "$WT")"
    # $AGY_BIN is what the probe above resolved (/root/.local/bin/agy first, so
    # Contabo runs the same binary as before); it used to be resolved and then
    # ignored in favour of the literal path.
    printf '%s -p "$(cat TASK.md)" --model gemini-3.8-flash-high --mode accept-edits --add-dir %s < /dev/null >> %s 2>&1\n' \
      "$(sh_quote "$AGY_BIN")" \
      "$(sh_quote "$WT")" \
      "$(sh_quote "$AGY_LOG")"
    printf 'CLI_RC=$?\n'
    emit_report_commit_push agy "" "$AGY_LOG" "-c user.name=agy-worker -c user.email=agy-worker@localhost" "agy: task $TASK"
  } > "$LAUNCH_SH"
fi
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

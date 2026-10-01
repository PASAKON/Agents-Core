#!/usr/bin/env bash
# sompong-supervise.sh — keep SomPong (the COO) alive in tmux session `sompong`.
#
# Run by deploy/systemd/mooniex-sompong.service (Type=simple). Contabo only: the
# launcher it starts (cxo-claude.sh --role coo) refuses every other host.
# Contract: docs/design/sompong-coo-session.md ("Singleton + spawn").
#
#   sompong-supervise.sh           the loop (systemd ExecStart)
#   sompong-supervise.sh --stop    end the session cleanly (systemd ExecStop)
#
# What the loop does:
#   1. one supervisor at a time (flock on state/sompong/supervisor.lock);
#   2. tmux session `sompong` missing, or present with no live `claude` under
#      its pane -> (re)start it with the launcher;
#   3. at most MAX_RESTARTS launches per WINDOW_S (default 5 per 10 min, the first
#      launch counts). Over budget -> wait until the oldest one ages out and say
#      so loudly in the journal;
#   4. while starting, read the pane and answer the unattended startup prompts
#      (folder trust, dev-channels warning, "Teach auto mode") — never anything
#      the supervisor cannot positively identify and verify first.
#
# bash 3.2-clean on purpose (no arrays, no associative arrays, no ${x,,}).
# Tests source this file with SOMPONG_SUPERVISE_SOURCE_ONLY=1 and fake
# tmux/ps/sleep on PATH — they never reach a real tmux or systemd.

ROOT="${SOMPONG_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SESSION="${SOMPONG_TMUX_SESSION:-sompong}"
TARGET="=$SESSION"    # tmux: a leading = is an exact session-name match, not a prefix
PANE="=$SESSION:"     # ... and pane commands (send-keys, capture-pane) need the trailing colon
                      # too: `-t =name` alone says "can't find pane" (tmux 3.4, probed 2026-10-01)
WORKDIR="${SOMPONG_WORKDIR:-/opt/MoonieXHQ/Projects/MoonieX/SomPong}"
LAUNCH="${SOMPONG_LAUNCH:-bash $ROOT/scripts/cxo-claude.sh --role coo}"
STATE_DIR="${SOMPONG_STATE_DIR:-$ROOT/state/sompong}"
RESTART_FILE="$STATE_DIR/launches"
STOP_FLAG="$STATE_DIR/stop"
MAX_RESTARTS="${SOMPONG_MAX_RESTARTS:-5}"
WINDOW_S="${SOMPONG_WINDOW_S:-600}"
POLL_S="${SOMPONG_POLL_S:-3}"
START_TIMEOUT_S="${SOMPONG_START_TIMEOUT_S:-240}"
STOP_GRACE_S="${SOMPONG_STOP_GRACE_S:-20}"
ANSWER_GAP_S="${SOMPONG_ANSWER_GAP_S:-15}"
MAX_ANSWERS="${SOMPONG_MAX_ANSWERS:-3}"
KEY_DELAY_S="${SOMPONG_KEY_DELAY_S:-1.5}"
PREFLIGHT="${SOMPONG_PREFLIGHT:-bash $ROOT/scripts/cxo-claude.sh --role coo --dry-run}"
PREFLIGHT_RETRY_S="${SOMPONG_PREFLIGHT_RETRY_S:-30}"

STOP=0
N_TEACH=0; N_TRUST=0; N_DEVCHAN=0; N_MCPJSON=0
T_TEACH=0;  T_TRUST=0;  T_DEVCHAN=0;  T_MCPJSON=0

now() { echo "${SOMPONG_NOW:-$(date +%s)}"; }
log() { printf '%s sompong-supervise: %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }
loud() { printf '%s sompong-supervise: !!! %s\n' "$(date -u +%FT%TZ)" "$*" >&2; }

# Interruptible sleep: `sleep N & wait` lets the TERM trap fire at once.
nap() { sleep "$1" & wait $! 2>/dev/null; }

# --- session state ---------------------------------------------------------

session_exists() { tmux has-session -t "$TARGET" 2>/dev/null; }

# True when a `claude` process lives anywhere under the pane's process tree.
# The launcher is a bash script that runs claude as a child, so the pane pid
# alone is not enough: a bash left behind after claude died must count as dead.
claude_alive() {
  local pp
  pp="$(tmux list-panes -t "$PANE" -F '#{pane_pid}' 2>/dev/null | head -n 1)"
  [ -n "$pp" ] || return 1
  ps -e -o pid=,ppid=,comm= 2>/dev/null | awk -v root="$pp" '
    { pid[NR] = $1; ppid[NR] = $2; comm[NR] = $3; n = NR }
    END {
      seen[root] = 1; changed = 1
      while (changed) {
        changed = 0
        for (i = 1; i <= n; i++)
          if (!(pid[i] in seen) && (ppid[i] in seen)) {
            seen[pid[i]] = 1; changed = 1
            if (comm[i] == "claude") found = 1
          }
      }
      exit(found ? 0 : 1)
    }'
}

capture() { tmux capture-pane -p -t "$PANE" 2>/dev/null; }

# --- restart budget (state in a file so it survives a supervisor restart) ---

prune_launches() {
  local now="$1"
  mkdir -p "$STATE_DIR"
  [ -f "$RESTART_FILE" ] || : > "$RESTART_FILE"
  awk -v now="$now" -v w="$WINDOW_S" '$1 ~ /^[0-9]+$/ && now - $1 < w' "$RESTART_FILE" \
    > "$RESTART_FILE.tmp" && mv "$RESTART_FILE.tmp" "$RESTART_FILE"
}

# Prints 0 when a launch is allowed now, else the seconds to wait.
backoff_wait() {
  local now="$1"
  prune_launches "$now"
  awk -v now="$now" -v w="$WINDOW_S" -v max="$MAX_RESTARTS" '
    { n++; if (n == 1) oldest = $1 }
    END { if (n >= max) print oldest + w - now + 1; else print 0 }' "$RESTART_FILE"
}

record_launch() { echo "$1" >> "$RESTART_FILE"; }

# --- the pane: classify, answer, readiness ---------------------------------

# stdin = captured pane text -> teach | devchan | trust | mcpjson | login | none.
# Each kind needs its menu structure on screen, not just a phrase, so a pane
# that merely quotes one of these sentences in chat is not answered.
classify_pane() {
  local t
  t="$(cat)"
  case "$t" in
    *"Teach auto mode"*"Enter to confirm"*) echo teach; return ;;
  esac
  case "$t" in
    *"WARNING: Loading development channels"*"I am using this for local development"*)
      echo devchan; return ;;
  esac
  case "$t" in
    *"Yes, I trust this folder"*"Enter to confirm"*) echo trust; return ;;
  esac
  case "$t" in
    *"New MCP server found in this project"*"1. Use this MCP server"*) echo mcpjson; return ;;
  esac
  case "$t" in
    *"Select login method"*|*"Please run /login"*) echo login; return ;;
  esac
  echo none
}

# stdin = pane text. Ready = no known prompt, and the footer or channel banner
# of an idle interactive session is on screen.
pane_ready() {
  local t kind
  t="$(cat)"
  kind="$(printf '%s' "$t" | classify_pane)"
  [ "$kind" = none ] || return 1
  case "$t" in
    *"shift+tab to cycle"*|*"inject directly in this session"*) return 0 ;;
  esac
  return 1
}

# Per-kind answer budget: not again within ANSWER_GAP_S, at most MAX_ANSWERS per
# start. A prompt that keeps coming back means the answer is not taking — stop
# typing into the pane and say so.
answer_allowed() {
  local kind="$1" now n t
  now="$(now)"
  case "$kind" in
    teach) n=$N_TEACH; t=$T_TEACH ;;
    trust) n=$N_TRUST; t=$T_TRUST ;;
    devchan) n=$N_DEVCHAN; t=$T_DEVCHAN ;;
    mcpjson) n=$N_MCPJSON; t=$T_MCPJSON ;;
    *) return 1 ;;
  esac
  [ "$n" -lt "$MAX_ANSWERS" ] || return 1
  [ $((now - t)) -ge "$ANSWER_GAP_S" ] || return 1
  case "$kind" in
    teach) N_TEACH=$((n + 1)); T_TEACH=$now ;;
    trust) N_TRUST=$((n + 1)); T_TRUST=$now ;;
    devchan) N_DEVCHAN=$((n + 1)); T_DEVCHAN=$now ;;
    mcpjson) N_MCPJSON=$((n + 1)); T_MCPJSON=$now ;;
  esac
  return 0
}

reset_answer_budget() { LOGIN_SAID=0;  N_TEACH=0; N_TRUST=0; N_DEVCHAN=0; N_MCPJSON=0; T_TEACH=0; T_TRUST=0; T_DEVCHAN=0; T_MCPJSON=0; }

# Look at the cursor line before pressing Enter: on the dev-channels dialog a
# stray Down lands on "2. Exit" and Enter then kills the session (seen in the
# 2026-10-01 probe). Enter is sent only when the wanted option is the selected one.
selected() { capture | grep -Eq "❯ ([0-9]+\. )?$1"; }

answer_prompt() {
  local kind="$1"
  case "$kind" in
    teach)
      # "Teach auto mode about your environment?" -> 3 (do not teach).
      tmux send-keys -t "$PANE" 3 ;;
    trust)
      # Folder-trust menu opens on "No, exit". Move to "Yes, I trust this
      # folder" only after the menu has settled, check, then confirm.
      nap "$KEY_DELAY_S"
      selected "Yes, I trust" || {
        tmux send-keys -t "$PANE" Down
        nap 1
      }
      if selected "Yes, I trust"; then
        tmux send-keys -t "$PANE" Enter
      else
        loud "trust prompt: 'Yes, I trust this folder' is not the selected line — NOT pressing Enter"
        return 1
      fi ;;
    mcpjson)
      # "New MCP server found in this project: sompong" (only when the project
      # .mcp.json is read as project scope; the launcher passes it with
      # --mcp-config, which does not ask). 1 = use this server, not the "all
      # future servers" option.
      tmux send-keys -t "$PANE" 1 ;;
    devchan)
      # "WARNING: Loading development channels": option 1 is the confirm.
      if selected "I am using this for local development"; then
        tmux send-keys -t "$PANE" Enter
      else
        loud "dev-channels dialog: option 1 is not the selected line — NOT pressing Enter"
        return 1
      fi ;;
    *) return 1 ;;
  esac
  log "answered startup prompt: $kind"
}

# One look at the pane while starting. Sets STEP = answered | ready | wait.
# (A global, not stdout: answer_allowed updates the budget counters, and a
# $(...) call would throw those updates away.)
STEP=wait
LOGIN_SAID=0
startup_step() {
  local pane kind
  STEP=wait
  pane="$(capture)"
  kind="$(printf '%s' "$pane" | classify_pane)"
  if [ "$kind" = login ]; then
    # Not something to type at: a CEO login for the SomPong unix user is needed.
    if [ "$LOGIN_SAID" = 0 ]; then
      loud "claude is asking for a LOGIN (the SomPong unix user has no Claude credentials) — the CEO must log in once as that user; not touching the pane"
      LOGIN_SAID=1
    fi
    STEP=wait; return 0
  fi
  if [ "$kind" != none ]; then
    if answer_allowed "$kind"; then
      answer_prompt "$kind"
    else
      loud "prompt '$kind' is still on screen but the answer budget ($MAX_ANSWERS per start, ${ANSWER_GAP_S}s apart) is spent — leaving the pane alone"
    fi
    STEP=answered; return 0
  fi
  if printf '%s' "$pane" | pane_ready; then
    case "$pane" in
      *"inject directly in this session"*) ;;
      *) loud "SomPong is up but the channel banner ('inject directly in this session') is not on screen — LINE/Telegram messages will NOT arrive until the dev channel loads" ;;
    esac
    STEP=ready
  fi
}

wait_ready() {
  local deadline
  deadline=$(( $(now) + START_TIMEOUT_S ))
  while [ "$(now)" -lt "$deadline" ]; do
    [ "$STOP" = 0 ] || return 3
    session_exists || return 1
    startup_step
    [ "$STEP" = ready ] && return 0
    nap 2
  done
  return 2
}

# The launcher's own check (--dry-run: host, the SomPong repo and its .mcp.json, the
# unix user, that user's claude; it starts nothing). Run first because a launcher
# that refuses inside the pane takes the pane, and its message, with it: the reason
# would never reach the journal.
preflight() {
  local out
  if out="$($PREFLIGHT 2>&1)"; then return 0; fi
  loud "launcher preflight failed (not starting): $(printf '%s' "$out" | tail -n 3 | tr '\n' ' ')"
  return 1
}

start_session() {
  reset_answer_budget
  # 9>&-: the tmux server must not inherit the supervisor's flock fd, or it would
  # hold the lock after the supervisor is gone and no new supervisor could start.
  # -c: the launcher cds to the SomPong repo itself; this only gives tmux a sane cwd.
  tmux new-session -d -s "$SESSION" -x 200 -y 50 -c "$WORKDIR" "$LAUNCH" 9>&-
}

# --- stop ------------------------------------------------------------------

stop_session() {
  mkdir -p "$STATE_DIR"
  : > "$STOP_FLAG"
  session_exists || { log "stop: no tmux session '$SESSION'"; return 0; }
  log "stop: asking claude to exit"
  tmux send-keys -t "$PANE" '/exit' Enter
  local i=0
  while [ "$i" -lt "$STOP_GRACE_S" ]; do
    session_exists || { log "stop: session ended cleanly"; return 0; }
    sleep 1; i=$((i + 1))
  done
  loud "stop: session still up after ${STOP_GRACE_S}s — killing it"
  tmux kill-session -t "$TARGET" 2>/dev/null
  return 0
}

# --- loop ------------------------------------------------------------------

main() {
  mkdir -p "$STATE_DIR"
  exec 9>"$STATE_DIR/supervisor.lock"
  if ! flock -n 9; then
    log "another supervisor holds $STATE_DIR/supervisor.lock — exiting"
    return 0
  fi
  rm -f "$STOP_FLAG"
  trap 'STOP=1' TERM INT
  log "supervising tmux session '$SESSION' (launcher: $LAUNCH)"

  local wait_s rc
  while [ "$STOP" = 0 ]; do
    [ -f "$STOP_FLAG" ] && break
    if session_exists && claude_alive; then
      # Steady state: a "Teach auto mode" prompt can still turn up later. Only the
      # gap rule applies here; the per-start budget is for the startup phase.
      if [ "$(capture | classify_pane)" = teach ]; then
        N_TEACH=0
        answer_allowed teach && answer_prompt teach
      fi
      nap "$POLL_S"
      continue
    fi

    if session_exists; then
      loud "tmux session '$SESSION' is up but no claude process is under it — removing it"
      tmux kill-session -t "$TARGET" 2>/dev/null
    fi

    wait_s="$(backoff_wait "$(now)")"
    if [ "$wait_s" -gt 0 ]; then
      loud "CRASH LOOP: $MAX_RESTARTS launches in the last ${WINDOW_S}s — waiting ${wait_s}s before the next one. Look at: tmux capture-pane -p -t $PANE ; journalctl -u mooniex-sompong"
      while [ "$wait_s" -gt 0 ] && [ "$STOP" = 0 ] && [ ! -f "$STOP_FLAG" ]; do
        nap 5; wait_s=$((wait_s - 5))
      done
      continue
    fi

    record_launch "$(now)"
    if ! preflight; then
      nap "$PREFLIGHT_RETRY_S"
      continue
    fi
    log "starting SomPong"
    if ! start_session; then
      loud "tmux new-session failed"
      nap "$POLL_S"
      continue
    fi
    wait_ready; rc=$?
    case "$rc" in
      0) log "SomPong is up" ;;
      1) loud "the session ended while starting" ;;
      2) loud "no ready prompt after ${START_TIMEOUT_S}s — leaving it; the loop restarts it if claude is gone" ;;
    esac
  done
  log "supervisor exiting"
}

if [ "${SOMPONG_SUPERVISE_SOURCE_ONLY:-}" != 1 ]; then
  case "${1:-}" in
    --stop) stop_session ;;
    "") main ;;
    *) echo "usage: sompong-supervise.sh [--stop]" >&2; exit 2 ;;
  esac
fi

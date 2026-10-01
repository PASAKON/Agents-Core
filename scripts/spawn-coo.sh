#!/usr/bin/env bash
# spawn-coo.sh — /spawn-coo: make sure SomPong (the COO) is online. Never a second one.
#
# SomPong is ONE session on Contabo (CEO 2026-10-01, docs/design/sompong-coo-session.md
# "Singleton + spawn"): tmux session `sompong`, started by mooniex-sompong.service.
# This script is the front door for the CEO and the C-levels.
#
#   on Contabo      flock; tmux `sompong` with a live claude -> say so, exit 0;
#                   else `systemctl start mooniex-sompong.service` and wait until
#                   the pane shows the prompt.
#   on Mac/winbox   refuse if a stray local coo session exists; else run this same
#                   script on Contabo over ssh (route from config/hosts.yaml);
#                   no route -> print the exact command to run, exit 2.
#
# Exit: 0 online · 1 could not (stray session, start failed, timeout, no unit) ·
#       2 no ssh route (the command to run is printed).
#
# bash 3.2-clean (runs on the Mac). Tests put fake tmux/systemctl/ssh/ps on PATH and
# set ORG_HOST; they never reach a real one.

ROOT="${SPAWN_COO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UNIT="${SPAWN_COO_UNIT:-mooniex-sompong.service}"
SC_WAIT_S="${SPAWN_COO_WAIT_S:-240}"
SC_POLL_S="${SPAWN_COO_POLL_S:-2}"
SC_LOCK_WAIT_S="${SPAWN_COO_LOCK_WAIT_S:-90}"
CONTABO_SCRIPT="/opt/MoonieXHQ/Agents/Core/scripts/spawn-coo.sh"

PY="${ORG_PYTHON:-$ROOT/.venv/bin/python}"
[ -x "$PY" ] || PY=python3

say() { printf '%s\n' "$*"; }
die() { printf '%s\n' "$*" >&2; exit "${2:-1}"; }

# --- shared definition of "alive" + "ready": the supervisor's own functions ---
SOMPONG_SUPERVISE_SOURCE_ONLY=1
export SOMPONG_SUPERVISE_SOURCE_ONLY
# shellcheck disable=SC1091
. "$ROOT/scripts/sompong-supervise.sh"
SESSION="${SOMPONG_TMUX_SESSION:-sompong}"

fmt_epoch() {  # epoch -> "YYYY-MM-DD HH:MM" Bangkok time (the CEO's clock)
  TZ=Asia/Bangkok date -d "@$1" '+%Y-%m-%d %H:%M' 2>/dev/null \
    || TZ=Asia/Bangkok date -r "$1" '+%Y-%m-%d %H:%M' 2>/dev/null \
    || echo "$1"
}

on_contabo() {
  mkdir -p "$STATE_DIR" || die "cannot create $STATE_DIR"
  exec 8>"$STATE_DIR/spawn.lock"
  flock -w "$SC_LOCK_WAIT_S" 8 || die "another /spawn-coo has held the lock for ${SC_LOCK_WAIT_S}s — try again in a minute"

  if session_exists && claude_alive; then
    local created
    created="$(tmux display-message -p -t "$PANE" '#{session_created}' 2>/dev/null)"
    say "SomPong already online (tmux $SESSION, since $(fmt_epoch "${created:-0}"))"
    return 0
  fi

  say "SomPong is not running — starting $UNIT"
  # 8>&-: systemctl must not carry the spawn lock into the unit it starts.
  systemctl start "$UNIT" 8>&- || die "systemctl start $UNIT failed — is the unit installed? (deploy/systemd/mooniex-sompong.service; the CTO installs it)"

  local waited=0
  while [ "$waited" -lt "$SC_WAIT_S" ]; do
    if session_exists && capture | pane_ready; then
      say "SomPong online (tmux $SESSION)"
      return 0
    fi
    sleep "$SC_POLL_S"
    waited=$((waited + SC_POLL_S))
  done
  die "SomPong did not show a ready prompt within ${SC_WAIT_S}s — look at: tmux capture-pane -p -t $PANE ; journalctl -u ${UNIT%.service}"
}

# A coo session on a host that is not Contabo is a stray: one session ever. Only
# tmux sessions are looked at — a lock file can be stale and would then block the
# Mac for good, and the launcher no longer starts coo anywhere but Contabo.
local_strays() {
  command -v tmux >/dev/null 2>&1 || return 0
  tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E "^($SESSION|coo-.*)$" | sed 's/^/tmux session /'
  return 0
}

off_contabo() {
  local here="$1" strays route alias root
  strays="$(local_strays)"
  if [ -n "$strays" ]; then
    printf '%s\n' "$strays" >&2
    die "A SomPong (coo) session already exists on $here. There is one SomPong, on Contabo — close the stray first (tmux kill-session -t <name>), then run /spawn-coo again."
  fi

  route="$("$PY" "$ROOT/scripts/lib/coo_host.py" route)"
  if [ -z "$route" ]; then
    say "No ssh route from $here to Contabo (config/hosts.yaml). Run this on Contabo:"
    say "  bash $CONTABO_SCRIPT"
    exit 2
  fi
  alias="${route%% *}"
  root="${route#* }"
  say "SomPong lives on Contabo — asking $alias"
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$alias" "bash $root/scripts/spawn-coo.sh"
  exit $?
}

HOST="$("$PY" "$ROOT/scripts/lib/coo_host.py" host)" \
  || die "cannot tell which machine this is (lib.config.self_host) — set ORG_HOST=mac|winbox|contabo"

if [ "$HOST" = contabo ]; then
  on_contabo
  exit $?
fi
off_contabo "$HOST"

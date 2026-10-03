#!/bin/sh
# org-tmux-adopt: keep the shared root tmux server out of any service's cgroup.
#
# Every org session on Contabo (C-levels, workers, SomPong) runs in ONE root tmux server on
# the default socket. A new server joins the cgroup of whichever process started it. On
# 2026-10-02 sompong-supervise.sh had started the server, so `systemctl restart
# mooniex-sompong.service` killed five C-level sessions and a worker in the same second.
#
# /etc/tmux.conf runs this once, when a server starts and before the first session's pane
# is forked (a run-shell without -b holds the server's command queue until it returns):
#
#   run-shell '/usr/local/sbin/org-tmux-adopt #{pid} #{socket_path} >/dev/null 2>&1 || true'
#
# It moves the server's pid into its own systemd scope, org-tmux.scope, created with
#   OOMPolicy=continue   the default, stop, makes systemd stop the WHOLE scope, so every
#                        session, when the kernel OOM killer kills any one process in it
#                        (measured on Contabo 2026-10-02 in a 64 MB test scope);
#   Delegate=yes         so a later server can join a scope that is still alive:
#                        AttachProcessesToUnit refuses a unit without delegation;
#   CollectMode=inactive-or-failed   so a failed scope does not keep the name taken.
# If org-tmux.scope exists and refuses the pid, the server gets org-tmux-<pid>.scope.
#
# Where the panes go depends on the server's environment, not on its cgroup. tmux 3.4 (the
# Ubuntu build) asks the USER bus to put each new pane in its own tmux-spawn-*.scope under
# user@0.service. A server started by a service has no user bus, so its panes stay in the
# server's cgroup, which is org-tmux.scope. A server started from an ssh login has one, so
# its panes live under user@0.service whatever happens to the server: an OOM kill of the
# user manager SIGKILLs all of them (2026-10-01: 11 claude processes), and so does user@0
# stopping after root's last logout. Moving such a server out of its login session would
# remove the one thing keeping user@0 alive, so a login-session server with a user bus is
# left where it is, and logged. Start the shared server from a service, or with
# DBUS_SESSION_BUS_ADDRESS and XDG_RUNTIME_DIR unset.
#
# A running server can be moved by hand the same way:
#
#   org-tmux-adopt "$(tmux display -p '#{pid}')" "$(tmux display -p '#{socket_path}')"
#
# Acts only on root's default socket: a server on another socket, or of another user, stays
# where it is. Always exits 0, because tmux shows a failing run-shell inside a pane, on top
# of the session that pane belongs to. Logs to the journal as org-tmux-adopt. Install:
# scripts/install-org-tmux-adopt.sh.
#
# Test overrides: ORG_TMUX_SCOPE, ORG_TMUX_SOCKET, ORG_TMUX_PROC, ORG_TMUX_WAIT (tenths
# of a second to wait for the move to land, default 100).

scope=${ORG_TMUX_SCOPE:-org-tmux.scope}
want_sock=${ORG_TMUX_SOCKET:-/tmp/tmux-0/default}
proc=${ORG_TMUX_PROC:-/proc}
tries=${ORG_TMUX_WAIT:-100}
pid=${1:-}
sock=${2:-}

log() { logger -t org-tmux-adopt -- "$*" 2>/dev/null || true; }

case $pid in
  ''|*[!0-9]*) log "no server pid given (got '$pid')"; exit 0 ;;
esac
[ "$sock" = "$want_sock" ] || exit 0

cg=$(tail -n 1 "$proc/$pid/cgroup" 2>/dev/null)
if [ -z "$cg" ]; then
  log "cannot read the cgroup of pid $pid"
  exit 0
fi
case $cg in
  */"$scope"|*/"${scope%.scope}"-[0-9]*.scope) exit 0 ;;
esac

# Only the variable names are tested; no value is read or printed.
if tr '\0' '\n' < "$proc/$pid/environ" 2>/dev/null |
    grep -qE '^(DBUS_SESSION_BUS_ADDRESS|XDG_RUNTIME_DIR)='; then
  case $cg in
    */session-*.scope)
      log "left tmux server $pid in ${cg#0::}: it has a user bus, so its panes live under user@0.service, which only its login session keeps alive"
      exit 0 ;;
  esac
  log "tmux server $pid has a user bus: its panes go to user@0.service, not $scope"
fi

manager() {
  busctl call org.freedesktop.systemd1 /org/freedesktop/systemd1 \
    org.freedesktop.systemd1.Manager "$@" >/dev/null 2>&1
}
start() {
  manager StartTransientUnit 'ssa(sv)a(sa(sv))' "$1" fail 6 \
    PIDs au 1 "$pid" \
    Description s "Shared root tmux server for every org session (scripts/org-tmux-adopt.sh)" \
    Slice s system.slice \
    Delegate b true \
    OOMPolicy s continue \
    CollectMode s inactive-or-failed 0
}
# A scope kept alive by something the previous server started is joined, not replaced.
attach() { manager AttachProcessesToUnit ssau "$scope" "" 1 "$pid"; }
# StartTransientUnit only queues a job; the pid moves when systemd runs it. Return before
# that and tmux forks the first pane into the old cgroup, where stopping the service that
# started the server kills it (measured on Contabo 2026-10-02 with a transient starter).
landed() {
  n=$tries
  while [ "$n" -gt 0 ]; do
    case $(tail -n 1 "$proc/$pid/cgroup" 2>/dev/null) in
      */"$1") return 0 ;;
    esac
    sleep 0.1
    n=$((n - 1))
  done
  return 1
}

spare=${scope%.scope}-$pid.scope
note=
if start "$scope" || attach; then
  unit=$scope
elif start "$spare"; then
  unit=$spare note=" ($scope exists and refused it)"
else
  log "could not move tmux server $pid out of ${cg#0::}"
  exit 0
fi
if landed "$unit"; then
  log "moved tmux server $pid from ${cg#0::} into $unit$note"
else
  log "systemd accepted moving tmux server $pid into $unit$note, but after $((tries / 10)) s it is still outside it"
fi
exit 0

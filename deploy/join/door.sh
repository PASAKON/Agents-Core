#!/bin/sh
# The hub's join door (Org Mesh W4.6c). CEO ruling 2026-10-01: "the door is closed by default".
#
#     door.sh open [--minutes N]               N = 1..120, default 30
#     door.sh close
#     door.sh status
#     door.sh approve --host H --fingerprint F
#
# Runs as root on Contabo, through a Run Inbox card (deploy/join/README.md has the exact
# `tools/ask_run.py create` lines); the CEO's tap on each card is the authority. A joining
# machine can reach the hub only while the door is open: org-join.service (tools/join_api.py) and
# the org-join-proxy container are both DOWN the rest of the time, and neither is enabled at boot.
#
# open     Schedules its own close FIRST (systemd-run --on-active=<N>m, unit org-join-door-close,
#          replacing any earlier one), then starts org-join.service, then the proxy compose, and
#          only then prints one line: `open until <UTC time>`. If any step fails the door is
#          closed again and the exit code is 1: it never stays open without a timer.
# close    Proxy down, service stopped, timer cancelled. Safe to run any number of times; prints
#          `closed` only after it has checked that both are really down.
# status   `closed`, or `open until <UTC time>` when the close timer exists (`open, no close timer
#          scheduled` when it does not, which means: run close).
# approve  `python -m tools.hq_join approve` for one pending host (the W4.6a F1 gate), run as
#          `secretary` with the full hub role. The endpoint's own role (org_join) cannot approve:
#          a row guard in deploy/join/org_join_role.sql forbids it on purpose. Prints the result
#          line only; no secret is ever in it.
#
# The timer must still find this file when it fires, even if the card runner deletes the copy it
# ran from, so `open` keeps a root-only copy in $ORG_JOIN_DOOR_HOME and schedules THAT one.
#
# Tests run it offline: ORG_JOIN_SYSTEMCTL, ORG_JOIN_DOCKER and ORG_JOIN_SYSTEMD_RUN replace the
# three commands (a shim on disk), ORG_JOIN_CORE / ORG_JOIN_DOOR_HOME / ORG_JOIN_PYTHON3 /
# ORG_JOIN_SETPRIV move the paths, ORG_JOIN_NOW_EPOCH fixes the clock, ORG_JOIN_SETTLE_S the wait,
# ORG_JOIN_DOOR_TEST=1 skips the is-root check. Real runs set none of them.
#
# POSIX sh (dash on Contabo, bash 3.2 on the Mac): no arrays, no `timeout`, no `date -d` unless
# `date --version` says GNU.
set -eu

CORE=${ORG_JOIN_CORE:-/opt/MoonieXHQ/Agents/Core}
SYSTEMCTL=${ORG_JOIN_SYSTEMCTL:-systemctl}
DOCKER=${ORG_JOIN_DOCKER:-docker}
SYSTEMD_RUN=${ORG_JOIN_SYSTEMD_RUN:-systemd-run}
PYTHON3=${ORG_JOIN_PYTHON3:-/usr/bin/python3}
SETPRIV=${ORG_JOIN_SETPRIV:-/usr/bin/setpriv}
DOOR_HOME=${ORG_JOIN_DOOR_HOME:-/var/lib/org-join-door}
SETTLE_S=${ORG_JOIN_SETTLE_S:-2}

SERVICE=org-join.service
TIMER=org-join-door-close
PROXY=org-join-proxy
COMPOSE="$CORE/deploy/join/docker-compose.join-proxy.yml"
DOOR_COPY="$DOOR_HOME/door.sh"
CLOSE_AT="$DOOR_HOME/close_at"
MAX_MINUTES=120
DEFAULT_MINUTES=30

die() {
    printf 'door: %s\n' "$*" >&2
    exit 1
}

usage() {
    cat >&2 <<'EOF'
usage: door.sh open [--minutes N]            (N = 1..120, default 30)
       door.sh close
       door.sh status
       door.sh approve --host H --fingerprint F
EOF
    exit 2
}

need_root() {
    [ "${ORG_JOIN_DOOR_TEST:-}" = 1 ] && return 0
    [ "$(id -u)" -eq 0 ] || die "run as root (through the Run Inbox card)"
}

now_epoch() {
    printf '%s' "${ORG_JOIN_NOW_EPOCH:-$(date -u +%s)}"
}

fmt_utc() {
    # epoch -> 2026-10-01T07:45:00Z. GNU date on Contabo, BSD date on the Mac. `-d` is never tried
    # on BSD: there it means "set the kernel's DST flag".
    if date --version >/dev/null 2>&1; then
        date -u -d "@$1" '+%Y-%m-%dT%H:%M:%SZ'
    else
        date -u -r "$1" '+%Y-%m-%dT%H:%M:%SZ'
    fi
}

proxy_up() {
    [ -n "$("$DOCKER" ps -q --filter "name=^/$PROXY\$" --filter status=running 2>/dev/null || true)" ]
}

service_up() {
    "$SYSTEMCTL" is-active --quiet "$SERVICE" >/dev/null 2>&1
}

timer_up() {
    "$SYSTEMCTL" is-active --quiet "$TIMER.timer" >/dev/null 2>&1
}

# Bring both down and check. Returns 0 only when neither is running. The exit codes of the stop
# commands are not trusted (a unit that is not installed "fails" to stop); the check at the end is.
shut() {
    if [ -f "$COMPOSE" ]; then
        "$DOCKER" compose -f "$COMPOSE" down >/dev/null 2>&1 || true
    else
        "$DOCKER" rm -f "$PROXY" >/dev/null 2>&1 || true
    fi
    "$SYSTEMCTL" stop "$SERVICE" >/dev/null 2>&1 || true
    "$SYSTEMCTL" stop "$TIMER.timer" >/dev/null 2>&1 || true
    rm -f "$CLOSE_AT"
    if service_up; then
        return 1
    fi
    if proxy_up; then
        return 1
    fi
    return 0
}

cmd_open() {
    minutes=$DEFAULT_MINUTES
    while [ $# -gt 0 ]; do
        case $1 in
            --minutes)
                [ $# -ge 2 ] || usage
                minutes=$2
                shift 2
                ;;
            --minutes=*)
                minutes=${1#--minutes=}
                shift
                ;;
            *) usage ;;
        esac
    done
    case $minutes in
        '' | *[!0-9]*) die "--minutes must be a whole number of minutes, 1 to $MAX_MINUTES" ;;
    esac
    [ "${#minutes}" -le 4 ] || die "--minutes is at most $MAX_MINUTES"
    while [ "${#minutes}" -gt 1 ] && [ "${minutes#0}" != "$minutes" ]; do
        minutes=${minutes#0}   # 007 is 7; the shell's arithmetic would read 08 as octal
    done
    [ "$minutes" -ge 1 ] || die "--minutes must be at least 1"
    [ "$minutes" -le "$MAX_MINUTES" ] || die "--minutes is at most $MAX_MINUTES (asked for $minutes)"

    need_root
    [ -f "$COMPOSE" ] || die "missing $COMPOSE (update the checkout first, see deploy/join/README.md)"

    # The copy the timer will run. $0 must be a real file: `sh -s` or a pipe has nothing to copy.
    self=$0
    case $self in /*) ;; *) self=$(pwd)/$self ;; esac
    [ -f "$self" ] && [ -r "$self" ] || die "cannot find this script's own file ($0) to schedule the close from"
    umask 077
    mkdir -p "$DOOR_HOME"
    chmod 700 "$DOOR_HOME"
    if [ "$self" != "$DOOR_COPY" ]; then
        cp "$self" "$DOOR_COPY.new"
        chmod 700 "$DOOR_COPY.new"
        mv -f "$DOOR_COPY.new" "$DOOR_COPY"
    fi

    # 1. The timer first, replacing any earlier one: from here on the door cannot be forgotten.
    "$SYSTEMCTL" stop "$TIMER.timer" >/dev/null 2>&1 || true
    "$SYSTEMCTL" reset-failed "$TIMER.service" "$TIMER.timer" >/dev/null 2>&1 || true
    if ! err=$("$SYSTEMD_RUN" "--on-active=${minutes}m" --timer-property=AccuracySec=1s \
        --unit "$TIMER" "$DOOR_COPY" close 2>&1 >/dev/null); then
        die "could not schedule the close, so nothing was opened: $err"
    fi
    close_epoch=$(( $(now_epoch) + minutes * 60 ))
    printf '%s\n' "$close_epoch" >"$CLOSE_AT"

    # 2. The endpoint, then the proxy in front of it. Any failure closes everything again.
    if ! err=$("$SYSTEMCTL" start "$SERVICE" 2>&1); then
        shut || true
        die "could not start $SERVICE, door closed again: $err"
    fi
    if ! err=$("$DOCKER" compose -f "$COMPOSE" up -d 2>&1); then
        shut || true
        die "could not start the proxy, door closed again: $err"
    fi
    # Type=simple reports "started" before the process has bound its port. Give a crash-on-start
    # (no database, no docker0) time to show, so the line printed below is true.
    [ "$SETTLE_S" -gt 0 ] && sleep "$SETTLE_S"
    if ! service_up || ! proxy_up || ! timer_up; then
        shut || true
        die "$SERVICE, the proxy or the close timer is not running after the start, door closed again (journalctl -u $SERVICE)"
    fi
    printf 'open until %s\n' "$(fmt_utc "$close_epoch")"
}

cmd_close() {
    [ $# -eq 0 ] || usage
    need_root
    if shut; then
        printf 'closed\n'
    else
        die "NOT closed: $SERVICE or the $PROXY container is still running. Run close again; if it stays up: systemctl stop $SERVICE; docker rm -f $PROXY"
    fi
}

cmd_status() {
    [ $# -eq 0 ] || usage
    svc=down
    prx=down
    service_up && svc=up
    proxy_up && prx=up
    if [ "$svc" = down ] && [ "$prx" = down ]; then
        printf 'closed\n'
        return 0
    fi
    if [ "$svc" != "$prx" ]; then
        printf 'half open: service %s, proxy %s; run close\n' "$svc" "$prx"
        return 0
    fi
    if timer_up && [ -r "$CLOSE_AT" ]; then
        epoch=$(cat "$CLOSE_AT")
        case $epoch in
            '' | *[!0-9]*) printf 'open, close time unreadable\n' ;;
            *) printf 'open until %s\n' "$(fmt_utc "$epoch")" ;;
        esac
    else
        printf 'open, no close timer scheduled; run close\n'
    fi
}

cmd_approve() {
    host=
    fp=
    while [ $# -gt 0 ]; do
        case $1 in
            --host)
                [ $# -ge 2 ] || usage
                host=$2
                shift 2
                ;;
            --fingerprint)
                [ $# -ge 2 ] || usage
                fp=$2
                shift 2
                ;;
            *) usage ;;
        esac
    done
    [ -n "$host" ] && [ -n "$fp" ] || usage
    # Shape only, so neither value can be read as an option or carry a shell character;
    # tools/hq_join.py checks the real rules (host charset, the fingerprint alphabet).
    case $host in
        -* | *[!A-Za-z0-9._-]*) die "--host has a character a host name cannot have" ;;
    esac
    [ "${#host}" -le 63 ] || die "--host is too long"
    case $fp in
        ????????) ;;
        *) die "--fingerprint is the last 8 characters of the node's age key, as read on its own screen" ;;
    esac
    case $fp in
        *[!A-Za-z0-9]*) die "--fingerprint has a character it cannot have" ;;
    esac

    need_root
    cd "$CORE"
    # Same shape as the units that run the org's other tools: the root leg reads the machine
    # identity and fetches the secrets, then setpriv drops to `secretary` before any hub code runs.
    # The [infisical run] line it prints on stderr names variables only; it is left out below so
    # the card shows the result and nothing else.
    rc=0
    out=$("$PYTHON3" "$CORE/tools/infisical_setup.py" run Agents-Core prod --as contabo -- \
        "$SETPRIV" --reuid=secretary --regid=secretary --init-groups -- \
        "$CORE/.venv/bin/python" -m tools.hq_join approve --host "$host" --fingerprint "$fp" 2>&1) || rc=$?
    printf '%s\n' "$out" | grep -v '^\[infisical run\]' | grep -v '^$' || true
    return "$rc"
}

[ $# -ge 1 ] || usage
verb=$1
shift
case $verb in
    open) cmd_open "$@" ;;
    close) cmd_close "$@" ;;
    status) cmd_status "$@" ;;
    approve) cmd_approve "$@" ;;
    *) usage ;;
esac

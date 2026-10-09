#!/usr/bin/env bash
# cookierun-health.sh — is the Cookie Run farm healthy? One headless answer.
#
#   ./scripts/cookierun-health.sh        # prints a verdict block
#   exit 0 = nothing to do (OK or PARKED)
#   exit 1 = needs attention (DOWN / STUCK / STALLING / NO-APP)
#
# Built for an hourly loop. Deliberately costs no screenshot: images never leave
# a model's context, so a recurring visual check makes every later iteration
# more expensive than the last (IRON-RULES §42). Go look at the screen only when
# this says there is something to look at.
#
# PARKED is not a fault. Cookie Run is supposed to be off while another agent
# holds the screen lease — see ALL_Rules_Winbox_PCLease.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HERE/windows/cookierun_health.py"
REMOTE_DIR='C:\mooniex\pclease'
REMOTE_PY="$REMOTE_DIR\\cookierun_health.py"
PYEXE='C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe'

[[ -f "$SRC" ]] || { echo "missing $SRC" >&2; exit 2; }

# Same one-way deploy as pc-lease.sh: only a HIGHER HEALTH_VERSION replaces the
# box copy. An md5 compare let a stale checkout put back a health check that
# calls the CEO's deliberately parked farm DOWN -- an instruction to restart it
# under him. Edit cookierun_health.py = bump HEALTH_VERSION.
# shellcheck source=lib/winbox_deploy.sh
. "$HERE/scripts/lib/winbox_deploy.sh"
winbox_deploy "$SRC" "$REMOTE_PY" HEALTH_VERSION \
  || { echo "could not deploy cookierun_health.py to $HOST" >&2; exit 2; }

ssh -o ConnectTimeout=25 "$HOST" "$PYEXE $REMOTE_PY" 2> >(tr -d '\r' >&2) | tr -d '\r'
exit "${PIPESTATUS[0]}"

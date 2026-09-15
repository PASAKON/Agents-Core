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
# holds the screen lease — see winbox-pc-lease.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HERE/windows/cookierun_health.py"
REMOTE_DIR='C:\mooniex\pclease'
REMOTE_PY="$REMOTE_DIR\\cookierun_health.py"
PYEXE='C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe'

[[ -f "$SRC" ]] || { echo "missing $SRC" >&2; exit 2; }

# Same md5-redeploy as pc-lease.sh: editing the local copy is the whole deploy.
local_md5=$(md5sum "$SRC" | cut -d' ' -f1)
remote_md5=$(ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
  "powershell -NoProfile -Command \"if (Test-Path '$REMOTE_PY') { (Get-FileHash '$REMOTE_PY' -Algorithm MD5).Hash.ToLower() } else { 'none' }\"" \
  2>/dev/null | tr -d '\r' || echo none)

if [[ "$local_md5" != "$remote_md5" ]]; then
  ssh -n "$HOST" "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
  scp -q "$SRC" "$HOST:$REMOTE_PY"
fi

ssh -o ConnectTimeout=25 "$HOST" "$PYEXE $REMOTE_PY" 2> >(tr -d '\r' >&2) | tr -d '\r'
exit "${PIPESTATUS[0]}"

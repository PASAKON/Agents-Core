#!/usr/bin/env bash
# pc-lease.sh — borrow the winbox screen from whatever is farming it.
#
#   ./scripts/pc-lease.sh status
#   ./scripts/pc-lease.sh take --who "browser_operator: harvest 4 clips" [--minutes 120] [--after-round]
#   ./scripts/pc-lease.sh give-back
#   ./scripts/pc-lease.sh extend --minutes 60
#
# You do not need to know what is running on that box or how it works. `take`
# parks it, `give-back` puts it back. If you never call `give-back`, a watchdog
# on the box puts it back when your lease expires — so the worst case is a
# wasted hour, not a wasted night.
#
# Everything real happens in windows/pc_lease.py ON the box; this is a thin
# wrapper so any machine with an `ssh winbox` alias can drive it. The script
# redeploys itself whenever the local copy changes, so there is no setup step
# to forget.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$HERE/windows/pc_lease.py"
REMOTE_DIR='C:\mooniex\pclease'
REMOTE_PY="$REMOTE_DIR\\pc_lease.py"
PYEXE='C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe'

die() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

[[ -f "$SRC" ]] || die "missing $SRC"

# Deploy only when the local file is newer than what the box has — an md5
# compare, because mtime does not survive scp the way you would hope.
# macOS ships `md5`, not GNU `md5sum` (bit a Mac CTO 2026-09-17: the wrapper
# died before `status` could even run). Both print lowercase hex.
if command -v md5sum >/dev/null 2>&1; then
  local_md5=$(md5sum "$SRC" | cut -d' ' -f1)
else
  local_md5=$(md5 -q "$SRC")
fi
remote_md5=$(ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
  "powershell -NoProfile -Command \"if (Test-Path '$REMOTE_PY') { (Get-FileHash '$REMOTE_PY' -Algorithm MD5).Hash.ToLower() } else { 'none' }\"" \
  2>/dev/null | tr -d '\r' || echo none)

if [[ "$local_md5" != "$remote_md5" ]]; then
  ssh -n "$HOST" "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
  scp -q "$SRC" "$HOST:$REMOTE_PY" || die "could not copy pc_lease.py to $HOST"
fi

# Remember locally which lease THIS machine took, so `gate` can stay quiet for
# the holder and keep the NOTE meaningful for everyone else. Only ever used to
# suppress; if the file is missing or stale the NOTE prints, which is the safe
# direction.
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/mooniex"
WHO_FILE="$STATE_DIR/pc-lease-who"

case "${1:-}" in
  take)
    # capture the --who value so the same string can identify us later
    for ((i = 1; i <= $#; i++)); do
      if [[ "${!i}" == "--who" ]]; then
        j=$((i + 1)); mkdir -p "$STATE_DIR"; printf '%s' "${!j}" > "$WHO_FILE"
      fi
    done
    ;;
  give-back) rm -f "$WHO_FILE" ;;
  gate)
    if [[ -s "$WHO_FILE" ]]; then
      set -- "$@" --as "$(cat "$WHO_FILE")"
    fi
    ;;
esac

# Re-quote every argument before it crosses ssh. "$*" loses the quoting, which
# turns --who "harvest 4 clips" into three unrecognised arguments (measured, the
# first time this ran). Keep --who ASCII too: it travels through a PowerShell
# argument layer that mangles anything else, and a mangled "?" is a wildcard in
# PowerShell paths.
remote_args=""
for a in "$@"; do
  remote_args+=" \"${a//\"/\\\"}\""
done

# Keep the two streams apart. `gate` writes its "someone else holds the screen"
# NOTE to stderr precisely so it cannot land in anything parsing stdout — and
# a plain `2>&1` here would merge them again one layer up and quietly break that
# guarantee (caught in review, 2026-09-14). ssh already keeps remote stdout and
# stderr separate; all we add is the CR strip on each.
#
# PIPESTATUS, not $?: the `tr` would otherwise swallow the remote exit code, and
# `gate` communicates entirely through its exit code.
ssh -o ConnectTimeout=20 "$HOST" "$PYEXE $REMOTE_PY$remote_args" \
  2> >(tr -d '\r' >&2) | tr -d '\r'
exit "${PIPESTATUS[0]}"

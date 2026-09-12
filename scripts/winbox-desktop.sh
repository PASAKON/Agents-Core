#!/usr/bin/env bash
# winbox-desktop.sh — reach the parts of winbox's desktop a browser cannot.
#
#   ./scripts/winbox-desktop.sh shot                  # photograph the screen
#   ./scripts/winbox-desktop.sh click <x> <y>         # click, then photograph
#   ./scripts/winbox-desktop.sh pickfile <winpath>    # fill the open FILE DIALOG
#
# Same session-1 route as winbox-line-send.sh: SSH lands in session 0, which has
# no desktop, so the work runs from a one-shot interactive scheduled task with a
# HIDDEN window — a visible console steals the foreground from whatever is being
# driven (measured 2026-09-12).
#
# `pickfile` exists because a native file picker is invisible to browser
# automation: an upload flow can be driven all the way to "choose a file" and
# then stop there forever. It is not a browser problem to solve, it is a
# different window.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
REMOTE_DIR='C:\mooniex\desktop'
TASK='mooniex-desktop'
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${DESKTOP_SHOT_DIR:-/tmp/winbox-desktop}"

ps1() { ssh -o ConnectTimeout=15 -n "$HOST" "powershell -NoProfile -Command \"$1\"" 2>&1 | tr -d '\r'; }
die() { printf '\n\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
ok()  { printf '\033[32m✓\033[0m %s\n' "$*"; }

run() {
  local args="$1"
  ssh -n "$HOST" "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
  scp -q "$HERE/windows/desktop.ps1" "$HOST:$REMOTE_DIR\\desktop.ps1"
  ssh -n "$HOST" "powershell -NoProfile -Command \"\
    \$me=[Security.Principal.WindowsIdentity]::GetCurrent().Name;\
    Unregister-ScheduledTask -TaskName '$TASK' -Confirm:\$false -ErrorAction SilentlyContinue;\
    \$a=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File $REMOTE_DIR\\desktop.ps1 $args';\
    \$p=New-ScheduledTaskPrincipal -UserId \$me -LogonType Interactive -RunLevel Limited;\
    \$s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 3);\
    Register-ScheduledTask -TaskName '$TASK' -Action \$a -Principal \$p -Settings \$s -Force | Out-Null;\
    Remove-Item '$REMOTE_DIR\\out.txt' -ErrorAction SilentlyContinue;\
    Start-ScheduledTask -TaskName '$TASK'\"" >/dev/null 2>&1
  local i r
  for i in $(seq 1 30); do
    sleep 2
    r=$(ps1 "if(Test-Path '$REMOTE_DIR\\out.txt'){Get-Content -Raw '$REMOTE_DIR\\out.txt'}" || true)
    [[ -n "${r// /}" ]] && { echo "$r"; return 0; }
  done
  die "no result from session 1 after 60s"
}

pull() {
  mkdir -p "$OUT"
  local f
  for f in "$@"; do
    scp -q "$HOST:C:/mooniex/desktop/$f.png" "$OUT/$f.png" 2>/dev/null && ok "→ $OUT/$f.png" || true
  done
}

case "${1:-shot}" in
  shot)
    run "-Mode shot" ; pull shot ;;
  click)
    x="${2:?usage: winbox-desktop.sh click <x> <y>}"; y="${3:?}"
    run "-Mode click -X $x -Y $y" ; pull click ;;
  pickfile)
    p="${2:?usage: winbox-desktop.sh pickfile '<C:\\path\\to\\file>'}"
    res=$(run "-Mode pickfile -Path '$p'"); echo "$res"
    pull pick-before pick-typed pick-after
    [[ "$res" == OK* ]] || die "pickfile failed"
    echo
    echo "Read pick-typed.png: the path must be in the File name box before Enter." ;;
  *) die "usage: $0 {shot|click <x> <y>|pickfile <winpath>}" ;;
esac

#!/usr/bin/env bash
# install_ceo_buttons.sh — put the CEO's two buttons on the winbox desktop.
#
#   ./windows/desktop/install_ceo_buttons.sh
#
# Run from the Mac, by the CTO, after review. It only copies files and finishes
# with a read-only `pc-lease.sh status`; it never touches a window, so it is
# safe while the CEO is at the PC.
#
#   ใช้คอม.cmd      "use PC"  -> ceo_button.ps1 -Mode on   -> pc_lease.py ceo-on
#   เลิกใช้คอม.cmd  "done"    -> ceo_button.ps1 -Mode off  -> pc_lease.py ceo-off
#
# Steps:
#   1. ceo_button.ps1 and both .cmd files -> C:\mooniex\pclease\ (the .cmd under
#      ASCII names: ceo_on.cmd, ceo_off.cmd).
#   2. Copy those two onto the desktop under their Thai names. The desktop is
#      asked for, not assumed: [Environment]::GetFolderPath('Desktop') — on this
#      box it is OneDrive's, C:\Users\passg\OneDrive\Desktop.
#   3. The two watchdogs that would otherwise undo a hold: cookierun_revive.py
#      (restarts a stopped farm after 10 min, minimising non-browser windows
#      such as a game after 3) and cookierun_health.py (would call a held farm
#      DOWN, which reads as an instruction to restart it).
#   4. `pc-lease.sh status`, which md5-deploys pc_lease.py — the half that knows
#      what ceo-on / ceo-off mean.
set -euo pipefail

HOST="${WINBOX_HOST:-winbox}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$HERE/windows/desktop"
REMOTE_DIR='C:\mooniex\pclease'
ON_NAME='ใช้คอม.cmd'
OFF_NAME='เลิกใช้คอม.cmd'
EXPECT_DESKTOP='C:\Users\passg\OneDrive\Desktop'

die()  { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[33m! %s\033[0m\n' "$*" >&2; }

# PowerShell over ssh as -EncodedCommand (UTF-16LE, base64). The Thai file
# names cannot cross ssh -> cmd -> powershell as text: that layer turns
# non-ASCII into "?", and "?" is a wildcard in PowerShell paths
# (docs/reports/FINDING-winbox-ascii-only.md). Base64 has nothing to mangle.
# For the same reason scp only ever writes ASCII names on the box.
winps() {
  local enc
  enc=$(printf '%s' "$1" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
  ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
    "powershell -NoProfile -NonInteractive -EncodedCommand $enc" | tr -d '\r'
}

for f in ceo_button.ps1 "$ON_NAME" "$OFF_NAME"; do
  [[ -f "$SRC/$f" ]] || die "missing $SRC/$f"
done
[[ "$(head -c3 "$SRC/ceo_button.ps1" | xxd -p)" == "efbbbf" ]] \
  || die "ceo_button.ps1 lost its UTF-8 BOM - Windows PowerShell 5.1 would read its Thai as ANSI"

# --- 1. the scripts, ASCII names only --------------------------------------
ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
  "if not exist \"$REMOTE_DIR\" mkdir \"$REMOTE_DIR\"" >/dev/null 2>&1 || true
scp -q "$SRC/ceo_button.ps1" "$HOST:$REMOTE_DIR\\ceo_button.ps1" || die "could not copy ceo_button.ps1 to $HOST"
scp -q "$SRC/$ON_NAME"  "$HOST:$REMOTE_DIR\\ceo_on.cmd"  || die "could not copy the use-PC button to $HOST"
scp -q "$SRC/$OFF_NAME" "$HOST:$REMOTE_DIR\\ceo_off.cmd" || die "could not copy the done button to $HOST"
ok "ceo_button.ps1, ceo_on.cmd, ceo_off.cmd -> $REMOTE_DIR"

# --- 2. onto the desktop, Thai names ---------------------------------------
read -r -d '' DESK_PS <<'PS' || true
$d = [Environment]::GetFolderPath('Desktop')
Copy-Item -LiteralPath 'C:\mooniex\pclease\ceo_on.cmd'  -Destination (Join-Path $d 'ใช้คอม.cmd')  -Force
Copy-Item -LiteralPath 'C:\mooniex\pclease\ceo_off.cmd' -Destination (Join-Path $d 'เลิกใช้คอม.cmd') -Force
'DESKTOP=' + $d
'ON=' + (Test-Path -LiteralPath (Join-Path $d 'ใช้คอม.cmd'))
'OFF=' + (Test-Path -LiteralPath (Join-Path $d 'เลิกใช้คอม.cmd'))
PS
desk=$(winps "$DESK_PS") || die "could not put the buttons on the desktop"
printf '%s\n' "$desk"
grep -qx 'ON=True' <<<"$desk" && grep -qx 'OFF=True' <<<"$desk" \
  || die "the buttons are not on the desktop (see the lines above)"
desk_path=$(sed -n 's/^DESKTOP=//p' <<<"$desk")
ok "both buttons on $desk_path"
# The ssh account's desktop is only the CEO's if ssh logs in as him. Say so
# rather than report a success he will never see.
[[ "$desk_path" == "$EXPECT_DESKTOP" ]] \
  || warn "expected $EXPECT_DESKTOP - check that this is the desktop the CEO looks at"

# --- 3. the watchdogs that must respect the hold ---------------------------
scp -q "$HERE/windows/cookierun_health.py" "$HOST:$REMOTE_DIR\\cookierun_health.py" \
  || die "could not copy cookierun_health.py"
ok "cookierun_health.py -> $REMOTE_DIR"

# Deploy revive to wherever its scheduled task actually runs it from — asked,
# not assumed, because a copy next to the one that runs changes nothing.
actions=$(winps "(Get-ScheduledTask -TaskName 'MooniexCookieRunRevive' -ErrorAction SilentlyContinue).Actions | ForEach-Object { \$_.Execute + ' ' + \$_.Arguments }") || actions=""
revive_path=$(grep -o -i -E '[A-Z]:\\[^" ]*cookierun_revive\.py' <<<"$actions" | head -1 || true)
if [[ -n "$revive_path" ]]; then
  scp -q "$HERE/windows/cookierun_revive.py" "$HOST:$revive_path" || die "could not copy cookierun_revive.py to $revive_path"
  ok "cookierun_revive.py -> $revive_path"
else
  warn "could not find where MooniexCookieRunRevive runs cookierun_revive.py from (task actions: ${actions:-none})."
  warn "Copy windows/cookierun_revive.py there by hand: until then revive can restart Cookie Run under the CEO's hold."
fi

# --- 4. pc_lease.py ----------------------------------------------------------
"$HERE/scripts/pc-lease.sh" status
ok "done - the CEO's buttons are live"

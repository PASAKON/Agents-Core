#!/usr/bin/env bash
# install_ceo_buttons.sh — put the CEO's two buttons on the winbox desktop.
#
#   ./windows/desktop/install_ceo_buttons.sh
#
# Run from the Mac, by the CTO, after review AND merge: it installs only a
# checkout whose HEAD is on origin/main. It copies files and finishes with a
# read-only `pc-lease.sh status`; it never touches a window, so it is safe while
# the CEO is at the PC.
#
#   ใช้คอม.cmd      "use PC"  -> ceo_button.ps1 -Mode on   -> pc_lease.py ceo-on
#   เลิกใช้คอม.cmd  "done"    -> ceo_button.ps1 -Mode off  -> pc_lease.py ceo-off
#
# The buttons go on the desktop LAST. Everything that must respect the hold is
# deployed and verified first, and any failure before that stops the install
# with no button on the desktop -- a button whose hold an old watchdog ignores is
# worse than no button, because he trusts it (review, 2026-10-09: the buttons
# used to go up in step 2 and a missing revive only warned).
#
# Steps:
#   0. Git: HEAD must be on origin/main, and nothing deployed may be uncommitted.
#   1. Find where the MooniexCookieRunRevive task runs cookierun_revive.py
#      (asked, not assumed; not found = stop). If the box copy carries no
#      REVIVE_VERSION and matches no version of it in git, it was edited on the
#      box: back it up to <path>.bak-<stamp> before replacing it.
#   2. Deploy forward-only (scripts/lib/winbox_deploy.sh), then verify the box
#      runs at least this version of each: pc_lease.py, cookierun_health.py,
#      cookierun_revive.py, desktop.ps1, line-send.ps1.
#   3. Prove the box copy of pc_lease.py is write-protected: an scp of the
#      identical bytes must FAIL. If it succeeds, wrappers older than the
#      versioned deploy could put a pc_lease.py that knows nothing of the hold
#      back on the box -- stop.
#   4. ceo_button.ps1 and both .cmd files -> C:\mooniex\pclease\ (the .cmd under
#      ASCII names: ceo_on.cmd, ceo_off.cmd).
#   5. Copy those two onto the desktop under their Thai names. The desktop is
#      asked for, not assumed: [Environment]::GetFolderPath('Desktop') -- on this
#      box it is OneDrive's, C:\Users\passg\OneDrive\Desktop.
#   6. `pc-lease.sh status`, then the rollout reminder.
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

# winbox_ps (PowerShell over ssh as -EncodedCommand), winbox_md5,
# winbox_file_version, winbox_deploy. The Thai file names cannot cross
# ssh -> cmd -> powershell as text: that layer turns non-ASCII into "?", and
# "?" is a wildcard in PowerShell paths (docs/reports/FINDING-winbox-ascii-only.md).
# Base64 has nothing to mangle. For the same reason scp only writes ASCII names.
# shellcheck source=../../scripts/lib/winbox_deploy.sh
. "$HERE/scripts/lib/winbox_deploy.sh"

md5_stdin() {
  if command -v md5sum >/dev/null 2>&1; then md5sum | cut -d' ' -f1; else md5 -q; fi
}

# "<version> <md5>" of a file on the box, or "none none".
box_version_md5() {
  local remote="$1" name="$2" probe
  probe=$(winbox_ps "\$p = '$remote'
if (-not (Test-Path -LiteralPath \$p)) { 'none none -'; exit 0 }
\$v = 0
\$m = Select-String -LiteralPath \$p -Pattern '^[# ]*${name}\\s*=\\s*(\\d+)' | Select-Object -First 1
if (\$m) { \$v = [int]\$m.Matches[0].Groups[1].Value }
\$h = (Get-FileHash -LiteralPath \$p -Algorithm MD5).Hash.ToLower()
\"\$v \$h ro\"" 2>/dev/null | tail -1) || probe=""
  printf '%s' "${probe% *}"
}

# Deploy forward-only, then insist the box really runs this version (or this
# exact file). winbox_deploy itself only warns when it does not deploy -- right
# for an everyday call, wrong for an install that is about to say "live".
deploy_and_verify() {
  local src="$1" remote="$2" name="$3" lv lmd5 got rv rmd5
  winbox_deploy "$src" "$remote" "$name" || die "could not deploy ${src##*/} to $HOST:$remote"
  lv=$(winbox_file_version "$src" "$name")
  lmd5=$(winbox_md5 "$src")
  got=$(box_version_md5 "$remote" "$name")
  read -r rv rmd5 <<<"$got"
  [[ "$rv" =~ ^[0-9]+$ ]] || die "could not read back $remote on $HOST (got '${got}')"
  if (( rv > lv )); then
    die "$HOST runs ${src##*/} $name $rv, newer than this checkout's $lv - install from an up-to-date main"
  fi
  [[ "$rmd5" == "$lmd5" ]] \
    || die "${src##*/} on $HOST is not this file ($name $rv, md5 $rmd5; ours $lv, $lmd5) - bump $name if it was edited"
  ok "${src##*/} ($name $lv) -> $remote"
}

for f in ceo_button.ps1 "$ON_NAME" "$OFF_NAME"; do
  [[ -f "$SRC/$f" ]] || die "missing $SRC/$f"
done
[[ "$(head -c3 "$SRC/ceo_button.ps1" | xxd -p)" == "efbbbf" ]] \
  || die "ceo_button.ps1 lost its UTF-8 BOM - Windows PowerShell 5.1 would read its Thai as ANSI"

# --- 0. only reviewed, merged, committed code ------------------------------
DEPLOYED=(windows/pc_lease.py windows/cookierun_health.py windows/cookierun_revive.py
          windows/desktop.ps1 windows/line-send.ps1 windows/desktop scripts/lib/winbox_deploy.sh
          scripts/pc-lease.sh)
git -C "$HERE" fetch -q origin main || die "git fetch origin main failed - cannot check what is being installed"
git -C "$HERE" merge-base --is-ancestor HEAD origin/main \
  || die "HEAD ($(git -C "$HERE" rev-parse --short HEAD)) is not on origin/main. Install only merged, pushed code: every other checkout pulls it from there."
[[ -z "$(git -C "$HERE" status --porcelain -- "${DEPLOYED[@]}")" ]] \
  || die "uncommitted changes in files this installs: $(git -C "$HERE" status --porcelain -- "${DEPLOYED[@]}" | tr '\n' ' ')"
ok "installing $(git -C "$HERE" rev-parse --short HEAD), which is on origin/main"

# --- 1. where revive runs from, and whether the box copy was edited there ----
actions=$(winbox_ps "(Get-ScheduledTask -TaskName 'MooniexCookieRunRevive' -ErrorAction SilentlyContinue).Actions | ForEach-Object { \$_.Execute + ' ' + \$_.Arguments }") || actions=""
revive_path=$(grep -o -i -E '[A-Z]:\\[^" ]*cookierun_revive\.py' <<<"$actions" | head -1 || true)
[[ -n "$revive_path" ]] || die "could not find where MooniexCookieRunRevive runs cookierun_revive.py from (task actions: ${actions:-none}). Not installing: an old revive restarts the farm under every hold."

read -r rv rmd5 <<<"$(box_version_md5 "$revive_path" REVIVE_VERSION)"
if [[ "$rv" == 0 ]]; then
  known=""
  while read -r h; do
    known+=" $(git -C "$HERE" show "$h:windows/cookierun_revive.py" 2>/dev/null | md5_stdin)"
  done < <(git -C "$HERE" log --format=%H -- windows/cookierun_revive.py)
  if [[ " $known " != *" $rmd5 "* ]]; then
    # Nothing but this installer deploys revive, so the box copy is the only
    # live one -- and this one matches nothing in git: someone edited it there.
    stamp=$(date +%Y%m%d-%H%M%S)
    bak=$(winbox_ps "\$p = '$revive_path'
Copy-Item -LiteralPath \$p -Destination (\$p + '.bak-$stamp') -Force
'BACKUP=' + (Test-Path -LiteralPath (\$p + '.bak-$stamp'))" 2>/dev/null | tail -1) || bak=""
    [[ "$bak" == "BACKUP=True" ]] || die "the box's cookierun_revive.py has changes that are not in git, and backing it up failed - not replacing it"
    warn "the box's cookierun_revive.py (md5 $rmd5) matches no version in git - kept as $revive_path.bak-$stamp. Merge what it changed into the repo by hand."
  fi
elif [[ ! "$rv" =~ ^[0-9]+$ && "$rv" != none ]]; then
  die "could not read $revive_path on $HOST (got '$rv')"
fi

# --- 2. everything that must respect the hold, verified ---------------------
deploy_and_verify "$HERE/windows/pc_lease.py"        "$REMOTE_DIR\\pc_lease.py"        LEASE_VERSION
deploy_and_verify "$HERE/windows/cookierun_health.py" "$REMOTE_DIR\\cookierun_health.py" HEALTH_VERSION
deploy_and_verify "$HERE/windows/cookierun_revive.py" "$revive_path"                    REVIVE_VERSION
deploy_and_verify "$HERE/windows/desktop.ps1"   'C:\mooniex\desktop\desktop.ps1' DESKTOP_PS1_VERSION
deploy_and_verify "$HERE/windows/line-send.ps1" 'C:\mooniex\line\line-send.ps1'  LINE_SEND_PS1_VERSION

# --- 3. the box copy must refuse a plain scp --------------------------------
if scp -q "$HERE/windows/pc_lease.py" "$HOST:$REMOTE_DIR\\pc_lease.py" 2>/dev/null; then
  die "an scp over the read-only $REMOTE_DIR\\pc_lease.py SUCCEEDED (identical bytes, so nothing changed). Old wrappers could put a hold-blind pc_lease.py back - not installing the buttons."
fi
ok "the box copy of pc_lease.py refuses a plain scp (old wrappers fail closed)"

# --- 4. the button scripts, ASCII names only --------------------------------
scp -q "$SRC/ceo_button.ps1" "$HOST:$REMOTE_DIR\\ceo_button.ps1" || die "could not copy ceo_button.ps1 to $HOST"
scp -q "$SRC/$ON_NAME"  "$HOST:$REMOTE_DIR\\ceo_on.cmd"  || die "could not copy the use-PC button to $HOST"
scp -q "$SRC/$OFF_NAME" "$HOST:$REMOTE_DIR\\ceo_off.cmd" || die "could not copy the done button to $HOST"
ok "ceo_button.ps1, ceo_on.cmd, ceo_off.cmd -> $REMOTE_DIR"

# --- 5. onto the desktop, Thai names: last ------------------------------------
read -r -d '' DESK_PS <<'PS' || true
$d = [Environment]::GetFolderPath('Desktop')
Copy-Item -LiteralPath 'C:\mooniex\pclease\ceo_on.cmd'  -Destination (Join-Path $d 'ใช้คอม.cmd')  -Force
Copy-Item -LiteralPath 'C:\mooniex\pclease\ceo_off.cmd' -Destination (Join-Path $d 'เลิกใช้คอม.cmd') -Force
'DESKTOP=' + $d
'ON=' + (Test-Path -LiteralPath (Join-Path $d 'ใช้คอม.cmd'))
'OFF=' + (Test-Path -LiteralPath (Join-Path $d 'เลิกใช้คอม.cmd'))
PS
desk=$(winbox_ps "$DESK_PS") || die "could not put the buttons on the desktop"
printf '%s\n' "$desk"
grep -qx 'ON=True' <<<"$desk" && grep -qx 'OFF=True' <<<"$desk" \
  || die "the buttons are not on the desktop (see the lines above)"
desk_path=$(sed -n 's/^DESKTOP=//p' <<<"$desk")
ok "both buttons on $desk_path"
# The ssh account's desktop is only the CEO's if ssh logs in as him. Say so
# rather than report a success he will never see.
[[ "$desk_path" == "$EXPECT_DESKTOP" ]] \
  || warn "expected $EXPECT_DESKTOP - check that this is the desktop the CEO looks at"

# --- 6. a read-only look, and what has to happen next --------------------------
"$HERE/scripts/pc-lease.sh" status
ok "done - the CEO's buttons are live"
cat <<'EOF'

Rollout -- do these now, the box is ahead of every other checkout:
  - Pull main on the Mac main tree, on Contabo (/opt/MoonieXHQ/Agents/Core) and in
    the winbox clone. Their pc-lease.sh now runs the box's newer pc_lease.py and
    says "stale" on stderr until they do.
  - Wrappers older than the versioned deploy now FAIL at the read-only box copy
    (pc-lease.sh, winbox-desktop.sh, winbox-line-send.sh, cookierun-health.sh).
    Every live worktree that drives winbox must rebase on main or stop.
  - Runners that hold a lease across stages (the Bedrock sky-scene scripts live in
    MoonieX-Bedrock) must call `pc-lease.sh gate --as "<who>"` before each stage:
    the hold refuses new screen work, it does not reach a run already going.
EOF

# winbox_deploy.sh — one-way, versioned deploy of one file onto winbox.
#
# Sourced, never run. Callers: scripts/pc-lease.sh, scripts/cookierun-health.sh,
# scripts/winbox-desktop.sh, scripts/winbox-line-send.sh,
# windows/desktop/install_ceo_buttons.sh. Needs $HOST.
#
#   winbox_deploy <local file> '<C:\remote\path>' <VERSION_NAME>
#
# The file carries one line `VERSION_NAME = <int>` (Python) or
# `# VERSION_NAME = <int>` (PowerShell, above param()). The box copy is replaced
# only when the local number is HIGHER than the box's.
#
# Why not the md5 compare every wrapper used to do: md5 says "different", not
# "newer". With ~25 worktrees plus the Contabo and winbox clones calling these
# wrappers, the first call from any stale checkout put its OLD file back on the
# box -- and an old pc_lease.py knows nothing of the CEO's hold: its gate passes,
# its take says OK, its tick minimises his windows and restarts the farm under
# him (review of the CEO-hold branch, 2026-10-09). A deploy that can go
# backwards is a hold that any ordinary call can undo.
#
# The wrappers that predate this cannot be patched, so the box copy is also kept
# READ-ONLY (re-armed on every probe). An old wrapper's scp then fails, it dies,
# and its callers fail closed: gate callers `|| exit 3`, take runners never see
# `^OK`. Only this function clears the flag, and only around a forward deploy.
#
#   local > box      deploy, re-arm read-only, md5-verify
#   local < box      run the box's newer copy, warn: your checkout is stale
#   equal, md5 diff  keep the box copy, warn: bump VERSION_NAME to deploy an edit
#
# Every warning goes to STDERR: `pc-lease.sh gate` promises an empty stdout.

# PowerShell over ssh as -EncodedCommand (UTF-16LE, base64): nothing in it has
# to survive the ssh -> cmd -> powershell quoting chain, which turns non-ASCII
# into "?" and eats `$` and `|` (docs/reports/FINDING-winbox-ascii-only.md).
winbox_ps() {
  local enc
  enc=$(printf '%s' "$1" | iconv -f UTF-8 -t UTF-16LE | base64 | tr -d '\n')
  ssh -o BatchMode=yes -o ConnectTimeout=20 -n "$HOST" \
    "powershell -NoProfile -NonInteractive -EncodedCommand $enc" | tr -d '\r'
}

# macOS ships `md5`, not GNU `md5sum` (bit a Mac CTO 2026-09-17). Both print
# lowercase hex.
winbox_md5() {
  if command -v md5sum >/dev/null 2>&1; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi
}

winbox_file_version() {
  local v
  v=$(sed -n -E "s/^[# ]*$2[[:space:]]*=[[:space:]]*([0-9]+).*/\\1/p" "$1" | head -1)
  printf '%s' "${v:-0}"
}

_winbox_deploy_warn() { printf '\033[33m! %s\033[0m\n' "$*" >&2; }
_winbox_deploy_note() { printf '%s\n' "$*" >&2; }

winbox_deploy() {
  local src="$1" remote="$2" name="$3"
  local lv lmd5 probe rv rmd5 ro dir after
  [[ -f "$src" ]] || { _winbox_deploy_warn "missing $src"; return 1; }
  lv=$(winbox_file_version "$src" "$name")
  lmd5=$(winbox_md5 "$src")

  # One round trip: the box copy's version and md5, and the read-only flag
  # re-armed while we are there. 'none none -' = no file on the box yet.
  probe=$(winbox_ps "\$p = '$remote'
if (-not (Test-Path -LiteralPath \$p)) { 'none none -'; exit 0 }
\$v = 0
\$m = Select-String -LiteralPath \$p -Pattern '^[# ]*${name}\\s*=\\s*(\\d+)' | Select-Object -First 1
if (\$m) { \$v = [int]\$m.Matches[0].Groups[1].Value }
\$h = (Get-FileHash -LiteralPath \$p -Algorithm MD5).Hash.ToLower()
\$ro = 'ro'
try { (Get-Item -LiteralPath \$p).IsReadOnly = \$true } catch { \$ro = 'rw' }
\"\$v \$h \$ro\"" 2>/dev/null | tail -1) || probe=""
  read -r rv rmd5 ro <<<"$probe"

  if [[ "$rv" != none && ! "$rv" =~ ^[0-9]+$ ]]; then
    # Box unreachable or the probe garbled. Deploying blind is how a downgrade
    # happens, so do not; the call that follows fails on its own if the box is
    # really down.
    _winbox_deploy_warn "could not read the version of $remote on $HOST - not deploying ${src##*/}"
    return 0
  fi
  if [[ "$rv" != none ]] && (( lv < rv )); then
    _winbox_deploy_warn "your ${src##*/} is $name $lv but $HOST runs $rv - running the box's newer copy. This checkout is stale: git pull / rebase on main."
    return 0
  fi
  if [[ "$rv" != none ]] && (( lv == rv )); then
    [[ "$lmd5" == "$rmd5" ]] && return 0
    _winbox_deploy_warn "${src##*/} differs from $HOST's copy at the same $name ($lv) - keeping the box copy. To deploy an edit, bump $name."
    return 0
  fi

  # Forward deploy: local is newer, or the box has no copy at all.
  dir="${remote%\\*}"
  winbox_ps "\$p = '$remote'
New-Item -ItemType Directory -Force -Path '$dir' | Out-Null
if (Test-Path -LiteralPath \$p) { (Get-Item -LiteralPath \$p).IsReadOnly = \$false }" >/dev/null 2>&1 || true
  scp -q "$src" "$HOST:$remote" || { _winbox_deploy_warn "could not copy ${src##*/} to $HOST:$remote"; return 1; }
  after=$(winbox_ps "\$p = '$remote'
(Get-Item -LiteralPath \$p).IsReadOnly = \$true
(Get-FileHash -LiteralPath \$p -Algorithm MD5).Hash.ToLower()" 2>/dev/null | tail -1) || after=""
  if [[ "$after" != "$lmd5" ]]; then
    _winbox_deploy_warn "deployed ${src##*/} to $HOST but its md5 reads back as '${after:-nothing}', not $lmd5"
    return 1
  fi
  _winbox_deploy_note "deployed ${src##*/} ($name $lv, box had $rv) to $HOST:$remote"
  return 0
}

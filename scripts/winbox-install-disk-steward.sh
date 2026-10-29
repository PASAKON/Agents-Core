#!/usr/bin/env bash
# WRITE-ONLY deliverable: execute install only from an approved Contabo card.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TICK_SHA256=995e08ba31e2c9e0b3fe663a7af688ea45df4cd75fb34c9e9fb78759960e240c
PUSH_SHA256=809f98e36a7ea0fcf056d8a9786c4dbf97e7cdd64d900a3419aa9c52fe54c7ae
REGISTER_SHA256=1e1056b82cb2191adc0d3d2013d97cd8c5d0f25dc6c11e0cbc5931afc6f27ca8
verb=${1:-}
case "$verb" in
  --print-sha)
    sha256sum "$ROOT/windows/disk-steward/"*.ps1
    sha256sum "$ROOT/windows/disk-push/disk-push.ps1"
    exit 0 ;;
  install|status|rollback) ;;
  *) echo "Usage: $0 {install|status|rollback|--print-sha}" >&2; exit 2 ;;
esac
# EncodedCommand avoids cmd.exe metacharacters and nested PowerShell quoting.
remote_ps() {
  local encoded
  encoded=$(python3 -c 'import base64,sys; print(base64.b64encode(sys.stdin.read().encode("utf-16le")).decode())')
  ssh -o BatchMode=yes winbox "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand $encoded"
}
if [[ "$verb" == status ]]; then
  remote_ps <<'PS'
$ErrorActionPreference = 'Stop'
try {
  Get-ScheduledTask -TaskName MooniexDiskSteward | Format-List TaskName,State
  Get-ScheduledTaskInfo -TaskName MooniexDiskSteward | Format-List LastRunTime,LastTaskResult,NextRunTime
} catch { Write-Error $_ -ErrorAction Continue; exit 1 }
PS
  exit 0
fi
if [[ "$verb" == rollback ]]; then
  remote_ps <<'PS'
$ErrorActionPreference = 'Stop'
try {
  $principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'FAIL CLOSED: elevated administrator session required for ProgramData' }
  $dir = 'C:\ProgramData\mooniex'
  $backup = Get-Content -Raw "$dir\disk-steward-pusher.backup"
  $backup = $backup.Trim()
  if ($backup -notmatch '^C:\\ProgramData\\mooniex\\disk-push\.ps1\.bak-[0-9-]+$' -or -not (Test-Path -LiteralPath $backup)) { throw 'Missing or invalid pusher backup' }
  Copy-Item -LiteralPath $backup -Destination "$dir\disk-push.ps1" -Force
  Remove-Item -LiteralPath "$dir\steward-status.path" -ErrorAction SilentlyContinue
  if (Get-ScheduledTask -TaskName MooniexDiskSteward -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName MooniexDiskSteward -Confirm:$false
  }
  Write-Output "Restored $backup; removed MooniexDiskSteward"
} catch { Write-Error $_ -ErrorAction Continue; exit 1 }
PS
  exit 0
fi
# Contract-derived candidates; no account name embedded in the installer.
candidates=$(python3 - "$ROOT/config/machine-contract.yaml" <<'PY'
import pathlib, sys, yaml
m = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text())['machines']['winbox']
assert m['scheduler'] == 'task_scheduler' and m['drive_leg'] == 'rclone_local', 'Deploy P1 first'
paths = [m['home']+'/mooniex/repo/Agents-Core', m['home']+'/mooniex/repo/MoonieX-Agents', m['hq']+'/agents', m['hq']+'/Agents/Core']
print(','.join("'"+p.replace("'", "''")+"'" for p in paths))
PY
)
checkout=$(remote_ps <<PS
\$ErrorActionPreference = 'Stop'
try {
  \$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not \$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'FAIL CLOSED: elevated administrator session required for ProgramData' }
  # PowerShell 5.1 turns native stderr (git progress, pip notices) into a terminating error under Stop;
  # every native call below checks \$LASTEXITCODE instead.
  \$ErrorActionPreference = 'Continue'
  \$paths = @($candidates)
  \$dedicated = \$paths[0]
  \$existing = \$paths[1]
  & git -C \$existing fetch origin main 1>\$null
  if (\$LASTEXITCODE -ne 0) { throw 'Fetch origin main failed' }
  if (Test-Path -LiteralPath \$dedicated) {
    \$top = & git -C \$dedicated rev-parse --show-toplevel 2>\$null
    if (\$LASTEXITCODE -ne 0 -or \$top.Trim().Replace('\\','/') -ine \$dedicated) { throw 'Dedicated path is not a checkout root' }
    \$dirty = & git -C \$dedicated status --porcelain --untracked-files=all 2>\$null
    if (\$LASTEXITCODE -ne 0 -or \$dirty) { throw 'Dedicated checkout is dirty; refusing update' }
    & git -C \$dedicated checkout --detach origin/main 1>\$null
  } else {
    & git -C \$existing worktree add --detach \$dedicated origin/main 1>\$null
  }
  if (\$LASTEXITCODE -ne 0) { throw 'Dedicated worktree preparation failed' }
  \$python = "\$dedicated/.venv/Scripts/python.exe"
  if (-not (Test-Path -LiteralPath \$python)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
      & py -3 -m venv "\$dedicated/.venv" 1>\$null
    } else {
      & "\$existing/.venv/Scripts/python.exe" -m venv "\$dedicated/.venv" 1>\$null
    }
    if (\$LASTEXITCODE -ne 0) { throw 'venv creation failed' }
  }
  & \$python -m pip install --quiet pyyaml *>\$null
  if (\$LASTEXITCODE -ne 0) { throw 'PyYAML installation failed' }
  Push-Location \$dedicated
  try {
    \$versions = & \$python -c "import sys, yaml; from tools import disk_steward; print('Python', sys.version.split()[0], 'PyYAML', yaml.__version__)"
    if (\$LASTEXITCODE -ne 0) { throw 'Steward import check failed' }
    [Console]::Error.WriteLine(\$versions)
  } finally { Pop-Location }
  Write-Output \$dedicated
} catch { Write-Error \$_ -ErrorAction Continue; exit 1 }
PS
)
checkout=${checkout//$'\r'/}
printf '%s  %s\n' "$TICK_SHA256" "$ROOT/windows/disk-steward/disk-steward-tick.ps1" "$REGISTER_SHA256" "$ROOT/windows/disk-steward/register-disk-steward.ps1" "$PUSH_SHA256" "$ROOT/windows/disk-push/disk-push.ps1" | sha256sum --check --status
# SCP target is also interpreted by a remote shell: fail closed on special chars.
[[ "$checkout" =~ ^[A-Za-z]:/[A-Za-z0-9_./-]+$ ]] || { echo 'Unsafe checkout path for scp' >&2; exit 2; }
remote_ps <<PS
\$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force '$checkout/windows/disk-steward' | Out-Null
PS
scp "$ROOT/windows/disk-steward/disk-steward-tick.ps1" "$ROOT/windows/disk-steward/register-disk-steward.ps1" "winbox:$checkout/windows/disk-steward/"
scp "$ROOT/windows/disk-push/disk-push.ps1" "winbox:$checkout/windows/disk-steward/disk-push.ps1"
remote_ps <<PS
\$ErrorActionPreference = 'Stop'
try {
  \$dir = '$checkout/windows/disk-steward'
  \$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
  if (-not \$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'FAIL CLOSED: elevated administrator session required for ProgramData' }
  \$pins = @{'disk-steward-tick.ps1'='$TICK_SHA256'; 'register-disk-steward.ps1'='$REGISTER_SHA256'; 'disk-push.ps1'='$PUSH_SHA256'}
  foreach (\$name in \$pins.Keys) {
    \$output = & certutil.exe -hashfile "\$dir/\$name" SHA256
    if (\$LASTEXITCODE -ne 0) { throw "certutil failed: \$name" }
    \$hashes = @(\$output | ForEach-Object { ("\$_" -replace '\\s','').ToLowerInvariant() } | Where-Object { \$_ -match '^[0-9a-f]{64}$' })
    if (\$hashes.Count -ne 1 -or \$hashes[0] -ne \$pins[\$name]) { throw "SHA256 mismatch: \$name" }
    Write-Output "Verified \$name \$(\$hashes[0])"
  }
  \$data = 'C:\ProgramData\mooniex'
  \$backup = "\$data\disk-push.ps1.bak-\$(Get-Date -Format yyyyMMdd-HHmmss-fffffff)"
  Copy-Item -LiteralPath "\$data\disk-push.ps1" -Destination \$backup -ErrorAction Stop
  Set-Content -LiteralPath "\$data\disk-steward-pusher.backup" -Value \$backup -Encoding UTF8
  Set-Content -LiteralPath "\$data\steward-status.path" -Value '$checkout/state/storage/steward-winbox.json' -Encoding UTF8
  Copy-Item -LiteralPath "\$dir/disk-push.ps1" -Destination "\$data\disk-push.ps1" -Force
  Remove-Item -LiteralPath "\$dir/disk-push.ps1"
  Write-Output "Pusher backup: \$backup"
  \$ErrorActionPreference = 'Continue'  # child stderr must not abort; exit codes are checked
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "\$dir/register-disk-steward.ps1"
  if (\$LASTEXITCODE -ne 0) { throw 'Registration failed' }
  \$lines = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "\$dir/disk-steward-tick.ps1" -DryRun 2>&1
  \$code = \$LASTEXITCODE
  \$lines | Select-Object -First 40
  exit \$code
} catch { Write-Error \$_ -ErrorAction Continue; exit 1 }
PS

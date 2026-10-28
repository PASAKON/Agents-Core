#!/usr/bin/env bash
# WRITE-ONLY deliverable: execute install only from an approved Contabo card.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
TICK_SHA256=62d3b65634b803c9a26d736d5a4b0fc1873cdc1a9e80b047e0154e374ba1e7f9
REGISTER_SHA256=1e1056b82cb2191adc0d3d2013d97cd8c5d0f25dc6c11e0cbc5931afc6f27ca8
verb=${1:-}
case "$verb" in
  --print-sha)
    sha256sum "$ROOT/windows/disk-steward/"*.ps1
    exit 0 ;;
  install|status) ;;
  *) echo "Usage: $0 {install|status|--print-sha}" >&2; exit 2 ;;
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
printf '%s  %s\n%s  %s\n' "$TICK_SHA256" "$ROOT/windows/disk-steward/disk-steward-tick.ps1" "$REGISTER_SHA256" "$ROOT/windows/disk-steward/register-disk-steward.ps1" | sha256sum --check --status
# Contract-derived candidates; no account name embedded in the installer.
candidates=$(python3 - "$ROOT/config/machine-contract.yaml" <<'PY'
import pathlib, sys, yaml
m = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text())['machines']['winbox']
assert m['scheduler'] == 'task_scheduler' and m['drive_leg'] == 'rclone_local', 'Deploy P1 first'
paths = [m['home']+'/mooniex/repo/MoonieX-Agents', m['home']+'/mooniex/repo/Agents-Core', m['hq']+'/agents', m['hq']+'/Agents/Core']
print(','.join("'"+p.replace("'", "''")+"'" for p in paths))
PY
)
checkout=$(remote_ps <<PS
\$ErrorActionPreference = 'Stop'
foreach (\$p in @($candidates)) {
  if ((Test-Path "\$p/tools/disk_steward.py") -and (Test-Path "\$p/.venv/Scripts/python.exe") -and (Test-Path "\$p/config/machine-contract.yaml")) { Write-Output \$p; exit 0 }
}
Write-Error 'No ready Agents-Core checkout; deploy P1 and its venv first'
exit 1
PS
)
checkout=${checkout//$'\r'/}
# SCP target is also interpreted by a remote shell: fail closed on special chars.
[[ "$checkout" =~ ^[A-Za-z]:/[A-Za-z0-9_./-]+$ ]] || { echo 'Unsafe checkout path for scp' >&2; exit 2; }
remote_ps <<PS
\$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force '$checkout/windows/disk-steward' | Out-Null
PS
scp "$ROOT/windows/disk-steward/disk-steward-tick.ps1" "$ROOT/windows/disk-steward/register-disk-steward.ps1" "winbox:$checkout/windows/disk-steward/"
remote_ps <<PS
\$ErrorActionPreference = 'Stop'
try {
  \$dir = '$checkout/windows/disk-steward'
  \$pins = @{'disk-steward-tick.ps1'='$TICK_SHA256'; 'register-disk-steward.ps1'='$REGISTER_SHA256'}
  foreach (\$name in \$pins.Keys) {
    \$output = & certutil.exe -hashfile "\$dir/\$name" SHA256
    if (\$LASTEXITCODE -ne 0) { throw "certutil failed: \$name" }
    \$hashes = @(\$output | ForEach-Object { ("\$_" -replace '\\s','').ToLowerInvariant() } | Where-Object { \$_ -match '^[0-9a-f]{64}$' })
    if (\$hashes.Count -ne 1 -or \$hashes[0] -ne \$pins[\$name]) { throw "SHA256 mismatch: \$name" }
    Write-Output "Verified \$name \$(\$hashes[0])"
  }
  & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "\$dir/register-disk-steward.ps1"
  if (\$LASTEXITCODE -ne 0) { throw 'Registration failed' }
  \$lines = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "\$dir/disk-steward-tick.ps1" -DryRun 2>&1
  \$code = \$LASTEXITCODE
  \$lines | Select-Object -First 40
  exit \$code
} catch { Write-Error \$_ -ErrorAction Continue; exit 1 }
PS

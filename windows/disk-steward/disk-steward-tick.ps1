# PowerShell 5.1; run from a deployed Agents-Core checkout.
param([switch] $DryRun)
$ErrorActionPreference = 'Stop'
try {
    $seed = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
    $bootstrap = Join-Path $seed '.venv\Scripts\python.exe'
    $contract = Join-Path $seed 'config\machine-contract.yaml'
    # Use the existing venv's YAML parser, never scrape YAML with a regex.
    $resolve = @'
import json, pathlib, sys, yaml
m = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))['machines']['winbox']
assert m['scheduler'] == 'task_scheduler' and m['drive_leg'] == 'rclone_local', 'P1 contract required'
paths = [pathlib.Path(m['home'])/'mooniex/repo/MoonieX-Agents', pathlib.Path(m['home'])/'mooniex/repo/Agents-Core', pathlib.Path(m['hq'])/'agents', pathlib.Path(m['hq'])/'Agents/Core']
seed = pathlib.Path(sys.argv[2]).resolve()
assert seed in [p.resolve() for p in paths], 'Checkout outside contract-derived locations'
assert (seed/'tools/disk_steward.py').is_file(), 'P1 disk_steward.py missing'
print(str(seed))
'@
    $root = & $bootstrap -I -X utf8 -c $resolve $contract $seed
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve winbox checkout from machine contract' }
    $root = "$root".Trim()
    $py = Join-Path $root '.venv\Scripts\python.exe'
    $log = Join-Path $root 'state\storage\steward-winbox.log'
    if (-not $DryRun) { New-Item -ItemType Directory -Force (Split-Path $log) | Out-Null }
    function Write-TickLine([string] $line) {
        Write-Output $line
        if (-not $DryRun) {
            if ((Test-Path -LiteralPath $log) -and (Get-Item -LiteralPath $log).Length -ge 5MB) {
                Move-Item -LiteralPath $log -Destination "$log.1" -Force -ErrorAction Stop
            }
            Add-Content -LiteralPath $log -Value $line -Encoding UTF8 -ErrorAction Stop
        }
    }
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    Set-Location -LiteralPath $root
    $tickArgs = @('tick', '--host', 'winbox')
    if ($DryRun) { $tickArgs += '--dry-run' }
    Write-TickLine "$(Get-Date -Format o) starting tick dry-run=$DryRun"
    # Continue permits native stderr to be logged on Windows PowerShell 5.1.
    $ErrorActionPreference = 'Continue'
    & $py -I -X utf8 (Join-Path $root 'tools\disk_steward.py') @tickArgs 2>&1 |
        ForEach-Object { Write-TickLine "$_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    Write-TickLine "$(Get-Date -Format o) tick exit=$code"
    exit $code
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

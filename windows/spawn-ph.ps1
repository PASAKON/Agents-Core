# Start a Project Head on winbox (org restructure M13c). PowerShell 5.1, ASCII only.
#
#   powershell -ExecutionPolicy Bypass -File windows\spawn-ph.ps1 --project <Name> [--brief <text> | --brief-file <path>] [--from-card <nonce>] [--dry-run]
#
# The PowerShell twin of scripts/spawn-ph.sh: every rule lives in tools/spawn_ph.py.
# Run it from a desktop session (a winbox C-level, or the relay-mode Console that
# runs a winbox Run card); from ssh (session 0) spawn_ph refuses, because no
# window opened there ever reaches the desktop. The Project Head opens in a new
# Windows Terminal tab; while the CEO's PC hold is on, nothing opens.
#
# Arguments go to python through windows\native-args.ps1 (M12): `& python @args`
# on PS 5.1 would split a --brief holding a double quote into extra arguments.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest = @())

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
    [Console]::Error.WriteLine("spawn-ph: no .venv at $venvPy")
    exit 2
}
. (Join-Path $PSScriptRoot 'native-args.ps1')
Push-Location $root
try {
    Invoke-NativeExe -Exe $venvPy -Arguments (@('-m', 'tools.spawn_ph') + @($Rest))
} finally {
    Pop-Location
}
exit $LASTEXITCODE

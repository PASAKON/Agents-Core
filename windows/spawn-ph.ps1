# Start a Project Head on winbox (org restructure M13c). PowerShell 5.1, ASCII only.
#
#   powershell -ExecutionPolicy Bypass -File windows\spawn-ph.ps1 --project <Name> [--brief <text> | --brief-file <path>] [--dry-run]
#
# The PowerShell twin of scripts/spawn-ph.sh: every rule lives in tools/spawn_ph.py.
# Run it from a desktop session (a winbox C-level, or the relay-mode Console that
# runs a winbox Run card); from ssh (session 0) spawn_ph refuses, because no
# window opened there ever reaches the desktop. The Project Head opens in a new
# Windows Terminal tab; while the CEO's PC hold is on, nothing opens.
#
# Run by a Run Inbox card (M13b/c): `--project P --from-card N --sha S [--brief B]`.
# The executor runs a pinned COPY of this file from a temp dir, so nothing beside
# it is trusted: it uses this host's fixed clone, only when that clone is exactly
# the card's commit with no changed tracked file and no untracked .py where Python
# would import it, loads native-args.ps1 from that clone, and runs Python isolated
# (-I, an empty pycache_prefix) (Section 2b review of #280, finding 1).
#
# Arguments go to python through windows\native-args.ps1 (M12): `& python @args`
# on PS 5.1 would split a --brief holding a double quote into extra arguments.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest = @())

$ErrorActionPreference = 'Stop'
# This host's fixed clone for a card run (never taken from the environment).
$CloneWin = 'C:\Users\passg\mooniex\repo\MoonieX-Agents'

function Stop-Spawn([string]$Why) {
    [Console]::Error.WriteLine("spawn-ph: $Why")
    exit 2
}

$card = ($Rest -contains '--from-card') -or ($Rest -contains '--sha')
if ($card) {
    $root = $CloneWin
    $i = [array]::IndexOf($Rest, '--sha')
    $sha = ''
    if ($i -ge 0 -and $i + 1 -lt $Rest.Count) { $sha = $Rest[$i + 1] }
    if ($sha -cnotmatch '^[0-9a-f]{40}$') { Stop-Spawn "a card run needs --sha <the card's 40-hex commit>" }
    # Native stderr under 'Stop' throws on PS 5.1; these git calls report by exit code.
    $ErrorActionPreference = 'Continue'
    $head = "$(& git -C $root rev-parse HEAD 2>$null)".Trim()
    if ($head -ne $sha) { Stop-Spawn "$root is at $head, the card is ${sha}: run 'git -C $root pull --ff-only' there first" }
    & git -C $root diff --quiet HEAD -- 2>$null
    if ($LASTEXITCODE -ne 0) { Stop-Spawn "$root has changed tracked files; a card runs only a clean checkout" }
    $stray = @(& git -C $root ls-files --others -- ':(glob)*.py' ':(glob)lib/**/*.py' ':(glob)tools/**/*.py' 2>$null)
    if ($LASTEXITCODE -ne 0 -or $stray.Count -gt 0) {
        Stop-Spawn "untracked Python in $root would be imported: $(($stray | Select-Object -First 3) -join ' ')"
    }
    $ErrorActionPreference = 'Stop'
} else {
    $root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$venvPy = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) { Stop-Spawn "no .venv at $venvPy" }
$nativeArgs = Join-Path $root 'windows\native-args.ps1'
if (-not (Test-Path $nativeArgs)) { Stop-Spawn "no windows\native-args.ps1 in $root (the checkout predates M12)" }
. $nativeArgs
Push-Location $root
$pyc = $null
try {
    if ($card) {
        $pyc = Join-Path ([IO.Path]::GetTempPath()) ("spawn-ph-pyc-" + [guid]::NewGuid().ToString('N'))
        $null = New-Item -ItemType Directory -Path $pyc
        $pyArgs = @('-I', '-X', "pycache_prefix=$pyc", (Join-Path $root 'tools\spawn_ph.py')) + @($Rest)
    } else {
        $pyArgs = @('-m', 'tools.spawn_ph') + @($Rest)
    }
    Invoke-NativeExe -Exe $venvPy -Arguments $pyArgs
} finally {
    Pop-Location
    if ($pyc) { Remove-Item -Recurse -Force -Path $pyc -ErrorAction SilentlyContinue }
}
exit $LASTEXITCODE

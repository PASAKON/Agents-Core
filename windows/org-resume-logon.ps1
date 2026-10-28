# org-resume-logon.ps1 - SafeRestart on winbox: bring the saved sessions back at logon.
# PowerShell 5.1, ASCII only (a non-ASCII byte in a script saved without a BOM is read
# as ANSI and fails to parse).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\org-resume-logon.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\org-resume-logon.ps1 -DryRun
#
# Run by the MooniexOrgResume task (windows\register-org-resume.ps1) at every logon of
# the interactive user, and by hand to retry. Cheap when nothing is pending: it looks for
#   <clone>\state\restart\pending-winbox.json
# and exits 0 when there is none. That marker is written by `restart_run.py prep` (via
# scripts/winbox-restart.sh) just before the reboot; `resume` removes it when every
# saved session is back.
#
# With a marker it
#   1. ignores one older than 24 h (moved aside as pending-winbox.stale-<time>.json): a
#      marker left by a prep that never rebooted must not reopen sessions days later;
#   2. waits while the CEO holds the PC (pc_lease.py ceo-check), up to -HoldWaitMin;
#   3. takes the PC lease so the night's farm cannot fight for the foreground, and gives
#      it back at the end, whatever happens;
#   4. runs `restart_run.py --host winbox resume` (one new Windows Terminal tab per saved
#      session, windows\cxo-claude.ps1 --resume <uuid>), up to -Attempts times, because
#      at logon the tailnet may not be up and a launcher that cannot reach the hub exits;
#      resume skips what is already running, so a retry only reopens what is missing;
#   5. runs `report --notify` (a Run Inbox card; winbox has no token yet, so the failure
#      is logged and does not fail the run).
# Everything is logged to <clone>\state\restart\resume-logon-<UTC time>.log.
#
# Python is run as `python -I -X utf8 tools\restart_run.py`: `-I -m tools.restart_run`
# does NOT work here (-I drops the current directory, so `tools` is not importable) and
# without -X utf8 the Thai session names are written in cp1252.
#
# -DryRun: no sleep, no lease, no log file; resume runs with --dry-run (it prints the tab
# commands and types nothing), so it may be run over ssh.
param(
    [string] $Root = '',
    [int] $DelaySec = 45,
    [int] $Attempts = 3,
    [int] $RetrySec = 60,
    [int] $HoldWaitMin = 30,
    [int] $WaitMax = 180,
    [switch] $DryRun
)

$ErrorActionPreference = 'Continue'
if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$stateDir = Join-Path $Root 'state\restart'
$marker = Join-Path $stateDir 'pending-winbox.json'
$py = Join-Path $Root '.venv\Scripts\python.exe'
$restartRun = Join-Path $Root 'tools\restart_run.py'
$leasePy = 'C:\Users\passg\cookierun-bot\.venv\Scripts\python.exe'
$leaseScript = 'C:\mooniex\pclease\pc_lease.py'
$leaseWho = 'SafeRestart winbox'

$logFile = $null
if (-not $DryRun) {
    $logFile = Join-Path $stateDir ('resume-logon-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss') + 'Z.log')
}

function Log([string] $m) {
    # Write-Host, not Write-Output: the helpers below return exit codes, and anything a
    # function writes to the pipeline would be mixed into that return value.
    $line = '{0} {1}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'), $m
    Write-Host $line
    if ($logFile) {
        try { Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8 } catch {}
    }
}

# Native stdout holds Thai; read it as UTF-8 (python is run with -X utf8). No console
# attached (rare) -> the setter throws; the log is then merely garbled, not lost.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch {}

function Invoke-Py([string[]] $PyArgs) {
    # Returns the exit code; logs the output line by line.
    $lines = & $py -I -X utf8 $restartRun --host winbox @PyArgs 2>&1
    $code = $LASTEXITCODE
    foreach ($l in @($lines)) { Log ("  " + "$l") }
    return $code
}

function Invoke-Lease([string[]] $LeaseArgs) {
    # pc_lease.py exit code, or $null when the lease tool is not on this box.
    if (-not (Test-Path -LiteralPath $leasePy) -or -not (Test-Path -LiteralPath $leaseScript)) { return $null }
    $lines = & $leasePy $leaseScript @LeaseArgs 2>&1
    $code = $LASTEXITCODE
    foreach ($l in @($lines)) { Log ("  lease: " + "$l") }
    return $code
}

function Resume-Sessions {
    # Returns the exit code of the whole run (0 = every saved session is back or nothing to do).
    if (-not $DryRun -and -not (Test-Path -LiteralPath $stateDir)) { New-Item -ItemType Directory -Path $stateDir | Out-Null }
    Log "org-resume-logon: marker $marker (clone $Root)"

    # 1. a stale marker
    $stamp = $null
    try { $stamp = [DateTimeOffset]::Parse("$((Get-Content -Raw -Encoding UTF8 -LiteralPath $marker | ConvertFrom-Json).timestamp)") } catch {}
    if (-not $stamp) { $stamp = [DateTimeOffset](Get-Item -LiteralPath $marker).LastWriteTimeUtc }
    $ageH = ([DateTimeOffset]::UtcNow - $stamp).TotalHours
    if ($ageH -gt 24) {
        Log ("marker is {0:N1} h old (more than 24 h): not resuming" -f $ageH)
        if (-not $DryRun) {
            $aside = Join-Path $stateDir ('pending-winbox.stale-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss') + 'Z.json')
            Move-Item -LiteralPath $marker -Destination $aside
            Log "marker moved to $aside"
        }
        return 0
    }
    if (-not (Test-Path -LiteralPath $py) -or -not (Test-Path -LiteralPath $restartRun)) {
        Log "missing $py or ${restartRun}: the clone is not set up"
        return 2
    }

    $tookLease = $false
    try {
        if (-not $DryRun) {
            # 2. the CEO's hold: not our screen to type on. Wait it out, then give up (marker kept).
            Log "waiting $DelaySec s for the desktop and the network"
            Start-Sleep -Seconds $DelaySec
            $deadline = (Get-Date).AddMinutes($HoldWaitMin)
            while ((Invoke-Lease @('ceo-check')) -eq 3) {
                if ((Get-Date) -gt $deadline) {
                    Log "the CEO still holds the PC after $HoldWaitMin min: resume deferred, marker kept. Run this script again when he is done."
                    return 3
                }
                Log 'the CEO holds the PC; waiting 60 s'
                Start-Sleep -Seconds 60
            }
            # 3. the lease (parks the farm). Exit 2 = refused: the CEO's hold began meanwhile.
            $took = Invoke-Lease @('take', '--who', $leaseWho, '--minutes', '45')
            if ($took -eq 2) {
                Log 'lease refused: the CEO holds the PC; resume deferred, marker kept'
                return 3
            }
            $tookLease = ($took -eq 0)
        }

        # 4. resume, retrying what is missing (resume skips sessions that are already running)
        $pyArgs = @('resume', '--wait-max', "$WaitMax")
        if ($DryRun) { $pyArgs += '--dry-run' }
        $n = $Attempts
        if ($DryRun) { $n = 1 }
        $code = 1
        for ($i = 1; $i -le $n; $i++) {
            Log "resume attempt $i of $n"
            $code = Invoke-Py $pyArgs
            Log "resume exit $code"
            if ($code -eq 0) { break }
            if ($i -lt $n) { Start-Sleep -Seconds $RetrySec }
        }

        # 5. the report; a missing Run Inbox token must not turn a good resume into a failure
        if (-not $DryRun) {
            $reportCode = Invoke-Py @('report', '--notify')
            Log "report exit $reportCode (non-zero: sessions missing, or no Run Inbox token yet)"
        }
        return $code
    }
    finally {
        if ($tookLease) {
            $back = Invoke-Lease @('give-back')
            Log "lease given back (exit $back)"
        }
    }
}

if (-not (Test-Path -LiteralPath $marker)) {
    if ($DryRun) { Write-Host "no pending restart marker at $marker; nothing to resume" }
    exit 0
}

# One instance at a time (a second logon, or a hand run while the task is still working).
$mutex = New-Object System.Threading.Mutex($false, 'Local\MooniexOrgResumeLogon')
if (-not $mutex.WaitOne(0)) {
    Write-Host 'another org-resume-logon is running; leaving it to finish'
    exit 0
}
$exitCode = 1
try { $exitCode = Resume-Sessions }
finally {
    if ($logFile) { Write-Host "log: $logFile" }
    $mutex.ReleaseMutex()
}
exit $exitCode

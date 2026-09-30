# register-org-tasks.ps1 - the CEO runs this ONCE, at the winbox desktop (W3.5).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\register-org-tasks.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\register-org-tasks.ps1 -Remove
#
# Registers one on-demand scheduled task, MooniexOrgWake, that runs
# windows\wake-request.ps1 in the logged-in desktop session (Interactive
# logon, no elevation, no trigger - it only ever runs when something runs it).
# What it does: it reads the request files under <this checkout>\state\wake\requests
# and, for each one, types the org's one-line wake marker + Enter into the
# Windows Terminal tab that request names (windows\wake.ps1, which refuses to
# send a key unless that tab is verifiably in front with keyboard focus in it).
#
# Why a person runs it: registering a task from an ssh command was refused by
# the auto-mode classifier as "Unauthorized Persistence" (2026-09-30), and that
# refusal is right - a persistent task should be a decision, made by the CEO,
# at the desktop. After it exists, the remote side never registers anything:
#   write state\wake\requests\<id>.json ; schtasks /run /tn MooniexOrgWake
#
# Run it from the checkout that runs node_agent: the task is bound to THIS
# checkout's windows\ and state\ folders. Re-running is safe (it replaces the
# task); -Remove deletes it. ASCII only.
param(
    [switch] $Remove,
    [string] $TaskName = 'MooniexOrgWake'
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Output "removed task $TaskName"
    } else {
        Write-Output "task $TaskName was not registered"
    }
    exit 0
}

if ((Get-Process -Id $PID).SessionId -eq 0) {
    Write-Error 'Run this at the desktop, not over ssh: session 0 has no desktop and the task must bind to the logged-in user.'
    exit 2
}

$runner = Join-Path $root 'windows\wake-request.ps1'
$wakePs = Join-Path $root 'windows\wake.ps1'
foreach ($p in @($runner, $wakePs)) {
    if (-not (Test-Path -LiteralPath $p)) { Write-Error "missing $p"; exit 2 }
}
foreach ($d in @('state\wake\requests', 'state\wake\results')) {
    $full = Join-Path $root $d
    if (-not (Test-Path -LiteralPath $full)) { New-Item -ItemType Directory -Path $full | Out-Null }
}

$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arg = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '" -Root "' + $root + '"'
$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
$pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $act -Principal $pri -Settings $set `
    -Description 'MoonieX org wake: types a one-line marker into a Windows Terminal tab named by a request file (windows\wake-request.ps1). On demand only.' `
    -Force | Out-Null

Write-Output "registered task $TaskName for $me (Interactive, no trigger, no elevation)"
Write-Output "  runs   : $runner"
Write-Output "  reads  : $root\state\wake\requests\*.json"
Write-Output "  remote : write a request file, then   schtasks /run /tn $TaskName"
Write-Output "  undo   : powershell -File windows\register-org-tasks.ps1 -Remove"

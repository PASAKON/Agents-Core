# register-org-resume.ps1 - run ONCE, in the console session, on the CEO's say-so (SafeRestart).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\register-org-resume.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File windows\register-org-resume.ps1 -Remove
#
# The CEO does not sit at the winbox desk: his Run card on Contabo runs
#   bash scripts/winbox-restart.sh --register-logon-task   --sha <40-hex>
#   bash scripts/winbox-restart.sh --unregister-logon-task --sha <40-hex>   (passes -Remove)
# which starts this script through a one-shot interactive task, so it runs in the console
# session. Over plain ssh (session 0) it still refuses, below.
#
# Registers one scheduled task, MooniexOrgResume, that runs windows\org-resume-logon.ps1
# at every logon of the interactive user (Interactive logon, no elevation, hidden window).
# The script does nothing unless <clone>\state\restart\pending-winbox.json exists, i.e.
# unless scripts/winbox-restart.sh saved the sessions and rebooted the box; then it
# reopens every saved Claude session in its own Windows Terminal tab.
#
# Why a card runs it: registering a task from an ssh command was refused by the
# auto-mode classifier as "Unauthorized Persistence" (2026-09-30), and that refusal is
# right - a task that survives reboots should be a decision made by the CEO, from a card
# whose text shows exactly what it does. After it exists, nothing remote registers anything.
#
# Run it from the checkout whose windows\ folder should run: the task is bound to THIS
# checkout. Re-running is safe (it replaces the task); -Remove deletes it. ASCII only.
param(
    [switch] $Remove,
    [string] $TaskName = 'MooniexOrgResume'
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

$runner = Join-Path $root 'windows\org-resume-logon.ps1'
foreach ($p in @($runner, (Join-Path $root 'tools\restart_run.py'), (Join-Path $root '.venv\Scripts\python.exe'))) {
    if (-not (Test-Path -LiteralPath $p)) { Write-Error "missing $p"; exit 2 }
}

$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arg = '-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '" -Root "' + $root + '"'
$act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
$trg = New-ScheduledTaskTrigger -AtLogOn -User $me
$pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $act -Trigger $trg -Principal $pri -Settings $set `
    -Description 'MoonieX SafeRestart: at logon, reopen the Claude sessions saved before a reboot (windows\org-resume-logon.ps1). Does nothing without state\restart\pending-winbox.json.' `
    -Force | Out-Null

$task = Get-ScheduledTask -TaskName $TaskName
Write-Output "registered task $TaskName for $me (AtLogOn, Interactive, no elevation) - state $($task.State)"
Write-Output "  runs   : $runner"
Write-Output "  reads  : $root\state\restart\pending-winbox.json"
Write-Output "  log    : $root\state\restart\resume-logon-*.log"
Write-Output "  undo   : powershell -File windows\register-org-resume.ps1 -Remove"

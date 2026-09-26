# Register + start the interactive scheduled task that opens Flow's
# CDP-debuggable Chrome on winbox's desktop (session 1). SSH lands in
# session 0, which has no desktop, so a headed browser can only be started
# this way — same mechanism as windows/spawn-worker.ps1 and
# windows/s1probe.ps1 use for claude.exe / one-shot probes.
#
#   ssh winbox powershell -NoProfile -ExecutionPolicy Bypass `
#       -File C:\mooniex\flow-chrome\flow-chrome-task-register.ps1
#
# flow-chrome-debug.cmd's own `start "" chrome.exe ...` detaches and
# returns immediately, so the 5-minute ExecutionTimeLimit below only
# bounds the task's own (already-finished) process — it never touches
# the Chrome window it launched.
param(
    [string]$TaskName = 'MooniexFlowChrome9226',
    [string]$LauncherCmd = 'C:\mooniex\flow-chrome\flow-chrome-debug.cmd'
)

$ErrorActionPreference = 'Stop'

# $env:USERDOMAIN is WORKGROUP on this box and breaks SID mapping — resolve
# the principal from the current identity instead.
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$LauncherCmd`""
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "started $TaskName as $me -> $LauncherCmd"

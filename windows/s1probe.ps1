# Run one command inside Windows session 1 (the logged-in desktop) and capture
# its output to a file. A process started from an SSH shell lives in session 0
# and never reaches the desktop, which is why codex's sandbox helper cannot
# connect its runner pipe over ssh. The only way in is a one-shot scheduled task
# with an INTERACTIVE logon type, run as the desktop user — the same mechanism
# windows/spawn-worker.ps1 uses for claude.exe.
#
#   ssh winbox powershell -NoProfile -ExecutionPolicy Bypass -File s1probe.ps1 `
#       -Cmd '<command line>' -LogPath 'C:\path\out.log'
#
# Poll LogPath from the calling side; the wrapper appends EXITCODE=<n> last.
param(
    [Parameter(Mandatory = $true)][string]$Cmd,
    [Parameter(Mandatory = $true)][string]$LogPath,
    [string]$TaskName = 'mooniex-s1probe',
    [int]$TimeLimitMinutes = 10
)

$ErrorActionPreference = 'Stop'

$dir = Split-Path $LogPath -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
Remove-Item -Path $LogPath -ErrorAction SilentlyContinue

# All quoting lives inside a wrapper .cmd so nothing crosses the schtasks
# argument boundary, where quoting is unreliable. ASCII: a .cmd turns anything
# else into '?', and '?' is a wildcard in PowerShell paths.
$wrapper = Join-Path $dir 's1probe.cmd'
$wrapperBody = @"
@echo off
$Cmd > "$LogPath" 2>&1
echo EXITCODE=%ERRORLEVEL%>> "$LogPath"
"@
Set-Content -Path $wrapper -Value $wrapperBody -Encoding ASCII

# $env:USERDOMAIN is WORKGROUP on this box and breaks SID mapping — resolve the
# principal from the current identity instead.
$me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$wrapper`""
$principal = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes $TimeLimitMinutes)

Register-ScheduledTask -TaskName $TaskName -Action $action -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "started $TaskName as $me -> $LogPath"

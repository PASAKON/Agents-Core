# Interactive token, limited privileges, no stored password; safe to invoke via SSH.
[CmdletBinding(SupportsShouldProcess)]
param([switch] $DryRun, [switch] $Uninstall)
$ErrorActionPreference = 'Stop'
$taskName = 'MooniexDiskSteward'
$runner = Join-Path $PSScriptRoot 'disk-steward-tick.ps1'
$rollback = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Uninstall'
Write-Output "Rollback: $rollback"
try {
    if ($Uninstall) {
        if ($DryRun -or $WhatIfPreference) { Write-Output "Would remove $taskName"; exit 0 }
        if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
            if ($PSCmdlet.ShouldProcess($taskName, 'Unregister')) {
                Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            }
        }
        exit 0
    }
    if (-not (Test-Path -LiteralPath $runner)) { throw "Missing $runner" }
    # Session 0 is allowed, but only when its identity matches the console user.
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $loggedOn = (Get-CimInstance Win32_ComputerSystem).UserName
    if (-not $loggedOn -or $loggedOn -ine $me) { throw 'Run as the currently logged-on console user' }
    $identity = [System.Security.SecurityElement]::Escape($me)
    $arguments = [System.Security.SecurityElement]::Escape('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '"')
    $start = (Get-Date).AddMinutes(30).ToString('yyyy-MM-ddTHH:mm:ss')
    $xml = @"
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Disk Steward: local winbox tick every 30 minutes; zero model.</Description></RegistrationInfo>
  <Triggers><TimeTrigger><Repetition><Interval>PT30M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>$start</StartBoundary><Enabled>true</Enabled></TimeTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$identity</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><Enabled>true</Enabled><ExecutionTimeLimit>PT29M</ExecutionTimeLimit></Settings>
  <Actions Context="Author"><Exec><Command>powershell.exe</Command><Arguments>$arguments</Arguments></Exec></Actions>
</Task>
"@
    if ($DryRun -or $WhatIfPreference) {
        Write-Output $xml
        exit 0
    }
    if ($PSCmdlet.ShouldProcess($taskName, 'Register or replace')) {
        Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Out-Null
    }
    Write-Output "Registered $taskName for $me (Interactive, Limited, every 30 minutes)"
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}

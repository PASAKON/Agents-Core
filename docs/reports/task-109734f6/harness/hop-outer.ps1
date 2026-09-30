param([string] $WakeScript, [string] $Marker, [string] $Method, [string] $Log, [string] $Result)
# Runs in SESSION 0 (an S4U task standing in for an ssh command). Does what
# tools/node_dispatch._one_shot_task_script does: registers a one-shot INTERACTIVE
# task that runs wake.ps1 on the console desktop, starts it, waits, unregisters.
$sess = (Get-Process -Id $PID).SessionId
$info = "outer session=$sess"
try {
    Add-Type -AssemblyName System.Windows.Forms
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $info += " screen=$($b.Width)x$($b.Height)"
} catch { $info += " screen=err" }
try {
    $tn = 'mooniex-wake-spike-hop-' + (Get-Random -Maximum 99999)
    $arg = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WakeScript`" -Title org-wake-test -Marker $Marker -Method $Method -Log `"$Log`""
    $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    Register-ScheduledTask -TaskName $tn -Action $act -Principal $pri -Settings $set -Force | Out-Null
    try {
        $startAt = Get-Date
        Start-ScheduledTask -TaskName $tn
        do {
            Start-Sleep -Milliseconds 300
            $ti = Get-ScheduledTaskInfo -TaskName $tn; $st = [string](Get-ScheduledTask -TaskName $tn).State
            $finished = ($st -ne 'Running' -and $ti.LastRunTime -ge $startAt.AddSeconds(-2))
        } while (-not $finished -and (Get-Date) -lt $startAt.AddSeconds(30))
        $info += " inner-task-result=$($ti.LastTaskResult)"
    } finally { Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue }
} catch { $info += " ERROR=$($_.Exception.Message -replace '\s+',' ')" }
Set-Content -LiteralPath $Result -Value $info -Encoding ASCII

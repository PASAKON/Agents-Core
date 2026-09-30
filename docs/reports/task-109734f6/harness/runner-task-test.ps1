param([string] $Repo)
# The production shape minus persistence: hidden Interactive one-shot task -> wake-request.ps1 -> wake.ps1.
$sp = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Join-Path $sp 'wakeroot'
$req = Join-Path $root 'state\wake\requests'; $res = Join-Path $root 'state\wake\results'
$logT = Join-Path $sp 'test-tab.log'
$runner = Join-Path $Repo 'windows\wake-request.ps1'
$results = @()
foreach ($i in 1..3) {
    $id = "task-run-$i"
    $m = 'VIATASK' + (Get-Random -Maximum 9999)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    Set-Content -LiteralPath (Join-Path $req "$id.json") -Value "{`"title`":`"-wake-test`",`"marker`":`"[New message from $m]`",`"contains`":true}" -Encoding ASCII
    $tn = 'mooniex-wake-spike-runner-' + (Get-Random -Maximum 99999)
    $act = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $runner + '" -Root "' + $root + '"')
    $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    $pri = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
    $set = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 2) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $tn -Action $act -Principal $pri -Settings $set -Force | Out-Null
    try {
        Start-ScheduledTask -TaskName $tn
        $rf = Join-Path $res "$id.json"
        do { Start-Sleep -Milliseconds 200 } while (-not (Test-Path $rf) -and $sw.Elapsed.TotalSeconds -lt 30)
    } finally { Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue }
    $got = $false
    while (-not $got -and $sw.Elapsed.TotalSeconds -lt 30) {
        if (Get-Content $logT | Select-String -SimpleMatch "[New message from $m]") { $got = $true } else { Start-Sleep -Milliseconds 150 }
    }
    $o = if (Test-Path $rf) { Get-Content $rf -Raw | ConvertFrom-Json } else { $null }
    "run {0}: result-exit={1} received={2} secs={3} :: {4}" -f $i, $(if ($o) { $o.exit } else { 'none' }), $got, [math]::Round($sw.Elapsed.TotalSeconds, 2), $(if ($o) { $o.output } else { '' })
}

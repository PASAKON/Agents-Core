Remove-Item C:\mooniex\ep04-shots\STOP,C:\mooniex\ep04-shots\STOPPED -ErrorAction SilentlyContinue
$ok = $false
try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',9224); $ok = $true; $c.Close() } catch {}
if (-not $ok) {
  $me = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $tn='MooniexChatgptChrome9224'
  Unregister-ScheduledTask -TaskName $tn -Confirm:$false -ErrorAction SilentlyContinue
  $a = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument '/c "C:\mooniex\chatgpt-chrome-debug.cmd"'
  $p = New-ScheduledTaskPrincipal -UserId $me -LogonType Interactive -RunLevel Limited
  $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
  Register-ScheduledTask -TaskName $tn -Action $a -Principal $p -Settings $s | Out-Null
  Start-ScheduledTask -TaskName $tn
  Start-Sleep 15
  Unregister-ScheduledTask -TaskName $tn -Confirm:$false
  'relaunched chrome 9224'
}
& powershell -NoProfile -ExecutionPolicy Bypass -File C:\mooniex\ep04-shots\run_shots2.ps1 -Names 'EP04-S062,EP04-S063,EP04-S064,EP04-S065,EP04-S066,EP04-S067,EP04-S068,EP04-S069,EP04-S070,EP04-S071,EP04-S072,EP04-S073,EP04-S074,EP04-S075,EP04-S076,EP04-S077,EP04-S078,EP04-S079,EP04-S080,EP04-S081,EP04-S082,EP04-S083,EP04-S084,EP04-S085,EP04-S086,EP04-S087,EP04-S088,EP04-S089,EP04-S090,EP04-S091,EP04-S092,EP04-S093,EP04-S094,EP04-S095,EP04-S096,EP04-S097,EP04-S098,EP04-S099,EP04-S100,EP04-S101,EP04-S102,EP04-S103,EP04-S104,EP04-S105,EP04-S106,EP04-S107,EP04-S108,EP04-S109,EP04-S110,EP04-S111,EP04-S112,EP04-S113,EP04-S114,EP04-S115,EP04-S116,EP04-S117,EP04-S118,EP04-S119,EP04-S120' -Tag main
& powershell -NoProfile -ExecutionPolicy Bypass -File C:\mooniex\ep04-shots\run_shots2.ps1 -Names 'EP04-S029,EP04-S039,EP04-S040' -Tag retry -Jobs jobs_retry.json
if (Test-Path C:\mooniex\ep04-shots\STOPPED) { 'STOPPED: ' + (Get-Content C:\mooniex\ep04-shots\STOPPED) } else { 'NOSTOP' }
'pngs=' + (Get-ChildItem C:\mooniex\ep04-shots\out -Filter *.png | Measure).Count

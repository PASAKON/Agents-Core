$sp = Split-Path -Parent $MyInvocation.MyCommand.Path
$wt = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
$loop = Join-Path $sp 'wake-test-loop.ps1'
$logT = Join-Path $sp 'test-tab.log'
$logD = Join-Path $sp 'decoy-tab.log'
Remove-Item $logT, $logD -ErrorAction SilentlyContinue
# Own window (named), so no tab of anyone else's is ever in the same window.
Start-Process $wt -ArgumentList @('-w', 'orgwake', 'nt', '--title', 'org-wake-test', '--suppressApplicationTitle',
    'powershell', '-NoProfile', '-NoExit', '-File', $loop, '-Log', $logT)
Start-Sleep -Seconds 3
Start-Process $wt -ArgumentList @('-w', 'orgwake', 'nt', '--title', 'org-wake-decoy', '--suppressApplicationTitle',
    'powershell', '-NoProfile', '-NoExit', '-File', $loop, '-Log', $logD)
Start-Sleep -Seconds 3
"logs:"; Get-Content $logT, $logD -ErrorAction SilentlyContinue

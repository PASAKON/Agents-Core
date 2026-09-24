# Read-only capture of winbox before the Windows reinstall (cto-6ebacd0e, 2026-09-24).
# Writes C:\mooniex\blueprint\ : NO private keys, NO tokens, NO passwords.
$ErrorActionPreference = 'Continue'
$B = 'C:\mooniex\blueprint'
New-Item -ItemType Directory -Force -Path $B, "$B\tasks" | Out-Null
# 1. apps
winget export -o "$B\winget.json" --accept-source-agreements --include-versions 2>&1 | Out-File "$B\winget-export.log"
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*, HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*, HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue |
  Where-Object DisplayName | Select-Object DisplayName, DisplayVersion, Publisher, InstallLocation | Sort-Object DisplayName |
  Export-Csv "$B\installed-programs.csv" -NoTypeInformation -Encoding UTF8
# 2. scheduled tasks (ours) as XML, re-importable with schtasks /Create /XML
Get-ScheduledTask | Where-Object { $_.TaskPath -eq '\' -and $_.TaskName -notmatch '^(Microsoft|MicrosoftEdge|OneDrive|GoogleUpdate|NvTm|NvDriver|NVIDIA|Adobe|CreateExplorerShellUnelevatedTask|npcapwatchdog|BlueStacks)' } | ForEach-Object {
  Export-ScheduledTask -TaskName $_.TaskName | Out-File -Encoding Unicode ("$B\tasks\" + ($_.TaskName -replace '[\\/:*?"<>|]', '_') + '.xml')
}
# 3. services + startup
Get-Service | Where-Object { $_.StartType -eq 'Automatic' } | Select-Object Name, DisplayName, Status | Export-Csv "$B\services-auto.csv" -NoTypeInformation
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Export-Csv "$B\startup.csv" -NoTypeInformation
# 4. ssh: config files + PUBLIC keys only
Copy-Item C:\ProgramData\ssh\sshd_config "$B\sshd_config" -ErrorAction SilentlyContinue
Copy-Item C:\ProgramData\ssh\administrators_authorized_keys "$B\administrators_authorized_keys.pub-list" -ErrorAction SilentlyContinue
Copy-Item "$env:USERPROFILE\.ssh\authorized_keys" "$B\user_authorized_keys.pub-list" -ErrorAction SilentlyContinue
Copy-Item "$env:USERPROFILE\.ssh\config" "$B\user_ssh_config" -ErrorAction SilentlyContinue
Get-ChildItem "$env:USERPROFILE\.ssh\*.pub" -ErrorAction SilentlyContinue | ForEach-Object { Copy-Item $_.FullName "$B\$($_.Name)" }
Get-ChildItem C:\ProgramData\ssh\ssh_host_*_key.pub -ErrorAction SilentlyContinue | ForEach-Object { Copy-Item $_.FullName "$B\$($_.Name)" }
# 5. machine + user settings the bot depends on
$o = [ordered]@{}
$o.computer = $env:COMPUTERNAME; $o.user = $env:USERNAME; $o.profile = $env:USERPROFILE
$o.os = (Get-CimInstance Win32_OperatingSystem | ForEach-Object { $_.Caption + ' ' + $_.Version + ' build ' + $_.BuildNumber })
$o.local_user = (Get-LocalUser | Where-Object Enabled | Select-Object Name, PrincipalSource | ConvertTo-Json -Compress)
$o.admins = (Get-LocalGroupMember Administrators | ForEach-Object Name) -join ', '
$o.display = (Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + ' ' + $_.CurrentHorizontalResolution + 'x' + $_.CurrentVerticalResolution }) -join ' | '
$o.dpi_scale = (Get-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' -ErrorAction SilentlyContinue).AppliedDPI
$o.power_ac_standby_min = (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'Current AC Power Setting Index').ToString()
$o.power_ac_display_min = (powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String 'Current AC Power Setting Index').ToString()
$o.defender_exclusions = ((Get-MpPreference).ExclusionPath -join '; ')
$o.tailscale = (& 'C:\Program Files\Tailscale\tailscale.exe' status --self --peers=false 2>&1 | Out-String).Trim()
$o.tailscale_prefs = (& 'C:\Program Files\Tailscale\tailscale.exe' debug prefs 2>&1 | Select-String 'RunSSH|Hostname|ShieldsUp' | Out-String).Trim()
$o.firewall_rules = (Get-NetFirewallRule -Enabled True -Direction Inbound | Where-Object { $_.DisplayName -match 'ssh|8792|8794|mooniex|cookie|python|tailscale' } | ForEach-Object DisplayName) -join '; '
$o.env_user = ([Environment]::GetEnvironmentVariables('User').Keys | Where-Object { $_ -notmatch 'KEY|TOKEN|SECRET|PASS' }) -join ', '
$o.path_user = [Environment]::GetEnvironmentVariable('Path', 'User')
$o.git_config = (git config --global --list 2>&1 | Where-Object { $_ -notmatch 'token|password|credential' } | Out-String).Trim()
$o.gh_auth = (gh auth status 2>&1 | Select-String 'Logged in' | Out-String).Trim()
$o.python = (& py -0p 2>&1 | Out-String).Trim()
$o | ConvertTo-Json -Depth 3 | Out-File -Encoding UTF8 "$B\machine.json"
# 6. python packages of the bot venv
& C:\Users\UsEr\cookierun-bot\.venv\Scripts\python.exe -m pip freeze | Out-File -Encoding UTF8 "$B\cookierun-bot-venv-freeze.txt"
# 7. BlueStacks instance settings (no account data)
Select-String -Path 'C:\ProgramData\BlueStacks_nxt\bluestacks.conf' -Pattern 'Tiramisu64\.' -ErrorAction SilentlyContinue | ForEach-Object Line |
  Where-Object { $_ -notmatch 'token|guid|email|password' } | Out-File -Encoding UTF8 "$B\bluestacks-instance.conf"
# 8. git repos under the user profile / C:\mooniex: remote, branch, dirty count
Get-ChildItem C:\Users\UsEr, C:\Users\UsEr\projects, C:\mooniex -Directory -ErrorAction SilentlyContinue | Where-Object { Test-Path (Join-Path $_.FullName '.git') } | ForEach-Object {
  $d = $_.FullName
  [pscustomobject]@{ repo = $d; remote = (git -C $d remote get-url origin 2>$null); branch = (git -C $d branch --show-current 2>$null);
    dirty = ((git -C $d status --porcelain 2>$null) | Measure-Object).Count; ahead = (git -C $d rev-list --count '@{u}..HEAD' 2>$null) }
} | Export-Csv "$B\git-repos.csv" -NoTypeInformation
"done $(Get-Date -Format s)" | Out-File "$B\DONE.txt"

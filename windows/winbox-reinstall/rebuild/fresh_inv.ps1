$ErrorActionPreference='Continue'
"free: {0:N1} GB of {1:N0} GB" -f ((Get-PSDrive C).Free/1GB), ((Get-PSDrive C).Used/1GB + (Get-PSDrive C).Free/1GB)
"admin: " + (([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrators'))
"winget: " + (& winget --version 2>&1)
foreach ($c in 'python','py','git','node','npm','rclone','claude','gh','ffmpeg','code') { $w = Get-Command $c -ErrorAction SilentlyContinue; "cmd $c : " + $(if ($w) { $w.Source } else { '-' }) }
"tailscale RunSSH: " + ((& 'C:\Program Files\Tailscale\tailscale.exe' debug prefs 2>&1 | Select-String 'RunSSH' | Out-String).Trim())
"sshd admin keys ACL: " + ((icacls C:\ProgramData\ssh\administrators_authorized_keys 2>&1 | Out-String).Trim() -replace '\s+',' ')
"power before: standby=" + ((powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'Current AC').ToString().Trim()) + " monitor=" + ((powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String 'Current AC').ToString().Trim())
powercfg /change monitor-timeout-ac 0; powercfg /change hibernate-timeout-ac 0; powercfg /change standby-timeout-ac 0
"power after: monitor=" + ((powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE | Select-String 'Current AC').ToString().Trim())
if (-not (Test-Path 'C:\Users\UsEr')) { cmd /c mklink /J C:\Users\UsEr C:\Users\passg | Out-Null }
"junction: " + ((Get-Item 'C:\Users\UsEr' -ErrorAction SilentlyContinue).LinkType) + " -> " + ((Get-Item 'C:\Users\UsEr' -ErrorAction SilentlyContinue).Target)
"autologon: " + ((Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon').AutoAdminLogon) + " user=" + ((Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon').DefaultUserName)
"display: " + ((Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + ' ' + $_.CurrentHorizontalResolution + 'x' + $_.CurrentVerticalResolution }) -join ' | ')
"tz: " + (tzutil /g)

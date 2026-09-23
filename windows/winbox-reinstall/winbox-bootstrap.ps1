# winbox-bootstrap.ps1 -- first 10 minutes on the fresh Windows (cto-6ebacd0e, 2026-09-24).
# Run ONCE as Administrator on the new install, logged in as UsEr. Idempotent: safe to run again.
# It opens the door for remote work and nothing else: OpenSSH server + the two org public keys,
# firewall, Tailscale, never sleep, Bangkok time, auto-logon. No secrets are inside this file.
#   -Check   = report what it would do, change nothing (used to test it on the old machine).
param([switch]$Check)
$ErrorActionPreference = 'Continue'
$KEYS = @'
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB4VBzzKuONJm8CeV7YGhRINHmbyE6sCxMml5aT+9S2s mac-to-desktop-3nqb2qo
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExwb04ClBZR01s9ZGnbBKTk+TYaIFItBovKQspMp1Ii mooniex-contabo->winbox
'@
function Say($m) { Write-Host ("[{0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Step($name, [scriptblock]$do, [scriptblock]$verify) {
    if ($Check) { $ok = & $verify; Say ("CHECK {0}: {1}" -f $name, $(if ($ok) { 'already OK' } else { 'would do' })); return }
    if (& $verify) { Say "SKIP  $name (already done)"; return }
    Say "DO    $name"
    try { & $do } catch { Say "ERROR $name : $($_.Exception.Message)" }
    if (& $verify) { Say "OK    $name" } else { Say "FAILED $name  <-- tell the CTO this line" }
}
# 0. admin?
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrators')
if (-not $isAdmin -and -not $Check) { Say "Not running as Administrator. Right-click the file -> Run with PowerShell as Administrator."; Read-Host 'Press Enter to close'; exit 1 }
Say ("user={0} computer={1} profile={2}" -f $env:USERNAME, $env:COMPUTERNAME, $env:USERPROFILE)
if ($env:USERNAME -ne 'UsEr') { Say "WARNING: the account is '$($env:USERNAME)', not 'UsEr'. Every org path expects C:\Users\UsEr." }

# 1. OpenSSH server
Step 'OpenSSH Server capability' {
    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
} { (Get-WindowsCapability -Online -Name 'OpenSSH.Server*' | Where-Object State -eq 'Installed') -ne $null }

Step 'sshd service running + automatic' {
    Set-Service sshd -StartupType Automatic; Start-Service sshd
} { $s = Get-Service sshd -ErrorAction SilentlyContinue; $s -and $s.Status -eq 'Running' -and $s.StartType -eq 'Automatic' }

# 2. the org's public keys, in BOTH places Windows sshd may read (admin file + user file), with the ACL sshd insists on
$adminKeys = 'C:\ProgramData\ssh\administrators_authorized_keys'
$userKeys = Join-Path $env:USERPROFILE '.ssh\authorized_keys'
Step 'authorized keys (admin file)' {
    Set-Content -Path $adminKeys -Value $KEYS -Encoding ascii
    icacls $adminKeys /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F' | Out-Null
} { (Test-Path $adminKeys) -and ((Get-Content $adminKeys -Raw) -match 'mooniex-contabo') -and ((icacls $adminKeys) -notmatch 'Users:') }
Step 'authorized keys (user file)' {
    New-Item -ItemType Directory -Force -Path (Split-Path $userKeys) | Out-Null
    Set-Content -Path $userKeys -Value $KEYS -Encoding ascii
} { (Test-Path $userKeys) -and ((Get-Content $userKeys -Raw) -match 'mooniex-contabo') }

# 3. firewall for port 22 (the capability normally adds it; make sure)
Step 'firewall rule sshd 22/tcp' {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH SSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
} { (Get-NetFirewallRule -Enabled True -Direction Inbound -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'OpenSSH' }) -ne $null }

# 4. Tailscale (the tunnel Contabo and the Mac reach this box through)
$ts = 'C:\Program Files\Tailscale\tailscale.exe'
Step 'Tailscale installed' {
    winget install --id Tailscale.Tailscale --exact --silent --accept-source-agreements --accept-package-agreements | Out-Null
} { Test-Path $ts }
Step 'Tailscale: OpenSSH keeps port 22 (Tailscale SSH off)' {
    & $ts set --ssh=false 2>&1 | Out-Null
} { (Test-Path $ts) -and ((& $ts debug prefs 2>&1 | Out-String) -match '"RunSSH":\s*false') }

# 5. never sleep, never blank; Bangkok time
Step 'power: never sleep on AC' {
    powercfg /change standby-timeout-ac 0; powercfg /change hibernate-timeout-ac 0; powercfg /change monitor-timeout-ac 0
} { ((powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String 'Current AC Power Setting Index').ToString() -match '0x00000000') }
Step 'time zone Asia/Bangkok' { tzutil /s 'SE Asia Standard Time' } { (tzutil /g) -eq 'SE Asia Standard Time' }

# 6. auto-logon (CEO decision 2026-09-24: "ควรเป็นแบบนั้น"). Sysinternals Autologon stores the
#    password as an LSA secret instead of plain text in the registry.
Step 'auto-logon for UsEr' {
    $exe = Join-Path $env:TEMP 'Autologon64.exe'
    Invoke-WebRequest -Uri 'https://live.sysinternals.com/Autologon64.exe' -OutFile $exe -UseBasicParsing
    $pw = Read-Host -AsSecureString 'Windows password of UsEr (for auto-logon; stored as an LSA secret, not shown)'
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($pw))
    & $exe /accepteula $env:USERNAME $env:COMPUTERNAME $plain | Out-Null
    $plain = $null
} { (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -ErrorAction SilentlyContinue).AutoAdminLogon -eq '1' }

# 7. join the tailnet -- the ONE click the CEO makes: a browser opens, press "Connect"/"Sign in"
if (-not $Check) {
    Say 'Tailscale login: a browser window opens now. Sign in as pass.gob1@gmail.com and approve this machine.'
    Start-Process -FilePath $ts -ArgumentList 'up' -Wait -NoNewWindow
}
$ip = if (Test-Path $ts) { (& $ts ip -4 2>$null | Select-Object -First 1) } else { '(tailscale not installed)' }
Say '------------------------------------------------------------'
Say ("READY  tailscale ip = {0}   user = {1}   sshd = {2}" -f $ip, $env:USERNAME, (Get-Service sshd -ErrorAction SilentlyContinue).Status)
Say 'Tell the CTO: READY + this IP. He connects from Contabo and takes it from here.'
Say '------------------------------------------------------------'
if (-not $Check) { Read-Host 'Press Enter to close' }

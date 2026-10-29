# Measure winbox's disk and report it to the disk hub. Windows PowerShell 5.1.
# Runs as a SYSTEM scheduled task every 10 minutes (install-winbox.ps1) — the minimum.
# Measuring is local; it REPORTS only when the hub's schedule says it is due, or when
# C: moved by at least force_delta_bytes since the last report (state: disk-push.state.json).
param([switch]$Force)
# Token: C:\ProgramData\mooniex\disk-push.token (one line, ACL SYSTEM+Administrators).
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$dir   = 'C:\ProgramData\mooniex'
$token = (Get-Content -Raw "$dir\disk-push.token").Trim()
$url   = 'https://webhook.mooniex.com/disk'
if (Test-Path "$dir\disk-hub.url") { $url = (Get-Content -Raw "$dir\disk-hub.url").Trim() }

# Fixed drives with a letter; C: first (it is the one that fills up).
$vols = @(Get-Volume | Where-Object { $_.DriveType -eq 'Fixed' -and $_.DriveLetter -and $_.Size -gt 0 } |
          Sort-Object @{ e = { if ($_.DriveLetter -eq 'C') { 0 } else { 1 } } }, DriveLetter |
          Select-Object -First 6 |
          ForEach-Object { [ordered]@{ name = "$($_.DriveLetter):"; mount = "$($_.DriveLetter):\";
                                       size_bytes = [int64]$_.Size; free_bytes = [int64]$_.SizeRemaining } })
$state = "$dir\disk-push.state.json"
$free0 = [int64]$vols[0].free_bytes
$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$st = $null
if (Test-Path $state) { try { $st = Get-Content -Raw $state | ConvertFrom-Json } catch { $st = $null } }
# Optional unprivileged steward handoff; invalid/unreadable status never blocks disk reports.
$steward = $null
try {
  $statusPath = (Get-Content -Raw "$dir\steward-status.path").Trim()
  if (Test-Path -LiteralPath $statusPath -PathType Leaf) {
    $candidate = Get-Content -Raw -LiteralPath $statusPath | ConvertFrom-Json
    if ($candidate.band -is [string] -and $candidate.band -cmatch '\A[a-z]{1,10}\z' -and
        $candidate.tick_at -is [string] -and $candidate.tick_at.Length -ge 1 -and $candidate.tick_at.Length -le 40 -and
        ($candidate.actions -is [int] -or $candidate.actions -is [long]) -and
        $candidate.actions -ge 0 -and $candidate.actions -le 1000) {
      $steward = [ordered]@{ band = $candidate.band; tick_at = $candidate.tick_at; actions = $candidate.actions }
    }
  }
} catch { $steward = $null }
$stewardChanged = $steward -and (!$st -or $st.steward_tick_at -cne $steward.tick_at)
if (-not $Force -and $st -and -not $stewardChanged) {
  $moved = [math]::Abs($free0 - [int64]$st.last_free)
  if ($now -lt [int64]$st.next_due -and $moved -lt [int64]$st.force_delta) { exit 0 }   # quiet tick
}
$payload = [ordered]@{ observed_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'); volumes = $vols }
if ($steward) { $payload['steward'] = $steward }
$body = $payload | ConvertTo-Json -Depth 4 -Compress
$log = "$dir\disk-push.log"
try {
  $r = Invoke-RestMethod -Method Post -Uri "$url`?host=winbox&k=$token" -ContentType 'application/json' -Body $body -TimeoutSec 20
  $interval = if ($r.next_push_after_s) { [int64]$r.next_push_after_s } else { 600 }
  $fdelta   = if ($r.force_delta_bytes) { [int64]$r.force_delta_bytes } else { 1000000000 }
  [ordered]@{ next_due = $now + $interval - 30; last_free = $free0; force_delta = $fdelta; steward_tick_at = $(if ($steward) { $steward.tick_at } else { $null }) } |
    ConvertTo-Json -Compress | Set-Content $state
  "$(Get-Date -Format s) reported free=$free0 next=${interval}s ($($r.reason))" | Set-Content $log
} catch {
  "$(Get-Date -Format s) FAIL disk hub report failed" | Set-Content $log
  exit 1
}

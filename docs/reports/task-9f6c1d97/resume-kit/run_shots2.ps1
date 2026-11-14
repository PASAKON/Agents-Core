param([string]$Names, [string]$Tag = 'run', [string]$Jobs = 'jobs.json')
$ErrorActionPreference = 'Continue'
$root = 'C:\mooniex\ep04-shots'
$py = 'C:\mooniex\pwvenv\Scripts\python.exe'
$log = "$root\run.log"
function L($m) { ((Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') + ' ' + $m) | Add-Content -Path $log -Encoding utf8 }
$fails = 0
foreach ($n in ($Names -split ',')) {
  if (Test-Path "$root\out\$n.png") { L "$n skip exists"; continue }
  if (Test-Path "$root\STOP") { L "STOP file seen before $n"; break }
  # RAM gate: Available MBytes >= 1024, wait up to 15 min
  $ok = $false; $t0 = Get-Date
  while (((Get-Date) - $t0).TotalMinutes -lt 15) {
    $av = (Get-Counter '\Memory\Available MBytes').CounterSamples[0].CookedValue
    $other = @(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'chatgpt_images' -and $_.ProcessId -ne $PID -and $_.CommandLine -notmatch 'run_shots' }).Count
    if ($av -ge 1024 -and $other -eq 0) { $ok = $true; break }
    Start-Sleep -Seconds 30
  }
  if (-not $ok) { L "RAMGATE stop before $n avail=$av other=$other"; 'ramgate' | Set-Content "$root\STOPPED"; break }
  L "$n start avail=$([int]$av)"
  & $py "$root\chatgpt_images.py" --json "$root\$Jobs" --one $n --out "$root\out" *> "$root\out\$n.runlog.txt"
  $rc = $LASTEXITCODE
  L "$n exit=$rc"
  if ($rc -eq 5 -or $rc -eq 6) { "hazard rc=$rc at $n" | Set-Content "$root\STOPPED"; break }
  if ($rc -ne 0) { $fails++ } else { $fails = 0 }
  if ($fails -ge 3) { "3 consecutive failures at $n" | Set-Content "$root\STOPPED"; break }
}
L "wrapper $Tag finished"

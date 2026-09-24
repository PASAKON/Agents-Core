# winbox rebuild R2: bot code + venv + templates + org tools + core scheduled tasks. Logs to C:\mooniex\rebuild\r2.log
$ErrorActionPreference = 'Continue'
$log = 'C:\mooniex\rebuild\r2.log'
function L($m) { Add-Content -Path $log -Value ("{0} {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$H = 'C:\Users\passg'; $BOT = "$H\cookierun-bot"
L "R2 start"
# 1. code
if (-not (Test-Path "$BOT\.git")) {
  & git clone -q git@github-cookierun:PASAKON/MoonieX-CookierunBot.git $BOT 2>&1 | ForEach-Object { L "  git: $_" }
}
L ("clone: " + (& git -C $BOT log -1 --format='%h %s' 2>&1))
# 2. templates + config (77 files kept on Contabo; some were never in git)
& tar -xzf C:\mooniex\rebuild\bot-templates.tgz -C $BOT 2>&1 | ForEach-Object { L "  tar: $_" }
L ("templates: " + (Get-ChildItem "$BOT\templates" -File).Count + " files; config screens: " + ((Get-Content "$BOT\config.json" -Raw | ConvertFrom-Json).screens.Count))
Set-Content "$BOT\tools\rclone_path.txt" ((Get-Command rclone -ErrorAction SilentlyContinue).Source)
# 3. venv from the old box's freeze (best effort: one line at a time so one dead pin does not stop the rest)
if (-not (Test-Path "$BOT\.venv\Scripts\python.exe")) { & py -3.11 -m venv "$BOT\.venv" 2>&1 | ForEach-Object { L "  venv: $_" } }
$py = "$BOT\.venv\Scripts\python.exe"
& $py -m pip install -q --upgrade pip 2>&1 | Out-Null
$ok = 0; $bad = @()
foreach ($line in Get-Content C:\mooniex\rebuild\venv-freeze.txt) {
  $line = $line.Trim(); if (-not $line -or $line.StartsWith('#') -or $line -match '^-e |@ file:|\+cu|nvidia') { continue }
  & $py -m pip install -q $line 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0) { $ok++ } else { $bad += $line }
}
L "pip: $ok pinned packages installed; failed: $($bad.Count) -> $($bad -join ', ')"
foreach ($m in 'cv2','numpy','mss','dxcam','onnxruntime','pynput','requests','PIL') { $r = & $py -c "import $m; print('$m ok')" 2>&1; L ("  import " + ($r | Select-Object -Last 1)) }
# 4. org tools on the box
New-Item -ItemType Directory -Force -Path C:\mooniex\pclease | Out-Null
Copy-Item C:\mooniex\rebuild\pclease\* C:\mooniex\pclease\ -Force
L ("pclease: " + ((Get-ChildItem C:\mooniex\pclease -File).Name -join ', '))
# 5. core scheduled tasks from the old box's XML, paths + principal rewritten
$core = 'CookieRunAppSrc','CookieRunAsk','CookieRun-DiskSense','CookieRunStreamRetry','MooniexPCLease','MooniexPCLeaseClear','MooniexCookieRunProbe','MooniexCookieRunRevive','MooniexCtoRun'
foreach ($t in $core) {
  $src = "C:\mooniex\rebuild\tasks\$t.xml"
  if (-not (Test-Path $src)) { L "task $t : no xml"; continue }
  $xml = Get-Content $src -Raw -Encoding Unicode
  $xml = $xml -replace 'C:\\Users\\UsEr', 'C:\Users\passg' -replace '<UserId>[^<]*</UserId>', '<UserId>GoB\passg</UserId>' -replace '<Author>[^<]*</Author>', '<Author>GoB\passg</Author>'
  $tmp = "C:\mooniex\rebuild\tasks\$t.new.xml"; Set-Content -Path $tmp -Value $xml -Encoding Unicode
  $r = & schtasks /Create /TN $t /XML $tmp /F 2>&1 | Out-String
  L ("task $t : " + $r.Trim())
}
L "R2 done"; Set-Content C:\mooniex\rebuild\r2.done (Get-Date -Format s)
